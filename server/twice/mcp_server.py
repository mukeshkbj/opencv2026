"""Twice's OpenCV 5 tools over the Model Context Protocol.

Any MCP client (Claude Desktop, Claude Code, or eval/mcp_agent.py) can run a move-out check through these tools.
Each tool calls the real Twice API in-process, so the photos, seals, trace and signed report are the same as in the
web app. The OpenCV 5 pipeline and the rule triage decide every verdict. The calling agent chooses which tool to
call next, asks the renter for the photos the tools request, sends unclear findings to a person, and seals the report.

Run:  cd server && python -m twice.mcp_server            (stdio)
      cd server && python -m twice.mcp_server --http     (Streamable HTTP on port 8765, path /mcp)

TWICE_MCP_STILL_CAMERA=1 makes the sample camera return the move-out photo for a side-step request, as if the
renter did not move. eval/mcp_agent.py uses it for the counterfactual run.
"""
import functools
import os
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient
from mcp.server.mcpserver import MCPServer

from . import app as twice_app
from . import objects, vision
from .app import app, load, save

# The app logs CloudWatch metrics with print(). On stdio, stdout carries the protocol, so the logs go to stderr.
twice_app.print = functools.partial(print, file=sys.stderr)

INSTRUCTIONS = (
    "Twice compares move-in and move-out photos of the same spots and produces signed evidence. "
    "Workflow: start_sample_check or start_check; for each spot, take or receive the move-out photo and call "
    "compare_move_out; whenever a result carries a `request`, get exactly that photo (take_sample_photo on sample "
    "checks, or ask the renter) and call submit_followup; when a spot is done, call request_human_review for every "
    "finding whose verdict is 'uncertain' or 'changed'; when every spot is done, call seal_report. "
    "The tools decide verdicts from measurements. Do not invent or change verdicts."
)

server = MCPServer("twice-opencv", instructions=INSTRUCTIONS, version="1.0.0")
client = TestClient(app)
_seen: dict[tuple[str, str], int] = {}
_reviews: dict[str, list[dict]] = {}
METRICS = ("structure", "chroma", "score", "brightening", "illumination", "lighting_only")


def _ok(resp) -> dict:
    if resp.status_code >= 400:
        raise ValueError(f"Twice API {resp.status_code}: {resp.json().get('detail', resp.text)}")
    return resp.json()


def _read(path: str) -> bytes:
    p = Path(path).expanduser()
    if not p.is_file():
        raise ValueError(f"no such photo: {path}")
    return p.read_bytes()


def _spot_view(cid: str, spot: dict) -> dict:
    """What an agent needs from a spot: status, findings with their measurements, the pending request, new trace rows."""
    st = spot["state"]
    seen = _seen.get((cid, spot["id"]), 0)
    _seen[(cid, spot["id"])] = len(st["trace"])
    return {
        "check_id": cid,
        "spot_id": spot["id"],
        "label": spot["label"],
        "status": st["status"],
        "registration": st.get("registration") or None,
        "findings": [{"id": f["id"], "verdict": f["verdict"], "kind": f["kind"], "box": f["box"],
                      "caption": f["caption"], "evidence": f["evidence"],
                      "measurements": {k: round(v, 3) if isinstance(v, float) else v
                                       for k, v in f["metrics"].items() if k in METRICS}}
                     for f in st["findings"]],
        "request": st["pending"],
        "followups_used": st["followups_used"],
        "new_trace": [{k: t[k] for k in ("tool", "result", "decision")} for t in st["trace"][seen:]],
    }


def _check_view(check: dict) -> dict:
    return {"check_id": check["id"], "name": check["name"], "sample": check.get("sample"),
            "sealed": [s["phase"] for s in check["seals"]],
            "spots": [{"spot_id": s["id"], "label": s["label"], "has_move_out": bool(s["after"]),
                       "status": s["state"]["status"]} for s in check["spots"]]}


@server.tool()
def health() -> dict:
    """OpenCV version and build (COOL or pip), CPU architecture, DNN engine, signer and captioner of this server."""
    return _ok(client.get("/api/health"))


@server.tool()
def start_sample_check() -> dict:
    """Create a check from the bundled sample (a rental car and an apartment, 3 spots). The move-in photos are sealed.
    Use take_sample_photo as the renter's camera for this check."""
    check = _ok(client.post("/api/samples/apartment"))
    if os.environ.get("TWICE_MCP_STILL_CAMERA") == "1":
        record = load(check["id"])
        for spot in record["spots"]:
            spot["sample"]["parallax"] = spot["sample"]["after"]
        save(record)
    return _check_view(check)


@server.tool()
def start_check(name: str, move_in_photos: list[str], labels: list[str] | None = None) -> dict:
    """Create a check from move-in photos on disk (JPEG or PNG paths, at most 8, one per spot) and seal them.
    `labels` names each spot, for example 'Kitchen, worktop'."""
    check = _ok(client.post("/api/checks", json={"name": name}))
    labels = labels or []
    for i, path in enumerate(move_in_photos):
        label = labels[i] if i < len(labels) else ""
        _ok(client.post(f"/api/checks/{check['id']}/spots", params={"label": label},
                        files={"file": (Path(path).name, _read(path), "image/jpeg")}))
    _ok(client.post(f"/api/checks/{check['id']}/seal"))
    return _check_view(load(check["id"]))


@server.tool()
def check_photo_quality(photo_path: str) -> dict:
    """Sharpness, exposure and texture of one photo, measured with OpenCV. Use it before a comparison to decide
    whether to ask for a better photo."""
    return _ok(client.post("/api/quality", content=_read(photo_path)))


@server.tool()
def compare_move_out(check_id: str, spot_id: str, photo_path: str) -> dict:
    """Register a move-out photo onto the sealed move-in photo (SIFT, FLANN, USAC_MAGSAC homography), build the
    change map, triage each region (lighting, glare, size, NanoDet objects) and plan the next step.
    If the result has a `request`, the spot needs that follow-up photo. Status 'retake' means take the move-out
    photo again from the move-in position."""
    spot = _ok(client.post(f"/api/checks/{check_id}/spots/{spot_id}/after",
                           files={"file": (Path(photo_path).name, _read(photo_path), "image/jpeg")}))
    return _spot_view(check_id, spot)


@server.tool()
def submit_followup(check_id: str, spot_id: str, photo_path: str) -> dict:
    """Send the follow-up photo that the last result requested (a side-step photo for 'parallax', a close-up for
    'closeup'). OpenCV checks that the camera really moved, then rules the finding in or out."""
    spot = _ok(client.post(f"/api/checks/{check_id}/spots/{spot_id}/followup",
                           files={"file": (Path(photo_path).name, _read(photo_path), "image/jpeg")}))
    return _spot_view(check_id, spot)


@server.tool()
def take_sample_photo(check_id: str, spot_id: str) -> dict:
    """Sample checks only: stands in for the renter's camera. Takes the move-out photo first, then whichever
    follow-up photo the spot is waiting for, and runs it through the same pipeline as compare_move_out and
    submit_followup."""
    spot = _ok(client.post(f"/api/checks/{check_id}/spots/{spot_id}/sample-shot"))
    return _spot_view(check_id, spot)


@server.tool()
def detect_objects(photo_path: str) -> list[dict]:
    """NanoDet-Plus on the OpenCV 5 DNN engine (ENGINE_NEW): COCO objects with confidence and box [x, y, w, h]."""
    img = vision.decode(_read(photo_path))
    return [{"name": d.name, "conf": round(d.conf, 3), "box": list(d.box)} for d in objects.detect(img)]


@server.tool()
def get_spot(check_id: str, spot_id: str) -> dict:
    """Current state of one spot, with its full trace."""
    spot = next((s for s in load(check_id)["spots"] if s["id"] == spot_id), None)
    if spot is None:
        raise ValueError(f"no spot {spot_id}")
    _seen[(check_id, spot_id)] = 0
    return _spot_view(check_id, spot)


@server.tool()
def request_human_review(check_id: str, spot_id: str, finding_id: str, reason: str) -> dict:
    """Hand one finding to a person (the renter, the landlord or a claims handler). Use it for every 'uncertain'
    finding, and for 'changed' findings that will be claimed. The request is listed in seal_report's result."""
    spot = next((s for s in load(check_id)["spots"] if s["id"] == spot_id), None)
    if spot is None or not any(f["id"] == finding_id for f in spot["state"]["findings"]):
        raise ValueError(f"no finding {finding_id} in spot {spot_id}")
    entry = {"spot_id": spot_id, "finding_id": finding_id, "reason": reason[:300], "at": round(time.time(), 3)}
    _reviews.setdefault(check_id, []).append(entry)
    return {"queued": entry, "open_reviews": len(_reviews[check_id])}


@server.tool()
def seal_report(check_id: str) -> dict:
    """Sign the move-out report (findings, evidence and the full trace of every spot), then verify the photos and
    both seals. Fails while a spot still waits for a follow-up photo."""
    check = _ok(client.post(f"/api/checks/{check_id}/report"))
    ver = _ok(client.get(f"/api/checks/{check_id}/verify"))
    return {**_check_view(check),
            "findings": [{"spot_id": s["id"], "id": f["id"], "verdict": f["verdict"], "kind": f["kind"],
                          "caption": f["caption"]} for s in check["spots"] for f in s["state"]["findings"]],
            "human_reviews": _reviews.get(check_id, []),
            "verified": ver["ok"], "algorithm": ver["algorithm"], "key_fingerprint": ver["fingerprint"]}


def main() -> None:
    if "--http" in sys.argv:
        server.run("streamable-http", port=int(os.environ.get("TWICE_MCP_PORT", "8765")))
    else:
        server.run()


if __name__ == "__main__":
    main()

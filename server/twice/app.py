import json
import os
import secrets
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import evidence, vision
from .agent import Agent, SpotState
from .caption import Captioner
from .store import get_json, make_store, put_json

MAX_UPLOAD = 15 * 1024 * 1024
MAX_SPOTS = 8
SAMPLES = Path(__file__).resolve().parent.parent / "samples"
WEB = Path(os.environ.get("TWICE_WEB", Path(__file__).resolve().parents[2] / "web" / "dist"))

app = FastAPI(title="Twice", docs_url="/api/docs", openapi_url="/api/openapi.json")
store = make_store()
signer = evidence.make_signer()
captioner = Captioner()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def metric(name: str, value: float, unit: str = "Milliseconds", **dims: str) -> None:
    """CloudWatch embedded metric format; plain JSON log line when run locally."""
    print(json.dumps({
        "_aws": {"Timestamp": int(time.time() * 1000), "CloudWatchMetrics": [{
            "Namespace": "Twice", "Dimensions": [list(dims)] if dims else [[]],
            "Metrics": [{"Name": name, "Unit": unit}]}]},
        name: value, **dims}))


def load(cid: str) -> dict:
    if not cid.isalnum():
        raise HTTPException(404, "check not found")
    try:
        return get_json(store, f"checks/{cid}/check.json")
    except KeyError:
        raise HTTPException(404, "check not found") from None


def save(check: dict) -> None:
    put_json(store, f"checks/{check['id']}/check.json", check)


def spot_of(check: dict, sid: str) -> dict:
    for s in check["spots"]:
        if s["id"] == sid:
            return s
    raise HTTPException(404, "spot not found")


async def read_image(request: Request | None = None, file: UploadFile | None = None) -> tuple[bytes, np.ndarray]:
    data = await file.read(MAX_UPLOAD + 1) if file else await request.body()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "image larger than 15 MB")
    try:
        return data, vision.decode(data)
    except ValueError:
        raise HTTPException(415, "not a readable image") from None


def put_photo(cid: str, name: str, data: bytes, img: np.ndarray) -> dict:
    key = f"checks/{cid}/{name}.jpg"
    store.put(key, data, "image/jpeg")
    h, w = img.shape[:2]
    return {"key": key, "sha256": evidence.sha256(data), "at": now(), "w": w, "h": h}


@lru_cache(maxsize=32)
def before_frames(key: str) -> tuple[vision.Keyframe, vision.Keyframe]:
    img = vision.decode(store.get(key))
    return vision.Keyframe.build(img), vision.guide_reference(img)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "opencv": cv2.__version__, "signer": signer.algorithm, "captioner": captioner.source}


@app.post("/api/checks")
async def create_check(request: Request) -> dict:
    body = await request.json() if request.headers.get("content-length", "0") != "0" else {}
    check = {"id": secrets.token_hex(8), "name": str(body.get("name") or "Untitled check")[:80],
             "created_at": now(), "spots": [], "seals": []}
    save(check)
    return check


@app.get("/api/checks/{cid}")
def get_check(cid: str) -> dict:
    return load(cid)


@app.post("/api/quality")
async def quality(request: Request) -> dict:
    _, img = await read_image(request)
    return vision.quick_quality(img).as_dict()


@app.post("/api/checks/{cid}/spots")
async def add_spot(cid: str, file: UploadFile, label: str = "") -> dict:
    check = load(cid)
    if check["seals"]:
        raise HTTPException(409, "the before set is sealed")
    if len(check["spots"]) >= MAX_SPOTS:
        raise HTTPException(409, f"at most {MAX_SPOTS} spots")
    data, img = await read_image(file=file)
    sid = f"s{len(check['spots']) + 1}"
    q = vision.quick_quality(img)
    spot = {"id": sid, "label": label[:60] or f"Spot {len(check['spots']) + 1}",
            "before": {**put_photo(cid, f"{sid}-before", data, img), "quality": q.as_dict()},
            "after": None, "followups": [], "state": SpotState().to_dict()}
    check["spots"].append(spot)
    save(check)
    return spot


def manifest(check: dict, phase: str) -> dict:
    spots = []
    for s in check["spots"]:
        entry = {"id": s["id"], "label": s["label"], "before": {k: s["before"][k] for k in ("sha256", "at")}}
        if phase == "report" and s["after"]:
            entry["after"] = {k: s["after"][k] for k in ("sha256", "at")}
            entry["followups"] = [{k: f[k] for k in ("sha256", "at", "kind")} for f in s["followups"]]
            entry["findings"] = [{k: f[k] for k in ("id", "box", "verdict", "kind", "caption")}
                                 for f in s["state"]["findings"]]
        spots.append(entry)
    return {"check": check["id"], "name": check["name"], "phase": phase, "spots": spots,
            "opencv": cv2.__version__, "signed_at": now()}


def seal(check: dict, phase: str) -> dict:
    m = manifest(check, phase)
    body = evidence.canonical(m)
    entry = {"phase": phase, "manifest": m, "digest": evidence.sha256(body),
             "signature": signer.sign(body), "algorithm": signer.algorithm}
    check["seals"].append(entry)
    return entry


@app.post("/api/checks/{cid}/seal")
def seal_before(cid: str) -> dict:
    check = load(cid)
    if not check["spots"]:
        raise HTTPException(409, "add at least one spot first")
    if any(s["phase"] == "before" for s in check["seals"]):
        raise HTTPException(409, "already sealed")
    entry = seal(check, "before")
    save(check)
    return entry


@app.post("/api/checks/{cid}/spots/{sid}/guide")
async def guide(cid: str, sid: str, request: Request) -> dict:
    spot = spot_of(load(cid), sid)
    _, img = await read_image(request)
    t0 = time.perf_counter()
    g = vision.guide(img, before_frames(spot["before"]["key"])[1])
    ms = (time.perf_counter() - t0) * 1000
    metric("GuideLatency", round(ms, 1), Route="guide")
    return {**g.as_dict(), "ms": round(ms)}


def _persist_views(cid: str, sid: str, res: vision.Comparison) -> None:
    store.put(f"checks/{cid}/{sid}-view-before.jpg", cv2.imencode(".jpg", res.before, [cv2.IMWRITE_JPEG_QUALITY, 88])[1].tobytes(), "image/jpeg")
    store.put(f"checks/{cid}/{sid}-view-after.jpg", cv2.imencode(".jpg", res.after_aligned, [cv2.IMWRITE_JPEG_QUALITY, 88])[1].tobytes(), "image/jpeg")
    heat = (np.clip(res.heat, 0, 1) * 255).astype(np.uint8)
    store.put(f"checks/{cid}/{sid}-view-heat.png", cv2.imencode(".png", heat)[1].tobytes(), "image/png")


def _caption(cid: str, sid: str, state: SpotState) -> None:
    pending = [f for f in state.findings if f.verdict == "changed" and not f.caption]
    if not pending:
        return
    before = vision.decode(store.get(f"checks/{cid}/{sid}-view-before.jpg"))
    after = vision.decode(store.get(f"checks/{cid}/{sid}-view-after.jpg"))
    for f in pending:
        x, y, w, h = f.box
        pad = max(24, max(w, h) // 2)
        y0, y1, x0, x1 = max(0, y - pad), y + h + pad, max(0, x - pad), x + w + pad
        label, needs_human = captioner(f.kind, before[y0:y1, x0:x1], after[y0:y1, x0:x1])
        f.caption = label
        if needs_human:
            f.verdict = "uncertain"
            f.evidence.append("the language model could not name the change: left for a human")
    state.trace.append({"t": round(time.time(), 3), "tool": "caption", "result": f"{len(pending)} labelled by {captioner.source}", "decision": ""})


@app.post("/api/checks/{cid}/spots/{sid}/after")
async def add_after(cid: str, sid: str, file: UploadFile) -> dict:
    check = load(cid)
    spot = spot_of(check, sid)
    data, img = await read_image(file=file)
    spot["after"] = put_photo(cid, f"{sid}-after", data, img)
    spot["followups"] = []
    state = SpotState()
    t0 = time.perf_counter()
    res = Agent(state).on_after(before_frames(spot["before"]["key"])[0], vision.Keyframe.build(img))
    metric("CompareLatency", round((time.perf_counter() - t0) * 1000, 1), Route="after")
    if res.ok:
        _persist_views(cid, sid, res)
    if state.status == "done":
        _caption(cid, sid, state)
    spot["state"] = state.to_dict()
    save(check)
    return spot


@app.post("/api/checks/{cid}/spots/{sid}/followup")
async def add_followup(cid: str, sid: str, file: UploadFile) -> dict:
    check = load(cid)
    spot = spot_of(check, sid)
    state = SpotState.from_dict(spot["state"])
    if state.pending is None:
        raise HTTPException(409, "no follow-up requested")
    data, img = await read_image(file=file)
    kind = state.pending.kind
    spot["followups"].append({**put_photo(cid, f"{sid}-{state.pending.id}", data, img), "kind": kind})
    Agent(state).on_followup(before_frames(spot["before"]["key"])[0], img)
    if state.status == "done":
        _caption(cid, sid, state)
    spot["state"] = state.to_dict()
    save(check)
    return spot


@app.post("/api/checks/{cid}/report")
def report(cid: str) -> dict:
    check = load(cid)
    if not any(s["after"] for s in check["spots"]):
        raise HTTPException(409, "no after photos yet")
    if any(s["after"] and s["state"]["status"] != "done" for s in check["spots"]):
        raise HTTPException(409, "some spots still need a follow-up photo")
    check["seals"] = [s for s in check["seals"] if s["phase"] != "report"]
    seal(check, "report")
    save(check)
    return check


@app.get("/api/checks/{cid}/files/{name}")
def file(cid: str, name: str) -> Response:
    load(cid)
    if "/" in name or ".." in name:
        raise HTTPException(404)
    try:
        data = store.get(f"checks/{cid}/{name}")
    except KeyError:
        raise HTTPException(404) from None
    media = "image/png" if name.endswith(".png") else "image/jpeg"
    return Response(data, media_type=media, headers={"Cache-Control": "private, max-age=86400, immutable"})


@app.get("/api/key")
def key() -> dict:
    return {"algorithm": signer.algorithm, "public_key": signer.public_pem()}


@app.get("/api/checks/{cid}/verify")
def verify(cid: str) -> dict:
    check = load(cid)
    files = []
    for s in check["spots"]:
        photos = [("before", s["before"])] + ([("after", s["after"])] if s["after"] else [])
        photos += [(f["kind"], f) for f in s["followups"]]
        for role, p in photos:
            ok = evidence.sha256(store.get(p["key"])) == p["sha256"]
            files.append({"spot": s["id"], "role": role, "sha256": p["sha256"], "ok": ok})
    pem = signer.public_pem()
    seals = []
    for entry in check["seals"]:
        body = evidence.canonical(entry["manifest"])
        seals.append({"phase": entry["phase"], "digest": entry["digest"],
                      "digest_ok": evidence.sha256(body) == entry["digest"],
                      "signature_ok": evidence.verify(pem, entry["algorithm"], body, entry["signature"])})
    return {"files": files, "seals": seals, "algorithm": signer.algorithm, "public_key": pem,
            "ok": all(f["ok"] for f in files) and all(s["digest_ok"] and s["signature_ok"] for s in seals)}


@app.post("/api/samples/{name}")
def sample(name: str) -> dict:
    folder = SAMPLES / name
    if not name.isalnum() or not folder.is_dir():
        raise HTTPException(404, "no such sample")
    meta = json.loads((folder / "sample.json").read_text())
    check = {"id": secrets.token_hex(8), "name": meta["name"], "created_at": now(), "spots": [], "seals": [],
             "sample": name}
    for i, spot_meta in enumerate(meta["spots"], 1):
        data = (folder / spot_meta["before"]).read_bytes()
        img = vision.decode(data)
        q = vision.quick_quality(img)
        check["spots"].append({"id": f"s{i}", "label": spot_meta["label"],
                               "before": {**put_photo(check["id"], f"s{i}-before", data, img), "quality": q.as_dict()},
                               "after": None, "followups": [], "state": SpotState().to_dict(),
                               "sample_after": spot_meta.get("after"), "sample_followup": spot_meta.get("followup")})
    seal(check, "before")
    save(check)
    return check


@app.get("/api/samples/{name}/{file_name}")
def sample_file(name: str, file_name: str) -> FileResponse:
    p = SAMPLES / name / file_name
    if not name.isalnum() or "/" in file_name or ".." in file_name or not p.is_file():
        raise HTTPException(404)
    return FileResponse(p)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    print(json.dumps({"event": "error", "path": request.url.path, "error": type(exc).__name__, "detail": str(exc)[:300]}))
    return JSONResponse({"detail": "internal error"}, status_code=500)


if WEB.is_dir():
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str) -> FileResponse:
        p = WEB / path
        return FileResponse(p if path and p.is_file() else WEB / "index.html")

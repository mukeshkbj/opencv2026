"""Agent-level benchmark: runs the full agent loop, including the follow-up photos it asks for.

Run from server/:  python eval/agent_bench.py [eval/scenes] [--out ../docs/eval]
Uses the same pairs as bench.py, once per RANSAC seed: the summary pools all seeds and per_seed gives the spread.
A side-step request gets a new camera position of the same scene; a glare patch moves to a new place on the surface,
damage stays. A close-up request gets a tighter shot of the area.
"""
import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench  # noqa: E402
import synth  # noqa: E402
from twice.agent import Agent, SpotState  # noqa: E402
from twice.vision import Keyframe  # noqa: E402

SCENES = Path(__file__).resolve().parent / "scenes"


def parallax_shot(pair: dict, rng: np.random.Generator) -> np.ndarray:
    world = pair["world"]
    if pair["set"] == "specular":
        world = pair["source"].copy()
        bench._specular(world, rng)
    return synth.camera(world, rng, 0.035)


def closeup_shot(pair: dict, box: list[int], rng: np.random.Generator) -> np.ndarray:
    world = pair["world"]
    h, w = world.shape[:2]
    my, mx = int(h * synth.MARGIN), int(w * synth.MARGIN)
    x, y, bw, bh = box
    pad = max(bw, bh, 60)
    x0, y0 = max(0, x + mx - pad), max(0, y + my - pad)
    x1, y1 = min(w, x + mx + bw + pad), min(h, y + my + bh + pad)
    patch = cv2.resize(world[y0:y1, x0:x1], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    ph, pw = patch.shape[:2]
    src = np.float32([[0, 0], [pw, 0], [pw, ph], [0, ph]])
    jitter = rng.normal(0, 0.02 * min(ph, pw), (4, 2)).astype(np.float32)
    patch = cv2.warpPerspective(patch, cv2.getPerspectiveTransform(src, src + jitter), (pw, ph), borderMode=cv2.BORDER_REFLECT)
    patch = np.clip(patch * rng.uniform(0.85, 1.15) + rng.normal(0, 3, patch.shape), 0, 255).astype(np.uint8)
    return cv2.imdecode(cv2.imencode(".jpg", patch, [cv2.IMWRITE_JPEG_QUALITY, 85])[1], cv2.IMREAD_COLOR)


def run_pair(job: tuple) -> dict:
    kind, idx, seed = job
    cv2.setNumThreads(2)
    cv2.setRNGSeed(seed)
    pair = bench.make_pair(kind, idx, bench.load_scenes(SCENES))
    rng = np.random.default_rng([bench.SEED, 99, bench.SET_ID[kind], idx])
    before = Keyframe.build(pair["before"], bench.SIDE)
    state = SpotState()
    agent = Agent(state)
    agent.on_after(before, Keyframe.build(pair["after"], bench.SIDE))
    asked = []
    while state.status == "needs_followup":
        req = state.pending
        asked.append(req.kind)
        img = parallax_shot(pair, rng) if req.kind == "parallax" else closeup_shot(pair, req.box, rng)
        agent.on_followup(before, img)
    changed = [f for f in state.findings if f.verdict == "changed"]
    rec = {"set": kind, "idx": idx, "seed": seed, "status": state.status, "followups": asked,
           "changed": len(changed), "uncertain": sum(f.verdict == "uncertain" for f in state.findings), "defects": []}
    hit = [False] * len(changed)
    for d in pair["defects"]:
        found = False
        for i, f in enumerate(changed):
            x, y, w, h = f.box
            if d["mask"][y:y + h, x:x + w].any():
                found = hit[i] = True
        rec["defects"].append({"kind": d["kind"], "hit": found})
    rec["false_changed"] = hit.count(False)
    return rec


def summarize(recs: list[dict]) -> dict:
    dmg = [r for r in recs if r["set"] == "damage"]
    tp = sum(d["hit"] for r in dmg for d in r["defects"])
    n_def = sum(len(r["defects"]) for r in dmg)
    fp = sum(r["false_changed"] for r in dmg)
    flagged = lambda kinds: [r for r in recs if r["set"] in kinds]
    rate = lambda rs: round(sum(r["false_changed"] > 0 for r in rs) / len(rs), 3)
    return {
        "recall": round(tp / n_def, 3),
        "precision": round(tp / max(1, tp + fp), 3),
        "false_changed_per_damage_pair": round(fp / len(dmg), 2),
        "nochange_false_alarm_rate": rate(flagged(["nochange"])),
        "lighting_false_alarm_rate": rate(flagged(bench.LIGHTING)),
        "lighting_false_alarm_by_type": {k: rate(flagged([k])) for k in bench.LIGHTING},
        "followups_per_pair": round(sum(len(r["followups"]) for r in recs) / len(recs), 2),
        "followup_kinds": {k: sum(r["followups"].count(k) for r in recs) for k in ("parallax", "closeup")},
        "cant_judge_per_pair": round(sum(r["uncertain"] for r in recs) / len(recs), 2),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "docs" / "eval"))
    ap.add_argument("--seeds", type=int, default=5, help="RANSAC seeds; each runs all 170 pairs")
    args = ap.parse_args()
    jobs = [(k, i, seed) for seed in range(args.seeds) for k, n in bench.MAIN_SETS.items() for i in range(n)]
    t0 = time.time()
    with ProcessPoolExecutor(12) as pool:
        recs = list(pool.map(run_pair, jobs, chunksize=2))
    runs = [summarize([r for r in recs if r["seed"] == seed]) for seed in range(args.seeds)]
    spread = {k: {"mean": round(float(np.mean([s[k] for s in runs])), 3), "min": min(s[k] for s in runs),
                  "max": max(s[k] for s in runs)}
              for k, v in runs[0].items() if isinstance(v, float)}
    result = {"summary": summarize(recs), "per_seed": spread, "seeds": args.seeds,
              "seconds": round(time.time() - t0, 1), "pairs": recs}
    print(json.dumps({"summary": result["summary"], "per_seed": spread}, indent=1), f"{result['seconds']} s")
    Path(args.out, "agent.json").write_text(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()

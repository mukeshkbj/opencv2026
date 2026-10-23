"""Hybrid benchmark: defects from the synthetic generator, drawn onto real Oxford photos.

Run from server/:  python eval/hybrid_bench.py [--out ../docs/eval] [--draws 8]
Each pair that real_bench.py judges (not the retake pairs) becomes a damage pair: the synth.py defects (and a cast shadow
in half of them) are drawn in the frame of image 1 and projected into the move-out photo with the ground-truth
homography of the sequence. Nothing else is simulated: the move-out photo keeps its real blur, noise, light and viewpoint.
Lighting-only controls draw a cast shadow or a glare patch alone. Follow-up requests are answered as in agent_bench.py,
except that a side-step shot is another real photo of the same sequence and a close-up is a crop of the real move-out photo.
Each job runs the full agent under its own RANSAC seed. The tolerant-first-pass ablation (the engine before the switch) runs the same jobs.
"""
import argparse
import functools
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_bench  # noqa: E402
import bench  # noqa: E402
import real_bench  # noqa: E402
import synth  # noqa: E402
from twice.agent import Agent, SpotState  # noqa: E402
from twice.vision import Keyframe  # noqa: E402

HYBRID_ID = 8
DRAWS = {"damage": 8, "clean": 3, "shadow": 3, "specular": 3}
ABLATIONS = ("full", "tolerant_first_pass")
images = functools.cache(real_bench.images)


def homography(seq: str, k: int) -> np.ndarray:
    return np.loadtxt(real_bench.CACHE / seq / f"H1to{k}p")


def layer(draw, shape: tuple, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Runs a synth.py drawing function on a black and a white canvas to recover its alpha and colour term."""
    lo, hi = np.zeros(shape, np.uint8), np.full(shape, 255, np.uint8)
    for canvas in (lo, hi):
        draw(canvas, np.random.default_rng(seed))
    return 1 - (hi.astype(np.float32) - lo).mean(2, keepdims=True) / 255, lo.astype(np.float32)


def composite(img: np.ndarray, layers: list, H: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    out = img.astype(np.float32)
    for alpha, term in layers:
        a = cv2.warpPerspective(alpha, H, (w, h)).reshape(h, w, 1)
        out = out * (1 - a) + cv2.warpPerspective(term, H, (w, h))
    return np.clip(out, 0, 255).astype(np.uint8)


def visible(mask: np.ndarray, H: np.ndarray, size: tuple) -> bool:
    ys, xs = np.nonzero(mask)
    box = np.float32([[xs.min(), ys.min()], [xs.max(), ys.min()], [xs.max(), ys.max()], [xs.min(), ys.max()]])
    p = cv2.perspectiveTransform(box.reshape(-1, 1, 2), H).reshape(-1, 2)
    return bool((p >= 0).all() and (p[:, 0] < size[1]).all() and (p[:, 1] < size[0]).all())


def draw_defect(kind: str, shape: tuple, rng: np.random.Generator, H: np.ndarray, size: tuple) -> tuple:
    for _ in range(50):
        mask = np.zeros(shape[:2], np.uint8)
        lay = layer(lambda img, r: synth.add_defect(img, mask, kind, r), shape, int(rng.integers(2 ** 32)))
        if visible(mask, H, size):
            break
    return lay, mask


def make_pair(seq: str, k: int, kind: str, draw: int) -> dict:
    imgs = images(seq)
    shape, H = imgs[0].shape, homography(seq, k)
    rng = np.random.default_rng([bench.SEED, HYBRID_ID, bench.SET_ID.get(kind, 0), list(real_bench.SEQUENCES).index(seq), k, draw])
    layers, defects = [], []
    if kind == "damage":
        for d in rng.choice(synth.DEFECTS, int(rng.integers(1, 4))):
            lay, mask = draw_defect(str(d), shape, rng, H, imgs[k - 1].shape[:2])
            layers.append(lay)
            defects.append({"kind": str(d), "mask": mask})
    if kind == "specular":
        layers.append(layer(bench._specular, shape, int(rng.integers(2 ** 32))))
    elif kind == "shadow" or (kind == "damage" and rng.random() < 0.5):
        layers.append(layer(synth.add_shadow, shape, int(rng.integers(2 ** 32))))
    return {"layers": layers, "defects": defects, "after": composite(imgs[k - 1], layers, H)}


def side_step(seq: str, k: int, judged: tuple, pair: dict, kind: str, rng: np.random.Generator) -> np.ndarray:
    j = min((j for j in range(2, 7) if j != k), key=lambda j: (j not in judged, abs(j - k), j))
    layers = pair["layers"]
    if kind == "specular":
        layers = [layer(bench._specular, images(seq)[0].shape, int(rng.integers(2 ** 32)))]
    return composite(images(seq)[j - 1], layers, homography(seq, j))


def close_up(seq: str, k: int, pair: dict, box: list, scale: float, rng: np.random.Generator) -> np.ndarray:
    x, y, w, h = (v / scale for v in box)
    p = cv2.perspectiveTransform(np.float32([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]).reshape(-1, 1, 2),
                                 homography(seq, k)).reshape(-1, 2)
    x0, y0 = p.min(0).astype(int)
    x1, y1 = p.max(0).astype(int)
    ih, iw = pair["after"].shape[:2]
    my, mx = int(ih * synth.MARGIN), int(iw * synth.MARGIN)
    return agent_bench.closeup_shot({"world": pair["after"]}, [x0 - mx, y0 - my, max(1, x1 - x0), max(1, y1 - y0)], rng)


def run_pair(job: tuple) -> dict:
    seq, k, kind, draw, ablation, judged = job
    cv2.setNumThreads(2)
    cv2.setRNGSeed(draw)
    pair = make_pair(seq, k, kind, draw)
    rng = np.random.default_rng([bench.SEED, HYBRID_ID, 99, bench.SET_ID.get(kind, 0), list(real_bench.SEQUENCES).index(seq), k, draw])
    with bench.patched(bench.ABLATIONS.get(ablation, {})):
        before = Keyframe.build(images(seq)[0])
        scale = before.image.shape[1] / images(seq)[0].shape[1]
        state = SpotState()
        agent = Agent(state)
        agent.on_after(before, Keyframe.build(pair["after"]))
        asked = []
        while state.status == "needs_followup":
            req = state.pending
            asked.append(req.kind)
            img = side_step(seq, k, judged, pair, kind, rng) if req.kind == "parallax" \
                else close_up(seq, k, pair, req.box, scale, rng)
            agent.on_followup(before, img)
    changed = [f for f in state.findings if f.verdict == "changed"]
    rec = {"sequence": seq, "pair": f"1-{k}", "set": kind, "draw": draw, "ablation": ablation, "status": state.status,
           "followups": asked, "changed": len(changed), "uncertain": sum(f.verdict == "uncertain" for f in state.findings),
           "defects": []}
    hit = [False] * len(changed)
    for d in pair["defects"]:
        m = cv2.resize(d["mask"], before.image.shape[1::-1], interpolation=cv2.INTER_LINEAR)
        ys, xs = np.nonzero(m > 40)
        gt = (int(xs.min()), int(ys.min()), int(np.ptp(xs)) + 1, int(np.ptp(ys)) + 1)
        found, best = False, 0.0
        for i, f in enumerate(changed):
            x, y, w, h = f.box
            if (m[y:y + h, x:x + w] > 40).any():
                found = hit[i] = True
                best = max(best, bench._box_iou(gt, tuple(f.box)))
        rec["defects"].append({"kind": d["kind"], "hit": found, "iou": round(best, 3)})
    rec["false_changed"] = hit.count(False)
    return rec


def summarize(recs: list[dict]) -> dict:
    dmg = [r for r in recs if r["set"] == "damage"]
    defects = [d for r in dmg for d in r["defects"]]
    tp = sum(d["hit"] for d in defects)
    strict = lambda ds: sum(d["hit"] and d["iou"] >= bench.IOU_STRICT for d in ds)
    fp = sum(r["false_changed"] for r in dmg)
    rate = lambda kind: round(sum(r["false_changed"] > 0 for r in recs if r["set"] == kind) / sum(r["set"] == kind for r in recs), 3)
    return {
        "damage_pairs": len(dmg), "defects": len(defects),
        "retakes_in_damage_pairs": sum(r["status"] == "retake" for r in dmg),
        "recall": round(tp / len(defects), 3),
        "recall_strict": round(strict(defects) / len(defects), 3),
        "precision": round(tp / max(1, tp + fp), 3),
        "false_changed_per_damage_pair": round(fp / len(dmg), 2),
        "recall_by_kind": {k: round(sum(d["hit"] for d in defects if d["kind"] == k) / sum(d["kind"] == k for d in defects), 3)
                           for k in synth.DEFECTS},
        "clean_false_alarm_rate": rate("clean"),
        "shadow_false_alarm_rate": rate("shadow"),
        "specular_false_alarm_rate": rate("specular"),
        "followups_per_pair": round(sum(len(r["followups"]) for r in recs) / len(recs), 2),
        "cant_judge_per_pair": round(sum(r["uncertain"] for r in recs) / len(recs), 2),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "docs" / "eval"))
    ap.add_argument("--draws", type=int, default=DRAWS["damage"], help="defect draws per pair")
    args = ap.parse_args()
    draws = {**DRAWS, "damage": args.draws}
    t0 = time.time()
    with ProcessPoolExecutor(12) as pool:
        probe = [("clean", seq, k) for seq in real_bench.SEQUENCES for k in range(2, 7)]
        first = list(pool.map(run_pair, [(s, k, "clean", 0, "full", ()) for _, s, k in probe], chunksize=2))
        judged = {(r["sequence"], int(r["pair"][2:])) for r in first if r["status"] != "retake"}
        by_seq = {s: tuple(k for q, k in sorted(judged) if q == s) for s in real_bench.SEQUENCES}
        jobs = [(s, k, kind, d, ab, by_seq[s]) for s, k in sorted(judged) for kind, n in draws.items()
                for d in range(n) for ab in ABLATIONS]
        recs = list(pool.map(run_pair, jobs, chunksize=2))
    result = {"judged_pairs": len(judged), "seconds": round(time.time() - t0, 1), "pairs": recs,
              "summary": {ab: summarize([r for r in recs if r["ablation"] == ab]) for ab in ABLATIONS}}
    print(json.dumps(result["summary"], indent=1), f"{result['judged_pairs']} pairs, {result['seconds']} s")
    Path(args.out, "hybrid.json").write_text(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()

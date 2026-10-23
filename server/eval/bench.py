"""Extended Twice benchmark: damage, no-change and lighting controls, registration stress, ablations, latency.

Run from server/:  python eval/bench.py <imgdir> [--out ../docs/eval] [--quick]
Every pair is generated from a seed derived from (seed, set, index), so any pair can be rebuilt on demand.
"""
import argparse
import contextlib
import json
import platform
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synth  # noqa: E402  (also puts server/ on sys.path)
from twice import vision  # noqa: E402
from twice.vision import Keyframe, compare  # noqa: E402

SEED = 20260
SIDE = 960  # same keyframe side synth.py uses
SET_ID = {"damage": 1, "nochange": 2, "exposure": 3, "colortemp": 4, "shadow": 5, "specular": 6, "stress": 7}
LIGHTING = ("exposure", "colortemp", "shadow", "specular")
N_DAMAGE, N_NOCHANGE, N_LIGHT, N_STRESS = 80, 30, 15, 12
SIZE_BUCKETS = (("small <150 px", 0, 150), ("medium 150-600 px", 150, 600), ("large >600 px", 600, 10 ** 9))
IOU_STRICT = 0.3
REG_TOL_PX = 3.0


# ---------------------------------------------------------------- pair generation

def load_scenes(folder: Path) -> list[tuple[str, np.ndarray]]:
    out = []
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() in {".jpg", ".png"}:
            img = cv2.imread(str(p))
            out.append((p.name, cv2.resize(img, (1100, int(1100 * img.shape[0] / img.shape[1])))))
    return out


def _rng(kind: str, idx: int) -> np.random.Generator:
    return np.random.default_rng([SEED, SET_ID[kind], idx])


def _specular(img: np.ndarray, rng: np.random.Generator) -> None:
    h, w = img.shape[:2]
    cx, cy = rng.uniform(0.2, 0.8) * w, rng.uniform(0.2, 0.8) * h
    sigma = rng.uniform(0.03, 0.07) * min(h, w)
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    a = (np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma ** 2)) * rng.uniform(0.6, 0.95))[..., None]
    img[:] = (img * (1 - a) + 255 * a).astype(np.uint8)


def _lighting(img: np.ndarray, kind: str, rng: np.random.Generator) -> None:
    if kind == "exposure":
        gain = rng.uniform(0.55, 0.75) if rng.random() < 0.5 else rng.uniform(1.3, 1.6)
        img[:] = np.clip(img * gain, 0, 255).astype(np.uint8)
    elif kind == "colortemp":
        d = rng.uniform(0.15, 0.25) * (1 if rng.random() < 0.5 else -1)
        img[:] = np.clip(img * np.float32([1 - d, 1, 1 + d]), 0, 255).astype(np.uint8)  # BGR: warm lowers B, raises R
    elif kind == "shadow":
        synth.add_shadow(img, rng)
    else:
        _specular(img, rng)


def make_pair(kind: str, idx: int, scenes: list) -> dict:
    """Returns before, after, GT defects [{kind, mask, contrast}] in before-frame coordinates, and metadata."""
    rng = _rng(kind, idx)
    name, scene = scenes[idx % len(scenes)]
    before = synth.crop(scene)
    defects = []
    if kind == "damage":
        damaged = scene.copy()
        gray0 = cv2.cvtColor(scene, cv2.COLOR_BGR2GRAY).astype(np.float32)
        for k in rng.choice(synth.DEFECTS, int(rng.integers(1, 4))):
            m = np.zeros(scene.shape[:2], np.uint8)
            synth.add_defect(damaged, m, k, rng)
            diff = np.abs(cv2.cvtColor(damaged, cv2.COLOR_BGR2GRAY).astype(np.float32) - gray0)
            defects.append({"kind": str(k), "mask": synth.crop(m), "contrast": float(diff[m > 0].mean())})
        shadowed = bool(rng.random() < 0.5)
        if shadowed:
            synth.add_shadow(damaged, rng)
        after = synth.camera(damaged, rng, 0.02)
        meta = {"shadowed": shadowed}
    elif kind == "nochange":
        after, meta = synth.camera(scene.copy(), rng, 0.02), {}
    else:
        lit = scene.copy()
        _lighting(lit, kind, rng)
        after, meta = synth.camera(lit, rng, 0.02), {}
    return {"set": kind, "idx": idx, "scene": name, "before": before, "after": after, "defects": defects, **meta}


# ---------------------------------------------------------------- evaluation

def _box_iou(a: tuple, b: tuple) -> float:
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / (a[2] * a[3] + b[2] * b[3] - inter)


def evaluate(pair: dict, z: float = 9.0) -> tuple[dict, vision.Comparison]:
    bkf, akf = Keyframe.build(pair["before"], SIDE), Keyframe.build(pair["after"], SIDE)
    res = compare(bkf, akf, z_thresh=z)
    rec = {"set": pair["set"], "idx": pair["idx"], "scene": pair["scene"], "ok": res.ok, "reason": res.reason,
           "inliers": res.inliers, "defects": [], "flagged": [], "lighting_regions": 0,
           "shadowed": pair.get("shadowed")}
    if not res.ok:
        rec["defects"] = [{"kind": d["kind"], "area": int((d["mask"] > 0).sum()), "contrast": round(d["contrast"], 1),
                           "hit": False, "iou": 0.0} for d in pair["defects"]]
        return rec, res
    flagged = [r for r in res.regions if not r.lighting_only]
    rec["lighting_regions"] = len(res.regions) - len(flagged)
    rec["flagged"] = [{"box": [r.x, r.y, r.w, r.h], "score": r.score, "structure": r.structure, "chroma": r.chroma,
                       "illumination": r.illumination, "brightening": r.brightening} for r in flagged]
    hit = [False] * len(flagged)
    for d in pair["defects"]:
        m = d["mask"]
        ys, xs = np.nonzero(m)
        gt = (int(xs.min()), int(ys.min()), int(np.ptp(xs)) + 1, int(np.ptp(ys)) + 1)
        found, best = False, 0.0
        for i, r in enumerate(flagged):
            if m[r.y:r.y + r.h, r.x:r.x + r.w].any():  # synth.py rule: any GT pixel inside the detection box
                found = hit[i] = True
                best = max(best, _box_iou(gt, (r.x, r.y, r.w, r.h)))
        rec["defects"].append({"kind": d["kind"], "area": int((m > 0).sum()), "contrast": round(d["contrast"], 1),
                               "hit": found, "iou": round(best, 3), "gt_box": list(gt)})
    rec["unmatched"] = hit.count(False)
    return rec, res


def run_set(kinds_counts: dict, scenes: list, z: float = 9.0, keep: list | None = None) -> list[dict]:
    out = []
    for kind, n in kinds_counts.items():
        for i in range(n):
            rec, _ = evaluate(make_pair(kind, i, scenes), z)
            out.append(rec)
    return out


MAIN_SETS = {"damage": N_DAMAGE, "nochange": N_NOCHANGE, **{k: N_LIGHT for k in LIGHTING}}


def summarize(recs: list[dict]) -> dict:
    dmg = [r for r in recs if r["set"] == "damage"]
    tp = sum(d["hit"] for r in dmg for d in r["defects"])
    n_def = sum(len(r["defects"]) for r in dmg)
    fp = sum(r.get("unmatched", 0) for r in dmg)
    shadow_fp = sum(r.get("unmatched", 0) for r in dmg if r["shadowed"])
    ctrl = [r for r in recs if r["set"] == "nochange"]
    light = [r for r in recs if r["set"] in LIGHTING]
    ok = lambda rs: [r for r in rs if r["ok"]]
    nflag = lambda rs: sum(len(r["flagged"]) for r in rs)
    return {
        "damage_pairs": len(dmg), "defects": n_def,
        "damage_registration_failures": sum(not r["ok"] for r in dmg),
        "recall": round(tp / max(1, n_def), 3),
        "precision": round(tp / max(1, tp + fp), 3),
        "fp_per_pair": round(fp / max(1, len(dmg)), 2),
        "fp_in_shadow_pairs": shadow_fp, "shadow_pairs": sum(bool(r["shadowed"]) for r in dmg),
        "nochange_pairs": len(ctrl),
        "nochange_false_alarm_rate": round(sum(bool(r["flagged"]) for r in ctrl) / max(1, len(ctrl)), 3),
        "nochange_flags_per_pair": round(nflag(ctrl) / max(1, len(ctrl)), 2),
        "nochange_registration_failures": sum(not r["ok"] for r in ctrl),
        "lighting_pairs": len(light),
        "lighting_false_alarm_rate": round(sum(bool(r["flagged"]) for r in light) / max(1, len(light)), 3),
        "lighting_flags_per_pair": round(nflag(light) / max(1, len(light)), 2),
        "lighting_registration_failures": sum(not r["ok"] for r in light),
        "lighting_by_kind": {k: {"pairs": sum(r["set"] == k for r in light),
                                 "false_alarm_rate": round(sum(bool(r["flagged"]) for r in light if r["set"] == k)
                                                           / max(1, sum(r["set"] == k for r in light)), 3),
                                 "flags": nflag([r for r in light if r["set"] == k])} for k in LIGHTING},
    }


def breakdowns(recs: list[dict]) -> dict:
    defects = [d for r in recs if r["set"] == "damage" for d in r["defects"]]
    def stat(ds):
        return {"n": len(ds), "recall": round(sum(d["hit"] for d in ds) / max(1, len(ds)), 3),
                "recall_iou": round(sum(d["hit"] and d["iou"] >= IOU_STRICT for d in ds) / max(1, len(ds)), 3)}
    hits = [d for d in defects if d["hit"]]
    return {
        "by_kind": {k: stat([d for d in defects if d["kind"] == k]) for k in synth.DEFECTS},
        "by_size": {name: stat([d for d in defects if lo <= d["area"] < hi]) for name, lo, hi in SIZE_BUCKETS},
        "by_kind_size": {k: {name: stat([d for d in defects if d["kind"] == k and lo <= d["area"] < hi])
                             for name, lo, hi in SIZE_BUCKETS} for k in synth.DEFECTS},
        "median_iou_of_hits": round(statistics.median(d["iou"] for d in hits), 3) if hits else None,
        "median_contrast_hit": round(statistics.median(d["contrast"] for d in hits), 1) if hits else None,
        "median_contrast_miss": round(statistics.median(d["contrast"] for d in defects if not d["hit"]), 1)
        if any(not d["hit"] for d in defects) else None,
    }


# ---------------------------------------------------------------- registration stress

STRESS_LEVELS = 6
# per-axis magnitudes for levels 0..5; "combined" applies all three at the smaller magnitudes below
_ROT, _ZOOM, _TILT = (5, 15, 30, 60, 90, 150), (1.1, 1.3, 1.7, 2.2, 3.0, 4.5), (10, 20, 30, 40, 50, 60)
_C_ROT, _C_ZOOM, _C_TILT = (3, 8, 15, 25, 40, 60), (1.05, 1.15, 1.3, 1.5, 1.8, 2.2), (3, 8, 15, 25, 35, 45)
AXES = ("rotation", "scale", "tilt", "combined")


def _stress_transform(axis: str, level: int, rng: np.random.Generator, w: int, h: int) -> np.ndarray:
    """Rotation (degrees in the image plane), scale (zoom in or out) and tilt (camera pitch or yaw, focal = image width)."""
    comb = axis == "combined"
    rot, zoom, tilt = (_C_ROT, _C_ZOOM, _C_TILT) if comb else (_ROT, _ZOOM, _TILT)
    angle = rng.choice([-1, 1]) * rot[level] * rng.uniform(0.8, 1.0) if axis in ("rotation", "combined") else 0.0
    scale = float(zoom[level] ** rng.choice([-1, 1])) if axis in ("scale", "combined") else 1.0
    M = np.eye(3)
    M[:2] = cv2.getRotationMatrix2D((w / 2, h / 2), float(angle), scale)
    if axis in ("tilt", "combined"):
        theta = np.radians(tilt[level] * rng.uniform(0.8, 1.0) * rng.choice([-1, 1]))
        rvec = np.array([theta, 0, 0]) if rng.random() < 0.5 else np.array([0, theta, 0])
        R, _ = cv2.Rodrigues(rvec)
        K = np.array([[w, 0, w / 2], [0, w, h / 2], [0, 0, 1]], float)
        M = K @ R @ np.linalg.inv(K) @ M
    return M


def stress_pair(axis: str, level: int, idx: int, scenes: list) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng([SEED, SET_ID["stress"], AXES.index(axis),
                                 level, idx])
    _, scene = scenes[idx % len(scenes)]
    h, w = scene.shape[:2]
    M = _stress_transform(axis, level, rng, w, h)
    after = synth.crop(cv2.warpPerspective(scene, M, (w, h)))
    after = np.clip(after + rng.normal(0, 3, after.shape), 0, 255).astype(np.uint8)
    after = cv2.imdecode(cv2.imencode(".jpg", after, [cv2.IMWRITE_JPEG_QUALITY, 85])[1], cv2.IMREAD_COLOR)
    my, mx = int(h * synth.MARGIN), int(w * synth.MARGIN)
    T = np.array([[1, 0, -mx], [0, 1, -my], [0, 0, 1]], float)
    return synth.crop(scene), after, T @ np.linalg.inv(M) @ np.linalg.inv(T)  # H maps after pixels to before pixels


def registration_error(H_est: np.ndarray, H_gt: np.ndarray, shape: tuple) -> float:
    h, w = shape
    gx, gy = np.meshgrid(np.linspace(0.1, 0.9, 7) * w, np.linspace(0.1, 0.9, 7) * h)
    pts = np.float32(np.stack([gx.ravel(), gy.ravel()], 1)).reshape(-1, 1, 2)
    truth = cv2.perspectiveTransform(pts, H_gt.astype(np.float32)).reshape(-1, 2)
    inside = (truth[:, 0] > 0) & (truth[:, 0] < w) & (truth[:, 1] > 0) & (truth[:, 1] < h)
    if inside.sum() < 5:
        return float("nan")
    est = cv2.perspectiveTransform(pts, H_est.astype(np.float32)).reshape(-1, 2)
    return float(np.median(np.linalg.norm(est - truth, axis=1)[inside]))


def registration_stress(scenes: list, n: int, axis: str) -> list[dict]:
    out = []
    for level in range(STRESS_LEVELS):
        reg = acc = usable = 0
        errs = []
        for i in range(n):
            before, after, H_gt = stress_pair(axis, level, i, scenes)
            bkf, akf = Keyframe.build(before, SIDE), Keyframe.build(after, SIDE)
            s = bkf.image.shape[1] / before.shape[1]
            S = np.diag([s, s, 1.0])
            H, _ = vision.match(akf, bkf)
            if H is not None:
                reg += 1
                e = registration_error(H, S @ H_gt @ np.linalg.inv(S), bkf.gray.shape)
                errs.append(e)
                acc += e <= REG_TOL_PX
                usable += compare(bkf, akf).ok
        out.append({"level": level, "pairs": n, "registered": reg, "accurate": acc, "usable": usable,
                    "registered_rate": round(reg / n, 3), "accurate_rate": round(acc / n, 3),
                    "median_error_px": round(float(np.nanmedian(errs)), 2) if errs else None})
    return out


# ---------------------------------------------------------------- ablations

class _ZeroFlow:
    def calc(self, a, b, init):
        return np.zeros((*a.shape[:2], 2), np.float32)


class _Cv2Proxy:
    """Stands in for `cv2` inside twice.vision only; the engine file is untouched."""

    def __init__(self, drop_flow=False, drop_clip=False):
        self.drop_flow, self.drop_clip, self.calls = drop_flow, drop_clip, 0

    def __getattr__(self, name):
        if name == "DISOpticalFlow_create" and self.drop_flow:
            self.calls += 1
            return lambda preset: _ZeroFlow()
        if name == "dilate" and self.drop_clip:
            return self._dilate
        return getattr(cv2, name)

    def _dilate(self, src, kernel, *a, **k):
        if src.dtype == np.uint8 and kernel.shape == (7, 7):  # the only 7x7 uint8 dilate is the clipped-pixel mask
            self.calls += 1
            return np.zeros_like(src)
        return cv2.dilate(src, kernel, *a, **k)


class _NoClahe:
    @staticmethod
    def apply(g):
        return g


ABLATIONS = {
    "full": {},
    "plain_abs_diff": {"_tolerant_diff": lambda a, b, r=1: np.abs(a - b)},
    "no_local_norm": {"_lnorm": lambda x, sigma=12: x},
    "no_flow_refine": {"cv2": _Cv2Proxy(drop_flow=True)},
    "no_clahe": {"_clahe": _NoClahe()},
    "no_clipped_mask": {"cv2": _Cv2Proxy(drop_clip=True)},
    "no_lighting_test": {"_illumination_likeness": lambda *a, **k: 0.0},
}


@contextlib.contextmanager
def patched(changes: dict):
    old = {k: getattr(vision, k) for k in changes}
    for k, v in changes.items():
        setattr(vision, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(vision, k, v)


# ---------------------------------------------------------------- latency

def cpu_name() -> str:
    try:
        import subprocess
        out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"],
                             capture_output=True, text=True, timeout=20).stdout.strip()
        return out or platform.processor()
    except Exception:
        return platform.processor()


def _pct(xs: list, q: float) -> float:
    return float(np.percentile(xs, q))


def latency(scenes: list, n: int = 30) -> dict:
    pairs = [make_pair("damage", i, scenes) for i in range(n)]
    big = [(cv2.resize(p["before"], (4032, int(4032 * p["before"].shape[0] / p["before"].shape[1])),
                       interpolation=cv2.INTER_CUBIC),
            cv2.resize(p["after"], (4032, int(4032 * p["after"].shape[0] / p["after"].shape[1])),
                       interpolation=cv2.INTER_CUBIC)) for p in pairs[:12]]
    inputs = {"bench_924px": [(p["before"], p["after"]) for p in pairs], "phone_4032px": big}

    def timed(a, b):
        t0 = time.perf_counter()
        ka = Keyframe.build(a)
        t1 = time.perf_counter()
        kb = Keyframe.build(b)
        t2 = time.perf_counter()
        compare(ka, kb)
        t3 = time.perf_counter()
        return (t1 - t0) * 1e3, (t2 - t1) * 1e3, (t3 - t2) * 1e3

    out = {}
    for threads in (cv2.getNumThreads(), 1):
        cv2.setNumThreads(threads)
        for label, ims in inputs.items():
            for a, b in ims[:3]:
                timed(a, b)  # warm-up
            rows = [timed(a, b) for a, b in ims]
            tot = [sum(r) / 1e3 for r in rows]
            out[f"{label}_threads{threads}"] = {
                "pairs": len(rows), "build_ms_median": round(statistics.median(r[0] for r in rows), 1),
                "compare_ms_median": round(statistics.median(r[2] for r in rows), 1),
                "total_s_median": round(statistics.median(tot), 3), "total_s_p95": round(_pct(tot, 95), 3)}
    cv2.setNumThreads(0)
    return out


# ---------------------------------------------------------------- failure gallery

def _draw(panel: np.ndarray, boxes: list, color: tuple, scale: float, thick: int) -> None:
    for x, y, w, h in boxes:
        cv2.rectangle(panel, (int(x * scale) - 1, int(y * scale) - 1), (int((x + w) * scale) + 1, int((y + h) * scale) + 1),
                      color, thick, cv2.LINE_AA)


def render_failure(pair: dict, label: str, path: Path) -> None:
    bkf, akf = Keyframe.build(pair["before"], SIDE), Keyframe.build(pair["after"], SIDE)
    res = compare(bkf, akf)
    left = bkf.image
    right = res.after_aligned if res.ok else cv2.resize(akf.image, (left.shape[1], left.shape[0]))
    sc = 560 / left.shape[0]
    panels = [cv2.resize(p, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA) for p in (left, right)]
    gt = []
    for d in pair["defects"]:
        ys, xs = np.nonzero(d["mask"])
        gt.append((int(xs.min()), int(ys.min()), int(np.ptp(xs)) + 1, int(np.ptp(ys)) + 1))
    det = [(r.x, r.y, r.w, r.h) for r in res.regions if not r.lighting_only] if res.ok else []
    lit = [(r.x, r.y, r.w, r.h) for r in res.regions if r.lighting_only] if res.ok else []
    for p in panels:
        _draw(p, lit, (255, 160, 0), sc, 1)
        _draw(p, gt, (0, 200, 0), sc, 2)
        _draw(p, det, (0, 0, 255), sc, 2)
    bar = np.full((34, panels[0].shape[1] * 2, 3), 255, np.uint8)
    cv2.putText(bar, label, (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    legend = np.full((24, bar.shape[1], 3), 255, np.uint8)
    cv2.putText(legend, "before | after (aligned)   green = ground truth   red = flagged   blue = lighting only",
                (8, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (60, 60, 60), 1, cv2.LINE_AA)
    cv2.imwrite(str(path), np.vstack([bar, np.hstack(panels), legend]), [cv2.IMWRITE_JPEG_QUALITY, 88])


def pick_failures(recs: list[dict]) -> list[dict]:
    """Up to 4 misses and 4 false alarms, taking one of each failure type before repeating a type."""
    misses, fps = [], []
    for r in recs:
        if not r["ok"]:
            misses.append({"type": "registration failure", "rec": r})
        for d in r["defects"]:
            if r["ok"] and not d["hit"]:
                misses.append({"type": f"missed {d['kind']}", "rec": r, "defect": d})
        if r.get("unmatched"):
            fps.append({"type": "false alarm" if r["set"] == "damage" else f"false alarm ({r['set']})", "rec": r})

    def diverse(pool: list, k: int) -> list:
        first = {f["type"]: f for f in reversed(pool)}.values()
        return (list(first) + [f for f in pool if f not in first])[:k]

    return diverse(misses, 4) + diverse(fps, 4)


# ---------------------------------------------------------------- main

WORKERS, WORKER_THREADS = 12, 2


def _job(args: tuple):
    """One independent unit of work; runs in a worker process so ablations never share patched state."""
    kind, imgdir, name, quick = args
    cv2.setNumThreads(WORKER_THREADS)
    scenes = load_scenes(Path(imgdir))
    sets = {k: (2 if quick else v) for k, v in MAIN_SETS.items()}
    if kind == "synth":
        return synth.run([Path(imgdir) / n for n, _ in scenes], 4 if quick else 40)
    if kind == "stress":
        return registration_stress(scenes, 2 if quick else N_STRESS, name)
    t0 = time.time()
    if name.startswith("threshold_z"):
        recs = run_set(sets, scenes, z=float(name[len("threshold_z"):]))
    else:
        changes = ABLATIONS[name]
        with patched(changes):
            recs = run_set(sets, scenes)
        calls = {k: v.calls for k, v in changes.items() if hasattr(v, "calls")}
    summary = summarize(recs)
    summary["seconds"] = round(time.time() - t0, 1)
    if not name.startswith("threshold_z") and calls:
        summary["patched_calls"] = calls
    return summary, recs


def main() -> None:
    from concurrent.futures import ProcessPoolExecutor

    ap = argparse.ArgumentParser()
    ap.add_argument("imgdir")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "docs" / "eval"))
    ap.add_argument("--quick", action="store_true", help="tiny run for smoke testing")
    args = ap.parse_args()
    out = Path(args.out)
    (out / "failures").mkdir(parents=True, exist_ok=True)
    scenes = load_scenes(Path(args.imgdir))
    t_start = time.time()
    sets = {k: (2 if args.quick else v) for k, v in MAIN_SETS.items()}
    result = {"seed": SEED, "scenes": [n for n, _ in scenes], "cv2": cv2.__version__, "cpu": cpu_name(),
              "logical_cores": cv2.getNumThreads(), "python": platform.python_version(), "set_sizes": sets,
              "iou_strict": IOU_STRICT, "registration_tolerance_px": REG_TOL_PX}

    print("latency (machine otherwise idle) ...", flush=True)
    result["latency"] = latency(scenes, 6 if args.quick else 30)
    print(json.dumps(result["latency"], indent=1), flush=True)

    print("parallel jobs: reference, ablations, registration stress ...", flush=True)
    configs = list(ABLATIONS) + ["threshold_z6", "threshold_z12"]
    axes = AXES
    jobs = [("synth", args.imgdir, "", args.quick)] + [("config", args.imgdir, c, args.quick) for c in configs]         + [("stress", args.imgdir, a, args.quick) for a in axes]
    with ProcessPoolExecutor(WORKERS) as pool:
        done = list(pool.map(_job, jobs))
    result["synth_reference"] = done[0]
    abl, recs = {}, None
    for name, (summary, r) in zip(configs, done[1:1 + len(configs)]):
        abl[name] = summary
        if name == "full":
            recs = r
        print(f"  {name}: recall {summary['recall']} precision {summary['precision']} fp/pair {summary['fp_per_pair']} "
              f"nochange {summary['nochange_false_alarm_rate']} lighting {summary['lighting_false_alarm_rate']}", flush=True)
    result["ablations"] = abl
    result["registration"] = dict(zip(axes, done[1 + len(configs):]))
    result["pairs"] = recs
    result["summary"] = summarize(recs)
    result["breakdown"] = breakdowns(recs)
    print(json.dumps(result["summary"], indent=1), flush=True)

    print("failure gallery ...", flush=True)
    gallery = []
    for n, f in enumerate(pick_failures(recs), 1):
        r = f["rec"]
        pair = make_pair(r["set"], r["idx"], scenes)
        name = f"{n:02d}_{r['set']}{r['idx']}_{f['type'].split(' (')[0].replace(' ', '-')}.jpg"
        render_failure(pair, f"{f['type']} | {r['set']} #{r['idx']} | {r['scene']}", out / "failures" / name)
        gallery.append({"file": f"failures/{name}", "type": f["type"], "set": r["set"], "idx": r["idx"],
                        "scene": r["scene"], "defect": f.get("defect"), "flagged": r["flagged"]})
    result["gallery"] = gallery

    result["runtime_s"] = round(time.time() - t_start, 1)
    (out / "results.json").write_text(json.dumps(result, indent=1))
    print(f"done in {result['runtime_s']} s; wrote {out / 'results.json'}")


if __name__ == "__main__":
    main()

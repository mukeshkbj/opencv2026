"""Synthetic before/after benchmark: known damage, random camera and lighting changes."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from twice.vision import Keyframe, compare  # noqa: E402

DEFECTS = ("scratch", "stain", "chip", "crack")


def add_defect(img: np.ndarray, mask: np.ndarray, kind: str, rng: np.random.Generator) -> None:
    h, w = img.shape[:2]
    cx, cy = int(rng.uniform(0.15, 0.85) * w), int(rng.uniform(0.15, 0.85) * h)
    s = min(h, w)
    layer = np.zeros((h, w), np.uint8)
    if kind == "scratch":
        ang = rng.uniform(0, np.pi)
        L = rng.uniform(0.04, 0.12) * s
        p0 = (int(cx - L * np.cos(ang)), int(cy - L * np.sin(ang)))
        p1 = (int(cx + L * np.cos(ang)), int(cy + L * np.sin(ang)))
        cv2.line(layer, p0, p1, 255, int(rng.integers(1, 3)), cv2.LINE_AA)
        tone = rng.choice([25.0, 230.0])
        alpha = rng.uniform(0.55, 0.9)
    elif kind == "stain":
        ax = (int(rng.uniform(0.02, 0.05) * s), int(rng.uniform(0.015, 0.04) * s))
        cv2.ellipse(layer, (cx, cy), ax, rng.uniform(0, 180), 0, 360, 255, -1, cv2.LINE_AA)
        layer = cv2.GaussianBlur(layer, (0, 0), 3)
        tone = np.array(rng.uniform(40, 140, 3))
        alpha = rng.uniform(0.35, 0.6)
    elif kind == "chip":
        pts = (np.array([cx, cy]) + rng.normal(0, 0.012 * s, (7, 2))).astype(np.int32)
        cv2.fillPoly(layer, [cv2.convexHull(pts)], 255, cv2.LINE_AA)
        tone = rng.choice([30.0, 215.0])
        alpha = 0.85
    else:
        pts = [np.array([cx, cy], float)]
        ang = rng.uniform(0, 2 * np.pi)
        for _ in range(int(rng.integers(6, 12))):
            ang += rng.normal(0, 0.6)
            pts.append(pts[-1] + 0.012 * s * np.array([np.cos(ang), np.sin(ang)]))
        cv2.polylines(layer, [np.int32(pts)], False, 255, 1, cv2.LINE_AA)
        tone = 20.0
        alpha = 0.9
    a = (layer.astype(np.float32) / 255 * alpha)[..., None]
    img[:] = (img * (1 - a) + np.broadcast_to(tone, img.shape) * a).astype(np.uint8)
    mask[layer > 40] = 255


def add_shadow(img: np.ndarray, rng: np.random.Generator) -> None:
    h, w = img.shape[:2]
    pts = (rng.uniform(0, 1, (4, 2)) * [w, h]).astype(np.int32)
    m = np.zeros((h, w), np.float32)
    cv2.fillPoly(m, [cv2.convexHull(pts)], 1.0)
    m = cv2.GaussianBlur(m, (0, 0), min(h, w) * 0.04)
    img[:] = np.clip(img * (1 - rng.uniform(0.25, 0.45) * m[..., None]), 0, 255).astype(np.uint8)


MARGIN = 0.08


def crop(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    my, mx = int(h * MARGIN), int(w * MARGIN)
    return img[my:h - my, mx:w - mx]


def camera(img: np.ndarray, rng: np.random.Generator, strength: float) -> np.ndarray:
    """Re-photograph the scene: perspective jitter inside the scene margin, then light, noise and JPEG."""
    h, w = img.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    jitter = np.clip(rng.normal(0, strength * min(h, w), (4, 2)), -MARGIN * h * 0.9, MARGIN * h * 0.9)
    out = crop(cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, src + jitter.astype(np.float32)), (w, h)))
    gain = rng.uniform(0.75, 1.2, 3) if rng.random() < 0.7 else np.ones(3)
    out = np.clip(out * gain + rng.uniform(-15, 15), 0, 255)
    out = np.clip(out + rng.normal(0, 3, out.shape), 0, 255).astype(np.uint8)
    q = int(rng.integers(70, 92))
    return cv2.imdecode(cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, q])[1], cv2.IMREAD_COLOR)


def run(images: list[Path], trials: int, seed: int = 7, strength: float = 0.02) -> dict:
    rng = np.random.default_rng(seed)
    tp = fn = fp = shadow_fp = 0
    per_kind = {k: [0, 0] for k in DEFECTS}
    failures = 0
    for t in range(trials):
        scene = cv2.imread(str(images[t % len(images)]))
        scene = cv2.resize(scene, (1100, int(1100 * scene.shape[0] / scene.shape[1])))
        before = crop(scene)
        damaged = scene.copy()
        masks = []
        for kind in rng.choice(DEFECTS, int(rng.integers(1, 4))):
            m = np.zeros(scene.shape[:2], np.uint8)
            add_defect(damaged, m, kind, rng)
            masks.append((kind, crop(m)))
        if rng.random() < 0.5:
            add_shadow(damaged, rng)
            shadowed = True
        else:
            shadowed = False
        after = camera(damaged, rng, strength)
        res = compare(Keyframe.build(before, 960), Keyframe.build(after, 960))
        if not res.ok:
            failures += 1
            fn += len(masks)
            continue
        flagged = [r for r in res.regions if not r.lighting_only]
        hit = [False] * len(flagged)
        for kind, m in masks:
            found = False
            for i, r in enumerate(flagged):
                if m[r.y:r.y + r.h, r.x:r.x + r.w].any():
                    found = hit[i] = True
            per_kind[kind][0 if found else 1] += 1
            tp += found
            fn += not found
        extra = hit.count(False)
        fp += extra
        shadow_fp += extra if shadowed else 0
    return {
        "trials": trials,
        "registration_failures": failures,
        "recall": round(tp / max(1, tp + fn), 3),
        "precision": round(tp / max(1, tp + fp), 3),
        "false_positives_per_pair": round(fp / trials, 2),
        "false_positives_in_shadow_pairs": shadow_fp,
        "recall_by_kind": {k: round(v[0] / max(1, sum(v)), 3) for k, v in per_kind.items()},
    }


if __name__ == "__main__":
    folder = Path(sys.argv[1])
    imgs = sorted(p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".png"})
    print(json.dumps(run(imgs, int(sys.argv[2]) if len(sys.argv) > 2 else 40), indent=2))

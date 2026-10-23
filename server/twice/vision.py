from dataclasses import dataclass, field

import cv2
import numpy as np

WORK_SIDE = 1024
GUIDE_SIDE = 480
MIN_INLIERS = 25

_clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))


def resize_max(img: np.ndarray, side: int) -> tuple[np.ndarray, float]:
    h, w = img.shape[:2]
    s = side / max(h, w)
    if s >= 1:
        return img, 1.0
    return cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA), s


def decode(data: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("not an image")
    return img


@dataclass
class Quality:
    sharpness: float
    brightness: float
    clipped: float
    features: int
    ok: bool
    issue: str | None

    def as_dict(self) -> dict:
        return self.__dict__


def assess(gray: np.ndarray, features: int) -> Quality:
    g, _ = resize_max(gray, GUIDE_SIDE)
    sharp = float(cv2.Laplacian(g, cv2.CV_32F).var())
    mean = float(g.mean())
    clipped = float(((g < 8) | (g > 247)).mean())
    issue = None
    if mean < 45:
        issue = "too_dark"
    elif mean > 225 or clipped > 0.35:
        issue = "too_bright"
    elif sharp < 60:
        issue = "blurry"
    elif features < 80:
        issue = "featureless"
    return Quality(round(sharp, 1), round(mean, 1), round(clipped, 3), features, issue is None, issue)


def quick_quality(img: np.ndarray) -> Quality:
    small, _ = resize_max(img, GUIDE_SIDE)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    return assess(gray, len(_sift(800).detect(gray, None)))


@dataclass
class Keyframe:
    image: np.ndarray
    gray: np.ndarray
    kp: tuple
    desc: np.ndarray | None

    @classmethod
    def build(cls, image: np.ndarray, side: int = WORK_SIDE, n: int = 3000) -> "Keyframe":
        img, _ = resize_max(image, side)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        kp, desc = _sift(n).detectAndCompute(_clahe.apply(gray), None)
        return cls(img, gray, kp, desc)


_sift_cache: dict[int, cv2.SIFT] = {}


def _sift(n: int) -> cv2.SIFT:
    if n not in _sift_cache:
        _sift_cache[n] = cv2.SIFT_create(nfeatures=n)
    return _sift_cache[n]


_matcher = cv2.FlannBasedMatcher({"algorithm": 1, "trees": 4}, {"checks": 48})


def match(src: Keyframe, dst: Keyframe) -> tuple[np.ndarray | None, int]:
    """Homography mapping src pixels into dst pixels, plus the inlier count."""
    if src.desc is None or dst.desc is None or len(src.kp) < 8 or len(dst.kp) < 8:
        return None, 0
    pairs = _matcher.knnMatch(src.desc, dst.desc, k=2)
    good = [p[0] for p in pairs if len(p) == 2 and p[0].distance < 0.75 * p[1].distance]
    if len(good) < MIN_INLIERS:
        return None, len(good)
    a = np.float32([src.kp[m.queryIdx].pt for m in good])
    b = np.float32([dst.kp[m.trainIdx].pt for m in good])
    H, mask = cv2.findHomography(a, b, cv2.USAC_MAGSAC, 3.0, maxIters=5000, confidence=0.999)
    inliers = int(mask.sum()) if mask is not None else 0
    if H is None or inliers < MIN_INLIERS or not _plausible(H, src.gray.shape):
        return None, inliers
    return H, inliers


def _plausible(H: np.ndarray, shape: tuple) -> bool:
    h, w = shape[:2]
    quad = cv2.perspectiveTransform(np.float32([[[0, 0]], [[w, 0]], [[w, h]], [[0, h]]]), H).reshape(4, 2)
    if not cv2.isContourConvex(quad.astype(np.float32)):
        return False
    ratio = cv2.contourArea(quad) / (w * h)
    return 0.15 < ratio < 6


def _same_view(H: np.ndarray, after_shape: tuple, before_shape: tuple) -> bool:
    """A comparison is fair only from roughly the same spot. At the centre and at each corner of the photo, the
    local scale must stay within 0.8 to 1.25 and the stretch below 1.3, with no mirror image. Scale is measured
    relative to the image sizes, so two resolutions of one view pass. The live guide locks far tighter; this
    bound also covers photos uploaded without it."""
    h, w = after_shape[:2]
    norm = np.sqrt(before_shape[0] * before_shape[1] / (h * w))
    for x, y in ((w / 2, h / 2), (0, 0), (w, 0), (0, h), (w, h)):
        d = H[2] @ (x, y, 1)
        J = (H[:2, :2] - np.outer(H[:2] @ (x, y, 1) / d, H[2, :2])) / d
        sv = np.linalg.svd(J, compute_uv=False)
        if np.linalg.det(J) <= 0 or not 0.8 < np.sqrt(sv[0] * sv[1]) / norm < 1.25 or sv[0] / sv[1] >= 1.3:
            return False
    return True


@dataclass
class Guidance:
    aligned: bool
    score: float
    instruction: str
    quad: list | None
    dx: float = 0
    dy: float = 0
    scale: float = 1
    roll: float = 0
    quality: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return self.__dict__


def guide_reference(image: np.ndarray) -> Keyframe:
    return Keyframe.build(image, GUIDE_SIDE, 1200)


def guide(frame: np.ndarray, small: Keyframe) -> Guidance:
    """Tell a person how to move the camera so that `frame` reproduces the reference view."""
    live = Keyframe.build(frame, GUIDE_SIDE, 1200)
    q = assess(live.gray, len(live.kp))
    H, inliers = match(small, live)
    if H is None:
        msg = {"too_dark": "More light, please", "too_bright": "Too much glare", "blurry": "Hold steady"}.get(
            q.issue or "", "Find the spot from your first visit")
        return Guidance(False, 0, msg, None, quality=q.as_dict())
    h, w = small.gray.shape
    lh, lw = live.gray.shape
    quad = cv2.perspectiveTransform(np.float32([[[0, 0]], [[w, 0]], [[w, h]], [[0, h]]]), H).reshape(4, 2)
    quad_n = (quad / [lw, lh]).round(4).tolist()
    center = quad.mean(axis=0)
    dx = float((center[0] - lw / 2) / lw)
    dy = float((center[1] - lh / 2) / lh)
    scale = float(np.sqrt(cv2.contourArea(quad) / (lw * lh)) / np.sqrt((w * h) / (lw * lh)))
    top = quad[1] - quad[0]
    roll = float(np.degrees(np.arctan2(top[1], top[0])))
    err = max(abs(dx) * 4, abs(dy) * 4, abs(np.log(scale)) * 3, abs(roll) / 8)
    score = float(np.clip(1 - err, 0, 1))
    aligned = score > 0.72 and q.ok
    if not q.ok:
        instruction = {"too_dark": "More light, please", "too_bright": "Too much glare", "blurry": "Hold steady",
                       "featureless": "Include an edge or corner"}[q.issue]
    elif aligned:
        instruction = "Hold still"
    else:
        moves = [
            (abs(dx) * 4, "Pan right" if dx > 0 else "Pan left"),
            (abs(dy) * 4, "Tilt down" if dy > 0 else "Tilt up"),
            (abs(np.log(scale)) * 3, "Step back" if scale > 1 else "Move closer"),
            (abs(roll) / 8, "Rotate clockwise" if roll < 0 else "Rotate counter-clockwise"),
        ]
        instruction = max(moves)[1]
    return Guidance(aligned, round(score, 3), instruction, quad_n, round(dx, 3), round(dy, 3),
                    round(scale, 3), round(roll, 1), q.as_dict())


@dataclass
class Region:
    x: int
    y: int
    w: int
    h: int
    score: float
    area: int
    structure: float
    chroma: float
    illumination: float
    brightening: float = 0
    veil: float = 0

    @property
    def lighting_only(self) -> bool:
        return self.illumination > 0.8 and self.chroma < 2.5

    def as_dict(self) -> dict:
        return {**self.__dict__, "lighting_only": self.lighting_only}


@dataclass
class Comparison:
    ok: bool
    reason: str | None
    inliers: int = 0
    overlap: float = 0
    regions: list[Region] = field(default_factory=list)
    before: np.ndarray | None = None
    after_aligned: np.ndarray | None = None
    heat: np.ndarray | None = None


def _lnorm(x: np.ndarray, sigma: float = 12) -> np.ndarray:
    mu = cv2.GaussianBlur(x, (0, 0), sigma)
    sd = np.sqrt(cv2.GaussianBlur((x - mu) ** 2, (0, 0), sigma)) + 6
    return (x - mu) / sd


def compare(before: Keyframe, after: Keyframe, z_thresh: float = 9.0, min_area: int = 40) -> Comparison:
    """Register `after` onto `before` and return the regions that physically changed."""
    H, inliers = match(after, before)
    if H is None:
        return Comparison(False, "no_registration", inliers)
    if not _same_view(H, after.gray.shape, before.gray.shape):
        return Comparison(False, "different_view", inliers)
    h, w = before.gray.shape
    warped = cv2.warpPerspective(after.image, H, (w, h), flags=cv2.INTER_LINEAR)
    valid = cv2.warpPerspective(np.full(after.gray.shape, 255, np.uint8), H, (w, h), flags=cv2.INTER_NEAREST)
    covered = (valid > 0).astype(np.float32)
    seen = lambda img: cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) * covered, (0, 0), 25)
    gain = np.clip((seen(warped) + 1) / (seen(before.image) + 1), 0.5, 2)
    outside = valid == 0
    warped[outside] = np.clip(before.image[outside] * gain[outside, None], 0, 255).astype(np.uint8)
    border = max(9, (min(h, w) // 40) | 1)
    valid = cv2.erode(valid, np.ones((border, border), np.uint8))
    overlap = float((valid > 0).mean())
    if overlap < 0.3:
        return Comparison(False, "low_overlap", inliers, overlap)

    lab_b = cv2.cvtColor(before.image, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab_a = cv2.cvtColor(warped, cv2.COLOR_BGR2LAB).astype(np.float32)
    lb, la = lab_b[..., 0], lab_a[..., 0]

    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    flow = dis.calc(_clahe.apply(lb.astype(np.uint8)), _clahe.apply(la.astype(np.uint8)), None)
    flow[np.linalg.norm(flow, axis=2) > 6] = 0
    flow = cv2.GaussianBlur(flow, (0, 0), 9)
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    mx, my = gx + flow[..., 0], gy + flow[..., 1]
    lab_a = cv2.remap(lab_a, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    la = lab_a[..., 0]

    sb, sa = cv2.GaussianBlur(lb, (0, 0), 1.0), cv2.GaussianBlur(la, (0, 0), 1.0)
    structure = cv2.GaussianBlur(_tolerant_diff(_lnorm(sb), _lnorm(sa)), (0, 0), 1.2)
    gain = cv2.GaussianBlur(sa + 4, (0, 0), 30) / cv2.GaussianBlur(sb + 4, (0, 0), 30)
    absolute = _tolerant_diff(sb * gain, sa)
    chroma = np.linalg.norm(lab_a[..., 1:] - lab_b[..., 1:], axis=2)
    chroma = cv2.GaussianBlur(chroma, (0, 0), 2)
    clipped = ((lb > 248) | (la > 248) | ((lb < 6) & (la < 6))).astype(np.uint8)
    valid[cv2.dilate(clipped, np.ones((7, 7), np.uint8)) > 0] = 0
    band = max(8, min(h, w) // 28)
    valid[:band], valid[-band:], valid[:, :band], valid[:, -band:] = 0, 0, 0, 0

    zs, zc = _robust_z(structure, valid), _robust_z(chroma, valid, floor=1.5)
    z = np.maximum(zs, zc * 0.8)
    mask = ((z > z_thresh) & ((absolute > 9) | (chroma > 6))).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    speck = np.isin(labels, np.nonzero(stats[:, cv2.CC_STAT_AREA] < max(12, min_area // 3))[0])
    mask[speck] = 0
    group = max(15, (min(h, w) // 50) | 1)
    grouped = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (group, group)))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(grouped)
    labels[mask == 0] = 0

    regions = []
    for i in range(1, n):
        x, y, bw, bh, _ = (int(v) for v in stats[i])
        sel = labels[y:y + bh, x:x + bw] == i
        area = int(sel.sum())
        if area < min_area:
            continue
        ys, xs = np.nonzero(sel)
        x, y, bw, bh = x + int(xs.min()), y + int(ys.min()), int(np.ptp(xs)) + 1, int(np.ptp(ys)) + 1
        sel = labels[y:y + bh, x:x + bw] == i
        regions.append(Region(
            x, y, bw, bh,
            score=round(float(z[y:y + bh, x:x + bw][sel].max()), 2),
            area=area,
            structure=round(float(zs[y:y + bh, x:x + bw][sel].mean()), 2),
            chroma=round(float(zc[y:y + bh, x:x + bw][sel].mean()), 2),
            illumination=round(_illumination_likeness(lb, la, x, y, bw, bh), 3),
            brightening=round(_brightening(lb, la, x, y, bw, bh), 3),
            veil=round(_veil(lb, la, x, y, bw, bh), 3),
        ))
    regions = _merge_overlapping(regions, gap=group)
    regions.sort(key=lambda r: -r.score * np.sqrt(r.area))
    regions = regions[:12] + _lighting_regions(lb, la, valid, mask)
    heat = np.clip(z / (z_thresh * 2), 0, 1)
    return Comparison(True, None, inliers, overlap, regions, before.image, cv2.remap(
        warped, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE), heat)


def _merge_overlapping(regions: list["Region"], gap: int) -> list["Region"]:
    """Union regions whose boxes touch within `gap` pixels; one physical mark should be one finding."""
    merged = True
    while merged:
        merged = False
        for i, a in enumerate(regions):
            for j in range(i + 1, len(regions)):
                b = regions[j]
                if a.x - gap < b.x + b.w and b.x - gap < a.x + a.w and a.y - gap < b.y + b.h and b.y - gap < a.y + a.h:
                    x0, y0 = min(a.x, b.x), min(a.y, b.y)
                    x1, y1 = max(a.x + a.w, b.x + b.w), max(a.y + a.h, b.y + b.h)
                    wa, wb = a.area, b.area
                    mix = lambda p, q: round((p * wa + q * wb) / (wa + wb), 3)
                    regions[i] = Region(x0, y0, x1 - x0, y1 - y0, score=max(a.score, b.score), area=wa + wb,
                                        structure=mix(a.structure, b.structure), chroma=mix(a.chroma, b.chroma),
                                        illumination=min(a.illumination, b.illumination),
                                        brightening=mix(a.brightening, b.brightening), veil=mix(a.veil, b.veil))
                    del regions[j]
                    merged = True
                    break
            if merged:
                break
    return regions


def _lighting_regions(lb: np.ndarray, la: np.ndarray, valid: np.ndarray, changed: np.ndarray) -> list["Region"]:
    """Large areas where only brightness moved (shadows, lamps, sun): reported so they can be shown as ignored."""
    h, w = lb.shape
    ratio = cv2.GaussianBlur(np.log(la + 8) - np.log(lb + 8), (0, 0), 8)
    ratio -= np.median(ratio[valid > 0])
    mask = ((np.abs(ratio) > np.log(1.15)) & (valid > 0) & (changed == 0)).astype(np.uint8) * 255
    k = max(9, (min(h, w) // 40) | 1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    out = []
    for i in range(1, n):
        x, y, bw, bh, area = (int(v) for v in stats[i])
        if area < 0.01 * h * w:
            continue
        mean = float(ratio[labels == i].mean())
        out.append(Region(x, y, bw, bh, score=round(abs(mean) * 100, 1), area=area, structure=0, chroma=0,
                          illumination=1.0, brightening=round(float(np.exp(mean) - 1), 3)))
    return sorted(out, key=lambda r: -r.area)[:3]


def _robust_z(m: np.ndarray, valid: np.ndarray, floor: float = 1e-3) -> np.ndarray:
    """Standardise a difference map by its noise level. The scale falls back to the upper tail because
    tolerant differences are zero for most pixels, which collapses the median absolute deviation.
    `floor` keeps a near-constant map (the chroma of a grey wall) from turning JPEG noise into huge scores."""
    v = m[valid > 0]
    med = float(np.median(v))
    scale = max(1.4826 * float(np.median(np.abs(v - med))), (float(np.percentile(v, 95)) - med) / 2, floor)
    z = (m - med) / scale
    z[valid == 0] = 0
    return z


def _tolerant_diff(a: np.ndarray, b: np.ndarray, r: int = 1) -> np.ndarray:
    """Per-pixel difference that ignores sub-pixel misalignment: each value is compared with the other
    image's min/max envelope over a (2r+1)^2 window, in both directions."""
    k = np.ones((2 * r + 1, 2 * r + 1), np.uint8)
    d_ab = np.maximum(0, np.maximum(a - cv2.dilate(b, k), cv2.erode(b, k) - a))
    d_ba = np.maximum(0, np.maximum(b - cv2.dilate(a, k), cv2.erode(a, k) - b))
    return np.maximum(d_ab, d_ba)


def _brightening(lb: np.ndarray, la: np.ndarray, x: int, y: int, w: int, h: int) -> float:
    """Share of pixels that newly reach near-white after exposure compensation:
    specular glare appearing (positive) or vanishing (negative)."""
    pad = max(10, max(w, h))
    H, W = lb.shape
    ring = (slice(max(0, y - pad), min(H, y + h + pad)), slice(max(0, x - pad), min(W, x + w + pad)))
    g = float(np.median(la[ring]) + 4) / float(np.median(lb[ring]) + 4)
    a, b = la[y:y + h, x:x + w] / g, lb[y:y + h, x:x + w]
    return float((a > 250).mean() - (b > 250).mean())


def _veil(lb: np.ndarray, la: np.ndarray, x: int, y: int, w: int, h: int) -> float:
    """How well the change fits a smooth blend toward white, the way glare veils a surface.
    0 when the region did not lighten; near 1 for a pure veil."""
    pad = max(10, max(w, h))
    H, W = lb.shape
    ring = (slice(max(0, y - pad), min(H, y + h + pad)), slice(max(0, x - pad), min(W, x + w + pad)))
    g = float(np.median(la[ring]) + 4) / float(np.median(lb[ring]) + 4)
    lift = la[ring] / g - lb[ring]
    a = lift / (263 - lb[ring])
    inner = np.s_[y - ring[0].start:y - ring[0].start + h, x - ring[1].start:x - ring[1].start + w]
    if float(np.median(a[inner])) < 0.1 or float(np.median(lift[inner])) < 8:
        return 0.0
    smooth = cv2.GaussianBlur(a, (0, 0), max(3.0, min(w, h) / 3))
    return max(0.0, 1 - float(((a - smooth) ** 2).sum()) / float((a ** 2).sum()))


def _illumination_likeness(lb: np.ndarray, la: np.ndarray, x: int, y: int, w: int, h: int) -> float:
    """Share of the change explained by a smooth multiplicative light field (1 = pure shadow or glare).
    0 when the box holds a sharp new edge (over 20 % local contrast), which no light field makes:
    a scratch inside a fresh shadow must not be explained away by the shadow around it."""
    pad = max(8, max(w, h) // 2)
    H, W = lb.shape
    x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(W, x + w + pad), min(H, y + h + pad)
    r = np.log(la[y0:y1, x0:x1] + 8) - np.log(lb[y0:y1, x0:x1] + 8)
    r -= np.median(r)
    total = float((r ** 2).sum())
    if total < 1e-6:
        return 1.0
    residual = r - cv2.GaussianBlur(r, (0, 0), max(3.0, min(w, h) / 3))
    if np.percentile(np.abs(residual[y - y0:y - y0 + h, x - x0:x - x0 + w]), 98) > 0.2:
        return 0.0
    return 1 - float((residual ** 2).sum()) / total

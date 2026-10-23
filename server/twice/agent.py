"""Perception-decision-action loop that turns raw change regions into findings with evidence."""
import time
from dataclasses import asdict, dataclass, field

import cv2
import numpy as np

from . import objects
from .vision import Comparison, Keyframe, Region, compare

FOLLOWUP_BUDGET = 2


@dataclass
class Finding:
    id: str
    box: list[int]
    metrics: dict
    verdict: str = "pending"
    kind: str = "surface"
    evidence: list[str] = field(default_factory=list)
    caption: str = ""


@dataclass
class Request:
    id: str
    finding: str
    kind: str
    prompt: str
    box: list[int]


@dataclass
class SpotState:
    findings: list[Finding] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)
    pending: Request | None = None
    followups_used: int = 0
    status: str = "new"
    registration: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SpotState":
        s = cls(**{k: v for k, v in d.items() if k not in ("findings", "pending")})
        s.findings = [Finding(**f) for f in d.get("findings", [])]
        s.pending = Request(**d["pending"]) if d.get("pending") else None
        return s


class Agent:
    """Rule planner. Every decision is logged with the measurement that caused it."""

    def __init__(self, state: SpotState):
        self.s = state

    def log(self, tool: str, result: str, decision: str = "") -> None:
        self.s.trace.append({"t": round(time.time(), 3), "tool": tool, "result": result, "decision": decision})

    def on_after(self, before: Keyframe, after: Keyframe) -> Comparison:
        t0 = time.perf_counter()
        res = compare(before, after)
        ms = round((time.perf_counter() - t0) * 1000)
        if not res.ok:
            self.s.status = "retake"
            self.log("register", f"failed: {res.reason}, {res.inliers} inliers ({ms} ms)",
                     "ask for a retake from the same spot")
            return res
        self.s.registration = {"inliers": res.inliers, "overlap": round(res.overlap, 3), "ms": ms}
        self.log("register", f"{res.inliers} inlier matches, {res.overlap:.0%} overlap ({ms} ms)")
        self.log("change_map", f"{len(res.regions)} candidate regions")
        self.s.findings = [self._finding(i, r) for i, r in enumerate(res.regions)]
        for f in self.s.findings:
            self._triage(f, res)
        self._object_check(res)
        self._plan()
        return res

    def _object_check(self, res: Comparison) -> None:
        t0 = time.perf_counter()
        before, after = objects.detect(res.before), objects.detect(res.after_aligned)
        ms = round((time.perf_counter() - t0) * 1000)
        self.log("object_check", f"NanoDet on the OpenCV 5 DNN engine, objects found: {len(before)} at move-in, {len(after)} at move-out ({ms} ms)")
        for f in self.s.findings:
            if f.verdict in ("lighting", "unchanged"):
                continue
            here = lambda ds, name=None: [d for d in ds if _covers(d.box, f.box) and name in (None, d.name)]
            if here(after, "person") and not here(before, "person"):
                f.verdict = "uncertain"
                f.evidence.append("a person is in the move-out photo here: retake without people")
                self.log("object_check", f"{f.id}: person in frame", "mark cannot judge")
                continue
            if f.verdict != "changed":
                continue
            gone = [d for d in here(before) if not here(after, d.name)]
            new = [d for d in here(after) if not here(before, d.name)]
            if gone or new:
                d = (gone or new)[0]
                f.kind = "object"
                f.caption = f"{d.name.capitalize()} missing" if gone else f"New {d.name}"
                f.evidence.append(f"detector saw a {d.name} ({d.conf:.2f}) only in the move-{'in' if gone else 'out'} photo")
                self.log("object_check", f"{f.id}: {d.name} {'gone' if gone else 'added'}", "label the finding")

    def _finding(self, i: int, r: Region) -> Finding:
        return Finding(f"f{i + 1}", [r.x, r.y, r.w, r.h], r.as_dict())

    def _triage(self, f: Finding, res: Comparison) -> None:
        m = f.metrics
        if m["lighting_only"]:
            f.verdict, f.kind = "lighting", "lighting"
            if m["structure"] == 0:
                f.evidence.append(f"{abs(m['brightening']):.0%} {'brighter' if m['brightening'] > 0 else 'darker'}, texture unchanged: a shadow or a light")
            else:
                f.evidence.append(f"smooth light field explains {m['illumination']:.0%} of the change, chroma shift z={m['chroma']:.1f}")
            self.log("relight_check", f"{f.id}: lighting only", "rule out")
            return
        area_frac = _area_frac(f, res.before.shape)
        if abs(m["brightening"]) > 0.05 or m["veil"] > 0.3:
            f.kind = "glare?"
            if abs(m["brightening"]) > 0.05:
                f.evidence.append(f"{abs(m['brightening']):.0%} of the region {'turned' if m['brightening'] > 0 else 'stopped being'} near white: possible reflection")
                self.log("glare_check", f"{f.id}: specular change {m['brightening']:+.0%}", "needs a parallax shot")
            else:
                f.evidence.append(f"the surface lightened like a veil of glare (fit {m['veil']:.0%}): possible reflection")
                self.log("glare_check", f"{f.id}: glare-like veil, fit {m['veil']:.0%}", "needs a parallax shot")
            return
        if m["illumination"] > 0.8 and m["chroma"] < 4:
            f.evidence.append(f"soft edges like a shadow, but colour shifted (z={m['chroma']:.1f})")
            self.log("relight_check", f"{f.id}: soft change with colour shift", "needs a close-up")
            return
        f.kind = _kind(f, area_frac)
        f.verdict = "changed"
        f.evidence.append(f"structure z={m['structure']:.1f}, colour z={m['chroma']:.1f}, peak z={m['score']:.1f}")
        if area_frac < 0.0015 and m["score"] < 18:
            f.verdict = "pending"
            f.evidence.append("small and weak: a close-up will confirm it")
            self.log("size_check", f"{f.id}: {area_frac:.2%} of view, peak z={m['score']:.1f}", "needs a close-up")
            return
        self.log("classify", f"{f.id}: {f.kind} change", "report")

    def _plan(self) -> None:
        self.s.pending = None
        for f in self.s.findings:
            if f.verdict != "pending":
                continue
            if self.s.followups_used >= FOLLOWUP_BUDGET:
                f.verdict = "uncertain"
                f.evidence.append("follow-up budget used: left for a human to judge")
                self.log("budget", f"{f.id}: no follow-ups left", "mark cannot judge")
                continue
            parallax = f.kind == "glare?"
            self.s.pending = Request(
                id=f"r{self.s.followups_used + 1}",
                finding=f.id,
                kind="parallax" if parallax else "closeup",
                prompt="Take one step to the side and shoot this spot again. Reflections move, damage stays."
                if parallax else "Move in close to the marked area and take a sharp photo.",
                box=f.box,
            )
            self.s.status = "needs_followup"
            self.log("plan", f"{f.id} unresolved", f"request {self.s.pending.kind} photo")
            return
        self.s.status = "done"
        self.log("finalize", ", ".join(f"{k} {v}" for k, v in _counts(self.s.findings).items()) or "no changes")

    def on_followup(self, before: Keyframe, image: np.ndarray) -> None:
        req = self.s.pending
        if req is None:
            raise ValueError("no follow-up pending")
        f = next(x for x in self.s.findings if x.id == req.finding)
        self.s.followups_used += 1
        if req.kind == "parallax":
            res = compare(before, Keyframe.build(image))
            if not res.ok:
                f.verdict = "uncertain"
                f.evidence.append(f"parallax shot failed to register ({res.reason})")
                self.log("compare_followup", f"{f.id}: parallax shot did not register", "mark cannot judge")
            elif _persists(f.box, res.regions):
                f.verdict, f.kind = "changed", _kind(f, _area_frac(f, before.image.shape))
                f.evidence.append("change stayed fixed to the surface when the camera moved")
                self.log("compare_followup", f"{f.id}: persists under parallax", f"report as {f.kind} change")
            else:
                f.verdict, f.kind = "lighting", "glare"
                f.evidence.append("change vanished when the camera moved: a reflection")
                self.log("compare_followup", f"{f.id}: vanished under parallax", "rule out as glare")
        else:
            crop, offset = _crop_around(before.image, f.box)
            up = min(2.0, 800 / max(crop.shape[:2]))
            if up > 1:
                crop = cv2.resize(crop, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
            res = compare(Keyframe.build(crop), Keyframe.build(image))
            if not res.ok:
                f.verdict = "uncertain"
                f.evidence.append(f"close-up did not match the area ({res.reason})")
                self.log("compare_followup", f"{f.id}: close-up did not register", "mark cannot judge")
            else:
                scale = res.before.shape[1] / crop.shape[1] * max(up, 1)
                local = [round(v * scale) for v in (f.box[0] - offset[0], f.box[1] - offset[1], f.box[2], f.box[3])]
                if _persists(local, res.regions):
                    f.verdict = "changed"
                    f.evidence.append("close-up confirms the change at higher detail")
                    self.log("compare_followup", f"{f.id}: confirmed in close-up", "report")
                else:
                    f.verdict, f.kind = "unchanged", "noise"
                    f.evidence.append("close-up shows no change: first detection was noise")
                    self.log("compare_followup", f"{f.id}: not present in close-up", "rule out")
        self._plan()


def _counts(findings: list[Finding]) -> dict:
    out: dict[str, int] = {}
    for f in findings:
        out[f.verdict] = out.get(f.verdict, 0) + 1
    return out


def _covers(det: tuple, box: list) -> bool:
    return max(objects.overlap(det, box), objects.overlap(box, det)) > 0.5


def _area_frac(f: Finding, shape: tuple) -> float:
    return f.box[2] * f.box[3] / (shape[0] * shape[1])


def _kind(f: Finding, area_frac: float) -> str:
    fill = f.metrics["area"] / (f.box[2] * f.box[3])
    return "object" if area_frac > 0.008 and fill > 0.3 and f.metrics["structure"] > 6 else "surface"


def _persists(box: list[int], regions: list[Region]) -> bool:
    """True when a non-lighting region of the new comparison sits where the finding was."""
    x, y, w, h = box
    cx, cy, reach = x + w / 2, y + h / 2, 0.35 * max(w, h) + 8
    return any(not r.lighting_only and np.hypot(r.x + r.w / 2 - cx, r.y + r.h / 2 - cy) < reach for r in regions)


def _crop_around(img: np.ndarray, box: list[int], context: float = 2.5) -> tuple[np.ndarray, tuple[int, int]]:
    x, y, w, h = box
    side = int(max(w, h, 60) * context)
    cx, cy = x + w // 2, y + h // 2
    H, W = img.shape[:2]
    x0, y0 = max(0, cx - side // 2), max(0, cy - side // 2)
    x1, y1 = min(W, x0 + side), min(H, y0 + side)
    return img[y0:y1, x0:x1], (x0, y0)

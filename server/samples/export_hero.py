"""Export aligned sample pairs and their findings for the landing page."""
import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from twice.agent import Agent, SpotState  # noqa: E402
from twice.vision import Keyframe  # noqa: E402

SRC = Path(__file__).resolve().parent / "apartment"
OUT = Path(__file__).resolve().parents[2] / "web" / "public" / "hero"

meta = {}
for name in ("room", "desk", "car"):
    before = Keyframe.build(cv2.imread(str(SRC / f"{name}-before.jpg")))
    state = SpotState()
    agent = Agent(state)
    res = agent.on_after(before, Keyframe.build(cv2.imread(str(SRC / f"{name}-after.jpg"))))
    if state.pending and (SRC / f"{name}-parallax.jpg").exists() and state.pending.kind == "parallax":
        agent.on_followup(before, cv2.imread(str(SRC / f"{name}-parallax.jpg")))
    h, w = res.before.shape[:2]
    cv2.imwrite(str(OUT / f"{name}-a.jpg"), res.before, [cv2.IMWRITE_JPEG_QUALITY, 84])
    cv2.imwrite(str(OUT / f"{name}-b.jpg"), res.after_aligned, [cv2.IMWRITE_JPEG_QUALITY, 84])
    meta[name] = {"w": w, "h": h, "findings": [
        {"box": [round(v / d, 4) for v, d in zip(f.box, (w, h, w, h))], "verdict": f.verdict, "kind": f.kind}
        for f in state.findings]}
(OUT / "hero.json").write_text(json.dumps(meta, indent=1))
print(json.dumps(meta, indent=1))

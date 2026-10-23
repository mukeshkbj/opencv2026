"""False alarms on real photos: the Oxford affine sequences (Mikolajczyk et al.), where nothing in the scene changes.

Run from server/:  python eval/real_bench.py [--out ../docs/eval]
Each sequence is one scene photographed six times with growing difficulty: light (leuven), blur (bikes, trees),
JPEG (ubc), viewpoint (graf, wall), zoom and rotation (boat, bark). Image 1 is compared with images 2 to 6.
Any "changed" verdict is a false alarm. The images are downloaded on first run and not committed.
"""
import argparse
import io
import json
import tarfile
import urllib.request
from pathlib import Path

import cv2

import bench  # noqa: F401  (puts server/ on sys.path)
from twice.agent import Agent, SpotState
from twice.vision import Keyframe

URL = "https://www.robots.ox.ac.uk/~vgg/research/affine/det_eval_files/{}.tar.gz"
SEQUENCES = {"leuven": "light", "bikes": "blur", "trees": "blur", "ubc": "JPEG", "graf": "viewpoint",
             "wall": "viewpoint", "boat": "zoom and rotation", "bark": "zoom and rotation"}
CACHE = Path(__file__).resolve().parent / "oxford"


def images(seq: str) -> list:
    folder = CACHE / seq
    if not folder.exists():
        folder.mkdir(parents=True)
        with urllib.request.urlopen(URL.format(seq), timeout=60) as r:
            tarfile.open(fileobj=io.BytesIO(r.read())).extractall(folder, filter="data")
    return [cv2.imread(str(p)) for p in sorted(folder.glob("img*.p?m"))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "docs" / "eval"))
    args = ap.parse_args()
    rows = []
    for seq, stress in SEQUENCES.items():
        imgs = images(seq)
        ref = Keyframe.build(imgs[0])
        for k, img in enumerate(imgs[1:], 2):
            state = SpotState()
            res = Agent(state).on_after(ref, Keyframe.build(img))
            verdicts = [f.verdict for f in state.findings]
            rows.append({"sequence": seq, "stress": stress, "pair": f"1-{k}", "registered": res.ok,
                         "changed": verdicts.count("changed"), "followup_asked": state.status == "needs_followup",
                         "ruled_out": verdicts.count("lighting")})
            print(rows[-1], flush=True)
    reg = [r for r in rows if r["registered"]]
    summary = {
        "pairs": len(rows),
        "registered": len(reg),
        "pairs_with_false_changed": sum(r["changed"] > 0 for r in reg),
        "false_changed_per_pair": round(sum(r["changed"] for r in reg) / max(1, len(reg)), 2),
        "pairs_with_followup_request": sum(r["followup_asked"] for r in reg),
        "by_sequence": {s: {"registered": sum(r["registered"] for r in rows if r["sequence"] == s),
                            "with_false_changed": sum(r["changed"] > 0 for r in reg if r["sequence"] == s)}
                        for s in SEQUENCES},
    }
    print(json.dumps(summary, indent=1))
    Path(args.out, "real.json").write_text(json.dumps({"summary": summary, "pairs": rows}, indent=1))


if __name__ == "__main__":
    main()

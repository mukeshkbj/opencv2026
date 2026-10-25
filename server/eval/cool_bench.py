"""Twice's core workload, timed under whichever cv2 is on the path. Used to compare COOL with pip OpenCV.

Run from server/:  python -m eval.cool_bench --label cool-arm --out cool-arm.json
The workload is the full agent check (keyframes, registration, change map, triage, NanoDet, follow-up photos)
on a fixed subset of the agent benchmark pairs, plus the OpenCV calls the check spends its time in.
"""
import argparse
import hashlib
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_bench  # noqa: E402
import bench  # noqa: E402
from twice import objects  # noqa: E402
from twice.agent import Agent, SpotState  # noqa: E402
from twice.vision import Keyframe  # noqa: E402

PER_SET = 6
PROFILED = ("GaussianBlur", "cvtColor", "resize", "warpPerspective", "remap", "findHomography", "dilate", "erode",
            "morphologyEx", "connectedComponentsWithStats", "Laplacian", "imdecode", "imencode")


def environment() -> dict:
    build = cv2.getBuildInformation()
    cpu = platform.processor()
    if Path("/proc/cpuinfo").exists():
        info = Path("/proc/cpuinfo").read_text()
        for key in ("model name", "CPU part"):
            line = next((x for x in info.splitlines() if x.startswith(key)), "")
            if line:
                cpu = f"{key}: {line.split(':', 1)[1].strip()}"
                break
    return {
        "cv2_version": cv2.__version__,
        "cv2_file": cv2.__file__,
        "is_cool": "/opt/cool" in cv2.__file__,
        "build_markers": [x.strip() for x in build.splitlines()
                          if any(k in x.lower() for k in ("kleidicv", "armpl", "neon", "sve", "cpu/hw", "dispatched", "version control"))][:20],
        "machine": platform.machine(),
        "cpu": cpu,
        "cores": os.cpu_count(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "has_dnn": hasattr(cv2, "dnn"),
    }


def jobs() -> list[tuple[str, int]]:
    return [(k, i) for k, n in bench.MAIN_SETS.items() for i in range(min(n, PER_SET))]


def run_check(kind: str, idx: int, scenes: list) -> tuple[float, dict]:
    cv2.setRNGSeed(0)
    pair = bench.make_pair(kind, idx, scenes)
    rng = np.random.default_rng([bench.SEED, 99, bench.SET_ID[kind], idx])
    t0 = time.perf_counter()
    before = Keyframe.build(pair["before"], bench.SIDE)
    state = SpotState()
    agent = Agent(state)
    agent.on_after(before, Keyframe.build(pair["after"], bench.SIDE))
    while state.status == "needs_followup":
        req = state.pending
        img = agent_bench.parallax_shot(pair, rng) if req.kind == "parallax" else agent_bench.closeup_shot(pair, req.box, rng)
        agent.on_followup(before, img)
    ms = (time.perf_counter() - t0) * 1000
    changed = [f for f in state.findings if f.verdict == "changed"]
    masks = [d["mask"] for d in pair["defects"]]
    touches = lambda f, m: m[f.box[1]:f.box[1] + f.box[3], f.box[0]:f.box[0] + f.box[2]].any()
    outcome = {"set": kind, "idx": idx, "status": state.status,
               "followups": [t["decision"] for t in state.trace if t["tool"] == "plan"],
               "verdicts": sorted(f.verdict for f in state.findings),
               "defects": len(masks), "found": sum(any(touches(f, m) for f in changed) for m in masks),
               "false_changed": sum(not any(touches(f, m) for m in masks) for f in changed)}
    return ms, outcome


def workload(threads: int, scenes: list) -> dict:
    cv2.setNumThreads(threads)
    todo = jobs()
    for kind, idx in todo[:2]:
        run_check(kind, idx, scenes)
    times, outcomes = [], []
    t0 = time.perf_counter()
    for kind, idx in todo:
        ms, out = run_check(kind, idx, scenes)
        times.append(ms)
        outcomes.append(out)
    wall = time.perf_counter() - t0
    times.sort()
    found = sum(o["found"] for o in outcomes)
    fp = sum(o["false_changed"] for o in outcomes)
    return {
        "threads": cv2.getNumThreads(),
        "checks": len(times),
        "median_ms": round(statistics.median(times), 1),
        "p95_ms": round(times[int(len(times) * 0.95) - 1], 1),
        "checks_per_s": round(len(times) / wall, 3),
        "recall": round(found / max(1, sum(o["defects"] for o in outcomes)), 3),
        "precision": round(found / max(1, found + fp), 3),
        "followups": sum(len(o["followups"]) for o in outcomes),
        "outcome_hash": hashlib.sha256(json.dumps([(o["set"], o["idx"], o["status"], o["followups"], o["verdicts"])
                                                   for o in outcomes]).encode()).hexdigest()[:16],
        "outcomes": outcomes,
    }


def profile(scenes: list) -> dict:
    spent: dict[str, float] = {}
    originals = {}
    for name in PROFILED:
        fn = getattr(cv2, name)
        originals[name] = fn

        def timed(*a, _fn=fn, _name=name, **k):
            t0 = time.perf_counter()
            try:
                return _fn(*a, **k)
            finally:
                spent[_name] = spent.get(_name, 0.0) + time.perf_counter() - t0
        setattr(cv2, name, timed)
    real_detect = objects.detect

    def timed_detect(img, *a, **k):
        t0 = time.perf_counter()
        try:
            return real_detect(img, *a, **k)
        finally:
            spent["dnn NanoDet (detect)"] = spent.get("dnn NanoDet (detect)", 0.0) + time.perf_counter() - t0
    objects.detect = timed_detect
    real_build = Keyframe.build.__func__

    def timed_build(cls, *a, **k):
        t0 = time.perf_counter()
        try:
            return real_build(cls, *a, **k)
        finally:
            spent["Keyframe.build (resize, CLAHE, SIFT)"] = spent.get("Keyframe.build (resize, CLAHE, SIFT)", 0.0) + time.perf_counter() - t0
    Keyframe.build = classmethod(timed_build)
    total = 0.0
    try:
        for kind, idx in jobs():
            ms, _ = run_check(kind, idx, scenes)
            total += ms / 1000
    finally:
        for name, fn in originals.items():
            setattr(cv2, name, fn)
        objects.detect = real_detect
        Keyframe.build = classmethod(real_build)
    return {"total_s": round(total, 2),
            "share": {k: round(v / total, 3) for k, v in sorted(spent.items(), key=lambda kv: -kv[1])}}


def ops(scenes: list, runs: int = 30) -> dict:
    img = cv2.resize(scenes[0][1], (bench.SIDE, round(bench.SIDE * scenes[0][1].shape[0] / scenes[0][1].shape[1])))
    big = cv2.resize(img, (4032, round(4032 * img.shape[0] / img.shape[1])), interpolation=cv2.INTER_CUBIC)
    jpeg = cv2.imencode(".jpg", big, [cv2.IMWRITE_JPEG_QUALITY, 90])[1]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    f32 = gray.astype(np.float32)
    sift = cv2.SIFT_create(nfeatures=3000)
    kp, des = sift.detectAndCompute(gray, None)
    shifted = cv2.warpAffine(gray, np.float32([[1, 0, 6], [0, 1, 4]]), gray.shape[::-1])
    kp2, des2 = sift.detectAndCompute(shifted, None)
    matcher = cv2.FlannBasedMatcher({"algorithm": 1, "trees": 4}, {"checks": 48})
    matches = [m for m, n in matcher.knnMatch(des, des2, k=2) if m.distance < 0.75 * n.distance]
    a = np.float32([kp[m.queryIdx].pt for m in matches])
    b = np.float32([kp2[m.trainIdx].pt for m in matches])
    H, _ = cv2.findHomography(a, b, cv2.USAC_MAGSAC, 3.0)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    mask = (gray > 128).astype(np.uint8) * 255
    kernel = np.ones((7, 7), np.uint8)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    cases = {
        "imdecode 4032 px JPEG": lambda: cv2.imdecode(jpeg, cv2.IMREAD_COLOR),
        "resize 4032 to 960 INTER_AREA": lambda: cv2.resize(big, (bench.SIDE, img.shape[0]), interpolation=cv2.INTER_AREA),
        "cvtColor BGR2LAB": lambda: cv2.cvtColor(img, cv2.COLOR_BGR2LAB),
        "GaussianBlur u8 sigma 1": lambda: cv2.GaussianBlur(gray, (0, 0), 1.0),
        "GaussianBlur f32 sigma 1.2": lambda: cv2.GaussianBlur(f32, (0, 0), 1.2),
        "GaussianBlur f32 sigma 30": lambda: cv2.GaussianBlur(f32, (0, 0), 30),
        "Laplacian": lambda: cv2.Laplacian(gray, cv2.CV_32F),
        "CLAHE": lambda: clahe.apply(gray),
        "SIFT detectAndCompute 3000": lambda: sift.detectAndCompute(gray, None),
        "FLANN knnMatch": lambda: matcher.knnMatch(des, des2, k=2),
        "findHomography USAC_MAGSAC": lambda: cv2.findHomography(a, b, cv2.USAC_MAGSAC, 3.0, maxIters=5000, confidence=0.999),
        "warpPerspective": lambda: cv2.warpPerspective(img, H, gray.shape[::-1]),
        "DISOpticalFlow MEDIUM": lambda: dis.calc(gray, shifted, None),
        "dilate 7x7": lambda: cv2.dilate(mask, kernel),
        "connectedComponentsWithStats": lambda: cv2.connectedComponentsWithStats(mask),
    }
    if hasattr(cv2, "dnn"):
        net = cv2.dnn.readNetFromONNX(str(objects.MODEL), engine=cv2.dnn.ENGINE_NEW)
        blob = cv2.dnn.blobFromImage(img, 1, (objects.SIDE, objects.SIDE))

        def nanodet():
            net.setInput(blob)
            net.forward(net.getUnconnectedOutLayersNames())
        cases["dnn NanoDet ENGINE_NEW"] = nanodet
    out = {}
    for name, fn in cases.items():
        for _ in range(3):
            fn()
        t = []
        for _ in range(runs):
            t0 = time.perf_counter()
            fn()
            t.append((time.perf_counter() - t0) * 1000)
        out[name] = round(statistics.median(t), 3)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--instance", default="", help="EC2 instance type, recorded with the result")
    args = ap.parse_args()
    scenes = bench.load_scenes(agent_bench.SCENES)
    result = {"label": args.label, "instance": args.instance, "env": environment()}
    cores = os.cpu_count() or 1
    print(json.dumps(result["env"], indent=1), flush=True)
    result["workload"] = [workload(1, scenes), workload(cores, scenes)]
    cv2.setNumThreads(cores)
    result["profile"] = profile(scenes)
    result["ops_ms"] = ops(scenes)
    Path(args.out).write_text(json.dumps(result, indent=1))
    for w in result["workload"]:
        print(f"{args.label}: {w['threads']} threads, {w['checks']} checks, median {w['median_ms']} ms, "
              f"p95 {w['p95_ms']} ms, {w['checks_per_s']} checks/s, outcomes {w['outcome_hash']}", flush=True)


if __name__ == "__main__":
    main()

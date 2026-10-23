"""Times NanoDet on the OpenCV 5 DNN engines: python -m eval.engines"""
import statistics
import time

import cv2

from twice import objects

RUNS = 100


def time_engine(engine: int) -> list[float]:
    net = cv2.dnn.readNetFromONNX(str(objects.MODEL), engine=engine)
    blob = cv2.dnn.blobFromImage(cv2.imread("../web/public/hero/desk-a.jpg"), 1, (objects.SIDE, objects.SIDE))
    for _ in range(10):
        net.setInput(blob)
        net.forward(net.getUnconnectedOutLayersNames())
    times = []
    for _ in range(RUNS):
        t0 = time.perf_counter()
        net.setInput(blob)
        net.forward(net.getUnconnectedOutLayersNames())
        times.append((time.perf_counter() - t0) * 1000)
    return times


if __name__ == "__main__":
    print(f"OpenCV {cv2.__version__}, {cv2.getNumThreads()} threads, {RUNS} runs after 10 warm-up runs")
    for name in ("ENGINE_CLASSIC", "ENGINE_NEW"):
        t = sorted(time_engine(getattr(cv2.dnn, name)))
        print(f"{name:15} median {statistics.median(t):6.1f} ms   p90 {t[int(RUNS * 0.9)]:6.1f} ms")

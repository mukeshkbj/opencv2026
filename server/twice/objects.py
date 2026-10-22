"""NanoDet-Plus object detector on the OpenCV 5 DNN engine."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

MODEL = Path(__file__).resolve().parent.parent / "models" / "nanodet.onnx"
SIDE = 416
STRIDES = (8, 16, 32)
REG_MAX = 7
MEAN = np.array([103.53, 116.28, 123.675], np.float32)
STD = np.array([57.375, 57.12, 58.395], np.float32)

COCO = tuple(c.replace("_", " ") for c in (
    "person bicycle car motorcycle airplane bus train truck boat traffic_light fire_hydrant stop_sign "
    "parking_meter bench bird cat dog horse sheep cow elephant bear zebra giraffe backpack umbrella handbag "
    "tie suitcase frisbee skis snowboard ball kite baseball_bat baseball_glove skateboard surfboard "
    "tennis_racket bottle wine_glass cup fork knife spoon bowl banana apple sandwich orange broccoli carrot "
    "hot_dog pizza donut cake chair couch potted_plant bed dining_table toilet tv laptop mouse remote "
    "keyboard phone microwave oven toaster sink refrigerator book clock vase scissors teddy_bear "
    "hair_drier toothbrush"
).split())


@dataclass
class Detection:
    name: str
    conf: float
    box: tuple[int, int, int, int]


def _anchors() -> list[np.ndarray]:
    out = []
    for s in STRIDES:
        n = SIDE // s
        ys, xs = np.mgrid[0:n, 0:n]
        out.append(np.column_stack([xs.ravel(), ys.ravel()]).astype(np.float32) * s + 0.5 * (s - 1))
    return out


@lru_cache(maxsize=1)
def _net() -> tuple[cv2.dnn.Net, list[np.ndarray]]:
    return cv2.dnn.readNetFromONNX(str(MODEL), engine=cv2.dnn.ENGINE_NEW), _anchors()


def detect(image: np.ndarray, threshold: float = 0.45) -> list[Detection]:
    net, anchors = _net()
    h, w = image.shape[:2]
    scale = SIDE / max(h, w)
    canvas = np.zeros((SIDE, SIDE, 3), np.float32)
    canvas[: round(h * scale), : round(w * scale)] = cv2.resize(image, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    net.setInput(cv2.dnn.blobFromImage((canvas - MEAN) / STD))
    outs = net.forward(net.getUnconnectedOutLayersNames())
    # The new and classic engines order outputs differently, so pair them by shape.
    by_size = sorted((o.reshape(-1, o.shape[-1]) for o in outs), key=lambda o: (-o.shape[0], o.shape[1]))
    boxes, scores = [], []
    for (reg, cls), stride, pts in zip(zip(by_size[::2], by_size[1::2]), STRIDES, anchors):
        p = np.exp(reg.reshape(-1, REG_MAX + 1))
        d = (p / p.sum(1, keepdims=True)) @ np.arange(REG_MAX + 1, dtype=np.float32)
        d = d.reshape(-1, 4) * stride
        boxes.append(np.column_stack([pts - d[:, :2], pts + d[:, 2:]]))
        scores.append(cls)
    boxes, scores = np.concatenate(boxes) / scale, np.concatenate(scores)
    ids, conf = scores.argmax(1), scores.max(1)
    xywh = np.column_stack([boxes[:, :2], boxes[:, 2:] - boxes[:, :2]])
    keep = cv2.dnn.NMSBoxes(xywh.tolist(), conf.tolist(), threshold, 0.6)
    return [
        Detection(COCO[ids[i]], round(float(conf[i]), 2), tuple(int(v) for v in xywh[i].round()))
        for i in np.array(keep).ravel()
    ]


def overlap(inner: tuple | list, outer: tuple | list) -> float:
    """Fraction of `inner` covered by `outer`, both as x, y, w, h."""
    ix = max(0, min(inner[0] + inner[2], outer[0] + outer[2]) - max(inner[0], outer[0]))
    iy = max(0, min(inner[1] + inner[3], outer[1] + outer[3]) - max(inner[1], outer[1]))
    return ix * iy / max(1, inner[2] * inner[3])

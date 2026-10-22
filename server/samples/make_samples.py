"""Build the bundled demo: real Wikimedia Commons photos, synthetic damage, simulated re-photography.

Run from the repo root: python server/samples/make_samples.py <folder with room.jpg desk.jpg car.jpg>
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

OUT = Path(__file__).resolve().parent / "apartment"
MARGIN = 0.06
rng = np.random.default_rng(26)


def blend(img, mask, color, alpha):
    a = (mask.astype(np.float32) / 255 * alpha)[..., None]
    img[:] = (img * (1 - a) + np.array(color, np.float32) * a).astype(np.uint8)


def stain(img, center, axes, color=(70, 95, 130), alpha=0.45, angle=20):
    m = np.zeros(img.shape[:2], np.uint8)
    cv2.ellipse(m, center, axes, angle, 0, 360, 255, -1, cv2.LINE_AA)
    jitter = rng.normal(0, 1, img.shape[:2]).astype(np.float32)
    jitter = cv2.GaussianBlur(jitter, (0, 0), 6)
    m = cv2.GaussianBlur(m, (0, 0), max(axes) * 0.25)
    m = np.clip(m.astype(np.float32) * (0.75 + 0.6 * jitter), 0, 255).astype(np.uint8)
    blend(img, m, color, alpha)


def ring(img, center, radius, color=(40, 75, 120), alpha=0.55):
    m = np.zeros(img.shape[:2], np.uint8)
    cv2.circle(m, center, radius, 255, max(3, radius // 9), cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), 2.2)
    blend(img, m, color, alpha)


def scratch(img, pts, color=(60, 60, 60), width=2, alpha=0.85):
    m = np.zeros(img.shape[:2], np.uint8)
    cv2.polylines(m, [np.int32(pts)], False, 255, width, cv2.LINE_AA)
    blend(img, m, color, alpha)


def shadow(img, poly, strength=0.35, soft=60):
    m = np.zeros(img.shape[:2], np.float32)
    cv2.fillPoly(m, [np.int32(poly)], 1.0)
    m = cv2.GaussianBlur(m, (0, 0), soft)
    img[:] = np.clip(img * (1 - strength * m[..., None]), 0, 255).astype(np.uint8)


def glare(img, center, axes):
    m = np.zeros(img.shape[:2], np.float32)
    cv2.ellipse(m, center, axes, -25, 0, 360, 1.0, -1, cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), min(axes) * 0.35)
    img[:] = np.clip(img + 255 * m[..., None], 0, 255).astype(np.uint8)


def remove(img, box, dark=90):
    x0, y0, x1, y1 = box
    roi = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    m = np.zeros(img.shape[:2], np.uint8)
    m[y0:y1, x0:x1] = (roi < dark).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((15, 15), np.uint8))
    img[:] = cv2.inpaint(img, m, 9, cv2.INPAINT_TELEA)


def crop(img):
    h, w = img.shape[:2]
    my, mx = int(h * MARGIN), int(w * MARGIN)
    return img[my:h - my, mx:w - mx]


def shoot(scene, strength=0.012, light=(1.0, 1.0, 1.0), offset=0.0, seed=0):
    r = np.random.default_rng(seed)
    h, w = scene.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    jitter = np.clip(r.normal(0, strength * min(h, w), (4, 2)), -MARGIN * h * 0.8, MARGIN * h * 0.8)
    jitter[:, 0] += offset * w
    out = crop(cv2.warpPerspective(scene, cv2.getPerspectiveTransform(src, src + jitter.astype(np.float32)), (w, h)))
    out = np.clip(out * np.array(light, np.float32), 0, 255)
    out = np.clip(out + r.normal(0, 2.5, out.shape), 0, 255).astype(np.uint8)
    return out


def write(name, img):
    cv2.imwrite(str(OUT / name), img, [cv2.IMWRITE_JPEG_QUALITY, 90])


def main(src: Path):
    OUT.mkdir(parents=True, exist_ok=True)
    spots = []

    room = cv2.imread(str(src / "room.jpg"))
    write("room-before.jpg", crop(room))
    r = room.copy()
    stain(r, (1395, 470), (34, 22))
    scratch(r, [(1010, 712), (1060, 706), (1118, 709)], color=(45, 45, 50), width=3)
    shadow(r, [(450, 0), (900, 0), (760, 1000), (300, 1000)], strength=0.3, soft=80)
    write("room-scene.jpg", r)
    write("room-after.jpg", shoot(r, light=(0.93, 0.97, 1.04), seed=1))
    spots.append({"label": "Living room, east wall", "before": "room-before.jpg", "after": "room-after.jpg",
                  "scene": "room-scene.jpg", "truth": ["wall stain", "floor scuff", "lighting only: shadow"]})

    desk = cv2.imread(str(src / "desk.jpg"))
    write("desk-before.jpg", crop(desk))
    d = desk.copy()
    remove(d, (455, 545, 660, 745))
    ring(d, (1180, 330), 62)
    shadow(d, [(0, 0), (700, 0), (420, 1280), (0, 1280)], strength=0.25, soft=90)
    write("desk-scene.jpg", d)
    write("desk-after.jpg", shoot(d, light=(1.02, 1.0, 0.96), seed=2))
    spots.append({"label": "Desk top", "before": "desk-before.jpg", "after": "desk-after.jpg",
                  "scene": "desk-scene.jpg", "truth": ["coffee ring", "missing item", "lighting only: shadow"]})

    car = cv2.imread(str(src / "car.jpg"))
    write("car-before.jpg", crop(car))
    c = car.copy()
    scratch(c, [(380, 905), (470, 890), (560, 884), (640, 872)], color=(70, 72, 76), width=2)
    g1, g2 = c.copy(), c.copy()
    glare(g1, (1560, 1180), (70, 26))
    glare(g2, (1380, 1260), (70, 26))
    write("car-scene.jpg", g1)
    write("car-after.jpg", shoot(g1, seed=3))
    write("car-parallax.jpg", shoot(g2, offset=0.01, seed=4))
    spots.append({"label": "Rental car, front quarter panel", "before": "car-before.jpg", "after": "car-after.jpg",
                  "scene": "car-scene.jpg", "parallax": "car-parallax.jpg",
                  "truth": ["door scratch", "reflection on chrome (moves with the camera)"]})

    meta = {"name": "Apartment 4B and rental car", "margin": MARGIN, "spots": spots,
            "credits": [
                "Sunny Room in old Apartment, Wikimedia Commons, CC BY 2.0",
                "Top Workspace Office, Wikimedia Commons, CC0",
                "1970 AMC Hornet SST 2-door sedan at 2024 AMO show, Wikimedia Commons, CC BY 4.0",
            ],
            "note": "Real photos. The damage, lighting, and camera moves are synthetic so the ground truth is known."}
    (OUT / "sample.json").write_text(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))

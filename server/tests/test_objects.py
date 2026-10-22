import cv2

from twice import objects

SAMPLES = "samples/apartment"


def test_nanodet_on_new_engine_finds_the_keyboard():
    img = cv2.imread(f"{SAMPLES}/desk-before.jpg")
    names = {d.name for d in objects.detect(img)}
    assert "keyboard" in names


def test_overlap_is_fraction_of_inner_box():
    assert objects.overlap((0, 0, 10, 10), (5, 0, 10, 10)) == 0.5
    assert objects.overlap((0, 0, 10, 10), (20, 20, 5, 5)) == 0

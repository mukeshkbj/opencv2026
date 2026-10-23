import cv2
import numpy as np

from twice.vision import _same_view

SIZE = (768, 1024)
K = np.array([[1024, 0, 512], [0, 1024, 384], [0, 0, 1.0]])


def turned(degrees: float) -> np.ndarray:
    R, _ = cv2.Rodrigues(np.array([0, np.radians(degrees), 0]))
    return K @ R @ np.linalg.inv(K)


def test_same_view_accepts_a_retake_and_refuses_another_viewpoint():
    assert _same_view(np.eye(3), SIZE, SIZE)
    assert _same_view(turned(3), SIZE, SIZE)
    assert _same_view(np.diag([0.5, 0.5, 1]), (1536, 2048), SIZE)
    assert not _same_view(np.diag([1.4, 1.4, 1]), SIZE, SIZE)
    assert not _same_view(turned(35), SIZE, SIZE)
    assert not _same_view(np.diag([-1, 1, 1]), SIZE, SIZE)

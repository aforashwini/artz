"""Generate sample pattern piece images for testing the Fabric Waste Optimizer."""

import numpy as np
import cv2
import os

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")
os.makedirs(SAMPLES_DIR, exist_ok=True)


def draw_on_white(width, height, draw_fn):
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    draw_fn(img)
    return img


def sample_banana_waistband():
    """A curved waistband piece — classic banana shape."""
    def draw(img):
        h, w = img.shape[:2]
        pts = []
        for i in range(100):
            t = i / 99.0
            x = int(80 + t * (w - 160))
            y_top = int(h * 0.3 + 80 * np.sin(t * np.pi))
            pts.append((x, y_top))
        for i in range(99, -1, -1):
            t = i / 99.0
            x = int(80 + t * (w - 160))
            y_bot = int(h * 0.3 + 80 * np.sin(t * np.pi) + 60)
            pts.append((x, y_bot))
        pts = np.array(pts, dtype=np.int32)
        cv2.fillPoly(img, [pts], (0, 0, 0))
        cv2.polylines(img, [pts], True, (0, 0, 0), 3)
    return draw_on_white(600, 300, draw)


def sample_l_shape_trouser():
    """An L-shaped trouser front with crotch point — classic concave shape."""
    def draw(img):
        pts = np.array([
            [100, 50],
            [350, 50],
            [350, 200],
            [250, 200],
            [250, 450],
            [100, 450],
        ], dtype=np.int32)
        cv2.fillPoly(img, [pts], (0, 0, 0))
        cv2.polylines(img, [pts], True, (0, 0, 0), 3)
    return draw_on_white(450, 500, draw)


def sample_bodice_panel():
    """A back bodice panel with slight curves on the side seams."""
    def draw(img):
        h, w = img.shape[:2]
        pts = []
        # Top edge (neckline curve)
        for i in range(50):
            t = i / 49.0
            x = int(100 + t * 300)
            y = int(60 + 30 * np.sin(t * np.pi))
            pts.append((x, y))
        # Right side seam (slight curve)
        for i in range(30):
            t = i / 29.0
            x = int(400 + 20 * np.sin(t * np.pi))
            y = int(90 + t * 350)
            pts.append((x, y))
        # Bottom hem (slight curve)
        for i in range(49, -1, -1):
            t = i / 49.0
            x = int(100 + t * 300)
            y = int(440 - 15 * np.sin(t * np.pi))
            pts.append((x, y))
        # Left side seam
        for i in range(29, -1, -1):
            t = i / 29.0
            x = int(100 - 15 * np.sin(t * np.pi))
            y = int(90 + t * 350)
            pts.append((x, y))
        pts = np.array(pts, dtype=np.int32)
        cv2.fillPoly(img, [pts], (0, 0, 0))
        cv2.polylines(img, [pts], True, (0, 0, 0), 3)
    return draw_on_white(520, 500, draw)


def sample_multi_piece():
    """Multiple pattern pieces on one sheet — a front, back, and sleeve."""
    def draw(img):
        # Front panel (rectangle-ish)
        front = np.array([
            [50, 50], [220, 50], [220, 300], [50, 300]
        ], dtype=np.int32)
        cv2.fillPoly(img, [front], (0, 0, 0))
        cv2.polylines(img, [front], True, (0, 0, 0), 3)

        # Back panel (with curved side)
        pts = []
        for i in range(40):
            t = i / 39.0
            x = int(280 + 20 * np.sin(t * np.pi))
            y = int(50 + t * 250)
            pts.append((x, y))
        pts.append((450, 300))
        pts.append((450, 50))
        pts = np.array(pts, dtype=np.int32)
        cv2.fillPoly(img, [pts], (0, 0, 0))
        cv2.polylines(img, [pts], True, (0, 0, 0), 3)

        # Sleeve (banana-ish)
        sleeve_pts = []
        for i in range(60):
            t = i / 59.0
            x = int(80 + t * 350)
            y = int(370 + 40 * np.sin(t * np.pi))
            sleeve_pts.append((x, y))
        for i in range(59, -1, -1):
            t = i / 59.0
            x = int(80 + t * 350)
            y = int(370 + 40 * np.sin(t * np.pi) + 70)
            sleeve_pts.append((x, y))
        sleeve_pts = np.array(sleeve_pts, dtype=np.int32)
        cv2.fillPoly(img, [sleeve_pts], (0, 0, 0))
        cv2.polylines(img, [sleeve_pts], True, (0, 0, 0), 3)
    return draw_on_white(520, 520, draw)


if __name__ == "__main__":
    samples = {
        "banana_waistband.png": sample_banana_waistband(),
        "l_shape_trouser.png": sample_l_shape_trouser(),
        "bodice_panel.png": sample_bodice_panel(),
        "multi_piece_layout.png": sample_multi_piece(),
    }
    for name, img in samples.items():
        path = os.path.join(SAMPLES_DIR, name)
        cv2.imwrite(path, img)
        print(f"Saved: {path}")
    print("Done. All samples generated.")

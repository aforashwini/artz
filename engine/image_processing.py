import cv2
import numpy as np
from shapely.geometry import Polygon


def extract_shapes(image_path):
    """
    Extract polygon shapes from a binary/near-binary image of pattern pieces.
    Returns a list of dicts with polygon geometry and metadata.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Adaptive threshold to handle varied lighting
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Morphological close to fill small gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter out noise — only keep contours above a minimum area
    img_area = img.shape[0] * img.shape[1]
    min_area = img_area * 0.005  # at least 0.5% of image

    shapes = []
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        # Approximate polygon to reduce vertices
        epsilon = 0.005 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Need at least 3 points for a polygon
        if len(approx) < 3:
            continue

        coords = [(pt[0][0], pt[0][1]) for pt in approx]
        try:
            polygon = Polygon(coords)
            if not polygon.is_valid:
                polygon = polygon.buffer(0)
            # buffer(0) can return MultiPolygon; take the largest piece
            if polygon.geom_type == "MultiPolygon":
                polygon = max(polygon.geoms, key=lambda g: g.area)
            if polygon.is_empty or polygon.area < min_area:
                continue
        except (RecursionError, Exception):
            continue

        shapes.append({
            "id": i,
            "polygon": polygon,
            "contour": contour,
            "coords": coords,
            "label": f"Piece {len(shapes) + 1}",
        })

    if not shapes:
        raise ValueError(
            "No pattern pieces detected. Make sure the image has clear, "
            "dark outlines on a light background."
        )

    return shapes, img

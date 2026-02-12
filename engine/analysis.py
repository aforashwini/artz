import numpy as np
from shapely.geometry import Polygon


def analyze_efficiency(polygon):
    """
    Analyze a single polygon for fabric waste potential.
    Returns a dict of metrics used by the suggestion engine.
    """
    area = polygon.area
    convex_hull = polygon.convex_hull
    convex_area = convex_hull.area
    bounds = polygon.bounds  # (minx, miny, maxx, maxy)
    bbox_width = bounds[2] - bounds[0]
    bbox_height = bounds[3] - bounds[1]
    bbox_area = bbox_width * bbox_height

    # Core metric: how much of the convex hull is wasted
    waste_factor = (convex_area - area) / convex_area if convex_area > 0 else 0

    # Bounding box utilization
    bbox_utilization = area / bbox_area if bbox_area > 0 else 0

    # Aspect ratio (width / height, normalized so > 1)
    aspect_ratio = max(bbox_width, bbox_height) / min(bbox_width, bbox_height) if min(bbox_width, bbox_height) > 0 else 1

    # Detect concave vertices (internal angles > 180°)
    concave_vertices = _find_concave_vertices(polygon)

    # Curvature analysis — compare perimeter to convex hull perimeter
    perimeter = polygon.length
    convex_perimeter = convex_hull.length
    curvature_excess = (perimeter - convex_perimeter) / convex_perimeter if convex_perimeter > 0 else 0

    return {
        "area": area,
        "convex_hull_area": convex_area,
        "bbox_area": bbox_area,
        "bbox_width": bbox_width,
        "bbox_height": bbox_height,
        "waste_factor": waste_factor,
        "bbox_utilization": bbox_utilization,
        "aspect_ratio": aspect_ratio,
        "concave_vertices": concave_vertices,
        "curvature_excess": curvature_excess,
        "is_inefficient": waste_factor > 0.15,
        "perimeter": perimeter,
        "convex_perimeter": convex_perimeter,
    }


def _find_concave_vertices(polygon):
    """
    Find vertices where the internal angle exceeds 180° (concave points).
    Returns list of (x, y, angle_degrees) tuples.
    """
    coords = list(polygon.exterior.coords)[:-1]  # drop closing duplicate
    n = len(coords)
    if n < 3:
        return []

    concave = []
    for i in range(n):
        p_prev = np.array(coords[(i - 1) % n])
        p_curr = np.array(coords[i])
        p_next = np.array(coords[(i + 1) % n])

        v1 = p_prev - p_curr
        v2 = p_next - p_curr

        cross = np.cross(v1, v2)
        dot = np.dot(v1, v2)
        angle = np.degrees(np.arctan2(abs(cross), dot))

        # Cross product sign tells us concavity direction
        # For a CCW polygon, negative cross = concave
        if cross < 0:
            internal_angle = 360 - angle
        else:
            internal_angle = angle

        if internal_angle > 200:  # threshold above 180 to reduce noise
            concave.append((float(p_curr[0]), float(p_curr[1]), internal_angle))

    return concave

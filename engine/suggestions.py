import numpy as np
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import split

from .analysis import analyze_efficiency


def generate_suggestions(shapes):
    """
    For each shape, run analysis and generate the top 3 suggestions
    ranked by projected fabric savings.
    """
    all_suggestions = []

    for shape in shapes:
        polygon = shape["polygon"]
        metrics = analyze_efficiency(polygon)
        shape["metrics"] = metrics

        suggestions = []

        # Rule A: The Splitter (for curved / banana-shaped pieces)
        splitter = _rule_splitter(polygon, metrics, shape["label"])
        if splitter:
            suggestions.append(splitter)

        # Rule B: The Gusset (for L-shapes / concave pieces)
        gusset = _rule_gusset(polygon, metrics, shape["label"])
        if gusset:
            suggestions.append(gusset)

        # Rule C: The Interlocker (straighten curves for tessellation)
        interlocker = _rule_interlocker(polygon, metrics, shape["label"])
        if interlocker:
            suggestions.append(interlocker)

        # Sort by projected savings descending
        suggestions.sort(key=lambda s: s["savings_pct"], reverse=True)

        # Assign impact labels
        for i, s in enumerate(suggestions):
            if i == 0:
                s["impact"] = "High Impact"
                s["color"] = "#e74c3c"  # red
            elif i == 1:
                s["impact"] = "Medium Impact"
                s["color"] = "#3498db"  # blue
            else:
                s["impact"] = "Quick Win"
                s["color"] = "#2ecc71"  # green

        shape["suggestions"] = suggestions
        all_suggestions.append({
            "shape": shape,
            "metrics": metrics,
            "suggestions": suggestions,
        })

    return all_suggestions


def _rule_splitter(polygon, metrics, label):
    """
    The Banana Split: for highly curved pieces, suggest splitting
    through the centroid along the shortest bounding-box axis.
    """
    # Trigger: high waste factor OR low bbox utilization with high curvature
    if metrics["waste_factor"] < 0.10 and metrics["curvature_excess"] < 0.05:
        return None

    centroid = polygon.centroid
    bounds = polygon.bounds
    bbox_w = metrics["bbox_width"]
    bbox_h = metrics["bbox_height"]

    # Cut along the shortest axis through the centroid
    margin = max(bbox_w, bbox_h) * 0.1
    if bbox_w <= bbox_h:
        # Cut vertically
        cut_line = LineString([
            (centroid.x, bounds[1] - margin),
            (centroid.x, bounds[3] + margin)
        ])
        axis = "vertical"
    else:
        # Cut horizontally
        cut_line = LineString([
            (bounds[0] - margin, centroid.y),
            (bounds[2] + margin, centroid.y)
        ])
        axis = "horizontal"

    # Calculate savings: splitting a curved piece into two straighter halves
    # typically saves proportionally to the waste factor
    new_pieces = _safe_split(polygon, cut_line)
    if new_pieces and len(new_pieces) >= 2:
        new_total_convex = sum(p.convex_hull.area for p in new_pieces)
        old_convex = metrics["convex_hull_area"]
        savings = max(0, (old_convex - new_total_convex) / old_convex * 100)
        savings = min(savings, 25)  # cap at realistic max
    else:
        savings = metrics["waste_factor"] * 40  # estimate

    savings = max(savings, 3)  # minimum visible suggestion

    return {
        "type": "splitter",
        "title": f"Banana Split — {label}",
        "description": (
            f"Split this panel with a {axis} seam through the center. "
            f"This turns one curved piece into two straighter halves that "
            f"nest tightly against each other in the lay plan."
        ),
        "cut_line": cut_line,
        "new_pieces": new_pieces,
        "savings_pct": round(savings, 1),
        "label": label,
    }


def _rule_gusset(polygon, metrics, label):
    """
    The Gusset: for L-shaped pieces with deep concave vertices,
    suggest slicing off the protruding section.
    """
    concave_verts = metrics["concave_vertices"]
    if not concave_verts:
        return None

    # Pick the deepest concave vertex (largest internal angle)
    deepest = max(concave_verts, key=lambda v: v[2])
    cx, cy, angle = deepest

    # Find the two neighboring vertices on the polygon boundary closest
    # to the concave point and create a cut line
    coords = list(polygon.exterior.coords)[:-1]
    idx = None
    for i, (x, y) in enumerate(coords):
        if abs(x - cx) < 1 and abs(y - cy) < 1:
            idx = i
            break

    if idx is None:
        return None

    n = len(coords)
    p_prev = coords[(idx - 2) % n]
    p_next = coords[(idx + 2) % n]
    cut_line = LineString([p_prev, p_next])

    new_pieces = _safe_split(polygon, cut_line)

    # Savings estimate based on concavity depth
    depth_ratio = (angle - 180) / 180  # 0 to 1
    savings = depth_ratio * 20
    savings = max(savings, 2)
    savings = min(savings, 18)

    return {
        "type": "gusset",
        "title": f"Gusset Slice — {label}",
        "description": (
            f"Remove the protruding corner at ({int(cx)}, {int(cy)}) and "
            f"re-attach it as a separate gusset piece. This eliminates the "
            f"deep concavity that traps dead space in the lay plan."
        ),
        "cut_line": cut_line,
        "new_pieces": new_pieces,
        "concave_point": (cx, cy),
        "savings_pct": round(savings, 1),
        "label": label,
    }


def _rule_interlocker(polygon, metrics, label):
    """
    The Straighten & Interlock: suggest straightening slightly curved
    edges so pieces can tessellate with zero gaps.
    """
    coords = list(polygon.exterior.coords)[:-1]
    n = len(coords)
    if n < 4:
        return None

    # Find the longest edge that deviates from a straight line
    best_edge = None
    best_deviation = 0

    for i in range(n):
        p1 = np.array(coords[i])
        p2 = np.array(coords[(i + 1) % n])
        p3 = np.array(coords[(i + 2) % n])

        # Check if three consecutive points form a near-straight line
        edge_len = np.linalg.norm(p2 - p1) + np.linalg.norm(p3 - p2)
        direct_len = np.linalg.norm(p3 - p1)

        if direct_len > 0:
            deviation = (edge_len - direct_len) / direct_len
            if deviation > best_deviation and deviation < 0.5:
                best_deviation = deviation
                best_edge = (
                    (float(p1[0]), float(p1[1])),
                    (float(p2[0]), float(p2[1])),
                    (float(p3[0]), float(p3[1])),
                )

    if best_edge is None or best_deviation < 0.01:
        # Fallback: always provide a tessellation suggestion
        # based on straightening the longest edge
        edges = []
        for i in range(n):
            p1 = np.array(coords[i])
            p2 = np.array(coords[(i + 1) % n])
            length = np.linalg.norm(p2 - p1)
            edges.append((length, i))
        edges.sort(reverse=True)
        if edges:
            i = edges[0][1]
            p1 = coords[i]
            p2 = coords[(i + 1) % n]
            straighten_line = LineString([p1, p2])
            savings = 3 + metrics["waste_factor"] * 10
        else:
            return None
    else:
        straighten_line = LineString([best_edge[0], best_edge[2]])
        savings = best_deviation * 30
        savings = max(savings, 2)
        savings = min(savings, 12)

    return {
        "type": "interlocker",
        "title": f"Straighten & Interlock — {label}",
        "description": (
            f"Straighten the slightly curved edge to allow this piece to be "
            f"placed top-to-tail with its neighbor, achieving near-zero gap "
            f"tessellation in the lay plan."
        ),
        "straighten_line": straighten_line,
        "savings_pct": round(savings, 1),
        "label": label,
    }


def _safe_split(polygon, line):
    """Split a polygon by a line, returning list of pieces or None."""
    try:
        # Simplify polygon to reduce vertex count and avoid deep recursion
        simplified = polygon.simplify(1.0, preserve_topology=True)
        if simplified.is_empty or not simplified.is_valid:
            simplified = polygon
        result = split(simplified, line)
        pieces = [g for g in result.geoms if isinstance(g, Polygon) and g.area > 0]
        return pieces if len(pieces) >= 2 else None
    except (RecursionError, Exception):
        return None

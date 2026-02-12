import os
import uuid

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import numpy as np
from shapely.geometry import Polygon


RESULT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results")


def generate_visualization(shape, suggestion, original_image=None):
    """
    Generate a visualization image for a single suggestion.
    Returns the filename of the saved image.
    """
    fig, ax = plt.subplots(1, 1, figsize=(8, 6), dpi=100)

    polygon = shape["polygon"]
    # Simplify for rendering to avoid deep recursion in matplotlib
    if len(polygon.exterior.coords) > 50:
        polygon = polygon.simplify(2.0, preserve_topology=True)
    coords = list(polygon.exterior.coords)
    xs, ys = zip(*coords)

    # Draw original polygon filled
    poly_patch = plt.Polygon(
        list(zip(xs, ys)),
        closed=True,
        facecolor="#f0f0f0",
        edgecolor="#2c3e50",
        linewidth=2.5,
        zorder=2,
    )
    ax.add_patch(poly_patch)

    stype = suggestion["type"]
    color = suggestion.get("color", "#e74c3c")

    if stype == "splitter":
        _draw_cut_line(ax, suggestion["cut_line"], color, "Cut Line")
        if suggestion.get("new_pieces"):
            for i, piece in enumerate(suggestion["new_pieces"]):
                pc = list(piece.exterior.coords)
                pxs, pys = zip(*pc)
                fill = "#ffe0e0" if i % 2 == 0 else "#e0ffe0"
                p = plt.Polygon(
                    list(zip(pxs, pys)),
                    closed=True,
                    facecolor=fill,
                    edgecolor=color,
                    linewidth=1.5,
                    linestyle="--",
                    alpha=0.6,
                    zorder=3,
                )
                ax.add_patch(p)

    elif stype == "gusset":
        _draw_cut_line(ax, suggestion["cut_line"], color, "Gusset Seam")
        if suggestion.get("concave_point"):
            cx, cy = suggestion["concave_point"]
            ax.plot(cx, cy, "o", color=color, markersize=10, zorder=5)
            ax.annotate(
                "Concave\nVertex",
                xy=(cx, cy),
                xytext=(cx + 20, cy - 30),
                fontsize=8,
                color=color,
                fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=color, lw=1.5),
                zorder=5,
            )

    elif stype == "interlocker":
        line = suggestion.get("straighten_line")
        if line:
            lx, ly = line.xy
            ax.plot(lx, ly, color=color, linewidth=3, linestyle="-", alpha=0.8, zorder=4)
            # Draw a subtle green overlay to show the straightened zone
            ax.fill_between(
                lx, [y - 5 for y in ly], [y + 5 for y in ly],
                color=color, alpha=0.15, zorder=3,
            )

    # Labels and styling
    ax.set_title(
        suggestion["title"],
        fontsize=14,
        fontweight="bold",
        color="#2c3e50",
        pad=15,
    )

    savings_text = f"Projected Savings: {suggestion['savings_pct']}% fabric reduction"
    ax.text(
        0.5, -0.08, savings_text,
        transform=ax.transAxes,
        fontsize=11,
        ha="center",
        color=color,
        fontweight="bold",
    )

    impact_text = suggestion.get("impact", "")
    if impact_text:
        ax.text(
            0.02, 0.98, impact_text,
            transform=ax.transAxes,
            fontsize=10,
            ha="left",
            va="top",
            fontweight="bold",
            color="white",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.9),
            zorder=10,
        )

    ax.set_aspect("equal")
    ax.invert_yaxis()  # match image coordinate system
    ax.set_xlim(min(xs) - 30, max(xs) + 30)
    ax.set_ylim(max(ys) + 30, min(ys) - 30)
    ax.axis("off")

    fig.tight_layout()

    filename = f"suggestion_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(RESULT_DIR, filename)
    fig.savefig(filepath, bbox_inches="tight", facecolor="white", dpi=120)
    plt.close(fig)

    return filename


def generate_overview(shapes, original_image):
    """
    Generate an overview image showing all detected pieces outlined on the original.
    """
    fig, ax = plt.subplots(1, 1, figsize=(10, 8), dpi=100)

    # Show original image
    import cv2
    rgb = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
    ax.imshow(rgb, alpha=0.5)

    colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]
    for i, shape in enumerate(shapes):
        polygon = shape["polygon"]
        if len(polygon.exterior.coords) > 50:
            polygon = polygon.simplify(2.0, preserve_topology=True)
        coords = list(polygon.exterior.coords)
        xs, ys = zip(*coords)
        color = colors[i % len(colors)]

        poly_patch = plt.Polygon(
            list(zip(xs, ys)),
            closed=True,
            facecolor=color,
            edgecolor=color,
            linewidth=2,
            alpha=0.3,
            zorder=2,
        )
        ax.add_patch(poly_patch)

        centroid = polygon.centroid
        ax.text(
            centroid.x, centroid.y, shape["label"],
            fontsize=10, fontweight="bold", color="white",
            ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.8),
            zorder=3,
        )

    ax.set_title("Detected Pattern Pieces", fontsize=14, fontweight="bold", color="#2c3e50")
    ax.axis("off")
    fig.tight_layout()

    filename = f"overview_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(RESULT_DIR, filename)
    fig.savefig(filepath, bbox_inches="tight", facecolor="white", dpi=120)
    plt.close(fig)

    return filename


def _draw_cut_line(ax, line, color, label):
    """Draw a dashed cut line on the axes."""
    lx, ly = line.xy
    ax.plot(
        lx, ly,
        color=color,
        linewidth=2.5,
        linestyle="--",
        dashes=(8, 4),
        zorder=4,
        label=label,
    )
    # Small scissors icon at midpoint
    mx = (lx[0] + lx[-1]) / 2
    my = (ly[0] + ly[-1]) / 2
    ax.annotate(
        "✂",
        xy=(mx, my),
        fontsize=16,
        ha="center",
        va="center",
        zorder=5,
    )

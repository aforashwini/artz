import io
import base64

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def generate_visualization(shape, suggestion, original_image=None):
    """Generate a visualization image for a single suggestion. Returns a data URI."""
    fig, ax = plt.subplots(1, 1, figsize=(8, 6), dpi=100)
    try:
        polygon = shape["polygon"]
        if len(polygon.exterior.coords) > 50:
            polygon = polygon.simplify(2.0, preserve_topology=True)
        coords = list(polygon.exterior.coords)
        xs, ys = zip(*coords)

        poly_patch = plt.Polygon(
            list(zip(xs, ys)),
            closed=True,
            facecolor="#EDE9FE",
            edgecolor="#5B21B6",
            linewidth=2.5,
            zorder=2,
        )
        ax.add_patch(poly_patch)

        stype = suggestion["type"]
        color = suggestion.get("color", "#5B21B6")

        if stype == "splitter":
            if suggestion.get("cut_line"):
                _draw_cut_line(ax, suggestion["cut_line"], color)
            if suggestion.get("new_pieces"):
                fills = ["#F3E8FF", "#DBEAFE", "#D1FAE5", "#FEF3C7"]
                for i, piece in enumerate(suggestion["new_pieces"]):
                    try:
                        if piece.geom_type == "MultiPolygon":
                            piece = max(piece.geoms, key=lambda g: g.area)
                        pc = list(piece.exterior.coords)
                        pxs, pys = zip(*pc)
                        p = plt.Polygon(
                            list(zip(pxs, pys)),
                            closed=True,
                            facecolor=fills[i % len(fills)],
                            edgecolor=color,
                            linewidth=1.5,
                            linestyle="--",
                            alpha=0.6,
                            zorder=3,
                        )
                        ax.add_patch(p)
                    except Exception:
                        pass

        elif stype == "gusset":
            if suggestion.get("cut_line"):
                _draw_cut_line(ax, suggestion["cut_line"], color)
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
                ax.fill_between(
                    lx, [y - 5 for y in ly], [y + 5 for y in ly],
                    color=color, alpha=0.15, zorder=3,
                )

        ax.set_title(
            suggestion["title"],
            fontsize=14,
            fontweight="bold",
            color="#1e1b4b",
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
        ax.invert_yaxis()
        ax.set_xlim(min(xs) - 30, max(xs) + 30)
        ax.set_ylim(max(ys) + 30, min(ys) - 30)
        ax.axis("off")

        return _fig_to_data_uri(fig)
    finally:
        plt.close(fig)


def generate_overview(shapes, original_image):
    """Generate an overview image showing all detected pieces. Returns a data URI."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 8), dpi=100)
    try:
        import cv2
        rgb = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
        ax.imshow(rgb, alpha=0.5)

        colors = ["#5B21B6", "#7C3AED", "#2563EB", "#059669", "#D97706", "#DC2626"]
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

        ax.set_title("Detected Pattern Pieces", fontsize=14, fontweight="bold", color="#1e1b4b")
        ax.axis("off")

        return _fig_to_data_uri(fig)
    finally:
        plt.close(fig)


def _fig_to_data_uri(fig):
    """Convert a matplotlib figure to a PNG base64 data URI."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", dpi=120)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _draw_cut_line(ax, line, color):
    """Draw a dashed cut line on the axes."""
    lx, ly = line.xy
    ax.plot(
        lx, ly,
        color=color,
        linewidth=2.5,
        linestyle="--",
        dashes=(8, 4),
        zorder=4,
    )
    mx = (lx[0] + lx[-1]) / 2
    my = (ly[0] + ly[-1]) / 2
    ax.plot(mx, my, "x", color=color, markersize=12, markeredgewidth=3, zorder=5)

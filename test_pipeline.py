"""Quick integration test: run the full pipeline on all sample images."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from engine.image_processing import extract_shapes
from engine.analysis import analyze_efficiency
from engine.suggestions import generate_suggestions
from engine.visualization import generate_visualization, generate_overview

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

errors = []

for fname in sorted(os.listdir(SAMPLES_DIR)):
    if not fname.endswith(".png"):
        continue
    path = os.path.join(SAMPLES_DIR, fname)
    print(f"\n{'='*60}")
    print(f"Testing: {fname}")
    print(f"{'='*60}")

    try:
        # Step 1: Extract shapes
        shapes, original_image = extract_shapes(path)
        print(f"  Detected {len(shapes)} piece(s)")

        # Step 2: Generate suggestions
        results = generate_suggestions(shapes)

        # Step 3: Generate visualizations
        overview_file = generate_overview(shapes, original_image)
        print(f"  Overview image: {overview_file}")

        for result in results:
            shape = result["shape"]
            metrics = result["metrics"]
            print(f"\n  {shape['label']}:")
            print(f"    Area: {metrics['area']:.0f}")
            print(f"    Waste Factor: {metrics['waste_factor']*100:.1f}%")
            print(f"    BBox Utilization: {metrics['bbox_utilization']*100:.1f}%")
            print(f"    Inefficient: {metrics['is_inefficient']}")
            print(f"    Concave vertices: {len(metrics['concave_vertices'])}")

            for s in result["suggestions"]:
                vis_file = generate_visualization(shape, s, original_image)
                print(f"    -> {s['title']} | {s['impact']} | Savings: {s['savings_pct']}% | Image: {vis_file}")

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        errors.append((fname, str(e)))

print(f"\n{'='*60}")
if errors:
    print(f"FAILED: {len(errors)} sample(s) had errors:")
    for fname, err in errors:
        print(f"  {fname}: {err}")
    sys.exit(1)
else:
    print("ALL SAMPLES PASSED")

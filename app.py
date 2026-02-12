import os
import sys
import uuid
import traceback

# Shapely split operations can recurse deeply on complex polygons
sys.setrecursionlimit(10000)

from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from engine.image_processing import extract_shapes
from engine.analysis import analyze_efficiency
from engine.suggestions import generate_suggestions
from engine.visualization import generate_visualization, generate_overview

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["RESULT_FOLDER"] = os.path.join(os.path.dirname(__file__), "results")
app.config["SAMPLE_FOLDER"] = os.path.join(os.path.dirname(__file__), "samples")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    # List available sample images
    samples = []
    sample_dir = app.config["SAMPLE_FOLDER"]
    if os.path.isdir(sample_dir):
        for f in sorted(os.listdir(sample_dir)):
            if allowed_file(f):
                samples.append(f)
    return render_template("index.html", samples=samples)


@app.route("/analyze", methods=["POST"])
def analyze():
    """Main analysis endpoint. Accepts an uploaded image or a sample name."""
    try:
        filepath = None

        # Check if using a sample image
        sample_name = request.form.get("sample")
        if sample_name:
            sample_path = os.path.join(app.config["SAMPLE_FOLDER"], secure_filename(sample_name))
            if os.path.isfile(sample_path):
                filepath = sample_path
            else:
                return jsonify({"error": f"Sample '{sample_name}' not found."}), 404

        # Check if a file was uploaded
        if filepath is None:
            if "file" not in request.files:
                return jsonify({"error": "No file uploaded."}), 400
            file = request.files["file"]
            if file.filename == "":
                return jsonify({"error": "No file selected."}), 400
            if not allowed_file(file.filename):
                return jsonify({"error": "File type not allowed. Use PNG, JPG, BMP, or TIFF."}), 400

            # Save uploaded file
            ext = file.filename.rsplit(".", 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

        # Run the analysis pipeline
        shapes, original_image = extract_shapes(filepath)
        results = generate_suggestions(shapes)

        # Generate overview image
        overview_file = generate_overview(shapes, original_image)

        # Generate suggestion visualizations
        response_data = {
            "overview": f"/results/{overview_file}",
            "piece_count": len(shapes),
            "pieces": [],
        }

        for result in results:
            shape = result["shape"]
            metrics = result["metrics"]
            suggestions_out = []

            for suggestion in result["suggestions"]:
                vis_file = generate_visualization(shape, suggestion, original_image)
                suggestions_out.append({
                    "type": suggestion["type"],
                    "title": suggestion["title"],
                    "description": suggestion["description"],
                    "savings_pct": suggestion["savings_pct"],
                    "impact": suggestion.get("impact", ""),
                    "color": suggestion.get("color", "#333"),
                    "image": f"/results/{vis_file}",
                })

            response_data["pieces"].append({
                "label": shape["label"],
                "area": round(metrics["area"], 1),
                "waste_factor": round(metrics["waste_factor"] * 100, 1),
                "bbox_utilization": round(metrics["bbox_utilization"] * 100, 1),
                "is_inefficient": metrics["is_inefficient"],
                "suggestions": suggestions_out,
            })

        return jsonify(response_data)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


@app.route("/results/<filename>")
def serve_result(filename):
    return send_from_directory(app.config["RESULT_FOLDER"], filename)


@app.route("/samples/<filename>")
def serve_sample(filename):
    return send_from_directory(app.config["SAMPLE_FOLDER"], filename)


# Ensure directories exist at import time (needed for Render/gunicorn)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["RESULT_FOLDER"], exist_ok=True)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

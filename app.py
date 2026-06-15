#!/usr/bin/env python3
"""
Simple web interface for the birth registration PDF generator.
"""

import json
import os
import tempfile
import uuid
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file

from generator import build_sample_data, generate_pdf
from renderer import register_fonts


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


def load_field_map():
    with open("analysis/field_map.json", encoding="utf-8") as f:
        return json.load(f)


@app.route("/")
def index():
    field_map = load_field_map()
    fields = field_map.get("fields", [])
    sample = build_sample_data()
    return render_template("index.html", fields=fields, sample=sample)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json() or {}
    output_filename = f"birth_form_{uuid.uuid4().hex[:8]}.pdf"
    output_path = os.path.join("output", output_filename)
    generate_pdf(data, output_path=output_path)
    return jsonify({"filename": output_filename, "path": output_path})


@app.route("/api/download/<filename>")
def api_download(filename):
    path = os.path.join("output", filename)
    if not os.path.exists(path):
        return jsonify({"error": "file not found"}), 404
    return send_file(path, as_attachment=True, download_name=filename)


@app.route("/api/preview", methods=["POST"])
def api_preview():
    data = request.get_json() or {}
    output_filename = f"preview_{uuid.uuid4().hex[:8]}.png"
    output_path = os.path.join("output", output_filename)
    pdf_path = os.path.join("output", f"preview_{uuid.uuid4().hex[:8]}.pdf")
    generate_pdf(data, output_path=pdf_path)
    import fitz
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    pix.save(output_path)
    doc.close()
    os.remove(pdf_path)
    return jsonify({"filename": output_filename, "path": output_path})


@app.route("/api/preview/<filename>")
def serve_preview(filename):
    path = os.path.join("output", filename)
    if not os.path.exists(path):
        return jsonify({"error": "preview not found"}), 404
    return send_file(path)


@app.route("/api/fields")
def api_fields():
    return jsonify(load_field_map())

register_fonts()

os.makedirs("output", exist_ok=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
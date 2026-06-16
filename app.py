#!/usr/bin/env python3

import json
import os

from flask import Flask, jsonify, render_template, request, send_file

from config.field_config import FIELD_SECTIONS, FIELD_LABELS
from html_pdf_generator import generate_pdf
from translator import build_english_fields

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_field_map():
    with open(
        os.path.join(BASE_DIR, "analysis", "field_map.json"),
        encoding="utf-8"
    ) as f:
        return json.load(f)


def build_sample_data():
    return {
        "applicant_name": "",
        "applicant_address": "",
        "application_date": "",

        "affidavit_applicant_name": "",
        "affidavit_applicant_age": "",
        "affidavit_relationship": "",
        "affidavit_birth_date": "",
        "affidavit_hospital_name": "",

        "child_name_marathi": "",
        "child_name_english": "",

        "father_name_marathi": "",
        "father_name_english": "",

        "mother_name_marathi": "",
        "mother_name_english": "",

        "birth_date_value": "",

        "address_at_birth_marathi":
            "",

        "permanent_address_marathi":
            "",

        "applicant_signature": "",
    }


@app.route("/")
def index():

    field_map = load_field_map()

    return render_template(
        "index.html",
        fields=field_map.get("fields", []),
        sections=FIELD_SECTIONS,
        labels=FIELD_LABELS,
        sample=build_sample_data()
    )


@app.route("/api/generate", methods=["POST"])
def api_generate():

    data = request.get_json() or {}

    translated = build_english_fields(data)

    if translated is not None:
     data = translated

    filename = generate_pdf(data)

    return jsonify({
        "filename": filename
    })


@app.route("/api/download/<filename>")
def api_download(filename):

    path = os.path.join("output", filename)

    if not os.path.exists(path):
        return jsonify({
            "error": "file not found"
        }), 404

    return send_file(
        path,
        as_attachment=True,
        download_name=filename
    )


@app.route("/api/fields")
def api_fields():
    return jsonify(load_field_map())
    

os.makedirs("output", exist_ok=True)

if __name__ == "__main__":
    app.run(
    host="0.0.0.0",
    port=5000,
    debug=False
)
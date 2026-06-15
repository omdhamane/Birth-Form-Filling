#!/usr/bin/env python3
"""
Generate filled birth registration PDF by overlaying text on the original template.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import fitz
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from renderer import (
    TextBox,
    detect_language,
    draw_text_box,
    fit_text_in_box,
    get_font_name,
    register_fonts,
)


PDF_PATH = "uploads/birth_registration_form_v3.pdf"
FIELD_MAP_PATH = "analysis/field_map.json"
OUTPUT_DIR = "output"


def create_overlay_pdf(fields: List[dict], data: Dict[str, str], page_size=A4,
                       debug: bool = False, diagnostic: bool = False) -> str:
    """Create a transparent overlay PDF with rendered text (and optional debug boxes)."""
    overlay_path = os.path.join(OUTPUT_DIR, "overlay.pdf")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    c = canvas.Canvas(overlay_path, pagesize=page_size)
    width, height = page_size

    # Optional diagnostic background: page dimensions, axes
    if diagnostic or debug:
        c.setStrokeColor(Color(1, 0, 0, alpha=0.4))
        c.setLineWidth(0.5)
        # Page boundary
        c.rect(0, 0, width, height, stroke=1, fill=0)
        # Center crosshair
        c.line(width / 2, 0, width / 2, height)
        c.line(0, height / 2, width, height / 2)
        # Margins at 42 pt
        c.setStrokeColor(Color(0, 0, 1, alpha=0.3))
        c.rect(42, 42, width - 84, height - 84, stroke=1, fill=0)

    def field_to_rl(field):
        """Convert top-down PDF field coordinates to reportlab bottom-up coordinates."""
        return {
            "x": field["x"],
            "y": height - field["y"] - field["height"],
            "width": field["width"],
            "height": field["height"],
        }

    for field in fields:
        name = field["fieldName"]
        value = data.get(name)
        f = field_to_rl(field)
        if not value or not str(value).strip():
            if diagnostic:
                # Draw empty field boundary with label
                c.setStrokeColor(Color(1, 0, 0, alpha=0.5))
                c.setFillColor(Color(1, 0.9, 0.9, alpha=0.3))
                c.rect(f["x"], f["y"], f["width"], f["height"], stroke=1, fill=1)
                c.setFillColor(Color(0, 0, 0))
                c.setFont("Mukta-Regular", 6)
                c.drawString(f["x"] + 1, f["y"] + f["height"] - 6, name)
            continue

        value = str(value).strip()
        lang = detect_language(value)
        font_name = get_font_name(lang)
        font_size = 11 if lang == "marathi" else 10.5

        # Auto-fit
        size, lines = fit_text_in_box(c, value, font_name, f["width"], f["height"], start_size=font_size, min_size=7)
        c.setFont(font_name, size)

        # Determine vertical alignment inside the field.
        # If the text fits on a single line, center it vertically; otherwise top-align.
        if len(lines) <= 1:
            baseline_y = f["y"] + (f["height"] + size) / 2 - 1
        else:
            baseline_y = f["y"] + f["height"] - 2

        # Apply a small downward baseline correction for top fields and inline affidavit fields so the text sits on the dotted line.
        source = field.get("source", "")
        if source == "inline_blank_words":
            baseline_y -= 3.5
        elif source in ("top_label_line", "date_slash_positions"):
            baseline_y -= 2.5

        box = TextBox(
            text=value,
            x=f["x"],
            y=baseline_y,
            width=f["width"],
            height=f["height"],
            font_name=font_name,
            font_size=size,
            align="left",
        )
        draw_text_box(c, box, debug=False)

        if debug or diagnostic:
            c.setStrokeColor(Color(1, 0, 0, alpha=0.5))
            c.rect(f["x"], f["y"], f["width"], f["height"], stroke=1, fill=0)
            c.setFillColor(Color(1, 0, 0))
            c.setFont("Mukta-Regular", 6)
            c.drawString(f["x"], f["y"] + f["height"] + 2, f"{name} ({size:.1f})")

    c.save()
    return overlay_path


def merge_with_template(overlay_path: str, template_path: str, output_path: str):
    """Merge overlay PDF with the original template PDF using PyMuPDF."""
    template_doc = fitz.open(template_path)
    overlay_doc = fitz.open(overlay_path)

    for page_num in range(template_doc.page_count):
        page = template_doc[page_num]
        if page_num < overlay_doc.page_count:
            overlay_page = overlay_doc[page_num]
            page.show_pdf_page(page.rect, overlay_doc, page_num, overlay=True)

    template_doc.save(output_path)
    template_doc.close()
    overlay_doc.close()


def generate_pdf(data: Dict[str, str], output_path: Optional[str] = None,
                 debug: bool = False, diagnostic: bool = False) -> str:
    """Generate the final filled PDF."""
    register_fonts()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, "final_output.pdf")

    with open(FIELD_MAP_PATH, encoding="utf-8") as f:
        field_map = json.load(f)
    fields = field_map.get("fields", [])

    overlay_path = create_overlay_pdf(fields, data, debug=debug, diagnostic=diagnostic)
    merge_with_template(overlay_path, PDF_PATH, output_path)
    return output_path


def generate_diagnostic_pdf(data: Dict[str, str] = None, output_path: Optional[str] = None) -> str:
    """Generate a diagnostic PDF showing field boundaries and coordinates."""
    if data is None:
        data = {}
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, "diagnostic_output.pdf")
    return generate_pdf(data, output_path=output_path, diagnostic=True)


def build_sample_data() -> Dict[str, str]:
    return {
        "applicant_name": "रत्नाकर शंकर पाटील",
        "applicant_address": "सेक्टर ५, महाराष्ट्र हॉस्पिटल रोड, मालेगाव",
        "application_date": "१५/०६/२०२६",
        "affidavit_applicant_name": "रत्नाकर शंकर पाटील",
        "affidavit_applicant_age": "३२",
        "affidavit_relationship": "वडील",
        "affidavit_birth_date": "१०/०६/२०२६",
        "affidavit_hospital_name": "महाराष्ट्र हॉस्पिटल",
        "child_name_marathi": "अर्जुन रत्नाकर पाटील",
        "child_name_english": "ARJUN RATNAKAR PATIL",
        "birth_date_value": "१०/०६/२०२६",
        "father_name_marathi": "रत्नाकर शंकर पाटील",
        "father_name_english": "RATNAKAR SHANKAR PATIL",
        "father_aadhaar_marathi": "१२३४ ५६७८ ९०१२",
        "mother_name_marathi": "सविता रत्नाकर पाटील",
        "mother_name_english": "SAVITA RATNAKAR PATIL",
        "mother_aadhaar_marathi": "९८७६ ५४३२ १०९८",
        "address_at_birth_marathi": "सेक्टर ५, महाराष्ट्र हॉस्पिटल, मालेगाव",
        "permanent_address_marathi": "सेक्टर ५, महाराष्ट्र हॉस्पिटल, मालेगाव",
        "applicant_signature": "रत्नाकर पाटील",
    }


def main():
    register_fonts()
    data = build_sample_data()
    final_path = generate_pdf(data)
    diag_path = generate_diagnostic_pdf()
    print(f"Final PDF: {final_path}")
    print(f"Diagnostic PDF: {diag_path}")


if __name__ == "__main__":
    main()

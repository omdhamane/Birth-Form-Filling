#!/usr/bin/env python3
"""
PHASE 3 & 4: Visual calibration and auto-calibration.
Produces diagnostic PDFs and coordinate_report.json.
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple

import fitz
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from renderer import detect_language, get_font_name, register_fonts


OUTPUT_DIR = "output"
ANALYSIS_DIR = "analysis"


def field_to_rl(field, page_height):
    return {
        "x": field["x"],
        "y": page_height - field["y"] - field["height"],
        "width": field["width"],
        "height": field["height"],
    }


def create_diagnostic_pdf(fields: List[dict], template_path: str, output_path: str):
    """Create a diagnostic PDF with field boundaries, coordinates, and anchor points."""
    register_fonts()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    template_doc = fitz.open(template_path)
    page = template_doc[0]
    page_width, page_height = page.rect.width, page.rect.height

    c = canvas.Canvas(output_path, pagesize=(page_width, page_height))

    # Draw template as background (optional: omit to keep vector overlay clean)
    # Instead, we draw the template page using PyMuPDF after text overlay.
    c.save()

    # Now create overlay with diagnostic info
    overlay_path = os.path.join(OUTPUT_DIR, "diagnostic_overlay.pdf")
    c = canvas.Canvas(overlay_path, pagesize=(page_width, page_height))

    # Page dimensions and axes
    c.setStrokeColor(Color(1, 0, 0, alpha=0.4))
    c.setLineWidth(0.5)
    c.rect(0, 0, page_width, page_height, stroke=1, fill=0)
    c.line(page_width / 2, 0, page_width / 2, page_height)
    c.line(0, page_height / 2, page_width, page_height / 2)

    # Margins
    c.setStrokeColor(Color(0, 0, 1, alpha=0.3))
    c.rect(42, 42, page_width - 84, page_height - 84, stroke=1, fill=0)

    # Anchor points: corners and center
    c.setFillColor(Color(1, 0, 0))
    for ax, ay in [(0, 0), (page_width, 0), (0, page_height), (page_width, page_height), (page_width/2, page_height/2)]:
        c.circle(ax, ay, 3, stroke=0, fill=1)

    c.setFont("Mukta-Regular", 6)
    for field in fields:
        f = field_to_rl(field, page_height)
        # Field boundary
        c.setStrokeColor(Color(1, 0, 0, alpha=0.6))
        c.setFillColor(Color(1, 0.9, 0.9, alpha=0.2))
        c.rect(f["x"], f["y"], f["width"], f["height"], stroke=1, fill=1)
        # Baseline guide (horizontal line through vertical center)
        c.setStrokeColor(Color(0, 0, 1, alpha=0.5))
        c.setDash(2, 2)
        by = f["y"] + f["height"] / 2
        c.line(f["x"] - 5, by, f["x"] + f["width"] + 5, by)
        c.setDash()
        # Coordinate labels
        c.setFillColor(Color(0, 0, 0))
        label = f"{field['fieldName']} ({field['x']:.1f},{field['y']:.1f}) {field['width']:.1f}x{field['height']:.1f}"
        c.drawString(f["x"] + 1, f["y"] + f["height"] - 6, label)
        # Anchor point at top-left
        c.setFillColor(Color(0, 1, 0))
        c.circle(f["x"], f["y"] + f["height"], 2, stroke=0, fill=1)

    c.save()

    # Merge overlay with template
    final_doc = fitz.open(template_path)
    overlay_doc = fitz.open(overlay_path)
    for page_num in range(final_doc.page_count):
        final_doc[page_num].show_pdf_page(final_doc[page_num].rect, overlay_doc, page_num, overlay=True)
    final_doc.save(output_path)
    final_doc.close()
    overlay_doc.close()


def measure_text_render_position(field: dict, template_path: str, test_value: str) -> Dict:
    """Render a single test value in a field and measure its bounding box in the merged PDF."""
    register_fonts()
    from generator import create_overlay_pdf, merge_with_template

    fields = [field]
    data = {field["fieldName"]: test_value}
    overlay_path = create_overlay_pdf(fields, data, page_size=A4)
    merged_path = os.path.join(OUTPUT_DIR, "calib_test.pdf")
    merge_with_template(overlay_path, template_path, merged_path)

    doc = fitz.open(merged_path)
    page = doc[0]
    # Get text blocks and find the one matching the test value
    blocks = page.get_text("dict")["blocks"]
    measured = None
    for b in blocks:
        if "lines" in b:
            for line in b["lines"]:
                for span in line["spans"]:
                    if test_value[:5] in span["text"] or span["text"][:5] in test_value:
                        bbox = span["bbox"]
                        measured = {
                            "x": bbox[0],
                            "y": bbox[1],
                            "width": bbox[2] - bbox[0],
                            "height": bbox[3] - bbox[1],
                        }
                        break
                if measured:
                    break
        if measured:
            break
    doc.close()

    target = {
        "x": field["x"],
        "y": field["y"],
        "width": field["width"],
        "height": field["height"],
    }
    if measured:
        offset = {
            "dx": measured["x"] - target["x"],
            "dy": measured["y"] - target["y"],
            "dw": measured["width"] - target["width"],
            "dh": measured["height"] - target["height"],
        }
    else:
        offset = None
    return {
        "fieldName": field["fieldName"],
        "target": target,
        "measured": measured,
        "offset": offset,
    }


def auto_calibrate_fields(fields: List[dict], template_path: str) -> List[dict]:
    """Run auto-calibration on a subset of fields and return adjusted fields."""
    calibrated = []
    for field in fields:
        test_value = "रत्नाकर" if "marathi" in field["fieldName"] or "address" in field["fieldName"] else "RATNAKAR"
        if "date" in field["fieldName"]:
            test_value = "१५/०६/२०२६"
        result = measure_text_render_position(field, template_path, test_value)
        if result["offset"]:
            # Adjust field y if measured text is significantly off vertically
            dy = result["offset"]["dy"]
            if abs(dy) > 3:
                field = dict(field)
                field["y"] -= dy
                field["confidence"] = min(1.0, field.get("confidence", 0.8) + 0.05)
                field["source"] = field.get("source", "") + "_calibrated"
        calibrated.append(field)
    return calibrated


def generate_coordinate_report(fields: List[dict], template_path: str) -> str:
    """Generate coordinate_report.json with field positions, confidence, and calibration info."""
    doc = fitz.open(template_path)
    page = doc[0]
    page_width, page_height = page.rect.width, page.rect.height
    doc.close()

    report = {
        "template": template_path,
        "page_width": page_width,
        "page_height": page_height,
        "fields": [],
    }
    for f in fields:
        entry = {
            "fieldName": f["fieldName"],
            "x": f["x"],
            "y": f["y"],
            "width": f["width"],
            "height": f["height"],
            "confidence": f.get("confidence"),
            "source": f.get("source"),
            "page": f.get("page", 0),
            "baseline_y": f["y"] + f["height"] / 2,
            "right_edge": f["x"] + f["width"],
            "bottom_edge": f["y"] + f["height"],
        }
        report["fields"].append(entry)

    report_path = os.path.join(OUTPUT_DIR, "coordinate_report.json")
    with open(report_path, "w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=2)
    return report_path


def generate_conjunct_validation_pdf(output_path: str = None):
    """Generate a validation PDF showing key Marathi conjuncts."""
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, "conjunct_validation.pdf")
    register_fonts()
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    c.setFont("NotoSansDevanagari-Regular", 16)
    c.drawString(50, height - 50, "Marathi Conjunct Validation")
    samples = [
        "रत्नाकर",
        "सेक्टर",
        "हॉस्पिटल",
        "महाराष्ट्र",
    ]
    y = height - 90
    for s in samples:
        w = c.stringWidth(s, "NotoSansDevanagari-Regular", 16)
        c.drawString(50, y, s)
        c.drawString(50 + w + 10, y, f"width={w:.1f}pt")
        y -= 30
    c.save()
    return output_path


def main():
    register_fonts()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(ANALYSIS_DIR, "field_map.json"), encoding="utf-8") as f:
        field_map = json.load(f)
    fields = field_map["fields"]
    template_path = field_map["file"]

    diag_path = os.path.join(OUTPUT_DIR, "diagnostic_output.pdf")
    create_diagnostic_pdf(fields, template_path, diag_path)

    report_path = generate_coordinate_report(fields, template_path)
    conj_path = generate_conjunct_validation_pdf()

    print(f"Diagnostic PDF: {diag_path}")
    print(f"Coordinate report: {report_path}")
    print(f"Conjunct validation PDF: {conj_path}")


if __name__ == "__main__":
    main()

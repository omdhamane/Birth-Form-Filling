#!/usr/bin/env python3
"""
PHASE 1: PDF Template Analysis
Extract structural map of the government birth registration PDF.
"""

import json
import math
import os
from collections import defaultdict

import fitz
import pdfplumber
from PIL import Image, ImageDraw


PDF_PATH = "uploads/birth_registration_form_v3.pdf"
OUTPUT_DIR = "analysis"


def merge_words_into_lines(words, y_tolerance=3.0, x_tolerance=2.0):
    """Merge pdfplumber words into logical text lines."""
    if not words:
        return []
    # Sort by top then x0
    sorted_words = sorted(words, key=lambda w: (round(w["top"] / y_tolerance), w["x0"]))
    lines = []
    current_line = []
    current_top = None
    for w in sorted_words:
        if current_line and abs(w["top"] - current_top) > y_tolerance:
            # finalize line
            lines.append(finalize_line(current_line))
            current_line = []
        current_line.append(w)
        current_top = w["top"]
    if current_line:
        lines.append(finalize_line(current_line))
    return lines


def finalize_line(words):
    words = sorted(words, key=lambda w: w["x0"])
    text_parts = []
    last_x1 = None
    for w in words:
        # Add space if gap is large
        if last_x1 is not None and (w["x0"] - last_x1) > 3.0:
            text_parts.append(" ")
        text_parts.append(w["text"])
        last_x1 = w["x1"]
    text = "".join(text_parts).strip()
    x0 = min(w["x0"] for w in words)
    x1 = max(w["x1"] for w in words)
    top = min(w["top"] for w in words)
    bottom = max(w["bottom"] for w in words)
    return {
        "text": text,
        "x0": x0,
        "y0": top,
        "x1": x1,
        "y1": bottom,
        "width": x1 - x0,
        "height": bottom - top,
        "word_count": len(words),
        "words": words,
    }


def extract_lines_and_boxes(page):
    """Extract line segments from PyMuPDF drawings and merge into rectangles."""
    drawings = page.get_drawings()
    segments = []
    for d in drawings:
        for item in d.get("items", []):
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                segments.append({
                    "x0": min(p1.x, p2.x),
                    "y0": min(p1.y, p2.y),
                    "x1": max(p1.x, p2.x),
                    "y1": max(p1.y, p2.y),
                })
    return segments


def merge_aligned_segments(segments, tolerance=1.5):
    """Merge collinear horizontal/vertical segments into longer lines."""
    horiz = []
    vert = []
    for s in segments:
        dx = s["x1"] - s["x0"]
        dy = s["y1"] - s["y0"]
        if dx > dy and dy <= tolerance:
            horiz.append(s)
        elif dy > dx and dx <= tolerance:
            vert.append(s)

    def merge_group(segs, group_axis, sort_axis, end_axis):
        """
        group_axis: coordinate used to bucket segments (constant coordinate)
        sort_axis: coordinate used to sort within a group
        end_axis: coordinate used to test continuity
        """
        groups = defaultdict(list)
        for s in segs:
            key = round(s[group_axis] / tolerance)
            groups[key].append(s)
        merged = []
        for key, group in groups.items():
            group.sort(key=lambda s: s[sort_axis])
            cur = dict(group[0])
            for s in group[1:]:
                if s[sort_axis] <= cur[end_axis] + tolerance:
                    cur[end_axis] = max(cur[end_axis], s[end_axis])
                    cur[sort_axis] = min(cur[sort_axis], s[sort_axis])
                else:
                    merged.append(cur)
                    cur = dict(s)
            merged.append(cur)
        return merged

    h_lines = merge_group(horiz, "y0", "x0", "x1")
    v_lines = merge_group(vert, "x0", "y0", "y1")
    return h_lines, v_lines


def detect_rectangles(h_lines, v_lines, tolerance=2.0):
    """Detect rectangles formed by intersecting horizontal and vertical lines."""
    rects = []
    # For each horizontal line, find vertical lines that intersect near both ends
    for h in h_lines:
        y = (h["y0"] + h["y1"]) / 2
        left_candidates = []
        right_candidates = []
        for v in v_lines:
            x = (v["x0"] + v["x1"]) / 2
            if v["y0"] - tolerance <= y <= v["y1"] + tolerance:
                if abs(x - h["x0"]) <= tolerance:
                    left_candidates.append(v)
                elif abs(x - h["x1"]) <= tolerance:
                    right_candidates.append(v)
        for lv in left_candidates:
            for rv in right_candidates:
                x0 = (lv["x0"] + lv["x1"]) / 2
                x1 = (rv["x0"] + rv["x1"]) / 2
                y_top = y
                # Find bottom horizontal line connecting these verticals
                for h2 in h_lines:
                    if h2 is h:
                        continue
                    y2 = (h2["y0"] + h2["y1"]) / 2
                    if y2 <= y_top:
                        continue
                    if (abs(h2["x0"] - x0) <= tolerance and abs(h2["x1"] - x1) <= tolerance
                            and lv["y0"] - tolerance <= y2 <= lv["y1"] + tolerance
                            and rv["y0"] - tolerance <= y2 <= rv["y1"] + tolerance):
                        rects.append({
                            "x0": x0,
                            "y0": y_top,
                            "x1": x1,
                            "y1": y2,
                            "width": x1 - x0,
                            "height": y2 - y_top,
                        })
                        break
    # Remove duplicates
    unique = []
    seen = set()
    for r in rects:
        key = (round(r["x0"]/tolerance), round(r["y0"]/tolerance),
               round(r["x1"]/tolerance), round(r["y1"]/tolerance))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def identify_field_regions(text_lines, rectangles, page_width, page_height):
    """Heuristic field detection: find labeled boxes and blank spaces near labels."""
    fields = []
    # Common Marathi label patterns and their field semantics
    label_map = [
        ("अर्जदाराचे पूर्ण नाव", "applicant_name_marathi"),
        ("पत्ता", "applicant_address"),
        ("दिनांक", "application_date"),
        ("बाळाचे नाव", "child_name_marathi"),
        ("इंग्लिश (कॅपिटल लेटर)", "child_name_english"),
        ("बाळाचे जन्म दिनांक", "child_birth_date"),
        ("वडिलांचे पूर्ण नाव", "father_name_marathi"),
        ("वडिलांचा आधार कार्ड क्रमांक", "father_aadhaar"),
        ("आईचे पूर्ण नाव", "mother_name_marathi"),
        ("आईचा आधार कार्ड क्रमांक", "mother_aadhaar"),
        ("जन्माच्या वेळी आई वडिलांचा पत्ता", "address_at_birth"),
        ("आई वडिलांचा कायमचा पत्ता", "permanent_address"),
    ]

    # Match labels to nearest rectangle below/right of label
    for line in text_lines:
        txt = line["text"]
        for pattern, field_name in label_map:
            if pattern in txt:
                # Find candidate rectangles below or to the right of label
                candidates = []
                for r in rectangles:
                    if r["y0"] > line["y1"] and r["x0"] >= line["x0"] - 20 and r["x1"] <= line["x1"] + 150:
                        dy = r["y0"] - line["y1"]
                        candidates.append((dy, r))
                if candidates:
                    candidates.sort(key=lambda x: x[0])
                    chosen = candidates[0][1]
                    fields.append({
                        "fieldName": field_name,
                        "x": chosen["x0"],
                        "y": chosen["y0"],
                        "width": chosen["width"],
                        "height": chosen["height"],
                        "confidence": 0.75,
                        "source": "label_box_below",
                        "label": txt,
                    })
                else:
                    # Fallback: blank area to the right of label
                    fields.append({
                        "fieldName": field_name,
                        "x": line["x1"] + 10,
                        "y": line["y0"],
                        "width": max(80, page_width - line["x1"] - 60),
                        "height": line["height"] + 4,
                        "confidence": 0.45,
                        "source": "label_fallback",
                        "label": txt,
                    })
    return fields


def create_visualization(page, text_lines, rectangles, fields, output_path):
    """Create a PNG showing detected text lines, rectangles, and fields."""
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    draw = ImageDraw.Draw(img)
    scale = 2.0

    # Draw rectangles (boxes) in green
    for r in rectangles:
        draw.rectangle(
            [r["x0"] * scale, r["y0"] * scale, r["x1"] * scale, r["y1"] * scale],
            outline="green",
            width=1,
        )

    # Draw text lines in blue
    for line in text_lines:
        draw.rectangle(
            [line["x0"] * scale, line["y0"] * scale, line["x1"] * scale, line["y1"] * scale],
            outline="blue",
            width=1,
        )

    # Draw fields in red
    for f in fields:
        draw.rectangle(
            [f["x"] * scale, f["y"] * scale, (f["x"] + f["width"]) * scale, (f["y"] + f["height"]) * scale],
            outline="red",
            width=2,
        )
        draw.text((f["x"] * scale, f["y"] * scale - 10), f["fieldName"], fill="red")

    img.save(output_path)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    doc = fitz.open(PDF_PATH)
    page = doc[0]
    rect = page.rect
    page_width = rect.width
    page_height = rect.height

    # Extract text with pdfplumber
    with pdfplumber.open(PDF_PATH) as pdf:
        plumber_page = pdf.pages[0]
        words = plumber_page.extract_words()
        text_lines = merge_words_into_lines(words, y_tolerance=3.5)

    # Extract lines and boxes
    raw_segments = extract_lines_and_boxes(page)
    h_lines, v_lines = merge_aligned_segments(raw_segments, tolerance=1.5)
    rectangles = detect_rectangles(h_lines, v_lines, tolerance=2.0)

    # Detect fields
    fields = identify_field_regions(text_lines, rectangles, page_width, page_height)

    # Build template analysis JSON
    analysis = {
        "file": PDF_PATH,
        "page_count": doc.page_count,
        "pages": [
            {
                "page_number": 0,
                "width": page_width,
                "height": page_height,
                "rotation": page.rotation,
                "text_lines": text_lines,
                "horizontal_lines": h_lines,
                "vertical_lines": v_lines,
                "rectangles": rectangles,
                "detected_fields": fields,
            }
        ],
    }

    with open(os.path.join(OUTPUT_DIR, "template_analysis.json"), "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    create_visualization(page, text_lines, rectangles, fields, os.path.join(OUTPUT_DIR, "detected_structure.png"))

    doc.close()

    print(f"Analysis saved to {OUTPUT_DIR}/template_analysis.json")
    print(f"Detected {len(text_lines)} text lines, {len(rectangles)} rectangles, {len(fields)} fields")
    print(f"Visualization: {OUTPUT_DIR}/detected_structure.png")


if __name__ == "__main__":
    main()

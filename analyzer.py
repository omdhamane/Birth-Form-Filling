#!/usr/bin/env python3
"""
PHASE 1 & 2: Template analysis + automatic field detection.
Produces template_analysis.json and field_map.json from the actual PDF.
"""

import json
import math
import os
import re
from collections import defaultdict

import fitz
import pdfplumber
from PIL import Image, ImageDraw


PDF_PATH = "uploads/birth_registration_form_v3.pdf"
OUTPUT_DIR = "analysis"
SCALE = 2.0
TOL = 1.5


def normalize_marathi(text):
    return re.sub(r"\s+", "", text)


def merge_words_into_lines(words, y_tolerance=3.5, x_gap_threshold=3.0):
    if not words:
        return []
    words_sorted = sorted(words, key=lambda w: (round(w["top"] / y_tolerance), w["x0"]))
    lines = []
    cur = []
    cur_top = None
    for w in words_sorted:
        if cur and abs(w["top"] - cur_top) > y_tolerance:
            lines.append(finalize_line(cur, x_gap_threshold))
            cur = []
        cur.append(w)
        cur_top = w["top"]
    if cur:
        lines.append(finalize_line(cur, x_gap_threshold))
    return lines


def finalize_line(words, x_gap_threshold):
    words = sorted(words, key=lambda w: w["x0"])
    parts = []
    last_x1 = None
    for w in words:
        if last_x1 is not None and (w["x0"] - last_x1) > x_gap_threshold:
            parts.append(" ")
        parts.append(w["text"])
        last_x1 = w["x1"]
    text = "".join(parts).strip()
    return {
        "text": text,
        "norm": normalize_marathi(text),
        "x0": min(w["x0"] for w in words),
        "y0": min(w["top"] for w in words),
        "x1": max(w["x1"] for w in words),
        "y1": max(w["bottom"] for w in words),
        "width": max(w["x1"] for w in words) - min(w["x0"] for w in words),
        "height": max(w["bottom"] for w in words) - min(w["top"] for w in words),
    }


def extract_all_segments(page):
    segments = []
    for d in page.get_drawings():
        for item in d.get("items", []):
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                segments.append({
                    "x0": float(min(p1.x, p2.x)),
                    "y0": float(min(p1.y, p2.y)),
                    "x1": float(max(p1.x, p2.x)),
                    "y1": float(max(p1.y, p2.y)),
                })
    return segments


def merge_aligned_segments(segments, tolerance=TOL):
    horiz, vert = [], []
    for s in segments:
        dx = s["x1"] - s["x0"]
        dy = s["y1"] - s["y0"]
        if dx >= 0 and dy <= tolerance:
            horiz.append(s)
        elif dy >= 0 and dx <= tolerance:
            vert.append(s)

    def merge_group(segs, group_key, sort_key, end_key):
        groups = defaultdict(list)
        for s in segs:
            groups[round(s[group_key] / tolerance)].append(s)
        merged = []
        for group in groups.values():
            group.sort(key=lambda s: s[sort_key])
            cur = dict(group[0])
            for s in group[1:]:
                if s[sort_key] <= cur[end_key] + tolerance:
                    cur[end_key] = max(cur[end_key], s[end_key])
                    cur[sort_key] = min(cur[sort_key], s[sort_key])
                else:
                    merged.append(cur)
                    cur = dict(s)
            merged.append(cur)
        return merged

    return merge_group(horiz, "y0", "x0", "x1"), merge_group(vert, "x0", "y0", "y1")


def find_table_boundaries(h_lines, v_lines, text_lines, page_width):
    """Determine the table's bounding box, column boundaries, and row boundaries from lines and text."""
    # Identify table vertical range from text labels
    label_patterns = ["बाळाचेनाव", "वडिलांचेपूर्जनाव", "आईचेपूर्जनाव", "न्माच्यावेळी", "आईवडिलांचाकायमचा"]
    label_rows = [line for line in text_lines if any(p in line["norm"] for p in label_patterns)]
    if not label_rows:
        return None, None, None, None, None
    table_top = min(line["y0"] for line in label_rows) - 20
    table_bottom = max(line["y1"] for line in label_rows) + 20

    # Vertical lines within the table region (or crossing it)
    v_in_table = [v for v in v_lines if v["y1"] >= table_top - 5 and v["y0"] <= table_bottom + 5]
    # Cluster vertical lines by x coordinate
    v_sorted = sorted(v_in_table, key=lambda v: (v["x0"] + v["x1"]) / 2)
    col_xs = []
    if v_sorted:
        cur = [v_sorted[0]]
        for v in v_sorted[1:]:
            cx = (v["x0"] + v["x1"]) / 2
            if abs(cx - (cur[-1]["x0"] + cur[-1]["x1"]) / 2) <= 4.0:
                cur.append(v)
            else:
                col_xs.append(sum((vv["x0"] + vv["x1"]) / 2 for vv in cur) / len(cur))
                cur = [v]
        col_xs.append(sum((vv["x0"] + vv["x1"]) / 2 for vv in cur) / len(cur))
    col_xs = sorted(set(round(x, 2) for x in col_xs))
    if not col_xs:
        return None, None, None, None, None
    table_left = col_xs[0]
    table_right = col_xs[-1]

    # Horizontal lines that cross the right two columns (span at least label-col to right edge)
    # We need all such lines, including partial ones that define Marathi/English sub-rows.
    table_h_lines = [h for h in h_lines
                     if h["y1"] >= table_top - 5 and h["y0"] <= table_bottom + 5
                     and h["x1"] - h["x0"] >= 100]
    row_ys = sorted({(h["y0"] + h["y1"]) / 2 for h in table_h_lines})
    # Merge close y values (within 4 pts)
    if not row_ys:
        return None, None, None, None, None
    merged_ys = [row_ys[0]]
    for y in row_ys[1:]:
        if y - merged_ys[-1] > 4.0:
            merged_ys.append(y)
    row_ys = merged_ys

    return table_left, table_right, col_xs, row_ys, table_h_lines


def find_top_fields(text_lines, words, page_width, page_height):
    """Detect free-form fields at the top of the page."""
    fields = []
    # Top fields must be in the top 150 pts of the page and labels should be on the right side
    top_lines = [line for line in text_lines if line["y1"] < 150]
    patterns = [
        ("अर्जदाराचेपूर्जनाव", "applicant_name"),
        ("पत्ता", "applicant_address"),
    ]
    for line in top_lines:
        norm = line["norm"]
        for frag, name in patterns:
            if frag in norm:
                x = line["x1"] + 5
                y = line["y0"] - 1
                width = page_width - x - 45
                height = line["height"] + 6
                fields.append({
                    "fieldName": name,
                    "x": x, "y": y,
                    "width": max(10, width), "height": height,
                    "confidence": 0.8,
                    "source": "top_label_line",
                    "label": line["text"],
                    "page": 0,
                })

    # Date field: use the exact position of the slashes in the date line
    for line in top_lines:
        if "दनांक" in line["norm"]:
            # Find slash word positions in this line
            slash_xs = []
            for w in words:
                if line["y0"] - 3 <= w["top"] <= line["y1"] + 3 and w["text"] == "/":
                    slash_xs.append((w["x0"], w["x1"]))
            if slash_xs:
                # Cover the entire date placeholder: from just after the label text through the year placeholder.
                # The first slash is inside the placeholder; the placeholder starts ~25 pts before it (spaces + first slash).
                x0 = slash_xs[0][0] - 25
                x1 = slash_xs[-1][1] + 30  # cover year placeholder
                y = line["y0"] - 1
                width = max(60, x1 - x0)
                # Keep within page
                width = min(width, page_width - x0 - 20)
                fields.append({
                    "fieldName": "application_date",
                    "x": x0, "y": y,
                    "width": width, "height": line["height"] + 6,
                    "confidence": 0.85,
                    "source": "date_slash_positions",
                    "label": line["text"],
                    "page": 0,
                })
            else:
                # New template: no pre-printed slashes, just a blank line after the label.
                x0 = line["x1"] + 5
                y = line["y0"] - 1
                width = max(80, page_width - x0 - 45)
                fields.append({
                    "fieldName": "application_date",
                    "x": x0, "y": y,
                    "width": width, "height": line["height"] + 6,
                    "confidence": 0.8,
                    "source": "top_date_blank_line",
                    "label": line["text"],
                    "page": 0,
                })
    return fields


def find_table_fields(text_lines, words, col_xs, row_ys, table_left, table_right):
    """Map table labels to the correct fillable cells in the rightmost column."""
    fields = []
    if not col_xs or not row_ys or table_left is None:
        return fields

    # Fillable column: the rightmost internal column boundary to table_right.
    # With col_xs = [left, label_right, sublabel_right, table_right], fillable starts at col_xs[-2].
    fillable_x0 = col_xs[-2] if len(col_xs) >= 3 else col_xs[-1]
    fillable_x1 = table_right

    # Row label patterns
    row_label_patterns = [
        ("बाळाचेनाव", "child_name"),
        ("बाळाचेन्मदनांक", "birth_date"),
        ("वडिलांचेपूर्जनाव", "father_name"),
        ("वडिलांचाआधारकाडिर्जक्रमांक", "father_aadhaar"),
        ("आईचेपूर्जनाव", "mother_name"),
        ("आईचाआधारकाडिर्जक्रमांक", "mother_aadhaar"),
        ("न्माच्यावेळीआईवडिलांचापत्ता", "address_at_birth"),
        ("आईवडिलांचाकायमचापत्ता", "permanent_address"),
    ]

    # Map each row label to the nearest row band
    for line in text_lines:
        norm = line["norm"]
        yc = (line["y0"] + line["y1"]) / 2
        for frag, field_prefix in row_label_patterns:
            if frag in norm:
                # Find row index: yc between row_ys[i] and row_ys[i+1]
                row_idx = None
                for i in range(len(row_ys) - 1):
                    if row_ys[i] - 3 <= yc <= row_ys[i + 1] + 3:
                        row_idx = i
                        break
                if row_idx is None:
                    continue
                y0, y1 = row_ys[row_idx], row_ys[row_idx + 1]
                # For birth date, try to locate the pre-printed slash/year placeholder
                # and restrict the field to that area so the filled date aligns.
                if field_prefix == "birth_date":
                    slash_xs = []
                    for w in words:
                        wyc = (w["top"] + w["bottom"]) / 2
                        if y0 - 3 <= wyc <= y1 + 3 and w["text"] == "/":
                            slash_xs.append((w["x0"], w["x1"]))
                    if slash_xs and fillable_x0 <= slash_xs[0][0] <= fillable_x1:
                        x0 = slash_xs[0][0] - 5
                        x1 = slash_xs[-1][1] + 30
                        fields.append({
                            "fieldName": "birth_date_value",
                            "x": x0,
                            "y": y0 + 2,
                            "width": max(50, min(x1 - x0, fillable_x1 - x0 - 5)),
                            "height": (y1 - y0) - 4,
                            "confidence": 0.92,
                            "source": "table_date_slash_positions",
                            "label": line["text"],
                            "page": 0,
                        })
                        continue
                # Determine if this row has an English counterpart (next row)
                has_english = field_prefix in ("child_name", "father_name", "mother_name")
                english_added = False
                if has_english and row_idx + 1 < len(row_ys) - 1:
                    y0e, y1e = row_ys[row_idx + 1], row_ys[row_idx + 2]
                    # Check if the next row band contains an English sub-label in the middle column
                    mid_x0 = col_xs[1] if len(col_xs) >= 3 else fillable_x0
                    mid_x1 = col_xs[2] if len(col_xs) >= 4 else fillable_x0
                    for tline in text_lines:
                        tyc = (tline["y0"] + tline["y1"]) / 2
                        if y0e - 2 <= tyc <= y1e + 2 and mid_x0 - 5 <= tline["x0"] <= mid_x1 + 5:
                            if "इंग्ल" in tline["text"] or "कॅपटल" in tline["norm"] or "लेटर" in tline["norm"]:
                                english_added = True
                                break
                if has_english and english_added:
                    # Marathi field occupies the current row
                    fields.append({
                        "fieldName": f"{field_prefix}_marathi",
                        "x": fillable_x0 + 4,
                        "y": y0 + 2,
                        "width": fillable_x1 - fillable_x0 - 8,
                        "height": (y1 - y0) - 4,
                        "confidence": 0.9,
                        "source": "table_row_marathi",
                        "label": line["text"],
                        "page": 0,
                    })
                    # English field occupies the next row
                    y0e, y1e = row_ys[row_idx + 1], row_ys[row_idx + 2]
                    fields.append({
                        "fieldName": f"{field_prefix}_english",
                        "x": fillable_x0 + 4,
                        "y": y0e + 2,
                        "width": fillable_x1 - fillable_x0 - 8,
                        "height": (y1e - y0e) - 4,
                        "confidence": 0.88,
                        "source": "table_row_english",
                        "label": line["text"],
                        "page": 0,
                    })
                else:
                    # Single row field
                    fname = f"{field_prefix}_value" if field_prefix == "birth_date" else f"{field_prefix}_marathi"
                    fields.append({
                        "fieldName": fname,
                        "x": fillable_x0 + 4,
                        "y": y0 + 2,
                        "width": fillable_x1 - fillable_x0 - 8,
                        "height": (y1 - y0) - 4,
                        "confidence": 0.9,
                        "source": "table_row_single",
                        "label": line["text"],
                        "page": 0,
                    })
    return fields


def find_word_extent(words, keywords, y_band=None):
    """Return x0, x1 of the first word matching any keyword, within optional y band."""
    for w in words:
        txt = w["text"]
        if y_band and not (y_band[0] <= w["top"] <= y_band[1]):
            continue
        for kw in keywords:
            if kw in txt:
                return float(w["x0"]), float(w["x1"])
    return None, None


def find_inline_affidavit_fields(text_lines, words, page_width):
    """Find inline blanks in the affidavit paragraph using exact word positions."""
    fields = []
    for line in text_lines:
        norm = line["norm"]
        y = (line["y0"] + line["y1"]) / 2
        if 190 < y < 280:
            if ("श्री/श्रीमती/कु" in norm or "श्री/श्रीमती/क" in norm) and "वय" in norm:
                x_honorific_end = find_word_extent(words, ["श्री/श्रीमती/कु"], (line["y0"] - 3, line["y1"] + 3))[1]
                x_age_label_start = find_word_extent(words, ["वय"], (line["y0"] - 3, line["y1"] + 3))[0]
                x_age_label_end = find_word_extent(words, ["वय"], (line["y0"] - 3, line["y1"] + 3))[1]
                x_years_start = find_word_extent(words, ["वर्षे", "र्षे"], (line["y0"] - 3, line["y1"] + 3))[0]
                if x_honorific_end and x_age_label_start and x_honorific_end < x_age_label_start:
                    fields.append({
                        "fieldName": "affidavit_applicant_name",
                        "x": x_honorific_end + 4,
                        "y": line["y0"] - 1,
                        "width": max(20, x_age_label_start - x_honorific_end - 8),
                        "height": line["height"] + 4,
                        "confidence": 0.7,
                        "source": "inline_blank_words",
                        "label": line["text"],
                        "page": 0,
                    })
                if x_age_label_end and x_years_start and x_age_label_end < x_years_start:
                    fields.append({
                        "fieldName": "affidavit_applicant_age",
                        "x": x_age_label_end + 2,
                        "y": line["y0"] - 1,
                        "width": max(15, x_years_start - x_age_label_end - 4),
                        "height": line["height"] + 4,
                        "confidence": 0.65,
                        "source": "inline_blank_words",
                        "label": line["text"],
                        "page": 0,
                    })
            if "बाळाशीनाते" in norm:
                x_relation_label_end = find_word_extent(words, ["नाते"], (line["y0"] - 3, line["y1"] + 3))[1]
                x_next_word_start = find_word_extent(words, ["वनंती", "विनंती"], (line["y0"] - 3, line["y1"] + 3))[0]
                if x_relation_label_end and x_next_word_start and x_relation_label_end < x_next_word_start:
                    fields.append({
                        "fieldName": "affidavit_relationship",
                        "x": x_relation_label_end + 4,
                        "y": line["y0"] - 1,
                        "width": max(20, x_next_word_start - x_relation_label_end - 8),
                        "height": line["height"] + 4,
                        "confidence": 0.7,
                        "source": "inline_blank_words",
                        "label": line["text"],
                        "page": 0,
                    })
            # New template: the affidavit birth date blank is between "दिनांक" and "रोजी" on line 9.
            if "दनांक" in norm and ("रोजी" in norm or "रो" in norm or "ी" in norm):
                x_dinank_end = find_word_extent(words, ["दनांक", "दिनांक"], (line["y0"] - 3, line["y1"] + 3))[1]
                x_roji_start = find_word_extent(words, ["रोजी", "रो"], (line["y0"] - 3, line["y1"] + 3))[0]
                if x_dinank_end and x_roji_start and x_dinank_end < x_roji_start:
                    fields.append({
                        "fieldName": "affidavit_birth_date",
                        "x": x_dinank_end + 4,
                        "y": line["y0"] - 1,
                        "width": max(20, x_roji_start - x_dinank_end - 8),
                        "height": line["height"] + 4,
                        "confidence": 0.65,
                        "source": "inline_blank_words",
                        "label": line["text"],
                        "page": 0,
                    })
            if ("रुग्णाल" in norm or "रुग्णालयाचे" in norm):
                # The hospital name blank is the large empty space on the NEXT line before the word "येथे".
                next_line = None
                y_next = line["y1"] + 5
                for tline in text_lines:
                    if tline["y0"] > line["y1"] and tline["y0"] < line["y1"] + 25:
                        if next_line is None or tline["y0"] < next_line["y0"]:
                            next_line = tline
                if next_line:
                    x_yethe_start = find_word_extent(words, ["येथे"], (next_line["y0"] - 3, next_line["y1"] + 3))[0]
                    if x_yethe_start:
                        fields.append({
                            "fieldName": "affidavit_hospital_name",
                            "x": 42.5,
                            "y": next_line["y0"] - 1,
                            "width": max(50, x_yethe_start - 50),
                            "height": next_line["height"] + 4,
                            "confidence": 0.65,
                            "source": "inline_blank_words",
                            "label": line["text"],
                            "page": 0,
                        })
                    else:
                        # Fallback: full width of next line
                        fields.append({
                            "fieldName": "affidavit_hospital_name",
                            "x": 42.5,
                            "y": next_line["y0"] - 1,
                            "width": max(50, page_width - 90),
                            "height": next_line["height"] + 4,
                            "confidence": 0.55,
                            "source": "inline_blank_words",
                            "label": line["text"],
                            "page": 0,
                        })
                else:
                    x_hospital_label_end = find_word_extent(words, ["नाव"], (line["y0"] - 3, line["y1"] + 3))[1]
                    if x_hospital_label_end:
                        width = max(20, page_width - x_hospital_label_end - 20)
                        if width > 0:
                            fields.append({
                                "fieldName": "affidavit_hospital_name",
                                "x": x_hospital_label_end + 2,
                                "y": line["y0"] - 1,
                                "width": width,
                                "height": line["height"] + 4,
                                "confidence": 0.5,
                                "source": "inline_blank_words",
                                "label": line["text"],
                                "page": 0,
                            })
    return fields


def find_signature_field(text_lines, page_width, page_height):
    for line in text_lines:
        if "सहि" in line["text"] or "सही" in line["text"] or "अर्जदाराचीसह" in line["norm"]:
            if line["y0"] > 600:
                return {
                    "fieldName": "applicant_signature",
                    "x": line["x0"] - 10,
                    "y": line["y1"] + 5,
                    "width": max(10, page_width - line["x0"] - 50),
                    "height": 30,
                    "confidence": 0.65,
                    "source": "signature_area",
                    "label": line["text"],
                    "page": 0,
                }
    return None


def deduplicate_fields(fields):
    by_name = defaultdict(list)
    for f in fields:
        by_name[f["fieldName"]].append(f)
    result = []
    for name, group in by_name.items():
        group.sort(key=lambda f: f["confidence"], reverse=True)
        result.append(group[0])
    return result


def create_visualization(page, text_lines, h_lines, v_lines, col_xs, row_ys, fields, output_path):
    pix = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    draw = ImageDraw.Draw(img)
    s = SCALE

    # Draw grid lines
    for x in col_xs or []:
        draw.line([x * s, 0, x * s, page.rect.height * s], fill="green", width=1)
    for y in row_ys or []:
        draw.line([0, y * s, page.rect.width * s, y * s], fill="green", width=1)

    for line in text_lines:
        draw.rectangle([line["x0"] * s, line["y0"] * s, line["x1"] * s, line["y1"] * s], outline="blue", width=1)

    for h in h_lines:
        draw.line([h["x0"] * s, h["y0"] * s, h["x1"] * s, h["y1"] * s], fill="cyan", width=1)
    for v in v_lines:
        draw.line([v["x0"] * s, v["y0"] * s, v["x1"] * s, v["y1"] * s], fill="magenta", width=1)

    for f in fields:
        draw.rectangle([f["x"] * s, f["y"] * s, (f["x"] + f["width"]) * s, (f["y"] + f["height"]) * s],
                       outline="red", width=2)
        draw.text((f["x"] * s, f["y"] * s - 10), f"{f['fieldName']} ({f['confidence']})", fill="red")

    img.save(output_path)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    doc = fitz.open(PDF_PATH)
    page = doc[0]
    page_width, page_height = page.rect.width, page.rect.height

    with pdfplumber.open(PDF_PATH) as pdf:
        plumber_page = pdf.pages[0]
        words = plumber_page.extract_words()
        text_lines = merge_words_into_lines(words, y_tolerance=3.5)

    raw_segments = extract_all_segments(page)
    h_lines, v_lines = merge_aligned_segments(raw_segments, tolerance=TOL)
    table_left, table_right, col_xs, row_ys, table_h_lines = find_table_boundaries(h_lines, v_lines, text_lines, page_width)

    fields = []
    fields.extend(find_top_fields(text_lines, words, page_width, page_height))
    fields.extend(find_table_fields(text_lines, words, col_xs, row_ys, table_left, table_right))
    fields.extend(find_inline_affidavit_fields(text_lines, words, page_width))
    sig = find_signature_field(text_lines, page_width, page_height)
    if sig:
        fields.append(sig)
    fields = deduplicate_fields(fields)
    fields.sort(key=lambda f: f["y"])

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
                "table_left": table_left,
                "table_right": table_right,
                "table_column_xs": col_xs,
                "table_row_ys": row_ys,
                "table_horizontal_lines": table_h_lines,
            }
        ],
        "detected_fields": fields,
    }

    with open(os.path.join(OUTPUT_DIR, "template_analysis.json"), "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    field_map = {
        "file": PDF_PATH,
        "page_count": doc.page_count,
        "fields": fields,
    }
    with open(os.path.join(OUTPUT_DIR, "field_map.json"), "w", encoding="utf-8") as f:
        json.dump(field_map, f, ensure_ascii=False, indent=2)

    create_visualization(page, text_lines, h_lines, v_lines, col_xs, row_ys, fields,
                         os.path.join(OUTPUT_DIR, "detected_structure.png"))

    doc.close()
    print(f"Wrote {OUTPUT_DIR}/template_analysis.json")
    print(f"Wrote {OUTPUT_DIR}/field_map.json")
    print(f"Table cols: {col_xs}")
    print(f"Table rows: {row_ys}")
    print(f"Fields detected: {len(fields)}")
    for f in fields:
        print(f"  {f['fieldName']:35s} x={f['x']:.1f} y={f['y']:.1f} w={f['width']:.1f} h={f['height']:.1f} conf={f['confidence']}")


if __name__ == "__main__":
    main()

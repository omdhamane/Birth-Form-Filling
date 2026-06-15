#!/usr/bin/env python3
"""
PHASE 5: Text rendering engine.
Shared engine for Marathi + English text, using real font metrics.
"""

import os
import re
from dataclasses import dataclass
from typing import List, Tuple

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


# Register fonts once
FONT_DIR = "fonts"
FONTS = {}


def register_fonts():
    """Register required TTF fonts with reportlab."""
    if FONTS:
        return
    font_files = [
        ("NotoSansDevanagari", "NotoSansDevanagari/NotoSansDevanagari-Regular.ttf", "NotoSansDevanagari/NotoSansDevanagari-Bold.ttf"),
        ("Mukta", "Mukta/Mukta-Regular.ttf", "Mukta/Mukta-Bold.ttf"),
    ]
    for family, regular, bold in font_files:
        reg_path = os.path.join(FONT_DIR, regular)
        bold_path = os.path.join(FONT_DIR, bold)
        if os.path.exists(reg_path):
            pdfmetrics.registerFont(TTFont(f"{family}-Regular", reg_path))
            FONTS[f"{family}-Regular"] = reg_path
        if os.path.exists(bold_path):
            pdfmetrics.registerFont(TTFont(f"{family}-Bold", bold_path))
            FONTS[f"{family}-Bold"] = bold_path
    # Fallback aliases
    if "NotoSansDevanagari-Regular" in FONTS:
        pdfmetrics.registerFontFamily("NotoSansDevanagari", normal="NotoSansDevanagari-Regular", bold="NotoSansDevanagari-Bold")
    if "Mukta-Regular" in FONTS:
        pdfmetrics.registerFontFamily("Mukta", normal="Mukta-Regular", bold="Mukta-Bold")


def get_font_name(language: str, bold: bool = False) -> str:
    """Choose font based on language."""
    if language == "english":
        return "Mukta-Bold" if bold else "Mukta-Regular"
    return "NotoSansDevanagari-Bold" if bold else "NotoSansDevanagari-Regular"


@dataclass
class TextBox:
    text: str
    x: float
    y: float
    width: float
    height: float
    font_name: str
    font_size: float
    align: str = "left"  # left, center, right
    color: Tuple[float, float, float] = (0, 0, 0)
    line_spacing: float = 1.2


def is_marathi(text: str) -> bool:
    """Check if text contains Devanagari characters."""
    return any("\u0900" <= c <= "\u097F" for c in text)


def detect_language(text: str) -> str:
    return "marathi" if is_marathi(text) else "english"


def measure_text(canvas: Canvas, text: str, font_name: str, font_size: float) -> float:
    """Measure text width using the actual font."""
    canvas.setFont(font_name, font_size)
    return canvas.stringWidth(text, font_name, font_size)


def wrap_text(canvas: Canvas, text: str, font_name: str, font_size: float, max_width: float) -> List[str]:
    """Wrap text into lines that fit within max_width using actual font metrics."""
    if not text:
        return []
    canvas.setFont(font_name, font_size)
    words = text.split()
    lines = []
    current = []
    for word in words:
        test = " ".join(current + [word]) if current else word
        width = canvas.stringWidth(test, font_name, font_size)
        if width <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def wrap_text_marathi(canvas: Canvas, text: str, font_name: str, font_size: float, max_width: float) -> List[str]:
    """Wrap Marathi text by character clusters so conjuncts stay together."""
    if not text:
        return []
    canvas.setFont(font_name, font_size)
    # Split on spaces but keep spaces as break opportunities; for Indic scripts we can break at word boundaries.
    words = re.split(r"(\s+)", text)
    words = [w for w in words if w]
    lines = []
    current = []
    current_width = 0.0
    space_width = canvas.stringWidth(" ", font_name, font_size)
    for token in words:
        if token.strip() == "":
            continue
        token_width = canvas.stringWidth(token, font_name, font_size)
        if not current:
            current.append(token)
            current_width = token_width
        elif current_width + space_width + token_width <= max_width:
            current.append(token)
            current_width += space_width + token_width
        else:
            lines.append(" ".join(current))
            current = [token]
            current_width = token_width
    if current:
        lines.append(" ".join(current))
    return lines


def fit_text_in_box(canvas: Canvas, text: str, font_name: str, max_width: float, max_height: float,
                    start_size: float = 12, min_size: float = 7) -> Tuple[float, List[str]]:
    """Find the largest font size and wrapped lines that fit inside a box."""
    if not text:
        return start_size, []
    for size in [start_size, start_size - 1, start_size - 2, min_size]:
        canvas.setFont(font_name, size)
        if is_marathi(text):
            lines = wrap_text_marathi(canvas, text, font_name, size, max_width)
        else:
            lines = wrap_text(canvas, text, font_name, size, max_width)
        line_height = size * 1.2
        total_height = len(lines) * line_height
        if total_height <= max_height:
            return size, lines
    # If nothing fits, return min size with best effort
    canvas.setFont(font_name, min_size)
    lines = wrap_text_marathi(canvas, text, font_name, min_size, max_width) if is_marathi(text) else wrap_text(canvas, text, font_name, min_size, max_width)
    return min_size, lines


def draw_text_box(canvas: Canvas, box: TextBox, debug: bool = False):
    """Draw a single text box with alignment. Returns (font_size, lines)."""
    canvas.setFont(box.font_name, box.font_size)
    canvas.setFillColorRGB(*box.color)

    if is_marathi(box.text):
        lines = wrap_text_marathi(canvas, box.text, box.font_name, box.font_size, box.width)
    else:
        lines = wrap_text(canvas, box.text, box.font_name, box.font_size, box.width)

    line_height = box.font_size * box.line_spacing
    # For vertical alignment we top-align inside the box (PDF coordinates grow upward)
    # y is the top baseline position in this implementation.
    current_y = box.y
    for line in lines:
        line_width = canvas.stringWidth(line, box.font_name, box.font_size)
        if box.align == "center":
            x = box.x + (box.width - line_width) / 2
        elif box.align == "right":
            x = box.x + box.width - line_width
        else:
            x = box.x
        canvas.drawString(x, current_y, line)
        current_y -= line_height
        if current_y < box.y - box.height:
            break

    if debug:
        canvas.setStrokeColorRGB(1, 0, 0)
        canvas.rect(box.x, box.y - box.height, box.width, box.height, stroke=1, fill=0)
    return box.font_size, lines


def render_field(canvas: Canvas, field: dict, value: str, font_size: float = 11, debug: bool = False):
    """Render a field value into its detected box."""
    if not value:
        return None
    lang = detect_language(value)
    font_name = get_font_name(lang)
    # Auto-fit if needed
    size, lines = fit_text_in_box(canvas, value, font_name, field["width"], field["height"], start_size=font_size, min_size=7)
    box = TextBox(
        text=value,
        x=field["x"],
        y=field["y"] + field["height"] - 2,  # baseline near top of box
        width=field["width"],
        height=field["height"],
        font_name=font_name,
        font_size=size,
        align="left",
    )
    # Debug: draw boundary
    if debug:
        canvas.setStrokeColorRGB(1, 0, 0)
        canvas.rect(field["x"], field["y"], field["width"], field["height"], stroke=1, fill=0)
    return draw_text_box(canvas, box, debug=False)


if __name__ == "__main__":
    register_fonts()
    print("Registered fonts:", list(FONTS.keys()))

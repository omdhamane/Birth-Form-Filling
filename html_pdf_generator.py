import os
import uuid
import base64

from flask import render_template
from playwright.sync_api import sync_playwright

from config.pdf_coordinates import FIELD_COORDS


def generate_pdf(data):

    if data is None:
        data = {}

    os.makedirs("output", exist_ok=True)

    fields = []

    for field_name, coord in FIELD_COORDS.items():

        fields.append({
            "x": coord["left"],
            "y": coord["top"],
            "width": coord["width"],
            "height": coord.get("height", 40),
            "value": data.get(field_name, "")
        })

    with open("static/form_bg.png", "rb") as img:
        bg_base64 = base64.b64encode(
            img.read()
        ).decode("utf-8")

    html = render_template(
        "pdf_template.html",
        fields=fields,
        background=bg_base64
    )

    output_name = f"birth_form_{uuid.uuid4().hex[:8]}.pdf"

    output_path = os.path.join(
        "output",
        output_name
    )

    with sync_playwright() as p:

        browser = p.chromium.launch(
    headless=True
)

        page = browser.new_page(
            viewport={
                "width": 1191,
                "height": 1684
            }
        )

        page.set_content(
            html,
            wait_until="networkidle"
        )

        page.pdf(
            path=output_path,
            width="1191px",
            height="1684px",
            print_background=True,
            margin={
                "top": "0",
                "right": "0",
                "bottom": "0",
                "left": "0"
            }
        )

        browser.close()

    return output_name
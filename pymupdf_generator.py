import os
import uuid
import fitz

from config.pdf_coordinates import FIELD_COORDS

TEMPLATE_PDF = "uploads/birth_registration_form_v3.pdf"

FONT_PATH = (
    "fonts/NotoSansDevanagari/"
    "NotoSansDevanagari-Regular.ttf"
)


def generate_pdf(data):

    os.makedirs("output", exist_ok=True)

    pdf = fitz.open(TEMPLATE_PDF)

    page = pdf[0]

    page.insert_font(
        fontname="dev",
        fontfile=FONT_PATH
    )

    for field_name, coord in FIELD_COORDS.items():

        value = str(
            data.get(field_name, "")
        )

        if not value.strip():
            continue

        x = coord["left"]
        y = coord["top"]

        page.insert_text(
            (x, y),
            value,
            fontsize=12,
            fontname="dev"
        )

    output_name = (
        f"birth_form_"
        f"{uuid.uuid4().hex[:8]}.pdf"
    )

    output_path = os.path.join(
        "output",
        output_name
    )

    pdf.save(output_path)
    pdf.close()

    return output_name
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate


def mr_to_en(text):

    if not text:
        return ""

    try:

        result = transliterate(
            text,
            sanscript.DEVANAGARI,
            sanscript.ITRANS
        )

        replacements = {
            "RATNAKARA": "RATNAKAR",
            "PATILA": "PATIL",
            "SHA~NKARA": "SHANKAR",
            "ARJUNA": "ARJUN",
        }

        result = result.upper()

        for k, v in replacements.items():
            result = result.replace(k, v)

        return result

    except Exception:
        return text.upper()

def build_english_fields(data):

    if not data:
        return {}

    if data.get("child_name_marathi"):
        data["child_name_english"] = mr_to_en(
            data["child_name_marathi"]
        )

    if data.get("father_name_marathi"):
        data["father_name_english"] = mr_to_en(
            data["father_name_marathi"]
        )

    if data.get("mother_name_marathi"):
        data["mother_name_english"] = mr_to_en(
            data["mother_name_marathi"]
        )

    return data
def mr_to_en(text):

    manual_names = {
        "रत्नाकर शंकर पाटील":
        "RATNAKAR SHANKAR PATIL",

        "अर्जुन रत्नाकर पाटील":
        "ARJUN RATNAKAR PATIL",

        "सविता रत्नाकर पाटील":
        "SAVITA RATNAKAR PATIL",
    }

    if text in manual_names:
        return manual_names[text]

    return text.upper()
    return data
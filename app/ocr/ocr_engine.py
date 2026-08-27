import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def extract_text_with_details(image_path):
    image = Image.open(image_path)

    data = pytesseract.image_to_data(
        image,
        output_type=pytesseract.Output.DICT
    )

    results = []

    for i in range(len(data["text"])):
        text = data["text"][i].strip()

        try:
            confidence = float(data["conf"][i])
        except ValueError:
            continue

        if text and confidence > 0:
            results.append({
                "text": text,
                "confidence": confidence,
                "x": data["left"][i],
                "y": data["top"][i],
                "width": data["width"][i],
                "height": data["height"][i]
            })

    return results

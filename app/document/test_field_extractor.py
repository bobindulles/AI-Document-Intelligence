from app.ocr.ocr_engine import extract_text_with_details
from app.document.field_extractor import extract_fields


image_path = "data/processed/page_1.png"

ocr_results = extract_text_with_details(image_path)

text = " ".join(
    item["text"]
    for item in ocr_results
)

print("========== OCR TEXT ==========")
print(text)

fields = extract_fields(text)

print("\n========== EXTRACTED FIELDS ==========")

for key, value in fields.items():
    print(f"{key}: {value}")

print("=======================================")
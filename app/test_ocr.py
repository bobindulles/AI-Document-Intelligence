from ocr.ocr_engine import extract_text_with_details

image_path = "data/processed/page_1.png"

results = extract_text_with_details(image_path)

print("========== OCR RESULTS ==========")

for item in results:
    print(
        f"Text: {item['text']} | "
        f"Confidence: {item['confidence']:.2f}% | "
        f"Position: ({item['x']}, {item['y']}) | "
        f"Size: {item['width']}x{item['height']}"
    )

print("=================================")
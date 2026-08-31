from PIL import Image, ImageDraw
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Path to your document image
image_path = "data/processed/page_1.png"

# Open image
image = Image.open(image_path).convert("RGB")

# Get OCR data
data = pytesseract.image_to_data(
    image,
    output_type=pytesseract.Output.DICT
)

# Create drawing object
draw = ImageDraw.Draw(image)

# Go through every detected word
for i in range(len(data["text"])):

    text = data["text"][i].strip()

    try:
        confidence = float(data["conf"][i])
    except ValueError:
        continue

    # Ignore empty or very low-confidence results
    if not text or confidence <= 0:
        continue

    x = data["left"][i]
    y = data["top"][i]
    width = data["width"][i]
    height = data["height"][i]

    # Draw bounding box
    draw.rectangle(
        [x, y, x + width, y + height],
        outline="red",
        width=2
    )

    # Write detected text above the box
    draw.text(
        (x, max(0, y - 15)),
        f"{text} ({confidence:.0f}%)",
        fill="red"
    )


# Save result
output_path = "data/processed/ocr_visualized.png"

image.save(output_path)

print("OCR visualization created successfully!")
print(f"Saved to: {output_path}")
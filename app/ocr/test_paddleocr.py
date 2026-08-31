import json
import fitz
from pathlib import Path
from tkinter import Tk, filedialog

from paddleocr import PaddleOCR
from app.document.field_extractor import extract_fields


# ============================================================
# STEP 1: Ask user to select an invoice
# ============================================================

root = Tk()
root.withdraw()

file_path = filedialog.askopenfilename(
    title="Select Invoice",
    filetypes=[
        ("Invoice files", "*.pdf *.png *.jpg *.jpeg"),
        ("PDF files", "*.pdf"),
        ("Image files", "*.png *.jpg *.jpeg"),
        ("All files", "*.*")
    ]
)

root.destroy()

if not file_path:
    print("No invoice selected.")
    exit()

print("\nSelected invoice:")
print(file_path)


# ============================================================
# STEP 2: Prepare image
# ============================================================

file_path = Path(file_path)

if file_path.suffix.lower() == ".pdf":

    print("\nConverting PDF to image...")

    pdf = fitz.open(str(file_path))

    page = pdf[0]

    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

    # Create processed folder
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Save converted image inside processed/
    image_path = processed_dir / f"{file_path.stem}_page.png"

    pix.save(str(image_path))

    pdf.close()

    print("PDF converted successfully.")
    print("Processed image saved to:", image_path)

    pdf.close()

    print("PDF converted successfully.")

else:

    image_path = file_path


# ============================================================
# STEP 3: Run PaddleOCR
# ============================================================

print("\nRunning PaddleOCR...")

ocr = PaddleOCR(lang="en")

result = ocr.predict(str(image_path))

print("OCR completed.")


# ============================================================
# STEP 4: Extract text + coordinates
# ============================================================

items = []

for res in result:

    data = res.json

    if isinstance(data, str):
        data = json.loads(data)

    ocr_data = data.get("res", data)

    texts = ocr_data.get("rec_texts", [])
    scores = ocr_data.get("rec_scores", [])
    boxes = ocr_data.get("rec_polys", [])

    for i, text in enumerate(texts):

        text = str(text).strip()

        if not text:
            continue

        if i < len(scores):

            confidence = float(scores[i])

            if confidence < 0.30:
                continue

        else:

            confidence = 1.0

        if i >= len(boxes):
            continue

        box = boxes[i]

        items.append(
            {
                "text": text,
                "confidence": confidence,
                "box": box
            }
        )


# ============================================================
# STEP 5: Extract invoice fields
# ============================================================

fields = extract_fields(items)


# ============================================================
# STEP 6: Display extracted values
# ============================================================

print("\n")
print("========================================")
print("       EXTRACTED INVOICE VALUES")
print("========================================")

print(
    "Invoice Number :",
    fields.get("invoice_number")
)

print(
    "Invoice Date   :",
    fields.get("invoice_date")
)

print(
    "VAT Number     :",
    fields.get("vat_number")
)

print(
    "Total Amount   :",
    fields.get("total_amount")
)

print("========================================")
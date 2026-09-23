import json
import fitz
from pathlib import Path
from tkinter import Tk, filedialog

from paddleocr import PaddleOCR

from app.document.document_classifier import classify_document
from app.document.field_extractor import extract_fields
from app.verification.ml_verifier import verify_invoice


# ============================================================
# STEP 1: SELECT DOCUMENT
# ============================================================

def select_document():

    root = Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Select Document",
        filetypes=[
            ("Document files", "*.pdf *.png *.jpg *.jpeg"),
            ("PDF files", "*.pdf"),
            ("Image files", "*.png *.jpg *.jpeg"),
            ("All files", "*.*")
        ]
    )

    root.destroy()

    return file_path


# ============================================================
# STEP 2: PREPARE DOCUMENT IMAGE
# ============================================================

def prepare_image(file_path):

    file_path = Path(file_path)

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    if file_path.suffix.lower() == ".pdf":

        print("\nConverting PDF to image...")

        pdf = fitz.open(str(file_path))

        page = pdf[0]

        pix = page.get_pixmap(
            matrix=fitz.Matrix(2, 2)
        )

        processed_dir = Path("data/processed")

        processed_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        image_path = (
            processed_dir /
            f"{file_path.stem}_page.png"
        )

        pix.save(str(image_path))

        pdf.close()

        print("PDF converted successfully.")
        print(
            "Processed image saved to:",
            image_path
        )

    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    else:

        image_path = file_path

        print("\nUsing image directly:")
        print(image_path)

    return image_path


# ============================================================
# STEP 3: RUN OCR
# ============================================================

def run_ocr(image_path):

    print("\nRunning PaddleOCR...")

    ocr = PaddleOCR(
        lang="en"
    )

    result = ocr.predict(
        str(image_path)
    )

    print("OCR completed.")

    return result


# ============================================================
# STEP 4: EXTRACT OCR ITEMS
# ============================================================

def extract_ocr_items(result):

    items = []

    for res in result:

        data = res.json

        if isinstance(data, str):
            data = json.loads(data)

        ocr_data = data.get(
            "res",
            data
        )

        texts = ocr_data.get(
            "rec_texts",
            []
        )

        scores = ocr_data.get(
            "rec_scores",
            []
        )

        boxes = ocr_data.get(
            "rec_polys",
            []
        )

        for i, text in enumerate(texts):

            text = str(text).strip()

            if not text:
                continue

            # ------------------------------------------------
            # Confidence
            # ------------------------------------------------

            if i < len(scores):

                confidence = float(
                    scores[i]
                )

                if confidence < 0.30:
                    continue

            else:

                confidence = 1.0

            # ------------------------------------------------
            # Bounding box
            # ------------------------------------------------

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

    return items


# ============================================================
# STEP 5: CLASSIFY DOCUMENT
# ============================================================

def classify(items):

    return classify_document(items)


# ============================================================
# STEP 6: EXTRACT DOCUMENT FIELDS
# ============================================================

def extract_document_fields(
    document_type,
    items,
    image_path
):

    # --------------------------------------------------------
    # Invoice
    # --------------------------------------------------------

    if document_type == "invoice":

        return extract_fields(items)

    # --------------------------------------------------------
    # Resume
    # --------------------------------------------------------

    elif document_type == "resume":

        from app.document.resume_extractor import (
            extract_resume
        )

        result = extract_resume(items)

        return result["fields"]

    # --------------------------------------------------------
    # Certificate
    # --------------------------------------------------------

    elif document_type == "certificate":

        from app.document.certificate_extractor import (
            extract_certificate
        )

        result = extract_certificate(
            items,
            image_path=image_path
        )

        return result["fields"]

    return {}


# ============================================================
# STEP 7: DISPLAY EXTRACTED FIELDS
# ============================================================

def display_fields(
    document_type,
    fields
):

    print("\n")
    print("=" * 50)
    print("       EXTRACTED DOCUMENT VALUES")
    print("=" * 50)

    print(
        "Document Type:",
        document_type
    )

    for key, value in fields.items():

        label = key.replace(
            "_",
            " "
        ).title()

        if isinstance(value, list):

            print(
                f"{label}:"
            )

            for item in value:

                print(
                    f"  - {item}"
                )

        else:

            print(
                f"{label} : {value}"
            )

    print("=" * 50)


# ============================================================
# STEP 8: ML / RELIABILITY VERIFICATION
# ============================================================

def run_ml_verification(fields):

    print("\n" + "=" * 50)
    print("       RELIABILITY ANALYSIS")
    print("=" * 50)

    # --------------------------------------------------------
    # Required fields for the new 7-feature ML model
    # --------------------------------------------------------

    required_fields = [
        "qty",
        "amount",
        "invoice_date"
    ]

    missing_fields = []

    for field in required_fields:
        value = fields.get(field)

        if value is None or str(value).strip() == "":
            missing_fields.append(field)

    # --------------------------------------------------------
    # Stop if required invoice fields are missing
    # --------------------------------------------------------

    if missing_fields:

        print("ML verification skipped.")
        print("Missing fields:")

        for field in missing_fields:
            print(f"  - {field}")

        print(
            "\nThe invoice does not currently provide "
            "enough information for ML reliability analysis."
        )

        print("=" * 50)

        return None

    # --------------------------------------------------------
    # Convert amount
    # --------------------------------------------------------

    amount_value = fields["amount"]

    if isinstance(amount_value, str):

        amount_value = (
            amount_value
            .replace("€", "")
            .replace("$", "")
            .replace("£", "")
            .strip()
        )

        # Handle European decimal format
        if "," in amount_value:

            if "." in amount_value:
                amount_value = amount_value.replace(".", "")

            amount_value = amount_value.replace(",", ".")

    try:
        amount_value = float(amount_value)

    except ValueError:

        print(
            f"ML verification skipped. "
            f"Invalid amount: {fields['amount']}"
        )

        print("=" * 50)

        return None

    # --------------------------------------------------------
    # Quantity
    # --------------------------------------------------------

    try:
        qty_value = float(fields["qty"])

    except ValueError:

        print(
            f"ML verification skipped. "
            f"Invalid quantity: {fields['qty']}"
        )

        print("=" * 50)

        return None

    # --------------------------------------------------------
    # Run ML verification
    # --------------------------------------------------------

    try:

        result = verify_invoice(
            qty=qty_value,
            amount=amount_value,
            invoice_date=fields["invoice_date"]
        )

    except Exception as error:

        print("ML verification failed.")
        print(f"Error: {error}")

        print("=" * 50)

        return None

    # --------------------------------------------------------
    # Display result
    # --------------------------------------------------------

    print(f"Status        : {result['status']}")
    print(f"Prediction    : {result['prediction']}")
    print(f"Anomaly Score : {result['anomaly_score']:.6f}")

    print("\nFeatures Used:")

    for key, value in result["features"].items():
        print(f"  {key:22}: {value}")

    print("=" * 50)

    return result

# ============================================================
# STEP 9: MAIN PIPELINE
# ============================================================

def main():

    # --------------------------------------------------------
    # 1. SELECT DOCUMENT
    # --------------------------------------------------------

    file_path = select_document()

    if not file_path:

        print(
            "No document selected."
        )

        return

    print(
        "\nSelected document:"
    )

    print(
        file_path
    )

    # --------------------------------------------------------
    # 2. PREPARE DOCUMENT
    # --------------------------------------------------------

    image_path = prepare_image(
        file_path
    )

    # --------------------------------------------------------
    # 3. RUN OCR
    # --------------------------------------------------------

    ocr_result = run_ocr(
        image_path
    )

    # --------------------------------------------------------
    # 4. EXTRACT OCR ITEMS
    # --------------------------------------------------------

    items = extract_ocr_items(
        ocr_result
    )

    print(
        "\nOCR text regions detected:",
        len(items)
    )

    # --------------------------------------------------------
    # 5. DOCUMENT CLASSIFICATION
    # --------------------------------------------------------

    classification = classify(
        items
    )

    # The classifier returns a dictionary.
    # Extract the actual document type.

    if isinstance(
        classification,
        dict
    ):

        document_type = classification.get(
            "document_type"
        )

        classification_confidence = (
            classification.get(
                "confidence"
            )
        )

        classification_scores = (
            classification.get(
                "scores"
            )
        )

    else:

        document_type = classification

        classification_confidence = None

        classification_scores = None

    # --------------------------------------------------------
    # Display classification
    # --------------------------------------------------------

    print(
        "\n" + "=" * 50
    )

    print(
        "       DOCUMENT CLASSIFICATION"
    )

    print(
        "=" * 50
    )

    print(
        "Document Type :",
        document_type
    )

    if classification_confidence is not None:

        print(
            "Confidence    :",
            classification_confidence
        )

    if classification_scores is not None:

        print(
            "\nScores:"
        )

        for key, value in classification_scores.items():

            print(
                f"  {key}: {value}"
            )

    print(
        "=" * 50
    )

    # --------------------------------------------------------
    # 6. EXTRACT DOCUMENT FIELDS
    # --------------------------------------------------------

    fields = extract_document_fields(
        document_type,
        items,
        image_path
    )

    # --------------------------------------------------------
    # 7. DISPLAY EXTRACTED VALUES
    # --------------------------------------------------------

    display_fields(
        document_type,
        fields
    )

    # --------------------------------------------------------
    # 8. RELIABILITY / ML VERIFICATION
    # --------------------------------------------------------

    run_ml_verification(
        fields
    )

    # --------------------------------------------------------
    # 9. PIPELINE COMPLETED
    # --------------------------------------------------------

    print(
        "\n" + "=" * 50
    )

    print(
        "       PIPELINE COMPLETED"
    )

    print(
        "=" * 50
    )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
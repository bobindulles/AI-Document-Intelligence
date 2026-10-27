import json
import fitz
from pathlib import Path
from tkinter import Tk, filedialog

from paddleocr import PaddleOCR

from app.document.document_classifier import classify_document
from app.document.field_extractor import extract_fields

from app.verification.ml_verifier import verify_invoice
from app.verification.verification_engine import verify_document
from app.verification.certificate_verifier import verify_certificate

from app.forgery.forgery_detector import detect_forgery_signals
from app.forgery.ocr_region_analyzer import analyze_ocr_regions

from app.verification.final_verifier import build_final_result

from app.verification.report_generator import (
    generate_report,
    save_report
)


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
# STEP 8: CALCULATE OCR CONFIDENCE
# ============================================================

def calculate_ocr_confidence(items):

    if not items:
        return 0.0

    confidences = []

    for item in items:

        confidence = item.get(
            "confidence"
        )

        if confidence is not None:

            confidences.append(
                float(confidence)
            )

    if not confidences:
        return 0.0

    return sum(confidences) / len(confidences)


# ============================================================
# STEP 9: INVOICE ML VERIFICATION
# ============================================================

def run_ml_verification(fields):

    print("\n" + "=" * 50)
    print("       RELIABILITY ANALYSIS")
    print("=" * 50)

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

            print(
                f"  - {field}"
            )

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

                amount_value = (
                    amount_value
                    .replace(".", "")
                )

            amount_value = (
                amount_value
                .replace(",", ".")
            )

    try:

        amount_value = float(
            amount_value
        )

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

        qty_value = float(
            fields["qty"]
        )

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

        print(
            "ML verification failed."
        )

        print(
            f"Error: {error}"
        )

        print("=" * 50)

        return None

    # --------------------------------------------------------
    # Display result
    # --------------------------------------------------------

    print(
        f"Status        : {result['status']}"
    )

    print(
        f"Prediction    : {result['prediction']}"
    )

    print(
        f"Anomaly Score : {result['anomaly_score']:.6f}"
    )

    print("\nFeatures Used:")

    for key, value in result["features"].items():

        print(
            f"  {key:22}: {value}"
        )

    print("=" * 50)

    return result


# ============================================================
# STEP 10: CERTIFICATE VERIFICATION
# ============================================================

def run_certificate_verification(
    fields,
    ocr_confidence
):

    print("\n" + "=" * 50)
    print("       CERTIFICATE VERIFICATION")
    print("=" * 50)

    result = verify_certificate(
        fields,
        ocr_confidence=ocr_confidence
    )

    print(
        f"Overall Status    : "
        f"{result['overall_status']}"
    )

    print(
        f"Consistency Score : "
        f"{result['consistency_score']}%"
    )

    print(
        f"Passed Checks     : "
        f"{result['passed_checks']}"
    )

    print(
        f"Warnings          : "
        f"{result['warning_checks']}"
    )

    print(
        f"Failed Checks     : "
        f"{result['failed_checks']}"
    )

    print("\nFindings:")

    for finding in result["findings"]:

        print(
            f"[{finding['status']}] "
            f"{finding['name']} : "
            f"{finding['message']}"
        )

    print("=" * 50)

    return result


# ============================================================
# STEP 11: BUILD GENERIC CERTIFICATE FINAL RESULT
# ============================================================

def build_certificate_final_result(
    certificate_verification,
    region_result,
    forgery_result
):

    status = certificate_verification[
        "overall_status"
    ]

    if (
        region_result["status"]
        != "NO OBVIOUS REGION ANOMALIES"
    ):

        status = "REVIEW RECOMMENDED"

    if (
        forgery_result["status"]
        != "NO OBVIOUS IMAGE ANOMALIES"
    ):

        status = "REVIEW RECOMMENDED"

    # --------------------------------------------------------
    # OCR reliability
    # --------------------------------------------------------

    ocr_confidence = 0.0

    for signal in region_result["signals"]:

        if signal["name"] == "OCR Confidence Distribution":

            message = signal["message"]

            match = None

            import re

            match = re.search(
                r"(\d+\.\d+)",
                message
            )

            if match:

                ocr_confidence = float(
                    match.group(1)
                )

                break

    if ocr_confidence >= 0.90:

        ocr_reliability = "HIGH"

    elif ocr_confidence >= 0.70:

        ocr_reliability = "MEDIUM"

    else:

        ocr_reliability = "LOW"

    # --------------------------------------------------------
    # Explanation
    # --------------------------------------------------------

    explanation = []

    if certificate_verification["failed_checks"] > 0:

        explanation.append(
            "One or more certificate verification checks failed."
        )

    elif certificate_verification["warning_checks"] > 0:

        explanation.append(
            "One or more certificate verification checks require review."
        )

    else:

        explanation.append(
            "Certificate fields passed the available structural checks."
        )

    explanation.append(
        f"OCR reliability is {ocr_reliability.lower()}."
    )

    explanation.append(
        "OCR region analysis was completed."
    )

    explanation.append(
        "Image-level analysis was completed."
    )

    explanation.append(
        "These checks do not prove that the certificate is authentic."
    )

    return {
        "overall_status": status,
        "document_consistency": (
            "PASS"
            if certificate_verification["failed_checks"] == 0
            else "REVIEW REQUIRED"
        ),
        "ocr_reliability": ocr_reliability,
        "visual_analysis": (
            "NO OBVIOUS ANOMALIES DETECTED"
            if forgery_result["status"]
            == "NO OBVIOUS IMAGE ANOMALIES"
            else forgery_result["status"]
        ),
        "ocr_region_analysis": region_result["status"],
        "ml_anomaly": "NOT APPLICABLE",
        "ela_status": next(
            (
                signal["status"]
                for signal in forgery_result["signals"]
                if signal["name"] == "ELA Analysis"
            ),
            "NOT AVAILABLE"
        ),
        "explanation": explanation
    }


# ============================================================
# STEP 12: MAIN PIPELINE
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
    # OCR confidence
    # --------------------------------------------------------

    ocr_confidence = calculate_ocr_confidence(
        items
    )

    # --------------------------------------------------------
    # 7. DOCUMENT-SPECIFIC VERIFICATION
    # --------------------------------------------------------

    ml_result = None
    verification_result = None
    certificate_verification = None

    # ========================================================
    # INVOICE
    # ========================================================

    if document_type == "invoice":

        # ----------------------------------------------------
        # ML anomaly analysis
        # ----------------------------------------------------

        ml_result = run_ml_verification(
            fields
        )

        # ----------------------------------------------------
        # Rule-based verification
        # ----------------------------------------------------

        verification_result = verify_document(
            fields,
            items,
            ml_result
        )

    # ========================================================
    # CERTIFICATE
    # ========================================================

    elif document_type == "certificate":

        certificate_verification = (
            run_certificate_verification(
                fields,
                ocr_confidence
            )
        )

        # Convert certificate result into a generic
        # verification structure for the report.

        verification_result = {
            "overall_status": (
                certificate_verification[
                    "overall_status"
                ]
            ),
            "reliability_score": (
                certificate_verification[
                    "consistency_score"
                ]
            ),
            "ocr_confidence": ocr_confidence,
            "findings": [
                {
                    "status": finding["status"],
                    "field": finding["name"],
                    "message": finding["message"]
                }

                for finding
                in certificate_verification["findings"]
            ]
        }

    # ========================================================
    # RESUME
    # ========================================================

    elif document_type == "resume":

        print(
            "\nResume-specific verification "
            "will be added next."
        )

        verification_result = {
            "overall_status": "REVIEW RECOMMENDED",
            "reliability_score": 0.0,
            "ocr_confidence": ocr_confidence,
            "findings": [
                {
                    "status": "WARNING",
                    "field": "Resume Verification",
                    "message": (
                        "Resume extraction is available, "
                        "but resume-specific verification "
                        "has not yet been implemented."
                    )
                }
            ]
        }

    else:

        verification_result = {
            "overall_status": "REVIEW REQUIRED",
            "reliability_score": 0.0,
            "ocr_confidence": ocr_confidence,
            "findings": [
                {
                    "status": "FAIL",
                    "field": "Document Type",
                    "message": (
                        "Document type is not supported."
                    )
                }
            ]
        }

    # --------------------------------------------------------
    # 8. OCR REGION ANALYSIS
    # --------------------------------------------------------

    region_result = analyze_ocr_regions(
        items
    )

    print(
        "\n" + "=" * 50
    )

    print(
        "       OCR REGION ANALYSIS"
    )

    print(
        "=" * 50
    )

    print(
        f"Status             : "
        f"{region_result['status']}"
    )

    print(
        f"OCR Regions        : "
        f"{region_result['region_count']}"
    )

    print(
        f"Suspicious Regions : "
        f"{region_result['suspicious_regions']}"
    )

    print(
        f"Average Confidence : "
        f"{region_result['average_confidence']}"
    )

    print(
        "\nSignals:"
    )

    for signal in region_result["signals"]:

        print(
            f"[{signal['status']}] "
            f"{signal['name']} : "
            f"{signal['message']}"
        )

    print(
        "=" * 50
    )

    # --------------------------------------------------------
    # 9. FORGERY / IMAGE ANALYSIS
    # --------------------------------------------------------

    forgery_result = detect_forgery_signals(
        image_path
    )

    print(
        "\n" + "=" * 50
    )

    print(
        "       FORGERY ANALYSIS"
    )

    print(
        "=" * 50
    )

    print(
        f"Status : "
        f"{forgery_result['status']}"
    )

    print(
        "\nSignals:"
    )

    for signal in forgery_result["signals"]:

        print(
            f"[{signal['status']}] "
            f"{signal['name']} : "
            f"{signal['message']}"
        )

    print(
        "=" * 50
    )

    # --------------------------------------------------------
    # 10. FINAL VERIFICATION
    # --------------------------------------------------------

    if document_type == "invoice":

        final_result = build_final_result(
            verification_result,
            ml_result,
            forgery_result,
            region_result
        )

    elif document_type == "certificate":

        final_result = build_certificate_final_result(
            certificate_verification,
            region_result,
            forgery_result
        )

    else:

        final_result = {
            "overall_status": "REVIEW RECOMMENDED",
            "document_consistency": "PASS",
            "ocr_reliability": (
                "HIGH"
                if ocr_confidence >= 0.90
                else "MEDIUM"
                if ocr_confidence >= 0.70
                else "LOW"
            ),
            "visual_analysis": (
                "NO OBVIOUS ANOMALIES DETECTED"
                if forgery_result["status"]
                == "NO OBVIOUS IMAGE ANOMALIES"
                else forgery_result["status"]
            ),
            "ocr_region_analysis": (
                region_result["status"]
            ),
            "ml_anomaly": "NOT APPLICABLE",
            "ela_status": next(
                (
                    signal["status"]
                    for signal
                    in forgery_result["signals"]
                    if signal["name"] == "ELA Analysis"
                ),
                "NOT AVAILABLE"
            ),
            "explanation": [
                "Resume extraction is currently available.",
                "Resume-specific verification is under development.",
                "OCR and image analysis were completed.",
                "This result does not establish document authenticity."
            ]
        }

    # --------------------------------------------------------
    # 11. DISPLAY VERIFICATION ANALYSIS
    # --------------------------------------------------------

    print(
        "\n" + "=" * 50
    )

    print(
        "       VERIFICATION ANALYSIS"
    )

    print(
        "=" * 50
    )

    print(
        f"Overall Status    : "
        f"{verification_result['overall_status']}"
    )

    print(
        f"Reliability Score : "
        f"{verification_result['reliability_score']}%"
    )

    print(
        f"OCR Confidence    : "
        f"{verification_result['ocr_confidence']}"
    )

    print(
        "\nFindings:"
    )

    for finding in verification_result["findings"]:

        print(
            f"[{finding['status']}] "
            f"{finding['field']} : "
            f"{finding['message']}"
        )

    print(
        "=" * 50
    )

    # --------------------------------------------------------
    # 12. FINAL VERIFICATION RESULT
    # --------------------------------------------------------

    print(
        "\n"
    )

    print(
        "=" * 50
    )

    print(
        "       FINAL VERIFICATION RESULT"
    )

    print(
        "=" * 50
    )

    print(
        f"Overall Status        : "
        f"{final_result['overall_status']}"
    )

    print(
        f"Document Consistency  : "
        f"{final_result['document_consistency']}"
    )

    print(
        f"OCR Reliability       : "
        f"{final_result['ocr_reliability']}"
    )

    print(
        f"Visual Analysis       : "
        f"{final_result['visual_analysis']}"
    )

    print(
        f"OCR Region Analysis   : "
        f"{final_result['ocr_region_analysis']}"
    )

    print(
        f"ML Anomaly            : "
        f"{final_result['ml_anomaly']}"
    )

    print(
        f"ELA Status            : "
        f"{final_result['ela_status']}"
    )

    print(
        "\nReason:"
    )

    for reason in final_result["explanation"]:

        print(
            f"- {reason}"
        )

    print(
        "\nImportant:"
    )

    print(
        "This result does not establish that the document "
        "is authentic or forged."
    )

    print(
        "=" * 50
    )

    # --------------------------------------------------------
    # 13. DISPLAY EXTRACTED VALUES
    # --------------------------------------------------------

    display_fields(
        document_type,
        fields
    )

    # --------------------------------------------------------
    # 14. SAVE JSON REPORT
    # --------------------------------------------------------

    report = generate_report(
        document_type=document_type,
        fields=fields,
        classification=classification,
        ml_result=ml_result or {},
        region_result=region_result,
        forgery_result=forgery_result,
        verification_result=verification_result,
        final_result=final_result
    )

    report_path = Path(
        "data/processed/verification_report.json"
    )

    save_report(
        report,
        report_path
    )

    print(
        "\nVerification report saved to:"
    )

    print(
        report_path
    )

    # --------------------------------------------------------
    # DEBUG: VERIFY UTF-8 JSON
    # --------------------------------------------------------

    with open(
        report_path,
        "r",
        encoding="utf-8"
    ) as file:

        saved_report = file.read()

    print(
        "\nDEBUG SAVED JSON:"
    )

    start = saved_report.find(
        '"total_amount"'
    )

    if start != -1:

        print(
            saved_report[
                start:start + 80
            ]
        )

    # --------------------------------------------------------
    # PIPELINE COMPLETED
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
import os
import joblib
import numpy as np


MODEL_PATH = "models/invoice_anomaly_model.joblib"


def load_model():
    """
    Load the trained Isolation Forest model.
    """
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"ML model not found: {MODEL_PATH}\n"
            "Run train_anomaly_model.py first."
        )

    return joblib.load(MODEL_PATH)


def calculate_ocr_confidence(items):
    """
    Calculate average OCR confidence from PaddleOCR results.
    """

    if not items:
        return 0.0

    confidences = []

    for item in items:
        confidence = item.get("confidence")

        if confidence is not None:
            try:
                confidences.append(float(confidence))
            except (ValueError, TypeError):
                pass

    if not confidences:
        return 0.0

    return sum(confidences) / len(confidences)


def create_features(fields, items):
    """
    Convert extracted invoice information into
    numerical features for the ML model.

    Features:
    1. Invoice number present
    2. Invoice date present
    3. VAT number present
    4. Total amount present
    5. OCR confidence
    6. Number of extracted fields
    """

    invoice_number = fields.get("invoice_number")
    invoice_date = fields.get("invoice_date")
    vat_number = fields.get("vat_number")
    total_amount = fields.get("total_amount")

    invoice_number_present = int(
        invoice_number is not None and str(invoice_number).strip() != ""
    )

    invoice_date_present = int(
        invoice_date is not None and str(invoice_date).strip() != ""
    )

    vat_number_present = int(
        vat_number is not None and str(vat_number).strip() != ""
    )

    total_amount_present = int(
        total_amount is not None and str(total_amount).strip() != ""
    )

    ocr_confidence = calculate_ocr_confidence(items)

    extracted_field_count = sum([
        invoice_number_present,
        invoice_date_present,
        vat_number_present,
        total_amount_present
    ])

    features = np.array([[
        invoice_number_present,
        invoice_date_present,
        vat_number_present,
        total_amount_present,
        ocr_confidence,
        extracted_field_count
    ]])

    return features


def calculate_anomaly_score(model, features):
    """
    Convert the Isolation Forest decision into
    a simple 0-1 anomaly score.

    Higher score = more suspicious.
    """

    decision_score = model.decision_function(features)[0]

    # Convert decision score into approximately 0-1.
    anomaly_score = 1 / (1 + np.exp(decision_score))

    return float(anomaly_score)


def verify_invoice(fields, items):
    """
    Run the ML verification process on an invoice.
    """

    model = load_model()

    features = create_features(fields, items)

    prediction = model.predict(features)[0]

    anomaly_score = calculate_anomaly_score(
        model,
        features
    )

    if prediction == -1:
        status = "SUSPICIOUS"
    else:
        status = "GENUINE"

    return {
        "status": status,
        "anomaly_score": round(anomaly_score, 4),
        "features": features[0].tolist()
    }
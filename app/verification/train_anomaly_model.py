from pathlib import Path

import joblib
import pandas as pd


# ============================================================
# PATH
# ============================================================

MODEL_PATH = Path("models/invoice_anomaly_model.joblib")


# ============================================================
# FEATURES
# ============================================================

FEATURE_NAMES = [
    "qty",
    "amount",
    "amount_per_quantity",
    "invoice_year",
    "invoice_month",
    "invoice_day",
    "invoice_weekday",
]


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"ML model not found: {MODEL_PATH}"
        )

    saved_data = joblib.load(MODEL_PATH)

    # New model format
    if isinstance(saved_data, dict):
        model = saved_data["model"]
    else:
        model = saved_data

    return model


# ============================================================
# VERIFY INVOICE
# ============================================================

def verify_invoice(
    qty,
    amount,
    invoice_date
):

    model = load_model()

    # --------------------------------------------------------
    # Convert values
    # --------------------------------------------------------

    qty = float(qty)
    amount = float(amount)

    # --------------------------------------------------------
    # Parse invoice date
    # --------------------------------------------------------

    date = pd.to_datetime(
        invoice_date,
        errors="coerce",
        dayfirst=True
    )

    if pd.isna(date):
        raise ValueError(
            f"Invalid invoice date: {invoice_date}"
        )

    # --------------------------------------------------------
    # Calculate features
    # --------------------------------------------------------

    if qty == 0:
        amount_per_quantity = 0.0
    else:
        amount_per_quantity = amount / qty

    features = {
        "qty": qty,
        "amount": amount,
        "amount_per_quantity": amount_per_quantity,
        "invoice_year": date.year,
        "invoice_month": date.month,
        "invoice_day": date.day,
        "invoice_weekday": date.weekday(),
    }

    # --------------------------------------------------------
    # Create DataFrame
    # --------------------------------------------------------

    X = pd.DataFrame(
        [features],
        columns=FEATURE_NAMES
    )

    # --------------------------------------------------------
    # Prediction
    # --------------------------------------------------------

    prediction = int(
        model.predict(X)[0]
    )

    # --------------------------------------------------------
    # Anomaly score
    # --------------------------------------------------------

    anomaly_score = float(
        model.decision_function(X)[0]
    )

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    if prediction == -1:
        status = "SUSPICIOUS"
    else:
        status = "NORMAL"

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {
        "status": status,
        "prediction": prediction,
        "anomaly_score": anomaly_score,
        "features": features,
    }
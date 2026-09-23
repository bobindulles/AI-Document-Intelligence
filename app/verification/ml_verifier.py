import joblib
import numpy as np
import pandas as pd
from pathlib import Path


# ============================================================
# MODEL PATH
# ============================================================

MODEL_PATH = Path("models/invoice_anomaly_model.joblib")


# ============================================================
# FEATURE NAMES
# Must match the features used during training
# ============================================================

FEATURE_NAMES = [
    "qty",
    "amount",
    "amount_per_quantity",
    "invoice_year",
    "invoice_month",
    "invoice_day",
    "invoice_weekday"
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

    # The training script saved:
    # {
    #     "model": model,
    #     "features": features
    # }

    if isinstance(saved_data, dict):
        model = saved_data["model"]
    else:
        model = saved_data

    return model


# ============================================================
# CREATE FEATURES
# ============================================================

def create_features(
    qty,
    amount,
    invoice_date
):

    # --------------------------------------------------------
    # Convert date
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
    # Convert numeric values
    # --------------------------------------------------------

    qty = float(qty)
    amount = float(amount)

    # --------------------------------------------------------
    # Calculate amount per quantity
    # --------------------------------------------------------

    if qty == 0:
        amount_per_quantity = 0.0
    else:
        amount_per_quantity = amount / qty

    # --------------------------------------------------------
    # Create feature vector
    # --------------------------------------------------------

    features = np.array([
        qty,
        amount,
        amount_per_quantity,
        date.year,
        date.month,
        date.day,
        date.weekday()
    ], dtype=float)

    return features


# ============================================================
# VERIFY INVOICE
# ============================================================

def verify_invoice(
    qty,
    amount,
    invoice_date
):

    # --------------------------------------------------------
    # Load trained model
    # --------------------------------------------------------

    model = load_model()

    # --------------------------------------------------------
    # Create features
    # --------------------------------------------------------

    features = create_features(
        qty=qty,
        amount=amount,
        invoice_date=invoice_date
    )

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

    prediction = model.predict(X)[0]

    # --------------------------------------------------------
    # Decision score
    # --------------------------------------------------------

    decision_score = model.decision_function(X)[0]

    # --------------------------------------------------------
    # Isolation Forest:
    #
    # -1 = anomaly
    #  1 = normal
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
        "prediction": int(prediction),
        "anomaly_score": float(decision_score),
        "features": {
            "qty": float(features[0]),
            "amount": float(features[1]),
            "amount_per_quantity": float(features[2]),
            "invoice_year": int(features[3]),
            "invoice_month": int(features[4]),
            "invoice_day": int(features[5]),
            "invoice_weekday": int(features[6])
        }
    }
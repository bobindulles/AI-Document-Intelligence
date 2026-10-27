import re
from datetime import datetime


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


def is_present(value):
    """
    Check whether a field contains a usable value.
    """

    return (
        value is not None
        and str(value).strip() != ""
        and str(value).strip().lower() != "none"
    )


def validate_invoice_number(invoice_number):
    """
    Validate invoice number structure.

    This intentionally uses a flexible rule because
    invoice numbering formats vary between organizations.
    """

    if not is_present(invoice_number):
        return False, "Invoice number is missing."

    value = str(invoice_number).strip()

    if len(value) < 3:
        return False, "Invoice number is too short."

    if not re.search(r"[A-Za-z0-9]", value):
        return False, "Invoice number does not contain valid alphanumeric characters."

    return True, "Invoice number is present and has a valid structure."


def validate_invoice_date(invoice_date):
    """
    Validate the invoice date.
    """

    if not is_present(invoice_date):
        return False, "Invoice date is missing."

    value = str(invoice_date).strip()

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%m/%d/%Y"
    ]

    for date_format in formats:

        try:
            datetime.strptime(value, date_format)
            return True, "Invoice date is valid."

        except ValueError:
            continue

    return False, f"Invoice date format could not be validated: {value}"


def validate_vat_number(vat_number):
    """
    Perform a basic VAT number structure check.

    This is not a country-specific VAT verification service.
    """

    if not is_present(vat_number):
        return False, "VAT number is missing."

    value = str(vat_number).strip()

    normalized = re.sub(r"[\s.\-]", "", value)

    if len(normalized) < 8:
        return False, "VAT number appears too short."

    if not re.search(r"\d", normalized):
        return False, "VAT number does not contain digits."

    return True, "VAT number has a valid-looking structure."


def parse_numeric(value):
    """
    Convert common OCR monetary/quantity formats into float.
    """

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip()

    if not value:
        return None

    value = (
        value
        .replace("€", "")
        .replace("$", "")
        .replace("£", "")
        .replace("₹", "")
        .strip()
    )

    try:

        # European format:
        # 1.234,56 -> 1234.56

        if "," in value and "." in value:

            if value.rfind(",") > value.rfind("."):
                value = value.replace(".", "")
                value = value.replace(",", ".")

            else:
                value = value.replace(",", "")

        elif "," in value:

            value = value.replace(",", ".")

        return float(value)

    except ValueError:
        return None


def validate_quantity(quantity):
    """
    Validate invoice quantity.
    """

    value = parse_numeric(quantity)

    if value is None:
        return False, "Quantity could not be interpreted as a number."

    if value <= 0:
        return False, "Quantity must be greater than zero."

    return True, "Quantity is valid."


def validate_amount(amount):
    """
    Validate invoice amount.
    """

    value = parse_numeric(amount)

    if value is None:
        return False, "Amount could not be interpreted as a number."

    if value < 0:
        return False, "Amount cannot be negative."

    return True, "Amount is valid."


def run_consistency_checks(fields):
    """
    Perform consistency checks between extracted invoice fields.
    """

    checks = []

    quantity = parse_numeric(fields.get("qty"))
    amount = parse_numeric(fields.get("amount"))
    total_amount = parse_numeric(fields.get("total_amount"))

    # Quantity check
    if quantity is not None:

        if quantity > 0:

            checks.append({
                "name": "Quantity",
                "status": "PASS",
                "message": "Quantity is greater than zero."
            })

        else:

            checks.append({
                "name": "Quantity",
                "status": "FAIL",
                "message": "Quantity must be greater than zero."
            })

    # Amount check
    if amount is not None:

        if amount >= 0:

            checks.append({
                "name": "Amount",
                "status": "PASS",
                "message": "Amount is a valid non-negative value."
            })

        else:

            checks.append({
                "name": "Amount",
                "status": "FAIL",
                "message": "Amount cannot be negative."
            })

    # Total amount comparison
    #
    # The current extractor may provide both:
    # amount       -> line/item amount
    # total_amount -> invoice total
    #
    # They should not be assumed equal because an invoice
    # may contain tax, discounts, shipping, or multiple items.

    if amount is not None and total_amount is not None:

        if total_amount >= amount:

            checks.append({
                "name": "Amount vs Total",
                "status": "PASS",
                "message": "Total amount is not lower than the extracted amount."
            })

        else:

            checks.append({
                "name": "Amount vs Total",
                "status": "WARNING",
                "message": "Total amount is lower than the extracted amount."
            })

    return checks


def verify_document(fields, items, ml_result=None):
    """
    Perform document-level verification.

    This engine performs:
    - Field presence checks
    - Format validation
    - Basic consistency checks
    - OCR confidence analysis
    - Integration of ML anomaly results
    """

    findings = []
    passed_checks = 0
    failed_checks = 0
    warning_checks = 0

    # --------------------------------------------------
    # FIELD PRESENCE
    # --------------------------------------------------

    required_fields = [
        ("invoice_number", "Invoice Number"),
        ("invoice_date", "Invoice Date"),
        ("vat_number", "VAT Number"),
        ("total_amount", "Total Amount")
    ]

    for field, label in required_fields:

        if is_present(fields.get(field)):

            findings.append({
                "category": "Field Presence",
                "field": label,
                "status": "PASS",
                "message": f"{label} was detected."
            })

            passed_checks += 1

        else:

            findings.append({
                "category": "Field Presence",
                "field": label,
                "status": "WARNING",
                "message": f"{label} was not detected."
            })

            warning_checks += 1

    # --------------------------------------------------
    # INVOICE NUMBER
    # --------------------------------------------------

    valid, message = validate_invoice_number(
        fields.get("invoice_number")
    )

    findings.append({
        "category": "Format Validation",
        "field": "Invoice Number",
        "status": "PASS" if valid else "WARNING",
        "message": message
    })

    if valid:
        passed_checks += 1
    else:
        warning_checks += 1

    # --------------------------------------------------
    # DATE
    # --------------------------------------------------

    valid, message = validate_invoice_date(
        fields.get("invoice_date")
    )

    findings.append({
        "category": "Format Validation",
        "field": "Invoice Date",
        "status": "PASS" if valid else "WARNING",
        "message": message
    })

    if valid:
        passed_checks += 1
    else:
        warning_checks += 1

    # --------------------------------------------------
    # VAT
    # --------------------------------------------------

    valid, message = validate_vat_number(
        fields.get("vat_number")
    )

    findings.append({
        "category": "Format Validation",
        "field": "VAT Number",
        "status": "PASS" if valid else "WARNING",
        "message": message
    })

    if valid:
        passed_checks += 1
    else:
        warning_checks += 1

    # --------------------------------------------------
    # QUANTITY
    # --------------------------------------------------

    if is_present(fields.get("qty")):

        valid, message = validate_quantity(
            fields.get("qty")
        )

        findings.append({
            "category": "Format Validation",
            "field": "Quantity",
            "status": "PASS" if valid else "FAIL",
            "message": message
        })

        if valid:
            passed_checks += 1
        else:
            failed_checks += 1

    # --------------------------------------------------
    # AMOUNT
    # --------------------------------------------------

    if is_present(fields.get("amount")):

        valid, message = validate_amount(
            fields.get("amount")
        )

        findings.append({
            "category": "Format Validation",
            "field": "Amount",
            "status": "PASS" if valid else "FAIL",
            "message": message
        })

        if valid:
            passed_checks += 1
        else:
            failed_checks += 1

    # --------------------------------------------------
    # CONSISTENCY CHECKS
    # --------------------------------------------------

    consistency_checks = run_consistency_checks(fields)

    for check in consistency_checks:

        findings.append({
            "category": "Consistency",
            "field": check["name"],
            "status": check["status"],
            "message": check["message"]
        })

        if check["status"] == "PASS":
            passed_checks += 1

        elif check["status"] == "FAIL":
            failed_checks += 1

        else:
            warning_checks += 1

    # --------------------------------------------------
    # OCR CONFIDENCE
    # --------------------------------------------------

    ocr_confidence = calculate_ocr_confidence(items)

    if ocr_confidence >= 0.90:

        ocr_status = "PASS"
        ocr_message = "OCR confidence is high."
        passed_checks += 1

    elif ocr_confidence >= 0.70:

        ocr_status = "WARNING"
        ocr_message = "OCR confidence is moderate."
        warning_checks += 1

    else:

        ocr_status = "WARNING"
        ocr_message = "OCR confidence is low."
        warning_checks += 1

    findings.append({
        "category": "OCR",
        "field": "OCR Confidence",
        "status": ocr_status,
        "message": ocr_message
    })

    # --------------------------------------------------
    # ML RESULT
    # --------------------------------------------------

    ml_status = None
    ml_anomaly_score = None

    if ml_result is not None:

        ml_status = ml_result.get("status")
        ml_anomaly_score = ml_result.get("anomaly_score")

        if ml_status == "SUSPICIOUS":

            findings.append({
                "category": "ML Anomaly Detection",
                "field": "Anomaly Status",
                "status": "WARNING",
                "message": (
                    "The transaction was identified as anomalous "
                    "relative to the training dataset."
                )
            })

            warning_checks += 1

        else:

            findings.append({
                "category": "ML Anomaly Detection",
                "field": "Anomaly Status",
                "status": "PASS",
                "message": (
                    "The transaction was not identified as anomalous "
                    "relative to the training dataset."
                )
            })

            passed_checks += 1

    # --------------------------------------------------
    # OVERALL RESULT
    # --------------------------------------------------

    total_checks = (
        passed_checks
        + failed_checks
        + warning_checks
    )

    if total_checks == 0:

        reliability_score = 0.0

    else:

        reliability_score = (
            passed_checks / total_checks
        ) * 100

    if failed_checks > 0:

        overall_status = "REVIEW REQUIRED"

    elif warning_checks > 0:

        overall_status = "REVIEW RECOMMENDED"

    else:

        overall_status = "CONSISTENT"

    return {
        "overall_status": overall_status,
        "reliability_score": round(reliability_score, 2),
        "ocr_confidence": round(ocr_confidence, 4),
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "warning_checks": warning_checks,
        "ml_status": ml_status,
        "ml_anomaly_score": ml_anomaly_score,
        "findings": findings
    }
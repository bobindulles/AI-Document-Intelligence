# ============================================================
# FINAL VERIFICATION RESULT
# ============================================================


def build_final_result(
    verification_result,
    ml_result,
    forgery_result,
    region_result
):
    """
    Combine document verification, ML anomaly detection,
    forgery analysis and OCR region analysis into one
    final result.
    """

    # --------------------------------------------------------
    # VERIFICATION STATUS
    # --------------------------------------------------------

    verification_status = verification_result.get(
        "overall_status",
        "UNKNOWN"
    )

    if verification_status == "REVIEW REQUIRED":
        document_consistency = "REVIEW REQUIRED"

    elif verification_status == "REVIEW RECOMMENDED":
        document_consistency = "REVIEW RECOMMENDED"

    elif verification_status == "CONSISTENT":
        document_consistency = "PASS"

    else:
        document_consistency = "UNKNOWN"

    # --------------------------------------------------------
    # OCR RELIABILITY
    # --------------------------------------------------------

    ocr_confidence = verification_result.get(
        "ocr_confidence"
    )

    if ocr_confidence is None:
        ocr_reliability = "NOT AVAILABLE"

    elif ocr_confidence >= 0.90:
        ocr_reliability = "HIGH"

    elif ocr_confidence >= 0.70:
        ocr_reliability = "MEDIUM"

    else:
        ocr_reliability = "LOW"

    # --------------------------------------------------------
    # OCR REGION ANALYSIS
    # --------------------------------------------------------

    region_status = region_result.get(
        "status",
        "UNKNOWN"
    )

    if "NO OBVIOUS" in region_status:
        ocr_region_analysis = "NO OBVIOUS REGION ANOMALIES"

    else:
        ocr_region_analysis = region_status

    # --------------------------------------------------------
    # FORGERY / IMAGE ANALYSIS
    # --------------------------------------------------------

    forgery_status = forgery_result.get(
        "status",
        "UNKNOWN"
    )

    if forgery_status == "NO OBVIOUS IMAGE ANOMALIES":
        visual_analysis = "NO OBVIOUS ANOMALIES DETECTED"

    else:
        visual_analysis = forgery_status

    # --------------------------------------------------------
    # ML ANALYSIS
    # --------------------------------------------------------

    if ml_result:

        ml_status = ml_result.get(
            "status",
            "NOT AVAILABLE"
        )

        if ml_status == "SUSPICIOUS":
            ml_anomaly = "SUSPICIOUS"

        elif ml_status == "NORMAL":
            ml_anomaly = "NORMAL"

        else:
            ml_anomaly = ml_status

    else:
        ml_anomaly = "NOT APPLICABLE"

    # --------------------------------------------------------
    # ELA STATUS
    # --------------------------------------------------------

    ela_status = "NOT AVAILABLE"

    signals = forgery_result.get(
        "signals",
        []
    )

    for signal in signals:

        if signal.get("name") == "ELA Analysis":

            ela_status = signal.get(
                "status",
                "UNKNOWN"
            )

            break

    # --------------------------------------------------------
    # OVERALL STATUS
    # --------------------------------------------------------

    if document_consistency == "REVIEW REQUIRED":

        overall_status = "REVIEW REQUIRED"

    elif (
        document_consistency == "REVIEW RECOMMENDED"
        or ml_anomaly == "SUSPICIOUS"
        or visual_analysis != "NO OBVIOUS ANOMALIES DETECTED"
        or ocr_region_analysis != "NO OBVIOUS REGION ANOMALIES"
    ):

        overall_status = "REVIEW RECOMMENDED"

    else:

        overall_status = "CONSISTENT"

    # --------------------------------------------------------
    # EXPLANATION
    # --------------------------------------------------------

    explanation = []

    if document_consistency == "REVIEW REQUIRED":

        explanation.append(
            "One or more document verification checks failed."
        )

    elif document_consistency == "REVIEW RECOMMENDED":

        explanation.append(
            "Some document verification checks require review."
        )

    else:

        explanation.append(
            "Document consistency checks passed."
        )

    if ocr_reliability == "HIGH":

        explanation.append(
            "OCR reliability is high."
        )

    elif ocr_reliability == "MEDIUM":

        explanation.append(
            "OCR reliability is moderate."
        )

    elif ocr_reliability == "LOW":

        explanation.append(
            "OCR reliability is low."
        )

    if ocr_region_analysis == "NO OBVIOUS REGION ANOMALIES":

        explanation.append(
            "OCR region analysis was completed with no "
            "obvious region anomalies."
        )

    else:

        explanation.append(
            "OCR region analysis identified signals "
            "that may require review."
        )

    if visual_analysis == "NO OBVIOUS ANOMALIES DETECTED":

        explanation.append(
            "No obvious image-level anomalies were detected."
        )

    else:

        explanation.append(
            "Image-level analysis identified signals "
            "that may require review."
        )

    if ml_anomaly == "SUSPICIOUS":

        explanation.append(
            "The transaction characteristics are unusual "
            "relative to the training dataset."
        )

    elif ml_anomaly == "NORMAL":

        explanation.append(
            "The transaction characteristics are "
            "consistent with the training dataset."
        )

    return {
        "overall_status": overall_status,
        "document_consistency": document_consistency,
        "ocr_reliability": ocr_reliability,
        "visual_analysis": visual_analysis,
        "ocr_region_analysis": ocr_region_analysis,
        "ml_anomaly": ml_anomaly,
        "ela_status": ela_status,
        "explanation": explanation
    }
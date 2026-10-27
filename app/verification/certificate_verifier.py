import re


# ============================================================
# CERTIFICATE VERIFICATION
# ============================================================

def is_present(value):
    """
    Check whether a field contains meaningful information.
    """
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    return True


def validate_certificate_title(title):
    """
    Validate that a certificate title was detected.
    """

    if not is_present(title):
        return {
            "status": "FAIL",
            "name": "Certificate Title",
            "message": "Certificate title was not detected."
        }

    return {
        "status": "PASS",
        "name": "Certificate Title",
        "message": "Certificate title was detected."
    }


def validate_organization(organization):
    if not is_present(organization):
        return {
            "status": "WARNING",
            "name": "Organization",
            "message": "Issuing organization was not detected."
        }

    return {
        "status": "PASS",
        "name": "Organization",
        "message": "Issuing organization was detected."
    }

def validate_recipient(recipient):
    """
    Validate certificate recipient.
    """

    if not is_present(recipient):
        return {
            "status": "FAIL",
            "name": "Recipient",
            "message": "Certificate recipient was not detected."
        }

    return {
        "status": "PASS",
        "name": "Recipient",
        "message": "Certificate recipient was detected."
    }


def validate_course(course):
    """
    Validate course or certification name.
    """

    if not is_present(course):
        return {
            "status": "WARNING",
            "name": "Course",
            "message": "Course or certification name was not detected."
        }

    return {
        "status": "PASS",
        "name": "Course",
        "message": "Course or certification name was detected."
    }


def validate_certificate_id(certificate_id):
    """
    Validate certificate ID / verification code.
    """

    if not is_present(certificate_id):
        return {
            "status": "WARNING",
            "name": "Certificate ID",
            "message": "Certificate ID or verification code was not detected."
        }

    certificate_id = str(certificate_id).strip()

    if len(certificate_id) < 4:
        return {
            "status": "WARNING",
            "name": "Certificate ID",
            "message": "Certificate ID was detected but appears unusually short."
        }

    return {
        "status": "PASS",
        "name": "Certificate ID",
        "message": "Certificate ID or verification code has a valid-looking structure."
    }


def validate_verification_url(url):
    """
    Validate a QR/verification URL.
    """

    if not is_present(url):
        return {
            "status": "WARNING",
            "name": "Verification URL",
            "message": "No certificate verification URL was detected."
        }

    url = str(url).strip()

    if not re.match(r"^https?://", url, re.IGNORECASE):
        return {
            "status": "WARNING",
            "name": "Verification URL",
            "message": "Verification URL was detected but does not have a valid HTTP/HTTPS structure."
        }

    return {
        "status": "PASS",
        "name": "Verification URL",
        "message": "Certificate verification URL was detected."
    }


def validate_signature(signature):
    """
    Validate signature information.
    """

    if not is_present(signature):
        return {
            "status": "WARNING",
            "name": "Signature",
            "message": "Signature information was not detected."
        }

    return {
        "status": "PASS",
        "name": "Signature",
        "message": "Signature information was detected."
    }


# ============================================================
# MAIN CERTIFICATE VERIFICATION
# ============================================================

def verify_certificate(fields, ocr_confidence=None):

    findings = []

    title = fields.get("certificate_name")

    organization = fields.get("organization")

    recipient = fields.get("recipient_name")

    course = fields.get("course_name")

    certificate_id = fields.get("certificate_id")

    verification_url = fields.get("verification_url")

    signature = fields.get("signatory_role")

    findings.append(
        validate_certificate_title(title)
    )

    findings.append(
        validate_organization(organization)
    )

    findings.append(
        validate_recipient(recipient)
    )

    findings.append(
        validate_course(course)
    )

    findings.append(
        validate_certificate_id(certificate_id)
    )

    findings.append(
        validate_verification_url(verification_url)
    )

    findings.append(
        validate_signature(signature)
    )

    if ocr_confidence is not None:

        if ocr_confidence >= 0.90:

            findings.append({
                "status": "PASS",
                "name": "OCR Confidence",
                "message": (
                    f"OCR confidence is high "
                    f"({ocr_confidence:.4f})."
                )
            })

        elif ocr_confidence >= 0.70:

            findings.append({
                "status": "WARNING",
                "name": "OCR Confidence",
                "message": (
                    f"OCR confidence is moderate "
                    f"({ocr_confidence:.4f})."
                )
            })

        else:

            findings.append({
                "status": "FAIL",
                "name": "OCR Confidence",
                "message": (
                    f"OCR confidence is low "
                    f"({ocr_confidence:.4f})."
                )
            })

    failed = sum(
        1 for finding in findings
        if finding["status"] == "FAIL"
    )

    warnings = sum(
        1 for finding in findings
        if finding["status"] == "WARNING"
    )

    passed = sum(
        1 for finding in findings
        if finding["status"] == "PASS"
    )

    total = len(findings)

    consistency_score = (
        (passed / total) * 100
        if total > 0
        else 0.0
    )

    if failed > 0:
        overall_status = "REVIEW REQUIRED"

    elif warnings > 0:
        overall_status = "REVIEW RECOMMENDED"

    else:
        overall_status = "CONSISTENT"

    return {
        "overall_status": overall_status,
        "consistency_score": round(
            consistency_score,
            2
        ),
        "passed_checks": passed,
        "warning_checks": warnings,
        "failed_checks": failed,
        "total_checks": total,
        "findings": findings
    }
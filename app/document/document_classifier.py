import re


def classify_document(items):

    text = " ".join(
        item["text"] for item in items
    ).lower()

    text = re.sub(r"\s+", " ", text)

    scores = {
        "invoice": 0,
        "resume": 0,
        "certificate": 0
    }

    invoice_words = [
        "invoice",
        "invoice number",
        "invoice date",
        "vat",
        "subtotal",
        "total",
        "amount due",
        "bill to",
        "payment terms"
    ]

    resume_words = [
        "resume",
        "curriculum vitae",
        "experience",
        "work experience",
        "education",
        "skills",
        "projects",
        "employment",
        "technical skills"
    ]

    certificate_words = [
        "certificate",
        "certification",
        "this is to certify",
        "awarded to",
        "presented to",
        "certificate id",
        "credential",
        "successfully completed"
    ]

    for word in invoice_words:
        if word in text:
            scores["invoice"] += 1

    for word in resume_words:
        if word in text:
            scores["resume"] += 1

    for word in certificate_words:
        if word in text:
            scores["certificate"] += 1

    document_type = max(
        scores,
        key=scores.get
    )

    if scores[document_type] == 0:
        document_type = "unknown"
        confidence = 0
    else:
        total = sum(scores.values())
        confidence = scores[document_type] / total

    return {
        "document_type": document_type,
        "confidence": round(confidence, 2),
        "scores": scores
    }
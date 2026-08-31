import re
from datetime import datetime


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):
    if text is None:
        return ""

    text = str(text).strip()

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text


def normalize_label(text):
    text = clean_text(text).lower()

    # OCR sometimes produces punctuation between words
    text = re.sub(r"[^a-z0-9]+", " ", text)

    return text.strip()


# ============================================================
# GEOMETRY
# ============================================================

def get_box_info(box):
    """
    Supports PaddleOCR polygon format:

    [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    """

    try:
        xs = [float(p[0]) for p in box]
        ys = [float(p[1]) for p in box]

        return {
            "left": min(xs),
            "right": max(xs),
            "top": min(ys),
            "bottom": max(ys),
            "center_x": (min(xs) + max(xs)) / 2,
            "center_y": (min(ys) + max(ys)) / 2,
            "width": max(xs) - min(xs),
            "height": max(ys) - min(ys),
        }

    except Exception:
        return None


def prepare_items(items):
    prepared = []

    for item in items:

        text = clean_text(item.get("text", ""))
        box = item.get("box")

        if not text or not box:
            continue

        geometry = get_box_info(box)

        if geometry is None:
            continue

        prepared.append(
            {
                "text": text,
                "normalized": normalize_label(text),
                "confidence": float(item.get("confidence", 1.0)),
                "box": box,
                **geometry,
            }
        )

    return prepared


# ============================================================
# LABEL MATCHING
# ============================================================

def contains_any_label(text, labels):
    normalized = normalize_label(text)

    for label in labels:

        label_normalized = normalize_label(label)

        if label_normalized in normalized:
            return True

    return False


# ============================================================
# INVOICE NUMBER
# ============================================================

INVOICE_NUMBER_LABELS = [
    "invoice number",
    "invoice no",
    "invoice no.",
    "invoice #",
    "invoice id",
    "invoice reference",
    "invoice ref",
    "document number",
    "document no",
    "document id",
    "reference number",
]


def looks_like_invoice_number(text):
    text = clean_text(text)

    if not text:
        return False

    normalized = normalize_label(text)

    # Reject obvious non-values
    if normalized in {
        "invoice",
        "number",
        "invoice number",
        "description",
        "date",
        "total",
        "vat",
    }:
        return False

    # Must contain at least one digit
    if not re.search(r"\d", text):
        return False

    # Avoid dates
    if looks_like_date(text):
        return False

    # Avoid pure monetary values
    if looks_like_amount(text):
        return False

    # Reasonable invoice-number characters
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ./_-]{2,40}", text):
        return True

    return False


# ============================================================
# DATE
# ============================================================

DATE_LABELS = [
    "invoice date",
    "invoice issued",
    "issued date",
    "date issued",
    "issue date",
    "date",
]


def looks_like_date(text):
    text = clean_text(text)

    patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
        r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b",
        r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
        r"\b[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}\b",
    ]

    return any(re.search(pattern, text) for pattern in patterns)


def extract_date_from_text(text):
    text = clean_text(text)

    patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
        r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b",
        r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
        r"\b[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}\b",
    ]

    for pattern in patterns:

        match = re.search(pattern, text)

        if match:
            return match.group(0)

    return None


# ============================================================
# VAT
# ============================================================

VAT_LABELS = [
    "vat number",
    "vat no",
    "vat no.",
    "vat id",
    "vat identification number",
    "tax id",
    "tax number",
    "tax identification number",
    "your vat number",
]


def looks_like_vat(text):
    text = clean_text(text)

    # Remove common OCR separators
    compact = re.sub(r"[\s.\-:/]", "", text).upper()

    # Remove obvious label words if OCR joined them
    compact = re.sub(
        r"^(VAT|NUMBER|NO|ID|TAX)+",
        "",
        compact
    )

    # Country-code VAT
    if re.fullmatch(
        r"[A-Z]{2}[A-Z0-9]{6,14}",
        compact
    ):
        return True

    # Numeric VAT
    if re.fullmatch(r"\d{8,15}", compact):
        return True

    return False


# ============================================================
# AMOUNT
# ============================================================

AMOUNT_LABELS = [
    "total",
    "total amount",
    "grand total",
    "invoice total",
    "total due",
    "amount due",
    "amount payable",
    "total payable",
    "balance due",
    "balance payable",
    "net payable",
    "payable",
    "amount to pay",
    "total incl vat",
    "total including vat",
    "total including tax",
]


NEGATIVE_AMOUNT_LABELS = [
    "subtotal",
    "sub total",
    "vat",
    "tax",
    "tax amount",
    "unit price",
    "price",
    "quantity",
    "discount",
    "shipping",
    "delivery",
    "net amount",
]


def looks_like_amount(text):
    text = clean_text(text)

    if not text:
        return False

    # Remove currency symbols and spaces
    cleaned = re.sub(
        r"[€$£¥₹]",
        "",
        text
    )

    cleaned = cleaned.replace(" ", "")

    # Examples:
    # 181.50
    # 181,50
    # 1,181.50
    # 1.181,50
    # 181
    # 181,50€
    pattern = (
        r"^[+-]?"
        r"(?:\d{1,3}(?:[.,]\d{3})+|\d+)"
        r"(?:[.,]\d{1,2})?"
        r"$"
    )

    return bool(re.fullmatch(pattern, cleaned))


def extract_amount(text):
    text = clean_text(text)

    # Currency + amount
    pattern = (
        r"(?:€|EUR|USD|GBP|£|\$|₹|¥)?\s*"
        r"[+-]?"
        r"(?:\d{1,3}(?:[.,]\d{3})+|\d+)"
        r"(?:[.,]\d{1,2})?"
        r"\s*(?:€|EUR|USD|GBP|£|\$|₹|¥)?"
    )

    matches = re.findall(pattern, text, re.IGNORECASE)

    if not matches:
        return None

    # Usually the last amount in the text is the relevant one
    return matches[-1].strip()


# ============================================================
# FIND VALUE NEAR LABEL
# ============================================================

def candidate_distance(label, candidate):
    """
    Calculate geometric distance between label and candidate.
    """

    dx = abs(candidate["center_x"] - label["center_x"])
    dy = abs(candidate["center_y"] - label["center_y"])

    return dx + dy


def find_nearby_candidates(
    items,
    label_item,
    validator,
    max_vertical_distance=180,
    max_horizontal_distance=500,
):
    candidates = []

    label = label_item

    for item in items:

        if item is label:
            continue

        if not validator(item["text"]):
            continue

        dx = abs(item["center_x"] - label["center_x"])
        dy = abs(item["center_y"] - label["center_y"])

        # Same row / value to the right
        same_row = (
            dy <= max(label["height"], item["height"]) * 1.5
            and item["center_x"] >= label["center_x"] - 20
            and dx <= max_horizontal_distance
        )

        # Value below label
        below = (
            item["center_y"] >= label["center_y"]
            and dy <= max_vertical_distance
            and dx <= max_horizontal_distance
        )

        # Value above label
        above = (
            item["center_y"] < label["center_y"]
            and dy <= max_vertical_distance
            and dx <= max_horizontal_distance
        )

        if same_row or below or above:

            score = 0

            # Strong preference for right side
            if same_row:
                score += 50

            # Strong preference for directly below
            if below:
                score += 35

            # Smaller distance is better
            score -= candidate_distance(label, item) * 0.05

            # OCR confidence
            score += item["confidence"] * 10

            candidates.append(
                (score, item)
            )

    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return candidates


# ============================================================
# FIND FIELD USING LABEL
# ============================================================

def find_labeled_value(
    items,
    labels,
    validator,
    extractor=None,
):
    label_items = [
        item
        for item in items
        if contains_any_label(
            item["text"],
            labels
        )
    ]

    all_candidates = []

    for label in label_items:

        candidates = find_nearby_candidates(
            items,
            label,
            validator
        )

        for score, candidate in candidates:

            all_candidates.append(
                (
                    score,
                    candidate,
                    label
                )
            )

    if not all_candidates:
        return None

    all_candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    candidate = all_candidates[0][1]

    if extractor:
        return extractor(candidate["text"])

    return candidate["text"]


# ============================================================
# SPECIAL TOTAL FINDER
# ============================================================

def find_total(items):
    """
    Find the most likely invoice total.

    Uses:
    - explicit total labels
    - coordinates
    - amount validation
    - negative labels
    - OCR confidence
    """

    candidates = []

    total_labels = [
        "grand total",
        "invoice total",
        "total amount",
        "amount due",
        "total due",
        "amount payable",
        "total payable",
        "balance due",
        "balance payable",
        "net payable",
        "amount to pay",
        "total incl vat",
        "total including vat",
        "total",
    ]

    for label in items:

        label_text = normalize_label(
            label["text"]
        )

        if not any(
            normalize_label(x) in label_text
            for x in total_labels
        ):
            continue

        # Don't treat "subtotal" as "total"
        if any(
            normalize_label(x) in label_text
            for x in NEGATIVE_AMOUNT_LABELS
            if x not in ["total"]
        ):
            continue

        nearby = find_nearby_candidates(
            items,
            label,
            looks_like_amount,
            max_vertical_distance=250,
            max_horizontal_distance=700
        )

        for score, amount in nearby:

            amount_value = extract_amount(
                amount["text"]
            )

            if not amount_value:
                continue

            final_score = score

            # Explicit labels get different strengths
            if "grand total" in label_text:
                final_score += 40

            elif "invoice total" in label_text:
                final_score += 35

            elif "amount due" in label_text:
                final_score += 35

            elif "total payable" in label_text:
                final_score += 35

            elif label_text == "total":
                final_score += 20

            candidates.append(
                (
                    final_score,
                    amount_value,
                    amount,
                    label
                )
            )

    # --------------------------------------------------------
    # If an explicit label was found
    # --------------------------------------------------------

    if candidates:

        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )

        return candidates[0][1]

    # --------------------------------------------------------
    # FALLBACK:
    # Find all amounts and choose the strongest
    # candidate near the bottom/right portion.
    # --------------------------------------------------------

    amount_items = [
        item
        for item in items
        if looks_like_amount(item["text"])
    ]

    if not amount_items:
        return None

    # Calculate page bounds
    max_y = max(
        item["bottom"]
        for item in items
    )

    fallback_candidates = []

    for item in amount_items:

        score = item["confidence"] * 10

        # Amounts near the bottom are often totals
        if item["center_y"] > max_y * 0.65:
            score += 25

        if item["center_y"] > max_y * 0.80:
            score += 15

        # Larger amounts are often totals.
        try:
            numeric = re.sub(
                r"[^\d.,]",
                "",
                item["text"]
            )

            numeric = numeric.replace(",", "")

            value = float(numeric)

            score += min(value / 1000, 20)

        except Exception:
            pass

        # Check nearby text for negative indicators
        nearby_text = []

        for other in items:

            if other is item:
                continue

            dx = abs(
                other["center_x"] -
                item["center_x"]
            )

            dy = abs(
                other["center_y"] -
                item["center_y"]
            )

            if dx < 350 and dy < 80:
                nearby_text.append(
                    normalize_label(other["text"])
                )

        combined = " ".join(nearby_text)

        if "subtotal" in combined:
            score -= 40

        if "vat" in combined:
            score -= 25

        if "tax" in combined:
            score -= 25

        if "discount" in combined:
            score -= 25

        fallback_candidates.append(
            (
                score,
                extract_amount(item["text"])
            )
        )

    fallback_candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return fallback_candidates[0][1]


# ============================================================
# MAIN EXTRACTOR
# ============================================================

def extract_fields(items):

    items = prepare_items(items)

    fields = {
        "invoice_number": None,
        "invoice_date": None,
        "vat_number": None,
        "total_amount": None,
    }

    # --------------------------------------------------------
    # Invoice number
    # --------------------------------------------------------

    fields["invoice_number"] = find_labeled_value(
        items,
        INVOICE_NUMBER_LABELS,
        looks_like_invoice_number
    )

    # --------------------------------------------------------
    # Invoice date
    # --------------------------------------------------------

    fields["invoice_date"] = find_labeled_value(
        items,
        DATE_LABELS,
        looks_like_date,
        extract_date_from_text
    )

    # --------------------------------------------------------
    # VAT
    # --------------------------------------------------------

    fields["vat_number"] = find_labeled_value(
        items,
        VAT_LABELS,
        looks_like_vat
    )

    # --------------------------------------------------------
    # Total
    # --------------------------------------------------------

    fields["total_amount"] = find_total(items)

    return fields
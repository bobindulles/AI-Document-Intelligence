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
                "confidence": float(
                    item.get("confidence", 1.0)
                ),
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

    # Reject obvious labels
    rejected = {
        "invoice",
        "invoice number",
        "invoice no",
        "invoice id",
        "invoice reference",
        "invoice ref",
        "document number",
        "document no",
        "document id",
        "reference number",
        "number",
        "date",
        "vat",
        "total",
        "description",
        "bill to",
        "ship to",
    }

    if normalized in rejected:
        return False

    # Never accept dates
    if looks_like_date(text):
        return False

    # Never accept currency/amount values
    if looks_like_amount(text):
        return False

    # Invoice numbers normally contain digits
    if not re.search(r"\d", text):
        return False

    # Remove spaces
    compact = re.sub(r"\s+", "", text)

    # Structured invoice number
    #
    # Examples:
    # FA2022-0001
    # F1000876/23
    # INV-2023-001
    # 2023/00125
    #
    if re.fullmatch(
        r"[A-Za-z0-9]+(?:[-_/][A-Za-z0-9]+)+",
        compact
    ):
        return True

    # Numeric-only invoice number
    if re.fullmatch(r"\d{3,20}", compact):
        return True

    return False


def find_invoice_number(items):

    label_items = [
        item
        for item in items
        if contains_any_label(
            item["text"],
            INVOICE_NUMBER_LABELS
        )
    ]

    candidates = []

    for label in label_items:

        for item in items:

            if item is label:
                continue

            if not looks_like_invoice_number(
                item["text"]
            ):
                continue

            dx = (
                item["center_x"]
                - label["center_x"]
            )

            dy = (
                item["center_y"]
                - label["center_y"]
            )

            # Invoice number immediately to the right
            same_row_right = (
                dx >= 0
                and abs(dy)
                <= max(
                    label["height"],
                    item["height"]
                ) * 1.5
                and dx <= 500
            )

            # Invoice number directly below
            below = (
                dy >= 0
                and abs(dx) <= 250
                and dy <= 120
            )

            if not (
                same_row_right
                or below
            ):
                continue

            score = item["confidence"] * 10

            if same_row_right:
                score += 70

            if below:
                score += 30

            compact = re.sub(
                r"\s+",
                "",
                item["text"]
            )

            # Strong preference for structured format
            if re.fullmatch(
                r"[A-Za-z0-9]+(?:[-_/][A-Za-z0-9]+)+",
                compact
            ):
                score += 40

            score -= (
                abs(dx) + abs(dy)
            ) * 0.05

            candidates.append(
                (
                    score,
                    item["text"]
                )
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return candidates[0][1]


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

        # 05/09/2022
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",

        # 2022/09/05
        r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",

        # 05.09.2022
        r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b",

        # 5 September 2022
        r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",

        # September 5, 2022
        r"\b[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}\b",
    ]

    return any(
        re.search(pattern, text)
        for pattern in patterns
    )


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

        match = re.search(
            pattern,
            text
        )

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


def extract_vat_from_text(text):

    """
    Extract VAT number from text.

    Handles OCR text such as:

    VAT BE0631922138
    your VAT number BE0631922138
    VAT number: BE0631922138
    """

    text = clean_text(text)

    if not text:
        return None

    # Country-code VAT
    #
    # Examples:
    # BE0631922138
    # FR12345678901
    # DE123456789
    #
    match = re.search(
        r"\b([A-Z]{2}[A-Z0-9]{6,14})\b",
        text.upper()
    )

    if match:

        candidate = match.group(1)

        # Make sure it isn't something unrelated
        if not looks_like_date(candidate):
            return candidate

    # Numeric VAT
    match = re.search(
        r"\b(\d{8,15})\b",
        text
    )

    if match:
        return match.group(1)

    return None


def looks_like_vat(text):

    text = clean_text(text)

    if not text:
        return False

    # First try extracting VAT from the text
    vat = extract_vat_from_text(text)

    if vat is None:
        return False

    return True


def find_vat_value(items):

    candidates = []

    for item in items:

        text = item["text"]

        normalized = normalize_label(text)

        # We only want text associated with VAT/tax
        if not contains_any_label(
            text,
            VAT_LABELS
        ):
            continue

        vat = extract_vat_from_text(text)

        if vat:

            score = (
                item["confidence"] * 10
            )

            # Strong preference if label and value
            # are in the same OCR region
            if (
                "vat" in normalized
                or "tax" in normalized
            ):
                score += 80

            candidates.append(
                (
                    score,
                    vat
                )
            )

    # If VAT is inside the same OCR item
    # such as:
    #
    # your VAT number BE0631922138
    #
    if candidates:

        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )

        return candidates[0][1]

    # Otherwise search nearby OCR regions
    label_items = [
        item
        for item in items
        if contains_any_label(
            item["text"],
            VAT_LABELS
        )
    ]

    for label in label_items:

        for item in items:

            if item is label:
                continue

            vat = extract_vat_from_text(
                item["text"]
            )

            if not vat:
                continue

            dx = (
                item["center_x"]
                - label["center_x"]
            )

            dy = (
                item["center_y"]
                - label["center_y"]
            )

            right_same_row = (
                dx >= 0
                and abs(dy)
                <= max(
                    label["height"],
                    item["height"]
                ) * 1.5
                and dx <= 500
            )

            below = (
                dy >= 0
                and abs(dx) <= 250
                and dy <= 120
            )

            if right_same_row or below:
                return vat

    return None


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

    # Remove currency symbols
    cleaned = re.sub(
        r"[€$£¥₹]",
        "",
        text
    )

    cleaned = cleaned.replace(
        " ",
        ""
    )

    # Examples:
    #
    # 181.50
    # 181,50
    # 1,181.50
    # 1.181,50
    # 181
    #
    pattern = (
        r"^[+-]?"
        r"(?:\d{1,3}(?:[.,]\d{3})+|\d+)"
        r"(?:[.,]\d{1,2})?"
        r"$"
    )

    return bool(
        re.fullmatch(
            pattern,
            cleaned
        )
    )


def extract_amount(text):

    text = clean_text(text)

    pattern = (
        r"(?:€|EUR|USD|GBP|£|\$|₹|¥)?\s*"
        r"[+-]?"
        r"(?:\d{1,3}(?:[.,]\d{3})+|\d+)"
        r"(?:[.,]\d{1,2})?"
        r"\s*(?:€|EUR|USD|GBP|£|\$|₹|¥)?"
    )

    matches = re.findall(
        pattern,
        text,
        re.IGNORECASE
    )

    if not matches:
        return None

    # Usually the last amount is the relevant amount
    return matches[-1].strip()


# ============================================================
# FIND VALUE NEAR LABEL
# ============================================================

def candidate_distance(
    label,
    candidate
):

    dx = (
        candidate["center_x"]
        - label["center_x"]
    )

    dy = (
        candidate["center_y"]
        - label["center_y"]
    )

    return abs(dx) + abs(dy)


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

        if not validator(
            item["text"]
        ):
            continue

        dx = (
            item["center_x"]
            - label["center_x"]
        )

        dy = (
            item["center_y"]
            - label["center_y"]
        )

        # Same row / value to the right
        same_row = (
            abs(dy)
            <= max(
                label["height"],
                item["height"]
            ) * 1.5
            and item["center_x"]
            >= label["center_x"] - 20
            and abs(dx)
            <= max_horizontal_distance
        )

        # Value below label
        below = (
            item["center_y"]
            >= label["center_y"]
            and dy <= max_vertical_distance
            and abs(dx)
            <= max_horizontal_distance
        )

        # Value above label
        above = (
            item["center_y"]
            < label["center_y"]
            and abs(dy)
            <= max_vertical_distance
            and abs(dx)
            <= max_horizontal_distance
        )

        if not (
            same_row
            or below
            or above
        ):
            continue

        score = 0

        # Strong preference for right side
        if same_row:
            score += 50

        # Strong preference for directly below
        if below:
            score += 35

        # Smaller distance is better
        score -= (
            candidate_distance(
                label,
                item
            ) * 0.05
        )

        # OCR confidence
        score += (
            item["confidence"] * 10
        )

        candidates.append(
            (
                score,
                item
            )
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
        return extractor(
            candidate["text"]
        )

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
            normalize_label(x)
            in label_text
            for x in total_labels
        ):
            continue

        # Don't treat subtotal as total
        if any(
            normalize_label(x)
            in label_text
            for x in NEGATIVE_AMOUNT_LABELS
            if x != "total"
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

            # Explicit labels get stronger scores
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
    # Explicit total found
    # --------------------------------------------------------

    if candidates:

        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )

        return candidates[0][1]

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    amount_items = [
        item
        for item in items
        if looks_like_amount(
            item["text"]
        )
    ]

    if not amount_items:
        return None

    # Page bounds
    max_y = max(
        item["bottom"]
        for item in items
    )

    fallback_candidates = []

    for item in amount_items:

        score = (
            item["confidence"] * 10
        )

        # Amounts near bottom are often totals
        if item["center_y"] > max_y * 0.65:
            score += 25

        if item["center_y"] > max_y * 0.80:
            score += 15

        # Larger amounts are often totals
        try:

            numeric = re.sub(
                r"[^\d.,]",
                "",
                item["text"]
            )

            numeric = numeric.replace(
                ",",
                ""
            )

            value = float(numeric)

            score += min(
                value / 1000,
                20
            )

        except Exception:
            pass

        # Check nearby text for negative indicators
        nearby_text = []

        for other in items:

            if other is item:
                continue

            dx = abs(
                other["center_x"]
                - item["center_x"]
            )

            dy = abs(
                other["center_y"]
                - item["center_y"]
            )

            if (
                dx < 350
                and dy < 80
            ):

                nearby_text.append(
                    normalize_label(
                        other["text"]
                    )
                )

        combined = " ".join(
            nearby_text
        )

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
                extract_amount(
                    item["text"]
                )
            )
        )

    fallback_candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return fallback_candidates[0][1]


# ============================================================
# QUANTITY + LINE ITEM AMOUNT
# ============================================================

def find_quantity_and_amount(items):

    """
    Extract:

    1. Quantity
    2. Line-item price/amount

    Works with values such as:

    1 piece
    2 pieces
    5 pcs
    10 pc

    The line-item amount is located relative
    to the "price" column.
    """

    quantity = None
    amount = None

    # --------------------------------------------------------
    # FIND QUANTITY
    # --------------------------------------------------------

    for item in items:

        text = (
            str(item["text"])
            .strip()
            .lower()
        )

        match = re.match(
            r"^(\d+(?:[.,]\d+)?)\s+"
            r"(piece|pieces|pc|pcs)$",
            text
        )

        if match:

            quantity = float(
                match.group(1)
                .replace(",", ".")
            )

            break

    # --------------------------------------------------------
    # FIND PRICE COLUMN
    # --------------------------------------------------------

    price_labels = [
        item
        for item in items
        if normalize_label(
            item["text"]
        ) == "price"
    ]

    if price_labels:

        price_label = price_labels[0]

        candidates = []

        for item in items:

            if item is price_label:
                continue

            if not looks_like_amount(
                item["text"]
            ):
                continue

            dx = (
                item["center_x"]
                - price_label["center_x"]
            )

            dy = abs(
                item["center_y"]
                - price_label["center_y"]
            )

            # Price should be below
            # the price header
            if (
                dy <= 150
                and dx >= -50
            ):

                score = (
                    100
                    - dy
                    - abs(dx) * 0.1
                )

                candidates.append(
                    (
                        score,
                        item["text"]
                    )
                )

        if candidates:

            candidates.sort(
                key=lambda x: x[0],
                reverse=True
            )

            amount = extract_amount(
                candidates[0][1]
            )

    return quantity, amount


# ============================================================
# MAIN EXTRACTOR
# ============================================================

def extract_fields(items):

    # Prepare OCR items with geometry
    items = prepare_items(items)

    fields = {
        "invoice_number": None,
        "invoice_date": None,
        "vat_number": None,
        "total_amount": None,
        "qty": None,
        "amount": None,
        "product_id": None,
        "stock_code": None,
    }

    # --------------------------------------------------------
    # QUANTITY + LINE ITEM AMOUNT
    # --------------------------------------------------------

    qty, amount = find_quantity_and_amount(
        items
    )

    fields["qty"] = qty
    fields["amount"] = amount

    # --------------------------------------------------------
    # INVOICE NUMBER
    # --------------------------------------------------------

    fields["invoice_number"] = (
        find_invoice_number(items)
    )

    # --------------------------------------------------------
    # INVOICE DATE
    # --------------------------------------------------------

    fields["invoice_date"] = (
        find_labeled_value(
            items,
            DATE_LABELS,
            looks_like_date,
            extract_date_from_text
        )
    )

    # --------------------------------------------------------
    # VAT NUMBER
    # --------------------------------------------------------

    fields["vat_number"] = (
        find_vat_value(items)
    )

    # --------------------------------------------------------
    # TOTAL AMOUNT
    # --------------------------------------------------------

    fields["total_amount"] = (
        find_total(items)
    )

    # --------------------------------------------------------
    # PRODUCT ID
    # --------------------------------------------------------
    #
    # Not extracted yet.
    #
    # We leave this as None instead of inventing
    # a product ID when the invoice does not contain one.
    #

    fields["product_id"] = None

    # --------------------------------------------------------
    # STOCK CODE
    # --------------------------------------------------------
    #
    # Not extracted yet.
    #

    fields["stock_code"] = None

    return fields
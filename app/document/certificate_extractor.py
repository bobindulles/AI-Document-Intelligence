import re
import cv2


# ============================================================
# TEXT CLEANING
# ============================================================

def clean(text):
    """Clean OCR text while keeping useful information."""

    if text is None:
        return ""

    text = str(text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# DATE EXTRACTION
# ============================================================

def extract_dates(full_text):

    patterns = [

        # DD/MM/YYYY
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",

        # DD/MM/YY
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2}\b",

        # DD Month YYYY
        r"\b\d{1,2}\s+"
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"\s+\d{4}\b",

        # Month DD, YYYY
        r"\b(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"\s+\d{1,2},\s+\d{4}\b",
    ]

    dates = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            full_text,
            re.IGNORECASE
        )

        for match in matches:

            if match not in dates:
                dates.append(match)

    return dates


# ============================================================
# QR CODE EXTRACTION
# ============================================================

def extract_qr_data(image_path):

    """
    Read QR code from certificate.

    Returns:
        {
            "verification_url": ...,
            "certificate_id": ...
        }
    """

    result = {
        "verification_url": None,
        "certificate_id": None
    }

    if not image_path:
        return result

    try:

        image = cv2.imread(str(image_path))

        if image is None:
            return result

        detector = cv2.QRCodeDetector()

        data, points, _ = detector.detectAndDecode(image)

        if not data:
            return result

        data = data.strip()

        result["verification_url"] = data

        # ----------------------------------------------------
        # Extract certificate code from URL
        # ----------------------------------------------------

        patterns = [
            r"[?&]code=([^&]+)",
            r"[?&]certificate[_-]?id=([^&]+)",
            r"[?&]id=([^&]+)"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                data,
                re.IGNORECASE
            )

            if match:

                result["certificate_id"] = (
                    match.group(1).strip()
                )

                break

        return result

    except Exception:

        return result


# ============================================================
# ORGANIZATION EXTRACTION
# ============================================================

def extract_organization(texts, full_text, certificate_name=None):

        certificate_name = clean(certificate_name or "")
        certificate_words = set(
        re.findall(
            r"[A-Za-z]+",
            certificate_name.lower()
        )
    )

    # --------------------------------------------------------
    # METHOD 1
    # Organization explicitly mentioned in a sentence
    # --------------------------------------------------------

    patterns = [

        r"(.{2,120}?)\s+hereby\s+certifies\s+that",

        r"(.{2,120}?)\s+hereby\s+certifies",

        r"issued\s+by\s*[:\-]?\s*(.{2,120})",

        r"provided\s+by\s*[:\-]?\s*(.{2,120})",

        r"awarded\s+by\s*[:\-]?\s*(.{2,120})",

        r"offered\s+by\s*[:\-]?\s*(.{2,120})",

        r"conducted\s+by\s*[:\-]?\s*(.{2,120})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            full_text,
            re.IGNORECASE
        )

        if match:

            organization = clean(match.group(1))

            # Remove common leading words
            organization = re.sub(
                r"^(certificate|this|the)\s+",
                "",
                organization,
                flags=re.IGNORECASE
            )

            # Remove sentence continuation
            organization = re.split(
                r"\b(?:hereby|certifies|certified|awarded|"
                r"presented|has successfully|successfully)\b",
                organization,
                maxsplit=1,
                flags=re.IGNORECASE
            )[0].strip()

            if is_valid_organization(organization):
                return organization


    # --------------------------------------------------------
    # METHOD 2
    # Look for organization-like OCR lines
    # --------------------------------------------------------

    organization_keywords = [
        "university",
        "institute",
        "college",
        "academy",
        "school",
        "foundation",
        "organization",
        "organisation",
        "technologies",
        "technology",
        "corporation",
        "company",
        "inc",
        "ltd",
        "limited",
        "llp",
        "trust",
        "association",
        "society",
        "group",
        "solutions",
        "services",
        "systems"
    ]


    candidates = []

    for index, text in enumerate(texts):

        text = clean(text)

        if not text:
            continue

        lower = text.lower()

        # Ignore obvious certificate content
        blocked = [
            "certificate",
            "completion",
            "congratulations",
            "successfully completed",
            "recipient",
            "verification",
            "certificate id",
            "credential",
            "authorized signatory",
            "authorised signatory",
            "signature"
        ]

        if any(word in lower for word in blocked):
            continue


        # Check organization keywords
        keyword_match = any(
            keyword in lower
            for keyword in organization_keywords
        )

        if keyword_match:

            candidates.append(text)


    # Prefer the shortest clean organization-looking candidate.
    # This avoids grabbing an entire sentence containing
    # an organization keyword.
    if candidates:

        candidates.sort(
            key=lambda x: (
                len(x.split()) > 8,
                len(x)
            )
        )

        for candidate in candidates:

            if is_valid_organization(candidate):
                return candidate


    return None

def is_valid_organization(text):

    if not text:
        return False

    text = clean(text)

    if len(text) < 3:
        return False

    lower = text.lower()

    # Things that are definitely not organization names
    blocked_phrases = [
        "certificate",
        "completion",
        "congratulations",
        "successfully completed",
        "recipient",
        "verification",
        "certificate id",
        "credential",
        "authorized signatory",
        "authorised signatory",
        "signature",
        "this is to certify",
        "hereby certifies"
    ]

    for phrase in blocked_phrases:
        if phrase in lower:
            return False


    # URLs are not organization names
    if (
        "http://" in lower
        or "https://" in lower
        or "www." in lower
    ):
        return False


    # Must contain actual alphabetic characters
    letters = sum(
        char.isalpha()
        for char in text
    )

    if letters < 3:
        return False


    # Avoid very long sentences
    if len(text.split()) > 12:
        return False


    return True

# ============================================================
# RECIPIENT NAME EXTRACTION
# ============================================================

def extract_recipient(full_text):

    patterns = [

        # hereby certifies that NAME has successfully
        r"hereby\s+certifies\s+that\s+"
        r"([A-Za-z][A-Za-z .'-]{1,80}?)"
        r"\s+has\s+successfully",

        # certifies that NAME has successfully
        r"certif(?:y|ies)\s+that\s+"
        r"([A-Za-z][A-Za-z .'-]{1,80}?)"
        r"\s+has\s+successfully",

        # awarded to NAME
        r"awarded\s+to\s+"
        r"([A-Za-z][A-Za-z .'-]{1,80})",

        # presented to NAME
        r"presented\s+to\s+"
        r"([A-Za-z][A-Za-z .'-]{1,80})",

        # given to NAME
        r"given\s+to\s+"
        r"([A-Za-z][A-Za-z .'-]{1,80})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            full_text,
            re.IGNORECASE
        )

        if match:

            name = clean(match.group(1))

            name = re.sub(
                r"\s+(has|had|was|is)$",
                "",
                name,
                flags=re.IGNORECASE
            )

            if len(name) >= 2:
                return name

    return None


# ============================================================
# CERTIFICATE TITLE
# ============================================================

def extract_certificate_name(texts, full_text):

    patterns = [

        # Certificate of Completion / Certificate of Completion Foundation
        r"(certificate\s+of\s+completion(?:\s+[A-Za-z0-9&'-]+)?)",

        # Course Completion Certificate
        r"(course\s+completion\s+certificate)",

        # Achievement Certificate
        r"(achievement\s+certificate)",

        # Participation Certificate
        r"(participation\s+certificate)",

        # Completion Certificate
        r"(completion\s+certificate)",

        # Training Certificate
        r"(training\s+certificate)",

        # Internship Certificate
        r"(internship\s+certificate)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            full_text,
            re.IGNORECASE
        )

        if match:

            title = clean(match.group(1))

            # Stop accidental sentence continuation
            title = re.split(
                r"\b(?:this\s+is\s+to\s+certify|"
                r"hereby\s+certifies|"
                r"awarded\s+to|"
                r"presented\s+to)\b",
                title,
                maxsplit=1,
                flags=re.IGNORECASE
            )[0]

            return title.strip()

    # Search individual OCR lines
    for text in texts:

        text = clean(text)

        if not text:
            continue

        if (
            "certificate" in text.lower()
            and len(text.split()) <= 8
        ):
            return text

    return None

# ============================================================
# COURSE / PROGRAM NAME
# ============================================================

def extract_course_name(items):

    """
    Extract the actual course/program name.

    Example:
        Analytics for Decision Making MAganwer

    Expected:
        Analytics for Decision Making

    The function uses OCR text + bounding boxes and removes
    signature-related OCR garbage.
    """

    if not items:
        return None

    ocr_items = []

    for item in items:

        if not isinstance(item, dict):
            continue

        text = clean(item.get("text", ""))
        box = item.get("box")

        if not text:
            continue

        x1 = x2 = y1 = y2 = 0

        if box is not None:

            try:

                xs = [
                    float(point[0])
                    for point in box
                ]

                ys = [
                    float(point[1])
                    for point in box
                ]

                x1 = min(xs)
                x2 = max(xs)
                y1 = min(ys)
                y2 = max(ys)

            except Exception:
                pass

        ocr_items.append({
            "text": text,
            "x1": x1,
            "x2": x2,
            "y1": y1,
            "y2": y2,
            "center_x": (x1 + x2) / 2,
            "center_y": (y1 + y2) / 2
        })

    if not ocr_items:
        return None

    full_text = clean(
        " ".join(
            item["text"]
            for item in ocr_items
        )
    )

    # --------------------------------------------------------
    # METHOD 1
    # Explicit "completed the COURSE" pattern
    # --------------------------------------------------------

    patterns = [

        r"successfully\s+completed\s+(?:the\s+)?"
        r"(.{3,150}?)"
        r"(?=\s+(?:and|from|at|on|in)\s+|$)",

        r"completed\s+(?:the\s+)?"
        r"(.{3,150}?)"
        r"(?=\s+(?:and|from|at|on|in)\s+|$)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            full_text,
            re.IGNORECASE
        )

        if match:

            course = clean_course_candidate(
                match.group(1)
            )

            if is_valid_course(course):
                return course

    # --------------------------------------------------------
    # METHOD 2
    # Look around "completed"
    # --------------------------------------------------------

    for index, item in enumerate(ocr_items):

        lower = item["text"].lower()

        if "completed" not in lower:
            continue

        candidates = []

        # Check next few OCR items
        for j in range(
            index + 1,
            min(index + 5, len(ocr_items))
        ):

            candidate = clean_course_candidate(
                ocr_items[j]["text"]
            )

            if is_valid_course(candidate):
                candidates.append(candidate)

        if candidates:

            candidates.sort(
                key=len,
                reverse=True
            )

            return candidates[0]

    # --------------------------------------------------------
    # METHOD 3
    # Search all OCR items
    # --------------------------------------------------------

    candidates = []

    for item in ocr_items:

        text = clean_course_candidate(
            item["text"]
        )

        if is_valid_course(text):

            candidates.append(text)

    if candidates:

        # Prefer longer meaningful text
        candidates.sort(
            key=len,
            reverse=True
        )

        return candidates[0]

    return None


# ============================================================
# COURSE CLEANING
# ============================================================

def clean_course_candidate(text):

    if not text:
        return None

    text = clean(text)

    # --------------------------------------------------------
    # Remove leading labels
    # --------------------------------------------------------

    text = re.sub(
        r"^(the|a|an)\s+",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^(course|program|programme)"
        r"\s*[:\-]\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # --------------------------------------------------------
    # Remove certificate/signature text
    # --------------------------------------------------------

    text = re.split(
        r"\b(?:certificate|"
        r"authorized\s+signatory|"
        r"authorised\s+signatory|"
        r"signature|"
        r"signatory)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]

    # --------------------------------------------------------
    # Remove signature OCR garbage
    #
    # Examples:
    # MAganwer
    # MAgawer
    # M A ganwer
    # --------------------------------------------------------

    text = re.sub(
        r"\s+[Mm]\s*[Aa]\s*[Gg]\s*[Aa]"
        r"\s*[Nn]\s*[Ww]\s*[Ee]\s*[Rr]\s*$",
        "",
        text
    )

    # Generic OCR signature pattern
    text = re.sub(
        r"\s+[Mm][A-Za-z]{4,20}$",
        "",
        text
    )

    # --------------------------------------------------------
    # Remove trailing random single-letter fragments
    # --------------------------------------------------------

    text = re.sub(
        r"\s+[A-Za-z]{1,2}$",
        "",
        text
    )

    # --------------------------------------------------------
    # Remove repeated whitespace
    # --------------------------------------------------------

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# COURSE VALIDATION
# ============================================================

def is_valid_course(text):

    if not text:
        return False

    text = clean(text)

    if len(text) < 4:
        return False

    lower = text.lower()

    # --------------------------------------------------------
    # Definitely NOT a course
    # --------------------------------------------------------

    blocked_phrases = [

        "course completion certificate",

        "completion certificate",

        "certificate",

        "hereby certifies",

        "certifies that",

        "authorized signatory",

        "authorised signatory",

        "signature",

        "signatory",

        "university",

        "institute",

        "college",

        "academy",

        "school",

        "recipient",

        "congratulations"
    ]

    for phrase in blocked_phrases:

        if phrase in lower:
            return False

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    if (
        "http://" in lower
        or "https://" in lower
        or "www." in lower
    ):
        return False

    # --------------------------------------------------------
    # Must contain enough letters
    # --------------------------------------------------------

    letters = sum(
        char.isalpha()
        for char in text
    )

    if letters < 3:
        return False

    # --------------------------------------------------------
    # Avoid obvious signature text
    # --------------------------------------------------------

    signature_words = [
        "signed",
        "signature",
        "signatory",
        "authorized",
        "authorised"
    ]

    if any(
        word in lower
        for word in signature_words
    ):
        return False

    return True

# ============================================================
# COURSE CLEANING
# ============================================================

def clean_course_candidate(text):

    if not text:
        return None

    text = clean(text)

    # Remove common leading phrases
    text = re.sub(
        r"^(the|a|an)\s+",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^(course|program|programme)\s*[:\-]\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove trailing certificate-related text
    text = re.split(
        r"\b(?:certificate|authorized\s+signatory|"
        r"authorised\s+signatory|signature)\b",
        text,
        flags=re.IGNORECASE
    )[0]

    return clean(text)


# ============================================================
# COURSE VALIDATION
# ============================================================

def is_valid_course(text):

    if not text:
        return False

    text = clean(text)

    if len(text) < 4:
        return False

    lower = text.lower()

    # --------------------------------------------------------
    # Things that should NEVER be course names
    # --------------------------------------------------------

    blocked_phrases = [

        "course completion certificate",
        "completion certificate",
        "certificate",
        "hereby certifies",
        "certifies that",
        "authorized signatory",
        "authorised signatory",
        "signature",
        "university",
        "institute",
        "college",
        "academy",
        "school"
    ]

    for phrase in blocked_phrases:

        if phrase in lower:

            return False

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    if (
        "http://" in lower
        or "https://" in lower
        or "www." in lower
    ):

        return False

    # --------------------------------------------------------
    # Mostly numeric text
    # --------------------------------------------------------

    letters = sum(
        char.isalpha()
        for char in text
    )

    if letters < 3:
        return False

    # --------------------------------------------------------
    # Signature-like OCR
    # --------------------------------------------------------

    signature_words = [
        "signatory",
        "signed",
        "signature",
        "authorized",
        "authorised"
    ]

    if any(
        word in lower
        for word in signature_words
    ):

        return False

    return True


# ============================================================
# CERTIFICATE ID FROM OCR TEXT
# ============================================================

def extract_certificate_id(full_text):

    patterns = [

        r"certificate\s*(?:id|no|number)"
        r"\s*[:#-]?\s*([A-Za-z0-9./_-]+)",

        r"certificate\s*#"
        r"\s*([A-Za-z0-9./_-]+)",

        r"credential\s*(?:id|no|number)"
        r"\s*[:#-]?\s*([A-Za-z0-9./_-]+)",

        r"credential\s*#"
        r"\s*([A-Za-z0-9./_-]+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            full_text,
            re.IGNORECASE
        )

        if match:

            return match.group(1).strip()

    return None


# ============================================================
# SIGNATORY ROLE
# ============================================================

def extract_signatory_role(full_text):

    patterns = [

        r"(authorized\s+signatory)",

        r"(authorised\s+signatory)",

        r"(program\s+director)",

        r"(programme\s+director)",

        r"(director)",

        r"(dean)",

        r"(registrar)",

        r"(principal)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            full_text,
            re.IGNORECASE
        )

        if match:

            return clean(
                match.group(1)
            )

    return None


# ============================================================
# MAIN CERTIFICATE EXTRACTOR
# ============================================================

def extract_certificate(items, image_path=None):

    texts = []
    valid_items = []

    for item in items:

        if not isinstance(item, dict):
            continue

        text = clean(
            item.get("text", "")
        )

        if not text:
            continue

        texts.append(text)
        valid_items.append(item)

        print("\n========== CERTIFICATE OCR LINES ==========")

        for i, text in enumerate(texts):
            print(f"[{i}] {text}")

        print("===========================================\n")

    full_text = clean(
        " ".join(texts)
    )

    result = {
        "recipient_name": None,
        "certificate_name": None,
        "course_name": None,
        "organization": None,
        "certificate_id": None,
        "issue_date": None,
        "expiry_date": None,
        "verification_url": None,
        "signatory_role": None
    }

    result["recipient_name"] = extract_recipient(
        full_text
    )

    result["certificate_name"] = extract_certificate_name(
        texts,
        full_text
    )

    # IMPORTANT:
    # Pass dictionaries, NOT texts.
    result["course_name"] = extract_course_name(
        valid_items
    )

    result["organization"] = extract_organization(
        texts,
        full_text
    )

    result["certificate_id"] = extract_certificate_id(
        full_text
    )

    dates = extract_dates(full_text)

    if len(dates) >= 1:
        result["issue_date"] = dates[0]

    if len(dates) >= 2:
        result["expiry_date"] = dates[1]

    result["signatory_role"] = extract_signatory_role(
        full_text
    )

    qr_result = extract_qr_data(
        image_path
    )

    result["verification_url"] = (
        qr_result["verification_url"]
    )

    if not result["certificate_id"]:

        result["certificate_id"] = (
            qr_result["certificate_id"]
        )

    return {
        "document_type": "certificate",
        "fields": result
    }
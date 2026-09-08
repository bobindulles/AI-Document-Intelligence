import re


# ============================================================
# TEXT CLEANING
# ============================================================

def clean(text):
    """Clean OCR text."""
    text = str(text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ============================================================
# SPLIT LONG OCR TEXT
# ============================================================

def split_content(text):
    """
    Split long OCR text into smaller readable pieces.

    Handles:
    - Bullet points
    - Sentences
    - Semicolons
    """

    text = clean(text)

    if not text:
        return []

    # Split bullet points
    parts = re.split(
        r"\s*[•●▪◦■◆►]\s*",
        text
    )

    final_parts = []

    for part in parts:

        part = part.strip()

        if not part:
            continue

        # Split sentences when they are clearly separated
        sentences = re.split(
            r"(?<=[.!?])\s+",
            part
        )

        for sentence in sentences:

            sentence = sentence.strip()

            if len(sentence) > 2:
                final_parts.append(sentence)

    return final_parts


# ============================================================
# SECTION DEFINITIONS
# ============================================================

SECTION_KEYWORDS = {

    "skills": [
        "skills",
        "core skills",
        "technical skills",
        "technical &",
        "technical and",
        "skills & technologies",
        "skills and technologies",
        "key skills"
    ],

    "education": [
        "education",
        "academic background",
        "academic qualification",
        "qualifications"
    ],

    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "work history"
    ],

    "projects": [
        "projects",
        "project",
        "academic projects",
        "personal projects",
        "key projects"
    ],

    "certifications": [
        "certifications",
        "certification",
        "certificates",
        "certificate"
    ]
}


# ============================================================
# CHECK WHETHER OCR TEXT IS A SECTION HEADING
# ============================================================

def detect_section(text):
    """
    Detect whether a line is a resume section heading.

    Returns:
        section name or None
    """

    original = clean(text)

    if not original:
        return None

    normalized = original.lower()

    # Remove common punctuation
    normalized = re.sub(
        r"[:\-–—|]+$",
        "",
        normalized
    ).strip()

    # Direct match
    for section, keywords in SECTION_KEYWORDS.items():

        for keyword in keywords:

            if normalized == keyword.lower():
                return section

    # Handle headings such as:
    # "PROJECTS:"
    # "SKILLS & TECHNOLOGIES:"
    # "CORE SKILLS"
    for section, keywords in SECTION_KEYWORDS.items():

        for keyword in keywords:

            pattern = (
                r"^"
                + re.escape(keyword.lower())
                + r"\s*[:\-–—|]?\s*$"
            )

            if re.match(pattern, normalized):
                return section

    # Detect uppercase headings
    # Example:
    # PROJECTS
    # EDUCATION
    # CERTIFICATIONS
    if original.isupper() and len(original.split()) <= 6:

        upper_normalized = original.lower()

        for section, keywords in SECTION_KEYWORDS.items():

            for keyword in keywords:

                if upper_normalized == keyword.lower():
                    return section

    return None


# ============================================================
# FIND NAME
# ============================================================

def find_name(texts):
    """
    Try to find the person's name.

    Usually the name appears near the top of the resume.
    """

    for text in texts[:15]:

        text = clean(text)

        if not text:
            continue

        # Skip section headings
        if detect_section(text):
            continue

        # Skip email
        if "@" in text:
            continue

        # Skip URLs
        if (
            "http://" in text.lower()
            or "https://" in text.lower()
            or "www." in text.lower()
        ):
            continue

        # Skip lines containing many numbers
        if len(re.findall(r"\d", text)) > 2:
            continue

        # Names are usually short
        words = text.split()

        if 1 <= len(words) <= 5 and len(text) <= 60:

            # Avoid common resume labels
            ignored = {
                "resume",
                "curriculum vitae",
                "profile",
                "objective",
                "about me",
                "contact",
                "career objective",
                "professional summary"
            }

            if text.lower() not in ignored:
                return text

    return None


# ============================================================
# EXTRACT EMAIL
# ============================================================

def find_email(full_text):

    email_pattern = (
        r"[A-Za-z0-9._%+-]+"
        r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    )

    match = re.search(
        email_pattern,
        full_text
    )

    if match:
        return match.group().strip()

    return None


# ============================================================
# EXTRACT PHONE
# ============================================================

def find_phone(full_text):

    phone_patterns = [

        # International / normal phone
        r"(?:\+?\d[\d\s().-]{8,}\d)",

        # Indian-style phone numbers
        r"\b[6-9]\d{9}\b"
    ]

    for pattern in phone_patterns:

        match = re.search(
            pattern,
            full_text
        )

        if match:

            phone = match.group().strip()

            # Avoid accidentally returning a huge number
            digits = re.sub(
                r"\D",
                "",
                phone
            )

            if 10 <= len(digits) <= 15:
                return phone

    return None


# ============================================================
# EXTRACT RESUME SECTIONS
# ============================================================

def extract_sections(texts):

    sections = {
        "skills": [],
        "education": [],
        "experience": [],
        "projects": [],
        "certifications": []
    }

    current_section = None

    for text in texts:

        text = clean(text)

        if not text:
            continue

        # --------------------------------------------
        # Check if this line is a section heading
        # --------------------------------------------

        detected = detect_section(text)

        if detected:

            current_section = detected
            continue

        # --------------------------------------------
        # Ignore content before first section
        # --------------------------------------------

        if current_section is None:
            continue

        # --------------------------------------------
        # Split content into readable lines/sentences
        # --------------------------------------------

        parts = split_content(text)

        for part in parts:

            part = clean(part)

            if not part:
                continue

            # Avoid duplicate content
            if part not in sections[current_section]:

                sections[current_section].append(
                    part
                )

    return sections


# ============================================================
# CLEAN SECTION RESULTS
# ============================================================

def clean_sections(sections):

    cleaned = {}

    for section, values in sections.items():

        cleaned[section] = []

        for value in values:

            value = clean(value)

            if len(value) <= 2:
                continue

            # Remove duplicate entries
            if value not in cleaned[section]:

                cleaned[section].append(value)

    return cleaned


# ============================================================
# MAIN RESUME EXTRACTOR
# ============================================================

def extract_resume(items):

    """
    Extract structured information from a resume.

    Input:
        items = PaddleOCR output items containing:
            text
            confidence
            box

    Output:
        {
            "document_type": "resume",
            "fields": {
                ...
            }
        }
    """

    # --------------------------------------------------------
    # Get OCR text
    # --------------------------------------------------------

    texts = []

    for item in items:

        text = item.get("text", "")

        text = clean(text)

        if text:
            texts.append(text)

    # --------------------------------------------------------
    # Combine text for email/phone detection
    # --------------------------------------------------------

    full_text = " ".join(texts)

    # --------------------------------------------------------
    # Create result structure
    # --------------------------------------------------------

    result = {

        "name": None,

        "email": None,

        "phone": None,

        "skills": [],

        "education": [],

        "experience": [],

        "projects": [],

        "certifications": []
    }

    # --------------------------------------------------------
    # Extract name
    # --------------------------------------------------------

    result["name"] = find_name(texts)

    # --------------------------------------------------------
    # Extract email
    # --------------------------------------------------------

    result["email"] = find_email(
        full_text
    )

    # --------------------------------------------------------
    # Extract phone
    # --------------------------------------------------------

    result["phone"] = find_phone(
        full_text
    )

    # --------------------------------------------------------
    # Extract sections
    # --------------------------------------------------------

    sections = extract_sections(
        texts
    )

    # --------------------------------------------------------
    # Clean section results
    # --------------------------------------------------------

    sections = clean_sections(
        sections
    )

    # --------------------------------------------------------
    # Add sections to result
    # --------------------------------------------------------

    result["skills"] = sections["skills"]

    result["education"] = sections["education"]

    result["experience"] = sections["experience"]

    result["projects"] = sections["projects"]

    result["certifications"] = sections["certifications"]

    # --------------------------------------------------------
    # Return final result
    # --------------------------------------------------------

    return {
        "document_type": "resume",
        "fields": result
    }
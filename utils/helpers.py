import re

EMAIL_RE = re.compile(
    r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
)

# Better phone regex
PHONE_RE = re.compile(
    r'(?:\+91[\-\s]?)?[6-9]\d{9}|\+?\d{1,3}[\-\s]?\d{3}[\-\s]?\d{3}[\-\s]?\d{4}'
)

NAME_BLACKLIST = {
    "resume",
    "curriculum vitae",
    "faculty profile",
    "academic profile",
    "biodata",
    "resume of",
    "cv",
    "profile",
}

try:
    import spacy

    _SPACY_AVAILABLE = True

    try:
        _NLP = spacy.load("en_core_web_sm")
    except Exception:
        _NLP = None
        _SPACY_AVAILABLE = False

except Exception:
    _SPACY_AVAILABLE = False
    _NLP = None


def extract_email(text, name=""):
    if not text:
        return ""

    emails = EMAIL_RE.findall(text)
    if not emails:
        return ""

    if name:
        # Extract parts of the name that are longer than 2 characters
        name_parts = [part.lower() for part in name.split() if len(part) > 2]
        for e in emails:
            prefix = e.split('@')[0].lower()
            if any(part in prefix for part in name_parts):
                return e

    return emails[0]


def extract_phone(text):
    """
    Extract Indian mobile number.
    Avoid extracting years and publication numbers.
    """

    if not text:
        return ""

    matches = PHONE_RE.findall(text)

    if matches:
        return matches[0]

    return ""


def clean_name(name):
    if not name:
        return ""
    # Remove mailto strings and email lookalikes
    name = re.sub(r'\S*mailto\S*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\S+@\S+', '', name)
    
    # Remove c/o prefix
    name = re.sub(r'^\s*c/o\.?\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^\s*care\s+of\s*', '', name, flags=re.IGNORECASE)
    
    # Remove words like resume, cv, curriculum vitae
    name = re.sub(r'\b(resume|cv|curriculum\s+vitae|biodata|profile)\b', '', name, flags=re.IGNORECASE)
    
    # Remove phone number / digits patterns (e.g. +91-988..., (9441309716)
    name = re.sub(r'\+?[\d\-\(\)\s]{7,}', '', name)
    
    # Remove any trailing junk after underscore or brackets
    name = re.sub(r'_[a-zA-Z0-9]+$', '', name)
    
    # Remove leading/trailing digits, underscores, dots, hyphens, slashes
    name = re.sub(r'^[\d\s_\-\+\.\*\/]+', '', name)
    name = re.sub(r'[\d\s_\-\+\.\*\/]+$', '', name)
    
    # Standardize whitespace
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def extract_name(text):
    """
    Extract faculty name.

    Priority:
    1. spaCy PERSON entities
    2. Top lines with Dr./Prof.
    3. Capitalized title-like names
    """

    if not text:
        return ""

    # -------------------------
    # spaCy NER
    # -------------------------

    if _SPACY_AVAILABLE and _NLP is not None:

        try:

            doc = _NLP(text[:5000])

            for ent in doc.ents:

                if ent.label_ != "PERSON":
                    continue

                candidate = clean_name(ent.text.strip())
                if not candidate:
                    continue

                if len(candidate.split()) > 5:
                    continue

                if candidate.lower() in NAME_BLACKLIST:
                    continue

                if any(char.isdigit() for char in candidate):
                    continue

                return candidate

        except Exception:
            pass

    # -------------------------
    # Faculty CV heuristics
    # -------------------------

    lines = [
        l.strip()
        for l in text.splitlines()
        if l.strip()
    ]

    top_lines = lines[:30]

    # First look for Dr / Prof

    for line in top_lines:

        low = line.lower()

        if low in NAME_BLACKLIST:
            continue

        if re.search(r'\b(?:position|post|apply|application|faculty|curriculum|vitae|resume|biodata|profile|cv|objective|career|address|contact|email|phone|mobile|website|personal|details|hobbies|languages|skills|qualification|qualifications|education|educational|university|college|institute|school|technology|dept|department|experience|experiences)\b', low):
            continue

        if EMAIL_RE.search(line):
            continue

        if PHONE_RE.search(line):
            continue

        if len(line.split()) > 8:
            continue

        if (
            low.startswith("dr ")
            or low.startswith("dr.")
            or low.startswith("prof ")
            or low.startswith("prof.")
            or low.startswith("professor ")
        ):
            cleaned = clean_name(line)
            if cleaned:
                return cleaned

    # Then look for capitalized or uppercase names

    for line in top_lines[:15]:

        low = line.lower()

        if low in NAME_BLACKLIST:
            continue

        if re.search(r'\b(?:position|post|apply|application|faculty|curriculum|vitae|resume|biodata|profile|cv|objective|career|address|contact|email|phone|mobile|website|personal|details|hobbies|languages|skills|qualification|qualifications|education|educational|university|college|institute|school|technology|dept|department|experience|experiences)\b', low):
            continue

        if EMAIL_RE.search(line):
            continue

        if PHONE_RE.search(line):
            continue

        # Clean qualification suffixes (like B.E., M.E., Ph.D.) from line first
        clean_line = re.sub(r'\b(?:B\.E\.|M\.E\.|Ph\.D\.|MISTE|M\.Tech|B\.Tech|MBA|MS|M\.S\.)\b.*$', '', line, flags=re.I)
        clean_line = re.sub(r'[,|–\-]', '', clean_line).strip()
        
        if not clean_line:
            continue

        words = clean_line.split()

        if len(words) < 1 or len(words) > 5:
            continue

        if all(w.isalpha() or '.' in w or '-' in w for w in words):
            # Accept if clean_line is uppercase or all words are capitalized
            if clean_line.isupper() or all(w[0].isupper() for w in words if w):
                cleaned = clean_name(clean_line)
                if cleaned and len(cleaned.split()) >= 1:
                    return cleaned

    return ""


def extract_nationality(text: str) -> str:
    if not text:
        return ""
    m = re.search(r'\bnationality\b\s*[:\-–—]?\s*([a-zA-Z]+)', text, re.I)
    if m:
        return m.group(1).strip().capitalize()
    m2 = re.search(r'\bcitizenship\b\s*[:\-–—]?\s*([a-zA-Z]+)', text, re.I)
    if m2:
        return m2.group(1).strip().capitalize()
    for nat in ['Indian', 'American', 'British', 'Canadian', 'Australian', 'German', 'French']:
        if re.search(rf'\b{nat}\b', text, re.I):
            return nat
    return "Indian"


def extract_country(text: str) -> str:
    if not text:
        return ""
    countries = ['India', 'United States', 'USA', 'United Kingdom', 'UK', 'Canada', 'Australia', 'Germany', 'France', 'Singapore']
    for country in countries:
        if re.search(rf'\b{re.escape(country)}\b', text, re.I):
            if country.upper() in ['USA', 'UNITED STATES']:
                return "United States"
            if country.upper() in ['UK', 'UNITED KINGDOM']:
                return "United Kingdom"
            return country.capitalize()
    if re.search(r'\b\d{6}\b', text) or any(k in text.lower() for k in ['jharkhand', 'maharashtra', 'karnataka', 'tamil nadu', 'delhi', 'mumbai', 'pune', 'bengaluru', 'chennai', 'hyderabad']):
        return "India"
    return "India"


def extract_address(text: str) -> str:
    if not text:
        return ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    address_lines = []
    found_header = False
    
    for idx, line in enumerate(lines[:50]):
        low = line.lower()
        if re.match(r'^(?:permanent\s+|present\s+|correspondence\s+|office\s+|contact\s+)?address\b\s*[:\-–—]?$', low):
            found_header = True
            for j in range(1, 6):
                if idx + j < len(lines):
                    next_line = lines[idx + j]
                    # Stop if it looks like a new section or next heading
                    if re.match(r'^[A-Z\d\.\-\s]+:', next_line) or len(next_line.split()) > 10:
                        break
                    address_lines.append(next_line)
            break
            
    if address_lines:
        return ", ".join(address_lines).strip()
        
    for idx, line in enumerate(lines[:25]):
        if re.search(r'\b(?:street|road|layout|nagar|colony|district|dist|pin|pincode|zip|floor|building|apartment|house|flat)\b', line, re.I) or re.search(r'\b\d{6}\b', line):
            addr = [line]
            if idx - 1 >= 0 and len(lines[idx-1].split()) <= 6 and not re.search(r'\b(?:email|phone|mobile|fax|dr|prof)\b', lines[idx-1], re.I):
                addr.insert(0, lines[idx-1])
            if idx + 1 < len(lines) and len(lines[idx+1].split()) <= 6 and not re.search(r'\b(?:email|phone|mobile|fax|education|degree)\b', lines[idx+1], re.I):
                addr.append(lines[idx+1])
            return addr.rstrip(',. ')
            
    return ""


def extract_orcid(text: str) -> str:
    if not text:
        return ""
    m = re.search(r'\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b', text, re.I)
    return m.group(0) if m else ""


def extract_google_scholar(text: str) -> str:
    if not text:
        return ""
    m = re.search(r'\b(?:scholar\.google\S+|user=([a-zA-Z0-9_\-]+))\b', text, re.I)
    return m.group(0) if m else ""
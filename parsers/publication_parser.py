import re

YEAR_RE = re.compile(r'(19|20)\d{2}')

# Patterns for detecting numbered or bulleted publication entries
ENTRY_START_RE = re.compile(r'^[\d]+[\).\-]\s+')
BULLET_START_RE = re.compile(r'^[\u2022\-\*]\s+')

# Patterns for extracting metadata from a publication string
IMPACT_FACTOR_RE = re.compile(r'impact\s*factor[:\s]*([0-9]+(?:\.[0-9]+)?)', re.IGNORECASE)
SCOPUS_RE = re.compile(r'scopus', re.IGNORECASE)
ISSN_RE = re.compile(r'ISSN[:\s]*[\dX\-]+', re.IGNORECASE)
DOI_RE = re.compile(r'doi[:\s]*\S+', re.IGNORECASE)

# Count keywords explicitly stated in the resume (e.g. "10 Journal papers")
COUNT_PATTERNS = {
    'journal': re.compile(r'(\d+)\s+journal', re.IGNORECASE),
    'int_conf': re.compile(r'(\d+)\s+international\s+conference', re.IGNORECASE),
    'nat_conf': re.compile(r'(\d+)\s+national\s+conference', re.IGNORECASE),
    'book': re.compile(r'(\d+)\s+book(?!\s+chapter)', re.IGNORECASE),
    'book_chapter': re.compile(r'(\d+)\s+book\s+chapter', re.IGNORECASE),
    'patent': re.compile(r'(\d+)\s+patent', re.IGNORECASE),
}

# Keywords that indicate an entry is NOT a publication (administrative/committee roles)
NON_PUBLICATION_KEYWORDS = [
    "coordinator",
    "co-ordinator",
    "committee",
    "member of",
    "bos",
    "evaluator",
    "judge",
    "judged",
    "moderator",
    "moderation",
    "syllabus",
    "toycathon",
    "responsibilities",
    "administrative",
    "exam",
    "convener",
    "faculty advisor",
    "coordinator of",
]

# At least one of these must be present for an entry to be accepted as a publication
PUBLICATION_INDICATORS = [
    "journal",
    "conference",
    "proceedings",
    "ieee",
    "springer",
    "elsevier",
    "wiley",
    "taylor",
    "scopus",
    "doi",
    "issn",
    "isbn",
    "international journal",
    "transactions",
    "patent",
    "book chapter",
]


def _is_valid_publication(entry: str) -> bool:
    """
    Return True only if the entry looks like a genuine publication.

    Rejects entries that:
      - Contain any NON_PUBLICATION_KEYWORDS (administrative / committee roles).
      - Lack any PUBLICATION_INDICATORS *and* don't have a year + enough words
        to constitute a titled work.
    """
    entry_lower = entry.lower()

    # Immediate reject: administrative / role keywords
    if any(kw in entry_lower for kw in NON_PUBLICATION_KEYWORDS):
        return False

    # Accept if a strong publication signal is present
    if any(ind in entry_lower for ind in PUBLICATION_INDICATORS):
        return True

    # Fallback: accept if there is a plausible year and enough words for a title
    has_year = bool(YEAR_RE.search(entry))
    has_enough_words = len(entry.split()) > 7
    return has_year and has_enough_words


def _classify(entry: str) -> str:
    """Classify a publication entry into a type based on keywords."""
    low = entry.lower()
    if 'patent' in low:
        return 'Patent'
    if 'book chapter' in low:
        return 'Book Chapter'
    if 'book' in low and 'chapter' not in low:
        return 'Book'
    if 'conference' in low or 'proceedings' in low or 'proc.' in low:
        return 'International Conference' if 'international' in low else 'National Conference'
    return 'Journal'


def _split_title_venue(entry: str):
    """
    Attempt to split an entry into (title, venue) using common separators.
    Returns (title, venue) strings; venue may be empty.
    """
    # Remove leading numbering like "1. " or "1) "
    cleaned = re.sub(r'^[\d]+[\).\-]\s+', '', entry).strip()
    cleaned = re.sub(r'^[\u2022\-\*]\s+', '', cleaned).strip()

    # Try splitting on common separator patterns
    for pattern in [r'\s+-\s+', r'\s+–\s+', r'\s+,\s+', r'\s+in\s+(?=[A-Z])', r'\s+In\s+']:
        parts = re.split(pattern, cleaned, maxsplit=1)
        if len(parts) == 2 and len(parts[0].split()) >= 3:
            return parts[0].strip(), parts[1].strip()

    return cleaned, ''


def _extract_journal_details(entry: str) -> dict:
    """
    Extract journal-specific metadata: journal_name, journal_details,
    impact_factor, scopus_indexed from a raw publication string.
    """
    title, venue = _split_title_venue(entry)

    # Impact factor
    if_match = IMPACT_FACTOR_RE.search(entry)
    impact_factor = if_match.group(1) if if_match else 'N/A'

    # Scopus index detection
    scopus_indexed = 'Yes' if SCOPUS_RE.search(entry) else 'Unknown'

    # journal_details: preserve ISSN, DOI, volume/issue/page hints
    details_parts = []
    issn = ISSN_RE.search(entry)
    if issn:
        details_parts.append(issn.group(0))
    doi = DOI_RE.search(entry)
    if doi:
        details_parts.append(doi.group(0))
    # Volume/issue/pages pattern
    vol_match = re.search(r'[Vv]ol\.?\s*\d+.*?(?:pp?\.?\s*[\d\-]+)?', entry)
    if vol_match:
        details_parts.append(vol_match.group(0).strip())

    journal_details = ', '.join(details_parts) if details_parts else venue

    return {
        'journal_name': venue,
        'journal_details': journal_details,
        'impact_factor': impact_factor,
        'scopus_indexed': scopus_indexed,
    }


def _extract_conference_details(entry: str) -> dict:
    """Extract conference-specific metadata: conference_name from a raw entry."""
    _, venue = _split_title_venue(entry)
    return {'conference_name': venue}


def _group_entries(lines: list) -> list:
    """
    Group consecutive lines into individual publication entry strings.
    A new entry begins when a numbered/bulleted pattern or a year is detected
    at the start of a line after at least one prior entry has been found.
    """
    buffer = []
    entries = []

    for line in lines:
        is_new = (
            ENTRY_START_RE.match(line)
            or BULLET_START_RE.match(line)
            or (YEAR_RE.search(line) and len(line.split()) > 5)
        )
        if is_new:
            if buffer:
                entries.append(' '.join(buffer))
            buffer = [line]
        else:
            if buffer:
                # Continuation of the current entry
                buffer.append(line)
            elif len(line.split()) > 6:
                # Standalone long line treated as an entry start
                buffer = [line]

    if buffer:
        entries.append(' '.join(buffer))

    return entries


def parse_publications(text: str) -> dict:
    """
    Parse a block of publication text and return:
      - counts: dict of publication type counts
      - publications: list of structured publication dicts

    Each publication dict contains at minimum:
      type, title, year
    Journal entries also include: journal_name, journal_details,
      impact_factor, scopus_indexed
    Conference entries also include: conference_name
    """
    if not text:
        return {'counts': {}, 'publications': []}

    counts = {
        'journal': 0, 'int_conf': 0, 'nat_conf': 0,
        'book': 0, 'book_chapter': 0, 'patent': 0,
    }

    # Check for explicitly stated counts in the text (e.g. "Published 10 journal papers")
    for key, pat in COUNT_PATTERNS.items():
        m = pat.search(text)
        if m:
            counts[key] = int(m.group(1))

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    raw_entries = _group_entries(lines)

    publications = []

    for entry in raw_entries:
        # Skip anything that isn't a genuine publication entry
        if not _is_valid_publication(entry):
            continue

        pub_type = _classify(entry)

        # Extract year
        y = YEAR_RE.search(entry)
        year = y.group(0) if y else ''

        # Extract title and venue
        title, _ = _split_title_venue(entry)

        pub = {
            'type': pub_type,
            'title': title,
            'year': year,
            'raw': entry,
        }

        # Populate type-specific fields and update counts
        if pub_type == 'Journal':
            pub.update(_extract_journal_details(entry))
            counts['journal'] += 1
        elif pub_type == 'International Conference':
            pub.update(_extract_conference_details(entry))
            pub.update({'impact_factor': 'N/A', 'scopus_indexed': 'Unknown'})
            counts['int_conf'] += 1
        elif pub_type == 'National Conference':
            pub.update(_extract_conference_details(entry))
            pub.update({'impact_factor': 'N/A', 'scopus_indexed': 'Unknown'})
            counts['nat_conf'] += 1
        elif pub_type == 'Book Chapter':
            pub.update({'journal_name': '', 'journal_details': '',
                        'impact_factor': 'N/A', 'scopus_indexed': 'Unknown'})
            counts['book_chapter'] += 1
        elif pub_type == 'Book':
            pub.update({'journal_name': '', 'journal_details': '',
                        'impact_factor': 'N/A', 'scopus_indexed': 'Unknown'})
            counts['book'] += 1
        elif pub_type == 'Patent':
            pub.update({'journal_name': '', 'journal_details': '',
                        'impact_factor': 'N/A', 'scopus_indexed': 'Unknown'})
            counts['patent'] += 1

        publications.append(pub)

    return {'counts': counts, 'publications': publications}


# ---------------------------------------------------------------------------
# Designation extraction helper (use in experience_parser.py)
# ---------------------------------------------------------------------------

# Matches date-range prefixes like "Nov 2023 – Till date: " or "2019-2021: "
_DESIGNATION_PREFIX_RE = re.compile(
    r'^[\w\s,.\-–/]+(?:till\s*date|present|current|\d{4})\s*[:\-–]\s*',
    re.IGNORECASE,
)

# Matches leading verbs like "Working as ", "Serving as ", "Appointed as "
_WORKING_AS_RE = re.compile(r'^(?:working|serving|appointed|joined|designated)\s+as\s+', re.IGNORECASE)


def extract_designation(raw: str) -> str:
    """
    Strip date-range prefixes and leading role-verbs from an experience string
    so that only the job title remains.

    Examples
    --------
    "Nov 2023 – Till date: Working as Dean (Admin. and Faculty) and Professor"
        → "Dean (Admin. and Faculty) and Professor"

    "2019-2021: Associate Professor"
        → "Associate Professor"

    "Professor"
        → "Professor"
    """
    text = raw.strip()
    # Remove date-range prefix (greedy up to the colon/dash separator)
    text = _DESIGNATION_PREFIX_RE.sub('', text).strip()
    # Remove "Working as " / "Serving as " etc.
    text = _WORKING_AS_RE.sub('', text).strip()
    return text
import re

YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')

# Patterns for detecting numbered or bulleted publication entries
ENTRY_START_RE = re.compile(r'^\d{1,2}[\).\-](?:\s+|$)')
BULLET_START_RE = re.compile(r'^[\u2022\-\*](?:\s+|$)')

# Patterns for extracting metadata
IMPACT_FACTOR_RE = re.compile(r'impact\s*factor[:\s]*([0-9]+(?:\.[0-9]+)?)', re.IGNORECASE)
SCOPUS_RE = re.compile(r'scopus', re.IGNORECASE)
ISSN_RE = re.compile(r'\b(?:issn|isbn)[:\s]*([\dX\-]+)', re.IGNORECASE)
DOI_RE = re.compile(r'\b(?:doi[:\s/]*|https?://(?:dx\.)?doi\.org/)\s*(\S+)', re.IGNORECASE)

COUNT_PATTERNS = {
    'journal': re.compile(r'(\d+)\s+journal', re.IGNORECASE),
    'int_conf': re.compile(r'(\d+)\s+international\s+conference', re.IGNORECASE),
    'nat_conf': re.compile(r'(\d+)\s+national\s+conference', re.IGNORECASE),
    'book': re.compile(r'(\d+)\s+book(?!\s+chapter)', re.IGNORECASE),
    'book_chapter': re.compile(r'(\d+)\s+book\s+chapter', re.IGNORECASE),
    'patent': re.compile(r'(\d+)\s+patent', re.IGNORECASE),
}

# Keywords indicating administrative/non-publication entries
NON_PUBLICATION_KEYWORDS = [
    "coordinator", "co-ordinator", "committee", "member of", "bos", "evaluator",
    "judge", "judged", "moderator", "moderation", "syllabus", "toycathon",
    "responsibilities", "administrative", "exam", "convener", "faculty advisor",
    "coordinator of", "attended", "participated", "worked as", "working as",
    "project description", "team functionality", "hereby declare", "declaration",
    "place:", "date:"
]

PUBLICATION_INDICATORS = [
    "journal", "conference", "proceedings", "ieee", "springer", "elsevier",
    "wiley", "taylor", "scopus", "doi", "issn", "isbn", "international journal",
    "transactions", "patent", "book chapter"
]


def _is_valid_publication(entry: str) -> bool:
    entry_lower = entry.lower()
    if any(kw in entry_lower for kw in NON_PUBLICATION_KEYWORDS):
        return False
    if any(ind in entry_lower for ind in PUBLICATION_INDICATORS):
        return True
    has_year = bool(YEAR_RE.search(entry))
    has_enough_words = len(entry.split()) > 7
    return has_year and has_enough_words


def _classify_with_reason(entry: str) -> tuple:
    low = entry.lower()
    if 'patent' in low:
        return 'Patent', "Contains keyword 'patent'"
    if 'book chapter' in low:
        return 'Book Chapter', "Contains keyword 'book chapter'"
    if 'book' in low and 'chapter' not in low:
        return 'Book', "Contains keyword 'book'"
    if 'thesis' in low or 'dissertation' in low:
        return 'Thesis', "Contains keyword 'thesis' or 'dissertation'"
    if 'magazine' in low:
        return 'Magazine', "Contains keyword 'magazine'"
    if 'workshop' in low:
        return 'Workshop', "Contains keyword 'workshop'"
    if 'seminar' in low:
        return 'Seminar', "Contains keyword 'seminar'"
    if 'poster' in low:
        return 'Poster', "Contains keyword 'poster'"
    if 'report' in low:
        return 'Report', "Contains keyword 'report'"
    if 'conference' in low or 'proceedings' in low or 'proc.' in low or 'symposium' in low or 'workshop' in low or 'seminar' in low or 'poster' in low:
        t = 'International Conference' if 'international' in low else 'National Conference'
        r = "Contains conference/proceedings indicator keywords"
        return t, r
    return 'Journal', "Default classification (no other type keywords matched)"


def _classify(entry: str) -> str:
    pub_type, _ = _classify_with_reason(entry)
    return pub_type


def _split_title_venue(entry: str):
    cleaned = re.sub(r'^[\d]+[\).\-]\s+', '', entry).strip()
    cleaned = re.sub(r'^[\u2022\-\*]\s+', '', cleaned).strip()

    # Check for quotes
    quote_match = re.search(r'[“"‘\'](.*?)[”"’\']', cleaned)
    if quote_match:
        title = quote_match.group(1).strip()
        remaining = cleaned[quote_match.end():].strip()
        remaining = re.sub(r'^[,.\s\-–—/]+', '', remaining).strip()
        remaining = re.sub(r'^(?:in|at|published in|published at)\s+', '', remaining, flags=re.I).strip()
        return title, remaining

    # Fallback split patterns
    for pattern in [r'\s+-\s+', r'\s+–\s+', r'\s+,\s+', r'\s+in\s+(?=[A-Z])', r'\s+In\s+']:
        parts = re.split(pattern, cleaned, maxsplit=1)
        if len(parts) == 2 and len(parts[0].split()) >= 3:
            return parts[0].strip(), parts[1].strip()

    return cleaned, ''


def _extract_publisher(entry: str, venue: str) -> str:
    low = entry.lower()
    PUBLISHERS = [
        'Springer', 'Elsevier', 'IEEE', 'Wiley', 'Taylor & Francis', 'ACM', 'Inderscience',
        'Nature Portfolio', 'Oxford University Press', 'Cambridge University Press', 'PLOS', 'Sage', 'MDPI'
    ]
    for pub in PUBLISHERS:
        if re.search(rf'\b{re.escape(pub)}\b', entry, re.I):
            return pub
            
    m = re.search(r'\b(?:published\s+by|publisher\b)\s*[:\-–—]?\s*([^,\(]+)', entry, re.I)
    if m:
        return m.group(1).strip().strip('"\'')
        
    if venue:
        for pub in PUBLISHERS:
            if re.search(rf'\b{re.escape(pub)}\b', venue, re.I):
                return pub
                
    return "Unknown"


def _extract_doi(entry: str) -> str:
    m = DOI_RE.search(entry)
    if m:
        return m.group(1).strip().rstrip(',.()[]{}')
    return ""


def _extract_issn_isbn(entry: str) -> str:
    m = ISSN_RE.search(entry)
    if m:
        return m.group(1).strip().rstrip(',. ')
    return ""


def _group_entries(lines: list) -> list:
    entries = []
    buffer = []
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        is_continuation = (
            line_str.lower().startswith(('vol', 'volume', 'issue', 'no.', 'pp.', 'p.', 'page', 'pages', 'issn', 'isbn', 'doi', 'https:', 'http:', 'www.')) or
            line_str[0].islower()
        )
        if is_continuation and buffer:
            buffer.append(line_str)
        else:
            if buffer:
                entries.append(" ".join(buffer))
            buffer = [line_str]
    if buffer:
        entries.append(" ".join(buffer))
    return entries


def parse_publications(text: str) -> dict:
    try:
        return _parse_publications_impl(text)
    except Exception as e:
        print(f"Warning in parse_publications: {e}")
        return {
            'counts': {
                'journal': 0, 'int_conf': 0, 'nat_conf': 0,
                'book': 0, 'book_chapter': 0, 'patent': 0,
            },
            'publications': []
        }


def _parse_publications_impl(text: str) -> dict:
    if not text or not isinstance(text, str):
        return {'counts': {}, 'publications': []}

    text = text.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '').replace('\u200e', '').replace('\u200f', '').replace('\ufeff', '')

    counts = {
        'journal': 0, 'int_conf': 0, 'nat_conf': 0,
        'book': 0, 'book_chapter': 0, 'patent': 0,
    }

    explicit_counts = {
        'journal': 0, 'int_conf': 0, 'nat_conf': 0,
        'book': 0, 'book_chapter': 0, 'patent': 0,
    }
    
    flat_text = re.sub(r'\s+', ' ', text)
    
    def get_clean_count(m):
        if not m:
            return 0
        val_str = m.group(1) if m.group(1) else m.group(2)
        if val_str:
            val = int(val_str)
            if not (1900 <= val <= 2100):
                return val
        return 0

    m_int_j = re.search(r'\binternational\s+journal[s]?\b[\s\:\-\–\—\=\(]*(\d+)\b|\b(\d+)\s*international\s+journal[s]?\b', flat_text, re.I)
    m_j = re.search(r'\bjournal[s]?\b[\s\:\-\–\—\=\(]*(\d+)\b|\b(\d+)\s*journal[s]?\b', flat_text, re.I)
    explicit_counts['journal'] = get_clean_count(m_int_j) or get_clean_count(m_j)

    m_int_c = re.search(r'\binternational\s+conference[s]?\b[\s\:\-\–\—\=\(]*(\d+)\b|\b(\d+)\s*international\s+conference[s]?\b', flat_text, re.I)
    explicit_counts['int_conf'] = get_clean_count(m_int_c)

    m_nat_c = re.search(r'\bnational\s+conference[s]?\b[\s\:\-\–\—\=\(]*(\d+)\b|\b(\d+)\s*national\s+conference[s]?\b', flat_text, re.I)
    explicit_counts['nat_conf'] = get_clean_count(m_nat_c)

    m_b = re.search(r'\bbook[s]?\b(?![\s\-\–\—]*chapter)[\s\:\-\–\—\=\(]*(\d+)\b|\b(\d+)\s*book[s]?\b(?![\s\-\–\—]*chapter)', flat_text, re.I)
    explicit_counts['book'] = get_clean_count(m_b)

    m_bc = re.search(r'\bbook\s+chapter[s]?\b[\s\:\-\–\—\=\(]*(\d+)\b|\b(\d+)\s*book\s+chapter[s]?\b', flat_text, re.I)
    explicit_counts['book_chapter'] = get_clean_count(m_bc)

    m_pat = re.search(r'\bpatent[s]?\b[\s\:\-\–\—\=\(]*(\d+)\b|\b(\d+)\s*patent[s]?\b', flat_text, re.I)
    explicit_counts['patent'] = get_clean_count(m_pat)

    for key, pat in COUNT_PATTERNS.items():
        m = pat.search(text)
        if m:
            val = int(m.group(1))
            if not (1900 <= val <= 2100):
                explicit_counts[key] = max(explicit_counts[key], val)

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line_split = re.sub(r'\s+(\d+[\.\)\-]\s+)', r'\n\1', line)
        for part in line_split.splitlines():
            if part.strip():
                lines.append(part.strip())

    raw_entries = _group_entries(lines)
    publications = []
    debug_publications = []

    for entry in raw_entries:
        if not _is_valid_publication(entry):
            continue

        pub_type, reason = _classify_with_reason(entry)
        y = YEAR_RE.search(entry)
        year = y.group(0) if y else ''

        title, venue = _split_title_venue(entry)
        publisher = _extract_publisher(entry, venue)
        doi = _extract_doi(entry)
        issn_isbn = _extract_issn_isbn(entry)
        scopus_indexed = 'Yes' if SCOPUS_RE.search(entry) else 'Unknown'

        pub = {
            'type': pub_type,
            'title': title,
            'journal_name': venue if pub_type in ['Journal', 'International Conference', 'National Conference'] else '',
            'publisher': publisher,
            'year': year,
            'doi': doi,
            'issn': issn_isbn,
            'scopus_indexed': scopus_indexed,
            'raw': entry,
            'classification_reason': reason,
            'confidence': 95 if (title and year) else 70
        }

        if pub_type == 'Journal':
            counts['journal'] += 1
        elif pub_type == 'International Conference':
            counts['int_conf'] += 1
        elif pub_type == 'National Conference':
            counts['nat_conf'] += 1
        elif pub_type == 'Book Chapter':
            counts['book_chapter'] += 1
        elif pub_type == 'Book':
            counts['book'] += 1
        elif pub_type == 'Patent':
            counts['patent'] += 1

        publications.append(pub)
        
        debug_publications.append({
            'Publication detected': entry,
            'Classification': pub_type,
            'Reason': reason,
            'Title': title,
            'Publisher': publisher,
            'Year': year,
            'Confidence': pub['confidence']
        })

    for key in counts.keys():
        counts[key] = max(explicit_counts.get(key, 0), counts[key])

    return {
        'counts': counts,
        'publications': publications,
        'debug_publications': debug_publications
    }
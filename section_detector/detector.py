from typing import Dict, List
import re

# Expanded list of sections to support common academic CV structures
SECTIONS = [
    'education', 'experience', 'publications', 'projects', 'awards', 'patents', 'memberships',
    'fdp', 'certifications', 'research', 'books', 'administrative_work', 'invited_talks',
    'research_funding', 'editorial_board', 'review_committee', 'advisory_committee',
    'technical_committee', 'research_scholars', 'professional_service', 'conference_activity'
]

# Improved keyword map for academic CVs (variations included)
KEYWORDS = {
    'education': ['education', 'educational', 'academic qualification', 'qualification', 'academic qualifications', 'educational qualification', 'academic profile'],
    'experience': ['experience', 'professional experience', 'work experience', 'appointments held', 'employment history', 'service record'],
    'publications': ['publications', 'research publications', 'journal', 'paper', 'papers', 'conference', 'paper publications', 'journal publications'],
    'projects': ['projects', 'project'],
    'awards': ['awards', 'achievements', 'recognition'],
    'patents': ['patents', 'patent'],
    'memberships': ['membership', 'memberships', 'member of', 'membership of'],
    'fdp': ['fdp', 'faculty development', 'faculty development programme', 'faculty development program', 'short term training program', 'sttp', 'training', 'workshop'],
    'certifications': ['certification', 'certifications'],
    'research': ['research', 'research profile', 'research interests'],
    'books': ['books', 'book', 'book chapter', 'book chapters'],
    'administrative_work': ['administrative', 'administration', 'administrative work', 'administrative responsibilities'],
    'invited_talks': ['invited talks', 'invited talk', 'invited lectures', 'invited lecture'],
    'research_funding': ['research funding', 'funding', 'grants', 'projects funded'],
    'editorial_board': ['editorial board', 'editorial'],
    'review_committee': ['review committee', 'reviewer', 'review committee membership'],
    'advisory_committee': ['advisory committee', 'advisory'],
    'technical_committee': ['technical committee', 'technical'],
    'research_scholars': ['research scholars', 'phd scholars', 'students guided', 'students supervised'],
    'professional_service': ['professional service', 'service'],
    'conference_activity': ['conference', 'conferences', 'conference activity', 'conference organisation', 'conference organizing']
}

try:
    from sentence_transformers import SentenceTransformer, util
    _ST_AVAILABLE = True
    # lazy-load model only when needed; do not embed every line
    _EMBED_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    KEY_EMB = {k: _EMBED_MODEL.encode(' '.join(v), convert_to_tensor=True) for k, v in KEYWORDS.items()}
except Exception:
    _ST_AVAILABLE = False


YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')


def looks_like_sentence(line: str) -> bool:
    if not line:
        return False
    if line.endswith('.'):
        return True
    verbs = [' is ', ' are ', ' was ', ' were ', ' has ', ' have ', ' had ', ' worked ', ' joined ', ' serves ', ' served ', ' held ', ' appointed ', ' completed ']
    low = f' {line.lower()} '
    for v in verbs:
        if v in low:
            return True
    words = line.split()
    lower_count = sum(1 for w in words if w and w[0].islower())
    if lower_count >= max(1, len(words) // 2):
        return True
    return False


def is_heading(line: str) -> bool:
    if not line:
        return False
    s = line.strip()
    # Basic length/word constraints
    if len(s) > 200:
        return False
    words = s.split()
    if len(words) > 6:
        return False
    if len(s) >= 60 and not s.isupper() and not s.endswith(':'):
        return False
    # Disqualify if contains years or date ranges
    if YEAR_RE.search(s):
        return False
    # Must not end with a period
    if s.endswith('.'):
        return False
    # Avoid lines with multiple commas (likely affiliation lines)
    if s.count(',') > 1:
        return False
    # Ends with colon or all caps are strong headings
    if s.endswith(':'):
        return True
    if s.isupper():
        return True
    # Avoid lines that look like sentences
    if looks_like_sentence(s):
        return False
    # otherwise consider short lines as possible headings
    if len(s) < 60 and len(words) <= 6:
        non_heading_tokens = ['professor', 'university', 'college', 'department', 'institute', 'hospital']
        low = s.lower()
        if any(tok in low for tok in non_heading_tokens) and any(tok in low for tok in ['department', 'university', 'college']):
            return False
        return True
    return False


def detect_sections(text: str) -> Dict[str, str]:
    """
    Detect sections in academic CV text.

    Primary method: keyword matching + robust heading detection.
    Use sentence-transformer embeddings only as a fallback when a line is detected
    as a heading but no keyword match is found.
    """
    if not text:
        return {k: '' for k in SECTIONS}

    lines = [l.rstrip() for l in text.splitlines()]
    cleaned_lines: List[str] = []
    for l in lines:
        if l.strip() == '':
            if not cleaned_lines or cleaned_lines[-1].strip() == '':
                continue
            cleaned_lines.append('')
        else:
            cleaned_lines.append(l.strip())

    sections: Dict[str, List[str]] = {k: [] for k in SECTIONS}
    current: str = ''

    for i, line in enumerate(cleaned_lines):
        if not line:
            if current:
                sections[current].append('')
            continue

        low = line.lower()
        assigned = False

        # First: keyword match anywhere in the line (strong signal)
        for sec, kws in KEYWORDS.items():
            for kw in kws:
                if kw in low:
                    if is_heading(line) or low.strip().startswith(kw) or len(line.split()) <= 6:
                        current = sec
                        assigned = True
                        break
                    if not current:
                        current = sec
                        assigned = True
                        break
            if assigned:
                break

        # If not assigned, and line looks like a heading, try embedding fallback to map to a section
        if not assigned and is_heading(line):
            if _ST_AVAILABLE:
                try:
                    emb = _EMBED_MODEL.encode(line, convert_to_tensor=True)
                    best = None
                    best_score = 0.0
                    for k, kem in KEY_EMB.items():
                        score = util.pytorch_cos_sim(emb, kem).item()
                        if score > best_score:
                            best_score = score
                            best = k
                    if best_score > 0.45 and best:
                        current = best
                        assigned = True
                except Exception:
                    assigned = False

        if not assigned and current:
            sections[current].append(line)
            continue

        if assigned and current:
            continue

    return {k: '\n'.join(v).strip() for k, v in sections.items()}

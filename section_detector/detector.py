from typing import Dict, List, Optional
import re

# Expanded list of sections to support common academic CV structures
SECTIONS = [
    'education', 'experience', 'fdp', 'publications', 'projects', 'awards', 'patents', 'memberships',
    'certifications', 'research', 'administrative_work', 'invited_talks',
    'research_funding', 'editorial_board', 'review_committee', 'advisory_committee',
    'technical_committee', 'research_scholars', 'professional_service'
]

# Improved keyword map for academic CVs (variations included)
KEYWORDS = {
    'education': ['education', 'educational', 'academic qualification', 'qualification', 'academic qualifications', 'educational qualification', 'academic profile'],
    'experience': ['experience', 'professional experience', 'work experience', 'appointments held', 'employment history', 'service record', 'employment', 'present employment', 'past experiences', 'past experience', 'teaching experience', 'teaching experiences', 'employment record', 'career profile', 'professional record'],
    'fdp': ['fdp', 'faculty development', 'faculty development programme', 'faculty development program', 'short term training program', 'sttp', 'training', 'workshop'],
    'publications': ['publications', 'research publications', 'journal', 'paper', 'papers', 'conference', 'paper publications', 'journal publications', 'books', 'book', 'book chapter', 'book chapters', 'proceedings', 'conferences'],
    'projects': ['projects', 'project'],
    'awards': ['awards', 'achievements', 'recognition'],
    'patents': ['patents', 'patent'],
    'memberships': ['membership', 'memberships', 'member of', 'membership of'],
    'certifications': ['certification', 'certifications'],
    'research': ['research', 'research profile', 'research interests'],
    'administrative_work': ['administrative', 'administration', 'administrative work', 'administrative responsibilities'],
    'invited_talks': ['invited talks', 'invited talk', 'invited lectures', 'invited lecture'],
    'research_funding': ['research funding', 'funding', 'grants', 'projects funded'],
    'editorial_board': ['editorial board', 'editorial'],
    'review_committee': ['review committee', 'reviewer', 'review committee membership'],
    'advisory_committee': ['advisory committee', 'advisory'],
    'technical_committee': ['technical committee', 'technical'],
    'research_scholars': ['research scholars', 'phd scholars', 'students guided', 'students supervised'],
    'professional_service': ['professional service', 'service']
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
    if len(words) <= 4:
        return False
    lower_count = sum(1 for w in words if w and w[0].islower() and w.lower() not in ['and', 'or', 'of', 'in', 'at', 'on', 'with', 'for', 'to', 'by'])
    if lower_count >= max(2, len(words) // 2):
        return True
    return False


def is_strong_section_heading(line: str) -> Optional[str]:
    s = line.strip().lower()
    # Strip numbering at the start, e.g. "III. Past Experiences" -> "past experiences"
    s_clean = re.sub(r'^(?:[ivxlcdm]+\.|\d+\.|\b[a-z]\b\.?)\s+', '', s).strip()
    s_clean = s_clean.rstrip(':').strip()
    
    # Precise mapped phrases for section headings
    HEADING_MAP = {
        'education': [
            'education', 'educational', 'academic qualification', 'qualification', 'academic qualifications', 
            'educational qualification', 'educational qualifications', 'academic profile', 'academic record', 'academic background'
        ],
        'experience': [
            'experience', 'professional experience', 'work experience', 'appointments held', 'employment history', 
            'service record', 'employment', 'present employment', 'past experiences', 'past experience', 
            'teaching experience', 'teaching experiences', 'employment record', 'career profile', 'professional record',
            'present position', 'present positions', 'position held', 'positions held', 'professional history', 
            'work history', 'teaching & research experience', 'teaching and research experience', 'academic experience',
            'academic experiences', 'academic appointments', 'academic appointment', 'designation', 'designations'
        ],
        'fdp': [
            'fdp', 'faculty development', 'faculty development programme', 'faculty development program', 
            'short term training program', 'sttp', 'training', 'workshop', 'workshops', 'short term courses'
        ],
        'publications': [
            'publications', 'research publications', 'journal', 'paper', 'papers', 'conference', 'paper publications', 
            'journal publications', 'books', 'book', 'book chapter', 'book chapters', 'proceedings', 'conferences',
            'list of publications', 'publications list', 'selected publications'
        ],
        'projects': ['projects', 'project', 'sponsored projects', 'sponsored project', 'research projects', 'research project', 'consultancy projects'],
        'awards': ['awards', 'achievements', 'recognition', 'awards & achievements', 'honors', 'honour', 'honours', 'distinctions'],
        'patents': ['patents', 'patent', 'patents filed', 'patents granted'],
        'memberships': ['membership', 'memberships', 'member of', 'membership of', 'professional memberships', 'professional membership', 'professional bodies'],
        'certifications': ['certification', 'certifications', 'certification courses'],
        'research': ['research', 'research profile', 'research interests', 'research interest'],
        'administrative_work': ['administrative', 'administration', 'administrative work', 'administrative responsibilities', 'administrative experience', 'administrative experiences', 'administrative status'],
        'invited_talks': ['invited talks', 'invited talk', 'invited lectures', 'invited lecture', 'guest lectures', 'expert lectures', 'expert talk'],
        'research_funding': ['research funding', 'funding', 'grants', 'projects funded', 'research grants'],
        'editorial_board': ['editorial board', 'editorial boards', 'editorial membership'],
        'review_committee': ['review committee', 'reviewer', 'review committee membership', 'reviewer of journals', 'journal reviewer', 'reviews'],
        'advisory_committee': ['advisory committee', 'advisory boards', 'advisory board'],
        'technical_committee': ['technical committee', 'technical programme committee', 'technical program committee', 'tpc'],
        'research_scholars': ['research scholars', 'phd scholars', 'students guided', 'students supervised', 'thesis supervision', 'ph d supervision', 'supervision'],
        'professional_service': ['professional service', 'service']
    }
    
    # Exact match check
    for sec, phrases in HEADING_MAP.items():
        if s_clean in phrases:
            return sec
            
    # Restricted short matches
    words = s_clean.split()
    if len(words) <= 4:
        for sec, phrases in HEADING_MAP.items():
            for p in phrases:
                if p in s_clean:
                    return sec
    return None


def merge_wrapped_lines(lines: List[str]) -> List[str]:
    merged = []
    for line in lines:
        line_str = line.strip()
        if not line_str:
            if merged and merged[-1] != "":
                merged.append("")
            continue
        if not merged:
            merged.append(line_str)
            continue
            
        prev = merged[-1]
        should_merge = False
        if prev and not prev.endswith(('.', ':', ';', '!', '?')):
            starts_with_bullet = line_str.startswith(('●', '❖', '*', '-', '▪', '•', '', '✔', '▪', '■', '✦', '★', '·', '', '\uf0b7', '\uf0b8', '\u2022', '\uf0d8'))
            starts_with_num = re.match(r'^(?:[ivxlcdm]+\.|\d+\.|\b[a-z]\b\.?)\s+', line_str, re.I)
            
            if not starts_with_bullet and not starts_with_num and not is_strong_section_heading(line_str):
                if not is_strong_section_heading(prev):
                    should_merge = True
                    
        if should_merge:
            merged[-1] = merged[-1] + " " + line_str
        else:
            merged.append(line_str)
    return merged


def detect_sections(text: str) -> Dict[str, str]:
    if not text:
        return {k: '' for k in SECTIONS}

    lines = [l.strip() for l in text.splitlines()]
    merged_lines = merge_wrapped_lines(lines)
    
    sections: Dict[str, List[str]] = {k: [] for k in SECTIONS}
    current: Optional[str] = None
    
    for line in merged_lines:
        if not line:
            if current:
                sections[current].append('')
            continue
            
        sec = is_strong_section_heading(line)
        if sec:
            current = sec
            continue
            
        # Sentence Transformer Fallback for Capitalized Headings
        if not sec and current and len(line.split()) <= 4 and line.isupper():
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
                    if best_score > 0.6 and best:
                        current = best
                        continue
                except Exception:
                    pass
                    
        if current:
            sections[current].append(line)
            
    return {k: '\n'.join(v).strip() for k, v in sections.items()}

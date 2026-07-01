import re

# Clean function
def clean_val(val: str) -> str:
    val = re.sub(r'^[•\-\*●❖\uf0d8\uf0b7\s_·]+', '', val)
    return val.strip()

def _extract_institutions(line_no_score: str) -> tuple:
    univ = ""
    inst = ""
    
    # Try affiliation split first
    aff_parts = re.split(r'\b(?:affiliated\s+(?:to|under|with)|under|affiliated|approved\s+by)\b', line_no_score, flags=re.I)
    if len(aff_parts) == 2:
        part_inst = aff_parts[0].strip()
        part_univ = aff_parts[1].strip()
        
        # Univ
        univ_match = re.search(r'\b([^,\(]+(?:university|univ|board|school|college|institute|iit|nit|iiit|bits)[^,\(]*)\b', part_univ, re.I)
        univ = univ_match.group(1).strip() if univ_match else part_univ
        
        # Inst
        inst_match = re.search(r'\b([^,\(]+(?:institute|college|school|academy|polytechnic|iit|nit|iiit|bits)[^,\(]*)\b', part_inst, re.I)
        inst = inst_match.group(1).strip() if inst_match else part_inst
    else:
        # Check commas
        parts = [p.strip() for p in re.split(r'[,|–\-]', line_no_score) if p.strip()]
        for part in parts:
            if re.search(r'\b(?:university|univ|board)\b', part, re.I) and not univ:
                univ = part
            elif re.search(r'\b(?:institute|college|school|academy)\b', part, re.I) and not inst:
                inst = part
                
        if not univ:
            m = re.search(r'\b([^,\(]+(?:university|univ|board|iit|nit|iiit|bits)[^,\(]*)\b', line_no_score, re.I)
            univ = m.group(1).strip() if m else ""
        if not inst:
            m = re.search(r'\b([^,\(]+(?:institute|college|school|academy|iit|nit|iiit|bits)[^,\(]*)\b', line_no_score, re.I)
            inst = m.group(1).strip() if m else ""
            
    # Clean prefix/suffixes
    def clean_edu_name(val: str) -> str:
        if not val:
            return ""
        val = re.sub(r'^(?:from|at|under|of|affiliated\s+to|affiliated\s+under|awarded\s+from|by)\s+', '', val, flags=re.I).strip()
        val = re.sub(r'\b(?:in\s+)?(?:19|20)\d{2}\b.*$', '', val, flags=re.I).strip()
        val = val.rstrip(',. ')
        return val.strip()
        
    univ = clean_edu_name(univ)
    inst = clean_edu_name(inst)
    
    if not inst and univ:
        inst = univ
    if not univ and inst:
        univ = inst
        
    return inst, univ

def parse_education(text: str) -> dict:
    try:
        return _parse_education_impl(text)
    except Exception as e:
        print(f"Warning in parse_education: {e}")
        return {
            "ug_degree": "", "ug_branch": "", "ug_university": "", "ug_institute": "", "ug_year": "",
            "pg_degree": "", "pg_branch": "", "pg_university": "", "pg_institute": "", "pg_year": "",
            "phd_university": "", "phd_institute": "", "phd_year": ""
        }


def _parse_education_impl(text: str) -> dict:
    result = {
        "ug_degree": "", "ug_branch": "", "ug_university": "", "ug_institute": "", "ug_year": "",
        "pg_degree": "", "pg_branch": "", "pg_university": "", "pg_institute": "", "pg_year": "",
        "phd_university": "", "phd_institute": "", "phd_year": ""
    }

    if not text or not isinstance(text, str):
        return result

    raw_lines = [l.strip() for l in text.splitlines() if l.strip()]
    lines = []
    for line in raw_lines:
        low = line.lower()
        # Stop processing if we hit another section header
        if not 'education' in low and re.match(r'^(?:[ivxlcdm]+[\.\)\-\s]|present\b|employment\b|experience\b|publication\b|project\b|work\b|certification\b|area\b|interest\b|workshop\b|keynote\b)', low):
            break
            
        is_new = (
            re.match(r'^[•\-\*●❖\uf0d8\uf0b7\uf0fc■·]', line)
            or re.match(r'^\d+[\.\)\-]', line)
            or re.match(r'^(?:p\s*\.?\s*h\s*\.?\s*d\s*\.?|doctor\s+of|m\s*\.?\s*e\s*\.?\b|m\s*\.?\s*tech\b|m\s*\.?\s*s\s*\.?\s*c\s*\.?\b|m\s*\.?\s*a\s*\.?\b|m\s*\.?\s*com\s*\.?\b|m\s*\.?\s*b\s*\.?\s*a\s*\.?\b|m\s*\.?\s*c\s*\.?\s*a\s*\.?\b|m\s*\.?\s*phil\s*\.?\b|master\b|b\s*\.?\s*e\s*\.?\b|b\s*\.?\s*tech\b|b\s*\.?\s*s\s*\.?\s*c\s*\.?\b|b\s*\.?\s*a\s*\.?\b|b\s*\.?\s*com\s*\.?\b|b\s*\.?\s*b\s*\.?\s*a\s*\.?\b|b\s*\.?\s*c\s*\.?\s*a\s*\.?\b|bachelor\b)', line, re.I)
            or re.match(r'^\d{4}\b', line)
        )
        if is_new or not lines:
            lines.append(line)
        else:
            lines[-1] = lines[-1] + " " + line

    found_phd = False
    found_pg = False
    found_ug = False

    PHD_RE = re.compile(r'\b(?:p\s*\.?\s*h\s*\.?\s*d\s*\.?|doctor\s+of\s+philosophy)\b', re.I)
    PG_RE = re.compile(r'\b(?:m\s*\.?\s*e\s*\.?|m\s*\.?\s*tech|m\s*\.?\s*s\s*\.?\s*c\s*\.?|m\s*\.?\s*a\s*\.?|m\s*\.?\s*com\s*\.?|m\s*\.?\s*b\s*\.?\s*a\s*\.?|m\s*\.?\s*c\s*\.?\s*a\s*\.?|m\s*\.?\s*phil\s*\.?|master(?:\'s)?)\b', re.I)
    UG_RE = re.compile(r'\b(?:b\s*\.?\s*e\s*\.?|b\s*\.?\s*tech|b\s*\.?\s*s\s*\.?\s*c\s*\.?|b\s*\.?\s*a\s*\.?|b\s*\.?\s*com\s*\.?|b\s*\.?\s*b\s*\.?\s*a\s*\.?|b\s*\.?\s*c\s*\.?\s*a\s*\.?|bachelor(?:\'s)?)\b', re.I)

    for idx, line in enumerate(lines):
        low = line.lower()
        
        # Skip thesis topic / title / supervisor lines for PhD
        if re.match(r'^(?:ph\.?d\.?\s+)?(?:topic|title|supervisor|thesis|synopsis|dissertation)\b', low):
            continue
            
        is_phd = bool(PHD_RE.search(low))
        is_pg = bool(PG_RE.search(low))
        is_ug = bool(UG_RE.search(low))

        # Year extraction
        year_match = re.search(r'\b((?:19|20)\d{2})\b', line)
        year = year_match.group(1) if year_match else ""
        line_no_year = re.sub(r'\b(?:19|20)\d{2}\b', '', line).strip()
        line_no_score = re.sub(r'\b(?:\d{1,2}(?:\.\d{1,2})?%|\b(?:cgp[a]?\s*)?\d\.\d{1,2}(?:\s*/\s*10)?)\b', '', line_no_year, flags=re.I).strip()

        # University and Institute extraction
        inst, univ = _extract_institutions(line_no_score)

        # Branch extraction
        branch = ""
        branch_match = re.search(r'\bin\s+([^,\(]+)\b', line_no_score, re.I)
        if branch_match:
            branch = branch_match.group(1).strip()
        else:
            paren_match = re.search(r'\(([^)]+)\)', line_no_score)
            if paren_match:
                branch = paren_match.group(1).strip()
        if branch:
            branch = re.split(r'\b(?:from|awarded|affiliated|under|at|university|college|institute)\b', branch, flags=re.I)[0].strip()
            branch = branch.rstrip(',. ')
            if branch.lower().replace('.', '').strip() in ['be', 'btech', 'bsc', 'ba', 'me', 'mtech', 'msc', 'ma', 'phd', 'mba', 'mca', 'bca', 'bba']:
                branch = ""
                
        if not branch:
            comma_parts = [p.strip() for p in re.split(r'[,|–\-]', line_no_score) if p.strip()]
            for part in comma_parts:
                part_clean = clean_val(part)
                if re.search(r'\b(?:engineering|science|technology|arts|commerce|mathematics|math|physics|chemistry|biology|english|literature|history|economics|social|management|business|applications|information)\b', part_clean, re.I):
                    if not re.search(r'\b(?:university|college|institute|iit|nit|school|board)\b', part_clean, re.I):
                        if not re.search(r'\b(?:bachelor|master|doctor|degree)\b', part_clean, re.I):
                            branch = part_clean
                            break

        if is_phd and not found_phd:
            result["phd_university"] = univ if univ else clean_val(line_no_score)
            result["phd_institute"] = inst if inst else clean_val(line_no_score)
            result["phd_year"] = year
            found_phd = True
        elif is_pg and not found_pg:
            deg_match = PG_RE.search(line_no_score)
            result["pg_degree"] = deg_match.group(0).strip().upper() if deg_match else "Master"
            result["pg_branch"] = branch
            result["pg_university"] = univ
            result["pg_institute"] = inst
            result["pg_year"] = year
            found_pg = True
        elif is_ug and not found_ug:
            deg_match = UG_RE.search(line_no_score)
            result["ug_degree"] = deg_match.group(0).strip().upper() if deg_match else "Bachelor"
            result["ug_branch"] = branch
            result["ug_university"] = univ
            result["ug_institute"] = inst
            result["ug_year"] = year
            found_ug = True

    return result
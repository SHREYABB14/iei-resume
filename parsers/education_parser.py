import re

YEAR_RE = re.compile(r'(19|20)\d{2}')

UG_PATTERNS = [
    'b.e', 'be ', 'b.tech', 'btech',
    'b.sc', 'bsc', 'bachelor'
]

PG_PATTERNS = [
    'm.e', 'me ', 'm.tech', 'mtech',
    'm.sc', 'msc', 'mba', 'master'
]

PHD_PATTERNS = [
    'ph.d', 'phd', 'doctor of philosophy'
]


def parse_education(text: str):

    result = {
        "ug_degree": "",
        "ug_branch": "",
        "ug_university": "",
        "ug_year": "",
        "pg_degree": "",
        "pg_branch": "",
        "pg_university": "",
        "pg_year": "",
        "phd_university": "",
        "phd_year": ""
    }

    if not text:
        return result

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for line in lines:

        low = line.lower()

        year_match = YEAR_RE.search(line)
        year = year_match.group(0) if year_match else ""

        if any(x in low for x in PHD_PATTERNS):
            result["phd_university"] = line
            result["phd_year"] = year

        elif any(x in low for x in PG_PATTERNS):
            if not result["pg_degree"]:
                result["pg_degree"] = line
                result["pg_year"] = year

        elif any(x in low for x in UG_PATTERNS):
            if not result["ug_degree"]:
                result["ug_degree"] = line
                result["ug_year"] = year

    return result
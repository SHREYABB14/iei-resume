"""
experience_parser.py

Parses the *raw text* of a resume's "Experience" section (exactly what
section_detector.detect_sections() hands back as sections['experience'] —
a plain string, not structured JSON) and computes:

    Academic Experience, Industry Experience, Research Experience,
    Administrative Experience, Total Experience

plus the current designation / department / organization.

-----------------------------------------------------------------------
Why the previous two attempts both failed
-----------------------------------------------------------------------
Attempt 1 (original): split each line on "-". Real resumes write date
ranges with an EN DASH (–, U+2013) almost universally, e.g.:
    "Jan 2011– Jan 2017: Associate Professor..."
A plain "-" almost never appears between two dates, so the split match
silently found nothing on real input. It also choked the moment a
structured "YYYY-MM" string appeared, because that string itself
contains a hyphen.

Attempt 2 (mine, previous revision): I assumed the pipeline already had
an LLM step producing structured JSON like
    {"designation": ..., "start": "2018-08", "end": "2020-11"}
and wrote a parser for THAT shape. It was validated and correct for that
shape — but main.py / evaluator.py never produce that shape. They call
parse_experience() directly on raw section text:
    exp = parse_experience(sections.get('experience', ''))
So my structured-input parser silently fell into "no data" and returned
zeros, same symptom as attempt 1, different cause.

This version fixes the *actual* call: it parses raw resume text directly,
tuned against real examples (see test fixture at the bottom), handling:
    - en dash (–), em dash (—), and hyphen (-) as range separators
    - dates with no space around the dash: "Jan 2011– Jan 2017"
    - 2-digit years: "Nov 23" -> 2023
    - "Till date" / "Present" / "Current" / "Ongoing" / "Continuing"
    - "Month.Year" with no space: "Aug.2000"
    - entries that wrap onto a second physical line (joined back into one
      logical entry before parsing)
    - missing month ("2015 - 2018")
"""

import re
import datetime

TODAY = datetime.date.today()

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

PRESENT_WORDS = re.compile(
    r"^(present|current|currently|ongoing|continuing|till\s*date|to\s*date|now|date)$",
    re.I,
)

# Matches a single date token: "Jan 2011", "Jan.2011", "January 2011", "2011",
# "Nov 23", "Nov'23" — month optional, year 2 or 4 digits, optional separators.
DATE_TOKEN = re.compile(
    r"(?P<month>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)?\.?\s*[',]?\s*(?P<year>\d{4}|\d{2})\b",
    re.I,
)

# Splits a "<date> <dash> <date> : <description>" line. Accepts -, –, —, to/till
# as the range separator, with or without surrounding spaces.
RANGE_LINE = re.compile(
    r"^\s*(?P<start>[A-Za-z.]*\s*\d{2,4})\s*[-–—]\s*"
    r"(?P<end>(?:[A-Za-z.]*\s*\d{2,4})|till\s*date|present|current(?:ly)?|ongoing|now)"
    r"\s*:\s*(?P<desc>.+)$",
    re.I,
)


def _expand_year(y: int) -> int:
    """2-digit year -> 4-digit, assuming 1950-2049 window."""
    if y >= 100:
        return y
    return 2000 + y if y <= 49 else 1900 + y


def _parse_date_token(token: str):
    """Parse a single date token like 'Jan 2011' / 'Aug.2000' / '2011' -> date(first of month)."""
    if not token:
        return None
    token = token.strip().strip(".,")
    if PRESENT_WORDS.match(token):
        return TODAY
    m = DATE_TOKEN.search(token)
    if not m:
        return None
    year_str = m.group("year")
    month_str = m.group("month")
    year = _expand_year(int(year_str))
    month = MONTHS.get(month_str.lower().rstrip(".")) if month_str else 1
    try:
        return datetime.date(year, month or 1, 1)
    except ValueError:
        return None


def _months_between(start, end) -> int:
    if not start or not end or end < start:
        return 0
    return (end.year - start.year) * 12 + (end.month - start.month)


def _merge_intervals(intervals):
    cleaned = [(s, e) for s, e in intervals if s and e and e >= s]
    if not cleaned:
        return 0
    cleaned.sort(key=lambda x: x[0])
    merged = [cleaned[0]]
    for s, e in cleaned[1:]:
        last_s, last_e = merged[-1]
        if s <= last_e:
            merged[-1] = (last_s, max(last_e, e))
        else:
            merged.append((s, e))
    return sum(_months_between(s, e) for s, e in merged)


# ---------------------------------------------------------------------------
# Designation classification — order-independent, a title can match >1 bucket
# ---------------------------------------------------------------------------
ACADEMIC_KEYWORDS = [
    "professor", "lecturer", "faculty", "dean", "instructor", "principal",
    "adjunct", "visiting", "reader", "hag",
]
INDUSTRY_KEYWORDS = [
    "engineer", "developer", "consultant", "analyst", "manager", "executive",
    "officer", "specialist", "architect", "designer", "trainee", "associate consultant",
]
RESEARCH_KEYWORDS = [
    "research", "postdoc", "post-doc", "researcher", "scholar", "fellow",
]
ADMIN_KEYWORDS = [
    "head", "dean", "director", "coordinator", "chair", "chairman",
    "registrar", "warden", "vice chancellor", "hod", "in-charge", "incharge",
    "principal investigator",
]


def _keyword_in(text: str, keyword: str) -> bool:
    """Word-boundary match so 'engineer' doesn't false-positive inside
    'engineering' (e.g. 'Mechanical Engineering Department' must NOT
    classify as Industry just because it contains 'engineer')."""
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return re.search(pattern, text) is not None


def _classify(designation: str):
    low = (designation or "").lower()
    cats = set()
    if any(_keyword_in(low, k) for k in ACADEMIC_KEYWORDS):
        cats.add("academic")
    if any(_keyword_in(low, k) for k in INDUSTRY_KEYWORDS):
        cats.add("industry")
    if any(_keyword_in(low, k) for k in RESEARCH_KEYWORDS):
        cats.add("research")
    if any(_keyword_in(low, k) for k in ADMIN_KEYWORDS):
        cats.add("admin")
    return cats


# ---------------------------------------------------------------------------
# Line joining: a logical resume entry is often wrapped across 2+ physical
# lines by the PDF text extractor. A new entry starts only when a line BEGINS
# with something that looks like a date. Anything else is a continuation of
# the previous entry's description and gets appended to it.
# ---------------------------------------------------------------------------
LINE_STARTS_WITH_DATE = re.compile(
    r"^\s*(?:[A-Za-z]{3,9}\.?\s*)?\d{2,4}\s*[-–—]",
)


def _join_wrapped_lines(raw_text: str):
    lines = [l for l in raw_text.splitlines() if l.strip()]
    joined = []
    for line in lines:
        if LINE_STARTS_WITH_DATE.match(line) or not joined:
            joined.append(line.strip())
        else:
            joined[-1] = joined[-1].rstrip() + " " + line.strip()
    return joined


# ---------------------------------------------------------------------------
# Extracting a designation from the free-text description of one entry.
# Typical phrasing: "Working as X", "Worked as X", "Worked As X in Y",
# or just "X, Department, Y" with no "worked as" lead-in.
# ---------------------------------------------------------------------------
ROLE_LEAD_IN = re.compile(
    r"^\s*(?:working|worked|served|employed)\s+as\s+",
    re.I,
)


def _split_designation_and_org(desc: str):
    """
    Best-effort split of a free-text entry description into
    (designation, organization). Designation = text up to the first
    " in " / " at " / "," that introduces the workplace; organization =
    the remainder. Falls back to the whole string as designation if no
    clear split point is found.
    """
    desc = desc.strip().rstrip(".")
    desc = ROLE_LEAD_IN.sub("", desc, count=1)

    m = re.search(r"\s+(?:in|at)\s+", desc, re.I)
    if m:
        return desc[: m.start()].strip(), desc[m.end():].strip()

    if "," in desc:
        parts = desc.split(",", 1)
        return parts[0].strip(), parts[1].strip()

    return desc.strip(), ""


def parse_experience(text: str) -> dict:
    """
    Main entry point — drop-in replacement for the original
    `parse_experience(text)` signature used by main.py and evaluator.py:

        exp = parse_experience(sections.get('experience', ''))

    Returns:
        {
          'summary': {
              'Academic Experience': float,
              'Industry Experience': float,
              'Research Experience': float,
              'Administrative Experience': float,
              'Total Experience': float,
          },
          'current_designation': str,
          'current_department': str,
          'current_organization': str,
        }
    """
    summary = {
        "Academic Experience": 0.0,
        "Industry Experience": 0.0,
        "Research Experience": 0.0,
        "Administrative Experience": 0.0,
        "Total Experience": 0.0,
    }
    result = {
        "summary": summary,
        "current_designation": "",
        "current_department": "",
        "current_organization": "",
    }
    if not text or not text.strip():
        return result

    entries = _join_wrapped_lines(text)

    category_months = {"academic": 0, "industry": 0, "research": 0, "admin": 0}
    all_intervals = []
    current_candidate = None  # (start_date, designation, organization) for the ongoing/most-recent role

    for line in entries:
        m = RANGE_LINE.match(line)
        if not m:
            continue

        start = _parse_date_token(m.group("start"))
        end_raw = m.group("end").strip()
        end = TODAY if PRESENT_WORDS.match(end_raw) else _parse_date_token(end_raw)
        desc = m.group("desc").strip()

        designation, org = _split_designation_and_org(desc)
        cats = _classify(designation)

        months = _months_between(start, end) if (start and end) else 0
        for c in cats:
            category_months[c] += months

        if start and end:
            all_intervals.append((start, end))

        is_present = PRESENT_WORDS.match(end_raw) is not None
        if is_present or current_candidate is None or (start and start > current_candidate[0]):
            current_candidate = (start or datetime.date.min, designation, org)

    total_months = _merge_intervals(all_intervals)

    summary["Academic Experience"] = round(category_months["academic"] / 12, 2)
    summary["Industry Experience"] = round(category_months["industry"] / 12, 2)
    summary["Research Experience"] = round(category_months["research"] / 12, 2)
    summary["Administrative Experience"] = round(category_months["admin"] / 12, 2)
    summary["Total Experience"] = round(total_months / 12, 2)

    if current_candidate:
        _, designation, org = current_candidate
        result["current_designation"] = designation
        result["current_organization"] = org

    return result


if __name__ == "__main__":
    with open("/home/claude/test_input/nilaj_experience.txt") as f:
        sample_text = f.read()

    out = parse_experience(sample_text)
    print("Parsed result:")
    for k, v in out["summary"].items():
        print(f"  {k}: {v}")
    print("  current_designation:", out["current_designation"])
    print("  current_organization:", out["current_organization"])

    print("\nGold expected (resume_nilaj Jan25.json):")
    print("  Academic Experience: 25.7")
    print("  Industry Experience: 1.8")
    print("  Research Experience: 0")
    print("  Total Experience: 27.5")

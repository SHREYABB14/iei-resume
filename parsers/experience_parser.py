import re
from dateutil import parser as dateparser
from dateutil.relativedelta import relativedelta
import datetime

DATE_RE = re.compile(r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|\d{4})', re.I)


def _parse_date(s):
    try:
        return dateparser.parse(s, default=datetime.datetime(1900,1,1))
    except Exception:
        return None


def parse_experience(text: str) -> dict:
    summary = {
        'Academic Experience': 0.0,
        'Industry Experience': 0.0,
        'Research Experience': 0.0,
        'Administrative Experience': 0.0,
        'Total Experience': 0.0
    }
    current_designation = ''
    current_department = ''
    current_organization = ''

    if not text:
        return {'summary': summary, 'current_designation': current_designation,
                'current_department': current_department, 'current_organization': current_organization}

    lines = [l for l in text.splitlines() if l.strip()]
    # find date ranges
    total_months = 0
    for l in lines:
        m = re.findall(r'(\b\d{4}\b)', l)
        # try to find patterns like 2015-2018 or Jan 2010 - Dec 2014
        if '-' in l:
            parts = l.split('-')
            if len(parts) >= 2:
                d1 = _parse_date(parts[0])
                d2 = _parse_date(parts[1])
                if d1 and d2:
                    rd = relativedelta(d2, d1)
                    months = rd.years * 12 + rd.months
                    total_months += max(0, months)

    total_years = round(total_months/12,2)
    summary['Total Experience'] = total_years
    # naive classification: if 'professor' in any line -> academic
    academic = 0.0
    industry = 0.0
    research = 0.0
    admin = 0.0
    for l in lines:
        low = l.lower()
        if any(x in low for x in ['professor','lecturer','assistant professor','associate professor']):
            academic += 1
        if any(x in low for x in ['engineer','developer','consultant','analyst']):
            industry += 1
        if any(x in low for x in ['research','postdoc','researcher']):
            research += 1
        if any(x in low for x in ['head','dean','director','coordinator','chair']):
            admin += 1

    # distribute total_years proportionally if any counts
    s = academic + industry + research + admin
    if s > 0:
        summary['Academic Experience'] = round(total_years * (academic / s),2)
        summary['Industry Experience'] = round(total_years * (industry / s),2)
        summary['Research Experience'] = round(total_years * (research / s),2)
        summary['Administrative Experience'] = round(total_years * (admin / s),2)
    else:
        summary['Academic Experience'] = round(total_years,2)

    # try to get current designation from first lines
    if lines:
        first = lines[0]
        if ',' in first:
            parts = [p.strip() for p in first.split(',')]
            current_designation = parts[0]
            if len(parts) > 1:
                current_organization = parts[-1]

    return {'summary': summary, 'current_designation': current_designation,
            'current_department': current_department, 'current_organization': current_organization}

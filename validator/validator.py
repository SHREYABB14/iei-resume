import re
import datetime

def validate_extracted_data(personal, edu, exp, pubs) -> list:
    warnings = []
    
    # 1. Total Experience checks
    summary = exp.get('summary', {})
    tot = summary.get('Total Experience', 0.0) or 0.0
    acad = summary.get('Academic Experience', 0.0) or 0.0
    ind = summary.get('Industry Experience', 0.0) or 0.0
    res = summary.get('Research Experience', 0.0) or 0.0
    admin = summary.get('Administrative Experience', 0.0) or 0.0
    
    if tot < acad:
        warnings.append("Total Experience is less than Academic Experience.")
    if tot < 0 or acad < 0 or ind < 0 or res < 0 or admin < 0:
        warnings.append("Negative experience value detected.")
    if tot > 50:
        warnings.append("Experience length (> 50 years) is greater than realistic career length.")
        
    # 2. Current Organization equals University from education
    curr_org = exp.get('current_organization', '').lower().strip()
    if curr_org:
        for deg in ['ug_university', 'pg_university', 'phd_university']:
            u = edu.get(deg, '').lower().strip()
            if u and u == curr_org:
                warnings.append(f"Current organization equals university from education ({deg}).")
                
    # 3. Publication year in future
    current_year = datetime.datetime.now().year
    publications_list = pubs.get('publications', [])
    for pub in publications_list:
        y_str = str(pub.get('year', ''))
        if y_str.isdigit():
            y = int(y_str)
            if y > current_year:
                warnings.append(f"Publication '{pub.get('title')[:30]}...' has year in the future ({y}).")
                
    # 4. PhD year earlier than UG year
    phd_y = str(edu.get('phd_year', ''))
    ug_y = str(edu.get('ug_year', ''))
    if phd_y.isdigit() and ug_y.isdigit():
        if int(phd_y) < int(ug_y):
            warnings.append("PhD year is earlier than UG year.")
            
    # 5. Journal title extracted as publisher / Publisher extracted as paper title
    for pub in publications_list:
        title = pub.get('title', '').lower().strip()
        pub_name = pub.get('publisher', '').lower().strip()
        j_name = pub.get('journal_name', '').lower().strip()
        
        if title == pub_name and title:
            warnings.append(f"Publisher is identical to paper title for '{pub.get('title')[:30]}...'.")
        if j_name == pub_name and j_name and pub_name not in ['springer', 'ieee', 'elsevier', 'wiley', 'acm', 'taylor & francis']:
            warnings.append("Journal name is identical to publisher name.")
            
    # 6. Duplicate publications
    seen_titles = set()
    for pub in publications_list:
        t = pub.get('title', '').lower().strip()
        if t:
            if t in seen_titles:
                warnings.append(f"Duplicate publication detected: '{pub.get('title')[:30]}...'.")
            seen_titles.add(t)
            
    # 7. Duplicate employment records
    seen_jobs = set()
    for job in exp.get('jobs', []):
        org = job.get('organization', '').lower().strip()
        des = job.get('designation', '').lower().strip()
        start = job.get('start_date', '')
        key = (org, des, start)
        if all(key):
            if key in seen_jobs:
                warnings.append(f"Duplicate employment record: {des} at {org}.")
            seen_jobs.add(key)
            
    return warnings


def compute_confidence(personal, edu, exp, pubs) -> int:
    score = 100
    
    # Check for missing crucial fields
    if not personal.get('Name'):
        score -= 20
    if not personal.get('Email'):
        score -= 15
    if not exp.get('current_designation'):
        score -= 10
        
    # Check for incomplete education
    has_ug = bool(edu.get('ug_degree') and edu.get('ug_university'))
    has_pg = bool(edu.get('pg_degree') and edu.get('pg_university'))
    has_phd = bool(edu.get('phd_university') and edu.get('phd_year'))
    if (has_pg or has_phd) and not has_ug:
        score -= 15
    if has_phd and not has_pg and not has_ug:
        score -= 20
        
    # Check for multiple current employers
    current_jobs = 0
    for job in exp.get('jobs', []):
        if job.get('currently_working'):
            current_jobs += 1
    if current_jobs > 1:
        score -= 15
        
    # Missing dates in jobs
    for job in exp.get('jobs', []):
        if not job.get('start_date'):
            score -= 10
            break
            
    # Conflicting experience (warnings count)
    warnings = validate_extracted_data(personal, edu, exp, pubs)
    score -= len(warnings) * 5
    
    return max(0, min(100, score))

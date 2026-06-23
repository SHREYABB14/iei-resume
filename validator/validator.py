def compute_confidence(personal, edu, exp, pubs):
    score = 0
    # personal
    if personal.get('Name'):
        score += 20
    if personal.get('Email'):
        score += 20
    # education
    if edu.get('ug_degree') or edu.get('pg_degree') or edu.get('phd_university'):
        score += 20
    # experience
    if exp.get('summary', {}).get('Total Experience', 0) > 0:
        score += 20
    # publications
    if pubs.get('counts', {}).get('journal', 0) + pubs.get('counts', {}).get('int_conf',0) > 0:
        score += 20
    return min(100, score)

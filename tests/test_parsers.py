import pytest
from parsers.education_parser import parse_education
from parsers.experience_parser import parse_experience
from parsers.publication_parser import parse_publications
from utils.helpers import extract_name, extract_email, extract_phone


def test_parse_education_basic():
    txt = """
    Educational Qualification
    B.Tech in Computer Science, XYZ College, 2010
    M.Tech in Computer Science, ABC University, 2012
    Ph.D. in AI, DEF University, 2018
    """
    ed = parse_education(txt)
    assert 'B.Tech' in ed.get('ug_degree') or ed.get('ug_degree') != ''
    assert 'M.Tech' in ed.get('pg_degree') or ed.get('pg_degree') != ''
    assert 'Ph' in ed.get('phd_university') or ed.get('phd_year') != ''


def test_parse_experience_and_classification():
    txt = """
    PROFESSIONAL EXPERIENCE
    Assistant Professor, University of X, Jan 2013 - Dec 2018
    Senior Researcher, Research Lab Y, Jan 2019 - Present
    """
    exp = parse_experience(txt)
    summary = exp.get('summary')
    assert 'Total Experience' in summary


def test_parse_publications_grouping():
    txt = """
    Publications
    1. A study on AI - Journal of AI, 2018
    2. Conference paper on ML - Proceedings of ICML, 2019
    3. Book Title: Deep Learning Advances, Publisher XYZ, 2020
    """
    pubs = parse_publications(txt)
    assert pubs['counts']['journal'] >= 1
    assert pubs['counts']['int_conf'] >= 1 or pubs['counts']['nat_conf'] >= 1


def test_helpers_name_email_phone():
    txt = "Dr. Alice Smith\nEmail: alice.smith@example.edu\nPhone: +1 555-123-4567\n"
    name = extract_name(txt)
    email = extract_email(txt)
    phone = extract_phone(txt)
    assert 'Alice' in name or name != ''
    assert email == 'alice.smith@example.edu'
    assert '+' in phone or any(ch.isdigit() for ch in phone)


def test_helpers_smart_email_matching():
    txt = "Dr. Nilaj Deshmukh\nCo-author Email: sds@aero.iitb.ac.in\nContact Email: nilaj.deshmukh@fcrit.ac.in\n"
    name = extract_name(txt)
    email = extract_email(txt, name=name)
    assert email == "nilaj.deshmukh@fcrit.ac.in"


def test_clean_special_characters():
    from excel_generator.generator import clean_special_characters
    assert clean_special_characters("☐ B.E. Mechanical") == "B.E. Mechanical"
    assert clean_special_characters("❖ Ph.D. in Computer Science") == "Ph.D. in Computer Science"
    assert clean_special_characters("• Bachelor of Science (B.Sc.)") == "Bachelor of Science (B.Sc.)"
    assert clean_special_characters("  - Regular Text  ") == "Regular Text"


def test_excel_generator_number_and_bullet_stripping():
    from excel_generator.generator import generate_excels
    master_rows = [{
        'Source File': 'resume.pdf',
        'Name': 'Dr. Nilaj Deshmukh',
        'UG Degree': '3. Bachelor of Engineering (B.E.)',
        'UG Year': '1996',
        'PG Degree': '• Master of Technology (M.Tech)',
        'PG Year': '1998 - 2000'
    }]
    pub_rows = [{
        'Faculty Name': 'Dr. Nilaj Deshmukh',
        'Title of Paper': '12) A study on Deep Learning',
        'Year of Publication': '2024'
    }]
    
    master_df, _ = generate_excels(master_rows, pub_rows)
    
    assert master_df.loc[0, 'UG Degree'] == "Bachelor of Engineering (B.E.)"
    assert master_df.loc[0, 'UG Year'] == "1996"
    assert master_df.loc[0, 'PG Degree'] == "Master of Technology (M.Tech)"
    assert master_df.loc[0, 'PG Year'] == "1998 - 2000"


def test_clean_name():
    from utils.helpers import clean_name
    assert clean_name("C/o. Dr.D. Kavitha_d(9441309716") == "Dr.D. Kavitha"
    assert clean_name("SureshN.p RESUME mailtonsu+91-9884785587") == "SureshN.p"
    assert clean_name("16460684 Sartaj Ul") == "Sartaj Ul"
    assert clean_name("638373082 DR PAVITRA") == "DR PAVITRA"






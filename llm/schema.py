import json
import re
from jsonschema import validate, ValidationError

SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "email": {"type": "string"},
        "phone": {"type": "string"},
        "current_designation": {"type": "string"},
        "current_department": {"type": "string"},
        "current_organization": {"type": "string"},
        "education": {
            "type": "object",
            "properties": {
                "ug_degree": {"type": "string"},
                "ug_branch": {"type": "string"},
                "ug_university": {"type": "string"},
                "ug_year": {"type": "string"},
                "pg_degree": {"type": "string"},
                "pg_branch": {"type": "string"},
                "pg_university": {"type": "string"},
                "pg_year": {"type": "string"},
                "phd_university": {"type": "string"},
                "phd_year": {"type": "string"}
            },
            "additionalProperties": True
        },
        "experience": {
            "type": "object",
            "properties": {
                "total_experience_years": {"type": ["number", "string"]}
            },
            "additionalProperties": True
        },
        "publications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "title": {"type": "string"},
                    "journal": {"type": "string"},
                    "publisher": {"type": "string"},
                    "year": {"type": "string"}
                },
                "additionalProperties": True
            }
        }
    },
    "required": [],
    "additionalProperties": True
}


def extract_json_text(text: str) -> str:
    """Find the first JSON object in text and return it as a string."""
    if not text:
        raise ValueError('Empty text')
    start = text.find('{')
    if start == -1:
        raise ValueError('No JSON object found in text')
    
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    raise ValueError('Incomplete JSON object')


def repair_json_string(s: str) -> str:
    s = s.strip()
    s = re.sub(r'^```(?:json)?\s*', '', s, flags=re.I)
    s = re.sub(r'\s*```$', '', s)
    s = re.sub(r'[“”]', '"', s)
    s = re.sub(r'[‘’]', "'", s)
    s = re.sub(r',\s*([\}\]])', r'\1', s)
    s = re.sub(r'[\x00-\x1f]', '', s)
    return s.strip()


def validate_and_extract(text: str) -> dict:
    if not text:
        return {}

    cleaned_text = repair_json_string(text)

    try:
        data = json.loads(cleaned_text)
        return data
    except Exception:
        pass

    try:
        jtext = extract_json_text(cleaned_text)
        data = json.loads(jtext)
        return data
    except Exception as e:
        # Fallback regex parser for major fields
        fallback_data = {}
        
        m_name = re.search(r'"name"\s*:\s*"([^"]+)"', cleaned_text, re.I)
        if m_name:
            fallback_data['name'] = m_name.group(1)
            
        m_email = re.search(r'"email"\s*:\s*"([^"]+)"', cleaned_text, re.I)
        if m_email:
            fallback_data['email'] = m_email.group(1)
            
        m_phone = re.search(r'"phone"\s*:\s*"([^"]+)"', cleaned_text, re.I)
        if m_phone:
            fallback_data['phone'] = m_phone.group(1)
            
        m_des = re.search(r'"current_designation"\s*:\s*"([^"]+)"', cleaned_text, re.I)
        if m_des:
            fallback_data['current_designation'] = m_des.group(1)

        m_dept = re.search(r'"current_department"\s*:\s*"([^"]+)"', cleaned_text, re.I)
        if m_dept:
            fallback_data['current_department'] = m_dept.group(1)

        m_org = re.search(r'"current_organization"\s*:\s*"([^"]+)"', cleaned_text, re.I)
        if m_org:
            fallback_data['current_organization'] = m_org.group(1)
            
        return fallback_data

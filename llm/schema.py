import json
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
    # naive bracket matching
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    raise ValueError('Incomplete JSON object')


def validate_and_extract(text: str) -> dict:
    jtext = extract_json_text(text)
    try:
        data = json.loads(jtext)
    except Exception as e:
        raise ValueError(f'Invalid JSON: {e}')

    try:
        validate(instance=data, schema=SCHEMA)
    except ValidationError as e:
        raise ValueError(f'JSON does not match schema: {e.message}')

    return data

import pytest
from llm.schema import validate_and_extract


def test_validate_and_extract_valid():
    txt = '{"name":"Alice","email":"a@b.com","phone":"+1 555","education":{},"experience":{"total_experience_years":5},"publications":[]}'
    data = validate_and_extract(txt)
    assert data['name'] == 'Alice'


def test_validate_and_extract_invalid():
    txt = 'No JSON here'
    with pytest.raises(ValueError):
        validate_and_extract(txt)

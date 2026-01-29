
import pytest
from backend.services.utils import extract_json

def test_extract_json_valid():
    content = '{"key": "value"}'
    assert extract_json(content) == {"key": "value"}

def test_extract_json_markdown_fence():
    content = 'Sure, here is the JSON:\n```json\n{"key": "value"}\n```\nHope this helps!'
    assert extract_json(content) == {"key": "value"}

def test_extract_json_no_lang_fence():
    content = '```\n{"key": "value"}\n```'
    assert extract_json(content) == {"key": "value"}

def test_extract_json_naked_with_text():
    content = 'The result is {"key": "value"} according to the model.'
    assert extract_json(content) == {"key": "value"}

def test_extract_json_trailing_comma():
    content = '{"key": "value",}'
    assert extract_json(content) == {"key": "value"}

def test_extract_json_nested_with_trailing_comma():
    content = '{"list": [1, 2, 3,], "obj": {"a": 1,},}'
    # This might be tricky for the simple regex, let's see
    result = extract_json(content)
    assert result["list"] == [1, 2, 3]
    assert result["obj"] == {"a": 1}

def test_extract_json_multiple_blocks():
    content = 'First: ```json\n{"a": 1}\n```, Second: ```json\n{"b": 2}\n```'
    # Should pick the first one matching the pattern
    assert extract_json(content) == {"a": 1}

def test_extract_json_fail():
    content = 'Not a JSON at all.'
    assert extract_json(content) is None

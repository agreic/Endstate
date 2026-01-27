"""
Unit tests for Remediation Service.
Tests diagnosis, content generation, and mock LLM responses.
"""
import pytest

from backend.services.remediation_service import (
    diagnose_failure,
    generate_remediation_content,
    _extract_json_block,
)


def test_extract_json_block_from_fenced():
    content = '```json\n{"diagnosis": "test", "missing_concepts": []}\n```'
    result = _extract_json_block(content)
    assert result is not None
    assert result.get("diagnosis") == "test"


def test_extract_json_block_from_raw():
    content = '{"diagnosis": "raw test", "severity": "minor"}'
    result = _extract_json_block(content)
    assert result is not None
    assert result.get("diagnosis") == "raw test"


def test_extract_json_block_returns_none_for_invalid():
    content = "This is just plain text with no JSON"
    result = _extract_json_block(content)
    assert result is None


@pytest.mark.asyncio
async def test_diagnose_failure_returns_valid_structure():
    """Test that diagnose_failure returns expected structure with mock LLM."""
    lesson = {"title": "Recursion Basics", "explanation": "Recursion is..."}
    assessment = {"prompt": "Explain base cases"}
    answer = "I don't know"
    feedback = "Missing understanding of base cases"
    
    result = await diagnose_failure(
        lesson=lesson,
        assessment=assessment,
        answer=answer,
        feedback=feedback,
    )
    
    assert "diagnosis" in result
    assert "missing_concepts" in result
    assert "severity" in result
    assert "recommended_action" in result
    assert result["severity"] in {"minor", "moderate", "major"}


@pytest.mark.asyncio
async def test_generate_remediation_content_returns_valid_structure():
    """Test that generate_remediation_content returns expected structure."""
    diagnosis = {
        "diagnosis": "Confusion with base cases",
        "missing_concepts": ["Understanding Base Cases"],
        "severity": "moderate",
    }
    original_node = {"properties": {"name": "Recursion"}}
    
    result = await generate_remediation_content(
        diagnosis=diagnosis,
        original_node=original_node,
    )
    
    assert "title" in result
    assert "description" in result
    assert "explanation" in result


@pytest.mark.asyncio
async def test_diagnose_failure_handles_null_prerequisites():
    """Regression test: diagnose_failure should not crash if prerequisites contain None."""
    lesson = {"title": "Recursion Basics", "explanation": "Recursion is..."}
    assessment = {"prompt": "Explain base cases"}
    answer = "I don't know"
    feedback = "Missing understanding of base cases"
    node_context = {"prerequisites": ["Strings", None, "Functions"]}
    
    # Should not raise TypeError
    result = await diagnose_failure(
        lesson=lesson,
        assessment=assessment,
        answer=answer,
        feedback=feedback,
        node_context=node_context
    )

    assert "diagnosis" in result


@pytest.mark.asyncio
async def test_generate_remediation_fail_fast_on_insufficient_content():
    """Test that generate_remediation_content fails fast on insufficient content."""
    from unittest.mock import MagicMock, AsyncMock, patch
    
    # Mock LLM behavior
    mock_llm = MagicMock()
    
    # Response: Content too short (should fail immediately, no retry)
    short_content = '{"title": "Short", "description": "Desc", "explanation": "Too short."}'
    val = MagicMock()
    val.content = short_content
    
    # Setup async return value
    mock_llm.ainvoke = AsyncMock(return_value=val)
    
    # Patch get_llm
    with patch("backend.services.remediation_service.get_llm", return_value=mock_llm):
        diagnosis = {"diagnosis": "Gap", "missing_concepts": ["Concept"], "severity": "minor"}
        original_node = {"name": "Test Node"}
        
        result = await generate_remediation_content(diagnosis, original_node)
        
        # Should fail fast with error, only 1 call (no retry)
        assert "error" in result
        assert mock_llm.ainvoke.call_count == 1

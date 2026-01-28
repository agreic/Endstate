
from backend.services.lesson_service import parse_lesson_content
from backend.services.assessment_service import parse_assessment_content

def test_lesson_fallback():
    # Scenario: JSON failed, just raw text
    content = "This is a detailed lesson about recursion. It covers base cases and recursive steps."
    result = parse_lesson_content(content)
    assert result["explanation"] == content
    
    # Scenario: JSON failed but has "Explanation:" prefix
    content = "Explanation: This is a lesson about recursion."
    result = parse_lesson_content(content)
    assert result["explanation"] == "This is a lesson about recursion."
    
    # Scenario: Trailing Task section to be truncated
    content = "Recursion is cool.\nTask: Write a factorial function."
    result = parse_lesson_content(content)
    assert result["explanation"] == "Recursion is cool."

def test_assessment_field_mapping():
    # Scenario: Model used "question" instead of "prompt"
    content = '{"question": "What is 2+2?"}'
    result = parse_assessment_content(content)
    assert result["prompt"] == "What is 2+2?"
    
    # Scenario: Model used "score" instead of "result"
    content = '{"score": "pass", "feedback": "Good job"}'
    result = parse_assessment_content(content)
    assert result["result"] == "pass"

if __name__ == "__main__":
    test_lesson_fallback()
    test_assessment_field_mapping()
    print("Lesson and Assessment parsing verification passed!")

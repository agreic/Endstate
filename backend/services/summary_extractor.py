"""
Summary Extraction Engine
Extracts structured project summaries from chat conversations.
"""
import json
import re
from typing import List, Dict, Any, Optional, Tuple


# System prompt for project extraction
SUMMARY_EXTRACTION_PROMPT = """You are an expert at extracting structured project summaries from conversations.

Your task is to analyze the conversation and determine if there's enough information to create a project summary.

REQUIREMENTS FOR A VALID PROJECT SUMMARY:
1. User has expressed a clear learning or project goal
2. At least 2-3 skills or topics to learn are identified
3. User has indicated interest in specific areas

EXTRACT THE FOLLOWING STRUCTURE:
{
  "user_profile": {
    "interests": ["list of 2+ interests mentioned"],
    "skill_level": "beginner|intermediate|advanced",
    "time_available": "time commitment mentioned",
    "learning_style": "theoretical|hands-on|hybrid|not specified"
  },
  "agreed_project": {
    "name": "Concise project name (max 10 words)",
    "description": "Detailed project description",
    "timeline": "expected duration",
    "milestones": ["milestone 1", "milestone 2"]
  },
  "topics": ["list of 2+ topics/concepts"],
  "skills": ["list of 2+ skills to develop"],
  "concepts": ["list of key concepts to understand"]
}

OUTPUT FORMAT:
- If requirements are NOT met: Output "INSUFFICIENT: <reason>"
- If requirements ARE met: Output JSON starting with "SUMMARY:" followed by the structured data

Example of good summary:
SUMMARY:
{
  "user_profile": {
    "interests": ["machine learning", "computer vision"],
    "skill_level": "beginner",
    "time_available": "10 hours per week",
    "learning_style": "hands-on"
  },
  "agreed_project": {
    "name": "Build Image Classifier with CNN",
    "description": "Create a convolutional neural network to classify images",
    "timeline": "3 weeks",
    "milestones": ["Learn Python basics", "Understand CNN architecture", "Build and train model"]
  },
  "topics": ["python", "neural networks", "convolutional layers", "image processing"],
  "skills": ["python programming", "deep learning", "model training", "data preprocessing"],
  "concepts": ["supervised learning", "gradient descent", "backpropagation"]
}
"""


def extract_summary(conversation_history: List[Dict[str, str]]) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Extract a structured summary from conversation history.
    
    Args:
        conversation_history: List of message dicts with 'role' and 'content'
        
    Returns:
        Tuple of (has_valid_summary, summary_data, raw_output)
    """
    from backend.llm.provider import get_llm
    
    llm = get_llm()
    
    # Build conversation for the extractor
    messages = [("system", SUMMARY_EXTRACTION_PROMPT)]
    for msg in conversation_history:
        role = "human" if msg.get("role") == "user" else "ai"
        messages.append((role, msg.get("content", "")))
    
    messages.append((
        "human",
        "Based on the conversation so far, should we extract a project summary? "
        "Only extract if we have a clear goal and at least 2-3 skills/topics identified."
    ))
    
    try:
        response = llm.invoke(messages)
        raw_output = response.content if hasattr(response, 'content') else str(response)
        
        # Check for SUMMARY marker
        if "SUMMARY:" in raw_output:
            json_str = raw_output.split("SUMMARY:")[1].strip()
            # Clean up any markdown formatting
            json_str = re.sub(r'^```json\s*', '', json_str, flags=re.MULTILINE)
            json_str = re.sub(r'\s*```$', '', json_str)
            
            try:
                summary_data = json.loads(json_str)
                return True, summary_data, raw_output
            except json.JSONDecodeError as e:
                # Try to fix common JSON issues
                json_str = json_str.replace("'", '"')
                try:
                    summary_data = json.loads(json_str)
                    return True, summary_data, raw_output
                except json.JSONDecodeError:
                    return False, None, raw_output
        else:
            # Check if it's an INSUFFICIENT response
            if "INSUFFICIENT:" in raw_output:
                reason = raw_output.split("INSUFFICIENT:")[1].strip()
                return False, None, reason
            
            return False, None, raw_output
            
    except Exception as e:
        return False, None, str(e)


def should_propose_projects(conversation_history: List[Dict[str, str]]) -> bool:
    """
    Determine if the agent should propose project ideas.
    
    Returns:
        True if user has shared enough context for proposals
    """
    user_messages = [
        msg.get("content", "").lower() 
        for msg in conversation_history 
        if msg.get("role") == "user"
    ]
    
    # Check for intent indicators
    intent_patterns = [
        r"want to learn",
        r"interested in",
        r"looking to",
        r"how to",
        r"start with",
        r"get started",
        r"learn about",
        r"build (a|an)",
        r"create (a|an)",
        r"project",
    ]
    
    for msg in user_messages:
        for pattern in intent_patterns:
            if re.search(pattern, msg):
                return True
    
    return False


def generate_project_proposals(conversation_history: List[Dict[str, str]]) -> str:
    """
    Generate project proposals based on conversation context.
    
    Returns:
        Text with 2-3 project proposals
    """
    from backend.llm.provider import get_llm
    
    llm = get_llm()
    
    proposals_prompt = """You are a learning architect. Based on the conversation, 
    propose 2-3 specific, achievable projects that match what the user wants to learn.

    Requirements:
    - Each project should be achievable in 1-4 weeks
    - Match the user's stated skill level and time availability
    - Be specific, not vague

    Format your response as a numbered list with brief descriptions."""
    
    messages = [("system", proposals_prompt)]
    for msg in conversation_history:
        role = "human" if msg.get("role") == "user" else "ai"
        messages.append((role, msg.get("content", "")))
    
    messages.append(("human", "What specific project ideas would you propose?"))
    
    try:
        response = llm.invoke(messages)
        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        return f"Error generating proposals: {e}"


def should_ask_question(conversation_history: List[Dict[str, str]]) -> Tuple[bool, str]:
    """
    Determine if the agent should ask a clarifying question.
    
    Returns:
        Tuple of (should_ask, question)
    """
    from backend.llm.provider import get_llm
    
    llm = get_llm()
    
    question_prompt = """You are helping someone define their learning project. 
    Based on their messages, ask ONE clarifying question to help better understand their needs.
    
    Ask about:
    - Specificity of their goal
    - Time availability
    - Current skill level
    - Preferred learning style
    - Any gaps in understanding their needs

    Keep the question concise and friendly. If you have enough information, say "SUFFICIENT"."""
    
    messages = [("system", question_prompt)]
    for msg in conversation_history[-5:]:  # Only look at recent messages
        role = "human" if msg.get("role") == "user" else "ai"
        messages.append((role, msg.get("content", "")))
    
    try:
        response = llm.invoke(messages)
        question = response.content if hasattr(response, 'content') else str(response)
        
        if "SUFFICIENT" in question.upper():
            return False, ""
        
        return True, question.strip()
    except Exception:
        return False, ""

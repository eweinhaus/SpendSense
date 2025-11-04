"""
Tone validation module for SpendSense MVP.
Validates generated content to prevent shaming language and judgmental tone.
"""

import logging
from typing import Tuple, List

# Configure logging for tone violations
logger = logging.getLogger(__name__)

# Prohibited phrases that indicate shaming or judgmental language
PROHIBITED_PHRASES = [
    "you're overspending",
    "you're doing it wrong",
    "you should be ashamed",
    "you're bad with money",
    "you're terrible with money",
    "you're wasting money",
    "you're irresponsible",
    "you're foolish",
    "you're reckless",
    "you should be embarrassed",
    "you're making bad decisions",
    "you're throwing away money",
    "you're being stupid",
    "you're making mistakes",
    "you're wrong",
    "you're lazy",
    "you're careless",
    "you're ignorant",
    # Variations with "your"
    "your overspending",
    "your bad decisions",
    "your mistakes",
    "your carelessness",
    # Negative imperatives
    "stop being stupid",
    "stop wasting money",
    "stop being careless",
    "stop making mistakes"
]


def validate_tone(content: str) -> Tuple[bool, List[str]]:
    """
    Validate content for prohibited shaming or judgmental phrases.
    
    Args:
        content: Content string to validate
        
    Returns:
        Tuple of (is_valid: bool, violations: List[str])
        - is_valid: True if content passes validation, False if violations found
        - violations: List of prohibited phrases found in content
    """
    if not content:
        return True, []
    
    content_lower = content.lower()
    violations = []
    
    for phrase in PROHIBITED_PHRASES:
        if phrase in content_lower:
            violations.append(phrase)
    
    is_valid = len(violations) == 0
    
    return is_valid, violations


def log_violation(user_id: int, content_snippet: str, violations: List[str], 
                 content_type: str = "recommendation") -> None:
    """
    Log tone validation violations for operator review.
    
    Args:
        user_id: User ID
        content_snippet: First 200 characters of content with violations
        violations: List of prohibited phrases found
        content_type: Type of content (recommendation, rationale, etc.)
    """
    snippet = content_snippet[:200] + "..." if len(content_snippet) > 200 else content_snippet
    
    logger.warning(
        f"Tone validation violation for user {user_id} ({content_type}): "
        f"Found prohibited phrases: {', '.join(violations)}. "
        f"Content snippet: {snippet}"
    )


def validate_and_log(user_id: int, content: str, content_type: str = "recommendation") -> bool:
    """
    Validate content and log violations if found.
    
    Convenience function that combines validation and logging.
    
    Args:
        user_id: User ID
        content: Content string to validate
        content_type: Type of content (recommendation, rationale, etc.)
        
    Returns:
        True if content passes validation, False if violations found
    """
    is_valid, violations = validate_tone(content)
    
    if not is_valid:
        log_violation(user_id, content, violations, content_type)
    
    return is_valid


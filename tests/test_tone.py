"""
Tests for tone validation module.
"""

import pytest
from spendsense.tone_validator import validate_tone, validate_and_log, PROHIBITED_PHRASES


def test_validate_tone_clean_content():
    """Test tone validation with clean content."""
    content = "Here are some strategies to help you save money and build your emergency fund."
    is_valid, violations = validate_tone(content)
    
    assert is_valid is True
    assert len(violations) == 0


def test_validate_tone_prohibited_phrase():
    """Test tone validation with prohibited phrase."""
    content = "You're overspending and need to stop wasting money."
    is_valid, violations = validate_tone(content)
    
    assert is_valid is False
    assert len(violations) > 0
    assert "you're overspending" in violations


def test_validate_tone_multiple_violations():
    """Test tone validation with multiple prohibited phrases."""
    content = "You're doing it wrong and you're bad with money."
    is_valid, violations = validate_tone(content)
    
    assert is_valid is False
    assert len(violations) >= 2


def test_validate_tone_case_insensitive():
    """Test tone validation is case-insensitive."""
    content = "YOU'RE OVERSPENDING AND WASTING MONEY"
    is_valid, violations = validate_tone(content)
    
    assert is_valid is False
    assert len(violations) > 0


def test_validate_tone_empty_content():
    """Test tone validation with empty content."""
    is_valid, violations = validate_tone("")
    
    assert is_valid is True
    assert len(violations) == 0


def test_validate_tone_partial_match():
    """Test tone validation with partial phrase match."""
    # Should match if phrase appears in content
    content = "I know you're overspending this month"
    is_valid, violations = validate_tone(content)
    
    assert is_valid is False
    assert "you're overspending" in violations


def test_validate_and_log():
    """Test validate_and_log convenience function."""
    content = "You're doing it wrong with your finances"
    is_valid = validate_and_log(1, content, "test")
    
    assert is_valid is False


def test_validate_and_log_clean():
    """Test validate_and_log with clean content."""
    content = "Here are some helpful financial tips"
    is_valid = validate_and_log(1, content, "test")
    
    assert is_valid is True


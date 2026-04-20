"""
Data Validation Utilities
Validates and cleans data from SurveyHeart XLSX files
"""

import re
from typing import Tuple, Optional

def validate_email(email: str) -> bool:
    """
    Validate if string is a valid email format
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if valid email format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def clean_name(name: str) -> str:
    """
    Clean and standardize a name string
    
    Args:
        name (str): Raw name from Excel
        
    Returns:
        str: Cleaned name
    """
    if not name or not isinstance(name, str):
        return ""
    return name.strip().title()

def clean_email(email: str) -> str:
    """
    Clean email address
    
    Args:
        email (str): Raw email from Excel
        
    Returns:
        str: Cleaned email (lowercase)
    """
    if not email or not isinstance(email, str):
        return ""
    return email.strip().lower()

def parse_score(score: any) -> Optional[float]:
    """
    Parse and validate a score/percentage value
    
    Args:
        score: Raw score value (can be str, int, float)
        
    Returns:
        float: Parsed score or None if invalid
    """
    if score is None or score == "":
        return None
    
    try:
        # Handle string percentages like "95%"
        if isinstance(score, str):
            score = score.replace('%', '').strip()
        
        score_float = float(score)
        
        # Validate score is between 0 and 100
        if 0 <= score_float <= 100:
            return round(score_float, 2)
        else:
            return None
    except (ValueError, TypeError):
        return None

def validate_row_data(full_name: str, email: str, score: Optional[float]) -> Tuple[bool, str]:
    """
    Validate a complete row of data.
    
    NOTE: score=None is deliberately ALLOWED — a participant may exist in a
    file without a recorded score (e.g. SurveyHeart exports blank for absent).
    Only name and email are hard requirements for a row to be kept.
    
    Args:
        full_name (str): Participant's full name
        email (str): Participant's email
        score (float): Test score (None is accepted)
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    errors = []
    
    if not full_name or not full_name.strip():
        errors.append("Full name is required")
    
    # If email is provided, validate it. Otherwise, allow it to be empty.
    # We will generate a pseudo-email based on the name in excel_processor.
    if email and email.strip() and not validate_email(email):
        errors.append(f"Invalid email: {email}")
    
    # Score is optional — None means the participant was absent for this test.
    # Do NOT reject the row for a missing score.
    
    is_valid = len(errors) == 0
    error_msg = " | ".join(errors) if errors else ""
    
    return is_valid, error_msg

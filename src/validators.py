import re
from typing import Tuple, Optional

def validate_email(email: str) -> bool:

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def clean_name(name: str) -> str:

    if not name or not isinstance(name, str):
        return ""
    return name.strip().title()

def clean_email(email: str) -> str:

    if not email or not isinstance(email, str):
        return ""
    return email.strip().lower()

def parse_score(score: any) -> Optional[float]:

    if score is None or score == "":
        return None

    try:

        if isinstance(score, str):
            score = score.replace('%', '').strip()

        score_float = float(score)

        if 0 <= score_float <= 100:
            return round(score_float, 2)
        else:
            return None
    except (ValueError, TypeError):
        return None

def validate_row_data(full_name: str, email: str, score: Optional[float]) -> Tuple[bool, str]:

    errors = []

    if not full_name or not full_name.strip():
        errors.append("Full name is required")

    if email and email.strip() and not validate_email(email):
        errors.append(f"Invalid email: {email}")

    is_valid = len(errors) == 0
    error_msg = " | ".join(errors) if errors else ""

    return is_valid, error_msg

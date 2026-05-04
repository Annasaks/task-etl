from typing import Optional


def safe_int(x) -> Optional[int]:
    """Convert to int. Returns None for None, empty string, or non-numeric values."""
    if x is None or x == "":
        return None
    try:
        return int(x)
    except (ValueError, TypeError):
        return None


def safe_str(x) -> Optional[str]:
    """Convert to str. Returns None for None or empty string."""
    if x is None or x == "":
        return None
    return str(x)

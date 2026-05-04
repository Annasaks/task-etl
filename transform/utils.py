from typing import Optional


def safe_int(x) -> Optional[int]:
    if x is None or x == "":
        return None
    try:
        return int(x)
    except (ValueError, TypeError):
        return None


def safe_str(x) -> Optional[str]:
    if x is None or x == "":
        return None
    return str(x)

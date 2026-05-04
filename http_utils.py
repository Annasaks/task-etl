import logging
import time
from functools import wraps
from typing import Callable

import requests

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


def retry(times: int = 3, backoff: float = 2.0):
    """Retry on Timeout / ConnectionError / 5xx / 408 / 429. No retry on other 4xx."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, times + 1):
                try:
                    return fn(*args, **kwargs)
                except (requests.Timeout, requests.ConnectionError) as e:
                    last_exc = e
                    if attempt < times:
                        wait = backoff * (2 ** (attempt - 1))
                        logger.warning(
                            f"{fn.__name__} attempt {attempt}/{times} failed ({type(e).__name__}); retrying in {wait:.1f}s"
                        )
                        time.sleep(wait)
                except requests.HTTPError as e:
                    status = e.response.status_code if e.response is not None else None
                    if status in RETRYABLE_STATUS and attempt < times:
                        wait = backoff * (2 ** (attempt - 1))
                        logger.warning(
                            f"{fn.__name__} attempt {attempt}/{times} got HTTP {status}; retrying in {wait:.1f}s"
                        )
                        time.sleep(wait)
                        last_exc = e
                    else:
                        raise
            logger.error(f"{fn.__name__} exhausted {times} attempts: {last_exc}")
            raise last_exc
        return wrapper
    return decorator

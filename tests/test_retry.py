"""Unit tests for the @retry decorator in http_utils.py."""
from unittest.mock import MagicMock, patch

import pytest
import requests

from http_utils import retry


def make_http_error(status_code: int) -> requests.HTTPError:
    response = MagicMock()
    response.status_code = status_code
    err = requests.HTTPError(f"HTTP {status_code}")
    err.response = response
    return err


class TestRetry:
    def test_no_retry_when_function_succeeds(self):
        fn = MagicMock(__name__="fn",return_value="ok")
        decorated = retry(times=3, backoff=0)(fn)
        assert decorated() == "ok"
        assert fn.call_count == 1

    def test_retries_on_timeout(self):
        fn = MagicMock(__name__="fn",side_effect=[requests.Timeout(), requests.Timeout(), "ok"])
        decorated = retry(times=3, backoff=0)(fn)
        with patch("time.sleep"):
            assert decorated() == "ok"
        assert fn.call_count == 3

    def test_retries_on_5xx(self):
        fn = MagicMock(__name__="fn",side_effect=[make_http_error(503), "ok"])
        decorated = retry(times=3, backoff=0)(fn)
        with patch("time.sleep"):
            assert decorated() == "ok"
        assert fn.call_count == 2

    def test_no_retry_on_4xx(self):
        # 403 is permanent — must raise without retrying
        fn = MagicMock(__name__="fn",side_effect=make_http_error(403))
        decorated = retry(times=3, backoff=0)(fn)
        with pytest.raises(requests.HTTPError):
            decorated()
        assert fn.call_count == 1

    def test_raises_after_exhausting_retries(self):
        fn = MagicMock(__name__="fn",side_effect=requests.Timeout())
        decorated = retry(times=2, backoff=0)(fn)
        with patch("time.sleep"), pytest.raises(requests.Timeout):
            decorated()
        assert fn.call_count == 2

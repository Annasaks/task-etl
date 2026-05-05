"""Unit tests for monitoring/metrics_collector.py."""
import logging
import time
from datetime import datetime, timezone

from monitoring.metrics_collector import RunMetrics, CountingHandler, make_run_id


class TestRunMetrics:
    def test_finalize_computes_duration(self):
        m = RunMetrics(
            run_id="20260101-120000",
            source_api="api_sports",
            started_at=datetime.now(timezone.utc),
        )
        time.sleep(0.01)
        m.finalize()
        assert m.duration_seconds is not None
        assert m.duration_seconds > 0

    def test_finalize_computes_skipped_rows(self):
        m = RunMetrics(
            run_id="20260101-120000",
            source_api="api_sports",
            started_at=datetime.now(timezone.utc),
            rows_extracted=20,
            rows_transformed=18,
        )
        m.finalize()
        assert m.rows_skipped == 2

    def test_finalize_skipped_never_negative(self):
        # If transform somehow produces more rows than extracted, skipped should be 0 (not negative).
        m = RunMetrics(
            run_id="20260101-120000",
            source_api="api_sports",
            started_at=datetime.now(timezone.utc),
            rows_extracted=18,
            rows_transformed=20,
        )
        m.finalize()
        assert m.rows_skipped == 0


class TestCountingHandler:
    def _make_record(self, level: int) -> logging.LogRecord:
        return logging.LogRecord("test", level, "f.py", 1, "msg", None, None)

    def test_counts_warnings(self):
        handler = CountingHandler()
        handler.emit(self._make_record(logging.WARNING))
        handler.emit(self._make_record(logging.WARNING))
        assert handler.warnings == 2
        assert handler.errors == 0

    def test_counts_errors(self):
        handler = CountingHandler()
        handler.emit(self._make_record(logging.ERROR))
        assert handler.errors == 1
        assert handler.warnings == 0

    def test_ignores_info_messages(self):
        handler = CountingHandler()
        handler.emit(self._make_record(logging.INFO))
        assert handler.warnings == 0
        assert handler.errors == 0


def test_run_id_format():
    run_id = make_run_id()
    # YYYYMMDD-HHMMSS = 15 chars
    assert len(run_id) == 15
    assert run_id[8] == "-"

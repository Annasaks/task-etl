"""Pipeline metrics collection — produces one row per (run × source) for the dashboard."""
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class RunMetrics:
    """Metrics for a single source within a pipeline run.

    One row per (run_id × source_api) — written to pipeline_monitoring.pipeline_runs.
    """
    run_id: str
    source_api: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    extract_success: bool = False
    transform_success: bool = False
    load_success: bool = False
    export_success: bool = False

    rows_extracted: int = 0
    rows_transformed: int = 0
    rows_skipped: int = 0

    warnings_count: int = 0
    errors_count: int = 0

    def finalize(self) -> None:
        """Compute end-of-run derived fields. Called once when the source flow finishes."""
        self.ended_at = datetime.now(timezone.utc)
        self.duration_seconds = (self.ended_at - self.started_at).total_seconds()
        self.rows_skipped = max(0, self.rows_extracted - self.rows_transformed)

    def to_dict(self) -> dict:
        return asdict(self)


class CountingHandler(logging.Handler):
    """Logging handler that counts WARNING and ERROR records.

    Attached to the root logger during a source's run, then detached.
    Lets us automatically count warnings/errors without modifying the
    extract/transform code.
    """
    def __init__(self):
        super().__init__()
        self.warnings = 0
        self.errors = 0

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= logging.ERROR:
            self.errors += 1
        elif record.levelno >= logging.WARNING:
            self.warnings += 1

    def reset(self) -> None:
        self.warnings = 0
        self.errors = 0


def make_run_id() -> str:
    """Run identifier shared across both sources within the same pipeline execution."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class RunMetrics:
    """One row per (run_id, source_api) — what we write to pipeline_runs."""
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
        self.ended_at = datetime.now(timezone.utc)
        self.duration_seconds = (self.ended_at - self.started_at).total_seconds()
        self.rows_skipped = max(0, self.rows_extracted - self.rows_transformed)

    def to_dict(self) -> dict:
        return asdict(self)


class CountingHandler(logging.Handler):
    """Counts WARNING and ERROR records — attached to root logger per run."""

    def __init__(self):
        super().__init__()
        self.warnings = 0
        self.errors = 0

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= logging.ERROR:
            self.errors += 1
        elif record.levelno >= logging.WARNING:
            self.warnings += 1


def make_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

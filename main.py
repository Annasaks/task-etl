import logging
from datetime import datetime, timezone
from pathlib import Path

from extract import api_sports, api_football
from transform import api_sports as transform_api_sports
from transform import api_football as transform_api_football
from load.loader import load
from export.csv_exporter import export_csv
from monitoring.metrics_collector import RunMetrics, CountingHandler, make_run_id
from monitoring.metrics_loader import save_metrics

logger = logging.getLogger(__name__)

LOG_FILE = Path(__file__).resolve().parent / "logs" / "etl.log"


SOURCES = [
    {
        "name": "API-Sports",
        "key": "api_sports",
        "table": "teams_api_sports",
        "extract": api_sports,
        "transform": transform_api_sports,
    },
    {
        "name": "API-Football",
        "key": "api_football",
        "table": "teams_api_football",
        "extract": api_football,
        "transform": transform_api_football,
    },
]


def setup_logging(level: int = logging.INFO) -> None:
    """Root logger with one handler to logs/etl.log and one to stdout."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(level)
    if root.handlers:
        return
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)


def run_source(run_id: str, source: dict):
    """Run extract -> transform -> load -> export for one source."""
    name, key, table = source["name"], source["key"], source["table"]
    metrics = RunMetrics(
        run_id=run_id,
        source_api=key,
        started_at=datetime.now(timezone.utc),
    )
    counter = CountingHandler()
    logging.getLogger().addHandler(counter)

    try:
        logger.info(f"=== {name}: extract ===")
        teams = source["extract"].get_teams()
        standings = source["extract"].get_standings()
        if teams is None or standings is None:
            logger.error(f"{name}: extract failed, skipping rest of pipeline")
            return None, metrics
        metrics.extract_success = True
        metrics.rows_extracted = len(standings)

        logger.info(f"=== {name}: transform ===")
        df = source["transform"].transform(teams, standings)
        if df is None or df.empty:
            logger.error(f"{name}: transform produced no rows, skipping load/export")
            return None, metrics
        metrics.transform_success = True
        metrics.rows_transformed = len(df)

        logger.info(f"=== {name}: load ===")
        metrics.load_success = load(df, table)

        logger.info(f"=== {name}: export ===")
        metrics.export_success = export_csv(df, table)

        return df, metrics
    finally:
        logging.getLogger().removeHandler(counter)
        metrics.finalize()
        metrics.warnings_count = counter.warnings
        metrics.errors_count = counter.errors


def run_etl():
    setup_logging()
    run_id = make_run_id()
    logger.info(f"########## ETL pipeline START (run_id={run_id}) ##########")

    results = [run_source(run_id, src) for src in SOURCES]

    logger.info("########## ETL pipeline SUMMARY ##########")
    for src, (_, m) in zip(SOURCES, results):
        if not m.extract_success:
            line = "FAILED at extract"
        else:
            parts = [f"{m.rows_transformed} rows"]
            parts.append("loaded" if m.load_success else "NOT loaded")
            parts.append("CSV ok" if m.export_success else "CSV FAILED")
            parts.append(f"{m.duration_seconds:.1f}s")
            line = " / ".join(parts)
        logger.info(f"{src['name']}: {line}")

    save_metrics([m for _, m in results])
    return [df for df, _ in results]


if __name__ == "__main__":
    run_etl()

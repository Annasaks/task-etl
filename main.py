import logging
from datetime import datetime, timezone

from logging_config import setup_logging
from extract import api_sports, api_football
from transform import api_sports as transform_api_sports
from transform import api_football as transform_api_football
from load.loader import load
from export.csv_exporter import export_csv
from monitoring.metrics_collector import RunMetrics, CountingHandler, make_run_id
from monitoring.metrics_loader import save_metrics

logger = logging.getLogger(__name__)


def run_source(run_id, name, source_key, table, extract_module, transform_module):
    """Run extract → transform → load → export for one source.

    Returns (df, metrics).
    """
    metrics = RunMetrics(
        run_id=run_id,
        source_api=source_key,
        started_at=datetime.now(timezone.utc),
    )
    counter = CountingHandler()
    logging.getLogger().addHandler(counter)

    try:
        logger.info(f"=== {name}: extract ===")
        teams = extract_module.get_teams()
        standings = extract_module.get_standings()
        if teams is None or standings is None:
            logger.error(f"{name}: extract failed, skipping rest of pipeline")
            metrics.finalize()
            metrics.warnings_count = counter.warnings
            metrics.errors_count = counter.errors
            return None, metrics
        metrics.extract_success = True
        metrics.rows_extracted = len(standings)

        logger.info(f"=== {name}: transform ===")
        df = transform_module.transform(teams, standings)
        if df is None or df.empty:
            logger.error(f"{name}: transform produced no rows, skipping load/export")
            metrics.finalize()
            metrics.warnings_count = counter.warnings
            metrics.errors_count = counter.errors
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
        if metrics.ended_at is None:
            metrics.finalize()
        metrics.warnings_count = counter.warnings
        metrics.errors_count = counter.errors


def run_etl():
    setup_logging()
    run_id = make_run_id()
    logger.info(f"########## ETL pipeline START (run_id={run_id}) ##########")

    df_as, m_as = run_source(
        run_id, "API-Sports", "api_sports", "teams_api_sports",
        api_sports, transform_api_sports,
    )
    df_af, m_af = run_source(
        run_id, "API-Football", "api_football", "teams_api_football",
        api_football, transform_api_football,
    )

    logger.info("########## ETL pipeline SUMMARY ##########")
    def summary(m):
        if not m.extract_success:
            return "FAILED at extract"
        parts = [f"{m.rows_transformed} rows"]
        parts.append("loaded" if m.load_success else "NOT loaded")
        parts.append("CSV ok" if m.export_success else "CSV FAILED")
        parts.append(f"{m.duration_seconds:.1f}s")
        return " / ".join(parts)
    logger.info(f"API-Sports:   {summary(m_as)}")
    logger.info(f"API-Football: {summary(m_af)}")

    logger.info("########## Saving metrics ##########")
    save_metrics([m_as, m_af])

    return df_as, df_af


if __name__ == "__main__":
    run_etl()

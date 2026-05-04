import logging
from typing import List

import pandas as pd

from config import LOAD_BACKEND, BIGQUERY_PROJECT, BIGQUERY_LOCATION
from monitoring.metrics_collector import RunMetrics

logger = logging.getLogger(__name__)

METRICS_TABLE = "pipeline_runs"
METRICS_DATASET_BQ = "pipeline_monitoring"


def save_metrics(metrics: List[RunMetrics]) -> bool:
    if not metrics:
        return False

    df = pd.DataFrame([m.to_dict() for m in metrics])

    if LOAD_BACKEND == "sqlite":
        return _save_to_sqlite(df)
    if LOAD_BACKEND == "bigquery":
        return _save_to_bigquery(df)

    logger.error(f"save_metrics: unknown LOAD_BACKEND '{LOAD_BACKEND}'")
    return False


def _save_to_sqlite(df: pd.DataFrame) -> bool:
    from load.sqlite_loader import DB_PATH
    from sqlalchemy import create_engine
    from sqlalchemy.exc import SQLAlchemyError

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        df.to_sql(METRICS_TABLE, engine, if_exists="append", index=False)
        logger.info(f"Metrics: appended {len(df)} rows to {METRICS_TABLE} ({DB_PATH.name})")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Metrics: SQLite error: {e}")
        return False


def _save_to_bigquery(df: pd.DataFrame) -> bool:
    from google.cloud import bigquery
    from google.api_core.exceptions import GoogleAPIError

    if not BIGQUERY_PROJECT:
        logger.error("Metrics: BIGQUERY_PROJECT not set")
        return False

    table_id = f"{BIGQUERY_PROJECT}.{METRICS_DATASET_BQ}.{METRICS_TABLE}"
    try:
        client = bigquery.Client(project=BIGQUERY_PROJECT, location=BIGQUERY_LOCATION)
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        logger.info(f"Metrics: appended {len(df)} rows to {table_id}")
        return True
    except GoogleAPIError as e:
        logger.error(f"Metrics: BigQuery error: {e}")
        return False

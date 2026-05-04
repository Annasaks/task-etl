import logging

import pandas as pd

from config import (
    LOAD_BACKEND,
    BIGQUERY_DATASET_API_SPORTS,
    BIGQUERY_DATASET_API_FOOTBALL,
)
from load.sqlite_loader import load_to_sqlite

logger = logging.getLogger(__name__)

# Map source table name → BigQuery dataset.
# The BigQuery architecture uses one dataset per source (stricter separation
# than SQLite where both tables live in the same .db file).
TABLE_TO_BQ_DATASET = {
    "teams_api_sports": BIGQUERY_DATASET_API_SPORTS,
    "teams_api_football": BIGQUERY_DATASET_API_FOOTBALL,
}


def load(df: pd.DataFrame, table_name: str) -> bool:
    """Dispatch the load to the configured backend.

    Backend is selected via the LOAD_BACKEND env var:
      - "sqlite"   (default) → data/etl.db, table {table_name}
      - "bigquery"           → {project}.{dataset_for_source}.teams
    Returns True on success, False on failure.
    """
    if df is None or df.empty:
        logger.error(f"load: refusing to write empty DataFrame to {table_name}")
        return False

    if LOAD_BACKEND == "sqlite":
        return load_to_sqlite(df, table_name)

    if LOAD_BACKEND == "bigquery":
        from load.bigquery_loader import load_to_bigquery
        dataset = TABLE_TO_BQ_DATASET.get(table_name)
        if not dataset:
            logger.error(f"load: no BigQuery dataset mapped for table '{table_name}'")
            return False
        # In BigQuery we use a simple table name "teams" since the dataset
        # already carries the source identity (api_sports_data / api_football_data).
        return load_to_bigquery(df, dataset, "teams")

    logger.error(f"load: unknown LOAD_BACKEND '{LOAD_BACKEND}' (expected 'sqlite' or 'bigquery')")
    return False

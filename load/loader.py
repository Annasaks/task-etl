import logging

import pandas as pd

from config import (
    LOAD_BACKEND,
    BIGQUERY_DATASET_API_SPORTS,
    BIGQUERY_DATASET_API_FOOTBALL,
)
from load.sqlite_loader import load_to_sqlite

logger = logging.getLogger(__name__)

# In BigQuery each source has its own dataset, so the table name is just "teams".
TABLE_TO_BQ_DATASET = {
    "teams_api_sports": BIGQUERY_DATASET_API_SPORTS,
    "teams_api_football": BIGQUERY_DATASET_API_FOOTBALL,
}


def load(df: pd.DataFrame, table_name: str) -> bool:
    """Dispatch the load to SQLite or BigQuery based on LOAD_BACKEND."""
    if df is None or df.empty:
        logger.error(f"load: refusing to write empty DataFrame to {table_name}")
        return False

    if LOAD_BACKEND == "sqlite":
        return load_to_sqlite(df, table_name)

    if LOAD_BACKEND == "bigquery":
        from load.bigquery_loader import load_to_bigquery
        dataset = TABLE_TO_BQ_DATASET.get(table_name)
        if not dataset:
            logger.error(f"load: no BigQuery dataset mapped for '{table_name}'")
            return False
        return load_to_bigquery(df, dataset, "teams")

    logger.error(f"load: unknown LOAD_BACKEND '{LOAD_BACKEND}'")
    return False

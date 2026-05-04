import logging

import pandas as pd
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

from config import BIGQUERY_PROJECT, BIGQUERY_LOCATION

logger = logging.getLogger(__name__)


def load_to_bigquery(df: pd.DataFrame, dataset: str, table_name: str) -> bool:
    """Write a DataFrame to BigQuery {project}.{dataset}.{table_name}.

    Mode: WRITE_TRUNCATE (idempotent — full replace on each run).
    """
    if not BIGQUERY_PROJECT or not dataset:
        logger.error(f"BigQuery: missing project ('{BIGQUERY_PROJECT}') or dataset ('{dataset}')")
        return False

    table_id = f"{BIGQUERY_PROJECT}.{dataset}.{table_name}"

    try:
        client = bigquery.Client(project=BIGQUERY_PROJECT, location=BIGQUERY_LOCATION)
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        logger.info(f"BigQuery: loaded {len(df)} rows into {table_id}")
        return True
    except GoogleAPIError as e:
        logger.error(f"BigQuery: API error writing {table_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"BigQuery: unexpected error writing {table_id}: {e}")
        return False

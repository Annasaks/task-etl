import logging

import pandas as pd
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

from config import BIGQUERY_PROJECT, BIGQUERY_LOCATION

logger = logging.getLogger(__name__)


def load_to_bigquery(df: pd.DataFrame, dataset: str, table_name: str) -> bool:
    """Append a DataFrame to BigQuery {project}.{dataset}.{table_name}.

    Bonus 2A — WRITE_APPEND keeps historical snapshots; the snapshot_at
              column distinguishes versions of the same team.
    Bonus 2B — ALLOW_FIELD_ADDITION lets BigQuery auto-extend the table
              schema if the DataFrame contains new columns. Combined with
              the transformer's `extra_fields` JSON column, the pipeline
              survives any new upstream API field gracefully.
    """
    if not BIGQUERY_PROJECT or not dataset:
        logger.error(f"BigQuery: missing project ('{BIGQUERY_PROJECT}') or dataset ('{dataset}')")
        return False

    table_id = f"{BIGQUERY_PROJECT}.{dataset}.{table_name}"

    try:
        client = bigquery.Client(project=BIGQUERY_PROJECT, location=BIGQUERY_LOCATION)
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema_update_options=[
                bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION,
            ],
        )
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        logger.info(f"BigQuery: appended {len(df)} rows to {table_id}")
        return True
    except GoogleAPIError as e:
        logger.error(f"BigQuery: API error writing {table_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"BigQuery: unexpected error writing {table_id}: {e}")
        return False

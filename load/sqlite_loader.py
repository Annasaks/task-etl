import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "etl.db"
ENGINE_URL = f"sqlite:///{DB_PATH}"


def load_to_sqlite(df: pd.DataFrame, table_name: str) -> bool:
    """Append a DataFrame to data/etl.db.

    Bonus 2A — append mode keeps historical snapshots (same team appears
    once per run, distinguished by the snapshot_at column).
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        engine = create_engine(ENGINE_URL)
        df.to_sql(table_name, engine, if_exists="append", index=False)
        logger.info(f"SQLite: appended {len(df)} rows to {table_name} ({DB_PATH.name})")
        return True
    except SQLAlchemyError as e:
        logger.error(f"SQLite: SQL error writing {table_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"SQLite: unexpected error writing {table_name}: {e}")
        return False

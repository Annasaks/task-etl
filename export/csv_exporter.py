import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

EXPORT_DIR = Path(__file__).resolve().parent.parent / "data" / "exports"


def export_csv(df: pd.DataFrame, table_name: str) -> bool:
    """Write df to data/exports/{table_name}.csv (UTF-8, no index)."""
    if df is None or df.empty:
        logger.error(f"export_csv: refusing to export empty DataFrame for {table_name}")
        return False

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORT_DIR / f"{table_name}.csv"

    try:
        df.to_csv(path, index=False, encoding="utf-8")
        logger.info(f"Exported {len(df)} rows to {path.name}")
        return True
    except Exception as e:
        logger.error(f"export_csv: failed writing {path}: {e}")
        return False

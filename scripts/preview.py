"""Preview the contents of data/etl.db — sanity check after a pipeline run."""
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, inspect

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "etl.db"
TABLES = ["teams_api_sports", "teams_api_football"]


def main():
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} does not exist. Run `python main.py` first.")
        sys.exit(1)

    engine = create_engine(f"sqlite:///{DB_PATH}")
    existing = inspect(engine).get_table_names()

    for table in TABLES:
        print(f"\n{'=' * 80}")
        print(f"TABLE: {table}")
        print("=" * 80)
        if table not in existing:
            print(f"(absent — extract/transform/load probably failed for this source)")
            continue
        df = pd.read_sql(f"SELECT * FROM {table}", engine)
        print(f"Rows: {len(df)}  |  Columns: {len(df.columns)}")
        print(f"\nFirst 5 rows (selected columns):")
        cols = ["team_name", "league_position", "points", "wins", "draws", "losses", "goals_for", "goals_against"]
        cols = [c for c in cols if c in df.columns]
        print(df[cols].head().to_string(index=False))


if __name__ == "__main__":
    main()

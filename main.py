import logging

from logging_config import setup_logging
from extract import api_sports, api_football
from transform import api_sports as transform_api_sports
from transform import api_football as transform_api_football
from load.loader import load
from export.csv_exporter import export_csv

logger = logging.getLogger(__name__)


def run_source(name: str, table: str, extract_module, transform_module):
    """Run extract → transform → load → export for one source.

    Returns (df, loaded:bool, exported:bool).
    """
    logger.info(f"=== {name}: extract ===")
    teams = extract_module.get_teams()
    standings = extract_module.get_standings()
    if teams is None or standings is None:
        logger.error(f"{name}: extract failed, skipping rest of pipeline")
        return None, False, False

    logger.info(f"=== {name}: transform ===")
    df = transform_module.transform(teams, standings)
    if df is None or df.empty:
        logger.error(f"{name}: transform produced no rows, skipping load/export")
        return None, False, False

    logger.info(f"=== {name}: load ===")
    loaded = load(df, table)

    logger.info(f"=== {name}: export ===")
    exported = export_csv(df, table)

    return df, loaded, exported


def run_etl():
    setup_logging()
    logger.info("########## ETL pipeline START ##########")

    df_as, ld_as, ex_as = run_source("API-Sports", "teams_api_sports", api_sports, transform_api_sports)
    df_af, ld_af, ex_af = run_source("API-Football", "teams_api_football", api_football, transform_api_football)

    logger.info("########## ETL pipeline SUMMARY ##########")
    def summary(df, loaded, exported):
        if df is None:
            return "FAILED"
        parts = [f"{len(df)} rows"]
        parts.append("loaded" if loaded else "NOT loaded")
        parts.append("CSV ok" if exported else "CSV FAILED")
        return " / ".join(parts)
    logger.info(f"API-Sports:   {summary(df_as, ld_as, ex_as)}")
    logger.info(f"API-Football: {summary(df_af, ld_af, ex_af)}")

    return df_as, df_af


if __name__ == "__main__":
    run_etl()

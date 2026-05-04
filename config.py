from dotenv import load_dotenv
import os

load_dotenv()

# --- API-Sports (v3.football.api-sports.io) ---
API_SPORTS_KEY = os.getenv("API_SPORTS_KEY")
LEAGUE_ID_API_SPORTS = int(os.getenv("LEAGUE_ID_API_SPORTS", "39"))  # 39 = Premier League
SEASON = int(os.getenv("SEASON", "2023"))

# --- API-Football (apiv3.apifootball.com) ---
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
LEAGUE_ID_API_FOOTBALL = int(os.getenv("LEAGUE_ID_API_FOOTBALL", "152"))  # 152 = Premier League

# --- Load backend ---
LOAD_BACKEND = os.getenv("LOAD_BACKEND", "sqlite").lower()

# --- BigQuery config ---
BIGQUERY_PROJECT = os.getenv("BIGQUERY_PROJECT")
BIGQUERY_DATASET_API_SPORTS = os.getenv("BIGQUERY_DATASET_API_SPORTS")
BIGQUERY_DATASET_API_FOOTBALL = os.getenv("BIGQUERY_DATASET_API_FOOTBALL")
BIGQUERY_LOCATION = os.getenv("BIGQUERY_LOCATION", "US")

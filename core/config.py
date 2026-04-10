import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "tippmix.db"

# API-Football
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
API_FOOTBALL_HEADERS = {
    "x-apisports-key": API_FOOTBALL_KEY,
}

# Zhipu AI (GLM)
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_API_BASE = "https://open.bigmodel.cn/api/paas/v4"
ZHIPU_MODEL = "glm-4-flash"

# Defaults
DEFAULT_INITIAL_BALANCE = 100_000.0  # HUF
CACHE_TTL_HOURS = 4
VALUE_BET_MARGIN = 0.05  # 5%
DROPPING_ODDS_THRESHOLD = 0.10  # 10%
MIN_TRAINING_SAMPLES = 30
RETRAIN_THRESHOLD = 50  # new finished fixtures since last train

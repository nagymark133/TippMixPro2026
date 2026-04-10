import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "tippmix.db"


def get_secret(key: str, default: str = "") -> str:
    try:
        value = st.secrets.get(key)
        if value is not None:
            return str(value)
    except Exception:
        pass
    return os.getenv(key, default)

API_FOOTBALL_KEY = get_secret("API_FOOTBALL_KEY")
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
API_FOOTBALL_HEADERS = {
    "x-apisports-key": API_FOOTBALL_KEY,
}

# Zhipu AI (GLM)
ZHIPU_API_KEY = get_secret("ZHIPU_API_KEY")
ZHIPU_API_BASE = "https://open.bigmodel.cn/api/paas/v4"
ZHIPU_MODEL = "glm-4-flash"

# Defaults
DEFAULT_INITIAL_BALANCE = 100_000.0  # HUF
CACHE_TTL_HOURS = 4
VALUE_BET_MARGIN = 0.05  # 5%
DROPPING_ODDS_THRESHOLD = 0.10  # 10%
MIN_TRAINING_SAMPLES = 30
RETRAIN_THRESHOLD = 50  # new finished fixtures since last train

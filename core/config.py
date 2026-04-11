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


def _normalize_secret(value) -> str:
    if value is None:
        return ""
    return str(value).strip().strip('"').strip("'")


def _find_in_mapping(mapping, keys: set[str]) -> str:
    try:
        items = mapping.items()
    except Exception:
        return ""

    normalized_keys = {candidate.lower() for candidate in keys}

    for current_key, current_value in items:
        if str(current_key).lower() in normalized_keys:
            value = _normalize_secret(current_value)
            if value:
                return value

        if hasattr(current_value, "items"):
            nested_value = _find_in_mapping(current_value, keys)
            if nested_value:
                return nested_value

    return ""


def get_secret(key: str, default: str = "") -> str:
    candidates = {
        key,
        key.lower(),
        key.upper(),
    }

    try:
        value = st.secrets.get(key)
        value = _normalize_secret(value)
        if value:
            return value
    except Exception:
        pass

    try:
        nested_value = _find_in_mapping(st.secrets, candidates)
        if nested_value:
            return nested_value
    except Exception:
        pass

    env_value = _normalize_secret(os.getenv(key, default))
    if env_value:
        return env_value

    return default

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

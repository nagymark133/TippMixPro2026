import logging
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from core.config import MODELS_DIR, MIN_TRAINING_SAMPLES, RETRAIN_THRESHOLD
from core import database as db

log = logging.getLogger(__name__)

MODEL_1X2_PATH = MODELS_DIR / "model_1x2.joblib"
MODEL_OU25_PATH = MODELS_DIR / "model_ou25.joblib"
META_PATH = MODELS_DIR / "model_meta.joblib"

# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def _form_to_numeric(form_str: str | None) -> float:
    """Convert form like 'WWDLW' to a numeric score (W=3, D=1, L=0), normalised to [0,1]."""
    if not form_str:
        return 0.5
    score = 0
    count = 0
    for ch in form_str[-5:]:
        if ch == "W":
            score += 3
        elif ch == "D":
            score += 1
        count += 1
    return score / (count * 3) if count > 0 else 0.5


def _safe_div(a, b, default=0.0):
    return a / b if b and b > 0 else default


def build_features(home_stats: dict | None, away_stats: dict | None) -> np.ndarray | None:
    """Build a feature vector from two team stats dicts.
    Returns a 1-D numpy array or None if stats are missing."""
    if not home_stats or not away_stats:
        return None

    features = [
        # Home team features
        _form_to_numeric(home_stats.get("form")),
        _safe_div(home_stats.get("goals_for", 0), home_stats.get("matches_played", 0)),
        _safe_div(home_stats.get("goals_against", 0), home_stats.get("matches_played", 0)),
        _safe_div(home_stats.get("wins", 0), home_stats.get("matches_played", 0)),
        _safe_div(home_stats.get("home_wins", 0),
                  sum(home_stats.get(k, 0) for k in ("home_wins", "home_draws", "home_losses")) or 1),
        # Away team features
        _form_to_numeric(away_stats.get("form")),
        _safe_div(away_stats.get("goals_for", 0), away_stats.get("matches_played", 0)),
        _safe_div(away_stats.get("goals_against", 0), away_stats.get("matches_played", 0)),
        _safe_div(away_stats.get("wins", 0), away_stats.get("matches_played", 0)),
        _safe_div(away_stats.get("away_wins", 0),
                  sum(away_stats.get(k, 0) for k in ("away_wins", "away_draws", "away_losses")) or 1),
        # Relative features
        _form_to_numeric(home_stats.get("form")) - _form_to_numeric(away_stats.get("form")),
        (_safe_div(home_stats.get("goals_for", 0), home_stats.get("matches_played", 0))
         + _safe_div(away_stats.get("goals_for", 0), away_stats.get("matches_played", 0))),
    ]
    return np.array(features, dtype=np.float32)


FEATURE_NAMES = [
    "home_form", "home_gf_avg", "home_ga_avg", "home_win_rate", "home_home_win_rate",
    "away_form", "away_gf_avg", "away_ga_avg", "away_win_rate", "away_away_win_rate",
    "form_diff", "combined_gf_avg",
]


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def _build_training_data() -> tuple[pd.DataFrame, pd.Series, pd.Series] | None:
    """Build training dataset from finished fixtures + stored team stats."""
    finished = db.get_finished_fixtures()
    if len(finished) < MIN_TRAINING_SAMPLES:
        log.info("Not enough finished fixtures for training (%d < %d)", len(finished), MIN_TRAINING_SAMPLES)
        return None

    rows = []
    labels_1x2 = []
    labels_ou25 = []

    for fix in finished:
        # We need stats for both teams at the time of the fixture.
        # Use the stored season stats (approximation — they reflect latest, not point-in-time).
        home_stats = db.get_team_stats(fix["home_team_api_id"], fix["league_api_id"],
                                        _season_from_date(fix["date"]))
        away_stats = db.get_team_stats(fix["away_team_api_id"], fix["league_api_id"],
                                        _season_from_date(fix["date"]))

        feats = build_features(home_stats, away_stats)
        if feats is None:
            continue

        hg = fix["home_goals"] or 0
        ag = fix["away_goals"] or 0
        if hg > ag:
            label_1x2 = 0  # Home
        elif hg == ag:
            label_1x2 = 1  # Draw
        else:
            label_1x2 = 2  # Away

        label_ou25 = 1 if (hg + ag) > 2 else 0  # Over=1, Under=0

        rows.append(feats)
        labels_1x2.append(label_1x2)
        labels_ou25.append(label_ou25)

    if len(rows) < MIN_TRAINING_SAMPLES:
        return None

    X = pd.DataFrame(rows, columns=FEATURE_NAMES)
    return X, pd.Series(labels_1x2), pd.Series(labels_ou25)


def _season_from_date(date_str: str) -> int:
    """Guess season year from fixture date. E.g. 2025-09 -> 2025, 2026-02 -> 2025."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.year if dt.month >= 7 else dt.year - 1
    except (ValueError, TypeError):
        return datetime.now().year


def train_models() -> str:
    """Train both XGBoost models on all available data. Returns model version string."""
    result = _build_training_data()
    if result is None:
        return ""

    X, y_1x2, y_ou25 = result

    # 1X2 Multi-class
    model_1x2 = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        objective="multi:softprob",
        num_class=3,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
    )
    model_1x2.fit(X, y_1x2)

    # Over/Under Binary
    model_ou25 = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        objective="binary:logistic",
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
    )
    model_ou25.fit(X, y_ou25)

    version = datetime.now(timezone.utc).strftime("v%Y%m%d_%H%M%S")
    joblib.dump(model_1x2, MODEL_1X2_PATH)
    joblib.dump(model_ou25, MODEL_OU25_PATH)
    joblib.dump({"version": version, "n_samples": len(X), "trained_at": _now_iso()}, META_PATH)
    log.info("Models trained: %s (%d samples)", version, len(X))
    return version


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

def predict(home_stats: dict | None, away_stats: dict | None, odds: dict | None = None) -> dict | None:
    """Predict match outcome probabilities. Returns dict with probs or None."""
    feats = build_features(home_stats, away_stats)

    # Try XGBoost models
    if feats is not None and MODEL_1X2_PATH.exists() and MODEL_OU25_PATH.exists():
        try:
            model_1x2 = joblib.load(MODEL_1X2_PATH)
            model_ou25 = joblib.load(MODEL_OU25_PATH)
            meta = joblib.load(META_PATH) if META_PATH.exists() else {}

            X = pd.DataFrame([feats], columns=FEATURE_NAMES)
            probs_1x2 = model_1x2.predict_proba(X)[0]
            probs_ou25 = model_ou25.predict_proba(X)[0]

            return {
                "home_prob": float(probs_1x2[0]),
                "draw_prob": float(probs_1x2[1]),
                "away_prob": float(probs_1x2[2]),
                "over25_prob": float(probs_ou25[1]) if len(probs_ou25) > 1 else 0.5,
                "under25_prob": float(probs_ou25[0]) if len(probs_ou25) > 1 else 0.5,
                "model_version": meta.get("version", "unknown"),
            }
        except Exception as e:
            log.error("XGBoost prediction failed: %s", e)

    # Fallback: simple statistical model
    return _fallback_predict(home_stats, away_stats, odds)


def _fallback_predict(home_stats: dict | None, away_stats: dict | None, odds: dict | None = None) -> dict:
    """Heuristic prediction when XGBoost is not available.
    Uses odds-implied probabilities when available, blended with stats if present."""

    # --- Start from odds-implied probabilities if we have odds ---
    if odds and odds.get("home_odd") and odds.get("draw_odd") and odds.get("away_odd"):
        ho = float(odds["home_odd"])
        do = float(odds["draw_odd"])
        ao = float(odds["away_odd"])
        # Raw implied probabilities (include bookmaker margin)
        raw_h = 1.0 / ho if ho > 0 else 0.33
        raw_d = 1.0 / do if do > 0 else 0.33
        raw_a = 1.0 / ao if ao > 0 else 0.33
        total = raw_h + raw_d + raw_a
        # Normalise to remove overround
        home_prob = raw_h / total
        draw_prob = raw_d / total
        away_prob = raw_a / total
    else:
        # No odds available — use global football averages
        home_prob = 0.45
        draw_prob = 0.25
        away_prob = 0.30

    over25_prob = 0.50

    # If over/under odds available, compute implied probability
    if odds and odds.get("over25_odd") and odds.get("under25_odd"):
        oo = float(odds["over25_odd"])
        uo = float(odds["under25_odd"])
        raw_over = 1.0 / oo if oo > 0 else 0.5
        raw_under = 1.0 / uo if uo > 0 else 0.5
        total_ou = raw_over + raw_under
        over25_prob = raw_over / total_ou if total_ou > 0 else 0.5

    if home_stats and away_stats:
        h_mp = max(home_stats.get("matches_played", 0), 1)
        a_mp = max(away_stats.get("matches_played", 0), 1)

        h_wr = home_stats.get("wins", 0) / h_mp
        a_wr = away_stats.get("wins", 0) / a_mp
        h_dr = home_stats.get("draws", 0) / h_mp
        a_dr = away_stats.get("draws", 0) / a_mp

        # Weight home advantage
        home_strength = h_wr * 0.6 + (1 - a_wr) * 0.4
        away_strength = a_wr * 0.6 + (1 - h_wr) * 0.4
        draw_strength = (h_dr + a_dr) / 2

        total = home_strength + draw_strength + away_strength
        if total > 0:
            stat_home = home_strength / total
            stat_draw = draw_strength / total
            stat_away = away_strength / total

            # Blend: 60% odds-implied (or default), 40% stats-based
            home_prob = home_prob * 0.6 + stat_home * 0.4
            draw_prob = draw_prob * 0.6 + stat_draw * 0.4
            away_prob = away_prob * 0.6 + stat_away * 0.4
            # Re-normalise
            t = home_prob + draw_prob + away_prob
            home_prob /= t
            draw_prob /= t
            away_prob /= t

        # Goals
        h_gf_avg = home_stats.get("goals_for", 0) / h_mp
        a_gf_avg = away_stats.get("goals_for", 0) / a_mp
        avg_goals = h_gf_avg + a_gf_avg
        # Rough sigmoid-like: if avg_goals > 2.5 → more likely over
        over25_prob = min(0.85, max(0.15, 0.3 + (avg_goals - 2.5) * 0.2))

    has_odds = odds and odds.get("home_odd")
    has_stats = home_stats and away_stats
    if has_odds and has_stats:
        version = "fallback_odds+stats"
    elif has_odds:
        version = "fallback_odds"
    elif has_stats:
        version = "fallback_stats"
    else:
        version = "fallback_defaults"

    return {
        "home_prob": home_prob,
        "draw_prob": draw_prob,
        "away_prob": away_prob,
        "over25_prob": over25_prob,
        "under25_prob": 1 - over25_prob,
        "model_version": version,
    }


def get_model_info() -> dict:
    """Return metadata about the currently trained model."""
    if META_PATH.exists():
        return joblib.load(META_PATH)
    return {"version": "none", "n_samples": 0, "trained_at": None}


def should_retrain() -> bool:
    """Check if we should retrain (enough new data since last training)."""
    meta = get_model_info()
    last_trained = meta.get("trained_at")
    if not last_trained:
        return True
    new_count = db.count_finished_since(last_trained)
    return new_count >= RETRAIN_THRESHOLD

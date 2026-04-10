from core.config import DROPPING_ODDS_THRESHOLD
from core import database as db


def detect_dropping_odds(fixture_api_id: int) -> list[dict]:
    """Analyse odds snapshots for a fixture and detect significant drops.

    Returns list of dicts with market, direction, pct_change for each detected drop.
    """
    snapshots = db.get_odds_snapshots(fixture_api_id)
    if len(snapshots) < 2:
        return []

    first = snapshots[0]
    latest = snapshots[-1]

    drops = []
    markets = [
        ("Hazai (1)", "home_odd"),
        ("Döntetlen (X)", "draw_odd"),
        ("Vendég (2)", "away_odd"),
        ("2.5 Felett", "over25_odd"),
        ("2.5 Alatt", "under25_odd"),
    ]

    for label, key in markets:
        old_val = first.get(key)
        new_val = latest.get(key)
        if not old_val or not new_val or old_val <= 0:
            continue

        pct_change = (new_val - old_val) / old_val

        if pct_change < -DROPPING_ODDS_THRESHOLD:
            drops.append({
                "market": label,
                "opening_odd": old_val,
                "current_odd": new_val,
                "pct_change": pct_change,
                "direction": "drop",
            })
        elif pct_change > DROPPING_ODDS_THRESHOLD:
            drops.append({
                "market": label,
                "opening_odd": old_val,
                "current_odd": new_val,
                "pct_change": pct_change,
                "direction": "rise",
            })

    return drops


def get_odds_history_df(fixture_api_id: int):
    """Return odds snapshots as a list of dicts suitable for charting."""
    snapshots = db.get_odds_snapshots(fixture_api_id)
    return snapshots

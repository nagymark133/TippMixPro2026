import logging
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

import requests

from core.config import (
    API_FOOTBALL_BASE,
    API_FOOTBALL_HEADERS,
    API_FOOTBALL_KEY,
    DATA_DIR,
    CACHE_TTL_HOURS,
)
from core import database as db

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate-limit state
# ---------------------------------------------------------------------------
_RATELIMIT_FILE = DATA_DIR / "ratelimit.json"

def get_rate_limit_info() -> dict:
    # Try reading from disk
    if _RATELIMIT_FILE.exists():
        try:
            with open(_RATELIMIT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Only use if from today
            stored_date = data.get("date")
            if stored_date == datetime.now(timezone.utc).strftime("%Y-%m-%d"):
                return {"remaining": data.get("remaining"), "limit": data.get("limit")}
        except Exception:
            pass

    # If no data for today yet, return safe fallback or None
    return {"remaining": None, "limit": None}

def _update_rate_limit(remaining: str | None, limit: str | None):
    if remaining is None or limit is None:
        return
    try:
        rem = int(remaining)
        lim = int(limit)
        data = {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "remaining": rem,
            "limit": lim
        }
        with open(_RATELIMIT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Low-level request helper
# ---------------------------------------------------------------------------

def _request(endpoint: str, params: dict | None = None) -> dict | None:
    if not API_FOOTBALL_KEY:
        log.warning("API_FOOTBALL_KEY not configured")
        return None

    url = f"{API_FOOTBALL_BASE}/{endpoint.lstrip('/')}"
    try:
        resp = requests.get(url, headers=API_FOOTBALL_HEADERS, params=params, timeout=15)
        
        # Track rate limits from response headers
        _update_rate_limit(
            resp.headers.get("x-ratelimit-requests-remaining"),
            resp.headers.get("x-ratelimit-requests-limit")
        )
            
        resp.raise_for_status()
        data = resp.json()
        if data.get("errors"):
            log.error("API-Football error: %s", data["errors"])
            return None
        return data
    except requests.RequestException as e:
        log.error("API-Football request failed: %s", e)
        return None


def _try_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def fetch_fixtures_by_date(date_str: str) -> list[dict]:
    """Fetch fixtures for a date (YYYY-MM-DD) and persist to DB.
    Returns list of fixture dicts from DB after upsert."""
    data = _request("fixtures", {"date": date_str})
    if not data or not data.get("response"):
        return db.get_fixtures_by_date(date_str)

    for item in data["response"]:
        fix = item["fixture"]
        league = item["league"]
        teams = item["teams"]
        goals = item["goals"]

        # Upsert league & teams
        db.upsert_league(
            league["id"], league["name"], league.get("country", ""),
            league.get("logo", ""), league.get("season"),
        )
        db.upsert_team(teams["home"]["id"], teams["home"]["name"],
                        teams["home"].get("logo", ""), league["id"])
        db.upsert_team(teams["away"]["id"], teams["away"]["name"],
                        teams["away"].get("logo", ""), league["id"])

        db.upsert_fixture(
            api_id=fix["id"],
            league_api_id=league["id"],
            home_team_api_id=teams["home"]["id"],
            away_team_api_id=teams["away"]["id"],
            date=fix["date"],
            status=fix["status"]["short"],
            home_goals=goals.get("home"),
            away_goals=goals.get("away"),
            referee=fix.get("referee"),
            venue=fix.get("venue", {}).get("name") if fix.get("venue") else None,
        )

    return db.get_fixtures_by_date(date_str)


# ---------------------------------------------------------------------------
# Odds
# ---------------------------------------------------------------------------

def fetch_odds_for_fixture(fixture_api_id: int) -> dict | None:
    """Fetch pre-match odds for a fixture and save a snapshot."""
    data = _request("odds", {"fixture": fixture_api_id})
    if not data or not data.get("response"):
        return db.get_latest_odds(fixture_api_id)

    for resp_item in data["response"]:
        for bm in resp_item.get("bookmakers", []):
            home_odd = draw_odd = away_odd = None
            over25 = under25 = None

            for bet in bm.get("bets", []):
                if bet["name"] == "Match Winner":
                    for v in bet["values"]:
                        if v["value"] == "Home":
                            home_odd = float(v["odd"])
                        elif v["value"] == "Draw":
                            draw_odd = float(v["odd"])
                        elif v["value"] == "Away":
                            away_odd = float(v["odd"])

                elif bet["name"] in ("Over/Under 2.5", "Goals Over/Under"):
                    for v in bet["values"]:
                        if "Over" in str(v["value"]):
                            over25 = float(v["odd"])
                        elif "Under" in str(v["value"]):
                            under25 = float(v["odd"])

            if home_odd and draw_odd and away_odd:
                db.insert_odds_snapshot(
                    fixture_api_id, bm["name"],
                    home_odd, draw_odd, away_odd, over25, under25,
                )
            break  # first bookmaker only to save API calls

    return db.get_latest_odds(fixture_api_id)


# ---------------------------------------------------------------------------
# Team Statistics
# ---------------------------------------------------------------------------

def _is_cache_fresh(updated_at_iso: str | None) -> bool:
    if not updated_at_iso:
        return False
    try:
        updated = datetime.fromisoformat(updated_at_iso)
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - updated < timedelta(hours=CACHE_TTL_HOURS)
    except (ValueError, TypeError):
        return False


def fetch_team_statistics(team_api_id: int, league_api_id: int, season: int) -> dict | None:
    """Fetch team season statistics. Uses cache if fresh.
    Falls back to older seasons if the requested season is not available on the free plan."""
    cached = db.get_team_stats(team_api_id, league_api_id, season)
    if cached and cached.get("matches_played", 0) > 0 and _is_cache_fresh(cached.get("updated_at")):
        return cached

    # Try requested season first, then fall back to older seasons (free plan: 2022-2024)
    seasons_to_try = [season]
    if season > 2024:
        seasons_to_try.extend([2024, 2023])

    data = None
    used_season = season
    for s in seasons_to_try:
        data = _request("teams/statistics", {
            "team": team_api_id,
            "league": league_api_id,
            "season": s,
        })
        if data and data.get("response"):
            used_season = s
            break
        data = None

    if not data or not data.get("response"):
        return cached

    r = data["response"]
    fixtures_data = r.get("fixtures", {})
    goals_data = r.get("goals", {})

    stats = {
        "matches_played": _safe_int(fixtures_data.get("played", {}).get("total")),
        "wins": _safe_int(fixtures_data.get("wins", {}).get("total")),
        "draws": _safe_int(fixtures_data.get("draws", {}).get("total")),
        "losses": _safe_int(fixtures_data.get("loses", {}).get("total")),
        "goals_for": _safe_int(goals_data.get("for", {}).get("total", {}).get("total")),
        "goals_against": _safe_int(goals_data.get("against", {}).get("total", {}).get("total")),
        "home_wins": _safe_int(fixtures_data.get("wins", {}).get("home")),
        "home_draws": _safe_int(fixtures_data.get("draws", {}).get("home")),
        "home_losses": _safe_int(fixtures_data.get("loses", {}).get("home")),
        "away_wins": _safe_int(fixtures_data.get("wins", {}).get("away")),
        "away_draws": _safe_int(fixtures_data.get("draws", {}).get("away")),
        "away_losses": _safe_int(fixtures_data.get("loses", {}).get("away")),
        "form": r.get("form", ""),
    }
    db.upsert_team_season_stats(team_api_id, league_api_id, season, **stats)
    return db.get_team_stats(team_api_id, league_api_id, season)


def _safe_int(val):
    try:
        return int(val) if val is not None else 0
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# Head-to-Head
# ---------------------------------------------------------------------------

def fetch_head_to_head(team1_api_id: int, team2_api_id: int, last: int = 10) -> list[dict]:
    """Fetch last N head-to-head fixtures between two teams."""
    data = _request("fixtures/headtohead", {
        "h2h": f"{team1_api_id}-{team2_api_id}",
        "last": last,
    })
    if not data or not data.get("response"):
        return []

    results = []
    for item in data["response"]:
        fix = item["fixture"]
        teams = item["teams"]
        goals = item["goals"]
        results.append({
            "date": fix["date"],
            "home_team": teams["home"]["name"],
            "away_team": teams["away"]["name"],
            "home_goals": goals.get("home"),
            "away_goals": goals.get("away"),
            "home_team_id": teams["home"]["id"],
            "away_team_id": teams["away"]["id"],
        })

        # Also persist to fixtures table
        db.upsert_fixture(
            api_id=fix["id"],
            league_api_id=item["league"]["id"],
            home_team_api_id=teams["home"]["id"],
            away_team_api_id=teams["away"]["id"],
            date=fix["date"],
            status=fix["status"]["short"],
            home_goals=goals.get("home"),
            away_goals=goals.get("away"),
            referee=fix.get("referee"),
            venue=fix.get("venue", {}).get("name") if fix.get("venue") else None,
        )
    return results


# ---------------------------------------------------------------------------
# Fetch finished results (for settlement)
# ---------------------------------------------------------------------------

def fetch_fixture_results(fixture_api_ids: list[int]) -> dict[int, dict]:
    """Fetch current status of specific fixtures. Returns {api_id: {status, home_goals, away_goals}}."""
    results = {}
    for fid in fixture_api_ids:
        data = _request("fixtures", {"id": fid})
        if not data or not data.get("response"):
            continue
        item = data["response"][0]
        fix = item["fixture"]
        goals = item["goals"]
        status = fix["status"]["short"]
        if status == "FT":
            db.upsert_fixture(
                api_id=fix["id"],
                league_api_id=item["league"]["id"],
                home_team_api_id=item["teams"]["home"]["id"],
                away_team_api_id=item["teams"]["away"]["id"],
                date=fix["date"],
                status=status,
                home_goals=goals.get("home"),
                away_goals=goals.get("away"),
                referee=fix.get("referee"),
                venue=fix.get("venue", {}).get("name") if fix.get("venue") else None,
            )
        results[fix["id"]] = {
            "status": status,
            "home_goals": goals.get("home"),
            "away_goals": goals.get("away"),
        }
    return results

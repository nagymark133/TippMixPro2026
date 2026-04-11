"""
Football-Data.org API client (v4) — replacement for the former API-Football integration.
https://www.football-data.org/documentation/quickstart

Free tier: 10 requests/minute, 12 supported competitions.
Odds are NOT available on the free tier — the app falls back to DB-cached values.
"""

import logging
import json
from datetime import datetime, timezone, timedelta

import requests

from core.config import (
    FOOTBALL_DATA_BASE,
    FOOTBALL_DATA_HEADERS,
    FOOTBALL_DATA_KEY,
    DATA_DIR,
    CACHE_TTL_HOURS,
)
from core import database as db

log = logging.getLogger(__name__)

# Last API failure reason for UI diagnostics.
_LAST_API_ERROR: str | None = None

# ---------------------------------------------------------------------------
# Status mapping: Football-Data.org -> internal short codes (FT, NS, …)
# ---------------------------------------------------------------------------
_STATUS_MAP = {
    "FINISHED": "FT",
    "SCHEDULED": "NS",
    "TIMED": "NS",
    "IN_PLAY": "1H",
    "PAUSED": "HT",
    "EXTRA_TIME": "ET",
    "PENALTY_SHOOTOUT": "P",
    "SUSPENDED": "SUSP",
    "POSTPONED": "PST",
    "CANCELLED": "CANC",
    "AWARDED": "FT",
}

# ---------------------------------------------------------------------------
# Rate-limit state (Football-Data.org: 10 req/min on free tier)
# ---------------------------------------------------------------------------
_RATELIMIT_FILE = DATA_DIR / "ratelimit.json"


def get_rate_limit_info() -> dict:
    if _RATELIMIT_FILE.exists():
        try:
            with open(_RATELIMIT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            stored_date = data.get("date")
            if stored_date == datetime.now(timezone.utc).strftime("%Y-%m-%d"):
                return {"remaining": data.get("remaining"), "limit": data.get("limit")}
        except Exception:
            pass
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
            "limit": lim,
        }
        with open(_RATELIMIT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Low-level request helper
# ---------------------------------------------------------------------------

def _request(endpoint: str, params: dict | None = None) -> dict | None:
    global _LAST_API_ERROR
    _LAST_API_ERROR = None

    if not FOOTBALL_DATA_KEY:
        log.warning("FOOTBALL_DATA_KEY not configured")
        _LAST_API_ERROR = "FOOTBALL_DATA_KEY is missing"
        return None

    url = f"{FOOTBALL_DATA_BASE}/{endpoint.lstrip('/')}"
    try:
        resp = requests.get(url, headers=FOOTBALL_DATA_HEADERS, params=params, timeout=15)
        # Football-Data.org header: X-Requests-Available-Minute (remaining in current window)
        _update_rate_limit(
            resp.headers.get("X-Requests-Available-Minute"),
            "10",  # free tier: 10/min
        )
        if not resp.ok:
            preview = (resp.text or "")[:240].replace("\n", " ")
            _LAST_API_ERROR = f"HTTP {resp.status_code} from Football-Data API: {preview}"
            resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        log.error("Football-Data.org request failed: %s", e)
        if _LAST_API_ERROR is None:
            _LAST_API_ERROR = f"Request failed: {e}"
        return None


def get_last_api_error() -> str | None:
    return _LAST_API_ERROR


def _safe_int(val) -> int:
    try:
        return int(val) if val is not None else 0
    except (TypeError, ValueError):
        return 0


def _normalize_form(form_str: str | None) -> str:
    """Convert Football-Data.org comma-separated form (e.g. 'W,W,D,L,W') to compact string 'WWDLW'."""
    if not form_str:
        return ""
    # Already compact format
    if "," not in form_str:
        return form_str
    return "".join(c for c in form_str.split(",") if c in ("W", "D", "L"))


# ---------------------------------------------------------------------------
# Fixtures / Matches
# ---------------------------------------------------------------------------

def fetch_fixtures_by_date(date_str: str) -> list[dict]:
    """Fetch fixtures for a date (YYYY-MM-DD) and persist to DB."""
    data = _request("matches", {"dateFrom": date_str, "dateTo": date_str})
    if not data or not data.get("matches"):
        return db.get_fixtures_by_date(date_str)

    for item in data["matches"]:
        competition = item.get("competition", {})
        area = item.get("area", competition.get("area", {}))
        home = item.get("homeTeam", {})
        away = item.get("awayTeam", {})
        score = item.get("score", {})
        full_time = score.get("fullTime", {})
        status = _STATUS_MAP.get(item.get("status", ""), "NS")

        db.upsert_league(
            competition["id"],
            competition.get("name", ""),
            area.get("name", ""),
            competition.get("emblem", ""),
            item.get("season", {}).get("id"),
        )
        db.upsert_team(home["id"], home.get("name", ""), home.get("crest", ""), competition["id"])
        db.upsert_team(away["id"], away.get("name", ""), away.get("crest", ""), competition["id"])

        home_goals = _safe_int(full_time.get("home")) if status == "FT" else None
        away_goals = _safe_int(full_time.get("away")) if status == "FT" else None

        referees = item.get("referees", [])
        referee = referees[0].get("name") if referees else None

        db.upsert_fixture(
            api_id=item["id"],
            league_api_id=competition["id"],
            home_team_api_id=home["id"],
            away_team_api_id=away["id"],
            date=item.get("utcDate", date_str),
            status=status,
            home_goals=home_goals,
            away_goals=away_goals,
            referee=referee,
            venue=item.get("venue"),
        )

    return db.get_fixtures_by_date(date_str)


# ---------------------------------------------------------------------------
# Odds — not available on the Football-Data.org free tier
# ---------------------------------------------------------------------------

def fetch_odds_for_fixture(fixture_api_id: int) -> dict | None:
    """Football-Data.org free tier does not provide odds. Returns DB-cached value only."""
    return db.get_latest_odds(fixture_api_id)


# ---------------------------------------------------------------------------
# Team Statistics (via competition standings)
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
    """Fetch team season statistics via competition standings.
    Falls back to previous seasons if the current season is not yet available."""
    cached = db.get_team_stats(team_api_id, league_api_id, season)
    if cached and cached.get("matches_played", 0) > 0 and _is_cache_fresh(cached.get("updated_at")):
        return cached

    seasons_to_try = [season, season - 1, season - 2]
    for s in seasons_to_try:
        data = _request(f"competitions/{league_api_id}/standings", {"season": s})
        if not data or not data.get("standings"):
            continue

        total_row = home_row = away_row = None
        for table in data["standings"]:
            stype = table.get("type", "TOTAL")
            for row in table.get("table", []):
                if row.get("team", {}).get("id") == team_api_id:
                    if stype == "TOTAL":
                        total_row = row
                    elif stype == "HOME":
                        home_row = row
                    elif stype == "AWAY":
                        away_row = row

        if not total_row:
            continue

        stats = {
            "matches_played": _safe_int(total_row.get("playedGames")),
            "wins": _safe_int(total_row.get("won")),
            "draws": _safe_int(total_row.get("draw")),
            "losses": _safe_int(total_row.get("lost")),
            "goals_for": _safe_int(total_row.get("goalsFor")),
            "goals_against": _safe_int(total_row.get("goalsAgainst")),
            "home_wins": _safe_int(home_row.get("won")) if home_row else 0,
            "home_draws": _safe_int(home_row.get("draw")) if home_row else 0,
            "home_losses": _safe_int(home_row.get("lost")) if home_row else 0,
            "away_wins": _safe_int(away_row.get("won")) if away_row else 0,
            "away_draws": _safe_int(away_row.get("draw")) if away_row else 0,
            "away_losses": _safe_int(away_row.get("lost")) if away_row else 0,
            "form": _normalize_form(total_row.get("form", "")),
        }
        db.upsert_team_season_stats(team_api_id, league_api_id, season, **stats)
        return db.get_team_stats(team_api_id, league_api_id, season)

    return cached


# ---------------------------------------------------------------------------
# Head-to-Head
# ---------------------------------------------------------------------------

def fetch_head_to_head(team1_api_id: int, team2_api_id: int, last: int = 10) -> list[dict]:
    """Fetch last N head-to-head finished matches between two teams."""
    data = _request(f"teams/{team1_api_id}/matches", {"status": "FINISHED", "limit": 50})
    if not data or not data.get("matches"):
        return []

    results = []
    for item in data["matches"]:
        home = item.get("homeTeam", {})
        away = item.get("awayTeam", {})
        if home.get("id") != team2_api_id and away.get("id") != team2_api_id:
            continue
        score = item.get("score", {})
        ft = score.get("fullTime", {})
        results.append({
            "date": item.get("utcDate"),
            "home_team": home.get("name", ""),
            "away_team": away.get("name", ""),
            "home_goals": ft.get("home"),
            "away_goals": ft.get("away"),
            "home_team_id": home["id"],
            "away_team_id": away["id"],
        })
        if len(results) >= last:
            break

    return results


# ---------------------------------------------------------------------------
# Fetch finished results (for bet settlement)
# ---------------------------------------------------------------------------

def fetch_fixture_results(fixture_api_ids: list[int]) -> dict[int, dict]:
    """Fetch current status of specific matches. Returns {api_id: {status, home_goals, away_goals}}."""
    results = {}
    for fid in fixture_api_ids:
        data = _request(f"matches/{fid}")
        if not data:
            continue
        score = data.get("score", {})
        ft = score.get("fullTime", {})
        raw_status = data.get("status", "")
        status = _STATUS_MAP.get(raw_status, "NS")

        if status == "FT":
            competition = data.get("competition", {})
            home = data.get("homeTeam", {})
            away = data.get("awayTeam", {})
            referees = data.get("referees", [])
            referee = referees[0].get("name") if referees else None
            db.upsert_fixture(
                api_id=data["id"],
                league_api_id=competition.get("id", 0),
                home_team_api_id=home.get("id", 0),
                away_team_api_id=away.get("id", 0),
                date=data.get("utcDate", ""),
                status=status,
                home_goals=ft.get("home"),
                away_goals=ft.get("away"),
                referee=referee,
                venue=data.get("venue"),
            )

        results[fid] = {
            "status": status,
            "home_goals": ft.get("home"),
            "away_goals": ft.get("away"),
        }
    return results

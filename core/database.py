import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from core.config import DB_PATH, DEFAULT_INITIAL_BALANCE

# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leagues (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    api_id          INTEGER UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    country         TEXT,
    logo            TEXT,
    current_season  INTEGER
);

CREATE TABLE IF NOT EXISTS teams (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    api_id          INTEGER UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    logo            TEXT,
    league_api_id   INTEGER
);

CREATE TABLE IF NOT EXISTS fixtures (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    api_id              INTEGER UNIQUE NOT NULL,
    league_api_id       INTEGER,
    home_team_api_id    INTEGER NOT NULL,
    away_team_api_id    INTEGER NOT NULL,
    date                TEXT NOT NULL,
    status              TEXT DEFAULT 'NS',
    home_goals          INTEGER,
    away_goals          INTEGER,
    referee             TEXT,
    venue               TEXT,
    updated_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS odds_snapshots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    fixture_api_id      INTEGER NOT NULL,
    bookmaker           TEXT,
    home_odd            REAL,
    draw_odd            REAL,
    away_odd            REAL,
    over25_odd          REAL,
    under25_odd         REAL,
    snapshot_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS team_season_stats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    team_api_id     INTEGER NOT NULL,
    league_api_id   INTEGER NOT NULL,
    season          INTEGER NOT NULL,
    matches_played  INTEGER DEFAULT 0,
    wins            INTEGER DEFAULT 0,
    draws           INTEGER DEFAULT 0,
    losses          INTEGER DEFAULT 0,
    goals_for       INTEGER DEFAULT 0,
    goals_against   INTEGER DEFAULT 0,
    home_wins       INTEGER DEFAULT 0,
    home_draws      INTEGER DEFAULT 0,
    home_losses     INTEGER DEFAULT 0,
    away_wins       INTEGER DEFAULT 0,
    away_draws      INTEGER DEFAULT 0,
    away_losses     INTEGER DEFAULT 0,
    form            TEXT,
    updated_at      TEXT NOT NULL,
    UNIQUE(team_api_id, league_api_id, season)
);

CREATE TABLE IF NOT EXISTS predictions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fixture_api_id  INTEGER NOT NULL,
    home_prob       REAL,
    draw_prob       REAL,
    away_prob       REAL,
    over25_prob     REAL,
    under25_prob    REAL,
    model_version   TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_bets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fixture_api_id  INTEGER NOT NULL,
    bet_type        TEXT NOT NULL,
    selection       TEXT NOT NULL,
    odds            REAL NOT NULL,
    stake           REAL NOT NULL,
    result          TEXT,
    profit          REAL,
    created_at      TEXT NOT NULL,
    settled_at      TEXT
);

CREATE TABLE IF NOT EXISTS bankroll (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    balance         REAL NOT NULL,
    initial_balance REAL NOT NULL,
    updated_at      TEXT NOT NULL
);
"""


def init_db():
    with get_db() as conn:
        conn.executescript(_SCHEMA)
        # Seed bankroll if empty
        row = conn.execute("SELECT COUNT(*) as cnt FROM bankroll").fetchone()
        if row["cnt"] == 0:
            conn.execute(
                "INSERT INTO bankroll (balance, initial_balance, updated_at) VALUES (?, ?, ?)",
                (DEFAULT_INITIAL_BALANCE, DEFAULT_INITIAL_BALANCE, _now_iso()),
            )


# ---------------------------------------------------------------------------
# Leagues
# ---------------------------------------------------------------------------

def upsert_league(api_id, name, country, logo, current_season):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO leagues (api_id, name, country, logo, current_season)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(api_id) DO UPDATE SET
                 name=excluded.name, country=excluded.country,
                 logo=excluded.logo, current_season=excluded.current_season""",
            (api_id, name, country, logo, current_season),
        )


def get_all_leagues():
    with get_db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM leagues ORDER BY country, name").fetchall()]


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

def upsert_team(api_id, name, logo, league_api_id=None):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO teams (api_id, name, logo, league_api_id)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(api_id) DO UPDATE SET
                 name=excluded.name, logo=excluded.logo,
                 league_api_id=COALESCE(excluded.league_api_id, teams.league_api_id)""",
            (api_id, name, logo, league_api_id),
        )


def get_team(api_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM teams WHERE api_id=?", (api_id,)).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def upsert_fixture(api_id, league_api_id, home_team_api_id, away_team_api_id,
                   date, status, home_goals, away_goals, referee, venue):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO fixtures
               (api_id, league_api_id, home_team_api_id, away_team_api_id,
                date, status, home_goals, away_goals, referee, venue, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(api_id) DO UPDATE SET
                 status=excluded.status, home_goals=excluded.home_goals,
                 away_goals=excluded.away_goals, referee=excluded.referee,
                 venue=excluded.venue, updated_at=excluded.updated_at""",
            (api_id, league_api_id, home_team_api_id, away_team_api_id,
             date, status, home_goals, away_goals, referee, venue, _now_iso()),
        )


def get_fixtures_by_date(date_str):
    """Return fixtures for a given date (YYYY-MM-DD)."""
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM fixtures WHERE date LIKE ? ORDER BY date",
            (f"{date_str}%",),
        ).fetchall()]


def get_finished_fixtures():
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM fixtures WHERE status='FT' ORDER BY date DESC"
        ).fetchall()]


def get_fixture_by_api_id(api_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM fixtures WHERE api_id=?", (api_id,)).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Odds Snapshots
# ---------------------------------------------------------------------------

def insert_odds_snapshot(fixture_api_id, bookmaker, home_odd, draw_odd, away_odd,
                         over25_odd=None, under25_odd=None):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO odds_snapshots
               (fixture_api_id, bookmaker, home_odd, draw_odd, away_odd,
                over25_odd, under25_odd, snapshot_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (fixture_api_id, bookmaker, home_odd, draw_odd, away_odd,
             over25_odd, under25_odd, _now_iso()),
        )


def get_odds_snapshots(fixture_api_id):
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM odds_snapshots WHERE fixture_api_id=? ORDER BY snapshot_at",
            (fixture_api_id,),
        ).fetchall()]


def get_latest_odds(fixture_api_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM odds_snapshots WHERE fixture_api_id=? ORDER BY snapshot_at DESC LIMIT 1",
            (fixture_api_id,),
        ).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Team Season Stats
# ---------------------------------------------------------------------------

def upsert_team_season_stats(team_api_id, league_api_id, season, **kwargs):
    with get_db() as conn:
        cols = ["team_api_id", "league_api_id", "season"]
        vals = [team_api_id, league_api_id, season]
        update_parts = []
        for k, v in kwargs.items():
            cols.append(k)
            vals.append(v)
            update_parts.append(f"{k}=excluded.{k}")
        cols.append("updated_at")
        vals.append(_now_iso())
        update_parts.append("updated_at=excluded.updated_at")

        placeholders = ",".join(["?"] * len(vals))
        col_str = ",".join(cols)
        update_str = ",".join(update_parts)

        conn.execute(
            f"""INSERT INTO team_season_stats ({col_str})
                VALUES ({placeholders})
                ON CONFLICT(team_api_id, league_api_id, season) DO UPDATE SET {update_str}""",
            vals,
        )


def get_team_stats(team_api_id, league_api_id, season):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM team_season_stats WHERE team_api_id=? AND league_api_id=? AND season=?",
            (team_api_id, league_api_id, season),
        ).fetchone()
        return dict(row) if row else None


def get_all_team_stats_for_season(league_api_id, season):
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM team_season_stats WHERE league_api_id=? AND season=?",
            (league_api_id, season),
        ).fetchall()]


# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------

def insert_prediction(fixture_api_id, home_prob, draw_prob, away_prob,
                      over25_prob, under25_prob, model_version):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO predictions
               (fixture_api_id, home_prob, draw_prob, away_prob,
                over25_prob, under25_prob, model_version, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (fixture_api_id, home_prob, draw_prob, away_prob,
             over25_prob, under25_prob, model_version, _now_iso()),
        )


def get_prediction(fixture_api_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM predictions WHERE fixture_api_id=? ORDER BY created_at DESC LIMIT 1",
            (fixture_api_id,),
        ).fetchone()
        return dict(row) if row else None


def get_all_predictions_with_results():
    """Return predictions joined with finished fixtures for model evaluation."""
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            """SELECT p.*, f.home_goals, f.away_goals, f.status
               FROM predictions p
               JOIN fixtures f ON f.api_id = p.fixture_api_id
               WHERE f.status = 'FT'
               ORDER BY p.created_at DESC"""
        ).fetchall()]


# ---------------------------------------------------------------------------
# Paper Bets
# ---------------------------------------------------------------------------

def insert_paper_bet(fixture_api_id, bet_type, selection, odds, stake):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO paper_bets
               (fixture_api_id, bet_type, selection, odds, stake, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (fixture_api_id, bet_type, selection, odds, stake, _now_iso()),
        )
        # Deduct stake from bankroll
        conn.execute(
            "UPDATE bankroll SET balance = balance - ?, updated_at = ? WHERE id = 1",
            (stake, _now_iso()),
        )


def get_pending_bets():
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM paper_bets WHERE result IS NULL ORDER BY created_at DESC"
        ).fetchall()]


def get_settled_bets():
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM paper_bets WHERE result IS NOT NULL ORDER BY settled_at DESC"
        ).fetchall()]


def settle_bet(bet_id, result, profit):
    with get_db() as conn:
        conn.execute(
            "UPDATE paper_bets SET result=?, profit=?, settled_at=? WHERE id=?",
            (result, profit, _now_iso(), bet_id),
        )
        if profit > 0:
            conn.execute(
                "UPDATE bankroll SET balance = balance + ?, updated_at = ? WHERE id = 1",
                (profit, _now_iso()),
            )


# ---------------------------------------------------------------------------
# Bankroll
# ---------------------------------------------------------------------------

def get_bankroll():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM bankroll WHERE id=1").fetchone()
        return dict(row) if row else None


def reset_bankroll(initial=None):
    amount = initial or DEFAULT_INITIAL_BALANCE
    with get_db() as conn:
        conn.execute(
            "UPDATE bankroll SET balance=?, initial_balance=?, updated_at=? WHERE id=1",
            (amount, amount, _now_iso()),
        )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def count_finished_since(iso_date):
    """Count finished fixtures updated after a given ISO date string."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM fixtures WHERE status='FT' AND updated_at > ?",
            (iso_date,),
        ).fetchone()
        return row["cnt"]

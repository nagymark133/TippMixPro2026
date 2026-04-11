import streamlit as st
import pandas as pd
import altair as alt
import time
from datetime import date, datetime
from html import escape

from core.database import init_db, get_fixtures_by_date, get_all_leagues, get_team, get_latest_odds
from core.api_football import fetch_fixtures_by_date, fetch_odds_for_fixture, get_rate_limit_info, get_last_api_error
from core.odds_tracker import detect_dropping_odds, get_odds_history_df
from core.config import FOOTBALL_DATA_KEY
from core.ui import inject_global_styles

init_db()
inject_global_styles()

st.markdown("# 📊 Napi Meccsek")
st.caption("Aznapi meccsek, odds és dropping odds figyelő")

# ---------------------------------------------------------------------------
# API Quota Bar (header)
# ---------------------------------------------------------------------------
rl = get_rate_limit_info()
if rl["remaining"] is not None and rl["limit"]:
    _pct = max(0, min(100, int(rl["remaining"] / rl["limit"] * 100)))
    _cls = "critical" if _pct < 15 else ("low" if _pct < 40 else "")
    _clr = "#ef4444" if _pct < 15 else ("#f59e0b" if _pct < 40 else "#10b981")
    st.markdown(
        f'<div class="api-quota-bar">'
        f'<span class="quota-label">API Kvóta</span>'
        f'<span class="quota-value {_cls}">{rl["remaining"]}</span>'
        f'<span style="color:var(--text-muted);font-size:0.75rem;">/ {rl["limit"]}</span>'
        f'<div class="api-quota-track"><div class="api-quota-fill" style="width:{_pct}%;background:{_clr};"></div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )
elif not FOOTBALL_DATA_KEY:
    st.markdown(
        '<div class="api-quota-bar">'
        '<span class="quota-label">API</span>'
        '<span style="color:#ef4444;font-weight:700;font-size:0.85rem;">⚠️ Nincs API kulcs</span>'
        '</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------
col_date, col_btn = st.columns([3, 1])
with col_date:
    selected_date = st.date_input("📅 Dátum", value=date.today())
with col_btn:
    st.markdown("<br/>", unsafe_allow_html=True)
    refresh = st.button("🔄 Frissítés", type="primary", use_container_width=True,
                        disabled=not FOOTBALL_DATA_KEY)

date_str = selected_date.strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Fetch data
# ---------------------------------------------------------------------------
if refresh:
    with st.spinner("Meccsek letöltése..."):
        fixtures = fetch_fixtures_by_date(date_str)

    if not fixtures:
        api_error = get_last_api_error()
        if api_error:
            st.error(
                "❌ Az API nem adott vissza meccset. "
                "Ellenőrizd a FOOTBALL_DATA_KEY értékét, a kvótát és a dátumot. "
                f"Részlet: {api_error}"
            )
        elif FOOTBALL_DATA_KEY.startswith("your_") or FOOTBALL_DATA_KEY.endswith("_here"):
            st.error(
                "❌ Úgy tűnik, példa API kulcs van beállítva (placeholder). "
                "Adj meg valódi Football-Data kulcsot Streamlit Secrets-ben."
            )

    if fixtures:
        limit_fixtures = min(len(fixtures), 8)
        odds_progress = st.progress(0, text="Odds letöltése...")
        for i, fix in enumerate(fixtures[:limit_fixtures]):
            if i > 0:
                time.sleep(6.1)
            fetch_odds_for_fixture(fix["api_id"])
            odds_progress.progress((i + 1) / limit_fixtures, text=f"Odds: {i+1}/{limit_fixtures}")
        odds_progress.empty()

    st.success(f"✅ {len(fixtures)} meccs frissítve!")
else:
    fixtures = get_fixtures_by_date(date_str)

# ---------------------------------------------------------------------------
# League filter
# ---------------------------------------------------------------------------
if fixtures:
    league_ids = list({f["league_api_id"] for f in fixtures})
    leagues = get_all_leagues()
    league_map = {lg["api_id"]: lg for lg in leagues}
    league_options = {lg_id: league_map.get(lg_id, {}).get("name", f"Liga #{lg_id}") for lg_id in league_ids}

    selected_leagues = st.multiselect(
        "🏆 Liga szűrő",
        options=list(league_options.keys()),
        format_func=lambda x: league_options.get(x, str(x)),
        default=list(league_options.keys()),
    )

    filtered = [f for f in fixtures if f["league_api_id"] in selected_leagues]

    st.markdown(f'<p class="section-header">Meccsek ({len(filtered)})</p>', unsafe_allow_html=True)

    # ---------------------------------------------------------------------------
    # Display matches as premium cards
    # ---------------------------------------------------------------------------
    for fix in filtered:
        home_team = get_team(fix["home_team_api_id"]) or {}
        away_team = get_team(fix["away_team_api_id"]) or {}
        odds = get_latest_odds(fix["api_id"])
        drops = detect_dropping_odds(fix["api_id"])
        league_name = escape(league_map.get(fix["league_api_id"], {}).get("name", ""))

        # Match time
        try:
            match_time = datetime.fromisoformat(fix["date"].replace("Z", "+00:00")).strftime("%H:%M")
        except (ValueError, TypeError):
            match_time = "?"

        # Status badge
        status = fix.get("status", "NS")
        if status == "FT":
            status_badge = '<span class="badge badge-value">✅ FT</span>'
        elif status in ("1H", "2H", "HT", "LIVE"):
            status_badge = '<span class="badge badge-live badge-live-pulse">🔴 LIVE</span>'
        else:
            status_badge = f'<span class="badge badge-time">🕐 {match_time}</span>'

        # Drop badges
        drop_html = ""
        for d in drops:
            if d["direction"] == "drop":
                drop_html += f'<span class="badge badge-drop">🔻 {escape(str(d["market"]))} {d["pct_change"]:+.1%}</span>'
            else:
                drop_html += f'<span class="badge badge-rise">🔺 {escape(str(d["market"]))} {d["pct_change"]:+.1%}</span>'

        # Home/Away logos
        home_logo = home_team.get("logo", "")
        away_logo = away_team.get("logo", "")
        home_logo_html = f'<img class="team-logo" src="{escape(home_logo)}" alt=""/>' if home_logo else '<div class="team-logo" style="display:flex;align-items:center;justify-content:center;font-size:1.2rem;">🏠</div>'
        away_logo_html = f'<img class="team-logo" src="{escape(away_logo)}" alt=""/>' if away_logo else '<div class="team-logo" style="display:flex;align-items:center;justify-content:center;font-size:1.2rem;">✈️</div>'

        home_name = escape(home_team.get("name", "?"))
        away_name = escape(away_team.get("name", "?"))

        # Score or "vs"
        if fix["home_goals"] is not None and fix["away_goals"] is not None:
            score_html = f'<span class="score-big">{fix["home_goals"]} — {fix["away_goals"]}</span>'
        else:
            score_html = '<span style="color:var(--text-muted); font-size:1.1rem; font-weight:700;">VS</span>'

        # Odds display
        odds_html = ""
        if odds:
            odds_html = (
                f'<div class="odds-row">'
                f'<div class="odds-pill"><div class="label">1</div><div class="value home">{odds["home_odd"]:.2f}</div></div>'
                f'<div class="odds-pill"><div class="label">X</div><div class="value draw">{odds["draw_odd"]:.2f}</div></div>'
                f'<div class="odds-pill"><div class="label">2</div><div class="value away">{odds["away_odd"]:.2f}</div></div>'
                f'</div>'
            )

        # Drops row
        drops_html = f'<div class="drops-row">{drop_html}</div>' if drop_html else ""

        st.markdown(
            f'<div class="match-card">'
            f'<div class="league-header">'
            f'<span class="league-name">🏆 {league_name}</span>'
            f'<div style="margin-left:auto;">{status_badge}</div>'
            f'</div>'
            f'<div class="match-teams-row">'
            f'<div class="match-team home">'
            f'<span class="match-team-name">{home_name}</span>'
            f'{home_logo_html}'
            f'</div>'
            f'<div class="match-score-center">{score_html}</div>'
            f'<div class="match-team away">'
            f'{away_logo_html}'
            f'<span class="match-team-name">{away_name}</span>'
            f'</div>'
            f'</div>'
            f'{odds_html}'
            f'{drops_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Odds history sparkline (expandable)
        odds_history = get_odds_history_df(fix["api_id"])
        if len(odds_history) >= 2:
            with st.expander("📉 Odds változás", expanded=False):
                df = pd.DataFrame(odds_history)
                df["snapshot_at"] = pd.to_datetime(df["snapshot_at"])
                df_melted = df.melt(
                    id_vars=["snapshot_at"],
                    value_vars=["home_odd", "draw_odd", "away_odd"],
                    var_name="Piac",
                    value_name="Odds",
                )
                df_melted["Piac"] = df_melted["Piac"].map({
                    "home_odd": "Hazai (1)",
                    "draw_odd": "Döntetlen (X)",
                    "away_odd": "Vendég (2)",
                })
                chart = alt.Chart(df_melted).mark_line(point=True).encode(
                    x=alt.X("snapshot_at:T", title="Idő"),
                    y=alt.Y("Odds:Q", title="Odds"),
                    color=alt.Color("Piac:N", scale=alt.Scale(
                        domain=["Hazai (1)", "Döntetlen (X)", "Vendég (2)"],
                        range=["#34d399", "#fbbf24", "#60a5fa"],
                    )),
                    tooltip=["Piac", "Odds", "snapshot_at:T"],
                ).properties(height=200).interactive()
                st.altair_chart(chart, use_container_width=True)

else:
    st.markdown(
        '<div class="empty-state">'
        '<div class="empty-icon">📊</div>'
        '<div class="empty-text">Nincs megjeleníthető meccs erre a napra.<br/>Kattints a <strong>🔄 Frissítés</strong> gombra!</div>'
        '</div>',
        unsafe_allow_html=True,
    )

import streamlit as st
import pandas as pd
import altair as alt
import time
from datetime import date, datetime

from core.database import init_db, get_fixtures_by_date, get_all_leagues, get_team, get_latest_odds
from core.api_football import fetch_fixtures_by_date, fetch_odds_for_fixture, get_rate_limit_info
from core.odds_tracker import detect_dropping_odds, get_odds_history_df
from core.config import FOOTBALL_DATA_KEY

init_db()

st.markdown("# 📊 Napi Meccsek")
st.caption("Aznapi meccsek, odds és dropping odds figyelő")

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------
col_date, col_btn, col_quota = st.columns([2, 1, 1])
with col_date:
    selected_date = st.date_input("📅 Dátum", value=date.today())
with col_btn:
    st.markdown("<br/>", unsafe_allow_html=True)
    refresh = st.button("🔄 Adatok frissítése", type="primary", use_container_width=True,
                        disabled=not FOOTBALL_DATA_KEY)
with col_quota:
    st.markdown("<br/>", unsafe_allow_html=True)
    quota_placeholder = st.empty()

    def update_quota_display():
        rl = get_rate_limit_info()
        if rl["remaining"] is not None:
            quota_placeholder.info(f"API kvóta: **{rl['remaining']}** / {rl['limit']}")
        elif not FOOTBALL_DATA_KEY:
            quota_placeholder.error("⚠️ Nincs API kulcs beállítva. Streamliten add meg a Secrets-ben, lokálisan pedig a .env fájlban!")

    update_quota_display()

date_str = selected_date.strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Fetch data
# ---------------------------------------------------------------------------
if refresh:
    with st.spinner("Meccsek letöltése..."):
        fixtures = fetch_fixtures_by_date(date_str)
    if fixtures:
        # Fetch odds for each fixture (first bookmaker only)
        # BIZTONSÁGI LIMIT (10 requests / perc az ingyenes fiókban) -> 8 meccset töltünk be 6.1s szünetekkel
        limit_fixtures = min(len(fixtures), 8)
        odds_progress = st.progress(0, text="Odds letöltése (Biztonsági limit miatt várakozás)...")
        for i, fix in enumerate(fixtures[:limit_fixtures]):
            if i > 0:
                time.sleep(6.1)  # Szünet a "10 kerés/perc" flood kitiltás elkerülése végett
            fetch_odds_for_fixture(fix["api_id"])
            odds_progress.progress((i + 1) / limit_fixtures, text=f"Odds letöltése: {i+1}/{limit_fixtures}")
        odds_progress.empty()
        
    st.success(f"✅ {len(fixtures)} meccs frissítve!")
    update_quota_display()
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
    # Display matches as cards
    # ---------------------------------------------------------------------------
    for fix in filtered:
        home_team = get_team(fix["home_team_api_id"]) or {}
        away_team = get_team(fix["away_team_api_id"]) or {}
        odds = get_latest_odds(fix["api_id"])
        drops = detect_dropping_odds(fix["api_id"])
        league_name = league_map.get(fix["league_api_id"], {}).get("name", "")

        # Match time
        try:
            match_time = datetime.fromisoformat(fix["date"].replace("Z", "+00:00")).strftime("%H:%M")
        except (ValueError, TypeError):
            match_time = "?"

        # Status badge
        status = fix.get("status", "NS")
        if status == "FT":
            status_badge = f'<span class="badge badge-live" style="background:#22c55e22;color:#22c55e;">✅ FT</span>'
        elif status in ("1H", "2H", "HT", "LIVE"):
            status_badge = f'<span class="badge badge-live">🔴 LIVE</span>'
        else:
            status_badge = f'<span class="badge" style="background:#334155;color:#94a3b8;">{match_time}</span>'

        # Drop badges
        drop_html = ""
        for d in drops:
            if d["direction"] == "drop":
                drop_html += f'<span class="badge badge-drop">🔻 {d["market"]} {d["pct_change"]:+.1%}</span> '
            else:
                drop_html += f'<span class="badge badge-rise">🔺 {d["market"]} {d["pct_change"]:+.1%}</span> '

        # Home/Away logos
        home_logo = home_team.get("logo", "")
        away_logo = away_team.get("logo", "")
        home_logo_html = f'<img class="team-logo" src="{home_logo}"/>' if home_logo else ""
        away_logo_html = f'<img class="team-logo" src="{away_logo}"/>' if away_logo else ""

        # Score or "vs"
        if fix["home_goals"] is not None and fix["away_goals"] is not None:
            score_html = f'<span class="score-big">{fix["home_goals"]} - {fix["away_goals"]}</span>'
        else:
            score_html = '<span style="color:#64748b; font-size:1.2rem;">vs</span>'

        # Odds display
        odds_html = ""
        if odds:
            odds_html = f"""
<div style="display:flex; gap:0.8rem; margin-top:0.6rem; justify-content:center;">
    <div style="text-align:center; padding:0.3rem 0.8rem; background:#0f172a; border-radius:8px; min-width:60px;">
        <div style="font-size:0.65rem; color:#64748b;">1</div>
        <div style="font-weight:600; color:#22c55e;">{odds['home_odd']:.2f}</div>
    </div>
    <div style="text-align:center; padding:0.3rem 0.8rem; background:#0f172a; border-radius:8px; min-width:60px;">
        <div style="font-size:0.65rem; color:#64748b;">X</div>
        <div style="font-weight:600; color:#f59e0b;">{odds['draw_odd']:.2f}</div>
    </div>
    <div style="text-align:center; padding:0.3rem 0.8rem; background:#0f172a; border-radius:8px; min-width:60px;">
        <div style="font-size:0.65rem; color:#64748b;">2</div>
        <div style="font-weight:600; color:#3b82f6;">{odds['away_odd']:.2f}</div>
    </div>
</div>"""

        st.markdown(f"""
<div class="match-card">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
        <span style="color:#64748b; font-size:0.8rem;">🏆 {league_name}</span>
        {status_badge}
    </div>
    <div style="display:flex; justify-content:center; align-items:center; gap:1rem; padding:0.5rem 0;">
        <div style="text-align:right; flex:1;">
            <span style="font-weight:600; font-size:1rem;">{home_team.get('name', '?')}</span>
            {home_logo_html}
        </div>
        <div style="text-align:center; min-width:80px;">
            {score_html}
        </div>
        <div style="text-align:left; flex:1;">
            {away_logo_html}
            <span style="font-weight:600; font-size:1rem;">{away_team.get('name', '?')}</span>
        </div>
    </div>
    {odds_html}
<div style="margin-top:0.5rem;">{drop_html}</div>
</div>
        """, unsafe_allow_html=True)

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
                        range=["#22c55e", "#f59e0b", "#3b82f6"],
                    )),
                    tooltip=["Piac", "Odds", "snapshot_at:T"],
                ).properties(height=200).interactive()
                st.altair_chart(chart, use_container_width=True)

else:
    st.info("Nincs megjeleníthető meccs erre a napra. Kattints a **🔄 Adatok frissítése** gombra!")

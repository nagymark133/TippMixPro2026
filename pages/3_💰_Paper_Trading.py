import streamlit as st
import pandas as pd
from datetime import date

from core.database import (
    init_db, get_fixtures_by_date, get_team, get_latest_odds,
    get_bankroll, reset_bankroll, insert_paper_bet,
    get_pending_bets, get_settled_bets, settle_bet, get_fixture_by_api_id,
)
from core.api_football import fetch_fixture_results
from core.config import DEFAULT_INITIAL_BALANCE

init_db()

st.markdown("# 💰 Paper Trading")
st.caption("Virtuális bankroll kezelés és tippek követése")

# ---------------------------------------------------------------------------
# Bankroll display
# ---------------------------------------------------------------------------
bankroll = get_bankroll()
if bankroll:
    bal = bankroll["balance"]
    init_bal = bankroll["initial_balance"]
    delta = bal - init_bal
    pct = (delta / init_bal * 100) if init_bal > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Egyenleg", f"{bal:,.0f} Ft", delta=f"{delta:+,.0f} Ft")
    with col2:
        st.metric("📊 ROI", f"{pct:+.1f}%")
    with col3:
        pending = get_pending_bets()
        st.metric("⏳ Nyitott tippek", len(pending))
    with col4:
        settled = get_settled_bets()
        wins = sum(1 for b in settled if b["result"] == "win")
        total_s = len(settled)
        wr = (wins / total_s * 100) if total_s > 0 else 0
        st.metric("🎯 Win Rate", f"{wr:.0f}%" if total_s > 0 else "N/A")

st.divider()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_new, tab_pending, tab_settled, tab_settings = st.tabs([
    "➕ Új Tipp", "⏳ Nyitott Tippek", "✅ Lezárt Tippek", "⚙️ Beállítások",
])

# ======= TAB: New Bet =======
with tab_new:
    st.markdown('<p class="section-header">Új virtuális fogadás</p>', unsafe_allow_html=True)

    selected_date = st.date_input("📅 Meccs dátuma", value=date.today(), key="pt_date")
    date_str = selected_date.strftime("%Y-%m-%d")
    fixtures = get_fixtures_by_date(date_str)

    if not fixtures:
        st.info("Nincs meccs erre a napra. Frissítsd az adatokat a **📊 Napi Meccsek** oldalon!")
    else:
        fixture_opts = {}
        for f in fixtures:
            ht = get_team(f["home_team_api_id"]) or {}
            at = get_team(f["away_team_api_id"]) or {}
            fixture_opts[f["api_id"]] = f"{ht.get('name', '?')} vs {at.get('name', '?')}"

        with st.form("new_bet_form"):
            fix_id = st.selectbox(
                "⚽ Meccs",
                options=list(fixture_opts.keys()),
                format_func=lambda x: fixture_opts.get(x, str(x)),
            )

            col_type, col_sel = st.columns(2)
            with col_type:
                bet_type = st.selectbox("📋 Fogadás típusa", ["1X2", "OU25"])
            with col_sel:
                if bet_type == "1X2":
                    selection = st.selectbox("🎯 Tipp", ["Home", "Draw", "Away"],
                                             format_func=lambda x: {"Home": "Hazai (1)", "Draw": "Döntetlen (X)", "Away": "Vendég (2)"}[x])
                else:
                    selection = st.selectbox("🎯 Tipp", ["Over", "Under"],
                                             format_func=lambda x: {"Over": "2.5 Felett", "Under": "2.5 Alatt"}[x])

            # Auto-fill odds
            current_odds = get_latest_odds(fix_id)
            default_odds = 2.0
            if current_odds:
                odds_map = {
                    "Home": current_odds.get("home_odd", 2.0),
                    "Draw": current_odds.get("draw_odd", 3.0),
                    "Away": current_odds.get("away_odd", 2.0),
                    "Over": current_odds.get("over25_odd", 1.8),
                    "Under": current_odds.get("under25_odd", 1.8),
                }
                default_odds = odds_map.get(selection, 2.0) or 2.0

            col_odds, col_stake = st.columns(2)
            with col_odds:
                odds = st.number_input("📈 Odds", min_value=1.01, value=float(default_odds), step=0.05)
            with col_stake:
                max_stake = bankroll["balance"] if bankroll else 10000
                stake = st.number_input("💵 Tét (Ft)", min_value=100, max_value=int(max_stake),
                                        value=min(1000, int(max_stake)), step=100)

            submitted = st.form_submit_button("✅ Tipp rögzítése", type="primary", use_container_width=True)

            if submitted:
                if stake > 0 and odds > 1:
                    insert_paper_bet(fix_id, bet_type, selection, odds, stake)
                    st.success(f"Tipp rögzítve! {fixture_opts[fix_id]} — {selection} @ {odds:.2f} | Tét: {stake:,.0f} Ft")
                    st.rerun()
                else:
                    st.error("Érvénytelen tét vagy odds!")

# ======= TAB: Pending Bets =======
with tab_pending:
    st.markdown('<p class="section-header">Nyitott (pending) tippek</p>', unsafe_allow_html=True)

    pending_bets = get_pending_bets()

    if not pending_bets:
        st.info("Nincs nyitott tipped. Adj hozzá egyet az **➕ Új Tipp** fülön!")
    else:
        # Settlement button
        if st.button("🔄 Eredmények ellenőrzése", type="primary"):
            fix_ids = list({b["fixture_api_id"] for b in pending_bets})
            with st.spinner("Eredmények lekérése..."):
                results = fetch_fixture_results(fix_ids)

            settled_count = 0
            for bet in pending_bets:
                fid = bet["fixture_api_id"]
                if fid in results and results[fid]["status"] == "FT":
                    hg = results[fid]["home_goals"] or 0
                    ag = results[fid]["away_goals"] or 0
                    total_goals = hg + ag

                    won = False
                    if bet["bet_type"] == "1X2":
                        if bet["selection"] == "Home" and hg > ag:
                            won = True
                        elif bet["selection"] == "Draw" and hg == ag:
                            won = True
                        elif bet["selection"] == "Away" and hg < ag:
                            won = True
                    elif bet["bet_type"] == "OU25":
                        if bet["selection"] == "Over" and total_goals > 2:
                            won = True
                        elif bet["selection"] == "Under" and total_goals < 3:
                            won = True

                    if won:
                        profit = bet["stake"] * bet["odds"]  # Return includes stake
                        settle_bet(bet["id"], "win", profit)
                    else:
                        settle_bet(bet["id"], "loss", 0)
                    settled_count += 1

            if settled_count > 0:
                st.success(f"✅ {settled_count} tipp lezárva!")
                st.rerun()
            else:
                st.info("Nincs lezárható meccs (még nem fejeződtek be).")

        # Display pending bets
        for bet in pending_bets:
            fix = get_fixture_by_api_id(bet["fixture_api_id"])
            ht = get_team(fix["home_team_api_id"]) if fix else {}
            at = get_team(fix["away_team_api_id"]) if fix else {}
            match_label = f"{ht.get('name', '?')} vs {at.get('name', '?')}" if fix else f"Fixture #{bet['fixture_api_id']}"

            sel_label = {
                "Home": "Hazai (1)", "Draw": "Döntetlen (X)", "Away": "Vendég (2)",
                "Over": "2.5 Felett", "Under": "2.5 Alatt",
            }.get(bet["selection"], bet["selection"])

            st.markdown(f"""
<div class="match-card">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <div style="font-weight:600;">{match_label}</div>
            <div style="color:#94a3b8; font-size:0.85rem;">
                {sel_label} @ {bet['odds']:.2f} | Tét: {bet['stake']:,.0f} Ft
            </div>
            <div style="color:#64748b; font-size:0.75rem;">{bet['created_at'][:16]}</div>
        </div>
        <div>
            <span class="badge badge-live">⏳ Pending</span>
        </div>
    </div>
</div>
            """, unsafe_allow_html=True)

# ======= TAB: Settled Bets =======
with tab_settled:
    st.markdown('<p class="section-header">Lezárt tippek</p>', unsafe_allow_html=True)

    settled_bets = get_settled_bets()

    if not settled_bets:
        st.info("Még nincs lezárt tipped.")
    else:
        total_profit = sum(b.get("profit", 0) or 0 for b in settled_bets)
        total_staked = sum(b["stake"] for b in settled_bets)
        wins = sum(1 for b in settled_bets if b["result"] == "win")
        losses = sum(1 for b in settled_bets if b["result"] == "loss")

        col1, col2, col3 = st.columns(3)
        with col1:
            net = total_profit - total_staked
            st.metric("📊 Nettó Profit", f"{net:+,.0f} Ft")
        with col2:
            st.metric("✅ Nyertes", wins)
        with col3:
            st.metric("❌ Vesztes", losses)

        for bet in settled_bets:
            fix = get_fixture_by_api_id(bet["fixture_api_id"])
            ht = get_team(fix["home_team_api_id"]) if fix else {}
            at = get_team(fix["away_team_api_id"]) if fix else {}
            match_label = f"{ht.get('name', '?')} vs {at.get('name', '?')}" if fix else f"#{bet['fixture_api_id']}"

            sel_label = {
                "Home": "Hazai (1)", "Draw": "Döntetlen (X)", "Away": "Vendég (2)",
                "Over": "2.5 Felett", "Under": "2.5 Alatt",
            }.get(bet["selection"], bet["selection"])

            is_win = bet["result"] == "win"
            profit = bet.get("profit", 0) or 0
            net_profit = profit - bet["stake"] if is_win else -bet["stake"]
            badge_cls = "badge-value" if is_win else "badge-drop"
            badge_text = f"✅ +{net_profit:,.0f} Ft" if is_win else f"❌ {net_profit:,.0f} Ft"

            st.markdown(f"""
<div class="match-card" style="border-color: {'#22c55e44' if is_win else '#ef444444'};">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <div style="font-weight:600;">{match_label}</div>
            <div style="color:#94a3b8; font-size:0.85rem;">
                {sel_label} @ {bet['odds']:.2f} | Tét: {bet['stake']:,.0f} Ft
            </div>
        </div>
        <div>
            <span class="badge {badge_cls}" style="font-size:0.9rem;">{badge_text}</span>
        </div>
    </div>
</div>
            """, unsafe_allow_html=True)

# ======= TAB: Settings =======
with tab_settings:
    st.markdown('<p class="section-header">Bankroll beállítások</p>', unsafe_allow_html=True)

    st.warning("⚠️ A bankroll resetelése törli az aktuális egyenleget és újraindítja a kezdőösszegről!")

    col1, col2 = st.columns(2)
    with col1:
        new_balance = st.number_input(
            "Kezdőösszeg (Ft)",
            min_value=1000,
            value=int(DEFAULT_INITIAL_BALANCE),
            step=10000,
        )
    with col2:
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("🔄 Bankroll reset", type="secondary"):
            reset_bankroll(new_balance)
            st.success(f"Bankroll visszaállítva: {new_balance:,.0f} Ft")
            st.rerun()

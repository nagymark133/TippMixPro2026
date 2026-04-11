import streamlit as st
import pandas as pd
from datetime import date, datetime
from html import escape
from zoneinfo import ZoneInfo

from core.database import (
    init_db, get_fixtures_by_date, get_team, get_latest_odds,
    get_all_leagues, insert_prediction, get_prediction,
    insert_paper_bet, get_bankroll,
)
from core.api_football import fetch_team_statistics, fetch_head_to_head
from core.ml_model import predict, should_retrain, train_models, get_model_info
from core.value_bet import detect_value_bets
from core.zhipu_ai import generate_analysis, generate_quick_tip
from core.betting_tips import generate_betting_tips
from core.ui import inject_global_styles

init_db()
inject_global_styles()

BUDAPEST_TZ = ZoneInfo("Europe/Budapest")


def _fixture_time_budapest(fixture_date_str: str) -> str:
    """Parse fixture UTC date string and return Budapest time as HH:MM."""
    try:
        dt = datetime.fromisoformat(fixture_date_str.replace("Z", "+00:00"))
        bp = dt.astimezone(BUDAPEST_TZ)
        return bp.strftime("%H:%M")
    except Exception:
        return ""


def _fixture_datetime_budapest(fixture_date_str: str) -> str:
    """Parse fixture UTC date and return Budapest datetime as YYYY-MM-DD HH:MM."""
    try:
        dt = datetime.fromisoformat(fixture_date_str.replace("Z", "+00:00"))
        bp = dt.astimezone(BUDAPEST_TZ)
        return bp.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


st.markdown("# 🎯 Meccs Elemzés")
st.caption("ML predikció · AI összefoglaló · Value Bet detektálás")

# ---------------------------------------------------------------------------
# Bet basket init
# ---------------------------------------------------------------------------
if "bet_basket" not in st.session_state:
    st.session_state["bet_basket"] = []

# ---------------------------------------------------------------------------
# Select match
# ---------------------------------------------------------------------------
selected_date = st.date_input("📅 Dátum", value=date.today(), key="analysis_date")
date_str = selected_date.strftime("%Y-%m-%d")
fixtures = get_fixtures_by_date(date_str)

if not fixtures:
    st.info("Nincs meccs erre a napra. Menj a **📊 Napi Meccsek** oldalra és frissíts!")
    st.stop()

# Build options — with Budapest time
fixture_options = {}
for f in fixtures:
    ht = get_team(f["home_team_api_id"]) or {}
    at = get_team(f["away_team_api_id"]) or {}
    bp_time = _fixture_time_budapest(f["date"])
    time_suffix = f" ({bp_time})" if bp_time else ""
    label = f"{ht.get('name', '?')} vs {at.get('name', '?')}{time_suffix}"
    fixture_options[f["api_id"]] = label

selected_fix_id = st.selectbox(
    "⚽ Válassz meccset",
    options=list(fixture_options.keys()),
    format_func=lambda x: fixture_options.get(x, str(x)),
)

fix = next((f for f in fixtures if f["api_id"] == selected_fix_id), None)
if not fix:
    st.stop()

home_team = get_team(fix["home_team_api_id"]) or {}
away_team = get_team(fix["away_team_api_id"]) or {}

# Show bankroll info
bankroll = get_bankroll()
if bankroll:
    st.caption(f"💰 Paper Trading egyenleg: **{bankroll['balance']:,.0f} Ft**")

st.divider()

# ---------------------------------------------------------------------------
# Analysis button
# ---------------------------------------------------------------------------
col_btn, col_info = st.columns([1, 2])
with col_btn:
    analyse = st.button("🚀 Elemzés indítása", type="primary", use_container_width=True)
with col_info:
    model_info = get_model_info()
    st.caption(f"Modell: `{model_info.get('version', 'nincs')}` | Minták: {model_info.get('n_samples', 0)}")

if analyse:
    # Auto-retrain if needed
    if should_retrain():
        with st.spinner("🔄 Modell újratanítása..."):
            new_ver = train_models()
            if new_ver:
                st.success(f"Modell frissítve: {new_ver}")

    # Guess season from fixture date
    try:
        from core.ml_model import _season_from_date
        season = _season_from_date(fix["date"])
    except Exception:
        season = date.today().year

    # Fetch team statistics
    with st.spinner("📊 Csapat statisztikák letöltése..."):
        home_stats = fetch_team_statistics(fix["home_team_api_id"], fix["league_api_id"], season)
        away_stats = fetch_team_statistics(fix["away_team_api_id"], fix["league_api_id"], season)

    # Fetch H2H
    with st.spinner("🔄 Egymás elleni meccsek..."):
        h2h = fetch_head_to_head(fix["home_team_api_id"], fix["away_team_api_id"])

    odds = get_latest_odds(fix["api_id"])

    # Run ML prediction
    with st.spinner("🤖 ML predikció futtatása..."):
        preds = predict(home_stats, away_stats, odds=odds)

    if preds:
        # Save prediction
        insert_prediction(
            fix["api_id"],
            preds["home_prob"], preds["draw_prob"], preds["away_prob"],
            preds["over25_prob"], preds["under25_prob"],
            preds["model_version"],
        )
        st.session_state[f"preds_{selected_fix_id}"] = preds
        st.session_state[f"h2h_{selected_fix_id}"] = h2h
        st.session_state[f"home_stats_{selected_fix_id}"] = home_stats
        st.session_state[f"away_stats_{selected_fix_id}"] = away_stats
        st.session_state[f"odds_{selected_fix_id}"] = odds
        st.session_state.pop(f"analysis_{selected_fix_id}", None)
        st.session_state.pop(f"quick_tip_{selected_fix_id}", None)

# ---------------------------------------------------------------------------
# Display results (from session state or DB)
# ---------------------------------------------------------------------------
preds = st.session_state.get(f"preds_{selected_fix_id}") or get_prediction(selected_fix_id)
h2h = st.session_state.get(f"h2h_{selected_fix_id}", [])
home_stats = st.session_state.get(f"home_stats_{selected_fix_id}")
away_stats = st.session_state.get(f"away_stats_{selected_fix_id}")
odds = st.session_state.get(f"odds_{selected_fix_id}") or get_latest_odds(selected_fix_id)

if preds:
    # --- Match Header with Budapest time ---
    home_crest = home_team.get('crest', '')
    away_crest = away_team.get('crest', '')
    home_logo_html = f'<img class="team-logo-lg" src="{escape(home_crest)}" alt="">' if home_crest else '<div class="team-logo-lg" style="display:flex;align-items:center;justify-content:center;font-size:1.5rem;">🏠</div>'
    away_logo_html = f'<img class="team-logo-lg" src="{escape(away_crest)}" alt="">' if away_crest else '<div class="team-logo-lg" style="display:flex;align-items:center;justify-content:center;font-size:1.5rem;">✈️</div>'

    bp_datetime = _fixture_datetime_budapest(fix["date"])
    time_html = f'<div style="color:#94a3b8;font-size:0.85rem;margin-top:0.3rem;">🕐 {escape(bp_datetime)} (Budapest)</div>' if bp_datetime else ''

    st.markdown(f'<div class="analysis-header">'
        f'<div class="ah-team">{home_logo_html}<div class="ah-team-name">{escape(home_team.get("name", "?"))}</div></div>'
        f'<div class="ah-vs">VS{time_html}</div>'
        f'<div class="ah-team">{away_logo_html}<div class="ah-team-name">{escape(away_team.get("name", "?"))}</div></div>'
        f'</div>', unsafe_allow_html=True)

    # =====================================================================
    # CONFIDENCE METER — 1X2
    # =====================================================================
    st.markdown('<p class="section-header">📊 Confidence Meter — 1X2</p>', unsafe_allow_html=True)

    home_pct = preds.get("home_prob", 0)
    draw_pct = preds.get("draw_prob", 0)
    away_pct = preds.get("away_prob", 0)

    best_1x2 = max(
        [("Hazai", home_pct), ("Döntetlen", draw_pct), ("Vendég", away_pct)],
        key=lambda x: x[1],
    )

    col1, col2, col3 = st.columns(3)
    for col, (label, emoji, pct, color) in zip(
        [col1, col2, col3],
        [
            ("HAZAI (1)", "🏠", home_pct, "#34d399"),
            ("DÖNTETLEN (X)", "🤝", draw_pct, "#fbbf24"),
            ("VENDÉG (2)", "✈️", away_pct, "#60a5fa"),
        ],
    ):
        with col:
            st.markdown(
                f'<div class="conf-meter">'
                f'<div class="conf-label" style="color:{color};">{emoji} {label}</div>'
                f'<div class="conf-value" style="color:{color};">{pct:.1%}</div>'
                f'<div class="conf-bar-track"><div class="conf-bar-fill" style="width:{pct*100:.0f}%;background:{color};"></div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.info(f"🏆 Legvalószínűbb: **{best_1x2[0]}** ({best_1x2[1]:.1%})")

    # =====================================================================
    # Over/Under 2.5
    # =====================================================================
    st.markdown('<p class="section-header">⚽ Gólok — 2.5 Felett/Alatt</p>', unsafe_allow_html=True)
    over_pct = preds.get("over25_prob", 0.5)
    under_pct = preds.get("under25_prob", 0.5)

    col_o, col_u = st.columns(2)
    for col, (label, emoji, pct, color) in zip(
        [col_o, col_u],
        [
            ("2.5 FELETT", "📈", over_pct, "#a78bfa"),
            ("2.5 ALATT", "📉", under_pct, "#fb923c"),
        ],
    ):
        with col:
            st.markdown(
                f'<div class="conf-meter">'
                f'<div class="conf-label" style="color:{color};">{emoji} {label}</div>'
                f'<div class="conf-value" style="color:{color};">{pct:.1%}</div>'
                f'<div class="conf-bar-track"><div class="conf-bar-fill" style="width:{pct*100:.0f}%;background:{color};"></div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # =====================================================================
    # AI QUICK TIP (Feature 5 — short AI message)
    # =====================================================================
    ai_stats = {
        "home_team": home_team.get("name", "?"),
        "away_team": away_team.get("name", "?"),
        "home_stats": home_stats,
        "away_stats": away_stats,
        "h2h": h2h,
        "predictions": preds,
        "odds": odds,
        "value_bets": [],
    }

    quick_tip_key = f"quick_tip_{selected_fix_id}"
    quick_tip_text = st.session_state.get(quick_tip_key)
    if not quick_tip_text:
        with st.spinner("🤖 AI gyors javaslat..."):
            quick_tip_text = generate_quick_tip(ai_stats)
        st.session_state[quick_tip_key] = quick_tip_text

    st.markdown(
        f'<div class="modern-card" style="border-left:4px solid #6366f1;padding:1rem 1.2rem;">'
        f'<div style="font-size:0.8rem;font-weight:700;color:#6366f1;margin-bottom:0.4rem;">🤖 AI Gyors Javaslat</div>'
        f'<div style="color:#f8fafc;font-size:0.95rem;line-height:1.6;">{escape(quick_tip_text)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # =====================================================================
    # BETTING TIPS — ALL MARKETS
    # =====================================================================
    st.markdown('<p class="section-header">🎰 Fogadási Tippek — Összes Piac</p>', unsafe_allow_html=True)

    tips = generate_betting_tips(
        preds, home_stats, away_stats, odds, h2h,
        home_name=home_team.get("name", "Hazai"),
        away_name=away_team.get("name", "Vendég"),
    )

    # =====================================================================
    # SORT CONTROLS (Feature 3)
    # =====================================================================
    sort_option = st.selectbox(
        "🔄 Rendezés",
        ["Esély szerint csökkenő ↓", "Esély szerint növekvő ↑", "ABC szerint (A→Z)", "ABC szerint (Z→A)"],
        key="tip_sort",
    )

    if sort_option == "Esély szerint csökkenő ↓":
        tips.sort(key=lambda t: t["prob"], reverse=True)
    elif sort_option == "Esély szerint növekvő ↑":
        tips.sort(key=lambda t: t["prob"])
    elif sort_option == "ABC szerint (A→Z)":
        tips.sort(key=lambda t: t["selection"].lower())
    elif sort_option == "ABC szerint (Z→A)":
        tips.sort(key=lambda t: t["selection"].lower(), reverse=True)

    # =====================================================================
    # AI Kiemelt Ajánlatok (87%+) - Swipeable Carousel
    # =====================================================================
    high_conf_tips = [t for t in tips if t["prob"] >= 0.87]
    if high_conf_tips:
        # Rendezve csökkenő valószínűség szerint
        high_conf_tips.sort(key=lambda x: x["prob"], reverse=True)
        
        st.markdown('<p class="section-header">🤖 AI Kiemelt Napi Ajánlatok (87%+)</p>', unsafe_allow_html=True)
        
        carousel_slides = []
        for rec in high_conf_tips:
            market = escape(str(rec.get("market", "Ismeretlen Piac")))
            selection = escape(str(rec.get("selection", "Tipp")))
            confidence_emoji = escape(str(rec.get("confidence_emoji", "🎯")))
            reasoning = escape(str(rec.get("reasoning", "Nincs extra indoklás.")))
            prob = rec.get("prob", 0)
            carousel_slides.append(
                (
                    f'<div class="tip-slide">'
                    f'<div class="ai-recommendation-card">'
                    f'<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1rem;">'
                    f'<div style="flex:1; min-width:0;">'
                    f'<div style="color:var(--accent); font-size:0.75rem; font-weight:800; text-transform:uppercase; letter-spacing:1px; margin-bottom:0.3rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">'
                    f'✨ {market}'
                    f'</div>'
                    f'<div style="color:var(--text-main); font-size:1.1rem; font-weight:800; line-height:1.2; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">'
                    f'{confidence_emoji} {selection}'
                    f'</div>'
                    f'</div>'
                    f'<div style="text-align:right; margin-left:1rem; flex-shrink:0;">'
                    f'<div style="color:var(--success); font-size:1.8rem; font-weight:800; line-height:1;">'
                    f'{prob:.1%}'
                    f'</div>'
                    f'</div>'
                    f'</div>'
                    f'<div style="background:rgba(0,0,0,0.35); border:1px solid rgba(255,255,255,0.08); padding:0.8rem; border-radius:12px; margin-top:auto;">'
                    f'<div style="color:var(--text-muted); font-size:0.75rem; font-weight:700; margin-bottom:0.4rem; text-transform:uppercase; letter-spacing:0.5px;">Érvelés:</div>'
                    f'<div style="color:rgba(248, 250, 252, 0.9); font-size:0.85rem; line-height:1.5;">'
                    f'{reasoning}'
                    f'</div>'
                    f'</div>'
                    f'</div>'
                    f'</div>'
                )
            )
        carousel_html = '<div class="tips-carousel-wrapper"><div class="tips-carousel">' + ''.join(carousel_slides) + '</div></div>'
        st.markdown(carousel_html, unsafe_allow_html=True)

    # Group tips by category
    categories = {
        "⚽ Eredmény": [],
        "🥅 Gólszám": [],
        "🔀 Kombinált": [],
        "⏱️ Félidő": [],
        "📐 Szögletek": [],
        "🟨 Lapok & Szabálytalanságok": [],
        "🎯 Lövések & Egyéb": [],
        "📊 Hendikep & Pontos": [],
    }

    for tip in tips:
        m = tip["market"].lower()
        if "hendikep" in m or "pontos" in m:
            categories["📊 Hendikep & Pontos"].append(tip)
        elif "félidő" in m and ("1x2" in m or "végeredmény" in m or "félidőben" in m or "nyer" in m or "nyeri" in m):
            categories["⏱️ Félidő"].append(tip)
        elif "félidő" in m:
            categories["🥅 Gólszám"].append(tip)
        elif "1x2" in m and "mindkét" not in m:
            categories["⚽ Eredmény"].append(tip)
        elif "kétesély" in m or "tét visszajár" in m or "0-ra" in m:
            categories["⚽ Eredmény"].append(tip)
        elif "mindkét csapat" in m and "gólszám" in m:
            categories["🔀 Kombinált"].append(tip)
        elif "mindkét csapat" in m or "btts" in m.lower() or "vagy" in m:
            categories["🔀 Kombinált"].append(tip)
        elif "1x2 +" in m:
            categories["🔀 Kombinált"].append(tip)
        elif "gólszám" in m or "gól" in m or "szerez" in m:
            categories["🥅 Gólszám"].append(tip)
        elif "szöglet" in m:
            categories["📐 Szögletek"].append(tip)
        elif "büntető" in m or "kiállít" in m or "szabály" in m or "lap" in m:
            categories["🟨 Lapok & Szabálytalanságok"].append(tip)
        else:
            categories["🎯 Lövések & Egyéb"].append(tip)

    # Helper: get match label for basket/paper bet
    match_label = f"{home_team.get('name', '?')} vs {away_team.get('name', '?')}"

    # Create tabs for categories
    non_empty = {k: v for k, v in categories.items() if v}
    if non_empty:
        tab_keys = list(non_empty.keys())
        tabs = st.tabs(tab_keys)

        for tab, cat_name in zip(tabs, tab_keys):
            with tab:
                for idx, tip in enumerate(non_empty[cat_name]):
                    prob_pct = f"{tip['prob']:.0%}"
                    emoji = tip["confidence_emoji"]
                    conf = tip["confidence_label"]

                    # Color based on confidence
                    if tip["prob"] >= 0.70:
                        bar_color = "#34d399"
                    elif tip["prob"] >= 0.55:
                        bar_color = "#60a5fa"
                    elif tip["prob"] >= 0.40:
                        bar_color = "#fbbf24"
                    else:
                        bar_color = "#f87171"

                    st.markdown(
                        f'<div class="tip-card">'
                        f'<div class="tip-header">'
                        f'<div><div class="tip-market">{escape(tip["market"])}</div>'
                        f'<div class="tip-selection">{escape(emoji)} {escape(tip["selection"])}</div></div>'
                        f'<div style="text-align:right;">'
                        f'<div class="tip-prob" style="color:{bar_color};">{prob_pct}</div>'
                        f'<div class="tip-conf">{escape(conf)}</div></div>'
                        f'</div>'
                        f'<div class="tip-bar-track"><div class="tip-bar-fill" style="width:{tip["prob"]*100:.0f}%;background:{bar_color};"></div></div>'
                        f'<div class="tip-reasoning">{escape(tip["reasoning"])}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    # --- Action buttons: Paper Trade ➕ and Basket 🛒 ---
                    tip_key = f"{cat_name}_{idx}_{tip['market']}"
                    col_pt, col_bk = st.columns(2)

                    with col_pt:
                        if st.button("➕ Paper Trade", key=f"pt_{tip_key}"):
                            st.session_state[f"show_pt_{tip_key}"] = True

                    with col_bk:
                        if st.button("🛒 Kosárba", key=f"bk_{tip_key}"):
                            basket_item = {
                                "match": match_label,
                                "fixture_api_id": selected_fix_id,
                                "market": tip["market"],
                                "selection": tip["selection"],
                                "prob": tip["prob"],
                                "odds": tip.get("odds"),
                                "confidence": tip["confidence_label"],
                            }
                            already = any(
                                b["fixture_api_id"] == basket_item["fixture_api_id"]
                                and b["market"] == basket_item["market"]
                                and b["selection"] == basket_item["selection"]
                                for b in st.session_state["bet_basket"]
                            )
                            if not already:
                                st.session_state["bet_basket"].append(basket_item)
                                st.success(f"🛒 Kosárba: {tip['selection']}")
                            else:
                                st.warning("Már a kosárban van!")

                    # Paper Trade quick-add form
                    if st.session_state.get(f"show_pt_{tip_key}"):
                        with st.expander(f"➕ Paper Bet: {tip['selection']}", expanded=True):
                            with st.form(key=f"ptform_{tip_key}"):
                                default_odds = tip.get("odds") or 2.0
                                pt_odds = st.number_input(
                                    "📈 Odds", min_value=1.01, value=float(default_odds),
                                    step=0.05, key=f"ptodds_{tip_key}",
                                )
                                current_bal = bankroll["balance"] if bankroll else 10000
                                pt_stake = st.number_input(
                                    "💵 Tét (Ft)", min_value=100, max_value=int(current_bal),
                                    value=min(1000, int(current_bal)), step=100,
                                    key=f"ptstake_{tip_key}",
                                )
                                # Map tip to bet_type + selection for paper_bets
                                market_lower = tip["market"].lower()
                                if "1x2" in market_lower:
                                    pt_bet_type = "1X2"
                                    sel = tip["selection"]
                                    if "hazai" in sel.lower() or "home" in sel.lower() or "(1)" in sel:
                                        pt_selection = "Home"
                                    elif "döntetlen" in sel.lower() or "draw" in sel.lower() or "(x)" in sel.lower():
                                        pt_selection = "Draw"
                                    else:
                                        pt_selection = "Away"
                                elif "gól" in market_lower and ("felett" in tip["selection"].lower() or "over" in tip["selection"].lower()):
                                    pt_bet_type = "OU25"
                                    pt_selection = "Over"
                                elif "gól" in market_lower and ("alatt" in tip["selection"].lower() or "under" in tip["selection"].lower()):
                                    pt_bet_type = "OU25"
                                    pt_selection = "Under"
                                else:
                                    pt_bet_type = "1X2"
                                    pt_selection = "Home"

                                submitted = st.form_submit_button("✅ Paper Bet rögzítése", type="primary")
                                if submitted:
                                    insert_paper_bet(selected_fix_id, pt_bet_type, pt_selection, pt_odds, pt_stake)
                                    st.success(f"✅ Paper bet rögzítve! {match_label} — {tip['selection']} @ {pt_odds:.2f} | Tét: {pt_stake:,.0f} Ft")
                                    st.session_state[f"show_pt_{tip_key}"] = False
                                    st.rerun()

    # =====================================================================
    # VALUE BET DETECTOR
    # =====================================================================
    if odds:
        st.markdown('<p class="section-header">💎 Value Bet Detektor</p>', unsafe_allow_html=True)
        value_bets = detect_value_bets(preds, odds)

        if value_bets:
            for vb in value_bets:
                st.markdown(
                    f'<div class="value-bet-card">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<div>'
                    f'<div style="font-size:1.05rem;font-weight:800;color:var(--success);margin-bottom:0.3rem;">'
                    f'⚡ VALUE BET: {escape(vb["selection"])}</div>'
                    f'<div style="color:var(--text-muted);font-size:0.8rem;">'
                    f'Modell: {vb["ml_prob"]:.1%} vs Implied: {vb["implied_prob"]:.1%} · Edge: +{vb["edge"]:.1%}</div>'
                    f'</div>'
                    f'<div style="text-align:right;">'
                    f'<div style="font-size:1.5rem;font-weight:900;color:var(--success);font-variant-numeric:tabular-nums;">{vb["odds"]:.2f}</div>'
                    f'<div style="font-size:0.7rem;color:var(--text-muted);">EV: {vb["expected_value"]:+.3f}</div>'
                    f'</div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="modern-card" style="text-align:center;">'
                '<span style="color:var(--text-muted);">Nincs value bet ennél a meccsnél. A modell és az odds közel vannak egymáshoz.</span>'
                '</div>',
                unsafe_allow_html=True,
            )
    else:
        st.warning("Nincs odds adat. Frissítsd az adatokat a **📊 Napi Meccsek** oldalon!")
        value_bets = []

    # =====================================================================
    # H2H & Form Guide
    # =====================================================================
    col_h2h, col_form = st.columns(2)

    with col_h2h:
        st.markdown('<p class="section-header">🔄 Egymás elleni (H2H)</p>', unsafe_allow_html=True)
        if h2h:
            h2h_data = []
            for m in h2h[:5]:
                h2h_data.append({
                    "Dátum": str(m.get("date", "?"))[:10],
                    "Hazai": m.get("home_team", "?"),
                    "Gól": f"{m.get('home_goals', '?')} - {m.get('away_goals', '?')}",
                    "Vendég": m.get("away_team", "?"),
                })
            st.dataframe(pd.DataFrame(h2h_data), use_container_width=True, hide_index=True)
        else:
            st.caption("Nincs H2H adat. Kattints az Elemzés gombra!")

    with col_form:
        st.markdown('<p class="section-header">📈 Forma</p>', unsafe_allow_html=True)
        form_data = []
        if home_stats:
            form_data.append({
                "Csapat": home_team.get("name", "?"),
                "Forma": home_stats.get("form", "N/A")[-5:] if home_stats.get("form") else "N/A",
                "Gy": home_stats.get("wins", 0),
                "D": home_stats.get("draws", 0),
                "V": home_stats.get("losses", 0),
                "Gól +/-": f"{home_stats.get('goals_for', 0)}/{home_stats.get('goals_against', 0)}",
            })
        if away_stats:
            form_data.append({
                "Csapat": away_team.get("name", "?"),
                "Forma": away_stats.get("form", "N/A")[-5:] if away_stats.get("form") else "N/A",
                "Gy": away_stats.get("wins", 0),
                "D": away_stats.get("draws", 0),
                "V": away_stats.get("losses", 0),
                "Gól +/-": f"{away_stats.get('goals_for', 0)}/{away_stats.get('goals_against', 0)}",
            })
        if form_data:
            st.dataframe(pd.DataFrame(form_data), use_container_width=True, hide_index=True)
        else:
            st.caption("Nincs form adat.")

    # =====================================================================
    # AI SUMMARY (detailed)
    # =====================================================================
    st.markdown('<p class="section-header">🧠 AI Elemzés (Zhipu GLM)</p>', unsafe_allow_html=True)

    ai_stats["value_bets"] = value_bets if odds else []

    analysis_key = f"analysis_{selected_fix_id}"
    analysis_text = st.session_state.get(analysis_key)
    if not analysis_text:
        with st.spinner("🤖 AI részletes elemzés generálása..."):
            analysis_text = generate_analysis(ai_stats)
        st.session_state[analysis_key] = analysis_text

    st.markdown(
        f'<div class="ai-summary-card">'
        f'<div class="ai-badge">🤖 AI Részletes Összefoglaló</div>'
        f'<div class="ai-text">{analysis_text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # =====================================================================
    # BET BASKET / FOGADÁSKÉSZÍTŐ (Feature 2)
    # =====================================================================
    basket = st.session_state.get("bet_basket", [])
    if basket:
        st.markdown('<p class="section-header">🛒 Fogadáskészítő Kosár</p>', unsafe_allow_html=True)

        total_odds = 1.0
        basket_lines = []
        for bi, item in enumerate(basket):
            item_odds = item.get("odds") or 2.0
            total_odds *= item_odds
            basket_lines.append(
                f"• {item['match']} — {item['market']}: {item['selection']} "
                f"({item['prob']:.0%}) @ {item_odds:.2f}"
            )

            col_info_b, col_del = st.columns([5, 1])
            with col_info_b:
                st.markdown(
                    f'<div class="modern-card" style="padding:0.6rem 1rem;margin-bottom:0.3rem;">'
                    f'<div style="font-size:0.85rem;font-weight:600;color:#f8fafc;">{escape(item["match"])}</div>'
                    f'<div style="font-size:0.8rem;color:#94a3b8;">'
                    f'{escape(item["market"])}: <b>{escape(item["selection"])}</b> ({item["prob"]:.0%}) @ {item_odds:.2f}'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            with col_del:
                if st.button("🗑️", key=f"del_basket_{bi}"):
                    st.session_state["bet_basket"].pop(bi)
                    st.rerun()

        st.markdown(
            f'<div class="modern-card" style="border:1px solid #6366f1;padding:1rem;">'
            f'<div style="font-size:1rem;font-weight:700;color:#6366f1;">📊 Összesített szorzó: {total_odds:.2f}</div>'
            f'<div style="font-size:0.8rem;color:#94a3b8;margin-top:0.3rem;">{len(basket)} meccs a kosárban</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Copy to clipboard text
        clipboard_text = "🎯 TippMixPro Fogadáskészítő\n"
        clipboard_text += "=" * 30 + "\n"
        for line in basket_lines:
            clipboard_text += line + "\n"
        clipboard_text += f"\nÖsszesített szorzó: {total_odds:.2f}"
        clipboard_text += f"\nTételek száma: {len(basket)}"

        col_copy, col_clear = st.columns(2)
        with col_copy:
            st.code(clipboard_text, language=None, line_numbers=False, container_width=True)
            st.markdown(
                """
                <style>
                .element-container pre {
                    font-size: 1.08rem !important;
                    font-family: 'Fira Mono', 'Consolas', 'Menlo', monospace !important;
                    white-space: pre-wrap !important;
                    word-break: break-word !important;
                    overflow-x: auto !important;
                    min-width: 340px;
                    max-width: 100vw;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.caption("⬆️ Másold ki a fenti szöveget a TippMixPro oldalon való megjátszáshoz!")
        with col_clear:
            if st.button("🗑️ Kosár ürítése", type="secondary"):
                st.session_state["bet_basket"] = []
                st.rerun()

else:
    st.markdown(
        '<div class="empty-state">'
        '<div class="empty-icon">🎯</div>'
        '<div class="empty-text">Válassz egy meccset és kattints az <strong>Elemzés indítása</strong> gombra!</div>'
        '</div>',
        unsafe_allow_html=True,
    )

import streamlit as st
import pandas as pd
from datetime import date
from html import escape

from core.database import (
    init_db, get_fixtures_by_date, get_team, get_latest_odds,
    get_all_leagues, insert_prediction, get_prediction,
)
from core.api_football import fetch_team_statistics, fetch_head_to_head
from core.ml_model import predict, should_retrain, train_models, get_model_info
from core.value_bet import detect_value_bets
from core.zhipu_ai import generate_analysis
from core.betting_tips import generate_betting_tips

init_db()

st.markdown("# 🎯 Meccs Elemzés")
st.caption("ML predikció • AI összefoglaló • Value Bet detektálás")

# ---------------------------------------------------------------------------
# Select match
# ---------------------------------------------------------------------------
selected_date = st.date_input("📅 Dátum", value=date.today(), key="analysis_date")
date_str = selected_date.strftime("%Y-%m-%d")
fixtures = get_fixtures_by_date(date_str)

if not fixtures:
    st.info("Nincs meccs erre a napra. Menj a **📊 Napi Meccsek** oldalra és frissíts!")
    st.stop()

# Build options
fixture_options = {}
for f in fixtures:
    ht = get_team(f["home_team_api_id"]) or {}
    at = get_team(f["away_team_api_id"]) or {}
    label = f"{ht.get('name', '?')} vs {at.get('name', '?')}"
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

# ---------------------------------------------------------------------------
# Display results (from session state or DB)
# ---------------------------------------------------------------------------
preds = st.session_state.get(f"preds_{selected_fix_id}") or get_prediction(selected_fix_id)
h2h = st.session_state.get(f"h2h_{selected_fix_id}", [])
home_stats = st.session_state.get(f"home_stats_{selected_fix_id}")
away_stats = st.session_state.get(f"away_stats_{selected_fix_id}")
odds = st.session_state.get(f"odds_{selected_fix_id}") or get_latest_odds(selected_fix_id)

if preds:
    st.divider()

    # --- Match Header ---
    st.markdown(f"""
<div style="text-align:center; padding:1rem 0;">
    <span style="font-size:1.4rem; font-weight:600;">{home_team.get('name', '?')}</span>
    <span style="color:#64748b; font-size:1.2rem; margin: 0 1rem;">vs</span>
    <span style="font-size:1.4rem; font-weight:600;">{away_team.get('name', '?')}</span>
</div>
    """, unsafe_allow_html=True)

    # =====================================================================
    # CONFIDENCE METER — 1X2
    # =====================================================================
    st.markdown('<p class="section-header">📊 Confidence Meter — 1X2</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    home_pct = preds.get("home_prob", 0)
    draw_pct = preds.get("draw_prob", 0)
    away_pct = preds.get("away_prob", 0)

    best_1x2 = max(
        [("Hazai", home_pct), ("Döntetlen", draw_pct), ("Vendég", away_pct)],
        key=lambda x: x[1],
    )

    with col1:
        st.markdown(f"""
<div style="text-align:center;">
    <div style="font-size:0.85rem; color:#22c55e; font-weight:600;">🏠 HAZAI (1)</div>
    <div style="font-size:2rem; font-weight:700; color:#22c55e;">{home_pct:.1%}</div>
</div>
        """, unsafe_allow_html=True)
        st.progress(home_pct)

    with col2:
        st.markdown(f"""
<div style="text-align:center;">
    <div style="font-size:0.85rem; color:#f59e0b; font-weight:600;">🤝 DÖNTETLEN (X)</div>
    <div style="font-size:2rem; font-weight:700; color:#f59e0b;">{draw_pct:.1%}</div>
</div>
        """, unsafe_allow_html=True)
        st.progress(draw_pct)

    with col3:
        st.markdown(f"""
<div style="text-align:center;">
    <div style="font-size:0.85rem; color:#3b82f6; font-weight:600;">✈️ VENDÉG (2)</div>
    <div style="font-size:2rem; font-weight:700; color:#3b82f6;">{away_pct:.1%}</div>
</div>
        """, unsafe_allow_html=True)
        st.progress(away_pct)

    st.info(f"🏆 Legvalószínűbb: **{best_1x2[0]}** ({best_1x2[1]:.1%})")

    # =====================================================================
    # Over/Under 2.5
    # =====================================================================
    st.markdown('<p class="section-header">⚽ Gólok — 2.5 Felett/Alatt</p>', unsafe_allow_html=True)
    col_o, col_u = st.columns(2)
    over_pct = preds.get("over25_prob", 0.5)
    under_pct = preds.get("under25_prob", 0.5)

    with col_o:
        st.markdown(f"""
<div style="text-align:center;">
    <div style="font-size:0.85rem; color:#a78bfa; font-weight:600;">📈 2.5 FELETT</div>
    <div style="font-size:1.8rem; font-weight:700; color:#a78bfa;">{over_pct:.1%}</div>
</div>
        """, unsafe_allow_html=True)
        st.progress(over_pct)

    with col_u:
        st.markdown(f"""
<div style="text-align:center;">
    <div style="font-size:0.85rem; color:#fb923c; font-weight:600;">📉 2.5 ALATT</div>
    <div style="font-size:1.8rem; font-weight:700; color:#fb923c;">{under_pct:.1%}</div>
</div>
        """, unsafe_allow_html=True)
        st.progress(under_pct)

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

    # Create tabs for categories
    non_empty = {k: v for k, v in categories.items() if v}
    if non_empty:
        tab_keys = list(non_empty.keys())
        tabs = st.tabs(tab_keys)

        for tab, cat_name in zip(tabs, tab_keys):
            with tab:
                for tip in non_empty[cat_name]:
                    prob_pct = f"{tip['prob']:.0%}"
                    emoji = tip["confidence_emoji"]
                    conf = tip["confidence_label"]

                    # Color based on confidence
                    if tip["prob"] >= 0.70:
                        bar_color = "#22c55e"
                    elif tip["prob"] >= 0.55:
                        bar_color = "#3b82f6"
                    elif tip["prob"] >= 0.40:
                        bar_color = "#f59e0b"
                    else:
                        bar_color = "#ef4444"

                    st.markdown(f"""
<div style="background:#1e293b; border:1px solid #334155; border-radius:10px; padding:0.8rem 1rem; margin-bottom:0.5rem;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
        <div style="flex:1;">
            <div style="font-size:0.75rem; color:#64748b; margin-bottom:0.2rem;">{tip['market']}</div>
            <div style="font-weight:600; color:#f8fafc; font-size:1rem;">{emoji} {tip['selection']}</div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:1.4rem; font-weight:700; color:{bar_color};">{prob_pct}</div>
            <div style="font-size:0.7rem; color:#94a3b8;">{conf}</div>
        </div>
    </div>
    <div style="background:#0f172a; border-radius:6px; height:6px; overflow:hidden;">
        <div style="background:{bar_color}; height:100%; width:{tip['prob']*100:.0f}%; border-radius:6px;"></div>
    </div>
    <div style="font-size:0.75rem; color:#94a3b8; margin-top:0.3rem;">{tip['reasoning']}</div>
</div>
                    """, unsafe_allow_html=True)

    # =====================================================================
    # VALUE BET DETECTOR
    # =====================================================================
    if odds:
        st.markdown('<p class="section-header">💎 Value Bet Detektor</p>', unsafe_allow_html=True)
        value_bets = detect_value_bets(preds, odds)

        if value_bets:
            for vb in value_bets:
                st.markdown(f"""
<div style="background:linear-gradient(135deg, #22c55e15, #22c55e08);
            border:1px solid #22c55e55; border-radius:10px; padding:1rem; margin-bottom:0.6rem;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <span style="font-size:1.1rem; font-weight:600; color:#22c55e;">
                ⚡ VALUE BET: {vb['selection']}
            </span><br/>
            <span style="color:#94a3b8; font-size:0.85rem;">
                Modell: {vb['ml_prob']:.1%} vs Odds implied: {vb['implied_prob']:.1%}
                &nbsp;|&nbsp; Edge: +{vb['edge']:.1%}
            </span>
        </div>
        <div style="text-align:right;">
            <div style="font-size:1.5rem; font-weight:700; color:#22c55e;">{vb['odds']:.2f}</div>
            <div style="font-size:0.75rem; color:#94a3b8;">EV: {vb['expected_value']:+.3f}</div>
        </div>
    </div>
</div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
<div style="background:#1e293b; border:1px solid #334155; border-radius:10px; padding:1rem; text-align:center;">
    <span style="color:#64748b;">Nincs value bet ennél a meccsnél. A modell és az odds közel vannak egymáshoz.</span>
</div>
            """, unsafe_allow_html=True)
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
    # AI SUMMARY
    # =====================================================================
    st.markdown('<p class="section-header">🧠 AI Elemzés (Zhipu GLM)</p>', unsafe_allow_html=True)

    ai_stats = {
        "home_team": home_team.get("name", "?"),
        "away_team": away_team.get("name", "?"),
        "home_stats": home_stats,
        "away_stats": away_stats,
        "h2h": h2h,
        "predictions": preds,
        "odds": odds,
        "value_bets": value_bets if odds else [],
    }

    with st.spinner("🤖 AI elemzés generálása..."):
        analysis_text = generate_analysis(ai_stats)

    st.markdown(f"""
<div style="background:linear-gradient(135deg, #1e293b, #0f172a);
            border:1px solid #334155; border-radius:12px; padding:1.2rem;">
    <div style="font-size:0.8rem; color:#64748b; margin-bottom:0.5rem;">🤖 AI Összefoglaló</div>
    <div style="color:#e2e8f0; line-height:1.6;">{analysis_text}</div>
</div>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
<div style="text-align:center; padding:3rem 0; color:#64748b;">
    <div style="font-size:3rem;">🎯</div>
    <p>Válassz egy meccset és kattints az <strong>Elemzés indítása</strong> gombra!</p>
</div>
    """, unsafe_allow_html=True)

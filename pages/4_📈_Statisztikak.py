import streamlit as st
import pandas as pd
import altair as alt
import numpy as np

from core.database import (
    init_db, get_all_predictions_with_results,
    get_settled_bets, get_bankroll,
)
from core.ml_model import get_model_info
from core.ui import inject_global_styles

init_db()
inject_global_styles()

st.markdown("# 📈 Statisztikák")
st.caption("Modell teljesítmény • Equity curve • Historikus adatok")

# ---------------------------------------------------------------------------
# Model Performance
# ---------------------------------------------------------------------------
st.markdown('<p class="section-header">🤖 ML Modell Teljesítmény</p>', unsafe_allow_html=True)

model_info = get_model_info()
predictions = get_all_predictions_with_results()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Modell verzió", model_info.get("version", "Nincs"))
with col2:
    st.metric("Tanító minták", model_info.get("n_samples", 0))
with col3:
    st.metric("Kiértékelt predikciók", len(predictions))

if predictions:
    # Calculate accuracy
    correct_1x2 = 0
    correct_ou25 = 0
    total = len(predictions)

    actual_labels = []
    predicted_labels = []

    for p in predictions:
        hg = p.get("home_goals", 0) or 0
        ag = p.get("away_goals", 0) or 0

        # Actual 1X2
        if hg > ag:
            actual = "Hazai"
        elif hg == ag:
            actual = "Döntetlen"
        else:
            actual = "Vendég"

        # Predicted 1X2 (highest prob)
        probs = {"Hazai": p.get("home_prob", 0), "Döntetlen": p.get("draw_prob", 0), "Vendég": p.get("away_prob", 0)}
        predicted = max(probs, key=probs.get)

        actual_labels.append(actual)
        predicted_labels.append(predicted)

        if actual == predicted:
            correct_1x2 += 1

        # OU25
        actual_ou = "Felett" if (hg + ag) > 2 else "Alatt"
        pred_ou = "Felett" if p.get("over25_prob", 0.5) > 0.5 else "Alatt"
        if actual_ou == pred_ou:
            correct_ou25 += 1

    acc_1x2 = correct_1x2 / total if total > 0 else 0
    acc_ou25 = correct_ou25 / total if total > 0 else 0

    col1, col2 = st.columns(2)
    with col1:
        st.metric("1X2 Pontosság", f"{acc_1x2:.1%}")
        st.progress(acc_1x2)
    with col2:
        st.metric("O/U 2.5 Pontosság", f"{acc_ou25:.1%}")
        st.progress(acc_ou25)

    # Confusion matrix as heatmap
    if len(set(actual_labels)) > 1:
        st.markdown("#### Tévesztési mátrix (1X2)")
        categories = ["Hazai", "Döntetlen", "Vendég"]
        matrix = np.zeros((3, 3), dtype=int)
        cat_idx = {c: i for i, c in enumerate(categories)}

        for actual, predicted in zip(actual_labels, predicted_labels):
            if actual in cat_idx and predicted in cat_idx:
                matrix[cat_idx[actual]][cat_idx[predicted]] += 1

        # Build dataframe for heatmap
        rows = []
        for i, actual_cat in enumerate(categories):
            for j, pred_cat in enumerate(categories):
                rows.append({
                    "Valós": actual_cat,
                    "Predikált": pred_cat,
                    "Darab": int(matrix[i][j]),
                })

        df_cm = pd.DataFrame(rows)
        heatmap = alt.Chart(df_cm).mark_rect().encode(
            x=alt.X("Predikált:N", title="Predikált", sort=categories),
            y=alt.Y("Valós:N", title="Valós", sort=categories),
            color=alt.Color("Darab:Q", scale=alt.Scale(scheme="blues")),
            tooltip=["Valós", "Predikált", "Darab"],
        ).properties(width=350, height=250)

        text = alt.Chart(df_cm).mark_text(fontSize=16, fontWeight="bold").encode(
            x=alt.X("Predikált:N", sort=categories),
            y=alt.Y("Valós:N", sort=categories),
            text="Darab:Q",
            color=alt.condition(
                alt.datum.Darab > (max(r["Darab"] for r in rows) / 2),
                alt.value("white"),
                alt.value("black"),
            ),
        )

        st.altair_chart(heatmap + text, use_container_width=False)

else:
    st.info("Még nincs kiértékelhető predikció. Futtass elemzéseket a **🎯 Elemzés** oldalon!")

st.divider()

# ---------------------------------------------------------------------------
# Paper Trading Equity Curve
# ---------------------------------------------------------------------------
st.markdown('<p class="section-header">💰 Paper Trading Equity Curve</p>', unsafe_allow_html=True)

settled_bets = get_settled_bets()
bankroll_data = get_bankroll()

if settled_bets and bankroll_data:
    initial = bankroll_data["initial_balance"]

    # Build equity curve from chronological settled bets
    sorted_bets = sorted(settled_bets, key=lambda b: b.get("settled_at", ""))
    running_balance = initial
    equity_points = [{"Dátum": sorted_bets[0].get("settled_at", "")[:10], "Egyenleg": initial, "Tipp #": 0}]

    for i, bet in enumerate(sorted_bets):
        profit = bet.get("profit", 0) or 0
        net = profit - bet["stake"] if bet["result"] == "win" else -bet["stake"]
        running_balance += net
        equity_points.append({
            "Dátum": bet.get("settled_at", "")[:10],
            "Egyenleg": running_balance,
            "Tipp #": i + 1,
        })

    df_eq = pd.DataFrame(equity_points)

    # Color based on above/below initial
    line_chart = alt.Chart(df_eq).mark_area(
        line={"color": "#FF6B35"},
        opacity=0.3,
    ).encode(
        x=alt.X("Tipp #:Q", title="Tipp sorszám"),
        y=alt.Y("Egyenleg:Q", title="Egyenleg (Ft)",
                scale=alt.Scale(zero=False)),
        color=alt.value("#FF6B35"),
        tooltip=["Tipp #", "Egyenleg", "Dátum"],
    ).properties(height=300)

    # Reference line for initial balance
    rule = alt.Chart(pd.DataFrame({"y": [initial]})).mark_rule(
        color="#64748b", strokeDash=[4, 4],
    ).encode(y="y:Q")

    st.altair_chart(line_chart + rule, use_container_width=True)

    # Summary stats
    col1, col2, col3, col4 = st.columns(4)
    total_bets = len(settled_bets)
    total_staked = sum(b["stake"] for b in settled_bets)
    total_returned = sum(b.get("profit", 0) or 0 for b in settled_bets)
    net_profit = total_returned - total_staked
    roi = (net_profit / total_staked * 100) if total_staked > 0 else 0

    with col1:
        st.metric("Összes tipp", total_bets)
    with col2:
        st.metric("Összes tét", f"{total_staked:,.0f} Ft")
    with col3:
        st.metric("Nettó profit", f"{net_profit:+,.0f} Ft")
    with col4:
        st.metric("ROI", f"{roi:+.1f}%")

else:
    st.info("Lezárt tippek szükségesek az equity curve megjelenítéséhez.")

st.divider()

# ---------------------------------------------------------------------------
# Bet History Table
# ---------------------------------------------------------------------------
st.markdown('<p class="section-header">📋 Összes lezárt tipp</p>', unsafe_allow_html=True)

if settled_bets:
    table_data = []
    for bet in settled_bets[:50]:
        net = (bet.get("profit", 0) or 0) - bet["stake"] if bet["result"] == "win" else -bet["stake"]
        sel_label = {
            "Home": "Hazai (1)", "Draw": "Döntetlen (X)", "Away": "Vendég (2)",
            "Over": "2.5 Felett", "Under": "2.5 Alatt",
        }.get(bet["selection"], bet["selection"])

        table_data.append({
            "Dátum": bet.get("settled_at", "?")[:10],
            "Típus": bet["bet_type"],
            "Tipp": sel_label,
            "Odds": f"{bet['odds']:.2f}",
            "Tét": f"{bet['stake']:,.0f}",
            "Eredmény": "✅ Nyert" if bet["result"] == "win" else "❌ Vesztett",
            "Profit": f"{net:+,.0f} Ft",
        })

    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)
else:
    st.info("Még nincs lezárt tipped.")

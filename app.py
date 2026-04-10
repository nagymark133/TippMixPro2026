import streamlit as st

st.set_page_config(
    page_title="TippMix Pro 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.database import init_db
from core.api_football import get_rate_limit_info
from core.config import API_FOOTBALL_KEY, ZHIPU_API_KEY

# ---------------------------------------------------------------------------
# Initialise DB on first run
# ---------------------------------------------------------------------------
init_db()

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ---- Global ---- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1923 0%, #1a1d2e 100%);
}

/* ---- Cards ---- */
.match-card {
    background: linear-gradient(135deg, #1a1d2e 0%, #252836 100%);
    border: 1px solid #2d3348;
    border-radius: 14px;
    padding: 1.2rem;
    margin-bottom: 1rem;
    transition: transform 0.15s, box-shadow 0.15s;
}
.match-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(0,0,0,0.35);
}

/* ---- Badges ---- */
.badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-right: 0.3rem;
}
.badge-value { background: #22c55e22; color: #22c55e; border: 1px solid #22c55e55; }
.badge-drop  { background: #ef444422; color: #ef4444; border: 1px solid #ef444455; }
.badge-rise  { background: #3b82f622; color: #3b82f6; border: 1px solid #3b82f655; }
.badge-live  { background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b55; }

/* ---- Metric overrides ---- */
[data-testid="stMetricValue"] { font-size: 1.8rem !important; }

/* ---- Progress bars ---- */
.stProgress > div > div > div { border-radius: 8px; }

/* ---- Team logo ---- */
.team-logo { width: 36px; height: 36px; vertical-align: middle; margin: 0 6px; }

/* ---- Score display ---- */
.score-big { font-size: 2rem; font-weight: 700; color: #FF6B35; }

/* ---- Section header ---- */
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 1.5rem 0 0.5rem 0;
    border-bottom: 2px solid #2d3348;
    padding-bottom: 0.3rem;
}

/* ---- Footer ---- */
.footer {
    text-align: center;
    color: #475569;
    font-size: 0.75rem;
    padding: 2rem 0 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image("https://em-content.zobj.net/source/twitter/408/soccer-ball_26bd.png", width=60)
    st.markdown("# TippMix Pro 2026")
    st.caption("Sportfogadási elemző dashboard")
    st.divider()

    # API status
    st.markdown('<p class="section-header">🔌 API Státusz</p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if API_FOOTBALL_KEY:
            rl = get_rate_limit_info()
            if rl["remaining"] is not None:
                st.metric("API Kvóta", f"{rl['remaining']}/{rl['limit']}")
            else:
                st.success("Kulcs OK", icon="✅")
        else:
            st.error("Hiányzik!", icon="⚠️")
    with col2:
        if ZHIPU_API_KEY:
            st.success("GLM OK", icon="✅")
        else:
            st.warning("Nincs kulcs", icon="⚠️")

    st.divider()
    st.markdown(
        '<p class="footer">TippMix Pro 2026 &copy; | Csak szórakozásra!</p>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Main page content
# ---------------------------------------------------------------------------
st.markdown("""
<div style="text-align:center; padding: 2rem 0 1rem 0;">
    <h1 style="font-size:2.5rem; background: linear-gradient(90deg, #FF6B35, #f7931a);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent;
               font-weight:700;">
        ⚽ TippMix Pro 2026
    </h1>
    <p style="color:#94a3b8; font-size:1.1rem; max-width:600px; margin:auto;">
        Sportfogadási adatelemző &amp; prediktív dashboard<br/>
        <em>ML alapú valószínűség-számítás • Value Bet detektálás • Virtuális bankroll</em>
    </p>
</div>
""", unsafe_allow_html=True)

st.divider()

# Quick stats row
col1, col2, col3, col4 = st.columns(4)
with col1:
    from core.database import get_db
    with get_db() as conn:
        cnt = conn.execute("SELECT COUNT(*) as c FROM fixtures").fetchone()["c"]
    st.metric("📋 Meccsek az adatbázisban", cnt)
with col2:
    with get_db() as conn:
        cnt = conn.execute("SELECT COUNT(*) as c FROM fixtures WHERE status='FT'").fetchone()["c"]
    st.metric("✅ Lezárt meccsek", cnt)
with col3:
    from core.ml_model import get_model_info
    info = get_model_info()
    st.metric("🤖 Modell verzió", info.get("version", "Nincs"))
with col4:
    from core.database import get_bankroll
    br = get_bankroll()
    if br:
        delta = br["balance"] - br["initial_balance"]
        st.metric("💰 Bankroll", f"{br['balance']:,.0f} Ft", delta=f"{delta:+,.0f} Ft")
    else:
        st.metric("💰 Bankroll", "N/A")

st.divider()

st.markdown("""
### 🚀 Navigáció

Használd a bal oldali menüt, vagy válassz az alábbi gyorslinkek közül:

| Oldal | Leírás |
|-------|--------|
| 📊 **Napi Meccsek** | Aznapi meccsek, odds, dropping odds figyelő |
| 🎯 **Elemzés** | ML predikció, AI összefoglaló, value bet detektálás |
| 💰 **Paper Trading** | Virtuális bankroll, tippek követése, eredmények |
| 📈 **Statisztikák** | Modell teljesítmény, equity curve, historikus adatok |

---

<div style="padding: 1rem; background: #1a1d2e; border-radius: 10px; border: 1px solid #2d3348;">
    <strong>💡 Első lépések:</strong>
    <ol style="color:#94a3b8; margin:0.5rem 0 0 0;">
        <li>Állítsd be az API kulcsokat Streamlit Secrets-ben vagy lokálisan a <code>.env</code> fájlban</li>
        <li>Menj a <strong>📊 Napi Meccsek</strong> oldalra és frissítsd az adatokat</li>
        <li>Válassz egy meccset az <strong>🎯 Elemzés</strong> oldalon</li>
        <li>Tippelj virtuálisan a <strong>💰 Paper Trading</strong> oldalon</li>
    </ol>
</div>
""", unsafe_allow_html=True)

import streamlit as st

st.set_page_config(
    page_title="TippMix Pro 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.database import init_db
from core.api_football import get_rate_limit_info
from core.config import RAPIDAPI_KEY, ZHIPU_API_KEY

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
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg-main: #0B0E14;
    --bg-card: rgba(22, 27, 34, 0.7);
    --primary: #FF6B35;
    --primary-glow: rgba(255, 107, 53, 0.4);
    --accent: #3b82f6;
    --accent-glow: rgba(59, 130, 246, 0.4);
    --success: #10b981;
    --text-main: #F8FAFC;
    --text-muted: #94A3B8;
    --border: rgba(255, 255, 255, 0.08);
}

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
    color: var(--text-main);
}

.stApp {
    background-color: var(--bg-main);
    background-image: 
        radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.08) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(255, 107, 53, 0.08) 0px, transparent 50%);
}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background: rgba(11, 14, 20, 0.8) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-right: 1px solid var(--border);
}

/* ---- Generic Glassmorphism Card ---- */
.modern-card, .match-card {
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.match-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4), 0 0 15px var(--accent-glow);
    border-color: rgba(255, 255, 255, 0.15);
}

/* ---- Swipeable Carousel (Extremely Mobile Friendly) ---- */
.tips-carousel-wrapper {
    width: 100%;
    position: relative;
}
.tips-carousel {
    display: flex;
    gap: 1.5rem;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    scroll-behavior: smooth;
    -webkit-overflow-scrolling: touch;
    padding-bottom: 1.5rem;
    padding-top: 0.5rem;
}
.tips-carousel::-webkit-scrollbar {
    height: 8px;
}
.tips-carousel::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 10px;
}
.tips-carousel::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 10px;
}
.tips-carousel::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.2);
}

.tip-slide {
    flex: 0 0 calc(100% - 2rem); /* Full width minus margin on mobile */
    max-width: 450px;
    scroll-snap-align: center;
}
@media (min-width: 768px) {
    .tip-slide { flex: 0 0 calc(50% - 1rem); }
}
@media (min-width: 1200px) {
    .tip-slide { flex: 0 0 calc(33.333% - 1rem); }
}

.ai-recommendation-card {
    background: linear-gradient(145deg, rgba(30, 58, 138, 0.6) 0%, rgba(15, 23, 42, 0.8) 100%);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(59, 130, 246, 0.5);
    border-radius: 16px;
    padding: 1.5rem;
    height: 100%;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255,255,255,0.1);
    transition: transform 0.2s;
}
.ai-recommendation-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.4), 0 0 20px var(--accent-glow);
    border-color: rgba(59, 130, 246, 0.8);
}

/* ---- Badges ---- */
.badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 700;
    margin-right: 0.4rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.badge-value { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
.badge-drop  { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
.badge-rise  { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
.badge-live  { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }

/* ---- Metric overrides ---- */
[data-testid="stMetricValue"] {
    font-size: 2.2rem !important;
    font-weight: 800 !important;
    background: linear-gradient(90deg, #F8FAFC, #cbd5e1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
[data-testid="stMetricLabel"] {
    font-size: 0.9rem !important;
    color: var(--text-muted) !important;
    font-weight: 500 !important;
}

/* ---- Progress bars ---- */
.stProgress > div > div > div {
    border-radius: 12px;
    background-image: linear-gradient(90deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 100%);
}

/* ---- Typography & Headings ---- */
h1, h2, h3 {
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
}

/* ---- Section header ---- */
.section-header {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 2rem 0 1rem 0;
    display: flex;
    align-items: center;
}
.section-header::after {
    content: "";
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, var(--border) 0%, transparent 100%);
    margin-left: 1rem;
}

/* ---- Footer ---- */
.footer {
    text-align: center;
    color: #475569;
    font-size: 0.8rem;
    padding: 3rem 0 1.5rem 0;
}

/* Responsive tweaks */
@media (max-width: 600px) {
    .modern-card, .match-card {
        padding: 1rem;
    }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
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
        if RAPIDAPI_KEY:
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

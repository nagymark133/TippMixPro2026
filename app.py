import streamlit as st

st.set_page_config(
    page_title="TippMix Pro 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.database import init_db
from core.api_football import get_rate_limit_info
from core.config import FOOTBALL_DATA_KEY, ZHIPU_API_KEY

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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

:root {
    --bg-main: #060910;
    --bg-card: rgba(15, 19, 28, 0.85);
    --bg-card-hover: rgba(20, 25, 38, 0.95);
    --bg-surface: rgba(22, 27, 40, 0.6);
    --primary: #FF6B35;
    --primary-glow: rgba(255, 107, 53, 0.35);
    --accent: #6366f1;
    --accent-glow: rgba(99, 102, 241, 0.35);
    --blue: #3b82f6;
    --blue-glow: rgba(59, 130, 246, 0.3);
    --success: #10b981;
    --success-glow: rgba(16, 185, 129, 0.25);
    --warning: #f59e0b;
    --danger: #ef4444;
    --text-main: #F0F4F8;
    --text-secondary: #B0BEC5;
    --text-muted: #6B7A8D;
    --border: rgba(255, 255, 255, 0.06);
    --border-hover: rgba(255, 255, 255, 0.12);
    --radius-sm: 10px;
    --radius-md: 14px;
    --radius-lg: 20px;
    --radius-xl: 24px;
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: var(--text-main);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

.stApp {
    background: var(--bg-main);
    background-image:
        radial-gradient(ellipse 80% 60% at 10% 0%, rgba(99, 102, 241, 0.07) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 90% 5%, rgba(255, 107, 53, 0.06) 0%, transparent 50%),
        radial-gradient(ellipse 50% 40% at 50% 100%, rgba(16, 185, 129, 0.04) 0%, transparent 60%);
}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background: rgba(8, 11, 18, 0.92) !important;
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border-right: 1px solid var(--border);
}

/* ---- Scrollbar ---- */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }

/* ---- API Quota Header Bar ---- */
.api-quota-bar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    background: linear-gradient(135deg, rgba(15,19,28,0.9) 0%, rgba(20,25,38,0.8) 100%);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 0.6rem 1.2rem;
    margin-bottom: 1.25rem;
    font-size: 0.8rem;
}
.api-quota-bar .quota-label {
    color: var(--text-muted);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 0.7rem;
}
.api-quota-bar .quota-value {
    color: var(--success);
    font-weight: 800;
    font-size: 0.95rem;
    font-variant-numeric: tabular-nums;
}
.api-quota-bar .quota-value.low { color: var(--warning); }
.api-quota-bar .quota-value.critical { color: var(--danger); }
.api-quota-track {
    flex: 1;
    height: 5px;
    background: rgba(255,255,255,0.06);
    border-radius: 10px;
    overflow: hidden;
}
.api-quota-fill {
    height: 100%;
    border-radius: 10px;
    transition: width 0.5s ease;
}

/* ---- Generic Glassmorphism Card ---- */
.modern-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px) saturate(150%);
    -webkit-backdrop-filter: blur(20px) saturate(150%);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3), 0 1px 0 inset rgba(255,255,255,0.03);
    transition: all 0.35s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.modern-card:hover {
    background: var(--bg-card-hover);
    border-color: var(--border-hover);
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255,255,255,0.05);
}

/* ---- Match Card ---- */
.match-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px) saturate(150%);
    -webkit-backdrop-filter: blur(20px) saturate(150%);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 2px 16px rgba(0,0,0,0.25);
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    position: relative;
    overflow: hidden;
}
.match-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), var(--blue), transparent);
    opacity: 0;
    transition: opacity 0.3s;
}
.match-card:hover {
    transform: translateY(-3px);
    border-color: var(--border-hover);
    box-shadow: 0 12px 40px rgba(0,0,0,0.45), 0 0 20px var(--accent-glow);
}
.match-card:hover::before { opacity: 1; }

/* ---- Team Logos ---- */
.team-logo {
    width: 36px;
    height: 36px;
    object-fit: contain;
    vertical-align: middle;
    border-radius: 6px;
    background: rgba(255,255,255,0.04);
    padding: 3px;
    flex-shrink: 0;
}
.team-logo-lg {
    width: 52px;
    height: 52px;
    object-fit: contain;
    vertical-align: middle;
    border-radius: 8px;
    background: rgba(255,255,255,0.04);
    padding: 4px;
    flex-shrink: 0;
}

/* ---- Score ---- */
.score-big {
    font-size: 1.8rem;
    font-weight: 900;
    color: var(--text-main);
    letter-spacing: 0.05em;
    font-variant-numeric: tabular-nums;
}

/* ---- Match Row Layout ---- */
.match-teams-row {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1rem;
    padding: 0.6rem 0;
}
.match-team {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex: 1;
}
.match-team.home { justify-content: flex-end; text-align: right; }
.match-team.away { justify-content: flex-start; text-align: left; }
.match-team-name {
    font-weight: 700;
    font-size: 0.95rem;
    color: var(--text-main);
    line-height: 1.2;
}
.match-score-center {
    min-width: 80px;
    text-align: center;
    flex-shrink: 0;
}

/* ---- Odds Pills ---- */
.odds-row {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.75rem;
    justify-content: center;
}
.odds-pill {
    text-align: center;
    padding: 0.4rem 0.9rem;
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    min-width: 64px;
    transition: all 0.2s;
}
.odds-pill:hover {
    background: rgba(255,255,255,0.08);
    border-color: var(--border-hover);
}
.odds-pill .label {
    font-size: 0.6rem;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.15rem;
}
.odds-pill .value { font-weight: 800; font-size: 0.95rem; font-variant-numeric: tabular-nums; }
.odds-pill .value.home { color: #34d399; }
.odds-pill .value.draw { color: #fbbf24; }
.odds-pill .value.away { color: #60a5fa; }

/* ---- League Header ---- */
.league-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.35rem;
}
.league-name {
    color: var(--text-muted);
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* ---- Drop Badges Row ---- */
.drops-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.6rem;
}

/* ---- Swipeable Carousel ---- */
.tips-carousel-wrapper {
    width: 100%;
    position: relative;
    padding: 0.5rem 0;
}
.tips-carousel {
    display: flex;
    gap: 1rem;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    scroll-behavior: smooth;
    -webkit-overflow-scrolling: touch;
    padding-bottom: 1rem;
    padding-top: 0.25rem;
}
.tips-carousel::-webkit-scrollbar { height: 4px; }
.tips-carousel::-webkit-scrollbar-track { background: transparent; }
.tips-carousel::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }

.tip-slide {
    flex: 0 0 calc(100% - 1rem);
    max-width: 420px;
    scroll-snap-align: center;
}
@media (min-width: 768px) {
    .tip-slide { flex: 0 0 calc(50% - 0.75rem); }
}
@media (min-width: 1200px) {
    .tip-slide { flex: 0 0 calc(33.333% - 0.75rem); }
}

.ai-recommendation-card {
    background: linear-gradient(160deg, rgba(99, 102, 241, 0.15) 0%, rgba(15, 23, 42, 0.85) 50%, rgba(16, 185, 129, 0.08) 100%);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: var(--radius-lg);
    padding: 1.25rem;
    height: 100%;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255,255,255,0.06);
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    position: relative;
    overflow: hidden;
}
.ai-recommendation-card::after {
    content: "";
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle, rgba(99,102,241,0.06) 0%, transparent 60%);
    pointer-events: none;
}
.ai-recommendation-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 16px 48px rgba(0,0,0,0.5), 0 0 30px var(--accent-glow);
    border-color: rgba(99, 102, 241, 0.5);
}

/* ---- Badges ---- */
.badge {
    display: inline-flex;
    align-items: center;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    gap: 0.2rem;
    white-space: nowrap;
}
.badge-value { background: rgba(34, 197, 94, 0.12); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.25); }
.badge-drop  { background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.25); }
.badge-rise  { background: rgba(59, 130, 246, 0.12); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.25); }
.badge-live  { background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.25); }
.badge-live-pulse { animation: pulse-badge 2s ease-in-out infinite; }
@keyframes pulse-badge {
    0%, 100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.3); }
    50% { box-shadow: 0 0 0 6px rgba(245, 158, 11, 0); }
}
.badge-time {
    background: rgba(255,255,255,0.06);
    color: var(--text-secondary);
    border: 1px solid var(--border);
}

/* ---- Tip Card (in tabs) ---- */
.tip-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.5rem;
    transition: all 0.25s ease;
    position: relative;
    overflow: hidden;
}
.tip-card:hover {
    background: var(--bg-card-hover);
    border-color: var(--border-hover);
}
.tip-card .tip-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.5rem;
}
.tip-card .tip-market {
    font-size: 0.7rem;
    color: var(--text-muted);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.2rem;
}
.tip-card .tip-selection {
    font-weight: 700;
    color: var(--text-main);
    font-size: 0.95rem;
    line-height: 1.3;
}
.tip-card .tip-prob {
    font-size: 1.4rem;
    font-weight: 900;
    font-variant-numeric: tabular-nums;
    line-height: 1;
}
.tip-card .tip-conf {
    font-size: 0.65rem;
    color: var(--text-muted);
    font-weight: 600;
    text-transform: uppercase;
}
.tip-bar-track {
    background: rgba(255,255,255,0.05);
    border-radius: 4px;
    height: 4px;
    overflow: hidden;
    margin-bottom: 0.4rem;
}
.tip-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
}
.tip-card .tip-reasoning {
    font-size: 0.75rem;
    color: var(--text-muted);
    line-height: 1.5;
}

/* ---- Value Bet Card ---- */
.value-bet-card {
    background: linear-gradient(135deg, rgba(16,185,129,0.08) 0%, rgba(15,23,42,0.85) 100%);
    border: 1px solid rgba(16,185,129,0.2);
    border-radius: var(--radius-md);
    padding: 1.1rem;
    margin-bottom: 0.6rem;
    transition: all 0.3s ease;
    position: relative;
}
.value-bet-card::before {
    content: "";
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: var(--success);
    border-radius: 3px 0 0 3px;
}
.value-bet-card:hover {
    border-color: rgba(16,185,129,0.4);
    box-shadow: 0 8px 32px rgba(16,185,129,0.1);
}

/* ---- Confidence Meter ---- */
.conf-meter {
    text-align: center;
    padding: 1rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    transition: all 0.3s;
}
.conf-meter:hover {
    border-color: var(--border-hover);
    background: var(--bg-card-hover);
}
.conf-meter .conf-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.3rem;
}
.conf-meter .conf-value {
    font-size: 2.2rem;
    font-weight: 900;
    line-height: 1;
    margin-bottom: 0.4rem;
    font-variant-numeric: tabular-nums;
}
.conf-meter .conf-bar-track {
    height: 6px;
    background: rgba(255,255,255,0.06);
    border-radius: 6px;
    overflow: hidden;
    margin-top: 0.5rem;
}
.conf-meter .conf-bar-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.6s cubic-bezier(0.25, 0.8, 0.25, 1);
}

/* ---- Analysis Match Header ---- */
.analysis-header {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1.5rem;
    padding: 1.5rem 1rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-xl);
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.analysis-header::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--primary), var(--accent), var(--blue));
}
.analysis-header .ah-team {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    flex: 1;
    min-width: 0;
}
.analysis-header .ah-team-name {
    font-weight: 800;
    font-size: 1.1rem;
    text-align: center;
    line-height: 1.2;
    color: var(--text-main);
    word-wrap: break-word;
}
.analysis-header .ah-vs {
    color: var(--text-muted);
    font-size: 1.2rem;
    font-weight: 800;
    flex-shrink: 0;
}

/* ---- AI Summary Card ---- */
.ai-summary-card {
    background: linear-gradient(160deg, rgba(99,102,241,0.08) 0%, var(--bg-card) 40%, rgba(255,107,53,0.05) 100%);
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    position: relative;
    overflow: hidden;
}
.ai-summary-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--primary));
}
.ai-summary-card .ai-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.25rem 0.65rem;
    background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 700;
    color: #a5b4fc;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.75rem;
}
.ai-summary-card .ai-text {
    color: var(--text-secondary);
    font-size: 0.9rem;
    line-height: 1.7;
}

/* ---- Metric overrides ---- */
[data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 900 !important;
    background: linear-gradient(135deg, #F0F4F8, #B0BEC5);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
[data-testid="stMetricLabel"] {
    font-size: 0.85rem !important;
    color: var(--text-muted) !important;
    font-weight: 600 !important;
}

/* ---- Progress bars ---- */
.stProgress > div > div > div {
    border-radius: 10px;
}

/* ---- Typography ---- */
h1, h2, h3 {
    font-weight: 900 !important;
    letter-spacing: -0.03em !important;
}
h1 { font-size: 1.8rem !important; }

/* ---- Section header ---- */
.section-header {
    font-size: 0.78rem;
    font-weight: 800;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 2rem 0 1rem 0;
    display: flex;
    align-items: center;
    gap: 0.75rem;
}
.section-header::after {
    content: "";
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, var(--border) 0%, transparent 100%);
}

/* ---- Streamlit Tab Overrides ---- */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.25rem;
    background: rgba(255,255,255,0.02);
    border-radius: var(--radius-md);
    padding: 0.25rem;
    border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-sm) !important;
    padding: 0.5rem 1rem !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    color: var(--text-muted) !important;
    transition: all 0.2s !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-main) !important;
    background: rgba(255,255,255,0.05) !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(99,102,241,0.15) !important;
    color: #a5b4fc !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background-color: var(--accent) !important;
}

/* ---- Dataframe ---- */
.stDataFrame { border-radius: var(--radius-md) !important; overflow: hidden; }

/* ---- Footer ---- */
.footer {
    text-align: center;
    color: #3D4A5C;
    font-size: 0.75rem;
    padding: 3rem 0 1.5rem 0;
    letter-spacing: 0.02em;
}

/* ---- No Data State ---- */
.empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: var(--text-muted);
}
.empty-state .empty-icon { font-size: 3rem; margin-bottom: 0.75rem; }
.empty-state .empty-text { font-size: 0.95rem; line-height: 1.6; }

/* ---- Responsive ---- */
@media (max-width: 768px) {
    .modern-card, .match-card { padding: 1rem; }
    .match-team-name { font-size: 0.85rem; }
    .team-logo { width: 28px; height: 28px; }
    .team-logo-lg { width: 40px; height: 40px; }
    .score-big { font-size: 1.4rem; }
    .odds-pill { min-width: 52px; padding: 0.35rem 0.6rem; }
    .odds-pill .value { font-size: 0.85rem; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    .conf-meter .conf-value { font-size: 1.8rem; }
    .analysis-header { gap: 0.75rem; padding: 1rem 0.5rem; }
    .analysis-header .ah-team-name { font-size: 0.9rem; }
    .api-quota-bar { padding: 0.5rem 0.8rem; flex-wrap: wrap; }
    h1 { font-size: 1.4rem !important; }
}
@media (max-width: 480px) {
    .match-teams-row { gap: 0.5rem; }
    .match-team-name { font-size: 0.8rem; }
    .tip-slide { flex: 0 0 calc(100% - 0.5rem); }
    .odds-row { gap: 0.3rem; }
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
        if FOOTBALL_DATA_KEY:
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

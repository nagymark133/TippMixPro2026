import streamlit as st


def inject_global_styles() -> None:
    st.markdown(
        """
<style>
:root {
    --bg-main: #0b1220;
    --bg-card: #111827;
    --bg-card-hover: #172033;
    --bg-soft: #0f172a;
    --primary: #f97316;
    --accent: #38bdf8;
    --success: #22c55e;
    --warning: #f59e0b;
    --danger: #ef4444;
    --text-main: #f8fafc;
    --text-secondary: #cbd5e1;
    --text-muted: #94a3b8;
    --border: rgba(148, 163, 184, 0.18);
    --border-strong: rgba(148, 163, 184, 0.28);
    --shadow: 0 10px 30px rgba(2, 6, 23, 0.24);
    --radius-sm: 10px;
    --radius-md: 16px;
    --radius-lg: 22px;
}

html, body, [class*="css"] {
    color: var(--text-main);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(249, 115, 22, 0.09), transparent 32%),
        radial-gradient(circle at top right, rgba(56, 189, 248, 0.08), transparent 28%),
        linear-gradient(180deg, #0b1220 0%, #0a1020 100%);
}

section[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid var(--border);
}

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.25);
    border-radius: 999px;
}

.api-quota-bar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    background: rgba(15, 23, 42, 0.9);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 0.7rem 1rem;
    margin-bottom: 1.1rem;
}
.api-quota-bar .quota-label {
    color: var(--text-muted);
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.api-quota-bar .quota-value {
    color: var(--success);
    font-weight: 900;
    font-variant-numeric: tabular-nums;
}
.api-quota-bar .quota-value.low { color: var(--warning); }
.api-quota-bar .quota-value.critical { color: var(--danger); }
.api-quota-track {
    flex: 1;
    height: 6px;
    background: rgba(148, 163, 184, 0.14);
    border-radius: 999px;
    overflow: hidden;
}
.api-quota-fill {
    height: 100%;
    border-radius: 999px;
}

.modern-card,
.match-card,
.conf-meter,
.tip-card,
.value-bet-card,
.ai-summary-card {
    box-shadow: var(--shadow);
}

.modern-card,
.match-card {
    background: rgba(17, 24, 39, 0.92);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
}

.modern-card {
    padding: 1.1rem 1.2rem;
    margin-bottom: 1rem;
}

.match-card {
    padding: 1rem 1.15rem;
    margin-bottom: 0.8rem;
}

.team-logo,
.team-logo-lg {
    object-fit: contain;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 14px;
    flex-shrink: 0;
}

.team-logo {
    width: 36px;
    height: 36px;
    padding: 4px;
}

.team-logo-lg {
    width: 60px;
    height: 60px;
    padding: 6px;
}

.score-big {
    font-size: 1.5rem;
    font-weight: 900;
    color: var(--text-main);
    font-variant-numeric: tabular-nums;
}

.match-teams-row {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 0.8rem;
    align-items: center;
}

.match-team {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    min-width: 0;
}

.match-team.home {
    justify-content: flex-end;
    text-align: right;
}

.match-team.away {
    justify-content: flex-start;
    text-align: left;
}

.match-team-name {
    font-weight: 700;
    font-size: 0.96rem;
    line-height: 1.25;
    color: var(--text-main);
    word-break: break-word;
}

.match-score-center {
    min-width: 72px;
    text-align: center;
}

.odds-row {
    display: flex;
    justify-content: center;
    gap: 0.55rem;
    margin-top: 0.9rem;
    flex-wrap: wrap;
}

.odds-pill {
    min-width: 62px;
    padding: 0.4rem 0.8rem;
    background: rgba(15, 23, 42, 0.88);
    border: 1px solid var(--border);
    border-radius: 999px;
    text-align: center;
}

.odds-pill .label {
    font-size: 0.62rem;
    font-weight: 800;
    color: var(--text-muted);
    text-transform: uppercase;
}

.odds-pill .value {
    font-weight: 900;
    font-size: 0.95rem;
    font-variant-numeric: tabular-nums;
}

.odds-pill .value.home { color: #4ade80; }
.odds-pill .value.draw { color: #fbbf24; }
.odds-pill .value.away { color: #60a5fa; }

.league-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.7rem;
}

.league-name {
    color: var(--text-muted);
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.drops-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-top: 0.8rem;
}

.tips-carousel-wrapper {
    width: 100%;
    overflow: hidden;
    padding-bottom: 0.25rem;
}

.tips-carousel {
    display: flex;
    gap: 1rem;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    padding-bottom: 0.75rem;
}

.tip-slide {
    flex: 0 0 min(360px, 92%);
    scroll-snap-align: start;
}

.ai-recommendation-card {
    background: linear-gradient(180deg, rgba(17, 24, 39, 0.96) 0%, rgba(15, 23, 42, 0.96) 100%);
    border: 1px solid rgba(56, 189, 248, 0.18);
    border-radius: var(--radius-lg);
    padding: 1.1rem;
    min-height: 230px;
}

.badge {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.28rem 0.65rem;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    white-space: nowrap;
}

.badge-value { background: rgba(34, 197, 94, 0.14); color: #4ade80; }
.badge-drop { background: rgba(239, 68, 68, 0.14); color: #f87171; }
.badge-rise { background: rgba(59, 130, 246, 0.14); color: #60a5fa; }
.badge-live { background: rgba(245, 158, 11, 0.14); color: #fbbf24; }
.badge-time { background: rgba(148, 163, 184, 0.14); color: var(--text-secondary); }

.tip-card {
    background: rgba(17, 24, 39, 0.92);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 0.95rem 1rem;
    margin-bottom: 0.65rem;
}

.tip-card .tip-header {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: flex-start;
    margin-bottom: 0.45rem;
}

.tip-card .tip-market {
    font-size: 0.7rem;
    font-weight: 800;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.22rem;
}

.tip-card .tip-selection {
    color: var(--text-main);
    font-size: 0.98rem;
    font-weight: 800;
    line-height: 1.35;
}

.tip-card .tip-prob {
    font-size: 1.35rem;
    line-height: 1;
    font-weight: 900;
    font-variant-numeric: tabular-nums;
}

.tip-card .tip-conf,
.tip-card .tip-reasoning {
    color: var(--text-muted);
}

.tip-card .tip-conf {
    font-size: 0.68rem;
    font-weight: 800;
    text-transform: uppercase;
}

.tip-card .tip-reasoning {
    font-size: 0.77rem;
    line-height: 1.55;
}

.tip-bar-track,
.conf-meter .conf-bar-track {
    background: rgba(148, 163, 184, 0.16);
    border-radius: 999px;
    overflow: hidden;
}

.tip-bar-track {
    height: 6px;
    margin-bottom: 0.45rem;
}

.tip-bar-fill,
.conf-meter .conf-bar-fill {
    height: 100%;
    border-radius: 999px;
}

.value-bet-card {
    background: linear-gradient(180deg, rgba(20, 83, 45, 0.22) 0%, rgba(15, 23, 42, 0.94) 100%);
    border: 1px solid rgba(34, 197, 94, 0.22);
    border-radius: var(--radius-md);
    padding: 1rem 1.05rem;
    margin-bottom: 0.7rem;
}

.conf-meter {
    background: rgba(17, 24, 39, 0.92);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1rem;
    text-align: center;
}

.conf-meter .conf-label {
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}

.conf-meter .conf-value {
    font-size: 2rem;
    font-weight: 900;
    line-height: 1;
    margin-bottom: 0.55rem;
    font-variant-numeric: tabular-nums;
}

.conf-meter .conf-bar-track {
    height: 8px;
}

.analysis-header {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 1rem;
    background: rgba(17, 24, 39, 0.94);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1rem 1.2rem;
    margin-bottom: 1.25rem;
    box-shadow: var(--shadow);
}

.analysis-header .ah-team {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.45rem;
    min-width: 0;
}

.analysis-header .ah-team-name {
    color: var(--text-main);
    font-size: 1rem;
    font-weight: 800;
    line-height: 1.25;
    text-align: center;
    word-break: break-word;
}

.analysis-header .ah-vs {
    color: var(--text-muted);
    font-size: 1rem;
    font-weight: 900;
    letter-spacing: 0.14em;
}

.ai-summary-card {
    background: linear-gradient(180deg, rgba(17, 24, 39, 0.96) 0%, rgba(15, 23, 42, 0.96) 100%);
    border: 1px solid rgba(56, 189, 248, 0.16);
    border-radius: var(--radius-lg);
    padding: 1.2rem;
}

.ai-summary-card .ai-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.3rem 0.7rem;
    border-radius: 999px;
    background: rgba(56, 189, 248, 0.12);
    color: #7dd3fc;
    font-size: 0.7rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.8rem;
}

.ai-summary-card .ai-text {
    color: var(--text-secondary);
    line-height: 1.7;
    font-size: 0.92rem;
}

.section-header {
    font-size: 0.75rem;
    font-weight: 900;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 1.8rem 0 0.9rem 0;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 0.35rem;
    background: rgba(15, 23, 42, 0.84);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.3rem;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    font-size: 0.82rem !important;
    font-weight: 700 !important;
    color: var(--text-muted) !important;
}

.stTabs [aria-selected="true"] {
    background: rgba(249, 115, 22, 0.14) !important;
    color: #fdba74 !important;
}

[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 900 !important;
}

[data-testid="stMetricLabel"] {
    color: var(--text-muted) !important;
    font-weight: 700 !important;
}

.stDataFrame {
    border-radius: var(--radius-md) !important;
    overflow: hidden;
}

.empty-state {
    text-align: center;
    color: var(--text-muted);
    padding: 2.8rem 1rem;
}

.empty-state .empty-icon {
    font-size: 2.8rem;
    margin-bottom: 0.7rem;
}

.empty-state .empty-text {
    font-size: 0.96rem;
    line-height: 1.6;
}

@media (max-width: 768px) {
    .analysis-header,
    .match-teams-row {
        grid-template-columns: 1fr;
    }

    .analysis-header .ah-vs,
    .match-score-center {
        min-width: auto;
    }

    .match-team.home,
    .match-team.away {
        justify-content: center;
        text-align: center;
    }

    .conf-meter .conf-value {
        font-size: 1.7rem;
    }

    .team-logo-lg {
        width: 52px;
        height: 52px;
    }

    .api-quota-bar {
        flex-wrap: wrap;
    }
}
</style>
        """,
        unsafe_allow_html=True,
    )
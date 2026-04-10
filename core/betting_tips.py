"""
Betting tips generator — derives tips for 30+ markets from predictions,
team stats, H2H data and odds.
"""
from __future__ import annotations
import math


# ── helpers ───────────────────────────────────────────────────────────────

def _sd(a, b, default=0.0):
    """Safe divide."""
    return a / b if b and b > 0 else default


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def _conf_label(prob: float) -> tuple[str, str]:
    """Return (emoji, label) for a confidence level."""
    if prob >= 0.75:
        return "🟢", "Nagyon valószínű"
    if prob >= 0.60:
        return "🔵", "Valószínű"
    if prob >= 0.45:
        return "🟡", "Közepes"
    if prob >= 0.30:
        return "🟠", "Bizonytalan"
    return "🔴", "Kevéssé valószínű"


def _tip_card(market: str, selection: str, prob: float, reasoning: str,
              odds_value: float | None = None) -> dict:
    emoji, label = _conf_label(prob)
    return {
        "market": market,
        "selection": selection,
        "prob": prob,
        "confidence_emoji": emoji,
        "confidence_label": label,
        "reasoning": reasoning,
        "odds": odds_value,
    }


# ── stat extractors ───────────────────────────────────────────────────────

def _avg_goals(stats: dict | None) -> tuple[float, float]:
    """Return (goals_for_avg, goals_against_avg) per match."""
    if not stats:
        return 1.2, 1.2
    mp = max(stats.get("matches_played", 0), 1)
    return _sd(stats.get("goals_for", 0), mp, 1.2), _sd(stats.get("goals_against", 0), mp, 1.2)


def _expected_goals(home_stats, away_stats) -> tuple[float, float]:
    """Estimate xG for home & away using available stats."""
    h_gf, h_ga = _avg_goals(home_stats)
    a_gf, a_ga = _avg_goals(away_stats)
    # Home expected = blend of home attack & away defence weakness
    home_xg = (h_gf * 0.6 + a_ga * 0.4) * 1.05  # slight home boost
    away_xg = (a_gf * 0.6 + h_ga * 0.4) * 0.95
    return max(home_xg, 0.2), max(away_xg, 0.2)


def _poisson_prob(lam: float, k: int) -> float:
    """P(X = k) for Poisson distribution."""
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def _poisson_over(lam: float, threshold: float) -> float:
    """P(X > threshold) for Poisson."""
    k_max = int(threshold)
    return 1.0 - sum(_poisson_prob(lam, k) for k in range(k_max + 1))


# ── main generator ────────────────────────────────────────────────────────

def generate_betting_tips(
    preds: dict,
    home_stats: dict | None,
    away_stats: dict | None,
    odds: dict | None,
    h2h: list | None,
    home_name: str = "Hazai",
    away_name: str = "Vendég",
) -> list[dict]:
    """Generate a comprehensive list of betting tip cards."""
    tips: list[dict] = []
    hp = preds.get("home_prob", 0.45)
    dp = preds.get("draw_prob", 0.25)
    ap = preds.get("away_prob", 0.30)
    o25 = preds.get("over25_prob", 0.50)
    u25 = preds.get("under25_prob", 0.50)

    home_xg, away_xg = _expected_goals(home_stats, away_stats)
    total_xg = home_xg + away_xg

    # ── 1X2 – Rendes játékidő ────────────────────────────────────────────
    best_1x2 = max([("1 (Hazai)", hp), ("X (Döntetlen)", dp), ("2 (Vendég)", ap)], key=lambda x: x[1])
    tips.append(_tip_card(
        "1X2 — Rendes játékidő",
        best_1x2[0],
        best_1x2[1],
        f"{home_name} {hp:.0%} | Döntetlen {dp:.0%} | {away_name} {ap:.0%}",
    ))

    # ── Kétesély (Double Chance) ──────────────────────────────────────────
    dc_1x = hp + dp
    dc_12 = hp + ap
    dc_x2 = dp + ap
    best_dc = max([("1X", dc_1x), ("12", dc_12), ("X2", dc_x2)], key=lambda x: x[1])
    dc_labels = {"1X": f"{home_name} vagy Döntetlen", "12": f"{home_name} vagy {away_name} (nem döntetlen)",
                 "X2": f"Döntetlen vagy {away_name}"}
    tips.append(_tip_card(
        "Kétesély — Rendes játékidő",
        f"{best_dc[0]} ({dc_labels[best_dc[0]]})",
        best_dc[1],
        f"1X: {dc_1x:.0%} | 12: {dc_12:.0%} | X2: {dc_x2:.0%}",
    ))

    # ── Döntetlennél a tét visszajár (Draw No Bet) ───────────────────────
    if dp < 1.0:
        dnb_home = hp / (hp + ap)
        dnb_away = ap / (hp + ap)
        best_dnb = (home_name, dnb_home) if dnb_home >= dnb_away else (away_name, dnb_away)
        tips.append(_tip_card(
            "Döntetlennél a tét visszajár — Rendes játékidő",
            best_dnb[0],
            best_dnb[1],
            f"{home_name}: {dnb_home:.0%} | {away_name}: {dnb_away:.0%} (döntetlen → visszatérítés)",
        ))

    # ── Mindkét csapat szerez gólt (BTTS) ────────────────────────────────
    # P(BTTS) ≈ P(home scores) * P(away scores)
    p_home_scores = 1.0 - _poisson_prob(home_xg, 0)
    p_away_scores = 1.0 - _poisson_prob(away_xg, 0)
    btts_yes = p_home_scores * p_away_scores
    btts_no = 1.0 - btts_yes
    best_btts = ("Igen", btts_yes) if btts_yes >= btts_no else ("Nem", btts_no)
    tips.append(_tip_card(
        "Mindkét csapat szerez gólt — Rendes játékidő",
        best_btts[0],
        best_btts[1],
        f"Igen: {btts_yes:.0%} | Nem: {btts_no:.0%} (xG: {home_name} {home_xg:.2f}, {away_name} {away_xg:.2f})",
    ))

    # ── 1X2 + BTTS ───────────────────────────────────────────────────────
    combos_1x2_btts = [
        (f"1 + Igen", hp * btts_yes),
        (f"X + Igen", dp * btts_yes),
        (f"2 + Igen", ap * btts_yes),
        (f"1 + Nem", hp * btts_no),
        (f"X + Nem", dp * btts_no),
        (f"2 + Nem", ap * btts_no),
    ]
    best_combo = max(combos_1x2_btts, key=lambda x: x[1])
    tips.append(_tip_card(
        "1X2 + Mindkét csapat szerez gólt — Rendes játékidő",
        best_combo[0],
        best_combo[1],
        f"Legjobb kombó: {best_combo[0]} ({best_combo[1]:.0%})",
    ))

    # ── Gólszám piacok (Over/Under) ──────────────────────────────────────
    for line, label in [(0.5, "0.5"), (1.5, "1.5"), (2.5, "2.5"), (3.5, "3.5"), (4.5, "4.5")]:
        p_over = _poisson_over(total_xg, line)
        p_under = 1.0 - p_over
        best_g = (f"{label} felett", p_over) if p_over >= p_under else (f"{label} alatt", p_under)
        tips.append(_tip_card(
            f"Gólszám {label} — Rendes játékidő",
            best_g[0],
            best_g[1],
            f"Felett: {p_over:.0%} | Alatt: {p_under:.0%} (várható gólszám: {total_xg:.2f})",
        ))

    # ── Hazai gólszám ────────────────────────────────────────────────────
    for line, label in [(0.5, "0.5"), (1.5, "1.5"), (2.5, "2.5")]:
        p_o = _poisson_over(home_xg, line)
        p_u = 1.0 - p_o
        best = (f"{label} felett", p_o) if p_o >= p_u else (f"{label} alatt", p_u)
        tips.append(_tip_card(
            f"{home_name} gólszám {label} — Rendes játékidő",
            best[0],
            best[1],
            f"Felett: {p_o:.0%} | Alatt: {p_u:.0%} ({home_name} xG: {home_xg:.2f})",
        ))

    # ── Vendég gólszám ───────────────────────────────────────────────────
    for line, label in [(0.5, "0.5"), (1.5, "1.5"), (2.5, "2.5")]:
        p_o = _poisson_over(away_xg, line)
        p_u = 1.0 - p_o
        best = (f"{label} felett", p_o) if p_o >= p_u else (f"{label} alatt", p_u)
        tips.append(_tip_card(
            f"{away_name} gólszám {label} — Rendes játékidő",
            best[0],
            best[1],
            f"Felett: {p_o:.0%} | Alatt: {p_u:.0%} ({away_name} xG: {away_xg:.2f})",
        ))

    # ── BTTS + Gólszám ───────────────────────────────────────────────────
    for line in [2.5, 3.5]:
        p_over_line = _poisson_over(total_xg, line)
        btts_over = btts_yes * p_over_line
        btts_under = btts_yes * (1 - p_over_line)
        no_btts_over = btts_no * p_over_line
        no_btts_under = btts_no * (1 - p_over_line)
        combos = [
            (f"Igen + {line} felett", btts_over),
            (f"Igen + {line} alatt", btts_under),
            (f"Nem + {line} felett", no_btts_over),
            (f"Nem + {line} alatt", no_btts_under),
        ]
        best_c = max(combos, key=lambda x: x[1])
        tips.append(_tip_card(
            f"Mindkét csapat gólt szerez + Gólszám {line} — Rendes játékidő",
            best_c[0],
            best_c[1],
            f"BTTS Igen & >{line}: {btts_over:.0%} | BTTS Igen & <{line}: {btts_under:.0%}",
        ))

    # ── 1. félidő gólszám ────────────────────────────────────────────────
    ht_xg = total_xg * 0.45  # ~45% of goals in first half
    for line, label in [(0.5, "0.5"), (1.5, "1.5"), (2.5, "2.5")]:
        p_o = _poisson_over(ht_xg, line)
        p_u = 1.0 - p_o
        best = (f"{label} felett", p_o) if p_o >= p_u else (f"{label} alatt", p_u)
        tips.append(_tip_card(
            f"Gólszám {label} — 1. félidő",
            best[0],
            best[1],
            f"Felett: {p_o:.0%} | Alatt: {p_u:.0%} (1. félidő xG: {ht_xg:.2f})",
        ))

    # ── 2. félidő gólszám ────────────────────────────────────────────────
    ht2_xg = total_xg * 0.55  # ~55% in second half
    for line, label in [(0.5, "0.5"), (1.5, "1.5"), (2.5, "2.5")]:
        p_o = _poisson_over(ht2_xg, line)
        p_u = 1.0 - p_o
        best = (f"{label} felett", p_o) if p_o >= p_u else (f"{label} alatt", p_u)
        tips.append(_tip_card(
            f"Gólszám {label} — 2. félidő",
            best[0],
            best[1],
            f"Felett: {p_o:.0%} | Alatt: {p_u:.0%} (2. félidő xG: {ht2_xg:.2f})",
        ))

    # ── 1X2 – 1. félidő ──────────────────────────────────────────────────
    # Half-time 1X2 is more draw-heavy
    ht_hp = hp * 0.75
    ht_dp = dp * 1.6
    ht_ap = ap * 0.75
    ht_total = ht_hp + ht_dp + ht_ap
    ht_hp /= ht_total
    ht_dp /= ht_total
    ht_ap /= ht_total
    best_ht = max([(f"1 ({home_name})", ht_hp), ("X (Döntetlen)", ht_dp), (f"2 ({away_name})", ht_ap)], key=lambda x: x[1])
    tips.append(_tip_card(
        "1X2 — 1. félidő",
        best_ht[0],
        best_ht[1],
        f"{home_name}: {ht_hp:.0%} | Döntetlen: {ht_dp:.0%} | {away_name}: {ht_ap:.0%}",
    ))

    # ── 1X2 – 2. félidő ──────────────────────────────────────────────────
    ht2_hp = hp * 0.85
    ht2_dp = dp * 1.3
    ht2_ap = ap * 0.9
    ht2_total = ht2_hp + ht2_dp + ht2_ap
    ht2_hp /= ht2_total
    ht2_dp /= ht2_total
    ht2_ap /= ht2_total
    best_ht2 = max([(f"1 ({home_name})", ht2_hp), ("X (Döntetlen)", ht2_dp), (f"2 ({away_name})", ht2_ap)], key=lambda x: x[1])
    tips.append(_tip_card(
        "1X2 — 2. félidő",
        best_ht2[0],
        best_ht2[1],
        f"{home_name}: {ht2_hp:.0%} | Döntetlen: {ht2_dp:.0%} | {away_name}: {ht2_ap:.0%}",
    ))

    # ── Félidő / Végeredmény ──────────────────────────────────────────────
    ht_ft_options = []
    for ht_label, ht_p in [("1", ht_hp), ("X", ht_dp), ("2", ht_ap)]:
        for ft_label, ft_p in [("1", hp), ("X", dp), ("2", ap)]:
            combo_p = ht_p * ft_p
            if ht_label == ft_label:
                combo_p *= 1.3  # correlated boost
            ht_ft_options.append((f"{ht_label}/{ft_label}", combo_p))
    # Normalise
    ht_ft_total = sum(x[1] for x in ht_ft_options)
    ht_ft_options = [(l, p / ht_ft_total) for l, p in ht_ft_options]
    best_htft = max(ht_ft_options, key=lambda x: x[1])
    top3 = sorted(ht_ft_options, key=lambda x: -x[1])[:3]
    tips.append(_tip_card(
        "Félidő/Végeredmény — Rendes játékidő",
        best_htft[0],
        best_htft[1],
        " | ".join(f"{l}: {p:.0%}" for l, p in top3),
    ))

    # ── Mindkét félidőben szerez gólt ─────────────────────────────────────
    p_ht_score = 1 - _poisson_prob(ht_xg, 0)
    p_ht2_score = 1 - _poisson_prob(ht2_xg, 0)
    # Either team in both halves
    p_both_halves = p_ht_score * p_ht2_score
    best_bh = ("Igen", p_both_halves) if p_both_halves >= 0.5 else ("Nem", 1 - p_both_halves)
    tips.append(_tip_card(
        "Mindkét félidőben szerez gólt — Rendes játékidő",
        best_bh[0],
        best_bh[1],
        f"Igen: {p_both_halves:.0%} | Nem: {1-p_both_halves:.0%}",
    ))

    # ── BTTS vagy 2.5 felett ──────────────────────────────────────────────
    p_btts_or_o25 = _clamp(btts_yes + _poisson_over(total_xg, 2.5) - btts_yes * _poisson_over(total_xg, 2.5))
    tips.append(_tip_card(
        "Mindkét csapat gólt szerez VAGY 2.5 felett — Rendes játékidő",
        "Igen" if p_btts_or_o25 >= 0.5 else "Nem",
        max(p_btts_or_o25, 1 - p_btts_or_o25),
        f"Igen: {p_btts_or_o25:.0%} | Nem: {1-p_btts_or_o25:.0%}",
    ))

    # ── Hendikep ──────────────────────────────────────────────────────────
    for handicap_line in [-1, -2, +1, +2]:
        sign = "+" if handicap_line > 0 else ""
        # Simulated score distribution via Poisson
        p_home_cover = 0.0
        p_draw = 0.0
        p_away_cover = 0.0
        for hg in range(8):
            for ag in range(8):
                p_score = _poisson_prob(home_xg, hg) * _poisson_prob(away_xg, ag)
                adj_diff = (hg + handicap_line) - ag
                if adj_diff > 0:
                    p_home_cover += p_score
                elif adj_diff == 0:
                    p_draw += p_score
                else:
                    p_away_cover += p_score
        options = [
            (f"1 ({home_name} {sign}{handicap_line})", p_home_cover),
            (f"X (Döntetlen)", p_draw),
            (f"2 ({away_name})", p_away_cover),
        ]
        best_h = max(options, key=lambda x: x[1])
        tips.append(_tip_card(
            f"Hendikep ({sign}{handicap_line}) — Rendes játékidő",
            best_h[0],
            best_h[1],
            f"1: {p_home_cover:.0%} | X: {p_draw:.0%} | 2: {p_away_cover:.0%}",
        ))

    # ── Pontos eredmény (top 5) ───────────────────────────────────────────
    score_probs = []
    for hg in range(6):
        for ag in range(6):
            p = _poisson_prob(home_xg, hg) * _poisson_prob(away_xg, ag)
            score_probs.append((f"{hg}-{ag}", p))
    score_probs.sort(key=lambda x: -x[1])
    top5_scores = score_probs[:5]
    tips.append(_tip_card(
        "Pontos eredmény — Rendes játékidő",
        top5_scores[0][0],
        top5_scores[0][1],
        " | ".join(f"{s}: {p:.0%}" for s, p in top5_scores),
    ))

    # ── Szerez gólt ───────────────────────────────────────────────────────
    tips.append(_tip_card(
        f"{home_name} szerez gólt — Rendes játékidő",
        "Igen" if p_home_scores >= 0.5 else "Nem",
        max(p_home_scores, 1 - p_home_scores),
        f"Igen: {p_home_scores:.0%} | Nem: {1-p_home_scores:.0%} (xG: {home_xg:.2f})",
    ))
    tips.append(_tip_card(
        f"{away_name} szerez gólt — Rendes játékidő",
        "Igen" if p_away_scores >= 0.5 else "Nem",
        max(p_away_scores, 1 - p_away_scores),
        f"Igen: {p_away_scores:.0%} | Nem: {1-p_away_scores:.0%} (xG: {away_xg:.2f})",
    ))

    # ── Nyer legalább 1 félidőt ───────────────────────────────────────────
    p_h_win_ht = ht_hp
    p_h_win_2h = ht2_hp
    p_h_win_any = _clamp(1 - (1 - p_h_win_ht) * (1 - p_h_win_2h))
    tips.append(_tip_card(
        f"{home_name} nyer legalább egy félidőt — Rendes játékidő",
        "Igen" if p_h_win_any >= 0.5 else "Nem",
        max(p_h_win_any, 1 - p_h_win_any),
        f"Igen: {p_h_win_any:.0%} | Nem: {1-p_h_win_any:.0%}",
    ))

    p_a_win_ht = ht_ap
    p_a_win_2h = ht2_ap
    p_a_win_any = _clamp(1 - (1 - p_a_win_ht) * (1 - p_a_win_2h))
    tips.append(_tip_card(
        f"{away_name} nyer legalább egy félidőt — Rendes játékidő",
        "Igen" if p_a_win_any >= 0.5 else "Nem",
        max(p_a_win_any, 1 - p_a_win_any),
        f"Igen: {p_a_win_any:.0%} | Nem: {1-p_a_win_any:.0%}",
    ))

    # ── Megnyeri mindkét félidőt ──────────────────────────────────────────
    p_h_win_both = ht_hp * ht2_hp
    tips.append(_tip_card(
        f"{home_name} nyeri mindkét félidőt — Rendes játékidő",
        "Igen" if p_h_win_both >= 0.15 else "Nem",
        max(p_h_win_both, 1 - p_h_win_both),
        f"Igen: {p_h_win_both:.0%} | Nem: {1-p_h_win_both:.0%}",
    ))
    p_a_win_both = ht_ap * ht2_ap
    tips.append(_tip_card(
        f"{away_name} nyeri mindkét félidőt — Rendes játékidő",
        "Igen" if p_a_win_both >= 0.15 else "Nem",
        max(p_a_win_both, 1 - p_a_win_both),
        f"Igen: {p_a_win_both:.0%} | Nem: {1-p_a_win_both:.0%}",
    ))

    # ── 0-ra nyeri ────────────────────────────────────────────────────────
    p_home_clean = _poisson_prob(away_xg, 0)  # away scores 0
    p_away_clean = _poisson_prob(home_xg, 0)  # home scores 0
    p_home_cs = hp * p_home_clean  # home wins + clean sheet
    p_away_cs = ap * p_away_clean
    tips.append(_tip_card(
        f"{home_name} 0-ra nyeri — Rendes játékidő",
        "Igen" if p_home_cs >= 0.15 else "Nem",
        max(p_home_cs, 1 - p_home_cs),
        f"Igen: {p_home_cs:.0%} | Nem: {1-p_home_cs:.0%}",
    ))
    tips.append(_tip_card(
        f"{away_name} 0-ra nyeri — Rendes játékidő",
        "Igen" if p_away_cs >= 0.10 else "Nem",
        max(p_away_cs, 1 - p_away_cs),
        f"Igen: {p_away_cs:.0%} | Nem: {1-p_away_cs:.0%}",
    ))

    # ── Szögletek ─────────────────────────────────────────────────────────
    # Estimate corners from goal averages (correlated ~3.5 corners per goal)
    est_home_corners = home_xg * 3.2 + 2.5
    est_away_corners = away_xg * 3.0 + 2.0
    total_corners = est_home_corners + est_away_corners

    tips.append(_tip_card(
        "Melyik csapat végez el több szögletet? — Rendes játékidő",
        home_name if est_home_corners > est_away_corners else away_name,
        _clamp(max(est_home_corners, est_away_corners) / total_corners + 0.05),
        f"{home_name}: ~{est_home_corners:.1f} | {away_name}: ~{est_away_corners:.1f}",
    ))

    for line in [8.5, 9.5, 10.5, 11.5]:
        p_over_c = _poisson_over(total_corners, line)
        best_c = (f"{line} felett", p_over_c) if p_over_c >= 0.5 else (f"{line} alatt", 1 - p_over_c)
        tips.append(_tip_card(
            f"Szögletszám {line} — Rendes játékidő",
            best_c[0],
            best_c[1],
            f"Felett: {p_over_c:.0%} | Alatt: {1-p_over_c:.0%} (becsült: {total_corners:.1f})",
        ))

    for line in [3.5, 4.5, 5.5]:
        p_o_h = _poisson_over(est_home_corners, line)
        tips.append(_tip_card(
            f"{home_name} szögletszám {line} — Rendes játékidő",
            f"{line} felett" if p_o_h >= 0.5 else f"{line} alatt",
            max(p_o_h, 1 - p_o_h),
            f"Felett: {p_o_h:.0%} | Alatt: {1-p_o_h:.0%} (~{est_home_corners:.1f} szöglet)",
        ))
        p_o_a = _poisson_over(est_away_corners, line)
        tips.append(_tip_card(
            f"{away_name} szögletszám {line} — Rendes játékidő",
            f"{line} felett" if p_o_a >= 0.5 else f"{line} alatt",
            max(p_o_a, 1 - p_o_a),
            f"Felett: {p_o_a:.0%} | Alatt: {1-p_o_a:.0%} (~{est_away_corners:.1f} szöglet)",
        ))

    # ── Büntetőlapok (sárga lapok) ────────────────────────────────────────
    est_home_cards = 1.8 + (away_xg - home_xg) * 0.3  # more cards if trailing
    est_away_cards = 1.6 + (home_xg - away_xg) * 0.3
    est_home_cards = max(est_home_cards, 0.8)
    est_away_cards = max(est_away_cards, 0.8)
    total_cards = est_home_cards + est_away_cards

    for line in [3.5, 4.5, 5.5]:
        p_o_cards = _poisson_over(total_cards, line)
        tips.append(_tip_card(
            f"Büntetőlap-szám {line} — Rendes játékidő",
            f"{line} felett" if p_o_cards >= 0.5 else f"{line} alatt",
            max(p_o_cards, 1 - p_o_cards),
            f"Felett: {p_o_cards:.0%} | Alatt: {1-p_o_cards:.0%} (becsült: {total_cards:.1f})",
        ))

    for line in [1.5, 2.5]:
        p_h_cards = _poisson_over(est_home_cards, line)
        tips.append(_tip_card(
            f"{home_name} büntetőlap-szám {line} — Rendes játékidő",
            f"{line} felett" if p_h_cards >= 0.5 else f"{line} alatt",
            max(p_h_cards, 1 - p_h_cards),
            f"Felett: {p_h_cards:.0%} | Alatt: {1-p_h_cards:.0%} (~{est_home_cards:.1f} lap)",
        ))
        p_a_cards = _poisson_over(est_away_cards, line)
        tips.append(_tip_card(
            f"{away_name} büntetőlap-szám {line} — Rendes játékidő",
            f"{line} felett" if p_a_cards >= 0.5 else f"{line} alatt",
            max(p_a_cards, 1 - p_a_cards),
            f"Felett: {p_a_cards:.0%} | Alatt: {1-p_a_cards:.0%} (~{est_away_cards:.1f} lap)",
        ))

    # ── Kaput eltaláló lövések ────────────────────────────────────────────
    est_home_sot = home_xg * 3.0 + 1.5
    est_away_sot = away_xg * 3.0 + 1.0
    total_sot = est_home_sot + est_away_sot

    for line in [8.5, 9.5, 10.5]:
        p_o_sot = _poisson_over(total_sot, line)
        tips.append(_tip_card(
            f"Kaput eltaláló lövések {line} — Rendes játékidő",
            f"{line} felett" if p_o_sot >= 0.5 else f"{line} alatt",
            max(p_o_sot, 1 - p_o_sot),
            f"Felett: {p_o_sot:.0%} | Alatt: {1-p_o_sot:.0%} (becsült: {total_sot:.1f})",
        ))

    for line in [3.5, 4.5]:
        p_h_sot = _poisson_over(est_home_sot, line)
        tips.append(_tip_card(
            f"{home_name} kaput eltaláló lövések {line} — Rendes játékidő",
            f"{line} felett" if p_h_sot >= 0.5 else f"{line} alatt",
            max(p_h_sot, 1 - p_h_sot),
            f"Felett: {p_h_sot:.0%} | Alatt: {1-p_h_sot:.0%} (~{est_home_sot:.1f})",
        ))
        p_a_sot = _poisson_over(est_away_sot, line)
        tips.append(_tip_card(
            f"{away_name} kaput eltaláló lövések {line} — Rendes játékidő",
            f"{line} felett" if p_a_sot >= 0.5 else f"{line} alatt",
            max(p_a_sot, 1 - p_a_sot),
            f"Felett: {p_a_sot:.0%} | Alatt: {1-p_a_sot:.0%} (~{est_away_sot:.1f})",
        ))

    # ── Lesz 11-es? ──────────────────────────────────────────────────────
    # Rough estimate: ~6-8% of matches have a penalty
    p_pen = _clamp(0.07 + (total_xg - 2.5) * 0.02)
    tips.append(_tip_card(
        "Lesz 11-es? — Rendes játékidő",
        "Nem",
        1 - p_pen,
        f"Igen: {p_pen:.0%} | Nem: {1-p_pen:.0%}",
    ))

    # ── Lesz kiállítás? ──────────────────────────────────────────────────
    p_red = _clamp(0.08 + total_cards * 0.01)
    tips.append(_tip_card(
        "Lesz kiállítás? — Rendes játékidő",
        "Nem",
        1 - p_red,
        f"Igen: {p_red:.0%} | Nem: {1-p_red:.0%}",
    ))

    # ── Lesz öngól? ──────────────────────────────────────────────────────
    p_og = _clamp(0.06 + total_xg * 0.01)
    tips.append(_tip_card(
        "Lesz öngól? — Rendes játékidő",
        "Nem",
        1 - p_og,
        f"Igen: {p_og:.0%} | Nem: {1-p_og:.0%}",
    ))

    # ── Szabálytalanságok ─────────────────────────────────────────────────
    est_fouls = total_cards * 4.5 + 8  # rough estimate
    for line in [22.5, 24.5, 26.5]:
        p_o_f = _poisson_over(est_fouls, line)
        tips.append(_tip_card(
            f"Szabálytalanságok {line} — Rendes játékidő",
            f"{line} felett" if p_o_f >= 0.5 else f"{line} alatt",
            max(p_o_f, 1 - p_o_f),
            f"Felett: {p_o_f:.0%} | Alatt: {1-p_o_f:.0%} (becsült: {est_fouls:.0f})",
        ))

    # ── Lesszám ───────────────────────────────────────────────────────────
    est_home_offside = home_xg * 1.5 + 0.8
    est_away_offside = away_xg * 1.5 + 0.8
    total_offside = est_home_offside + est_away_offside

    for line in [3.5, 4.5]:
        p_o_off = _poisson_over(total_offside, line)
        tips.append(_tip_card(
            f"Lesszám {line} — Rendes játékidő",
            f"{line} felett" if p_o_off >= 0.5 else f"{line} alatt",
            max(p_o_off, 1 - p_o_off),
            f"Felett: {p_o_off:.0%} | Alatt: {1-p_o_off:.0%} (becsült: {total_offside:.1f})",
        ))
    for line in [1.5, 2.5]:
        p_h_off = _poisson_over(est_home_offside, line)
        tips.append(_tip_card(
            f"{home_name} lesszám {line} — Rendes játékidő",
            f"{line} felett" if p_h_off >= 0.5 else f"{line} alatt",
            max(p_h_off, 1 - p_h_off),
            f"Felett: {p_h_off:.0%} | Alatt: {1-p_h_off:.0%} (~{est_home_offside:.1f})",
        ))
        p_a_off = _poisson_over(est_away_offside, line)
        tips.append(_tip_card(
            f"{away_name} lesszám {line} — Rendes játékidő",
            f"{line} felett" if p_a_off >= 0.5 else f"{line} alatt",
            max(p_a_off, 1 - p_a_off),
            f"Felett: {p_a_off:.0%} | Alatt: {1-p_a_off:.0%} (~{est_away_offside:.1f})",
        ))

    return tips

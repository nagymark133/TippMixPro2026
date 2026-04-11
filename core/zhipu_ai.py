import json
import logging

import requests

from core.config import ZHIPU_API_KEY, ZHIPU_API_BASE, ZHIPU_MODEL

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Te egy profi sportfogadási elemző vagy. A felhasználó megadja egy focimeccs statisztikáit és az ML modell által számolt valószínűségeket. A feladatod:
1. NAGYON részletes elemzés magyarul (minimum 500 szó, de inkább 600-800).
2. Emeld ki a kulcsfontosságú faktorokat (forma, gólátlag, H2H, hazai/idegen mérleg, sérülések, motiváció).
3. Adj KONKRÉT fogadási javaslatokat: írd le pontosan MIT raknál meg, milyen piacon, és MIÉRT. Pl: "1X2: Hazai győzelem", "Gólszám: 2.5 felett", "Mindkét csapat szerez gólt: Igen" stb.
4. Minden javaslatnál magyarázd el az érvelésed részletesen.
5. Ha Value Bet-et találtunk, magyarázd el miért értékes és miért érdemes megjátszani.
6. Adj egy rövid kockázatelemzést is: mi az ami elromolhat, milyen tényezők szólnak a tipped ellen.
7. Végül adj egy összefoglaló "top 3 tipp" listát a legbiztosabb fogadásokkal.
Legyél objektív és ne ígérj biztos eredményt. Jelezd, hogy ez nem pénzügyi tanács."""

QUICK_TIP_PROMPT = """Te egy profi sportfogadási elemző vagy. A felhasználó megadja egy focimeccs adatait. Adj egyetlen rövid, 1-2 mondatos magyar nyelvű javaslatot arról, hogy szerinted mire érdemes figyelni ennél a meccsnél, és mit érdemes esetleg másképp megközelíteni. Legyél tömör és lényegre törő."""


def generate_analysis(stats: dict) -> str:
    """Send match stats to Zhipu AI GLM and return a Hungarian analysis text."""
    if not ZHIPU_API_KEY:
        return _fallback_analysis(stats)

    user_content = _build_user_message(stats)

    payload = {
        "model": ZHIPU_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.7,
        "max_tokens": 1500,
    }

    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"{ZHIPU_API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        log.error("Zhipu AI request failed: %s", e)
        return _fallback_analysis(stats)


def generate_quick_tip(stats: dict) -> str:
    """Generate a short 1-2 sentence AI recommendation."""
    if not ZHIPU_API_KEY:
        return _fallback_quick_tip(stats)

    user_content = _build_user_message(stats)

    payload = {
        "model": ZHIPU_MODEL,
        "messages": [
            {"role": "system", "content": QUICK_TIP_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.7,
        "max_tokens": 150,
    }

    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"{ZHIPU_API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        log.error("Zhipu AI quick tip request failed: %s", e)
        return _fallback_quick_tip(stats)


def _fallback_quick_tip(stats: dict) -> str:
    """Template-based quick tip when API is unavailable."""
    p = stats.get("predictions", {})
    if not p:
        return "Futtasd az elemzést a részletes javaslatok megtekintéséhez."
    best = max(
        [("hazai győzelem", p.get("home_prob", 0)),
         ("döntetlen", p.get("draw_prob", 0)),
         ("vendég győzelem", p.get("away_prob", 0))],
        key=lambda x: x[1],
    )
    over_prob = p.get("over25_prob", 0.5)
    tip = f"A modell szerint a legvalószínűbb kimenetel: {best[0]} ({best[1]:.0%})."
    if over_prob > 0.6:
        tip += f" Gólgazdag meccs várható (2.5 felett: {over_prob:.0%})."
    elif over_prob < 0.4:
        tip += f" Alacsony gólszám várható (2.5 alatt: {1-over_prob:.0%})."
    return tip


def _build_user_message(stats: dict) -> str:
    parts = [f"Meccs: {stats.get('home_team', '?')} vs {stats.get('away_team', '?')}"]

    if stats.get("home_stats"):
        hs = stats["home_stats"]
        parts.append(f"\nHazai csapat ({stats.get('home_team', '?')}):")
        parts.append(f"  Forma: {hs.get('form', 'N/A')}")
        parts.append(f"  Mérkőzések: {hs.get('matches_played', 0)}, Győzelem: {hs.get('wins', 0)}, Döntetlen: {hs.get('draws', 0)}, Vereség: {hs.get('losses', 0)}")
        parts.append(f"  Gólok: {hs.get('goals_for', 0)} lőtt / {hs.get('goals_against', 0)} kapott")
        parts.append(f"  Otthon: {hs.get('home_wins', 0)}Gy {hs.get('home_draws', 0)}D {hs.get('home_losses', 0)}V")

    if stats.get("away_stats"):
        aws = stats["away_stats"]
        parts.append(f"\nVendég csapat ({stats.get('away_team', '?')}):")
        parts.append(f"  Forma: {aws.get('form', 'N/A')}")
        parts.append(f"  Mérkőzések: {aws.get('matches_played', 0)}, Győzelem: {aws.get('wins', 0)}, Döntetlen: {aws.get('draws', 0)}, Vereség: {aws.get('losses', 0)}")
        parts.append(f"  Gólok: {aws.get('goals_for', 0)} lőtt / {aws.get('goals_against', 0)} kapott")
        parts.append(f"  Idegenben: {aws.get('away_wins', 0)}Gy {aws.get('away_draws', 0)}D {aws.get('away_losses', 0)}V")

    if stats.get("h2h"):
        parts.append(f"\nEgymás elleni (utolsó {len(stats['h2h'])} meccs):")
        for m in stats["h2h"][:5]:
            parts.append(f"  {m.get('date', '?')[:10]}: {m.get('home_team', '?')} {m.get('home_goals', '?')} - {m.get('away_goals', '?')} {m.get('away_team', '?')}")

    if stats.get("predictions"):
        p = stats["predictions"]
        parts.append(f"\nML Modell predikció:")
        parts.append(f"  Hazai győzelem: {p.get('home_prob', 0):.1%}")
        parts.append(f"  Döntetlen: {p.get('draw_prob', 0):.1%}")
        parts.append(f"  Vendég győzelem: {p.get('away_prob', 0):.1%}")
        parts.append(f"  2.5 gól felett: {p.get('over25_prob', 0):.1%}")
        parts.append(f"  2.5 gól alatt: {p.get('under25_prob', 0):.1%}")

    if stats.get("odds"):
        o = stats["odds"]
        parts.append(f"\nOdds: Hazai {o.get('home_odd', '?')} | Döntetlen {o.get('draw_odd', '?')} | Vendég {o.get('away_odd', '?')}")

    if stats.get("value_bets"):
        parts.append(f"\nValue Bet jelzések: {json.dumps(stats['value_bets'], ensure_ascii=False)}")

    return "\n".join(parts)


def _fallback_analysis(stats: dict) -> str:
    """Generate a simple template-based analysis when GLM API is unavailable."""
    home = stats.get("home_team", "Hazai")
    away = stats.get("away_team", "Vendég")
    p = stats.get("predictions", {})

    lines = [f"**{home} vs {away} — Részletes automatikus elemzés**\n"]

    if p:
        best = max(
            [("Hazai győzelem", p.get("home_prob", 0)),
             ("Döntetlen", p.get("draw_prob", 0)),
             ("Vendég győzelem", p.get("away_prob", 0))],
            key=lambda x: x[1],
        )
        lines.append(f"### 📊 ML Modell Predikció")
        lines.append(f"Az ML modell szerint a legvalószínűbb kimenetel: **{best[0]}** ({best[1]:.1%}).")
        lines.append(f"- Hazai győzelem: {p.get('home_prob', 0):.1%}")
        lines.append(f"- Döntetlen: {p.get('draw_prob', 0):.1%}")
        lines.append(f"- Vendég győzelem: {p.get('away_prob', 0):.1%}")
        lines.append(f"- 2.5 gól felett: {p.get('over25_prob', 0):.1%} | alatt: {p.get('under25_prob', 0):.1%}")

    hs = stats.get("home_stats")
    aws = stats.get("away_stats")
    if hs or aws:
        lines.append(f"\n### 📈 Forma és Statisztikák")
        if hs:
            lines.append(f"**{home}** (hazai): Forma: {hs.get('form', 'N/A')[-5:] if hs.get('form') else 'N/A'} | "
                         f"{hs.get('wins', 0)}Gy {hs.get('draws', 0)}D {hs.get('losses', 0)}V | "
                         f"Gólok: {hs.get('goals_for', 0)} lőtt / {hs.get('goals_against', 0)} kapott")
        if aws:
            lines.append(f"**{away}** (vendég): Forma: {aws.get('form', 'N/A')[-5:] if aws.get('form') else 'N/A'} | "
                         f"{aws.get('wins', 0)}Gy {aws.get('draws', 0)}D {aws.get('losses', 0)}V | "
                         f"Gólok: {aws.get('goals_for', 0)} lőtt / {aws.get('goals_against', 0)} kapott")

    if stats.get("h2h"):
        lines.append(f"\n### 🔄 Egymás Elleni Eredmények")
        for m in stats["h2h"][:5]:
            lines.append(f"- {m.get('date', '?')[:10]}: {m.get('home_team', '?')} {m.get('home_goals', '?')}-{m.get('away_goals', '?')} {m.get('away_team', '?')}")

    lines.append(f"\n### 🎯 Konkrét Fogadási Javaslatok")
    if p:
        if best[1] >= 0.5:
            lines.append(f"1. **Fő tipp — {best[0]}**: A modell {best[1]:.0%} valószínűséget ad. Ez a legbiztosabb fogadás erre a meccsre.")
        over_p = p.get('over25_prob', 0.5)
        if over_p > 0.6:
            lines.append(f"2. **Gólszám — 2.5 felett**: {over_p:.0%} valószínűséggel gólgazdag meccsre számíthatunk.")
        elif over_p < 0.4:
            lines.append(f"2. **Gólszám — 2.5 alatt**: {1-over_p:.0%} valószínűséggel kevés gól várható.")
        else:
            lines.append(f"2. **Gólszám**: A modell szerint nincs egyértelmű irány (felett: {over_p:.0%}), óvatosság javasolt.")

    if stats.get("value_bets"):
        lines.append(f"\n### ⚡ Value Bet Lehetőségek")
        for vb in stats["value_bets"]:
            lines.append(f"- **{vb.get('selection', '?')}** — Modell: {vb.get('ml_prob', 0):.1%} vs Implied: {vb.get('implied_prob', 0):.1%} | "
                         f"Edge: +{vb.get('edge', 0):.1%} | Ez azt jelenti, hogy a fogadóiroda alulbecsüli ezt a kimenetelt.")

    lines.append(f"\n### ⚠️ Kockázatok")
    lines.append("Fontos figyelembe venni: egyetlen ML modell sem tökéletes. A forma változhat, sérülések, "
                 "időjárás és motivációs tényezők mind befolyásolhatják az eredményt.")

    lines.append("\n*Ez egy gépi elemzés, nem pénzügyi tanács.*")
    return "\n".join(lines)

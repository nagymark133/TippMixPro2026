import json
import logging

import requests

from core.config import ZHIPU_API_KEY, ZHIPU_API_BASE, ZHIPU_MODEL

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Te egy profi sportfogadási elemző vagy. A felhasználó megadja egy focimeccs statisztikáit és az ML modell által számolt valószínűségeket. A feladatod:
1. Rövid, tömör elemzés magyarul (max 200 szó).
2. Emeld ki a kulcsfontosságú faktorokat (forma, gólátlag, H2H, hazai/idegen mérleg).
3. Adj egy rövid tipp-javaslatot, de mindig jelezd, hogy ez nem pénzügyi tanács.
4. Ha Value Bet-et találtunk, magyarázd el miért értékes.
Legyél objektív és ne ígérj biztos eredményt."""


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
        "max_tokens": 600,
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

    lines = [f"**{home} vs {away} — Automatikus elemzés**\n"]

    if p:
        best = max(
            [("Hazai győzelem", p.get("home_prob", 0)),
             ("Döntetlen", p.get("draw_prob", 0)),
             ("Vendég győzelem", p.get("away_prob", 0))],
            key=lambda x: x[1],
        )
        lines.append(f"Az ML modell szerint a legvalószínűbb kimenetel: **{best[0]}** ({best[1]:.1%}).")
        lines.append(f"Gólok: 2.5 felett {p.get('over25_prob', 0):.1%} | alatt {p.get('under25_prob', 0):.1%}.")

    if stats.get("value_bets"):
        vbs = stats["value_bets"]
        for vb in vbs:
            lines.append(f"\n⚡ **Value Bet**: {vb.get('selection', '?')} — "
                         f"Modell: {vb.get('ml_prob', 0):.1%} vs Odds implied: {vb.get('implied_prob', 0):.1%}")

    lines.append("\n*Ez egy gépi elemzés, nem pénzügyi tanács.*")
    return "\n".join(lines)

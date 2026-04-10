from core.config import VALUE_BET_MARGIN


def detect_value_bets(predictions: dict, odds: dict) -> list[dict]:
    """Compare ML probabilities with bookmaker implied probabilities.

    Args:
        predictions: dict with home_prob, draw_prob, away_prob, over25_prob, under25_prob
        odds: dict with home_odd, draw_odd, away_odd, over25_odd, under25_odd

    Returns:
        List of value bet dicts with selection, ml_prob, implied_prob, expected_value, odds.
    """
    if not predictions or not odds:
        return []

    checks = [
        ("Hazai győzelem (1)", "home_prob", "home_odd"),
        ("Döntetlen (X)", "draw_prob", "draw_odd"),
        ("Vendég győzelem (2)", "away_prob", "away_odd"),
        ("2.5 Gól Felett", "over25_prob", "over25_odd"),
        ("2.5 Gól Alatt", "under25_prob", "under25_odd"),
    ]

    value_bets = []
    for label, prob_key, odd_key in checks:
        ml_prob = predictions.get(prob_key, 0)
        odd_val = odds.get(odd_key)
        if not odd_val or odd_val <= 1:
            continue

        implied_prob = 1.0 / odd_val
        edge = ml_prob - implied_prob

        if edge > VALUE_BET_MARGIN:
            ev = (ml_prob * (odd_val - 1)) - (1 - ml_prob)
            value_bets.append({
                "selection": label,
                "ml_prob": ml_prob,
                "implied_prob": implied_prob,
                "edge": edge,
                "expected_value": ev,
                "odds": odd_val,
                "bet_type": "1X2" if "1" in label or "X" in label or "2" in label else "OU25",
                "bet_selection": _map_selection(label),
            })

    return sorted(value_bets, key=lambda x: x["expected_value"], reverse=True)


def _map_selection(label: str) -> str:
    if "Hazai" in label or "(1)" in label:
        return "Home"
    if "Döntetlen" in label or "(X)" in label:
        return "Draw"
    if "Vendég" in label or "(2)" in label:
        return "Away"
    if "Felett" in label:
        return "Over"
    if "Alatt" in label:
        return "Under"
    return label

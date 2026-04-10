# ⚽ TippMix Pro 2026

Sportfogadási adatelemző és prediktív dashboard — ML alapú valószínűség-számítás, Value Bet detektálás, és virtuális bankroll kezelés.

## 🚀 Telepítés

### 1. Klónozás & környezet

```bash
cd TippMixPro2026
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### 2. API kulcsok beállítása

Lokális futtatáshoz másold le a `.env.example` fájlt `.env` néven és töltsd ki:


```bash
cp .env.example .env
```

```env
API_FOOTBALL_KEY=your_api_football_key_here
ZHIPU_API_KEY=your_zhipu_api_key_here
```

Streamlit Community Cloudon ne `.env` fájlt tölts fel, hanem az app `Secrets` felületén add meg ugyanezeket a kulcsokat:

```toml
API_FOOTBALL_KEY = "your_api_football_key_here"
ZHIPU_API_KEY = "your_zhipu_api_key_here"
```

- **API-Football**: Regisztrálj a [api-football.com](https://www.api-football.com/) oldalon (free tier: 100 request/nap)
- **Zhipu AI**: Regisztrálj a [open.bigmodel.cn](https://open.bigmodel.cn/) oldalon

### 3. Indítás

```bash
streamlit run app.py
```

A dashboard elérhető lesz a `http://localhost:8501` címen.

## 📋 Funkciók

| Oldal | Funkció |
|-------|---------|
| 📊 **Napi Meccsek** | Aznapi meccsek letöltése, odds megjelenítés, dropping odds figyelő |
| 🎯 **Elemzés** | ML predikció (XGBoost), AI összefoglaló (Zhipu GLM), Value Bet detektálás |
| 💰 **Paper Trading** | Virtuális bankroll, tippek rögzítése, eredmények automatikus ellenőrzése |
| 📈 **Statisztikák** | Modell pontosság, equity curve, historikus teljesítmény |

## 🏗️ Architektúra

```
app.py                          # Streamlit főoldal
pages/                          # Streamlit multi-page navigation
core/
  config.py                     # Konfiguráció (Streamlit Secrets + .env fallback)
  database.py                   # SQLite adatbázis réteg
  api_football.py               # API-Football kliens (rate-limit aware)
  zhipu_ai.py                   # Zhipu AI GLM kliens
  ml_model.py                   # XGBoost modellek (1X2 + O/U 2.5)
  value_bet.py                  # Value Bet detektálás
  odds_tracker.py               # Dropping odds figyelő
```

## ⚙️ Tech Stack

- **Frontend**: Streamlit
- **Adatbázis**: SQLite
- **ML**: XGBoost + scikit-learn
- **AI elemzés**: Zhipu AI (GLM-4-Flash)
- **Sport adat**: API-Football v3
- **Vizualizáció**: Altair

## 📝 Megjegyzések

- Az API-Football free tier 100 request/napot engedélyez. Az app intelligensen cache-el, hogy ne lépje túl a limitet.
- Az ML modell az első ~30 lezárt meccs után kezd el tanulni. Addig egy egyszerű statisztikai fallback modell fut.
- A Paper Trading virtuális — valódi pénzt nem kezel az alkalmazás.
- Ez **nem pénzügyi tanács** — kizárólag szórakoztatási és oktatási célokra készült.

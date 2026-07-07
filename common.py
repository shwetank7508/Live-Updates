"""
OptiScan Pro — Common Utilities
Shared functions used across all briefing scripts
"""
import requests
import yfinance as yf
import feedparser
from datetime import datetime, date, timedelta
import calendar
import os

# ── Credentials from environment ─────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8994608030:AAF7nFq4zWwcNMAzUw70mpp9mt3_ZUDPWrI")
CHAT_ID   = os.environ.get("CHAT_ID",   "889422959")

# ── Send Telegram ─────────────────────────────────────────────────────────────
def send(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r   = requests.post(url, json={
            "chat_id":    CHAT_ID,
            "text":       text,
            "parse_mode": "HTML"
        }, timeout=15)
        if r.status_code == 200:
            print(f"[Telegram] Message sent successfully")
            return True
        else:
            print(f"[Telegram] Failed: {r.text}")
            return False
    except Exception as e:
        print(f"[Telegram] Error: {e}")
        return False

# ── Get price ─────────────────────────────────────────────────────────────────
def get_price(symbol, name, prefix=""):
    try:
        tk   = yf.Ticker(symbol)
        h    = tk.history(period="5d", interval="1d", auto_adjust=True)
        if h.empty or len(h) < 2:
            return None
        ltp  = float(h["Close"].iloc[-1])
        prev = float(h["Close"].iloc[-2])
        yh   = float(h["High"].iloc[-1])
        yl   = float(h["Low"].iloc[-1])
        chg  = round((ltp - prev) / prev * 100, 2)
        return {
            "name":   name,
            "symbol": symbol,
            "ltp":    round(ltp, 2),
            "prev":   round(prev, 2),
            "chg":    chg,
            "yh":     round(yh, 2),
            "yl":     round(yl, 2),
            "prefix": prefix
        }
    except Exception as e:
        print(f"[Price] Error {symbol}: {e}")
        return None

# ── Format price line ─────────────────────────────────────────────────────────
def fmt(d, decimals=2):
    if not d:
        return "N/A"
    arrow = "▲" if d["chg"] >= 0 else "▼"
    ltp   = f"{d['prefix']}{d['ltp']:,.{decimals}f}"
    return f"{ltp}  {arrow} {abs(d['chg']):.2f}%"

# ── Pivot points ──────────────────────────────────────────────────────────────
def calc_pivots(high, low, close):
    P  = round((high + low + close) / 3, 2)
    R1 = round((2 * P) - low, 2)
    R2 = round(P + (high - low), 2)
    S1 = round((2 * P) - high, 2)
    S2 = round(P - (high - low), 2)
    return {"P": P, "R1": R1, "R2": R2, "S1": S1, "S2": S2}

# ── VIX verdict ───────────────────────────────────────────────────────────────
def vix_verdict(vix):
    if not vix:
        return "⚠️ VIX data unavailable"
    v = vix["ltp"]
    if v < 11:    return f"⚠️ VIX {v:.1f} — TOO LOW, premiums cheap, SKIP ratio spread"
    elif v < 15:  return f"✅ VIX {v:.1f} — EXCELLENT for ratio spread"
    elif v < 18:  return f"✅ VIX {v:.1f} — GOOD for ratio spread, normal size"
    elif v < 22:  return f"⚠️ VIX {v:.1f} — ELEVATED, reduce size by 50%"
    else:         return f"❌ VIX {v:.1f} — TOO HIGH, AVOID ratio spread today"

# ── Monthly expiry ────────────────────────────────────────────────────────────
def get_monthly_expiry(weekday=3):  # 3=Thursday, 4=Friday
    today = date.today()
    def last_weekday(y, m, wd):
        ld = calendar.monthrange(y, m)[1]
        d  = date(y, m, ld)
        while d.weekday() != wd:
            d -= timedelta(days=1)
        return d
    exp = last_weekday(today.year, today.month, weekday)
    if (exp - today).days < 0:
        nm  = today.month + 1 if today.month < 12 else 1
        ny  = today.year if today.month < 12 else today.year + 1
        exp = last_weekday(ny, nm, weekday)
    return exp

# ── Weekly expiry ─────────────────────────────────────────────────────────────
def get_weekly_expiry(weekday=3):  # 3=Thursday for Nifty, 4=Friday for Sensex
    today = date.today()
    days_ahead = weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)

# ── Expiry alert ──────────────────────────────────────────────────────────────
def expiry_alert():
    today         = date.today()
    nifty_weekly  = get_weekly_expiry(3)
    sensex_weekly = get_weekly_expiry(4)
    nifty_monthly = get_monthly_expiry(3)
    sensex_monthly= get_monthly_expiry(4)

    alerts = []

    # Check if today IS expiry
    if nifty_weekly == today:
        alerts.append("🚨 TODAY IS NIFTY WEEKLY EXPIRY — Close/adjust positions by 3:20 PM!")
    elif (nifty_weekly - today).days == 1:
        alerts.append(f"⚠️ NIFTY WEEKLY EXPIRY TOMORROW ({nifty_weekly.strftime('%d %b')})")

    if sensex_weekly == today:
        alerts.append("🚨 TODAY IS SENSEX WEEKLY EXPIRY — Close/adjust positions by 3:20 PM!")
    elif (sensex_weekly - today).days == 1:
        alerts.append(f"⚠️ SENSEX WEEKLY EXPIRY TOMORROW ({sensex_weekly.strftime('%d %b')})")

    if nifty_monthly == today:
        alerts.append("🚨 TODAY IS NIFTY MONTHLY EXPIRY!")
    if sensex_monthly == today:
        alerts.append("🚨 TODAY IS SENSEX MONTHLY EXPIRY!")

    expiry_info = f"""📅 EXPIRY TRACKER
  Nifty Weekly   : {nifty_weekly.strftime('%a %d %b')} ({(nifty_weekly-today).days}d)
  Sensex Weekly  : {sensex_weekly.strftime('%a %d %b')} ({(sensex_weekly-today).days}d)
  Nifty Monthly  : {nifty_monthly.strftime('%a %d %b')} ({(nifty_monthly-today).days}d)
  Sensex Monthly : {sensex_monthly.strftime('%a %d %b')} ({(sensex_monthly-today).days}d)"""

    return expiry_info, alerts

# ── News feed ─────────────────────────────────────────────────────────────────
POSITIVE_KW = ["rally","gain","rise","surge","up","bullish","buy","profit",
               "growth","high","record","strong","boost","positive","recover"]
NEGATIVE_KW = ["fall","drop","loss","decline","down","bearish","sell","crash",
               "slump","weak","concern","pressure","risk","fear","negative"]
CRITICAL_KW = ["rbi","fed","rate","policy","gdp","inflation","cpi","budget",
               "war","crisis","ban","sanction","default","recession"]

def get_news(max_items=12):
    feeds = [
        ("https://economictimes.indiatimes.com/markets/rss.cms",    "ET Markets"),
        ("https://www.moneycontrol.com/rss/marketreports.xml",       "Moneycontrol"),
        ("https://feeds.reuters.com/reuters/businessNews",            "Reuters"),
        ("https://www.livemint.com/rss/markets",                      "LiveMint"),
    ]
    news = []
    seen = set()

    for url, source in feeds:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:6]:
                hl = e.get("title", "").strip()[:120]
                if not hl or hl in seen:
                    continue
                seen.add(hl)
                hl_l = hl.lower()
                ps   = sum(1 for k in POSITIVE_KW if k in hl_l)
                ns   = sum(1 for k in NEGATIVE_KW if k in hl_l)
                cs   = sum(1 for k in CRITICAL_KW if k in hl_l)

                if cs >= 2:       tag = "🔴 CRITICAL"
                elif cs >= 1:     tag = "🟠 HIGH"
                elif ps > ns:     tag = "🟢 POSITIVE"
                elif ns > ps:     tag = "🔴 NEGATIVE"
                else:             tag = "⚪ NEUTRAL"

                news.append(f"  {tag} | {source}\n  {hl}")
        except Exception as e:
            print(f"[News] Error {url}: {e}")

    return news[:max_items]

# ── Pre-market analysis ───────────────────────────────────────────────────────
def pre_market_analysis(nifty, sensex, vix, crude, usdinr, btc, dow, nasdaq, sgx):
    dont_do = []
    safe_do  = []
    reasons  = []

    vix_val    = vix["ltp"]    if vix    else 15
    crude_chg  = crude["chg"]  if crude  else 0
    dollar_chg = usdinr["chg"] if usdinr else 0
    sgx_chg    = sgx["chg"]    if sgx    else 0
    dow_chg    = dow["chg"]    if dow    else 0
    nasdaq_chg = nasdaq["chg"] if nasdaq else 0
    btc_chg    = btc["chg"]    if btc    else 0

    # Determine overall global bias
    positive_signals = sum([
        sgx_chg > 0.3,
        dow_chg > 0,
        nasdaq_chg > 0,
        crude_chg < 0,
        dollar_chg < 0,
    ])
    negative_signals = sum([
        sgx_chg < -0.3,
        dow_chg < 0,
        nasdaq_chg < 0,
        crude_chg > 1.0,
        dollar_chg > 0.2,
        vix_val > 18,
    ])

    # Rules
    if sgx_chg > 0.8:
        safe_do.append("✅ Gift Nifty strong — Nifty likely to open gap up")
        dont_do.append("⛔ DO NOT short Nifty at open — Gift Nifty up {:.1f}%".format(sgx_chg))
    elif sgx_chg < -0.8:
        dont_do.append("⛔ DO NOT buy Nifty calls at open — Gift Nifty down {:.1f}%".format(abs(sgx_chg)))
        safe_do.append("✅ Wait for gap-down to stabilize before entering ratio spread")

    if crude_chg > 1.5:
        dont_do.append("⛔ DO NOT buy Oil & Gas stocks (ONGC, BPCL) — Crude up {:.1f}%".format(crude_chg))
        reasons.append("Crude oil spiking — may pressure market sentiment")
    elif crude_chg < -1.5:
        safe_do.append("✅ Oil & Gas stocks may face pressure — avoid ratio spread on ONGC/BPCL")

    if dollar_chg > 0.3:
        dont_do.append("⛔ DO NOT buy IT stocks (INFY, TCS, WIPRO) — Dollar strengthening")
        reasons.append("Strong dollar is negative for IT sector exports")
    elif dollar_chg < -0.3:
        safe_do.append("✅ IT sector may outperform — Dollar weakening is positive for IT")

    if vix_val > 18:
        dont_do.append("⛔ DO NOT enter ratio spread today — VIX too high ({:.1f})".format(vix_val))
        dont_do.append("⛔ DO NOT sell options naked — high volatility environment")
    elif vix_val < 11:
        dont_do.append("⛔ DO NOT enter ratio spread — VIX too low, premiums insufficient ({:.1f})".format(vix_val))

    if dow_chg < -1.0:
        dont_do.append("⛔ DO NOT take aggressive long positions — Dow fell {:.1f}%".format(abs(dow_chg)))
    if nasdaq_chg < -1.5:
        dont_do.append("⛔ DO NOT buy IT/Tech calls — Nasdaq fell {:.1f}%".format(abs(nasdaq_chg)))

    if positive_signals >= 4:
        safe_do.append("✅ Overall global cues POSITIVE — Nifty likely bullish today")
        safe_do.append("✅ Safe to enter ratio spread on range-bound stocks after 9:30 AM")
    elif negative_signals >= 4:
        dont_do.append("⛔ Overall global cues NEGATIVE — wait and watch before any trade")
        dont_do.append("⛔ DO NOT enter ratio spread until market stabilizes after 10 AM")
    else:
        safe_do.append("✅ Mixed global cues — wait for first 15 min candle before deciding")

    return dont_do, safe_do

# ── Range-bound stock check ───────────────────────────────────────────────────
UPCOMING_RESULTS = []  # Update this list before results season

def check_range(symbol_ns, name, days=10, max_range=3.5):
    try:
        tk      = yf.Ticker(symbol_ns)
        h       = tk.history(period="20d", interval="1d", auto_adjust=True)
        if h.empty or len(h) < days:
            return None
        recent  = h.tail(days)
        high    = float(recent["High"].max())
        low     = float(recent["Low"].min())
        close   = float(recent["Close"].iloc[-1])
        avg     = float(recent["Close"].mean())
        rng     = round((high - low) / avg * 100, 2)
        first   = float(recent["Close"].iloc[0])
        trend   = round((close - first) / first * 100, 2)
        sideways = rng < max_range and abs(trend) < 2.0
        return {
            "name":     name,
            "symbol":   symbol_ns,
            "ltp":      round(close, 2),
            "high10":   round(high, 2),
            "low10":    round(low, 2),
            "range":    rng,
            "trend":    trend,
            "sideways": sideways
        }
    except Exception as e:
        print(f"[Range] Error {symbol_ns}: {e}")
        return None

# ── Ratio spread setup ────────────────────────────────────────────────────────
def build_ratio_spread_setup(name, ltp, step=5):
    """
    Build ratio spread setup using approximate premiums.
    For exact premiums, NSE API is needed (available at 9:30 AM script).
    """
    # ATM strike
    atm = round(ltp / step) * step

    # Approximate ATM premiums based on % of price
    # These are estimates — exact values come from NSE at 9:30 AM
    atm_ce_approx = round(ltp * 0.018, 1)  # ~1.8% of price for ATM CE
    atm_pe_approx = round(ltp * 0.016, 1)  # ~1.6% of price for ATM PE

    # OTM strikes (1/3rd premium)
    sell_ce_prem = round(atm_ce_approx / 3, 1)
    sell_pe_prem = round(atm_pe_approx / 3, 1)

    # Approximate OTM strikes
    otm_ce_strike = atm + round(ltp * 0.02 / step) * step
    otm_pe_strike = atm - round(ltp * 0.02 / step) * step

    return {
        "atm":          atm,
        "buy_ce_strike": atm,
        "buy_ce_prem":  atm_ce_approx,
        "buy_pe_strike": atm,
        "buy_pe_prem":  atm_pe_approx,
        "sell_ce_strike": otm_ce_strike,
        "sell_ce_prem": sell_ce_prem,
        "sell_pe_strike": otm_pe_strike,
        "sell_pe_prem": sell_pe_prem,
        "net":          round((atm_ce_approx + atm_pe_approx) -
                              (sell_ce_prem * 3 + sell_pe_prem * 3), 1),
        "note":         "⚠️ Approximate — verify exact premiums on NSE at 9:30 AM"
    }

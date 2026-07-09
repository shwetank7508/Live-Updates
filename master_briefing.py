"""
OptiScan Pro — Master Daily Briefing
Single comprehensive message at 9:30 AM IST
Combines: Global markets + Pre-market analysis + Ratio spread with exact strikes
"""
import requests
import yfinance as yf
import feedparser
import pandas as pd
import time
import os
from datetime import datetime, date, timedelta
import calendar

# ── Credentials ───────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8994608030:AAF7nFq4zWwcNMAzUw70mpp9mt3_ZUDPWrI")
CHAT_ID   = os.environ.get("CHAT_ID",   "889422959")

# ── Telegram ──────────────────────────────────────────────────────────────────
def send(text):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=15
        )
        if r.status_code == 200:
            print("[Telegram] Sent successfully")
            return True
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
        yh   = float(h["High"].iloc[-2])   # yesterday high
        yl   = float(h["Low"].iloc[-2])    # yesterday low
        chg  = round((ltp - prev) / prev * 100, 2)
        return {
            "name": name, "ltp": round(ltp,2), "prev": round(prev,2),
            "chg": chg, "yh": round(yh,2), "yl": round(yl,2), "prefix": prefix
        }
    except Exception as e:
        print(f"[Price] Error {symbol}: {e}")
        return None

def fmt(d):
    if not d: return "N/A"
    arrow = "▲" if d["chg"] >= 0 else "▼"
    return f"{d['prefix']}{d['ltp']:,.2f}  {arrow} {abs(d['chg']):.2f}%"

# ── Pivot points ──────────────────────────────────────────────────────────────
def calc_pivots(high, low, close):
    P  = round((high + low + close) / 3, 0)
    R1 = round((2 * P) - low, 0)
    R2 = round(P + (high - low), 0)
    S1 = round((2 * P) - high, 0)
    S2 = round(P - (high - low), 0)
    return {"P": P, "R1": R1, "R2": R2, "S1": S1, "S2": S2}

# ── VIX verdict ───────────────────────────────────────────────────────────────
def vix_verdict(vix):
    if not vix: return "VIX data unavailable"
    v = vix["ltp"]
    if v < 11:   return f"⚠️ VIX {v:.1f} — TOO LOW, skip ratio spread"
    elif v < 15: return f"✅ VIX {v:.1f} — EXCELLENT for ratio spread"
    elif v < 18: return f"✅ VIX {v:.1f} — GOOD for ratio spread"
    elif v < 22: return f"⚠️ VIX {v:.1f} — HIGH, reduce size 50%"
    else:        return f"❌ VIX {v:.1f} — TOO HIGH, avoid ratio spread"

# ── Expiry info ───────────────────────────────────────────────────────────────
def get_expiry_info():
    today = date.today()

    def next_weekday(d, wd):
        days = wd - d.weekday()
        if days <= 0: days += 7
        return d + timedelta(days=days)

    def last_weekday_month(y, m, wd):
        ld = calendar.monthrange(y, m)[1]
        d  = date(y, m, ld)
        while d.weekday() != wd: d -= timedelta(days=1)
        return d

    nifty_weekly   = next_weekday(today, 3)
    sensex_weekly  = next_weekday(today, 4)
    nifty_monthly  = last_weekday_month(today.year, today.month, 3)
    sensex_monthly = last_weekday_month(today.year, today.month, 4)

    if (nifty_monthly - today).days < 0:
        nm = today.month + 1 if today.month < 12 else 1
        ny = today.year if today.month < 12 else today.year + 1
        nifty_monthly = last_weekday_month(ny, nm, 3)
    if (sensex_monthly - today).days < 0:
        nm = today.month + 1 if today.month < 12 else 1
        ny = today.year if today.month < 12 else today.year + 1
        sensex_monthly = last_weekday_month(ny, nm, 4)

    alerts = []
    if nifty_weekly  == today: alerts.append("🚨 TODAY IS NIFTY WEEKLY EXPIRY!")
    if sensex_weekly == today: alerts.append("🚨 TODAY IS SENSEX WEEKLY EXPIRY!")
    if nifty_monthly == today: alerts.append("🚨 TODAY IS NIFTY MONTHLY EXPIRY!")
    if sensex_monthly== today: alerts.append("🚨 TODAY IS SENSEX MONTHLY EXPIRY!")

    info = (
        f"  Nifty Weekly   : {nifty_weekly.strftime('%a %d %b')}  ({(nifty_weekly-today).days}d)\n"
        f"  Sensex Weekly  : {sensex_weekly.strftime('%a %d %b')} ({(sensex_weekly-today).days}d)\n"
        f"  Nifty Monthly  : {nifty_monthly.strftime('%a %d %b')}  ({(nifty_monthly-today).days}d)\n"
        f"  Sensex Monthly : {sensex_monthly.strftime('%a %d %b')} ({(sensex_monthly-today).days}d)"
    )
    return info, alerts

# ── Top movers ────────────────────────────────────────────────────────────────
def get_top_movers():
    stocks = {
        "RELIANCE":"RELIANCE.NS","TCS":"TCS.NS","INFY":"INFY.NS",
        "HDFCBANK":"HDFCBANK.NS","ICICIBANK":"ICICIBANK.NS",
        "WIPRO":"WIPRO.NS","SBIN":"SBIN.NS","AXISBANK":"AXISBANK.NS",
        "KOTAKBANK":"KOTAKBANK.NS","LT":"LT.NS","ITC":"ITC.NS",
        "TITAN":"TITAN.NS","SUNPHARMA":"SUNPHARMA.NS",
        "BHARTIARTL":"BHARTIARTL.NS","HCLTECH":"HCLTECH.NS",
        "MARUTI":"MARUTI.NS","NTPC":"NTPC.NS","ONGC":"ONGC.NS",
        "COALINDIA":"COALINDIA.NS","POWERGRID":"POWERGRID.NS",
    }
    movers = []
    for name, sym in stocks.items():
        d = get_price(sym, name)
        if d: movers.append(d)
        time.sleep(0.15)

    gainers  = sorted([m for m in movers if m["chg"] > 0], key=lambda x: x["chg"], reverse=True)[:5]
    losers   = sorted([m for m in movers if m["chg"] < 0], key=lambda x: x["chg"])[:5]
    advances = len([m for m in movers if m["chg"] > 0])
    declines = len([m for m in movers if m["chg"] < 0])
    return gainers, losers, advances, declines

# ── NSE option chain ──────────────────────────────────────────────────────────
def fetch_option_chain(symbol, is_index=False):
    try:
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://www.nseindia.com/",
            "Accept": "application/json",
        })
        s.get("https://www.nseindia.com", timeout=10)
        time.sleep(1)

        if is_index:
            url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        else:
            url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"

        r    = s.get(url, timeout=15)
        data = r.json()
        records  = data["records"]["data"]
        expiries = data["records"]["expiryDates"]
        spot     = float(data["records"]["underlyingValue"])

        # Get monthly expiry
        today = date.today()
        wd    = 4 if symbol == "SENSEX" else 3

        def last_wd(y, m, wd):
            ld = calendar.monthrange(y, m)[1]
            d  = date(y, m, ld)
            while d.weekday() != wd: d -= timedelta(days=1)
            return d

        monthly = last_wd(today.year, today.month, wd)
        if (monthly - today).days < 5:
            nm = today.month + 1 if today.month < 12 else 1
            ny = today.year if today.month < 12 else today.year + 1
            monthly = last_wd(ny, nm, wd)

        matched = None
        for exp in expiries:
            try:
                ed = datetime.strptime(exp, "%d-%b-%Y").date()
                if ed >= monthly and (ed - monthly).days <= 7:
                    matched = exp
                    break
            except: pass
        if not matched and expiries:
            matched = expiries[-1]

        rows = []
        for rec in records:
            if rec.get("expiryDate","").upper() != (matched or "").upper():
                continue
            strike = rec["strikePrice"]
            ce = rec.get("CE", {})
            pe = rec.get("PE", {})
            rows.append({
                "strike": strike,
                "ce_ltp": ce.get("lastPrice", 0),
                "ce_vol": ce.get("totalTradedVolume", 0),
                "pe_ltp": pe.get("lastPrice", 0),
                "pe_vol": pe.get("totalTradedVolume", 0),
            })

        df  = pd.DataFrame(rows).sort_values("strike").reset_index(drop=True)
        dte = (monthly - today).days
        return df, spot, matched, dte
    except Exception as e:
        print(f"[NSE] Error {symbol}: {e}")
        return None, 0, "", 0

# ── Find ratio spread ─────────────────────────────────────────────────────────
LOT_SIZES = {
    "NIFTY":75,"SENSEX":20,"RELIANCE":250,"TCS":150,"INFY":300,
    "HDFCBANK":550,"ICICIBANK":700,"WIPRO":3000,"SBIN":1500,
    "AXISBANK":1200,"KOTAKBANK":400,"LT":150,"ITC":3200,
    "POWERGRID":5400,"NTPC":5250,"COALINDIA":4200,"ONGC":4800,
    "BHARTIARTL":1880,"SUNPHARMA":700,"DRREDDY":175,"CIPLA":700,
    "HINDALCO":2750,"MARUTI":100,"TITAN":375,"BAJFINANCE":125,
}

def find_ratio_spread(df, spot, lot_size):
    if df is None or df.empty: return None
    atm_idx    = (df["strike"] - spot).abs().idxmin()
    atm_strike = int(df.loc[atm_idx, "strike"])
    atm_ce     = float(df.loc[atm_idx, "ce_ltp"])
    atm_pe     = float(df.loc[atm_idx, "pe_ltp"])
    if atm_ce <= 0 or atm_pe <= 0: return None

    ce_otm = df[df["strike"] > atm_strike].copy()
    pe_otm = df[df["strike"] < atm_strike].copy()
    if ce_otm.empty or pe_otm.empty: return None

    ce_otm["diff"] = (ce_otm["ce_ltp"] - atm_ce/3).abs()
    pe_otm["diff"] = (pe_otm["pe_ltp"] - atm_pe/3).abs()

    sell_ce_idx    = ce_otm["diff"].idxmin()
    sell_pe_idx    = pe_otm["diff"].idxmin()
    sell_ce_strike = int(ce_otm.loc[sell_ce_idx, "strike"])
    sell_pe_strike = int(pe_otm.loc[sell_pe_idx, "strike"])
    sell_ce_ltp    = float(ce_otm.loc[sell_ce_idx, "ce_ltp"])
    sell_pe_ltp    = float(pe_otm.loc[sell_pe_idx, "pe_ltp"])

    ce_ratio = sell_ce_ltp / atm_ce if atm_ce > 0 else 0
    pe_ratio = sell_pe_ltp / atm_pe if atm_pe > 0 else 0
    if not (0.20 <= ce_ratio <= 0.50 and 0.20 <= pe_ratio <= 0.50):
        return None

    deployed     = (atm_ce + atm_pe) * lot_size
    net_cost     = deployed - (sell_ce_ltp * 3 + sell_pe_ltp * 3) * lot_size
    profit_target= round(deployed * 0.005, 0)
    loss_exit    = round(deployed * 0.01, 0)

    return {
        "atm": atm_strike, "spot": round(spot,2),
        "buy_ce": atm_strike, "buy_ce_ltp": round(atm_ce,2),
        "buy_pe": atm_strike, "buy_pe_ltp": round(atm_pe,2),
        "sell_ce": sell_ce_strike, "sell_ce_ltp": round(sell_ce_ltp,2),
        "sell_pe": sell_pe_strike, "sell_pe_ltp": round(sell_pe_ltp,2),
        "net_cost": round(net_cost,0), "deployed": round(deployed,0),
        "profit_target": profit_target, "loss_exit": loss_exit,
        "lot_size": lot_size,
    }

# ── Range check ───────────────────────────────────────────────────────────────
def check_range(symbol_ns, name, days=10, max_range=3.5):
    try:
        tk      = yf.Ticker(symbol_ns)
        h       = tk.history(period="20d", interval="1d", auto_adjust=True)
        if h.empty or len(h) < days: return None
        recent  = h.tail(days)
        high    = float(recent["High"].max())
        low     = float(recent["Low"].min())
        close   = float(recent["Close"].iloc[-1])
        avg     = float(recent["Close"].mean())
        rng     = round((high-low)/avg*100, 2)
        first   = float(recent["Close"].iloc[0])
        trend   = round((close-first)/first*100, 2)
        sideways = rng < max_range and abs(trend) < 2.0
        return {"name":name,"ltp":round(close,2),"range":rng,"sideways":sideways}
    except: return None

# ── News ──────────────────────────────────────────────────────────────────────
POSITIVE_KW = ["rally","gain","rise","surge","up","bullish","profit","growth","high","record","strong","boost"]
NEGATIVE_KW = ["fall","drop","loss","decline","down","bearish","crash","slump","weak","concern","pressure"]
CRITICAL_KW = ["rbi","fed","rate","policy","gdp","inflation","cpi","budget","war","crisis","ban","recession"]

def get_news(max_items=8):
    feeds = [
        ("https://economictimes.indiatimes.com/markets/rss.cms", "ET Markets"),
        ("https://www.moneycontrol.com/rss/marketreports.xml",   "Moneycontrol"),
        ("https://feeds.reuters.com/reuters/businessNews",         "Reuters"),
    ]
    news = []
    seen = set()
    for url, source in feeds:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:5]:
                hl = e.get("title","").strip()[:100]
                if not hl or hl in seen: continue
                seen.add(hl)
                hl_l = hl.lower()
                ps   = sum(1 for k in POSITIVE_KW if k in hl_l)
                ns   = sum(1 for k in NEGATIVE_KW if k in hl_l)
                cs   = sum(1 for k in CRITICAL_KW if k in hl_l)
                tag  = "🔴 CRITICAL" if cs>=2 else "🟠 HIGH" if cs>=1 else "🟢 POSITIVE" if ps>ns else "🔴 NEGATIVE" if ns>ps else "⚪ NEUTRAL"
                news.append(f"  {tag} | {source}\n  {hl}")
        except: pass
    return news[:max_items]

# ── Pre-market analysis ───────────────────────────────────────────────────────
def pre_market_analysis(vix, crude, usdinr, sgx, dow, nasdaq):
    dont = []
    safe = []
    vix_val  = vix["ltp"]    if vix    else 15
    crude_chg= crude["chg"]  if crude  else 0
    dollar_chg=usdinr["chg"] if usdinr else 0
    sgx_chg  = sgx["chg"]   if sgx    else 0
    dow_chg  = dow["chg"]   if dow    else 0
    nas_chg  = nasdaq["chg"] if nasdaq else 0

    if sgx_chg > 0.8:
        dont.append(f"⛔ DO NOT short Nifty — Gift Nifty up {sgx_chg:.1f}%")
    elif sgx_chg < -0.8:
        dont.append(f"⛔ DO NOT buy Nifty calls — Gift Nifty down {abs(sgx_chg):.1f}%")
        safe.append("✅ Wait for gap-down to stabilize before ratio spread")

    if crude_chg > 1.5:
        dont.append(f"⛔ DO NOT buy ONGC/BPCL calls — Crude up {crude_chg:.1f}%")
    if dollar_chg > 0.3:
        dont.append("⛔ DO NOT buy IT stocks — Dollar strengthening")
    elif dollar_chg < -0.3:
        safe.append("✅ IT sector may outperform — Dollar weakening")

    if vix_val > 18:
        dont.append(f"⛔ DO NOT enter ratio spread — VIX too high ({vix_val:.1f})")
    elif vix_val < 11:
        dont.append(f"⛔ DO NOT enter ratio spread — VIX too low ({vix_val:.1f})")
    else:
        safe.append("✅ VIX in good range — ratio spread conditions OK")

    if dow_chg < -1.0:
        dont.append(f"⛔ DO NOT take aggressive longs — Dow fell {abs(dow_chg):.1f}%")
    if nas_chg < -1.5:
        dont.append(f"⛔ DO NOT buy IT/Tech calls — Nasdaq fell {abs(nas_chg):.1f}%")

    pos = sum([sgx_chg>0.3, dow_chg>0, nas_chg>0, crude_chg<0, dollar_chg<0])
    if pos >= 4:
        safe.append("✅ Global cues POSITIVE — Nifty likely bullish today")
        safe.append("✅ Safe to enter ratio spread after 9:30 AM")
    elif pos <= 1:
        dont.append("⛔ Global cues NEGATIVE — wait before any trade")

    return dont, safe

# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    now = datetime.now()
    print(f"[Master Briefing] Starting at {now.strftime('%H:%M:%S')}")

    # Fetch all data
    print("[1/8] Fetching indices...")
    nifty  = get_price("^NSEI",     "Nifty 50")
    sensex = get_price("^BSESN",    "Sensex")
    vix    = get_price("^INDIAVIX", "VIX")
    bnk    = get_price("^NSEBANK",  "BankNifty")

    print("[2/8] Fetching global markets...")
    dow    = get_price("YM=F",   "Dow Futures")
    nasdaq = get_price("NQ=F",   "Nasdaq Fut")
    sgx    = get_price("^NSEI",  "Gift Nifty")
    btc    = get_price("BTC-USD","Bitcoin",   "$")
    crude  = get_price("CL=F",   "Crude Oil", "$")
    gold   = get_price("GC=F",   "Gold",      "$")
    usdinr = get_price("INR=X",  "USD/INR",   "₹")

    print("[3/8] Calculating pivots...")
    np = calc_pivots(nifty["yh"],  nifty["yl"],  nifty["prev"])  if nifty  else None
    sp = calc_pivots(sensex["yh"], sensex["yl"], sensex["prev"]) if sensex else None

    print("[4/8] Getting expiry info...")
    expiry_info, expiry_alerts = get_expiry_info()

    print("[5/8] Getting top movers...")
    gainers, losers, advances, declines = get_top_movers()

    print("[6/8] Scanning range-bound stocks...")
    fno = {
        "ITC":"ITC.NS","POWERGRID":"POWERGRID.NS","NTPC":"NTPC.NS",
        "COALINDIA":"COALINDIA.NS","HDFCBANK":"HDFCBANK.NS",
        "INFY":"INFY.NS","WIPRO":"WIPRO.NS","SBIN":"SBIN.NS",
        "ONGC":"ONGC.NS","BHARTIARTL":"BHARTIARTL.NS",
        "TCS":"TCS.NS","RELIANCE":"RELIANCE.NS","CIPLA":"CIPLA.NS",
        "SUNPHARMA":"SUNPHARMA.NS","LT":"LT.NS",
        "AXISBANK":"AXISBANK.NS","KOTAKBANK":"KOTAKBANK.NS",
        "HINDALCO":"HINDALCO.NS","TITAN":"TITAN.NS","MARUTI":"MARUTI.NS",
    }
    range_stocks = []
    for name, sym in fno.items():
        r = check_range(sym, name)
        if r and r["sideways"]:
            range_stocks.append((name, False))
        time.sleep(0.2)

    nifty_r  = check_range("^NSEI",  "NIFTY",  max_range=1.5)
    sensex_r = check_range("^BSESN", "SENSEX", max_range=1.5)
    if nifty_r  and nifty_r["sideways"]:  range_stocks.insert(0, ("NIFTY",  True))
    if sensex_r and sensex_r["sideways"]: range_stocks.insert(1, ("SENSEX", True))

    print("[7/8] Fetching live options data...")
    opportunities = []
    for symbol, is_index in range_stocks[:10]:
        try:
            lot_size = LOT_SIZES.get(symbol, 25)
            df, spot, expiry, dte = fetch_option_chain(symbol, is_index)
            if df is None or dte < 5: continue
            setup = find_ratio_spread(df, spot, lot_size)
            if setup:
                setup["expiry"] = expiry
                setup["dte"]    = dte
                opportunities.append((symbol, is_index, setup))
                print(f"[Options] ✅ {symbol} found!")
            time.sleep(1)
        except Exception as e:
            print(f"[Options] Error {symbol}: {e}")

    print("[8/8] Fetching news...")
    news = get_news(8)

    # ── Pre-market analysis ───────────────────────────────────────────────────
    dont, safe = pre_market_analysis(vix, crude, usdinr, sgx, dow, nasdaq)

    # ── Build sections ────────────────────────────────────────────────────────

    # Expiry alerts
    ea_text = "\n".join(expiry_alerts) + "\n\n" if expiry_alerts else ""

    # Pivots
    def pivot_section(name, p, idx):
        if not p or not idx: return ""
        return (
            f"  <b>{name}</b>\n"
            f"  Yest H:{idx['yh']:,.0f} | L:{idx['yl']:,.0f} | C:{idx['prev']:,.0f}\n"
            f"  Pivot: {p['P']:,.0f} | R1:{p['R1']:,.0f} | R2:{p['R2']:,.0f}\n"
            f"  S1:{p['S1']:,.0f} | S2:{p['S2']:,.0f}"
        )

    # Gainers/Losers
    g_lines = "\n".join([f"  🟢 {g['name']:12} ▲{g['chg']:.2f}%  ₹{g['ltp']:,.2f}" for g in gainers])
    l_lines = "\n".join([f"  🔴 {l['name']:12} ▼{abs(l['chg']):.2f}%  ₹{l['ltp']:,.2f}" for l in losers])

    # A/D mood
    ad_mood = "🟢 BULLISH" if advances > declines*1.5 else "🔴 BEARISH" if declines > advances*1.5 else "🟡 MIXED"

    # Ratio spread
    if opportunities:
        opp_lines = []
        for i, (sym, is_idx, s) in enumerate(opportunities, 1):
            net = f"CREDIT ₹{abs(s['net_cost']):,.0f}" if s["net_cost"]<=0 else f"DEBIT ₹{s['net_cost']:,.0f}"
            opp_lines.append(
                f"<b>{i}. {sym}</b> | ₹{s['spot']:,.2f} | {s.get('expiry','--')} ({s.get('dte','--')}d)\n"
                f"  ▲ Buy  1 lot {s['buy_ce']:,} CE @ ₹{s['buy_ce_ltp']}\n"
                f"  ▲ Buy  1 lot {s['buy_pe']:,} PE @ ₹{s['buy_pe_ltp']}\n"
                f"  ▼ Sell 3 lots {s['sell_ce']:,} CE @ ₹{s['sell_ce_ltp']}\n"
                f"  ▼ Sell 3 lots {s['sell_pe']:,} PE @ ₹{s['sell_pe_ltp']}\n"
                f"  Net:{net} | Target:+₹{s['profit_target']:,.0f} | SL:-₹{s['loss_exit']:,.0f}"
            )
        opp_text = "\n\n".join(opp_lines)
    else:
        opp_text = "No ratio spread setups found today\nStocks may be trending — wait for better setup"

    # Pre-market
    dont_text = "\n".join(dont) if dont else "  No specific restrictions today"
    safe_text = "\n".join(safe) if safe else "  Monitor first 15 min candle"

    # News
    news_text = "\n\n".join(news) if news else "No news available"

    # ── Final message ─────────────────────────────────────────────────────────
    msg = f"""⚡ <b>OPTISCAN PRO — 9:30 AM MARKET BRIEFING</b>
📅 {now.strftime('%A, %d %b %Y')}  ⏰ {now.strftime('%I:%M %p')} IST
━━━━━━━━━━━━━━━━━━━━━━━━━━
{ea_text}🌍 <b>GLOBAL MARKETS</b>
  Dow Futures : {fmt(dow)}
  Nasdaq Fut  : {fmt(nasdaq)}
  Gift Nifty  : {fmt(sgx)}
  Bitcoin     : {fmt(btc)}
  Crude Oil   : {fmt(crude)}
  Gold        : {fmt(gold)}
  USD/INR     : {fmt(usdinr)}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>INDIAN MARKETS</b>
  Nifty 50   : {fmt(nifty)}
  Sensex     : {fmt(sensex)}
  BankNifty  : {fmt(bnk)}
  {vix_verdict(vix)}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📐 <b>SUPPORT, RESISTANCE and PIVOT</b>
{pivot_section('NIFTY', np, nifty)}

{pivot_section('SENSEX', sp, sensex)}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>ADVANCE / DECLINE</b>
  Advances : {advances} 🟢  |  Declines : {declines} 🔴  |  {ad_mood}

🚀 <b>TOP 5 GAINERS</b>
{g_lines}

📉 <b>TOP 5 LOSERS</b>
{l_lines}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🚦 <b>PRE-MARKET ANALYSIS</b>

❌ <b>WHAT NOT TO DO:</b>
{dont_text}

✅ <b>WHAT IS SAFE:</b>
{safe_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 <b>EXPIRY TRACKER</b>
{expiry_info}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>RATIO SPREAD — EXACT STRIKES (Live NSE)</b>

{opp_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📐 <b>RULES REMINDER</b>
  ✅ Target: +0.5% of deployed
  ✅ Stop Loss: -1% of deployed
  ✅ Max 1 adjustment per trade
  ✅ Roll CE up if market rises
  ✅ Roll PE down if market falls
  ❌ Never adjust after 2:30 PM
  ❌ Exit if VIX spikes above 18

━━━━━━━━━━━━━━━━━━━━━━━━━━
📰 <b>MARKET NEWS</b>
{news_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <i>Not financial advice. Trade at own risk.</i>"""

    send(msg)
    print(f"[Master Briefing] Done at {now.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    run()

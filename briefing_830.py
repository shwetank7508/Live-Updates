"""
Script 1 — 8:30 AM Full Morning Briefing
Sends complete market overview before market opens
"""
from common import *
import time

def run():
    now = datetime.now()
    print(f"[8:30 Briefing] Starting at {now.strftime('%H:%M:%S')}")

    # ── Fetch all data ────────────────────────────────────────────────────────
    print("[8:30] Fetching indices...")
    nifty  = get_price("^NSEI",     "Nifty 50")
    sensex = get_price("^BSESN",    "Sensex")
    vix    = get_price("^INDIAVIX", "India VIX")
    bnk    = get_price("^NSEBANK",  "BankNifty")

    print("[8:30] Fetching global markets...")
    dow    = get_price("YM=F",  "Dow Futures")
    nasdaq = get_price("NQ=F",  "Nasdaq Fut")
    sgx    = get_price("^NSEI", "Gift Nifty")
    btc    = get_price("BTC-USD","Bitcoin", "$")
    crude  = get_price("CL=F",  "Crude Oil", "$")
    gold   = get_price("GC=F",  "Gold",      "$")
    usdinr = get_price("INR=X", "USD/INR",   "₹")

    print("[8:30] Calculating pivots...")
    nifty_pivots  = calc_pivots(
        nifty["yh"], nifty["yl"], nifty["prev"]) if nifty else None
    sensex_pivots = calc_pivots(
        sensex["yh"], sensex["yl"], sensex["prev"]) if sensex else None

    print("[8:30] Getting expiry info...")
    expiry_info, expiry_alerts = expiry_alert()

    print("[8:30] Getting news...")
    news = get_news(12)

    print("[8:30] Pre-market analysis...")
    dont_do, safe_do = pre_market_analysis(
        nifty, sensex, vix, crude, usdinr, btc, dow, nasdaq, sgx)

    print("[8:30] Scanning range-bound stocks...")
    fno_stocks = {
        "ITC":        "ITC.NS",
        "POWERGRID":  "POWERGRID.NS",
        "NTPC":       "NTPC.NS",
        "COALINDIA":  "COALINDIA.NS",
        "HDFCBANK":   "HDFCBANK.NS",
        "INFY":       "INFY.NS",
        "WIPRO":      "WIPRO.NS",
        "SBIN":       "SBIN.NS",
        "ONGC":       "ONGC.NS",
        "BHARTIARTL": "BHARTIARTL.NS",
        "TCS":        "TCS.NS",
        "RELIANCE":   "RELIANCE.NS",
        "CIPLA":      "CIPLA.NS",
        "DRREDDY":    "DRREDDY.NS",
        "SUNPHARMA":  "SUNPHARMA.NS",
        "LT":         "LT.NS",
        "AXISBANK":   "AXISBANK.NS",
        "KOTAKBANK":  "KOTAKBANK.NS",
        "HINDALCO":   "HINDALCO.NS",
        "BAJFINANCE": "BAJFINANCE.NS",
        "TITAN":      "TITAN.NS",
        "MARUTI":     "MARUTI.NS",
    }
    # Also check indices
    index_checks = {
        "NIFTY":  ("^NSEI",  50),
        "SENSEX": ("^BSESN", 100),
    }

    candidates = []
    for name, sym in fno_stocks.items():
        if name in UPCOMING_RESULTS:
            continue
        r = check_range(sym, name)
        if r and r["sideways"]:
            candidates.append(r)
        time.sleep(0.2)

    # Check indices
    for name, (sym, step) in index_checks.items():
        r = check_range(sym, name, max_range=2.0)
        if r and r["sideways"]:
            r["is_index"] = True
            candidates.append(r)

    candidates.sort(key=lambda x: x["range"])

    # ── Build message ─────────────────────────────────────────────────────────

    # Expiry alerts
    expiry_alert_text = ""
    if expiry_alerts:
        expiry_alert_text = "\n".join(expiry_alerts) + "\n\n"

    # Pivots
    def pivot_text(name, p, idx):
        if not p or not idx:
            return ""
        return f"""  {name}
    Yesterday: H:{idx['yh']:,.0f} | L:{idx['yl']:,.0f} | C:{idx['prev']:,.0f}
    Pivot(P) : {p['P']:,.2f}
    R1:{p['R1']:,.0f}  R2:{p['R2']:,.0f}
    S1:{p['S1']:,.0f}  S2:{p['S2']:,.0f}"""

    # Ratio spread candidates
    if candidates:
        cand_lines = []
        step_map = {"NIFTY":50,"SENSEX":100,"BANKNIFTY":100}
        for c in candidates[:12]:
            q    = "🔥" if c["range"] < 2 else "✅" if c["range"] < 2.8 else "⚠️"
            step = step_map.get(c["name"], 5)
            ss   = build_ratio_spread_setup(c["name"], c["ltp"], step)
            cand_lines.append(
                f"{q} <b>{c['name']}</b> | LTP:₹{c['ltp']:,.1f} | Range:{c['range']:.1f}% (10d)\n"
                f"   Buy 1 lot {ss['buy_ce_strike']:,} CE ~₹{ss['buy_ce_prem']} | "
                f"Buy 1 lot {ss['buy_pe_strike']:,} PE ~₹{ss['buy_pe_prem']}\n"
                f"   Sell 3 lots {ss['sell_ce_strike']:,} CE ~₹{ss['sell_ce_prem']} | "
                f"Sell 3 lots {ss['sell_pe_strike']:,} PE ~₹{ss['sell_pe_prem']}\n"
                f"   Net: {'CREDIT' if ss['net'] <= 0 else 'DEBIT'} ~₹{abs(ss['net']):.0f}"
            )
        cand_text = "\n\n".join(cand_lines)
    else:
        cand_text = "No strong range-bound candidates today\nCheck again at 9:30 AM after market opens"

    # Dont do / safe do
    dont_text = "\n".join(dont_do) if dont_do else "  No specific restrictions today"
    safe_text = "\n".join(safe_do) if safe_do else "  Monitor first 15 min candle"

    # News
    news_text = "\n\n".join(news[:10]) if news else "No news fetched"

    msg = f"""⚡ <b>OPTISCAN PRO — 8:30 AM BRIEFING</b>
📅 {now.strftime('%A, %d %b %Y')}
━━━━━━━━━━━━━━━━━━━━━━━━━━
{expiry_alert_text}
🌍 <b>GLOBAL MARKETS</b>
  Dow Futures : {fmt(dow)}
  Nasdaq Fut  : {fmt(nasdaq)}
  Gift Nifty  : {fmt(sgx)}
  Bitcoin     : {fmt(btc)}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>INDIAN MARKETS (Prev Close)</b>
  Nifty 50   : {fmt(nifty)}
  Sensex     : {fmt(sensex)}
  BankNifty  : {fmt(bnk)}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🌡️ <b>KEY INDICATORS</b>
  {vix_verdict(vix)}
  Crude Oil  : {fmt(crude)}
  Gold       : {fmt(gold)}
  USD/INR    : {fmt(usdinr)}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📐 <b>SUPPORT, RESISTANCE and PIVOT</b>
{pivot_text('NIFTY', nifty_pivots, nifty)}

{pivot_text('SENSEX', sensex_pivots, sensex)}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🚦 <b>PRE-MARKET ANALYSIS</b>

❌ <b>WHAT NOT TO DO TODAY:</b>
{dont_text}

✅ <b>WHAT IS SAFE:</b>
{safe_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━
{expiry_info}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>RATIO SPREAD WATCHLIST</b>
(Premiums approximate — exact strikes at 9:30 AM)

{cand_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📰 <b>MARKET NEWS</b>
{news_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <i>Not financial advice. Premiums are approximate.
Verify exact strikes at 9:30 AM message.</i>"""

    send(msg)
    print("[8:30 Briefing] Done!")

if __name__ == "__main__":
    run()

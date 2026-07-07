"""
Script 2 — 9:10 AM Pre-Open Update
Advance/Decline, Top Gainers, Top Losers, Pre-open session data
"""
from common import *
import time

def get_nse_preopen():
    """Fetch NSE pre-open data"""
    try:
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer":    "https://www.nseindia.com/",
        })
        s.get("https://www.nseindia.com", timeout=10)
        r = s.get(
            "https://www.nseindia.com/api/market-status",
            timeout=10
        )
        return r.json()
    except:
        return None

def get_top_movers():
    """Get top gainers and losers from Nifty 50"""
    stocks = {
        "RELIANCE":"RELIANCE.NS","TCS":"TCS.NS","INFY":"INFY.NS",
        "HDFCBANK":"HDFCBANK.NS","ICICIBANK":"ICICIBANK.NS",
        "WIPRO":"WIPRO.NS","SBIN":"SBIN.NS","AXISBANK":"AXISBANK.NS",
        "KOTAKBANK":"KOTAKBANK.NS","LT":"LT.NS",
        "BAJFINANCE":"BAJFINANCE.NS","ITC":"ITC.NS",
        "TITAN":"TITAN.NS","SUNPHARMA":"SUNPHARMA.NS",
        "TATAMOTORS":"TATAMOTORS.NS","BHARTIARTL":"BHARTIARTL.NS",
        "HCLTECH":"HCLTECH.NS","MARUTI":"MARUTI.NS",
        "NTPC":"NTPC.NS","ONGC":"ONGC.NS",
        "ADANIPORTS":"ADANIPORTS.NS","TECHM":"TECHM.NS",
        "POWERGRID":"POWERGRID.NS","COALINDIA":"COALINDIA.NS",
        "DRREDDY":"DRREDDY.NS","CIPLA":"CIPLA.NS",
        "HINDALCO":"HINDALCO.NS","BPCL":"BPCL.NS",
        "TATASTEEL":"TATASTEEL.NS","BAJAJ-AUTO":"BAJAJ-AUTO.NS",
    }

    movers = []
    for name, sym in stocks.items():
        d = get_price(sym, name)
        if d:
            movers.append(d)
        time.sleep(0.15)

    gainers = sorted([m for m in movers if m["chg"] > 0],
                     key=lambda x: x["chg"], reverse=True)[:5]
    losers  = sorted([m for m in movers if m["chg"] < 0],
                     key=lambda x: x["chg"])[:5]

    # Advance/Decline count
    advances = len([m for m in movers if m["chg"] > 0])
    declines = len([m for m in movers if m["chg"] < 0])
    unchanged= len([m for m in movers if m["chg"] == 0])

    return gainers, losers, advances, declines, unchanged

def run():
    now = datetime.now()
    print(f"[9:10 Update] Starting at {now.strftime('%H:%M:%S')}")

    # Fetch data
    nifty  = get_price("^NSEI",     "Nifty 50")
    sensex = get_price("^BSESN",    "Sensex")
    vix    = get_price("^INDIAVIX", "VIX")
    sgx    = get_price("^NSEI",     "Gift Nifty")

    print("[9:10] Getting top movers...")
    gainers, losers, advances, declines, unchanged = get_top_movers()

    # Expiry alerts
    _, expiry_alerts = expiry_alert()
    expiry_alert_text = "\n".join(expiry_alerts) + "\n\n" if expiry_alerts else ""

    # Gap analysis
    gap_text = ""
    if nifty and sgx:
        gap = round(sgx["ltp"] - nifty["prev"], 2)
        gap_pct = round(gap / nifty["prev"] * 100, 2)
        if abs(gap_pct) > 0.3:
            direction = "GAP UP" if gap > 0 else "GAP DOWN"
            gap_text  = f"  Expected {direction}: {abs(gap_pct):.2f}% (~{abs(gap):.0f} pts)\n"

    # A/D ratio mood
    if advances > declines * 1.5:
        ad_mood = "🟢 BULLISH BREADTH"
    elif declines > advances * 1.5:
        ad_mood = "🔴 BEARISH BREADTH"
    else:
        ad_mood = "🟡 MIXED BREADTH"

    # Format gainers
    gainer_lines = "\n".join([
        f"  🟢 {g['name']:12} ₹{g['ltp']:>8,.2f}  ▲ {g['chg']:.2f}%"
        for g in gainers
    ]) if gainers else "  No data"

    loser_lines = "\n".join([
        f"  🔴 {l['name']:12} ₹{l['ltp']:>8,.2f}  ▼ {abs(l['chg']):.2f}%"
        for l in losers
    ]) if losers else "  No data"

    msg = f"""📊 <b>OPTISCAN PRO — 9:10 AM PRE-OPEN UPDATE</b>
📅 {now.strftime('%A, %d %b %Y')}
━━━━━━━━━━━━━━━━━━━━━━━━━━
{expiry_alert_text}
🔔 <b>MARKET OPENING IN 5 MINUTES</b>

📈 <b>INDEX SNAPSHOT</b>
  Nifty 50  : {fmt(nifty)}
  Sensex    : {fmt(sensex)}
  VIX       : {f"{vix['ltp']:.2f}" if vix else "N/A"}
  Gift Nifty: {fmt(sgx)}
{gap_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>ADVANCE / DECLINE (Nifty 50 stocks)</b>
  Advances  : {advances} stocks 🟢
  Declines  : {declines} stocks 🔴
  Unchanged : {unchanged} stocks ⚪
  A/D Ratio : {round(advances/max(declines,1), 2)} — {ad_mood}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 <b>TOP 5 GAINERS (Previous Close)</b>
{gainer_lines}

📉 <b>TOP 5 LOSERS (Previous Close)</b>
{loser_lines}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📐 <b>TRADING PLAN FOR TODAY</b>
  ✅ Wait for first 15 min candle to close (9:30 AM)
  ✅ Check if Nifty is above/below VWAP at 9:30 AM
  ✅ Enter ratio spread only after 9:30 AM
  ✅ Exact ratio spread strikes coming at 9:30 AM

━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <i>Not financial advice. Trade at own risk.</i>"""

    send(msg)
    print("[9:10 Update] Done!")

if __name__ == "__main__":
    run()

"""
Script 3 — 9:30 AM Exact Ratio Spread Strategy
Live NSE options chain — exact strikes and premiums
"""
from common import *
import pandas as pd
import time

LOT_SIZES = {
    "NIFTY":75,"SENSEX":20,"BANKNIFTY":30,
    "RELIANCE":250,"TCS":150,"INFY":300,"HDFCBANK":550,
    "ICICIBANK":700,"WIPRO":3000,"SBIN":1500,"AXISBANK":1200,
    "KOTAKBANK":400,"LT":150,"BAJFINANCE":125,"ITC":3200,
    "TITAN":375,"SUNPHARMA":700,"NTPC":5250,"ONGC":4800,
    "COALINDIA":4200,"BHARTIARTL":1880,"POWERGRID":5400,
    "DRREDDY":175,"CIPLA":700,"HINDALCO":2750,"MARUTI":100,
}

def fetch_nse_option_chain(symbol, is_index=False):
    """Fetch live option chain from NSE"""
    try:
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer":    "https://www.nseindia.com/",
            "Accept":     "application/json",
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

        # Get nearest monthly expiry
        monthly_exp = get_monthly_expiry(3 if symbol != "SENSEX" else 4)
        today       = date.today()

        matched = None
        for exp in expiries:
            try:
                ed = datetime.strptime(exp, "%d-%b-%Y").date()
                if ed >= monthly_exp and (ed - monthly_exp).days <= 7:
                    matched = exp
                    break
            except:
                pass
        if not matched and expiries:
            matched = expiries[-1]

        rows = []
        for rec in records:
            if rec.get("expiryDate","").upper() != (matched or "").upper():
                continue
            strike = rec["strikePrice"]
            ce     = rec.get("CE", {})
            pe     = rec.get("PE", {})
            rows.append({
                "strike":   strike,
                "ce_ltp":   ce.get("lastPrice", 0),
                "ce_oi":    ce.get("openInterest", 0),
                "ce_vol":   ce.get("totalTradedVolume", 0),
                "pe_ltp":   pe.get("lastPrice", 0),
                "pe_oi":    pe.get("openInterest", 0),
                "pe_vol":   pe.get("totalTradedVolume", 0),
            })

        df = pd.DataFrame(rows).sort_values("strike").reset_index(drop=True)
        dte = (monthly_exp - today).days

        return df, spot, matched, dte
    except Exception as e:
        print(f"[NSE] Error {symbol}: {e}")
        return None, 0, "", 0

def find_ratio_spread(df, spot, lot_size, symbol):
    """Find exact 1x3 ratio spread setup"""
    if df is None or df.empty:
        return None

    # ATM strike
    atm_idx    = (df["strike"] - spot).abs().idxmin()
    atm_strike = int(df.loc[atm_idx, "strike"])
    atm_ce_ltp = float(df.loc[atm_idx, "ce_ltp"])
    atm_pe_ltp = float(df.loc[atm_idx, "pe_ltp"])

    if atm_ce_ltp <= 0 or atm_pe_ltp <= 0:
        return None

    # Target sell premiums
    target_ce = atm_ce_ltp / 3
    target_pe = atm_pe_ltp / 3

    # Find OTM strikes
    ce_otm = df[df["strike"] > atm_strike].copy()
    pe_otm = df[df["strike"] < atm_strike].copy()

    if ce_otm.empty or pe_otm.empty:
        return None

    ce_otm["diff"] = (ce_otm["ce_ltp"] - target_ce).abs()
    pe_otm["diff"] = (pe_otm["pe_ltp"] - target_pe).abs()

    sell_ce_idx    = ce_otm["diff"].idxmin()
    sell_pe_idx    = pe_otm["diff"].idxmin()
    sell_ce_strike = int(ce_otm.loc[sell_ce_idx, "strike"])
    sell_pe_strike = int(pe_otm.loc[sell_pe_idx, "strike"])
    sell_ce_ltp    = float(ce_otm.loc[sell_ce_idx, "ce_ltp"])
    sell_pe_ltp    = float(pe_otm.loc[sell_pe_idx, "pe_ltp"])

    # Validate ratio
    ce_ratio = sell_ce_ltp / atm_ce_ltp
    pe_ratio = sell_pe_ltp / atm_pe_ltp

    if not (0.20 <= ce_ratio <= 0.50 and 0.20 <= pe_ratio <= 0.50):
        return None

    # Liquidity check
    if ce_otm.loc[sell_ce_idx, "ce_vol"] < 100:
        return None
    if pe_otm.loc[sell_pe_idx, "pe_vol"] < 100:
        return None

    # Economics
    deployed     = (atm_ce_ltp + atm_pe_ltp) * lot_size
    sell_recv    = (sell_ce_ltp * 3 + sell_pe_ltp * 3) * lot_size
    net_cost     = (atm_ce_ltp + atm_pe_ltp) * lot_size - sell_recv
    profit_1pct  = round(deployed * 0.01, 0)
    loss_1pct    = round(deployed * 0.01, 0)
    profit_05pct = round(deployed * 0.005, 0)

    return {
        "atm":           atm_strike,
        "spot":          round(spot, 2),
        "buy_ce":        atm_strike,
        "buy_ce_ltp":    round(atm_ce_ltp, 2),
        "buy_pe":        atm_strike,
        "buy_pe_ltp":    round(atm_pe_ltp, 2),
        "sell_ce":       sell_ce_strike,
        "sell_ce_ltp":   round(sell_ce_ltp, 2),
        "sell_pe":       sell_pe_strike,
        "sell_pe_ltp":   round(sell_pe_ltp, 2),
        "net_cost":      round(net_cost, 0),
        "deployed":      round(deployed, 0),
        "profit_target": profit_05pct,
        "loss_exit":     loss_1pct,
        "lot_size":      lot_size,
        "symbol":        symbol,
    }

def run():
    now = datetime.now()
    print(f"[9:30 Ratio Spread] Starting at {now.strftime('%H:%M:%S')}")

    # Check market is open
    nifty  = get_price("^NSEI",     "Nifty 50")
    sensex = get_price("^BSESN",    "Sensex")
    vix    = get_price("^INDIAVIX", "VIX")

    # Expiry alerts
    _, expiry_alerts = expiry_alert()
    expiry_alert_text = "\n".join(expiry_alerts) + "\n\n" if expiry_alerts else ""

    # Scan range-bound stocks first
    print("[9:30] Scanning range-bound stocks...")
    fno_stocks = {
        "ITC":"ITC.NS","POWERGRID":"POWERGRID.NS","NTPC":"NTPC.NS",
        "COALINDIA":"COALINDIA.NS","HDFCBANK":"HDFCBANK.NS",
        "INFY":"INFY.NS","WIPRO":"WIPRO.NS","SBIN":"SBIN.NS",
        "ONGC":"ONGC.NS","BHARTIARTL":"BHARTIARTL.NS",
        "TCS":"TCS.NS","RELIANCE":"RELIANCE.NS","CIPLA":"CIPLA.NS",
        "DRREDDY":"DRREDDY.NS","SUNPHARMA":"SUNPHARMA.NS",
        "LT":"LT.NS","AXISBANK":"AXISBANK.NS","KOTAKBANK":"KOTAKBANK.NS",
        "HINDALCO":"HINDALCO.NS","BAJFINANCE":"BAJFINANCE.NS",
        "TITAN":"TITAN.NS","MARUTI":"MARUTI.NS",
    }

    range_candidates = []
    for name, sym in fno_stocks.items():
        if name in UPCOMING_RESULTS:
            continue
        r = check_range(sym, name)
        if r and r["sideways"]:
            range_candidates.append((name, False))
        time.sleep(0.2)

    # Always check indices
    nifty_range  = check_range("^NSEI",  "NIFTY",  max_range=1.5)
    sensex_range = check_range("^BSESN", "SENSEX", max_range=1.5)
    if nifty_range  and nifty_range["sideways"]:
        range_candidates.insert(0, ("NIFTY",  True))
    if sensex_range and sensex_range["sideways"]:
        range_candidates.insert(1, ("SENSEX", True))

    # Now fetch live option chains for top candidates
    print("[9:30] Fetching live options data from NSE...")
    opportunities = []

    for symbol, is_index in range_candidates[:12]:
        try:
            lot_size = LOT_SIZES.get(symbol, 25)
            df, spot, expiry, dte = fetch_nse_option_chain(symbol, is_index)

            if df is None or dte < 5:
                continue

            setup = find_ratio_spread(df, spot, lot_size, symbol)
            if setup:
                setup["expiry"] = expiry
                setup["dte"]    = dte
                opportunities.append((symbol, is_index, setup))
                print(f"[9:30] ✅ {symbol} — ratio spread found!")
            time.sleep(1)
        except Exception as e:
            print(f"[9:30] Error {symbol}: {e}")
            continue

    # Build message
    if opportunities:
        opp_lines = []
        for i, (symbol, is_index, s) in enumerate(opportunities, 1):
            net_str = f"CREDIT ₹{abs(s['net_cost']):,.0f}" if s["net_cost"] <= 0 else f"DEBIT ₹{s['net_cost']:,.0f}"
            opp_lines.append(f"""
<b>{i}. {symbol}</b> {'(Index)' if is_index else '(Stock)'} | LTP: ₹{s['spot']:,.2f}
   Expiry: {s.get('expiry','--')} ({s.get('dte','--')} days)

   BUY LEGS:
   ▲ Buy  1 lot  {s['buy_ce']:,} CE @ ₹{s['buy_ce_ltp']}
   ▲ Buy  1 lot  {s['buy_pe']:,} PE @ ₹{s['buy_pe_ltp']}

   SELL LEGS:
   ▼ Sell 3 lots {s['sell_ce']:,} CE @ ₹{s['sell_ce_ltp']}
   ▼ Sell 3 lots {s['sell_pe']:,} PE @ ₹{s['sell_pe_ltp']}

   Net      : {net_str}
   Deployed : ₹{s['deployed']:,.0f}
   Target   : +₹{s['profit_target']:,.0f} (0.5%)
   Stop Loss: -₹{s['loss_exit']:,.0f} (1%)
   Lot Size : {s['lot_size']} units""")

        opp_text = "\n".join(opp_lines)
    else:
        opp_text = """No ratio spread opportunities found right now.
Possible reasons:
  • Stocks moved too much at open — not range-bound
  • VIX too high or too low
  • No liquid options available
  • Try again at 10:00 AM update"""

    vix_text = vix_verdict(vix) if vix else "VIX data unavailable"

    msg = f"""🎯 <b>OPTISCAN PRO — 9:30 AM RATIO SPREAD STRATEGY</b>
📅 {now.strftime('%A, %d %b %Y')} | ⏰ {now.strftime('%I:%M %p')}
━━━━━━━━━━━━━━━━━━━━━━━━━━
{expiry_alert_text}
📊 <b>MARKET STATUS</b>
  Nifty 50 : {fmt(nifty)}
  Sensex   : {fmt(sensex)}
  {vix_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>EXACT RATIO SPREAD SETUPS</b>
(Live NSE premiums — verified at {now.strftime('%I:%M %p')})

{opp_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📐 <b>RULES REMINDER</b>
  ✅ Target: +0.5% of deployed capital
  ✅ Stop Loss: -1% of deployed capital
  ✅ Max 1 adjustment per trade
  ✅ Exit by 3:00 PM for intraday
  ✅ Roll CE up if market rises
  ✅ Roll PE down if market falls
  ❌ Never adjust after 2:30 PM
  ❌ Exit immediately if VIX spikes above 18

━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <i>Live premiums. Trade at own risk.</i>"""

    send(msg)
    print("[9:30 Ratio Spread] Done!")

if __name__ == "__main__":
    run()

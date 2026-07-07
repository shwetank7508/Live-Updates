"""
Script 4 — Every 15 Minutes Market Update
Nifty/Sensex: VWAP, EMA, RSI, Support/Resistance
Ratio spread status update
Runs: 9:45 AM to 3:30 PM every 15 minutes
"""
from common import *
import numpy as np
import time

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains  = [d for d in deltas if d > 0]
    losses = [abs(d) for d in deltas if d < 0]
    if not losses:
        return 100
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 1)

def calc_ema(closes, period):
    if len(closes) < period:
        return closes[-1]
    k   = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for c in closes[period:]:
        ema = c * k + ema * (1 - k)
    return round(ema, 2)

def calc_vwap(highs, lows, closes, volumes):
    tp     = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    cum_tv = sum(t * v for t, v in zip(tp, volumes))
    cum_v  = sum(volumes)
    return round(cum_tv / cum_v, 2) if cum_v > 0 else closes[-1]

def get_intraday_data(symbol):
    """Get 15-min candle data"""
    try:
        tk  = yf.Ticker(symbol)
        h   = tk.history(period="1d", interval="15m", auto_adjust=True)
        if h.empty or len(h) < 5:
            return None
        closes  = [float(x) for x in h["Close"]]
        highs   = [float(x) for x in h["High"]]
        lows    = [float(x) for x in h["Low"]]
        volumes = [float(x) for x in h["Volume"]]

        ltp     = closes[-1]
        rsi     = calc_rsi(closes)
        ema20   = calc_ema(closes, 20)
        ema9    = calc_ema(closes, 9)
        vwap    = calc_vwap(highs, lows, closes, volumes)

        # Candle pattern (last candle)
        op   = float(h["Open"].iloc[-1])
        hi   = float(h["High"].iloc[-1])
        lo   = float(h["Low"].iloc[-1])
        cl   = float(h["Close"].iloc[-1])
        body = abs(cl - op)
        wick = hi - lo

        pattern = ""
        if body < wick * 0.1:
            pattern = "🕯️ Doji (indecision)"
        elif cl > op and body > wick * 0.6:
            pattern = "🟢 Strong Bullish candle"
        elif cl < op and body > wick * 0.6:
            pattern = "🔴 Strong Bearish candle"
        elif cl > op:
            pattern = "🟢 Bullish candle"
        else:
            pattern = "🔴 Bearish candle"

        return {
            "ltp":     round(ltp, 2),
            "rsi":     rsi,
            "ema9":    ema9,
            "ema20":   ema20,
            "vwap":    vwap,
            "hi":      round(hi, 2),
            "lo":      round(lo, 2),
            "op":      round(op, 2),
            "pattern": pattern,
        }
    except Exception as e:
        print(f"[Intraday] Error {symbol}: {e}")
        return None

def analyze(name, d, pivots):
    """Generate market analysis text"""
    if not d:
        return f"{name}: Data unavailable"

    ltp   = d["ltp"]
    lines = []

    # VWAP
    if ltp > d["vwap"]:
        lines.append(f"  VWAP    : ₹{d['vwap']:,.0f} — Price ABOVE ✅ (Bullish)")
    else:
        lines.append(f"  VWAP    : ₹{d['vwap']:,.0f} — Price BELOW ❌ (Bearish)")

    # EMA
    if ltp > d["ema20"]:
        lines.append(f"  EMA 20  : ₹{d['ema20']:,.0f} — Price ABOVE ✅")
    else:
        lines.append(f"  EMA 20  : ₹{d['ema20']:,.0f} — Price BELOW ❌")

    # RSI
    rsi = d["rsi"]
    if rsi >= 70:
        rsi_txt = f"🔴 {rsi} OVERBOUGHT — caution on buys"
    elif rsi <= 30:
        rsi_txt = f"🟢 {rsi} OVERSOLD — watch for bounce"
    elif rsi >= 55:
        rsi_txt = f"🟢 {rsi} Bullish momentum"
    elif rsi <= 45:
        rsi_txt = f"🔴 {rsi} Bearish momentum"
    else:
        rsi_txt = f"🟡 {rsi} Neutral"
    lines.append(f"  RSI(14) : {rsi_txt}")

    # Support/Resistance
    if pivots:
        if ltp >= pivots["R1"]:
            zone = f"Near R1 ({pivots['R1']:,.0f}) — resistance zone"
        elif ltp >= pivots["P"]:
            zone = f"Between Pivot ({pivots['P']:,.0f}) and R1 ({pivots['R1']:,.0f})"
        elif ltp >= pivots["S1"]:
            zone = f"Between S1 ({pivots['S1']:,.0f}) and Pivot ({pivots['P']:,.0f})"
        else:
            zone = f"Below S1 ({pivots['S1']:,.0f}) — support zone"
        lines.append(f"  Zone    : {zone}")

    # Pattern
    lines.append(f"  Candle  : {d['pattern']}")

    # Bias
    bullish_signals = sum([
        ltp > d["vwap"],
        ltp > d["ema20"],
        rsi > 50,
    ])
    if bullish_signals == 3:
        bias = "🟢 BULLISH — all signals aligned"
    elif bullish_signals == 2:
        bias = "🟡 MILD BULLISH"
    elif bullish_signals == 1:
        bias = "🟡 MILD BEARISH"
    else:
        bias = "🔴 BEARISH — all signals weak"
    lines.append(f"  Bias    : {bias}")

    return "\n".join(lines)

def check_ratio_spread_status():
    """Quick check of top ratio spread candidates"""
    quick_stocks = {
        "ITC":"ITC.NS","POWERGRID":"POWERGRID.NS",
        "NTPC":"NTPC.NS","COALINDIA":"COALINDIA.NS",
        "WIPRO":"WIPRO.NS","ONGC":"ONGC.NS",
    }
    status = []
    for name, sym in quick_stocks.items():
        r = check_range(sym, name, days=5, max_range=3.0)
        if r:
            if r["sideways"]:
                status.append(f"  ✅ {name:12} ₹{r['ltp']:>8,.1f} — Still in range ({r['range']:.1f}%) — HOLD/ENTER")
            else:
                status.append(f"  ⚠️ {name:12} ₹{r['ltp']:>8,.1f} — Range broken ({r['range']:.1f}%) — AVOID")
        time.sleep(0.1)
    return status

def run():
    now = datetime.now()
    hour = now.hour
    minute = now.minute

    # Only run during market hours
    if hour < 9 or (hour == 9 and minute < 45) or hour >= 15 or (hour == 15 and minute > 30):
        print(f"[15min] Outside market hours — skipping")
        return

    print(f"[15min Update] Starting at {now.strftime('%H:%M:%S')}")

    # Get intraday data
    nifty_d  = get_intraday_data("^NSEI")
    sensex_d = get_intraday_data("^BSESN")
    vix      = get_price("^INDIAVIX", "VIX")

    # Get pivots from previous day
    nifty_p  = get_price("^NSEI",  "Nifty")
    sensex_p = get_price("^BSESN", "Sensex")
    nifty_pivots  = calc_pivots(nifty_p["yh"],  nifty_p["yl"],  nifty_p["prev"])  if nifty_p  else None
    sensex_pivots = calc_pivots(sensex_p["yh"], sensex_p["yl"], sensex_p["prev"]) if sensex_p else None

    # Analysis
    nifty_analysis  = analyze("NIFTY",  nifty_d,  nifty_pivots)
    sensex_analysis = analyze("SENSEX", sensex_d, sensex_pivots)

    # Ratio spread status
    rs_status = check_ratio_spread_status()
    rs_text   = "\n".join(rs_status) if rs_status else "  No data available"

    # VIX
    vix_text = vix_verdict(vix) if vix else "VIX unavailable"

    # Expiry alert
    _, expiry_alerts = expiry_alert()
    expiry_text = "\n".join(expiry_alerts) + "\n" if expiry_alerts else ""

    nifty_ltp  = f"₹{nifty_d['ltp']:,.2f}"  if nifty_d  else "--"
    sensex_ltp = f"₹{sensex_d['ltp']:,.2f}" if sensex_d else "--"

    msg = f"""⚡ <b>OPTISCAN PRO — {now.strftime('%I:%M %p')} UPDATE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━
{expiry_text}
📈 <b>NIFTY 50</b> — {nifty_ltp}
{nifty_analysis}

📊 <b>SENSEX</b> — {sensex_ltp}
{sensex_analysis}

🌡️ {vix_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>RATIO SPREAD STATUS</b>
{rs_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <i>Not financial advice. Trade at own risk.</i>"""

    send(msg)
    print(f"[15min Update] Done at {now.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    run()

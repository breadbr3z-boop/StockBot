import requests, pandas as pd, numpy as np, time
from datetime import datetime

# ================= CONFIG =================
WATCHLIST = ["QQQ", "LMT", "NVDA", "AAPL", "TSLA"]
TIMEFRAMES = {"trend":"1Hour", "structure":"15Min", "entry":"5Min"}
RR = 2
MIN_SCORE = 80
MAX_TRADES_PER_TICKER = 3  # prevents overtrading

ALPACA_KEY = "YOUR_ALPACA_KEY"
ALPACA_SECRET = "YOUR_ALPACA_SECRET"
BASE = "https://data.alpaca.markets/v2"

TG_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TG_CHAT = "YOUR_TELEGRAM_CHAT_ID"
# =========================================

# Track daily trades per ticker
daily_trades = {ticker: 0 for ticker in WATCHLIST}

def tg(msg):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                  data={"chat_id":TG_CHAT,"text":msg})

def get_bars(sym, tf, limit=200):
    headers = {"APCA-API-KEY-ID":ALPACA_KEY,"APCA-API-SECRET-KEY":ALPACA_SECRET}
    r = requests.get(f"{BASE}/stocks/{sym}/bars?timeframe={tf}&limit={limit}", headers=headers).json()
    return pd.DataFrame(r["bars"])

def ema(series, period):
    return series.ewm(span=period).mean()

def vwap(df):
    return (df['c']*df['v']).cumsum()/df['v'].cumsum()

def atr(df, period=14):
    tr = np.maximum(df['h']-df['l'],
                    np.maximum(abs(df['h']-df['c'].shift()),
                               abs(df['l']-df['c'].shift())))
    return tr.rolling(period).mean()

def score_setup(df):
    score = 0
    if df['ema9'].iloc[-1] > df['ema20'].iloc[-1] > df['ema50'].iloc[-1]: score += 25
    if df['c'].iloc[-1] > df['vwap'].iloc[-1]: score += 20
    if df['v'].iloc[-1] > df['v'].mean(): score += 15
    if abs(df['c'].iloc[-1]-df['ema20'].iloc[-1]) < df['atr'].iloc[-1]*0.3: score += 15
    if df['atr'].iloc[-1] > df['atr'].mean()*0.8: score += 10
    score += 15  # placeholder for news alignment
    return score

def generate_signal(sym):
    df1 = get_bars(sym,TIMEFRAMES["trend"])
    df2 = get_bars(sym,TIMEFRAMES["structure"])
    df3 = get_bars(sym,TIMEFRAMES["entry"])

    for df in [df1, df2, df3]:
        df['ema9'] = ema(df['c'],9)
        df['ema20'] = ema(df['c'],20)
        df['ema50'] = ema(df['c'],50)
        df['vwap'] = vwap(df)
        df['atr'] = atr(df)

    # Check trend alignment (1H)
    if not (df1['ema9'].iloc[-1] > df1['ema20'].iloc[-1]):
        return None

    # Score entry (5M)
    score = score_setup(df3)
    if score < MIN_SCORE:
        return None

    entry = df3['c'].iloc[-1]
    sl = df3['l'].iloc[-5:].min()
    risk = entry - sl
    tp = entry + (risk * RR)

    return entry, sl, tp, score

# ================= LOOP =================
while True:
    now = datetime.utcnow()
    ny_hour = now.hour - 5  # convert UTC to NY time
    if 9 <= ny_hour <= 16:  # NY trading session
        for ticker in WATCHLIST:
            if daily_trades[ticker] >= MAX_TRADES_PER_TICKER:
                continue
            try:
                sig = generate_signal(ticker)
                if sig:
                    e, sl, tp, sc = sig
                    msg = (f"📈 LONG – {ticker}\nScore: {sc}/100\nEntry: {e:.2f}\n"
                           f"Stop: {sl:.2f}\nTP: {tp:.2f} (2R)")
                    tg(msg)
                    daily_trades[ticker] += 1
            except Exception as ex:
                print(f"Error {ticker}: {ex}")
    else:
        # Reset daily trade counters at midnight NY time
        if ny_hour == 0:
            daily_trades = {ticker: 0 for ticker in WATCHLIST}

    time.sleep(60) schedule

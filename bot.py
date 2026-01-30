import os
import time
import requests
import pandas as pd
from datetime import datetime, time as dt_time

# ===== ENV VARIABLES =====
ALPACA_KEY = os.getenv("ALPACA_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT = os.getenv("TG_CHAT")

# ===== SETTINGS =====
SYMBOLS = ["QQQ", "NVDA", "AAPL", "TSLA", "LMT"]
TIMEFRAME = "5Min"
TP_RATIO = 2
SL_RATIO = 1

BASE_URL = "https://data.alpaca.markets/v2/stocks"

# ===== FUNCTIONS =====

def is_market_open():
    """Checks if the current time is between 9:30 AM and 4:00 PM."""
    now = datetime.now().time()
    start_time = dt_time(9, 30)
    end_time = dt_time(16, 0)
    return start_time <= now <= end_time

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT,
        "text": message
    }
    requests.post(url, json=payload)


def get_bars(symbol):
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET
    }

    params = {
        "timeframe": TIMEFRAME,
        "limit": 50
    }

    r = requests.get(f"{BASE_URL}/{symbol}/bars", headers=headers, params=params)
    data = r.json()

    if "bars" not in data:
        return None

    return pd.DataFrame(data["bars"])


def check_signal(symbol):
    df = get_bars(symbol)
    if df is None or len(df) < 20:
        return

    df["sma20"] = df["c"].rolling(20).mean()
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if prev["c"] < prev["sma20"] and last["c"] > last["sma20"]:
        entry = round(last["c"], 2)
        sl = round(entry - (entry * 0.005), 2)
        tp = round(entry + (entry - sl) * TP_RATIO, 2)

        message = (
            f"📈 BUY SIGNAL: {symbol}\n"
            f"Entry: {entry}\n"
            f"TP: {tp}\n"
            f"SL: {sl}\n"
            f"Time: {datetime.utcnow()} UTC"
        )

        send_telegram(message)


# ===== START =====
send_telegram("✅ Stock signal bot started")

while True:
    if is_market_open():
        for sym in SYMBOLS:
            try:
                check_signal(sym)
            except Exception as e:
                print(f"Error on {sym}: {e}")
    else:
        print(f"Market closed. Current time: {datetime.now().strftime('%H:%M:%S')}")

    time.sleep(300)

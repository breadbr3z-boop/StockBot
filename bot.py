import os
import time
import requests
import pandas as pd
from datetime import datetime

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
    for sym in SYMBOLS:
        try:
            check_signal(sym)
        except Exception as e:
            print(f"Error on {sym}: {e}")

    time.sleep(300)

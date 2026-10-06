import requests
from datetime import datetime, timezone

# Get Ethereum price from Kraken
ticker_url = "https://api.kraken.com/0/public/Ticker?pair=ETHUSD"
ticker = requests.get(ticker_url, timeout=10).json()

if ticker.get("error"):
    raise Exception(f"Kraken error: {ticker['error']}")

pair_data = list(ticker["result"].values())[0]
price = float(pair_data["c"][0])

# Get recent 5-minute candles
ohlc_url = "https://api.kraken.com/0/public/OHLC"
response = requests.get(
    ohlc_url,
    params={
        "pair": "ETHUSD",
        "interval": 5
    },
    timeout=10
)

ohlc = response.json()

if ohlc.get("error"):
    raise Exception(f"Kraken error: {ohlc['error']}")

candles = list(ohlc["result"].values())[0]

# Remove the current unfinished candle
candles = candles[:-1]

if len(candles) < 12:
    raise Exception("Not enough candle data")

closes = [float(candle[4]) for candle in candles[-12:]]

# Short-term momentum: last 10 minutes
short_change = (closes[-1] / closes[-3] - 1) * 100

# Longer momentum: roughly 1 hour
long_change = (closes[-1] / closes[0] - 1) * 100

score = 0

if short_change > 0:
    score += 1
else:
    score -= 1

if long_change > 0:
    score += 1
else:
    score -= 1

if score >= 2:
    prediction = "UP"
    confidence = 65
elif score <= -2:
    prediction = "DOWN"
    confidence = 65
else:
    prediction = "SKIP"
    confidence = 50

print("")
print("================================")
print("       ETH 15-MIN SIGNAL")
print("================================")
print(f"ETH PRICE: ${price:,.2f}")
print(f"5-MIN MOMENTUM: {short_change:.3f}%")
print(f"1-HOUR MOMENTUM: {long_change:.3f}%")
print(f"PREDICTION: {prediction}")
print(f"CONFIDENCE: {confidence}%")
print(f"TIME: {datetime.now(timezone.utc).isoformat()}")
print("================================")

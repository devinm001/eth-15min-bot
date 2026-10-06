import requests
from datetime import datetime, timezone

# Get current Ethereum price
data = requests.get(
    "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT"
).json()

price = float(data["price"])

# Get recent 5-minute candles
candles = requests.get(
    "https://api.binance.com/api/v3/klines",
    params={
        "symbol": "ETHUSDT",
        "interval": "5m",
        "limit": 12
    }
).json()

closes = [float(c[4]) for c in candles]

# Simple momentum calculation
short_change = (closes[-1] / closes[-3] - 1) * 100
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
elif score <= -2:
    prediction = "DOWN"
else:
    prediction = "SKIP"

print("ETH 15-MIN SIGNAL")
print("------------------")
print(f"ETH: ${price:,.2f}")
print(f"5m momentum: {short_change:.3f}%")
print(f"1h momentum: {long_change:.3f}%")
print(f"Prediction: {prediction}")
print(f"Time: {datetime.now(timezone.utc).isoformat()}")

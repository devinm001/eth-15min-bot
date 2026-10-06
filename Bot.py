import requests
from datetime import datetime, timezone

BASE = "https://api.elections.kalshi.com/trade-api/v2"

def get_json(url, params=None):
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

# --------------------------------------------------
# 1. Find the active ETH 15-minute market
# --------------------------------------------------

data = get_json(
    BASE + "/markets",
    {
        "status": "open",
        "limit": 100
    }
)

markets = data.get("markets", [])

eth_markets = []

for m in markets:
    text = (
        str(m.get("ticker", "")) + " " +
        str(m.get("title", "")) + " " +
        str(m.get("subtitle", ""))
    ).lower()

    if "eth" in text and "15" in text:
        eth_markets.append(m)

if not eth_markets:
    raise Exception("Could not find an open ETH 15-minute Kalshi market.")

# Pick the market with the nearest expiration
eth_markets.sort(
    key=lambda x: x.get("close_time", "")
)

market = eth_markets[0]

ticker = market["ticker"]

# --------------------------------------------------
# 2. Read the market information
# --------------------------------------------------

yes_bid = market.get("yes_bid")
yes_ask = market.get("yes_ask")
no_bid = market.get("no_bid")
no_ask = market.get("no_ask")

last_price = market.get("last_price")

close_time = market.get("close_time")

# --------------------------------------------------
# 3. Get the current ETH price from Kraken
# --------------------------------------------------

kraken = get_json(
    "https://api.kraken.com/0/public/Ticker",
    {"pair": "ETHUSD"}
)

if kraken.get("error"):
    raise Exception(str(kraken["error"]))

pair_data = list(kraken["result"].values())[0]

eth_price = float(pair_data["c"][0])

# --------------------------------------------------
# 4. Get recent ETH candles
# --------------------------------------------------

ohlc = get_json(
    "https://api.kraken.com/0/public/OHLC",
    {
        "pair": "ETHUSD",
        "interval": 1
    }
)

if ohlc.get("error"):
    raise Exception(str(ohlc["error"]))

candles = list(ohlc["result"].values())[0]

# Remove unfinished candle
candles = candles[:-1]

if len(candles) < 60:
    raise Exception("Not enough ETH price history.")

closes = [float(x[4]) for x in candles]

# --------------------------------------------------
# 5. Momentum measurements
# --------------------------------------------------

price_1m = closes[-1]
price_5m = closes[-5]
price_15m = closes[-15]
price_60m = closes[-60]

mom_1m = (price_1m / price_1m - 1) * 100
mom_5m = (price_1m / price_5m - 1) * 100
mom_15m = (price_1m / price_15m - 1) * 100
mom_60m = (price_1m / price_60m - 1) * 100

# --------------------------------------------------
# 6. Volatility
# --------------------------------------------------

recent = closes[-15:]

high = max(recent)
low = min(recent)

volatility = (high - low) / price_1m * 100

# --------------------------------------------------
# 7. Score the direction
# --------------------------------------------------

score = 0

if mom_5m > 0.02:
    score += 1
elif mom_5m < -0.02:
    score -= 1

if mom_15m > 0.04:
    score += 1
elif mom_15m < -0.04:
    score -= 1

if mom_60m > 0.10:
    score += 1
elif mom_60m < -0.10:
    score -= 1

# --------------------------------------------------
# 8. Convert score to signal
# --------------------------------------------------

if score >= 3:
    prediction = "UP"
    confidence = 70

elif score == 2:
    prediction = "UP"
    confidence = 62

elif score <= -3:
    prediction = "DOWN"
    confidence = 70

elif score == -2:
    prediction = "DOWN"
    confidence = 62

else:
    prediction = "SKIP"
    confidence = 50

# --------------------------------------------------
# 9. Display everything
# --------------------------------------------------

print("")
print("======================================")
print("       ETH 15-MIN KALSHI SIGNAL")
print("======================================")

print(f"MARKET: {ticker}")

print(f"ETH PRICE: ${eth_price:,.2f}")

print("")
print(f"5-MIN MOMENTUM:  {mom_5m:+.3f}%")
print(f"15-MIN MOMENTUM: {mom_15m:+.3f}%")
print(f"1-HOUR MOMENTUM: {mom_60m:+.3f}%")

print("")
print(f"VOLATILITY: {volatility:.3f}%")

print("")
print(f"KALSHI YES BID: {yes_bid}")
print(f"KALSHI YES ASK: {yes_ask}")
print(f"KALSHI NO BID:  {no_bid}")
print(f"KALSHI NO ASK:  {no_ask}")

print("")
print(f"SCORE: {score}")
print(f"PREDICTION: {prediction}")
print(f"CONFIDENCE: {confidence}%")

print("")
print(f"MARKET CLOSE: {close_time}")

print("")
print("======================================")
print(f"TIME: {datetime.now(timezone.utc).isoformat()}")
print("======================================")

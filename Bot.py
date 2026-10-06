import requests
from datetime import datetime, timezone

BASE = "https://api.elections.kalshi.com/trade-api/v2"


def get_json(url, params=None):
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# --------------------------------------------------
# 1. Find ETH 15-minute markets using the actual
#    Kalshi series ticker
# --------------------------------------------------

data = get_json(
    BASE + "/markets",
    {
        "series_ticker": "KXETH15M",
        "status": "open",
        "limit": 100
    }
)

markets = data.get("markets", [])

if not markets:
    raise Exception(
        "Kalshi returned no open KXETH15M markets. "
        f"API response: {data}"
    )


# Find the market that closes soonest
markets.sort(key=lambda x: x.get("close_time", ""))

market = markets[0]

ticker = market["ticker"]


# --------------------------------------------------
# 2. Market information
# --------------------------------------------------

yes_bid = market.get("yes_bid")
yes_ask = market.get("yes_ask")
no_bid = market.get("no_bid")
no_ask = market.get("no_ask")

last_price = market.get("last_price")

close_time = market.get("close_time")

title = market.get("title")

# Kalshi's target/strike
floor_strike = market.get("floor_strike")
cap_strike = market.get("cap_strike")

# Some versions of these markets expose a custom
# reference/strike field.
strike = (
    floor_strike
    if floor_strike is not None
    else market.get("strike")
)


# --------------------------------------------------
# 3. Current ETH price
# --------------------------------------------------

kraken = get_json(
    "https://api.kraken.com/0/public/Ticker",
    {"pair": "ETHUSD"}
)

if kraken.get("error"):
    raise Exception(f"Kraken error: {kraken['error']}")

pair_data = list(kraken["result"].values())[0]

eth_price = float(pair_data["c"][0])


# --------------------------------------------------
# 4. ETH 1-minute candles
# --------------------------------------------------

ohlc = get_json(
    "https://api.kraken.com/0/public/OHLC",
    {
        "pair": "ETHUSD",
        "interval": 1
    }
)

if ohlc.get("error"):
    raise Exception(f"Kraken error: {ohlc['error']}")

candles = list(ohlc["result"].values())[0]

# Remove unfinished candle
candles = candles[:-1]

if len(candles) < 60:
    raise Exception("Not enough ETH candle data.")

closes = [float(x[4]) for x in candles]


# --------------------------------------------------
# 5. Momentum
# --------------------------------------------------

price_now = closes[-1]

price_5m = closes[-5]

price_15m = closes[-15]

price_60m = closes[-60]


mom_5m = (price_now / price_5m - 1) * 100

mom_15m = (price_now / price_15m - 1) * 100

mom_60m = (price_now / price_60m - 1) * 100


# --------------------------------------------------
# 6. Recent volatility
# --------------------------------------------------

recent = closes[-15:]

high = max(recent)

low = min(recent)

volatility = (high - low) / price_now * 100


# --------------------------------------------------
# 7. Direction score
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
# 8. Prediction
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
# 9. Print results
# --------------------------------------------------

print("")
print("======================================")
print("       ETH 15-MIN KALSHI SIGNAL")
print("======================================")

print(f"MARKET: {ticker}")

print(f"TITLE: {title}")

print(f"ETH PRICE: ${eth_price:,.2f}")

if strike is not None:
    print(f"TARGET: ${float(strike):,.2f}")

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

print(
    f"TIME: {datetime.now(timezone.utc).isoformat()}"
)

print("======================================")

import requests
from datetime import datetime, timezone

BASE = "https://api.elections.kalshi.com/trade-api/v2"


def get_json(url, params=None):
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# ==================================================
# 1. FIND CURRENT ETH 15-MINUTE KALSHI MARKET
# ==================================================

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
    raise Exception("No open KXETH15M markets found.")

markets.sort(key=lambda x: x.get("close_time", ""))

market = markets[0]

ticker = market["ticker"]
title = market.get("title", "")

close_time = market.get("close_time")

floor_strike = market.get("floor_strike")
cap_strike = market.get("cap_strike")


# ==================================================
# 2. GET KALSHI ORDER BOOK
# ==================================================

book = get_json(
    BASE + f"/markets/{ticker}/orderbook"
)

orderbook = book.get("orderbook", {})

yes_bids = orderbook.get("yes", [])
no_bids = orderbook.get("no", [])


def best_price(side):
    if not side:
        return None

    prices = []

    for item in side:
        if isinstance(item, list):
            prices.append(item[0])
        elif isinstance(item, dict):
            if "price" in item:
                prices.append(item["price"])

    if not prices:
        return None

    return max(prices)


yes_bid = best_price(yes_bids)
no_bid = best_price(no_bids)


# ==================================================
# 3. CURRENT ETH PRICE
# ==================================================

kraken = get_json(
    "https://api.kraken.com/0/public/Ticker",
    {"pair": "ETHUSD"}
)

if kraken.get("error"):
    raise Exception(f"Kraken error: {kraken['error']}")

pair_data = list(kraken["result"].values())[0]

eth_price = float(pair_data["c"][0])


# ==================================================
# 4. ETH 1-MINUTE CANDLES
# ==================================================

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

candles = candles[:-1]

if len(candles) < 60:
    raise Exception("Not enough ETH candle data.")

closes = [float(x[4]) for x in candles]


# ==================================================
# 5. MOMENTUM
# ==================================================

price_now = closes[-1]

price_5m = closes[-5]

price_15m = closes[-15]

price_60m = closes[-60]

mom_5m = (price_now / price_5m - 1) * 100

mom_15m = (price_now / price_15m - 1) * 100

mom_60m = (price_now / price_60m - 1) * 100


# ==================================================
# 6. VOLATILITY
# ==================================================

recent = closes[-15:]

high = max(recent)

low = min(recent)

volatility = (high - low) / price_now * 100


# ==================================================
# 7. DISTANCE FROM TARGET
# ==================================================

if floor_strike is not None:

    target = float(floor_strike)

    distance = (eth_price - target) / target * 100

else:

    target = None
    distance = None


# ==================================================
# 8. DIRECTION SCORE
# ==================================================

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


# ==================================================
# 9. MODEL PROBABILITY
# ==================================================

if score >= 3:

    prediction = "UP"
    probability = 0.70

elif score == 2:

    prediction = "UP"
    probability = 0.62

elif score <= -3:

    prediction = "DOWN"
    probability = 0.70

elif score == -2:

    prediction = "DOWN"
    probability = 0.62

else:

    prediction = "SKIP"
    probability = 0.50


# ==================================================
# 10. MARKET PRICE
# ==================================================

def cents(value):

    if value is None:
        return None

    return float(value) / 100


yes_probability = cents(yes_bid)

no_probability = cents(no_bid)


# ==================================================
# 11. EDGE CALCULATION
# ==================================================

if prediction == "UP" and yes_probability is not None:

    edge = probability - yes_probability

    if edge >= 0.08:
        action = "BUY UP"

    else:
        action = "SKIP"


elif prediction == "DOWN" and no_probability is not None:

    edge = probability - no_probability

    if edge >= 0.08:
        action = "BUY DOWN"

    else:
        action = "SKIP"


else:

    edge = None
    action = "SKIP"


# ==================================================
# 12. OUTPUT
# ==================================================

print("")
print("==============================================")
print("          ETH 15-MIN KALSHI BOT")
print("==============================================")

print(f"MARKET: {ticker}")

print(f"TITLE: {title}")

print("")

print(f"ETH PRICE: ${eth_price:,.2f}")

if target is not None:

    print(f"TARGET: ${target:,.2f}")

    print(f"DISTANCE: {distance:+.3f}%")

print("")

print(f"5-MIN MOMENTUM:  {mom_5m:+.3f}%")

print(f"15-MIN MOMENTUM: {mom_15m:+.3f}%")

print(f"1-HOUR MOMENTUM: {mom_60m:+.3f}%")

print("")

print(f"VOLATILITY: {volatility:.3f}%")

print("")

print(f"KALSHI YES BID: {yes_bid}")

print(f"KALSHI NO BID:  {no_bid}")

print("")

print(f"MODEL: {prediction}")

print(f"MODEL PROBABILITY: {probability * 100:.0f}%")

if edge is not None:

    print(f"EDGE: {edge * 100:+.1f}%")

print("")

print(f"FINAL ACTION: {action}")

print("")

print(f"CLOSE: {close_time}")

print("==============================================")

print(
    f"TIME: {datetime.now(timezone.utc).isoformat()}"
)

print("==============================================")

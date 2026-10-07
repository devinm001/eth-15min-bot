import requests
import os
from datetime import datetime, timezone

BASE = "https://api.elections.kalshi.com/trade-api/v2"
STATE_FILE = "bot_state.txt"


def get_json(url, params=None):
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# =========================
# FIND CURRENT MARKET
# =========================

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


# =========================
# KALSHI ORDER BOOK
# =========================

book = get_json(BASE + f"/markets/{ticker}/orderbook")

orderbook = book.get("orderbook_fp", {})

yes_data = orderbook.get("yes_dollars", [])
no_data = orderbook.get("no_dollars")


def best_bid(data):
    if not data:
        return None

    prices = []

    for item in data:
        if isinstance(item, list) and len(item) >= 1:
            try:
                prices.append(float(item[0]))
            except:
                pass

    return max(prices) if prices else None


yes_bid = best_bid(yes_data)
no_bid = best_bid(no_data)


# =========================
# ETH PRICE
# =========================

eth_data = get_json(
    "https://api.kraken.com/0/public/Ticker",
    {"pair": "ETHUSD"}
)

eth_price = float(
    eth_data["result"]["XETHZUSD"]["c"][0]
)


# =========================
# ETH MOMENTUM
# =========================

ohlc = get_json(
    "https://api.kraken.com/0/public/OHLC",
    {
        "pair": "ETHUSD",
        "interval": 1
    }
)

candles = ohlc["result"]["XETHZUSD"]

closes = [float(c[4]) for c in candles]


def momentum(minutes):
    if len(closes) <= minutes:
        return 0

    old = closes[-minutes - 1]
    new = closes[-1]

    return ((new - old) / old) * 100


m5 = momentum(5)
m15 = momentum(15)
m60 = momentum(60)


# =========================
# VOLATILITY
# =========================

recent = closes[-15:]

returns = []

for i in range(1, len(recent)):
    returns.append(
        (recent[i] - recent[i - 1]) /
        recent[i - 1]
    )

if returns:
    avg = sum(returns) / len(returns)

    variance = sum(
        (x - avg) ** 2 for x in returns
    ) / len(returns)

    volatility = (variance ** 0.5) * 100
else:
    volatility = 0


# =========================
# MODEL
# =========================

score = 0

if m5 > 0.02:
    score += 1
elif m5 < -0.02:
    score -= 1

if m15 > 0.04:
    score += 1
elif m15 < -0.04:
    score -= 1

if m60 > 0.10:
    score += 1
elif m60 < -0.10:
    score -= 1


if score >= 3:
    prediction = "YES"
    probability = 70

elif score == 2:
    prediction = "YES"
    probability = 62

elif score <= -3:
    prediction = "NO"
    probability = 70

elif score == -2:
    prediction = "NO"
    probability = 62

else:
    prediction = "SKIP"
    probability = 50


# =========================
# EDGE
# =========================

market_price = None
edge = None

if prediction == "YES" and yes_bid is not None:
    market_price = yes_bid
    edge = probability / 100 - yes_bid

elif prediction == "NO" and no_bid is not None:
    market_price = no_bid
    edge = probability / 100 - no_bid


# =========================
# FLIP DETECTION
# =========================

previous_prediction = None
previous_ticker = None

if os.path.exists(STATE_FILE):

    with open(STATE_FILE, "r") as f:
        lines = f.read().split("|")

        if len(lines) >= 2:
            previous_ticker = lines[0]
            previous_prediction = lines[1]


if previous_ticker == ticker:

    if (
        previous_prediction in ["YES", "NO"]
        and prediction in ["YES", "NO"]
        and previous_prediction != prediction
    ):
        flip = f"FLIP: {previous_prediction} -> {prediction}"

    else:
        flip = "NO FLIP"

else:
    flip = "NEW MARKET"


# Save current state

with open(STATE_FILE, "w") as f:
    f.write(f"{ticker}|{prediction}")


# =========================
# OUTPUT
# =========================

print("\n==============================================")
print("          ETH 15-MIN KALSHI BOT")
print("==============================================")

print(f"MARKET: {ticker}")
print(f"TITLE: {title}")

print(f"\nETH PRICE: ${eth_price:,.2f}")

if floor_strike:
    print(f"TARGET: ${float(floor_strike):,.2f}")

print(f"\n5-MIN MOMENTUM:  {m5:+.3f}%")
print(f"15-MIN MOMENTUM: {m15:+.3f}%")
print(f"1-HOUR MOMENTUM: {m60:+.3f}%")

print(f"\nVOLATILITY: {volatility:.3f}%")

print("\nKALSHI MARKET")
print(f"YES BID: {yes_bid}")
print(f"NO BID:  {no_bid}")

print("\nMODEL")
print(f"PREDICTION: {prediction}")
print(f"PROBABILITY: {probability}%")

if market_price is not None:
    print(f"MARKET PRICE: ${market_price:.2f}")

if edge is not None:
    print(f"EDGE: {edge * 100:+.1f} percentage points")

print(f"\n{flip}")

print(f"\nCLOSE: {close_time}")

print("\n==============================================")

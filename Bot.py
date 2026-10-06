import requests
import json
from datetime import datetime, timezone

BASE = "https://api.elections.kalshi.com/trade-api/v2"


def get_json(url, params=None):
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# =========================
# FIND CURRENT KALSHI MARKET
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
    raise Exception("No open ETH 15-minute markets found.")

markets.sort(key=lambda x: x.get("close_time", ""))

market = markets[0]

ticker = market["ticker"]
title = market.get("title", "")
close_time = market.get("close_time")

floor_strike = market.get("floor_strike")
cap_strike = market.get("cap_strike")


# =========================
# GET KALSHI ORDER BOOK
# =========================

book = get_json(BASE + f"/markets/{ticker}/orderbook")

print("\nRAW ORDER BOOK:")
print(json.dumps(book, indent=2))


# =========================
# PARSE ORDER BOOK
# =========================

orderbook = book.get("orderbook", {})


def extract_prices(data):
    prices = []

    if isinstance(data, list):
        for item in data:

            if isinstance(item, list) and len(item) >= 1:
                try:
                    prices.append(float(item[0]))
                except:
                    pass

            elif isinstance(item, dict):

                for key in [
                    "price",
                    "price_cents",
                    "yes_price",
                    "no_price"
                ]:
                    if key in item:
                        try:
                            prices.append(float(item[key]))
                            break
                        except:
                            pass

    return prices


yes_data = orderbook.get("yes", [])
no_data = orderbook.get("no", [])

yes_prices = extract_prices(yes_data)
no_prices = extract_prices(no_data)

yes_bid = max(yes_prices) if yes_prices else None
no_bid = max(no_prices) if no_prices else None


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
# KRAKEN 1-MINUTE DATA
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
# SIMPLE DIRECTION MODEL
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

print(f"\nKALSHI YES BID: {yes_bid}")
print(f"KALSHI NO BID:  {no_bid}")

print(f"\nMODEL: {prediction}")
print(f"MODEL PROBABILITY: {probability}%")

print(f"\nCLOSE: {close_time}")

print("\n==============================================")

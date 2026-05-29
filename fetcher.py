import requests
import mysql.connector
from datetime import datetime
import time

# ─── DATABASE CONNECTION ───────────────────────────────────────────────────
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Danish12",
        database="crypto_sentiment"
    )

# ─── AUTOMATED DATABASE CLEANER ───────────────────────────────────────────
def clear_old_data(cursor, db):
    print("Wiping old data to prevent duplication...")
    cursor.execute("SET SQL_SAFE_UPDATES = 0;")
    cursor.execute("TRUNCATE TABLE price_data;")
    cursor.execute("TRUNCATE TABLE sentiment_data;")
    cursor.execute("TRUNCATE TABLE regression_results;")
    cursor.execute("SET SQL_SAFE_UPDATES = 1;")
    db.commit()
    print("✓ Database cleared and ready")

# ─── FETCH CURRENT CRYPTO PRICES FROM COINGECKO ───────────────────────────
def fetch_prices(cursor, db):
    print("Fetching current live crypto prices...")
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": "bitcoin,ethereum,solana",
        "order": "market_cap_desc",
        "sparkline": "false"
    }
    response = requests.get(url, params=params)
    data = response.json()

    for coin in data:
        cursor.execute("""
            INSERT IGNORE INTO price_data 
            (coin_id, coin_name, price_usd, market_cap, volume_24h, price_change_24h, recorded_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            coin["id"],
            coin["name"],
            coin["current_price"],
            coin["market_cap"],
            coin["total_volume"],
            coin["price_change_percentage_24h"],
            datetime.now()
        ))
    db.commit()
    print(f"✓ Saved live prices for {len(data)} coins")

# ─── FETCH TODAY'S SENTIMENT ──────────────────────────────────────────────
def fetch_sentiment(cursor, db):
    print("Fetching today's public mood score...")
    url = "https://api.alternative.me/fng/?limit=1"
    response = requests.get(url)
    data = response.json()["data"][0]

    cursor.execute("""
        INSERT IGNORE INTO sentiment_data (score, sentiment_label, recorded_at)
        VALUES (%s, %s, %s)
    """, (
        int(data["value"]),
        data["value_classification"],
        datetime.now()
    ))
    db.commit()
    print(f"✓ Saved today's mood: {data['value_classification']} ({data['value']})")

# ─── FETCH HISTORICAL PRICES (365 DAYS) ───────────────────────────────────
def fetch_historical(cursor, db):
    print("Fetching 365 days of historical price data...")
    coins = ["bitcoin", "ethereum", "solana"]

    for coin in coins:
        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
        params = {"vs_currency": "usd", "days": "365", "interval": "daily"}
        response = requests.get(url, params=params)
        data = response.json()

        if "prices" not in data:
            print(f"Error fetching data for {coin}: {data}")
            continue

        prices = data["prices"]
        volumes = data["total_volumes"]

        for i in range(len(prices)):
            timestamp = datetime.fromtimestamp(prices[i][0] / 1000)
            price = prices[i][1]
            volume = int(volumes[i][1])

            if i > 0:
                prev_price = prices[i-1][1]
                change = ((price - prev_price) / prev_price) * 100
            else:
                change = 0.0

            cursor.execute("""
                INSERT IGNORE INTO price_data 
                (coin_id, coin_name, price_usd, market_cap, volume_24h, price_change_24h, recorded_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                coin,
                coin.capitalize(),
                price,
                None,
                volume,
                round(change, 4),
                timestamp
            ))
        db.commit()
        print(f"✓ Saved 365 days for {coin.upper()}")
        time.sleep(3)  # Rate limit protection

# ─── FETCH HISTORICAL SENTIMENT (365 DAYS) ────────────────────────────────
def fetch_historical_sentiment(cursor, db):
    print("Fetching 365 days of historical mood scores...")
    url = "https://api.alternative.me/fng/?limit=365"
    response = requests.get(url)
    data = response.json()["data"]

    for entry in data:
        timestamp = datetime.fromtimestamp(int(entry["timestamp"]))
        cursor.execute("""
            INSERT IGNORE INTO sentiment_data (score, sentiment_label, recorded_at)
            VALUES (%s, %s, %s)
        """, (
            int(entry["value"]),
            entry["value_classification"],
            timestamp
        ))
    db.commit()
    print(f"✓ Saved {len(data)} days of mood score history")

# ─── MAIN ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Starting Data Fetch Pipeline ===")
    connection = get_connection()
    active_cursor = connection.cursor()

    clear_old_data(active_cursor, connection)
    fetch_historical(active_cursor, connection)
    fetch_historical_sentiment(active_cursor, connection)
    fetch_prices(active_cursor, connection)
    fetch_sentiment(active_cursor, connection)

    print("=== Pipeline Complete — Database Rebuilt Successfully ===")
    active_cursor.close()
    connection.close()

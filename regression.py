import mysql.connector
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from datetime import datetime

# ─── DATABASE CONNECTION ───────────────────────────────────────────────────
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Danish12",
    database="crypto_sentiment"
)
cursor = db.cursor()

# ─── LOAD DATA FROM MYSQL ─────────────────────────────────────────────────
def load_data(coin_id):
    cursor.execute("""
        SELECT DATE(recorded_at) as date, AVG(price_change_24h) as avg_change
        FROM price_data
        WHERE coin_id = %s
        GROUP BY DATE(recorded_at)
        ORDER BY date
    """, (coin_id,))
    price_rows = cursor.fetchall()
    price_df = pd.DataFrame(price_rows, columns=["date", "price_change"])

    cursor.execute("""
        SELECT DATE(recorded_at) as date, AVG(score) as avg_score
        FROM sentiment_data
        GROUP BY DATE(recorded_at)
        ORDER BY date
    """)
    sentiment_rows = cursor.fetchall()
    sentiment_df = pd.DataFrame(sentiment_rows, columns=["date", "sentiment_score"])

    merged = pd.merge(price_df, sentiment_df, on="date")
    merged = merged.dropna()
    return merged

# ─── RUN REGRESSION ───────────────────────────────────────────────────────
def run_regression(coin_id):
    print(f"\n=== Linear Regression for {coin_id.upper()} ===")
    df = load_data(coin_id)

    if len(df) < 10:
        print(f"Not enough data for {coin_id}")
        return

    X = df["sentiment_score"].values.astype(float).reshape(-1, 1)
    y = df["price_change"].values.astype(float)

    model = LinearRegression()
    model.fit(X, y)

    y_pred = model.predict(X)
    r2 = r2_score(y, y_pred)
    correlation = np.corrcoef(
        df["sentiment_score"].astype(float),
        df["price_change"].astype(float)
    )[0][1]
    slope = model.coef_[0]
    intercept = model.intercept_

    print(f"Correlation Coefficient : {correlation:.4f}")
    print(f"R² Score               : {r2:.4f}")
    print(f"Slope (β)              : {slope:.4f}")
    print(f"Intercept (α)          : {intercept:.4f}")

    # Academically honest correlation thresholds
    if correlation > 0.7:
        note = f"{coin_id}: Strong positive link — public confidence strongly drives price up"
    elif correlation > 0.5:
        note = f"{coin_id}: Moderate positive link — public confidence has noticeable effect on price"
    elif correlation > 0.3:
        note = f"{coin_id}: Weak positive link — public confidence has some but inconsistent effect"
    elif correlation < -0.7:
        note = f"{coin_id}: Strong inverse link — higher confidence paradoxically associates with price drops"
    elif correlation < -0.5:
        note = f"{coin_id}: Moderate inverse link — public confidence moderately associates with price drops"
    elif correlation < -0.3:
        note = f"{coin_id}: Weak inverse link — slight inverse pattern detected"
    else:
        note = f"{coin_id}: No meaningful link — public mood does not predict price movement"

    print(f"Interpretation         : {note}")

    cursor.execute("""
        INSERT INTO regression_results 
        (correlation_coefficient, r_squared, slope, intercept, prediction_note, calculated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        round(float(correlation), 6),
        round(float(r2), 6),
        round(float(slope), 6),
        round(float(intercept), 6),
        note,
        datetime.now()
    ))
    db.commit()
    print(f"✓ Results saved to database")

# ─── MAIN ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    coins = ["bitcoin", "ethereum", "solana"]
    for coin in coins:
        run_regression(coin)

    print("\n=== All regression results saved ===")

    print("\n─── Summary from Database ───")
    cursor.execute("""
        SELECT prediction_note, correlation_coefficient, r_squared 
        FROM regression_results
        ORDER BY calculated_at DESC
        LIMIT 3
    """)
    for row in cursor.fetchall():
        print(f"{row[0]}")
        print(f"  r = {row[1]}  |  R² = {row[2]}")

    cursor.close()
    db.close()

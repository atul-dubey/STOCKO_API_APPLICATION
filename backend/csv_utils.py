import csv 
import os

CSV_FOLDER = "data"

def initialize_csv(ticker):
    ticker = ticker.upper()
    filepath = os.path.join(CSV_FOLDER, f"{ticker}.csv")
    os.makedirs(CSV_FOLDER, exist_ok=True)

    if not os.path.exists(filepath) or os.stat(filepath).st_size == 0:
        with open(filepath, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Ticker", "Date", "Time", "LTP", "LTQ"])

    return filepath


def save_tick_in_csv(tick, filepath):
    print(f"💾 Saving tick to {filepath}: {tick}")  # Add this
    with open(filepath, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            tick["symbol"],
            tick["date"],
            tick["time"],
            tick["ltp"],
            tick["ltq"]
        ])
        f.flush()  # ✅ Immediately write to disk to prevent loss on crash



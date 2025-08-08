from datetime import datetime
from .mongodb_connect import db

def insert_tick_data(ticker: str, ltp: float, ltq: int):
    """
    Insert a single tick data point into the MongoDB Atlas collection for the given ticker.
    Each ticker gets its own collection.
    """
    collection_name = ticker.replace('.', '_')  # e.g., TCS_NSE
    collection = db[collection_name]

    document = {
        "ticker": ticker,
        "date": datetime.now().strftime("%d-%m-%Y"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "ltp": ltp,
        "ltq": ltq
    }
    collection.insert_one(document)
    print(f"📥 Inserted tick data into MongoDB for {ticker}: {document}")



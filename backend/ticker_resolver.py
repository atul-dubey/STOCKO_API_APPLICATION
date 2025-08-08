import requests
from backend.exchange_constants import EXCHANGE_NAME_TO_CODE, get_multiplier
import os
from dotenv import load_dotenv

# Load all variables from .env
load_dotenv()

BASE_URL = os.getenv("BASE_URL")

def resolve_ticker(ticker_with_exchange: str, access_token: str) -> dict:
    """
    Resolves a user-entered ticker like 'RELIANCE.NSE' or 'TCS.BSE'
    to the correct instrument details using the Stocko search API.

    Returns:
        {
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "exchange_code": 1,
            "token": 2885,
            "trading_symbol": "RELIANCE-EQ",
            "company": "RELIANCE INDUSTRIES LTD."
            "multiplier":100
        }
    or raises ValueError if not found.
    """
    try:
        if '.' not in ticker_with_exchange:
            raise ValueError("Ticker must be in format SYMBOL.EXCHANGE (e.g., RELIANCE.NSE)")

        symbol, exchange = ticker_with_exchange.strip().upper().split('.')
        if exchange not in EXCHANGE_NAME_TO_CODE:
            raise ValueError(f"Unsupported exchange: {exchange}")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.get(
            f"{BASE_URL}/api/v1/search?key={symbol}",
            headers=headers
        )

        if response.status_code != 200:
            raise ValueError(f"API Error: {response.status_code} - {response.text}")

        results = response.json().get("result", [])

        

        for item in results:
            if (
                item.get("symbol", "").upper() == symbol
                and item.get("exchange", "").upper() == exchange
            ):
                exchange_code = EXCHANGE_NAME_TO_CODE.get(item["exchange"].upper(), -1)
                multiplier = get_multiplier(exchange_code)
                
                return {
                    "symbol": item["symbol"],
                    "exchange": item["exchange"],
                    "exchange_code": exchange_code,
                    "token": item["token"],
                    "trading_symbol": item["trading_symbol"],
                    "company": item["company"],
                    "multiplier": multiplier

                }

        raise ValueError(f"No matching instrument found for {ticker_with_exchange}. Search API returned {len(results)} results.")

    except Exception as e:
        raise ValueError(f"Error resolving ticker: {e}")





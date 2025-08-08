# exchange_constants.py

EXCHANGES = {
    1: {"name": "NSE", "multiplier": 100},
    2: {"name": "NFO", "multiplier": 100},
    3: {"name": "CDS", "multiplier": 10000000},
    4: {"name": "MCX", "multiplier": 100},
    6: {"name": "BSE", "multiplier": 100},
    7: {"name": "BFO", "multiplier": 100}
}

def get_exchange_name(code: int) -> str:
    return EXCHANGES.get(code, {}).get("name", "UNKNOWN")

def get_multiplier(code: int) -> int:
    return EXCHANGES.get(code, {}).get("multiplier", 1)

EXCHANGE_NAME_TO_CODE = {v["name"]: k for k, v in EXCHANGES.items()}
#This lets you go from "NSE" → 1, "BSE" → 6, etc.


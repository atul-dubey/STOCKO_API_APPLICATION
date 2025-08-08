# ws_recorder.py

import os
import time
import queue
import sys
import threading
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "pyoauthbridge", "connect")))
from dotenv import load_dotenv
from backend.ticker_resolver import resolve_ticker
from backend.exchange_constants import get_exchange_name, get_multiplier
from pyoauthbridge.connect import Connect
from pyoauthbridge.wsclient import is_socket_open
from backend.db_utils import insert_tick_data
from backend.csv_utils import initialize_csv, save_tick_in_csv
from pyoauthbridge.wsclient import subscribe_ticker, unsubscribe_ticker


load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
BASE_URL = os.getenv("BASE_URL")
STORAGE_MODE = os.getenv("STORAGE_MODE", "mongodb").strip().lower()

# ACCESS_TOKEN_PATH = "access_token_new.txt"

# Shared socket connection
shared_conn = Connect(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, BASE_URL)

recording_threads = {}      # ticker -> Thread
recording_flags = {}        # ticker -> {"stop": False}
recording_conns = {}        # ticker -> Connect object

# # Auto-close if no activity for this duration
# inactivity_timeout_sec = 30
# last_active_time = time.time()


def format_tick(raw_data, symbol, exchange_code):
    if "last_traded_price" not in raw_data or "last_traded_quantity" not in raw_data:
        return None

    multiplier = get_multiplier(exchange_code)
    exchange_name = get_exchange_name(exchange_code)

    ltp_real = raw_data["last_traded_price"] / multiplier
    timestamp = datetime.now()

    return {
        "symbol": f"{symbol.upper()}.{exchange_name}",
        "date": timestamp.strftime("%d-%m-%y"),
        "time": timestamp.strftime("%H:%M:%S"),
        "ltp": ltp_real,
        "ltq": raw_data.get("last_traded_quantity", 0),
    }


def record_ticker(ticker, access_token, stop_flag):
    print(f"[DEBUG] STORAGE_MODE = {STORAGE_MODE}")
    global last_active_time
    ticker = ticker.strip().upper()

    try:
        instrument = resolve_ticker(ticker, access_token)
    except ValueError as e:
        print(f"❌ {e}")
        return

    print(f"[DEBUG] Instrument: {instrument}")

    conn = shared_conn

    # Start socket if not already running
    if not is_socket_open():
        conn.set_access_token(access_token)
        conn.run_socket()

    # recording_conns[ticker] = conn
    recording_conns[ticker] = {
    "exchange_code": instrument["exchange_code"],
    "token": instrument["token"]
}

    payload = {
        "exchangeCode": instrument["exchange_code"],
        "instrumentToken": int(instrument["token"])
    }

    conn.subscribe_detailed_marketdata(payload)

    filepath = initialize_csv(ticker)
    print(f"✅ Recording started for {ticker}")

    key = f"{instrument['token']}_{instrument['exchange_code']}"#new

    previous = {}
    try:
        while not stop_flag["stop"]:
            if not is_socket_open():
                print(f"[{ticker}] Shared socket closed. Exiting recording loop.")
                break
            
            # tick_data = conn.read_detailed_marketdata()

            tick_data = conn.read_detailed_marketdata(key)#new


            print(f"[DEBUG] Polled tick: {tick_data}")  #   Raw data from WebSocket
            
            if tick_data:
                tick = format_tick(tick_data, instrument["symbol"], instrument["exchange_code"])
                if tick:
                    last_active_time = time.time()  # ⏰ Update only if tick is valid

                    

                    print("[record_ticker] Tick LTP:", tick.get("ltp"), "LTQ:", tick.get("ltq"))
                    ltp, ltq = tick["ltp"], tick["ltq"]

                    
                    if ltq > 0 and (ltp != previous.get("ltp") or ltq != previous.get("ltq")):
                        
                        if STORAGE_MODE == "csv":
                            save_tick_in_csv(tick, filepath)
                        elif STORAGE_MODE == "mongodb":
                             insert_tick_data(ticker, ltp, ltq)
                        else:
                            print("❌ Unknown storage mode:", STORAGE_MODE)

                        previous = {"ltp": ltp, "ltq": ltq}


            time.sleep(0.05)

    finally:
        print(f"🛑 Recording stopped for {ticker}")
        try:
            conn.unsubscribe_detailed_marketdata()
        except Exception as e:
            print(f"[ERROR] Closing socket failed: {e}")

        recording_threads.pop(ticker, None)
        recording_flags.pop(ticker, None)
        recording_conns.pop(ticker, None)


def start_recording(ticker, access_token):
    ticker = ticker.strip().upper()

    if ticker in recording_threads:
        return f"⚠️ {ticker} is already being recorded."

    try:
        instrument = resolve_ticker(ticker, access_token)
    except ValueError as e:
        return f"❌ Failed to resolve {ticker}: {e}"

    exchange_code = instrument["exchange_code"]
    token = instrument["token"]
    key = f"{token}_{exchange_code}"

    # ✅ Ensure queue exists
    if key not in shared_conn.tick_queues:
        shared_conn.tick_queues[key] = queue.Queue()
        print(f"[start_recording] Created tick queue for {key}")

    # ✅ Ensure socket is open
    if not is_socket_open():
        shared_conn.set_access_token(access_token)
        success = shared_conn.run_socket()
        if not success:
            return "❌ WebSocket failed to connect."

    # ✅ Set subscription success flag
    subscribed_flag = {"success": False}

    # ✅ Define the callback and push tick to queue
    def test_callback(tick):
        print(f"[test_callback] Received tick for {ticker}")
        shared_conn.tick_queues[key].put(tick)
        print(f"[test_callback] Tick pushed to queue for {key}")
        subscribed_flag["success"] = True

    # ✅ Subscribe to ticker with callback
    subscribe_ticker(exchange_code, token, callback=test_callback)

    # ✅ Wait briefly to ensure subscription worked
    for _ in range(10):
        if subscribed_flag["success"]:
            break
        time.sleep(0.3)

    if not subscribed_flag["success"]:
        return f"❌ Failed to receive data for {ticker}. Subscription may have failed."

    # ✅ Start recording thread
    stop_flag = {"stop": False}
    thread = threading.Thread(target=record_ticker, args=(ticker, access_token, stop_flag), daemon=True)
    thread.start()

    recording_threads[ticker] = thread
    recording_flags[ticker] = stop_flag
    return None  # Success



def stop_recording(ticker):
    ticker = ticker.strip().upper()

    if ticker in recording_flags:
        recording_flags[ticker]["stop"] = True

        instrument = recording_conns.get(ticker)
        if instrument:
            unsubscribe_ticker(instrument["exchange_code"], instrument["token"])
        print(f"🔔 Stop signal sent for {ticker}")
    else:
        print(f"⚠️ {ticker} was not recording.")


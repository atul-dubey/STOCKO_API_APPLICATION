# streamlit_app.py
import streamlit as st
import sys
import os
import time
import pandas as pd
# sys.path.append(os.path.dirname(__file__), ".."))
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
from backend.mongodb_connect import db
from dotenv import load_dotenv
from backend.ws_recorder import start_recording, stop_recording, shared_conn 
from pyoauthbridge.pyoauthbridge.wsclient import is_socket_open
from backend.token_utils import is_token_valid

load_dotenv()

BASE_URL = os.getenv("BASE_URL")

# --- UI Config ---
st.set_page_config(page_title="Ticker Recorder", layout="wide")
st.title("📈 Ticker Live Recorder")
st.markdown("_Enter tickers in the format [SYMBOL].[EXCHANGE] like `TCS.NSE`, `RELIANCE.BSE`_")
st.markdown("---")


# --- Access Token Input ---
if "access_token" not in st.session_state:
    st.session_state.access_token = ""

if "token_validated" not in st.session_state:
    st.session_state.token_validated = False

if not st.session_state.token_validated:
    # Input form for token
    with st.form("token_form"):
        token_input = st.text_input("🔑 Enter your Access Token", type="password")
        submitted = st.form_submit_button("Validate Token")

        if submitted:
            if not token_input.strip():
                st.warning("Access token is required.")
            elif is_token_valid(BASE_URL, token_input.strip()):
                st.success("✅ Token is valid.")
                st.session_state.access_token = token_input.strip()
                st.session_state.token_validated = True

                # Set token for shared WebSocket
                shared_conn.set_access_token(token_input.strip())
                if not is_socket_open():
                    shared_conn.run_socket()
                    time.sleep(1)
            else:
                st.error("❌ Invalid token. Please try again.")
                st.text("Token validation failed. Please check if the token is expired or incorrect.")


# --- UI after validation ---
if st.session_state.token_validated:
    ACCESS_TOKEN = st.session_state.access_token
    
    # --- Init session state ---
    if "ticker_values" not in st.session_state:
        st.session_state.ticker_values = [""] * 5
    if "ticker_status" not in st.session_state:
        st.session_state.ticker_status = {}  # {ticker: "started"/"stopped"}


    # --- Ticker Rows ---
    for i in range(5):
        col1, col2, col3, _ = st.columns([2, 1, 1, 6])

        # Text input
        ticker_input = col1.text_input(
            label=f"Ticker {i+1}",
            value=st.session_state.ticker_values[i],
            key=f"ticker_input_{i}",
            placeholder="SYMBOL.EXCHANGE",
            label_visibility="collapsed"
        )

        ticker = ticker_input.strip().upper()
        st.session_state.ticker_values[i] = ticker


        # ▶️ Start Button
        disabled_start = st.session_state.ticker_status.get(ticker) == "started"
        if col2.button("▶️ Start", key=f"start_{i}", disabled=disabled_start):
            if not ticker:
                st.warning("Please enter a ticker.")
            else:
                # ✅ Ensure WebSocket is started
                shared_conn.set_access_token(ACCESS_TOKEN)

                if not is_socket_open():
                    st.warning("WebSocket is not connected. Trying to reconnect...")
                    shared_conn.run_socket()
                    time.sleep(1)  # give time to connect
                    if not is_socket_open():
                        st.error("❌ Could not connect to WebSocket.")
                        continue  # Skip starting ticker

                with st.spinner(f"Starting {ticker}..."):
                    error = start_recording(ticker, ACCESS_TOKEN)

                if error:
                    st.warning(error)
                else:
                    st.session_state.ticker_status[ticker] = "started"
                    st.success(f"✅ Started recording: {ticker}")


        # ⏹ Stop Button
        disabled_stop = st.session_state.ticker_status.get(ticker) != "started"
        if col3.button("⏹ Stop", key=f"stop_{i}" , disabled=disabled_stop):
            if not ticker:
                st.warning("Please enter a ticker.")
            else:
                stop_recording(ticker)
                st.session_state.ticker_status[ticker] = "stopped"
                st.info(f"🛑 Stopped recording: {ticker}")

    # 🔁 Clean up ticker_status for tickers no longer in inputs
    visible_tickers = set(st.session_state.ticker_values)
    st.session_state.ticker_status = {
        t: status for t, status in st.session_state.ticker_status.items()
        if t in visible_tickers
    }

    # --- Footer Status ---
    st.markdown("---")
    st.subheader("📌 Recording Status")

    if st.session_state.ticker_status:
        for ticker, status in st.session_state.ticker_status.items():
            icon = "✅" if status == "started" else "🛑"
            st.write(f"{icon} `{ticker}` → **{status.upper()}**")
    else:
        st.info("No tickers started yet.")
    

    # --- Data Viewer ---
    st.divider()
    st.header("📊 Tick Data Viewer")
    collections = db.list_collection_names()

    selected_collection = st.selectbox("🔍 Select Ticker Collection", collections, index=0 if collections else None)

    if selected_collection:
        col1, col2 = st.columns([2, 2])

        # Record limit
        limit = col1.slider("🎚️ Number of records to load", min_value=10, max_value=1000, value=100, step=10)

        # Date filter
        date_filter = col2.date_input("📅 Filter by Date (optional)")

        query = {}
        if date_filter:
            query["date"] = date_filter.strftime("%d-%m-%Y")

        # Fetch Data
        collection = db[selected_collection]
        cursor = collection.find(query).sort("time", -1).limit(limit)
        df = pd.DataFrame(list(cursor))

        if not df.empty:
            df.drop(columns=["_id"], inplace=True)
            st.dataframe(df, use_container_width=True)

            # Export button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download as CSV", data=csv, file_name=f"{selected_collection}.csv", mime='text/csv')

            # Optional Delete
            with st.expander("🗑️ Delete Data"):
                delete_date = st.date_input("Select date to delete data for")
                if st.button("Delete Records"):
                    del_query = {"date": delete_date.strftime("%d-%m-%Y")}
                    result = collection.delete_many(del_query)
                    st.warning(f"Deleted {result.deleted_count} record(s) from {selected_collection}.")

        else:
            st.info("No data found for the selected options.")

        # Auto-refresh
        if st.checkbox("🔄 Auto-refresh every 5 sec"):
            time.sleep(5)
            st.rerun()


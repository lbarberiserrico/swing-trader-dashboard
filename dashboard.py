import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import os

# --- File to persist data ---
DATA_FILE = "trader_data.json"

# --- Initialize session state ---
if 'trades' not in st.session_state:
    st.session_state.trades = []

if 'settings' not in st.session_state:
    st.session_state.settings = {
        'starting_capital': 10000.00,
        'default_commission': 1.00,
        'max_risk_pct': 2.0
    }

# --- Load saved data ---
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        saved = json.load(f)
        st.session_state.trades = saved.get("trades", st.session_state.trades)
        st.session_state.settings = saved.get("settings", st.session_state.settings)

# --- Function to save data ---
def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({
            "trades": st.session_state.trades,
            "settings": st.session_state.settings
        }, f, indent=2)

# --- Sidebar Settings ---
st.sidebar.subheader("Settings")

settings = st.session_state.settings

settings['starting_capital'] = st.sidebar.number_input(
    "Starting Capital ($)",
    value=float(settings['starting_capital']),
    step=100.00,
    format="%.2f"
)

settings['default_commission'] = st.sidebar.number_input(
    "Default Commission ($)",
    value=float(settings['default_commission']),
    step=0.10,
    format="%.2f"
)

settings['max_risk_pct'] = st.sidebar.number_input(
    "Max Risk % per Trade",
    value=float(settings['max_risk_pct']),
    step=0.5,
    format="%.2f"
)

# --- Main App ---
st.title("Swing Trader Dashboard")

# --- Add Trade ---
st.subheader("Add Trade")

col1, col2, col3, col4 = st.columns(4)
with col1:
    symbol = st.text_input("Symbol")
with col2:
    entry = st.number_input("Entry Price", format="%.2f")
with col3:
    exit_price = st.number_input("Exit Price", format="%.2f")
with col4:
    commission = st.number_input("Commission ($)", value=float(settings['default_commission']), step=0.10, format="%.2f")

if st.button("Add Trade"):
    if symbol and entry and exit_price is not None:
        trade = {
            "symbol": symbol,
            "entry": entry,
            "exit": exit_price,
            "commission": commission
        }
        st.session_state.trades.append(trade)
        save_data()
        st.success(f"Trade for {symbol} added!")

# --- Trades Table ---
if st.session_state.trades:
    df = pd.DataFrame(st.session_state.trades)
    df["Profit"] = df["exit"] - df["entry"] - df["commission"]
    st.subheader("Trades")
    st.dataframe(df)

    # --- Stats ---
    total_trades = len(df)
    winning_trades = len(df[df["Profit"] > 0])
    win_rate = round((winning_trades / total_trades) * 100, 2) if total_trades else 0
    avg_win = round(df[df["Profit"] > 0]["Profit"].mean(), 2) if winning_trades else 0
    avg_loss = round(df[df["Profit"] <= 0]["Profit"].mean(), 2) if total_trades - winning_trades else 0

    st.subheader("Stats")
    st.write(f"Total Trades: {total_trades}")
    st.write(f"Win Rate: {win_rate}%")
    st.write(f"Avg Win: ${avg_win} • Avg Loss: ${avg_loss}")

    # --- Equity Curve ---
    df["Equity"] = settings['starting_capital'] + df["Profit"].cumsum()
    st.subheader("Equity Curve")
    fig, ax = plt.subplots()
    ax.plot(df["Equity"], marker='o')
    ax.set_xlabel("Trade #")
    ax.set_ylabel("Equity ($)")
    ax.grid(True)
    st.pyplot(fig)
else:
    st.info("No trades added yet.")

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import json
import os
from datetime import datetime

# ----------------------------
# File for saving trades
# ----------------------------
DATA_FILE = "trades.json"

# Load trades from JSON file
def load_trades():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            df = pd.DataFrame(json.load(f))
            if not df.empty:
                # Ensure Entry/Exit Dates are proper datetime.date objects
                df["Entry Date"] = pd.to_datetime(df["Entry Date"]).dt.date
                df["Exit Date"] = pd.to_datetime(df["Exit Date"]).dt.date
            return df
    return pd.DataFrame(columns=[
        "Symbol", "Entry Date", "Exit Date", "Entry Price", "Exit Price",
        "Position", "Quantity", "P&L", "Return %", "Notes"
    ])

# Save trades to JSON file
def save_trades(df):
    with open(DATA_FILE, "w") as f:
        json.dump(df.to_dict(orient="records"), f, indent=4)

# Initialize trades DataFrame
trades = load_trades()

# ----------------------------
# Sidebar Settings
# ----------------------------
st.sidebar.header("Settings")
starting_capital = st.sidebar.number_input("Starting Capital ($)", value=10000.0, step=100.0, format="%.2f")

# ----------------------------
# Trade Logging
# ----------------------------
st.header("📈 Swing Trading Dashboard")

with st.expander("➕ Log New Trade", expanded=True):
    col1, col2, col3 = st.columns(3)
    symbol = col1.text_input("Symbol")
    entry_date = col2.date_input("Entry Date", datetime.today().date())
    exit_date = col3.date_input("Exit Date", datetime.today().date())

    col4, col5, col6 = st.columns(3)
    entry_price = col4.number_input("Entry Price", min_value=0.0, value=0.0, format="%.2f")
    exit_price = col5.number_input("Exit Price", min_value=0.0, value=0.0, format="%.2f")
    position = col6.selectbox("Position", ["Long", "Short"])

    col7, col8 = st.columns(2)
    quantity = col7.number_input("Quantity", min_value=1, value=1, step=1)
    notes = col8.text_input("Notes (Optional)")

    if st.button("Add Trade"):
        if entry_price > 0 and exit_price > 0 and symbol:
            pnl = (exit_price - entry_price) * quantity if position == "Long" else (entry_price - exit_price) * quantity
            ret_pct = (pnl / (entry_price * quantity)) * 100

            new_trade = pd.DataFrame([{
                "Symbol": symbol,
                "Entry Date": entry_date,
                "Exit Date": exit_date,
                "Entry Price": entry_price,
                "Exit Price": exit_price,
                "Position": position,
                "Quantity": quantity,
                "P&L": pnl,
                "Return %": ret_pct,
                "Notes": notes
            }])

            trades = pd.concat([trades, new_trade], ignore_index=True)
            save_trades(trades)
            st.success("✅ Trade added!")

# ----------------------------
# Statistics Dashboard
# ----------------------------
st.subheader("📊 Statistics")

if not trades.empty:
    total_trades = len(trades)
    total_pnl = trades["P&L"].sum()
    win_rate = (trades["P&L"] > 0).mean() * 100
    avg_win = trades.loc[trades["P&L"] > 0, "P&L"].mean() if not trades.loc[trades["P&L"] > 0].empty else 0
    avg_loss = trades.loc[trades["P&L"] < 0, "P&L"].mean() if not trades.loc[trades["P&L"] < 0].empty else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Trades", total_trades)
    col2.metric("Total P&L", f"${total_pnl:,.2f}")
    col3.metric("Win Rate", f"{win_rate:.2f}%")

    col4, col5 = st.columns(2)
    col4.metric("Avg Win", f"${avg_win:,.2f}")
    col5.metric("Avg Loss", f"${avg_loss:,.2f}")

    # ----------------------------
    # Equity Curve
    # ----------------------------
    st.subheader("📈 Equity Curve")

    trades_sorted = trades.sort_values("Exit Date")
    equity = [starting_capital]
    for pnl in trades_sorted["P&L"]:
        equity.append(equity[-1] + pnl)

    fig, ax = plt.subplots()
    ax.plot(trades_sorted["Exit Date"], equity[1:], marker="o")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity ($)")
    ax.set_title("Equity Curve")
    st.pyplot(fig)

    # ----------------------------
    # Trade History Table
    # ----------------------------
    st.subheader("📜 Trade History")
    st.dataframe(trades)

    if st.button("Delete All Trades"):
        trades = trades.iloc[0:0]
        save_trades(trades)
        st.warning("All trades deleted.")

else:
    st.info("No trades logged yet.")

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime
import plotly.graph_objects as go

# ----------------------------
# File for saving trades
# ----------------------------
DATA_FILE = "trades.json"

# Load trades from JSON file
def load_trades():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            df = pd.DataFrame(json.load(f))
            # Convert dates back to datetime
            if not df.empty:
                df["Entry Date"] = pd.to_datetime(df["Entry Date"])
                df["Exit Date"] = pd.to_datetime(df["Exit Date"])
            return df
    return pd.DataFrame(columns=["Symbol", "Entry Date", "Exit Date", "Entry Price", "Exit Price",
                                 "Position", "Quantity", "P&L", "Return %", "Notes"])

# Save trades to JSON file
def save_trades(df):
    with open(DATA_FILE, "w") as f:
        json.dump(df.to_dict(orient="records"), f, indent=4, default=str)

# Initialize trades DataFrame
trades = load_trades()

# ----------------------------
# Sidebar Settings
# ----------------------------
st.sidebar.header("Settings")
starting_capital = st.sidebar.number_input("Starting Capital ($)", value=10000.0, step=1000.0, format="%.2f")

# ----------------------------
# Trade Logging
# ----------------------------
st.title("📈 Swing Trading Dashboard")

with st.expander("➕ Log New Trade", expanded=True):
    col1, col2, col3 = st.columns(3)
    symbol = col1.text_input("Symbol")
    entry_date = col2.date_input("Entry Date", datetime.today())
    exit_date = col3.date_input("Exit Date", datetime.today())

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
# Filters
# ----------------------------
st.subheader("📂 Filter Trades")
symbols = ["All"] + trades["Symbol"].unique().tolist()
selected_symbol = st.selectbox("Symbol", symbols)
date_range = st.date_input("Date Range", [trades["Entry Date"].min() if not trades.empty else datetime.today(),
                                          trades["Exit Date"].max() if not trades.empty else datetime.today()])

filtered_trades = trades.copy()
if selected_symbol != "All":
    filtered_trades = filtered_trades[filtered_trades["Symbol"] == selected_symbol]

filtered_trades = filtered_trades[
    (filtered_trades["Entry Date"] >= pd.to_datetime(date_range[0])) &
    (filtered_trades["Exit Date"] <= pd.to_datetime(date_range[1]))
]

# ----------------------------
# Tabs for Stats, Equity, History
# ----------------------------
tabs = st.tabs(["📊 Metrics", "📈 Equity Curve", "📜 Trade History"])

# ----------------------------
# Metrics Tab
# ----------------------------
with tabs[0]:
    st.subheader("Statistics")
    if not filtered_trades.empty:
        total_trades = len(filtered_trades)
        total_pnl = filtered_trades["P&L"].sum()
        win_rate = (filtered_trades["P&L"] > 0).mean() * 100
        avg_win = filtered_trades.loc[filtered_trades["P&L"] > 0, "P&L"].mean() if not filtered_trades.loc[filtered_trades["P&L"] > 0].empty else 0
        avg_loss = filtered_trades.loc[filtered_trades["P&L"] < 0, "P&L"].mean() if not filtered_trades.loc[filtered_trades["P&L"] < 0].empty else 0

        trades_sorted = filtered_trades.sort_values("Exit Date")
        equity = [starting_capital]
        for pnl in trades_sorted["P&L"]:
            equity.append(equity[-1] + pnl)
        equity_series = pd.Series(equity[1:], index=trades_sorted["Exit Date"])

        # Pro-level metrics
        cumulative_max = equity_series.cummax()
        drawdown = equity_series - cumulative_max
        max_drawdown = drawdown.min()
        max_drawdown_pct = (max_drawdown / cumulative_max.max()) * 100 if cumulative_max.max() != 0 else 0

        returns = equity_series.pct_change().fillna(0)
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0
        holding_days = (trades_sorted["Exit Date"] - trades_sorted["Entry Date"]).dt.days
        avg_holding = holding_days.mean()
        cum_return_pct = ((equity_series[-1] - starting_capital) / starting_capital) * 100 if not equity_series.empty else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Trades", total_trades)
        col2.metric("Total P&L", f"${total_pnl:,.2f}")
        col3.metric("Win Rate", f"{win_rate:.2f}%")

        col4, col5 = st.columns(2)
        col4.metric("Avg Win", f"${avg_win:,.2f}")
        col5.metric("Avg Loss", f"${avg_loss:,.2f}")

        col6, col7, col8 = st.columns(3)
        col6.metric("Max Drawdown", f"${max_drawdown:,.2f}")
        col7.metric("Max Drawdown %", f"{max_drawdown_pct:.2f}%")
        col8.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")

        col9, col10 = st.columns(2)
        col9.metric("Avg Holding (days)", f"{avg_holding:.1f}")
        col10.metric("Cumulative Return %", f"{cum_return_pct:.2f}%")
    else:
        st.info("No trades match the filters.")

# ----------------------------
# Equity Curve Tab
# ----------------------------
with tabs[1]:
    st.subheader("Equity Curve")
    if not filtered_trades.empty:
        fig = go.Figure()
        equity_color = "#1f77b4"
        fig.add_trace(go.Scatter(
            x=equity_series.index,
            y=equity_series.values,
            mode="lines+markers",
            name="Equity",
            line=dict(color=equity_color, width=3),
            hovertemplate='<b>Date:</b> %{x}<br><b>Equity:</b> $%{y:.2f}<br><b>Symbol:</b> %{text}',
            text=trades_sorted["Symbol"]
        ))
        fig.add_trace(go.Scatter(
            x=equity_series.index,
            y=cumulative_max + drawdown,
            fill='tonexty',
            fillcolor='rgba(255,0,0,0.2)',
            line=dict(color='rgba(255,0,0,0)'),
            name="Drawdown"
        ))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trades to plot.")

# ----------------------------
# Trade History Tab
# ----------------------------
with tabs[2]:
    st.subheader("Trade History")
    st.dataframe(filtered_trades.sort_values("Exit Date"))
    if st.button("Delete All Trades"):
        trades = trades.iloc[0:0]
        save_trades(trades)
        st.warning("All trades deleted.")


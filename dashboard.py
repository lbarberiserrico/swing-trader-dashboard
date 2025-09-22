import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import json

# -------------------------
# Initialize session state
# -------------------------
if "trades" not in st.session_state:
    st.session_state.trades = []
if "capital" not in st.session_state:
    st.session_state.capital = 10000  # default starting equity

# -------------------------
# Utility functions
# -------------------------
def calculate_pnl(entry, exit, qty, position, commission=0):
    """Calculate profit/loss for a trade."""
    if position == "Long":
        pnl = (exit - entry) * qty - commission
    else:  # Short
        pnl = (entry - exit) * qty - commission
    return pnl

def calculate_metrics(trades):
    """Compute trading statistics."""
    if not trades:
        return {}

    df = pd.DataFrame(trades)

    wins = df[df["PnL"] > 0]
    losses = df[df["PnL"] <= 0]

    total_pnl = df["PnL"].sum()
    win_rate = len(wins) / len(df) * 100 if len(df) > 0 else 0
    avg_win = wins["PnL"].mean() if not wins.empty else 0
    avg_loss = losses["PnL"].mean() if not losses.empty else 0

    # Sharpe ratio
    returns = df["ReturnPct"] / 100
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

    # Profit Factor
    gross_profit = wins["PnL"].sum()
    gross_loss = abs(losses["PnL"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    # Equity curve
    df["Equity"] = st.session_state.capital + df["PnL"].cumsum()
    max_equity = df["Equity"].cummax()
    drawdowns = df["Equity"] - max_equity
    max_drawdown = drawdowns.min()

    return {
        "total_trades": len(df),
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "sharpe": sharpe,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "equity_curve": df[["ExitDate", "Equity"]]
    }

def save_to_file():
    """Export trades to JSON."""
    return json.dumps(st.session_state.trades, indent=2)

def load_from_file(file_content):
    """Import trades from JSON."""
    st.session_state.trades = json.loads(file_content)

# -------------------------
# Sidebar Settings
# -------------------------
st.sidebar.header("Settings")
st.session_state.capital = st.sidebar.number_input("Starting Capital ($)", min_value=1000, value=st.session_state.capital, step=1000)
commission_default = st.sidebar.number_input("Default Commission ($)", min_value=0.0, value=0.0, step=0.5)

# -------------------------
# Trade Logging
# -------------------------
st.header("📈 Swing Trading Journal")

with st.form("log_trade"):
    st.subheader("Log a New Trade")
    symbol = st.text_input("Symbol").upper()
    position = st.selectbox("Position", ["Long", "Short"])
    qty = st.number_input("Quantity", min_value=1, value=100, step=1)
    entry_date = st.date_input("Entry Date", value=datetime.date.today())
    entry_price = st.number_input("Entry Price", min_value=0.0, value=100.0, step=0.01)
    exit_date = st.date_input("Exit Date", value=datetime.date.today())
    exit_price = st.number_input("Exit Price", min_value=0.0, value=100.0, step=0.01)
    notes = st.text_area("Notes (optional)")
    commission = st.number_input("Commission/Fees", min_value=0.0, value=commission_default, step=0.01)

    submitted = st.form_submit_button("Add Trade")
    if submitted:
        pnl = calculate_pnl(entry_price, exit_price, qty, position, commission)
        return_pct = (pnl / (entry_price * qty)) * 100
        trade = {
            "Symbol": symbol,
            "Position": position,
            "Quantity": qty,
            "EntryDate": str(entry_date),
            "EntryPrice": entry_price,
            "ExitDate": str(exit_date),
            "ExitPrice": exit_price,
            "PnL": pnl,
            "ReturnPct": return_pct,
            "Notes": notes
        }
        st.session_state.trades.append(trade)
        st.success(f"Trade for {symbol} added!")

# -------------------------
# Statistics Dashboard
# -------------------------
st.subheader("📊 Statistics Dashboard")
metrics = calculate_metrics(st.session_state.trades)

if metrics:
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Trades", metrics["total_trades"])
    col2.metric("Total P&L", f"${metrics['total_pnl']:,.2f}")
    col3.metric("Win Rate", f"{metrics['win_rate']:.1f}%")

    col4, col5, col6 = st.columns(3)
    col4.metric("Average Win", f"${metrics['avg_win']:,.2f}")
    col5.metric("Average Loss", f"${metrics['avg_loss']:,.2f}")
    col6.metric("Sharpe Ratio", f"{metrics['sharpe']:.2f}")

    col7, col8 = st.columns(2)
    col7.metric("Profit Factor", f"{metrics['profit_factor']:.2f}")
    col8.metric("Max Drawdown", f"${metrics['max_drawdown']:,.2f}")

# -------------------------
# Equity Curve Chart
# -------------------------
if metrics and not metrics["equity_curve"].empty:
    st.subheader("💰 Equity Curve")
    eq_df = metrics["equity_curve"]
    fig, ax = plt.subplots()
    ax.plot(eq_df["ExitDate"], eq_df["Equity"], marker="o")
    ax.set_title("Equity Curve")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity ($)")
    plt.xticks(rotation=45)
    st.pyplot(fig)

# -------------------------
# Trade History
# -------------------------
st.subheader("📜 Trade History")

if st.session_state.trades:
    df = pd.DataFrame(st.session_state.trades)
    st.dataframe(df)

    # Export button
    st.download_button(
        label="Export Trades (JSON)",
        data=save_to_file(),
        file_name="trades.json",
        mime="application/json"
    )

    # Import button
    uploaded = st.file_uploader("Import Trades (JSON)", type="json")
    if uploaded:
        load_from_file(uploaded.read().decode())
        st.success("Trades imported successfully!")

else:
    st.info("No trades logged yet.")

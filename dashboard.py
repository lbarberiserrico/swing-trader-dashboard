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
starting_capital = st.sidebar.number_input(
    "Starting Capital ($)", value=10000.0, step=100.0, format="%.2f"
)

# ----------------------------
# Auto Import Trades
# ----------------------------
st.sidebar.subheader("📂 Import Trades")

uploaded_file = st.sidebar.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            imported_df = pd.read_csv(uploaded_file)
        else:
            imported_df = pd.read_excel(uploaded_file)

        # Standardize column names
        imported_df.columns = imported_df.columns.str.strip().str.title()

        # Expected minimum columns
        required_cols = [
            "Symbol", "Entry Date", "Exit Date",
            "Entry Price", "Exit Price", "Quantity", "Position"
        ]
        if all(col in imported_df.columns for col in required_cols):

            # Convert dates
            imported_df["Entry Date"] = pd.to_datetime(imported_df["Entry Date"]).dt.date
            imported_df["Exit Date"] = pd.to_datetime(imported_df["Exit Date"]).dt.date

            # Calculate P&L and Return %
            def calc_pnl(row):
                if row["Position"].lower() == "long":
                    return (row["Exit Price"] - row["Entry Price"]) * row["Quantity"]
                else:
                    return (row["Entry Price"] - row["Exit Price"]) * row["Quantity"]

            imported_df["P&L"] = imported_df.apply(calc_pnl, axis=1)
            imported_df["Return %"] = (
                imported_df["P&L"] / (imported_df["Entry Price"] * imported_df["Quantity"])
            ) * 100

            if "Notes" not in imported_df.columns:
                imported_df["Notes"] = ""

            # Prevent duplicates
            before_count = len(trades)
            trades = pd.concat([trades, imported_df], ignore_index=True).drop_duplicates(
                subset=["Symbol", "Entry Date", "Exit Date"], keep="last"
            )
            save_trades(trades)

            added_count = len(trades) - before_count
            st.sidebar.success(f"✅ Imported {added_count} new trades!")

        else:
            st.sidebar.error("❌ File must include columns: " + ", ".join(required_cols))

    except Exception as e:
        st.sidebar.error(f"⚠️ Error importing file: {e}")

# ----------------------------
# Trade Logging
# ----------------------------
st.header("📈 Swing Trading Dashboard")

with st.expander("➕ Log New Trade", expanded=True):
    col1, col2, col3 = st.columns(3)
    symbol = col1.text_input("Symbol")
    entry_date = col2.date_input("Entry Date", datetime.today().date())
    exit_date = col3.date_input

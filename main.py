# IT 4320 Project 3
# Aidan Engbert
# Pranav Malatkar
# Grant Wiedeman
# NAME

import os
import time
import json
import tempfile
import webbrowser
from datetime import datetime
import requests
import pandas as pd
import matplotlib.pyplot as plt

# ---------- API CONFIG ----------
API_KEY = "Y1VTX9XT399MJE42"
BASE_URL = "https://www.alphavantage.co/query"

TIME_SERIES_MAP = {
    "1": {"fn": "TIME_SERIES_INTRADAY", "params": {"interval": "5min"}},
    "2": {"fn": "TIME_SERIES_DAILY_ADJUSTED", "params": {}},
    "3": {"fn": "TIME_SERIES_WEEKLY_ADJUSTED", "params": {}},
    "4": {"fn": "TIME_SERIES_MONTHLY_ADJUSTED", "params": {}},
}


# ---------- VALIDATION FUNCTIONS ----------
def Stock_Name_Check(name):
    return 1 if name.isalpha() and len(name) <= 5 else 0


def Chart_Type(chart_type):
    return 1 if chart_type in ["1", "2"] else 0


def Time_Series(time_type):
    return 1 if time_type in ["1", "2", "3", "4"] else 0


def Dates(START, END):
    """Validate dates, attempt common reformats, and swap if necessary."""
    def try_parse(date_str):
        formats = ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%m-%d-%Y", "%m/%d/%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    start = try_parse(START)
    end = try_parse(END)

    if not start or not end:
        print("Invalid date format. Please use YYYY-MM-DD or common variants (DD-MM-YYYY, MM/DD/YYYY, etc.).")
        return 0, None, None

    if start > end:
        print(f"Warning: Start date ({start.date()}) is after end date ({end.date()}). Swapping them.")
        start, end = end, start

    return 1, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


# ---------- CORE DATA + CHART FUNCTIONS ----------
def fetch_alpha_vantage_ohlc(symbol: str, ts_choice: str) -> pd.DataFrame:
    cfg = TIME_SERIES_MAP[ts_choice]
    params = {"function": cfg["fn"], "symbol": symbol, "apikey": API_KEY, **cfg["params"]}
    if cfg["fn"] != "TIME_SERIES_INTRADAY":
        params["outputsize"] = "full"

    def _call():
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    data = _call()
    if "Note" in data:
        print("\nAPI limit reached — waiting 60 seconds before retry...\n")
        time.sleep(60)
        data = _call()
    if "Error Message" in data:
        raise RuntimeError(f"API error: {data['Error Message']}")

    # Dynamic key detection
    json_key = next((k for k in data.keys() if "Time Series" in k), None)
    if not json_key:
        preview = json.dumps(data, indent=2)[:800]
        raise RuntimeError(f"Unexpected API response. No 'Time Series' key found.\nPreview:\n{preview}")

    df_raw = pd.DataFrame(data[json_key]).T
    df_raw.index = pd.to_datetime(df_raw.index)

    df = _parse_ohlc_columns(df_raw)
    return df.sort_index()


def _parse_ohlc_columns(df_raw: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df_raw.index)

    def pick_first(fragment):
        for c in df_raw.columns:
            if fragment in c.lower():
                return c
        return None

    for name, frag in [("Open", " open"), ("High", " high"), ("Low", " low")]:
        col = pick_first(frag)
        if col:
            out[name] = pd.to_numeric(df_raw[col], errors="coerce")

    close_col = pick_first("adjusted close") or pick_first(" close")
    if close_col:
        out["Close"] = pd.to_numeric(df_raw[close_col], errors="coerce")

    out = out.dropna(axis=1, how="all")
    return out


def filter_by_date(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    start_d = pd.to_datetime(start)
    end_d = pd.to_datetime(end)
    df_filtered = df.loc[(df.index >= start_d) & (df.index <= end_d)]
    if df_filtered.empty:
        raise RuntimeError("No data found in that date range.")
    return df_filtered


def Graph(data: dict):
    symbol = data["stock"]
    ts_choice = data["time_type"]
    start_date = data["start"]
    end_date = data["end"]

    df_all = fetch_alpha_vantage_ohlc(symbol, ts_choice)
    df = filter_by_date(df_all, start_date, end_date)
    return df


def Open_Browser(df_info: dict):
    df = df_info["df"]
    symbol = df_info["symbol"]
    start_date = df_info["start"]
    end_date = df_info["end"]

    ohlc_cols = [c for c in ["Open", "High", "Low", "Close"] if c in df.columns]

    plt.figure(figsize=(12, 6))
    for col in ohlc_cols:
        plt.plot(df.index, df[col], marker="o", linewidth=1.3, markersize=3, label=col)

    plt.title(f"{symbol} Stock Prices: {start_date} to {end_date}")
    plt.xlabel("Date")
    plt.ylabel("Price (USD)")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()

    tmpdir = tempfile.mkdtemp(prefix="stock_chart_")
    img_path = os.path.join(tmpdir, "chart.png")
    html_path = os.path.join(tmpdir, "chart.html")
    plt.savefig(img_path, dpi=150)
    plt.close()

    with open(html_path, "w") as f:
        f.write(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{symbol} Stock Chart</title></head>
<body><h2>{symbol} Stock Data: {start_date} to {end_date}</h2>
<img src="{os.path.basename(img_path)}" alt="chart"></body></html>""")

    webbrowser.open(f"file://{os.path.abspath(html_path)}", new=2)
    return 1


# ---------- MAIN FUNCTION ----------
def main():
    print("********** Stock Data Chart Generator **********")

    # Stock Name
    Stock_Name = input("Enter Stock Symbol (e.g., AAPL, MSFT): ").upper()
    if not Stock_Name_Check(Stock_Name):
        print("Invalid stock symbol.")
        return

    # Chart Type
    print("\nSelect Chart Type:")
    print("1. Line Chart")
    print("2. Bar Chart")
    chart_type = input("Enter your choice (1 or 2): ")
    if not Chart_Type(chart_type):
        print("Invalid chart type.")
        return

    # Time Series
    print("\nSelect Time Series:")
    print("1. Intraday")
    print("2. Daily")
    print("3. Weekly")
    print("4. Monthly")
    time_type = input("Enter your choice (1, 2, 3, 4): ")
    if not Time_Series(time_type):
        print("Invalid time series.")
        return

    # Dates
    input_start = input("Enter start date: ")
    input_end = input("Enter end date: ")
    status, start_date, end_date = Dates(input_start, input_end)
    if not status:
        return

    try:
        df = Graph({
            "stock": Stock_Name,
            "chart_type": chart_type,
            "time_type": time_type,
            "start": start_date,
            "end": end_date
        })
        Open_Browser({"df": df, "symbol": Stock_Name, "start": start_date, "end": end_date})
        print("\nChart successfully generated and opened in your browser!")
    except Exception as e:
        print("\nERROR:", e)


if __name__ == "__main__":
    main()

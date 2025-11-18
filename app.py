## IT 4320 Project 3b
# Aidan Engbert
# Grant Wiedeman
# NAME
# NAME

import os
from flask import Flask, render_template, request, jsonify, url_for
import requests
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

# Alpha Vantage settings
API_KEY = "Y1VTX9XT399MJE42"
AV_BASE = "https://www.alphavantage.co/query"

app = Flask(__name__, static_folder="static", template_folder="templates")


# ---------------------------------------------------------------------
# Helper: load fallback symbols from stocks.csv (or a small list)
# ---------------------------------------------------------------------
def load_fallback_symbols():
    """
    Load a list of symbols from stocks.csv.

    Returns a list of dicts shaped like Alpha Vantage results:
    [
        {"1. symbol": "AAPL", "2. name": "Apple Inc."},
        ...
    ]
    """
    symbols = []
    csv_path = os.path.join(os.path.dirname(__file__), "stocks.csv")

    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                sym = str(row.get("Symbol") or row.get("symbol") or "").strip()
                name = str(row.get("Name") or row.get("name") or sym).strip()
                if sym:
                    symbols.append({"1. symbol": sym, "2. name": name})
        except Exception as e:
            print(f"Error loading stocks.csv: {e}")

    # If csv missing or broken, fall back to a small hard-coded list
    if not symbols:
        symbols = [
            {"1. symbol": "AAPL", "2. name": "Apple Inc."},
            {"1. symbol": "MSFT", "2. name": "Microsoft Corporation"},
            {"1. symbol": "GOOGL", "2. name": "Alphabet Inc. Class A"},
            {"1. symbol": "AMZN", "2. name": "Amazon.com Inc."},
        ]

    return symbols


FALLBACK_SYMBOLS = load_fallback_symbols()


# ---------------------------------------------------------------------
# Alpha Vantage functions
# ---------------------------------------------------------------------
def alphavantage_symbol_search(keywords):
    """Call Alpha Vantage SYMBOL_SEARCH. Returns list of matches."""
    if not API_KEY:
        raise RuntimeError("ALPHAVANTAGE_API_KEY not set")

    params = {
        "function": "SYMBOL_SEARCH",
        "keywords": keywords,
        "apikey": API_KEY
    }
    r = requests.get(AV_BASE, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    matches = data.get("bestMatches") or []
    return matches


def alphavantage_daily_series(symbol, outputsize="compact"):
    """Call Alpha Vantage TIME_SERIES_DAILY_ADJUSTED and return JSON."""
    if not API_KEY:
        raise RuntimeError("ALPHAVANTAGE_API_KEY not set")

    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": symbol,
        "outputsize": outputsize,
        "apikey": API_KEY
    }
    r = requests.get(AV_BASE, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------
# Main page (GET shows form, POST generates chart)
# ---------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    chart_url = None
    error = None
    selected_symbol = None

    if request.method == "POST":
        # symbol from dropdown OR free-text box
        selected_symbol = request.form.get("symbol") or request.form.get("symbol_text")
        if selected_symbol and " " in selected_symbol:
            selected_symbol = selected_symbol.split()[0].strip()

        chart_type = request.form.get("chart_type")  # e.g. "line", "bar"
        time_series = request.form.get("time_series")  # e.g. "daily"
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")

        # ------------------------
        # Input error checks
        # ------------------------
        if not selected_symbol:
            error = "No stock symbol provided."

        allowed_chart_types = {"line", "bar"}
        if not error and chart_type:
            if chart_type not in allowed_chart_types:
                error = "Invalid chart type selected."

        allowed_time_series = {"daily", "weekly", "monthly"}
        if not error and time_series:
            if time_series not in allowed_time_series:
                error = "Invalid time series selected."

        start_date = end_date = None
        if not error and start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except ValueError:
                error = "Start Date must be in YYYY-MM-DD format."

        if not error and end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                error = "End Date must be in YYYY-MM-DD format."

        if not error and start_date and end_date and end_date < start_date:
            error = "End Date must be after Start Date."

        # ------------------------
        # If no errors, call API and build chart
        # ------------------------
        if not error:
            try:
                av = alphavantage_daily_series(selected_symbol, outputsize="compact")

                ts_key = None
                for k in av.keys():
                    if "Time Series" in k:
                        ts_key = k
                        break
                if not ts_key:
                    msg = av.get("Note") or av.get("Error Message") or "Unexpected API response from Alpha Vantage."
                    raise RuntimeError(msg)

                df = pd.DataFrame.from_dict(av[ts_key], orient="index")
                df = df.sort_index()

                if "5. adjusted close" in df.columns:
                    close_col = "5. adjusted close"
                elif "4. close" in df.columns:
                    close_col = "4. close"
                else:
                    raise RuntimeError("Cannot find close prices in API response.")

                df.index = pd.to_datetime(df.index)
                df[close_col] = pd.to_numeric(df[close_col], errors="coerce")

                if start_date and end_date:
                    df = df.loc[start_date_str:end_date_str]

                plt.figure(figsize=(10, 4))
                if chart_type == "bar":
                    plt.bar(df.index, df[close_col])
                else:
                    plt.plot(df.index, df[close_col])

                plt.title(f"{selected_symbol} - Closing Price")
                plt.xlabel("Date")
                plt.ylabel("Price (USD)")
                plt.tight_layout()

                chart_path = os.path.join(app.static_folder, "chart.png")
                plt.savefig(chart_path)
                plt.close()

                chart_url = url_for("static", filename="chart.png") + f"?t={int(datetime.now().timestamp())}"

            except Exception as e:
                error = str(e)

    return render_template(
        "index.html",
        symbols=FALLBACK_SYMBOLS,
        chart_url=chart_url,
        error=error,
        selected_symbol=selected_symbol,
    )


# ---------------------------------------------------------------------
# AJAX endpoint for live symbol search (optional)
# ---------------------------------------------------------------------
@app.route("/search_symbols")
def search_symbols():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([{"symbol": m["1. symbol"], "name": m["2. name"]} for m in FALLBACK_SYMBOLS])

    try:
        matches = alphavantage_symbol_search(q)
        results = []
        for m in matches:
            results.append({"symbol": m.get("1. symbol"), "name": m.get("2. name")})

        if not results:
            results = [{"symbol": m["1. symbol"], "name": m["2. name"]} for m in FALLBACK_SYMBOLS]

        return jsonify(results)
    except Exception as e:
        print(f"Error in /search_symbols: {e}")
        return jsonify([{"symbol": m["1. symbol"], "name": m["2. name"]} for m in FALLBACK_SYMBOLS]), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")

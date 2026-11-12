"""Reconstitue les cours ajustés de fin de mois à partir des clôtures quotidiennes."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
from urllib.request import Request, urlopen
import pandas as pd

TICKERS = ["SPY", "AGG", "GLD", "VNQ"]
ROOT = Path(__file__).resolve().parent

def prices(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    request = Request(url + "?period1=1262304000&period2=1767225600&interval=1d",
                      headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=45) as response:
        chart = json.load(response)["chart"]["result"][0]
    index = pd.to_datetime(chart["timestamp"], unit="s", utc=True).tz_convert("America/New_York")
    daily = pd.Series(chart["indicators"]["adjclose"][0]["adjclose"], index=index, name=ticker)
    return daily.groupby(daily.index.strftime("%Y-%m")).last()

if __name__ == "__main__":
    with ThreadPoolExecutor(4) as pool:
        panel = pd.concat(list(pool.map(prices, TICKERS)), axis=1)
    expected = pd.period_range("2010-01", "2025-12", freq="M").astype(str)
    assert panel.index.equals(pd.Index(expected)) and (panel > 0).all().all()
    panel.to_csv(ROOT / "data/prices.csv", index_label="Mois")

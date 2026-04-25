"""Daily Market Scanner — see file header for full docs."""

from __future__ import annotations

import argparse
import sys
import time
import warnings
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")

STOCK_PCT_OF_52W_HIGH = 0.98
STOCK_VOL_SURGE_MIN   = 1.30
STOCK_HISTORY_DAYS    = "1y"
CRYPTO_RSI_MIN        = 55
CRYPTO_RSI_MAX        = 75
CRYPTO_VOL_SURGE_MIN  = 1.50
SCANNER_TOP_N         = 10
REPORTS_DIR           = Path("reports")
WATCHLIST_DIR         = Path("watchlist")
TEMP_STOCKS_FILE      = WATCHLIST_DIR / "scanned_stocks.txt"
TEMP_CRYPTO_FILE      = WATCHLIST_DIR / "scanned_crypto.txt"
STABLECOIN_SYMBOLS = {
    "USDT", "USDC", "DAI", "BUSD", "TUSD", "USDP", "FRAX", "LUSD",
    "USDE", "FDUSD", "PYUSD", "USDD", "GUSD", "SUSD", "USD1",
}
WRAPPED_SYMBOLS = {"WBTC", "WETH", "STETH", "WSTETH", "WEETH", "CBETH", "RETH"}
CRYPTO_EXCLUDE = STABLECOIN_SYMBOLS | WRAPPED_SYMBOLS
USER_AGENT    = "Mozilla/5.0 (compatible; trading-bot-scanner/2.0)"
HTTP_TIMEOUT  = 20
COINGECKO_API_KEY     = ""
COINGECKO_DELAY       = 2.5
COINGECKO_MAX_RETRIES = 3
COINGECKO_BASE_WAIT   = 30
WIKIPEDIA_DELAY       = 3.0

try:
    import config as _cfg
    STOCK_PCT_OF_52W_HIGH   = _cfg.STOCK_PCT_OF_52W_HIGH
    STOCK_VOL_SURGE_MIN     = _cfg.STOCK_VOL_SURGE_MIN
    STOCK_HISTORY_DAYS      = _cfg.STOCK_HISTORY_DAYS
    CRYPTO_RSI_MIN          = _cfg.CRYPTO_RSI_MIN
    CRYPTO_RSI_MAX          = _cfg.CRYPTO_RSI_MAX
    CRYPTO_VOL_SURGE_MIN    = _cfg.CRYPTO_VOL_SURGE_MIN
    COINGECKO_API_KEY       = _cfg.COINGECKO_API_KEY
    COINGECKO_DELAY         = _cfg.COINGECKO_DELAY
    COINGECKO_MAX_RETRIES   = _cfg.COINGECKO_MAX_RETRIES
    COINGECKO_BASE_WAIT     = _cfg.COINGECKO_BASE_WAIT
    WIKIPEDIA_DELAY         = _cfg.WIKIPEDIA_DELAY
    SCANNER_TOP_N           = _cfg.SCANNER_TOP_N
    REPORTS_DIR             = Path(_cfg.SCANNER_REPORTS_DIR)
    WATCHLIST_DIR           = Path(_cfg.SCANNER_WATCHLIST_DIR)
    TEMP_STOCKS_FILE        = Path(_cfg.TEMP_STOCKS_FILE)
    TEMP_CRYPTO_FILE        = Path(_cfg.TEMP_CRYPTO_FILE)
except (ImportError, AttributeError):
    pass

FALLBACK_TICKERS = [
    "AAPL","MSFT","NVDA","GOOGL","GOOG","AMZN","META","TSLA","AVGO","LLY",
    "JPM","V","UNH","XOM","WMT","MA","JNJ","PG","HD","COST","ORCL","ABBV",
    "CVX","MRK","BAC","KO","PEP","NFLX","TMO","ADBE","CSCO","CRM","AMD",
    "ABT","LIN","WFC","DIS","ACN","MCD","TXN","DHR","INTU","VZ","NEE","PM",
    "INTC","AMGN","QCOM","IBM","CAT","GS","PFE","NOW","UNP","T","LOW","SPGI",
    "HON","NKE","AXP","RTX","UPS","BLK","BKNG","SCHW","BA","MDT","DE","GE",
    "PLD","ELV","SBUX","TJX","MDLZ","LMT","ADP","GILD","MMC","ISRG","CVS",
    "C","SYK","REGN","ZTS","VRTX","CB","ADI","AMAT","MU","LRCX","KLAC",
    "PANW","ANET","MRNA","MELI","PYPL","SNOW","CRWD","SHOP","ABNB","UBER",
    "COIN","PLTR","SMCI","ARM","APP","ASML","TSM","BIDU","JD","PDD","BABA",
]


def resolve_output_path(name: Optional[str]) -> Path:
    today = datetime.now().strftime("%m-%d-%Y")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if not name:
        return REPORTS_DIR / f"{today}-market_scan.csv"
    p = Path(name)
    stem = p.stem
    if len(stem) >= 11 and stem[2] == "-" and stem[5] == "-" and stem[9] == "-":
        return REPORTS_DIR / f"{stem}.csv"
    return REPORTS_DIR / f"{today}-{stem}.csv"


def fetch_stock_universe() -> list[str]:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    try:
        print("Fetching S&P 500 list from Wikipedia...", file=sys.stderr)
        resp = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers=headers, timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        sp500 = pd.read_html(StringIO(resp.text))[0]
        sp500_tickers = sp500["Symbol"].astype(str).tolist()
        time.sleep(WIKIPEDIA_DELAY)
        print("Fetching Nasdaq 100 list from Wikipedia...", file=sys.stderr)
        resp2 = requests.get(
            "https://en.wikipedia.org/wiki/Nasdaq-100",
            headers=headers, timeout=HTTP_TIMEOUT,
        )
        resp2.raise_for_status()
        ndx_tables = pd.read_html(StringIO(resp2.text))
        ndx_tickers: list[str] = []
        for t in ndx_tables:
            cols = [str(c) for c in t.columns]
            sym_col = next((c for c in ("Ticker", "Symbol") if c in cols), None)
            if sym_col and 80 <= len(t) <= 110:
                ndx_tickers = t[sym_col].astype(str).tolist()
                break
        combined = sorted(set(sp500_tickers) | set(ndx_tickers))
        combined = [s.replace(".", "-").strip() for s in combined if s and s != "nan"]
        print(f"Universe: {len(combined)} tickers from Wikipedia", file=sys.stderr)
        return combined
    except Exception as e:
        print(f"Wikipedia fetch failed ({e}); using fallback universe of {len(FALLBACK_TICKERS)} large caps.", file=sys.stderr)
        return FALLBACK_TICKERS.copy()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs    = gain / loss
    return 100 - 100 / (1 + rs)


def _coingecko_headers() -> dict:
    h = {"User-Agent": USER_AGENT}
    if COINGECKO_API_KEY:
        h["x-cg-demo-api-key"] = COINGECKO_API_KEY
    return h


def coingecko_get(url: str, params: Optional[dict] = None) -> Optional[dict | list]:
    wait = COINGECKO_BASE_WAIT
    for attempt in range(COINGECKO_MAX_RETRIES + 1):
        try:
            r = requests.get(url, params=params, headers=_coingecko_headers(), timeout=HTTP_TIMEOUT)
            if r.status_code == 429:
                if attempt < COINGECKO_MAX_RETRIES:
                    print(f"  CoinGecko rate-limited (429); waiting {wait}s (retry {attempt + 1}/{COINGECKO_MAX_RETRIES})...", file=sys.stderr)
                    time.sleep(wait)
                    wait *= 2
                    continue
                print("  CoinGecko: max retries reached on rate limit.", file=sys.stderr)
                return None
            r.raise_for_status()
            payload = r.json()
            if isinstance(payload, dict) and "status" in payload and "error_code" in payload.get("status", {}):
                print(f"  CoinGecko API error: {payload['status']}", file=sys.stderr)
                return None
            return payload
        except requests.exceptions.Timeout:
            print(f"  CoinGecko timeout on attempt {attempt + 1}", file=sys.stderr)
            if attempt < COINGECKO_MAX_RETRIES:
                time.sleep(wait)
                wait *= 2
        except requests.exceptions.RequestException as e:
            print(f"  CoinGecko request failed: {e}", file=sys.stderr)
            if attempt < COINGECKO_MAX_RETRIES:
                time.sleep(wait)
                wait *= 2
    return None


def scan_stocks(top_n: int = SCANNER_TOP_N, tickers: Optional[list[str]] = None) -> pd.DataFrame:
    import yfinance as yf
    if tickers is None:
        tickers = fetch_stock_universe()
    print(f"Downloading daily bars for {len(tickers)} tickers...", file=sys.stderr)
    data = yf.download(tickers, period=STOCK_HISTORY_DAYS, interval="1d", progress=False, auto_adjust=True, group_by="ticker", threads=True)
    results: list[dict] = []
    for t in tickers:
        try:
            df = data[t] if t in data.columns.get_level_values(0) else data
            df = df.dropna()
            if len(df) < 200:
                continue
            close      = df["Close"]
            vol        = df["Volume"]
            high       = df["High"]
            last_close = float(close.iloc[-1])
            prev_close = float(close.iloc[-2])
            high_52w   = float(high.tail(252).max())
            ema21      = float(close.ewm(span=21, adjust=False).mean().iloc[-1])
            sma200     = float(close.rolling(200).mean().iloc[-1])
            avg_vol_30 = float(vol.tail(30).mean())
            last_vol   = float(vol.iloc[-1])
            vol_surge  = last_vol / avg_vol_30 if avg_vol_30 > 0 else 0.0
            rsi_14     = float(rsi(close).iloc[-1])
            if not (last_close >= high_52w * STOCK_PCT_OF_52W_HIGH and ema21 > sma200 and vol_surge >= STOCK_VOL_SURGE_MIN and last_close > prev_close):
                continue
            pct_above_sma = (last_close - sma200) / sma200 * 100
            pct_from_52w  = (last_close / high_52w - 1) * 100
            score         = vol_surge * max(pct_above_sma, 0)
            results.append({
                "Ticker": t, "Price": round(last_close, 2), "Vol Change": round(vol_surge, 2),
                "RSI": round(rsi_14, 1), "% from 52W High": round(pct_from_52w, 2),
                "% vs 200SMA": round(pct_above_sma, 1), "Score": round(score, 2),
                "Bullish Reason": f"Within {abs(pct_from_52w):.1f}% of 52W high on {vol_surge:.1f}x avg volume, trending {pct_above_sma:.0f}% above 200-day MA.",
            })
        except Exception:
            continue
    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results).sort_values("Score", ascending=False).head(top_n).reset_index(drop=True)


def fetch_kraken_funding_rates() -> dict[str, float]:
    try:
        r = requests.get("https://futures.kraken.com/derivatives/api/v3/tickers", headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT)
        tickers = r.json().get("tickers", [])
    except Exception as e:
        print(f"Kraken funding fetch failed: {e}", file=sys.stderr)
        return {}
    out: dict[str, float] = {}
    for t in tickers:
        sym = t.get("symbol", "")
        if not (sym.startswith("PF_") and sym.endswith("USD")):
            continue
        base = sym[3:-3]
        if base == "XBT":
            base = "BTC"
        fr = t.get("fundingRate")
        mark = t.get("markPrice")
        if fr is None or mark is None or mark == 0:
            continue
        out[base] = float(fr) / float(mark) * 100
    return out


def scan_crypto(top_n: int = SCANNER_TOP_N) -> pd.DataFrame:
    markets = coingecko_get(
        "https://api.coingecko.com/api/v3/coins/markets",
        {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 50, "page": 1, "sparkline": "false", "price_change_percentage": "24h"},
    )
    if not markets or not isinstance(markets, list):
        print("Crypto scan aborted: could not fetch market data from CoinGecko.", file=sys.stderr)
        return pd.DataFrame()
    funding_map = fetch_kraken_funding_rates()
    excluded_count = len(CRYPTO_EXCLUDE & {c["symbol"].upper() for c in markets})
    print(f"Scanning top 50 crypto ({excluded_count} stablecoins/wrapped excluded)...", file=sys.stderr)
    results: list[dict] = []
    for coin in markets:
        sym = coin["symbol"].upper()
        if sym in CRYPTO_EXCLUDE:
            continue
        payload = coingecko_get(
            f"https://api.coingecko.com/api/v3/coins/{coin['id']}/market_chart",
            {"vs_currency": "usd", "days": "30", "interval": "daily"},
        )
        time.sleep(COINGECKO_DELAY)
        if not payload or not isinstance(payload, dict):
            continue
        try:
            prices  = payload.get("prices", [])
            volumes = payload.get("total_volumes", [])
            if len(prices) < 20 or len(volumes) < 8:
                continue
            closes     = pd.Series([p[1] for p in prices])
            vols       = pd.Series([v[1] for v in volumes])
            rsi_14     = float(rsi(closes).iloc[-1])
            vol_24h    = float(vols.iloc[-1])
            avg_vol_7d = float(vols.iloc[-8:-1].mean())
            vol_surge  = vol_24h / avg_vol_7d if avg_vol_7d > 0 else 0.0
            change_24h = float(coin.get("price_change_percentage_24h") or 0)
            if not (CRYPTO_RSI_MIN <= rsi_14 <= CRYPTO_RSI_MAX and vol_surge >= CRYPTO_VOL_SURGE_MIN and change_24h > 0):
                continue
            funding_pct  = funding_map.get(sym)
            funding_flag = ""
            if funding_pct is not None:
                annualized = funding_pct * 24 * 365
                if annualized > 20:
                    funding_flag = " | \u26a0 crowded longs (high funding)"
                elif annualized < -20:
                    funding_flag = " | shorts paying (contrarian long setup)"
            score = vol_surge * (rsi_14 - 50)
            results.append({
                "Ticker": sym,
                "Price": round(coin["current_price"], 6 if coin["current_price"] < 1 else 2),
                "Vol Change": round(vol_surge, 2), "RSI": round(rsi_14, 1),
                "24h %": round(change_24h, 2),
                "Funding %": round(funding_pct, 4) if funding_pct is not None else None,
                "Score": round(score, 2),
                "Bullish Reason": f"+{change_24h:.1f}% on {vol_surge:.1f}x 7d-avg volume with RSI at {rsi_14:.0f} (momentum zone){funding_flag}.",
            })
        except Exception:
            continue
    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results).sort_values("Score", ascending=False).head(top_n).reset_index(drop=True)


def save_watchlist_temps(stock_df: pd.DataFrame, crypto_df: pd.DataFrame) -> None:
    WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)
    if not stock_df.empty:
        tickers = stock_df["Ticker"].tolist()
        TEMP_STOCKS_FILE.write_text("\n".join(tickers))
        print(f"Watchlist temp written: {TEMP_STOCKS_FILE} ({len(tickers)} stocks)", file=sys.stderr)
    else:
        TEMP_STOCKS_FILE.write_text("")
    if not crypto_df.empty:
        pairs = [f"{sym}/USD" for sym in crypto_df["Ticker"].tolist()]
        TEMP_CRYPTO_FILE.write_text("\n".join(pairs))
        print(f"Watchlist temp written: {TEMP_CRYPTO_FILE} ({len(pairs)} crypto)", file=sys.stderr)
    else:
        TEMP_CRYPTO_FILE.write_text("")


def load_watchlist_temps() -> tuple[list[str], list[str]]:
    stocks: list[str] = []
    crypto: list[str] = []
    if TEMP_STOCKS_FILE.exists():
        content = TEMP_STOCKS_FILE.read_text().strip()
        stocks = [t for t in content.splitlines() if t.strip()]
    if TEMP_CRYPTO_FILE.exists():
        content = TEMP_CRYPTO_FILE.read_text().strip()
        crypto = [t for t in content.splitlines() if t.strip()]
    return stocks, crypto


def print_table(title: str, df: pd.DataFrame) -> None:
    bar = "=" * 100
    print(f"\n{bar}\n{title}\n{bar}")
    if df.empty:
        print("  No results matched the filter criteria.")
        return
    print(df.drop(columns=["Score"], errors="ignore").to_string(index=False))


def save_csv(stock_df: pd.DataFrame, crypto_df: pd.DataFrame, output_path: Path) -> None:
    frames = []
    if not stock_df.empty:
        s = stock_df.copy()
        s.insert(0, "AssetClass", "Stock")
        frames.append(s)
    if not crypto_df.empty:
        c = crypto_df.copy()
        c.insert(0, "AssetClass", "Crypto")
        frames.append(c)
    if frames:
        pd.concat(frames, ignore_index=True).to_csv(output_path, index=False)
        print(f"\nResults saved to: {output_path}", file=sys.stderr)
    else:
        print("\nNo results to save.", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily stock + crypto momentum scanner.")
    parser.add_argument("--top", type=int, default=SCANNER_TOP_N)
    parser.add_argument("--stocks-only", action="store_true")
    parser.add_argument("--crypto-only",  action="store_true")
    parser.add_argument("--output", "-o", type=str, default=None)
    args = parser.parse_args()
    stock_df  = pd.DataFrame()
    crypto_df = pd.DataFrame()
    if not args.crypto_only:
        stock_df = scan_stocks(top_n=args.top)
        print_table(f"TOP {args.top} STOCKS (S&P 500 + Nasdaq 100)", stock_df)
    if not args.stocks_only:
        crypto_df = scan_crypto(top_n=args.top)
        print_table(f"TOP {args.top} CRYPTO (Top 50 by market cap)", crypto_df)
    output_path = resolve_output_path(args.output)
    save_csv(stock_df, crypto_df, output_path)
    save_watchlist_temps(stock_df, crypto_df)
    return 0


if __name__ == "__main__":
    sys.exit(main())

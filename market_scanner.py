"""
Daily Market Scanner — Stocks + Crypto
=======================================
Scans the S&P 500 + Nasdaq 100 for momentum stock setups, and the top 50
cryptocurrencies for momentum crypto setups, ranking the top 10 of each.

Stock filter:
  - Price within 2% of 52-week high
  - 21 EMA > 200 SMA (trend confirmation)
  - Today's volume >= 1.3x 30-day average
  - Today's close > yesterday's close
  Rank: (volume surge) * (% above 200 SMA)

Crypto filter:
  - Top 50 by market cap (stablecoins excluded)
  - RSI(14) between 55 and 75 (momentum without mean-reversion zone)
  - 24h volume >= 1.5x 7-day average
  - 24h price change > 0
  Rank: (volume surge) * (RSI - 50)
  Funding rate (Kraken Futures perpetuals) shown as context, not filtered.

Data sources (all free, no API keys):
  - yfinance: stock price/volume
  - Wikipedia: S&P 500 and Nasdaq 100 universe (with hardcoded fallback)
  - CoinGecko: crypto markets + historical prices
  - Kraken Futures: perpetual funding rates

Usage:
    python market_scanner.py
    python market_scanner.py --stocks-only
    python market_scanner.py --crypto-only
    python market_scanner.py --top 20              # top 20 instead of 10
    python market_scanner.py -o scan.csv           # save to reports/MM-DD-YYYY-scan.csv
    python market_scanner.py -o myfile             # save to reports/MM-DD-YYYY-myfile.csv

Integration:
    from market_scanner import scan_stocks, scan_crypto
    stock_df = scan_stocks(top_n=10)
    crypto_df = scan_crypto(top_n=10)
"""

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

# ---------------------------------------------------------------------------
# Configuration — all tunable values live in config.py when bot-integrated.
# When run standalone these module-level constants are used directly.
# ---------------------------------------------------------------------------

# Stock filter parameters
STOCK_PCT_OF_52W_HIGH = 0.98      # within 2% of 52w high
STOCK_VOL_SURGE_MIN   = 1.30      # 30% above 30d avg volume
STOCK_HISTORY_DAYS    = "1y"      # yfinance period string

# Crypto filter parameters
CRYPTO_RSI_MIN        = 55        # momentum floor
CRYPTO_RSI_MAX        = 75        # cap before mean-reversion zone
CRYPTO_VOL_SURGE_MIN  = 1.50      # 50% above 7d avg volume

# How many top results to return from each scan
SCANNER_TOP_N         = 10

# Reports output folder (relative to project root)
REPORTS_DIR           = Path("reports")

# Watchlist temp file paths — overwritten each scan run
WATCHLIST_DIR         = Path("watchlist")
TEMP_STOCKS_FILE      = WATCHLIST_DIR / "scanned_stocks.txt"
TEMP_CRYPTO_FILE      = WATCHLIST_DIR / "scanned_crypto.txt"

# Stablecoins and wrapped tokens to exclude from crypto universe
STABLECOIN_SYMBOLS = {
    "USDT", "USDC", "DAI", "BUSD", "TUSD", "USDP", "FRAX", "LUSD",
    "USDE", "FDUSD", "PYUSD", "USDD", "GUSD", "SUSD", "USD1",
}
WRAPPED_SYMBOLS = {"WBTC", "WETH", "STETH", "WSTETH", "WEETH", "CBETH", "RETH"}
CRYPTO_EXCLUDE = STABLECOIN_SYMBOLS | WRAPPED_SYMBOLS

# HTTP
USER_AGENT    = "Mozilla/5.0 (compatible; trading-bot-scanner/2.0)"
HTTP_TIMEOUT  = 20

# CoinGecko rate limit settings.
# Free tier: ~30 calls/min. Paid key: set COINGECKO_API_KEY in .env and
# drop COINGECKO_DELAY to 0.5.
COINGECKO_API_KEY     = ""        # set in config.py / .env for paid tier
COINGECKO_DELAY       = 2.5      # seconds between per-coin calls (conservative)
COINGECKO_MAX_RETRIES = 3        # retries on 429 with exponential backoff
COINGECKO_BASE_WAIT   = 30       # seconds to wait on first 429

# Wikipedia rate limiting — two calls, small gap to avoid 429 from their CDN
WIKIPEDIA_DELAY       = 3.0      # seconds between S&P and Nasdaq Wikipedia calls

# Hardcoded fallback universe — used if Wikipedia scraping fails.
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


# ---------------------------------------------------------------------------
# Output path helper
# ---------------------------------------------------------------------------

def resolve_output_path(name: Optional[str]) -> Path:
    """
    Resolve the output CSV path with these rules:
      - No name given      → reports/MM-DD-YYYY-market_scan.csv
      - Name given         → reports/MM-DD-YYYY-<name>.csv
      - Name already has   → strip it, re-apply prefix and reports/ dir
        a date prefix or
        wrong folder
      - .csv auto-appended if missing

    Always outputs into the REPORTS_DIR folder.
    """
    today = datetime.now().strftime("%m-%d-%Y")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if not name:
        return REPORTS_DIR / f"{today}-market_scan.csv"

    p = Path(name)
    stem = p.stem   # filename without extension

    # Strip .csv regardless of case, then re-append cleanly
    # Check if stem already starts with a date pattern MM-DD-YYYY (10 chars + dash)
    # to avoid double-dating if user passes in a previously generated filename.
    if len(stem) >= 11 and stem[2] == "-" and stem[5] == "-" and stem[9] == "-":
        # Already has a date prefix — use as-is but force into reports/ folder
        return REPORTS_DIR / f"{stem}.csv"

    return REPORTS_DIR / f"{today}-{stem}.csv"


# ---------------------------------------------------------------------------
# Ticker universe
# ---------------------------------------------------------------------------

def fetch_stock_universe() -> list[str]:
    """Return combined S&P 500 + Nasdaq 100 universe.

    Tries Wikipedia with a delay between the two calls.
    Falls back to hardcoded list on any failure.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        # --- S&P 500 ---
        print("Fetching S&P 500 list from Wikipedia...", file=sys.stderr)
        resp = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers=headers,
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        sp500 = pd.read_html(StringIO(resp.text))[0]
        sp500_tickers = sp500["Symbol"].astype(str).tolist()

        # Polite delay before second Wikipedia call
        time.sleep(WIKIPEDIA_DELAY)

        # --- Nasdaq 100 ---
        print("Fetching Nasdaq 100 list from Wikipedia...", file=sys.stderr)
        resp2 = requests.get(
            "https://en.wikipedia.org/wiki/Nasdaq-100",
            headers=headers,
            timeout=HTTP_TIMEOUT,
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
        print(
            f"Wikipedia fetch failed ({e}); using fallback universe "
            f"of {len(FALLBACK_TICKERS)} large caps.",
            file=sys.stderr,
        )
        return FALLBACK_TICKERS.copy()


# ---------------------------------------------------------------------------
# Technical indicators
# ---------------------------------------------------------------------------

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder-style RSI. Returns NaN for the first `period` bars."""
    delta = series.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs    = gain / loss
    return 100 - 100 / (1 + rs)


# ---------------------------------------------------------------------------
# CoinGecko HTTP helper — single consolidated implementation
# ---------------------------------------------------------------------------

def _coingecko_headers() -> dict:
    """Build headers for CoinGecko. Adds API key header if configured."""
    h = {"User-Agent": USER_AGENT}
    if COINGECKO_API_KEY:
        h["x-cg-demo-api-key"] = COINGECKO_API_KEY
    return h


def coingecko_get(url: str, params: Optional[dict] = None) -> Optional[dict | list]:
    """
    GET a CoinGecko endpoint with exponential backoff on 429 rate-limit responses.

    Waits COINGECKO_BASE_WAIT seconds on first 429, doubling on each retry.
    Returns parsed JSON on success, None if all retries exhausted or error.
    """
    wait = COINGECKO_BASE_WAIT
    for attempt in range(COINGECKO_MAX_RETRIES + 1):
        try:
            r = requests.get(
                url,
                params=params,
                headers=_coingecko_headers(),
                timeout=HTTP_TIMEOUT,
            )
            if r.status_code == 429:
                if attempt < COINGECKO_MAX_RETRIES:
                    print(
                        f"  CoinGecko rate-limited (429); waiting {wait}s "
                        f"(retry {attempt + 1}/{COINGECKO_MAX_RETRIES})...",
                        file=sys.stderr,
                    )
                    time.sleep(wait)
                    wait *= 2
                    continue
                print("  CoinGecko: max retries reached on rate limit.", file=sys.stderr)
                return None

            r.raise_for_status()
            payload = r.json()

            # CoinGecko occasionally returns error dicts with HTTP 200
            if (
                isinstance(payload, dict)
                and "status" in payload
                and "error_code" in payload.get("status", {})
            ):
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


# ---------------------------------------------------------------------------
# Stock scanner
# ---------------------------------------------------------------------------

def scan_stocks(top_n: int = SCANNER_TOP_N, tickers: Optional[list[str]] = None) -> pd.DataFrame:
    """Run the stock scan. Returns a ranked DataFrame."""
    import yfinance as yf

    if tickers is None:
        tickers = fetch_stock_universe()

    print(f"Downloading daily bars for {len(tickers)} tickers...", file=sys.stderr)
    data = yf.download(
        tickers,
        period=STOCK_HISTORY_DAYS,
        interval="1d",
        progress=False,
        auto_adjust=True,
        group_by="ticker",
        threads=True,
    )

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

            near_52w  = last_close >= high_52w * STOCK_PCT_OF_52W_HIGH
            trend_ok  = ema21 > sma200
            vol_ok    = vol_surge >= STOCK_VOL_SURGE_MIN
            price_up  = last_close > prev_close

            if not (near_52w and trend_ok and vol_ok and price_up):
                continue

            pct_above_sma = (last_close - sma200) / sma200 * 100
            pct_from_52w  = (last_close / high_52w - 1) * 100
            score         = vol_surge * max(pct_above_sma, 0)

            results.append({
                "Ticker":          t,
                "Price":           round(last_close, 2),
                "Vol Change":      round(vol_surge, 2),
                "RSI":             round(rsi_14, 1),
                "% from 52W High": round(pct_from_52w, 2),
                "% vs 200SMA":     round(pct_above_sma, 1),
                "Score":           round(score, 2),
                "Bullish Reason":  (
                    f"Within {abs(pct_from_52w):.1f}% of 52W high on "
                    f"{vol_surge:.1f}x avg volume, trending {pct_above_sma:.0f}% "
                    "above 200-day MA."
                ),
            })
        except Exception:
            continue

    if not results:
        return pd.DataFrame()

    out = pd.DataFrame(results).sort_values("Score", ascending=False).head(top_n)
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Crypto scanner
# ---------------------------------------------------------------------------

def fetch_kraken_funding_rates() -> dict[str, float]:
    """Return {symbol: funding_rate_pct} for Kraken perpetuals."""
    try:
        r = requests.get(
            "https://futures.kraken.com/derivatives/api/v3/tickers",
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
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
        fr   = t.get("fundingRate")
        mark = t.get("markPrice")
        if fr is None or mark is None or mark == 0:
            continue
        out[base] = float(fr) / float(mark) * 100
    return out


def scan_crypto(top_n: int = SCANNER_TOP_N) -> pd.DataFrame:
    """Run the crypto scan. Returns a ranked DataFrame."""
    # 1) Top 50 markets snapshot
    markets = coingecko_get(
        "https://api.coingecko.com/api/v3/coins/markets",
        {
            "vs_currency":            "usd",
            "order":                  "market_cap_desc",
            "per_page":               50,
            "page":                   1,
            "sparkline":              "false",
            "price_change_percentage": "24h",
        },
    )
    if not markets or not isinstance(markets, list):
        print("Crypto scan aborted: could not fetch market data from CoinGecko.", file=sys.stderr)
        return pd.DataFrame()

    # 2) Funding rates (single request, indexed by symbol)
    funding_map = fetch_kraken_funding_rates()

    excluded_count = len(CRYPTO_EXCLUDE & {c["symbol"].upper() for c in markets})
    print(
        f"Scanning top 50 crypto ({excluded_count} stablecoins/wrapped excluded)...",
        file=sys.stderr,
    )

    results: list[dict] = []
    for coin in markets:
        sym = coin["symbol"].upper()
        if sym in CRYPTO_EXCLUDE:
            continue

        # Daily closes for last 30 days — enough for RSI(14) + 7d vol avg
        payload = coingecko_get(
            f"https://api.coingecko.com/api/v3/coins/{coin['id']}/market_chart",
            {"vs_currency": "usd", "days": "30", "interval": "daily"},
        )

        # Always sleep between per-coin calls to respect free tier rate limit
        time.sleep(COINGECKO_DELAY)

        if not payload or not isinstance(payload, dict):
            continue

        try:
            prices  = payload.get("prices", [])
            volumes = payload.get("total_volumes", [])
            if len(prices) < 20 or len(volumes) < 8:
                continue

            closes    = pd.Series([p[1] for p in prices])
            vols      = pd.Series([v[1] for v in volumes])
            rsi_14    = float(rsi(closes).iloc[-1])
            vol_24h   = float(vols.iloc[-1])
            avg_vol_7d = float(vols.iloc[-8:-1].mean())
            vol_surge = vol_24h / avg_vol_7d if avg_vol_7d > 0 else 0.0
            change_24h = float(coin.get("price_change_percentage_24h") or 0)

            rsi_ok   = CRYPTO_RSI_MIN <= rsi_14 <= CRYPTO_RSI_MAX
            vol_ok   = vol_surge >= CRYPTO_VOL_SURGE_MIN
            price_up = change_24h > 0

            if not (rsi_ok and vol_ok and price_up):
                continue

            funding_pct  = funding_map.get(sym)
            funding_flag = ""
            if funding_pct is not None:
                annualized = funding_pct * 24 * 365
                if annualized > 20:
                    funding_flag = " | ⚠ crowded longs (high funding)"
                elif annualized < -20:
                    funding_flag = " | shorts paying (contrarian long setup)"

            score = vol_surge * (rsi_14 - 50)

            results.append({
                "Ticker":         sym,
                "Price":          round(
                    coin["current_price"],
                    6 if coin["current_price"] < 1 else 2,
                ),
                "Vol Change":     round(vol_surge, 2),
                "RSI":            round(rsi_14, 1),
                "24h %":          round(change_24h, 2),
                "Funding %":      round(funding_pct, 4) if funding_pct is not None else None,
                "Score":          round(score, 2),
                "Bullish Reason": (
                    f"+{change_24h:.1f}% on {vol_surge:.1f}x 7d-avg volume with "
                    f"RSI at {rsi_14:.0f} (momentum zone){funding_flag}."
                ),
            })
        except Exception:
            continue

    if not results:
        return pd.DataFrame()

    out = pd.DataFrame(results).sort_values("Score", ascending=False).head(top_n)
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Watchlist temp file helpers  (used by bot integration)
# ---------------------------------------------------------------------------

def _load_master_watchlist(filepath: Path) -> set:
    """Load master watchlist into a set of uppercase symbols for dedup checks."""
    if not filepath.exists():
        return set()
    try:
        lines = filepath.read_text().splitlines()
        return {l.strip().upper() for l in lines if l.strip() and not l.strip().startswith("#")}
    except Exception:
        return set()


def save_watchlist_temps(stock_df: pd.DataFrame, crypto_df: pd.DataFrame) -> None:
    """
    Write scanned tickers to temp watchlist files, overwriting the previous run.
    Deduplicates against master watchlist files so symbols already being watched
    don't get double-scanned each cycle (e.g. AMZN in both master and temp).
    """
    WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)

    master_stocks = _load_master_watchlist(Path("watchlists/stocks.txt"))
    master_crypto = _load_master_watchlist(Path("watchlists/crypto.txt"))

    if not stock_df.empty:
        all_tickers = stock_df["Ticker"].tolist()
        new_tickers = [t for t in all_tickers if t.upper() not in master_stocks]
        skipped     = len(all_tickers) - len(new_tickers)
        TEMP_STOCKS_FILE.write_text("\n".join(new_tickers))
        print(
            f"Watchlist temp written: {TEMP_STOCKS_FILE} "
            f"({len(new_tickers)} new stocks"
            f"{f', {skipped} already in master list skipped' if skipped else ''})",
            file=sys.stderr
        )
    else:
        TEMP_STOCKS_FILE.write_text("")

    if not crypto_df.empty:
        all_pairs = [f"{sym}/USD" for sym in crypto_df["Ticker"].tolist()]
        new_pairs = [
            p for p in all_pairs
            if p.upper() not in master_crypto
            and p.split("/")[0].upper() not in master_crypto
        ]
        skipped = len(all_pairs) - len(new_pairs)
        TEMP_CRYPTO_FILE.write_text("\n".join(new_pairs))
        print(
            f"Watchlist temp written: {TEMP_CRYPTO_FILE} "
            f"({len(new_pairs)} new crypto pairs"
            f"{f', {skipped} already in master list skipped' if skipped else ''})",
            file=sys.stderr
        )
    else:
        TEMP_CRYPTO_FILE.write_text("")


def load_watchlist_temps() -> tuple[list[str], list[str]]:
    """
    Read scanned tickers from temp files.
    Returns (stock_tickers, crypto_pairs).
    Returns empty lists if temp files don't exist (first boot, or scan hasn't run).
    """
    stocks: list[str] = []
    crypto: list[str] = []

    if TEMP_STOCKS_FILE.exists():
        content = TEMP_STOCKS_FILE.read_text().strip()
        stocks = [t for t in content.splitlines() if t.strip()]

    if TEMP_CRYPTO_FILE.exists():
        content = TEMP_CRYPTO_FILE.read_text().strip()
        crypto = [t for t in content.splitlines() if t.strip()]

    return stocks, crypto


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def print_table(title: str, df: pd.DataFrame) -> None:
    bar = "=" * 100
    print(f"\n{bar}\n{title}\n{bar}")
    if df.empty:
        print("  No results matched the filter criteria.")
        return
    display_df = df.drop(columns=["Score"], errors="ignore")
    print(display_df.to_string(index=False))


def save_csv(stock_df: pd.DataFrame, crypto_df: pd.DataFrame, output_path: Path) -> None:
    """Save combined stock + crypto results to CSV."""
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Daily stock + crypto momentum scanner.")
    parser.add_argument(
        "--top", type=int, default=SCANNER_TOP_N,
        help=f"Top N results per asset class (default {SCANNER_TOP_N})",
    )
    parser.add_argument("--stocks-only", action="store_true")
    parser.add_argument("--crypto-only",  action="store_true")
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help=(
            "Output filename. Saved to reports/ folder with date prefix. "
            "Examples: -o scan.csv  or  -o myscan  (both produce reports/MM-DD-YYYY-*.csv). "
            "Omit for default: reports/MM-DD-YYYY-market_scan.csv"
        ),
    )
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

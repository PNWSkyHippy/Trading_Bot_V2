# 🤖 Autonomous Day Trading AI

A self-sufficient algorithmic trading system that scans stocks and crypto,
executes trades with strict risk management, compounds gains, and reports
daily — all running on your own desktop.

---

## 📁 Project Structure

```
trading_bot/
├── bot_engine.py           ← MAIN ENTRY POINT — run this to start
├── dashboard.py            ← Live browser dashboard (Streamlit)
├── config.py               ← All settings and parameters
├── requirements.txt        ← Python dependencies
├── .env.template           ← API key template (copy to .env)
│
├── core/
│   ├── risk_manager.py     ← ALL risk rules enforced here
│   ├── trade_executor.py   ← Sends orders to brokers
│   └── position_monitor.py ← Watches open trades, trailing stops
│
├── scanners/
│   └── market_scanner.py   ← Scans stocks + crypto for signals
│
├── intelligence/
│   └── chat_interface.py   ← Claude AI chat — talk to your bot
│
├── reporting/
│   └── report_generator.py ← Daily reports, email, tax exports
│
├── data/
│   └── database.py         ← All storage (SQLite, local)
│
├── logs/                   ← Auto-created, all activity logged
├── exports/                ← Tax CSVs and reports saved here
└── data/trading_bot.db     ← Your complete trade history (SQLite)
```

---

## 🚀 Quick Start

### Step 1 — Install Python 3.11+
Download from: https://python.org/downloads

### Step 2 — Install dependencies
```bash
cd trading_bot
pip install -r requirements.txt
```

### Step 3 — Set up your API keys
```bash
cp .env.template .env
# Edit .env with your actual API keys
```

### Step 4 — Create accounts (all free to start)
- **Alpaca Markets**: https://alpaca.markets (paper trading is free, no real money needed to start)
- **Anthropic Claude API**: https://console.anthropic.com (~$5-10/month)
- **Binance US** (crypto): https://binance.us

### Step 5 — Start paper trading (NO real money yet)
```bash
# Terminal 1 — Start the bot
python bot_engine.py

# Terminal 2 — Start the dashboard
streamlit run dashboard.py
```
Open your browser to: http://localhost:8501

### Step 6 — Monitor for 30 days on paper trading
Review daily reports. When consistently profitable, switch to live in config.py:
```python
ALPACA_BASE_URL = "https://api.alpaca.markets"  # Remove "paper-" prefix
```

---

## ⚙️ Configuring Your Settings

Edit `config.py` to customize:

```python
# Risk rules
max_position_pct = 0.02    # 2% of capital per trade
stop_loss_pct    = 0.01    # 1% stop-loss
take_profit_pct  = 0.03    # 3% take-profit
max_daily_loss_pct = 0.10  # Halt after 10% daily loss
max_consecutive_losses = 3  # Halt after 3 losing trades in a row

# What to scan
stock_watchlist = ["AAPL", "NVDA", "TSLA", ...]  # Add/remove symbols
crypto_pairs    = ["BTC/USDT", "ETH/USDT", ...]
```

---

## 💬 Talking to Your Bot

From the dashboard chat or directly via the chat interface:

| What you say | What happens |
|---|---|
| "Show my stats" | Displays full performance summary |
| "Pause trading today" | Halts all new trades immediately |
| "Resume trading" | Re-enables trading |
| "Withdraw $500 for rent" | Deducts from capital, logs it |
| "What's my win rate this week?" | Calculates and reports |
| "Export my taxes for 2024" | Saves Form 8949 CSV to exports/ |
| "Lower my risk to 1.5% per trade" | Adjusts position sizing |

---

## 📊 Risk Rules (Hardcoded)

These rules run on every trade, no exceptions:

| Rule | Value |
|---|---|
| Max position size | 2% of total capital |
| Stop-loss | 1% below entry (automatic) |
| Initial take-profit | 3% above entry (automatic) |
| Trailing stop | Rises with price, stays 1% behind |
| Daily loss ceiling | 10% — trading halts for the day |
| Consecutive loss halt | 3 losses in a row = halt for the day |
| Max open positions | 5 simultaneous trades |
| Opening noise avoidance | No trades in first 30 min after open |
| End-of-day | All stock positions closed before close |

---

## 📄 Tax Records

Every trade is automatically recorded in the tax ledger with:
- Open and close dates
- Proceeds and cost basis
- Gain/loss amounts
- Short-term vs long-term classification

Export Form 8949-ready CSV anytime:
```bash
# Via dashboard sidebar, or via chat:
"Export my taxes for 2024"
```

---

## 💸 Withdrawals

Process a withdrawal anytime via the dashboard or chat:
- Capital base is reduced accordingly
- All compounding recalculates from new base
- Withdrawal is logged as a capital return event (not taxable income)

---

## 📈 Compounding Projection

At 65% win rate with 2% avg daily gain on winning days:

| Timeframe | Conservative | Moderate |
|---|---|---|
| 6 months  | $250–$400    | $500–$800 |
| 1 year    | $700–$1,500  | $2,000–$5,000 |
| 2 years   | $3,000–$8,000| $20,000–$60,000 |
| 3 years   | $15,000+     | $100,000+ |

*Assumes reinvestment of profits and modest monthly withdrawals from year 2*

---

## ⚠️ Important Disclaimers

1. **Paper trade first.** Run for at least 30 days on paper before real money.
2. **Past performance** of any strategy does not guarantee future results.
3. **Day trading involves substantial risk** of loss and is not suitable for all investors.
4. **Tax obligations**: Consult a CPA — the bot tracks data but doesn't give tax advice.
5. **Your capital is yours.** The bot only trades on your connected brokerage accounts.
6. **Never trade money you cannot afford to lose.**

---

## 🔧 Built With

- **Python 3.11** — Core language
- **Alpaca Markets API** — Stock execution
- **CCXT** — Crypto exchange connectivity  
- **pandas + numpy** — Data analysis
- **APScheduler** — Task scheduling
- **Streamlit + Plotly** — Live dashboard
- **Claude AI (Anthropic)** — Conversational intelligence
- **SQLite** — Local database (no server needed)

---

*Built with care. Trade responsibly. 📈*

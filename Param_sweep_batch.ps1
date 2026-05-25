cd c:\users\linda\trading_bot_v2

$PYTHON = "venv312\Scripts\python.exe"
$SCRIPT = ".\Scripts\param_sweep.py"

# ============================================================
#  PARAM SWEEP BATCH
#  Based on strategy_matrix round 1 results (2026-05-24)
#  Only running strategies that showed PF >= 1.3 on the matrix
#  Symbols chosen from top edge cells per strategy
# ============================================================

# -----------------------------------------------------------
# adaptive_regime  PF=5.04  |  stocks 1h long only
# Top symbols: CHPT TSLA ZIM UPST LRCX CVNA PLTR ACHR RIVN NVDA JPM
# Only 2 params -- quick annealing run
# -----------------------------------------------------------
& $PYTHON $SCRIPT --strategy adaptive_regime `
    --param stop_loss_pct=0.6:3.75:0.5 `
    --param take_profit_pct=1.2:7.5:0.5 `
    --symbols CHPT,TSLA,ZIM,LRCX,CVNA,PLTR,ACHR,RIVN,NVDA,JPM `
    --timeframe 1h --days 365 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 `
    --metric profit_factor

# -----------------------------------------------------------
# orb_breakout  PF=1.99  |  stocks 1h  (crypto is dead for this one)
# Top cells: MSFT 1h both (PF=20.5), META 1h short (9.4), GOOGL 1h both (4.2)
# Only 2 params -- quick
# -----------------------------------------------------------
& $PYTHON $SCRIPT --strategy orb_breakout `
    --param stop_loss_pct=0.6:3.75:0.5 `
    --param take_profit_pct=1.2:7.5:0.5 `
    --symbols MSFT,META,GOOGL,AMZN `
    --timeframe 1h --days 365 --asset-class stock `
    --direction both `
    --method annealing --iterations 60 `
    --metric profit_factor

# -----------------------------------------------------------
# vwap_momentum  PF=1.99  |  stocks 1h + SOL 1d
# Top cells: AMZN 1h both (PF=5.15), TSLA 1h long (3.0), GOOGL 1h short (1.85), NVDA 1h short (1.83)
# Run stocks and crypto separately (different timeframes)
# -----------------------------------------------------------
& $PYTHON $SCRIPT --strategy vwap_momentum `
    --param stop_loss_pct=0.6:3.75:0.5 `
    --param take_profit_pct=1.2:7.5:0.5 `
    --symbols AMZN,TSLA,MSFT,GOOGL,NVDA `
    --timeframe 1h --days 365 --asset-class stock `
    --direction both `
    --method annealing --iterations 60 `
    --metric profit_factor

& $PYTHON $SCRIPT --strategy vwap_momentum `
    --param stop_loss_pct=0.6:3.75:0.5 `
    --param take_profit_pct=1.2:7.5:0.5 `
    --symbols SOL/USD `
    --timeframe 1d --days 365 --asset-class crypto `
    --direction long `
    --method annealing --iterations 40 `
    --metric profit_factor

# -----------------------------------------------------------
# bollinger_squeeze  PF=1.40  |  mix of stocks + crypto, 1h
# Top cells: TSLA long (5.22), DOT long (5.18), AMD both (4.73), NVDA both (2.98)
#            BNB short (2.43), LINK long (2.21)
# Run stocks and crypto separately
# -----------------------------------------------------------
& $PYTHON $SCRIPT --strategy bollinger_squeeze `
    --param stop_loss_pct=1.0:6.25:0.5 `
    --param take_profit_pct=2.8:17.5:0.5 `
    --symbols TSLA,AMD,NVDA `
    --timeframe 1h --days 365 --asset-class stock `
    --direction both `
    --method annealing --iterations 60 `
    --metric profit_factor

& $PYTHON $SCRIPT --strategy bollinger_squeeze `
    --param stop_loss_pct=1.0:6.25:0.5 `
    --param take_profit_pct=2.8:17.5:0.5 `
    --symbols DOT/USD,BNB/USD,LINK/USD,AVAX/USD `
    --timeframe 1h --days 365 --asset-class crypto `
    --direction both `
    --method annealing --iterations 60 `
    --metric profit_factor

# -----------------------------------------------------------
# mr_03_fbs  PF=1.30  |  8 params -- use zoom method
# Top cells: ADA 1d short (10.25), AAPL 1h both (8.29), XRP 1d short (5.2)
#            NVDA 1h short (2.72), SOL 1d short (2.45), BTC 1d short (2.09)
# Run 1h stocks and 1d crypto separately (different best directions)
# -----------------------------------------------------------
& $PYTHON $SCRIPT --strategy mr_03_fbs `
    --param bb_len=10:60:2:int `
    --param bb_mult=0.7:4.375:0.5 `
    --param snap_bars=1:6:1:int `
    --param ma_len=100:600:20:int `
    --param atr_len=7:42:1:int `
    --param tp_mult=0.6:3.75:0.5 `
    --param sl_mult=0.8:5.0:0.5 `
    --param max_bars=18:108:3:int `
    --symbols AAPL,NVDA,AMD,TSLA,SPY `
    --timeframe 1h --days 365 --asset-class stock `
    --direction both `
    --method zoom --iterations 80 `
    --metric profit_factor

& $PYTHON $SCRIPT --strategy mr_03_fbs `
    --param bb_len=10:60:2:int `
    --param bb_mult=0.7:4.375:0.5 `
    --param snap_bars=1:6:1:int `
    --param ma_len=100:600:20:int `
    --param atr_len=7:42:1:int `
    --param tp_mult=0.6:3.75:0.5 `
    --param sl_mult=0.8:5.0:0.5 `
    --param max_bars=18:108:3:int `
    --symbols ADA/USD,XRP/USD,SOL/USD,BTC/USD,DOGE/USD `
    --timeframe 1d --days 365 --asset-class crypto `
    --direction short `
    --method zoom --iterations 80 `
    --metric profit_factor

# -----------------------------------------------------------
# btc_v6_chandelier  PF=1.490  |  stocks 1h + 1d (both good)
# Top cells: CLSK 6.74, MARA 4.92, CRM 3.64, NOC 3.37, OPEN 4.09 (stocks 1h)
#            FIL 27.85, HT 13.66, TRUMP 5.26, AXS 4.24 (crypto 1d)
# Long only, chandelier custom exit — sweep structural params not just SL/TP
# atr_mult controls chandelier width; rsi_thresh controls entry tightness
# -----------------------------------------------------------
& $PYTHON $SCRIPT --strategy btc_v6_chandelier `
    --param atr_mult=2.5:8.0:0.5 `
    --param rsi_thresh=35.0:55.0:2.5 `
    --symbols CLSK,MARA,CRM,NOC,OPEN,TSLA,NVDA `
    --timeframe 1h --days 365 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 `
    --metric profit_factor

& $PYTHON $SCRIPT --strategy btc_v6_chandelier `
    --param atr_mult=2.5:8.0:0.5 `
    --param rsi_thresh=35.0:55.0:2.5 `
    --symbols FIL/USD,HT/USD,AXS/USD,BTC/USD,ETH/USD,SOL/USD `
    --timeframe 1d --days 365 --asset-class crypto `
    --direction long `
    --method annealing --iterations 60 `
    --metric profit_factor

# -----------------------------------------------------------
# rsi_dip_simple  PF=1.319  |  stocks 1d best (PF=1.784)
# Top cells: AMAT 22.96, BIIB 9.22, LUNR 8.42, MPWR 8.33 (stocks 1d)
#            AGIX 4.35, NMR 4.37, BONK 3.97, TRUMP 3.57 (crypto 1d)
# Naked RSI cross — sweep oversold entry threshold + overbought exit
# -----------------------------------------------------------
& $PYTHON $SCRIPT --strategy rsi_dip_simple `
    --param rsi_oversold=22.0:45.0:2.0 `
    --param rsi_exit=65.0:90.0:2.5 `
    --symbols AMAT,BIIB,LUNR,MPWR,NVDA,AMD,TSLA `
    --timeframe 1d --days 730 --asset-class stock `
    --direction long `
    --method annealing --iterations 60 `
    --metric profit_factor

& $PYTHON $SCRIPT --strategy rsi_dip_simple `
    --param rsi_oversold=22.0:45.0:2.0 `
    --param rsi_exit=65.0:90.0:2.5 `
    --symbols BTC/USD,ETH/USD,SOL/USD,BONK/USD,TRUMP/USD `
    --timeframe 1d --days 730 --asset-class crypto `
    --direction long `
    --method annealing --iterations 60 `
    --metric profit_factor

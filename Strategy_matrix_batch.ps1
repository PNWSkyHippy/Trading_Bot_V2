cd c:\users\linda\trading_bot_v2

$STOCKS  = ".\watchlists\stocks.txt"
$CRYPTO  = ".\watchlists\crypto.txt"
$PYTHON  = "venv312\Scripts\python.exe"
$SCRIPT  = ".\Scripts\strategy_matrix.py"

& $PYTHON $SCRIPT --strategy btc_v6_chandelier     --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO
& $PYTHON $SCRIPT --strategy rsi_dip_simple        --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO
& $PYTHON $SCRIPT --strategy pll_cycle             --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO
& $PYTHON $SCRIPT --strategy pll_cycle_martingale  --symbols-stock-file $STOCKS --symbols-crypto-file $CRYPTO

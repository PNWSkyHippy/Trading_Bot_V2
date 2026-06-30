import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config
import alpaca_trade_api as tradeapi

print(f"base_url : {config.ALPACA_BASE_URL}")
print(f"api_key configured: {'yes' if config.ALPACA_API_KEY else 'no'}")

try:
    api = tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, config.ALPACA_BASE_URL)
    acct = api.get_account()
    print(f"OK — account status: {acct.status}, equity: ${float(acct.equity):,.2f}")
except Exception as e:
    print(f"FAILED: {e}")

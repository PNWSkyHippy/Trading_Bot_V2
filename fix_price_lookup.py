with open('scanners/market_scanner.py', encoding='utf-8') as f:
    src = f.read()

old = '''    def get_current_price(self, symbol: str) -> Optional[float]:
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker["last"])
        except Exception:
            return None'''

new = '''    def get_current_price(self, symbol: str) -> Optional[float]:
        """Try primary exchange first, then any other loaded exchanges."""
        exchanges = list(getattr(self, "exchanges", {}).values())
        if self.exchange and self.exchange not in exchanges:
            exchanges = [self.exchange] + exchanges
        for exc in exchanges:
            try:
                ticker = exc.fetch_ticker(symbol)
                price = ticker.get("last") or ticker.get("close")
                if price and float(price) > 0:
                    return float(price)
            except Exception:
                continue
        return None'''

if old in src:
    with open('scanners/market_scanner.py', 'w', encoding='utf-8') as f:
        f.write(src.replace(old, new, 1))
    print('Fixed - get_current_price tries all exchanges')
else:
    print('Not found')
    idx = src.find('def get_current_price')
    if idx > 0: print(repr(src[idx:idx+200]))

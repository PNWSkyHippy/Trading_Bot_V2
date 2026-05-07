with open('BreakoutScanner.py', encoding='utf-8') as f:
    src = f.read()

old = '''    def _scan_cryptos(self):
        broker = self.crypto_fetcher.exchange_name
        try:
            movers = self.crypto_fetcher.get_top_movers(
                self.config.get("top_cryptos_count", 100))
            self.latest_crypto_movers = movers
            logger.info(f"Crypto scan: {len(movers)} movers via {broker} | "
                        f"watching={self.watchlist.size()}")
            for pd in movers:
                if not self.crypto_fetcher.exchange: break
                if pd.symbol not in self.crypto_fetcher.exchange.symbols: continue
                for h in self.crypto_fetcher.get_historical_data(pd.symbol):
                    self.detector.update_history(h)
                self._process_symbol(pd, broker)
        except Exception as e:
            logger.error(f"Crypto scan error: {e}")'''

new = '''    def _scan_cryptos(self):
        try:
            movers = self.crypto_fetcher.get_top_movers(
                self.config.get("top_cryptos_count", 100))
            self.latest_crypto_movers = movers
            exchanges = getattr(self.crypto_fetcher, "exchanges", {})
            logger.info(f"Crypto scan: {len(movers)} movers via "
                        f"{list(exchanges.keys()) or self.crypto_fetcher.exchange_name} | "
                        f"watching={self.watchlist.size()}")
            for pd in movers:
                # Use the broker tag set by get_top_movers, fall back to primary
                broker = getattr(pd, "_exchange_name",
                                 self.crypto_fetcher.exchange_name)
                # Find the correct exchange for this symbol
                exc = exchanges.get(broker) or self.crypto_fetcher.exchange
                if not exc:
                    continue
                if pd.symbol not in exc.symbols:
                    continue
                for h in self.crypto_fetcher.get_historical_data(pd.symbol):
                    self.detector.update_history(h)
                self._process_symbol(pd, broker)
        except Exception as e:
            logger.error(f"Crypto scan error: {e}")'''

if old in src:
    with open('BreakoutScanner.py', 'w', encoding='utf-8') as f:
        f.write(src.replace(old, new, 1))
    print('Fixed - _scan_cryptos now uses per-symbol broker tag')
else:
    print('Not found - showing context:')
    idx = src.find('def _scan_cryptos')
    if idx > 0: print(repr(src[idx:idx+400]))

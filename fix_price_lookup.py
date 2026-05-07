# Fix 1: market_scanner.py - get_current_price tries all exchanges and returns broker name
with open('scanners/market_scanner.py', encoding='utf-8') as f:
    src = f.read()

old = '''    def get_current_price(self, symbol: str) -> Optional[float]:
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

new = '''    def get_current_price(self, symbol: str) -> Optional[float]:
        """Try all loaded exchanges. Returns price or None."""
        price, _ = self.get_current_price_with_broker(symbol)
        return price

    def get_current_price_with_broker(self, symbol: str):
        """
        Try all loaded exchanges for a price.
        Returns (price, broker_name) or (None, None).
        Used by manual trade entry to show which exchange has the symbol.
        """
        named = getattr(self, "exchanges", {})
        # Build list of (name, exchange) pairs, primary first
        pairs = list(named.items())
        if self.exchange and self.exchange not in named.values():
            pairs = [(getattr(self, "exchange_name", "KRAKEN"), self.exchange)] + pairs
        for name, exc in pairs:
            try:
                ticker = exc.fetch_ticker(symbol)
                price  = ticker.get("last") or ticker.get("close")
                if price and float(price) > 0:
                    return float(price), name
            except Exception:
                continue
        return None, None'''

if old in src:
    with open('scanners/market_scanner.py', 'w', encoding='utf-8') as f:
        f.write(src.replace(old, new, 1))
    print('Fix 1 OK: get_current_price_with_broker added')
else:
    # Try original version
    old2 = '''    def get_current_price(self, symbol: str) -> Optional[float]:
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker["last"])
        except Exception:
            return None'''
    new2 = '''    def get_current_price(self, symbol: str) -> Optional[float]:
        price, _ = self.get_current_price_with_broker(symbol)
        return price

    def get_current_price_with_broker(self, symbol: str):
        named = getattr(self, "exchanges", {})
        pairs = list(named.items())
        if self.exchange and self.exchange not in named.values():
            pairs = [(getattr(self, "exchange_name", "KRAKEN"), self.exchange)] + pairs
        for name, exc in pairs:
            try:
                ticker = exc.fetch_ticker(symbol)
                price  = ticker.get("last") or ticker.get("close")
                if price and float(price) > 0:
                    return float(price), name
            except Exception:
                continue
        return None, None'''
    if old2 in src:
        with open('scanners/market_scanner.py', 'w', encoding='utf-8') as f:
            f.write(src.replace(old2, new2, 1))
        print('Fix 1 OK (v2): get_current_price_with_broker added')
    else:
        print('Fix 1 FAIL')
        idx = src.find('def get_current_price')
        if idx > 0: print(repr(src[idx:idx+200]))

# Fix 2: dashboard.py - use get_current_price_with_broker and show which exchange found it
with open('dashboard.py', encoding='utf-8') as f:
    dash = f.read()

old_dash = '''            live_price = scanner.get_current_price(sym_upper, m_asset)
            if live_price:
                m_entry = live_price
                if m_direction == "long":
                    preview_sl = live_price * (1 - m_sl_pct / 100)
                    preview_tp = live_price * (1 + m_tp_pct / 100)
                else:
                    preview_sl = live_price * (1 + m_sl_pct / 100)
                    preview_tp = live_price * (1 - m_tp_pct / 100)
                st.markdown(f"""
                <div style="background:#1a2a1a;border:1px solid #2a5c2a;border-radius:8px;padding:10px 14px;font-size:13px;margin-top:8px;">
                    📡 <b>Live Price:</b> <code>${live_price:.6f}</code><br>
                    🔴 <b>Stop Loss:</b> <code>${preview_sl:.6f}</code> &nbsp;&nbsp;
                    🟢 <b>Take Profit:</b> <code>${preview_tp:.6f}</code><br>
                    💰 <b>Position:</b> <code>{m_size/live_price:.4f} units @ ${live_price:.6f}</code>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning(f"Could not fetch live price for {sym_upper}")'''

new_dash = '''            # Try all exchanges, show which one found the price
            if m_asset == "crypto":
                try:
                    from scanners.market_scanner import scanner as _sc
                    crypto_fetcher = _sc.crypto_scanner
                    live_price, found_broker = crypto_fetcher.get_current_price_with_broker(sym_upper)
                except Exception:
                    live_price, found_broker = scanner.get_current_price(sym_upper, m_asset), None
            else:
                live_price, found_broker = scanner.get_current_price(sym_upper, m_asset), "ALPACA"
            if live_price:
                m_entry = live_price
                if m_direction == "long":
                    preview_sl = live_price * (1 - m_sl_pct / 100)
                    preview_tp = live_price * (1 + m_tp_pct / 100)
                else:
                    preview_sl = live_price * (1 + m_sl_pct / 100)
                    preview_tp = live_price * (1 - m_tp_pct / 100)
                broker_label = f" (found on {found_broker})" if found_broker else ""
                st.markdown(f"""
                <div style="background:#1a2a1a;border:1px solid #2a5c2a;border-radius:8px;padding:10px 14px;font-size:13px;margin-top:8px;">
                    📡 <b>Live Price{broker_label}:</b> <code>${live_price:.6f}</code><br>
                    🔴 <b>Stop Loss:</b> <code>${preview_sl:.6f}</code> &nbsp;&nbsp;
                    🟢 <b>Take Profit:</b> <code>${preview_tp:.6f}</code><br>
                    💰 <b>Position:</b> <code>{m_size/live_price:.4f} units @ ${live_price:.6f}</code>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning(f"Could not fetch live price for {sym_upper} on any exchange")'''

if old_dash in dash:
    with open('dashboard.py', 'w', encoding='utf-8') as f:
        f.write(dash.replace(old_dash, new_dash, 1))
    print('Fix 2 OK: dashboard shows which exchange found the price')
else:
    print('Fix 2 FAIL')
    idx = dash.find('live_price = scanner.get_current_price')
    if idx > 0: print(repr(dash[idx-10:idx+100]))

    def _load_strategy(self, strategy_name: str):
        strategy_map = {
            "rsi_momentum":       ("strategies.rsi_momentum",       "RSIMomentum"),
            "bollinger_breakout": ("strategies.bollinger_breakout",  "BollingerBreakout"),
            "ema_crossover":      ("strategies.ema_crossover",       "EMACrossover"),
            "mean_reversion":     ("strategies.mean_reversion",      "MeanReversion"),
            "scalp_master":       ("strategies.scalp_master",        "ScalpMaster"),
            "swing_trader":       ("strategies.swing_trader",        "SwingTrader"),
            "grid_bot":           ("strategies.grid_bot",            "GridBot"),
            "dca_accumulator":    ("strategies.dca_accumulator",     "DCAAccumulator"),
            "vwap_momentum":      ("strategies.vwap_momentum",       "VWAPMomentum"),
            "hammer_reversal":    ("strategies.hammer_reversal",     "HammerReversal"),
        }
        if strategy_name not in strategy_map:
            return None
        import importlib
        module_path, class_name = strategy_map[strategy_name]
        module = importlib.import_module(module_path)
        return getattr(module, class_name)()

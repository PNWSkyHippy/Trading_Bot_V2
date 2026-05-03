"""
test_alerts.py — Full pipeline alert tester
============================================
Tests sound AND GUI display by injecting fake signals into a running scanner.

Usage:
    python test_alerts.py gui       # Launch scanner GUI with auto-injected test signals
    python test_alerts.py sound     # Sound-only test (no GUI needed)
    python test_alerts.py 0-3       # Single escalation level sound test
"""

import sys
import time
import threading
from datetime import datetime

# ── Sound-only mode ───────────────────────────────────────────────────────────
if len(sys.argv) > 1 and sys.argv[1] == "sound":
    from alert_sound import init_audio, _play_pattern
    print("\n  SOUND TEST — all 4 levels\n")
    if not init_audio():
        print("  pygame not available — run: pip install pygame numpy")
        sys.exit(1)
    labels = {0:"NEW ALERT (440Hz x1)", 1:"MOVING >2% (660Hz x2)",
              2:"HOT >5% (880Hz x3)",   3:"ROCKET >10% (1100Hz x4)"}
    for lvl in range(4):
        print(f"  Level {lvl}: {labels[lvl]}")
        _play_pattern(lvl, 1.0)
        time.sleep(1.5)
    print("  Done.\n")
    sys.exit(0)

# ── Single level sound test ───────────────────────────────────────────────────
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    from alert_sound import init_audio, _play_pattern
    lvl = int(sys.argv[1])
    if lvl not in range(4): print("Level must be 0-3"); sys.exit(1)
    init_audio(); time.sleep(0.3)
    _play_pattern(lvl, 1.0); time.sleep(2)
    sys.exit(0)

# ── Full GUI test mode ────────────────────────────────────────────────────────
from BreakoutScanner import (
    MarketScanner, BreakoutSignal, AssetType, SignalPhase, move_pct
)

FAKE_SIGNALS = [
    # (asset_type, symbol, broker, entry, current, escalation, momentum_score)
    (AssetType.STOCK,  "NVDA",    "ALPACA",  850.00,  850.00,  0,  1.5),
    (AssetType.CRYPTO, "BTC/USD", "KRAKEN",  95000.0, 95000.0, 0,  1.8),
    (AssetType.CRYPTO, "ETH/USD", "KRAKEN",  3200.0,  3264.0,  1,  2.1),
    (AssetType.STOCK,  "TSLA",    "ALPACA",  180.00,  189.90,  2,  3.2),
    (AssetType.CRYPTO, "SOL/USD", "KRAKEN",  140.0,   156.80,  3,  4.5),
]

def make_signal(asset_type, symbol, broker, entry, current, escalation, mom):
    mpct = move_pct(entry, current)
    return BreakoutSignal(
        symbol             = symbol,
        asset_type         = asset_type,
        current_price      = current,
        predicted_move_pct = 65.0 + escalation * 10,
        confidence         = 0.60 + escalation * 0.10,
        volume_spike       = 2.0  + escalation * 0.8,
        momentum_score     = mom,
        pattern_detected   = ["watchlist", "early_breakout",
                              "early_breakout", "early_breakout_strong",
                              "early_breakout_strong"][escalation],
        timestamp          = datetime.now(),
        broker             = broker,
        phase              = SignalPhase.ALERTED,
        entry_price        = entry,
        best_move_pct      = mpct,
    )

def inject_signals(scanner: MarketScanner):
    """
    Wait until GUI root window exists, wire up the gui reference manually,
    then inject fake signals directly via root.after so they land on the main thread.
    """
    print("  [TEST] Waiting for GUI root window...")

    # Wait for GUI object and its root window to exist
    for _ in range(60):
        gui = getattr(scanner, "gui", None)
        if gui and getattr(gui, "root", None):
            break
        time.sleep(0.5)
    else:
        print("  [TEST] Timed out waiting for GUI — aborting")
        return

    # Wire the GUI into the alert system if not already done
    # (normally done when Start is clicked, but we bypass that in test mode)
    scanner.alert_system.gui = gui
    print("  [TEST] GUI wired — injecting signals (4 seconds apart)\n")
    time.sleep(1.0)

    for asset_type, symbol, broker, entry, current, esc, mom in FAKE_SIGNALS:
        sig = make_signal(asset_type, symbol, broker, entry, current, esc, mom)
        mpct_str = f"{move_pct(entry, current):+.1f}%" if entry != current else "+0.0%"
        print(f"  [TEST] {broker:8s} {symbol:10s}  esc={esc}  move={mpct_str}")
        # Send via root.after so it lands on the tkinter main thread
        gui.root.after(0, gui.add_alert, "test", sig, esc)
        # Also fire the beep directly (doesn't need main thread)
        gui._beep(sig, esc)
        time.sleep(4)

    print("\n  [TEST] All 5 signals injected.")
    print("  Stocks panel: NVDA (blue), TSLA (green)")
    print("  Crypto panel: BTC/USD (blue), ETH/USD (orange), SOL/USD (white)")
    print("  Close the window when done.\n")

def main():
    print("\n" + "="*58)
    print("  BREAKOUT SCANNER — FULL GUI + SOUND TEST")
    print("  GUI opens — signals auto-inject, no need to click Start")
    print("="*58 + "\n")

    scanner = MarketScanner()

    # Start alert system so send_alert works
    scanner.alert_system.start()

    # Inject thread — waits internally for GUI to be ready
    t = threading.Thread(target=inject_signals, args=(scanner,), daemon=True)
    t.start()

    # Launch GUI — blocks until window closed
    scanner.run_gui()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("  Quick start: python test_alerts.py gui")
    else:
        main()

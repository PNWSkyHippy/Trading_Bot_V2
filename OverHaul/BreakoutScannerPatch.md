1) Add a single direction resolver helper
Put this right below favorable_move_pct():

def resolved_direction(direction: str = "", momentum_score: float = 0.0) -> str:
    """
    Resolve trade direction safely.
    Priority:
      1. explicit direction ("long"/"short")
      2. fallback from momentum_score
    """
    d = str(direction or "").strip().lower()
    if d in ("long", "short"):
        return d
    try:
        return "short" if float(momentum_score) < -0.5 else "long"
    except Exception:
        return "long"


def signal_direction(signal: BreakoutSignal) -> str:
    return resolved_direction(
        getattr(signal, "direction", ""),
        getattr(signal, "momentum_score", 0.0),
    )
2) Fix classify_signal() to use explicit direction first
Replace this:
def classify_signal(signal: BreakoutSignal) -> dict:
    score     = signal.confidence
    direction = "LONG" if signal.momentum_score >= -0.5 else "SHORT"
    if "strong" in signal.pattern_detected:
        stage = "CONFIRMED"
    elif "early" in signal.pattern_detected:
        stage = "EARLY"
    else:
        stage = "WATCHLIST"
    poc = min(95, score * 100)
    if signal.volume_spike > 3.0:
        poc = min(95, poc + 10)
    return {"direction": direction, "stage": stage, "poc": poc}
With this:
def classify_signal(signal: BreakoutSignal) -> dict:
    score     = signal.confidence
    direction = signal_direction(signal).upper()
    if "strong" in signal.pattern_detected:
        stage = "CONFIRMED"
    elif "early" in signal.pattern_detected:
        stage = "EARLY"
    else:
        stage = "WATCHLIST"
    poc = min(95, score * 100)
    if signal.volume_spike > 3.0:
        poc = min(95, poc + 10)
    return {"direction": direction, "stage": stage, "poc": poc}
3) Add get() to WatchlistManager and stop re-inferring direction from momentum
Inside class WatchlistManager, add this method:

def get(self, symbol: str) -> Optional[BreakoutSignal]:
    return self._watched.get(symbol)
Then patch check().

Replace this block:
def check(self, pd: PriceData) -> Optional[BreakoutSignal]:
    sym = pd.symbol
    if sym not in self._watched:
        return None
    sig       = self._watched[sym]
    sig.scan_count += 1
    gate_pct  = self.config.get("momentum_gate_pct",  0.80)
    max_scans = self.config.get("momentum_gate_scans", 3)
    mpct      = move_pct(sig.entry_price, pd.price)
    direction = "LONG" if sig.momentum_score >= -0.5 else "SHORT"
    moved_right = (mpct >= gate_pct  if direction == "LONG"  else
                   mpct <= -gate_pct if direction == "SHORT" else False)
    if moved_right:
        sig.phase         = SignalPhase.ALERTED
        sig.current_price = pd.price
        sig.best_move_pct = mpct
        del self._watched[sym]
        logger.warning(f"[GATE PASSED] {sig.broker} {sym} moved {mpct:+.2f}%")
        return sig
    if sig.scan_count >= max_scans:
        logger.info(f"[WATCHLIST EXPIRED] {sym} — dropped after {max_scans} scans")
        del self._watched[sym]
    return None
With this:
def check(self, pd: PriceData) -> Optional[BreakoutSignal]:
    sym = pd.symbol
    if sym not in self._watched:
        return None
    sig       = self._watched[sym]
    sig.scan_count += 1
    gate_pct  = self.config.get("momentum_gate_pct",  0.80)
    max_scans = self.config.get("momentum_gate_scans", 3)
    mpct      = move_pct(sig.entry_price, pd.price)
    direction = signal_direction(sig).upper()

    moved_right = (
        mpct >= gate_pct if direction == "LONG"
        else mpct <= -gate_pct if direction == "SHORT"
        else False
    )

    if moved_right:
        sig.phase         = SignalPhase.ALERTED
        sig.current_price = pd.price
        sig.best_move_pct = favorable_move_pct(direction, mpct)
        del self._watched[sym]
        logger.warning(
            f"[GATE PASSED] {sig.broker} {sym} raw_move={mpct:+.2f}% dir={direction}"
        )
        return sig

    if sig.scan_count >= max_scans:
        logger.info(f"[WATCHLIST EXPIRED] {sym} — dropped after {max_scans} scans")
        del self._watched[sym]
    return None
That does two good things:

uses signal.direction first
stores best_move_pct as favorable move, so shorts don’t look “negative best move”
4) Fix GUI direction storage in ScannerGUI.add_alert()
Replace this line:
"direction":     "LONG" if signal.momentum_score >= -0.5 else "SHORT",
With this:
"direction":     signal_direction(signal).upper(),
And while you’re there, patch best_move too.

Replace this:
"best_move":     max(mpct, existing.get("best_move", 0.0)),
With this:
"best_move":     max(
    favorable_move_pct(signal_direction(signal), mpct),
    existing.get("best_move", 0.0)
),
So the whole middle section becomes:

mpct     = move_pct(signal.entry_price, signal.current_price)
dir_txt  = signal_direction(signal).upper()

store[sym] = {
    "time":          signal.timestamp.strftime("%H:%M:%S"),
    "broker":        signal.broker,
    "symbol":        sym,
    "direction":     dir_txt,
    "score":         round(signal.predicted_move_pct, 1),
    "confidence":    round(signal.confidence * 100, 0),
    "entry_price":   existing.get("entry_price", signal.entry_price or signal.current_price),
    "entry_time":    existing.get("entry_time",  signal.timestamp),
    "current_price": signal.current_price,
    "move_pct":      mpct,
    "best_move":     max(
        favorable_move_pct(dir_txt, mpct),
        existing.get("best_move", 0.0)
    ),
    "t5m":  existing.get("t5m",  ""),
    "t15m": existing.get("t15m", ""),
    "t1h":  existing.get("t1h",  ""),
    "asset_type":    signal.asset_type,
    "escalation":    escalation,
    "phase":         signal.phase.value,
}
5) Fix GUI live-update best_move for shorts
Inside _update_loop() → _fetch_prices():

Replace this:
new_r["best_move"]     = max(new_r["move_pct"],
                              r.get("best_move", 0.0))
With this:
new_r["best_move"] = max(
    favorable_move_pct(new_r.get("direction", "long"), new_r["move_pct"]),
    r.get("best_move", 0.0)
)
6) Optional but recommended: sort Move% by favorable move, not raw price move
Without this, short winners sort badly because their raw move_pct is negative.

Inside _refresh_tree() replace the sort block with:

try:
    if sk == "move_pct":
        rows.sort(
            key=lambda r: favorable_move_pct(
                r.get("direction", "long"),
                float(r.get("move_pct", 0) or 0)
            ),
            reverse=self._sort_desc
        )
    else:
        rows.sort(
            key=lambda r: float(str(r.get(sk,0)).replace("%","").replace("$","").replace("+","") or 0),
            reverse=self._sort_desc
        )
except Exception:
    rows.sort(key=lambda r: str(r.get(sk,"")), reverse=self._sort_desc)
Why these are the important ones
These are the remaining places where the scanner was still effectively saying:

“I know direction exists…”
“…but I’ll quietly re-infer it from momentum anyway.”
That’s exactly how a late parabolic-up signal can still get treated wrong.

Tiny summary
If you only want the must-do items:

add resolved_direction() / signal_direction()
patch classify_signal()
patch WatchlistManager.check()
add WatchlistManager.get()
patch ScannerGUI.add_alert()
Those are the big ones.

If you want, next I can do the same thing for ECBStrategy and give you a clean drop-in bot-native strategy file patch.

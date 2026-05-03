"""
patch_scanner.py — one-shot patch script
Run once then delete: python patch_scanner.py
Applies 3 patches to BreakoutScanner.py:
  1. Add alert_sound + chart_patterns imports
  2. Add _init_audio() call in ScannerGUI.start()
  3. Replace _beep() with pygame version
  4. Add chart pattern bonus in BreakoutDetector.score()
"""

with open("BreakoutScanner.py", "r", encoding="utf-8") as f:
    src = f.read()

original = src
patches_applied = []

# ── PATCH 1: Add imports after winsound block ─────────────────────────────────
old1 = """try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False"""

new1 = """try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

# pygame-based audio — plays through actual sound card, not PC speaker
try:
    from alert_sound import init_audio as _init_audio, play_alert as _play_alert
    ALERT_SOUND_AVAILABLE = True
except ImportError:
    ALERT_SOUND_AVAILABLE = False

# geometric chart pattern detection
try:
    from chart_patterns import score_patterns as _score_patterns
    PATTERNS_AVAILABLE = True
except ImportError:
    PATTERNS_AVAILABLE = False"""

if old1 in src:
    src = src.replace(old1, new1, 1)
    patches_applied.append("PATCH 1: imports")
else:
    print("PATCH 1 FAIL — winsound block not found")

# ── PATCH 2: Init audio in ScannerGUI.start() ────────────────────────────────
old2 = """    def start(self):
        if not TKINTER_AVAILABLE:
            self.scanner.run_console()
            return
        self.root = tk.Tk()"""

new2 = """    def start(self):
        if not TKINTER_AVAILABLE:
            self.scanner.run_console()
            return
        if ALERT_SOUND_AVAILABLE:
            _init_audio()
        self.root = tk.Tk()"""

if old2 in src:
    src = src.replace(old2, new2, 1)
    patches_applied.append("PATCH 2: audio init")
else:
    print("PATCH 2 FAIL — start() not found")

# ── PATCH 3: Replace _beep with pygame version ────────────────────────────────
old3 = """    def _beep(self, signal: BreakoutSignal, escalation: int = 0):
        if not self.scanner.config.get("enable_sound_alert", True): return
        try:
            vol = self.volume_var.get() if hasattr(self, "volume_var") else 0.7
            if vol < 0.05: return
            if ALERT_SOUND_AVAILABLE:
                # pygame-based — plays through your actual sound card
                _play_alert(level=escalation, volume=vol)
            elif WINSOUND_AVAILABLE:
                # fallback: winsound (may be silent on modern PCs)
                patterns = {
                    0: [(650, 220)],
                    1: [(900, 220),(900, 220)],
                    2: [(1100,200),(1100,200),(1100,200)],
                    3: [(1400,150),(1400,150),(1400,150),(1400,150)],
                }
                for freq, dur in patterns.get(escalation, [(650, 220)]):
                    winsound.Beep(freq, dur)
                    time.sleep(0.05)
        except Exception:
            pass"""

# Check if already patched
if "ALERT_SOUND_AVAILABLE" in src and "_play_alert" in src:
    patches_applied.append("PATCH 3: _beep already patched")
else:
    old3_orig = """    def _beep(self, signal: BreakoutSignal, escalation: int = 0):
        if not WINSOUND_AVAILABLE: return
        if not self.scanner.config.get("enable_sound_alert", True): return
        try:
            if self.volume_var.get() < 0.05: return
            patterns = {
                0: [(650, 220)],
                1: [(900, 220),(900, 220)],
                2: [(1100,200),(1100,200),(1100,200)],
                3: [(1400,150),(1400,150),(1400,150),(1400,150)],
            }
            for freq, dur in patterns.get(escalation, [(650, 220)]):
                winsound.Beep(freq, dur)
                time.sleep(0.05)
        except Exception:
            pass"""

    new3 = """    def _beep(self, signal: BreakoutSignal, escalation: int = 0):
        if not self.scanner.config.get("enable_sound_alert", True): return
        try:
            vol = self.volume_var.get() if hasattr(self, "volume_var") else 0.7
            if vol < 0.05: return
            if ALERT_SOUND_AVAILABLE:
                _play_alert(level=escalation, volume=vol)
            elif WINSOUND_AVAILABLE:
                patterns = {
                    0: [(650, 220)],
                    1: [(900, 220),(900, 220)],
                    2: [(1100,200),(1100,200),(1100,200)],
                    3: [(1400,150),(1400,150),(1400,150),(1400,150)],
                }
                for freq, dur in patterns.get(escalation, [(650, 220)]):
                    winsound.Beep(freq, dur)
                    time.sleep(0.05)
        except Exception:
            pass"""

    if old3_orig in src:
        src = src.replace(old3_orig, new3, 1)
        patches_applied.append("PATCH 3: _beep replaced")
    else:
        print("PATCH 3 FAIL — _beep not found")

# ── PATCH 4: Chart pattern bonus in score() ───────────────────────────────────
old4 = """        vs = self._vol_spike(volumes)
        if vs >= 3.0:   sc = min(1.0, sc + 0.10)
        elif vs >= 2.0: sc = min(1.0, sc + 0.05)
        return round(sc, 3)"""

new4 = """        vs = self._vol_spike(volumes)
        if vs >= 3.0:   sc = min(1.0, sc + 0.10)
        elif vs >= 2.0: sc = min(1.0, sc + 0.05)

        # Chart pattern confirmation — adds up to +0.20 when a strong pattern aligns
        if PATTERNS_AVAILABLE:
            try:
                pat = _score_patterns(prices, volumes)
                if pat["best_confidence"] >= 0.55:
                    sc = min(1.0, sc + pat["pattern_score"] * 0.20)
                    pd._pattern     = pat["best_pattern"]
                    pd._pattern_dir = pat["direction"]
            except Exception:
                pass

        return round(sc, 3)"""

if "Chart pattern confirmation" in src:
    patches_applied.append("PATCH 4: already patched")
elif old4 in src:
    src = src.replace(old4, new4, 1)
    patches_applied.append("PATCH 4: chart pattern scoring")
else:
    print("PATCH 4 FAIL — score() end not found")

# ── Write if changed ──────────────────────────────────────────────────────────
if src != original:
    with open("BreakoutScanner.py", "w", encoding="utf-8") as f:
        f.write(src)
    print("BreakoutScanner.py updated successfully.")
else:
    print("No changes made — already up to date.")

for p in patches_applied:
    print(f"  ✓ {p}")

print("\nDone. You can delete patch_scanner.py now.")
print("Then run: python alert_sound.py   (sound test)")
print("Then run: python BreakoutScanner.py")

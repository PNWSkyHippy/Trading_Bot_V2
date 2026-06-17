"""
chart_patterns.py
=================
Geometric chart-pattern AND candlestick-signal detection.

Chart patterns  (use close prices + volumes, full window):
  Triangles   : Ascending · Descending · Symmetrical  (trend-context direction)
  Wedges      : Rising Wedge · Falling Wedge
  Flags       : Bull Flag · Bear Flag
  Pennants    : Bull Pennant · Bear Pennant
  Reversals   : Head & Shoulders · Inv Head & Shoulders
                Double Top · Double Bottom · Cup & Handle
  Misc        : Consolidation Breakout · Parabolic Acceleration · Volume Climax

Candlestick signals (use OHLCV, look at last 1-5 candles):
  Bearish     : Shooting Star · Gravestone Doji · Bearish Engulfing
                Evening Star · Three Black Crows · Bearish Exhaustion
  Bullish     : Hammer · Dragonfly Doji · Bullish Engulfing
                Morning Star · Three White Soldiers · Bullish Exhaustion
  Neutral     : Doji

Usage:
    detector = PatternDetector()
    results  = detector.detect(closes, volumes)
    # — or with full OHLCV for candlestick signals —
    results  = detector.detect(closes, volumes, opens=opens, highs=highs, lows=lows)
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import math


@dataclass
class PatternResult:
    name:        str
    confidence:  float   # 0.0 – 1.0
    direction:   str     # "LONG" | "SHORT" | "NEUTRAL"
    description: str
    score:       float


class PatternDetector:
    MIN_CANDLES = 20

    # ── Public API ────────────────────────────────────────────────────────

    def detect(self,
               prices:  List[float],
               volumes: List[float],
               opens:   Optional[List[float]] = None,
               highs:   Optional[List[float]] = None,
               lows:    Optional[List[float]] = None,
               min_confidence: float = 0.40) -> List[PatternResult]:
        """Run all detectors.  OHLCV optional — enables candlestick signals."""
        if len(prices) < self.MIN_CANDLES:
            return []

        chart_fns = [
            self._ascending_triangle,
            self._descending_triangle,
            self._symmetrical_triangle,
            self._rising_wedge,
            self._falling_wedge,
            self._bull_flag,
            self._bear_flag,
            self._bull_pennant,
            self._bear_pennant,
            self._head_and_shoulders,
            self._inv_head_and_shoulders,
            self._double_top,
            self._double_bottom,
            self._cup_and_handle,
            self._consolidation_breakout,
            self._parabolic_acceleration,
            self._volume_climax,
        ]

        results = []
        for fn in chart_fns:
            try:
                r = fn(prices, volumes)
                if r and r.confidence >= min_confidence:
                    results.append(r)
            except Exception:
                continue

        if opens and highs and lows and len(opens) == len(prices):
            candle_fns = [
                self._shooting_star,
                self._hammer,
                self._gravestone_doji,
                self._dragonfly_doji,
                self._doji,
                self._bearish_engulfing,
                self._bullish_engulfing,
                self._evening_star,
                self._morning_star,
                self._three_black_crows,
                self._three_white_soldiers,
                self._bearish_exhaustion,
                self._bullish_exhaustion,
            ]
            for fn in candle_fns:
                try:
                    r = fn(opens, highs, lows, prices, volumes)
                    if r and r.confidence >= min_confidence:
                        results.append(r)
                except Exception:
                    continue

        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

    def best(self, prices, volumes, **kw):
        r = self.detect(prices, volumes, **kw)
        return r[0] if r else None

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _linreg_slope(values: List[float]) -> float:
        n = len(values)
        if n < 2: return 0.0
        xs = list(range(n)); mx = sum(xs)/n; my = sum(values)/n
        num = sum((xs[i]-mx)*(values[i]-my) for i in range(n))
        den = sum((xs[i]-mx)**2 for i in range(n))
        if den == 0: return 0.0
        return (num/den) / (my if my != 0 else 1.0)

    @staticmethod
    def _range_pct(values: List[float]) -> float:
        mn, mx = min(values), max(values)
        return (mx-mn)/mn*100 if mn != 0 else 0.0

    @staticmethod
    def _pivot_highs(prices: List[float], window: int = 3) -> List[float]:
        return [prices[i] for i in range(window, len(prices)-window)
                if prices[i] == max(prices[i-window:i+window+1])]

    @staticmethod
    def _pivot_lows(prices: List[float], window: int = 3) -> List[float]:
        return [prices[i] for i in range(window, len(prices)-window)
                if prices[i] == min(prices[i-window:i+window+1])]

    @staticmethod
    def _pivot_highs_idx(prices: List[float], window: int = 3) -> List[Tuple[int,float]]:
        return [(i, prices[i]) for i in range(window, len(prices)-window)
                if prices[i] == max(prices[i-window:i+window+1])]

    @staticmethod
    def _pivot_lows_idx(prices: List[float], window: int = 3) -> List[Tuple[int,float]]:
        return [(i, prices[i]) for i in range(window, len(prices)-window)
                if prices[i] == min(prices[i-window:i+window+1])]

    @staticmethod
    def _prior_trend(prices: List[float], frac: float = 0.25) -> float:
        """Slope of the first `frac` of the series — proxy for incoming trend."""
        n = max(5, int(len(prices) * frac))
        return PatternDetector._linreg_slope(prices[:n])

    # ── Candlestick helpers ───────────────────────────────────────────────

    @staticmethod
    def _cnd(o, h, l, c):
        rng   = h - l if h > l else abs(c-o) or 1e-9
        body  = abs(c - o)
        upper = h - max(o, c)
        lower = min(o, c) - l
        bull  = c >= o
        return rng, body, upper, lower, bull

    # ── Chart pattern implementations ────────────────────────────────────

    def _ascending_triangle(self, prices, volumes):
        highs = self._pivot_highs(prices)
        lows  = self._pivot_lows(prices)
        if len(highs) < 2 or len(lows) < 2: return None

        hs = self._linreg_slope(highs)
        ls = self._linreg_slope(lows)

        flat_top    = abs(hs) < 0.006
        rising_base = ls > 0.003
        if not (flat_top and rising_base): return None

        re = self._range_pct(prices[:len(prices)//2])
        rl = self._range_pct(prices[len(prices)//2:])
        conv = rl < re * 0.75

        # Trend context: entered from uptrend → LONG; downtrend → SHORT
        prior = self._prior_trend(prices)
        direction = "SHORT" if prior < -0.002 else "LONG"

        score = 0.35 + 0.25*(flat_top) + 0.25*conv + 0.15*(self._linreg_slope(volumes)<0)
        desc  = (f"Rising base (slope={ls:.4f}) + flat resistance. "
                 f"Entry trend={'down' if prior<-0.002 else 'up'} → {direction}.")
        return PatternResult("Ascending Triangle", min(score,1.0), direction, desc, score)

    def _descending_triangle(self, prices, volumes):
        highs = self._pivot_highs(prices)
        lows  = self._pivot_lows(prices)
        if len(highs) < 2 or len(lows) < 2: return None

        hs = self._linreg_slope(highs)
        ls = self._linreg_slope(lows)

        falling_top  = hs < -0.003
        flat_base    = abs(ls) < 0.006
        if not (falling_top and flat_base): return None

        re = self._range_pct(prices[:len(prices)//2])
        rl = self._range_pct(prices[len(prices)//2:])
        conv = rl < re * 0.75

        prior     = self._prior_trend(prices)
        direction = "LONG" if prior > 0.002 else "SHORT"

        score = 0.35 + 0.25*flat_base + 0.25*conv + 0.15*(self._linreg_slope(volumes)<0)
        desc  = (f"Falling highs (slope={hs:.4f}) + flat support. "
                 f"Entry trend={'up' if prior>0.002 else 'down'} → {direction}.")
        return PatternResult("Descending Triangle", min(score,1.0), direction, desc, score)

    def _symmetrical_triangle(self, prices, volumes):
        highs = self._pivot_highs(prices)
        lows  = self._pivot_lows(prices)
        if len(highs) < 2 or len(lows) < 2: return None

        hs = self._linreg_slope(highs)
        ls = self._linreg_slope(lows)
        if not (hs < -0.002 and ls > 0.002): return None

        re = self._range_pct(prices[:len(prices)//2])
        rl = self._range_pct(prices[len(prices)//2:])
        conv = rl < re * 0.70

        prior     = self._prior_trend(prices)
        direction = "LONG" if prior > 0.001 else "SHORT"

        score = 0.40*conv + 0.30 + 0.15*(self._linreg_slope(volumes)<0) + 0.15
        desc  = f"Converging highs/lows. Entry trend={'up' if prior>0 else 'down'} → {direction}."
        return PatternResult("Symmetrical Triangle", min(score,1.0), direction, desc, score)

    def _rising_wedge(self, prices, volumes):
        """Both trendlines rising but converging — bearish regardless of context."""
        highs = self._pivot_highs(prices)
        lows  = self._pivot_lows(prices)
        if len(highs) < 2 or len(lows) < 2: return None

        hs = self._linreg_slope(highs)
        ls = self._linreg_slope(lows)

        # Both rising, lows rising faster than highs (converging upward)
        both_rising = hs > 0.002 and ls > 0.002
        converging  = ls > hs + 0.001   # lower line steeper = squeezing
        if not (both_rising and converging): return None

        re = self._range_pct(prices[:len(prices)//2])
        rl = self._range_pct(prices[len(prices)//2:])
        tightening = rl < re * 0.80

        vol_declining = self._linreg_slope(volumes) < 0

        score = 0.40 + 0.25*tightening + 0.20 + 0.15*vol_declining
        desc  = (f"Both trendlines rising (top={hs:.4f}, bottom={ls:.4f}), converging. "
                 f"Bearish — breakdown expected despite rising price.")
        return PatternResult("Rising Wedge", min(score,1.0), "SHORT", desc, score)

    def _falling_wedge(self, prices, volumes):
        """Both trendlines falling but converging — bullish reversal/continuation."""
        highs = self._pivot_highs(prices)
        lows  = self._pivot_lows(prices)
        if len(highs) < 2 or len(lows) < 2: return None

        hs = self._linreg_slope(highs)
        ls = self._linreg_slope(lows)

        both_falling = hs < -0.002 and ls < -0.002
        converging   = hs > ls + 0.001   # upper line less steep = squeezing
        if not (both_falling and converging): return None

        re = self._range_pct(prices[:len(prices)//2])
        rl = self._range_pct(prices[len(prices)//2:])
        tightening = rl < re * 0.80

        score = 0.40 + 0.25*tightening + 0.20 + 0.15*(self._linreg_slope(volumes)<0)
        desc  = (f"Both trendlines falling (top={hs:.4f}, bottom={ls:.4f}), converging. "
                 f"Bullish — breakout upward expected.")
        return PatternResult("Falling Wedge", min(score,1.0), "LONG", desc, score)

    def _bull_flag(self, prices, volumes):
        n    = len(prices)
        pole = prices[:n//3]; flag = prices[n//3:]
        pm   = (pole[-1]-pole[0])/pole[0]*100 if pole[0] else 0
        fm   = (flag[-1]-flag[0])/flag[0]*100 if flag[0] else 0
        fr   = self._range_pct(flag)

        if not (pm > 4.0 and -4.0 < fm < 0.5 and fr < 3.0): return None

        pv = sum(volumes[:n//3])/max(n//3,1)
        fv = sum(volumes[n//3:])/max(len(volumes[n//3:]),1)
        score = 0.35*(pm>4) + 0.25*(-4<fm<0.5) + 0.25*(fr<3) + 0.15*(fv<pv)
        return PatternResult("Bull Flag", min(score,1.0), "LONG",
            f"Pole +{pm:.1f}% then tight pullback ({fr:.1f}% range).", score)

    def _bear_flag(self, prices, volumes):
        n    = len(prices)
        pole = prices[:n//3]; flag = prices[n//3:]
        pm   = (pole[-1]-pole[0])/pole[0]*100 if pole[0] else 0
        fm   = (flag[-1]-flag[0])/flag[0]*100 if flag[0] else 0
        fr   = self._range_pct(flag)

        if not (pm < -4.0 and -0.5 < fm < 4.0 and fr < 3.0): return None

        pv = sum(volumes[:n//3])/max(n//3,1)
        fv = sum(volumes[n//3:])/max(len(volumes[n//3:]),1)
        score = 0.35*(pm<-4) + 0.25*(-0.5<fm<4) + 0.25*(fr<3) + 0.15*(fv<pv)
        return PatternResult("Bear Flag", min(score,1.0), "SHORT",
            f"Pole {pm:.1f}% then tight bounce ({fr:.1f}% range).", score)

    def _bull_pennant(self, prices, volumes):
        """Strong up-pole + converging (symmetrical) consolidation."""
        n    = len(prices)
        pole = prices[:n//3]; pnt = prices[n//3:]
        pm   = (pole[-1]-pole[0])/pole[0]*100 if pole[0] else 0
        if pm < 4.0: return None

        ph = self._pivot_highs(pnt); pl = self._pivot_lows(pnt)
        if len(ph) < 2 or len(pl) < 2: return None
        hs = self._linreg_slope(ph); ls = self._linreg_slope(pl)
        converging = hs < -0.001 and ls > 0.001
        if not converging: return None

        score = 0.40 + 0.30*(pm>6) + 0.30*converging
        return PatternResult("Bull Pennant", min(score,1.0), "LONG",
            f"Pole +{pm:.1f}% + converging pennant. Breakout up expected.", score)

    def _bear_pennant(self, prices, volumes):
        n    = len(prices)
        pole = prices[:n//3]; pnt = prices[n//3:]
        pm   = (pole[-1]-pole[0])/pole[0]*100 if pole[0] else 0
        if pm > -4.0: return None

        ph = self._pivot_highs(pnt); pl = self._pivot_lows(pnt)
        if len(ph) < 2 or len(pl) < 2: return None
        hs = self._linreg_slope(ph); ls = self._linreg_slope(pl)
        converging = hs < -0.001 and ls > 0.001
        if not converging: return None

        score = 0.40 + 0.30*(pm<-6) + 0.30*converging
        return PatternResult("Bear Pennant", min(score,1.0), "SHORT",
            f"Pole {pm:.1f}% + converging pennant. Breakdown expected.", score)

    def _head_and_shoulders(self, prices, volumes):
        ph = self._pivot_highs_idx(prices, window=5)
        if len(ph) < 3: return None

        # Find the highest peak (head)
        hi = max(range(len(ph)), key=lambda i: ph[i][1])
        if hi == 0 or hi == len(ph)-1: return None

        ls_v = ph[hi-1][1]; hd_v = ph[hi][1]; rs_v = ph[hi+1][1]
        if not (hd_v > ls_v and hd_v > rs_v): return None

        avg_sh = (ls_v + rs_v) / 2
        sym    = 1 - abs(ls_v-rs_v)/avg_sh if avg_sh else 0
        head_h = (hd_v - avg_sh) / avg_sh

        if head_h < 0.015: return None   # head not clearly higher

        score = 0.35 + 0.30*(sym>0.85) + 0.20*(head_h>0.03) + 0.15*(self._linreg_slope(volumes)<0)
        desc  = (f"L-shoulder={ls_v:.2f}, Head={hd_v:.2f}, R-shoulder={rs_v:.2f}. "
                 f"Symmetry={sym:.0%}. Neckline breakdown expected.")
        return PatternResult("Head & Shoulders", min(score,1.0), "SHORT", desc, score)

    def _inv_head_and_shoulders(self, prices, volumes):
        pl = self._pivot_lows_idx(prices, window=5)
        if len(pl) < 3: return None

        li = min(range(len(pl)), key=lambda i: pl[i][1])
        if li == 0 or li == len(pl)-1: return None

        ls_v = pl[li-1][1]; hd_v = pl[li][1]; rs_v = pl[li+1][1]
        if not (hd_v < ls_v and hd_v < rs_v): return None

        avg_sh = (ls_v + rs_v) / 2
        sym    = 1 - abs(ls_v-rs_v)/avg_sh if avg_sh else 0
        head_d = (avg_sh - hd_v) / avg_sh

        if head_d < 0.015: return None

        score = 0.35 + 0.30*(sym>0.85) + 0.20*(head_d>0.03) + 0.15*(self._linreg_slope(volumes)>0)
        desc  = (f"L-shoulder={ls_v:.2f}, Head={hd_v:.2f}, R-shoulder={rs_v:.2f}. "
                 f"Symmetry={sym:.0%}. Neckline breakout expected.")
        return PatternResult("Inv Head & Shoulders", min(score,1.0), "LONG", desc, score)

    def _double_top(self, prices, volumes):
        ph = self._pivot_highs_idx(prices, window=4)
        if len(ph) < 2: return None

        # Last two significant highs
        p1, p2 = ph[-2], ph[-1]
        if p2[0] - p1[0] < 6: return None
        diff   = abs(p1[1]-p2[1]) / max(p1[1], p2[1])
        if diff > 0.018: return None   # peaks must be genuinely similar

        # Valley between them
        valley = min(prices[p1[0]:p2[0]+1]) if p1[0] < p2[0] else None
        if valley is None: return None
        pullback = (max(p1[1],p2[1]) - valley) / max(p1[1],p2[1])
        if pullback < 0.03: return None   # meaningful trough between

        prior = self._prior_trend(prices[:p1[0]+1]) if p1[0] >= 8 else self._prior_trend(prices)
        if prior < 0.001: return None

        # Confirmed double top should be breaking or retesting below the neckline.
        cur_drop = (p2[1] - prices[-1]) / p2[1]
        confirming = prices[-1] <= valley * 1.005
        if not confirming: return None

        score = 0.45 + 0.25*(diff<0.01) + 0.20*(pullback>0.045) + 0.10*(cur_drop>0.02)
        desc  = f"Two similar peaks at {p1[1]:.2f}/{p2[1]:.2f} ({diff:.1%} apart), neckline={valley:.2f}, confirmed below neckline."
        return PatternResult("Double Top", min(score,1.0), "SHORT", desc, score)

    def _double_bottom(self, prices, volumes):
        pl = self._pivot_lows_idx(prices, window=4)
        if len(pl) < 2: return None

        t1, t2 = pl[-2], pl[-1]
        if t2[0] - t1[0] < 6: return None
        diff   = abs(t1[1]-t2[1]) / max(t1[1], t2[1])
        if diff > 0.018: return None

        peak  = max(prices[t1[0]:t2[0]+1]) if t1[0] < t2[0] else None
        if peak is None: return None
        bounce = (peak - min(t1[1],t2[1])) / peak
        if bounce < 0.03: return None

        prior = self._prior_trend(prices[:t1[0]+1]) if t1[0] >= 8 else self._prior_trend(prices)
        if prior > -0.001: return None

        # Confirmed double bottom should be breaking or retesting above the neckline.
        cur_rise = (prices[-1] - t2[1]) / t2[1]
        confirming = prices[-1] >= peak * 0.995
        if not confirming: return None

        score = 0.45 + 0.25*(diff<0.01) + 0.20*(bounce>0.045) + 0.10*(cur_rise>0.02)
        desc  = f"Two similar troughs at {t1[1]:.2f}/{t2[1]:.2f} ({diff:.1%} apart), neckline={peak:.2f}, confirmed above neckline."
        return PatternResult("Double Bottom", min(score,1.0), "LONG", desc, score)

    def _cup_and_handle(self, prices, volumes):
        """U-shaped base + small downward handle. Bullish."""
        n = len(prices)
        if n < 30: return None
        cup    = prices[:int(n*0.75)]
        handle = prices[int(n*0.75):]

        # Cup: high on both sides, low in middle
        left_h  = max(cup[:len(cup)//3])
        right_h = max(cup[2*len(cup)//3:])
        bottom  = min(cup[len(cup)//4:3*len(cup)//4])
        depth   = (min(left_h,right_h) - bottom) / min(left_h,right_h)

        u_shape = (depth > 0.04 and
                   abs(left_h-right_h)/max(left_h,right_h) < 0.10)
        if not u_shape: return None

        # Handle: small pullback, less than 50% of cup depth
        handle_move = (handle[-1]-handle[0])/handle[0]*100 if handle[0] else 0
        tight_handle = -5.0 < handle_move < 0.5 and self._range_pct(handle) < depth*100*0.5

        score = 0.40*u_shape + 0.35*tight_handle + 0.25*(depth>0.08)
        desc  = f"Cup depth={depth:.1%}, handle={handle_move:.1f}%. Breakout above rim expected."
        return PatternResult("Cup & Handle", min(score,1.0), "LONG", desc, score)

    def _consolidation_breakout(self, prices, volumes):
        body      = prices[:-5]; tail = prices[-5:]
        br        = self._range_pct(body)
        tm        = (tail[-1]-tail[0])/tail[0]*100 if tail[0] else 0
        tr        = self._range_pct(tail)
        if not (br < 2.5 and (tr > br*1.5 or abs(tm) > 1.0)): return None

        direction = "LONG" if tm > 0 else "SHORT"
        avg_vol   = sum(volumes[:-1])/max(len(volumes[:-1]),1)
        vs        = volumes[-1]/avg_vol if avg_vol else 1.0

        score = 0.30 + 0.30 + 0.25*(vs>1.5) + 0.15*(abs(tm)>1.5)
        return PatternResult("Consolidation Breakout", min(score,1.0), direction,
            f"Body range {br:.2f}% then {tm:+.2f}% expansion. Vol spike {vs:.1f}x.", score)

    def _parabolic_acceleration(self, prices, volumes):
        if len(prices) < 10: return None
        rets = [(prices[i]-prices[i-1])/prices[i-1]*100 for i in range(1,len(prices))]
        h    = len(rets)//2
        em   = sum(rets[:h])/max(h,1); lm = sum(rets[h:])/max(len(rets[h:]),1)
        if lm - em < 0.1: return None
        t    = len(rets)//3
        m1,m2,m3 = sum(rets[:t])/max(t,1), sum(rets[t:2*t])/max(t,1), sum(rets[2*t:])/max(len(rets[2*t:]),1)
        sd   = (m3-m2)-(m2-m1)
        direction = "LONG" if lm > 0 else "SHORT"
        score = 0.40 + 0.30*(sd>0) + 0.15*(self._range_pct(prices)<15) + 0.15*(abs(lm)>0.3)
        return PatternResult("Parabolic Acceleration", min(score,1.0), direction,
            f"Momentum early={em:.3f}% → late={lm:.3f}%. Curving up={sd>0}.", score)

    def _volume_climax(self, prices, volumes):
        if len(volumes) < 5: return None
        avg = sum(volumes[:-1])/max(len(volumes[:-1]),1)
        spk = volumes[-1]/avg if avg else 1.0
        if spk < 3.0: return None
        pm  = (prices[-1]-prices[-2])/prices[-2]*100 if prices[-2] else 0
        direction = "LONG" if pm > 0 else "SHORT"
        score = (0.50 if spk>=6 else 0.35 if spk>=4 else 0.20) + (0.30 if abs(pm)>1 else 0.15) + 0.20
        return PatternResult("Volume Climax", min(score,1.0), direction,
            f"Volume {spk:.1f}x avg on {pm:+.2f}% candle.", score)

    # ── Candlestick signal implementations ───────────────────────────────

    def _shooting_star(self, opens, highs, lows, closes, volumes):
        """Small body near bottom + long upper wick after rally. Bearish."""
        o,h,l,c = opens[-1],highs[-1],lows[-1],closes[-1]
        rng,body,upper,lower,bull = self._cnd(o,h,l,c)
        if rng == 0: return None

        small_body  = body / rng < 0.30
        long_upper  = upper / rng > 0.55
        little_lower= lower / rng < 0.20
        prior_up    = self._prior_trend(closes) > 0.001

        if not (small_body and long_upper and little_lower): return None

        score = 0.35 + 0.25*long_upper + 0.25*(body/rng<0.15) + 0.15*prior_up
        return PatternResult("Shooting Star", min(score,1.0), "SHORT",
            f"Body={body/rng:.0%} of range, upper wick={upper/rng:.0%}. "
            f"Bearish reversal after {'up' if prior_up else 'neutral'} trend.", score)

    def _hammer(self, opens, highs, lows, closes, volumes):
        """Small body near top + long lower wick after decline. Bullish."""
        o,h,l,c = opens[-1],highs[-1],lows[-1],closes[-1]
        rng,body,upper,lower,bull = self._cnd(o,h,l,c)
        if rng == 0: return None

        small_body  = body / rng < 0.30
        long_lower  = lower / rng > 0.55
        little_upper= upper / rng < 0.20
        prior_down  = self._prior_trend(closes) < -0.001

        if not (small_body and long_lower and little_upper): return None

        score = 0.35 + 0.25*long_lower + 0.25*(body/rng<0.15) + 0.15*prior_down
        return PatternResult("Hammer", min(score,1.0), "LONG",
            f"Body={body/rng:.0%} of range, lower wick={lower/rng:.0%}. "
            f"Bullish reversal after {'down' if prior_down else 'neutral'} trend.", score)

    def _gravestone_doji(self, opens, highs, lows, closes, volumes):
        """Open≈close near low, very long upper wick. Strong bearish signal."""
        o,h,l,c = opens[-1],highs[-1],lows[-1],closes[-1]
        rng,body,upper,lower,_ = self._cnd(o,h,l,c)
        if rng == 0: return None

        doji_body  = body / rng < 0.10
        long_upper = upper / rng > 0.70
        tiny_lower = lower / rng < 0.10

        if not (doji_body and long_upper and tiny_lower): return None

        score = 0.50 + 0.30*(upper/rng>0.85) + 0.20*(self._prior_trend(closes)>0)
        return PatternResult("Gravestone Doji", min(score,1.0), "SHORT",
            f"Open≈close at bottom, upper wick={upper/rng:.0%}. Rejection at highs.", score)

    def _dragonfly_doji(self, opens, highs, lows, closes, volumes):
        """Open≈close near high, very long lower wick. Bullish reversal."""
        o,h,l,c = opens[-1],highs[-1],lows[-1],closes[-1]
        rng,body,upper,lower,_ = self._cnd(o,h,l,c)
        if rng == 0: return None

        doji_body  = body / rng < 0.10
        long_lower = lower / rng > 0.70
        tiny_upper = upper / rng < 0.10

        if not (doji_body and long_lower and tiny_upper): return None

        score = 0.50 + 0.30*(lower/rng>0.85) + 0.20*(self._prior_trend(closes)<0)
        return PatternResult("Dragonfly Doji", min(score,1.0), "LONG",
            f"Open≈close at top, lower wick={lower/rng:.0%}. Support rejection.", score)

    def _doji(self, opens, highs, lows, closes, volumes):
        """Open≈close, indecision. Reversal warning."""
        o,h,l,c = opens[-1],highs[-1],lows[-1],closes[-1]
        rng,body,_,_,_ = self._cnd(o,h,l,c)
        if rng == 0: return None
        if body/rng > 0.08: return None   # not a doji

        prior = self._prior_trend(closes)
        direction = "SHORT" if prior > 0.002 else "LONG" if prior < -0.002 else "NEUTRAL"

        score = 0.40 + 0.30*(body/rng<0.04) + 0.30
        return PatternResult("Doji", min(score,1.0), direction,
            f"Body={body/rng:.1%} of range. Indecision candle, possible reversal.", score)

    def _bearish_engulfing(self, opens, highs, lows, closes, volumes):
        if len(opens) < 2: return None
        o1,c1 = opens[-2],closes[-2]
        o2,c2 = opens[-1],closes[-1]
        prev_bull  = c1 > o1
        curr_bear  = c2 < o2
        engulfs    = o2 >= c1 and c2 <= o1   # current body wraps prior body
        size_ratio = abs(c2-o2) / max(abs(c1-o1), 1e-9)
        if not (prev_bull and curr_bear and engulfs and size_ratio >= 1.05): return None

        score = 0.45 + 0.30*(size_ratio>1.5) + 0.25*(self._prior_trend(closes)>0)
        return PatternResult("Bearish Engulfing", min(score,1.0), "SHORT",
            f"Bearish candle engulfs prior bullish ({size_ratio:.1f}x size).", score)

    def _bullish_engulfing(self, opens, highs, lows, closes, volumes):
        if len(opens) < 2: return None
        o1,c1 = opens[-2],closes[-2]
        o2,c2 = opens[-1],closes[-1]
        prev_bear  = c1 < o1
        curr_bull  = c2 > o2
        engulfs    = o2 <= c1 and c2 >= o1
        size_ratio = abs(c2-o2) / max(abs(c1-o1), 1e-9)
        if not (prev_bear and curr_bull and engulfs and size_ratio >= 1.05): return None

        score = 0.45 + 0.30*(size_ratio>1.5) + 0.25*(self._prior_trend(closes)<0)
        return PatternResult("Bullish Engulfing", min(score,1.0), "LONG",
            f"Bullish candle engulfs prior bearish ({size_ratio:.1f}x size).", score)

    def _evening_star(self, opens, highs, lows, closes, volumes):
        """3-candle: big green → small body/doji → big red. Top reversal."""
        if len(opens) < 3: return None
        o1,c1 = opens[-3],closes[-3]
        o2,c2 = opens[-2],closes[-2]
        o3,c3 = opens[-1],closes[-1]

        big_green = c1-o1 > 0 and (c1-o1)/(highs[-3]-lows[-3]+1e-9) > 0.50
        small_mid = abs(c2-o2) < abs(c1-o1)*0.40
        big_red   = o3-c3 > 0 and (o3-c3)/(highs[-1]-lows[-1]+1e-9) > 0.50
        gap_up    = min(o2,c2) > c1   # star gapped above prior close (ideal)

        if not (big_green and small_mid and big_red): return None

        score = 0.40 + 0.25*gap_up + 0.20*(c3 < (o1+c1)/2) + 0.15
        return PatternResult("Evening Star", min(score,1.0), "SHORT",
            f"Big green → small star → big red. Top reversal signal.", score)

    def _morning_star(self, opens, highs, lows, closes, volumes):
        """3-candle: big red → small body/doji → big green. Bottom reversal."""
        if len(opens) < 3: return None
        o1,c1 = opens[-3],closes[-3]
        o2,c2 = opens[-2],closes[-2]
        o3,c3 = opens[-1],closes[-1]

        big_red   = o1-c1 > 0 and (o1-c1)/(highs[-3]-lows[-3]+1e-9) > 0.50
        small_mid = abs(c2-o2) < abs(o1-c1)*0.40
        big_green = c3-o3 > 0 and (c3-o3)/(highs[-1]-lows[-1]+1e-9) > 0.50
        gap_down  = max(o2,c2) < c1

        if not (big_red and small_mid and big_green): return None

        score = 0.40 + 0.25*gap_down + 0.20*(c3 > (o1+c1)/2) + 0.15
        return PatternResult("Morning Star", min(score,1.0), "LONG",
            f"Big red → small star → big green. Bottom reversal signal.", score)

    def _three_black_crows(self, opens, highs, lows, closes, volumes):
        """3 consecutive large bearish candles. Strong downtrend confirmation."""
        if len(opens) < 3: return None
        bodies = [abs(closes[-i]-opens[-i]) for i in range(1,4)]
        all_bear = all(closes[-i] < opens[-i] for i in range(1,4))
        avg_body = sum(abs(closes[j]-opens[j]) for j in range(len(closes)-6,-1)
                       if j >= 0) / max(6,1)
        big_bodies = all(b > avg_body*0.8 for b in bodies)
        # Each opens within prior body
        nested = all(opens[-i] <= closes[-(i+1)] for i in range(1,3))

        if not (all_bear and big_bodies): return None

        score = 0.40 + 0.30*nested + 0.30*(all(b>avg_body*1.2 for b in bodies))
        return PatternResult("Three Black Crows", min(score,1.0), "SHORT",
            f"3 consecutive large bearish candles. Strong downtrend.", score)

    def _three_white_soldiers(self, opens, highs, lows, closes, volumes):
        """3 consecutive large bullish candles. Strong uptrend confirmation."""
        if len(opens) < 3: return None
        bodies = [abs(closes[-i]-opens[-i]) for i in range(1,4)]
        all_bull = all(closes[-i] > opens[-i] for i in range(1,4))
        avg_body = sum(abs(closes[j]-opens[j]) for j in range(len(closes)-6,-1)
                       if j >= 0) / max(6,1)
        big_bodies = all(b > avg_body*0.8 for b in bodies)
        nested = all(opens[-i] >= closes[-(i+1)] for i in range(1,3))

        if not (all_bull and big_bodies): return None

        score = 0.40 + 0.30*nested + 0.30*(all(b>avg_body*1.2 for b in bodies))
        return PatternResult("Three White Soldiers", min(score,1.0), "LONG",
            f"3 consecutive large bullish candles. Strong uptrend.", score)

    def _bearish_exhaustion(self, opens, highs, lows, closes, volumes):
        """Successively smaller green candles near a top. Momentum dying."""
        if len(opens) < 4: return None
        # Last 3 candles all green but shrinking
        recent_bodies = [abs(closes[-i]-opens[-i]) for i in range(1,4)]
        all_green  = all(closes[-i] > opens[-i] for i in range(1,4))
        shrinking  = recent_bodies[0] < recent_bodies[1] < recent_bodies[2]
        near_top   = closes[-1] > max(closes[-10:-1]) * 0.97 if len(closes) > 10 else False

        if not (all_green and shrinking): return None

        score = 0.35 + 0.30*near_top + 0.20*(recent_bodies[0]/max(recent_bodies[2],1e-9)<0.5) + 0.15
        desc  = (f"3 shrinking green candles: {recent_bodies[2]:.4f} → {recent_bodies[1]:.4f} "
                 f"→ {recent_bodies[0]:.4f}. Buying pressure fading at top.")
        return PatternResult("Bearish Exhaustion", min(score,1.0), "SHORT", desc, score)

    def _bullish_exhaustion(self, opens, highs, lows, closes, volumes):
        """Successively smaller red candles near a bottom. Selling drying up."""
        if len(opens) < 4: return None
        recent_bodies = [abs(closes[-i]-opens[-i]) for i in range(1,4)]
        all_red   = all(closes[-i] < opens[-i] for i in range(1,4))
        shrinking = recent_bodies[0] < recent_bodies[1] < recent_bodies[2]
        near_bot  = closes[-1] < min(closes[-10:-1]) * 1.03 if len(closes) > 10 else False

        if not (all_red and shrinking): return None

        score = 0.35 + 0.30*near_bot + 0.20*(recent_bodies[0]/max(recent_bodies[2],1e-9)<0.5) + 0.15
        desc  = (f"3 shrinking red candles: {recent_bodies[2]:.4f} → {recent_bodies[1]:.4f} "
                 f"→ {recent_bodies[0]:.4f}. Selling pressure fading at bottom.")
        return PatternResult("Bullish Exhaustion", min(score,1.0), "LONG", desc, score)


# ── Convenience function ──────────────────────────────────────────────────────

def score_patterns(prices, volumes, opens=None, highs=None, lows=None):
    detector = PatternDetector()
    results  = detector.detect(prices, volumes, opens=opens, highs=highs, lows=lows)
    if not results:
        return {"best_pattern":"none","best_confidence":0.0,
                "direction":"NEUTRAL","pattern_score":0.0,"all_patterns":[]}
    best = results[0]
    return {"best_pattern":best.name,"best_confidence":best.confidence,
            "direction":best.direction,"pattern_score":best.confidence,
            "all_patterns":[{"name":r.name,"confidence":r.confidence,
                             "direction":r.direction} for r in results]}

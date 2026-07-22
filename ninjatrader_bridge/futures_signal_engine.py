"""Pure, completed-candle futures confluence calculations for the scanner."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class SignalAssessment:
    state: str
    direction: str
    score: int
    reason: str
    metrics: Dict[str, object]


def _number(value, default=0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return result if math.isfinite(result) else default


def _parse_time(value: object, source_timezone: str) -> datetime:
    text = str(value).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(source_timezone))
    return parsed.astimezone(timezone.utc)


def _clean_bars(bars: Iterable[dict], source_timezone: str) -> List[dict]:
    clean = []
    seen = set()
    for bar in bars:
        try:
            stamp = _parse_time(bar["time"], source_timezone)
            values = {key: _number(bar[key], float("nan")) for key in ("open", "high", "low", "close", "volume")}
        except (KeyError, TypeError, ValueError):
            continue
        if stamp in seen or not all(math.isfinite(v) for v in values.values()):
            continue
        if min(values["open"], values["high"], values["low"], values["close"]) <= 0:
            continue
        if values["low"] > min(values["open"], values["close"]) or values["high"] < max(values["open"], values["close"]):
            continue
        seen.add(stamp)
        clean.append({"dt": stamp, **values})
    return sorted(clean, key=lambda item: item["dt"])


def aggregate_completed(bars: Sequence[dict], minutes: int, source_timezone: str) -> List[dict]:
    """Aggregate only complete, clock-aligned buckets; never use a partial bucket."""
    clean = _clean_bars(bars, source_timezone)
    if minutes <= 1:
        return clean
    groups: Dict[datetime, List[dict]] = {}
    for bar in clean:
        stamp = bar["dt"].replace(second=0, microsecond=0)
        bucket = stamp.replace(minute=(stamp.minute // minutes) * minutes)
        groups.setdefault(bucket, []).append(bar)
    result = []
    for bucket in sorted(groups):
        group = groups[bucket]
        expected = [bucket + timedelta(minutes=i) for i in range(minutes)]
        actual = [item["dt"].replace(second=0, microsecond=0) for item in group]
        if actual != expected:
            continue
        result.append({
            "dt": bucket,
            "open": group[0]["open"],
            "high": max(item["high"] for item in group),
            "low": min(item["low"] for item in group),
            "close": group[-1]["close"],
            "volume": sum(item["volume"] for item in group),
        })
    return result


def ema_series(values: Sequence[float], period: int) -> List[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    output = [float(values[0])]
    for value in values[1:]:
        output.append(alpha * float(value) + (1.0 - alpha) * output[-1])
    return output


def rsi_series(values: Sequence[float], period: int = 14) -> List[Optional[float]]:
    output: List[Optional[float]] = [None] * len(values)
    if len(values) <= period:
        return output
    gains = [max(0.0, values[i] - values[i - 1]) for i in range(1, len(values))]
    losses = [max(0.0, values[i - 1] - values[i]) for i in range(1, len(values))]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for index in range(period, len(values)):
        if index > period:
            avg_gain = ((period - 1) * avg_gain + gains[index - 1]) / period
            avg_loss = ((period - 1) * avg_loss + losses[index - 1]) / period
        output[index] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return output


def _true_ranges(bars: Sequence[dict]) -> List[float]:
    ranges = []
    for index, bar in enumerate(bars):
        previous = bar["close"] if index == 0 else bars[index - 1]["close"]
        ranges.append(max(bar["high"] - bar["low"], abs(bar["high"] - previous), abs(bar["low"] - previous)))
    return ranges


def wilder_last(values: Sequence[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    average = sum(values[:period]) / period
    for value in values[period:]:
        average = ((period - 1) * average + value) / period
    return average


def adx_last(bars: Sequence[dict], period: int = 14) -> Optional[float]:
    if len(bars) < period * 2:
        return None
    tr = _true_ranges(bars)[1:]
    plus_dm, minus_dm = [], []
    for index in range(1, len(bars)):
        up = bars[index]["high"] - bars[index - 1]["high"]
        down = bars[index - 1]["low"] - bars[index]["low"]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
    atr = sum(tr[:period]) / period
    plus = sum(plus_dm[:period]) / period
    minus = sum(minus_dm[:period]) / period
    dx = []
    for index in range(period, len(tr) + 1):
        if index > period:
            atr = ((period - 1) * atr + tr[index - 1]) / period
            plus = ((period - 1) * plus + plus_dm[index - 1]) / period
            minus = ((period - 1) * minus + minus_dm[index - 1]) / period
        plus_di = 100.0 * plus / atr if atr > 0 else 0.0
        minus_di = 100.0 * minus / atr if atr > 0 else 0.0
        denom = plus_di + minus_di
        dx.append(100.0 * abs(plus_di - minus_di) / denom if denom > 0 else 0.0)
    return wilder_last(dx, period)


def choppiness_last(bars: Sequence[dict], period: int = 14) -> Optional[float]:
    if len(bars) < period + 1:
        return None
    window = bars[-period:]
    span = max(item["high"] for item in window) - min(item["low"] for item in window)
    if span <= 0:
        return 100.0
    return 100.0 * math.log10(sum(_true_ranges(bars)[-period:]) / span) / math.log10(period)


def _trend(values: Sequence[float], fast: int, slow: int) -> str:
    if len(values) < slow + 1:
        return "unknown"
    fast_values = ema_series(values, fast)
    slow_values = ema_series(values, slow)
    if fast_values[-1] > slow_values[-1] and fast_values[-1] > fast_values[-2]:
        return "long"
    if fast_values[-1] < slow_values[-1] and fast_values[-1] < fast_values[-2]:
        return "short"
    return "flat"


def _session_vwap(bars: Sequence[dict], settings: dict) -> Tuple[List[float], bool]:
    if not bars:
        return [], False
    eastern = ZoneInfo(settings.get("vwap_timezone", "America/New_York"))
    hour, minute = [int(part) for part in settings.get("vwap_session_start", "18:00").split(":")]
    latest_et = bars[-1]["dt"].astimezone(eastern)
    session_date = latest_et.date() if latest_et.time() >= dt_time(hour, minute) else latest_et.date() - timedelta(days=1)
    start_et = datetime.combine(session_date, dt_time(hour, minute), tzinfo=eastern)
    session = [bar for bar in bars if bar["dt"] >= start_et.astimezone(timezone.utc)]
    if not session:
        return [], False
    cumulative_pv = 0.0
    cumulative_volume = 0.0
    values = []
    for bar in session:
        typical = (bar["high"] + bar["low"] + bar["close"]) / 3.0
        cumulative_pv += typical * bar["volume"]
        cumulative_volume += bar["volume"]
        values.append(cumulative_pv / cumulative_volume if cumulative_volume > 0 else typical)
    complete = session[0]["dt"] <= start_et.astimezone(timezone.utc) + timedelta(minutes=1)
    return values, complete


def assess_confluence(symbol: str, bars: Sequence[dict], contract: dict, settings: dict) -> SignalAssessment:
    source_tz = settings.get("source_timezone", "America/Los_Angeles")
    one = aggregate_completed(bars, 1, source_tz)
    three = aggregate_completed(bars, 3, source_tz)
    fifteen = aggregate_completed(bars, 15, source_tz)
    minimum = int(settings.get("minimum_one_minute_bars", 105))
    minimum_three = max(
        int(settings.get("adx_period", 14)) * 2,
        int(settings.get("macd_slow", 26)) + int(settings.get("macd_signal", 9)),
    )
    minimum_fifteen = 6
    if len(one) < minimum or len(three) < minimum_three or len(fifteen) < minimum_fifteen:
        return SignalAssessment("WARMING", "wait", 0,
                                f"enhanced {len(one)}/{minimum} bars; "
                                f"3m={len(three)}/{minimum_three} 15m={len(fifteen)}/{minimum_fifteen}", {})

    closes1 = [bar["close"] for bar in one]
    closes3 = [bar["close"] for bar in three]
    closes15 = [bar["close"] for bar in fifteen]
    fast_period = int(settings.get("ema_fast", 8))
    slow_period = int(settings.get("ema_slow", 20))
    ema_fast = ema_series(closes3, fast_period)
    ema_slow = ema_series(closes3, slow_period)
    gap = ema_fast[-1] - ema_slow[-1]
    previous_gap = ema_fast[-2] - ema_slow[-2]
    direction = "long" if gap > 0 else "short" if gap < 0 else "wait"
    widening = abs(gap) > abs(previous_gap)

    rsi = rsi_series(closes3, int(settings.get("rsi_period", 14)))
    rsi_now = rsi[-1]
    rsi_prev = rsi[-2]
    macd_fast = ema_series(closes3, int(settings.get("macd_fast", 12)))
    macd_slow = ema_series(closes3, int(settings.get("macd_slow", 26)))
    macd_line = [a - b for a, b in zip(macd_fast, macd_slow)]
    macd_signal = ema_series(macd_line, int(settings.get("macd_signal", 9)))
    macd_cross = (
        direction == "long" and macd_line[-2] <= macd_signal[-2] and macd_line[-1] > macd_signal[-1]
    ) or (
        direction == "short" and macd_line[-2] >= macd_signal[-2] and macd_line[-1] < macd_signal[-1]
    )
    macd_aligned = (direction == "long" and macd_line[-1] > macd_signal[-1]) or (
        direction == "short" and macd_line[-1] < macd_signal[-1]
    )

    atr_period = int(settings.get("atr_period", 14))
    atr = wilder_last(_true_ranges(three), atr_period) or 0.0
    ema_gap_atr = abs(gap) / atr if atr > 0 else 0.0
    ema_confirmed = widening or ema_gap_atr >= settings.get("min_ema_gap_atr", 0.35)
    adx = adx_last(three, int(settings.get("adx_period", 14)))
    chop = choppiness_last(three, int(settings.get("choppiness_period", 14)))
    atr_pct = atr / closes3[-1] if closes3[-1] else 0.0
    spike = _true_ranges(three)[-1] / atr if atr > 0 else float("inf")
    volatility_ok = (
        settings.get("min_atr_pct", 0.00005) <= atr_pct <= settings.get("max_atr_pct", 0.006)
        and spike <= settings.get("max_range_atr", 2.5)
        and chop is not None and chop <= settings.get("max_choppiness", 61.8)
    )

    vwap_values, vwap_complete = _session_vwap(one, settings)
    vwap = vwap_values[-1] if vwap_values else None
    vwap_position = vwap is not None and (
        (direction == "long" and closes1[-1] > vwap) or (direction == "short" and closes1[-1] < vwap)
    )
    tolerance = float(settings.get("vwap_touch_tolerance_pct", 0.0005))
    vwap_confirmation = False
    if len(vwap_values) >= 2:
        previous, current = one[-2], one[-1]
        previous_vwap = vwap_values[-2]
        if direction == "long":
            vwap_confirmation = previous["low"] <= previous_vwap * (1 + tolerance) and previous["close"] >= previous_vwap and current["close"] > previous["close"]
        elif direction == "short":
            vwap_confirmation = previous["high"] >= previous_vwap * (1 - tolerance) and previous["close"] <= previous_vwap and current["close"] < previous["close"]

    trends = {
        "1m": _trend(closes1, 8, 20),
        "3m": _trend(closes3, 8, 20),
        "15m": _trend(closes15, 3, 6),
    }
    agreement = sum(1 for value in trends.values() if value == direction)

    prior_15 = fifteen[-13:-1] if len(fifteen) >= 13 else fifteen[:-1]
    support = min((bar["low"] for bar in prior_15), default=fifteen[-1]["low"])
    resistance = max((bar["high"] for bar in prior_15), default=fifteen[-1]["high"])
    room_atr = ((resistance - closes1[-1]) / atr if direction == "long" else (closes1[-1] - support) / atr) if atr > 0 else 0.0

    score = 0.0
    score += 15 if direction != "wait" else 0
    score += 10 if widening else 6 if ema_confirmed else 0
    score += 8 if vwap_position else 0
    score += 8 if vwap_confirmation and vwap_complete else 0
    score += 10 if adx is not None and adx >= settings.get("adx_min", 25) else 0
    rsi_ok = False
    if rsi_now is not None and rsi_prev is not None:
        if direction == "long" and settings.get("rsi_long_min", 52) <= rsi_now <= settings.get("rsi_long_max", 72) and rsi_now > rsi_prev:
            rsi_ok = True
            score += 8
        if direction == "short" and settings.get("rsi_short_min", 28) <= rsi_now <= settings.get("rsi_short_max", 48) and rsi_now < rsi_prev:
            rsi_ok = True
            score += 8
    score += 12 if macd_aligned else 0
    score += 4 if macd_cross else 0
    score += 10 if volatility_ok else 0
    score += agreement * 5
    score += 5 if room_atr >= settings.get("minimum_room_atr", 1.0) else 0
    score = min(100, int(round(score)))

    hard_ready = (
        direction != "wait" and ema_confirmed and vwap_position and rsi_ok and adx is not None
        and adx >= settings.get("adx_min", 25) and volatility_ok
        and macd_aligned and agreement >= 2
    )
    ready_threshold = int(settings.get("ready_score", 65))
    watch_threshold = int(settings.get("watch_score", 38))
    state = "READY" if score >= ready_threshold and hard_ready else "WATCH" if score >= watch_threshold else "WAIT"

    stop_points = atr * float(settings.get("atr_stop_multiplier", 1.5))
    target_points = stop_points * float(settings.get("target_r_multiple", 2.0))
    tick_size = _number(contract.get("tick_size"), 0.0)
    tick_value = _number(contract.get("tick_value"), 0.0)
    stop_dollars = stop_points / tick_size * tick_value if tick_size > 0 else 0.0
    target_dollars = target_points / tick_size * tick_value if tick_size > 0 else 0.0

    reason = (
        f"{direction.upper()} EMA{fast_period}/{slow_period}={ema_fast[-1]:.2f}/{ema_slow[-1]:.2f} "
        f"VWAP={'above' if vwap_position and direction == 'long' else 'below' if vwap_position else 'wrong-side'}"
        f"{'*' if not vwap_complete else ''} ADX={adx:.1f} RSI={rsi_now:.1f} "
        f"MACD={'cross' if macd_cross else 'aligned' if macd_aligned else 'against'} "
        f"CHOP={chop:.1f} TF={agreement}/3 SL={stop_points:.2f}pt/${stop_dollars:.0f} "
        f"TP={target_points:.2f}pt/${target_dollars:.0f} S/R={support:.2f}/{resistance:.2f}"
    )
    metrics = {
        "ema_fast": ema_fast[-1], "ema_slow": ema_slow[-1], "ema_widening": widening,
        "ema_gap_atr": ema_gap_atr, "ema_confirmed": ema_confirmed,
        "vwap": vwap, "vwap_complete": vwap_complete, "vwap_confirmation": vwap_confirmation,
        "adx": adx, "rsi": rsi_now, "macd": macd_line[-1], "macd_signal": macd_signal[-1],
        "atr": atr, "atr_pct": atr_pct, "choppiness": chop, "trends": trends,
        "support": support, "resistance": resistance, "room_atr": room_atr,
        "stop_points": stop_points, "target_points": target_points,
        "stop_dollars": stop_dollars, "target_dollars": target_dollars,
    }
    return SignalAssessment(state, direction, score, reason, metrics)

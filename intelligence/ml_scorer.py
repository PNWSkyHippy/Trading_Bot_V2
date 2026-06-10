"""
=============================================================
  ML SIGNAL SCORER  (Phase 3)
  Learns from YOUR actual trade history to improve signal
  quality over time. Uses a Random Forest classifier trained
  on indicator values at entry and whether the trade won.

  Starts with rule-based scoring (no data needed).
  After 50+ closed trades, ML layer activates automatically.
  After 200+ trades, the model becomes the primary scorer.

  This gets smarter every single day as you trade.
=============================================================
"""

import logging
import json
import pickle
import os
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List, Tuple

import config
from data.database import db

logger = logging.getLogger(__name__)


def _safe_float(value, default: float) -> float:
    """Convert value to float, substituting default for None or unconvertible values.

    dict.get(key, default) only falls back when the key is absent — if the key
    exists with a None value (common when an indicator failed to compute), the
    caller receives None and float(None) raises TypeError.  This helper handles
    both the missing-key and None-value cases cleanly.
    """
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


MODEL_PATH  = "data/ml_model.pkl"
SCALER_PATH = "data/ml_scaler.pkl"
MIN_TRADES_TO_ACTIVATE  = config.ML_MIN_TRADES   # 50
MIN_TRADES_FULL_CONTROL = 200


class MLSignalScorer:
    """
    Random Forest model trained on your actual trade outcomes.
    Features: RSI, MACD histogram, EMA alignment, BB%, volume ratio,
              market condition, time of day, day of week.
    Label: 1 = winning trade, 0 = losing trade.
    """

    def __init__(self, db_ref=None):
        self._db        = db_ref or db
        self.model      = None
        self.scaler     = None
        self.is_trained = False
        self.trade_count= 0
        self._load_model()

    def _load_model(self):
        """Load previously trained model if it exists."""
        try:
            if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
                with open(MODEL_PATH, "rb") as f:
                    self.model = pickle.load(f)
                with open(SCALER_PATH, "rb") as f:
                    self.scaler = pickle.load(f)
                self.is_trained = True
                logger.info("ML model loaded from disk.")
        except Exception as e:
            logger.debug(f"No ML model found, will train when enough data: {e}")

    def _save_model(self):
        try:
            os.makedirs("data", exist_ok=True)
            with open(MODEL_PATH, "wb") as f:
                pickle.dump(self.model, f)
            with open(SCALER_PATH, "wb") as f:
                pickle.dump(self.scaler, f)
            logger.info("ML model saved.")
        except Exception as e:
            logger.error(f"Failed to save ML model: {e}")

    def _build_feature_vector(self, indicators: Dict,
                               entry_time: str = None,
                               condition_adx: float = 25.0) -> Optional[np.ndarray]:
        """Convert indicator snapshot to ML feature vector."""
        try:
            dt = datetime.fromisoformat(entry_time) if entry_time else datetime.now()
            features = [
                _safe_float(indicators.get("rsi"),          50.0),
                _safe_float(indicators.get("macd_hist"),     0.0),
                _safe_float(indicators.get("macd"),          0.0),
                _safe_float(indicators.get("volume_ratio"),  1.0),
                _safe_float(indicators.get("bb_pct"),        0.5),
                self._ema_score(indicators),
                _safe_float(condition_adx,                  25.0),
                float(dt.hour),       # Hour of entry (0-23)
                float(dt.weekday()),  # Day of week (0=Mon, 4=Fri)
            ]
            return np.array(features, dtype=float)
        except Exception as e:
            logger.debug(f"Feature vector build error: {e}")
            return None

    def _ema_score(self, indicators: Dict) -> float:
        fast  = indicators.get("ema_fast",  0)
        slow  = indicators.get("ema_slow",  0)
        trend = indicators.get("ema_trend", 0)
        if fast > slow > trend:   return  2.0
        if fast > slow:           return  1.0
        if fast < slow < trend:   return -2.0
        if fast < slow:           return -1.0
        return 0.0

    def _prepare_training_data(self):
        """Build training dataset from closed trade history."""
        trades = self._db.get_all_closed_trades(limit=2000)
        trades = [
            t for t in trades
            if t.get("indicators_json") and t.get("pnl") is not None
        ]

        if len(trades) < MIN_TRADES_TO_ACTIVATE:
            return None, None

        X_rows, y_rows = [], []
        for trade in trades:
            try:
                indicators = json.loads(trade["indicators_json"])
                fv = self._build_feature_vector(
                    indicators,
                    entry_time    = trade.get("entry_time"),
                    condition_adx = indicators.get("adx", 25.0)
                )
                if fv is None:
                    continue
                label = 1 if trade["pnl"] > 0 else 0
                X_rows.append(fv)
                y_rows.append(label)
            except Exception:
                continue

        if len(X_rows) < MIN_TRADES_TO_ACTIVATE:
            return None, None

        return np.array(X_rows), np.array(y_rows)

    def retrain(self) -> bool:
        """
        Train (or retrain) the Random Forest on all closed trade history.
        Called by the daily scheduler at 6 PM ET.
        Returns True if training succeeded.
        """
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.preprocessing import StandardScaler
            from sklearn.model_selection import cross_val_score

            X, y = self._prepare_training_data()
            if X is None:
                all_trades   = self._db.get_all_closed_trades(500)
                trade_count  = len(all_trades)
                remaining    = MIN_TRADES_TO_ACTIVATE - trade_count
                logger.info(
                    f"ML training: need {remaining} more closed trades to activate."
                )
                return False

            self.scaler = StandardScaler()
            X_scaled    = self.scaler.fit_transform(X)

            self.model = RandomForestClassifier(
                n_estimators   = 100,
                max_depth      = 6,
                min_samples_leaf = 5,
                random_state   = 42,
                class_weight   = "balanced"
            )
            self.model.fit(X_scaled, y)

            scores   = cross_val_score(
                self.model, X_scaled, y, cv=min(5, len(X) // 10)
            )
            accuracy = scores.mean()
            win_rate = y.mean() * 100

            self.is_trained = True
            self._save_model()

            logger.info(
                f"ML model trained on {len(X)} trades | "
                f"CV accuracy: {accuracy*100:.1f}% | "
                f"Historical win rate: {win_rate:.1f}%"
            )

            feature_names = [
                "RSI", "MACD_hist", "MACD", "Volume", "BB%",
                "EMA_align", "ADX", "Hour", "Weekday"
            ]
            importances = sorted(
                zip(feature_names, self.model.feature_importances_),
                key=lambda x: x[1], reverse=True
            )
            logger.info(
                "Feature importances: " +
                ", ".join(f"{n}={v:.3f}" for n, v in importances[:5])
            )
            return True

        except ImportError:
            logger.warning(
                "scikit-learn not installed. Run: pip install scikit-learn"
            )
            return False
        except Exception as e:
            logger.error(f"ML training failed: {e}")
            return False

    # Keep old name as alias
    def train(self) -> bool:
        return self.retrain()

    def score(self, indicators: Dict, base_score: float,
              entry_time: str = None,
              condition_adx: float = 25.0) -> float:
        """
        Return an enhanced signal score blending rule-based and ML scores.

        Early stage (<50 trades):    100% rule-based score
        Mid stage   (50-200 trades): 70% rule-based + 30% ML
        Mature      (200+ trades):   40% rule-based + 60% ML
        """
        all_trades        = self._db.get_all_closed_trades(500)
        self.trade_count  = len(all_trades)

        if not self.is_trained or self.trade_count < MIN_TRADES_TO_ACTIVATE:
            return base_score

        try:
            fv = self._build_feature_vector(
                indicators, entry_time, condition_adx
            )
            if fv is None:
                return base_score

            fv_scaled = self.scaler.transform(fv.reshape(1, -1))
            ml_proba  = float(self.model.predict_proba(fv_scaled)[0][1])

            if self.trade_count >= MIN_TRADES_FULL_CONTROL:
                ml_weight   = 0.60
                rule_weight = 0.40
            else:
                ratio       = (
                    (self.trade_count - MIN_TRADES_TO_ACTIVATE) /
                    (MIN_TRADES_FULL_CONTROL - MIN_TRADES_TO_ACTIVATE)
                )
                ml_weight   = 0.30 + ratio * 0.30
                rule_weight = 1.0 - ml_weight

            blended = (base_score * rule_weight) + (ml_proba * ml_weight)
            logger.debug(
                f"ML scoring: rule={base_score:.3f} ml={ml_proba:.3f} "
                f"blended={blended:.3f} "
                f"(rule={rule_weight:.0%} ml={ml_weight:.0%})"
            )
            return round(blended, 3)

        except Exception as e:
            logger.debug(f"ML scoring error: {e}")
            return base_score

    def get_status(self) -> Dict:
        """Return ML system status for dashboard display."""
        trade_count = len(self._db.get_all_closed_trades(500))
        if not self.is_trained or trade_count < MIN_TRADES_TO_ACTIVATE:
            stage = "warming_up"
            pct   = min(trade_count / MIN_TRADES_TO_ACTIVATE * 100, 100)
        elif trade_count < MIN_TRADES_FULL_CONTROL:
            stage = "learning"
            pct   = min(trade_count / MIN_TRADES_FULL_CONTROL * 100, 100)
        else:
            stage = "active"
            pct   = 100.0

        messages = {
            "warming_up": (
                f"Collecting data: {trade_count}/{MIN_TRADES_TO_ACTIVATE} "
                "trades. Rule-based scoring active."
            ),
            "learning": (
                f"ML active at 30% weight. "
                f"{MIN_TRADES_FULL_CONTROL - trade_count} trades to full ML."
            ),
            "active": (
                f"ML fully active (60% weight) trained on {trade_count} trades."
            ),
        }

        return {
            "stage":            stage,
            "trade_count":      trade_count,
            "progress_pct":     round(pct, 1),
            "is_trained":       self.is_trained,
            "min_to_activate":  MIN_TRADES_TO_ACTIVATE,
            "min_full":         MIN_TRADES_FULL_CONTROL,
            "message":          messages.get(stage, "")
        }


# Class alias so bot_engine.py can do: from intelligence.ml_scorer import MLScorer
MLScorer = MLSignalScorer

# Singleton
ml_scorer = MLSignalScorer()

import logging

logger = logging.getLogger(__name__)


class BreakoutDetector:
    """Detects breakouts from candle data.
    
    Works with any candle resolution (1h, 4h, 1d, etc.).
    lookback_candles controls how many candles to use for resistance/support.
    
    Examples with candle_resolution + lookback_candles:
      1h  + 24 candles = 1-day breakout
      4h  +  6 candles = 1-day breakout
      4h  + 42 candles = 1-week breakout
      1d  +  7 candles = 1-week breakout
    """

    def detect_breakout(self, candles, lookback_candles):
        """
        Detect breakout from candles.
        
        - Resistance = highest high of last N candles
        - Support = lowest low of last N candles
        - LONG: latest closed candle close > resistance
        - SHORT: latest closed candle close < support
        
        Returns signal dict or None.
        """
        if len(candles) < lookback_candles + 1:
            logger.debug(
                "Not enough candles for breakout: have %d, need %d",
                len(candles), lookback_candles + 1,
            )
            return None

        # The latest closed candle is the signal candle
        signal_candle = candles[-1]

        # Lookback window excludes the signal candle
        lookback = candles[-(lookback_candles + 1):-1]

        resistance = max(c["high"] for c in lookback)
        support = min(c["low"] for c in lookback)
        close = signal_candle["close"]

        logger.debug(
            "Breakout levels (%d candles): resistance=%.2f, support=%.2f, close=%.2f",
            lookback_candles, resistance, support, close,
        )

        if close > resistance:
            logger.info(
                "BREAKOUT LONG detected (%d candles): close=%.2f > resistance=%.2f",
                lookback_candles, close, resistance,
            )
            return {
                "signal": "LONG",
                "level": resistance,
                "type": f"{lookback_candles}-candle",
                "close": close,
                "candle_time": signal_candle["time"],
            }

        if close < support:
            logger.info(
                "BREAKOUT SHORT detected (%d candles): close=%.2f < support=%.2f",
                lookback_candles, close, support,
            )
            return {
                "signal": "SHORT",
                "level": support,
                "type": f"{lookback_candles}-candle",
                "close": close,
                "candle_time": signal_candle["time"],
            }

        return None

    def get_levels(self, candles, lookback_candles):
        """Return current resistance/support levels without triggering a breakout."""
        if len(candles) < lookback_candles + 1:
            return None
        lookback = candles[-(lookback_candles + 1):-1]
        return {
            "resistance": max(c["high"] for c in lookback),
            "support": min(c["low"] for c in lookback),
            "close": candles[-1]["close"],
        }

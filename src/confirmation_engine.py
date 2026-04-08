import time
import logging

logger = logging.getLogger(__name__)


class ConfirmationEngine:
    """
    Post-breakout confirmation:
    - Time-based: price must remain beyond breakout level for X minutes
    - RSI-based: optional RSI filter
    - Stale expiry: pending breakouts expire after max_pending_minutes
    """

    MAX_PENDING_MINUTES = 30  # expire stale breakouts after 30 minutes

    def __init__(self):
        # Pending breakout signals: {symbol: {signal, level, type, registered_at}}
        self._pending = {}

    def register_breakout(self, symbol, signal_type, breakout_level, breakout_kind, candle_time):
        """Register a new breakout signal for confirmation tracking."""
        # Only register if there's no existing pending signal, or if it's a new candle
        existing = self._pending.get(symbol)
        if existing and existing["candle_time"] == candle_time:
            return  # Already registered for this candle

        self._pending[symbol] = {
            "signal": signal_type,
            "level": breakout_level,
            "type": breakout_kind,
            "registered_at": time.time(),
            "candle_time": candle_time,
        }
        logger.info(
            "[%s] Breakout registered: %s %s at level=%.2f",
            symbol, breakout_kind, signal_type, breakout_level,
        )

    def is_confirmed(self, symbol, current_price, minutes_after):
        """
        Check if the pending breakout signal is confirmed.
        - Must have waited at least `minutes_after` minutes
        - LONG: current price must remain above breakout level
        - SHORT: current price must remain below breakout level
        """
        pending = self._pending.get(symbol)
        if not pending:
            return False

        elapsed_minutes = (time.time() - pending["registered_at"]) / 60.0

        # Expire stale breakout signals
        if elapsed_minutes > self.MAX_PENDING_MINUTES:
            logger.info(
                "[%s] Breakout EXPIRED: %s after %.1f min (max=%d min)",
                symbol, pending["signal"], elapsed_minutes, self.MAX_PENDING_MINUTES,
            )
            self.clear(symbol)
            return False

        if elapsed_minutes < minutes_after:
            return False

        signal = pending["signal"]
        level = pending["level"]

        if signal == "LONG" and current_price > level:
            logger.info(
                "[%s] CONFIRMED LONG: price=%.2f > level=%.2f after %.1f min",
                symbol, current_price, level, elapsed_minutes,
            )
            return True

        if signal == "SHORT" and current_price < level:
            logger.info(
                "[%s] CONFIRMED SHORT: price=%.2f < level=%.2f after %.1f min",
                symbol, current_price, level, elapsed_minutes,
            )
            return True

        # Price reverted — breakout failed
        logger.info(
            "[%s] Breakout FAILED: %s price=%.2f vs level=%.2f after %.1f min",
            symbol, signal, current_price, level, elapsed_minutes,
        )
        self.clear(symbol)
        return False

    def get_pending(self, symbol):
        """Get the pending breakout signal for a symbol."""
        return self._pending.get(symbol)

    def clear(self, symbol):
        """Clear pending breakout signal after trade execution or failure."""
        self._pending.pop(symbol, None)

    @staticmethod
    def check_rsi_confirmation(rsi_value, signal_type, rsi_config):
        """
        RSI confirmation check.
        LONG: RSI must be below overbought threshold
        SHORT: RSI must be above oversold threshold
        """
        if not rsi_config.get("enabled", True):
            return True  # RSI disabled, auto-confirm

        if rsi_value is None:
            logger.warning("RSI value unavailable, skipping RSI confirmation")
            return True  # Can't confirm without data, allow trade

        overbought = rsi_config.get("overbought", 70)
        oversold = rsi_config.get("oversold", 30)

        if signal_type == "LONG":
            confirmed = rsi_value < overbought
            if not confirmed:
                logger.info("RSI rejection for LONG: RSI=%.2f >= overbought=%d", rsi_value, overbought)
            return confirmed

        if signal_type == "SHORT":
            confirmed = rsi_value > oversold
            if not confirmed:
                logger.info("RSI rejection for SHORT: RSI=%.2f <= oversold=%d", rsi_value, oversold)
            return confirmed

        return False

import logging

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """Stateless technical indicator calculations."""

    @staticmethod
    def calculate_rsi(closes, period=14):
        """
        Calculate RSI using Wilder's smoothing method.
        Returns the latest RSI value, or None if insufficient data.
        """
        if len(closes) < period + 1:
            logger.warning("Not enough data for RSI: have %d, need %d", len(closes), period + 1)
            return None

        # Calculate price changes
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

        # Initial average gain/loss over first `period` deltas
        gains = [d if d > 0 else 0.0 for d in deltas[:period]]
        losses = [-d if d < 0 else 0.0 for d in deltas[:period]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        # Wilder's smoothing for subsequent periods
        for i in range(period, len(deltas)):
            d = deltas[i]
            gain = d if d > 0 else 0.0
            loss = -d if d < 0 else 0.0

            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return round(rsi, 2)

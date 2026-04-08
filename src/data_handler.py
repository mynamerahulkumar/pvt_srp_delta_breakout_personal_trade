import time
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# Map resolution string to seconds per candle
RESOLUTION_SECONDS = {
    "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "6h": 21600,
    "1d": 86400, "1w": 604800,
}


class DataHandler:
    """Manages rolling candle windows per symbol using live Delta Exchange API."""

    def __init__(self, api_client, config):
        self.api = api_client
        self.resolution = config["breakout"].get("candle_resolution", "1h")
        self.lookback_candles = config["breakout"]["lookback_candles"]
        self.candle_seconds = RESOLUTION_SECONDS.get(self.resolution, 3600)

        # Per-symbol candle storage
        self._candles = {}   # symbol -> list of candle dicts

        # Track last refresh timestamps to avoid excessive API calls
        self._last_refresh = {}  # symbol -> epoch
        self._refresh_interval = 30  # seconds

    def initialize(self, symbols):
        """Fetch initial candle history for all symbols."""
        for symbol in symbols:
            logger.info("[%s] Fetching initial %s candle history...", symbol, self.resolution)
            self._refresh_candles(symbol, initial=True)
            logger.info(
                "[%s] Loaded %d candles (%s, lookback=%d)",
                symbol, len(self._candles.get(symbol, [])),
                self.resolution, self.lookback_candles,
            )

    def refresh(self, symbol):
        """Fetch latest candles with smart refresh interval to reduce API calls."""
        now = time.time()
        last = self._last_refresh.get(symbol, 0)
        if now - last >= self._refresh_interval:
            self._refresh_candles(symbol)
            self._last_refresh[symbol] = now

    def _refresh_candles(self, symbol, initial=False):
        now = int(time.time())
        # Fetch extra candles to ensure we have enough data
        extra = self.lookback_candles + 2 if initial else 3
        start = now - (extra * self.candle_seconds)

        try:
            candles = self.api.get_ohlc_candles(symbol, resolution=self.resolution, start=start, end=now)
            if candles:
                parsed = self._parse_candles(candles)
                # Only keep closed candles (exclude the current forming candle)
                closed = self._filter_closed_candles(parsed, self.candle_seconds)
                if closed:
                    if initial:
                        self._candles[symbol] = closed
                    else:
                        self._merge_candles(symbol, self._candles, closed)
                    # Trim to lookback window
                    max_candles = self.lookback_candles + 5
                    self._candles[symbol] = self._candles[symbol][-max_candles:]
        except Exception as e:
            logger.error("[%s] Failed to refresh %s candles: %s", symbol, self.resolution, e)

    def _parse_candles(self, raw_candles):
        """Normalize candle data into standard dict format."""
        parsed = []
        for c in raw_candles:
            # Handle both list format [time,o,h,l,c,v] and dict format
            if isinstance(c, (list, tuple)):
                parsed.append({
                    "time": int(c[0]),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]) if len(c) > 5 else 0,
                })
            elif isinstance(c, dict):
                parsed.append({
                    "time": int(c.get("time", c.get("t", 0))),
                    "open": float(c.get("open", c.get("o", 0))),
                    "high": float(c.get("high", c.get("h", 0))),
                    "low": float(c.get("low", c.get("l", 0))),
                    "close": float(c.get("close", c.get("c", 0))),
                    "volume": float(c.get("volume", c.get("v", 0))),
                })

        # Sort by time ascending
        parsed.sort(key=lambda x: x["time"])
        return parsed

    def _filter_closed_candles(self, candles, interval_seconds):
        """Remove the current (still-forming) candle."""
        now = int(time.time())
        # A candle is closed if its time + interval <= now
        return [c for c in candles if c["time"] + interval_seconds <= now]

    def _merge_candles(self, symbol, storage, new_candles):
        """Merge new candles into existing storage, avoiding duplicates."""
        existing = storage.get(symbol, [])
        existing_times = {c["time"] for c in existing}
        for c in new_candles:
            if c["time"] not in existing_times:
                existing.append(c)
        existing.sort(key=lambda x: x["time"])
        storage[symbol] = existing

    def get_candles(self, symbol):
        return self._candles.get(symbol, [])

    # Keep backward-compatible alias
    get_hourly_candles = get_candles

    def get_close_prices(self, symbol):
        """Return list of close prices for indicator calculation."""
        candles = self.get_candles(symbol)
        return [c["close"] for c in candles]

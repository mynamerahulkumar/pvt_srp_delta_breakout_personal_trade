import time
import signal
import logging

from src.delta_api_client import DeltaAPIClient, FatalAPIError
from src.data_handler import DataHandler
from src.indicator_calculator import IndicatorCalculator
from src.breakout_detector import BreakoutDetector
from src.confirmation_engine import ConfirmationEngine
from src.execution_engine import ExecutionEngine
from src.trade_manager import TradeManager

logger = logging.getLogger(__name__)


class StrategyEngine:
    """Main orchestrator: runs the breakout strategy loop for all symbols."""

    def __init__(self, config):
        self.config = config
        self.symbols = config["symbols"]
        self.poll_interval = config.get("polling_interval_seconds", 10)
        self.candle_resolution = config["breakout"].get("candle_resolution", "1h")
        self.lookback_candles = config["breakout"]["lookback_candles"]
        self.confirmation_minutes = config["confirmation"]["minutes_after_breakout"]
        self.rsi_config = config.get("rsi", {})
        self.rsi_period = self.rsi_config.get("period", 14)
        self._running = False

        # Initialize components
        logger.info("Initializing Delta API client...")
        self.api = DeltaAPIClient(config)

        logger.info("Initializing data handler...")
        self.data_handler = DataHandler(self.api, config)

        self.indicator = IndicatorCalculator()
        self.breakout_detector = BreakoutDetector()
        self.confirmation = ConfirmationEngine()
        self.execution = ExecutionEngine(self.api, config)
        self.trade_manager = TradeManager(config)

        # Track last processed candle time per symbol to avoid redundant detection
        self._last_processed_candle = {}  # symbol -> candle_time

        # Fatal error tracking: stop bot after N consecutive API failures
        self._consecutive_api_failures = 0
        self._max_fatal_retries = config.get("max_fatal_retries", 20)

    def run(self):
        """Main strategy loop."""
        self._running = True

        # Graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        logger.info("═" * 60)
        logger.info("│  BREAKOUT TRADING BOT STARTED")
        logger.info("═" * 60)
        logger.info("│  Symbols        : %s", self.symbols)
        logger.info("│  Poll interval  : %ds", self.poll_interval)
        logger.info("│  Candle res.    : %s", self.candle_resolution)
        logger.info("│  Lookback       : %d candles", self.lookback_candles)
        logger.info("│  RSI enabled    : %s (period=%d)", self.rsi_config.get("enabled"), self.rsi_period)
        logger.info("│  Stop-loss      : %.1f%%", self.config["risk_management"]["stop_loss_percentage"])
        logger.info("│  Take-profit    : %.1f%%", self.config["risk_management"]["take_profit_percentage"])
        logger.info("│  Trailing stop  : %.1f%%", self.config["risk_management"]["trailing_stop_percentage"])
        logger.info("═" * 60)

        # Load initial candle history
        self.data_handler.initialize(self.symbols)

        logger.info("Entering main trading loop...")

        while self._running:
            for symbol in self.symbols:
                try:
                    self._process_symbol(symbol)
                    self._consecutive_api_failures = 0  # reset on success
                except FatalAPIError as e:
                    self._consecutive_api_failures += 1
                    logger.error("[%s] Fatal API error (%d/%d): %s",
                                 symbol, self._consecutive_api_failures,
                                 self._max_fatal_retries, e)
                    if self._consecutive_api_failures >= self._max_fatal_retries:
                        logger.critical(
                            "Reached %d consecutive API failures. Stopping bot.",
                            self._max_fatal_retries,
                        )
                        self._running = False
                        break
                except Exception as e:
                    self._consecutive_api_failures += 1
                    logger.error("[%s] Error in strategy loop (%d/%d): %s",
                                 symbol, self._consecutive_api_failures,
                                 self._max_fatal_retries, e, exc_info=True)
                    if self._consecutive_api_failures >= self._max_fatal_retries:
                        logger.critical(
                            "Reached %d consecutive API failures. Stopping bot.",
                            self._max_fatal_retries,
                        )
                        self._running = False
                        break

            if self._running:
                time.sleep(self.poll_interval)

        logger.info("Trading bot stopped.")

    def _process_symbol(self, symbol):
        """Process one symbol: refresh data, check exits, detect entries."""

        # 1. Refresh candle data
        self.data_handler.refresh(symbol)

        # 2. Get current price
        current_price = self._get_current_price(symbol)
        if current_price is None:
            return

        # 3. If there's an active trade, manage it (trailing stop + exit check)
        if self.trade_manager.has_active_trade(symbol):
            self._manage_active_trade(symbol, current_price)
            return

        # 4. Check for pending breakout confirmation
        pending = self.confirmation.get_pending(symbol)
        if pending:
            self._check_confirmation(symbol, current_price)
            return

        # 5. Detect new breakouts
        self._detect_breakout(symbol)

    def _get_current_price(self, symbol):
        """Fetch current mark price for a symbol."""
        try:
            ticker = self.api.get_ticker(symbol)
            price = float(ticker.get("mark_price", ticker.get("close", 0)))
            if price <= 0:
                logger.warning("[%s] Invalid price from ticker: %s", symbol, ticker)
                return None
            return price
        except Exception as e:
            logger.error("[%s] Failed to get current price: %s", symbol, e)
            return None

    def _manage_active_trade(self, symbol, current_price):
        """Update trailing stop and check for SL/TP exits."""
        trade = self.trade_manager.get_active_trade(symbol)

        # Update trailing stop
        self.trade_manager.update_trailing_stop(symbol, current_price)

        # Check exit conditions
        exit_signal = self.trade_manager.check_exit(symbol, current_price)
        if exit_signal:
            # Close the position
            result = self.execution.close_position(symbol, trade.side, trade.size)
            if result:
                if trade.side == "buy":
                    pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100
                else:
                    pnl_pct = ((trade.entry_price - current_price) / trade.entry_price) * 100

                pnl_tag = "PROFIT" if pnl_pct >= 0 else "LOSS"
                logger.info("─" * 50)
                logger.info("│  Position closed  [%s]", symbol)
                logger.info("─" * 50)
                logger.info("│  Reason   : %s", exit_signal)
                logger.info("│  Side     : %s", trade.side.upper())
                logger.info("│  Entry    : %.2f", trade.entry_price)
                logger.info("│  Exit     : %.2f", current_price)
                logger.info("│  PnL      : %+.2f%%  (%s)", pnl_pct, pnl_tag)
                logger.info("─" * 50)

            self.trade_manager.close_trade(symbol, reason=exit_signal)
            self.confirmation.clear(symbol)

    def _detect_breakout(self, symbol):
        """Detect breakout from candles. Only checks on new candles."""
        candles = self.data_handler.get_candles(symbol)

        # Skip if no new closed candle since last check
        if candles:
            latest_time = candles[-1]["time"]
            if latest_time <= self._last_processed_candle.get(symbol, 0):
                return
            self._last_processed_candle[symbol] = latest_time

        # Always show current breakout levels + RSI
        levels = self.breakout_detector.get_levels(candles, self.lookback_candles)
        if levels:
            mark = None
            try:
                ticker = self.api.get_ticker(symbol)
                mark = float(ticker.get("mark_price", 0)) or None
            except Exception:
                pass

            # Calculate RSI if enabled
            rsi_str = ""
            if self.rsi_config.get("enabled"):
                closes = self.data_handler.get_close_prices(symbol)
                rsi = self.indicator.calculate_rsi(closes, self.rsi_period)
                if rsi is not None:
                    ob = self.rsi_config.get("overbought", 70)
                    os_ = self.rsi_config.get("oversold", 30)
                    if rsi >= ob:
                        rsi_tag = "OVERBOUGHT"
                    elif rsi <= os_:
                        rsi_tag = "OVERSOLD"
                    else:
                        rsi_tag = "NEUTRAL"
                    rsi_str = f" │ RSI({self.rsi_period}): {rsi:.1f} {rsi_tag}"

            logger.info(
                "[%s] Levels (%s x %d) │ BUY above: %.2f │ SELL below: %.2f │ Last close: %.2f%s%s",
                symbol, self.candle_resolution, self.lookback_candles,
                levels["resistance"], levels["support"], levels["close"],
                f" │ Mark: {mark:.2f}" if mark else "",
                rsi_str,
            )

        breakout = self.breakout_detector.detect_breakout(candles, self.lookback_candles)

        if breakout:
            logger.info("─" * 50)
            logger.info("│  BREAKOUT DETECTED  [%s]", symbol)
            logger.info("─" * 50)
            logger.info("│  Signal     : %s", breakout["signal"])
            logger.info("│  Period     : %s", breakout["type"])
            logger.info("│  Level      : %.2f", breakout["level"])
            logger.info("│  Close      : %.2f", breakout["close"])
            ticker = self.api.get_ticker(symbol)
            mark = float(ticker.get("mark_price", 0))
            if mark > 0:
                logger.info("│  Mark price : %.2f", mark)
            logger.info("│  Waiting %d min for confirmation...", self.confirmation_minutes)
            logger.info("─" * 50)
            self.confirmation.register_breakout(
                symbol=symbol,
                signal_type=breakout["signal"],
                breakout_level=breakout["level"],
                breakout_kind=breakout["type"],
                candle_time=breakout["candle_time"],
            )

    def _check_confirmation(self, symbol, current_price):
        """Check if a pending breakout is confirmed and execute trade."""
        if not self.confirmation.is_confirmed(symbol, current_price, self.confirmation_minutes):
            return

        pending = self.confirmation.get_pending(symbol)
        if not pending:
            return

        signal_type = pending["signal"]
        breakout_level = pending["level"]

        # RSI confirmation
        closes = self.data_handler.get_close_prices(symbol)
        rsi = self.indicator.calculate_rsi(closes, self.rsi_period)

        if rsi is not None:
            rsi_status = "OK" if self.confirmation.check_rsi_confirmation(rsi, signal_type, self.rsi_config) else "FAILED"
            logger.info("│  [%s] RSI = %.2f  (%s)", symbol, rsi, rsi_status)

        if not self.confirmation.check_rsi_confirmation(rsi, signal_type, self.rsi_config):
            logger.warning("[%s] RSI confirmation FAILED — breakout cancelled", symbol)
            self.confirmation.clear(symbol)
            return

        # Execute trade
        side = "buy" if signal_type == "LONG" else "sell"
        fill = self.execution.execute_trade(symbol, side, breakout_level)

        if fill:
            fill_price = fill["fill_price"]
            size = fill["size"] or self.config.get("position_size", 1)

            self.trade_manager.open_trade(
                symbol=symbol,
                entry_price=fill_price,
                side=side,
                size=size,
                order_id=fill.get("order_id"),
            )

            sl_pct = self.config["risk_management"]["stop_loss_percentage"]
            tp_pct = self.config["risk_management"]["take_profit_percentage"]
            if side == "buy":
                sl_price = fill_price * (1 - sl_pct / 100)
                tp_price = fill_price * (1 + tp_pct / 100)
            else:
                sl_price = fill_price * (1 + sl_pct / 100)
                tp_price = fill_price * (1 - tp_pct / 100)

            logger.info("─" * 50)
            logger.info("│  Trade opened  [%s]", symbol)
            logger.info("─" * 50)
            logger.info("│  Side       : %s", side.upper())
            logger.info("│  Entry      : %.2f", fill_price)
            logger.info("│  Size       : %s", size)
            logger.info("│  Stop-loss  : %.2f (%.1f%%)", sl_price, sl_pct)
            logger.info("│  Take-profit: %.2f (%.1f%%)", tp_price, tp_pct)
            logger.info("│  Breakout   : %.2f", breakout_level)
            logger.info("─" * 50)

        # Clear the pending breakout whether trade succeeded or not
        self.confirmation.clear(symbol)

    def _shutdown(self, signum, frame):
        """Graceful shutdown handler."""
        logger.info("Shutdown signal received (sig=%s), stopping...", signum)
        self._running = False

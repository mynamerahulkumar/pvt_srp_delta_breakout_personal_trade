import time
import logging

logger = logging.getLogger(__name__)


class TradeState:
    """Represents an active trade for a symbol."""

    def __init__(self, symbol, side, entry_price, size, sl_price, tp_price, trailing_pct, order_id=None):
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.size = size
        self.sl_price = sl_price
        self.tp_price = tp_price
        self.trailing_pct = trailing_pct / 100.0
        self.order_id = order_id
        self.entry_time = time.time()
        self.highest_price = entry_price  # for LONG trailing
        self.lowest_price = entry_price   # for SHORT trailing

    def __repr__(self):
        return (
            f"TradeState({self.symbol} {self.side} entry={self.entry_price:.2f} "
            f"SL={self.sl_price:.2f} TP={self.tp_price:.2f})"
        )


class TradeManager:
    """
    Manages active trades with SL/TP/trailing stop logic.
    Only one active trade per symbol to prevent overtrading.
    """

    def __init__(self, config):
        risk = config.get("risk_management", {})
        self.sl_pct = risk.get("stop_loss_percentage", 0.8) / 100.0
        self.tp_pct = risk.get("take_profit_percentage", 1.5) / 100.0
        self.trailing_pct = risk.get("trailing_stop_percentage", 0.4)

        # Active trades: {symbol: TradeState}
        self._trades = {}

    def has_active_trade(self, symbol):
        return symbol in self._trades

    def get_active_trade(self, symbol):
        return self._trades.get(symbol)

    def open_trade(self, symbol, entry_price, side, size, order_id=None):
        """Open a new trade and calculate SL/TP levels."""
        if self.has_active_trade(symbol):
            logger.warning("[%s] Already has an active trade, skipping", symbol)
            return None

        if side == "buy":
            sl_price = entry_price * (1 - self.sl_pct)
            tp_price = entry_price * (1 + self.tp_pct)
        else:
            sl_price = entry_price * (1 + self.sl_pct)
            tp_price = entry_price * (1 - self.tp_pct)

        trade = TradeState(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            size=size,
            sl_price=sl_price,
            tp_price=tp_price,
            trailing_pct=self.trailing_pct,
            order_id=order_id,
        )
        self._trades[symbol] = trade

        logger.info(
            "[%s] TRADE OPENED: %s entry=%.2f SL=%.2f TP=%.2f size=%d",
            symbol, side.upper(), entry_price, sl_price, tp_price, size,
        )
        return trade

    def update_trailing_stop(self, symbol, current_price):
        """Dynamically move SL using trailing stop logic."""
        trade = self._trades.get(symbol)
        if not trade:
            return

        if trade.side == "buy":
            # Track highest price for LONG
            if current_price > trade.highest_price:
                trade.highest_price = current_price
                new_sl = current_price * (1 - trade.trailing_pct)
                if new_sl > trade.sl_price:
                    old_sl = trade.sl_price
                    trade.sl_price = new_sl
                    logger.info(
                        "[%s] Trailing SL updated: %.2f -> %.2f (price=%.2f)",
                        symbol, old_sl, new_sl, current_price,
                    )
        else:
            # Track lowest price for SHORT
            if current_price < trade.lowest_price:
                trade.lowest_price = current_price
                new_sl = current_price * (1 + trade.trailing_pct)
                if new_sl < trade.sl_price:
                    old_sl = trade.sl_price
                    trade.sl_price = new_sl
                    logger.info(
                        "[%s] Trailing SL updated: %.2f -> %.2f (price=%.2f)",
                        symbol, old_sl, new_sl, current_price,
                    )

    def check_exit(self, symbol, current_price):
        """
        Check if SL or TP has been hit.
        Returns: "sl_hit", "tp_hit", or None
        """
        trade = self._trades.get(symbol)
        if not trade:
            return None

        if trade.side == "buy":
            if current_price <= trade.sl_price:
                logger.info(
                    "[%s] STOP LOSS HIT: price=%.2f <= SL=%.2f (entry=%.2f)",
                    symbol, current_price, trade.sl_price, trade.entry_price,
                )
                return "sl_hit"
            if current_price >= trade.tp_price:
                logger.info(
                    "[%s] TAKE PROFIT HIT: price=%.2f >= TP=%.2f (entry=%.2f)",
                    symbol, current_price, trade.tp_price, trade.entry_price,
                )
                return "tp_hit"
        else:
            if current_price >= trade.sl_price:
                logger.info(
                    "[%s] STOP LOSS HIT: price=%.2f >= SL=%.2f (entry=%.2f)",
                    symbol, current_price, trade.sl_price, trade.entry_price,
                )
                return "sl_hit"
            if current_price <= trade.tp_price:
                logger.info(
                    "[%s] TAKE PROFIT HIT: price=%.2f <= TP=%.2f (entry=%.2f)",
                    symbol, current_price, trade.tp_price, trade.entry_price,
                )
                return "tp_hit"

        return None

    def close_trade(self, symbol, reason="manual"):
        """Remove trade from active tracking."""
        trade = self._trades.pop(symbol, None)
        if trade:
            logger.info(
                "[%s] TRADE CLOSED (%s): %s entry=%.2f",
                symbol, reason, trade.side.upper(), trade.entry_price,
            )
        return trade

    def get_all_active(self):
        """Return all active trades."""
        return dict(self._trades)

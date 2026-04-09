import time
import logging

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Execution engine: places market orders at breakout with SL/TP.
    1. Check spread from order book
    2. Place market order immediately
    """

    def __init__(self, api_client, config):
        self.api = api_client
        exec_cfg = config.get("execution", {})
        self.max_spread_pct = exec_cfg.get("max_spread_percentage", 0.1) / 100.0
        self.position_size = config.get("position_size", 1)

    def execute_trade(self, symbol, side, breakout_price):
        """
        Execute a market order at breakout.
        
        Returns fill info dict or None if trade was skipped.
        """
        logger.info("[%s] Executing %s market order at breakout_price=%.2f", symbol, side, breakout_price)

        # Step 1: Spread check
        if not self._check_spread(symbol):
            return None

        # Step 2: Market order
        return self._place_market(symbol, side, self.position_size)

    def _check_spread(self, symbol):
        """Check if the bid-ask spread is within acceptable range."""
        try:
            book = self.api.get_l2_orderbook(symbol)
            buy_orders = book.get("buy", [])
            sell_orders = book.get("sell", [])

            if not buy_orders or not sell_orders:
                logger.warning("[%s] Order book empty, skipping trade", symbol)
                return False

            best_bid = float(buy_orders[0].get("price", buy_orders[0].get("limit_price", 0)))
            best_ask = float(sell_orders[0].get("price", sell_orders[0].get("limit_price", 0)))

            if best_bid <= 0 or best_ask <= 0:
                logger.warning("[%s] Invalid bid/ask prices", symbol)
                return False

            mid_price = (best_bid + best_ask) / 2.0
            spread = (best_ask - best_bid) / mid_price

            logger.info(
                "[%s] Spread check: bid=%.2f ask=%.2f spread=%.4f%% max=%.4f%%",
                symbol, best_bid, best_ask, spread * 100, self.max_spread_pct * 100,
            )

            if spread > self.max_spread_pct:
                logger.warning("[%s] Spread too high (%.4f%%), skipping trade", symbol, spread * 100)
                return False

            return True

        except Exception as e:
            logger.error("[%s] Spread check failed: %s", symbol, e)
            return False

    def _place_market(self, symbol, side, size):
        """Place a market order as direct execution or fallback."""
        logger.info("[%s] Placing market %s order: size=%d", symbol, side, size)
        try:
            order = self.api.place_market_order(symbol, side, size)
            order_id = order.get("id")
            fill_price = float(order.get("average_fill_price", 0))

            if fill_price == 0:
                # Fetch updated order for fill price
                time.sleep(0.5)
                try:
                    updated = self.api.get_order(order_id)
                    fill_price = float(updated.get("average_fill_price", 0))
                except Exception:
                    pass

            logger.info(
                "[%s] Market order executed: id=%s price=%.2f",
                symbol, order_id, fill_price,
            )
            return {
                "order_id": order_id,
                "fill_price": fill_price,
                "side": side,
                "size": size,
                "symbol": symbol,
                "type": "market",
            }

        except Exception as e:
            logger.error("[%s] Market order FAILED: %s", symbol, e)
            return None

    def close_position(self, symbol, side, size):
        """Close an existing position with a reduce-only market order."""
        close_side = "sell" if side == "buy" else "buy"
        logger.info("[%s] Closing position: %s size=%d", symbol, close_side, size)
        try:
            order = self.api.place_market_order(symbol, close_side, size, reduce_only=True)
            order_id = order.get("id")
            fill_price = float(order.get("average_fill_price", 0))

            if fill_price == 0:
                time.sleep(0.5)
                try:
                    updated = self.api.get_order(order_id)
                    fill_price = float(updated.get("average_fill_price", 0))
                except Exception:
                    pass

            logger.info(
                "[%s] Position closed: id=%s price=%.2f",
                symbol, order_id, fill_price,
            )
            return {
                "order_id": order_id,
                "fill_price": fill_price,
                "side": close_side,
                "size": size,
                "symbol": symbol,
                "type": "market_close",
            }
        except Exception as e:
            logger.error("[%s] Close position FAILED: %s", symbol, e)
            return None

    def place_stop_loss(self, symbol, side, size, sl_price):
        """
        Place a stop-loss order on the exchange for crash protection.
        side: the side of the POSITION (buy/sell). SL order is the opposite side.
        """
        sl_side = "sell" if side == "buy" else "buy"
        logger.info("[%s] Placing exchange SL: %s size=%d stop_price=%.2f", symbol, sl_side, size, sl_price)
        try:
            order = self.api.place_stop_order(
                symbol, sl_side, size, stop_price=sl_price, reduce_only=True,
            )
            order_id = order.get("id")
            logger.info("[%s] Exchange SL placed: id=%s price=%.2f", symbol, order_id, sl_price)
            return order_id
        except Exception as e:
            logger.error("[%s] Exchange SL placement FAILED: %s", symbol, e)
            return None

    def update_stop_loss(self, symbol, old_sl_order_id, side, size, new_sl_price):
        """
        Update exchange SL by cancelling old and placing new.
        Returns new SL order ID, or None if failed.
        """
        if old_sl_order_id:
            try:
                self.api.cancel_order(symbol, old_sl_order_id)
                logger.info("[%s] Cancelled old exchange SL: %s", symbol, old_sl_order_id)
            except Exception as e:
                logger.warning("[%s] Failed to cancel old SL %s: %s", symbol, old_sl_order_id, e)

        return self.place_stop_loss(symbol, side, size, new_sl_price)

    def cancel_stop_loss(self, symbol, sl_order_id):
        """Cancel an exchange-side stop-loss order."""
        if not sl_order_id:
            return
        try:
            self.api.cancel_order(symbol, sl_order_id)
            logger.info("[%s] Exchange SL cancelled: %s", symbol, sl_order_id)
        except Exception as e:
            logger.warning("[%s] Failed to cancel exchange SL %s: %s", symbol, sl_order_id, e)

    def place_take_profit(self, symbol, side, size, tp_price):
        """
        Place a take-profit order on the exchange.
        side: the side of the POSITION (buy/sell). TP order is the opposite side.
        """
        tp_side = "sell" if side == "buy" else "buy"
        logger.info("[%s] Placing exchange TP: %s size=%d stop_price=%.2f", symbol, tp_side, size, tp_price)
        try:
            order = self.api.place_take_profit_order(
                symbol, tp_side, size, stop_price=tp_price, reduce_only=True,
            )
            order_id = order.get("id")
            logger.info("[%s] Exchange TP placed: id=%s price=%.2f", symbol, order_id, tp_price)
            return order_id
        except Exception as e:
            logger.error("[%s] Exchange TP placement FAILED: %s", symbol, e)
            return None

    def cancel_take_profit(self, symbol, tp_order_id):
        """Cancel an exchange-side take-profit order."""
        if not tp_order_id:
            return
        try:
            self.api.cancel_order(symbol, tp_order_id)
            logger.info("[%s] Exchange TP cancelled: %s", symbol, tp_order_id)
        except Exception as e:
            logger.warning("[%s] Failed to cancel exchange TP %s: %s", symbol, tp_order_id, e)

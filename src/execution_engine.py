import time
import logging

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Low-slippage execution engine:
    1. Check spread from order book
    2. Place limit order at breakout_price +/- buffer%
    3. Wait for fill, cancel + market fallback if not filled
    """

    def __init__(self, api_client, config):
        self.api = api_client
        exec_cfg = config.get("execution", {})
        self.use_limit = exec_cfg.get("use_limit_orders", True)
        self.buffer_pct = exec_cfg.get("limit_order_buffer_percentage", 0.03) / 100.0
        self.max_wait = exec_cfg.get("max_wait_seconds_for_limit_fill", 5)
        self.max_spread_pct = exec_cfg.get("max_spread_percentage", 0.1) / 100.0
        self.position_size = config.get("position_size", 1)

    def execute_trade(self, symbol, side, breakout_price):
        """
        Execute a trade with low-slippage logic.
        
        Returns fill info dict or None if trade was skipped.
        """
        logger.info("[%s] Executing %s trade at breakout_price=%.2f", symbol, side, breakout_price)

        # Step 1: Spread check
        if not self._check_spread(symbol):
            return None

        size = self.position_size

        # Step 2: Limit order
        if self.use_limit:
            fill = self._try_limit_order(symbol, side, size, breakout_price)
            if fill:
                return fill
            # Step 3: Fallback to market order
            logger.info("[%s] Limit order not filled, falling back to market order", symbol)

        # Market order (direct or fallback)
        return self._place_market(symbol, side, size)

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

    def _try_limit_order(self, symbol, side, size, breakout_price):
        """Place a limit order and wait for fill."""
        if side == "buy":
            limit_price = breakout_price * (1 + self.buffer_pct)
        else:
            limit_price = breakout_price * (1 - self.buffer_pct)

        logger.info(
            "[%s] Placing limit %s order: size=%d price=%.2f",
            symbol, side, size, limit_price,
        )

        try:
            order = self.api.place_limit_order(symbol, side, size, limit_price)
            order_id = order.get("id")

            if not order_id:
                logger.error("[%s] Limit order returned no ID: %s", symbol, order)
                return None

            # Wait for fill
            fill = self._wait_for_fill(symbol, order_id)

            if fill:
                return fill

            # Not filled — cancel
            logger.info("[%s] Cancelling unfilled limit order %s", symbol, order_id)
            try:
                self.api.cancel_order(symbol, order_id)
            except Exception as e:
                logger.warning("[%s] Cancel failed (may already be filled): %s", symbol, e)
                # Re-check if it got filled during cancel
                return self._check_order_filled(symbol, order_id)

            return None

        except Exception as e:
            logger.error("[%s] Limit order failed: %s", symbol, e)
            return None

    def _wait_for_fill(self, symbol, order_id):
        """Poll order status until filled or timeout."""
        start = time.time()
        poll_interval = 0.5

        while (time.time() - start) < self.max_wait:
            try:
                order = self.api.get_order(order_id)
                state = order.get("state", "")

                if state in ("closed", "filled"):
                    fill_price = float(order.get("average_fill_price", order.get("limit_price", 0)))
                    logger.info(
                        "[%s] Limit order FILLED: id=%s price=%.2f",
                        symbol, order_id, fill_price,
                    )
                    return {
                        "order_id": order_id,
                        "fill_price": fill_price,
                        "side": order.get("side"),
                        "size": order.get("size"),
                        "symbol": symbol,
                        "type": "limit",
                    }

                if state in ("cancelled", "rejected"):
                    logger.warning("[%s] Order %s state=%s", symbol, order_id, state)
                    return None

            except Exception as e:
                logger.warning("[%s] Order status check failed: %s", symbol, e)

            time.sleep(poll_interval)

        return None

    def _check_order_filled(self, symbol, order_id):
        """Check if an order got filled (used after cancel attempt)."""
        try:
            order = self.api.get_order(order_id)
            if order.get("state") in ("closed", "filled"):
                fill_price = float(order.get("average_fill_price", order.get("limit_price", 0)))
                return {
                    "order_id": order_id,
                    "fill_price": fill_price,
                    "side": order.get("side"),
                    "size": order.get("size"),
                    "symbol": symbol,
                    "type": "limit",
                }
        except Exception:
            pass
        return None

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

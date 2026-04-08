import requests
import urllib.parse
import time
import hashlib
import hmac
import json
import logging
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)


class OrderType(Enum):
    MARKET = "market_order"
    LIMIT = "limit_order"


class TimeInForce(Enum):
    FOK = "fok"
    IOC = "ioc"
    GTC = "gtc"


# ---------------------------------------------------------------------------
# Low-level helpers (from reference delta_rest_client)
# ---------------------------------------------------------------------------

def _generate_signature(secret, message):
    message = bytes(message, "utf-8")
    secret = bytes(secret, "utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def _get_timestamp():
    return str(int(time.time()))


def _query_string(query):
    if query is None:
        return ""
    parts = []
    for key, value in query.items():
        parts.append(key + "=" + urllib.parse.quote_plus(str(value)))
    return "?" + "&".join(parts)


def _body_string(body):
    if body is None:
        return ""
    return json.dumps(body, separators=(",", ":"))


def round_by_tick_size(price, tick_size, floor_or_ceil=None):
    remainder = price % tick_size
    if remainder == 0:
        return price
    if floor_or_ceil is None:
        floor_or_ceil = "ceil" if (remainder >= tick_size / 2) else "floor"
    if floor_or_ceil == "ceil":
        price = price - remainder + tick_size
    else:
        price = price - remainder
    decimals = len(format(Decimal(repr(float(tick_size))), "f").split(".")[1])
    return float(round(Decimal(price), decimals))


# ---------------------------------------------------------------------------
# Low-level REST client (mirrors reference DeltaRestClient)
# ---------------------------------------------------------------------------

class _DeltaRestClient:
    def __init__(self, base_url, api_key, api_secret):
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()

    def request(self, method, path, payload=None, query=None, auth=False):
        url = f"{self.base_url}{path}"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "delta-breakout-bot/1.0",
        }

        if auth:
            timestamp = _get_timestamp()
            sig_data = method + timestamp + path + _query_string(query) + _body_string(payload)
            signature = _generate_signature(self.api_secret, sig_data)
            headers.update({
                "api-key": self.api_key,
                "timestamp": timestamp,
                "signature": signature,
            })

        resp = self.session.request(
            method,
            url,
            data=_body_string(payload) if payload else None,
            params=query,
            timeout=(5, 10),
            headers=headers,
        )
        return resp

    def _parse(self, response):
        data = response.json()
        if data.get("success"):
            return data.get("result")
        error = data.get("error", response.text)
        raise requests.exceptions.HTTPError(f"API error: {error}")


# ---------------------------------------------------------------------------
# High-level API client used by the trading bot
# ---------------------------------------------------------------------------

class DeltaAPIClient:
    """High-level Delta Exchange API client with symbol resolution and retry."""

    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds, doubles each retry

    def __init__(self, config):
        self.base_url = config["delta_base_url"]
        self._client = _DeltaRestClient(
            base_url=self.base_url,
            api_key=config["delta_api_key"],
            api_secret=config["delta_api_secret"],
        )
        self._symbol_map = {}  # symbol -> product info dict
        self._product_cache = {}  # product_id -> product info
        self._resolve_symbols(config.get("symbols", []))

    # ---- Symbol resolution ------------------------------------------------

    def _resolve_symbols(self, symbols):
        logger.info("Resolving product IDs for symbols: %s", symbols)
        resp = self._client.request("GET", "/v2/products")
        products = self._client._parse(resp)

        for product in products:
            sym = product.get("symbol", "")
            if sym in symbols:
                self._symbol_map[sym] = product
                self._product_cache[product["id"]] = product
                logger.info(
                    "Resolved %s -> product_id=%s tick_size=%s",
                    sym, product["id"], product.get("tick_size"),
                )

        missing = set(symbols) - set(self._symbol_map.keys())
        if missing:
            raise ValueError(f"Could not resolve symbols: {missing}")

    def get_product_id(self, symbol):
        return self._symbol_map[symbol]["id"]

    def get_tick_size(self, symbol):
        return float(self._symbol_map[symbol].get("tick_size", 0.5))

    # ---- Retry wrapper ----------------------------------------------------

    def _retry(self, fn, *args, **kwargs):
        delay = self.RETRY_DELAY
        last_err = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_err = e
                logger.warning("API call failed (attempt %d/%d): %s", attempt, self.MAX_RETRIES, e)
                if attempt < self.MAX_RETRIES:
                    time.sleep(delay)
                    delay *= 2
        raise last_err

    # ---- Market data ------------------------------------------------------

    def get_ohlc_candles(self, symbol, resolution="1h", start=None, end=None):
        """Fetch OHLC candles. resolution: 1m,5m,15m,30m,1h,2h,4h,6h,1d,7d,30d,1w,2w"""
        query = {"resolution": resolution, "symbol": symbol}
        if start:
            query["start"] = int(start)
        if end:
            query["end"] = int(end)

        def _fetch():
            resp = self._client.request("GET", "/v2/history/candles", query=query)
            return self._client._parse(resp)

        return self._retry(_fetch)

    def get_ticker(self, symbol):
        def _fetch():
            resp = self._client.request("GET", f"/v2/tickers/{symbol}")
            return self._client._parse(resp)

        return self._retry(_fetch)

    def get_l2_orderbook(self, symbol):
        def _fetch():
            resp = self._client.request("GET", f"/v2/l2orderbook/{symbol}")
            return self._client._parse(resp)

        return self._retry(_fetch)

    # ---- Order management -------------------------------------------------

    def place_limit_order(self, symbol, side, size, limit_price, time_in_force=None, reduce_only=False):
        pid = self.get_product_id(symbol)
        tick = self.get_tick_size(symbol)
        limit_price = round_by_tick_size(float(limit_price), tick)

        order = {
            "product_id": pid,
            "size": int(size),
            "side": side,
            "order_type": OrderType.LIMIT.value,
            "limit_price": str(limit_price),
            "post_only": "false",
            "reduce_only": "true" if reduce_only else "false",
        }
        if time_in_force:
            order["time_in_force"] = time_in_force

        def _place():
            resp = self._client.request("POST", "/v2/orders", payload=order, auth=True)
            return self._client._parse(resp)

        return self._retry(_place)

    def place_market_order(self, symbol, side, size, reduce_only=False):
        pid = self.get_product_id(symbol)
        order = {
            "product_id": pid,
            "size": int(size),
            "side": side,
            "order_type": OrderType.MARKET.value,
            "reduce_only": "true" if reduce_only else "false",
        }

        def _place():
            resp = self._client.request("POST", "/v2/orders", payload=order, auth=True)
            return self._client._parse(resp)

        return self._retry(_place)

    def place_stop_order(self, symbol, side, size, stop_price, limit_price=None,
                         trail_amount=None, is_trailing=False, reduce_only=False):
        pid = self.get_product_id(symbol)
        tick = self.get_tick_size(symbol)

        order = {
            "product_id": pid,
            "size": int(size),
            "side": side,
            "order_type": OrderType.LIMIT.value if limit_price else OrderType.MARKET.value,
            "stop_order_type": "stop_loss_order",
            "reduce_only": "true" if reduce_only else "false",
        }

        if limit_price:
            order["limit_price"] = str(round_by_tick_size(float(limit_price), tick))

        if is_trailing and trail_amount:
            order["trail_amount"] = str(trail_amount) if side == "buy" else str(-1 * trail_amount)
        else:
            order["stop_price"] = str(round_by_tick_size(float(stop_price), tick))

        def _place():
            resp = self._client.request("POST", "/v2/orders", payload=order, auth=True)
            return self._client._parse(resp)

        return self._retry(_place)

    def cancel_order(self, symbol, order_id):
        pid = self.get_product_id(symbol)
        payload = {"id": order_id, "product_id": pid}

        def _cancel():
            resp = self._client.request("DELETE", "/v2/orders", payload=payload, auth=True)
            return self._client._parse(resp)

        return self._retry(_cancel)

    def get_open_orders(self, symbol=None):
        query = {}
        if symbol:
            query["product_id"] = self.get_product_id(symbol)

        def _fetch():
            resp = self._client.request("GET", "/v2/orders", query=query if query else None, auth=True)
            return self._client._parse(resp)

        return self._retry(_fetch)

    def get_order(self, order_id):
        """Get order by ID. Tries direct lookup, falls back to live orders list."""
        def _fetch():
            try:
                resp = self._client.request("GET", f"/v2/orders/{order_id}", auth=True)
                return self._client._parse(resp)
            except Exception:
                # Fallback: search in live orders
                resp = self._client.request("GET", "/v2/orders", auth=True)
                orders = self._client._parse(resp)
                for order in (orders if isinstance(orders, list) else []):
                    if order.get("id") == order_id:
                        return order
                # Try order history as last resort
                resp = self._client.request("GET", "/v2/orders/history",
                                            query={"page_size": 5}, auth=True)
                history = resp.json()
                for order in history.get("result", []):
                    if order.get("id") == order_id:
                        return order
                raise

        return self._retry(_fetch)

    # ---- Position management ----------------------------------------------

    def get_position(self, symbol):
        pid = self.get_product_id(symbol)

        def _fetch():
            resp = self._client.request(
                "GET", "/v2/positions/margined",
                query={"product_ids": pid},
                auth=True,
            )
            positions = self._client._parse(resp)
            if positions and len(positions) > 0:
                return positions[0]
            return None

        return self._retry(_fetch)

    # ---- Account ----------------------------------------------------------

    def get_wallet_balances(self):
        def _fetch():
            resp = self._client.request("GET", "/v2/wallet/balances", auth=True)
            return self._client._parse(resp)

        return self._retry(_fetch)

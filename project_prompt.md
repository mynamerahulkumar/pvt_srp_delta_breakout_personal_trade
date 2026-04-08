You are an expert quantitative developer and real-time algorithmic trading engineer.

Create a production-ready, modular algorithmic trading system in Python that operates ONLY on real-time market data using Delta Exchange API.

---

## 🚀 System Overview

Build a live trading bot that supports:

* Real-time trading using Delta Exchange API (no mock data, no backtesting)
* Multi-asset trading (BTCUSD, ETHUSD)
* Hourly and Daily breakout strategies
* RSI confirmation
* Post-breakout time confirmation
* Percentage-based Stop Loss (SL) and Take Profit (TP)
* Low-slippage execution system
* Runs both locally and on AWS Lightsail
* Single entry point: `start.py`

---

## ⚙️ 1. Real-Time Data Handling (CRITICAL)

* Use Delta Exchange API for:

  * OHLCV candles
  * Live price
  * Order book (for spread/slippage check)

* No CSV / no historical simulation

* System must:

  * Continuously fetch latest candles
  * Maintain rolling window of candles (in memory)

---

## ⚙️ 2. Multi-Asset Support

* Symbols:
  ["BTCUSD", "ETHUSD"]

* Each symbol runs independently:

  * Separate breakout levels
  * Separate RSI
  * Separate trades

---

## ⚙️ 3. Configuration (config.json)

Include:

```json id="livecfg1"
{
  "environment": "local",

  "symbols": ["BTCUSD", "ETHUSD"],

  "polling_interval_seconds": 10,

  "breakout": {
    "type": ["hourly", "daily"],
    "lookback_hours": 24,
    "lookback_days": 1
  },

  "confirmation": {
    "minutes_after_breakout": 3
  },

  "rsi": {
    "enabled": true,
    "period": 14,
    "overbought": 70,
    "oversold": 30
  },

  "execution": {
    "use_limit_orders": true,
    "limit_order_buffer_percentage": 0.03,
    "max_wait_seconds_for_limit_fill": 5,
    "max_spread_percentage": 0.1
  },

  "risk_management": {
    "stop_loss_percentage": 0.8,
    "take_profit_percentage": 1.5,
    "trailing_stop_percentage": 0.4
  }
}
```

---

## 📊 4. Breakout Logic (LIVE)

### Hourly Breakout:

* Resistance = highest high of last N hours
* Support = lowest low of last N hours

### Daily Breakout:

* Resistance = previous day high
* Support = previous day low

### Entry Conditions:

* LONG:
  candle close > resistance

* SHORT:
  candle close < support

* Use only CLOSED candles (avoid noise)

---

## ⏱️ 5. Post-Breakout Confirmation

* After breakout:

  * Wait X minutes
* Confirm:

  * LONG → price remains above breakout level
  * SHORT → price remains below breakout level

---

## 📉 6. RSI Confirmation

* Optional
* LONG → RSI < overbought
* SHORT → RSI > oversold

---

## ⚡ 7. Execution Engine (LOW SLIPPAGE - VERY IMPORTANT)

Create ExecutionEngine:

### Step 1: Check Spread

* Fetch bid/ask from order book
* Skip trade if spread too high

### Step 2: Limit Order Entry

* LONG:
  entry = breakout_price * (1 + buffer%)
* SHORT:
  entry = breakout_price * (1 - buffer%)

### Step 3: Fallback

* If not filled in X seconds:
  → cancel order
  → place market order

### Step 4: Avoid Overtrading

* Only one active trade per symbol

---

## 💰 8. Risk Management

### Stop Loss:

* LONG:
  SL = entry * (1 - sl%)
* SHORT:
  SL = entry * (1 + sl%)

### Take Profit:

* LONG:
  TP = entry * (1 + tp%)
* SHORT:
  TP = entry * (1 - tp%)

### Trailing Stop:

* Move SL dynamically

---

## 🧱 9. Architecture

Modules:

* ConfigLoader
* DeltaAPIClient (IMPORTANT)
* DataHandler (real-time candles)
* IndicatorCalculator (RSI)
* BreakoutDetector
* ConfirmationEngine
* ExecutionEngine
* TradeManager
* StrategyEngine

---

## 🔄 10. start.py (ENTRY POINT)

* Load config
* Initialize Delta API client
* Start strategy loop

```python id="entrylive"
if __name__ == "__main__":
    engine = StrategyEngine(config)
    engine.run()
```

---

## ☁️ 11. Local + AWS Lightsail Support

* Same code runs everywhere

* Use ENV variable:
  ENV=local or cloud

* Local:

  * Console logs

* Cloud:

  * File logs only

* Must run efficiently on low RAM (512MB–1GB)

---

## 📜 12. Logging

* Log:

  * Breakout detected
  * Trade entry
  * SL/TP hit
* Include symbol:
  [BTCUSD], [ETHUSD]

---

## 🛡️ 13. Fault Tolerance

* Retry API failures
* Prevent crashes
* Wrap main loop with try/except

---

## 🚀 Output Required

* Full working live trading bot code
* Delta API integration
* start.py
* config.json
* requirements.txt

---

## 🔥 Bonus

* Graceful shutdown
* Order state tracking
* Prevent duplicate trades
* Lightweight in-memory state

---

Write clean, efficient, real-time, production-grade Python code suitable for live trading systems.

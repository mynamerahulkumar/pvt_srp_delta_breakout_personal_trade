# Delta Exchange Trading API

A comprehensive Python client for Delta Exchange India API, designed for algorithmic trading strategies. This library provides robust order management, bracket orders (TP/SL), position tracking, and risk management features.

## 📚 Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Authentication](#authentication)
6. [Placing Orders](#placing-orders)
7. [Bracket Orders (TP/SL)](#bracket-orders-tpsl)
8. [Position Management](#position-management)
9. [Order Management](#order-management)
10. [Market Data](#market-data)
11. [Risk Management](#risk-management)
12. [Algo Trading Integration](#algo-trading-integration)
13. [API Reference](#api-reference)
14. [Error Handling](#error-handling)
15. [Examples](#examples)

---

## Overview

Delta Exchange is a leading cryptocurrency derivatives exchange offering perpetual futures, options, and spot trading. This Python client provides a complete interface to Delta's REST API with enhanced features for algorithmic trading.

### Supported Products
- **Perpetual Futures**: BTCUSD, ETHUSD, etc.
- **Options**: Call/Put options on major cryptocurrencies
- **Spot Trading**: Selected cryptocurrency pairs

---

## Features

✅ **Complete API Coverage**: All Delta Exchange REST API endpoints
✅ **Bracket Orders**: Built-in Take Profit/Stop Loss order management
✅ **Position Tracking**: Real-time position monitoring and management
✅ **Risk Management**: Configurable position sizing and risk limits
✅ **Error Handling**: Robust retry logic and failure tracking
✅ **HMAC Authentication**: Secure API key authentication
✅ **Testnet Support**: Full testnet environment support
✅ **Async Operations**: Non-blocking API calls for high-frequency trading
✅ **Order Types**: Market, Limit, Stop Loss, Take Profit orders

---

## Installation

### Prerequisites
- Python 3.8+
- Delta Exchange API credentials (API Key & Secret)

### Install from source
```bash
git clone https://github.com/your-repo/delta-trading-api.git
cd delta-trading-api
pip install -r requirements.txt
```

### Dependencies
```
requests>=2.25.0
hmac
hashlib
logging
```

---

## Quick Start

```python
from api.delta_client import DeltaExchangeClient

# Initialize client
client = DeltaExchangeClient(
    api_key="your_api_key",
    api_secret="your_api_secret",
    testnet=True  # Use testnet for testing
)

# Place a market order
order = client.place_order(
    symbol="BTCUSD",
    side="buy",
    size=1,
    order_type="market_order"
)

print(f"Order placed: {order}")
```

---

## Authentication

### API Credentials Setup

1. **Create Delta Exchange Account**: Sign up at [Delta Exchange India](https://india.delta.exchange)
2. **Generate API Keys**:
   - Go to Account → API Keys
   - Create new API key with trading permissions
   - Note down API Key and Secret

### Client Initialization

```python
# Production environment
client = DeltaExchangeClient(
    api_key="your_production_api_key",
    api_secret="your_production_api_secret",
    base_url="https://api.india.delta.exchange"
)

# Testnet environment (recommended for testing)
client = DeltaExchangeClient(
    api_key="your_testnet_api_key",
    api_secret="your_testnet_api_secret",
    testnet=True
)
```

### Security Notes
- Never expose API credentials in code
- Use environment variables or secure credential storage
- Enable IP whitelist on your API keys
- Regularly rotate API keys

---

## Placing Orders

### Market Orders

Execute immediately at current market price:

```python
# Buy 1 BTCUSD contract at market price
order = client.place_order(
    symbol="BTCUSD",
    side="buy",
    size=1,
    order_type="market_order"
)
```

### Limit Orders

Execute only at specified price or better:

```python
# Buy 1 BTCUSD contract at limit price
order = client.place_order(
    symbol="BTCUSD",
    side="buy",
    size=1,
    order_type="limit_order",
    limit_price="45000.00"
)
```

### Order Response

```json
{
    "success": true,
    "result": {
        "id": 12345678,
        "product_symbol": "BTCUSD",
        "side": "buy",
        "size": 1,
        "order_type": "market_order",
        "state": "filled",
        "average_fill_price": "45123.50",
        "created_at": "2024-01-15T10:30:00Z"
    }
}
```

---

## Bracket Orders (TP/SL)

Bracket orders automatically place Take Profit and Stop Loss orders when a position is opened.

### Method 1: Bracket Orders with Entry Order

Place entry order with TP/SL in single API call:

```python
# Long position with bracket orders
order = client.place_order(
    symbol="BTCUSD",
    side="buy",
    size=1,
    order_type="market_order",
    bracket_stop_loss_price="44000.00",      # Stop Loss trigger price
    bracket_take_profit_price="47000.00",    # Take Profit trigger price
    bracket_take_profit_limit_price="46900.00", # TP limit price (optional)
    bracket_stop_trigger_method="last_traded_price"  # or "mark_price"
)
```

### Method 2: Separate Bracket Order Placement

Place entry order first, then add TP/SL separately:

```python
# Step 1: Place entry order
entry_order = client.place_order(
    symbol="BTCUSD",
    side="buy",
    size=1,
    order_type="market_order"
)

# Step 2: Add bracket orders to existing position
bracket_result = client.place_bracket_order_on_position(
    symbol="BTCUSD",
    stop_loss_price="44000.00",
    take_profit_price="47000.00",
    take_profit_limit_price="46900.00",
    trigger_method="mark_price"
)
```

### Bracket Order Parameters

| Parameter | Description | Required |
|-----------|-------------|----------|
| `stop_loss_price` | Price that triggers stop loss order | Yes |
| `take_profit_price` | Price that triggers take profit order | Yes |
| `take_profit_limit_price` | Limit price for TP order (defaults to trigger price) | No |
| `trigger_method` | "mark_price" or "last_traded_price" | No (default: "mark_price") |

### Trigger Methods

- **mark_price**: Uses mark price (more stable, recommended for volatile markets)
- **last_traded_price**: Uses last traded price (more responsive)

### Example: Complete Bracket Setup

```python
# Entry at $45,000
entry_price = 45000.00

# Stop Loss: 2% below entry ($44,100)
sl_price = str(entry_price * 0.98)

# Take Profit: 4% above entry ($46,800)
tp_trigger = str(entry_price * 1.04)
tp_limit = str(entry_price * 1.039)  # Slightly below trigger for execution

bracket_result = client.place_bracket_order_on_position(
    symbol="BTCUSD",
    stop_loss_price=sl_price,
    take_profit_price=tp_trigger,
    take_profit_limit_price=tp_limit,
    trigger_method="mark_price"
)
```

---

## Position Management

### Get Current Position

```python
position = client.get_position("BTCUSD")
print(f"Size: {position['size']}, Entry Price: {position['entry_price']}")
```

### Get All Positions

```python
positions = client.get_margined_positions()
for pos in positions:
    print(f"{pos['product_symbol']}: {pos['size']} @ {pos['entry_price']}")
```

### Close Position

```python
# Close entire position
close_order = client.place_order(
    symbol="BTCUSD",
    side="sell",  # Opposite of position side
    size=abs(position['size']),
    order_type="market_order"
)
```

---

## Order Management

### Get Open Orders

```python
open_orders = client.get_open_orders("BTCUSD")
for order in open_orders:
    print(f"Order {order['id']}: {order['side']} {order['size']} @ {order['price']}")
```

### Cancel Order

```python
cancel_result = client.cancel_order(
    order_id=12345678,
    product_symbol="BTCUSD"
)
```

### Cancel All Orders

```python
# Get all open orders
open_orders = client.get_open_orders()

# Cancel each order
for order in open_orders:
    client.cancel_order(order['id'], order['product_symbol'])
```

---

## Market Data

### Get OHLC Candles

```python
# Get 1-hour candles for last 24 hours
candles = client.get_ohlc_candles(
    symbol="BTCUSD",
    timeframe="1h",
    limit=24
)

for candle in candles:
    print(f"Time: {candle['time']}, O: {candle['open']}, H: {candle['high']}, L: {candle['low']}, C: {candle['close']}")
```

### Get Ticker Data

```python
ticker = client.get_ticker("BTCUSD")
print(f"BTCUSD: ${ticker['mark_price']} (24h change: {ticker['price_change_24h']})")
```

### Get Product Info

```python
product = client.get_product("BTCUSD")
print(f"Contract size: {product['contract_value']}, Tick size: {product['tick_size']}")
```

---

## Risk Management

### Position Sizing

Calculate position size based on risk parameters:

```python
from risk.risk_manager import RiskManager

risk_manager = RiskManager(
    position_size_type="percentage",
    risk_percentage=2.0,  # Risk 2% of account per trade
    stop_loss_pct=1.0,    # 1% stop loss
    take_profit_pct=2.0   # 2% take profit
)

balance = client.get_balance_for_asset("USD")['balance']
current_price = float(client.get_ticker("BTCUSD")['mark_price'])

position_size = risk_manager.calculate_position_size(balance, current_price)
print(f"Position size: {position_size} contracts")
```

### Bracket Order Creation

```python
# Calculate SL/TP prices
entry_price = 45000.00
bracket_params = risk_manager.create_bracket_order_params(entry_price, "buy")

# Place order with brackets
order = client.place_order(
    symbol="BTCUSD",
    side="buy",
    size=position_size,
    order_type="market_order",
    **bracket_params
)
```

---

## Algo Trading Integration

### Strategy Framework

```python
class MyTradingStrategy:
    def __init__(self, client, risk_manager):
        self.client = client
        self.risk_manager = risk_manager

    def generate_signal(self, market_data):
        """Implement your trading logic here"""
        # Example: Simple moving average crossover
        if market_data['sma_short'] > market_data['sma_long']:
            return "buy"
        elif market_data['sma_short'] < market_data['sma_long']:
            return "sell"
        return None

    def execute_trade(self, signal, symbol, size):
        """Execute trade with proper risk management"""
        if not signal:
            return

        # Calculate position size
        balance = self.client.get_balance_for_asset("USD")['balance']
        current_price = float(self.client.get_ticker(symbol)['mark_price'])
        position_size = self.risk_manager.calculate_position_size(balance, current_price)

        # Create bracket order parameters
        bracket_params = self.risk_manager.create_bracket_order_params(
            current_price, signal
        )

        # Place order with TP/SL
        order = self.client.place_order(
            symbol=symbol,
            side=signal,
            size=min(position_size, size),  # Respect max size limits
            order_type="market_order",
            **bracket_params
        )

        return order
```

### Different Strategy Types

#### 1. Trend Following Strategy

```python
class TrendFollowingStrategy(MyTradingStrategy):
    def generate_signal(self, data):
        # Use moving averages, trend indicators
        if data['ema_50'] > data['ema_200'] and data['rsi'] > 50:
            return "buy"
        elif data['ema_50'] < data['ema_200'] and data['rsi'] < 50:
            return "sell"
        return None
```

#### 2. Mean Reversion Strategy

```python
class MeanReversionStrategy(MyTradingStrategy):
    def generate_signal(self, data):
        # Bollinger Band squeeze + RSI divergence
        bb_width = (data['bb_upper'] - data['bb_lower']) / data['bb_middle']
        if bb_width < 0.05 and data['rsi'] < 30:
            return "buy"
        elif bb_width < 0.05 and data['rsi'] > 70:
            return "sell"
        return None
```

#### 3. Breakout Strategy

```python
class BreakoutStrategy(MyTradingStrategy):
    def generate_signal(self, data):
        # N-period high/low breakout
        if data['close'] > data['high_24h']:
            return "buy"
        elif data['close'] < data['low_24h']:
            return "sell"
        return None
```

#### 4. Arbitrage Strategy

```python
class ArbitrageStrategy(MyTradingStrategy):
    def generate_signal(self, data):
        # Spot vs Futures arbitrage
        spot_price = data['spot_price']
        futures_price = data['futures_price']
        spread = (futures_price - spot_price) / spot_price

        if spread > 0.005:  # 0.5% spread
            return "sell"  # Short futures, buy spot
        elif spread < -0.005:
            return "buy"   # Buy futures, short spot
        return None
```

### Multi-Strategy Bot

```python
class MultiStrategyBot:
    def __init__(self, client):
        self.client = client
        self.strategies = {
            'trend': TrendFollowingStrategy(client, risk_manager),
            'mean_rev': MeanReversionStrategy(client, risk_manager),
            'breakout': BreakoutStrategy(client, risk_manager)
        }

    def run(self):
        while True:
            market_data = self.client.get_market_data()
            signals = {}

            # Get signals from all strategies
            for name, strategy in self.strategies.items():
                signal = strategy.generate_signal(market_data)
                if signal:
                    signals[name] = signal

            # Execute trades based on consensus or priority
            if len(signals) >= 2:  # Require 2+ strategy agreement
                consensus_signal = self.get_consensus_signal(signals)
                if consensus_signal:
                    self.execute_consensus_trade(consensus_signal)

            time.sleep(60)  # Check every minute
```

---

## API Reference

### DeltaExchangeClient Methods

#### Order Management
- `place_order(...)` - Place market/limit orders with optional brackets
- `cancel_order(order_id, symbol)` - Cancel specific order
- `get_open_orders(symbol=None)` - Get open orders

#### Position Management
- `get_position(symbol)` - Get position for specific symbol
- `get_margined_positions(symbol=None)` - Get all margined positions

#### Bracket Orders
- `place_bracket_order_on_position(...)` - Add TP/SL to existing position

#### Market Data
- `get_ohlc_candles(symbol, timeframe, limit)` - Get price candles
- `get_ticker(symbol)` - Get current ticker data
- `get_product(symbol)` - Get product specifications

#### Account
- `get_wallet_balances()` - Get all wallet balances
- `get_balance_for_asset(asset)` - Get balance for specific asset

---

## Error Handling

### Common Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| `INSUFFICIENT_BALANCE` | Not enough funds | Check balance, reduce position size |
| `INVALID_ORDER_SIZE` | Order size too small/large | Check min/max order sizes |
| `POSITION_NOT_FOUND` | No position to bracket | Ensure position exists before adding brackets |
| `RATE_LIMIT_EXCEEDED` | Too many API calls | Implement rate limiting, use websockets for real-time data |

### Retry Logic

The client includes automatic retry logic for transient failures:

```python
# Client automatically retries failed requests
order = client.place_order(
    symbol="BTCUSD",
    side="buy",
    size=1,
    order_type="market_order"
)

# Check for success
if order.get('success'):
    print("Order placed successfully")
else:
    print(f"Order failed: {order.get('error')}")
```

### Circuit Breaker

Built-in circuit breaker stops trading after consecutive failures:

```python
# Check failure count
failure_count = client.get_failure_count()
if failure_count > 5:
    print("Circuit breaker triggered - stopping trading")
    # Implement your stop logic here
```

---

## Examples

### Complete Trading Bot

```python
import time
from api.delta_client import DeltaExchangeClient
from risk.risk_manager import RiskManager

class SimpleTradingBot:
    def __init__(self, api_key, api_secret):
        self.client = DeltaExchangeClient(api_key, api_secret, testnet=True)
        self.risk_manager = RiskManager(
            risk_percentage=1.0,
            stop_loss_pct=2.0,
            take_profit_pct=4.0
        )
        self.symbol = "BTCUSD"

    def run(self):
        print("Starting trading bot...")

        while True:
            try:
                # Get market data
                ticker = self.client.get_ticker(self.symbol)
                price = float(ticker['mark_price'])

                # Simple strategy: Buy on dips, sell on rallies
                if self.should_buy(price):
                    self.place_buy_order(price)
                elif self.should_sell(price):
                    self.place_sell_order()

                time.sleep(60)  # Check every minute

            except Exception as e:
                print(f"Error: {e}")
                time.sleep(30)

    def should_buy(self, price):
        # Buy if price drops 1% from recent high
        return price < self.get_recent_high() * 0.99

    def should_sell(self, price):
        # Sell if price rises 2% from recent low
        return price > self.get_recent_low() * 1.02

    def place_buy_order(self, price):
        balance = self.client.get_balance_for_asset("USD")['balance']
        position_size = self.risk_manager.calculate_position_size(balance, price)

        bracket_params = self.risk_manager.create_bracket_order_params(price, "buy")

        order = self.client.place_order(
            symbol=self.symbol,
            side="buy",
            size=position_size,
            order_type="market_order",
            **bracket_params
        )

        if order.get('success'):
            print(f"✓ Buy order placed: {position_size} contracts @ ${price}")
        else:
            print(f"✗ Buy order failed: {order.get('error')}")

    def place_sell_order(self):
        position = self.client.get_position(self.symbol)
        if position['size'] > 0:
            order = self.client.place_order(
                symbol=self.symbol,
                side="sell",
                size=position['size'],
                order_type="market_order"
            )
            print(f"✓ Sell order placed: {position['size']} contracts")

# Usage
bot = SimpleTradingBot("your_api_key", "your_api_secret")
bot.run()
```

### Risk Management Example

```python
from risk.risk_manager import RiskManager

# Initialize risk manager
risk_mgr = RiskManager(
    position_size_type="percentage",
    risk_percentage=2.0,      # Risk 2% per trade
    stop_loss_pct=1.5,        # 1.5% stop loss
    take_profit_pct=3.0,      # 3% take profit
    max_positions=3,          # Max 3 open positions
    max_daily_loss=5.0        # Stop if daily loss > 5%
)

# Check if trading is allowed
can_trade, reason = risk_mgr.can_trade(current_positions=2, account_balance=10000)
if can_trade:
    # Calculate position size
    size = risk_mgr.calculate_position_size(10000, 45000)
    print(f"Position size: {size} contracts")
else:
    print(f"Trading blocked: {reason}")
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and research purposes only. Trading cryptocurrencies involves substantial risk of loss and is not suitable for every investor. Past performance does not guarantee future results. Please trade responsibly and never risk more than you can afford to lose.

---

## Trading Strategy Explained

### What is Mean Reversion?

Mean reversion is based on the principle that **prices tend to return to their average over time**. When prices deviate significantly from the mean, they're likely to reverse.

```
Price at Upper Band → Overbought → Likely to fall → SELL Signal
Price at Lower Band → Oversold  → Likely to rise → BUY Signal
```

### Bollinger Bands Explained

Bollinger Bands consist of three lines:

```
Upper Band  = SMA(20) + (2 × Standard Deviation)
Middle Band = SMA(20)  ← Simple Moving Average
Lower Band  = SMA(20) - (2 × Standard Deviation)
```

**Visual Representation:**
```
         ┌─────────────────────────────────────┐
   $105  │    ╱╲    Upper Band (Overbought)    │  ← SELL Zone
         │   ╱  ╲   ╱╲                         │
   $100  │──╱────╲─╱──╲──── Middle Band ───────│  ← Mean/SMA
         │ ╱      ╲    ╲  ╱                    │
    $95  │╱            ╲╱  Lower Band          │  ← BUY Zone
         └─────────────────────────────────────┘
              Time →
```

### Mathematical Foundation

#### Simple Moving Average (SMA)
```
SMA = (P₁ + P₂ + P₃ + ... + Pₙ) / n

Where:
- P = Price at each period
- n = Number of periods (typically 20)
```

#### Standard Deviation (σ)
```
σ = √[ Σ(Pᵢ - SMA)² / n ]

Where:
- Pᵢ = Price at period i
- SMA = Simple Moving Average
- n = Number of periods
```

#### Bollinger Bands Formula
```
Upper Band = SMA + (k × σ)
Lower Band = SMA - (k × σ)

Where:
- k = Standard deviation multiplier (typically 2.0)
- σ = Standard deviation of prices
```

### RSI (Relative Strength Index) Explained

RSI measures the speed and magnitude of price changes on a scale of 0-100:

```python
RSI = 100 - (100 / (1 + RS))
where RS = Average Gain / Average Loss
```

**RSI Zones:**
```
100 ┬──────────────────────────
    │      OVERBOUGHT (>70)     ← Sell Confirmation
 70 ├──────────────────────────
    │         NEUTRAL
 30 ├──────────────────────────
    │       OVERSOLD (<30)      ← Buy Confirmation
  0 ┴──────────────────────────
```

#### Wilder's Smoothing Method

The RSI uses exponential smoothing for subsequent calculations:

```
Average Gain = [(Previous Avg Gain × 13) + Current Gain] / 14
Average Loss = [(Previous Avg Loss × 13) + Current Loss] / 14
```

### Combined Strategy Logic

| Signal | Bollinger Band Condition | RSI Condition | Action |
|--------|-------------------------|---------------|--------|
| **BUY** | Price ≤ Lower Band | RSI ≤ 30 (Oversold) | Open Long Position |
| **SELL** | Price ≥ Upper Band | RSI ≥ 70 (Overbought) | Open Short Position |
| **EXIT** | Price reaches Middle Band | Any | Close Position (Mean Reversion Complete) |

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Web Dashboard (HTML/CSS/JS)                   │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │   │
│  │  │Bot Control│ │ Strategy │ │ Market   │ │ Credential       │   │   │
│  │  │Start/Stop │ │ Settings │ │ Data     │ │ Manager          │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    │ HTTP/REST API                      │
│                                    ▼                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                              BACKEND                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Application                           │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │  /bot/*     /market/*    /positions/*    /auth/*         │   │   │
│  │  │  Control    Data         Management      Credentials     │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│  ┌─────────────────────────────────┼─────────────────────────────────┐ │
│  │                    TRADING BOT CORE                               │ │
│  │  ┌───────────────┐ ┌───────────┴───────────┐ ┌─────────────────┐ │ │
│  │  │  Trading Bot  │ │   Trading Strategy    │ │  Risk Manager   │ │ │
│  │  │  (Main Loop)  │ │  (Signal Generator)   │ │  (SL/TP/Size)   │ │ │
│  │  └───────┬───────┘ └───────────────────────┘ └─────────────────┘ │ │
│  │          │                                                        │ │
│  │  ┌───────▼────────────────────────────────────────────────────┐  │ │
│  │  │              Technical Indicators Module                    │  │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │  │ │
│  │  │  │Bollinger Bands│  │     RSI      │  │   MACD (Future) │  │  │ │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────┘  │  │ │
│  │  └────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                    │                                    │
│  ┌─────────────────────────────────▼─────────────────────────────────┐ │
│  │                    Delta Exchange API Client                      │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │ │
│  │  │  Market  │ │  Orders  │ │ Positions│ │  Authentication      │ │ │
│  │  │  Data    │ │  Execute │ │  Manage  │ │  HMAC-SHA256         │ │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS
                                    ▼
                    ┌───────────────────────────────┐
                    │    Delta Exchange India API   │
                    │    https://api.india.delta.   │
                    │           exchange            │
                    └───────────────────────────────┘
```

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TRADING LOOP FLOW                                │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │   START      │
    └──────┬───────┘
           ▼
    ┌──────────────┐     No      ┌──────────────┐
    │  Bot Running?├────────────►│    STOP      │
    └──────┬───────┘             └──────────────┘
           │ Yes
           ▼
    ┌──────────────┐
    │ Fetch OHLC   │◄──── Delta API: GET /v2/history/candles
    │ Candles      │
    └──────┬───────┘
           ▼
    ┌──────────────┐
    │ Calculate    │
    │ Indicators   │
    │ - BB         │
    │ - RSI        │
    └──────┬───────┘
           ▼
    ┌──────────────┐
    │ Get Current  │◄──── Delta API: GET /v2/positions
    │ Position     │
    └──────┬───────┘
           ▼
    ┌──────────────┐     Yes     ┌──────────────┐
    │ Has Position?├────────────►│ Check Exit   │
    └──────┬───────┘             │ Condition    │
           │ No                  └──────┬───────┘
           ▼                            │
    ┌──────────────┐             ┌──────▼───────┐
    │ Generate     │             │ Price at     │ Yes  ┌──────────────┐
    │ Entry Signal │             │ Middle Band? ├─────►│ Close        │
    └──────┬───────┘             └──────┬───────┘      │ Position     │
           │                            │ No           └──────────────┘
           ▼                            ▼
    ┌──────────────┐             ┌──────────────┐
    │ Signal Type? │             │ Continue     │
    └──────┬───────┘             │ Holding      │
           │                     └──────────────┘
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌───────┐    ┌───────┐    ┌───────────┐
│  BUY  │    │ SELL  │    │ No Signal │
└───┬───┘    └───┬───┘    └─────┬─────┘
    │            │              │
    ▼            ▼              │
┌────────────────────────┐      │
│ Execute Trade          │      │
│ - Calculate Size       │      │
│ - Set SL/TP           │      │
│ - Place Bracket Order │      │
└────────────────────────┘      │
    │                           │
    └───────────┬───────────────┘
                ▼
         ┌──────────────┐
         │ Sleep        │
         │ (interval)   │
         └──────┬───────┘
                │
                └────────► Loop Back to "Bot Running?"
```

---

## Project Structure

```
4BollingerRsiTradingstrategy/
│
├── main.py                    # Application entry point
├── config.yaml                # Main configuration file
├── requirements.txt           # Python dependencies
├── start.sh                   # Start backend + frontend
├── stop.sh                    # Stop all services
│
├── api/                       # REST API Layer
│   ├── __init__.py
│   ├── fastapi_app.py         # FastAPI endpoints
│   └── delta_client.py        # Delta Exchange API wrapper
│
├── bot/                       # Trading Bot Core
│   ├── __init__.py
│   └── trading_bot.py         # Main trading loop
│
├── strategy/                  # Strategy & Indicators
│   ├── __init__.py
│   ├── trading_strategy.py    # Signal generation logic
│   └── indicators.py          # Technical indicator calculations
│
├── risk/                      # Risk Management
│   ├── __init__.py
│   └── risk_manager.py        # Position sizing, SL/TP
│
├── utils/                     # Utilities
│   ├── __init__.py
│   └── config_loader.py       # Configuration management
│
├── frontend/                  # Web Dashboard
│   ├── index.html             # Main dashboard page
│   ├── styles.css             # Professional styling
│   ├── app.js                 # Frontend logic
│   ├── config.js              # Frontend configuration
│   ├── serve.py               # Simple HTTP server
│   └── images/
│       └── srpalgo_logo.jpeg  # Brand logo
│
├── logs/                      # Log files
│   └── trading_bot_*.log
│
└── scripts/                   # Utility scripts
    └── bot_manager.py
```

---

## Component Deep Dive

### 1. Technical Indicators (`strategy/indicators.py`)

#### Bollinger Bands Calculation

```python
def bollinger_bands(prices, period=20, std_dev=2.0):
    """
    Calculate Bollinger Bands
    
    Formula:
    - Middle Band = SMA(period)
    - Upper Band  = Middle + (std_dev × σ)
    - Lower Band  = Middle - (std_dev × σ)
    
    Where σ = Standard Deviation of prices over the period
    """
    for i in range(period - 1, len(prices)):
        window = prices[i - period + 1:i + 1]
        
        # Calculate SMA (Simple Moving Average)
        sma = sum(window) / period
        
        # Calculate Standard Deviation
        variance = sum((p - sma) ** 2 for p in window) / period
        std = variance ** 0.5
        
        # Calculate Bands
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
```

#### RSI Calculation (Wilder's Smoothing)

```python
def rsi(prices, period=14):
    """
    Calculate RSI using Wilder's Smoothed Moving Average
    
    Step 1: Calculate price changes (deltas)
    Step 2: Separate gains and losses
    Step 3: Calculate initial average gain/loss using SMA
    Step 4: Apply Wilder's smoothing for subsequent values
    
    Formula:
    RS = Average Gain / Average Loss
    RSI = 100 - (100 / (1 + RS))
    """
    # Calculate price changes
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    
    # Separate gains and losses
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]
    
    # First average using SMA
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Wilder's smoothing for subsequent values
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        # Calculate RSI
        if avg_loss == 0:
            rsi_value = 100
        else:
            rs = avg_gain / avg_loss
            rsi_value = 100 - (100 / (1 + rs))
```

### 2. Trading Strategy (`strategy/trading_strategy.py`)

```python
class TradingStrategy:
    """
    Main strategy class that combines indicators to generate signals
    """
    
    def generate_signal(self, indicators, current_position):
        """
        Decision Tree:
        
        1. Check cooldown (prevent overtrading)
        2. Get latest indicator values
        3. Detect Bollinger Band touch/close
        4. Confirm with RSI
        5. Check position constraints
        6. Return signal
        """
        
        # BUY CONDITIONS
        if price <= lower_band:           # Price at lower band
            if rsi <= oversold_threshold: # RSI confirms oversold
                if current_position <= 0: # Not already long
                    return "buy"
        
        # SELL CONDITIONS
        if price >= upper_band:            # Price at upper band
            if rsi >= overbought_threshold: # RSI confirms overbought
                if current_position >= 0:   # Not already short
                    return "sell"
        
        return None  # No signal
    
    def should_close_position(self, current_price, position_side, middle_band):
        """
        Mean Reversion Exit Logic:
        Close position when price returns to the middle band
        """
        if position_side == "long":
            # Close long when price rises to middle band
            return current_price >= middle_band
        elif position_side == "short":
            # Close short when price falls to middle band
            return current_price <= middle_band
        return False
```

### 3. Risk Manager (`risk/risk_manager.py`)  

```python
class RiskManager:
    """
    Handles all risk-related calculations
    """
    
    def calculate_position_size(self, balance, price):
        """
        Two modes:
        1. Fixed: Use configured fixed size
        2. Percentage: Risk X% of account per trade
        
        Percentage Mode Formula:
        Position Size = (Balance × Risk%) / (Price × SL%)
        """
        
    def calculate_sl_tp_prices(self, entry_price, side):
        """
        For LONG position:
        - Stop Loss = Entry × (1 - SL%)
        - Take Profit = Entry × (1 + TP%)
        
        For SHORT position:
        - Stop Loss = Entry × (1 + SL%)
        - Take Profit = Entry × (1 - TP%)
        """
        
    def can_trade(self, current_positions, balance):
        """
        Pre-trade checks:
        1. Max positions limit not exceeded
        2. Daily loss limit not exceeded
        3. Sufficient balance available
        """
```

### 4. Delta API Client (`api/delta_client.py`)

```python
class DeltaExchangeClient:
    """
    Handles all communication with Delta Exchange API
    """
    
    def generate_signature(self, message):
        """
        HMAC-SHA256 authentication
        
        Signature = HMAC-SHA256(secret, message)
        Message = METHOD + TIMESTAMP + PATH + QUERY_STRING + BODY
        
        Headers Required:
        - api-key: Your API key
        - signature: HMAC-SHA256 signature
        - timestamp: Unix timestamp in seconds
        """
        
    def place_order(self, symbol, side, size, order_type, **kwargs):
        """
        Order Types:
        - market_order: Execute immediately at market price
        - limit_order: Execute at specified price or better
        
        Bracket Order: Include SL and TP in single order
        """
```

---

## Signal Generation Logic

### Entry Signal Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    SIGNAL GENERATION                         │
└─────────────────────────────────────────────────────────────┘

Input: Last 50+ OHLC Candles
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Calculate Bollinger Bands (Period: 20, StdDev: 2)   │
│                                                              │
│   Upper = SMA(20) + 2σ  →  $105.50                          │
│   Middle = SMA(20)      →  $100.00                          │
│   Lower = SMA(20) - 2σ  →   $94.50                          │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Calculate RSI (Period: 14)                          │
│                                                              │
│   Current RSI → 28.5 (OVERSOLD)                             │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Get Current Price                                    │
│                                                              │
│   Close Price → $94.20 (BELOW Lower Band)                   │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Apply Strategy Rules                                 │
│                                                              │
│   ✓ Price ($94.20) < Lower Band ($94.50)                    │
│   ✓ RSI (28.5) < Oversold Threshold (30)                    │
│   ✓ No existing long position                               │
│                                                              │
│   RESULT: BUY SIGNAL GENERATED                              │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Execute Trade                                        │
│                                                              │
│   Order: BUY 1 Contract @ Market                            │
│   Stop Loss: $92.31 (-2%)                                   │
│   Take Profit: $97.97 (+4%)                                 │
└─────────────────────────────────────────────────────────────┘
```

### Exit Signal Flow (Mean Reversion)

```
┌─────────────────────────────────────────────────────────────┐
│                    EXIT LOGIC                                │
└─────────────────────────────────────────────────────────────┘

Position: LONG from $94.20
Current Price: $99.80
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Check: Has price reached Middle Band?                        │
│                                                              │
│   Middle Band = $100.00                                      │
│   Current Price = $99.80                                     │
│                                                              │
│   $99.80 ≈ $100.00 → YES, close enough!                     │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ ACTION: Close Long Position                                  │
│                                                              │
│   Entry: $94.20                                              │
│   Exit: $99.80                                               │
│   Profit: +5.94%                                             │
│                                                              │
│   ✓ Mean Reversion Complete                                  │
└─────────────────────────────────────────────────────────────┘
```

### Complete Trade Example

```
TRADE LIFECYCLE - BTCUSD LONG

TIME        EVENT                 PRICE      RSI     BB POSITION
────────────────────────────────────────────────────────────────
10:00       Start Monitoring      $98,500    45      Middle Zone
10:15       Price Dropping        $97,200    38      Near Lower
10:30       Entry Signal!         $95,800    28      At Lower ✓
            → BUY 1 Contract
            → SL: $93,884 (-2%)
            → TP: $99,632 (+4%)
            
11:00       Holding              $96,500     35      Below Middle
11:30       Holding              $97,800     48      Below Middle
12:00       Mean Reversion!      $98,200     52      At Middle ✓
            → CLOSE POSITION
            → Profit: +2.5%
            
RESULT: Successful mean reversion trade
```

---

## Risk Management

### Position Sizing Methods

#### 1. Fixed Size
```
Position Size = Configured Fixed Value
Example: Always trade 1 contract
```

#### 2. Percentage Risk
```
Position Size = (Account Balance × Risk%) / (Entry Price × Stop Loss%)

Example:
- Balance: $10,000
- Risk per trade: 2%
- Stop Loss: 2%

Position Size = ($10,000 × 0.02) / ($100 × 0.02)
             = $200 / $2
             = 100 contracts
```

### Stop Loss & Take Profit

```
LONG Position:
┌────────────────────────────────────────────────┐
│                                                │
│  Take Profit (+4%) ─────── $104.00            │
│         ▲                                      │
│         │                                      │
│         │ Target: +$4.00 per contract         │
│         │                                      │
│  Entry ─────────────────── $100.00            │
│         │                                      │
│         │ Risk: -$2.00 per contract           │
│         │                                      │
│         ▼                                      │
│  Stop Loss (-2%) ───────── $98.00             │
│                                                │
│  Risk:Reward Ratio = 1:2                      │
└────────────────────────────────────────────────┘

SHORT Position:
┌────────────────────────────────────────────────┐
│                                                │
│  Stop Loss (+2%) ───────── $102.00            │
│         ▲                                      │
│         │ Risk: -$2.00 per contract           │
│         │                                      │
│  Entry ─────────────────── $100.00            │
│         │                                      │
│         │ Target: +$4.00 per contract         │
│         ▼                                      │
│  Take Profit (-4%) ─────── $96.00             │
│                                                │
│  Risk:Reward Ratio = 1:2                      │
└────────────────────────────────────────────────┘
```

### Daily Loss Circuit Breaker

```python
if daily_pnl / starting_balance < -max_daily_loss:
    # STOP ALL TRADING
    # Example: If lost 5% of daily starting balance, halt trading
```

### Risk Parameters Summary

| Parameter | Default | Description |
|-----------|---------|-------------|
| Stop Loss % | 2.0% | Maximum loss per trade |
| Take Profit % | 4.0% | Target profit per trade |
| Max Positions | 1 | Concurrent positions allowed |
| Max Daily Loss | 5.0% | Daily drawdown limit |
| Position Type | Fixed | Fixed size or % of balance |

---

## Installation & Setup

### Prerequisites

- Python 3.10+
- Delta Exchange India account with API access
- Git

### Step 1: Clone Repository

```bash
git clone https://github.com/your-repo/4BollingerRsiTradingstrategy.git
cd 4BollingerRsiTradingstrategy
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment

Create a `.env` file with your Delta Exchange credentials:

```env
DELTA_API_KEY=your_api_key_here
DELTA_API_SECRET=your_api_secret_here
```

Or use the web dashboard to enter credentials (stored in browser only).

### Step 5: Start Services

```bash
./start.sh
```

This will start:
- **Backend API**: http://localhost:8504
- **Frontend Dashboard**: http://localhost:9504

### Step 6: Stop Services

```bash
./stop.sh
```

---

## Configuration Guide

### config.yaml Structure

```yaml
# Exchange Configuration
exchange:
  name: "delta_india"
  base_url: "https://api.india.delta.exchange"
  testnet: false  # Set true for paper trading

# Trading Configuration
trading:
  symbol: "BTCUSD"           # Trading pair
  timeframe: "5m"            # Candle timeframe
  order_type: "market_order" # Order execution type

# Strategy Configuration
strategy:
  bollinger:
    period: 20               # BB period (default: 20)
    std_dev: 2.0             # Standard deviations (default: 2)
    enabled: true
    
  rsi:
    period: 14               # RSI period (default: 14)
    overbought: 70           # Overbought threshold
    oversold: 30             # Oversold threshold
    enabled: true
    
  confirmation:
    candles: 1               # Candles to wait for confirmation
    type: "close"            # "close" or "touch"
    signal_cooldown: 300     # Seconds between signals

# Risk Management
risk:
  position_sizing:
    type: "fixed"            # "fixed" or "percentage"
    fixed_size: 1            # Fixed contract size
    risk_percentage: 2.0     # Risk per trade (if percentage)
    
  stop_loss:
    percentage: 2.0          # Stop loss percentage
    
  take_profit:
    percentage: 4.0          # Take profit percentage
    
  limits:
    max_positions: 1         # Max concurrent positions
    max_daily_loss: 5.0      # Max daily loss percentage

# Bot Configuration
bot:
  mode: "api"                # "live" or "api"
  loop_interval: 60          # Seconds between iterations

# API Configuration
api:
  host: "0.0.0.0"
  port: 8504
```

### Parameter Tuning Guide

| Parameter | Conservative | Balanced | Aggressive |
|-----------|--------------|----------|------------|
| BB Period | 25 | 20 | 15 |
| BB StdDev | 2.5 | 2.0 | 1.5 |
| RSI Period | 21 | 14 | 7 |
| RSI Oversold | 25 | 30 | 35 |
| RSI Overbought | 75 | 70 | 65 |
| Stop Loss | 1.5% | 2.0% | 3.0% |
| Take Profit | 3.0% | 4.0% | 6.0% |

---

## API Reference

### Bot Control

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/bot/start` | POST | Start trading bot |
| `/bot/stop` | POST | Stop trading bot |
| `/bot/status` | GET | Get current status |
| `/bot/config` | GET | Get configuration |
| `/bot/logs` | GET | Get activity logs |

### Strategy Updates

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/bot/strategy` | PUT | Update strategy parameters |
| `/bot/risk` | PUT | Update risk parameters |
| `/bot/symbol` | PUT | Change trading symbol |

### Market Data

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/market/ticker` | GET | Get current ticker |
| `/market/candles` | GET | Get OHLC candles |

### Positions & Orders

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/positions` | GET | Get current position |
| `/positions/close` | POST | Close position |
| `/orders` | GET | Get open orders |
| `/balance` | GET | Get account balance |

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/credentials` | POST | Set API credentials |
| `/auth/test` | POST | Test credentials |
| `/auth/status` | GET | Check auth status |

### Example API Calls

```bash
# Start bot
curl -X POST http://localhost:8504/bot/start

# Get status
curl http://localhost:8504/bot/status

# Update strategy
curl -X PUT http://localhost:8504/bot/strategy \
  -H "Content-Type: application/json" \
  -d '{"bollinger_period": 20, "bollinger_std_dev": 2.0, "rsi_period": 14}'

# Get positions
curl http://localhost:8504/positions/margined
```

---

## Frontend Features

### Dashboard Components

1. **Bot Control Panel**
   - Start/Stop strategy
   - Real-time status indicator
   - Uptime display

2. **Trading Parameters**
   - Symbol selection (BTCUSD, ETHUSD)
   - Timeframe selection
   - Position size configuration
   - Stop Loss / Take Profit settings

3. **Strategy Settings**
   - Bollinger Bands: Period, Std Dev
   - RSI: Period, Overbought, Oversold
   - Confirmation settings

4. **Market Data Display**
   - Current price
   - 24h High/Low
   - Volume
   - Mark price

5. **Position Monitor**
   - Current position side (Long/Short)
   - Entry price
   - Unrealized PnL
   - Close position button

6. **Activity Logs**
   - Real-time log streaming
   - Color-coded log levels
   - Auto-scroll toggle

### Strategy Selection

Two modes available:

1. **Simple BB + RSI** - Classic mean-reversion strategy
2. **Multi-Strategy** - Combines BB+RSI with MACD and EMA crossover (future)

### Credential Management

- Credentials stored in browser localStorage
- Never sent to server filesystem
- Secure for Azure deployment

---

## Deployment to Azure

### Prerequisites

1. Azure account with App Service
2. Azure CLI installed

### Deployment Steps

```bash
# Login to Azure
az login

# Create resource group
az group create --name srp-algo-rg --location eastus

# Create App Service plan
az appservice plan create --name srp-algo-plan \
  --resource-group srp-algo-rg --sku B1 --is-linux

# Create web app
az webapp create --resource-group srp-algo-rg \
  --plan srp-algo-plan --name srp-algo-bot \
  --runtime "PYTHON|3.10"

# Deploy code
az webapp up --name srp-algo-bot --resource-group srp-algo-rg
```

### Client-Side Credentials

When deployed to Azure, users enter their Delta API credentials via the Settings modal. Credentials are stored in browser localStorage - they never touch the server filesystem.

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "No module named uvicorn" | `pip install uvicorn fastapi` |
| Backend won't start | Check `.pids/backend.log` for errors |
| API connection failed | Verify Delta API credentials |
| No signals generated | Check if cooldown period active |
| Position not closing | Verify bracket order execution on Delta |

### Log Files

- Backend logs: `.pids/backend.log`
- Frontend logs: `.pids/frontend.log`
- Trading logs: `logs/trading_bot_*.log`

### Debug Mode

Enable debug logging in `config.yaml`:

```yaml
logging:
  level: "DEBUG"
```

---

## For Students: Learning Path

### Week 1: Understanding the Basics
1. Learn what Bollinger Bands measure (volatility + price deviation)
2. Understand RSI (momentum oscillator)
3. Study the mean reversion concept

### Week 2: Code Analysis
1. Read `strategy/indicators.py` - understand the math
2. Read `strategy/trading_strategy.py` - understand signal logic
3. Read `risk/risk_manager.py` - understand position sizing

### Week 3: System Architecture
1. Trace data flow from API to trade execution
2. Understand REST API design patterns
3. Study the trading loop in `bot/trading_bot.py`

### Week 4: Hands-On Practice
1. Run the bot in testnet mode
2. Modify parameters and observe results
3. Add logging to understand execution flow

### Exercises

1. **Calculate Bollinger Bands manually** for 5 prices
2. **Calculate RSI manually** for 6 prices
3. **Trace a trade** from signal generation to execution
4. **Add a new indicator** (e.g., MACD)

---

## License

This project is proprietary software owned by SRP Algo.

---

## Support

For questions or issues, contact:
- Email: support@srpalgo.com
- Documentation: This README

---

<p align="center">
  <strong>Happy Trading! 📈</strong><br>
  <em>Remember: Past performance does not guarantee future results. Trade responsibly.</em>
</p>

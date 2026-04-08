#!/usr/bin/env python3
"""
Delta Exchange Breakout Trading Bot
====================================
Entry point for the live breakout trading system.
Supports BTCUSD, ETHUSD with hourly/daily breakout strategies.

Usage:
    python start.py
"""
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config_loader import load_config
from src.logger_setup import setup_logger
from src.strategy_engine import StrategyEngine


def main():
    try:
        # Load configuration
        config = load_config()

        # Setup logging
        setup_logger(config)

        import logging
        logger = logging.getLogger(__name__)

        logger.info("Configuration loaded successfully")
        logger.info("Environment: %s", config.get("environment", "local"))
        logger.info("Base URL: %s", config.get("delta_base_url"))

        # Initialize and run the strategy engine
        engine = StrategyEngine(config)
        engine.run()

    except KeyboardInterrupt:
        print("\nShutdown requested by user.")
        sys.exit(0)
    except Exception as e:
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

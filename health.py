#!/usr/bin/env python3
"""
Delta Exchange API Health Check
================================
Verifies connectivity, authentication, and data access against the Delta Exchange API.

Usage:
    python health.py
"""
import sys
import os
import socket
import time
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config_loader import load_config
from src.logger_setup import setup_logger


# ── ANSI helpers ──
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"


def _pass(label):
    print(f"  {GREEN}✔ PASS{RESET}  {label}")


def _fail(label, detail=""):
    msg = f"  {RED}✘ FAIL{RESET}  {label}"
    if detail:
        msg += f"  {DIM}({detail}){RESET}"
    print(msg)


def _warn(label, detail=""):
    msg = f"  {YELLOW}⚠ WARN{RESET}  {label}"
    if detail:
        msg += f"  {DIM}({detail}){RESET}"
    print(msg)


def _header(title):
    print(f"\n{BOLD}── {title} ──{RESET}")


def run_health_checks():
    results = []  # list of (name, passed: bool)

    # ──────────────────────────────────────────────────────────
    # 1. Config check
    # ──────────────────────────────────────────────────────────
    _header("1. Configuration")
    try:
        config = load_config()
        setup_logger(config)
    except Exception as e:
        _fail("Load config / .env", str(e))
        results.append(("Configuration", False))
        print(f"\n{RED}Cannot proceed without valid config. Fix and retry.{RESET}")
        return results

    base_url = config.get("delta_base_url", "")
    api_key = config.get("delta_api_key", "")
    symbols = config.get("symbols", [])

    checks = [
        ("delta_base_url is set", bool(base_url)),
        ("delta_api_key is set", bool(api_key)),
        ("delta_api_secret is set", bool(config.get("delta_api_secret"))),
        ("symbols configured", bool(symbols)),
    ]
    all_ok = True
    for label, ok in checks:
        if ok:
            _pass(label)
        else:
            _fail(label)
            all_ok = False
    results.append(("Configuration", all_ok))

    if not all_ok:
        print(f"\n{RED}Cannot proceed without valid config. Fix and retry.{RESET}")
        return results

    print(f"  {DIM}Base URL : {base_url}{RESET}")
    print(f"  {DIM}Symbols  : {symbols}{RESET}")

    # ──────────────────────────────────────────────────────────
    # 2. DNS resolution
    # ──────────────────────────────────────────────────────────
    _header("2. DNS Resolution")
    hostname = urlparse(base_url).hostname
    try:
        ip = socket.gethostbyname(hostname)
        _pass(f"{hostname} → {ip}")
        results.append(("DNS Resolution", True))
    except socket.gaierror as e:
        _fail(f"Cannot resolve {hostname}", str(e))
        results.append(("DNS Resolution", False))
        print(f"\n{RED}DNS failed — network checks will also fail.{RESET}")

    # ──────────────────────────────────────────────────────────
    # 3. HTTP connectivity (raw GET to base URL)
    # ──────────────────────────────────────────────────────────
    _header("3. HTTP Connectivity")
    try:
        import requests
        resp = requests.get(base_url, timeout=10)
        _pass(f"GET {base_url} → HTTP {resp.status_code}")
        results.append(("HTTP Connectivity", True))
    except Exception as e:
        _fail(f"GET {base_url}", str(e))
        results.append(("HTTP Connectivity", False))

    # ──────────────────────────────────────────────────────────
    # 4. Symbol resolution via /v2/products
    # ──────────────────────────────────────────────────────────
    _header("4. Symbol Resolution")
    try:
        from src.delta_api_client import DeltaAPIClient
        api = DeltaAPIClient(config)
        for sym in symbols:
            pid = api.get_product_id(sym)
            tick = api.get_tick_size(sym)
            _pass(f"{sym} → product_id={pid}, tick_size={tick}")
        results.append(("Symbol Resolution", True))
    except Exception as e:
        _fail("Resolve symbols", str(e))
        results.append(("Symbol Resolution", False))
        # Cannot continue without API client
        _print_summary(results)
        return results

    # ──────────────────────────────────────────────────────────
    # 5. Ticker / price fetch
    # ──────────────────────────────────────────────────────────
    _header("5. Ticker / Price Fetch")
    ticker_ok = True
    for sym in symbols:
        try:
            ticker = api.get_ticker(sym)
            mark = ticker.get("mark_price", "N/A")
            _pass(f"{sym} mark_price = {mark}")
        except Exception as e:
            _fail(f"{sym} ticker", str(e))
            ticker_ok = False
    results.append(("Ticker Fetch", ticker_ok))

    # ──────────────────────────────────────────────────────────
    # 6. Candle / OHLC fetch
    # ──────────────────────────────────────────────────────────
    _header("6. Candle Data Fetch")
    candle_ok = True
    resolution = config.get("breakout", {}).get("candle_resolution", "1h")
    end_ts = int(time.time())
    start_ts = end_ts - 3600 * 4  # last 4 hours
    for sym in symbols:
        try:
            candles = api.get_ohlc_candles(sym, resolution=resolution, start=start_ts, end=end_ts)
            count = len(candles) if candles else 0
            if count > 0:
                _pass(f"{sym} ({resolution}) → {count} candles")
            else:
                _warn(f"{sym} ({resolution}) → 0 candles", "market may be closed or resolution too large")
            candle_ok = candle_ok and (count > 0)
        except Exception as e:
            _fail(f"{sym} candles", str(e))
            candle_ok = False
    results.append(("Candle Fetch", candle_ok))

    # ──────────────────────────────────────────────────────────
    # 7. Auth check — wallet balances
    # ──────────────────────────────────────────────────────────
    _header("7. Authentication (Wallet Balances)")
    try:
        balances = api.get_wallet_balances()
        if balances:
            # Show first non-zero balance
            shown = False
            for b in balances:
                bal = float(b.get("balance", 0))
                if bal > 0:
                    asset = b.get("asset_symbol", b.get("asset_id", "?"))
                    _pass(f"Authenticated OK — {asset} balance: {bal}")
                    shown = True
                    break
            if not shown:
                _pass("Authenticated OK — no non-zero balances")
        else:
            _pass("Authenticated OK — empty wallet response")
        results.append(("Authentication", True))
    except Exception as e:
        _fail("Wallet balances", str(e))
        results.append(("Authentication", False))

    # ──────────────────────────────────────────────────────────
    _print_summary(results)
    return results


def _print_summary(results):
    print(f"\n{BOLD}{'═' * 50}{RESET}")
    print(f"{BOLD}  HEALTH CHECK SUMMARY{RESET}")
    print(f"{BOLD}{'═' * 50}{RESET}")
    all_passed = True
    for name, passed in results:
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False
    print(f"{BOLD}{'═' * 50}{RESET}")
    if all_passed:
        print(f"\n{GREEN}{BOLD}All checks passed. API connectivity is healthy.{RESET}\n")
    else:
        print(f"\n{RED}{BOLD}Some checks failed. Review errors above.{RESET}\n")


if __name__ == "__main__":
    results = run_health_checks()
    passed = all(ok for _, ok in results)
    sys.exit(0 if passed else 1)

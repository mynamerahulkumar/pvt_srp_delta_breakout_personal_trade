#!/bin/bash
# ══════════════════════════════════════════════════════════
#  Delta Breakout Bot — Monitor & Log Viewer
# ══════════════════════════════════════════════════════════
#
#  Usage:
#    ./monitor.sh status   — Check if the bot is running
#    ./monitor.sh logs     — Tail live logs (colored)
#    ./monitor.sh last     — Show last 50 log lines
#    ./monitor.sh          — Show status + last 10 lines
# ══════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/logs/trading_bot.log"
BOT_SCRIPT="start.py"

# ── Colors ──
GREEN="\033[1;32m"
RED="\033[1;31m"
YELLOW="\033[1;33m"
CYAN="\033[1;36m"
BOLD="\033[1m"
RESET="\033[0m"

check_status() {
    # Look for the bot process (python/uv running start.py)
    PIDS=$(ps aux | grep -E "(python|uv).*${BOT_SCRIPT}" | grep -v grep | awk '{print $2}')

    if [ -n "$PIDS" ]; then
        echo -e "${GREEN}✔ Bot is RUNNING${RESET}"
        echo -e "${CYAN}  PID(s): ${BOLD}${PIDS}${RESET}"
        # Show uptime info
        for pid in $PIDS; do
            ELAPSED=$(ps -o etime= -p "$pid" 2>/dev/null | xargs)
            if [ -n "$ELAPSED" ]; then
                echo -e "${CYAN}  Uptime: ${BOLD}${ELAPSED}${RESET}"
            fi
        done
        return 0
    else
        echo -e "${RED}✘ Bot is NOT running${RESET}"
        return 1
    fi
}

show_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        echo -e "${RED}Log file not found: $LOG_FILE${RESET}"
        exit 1
    fi
    echo -e "${CYAN}${BOLD}═══ Live Logs (Ctrl+C to stop) ═══${RESET}"
    echo ""
    tail -f "$LOG_FILE"
}

show_last() {
    LINES=${1:-50}
    if [ ! -f "$LOG_FILE" ]; then
        echo -e "${RED}Log file not found: $LOG_FILE${RESET}"
        exit 1
    fi
    echo -e "${CYAN}${BOLD}═══ Last $LINES log lines ═══${RESET}"
    echo ""
    tail -n "$LINES" "$LOG_FILE"
}

case "${1:-}" in
    status)
        check_status
        ;;
    logs|tail)
        check_status
        echo ""
        show_logs
        ;;
    last)
        show_last "${2:-50}"
        ;;
    *)
        check_status
        echo ""
        if [ -f "$LOG_FILE" ]; then
            echo -e "${YELLOW}── Last 10 log lines ──${RESET}"
            tail -n 10 "$LOG_FILE"
            echo ""
            echo -e "${CYAN}Tip: ${RESET}./monitor.sh logs  ${CYAN}for live streaming${RESET}"
        fi
        ;;
esac

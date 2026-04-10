import logging
import os
from logging.handlers import RotatingFileHandler


# ── ANSI color codes ──
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RED    = "\033[31m"
    GREEN  = "\033[32m"
    YELLOW = "\033[33m"
    BLUE   = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN   = "\033[36m"
    WHITE  = "\033[37m"
    BG_GREEN  = "\033[42m"
    BG_RED    = "\033[41m"
    BG_MAGENTA = "\033[45m"
    BG_BLUE   = "\033[44m"


class ColorFormatter(logging.Formatter):
    """Formatter that applies ANSI colors based on level and message keywords."""

    LEVEL_COLORS = {
        logging.DEBUG:    C.DIM,
        logging.INFO:     C.CYAN,
        logging.WARNING:  C.YELLOW,
        logging.ERROR:    C.RED,
        logging.CRITICAL: C.BOLD + C.RED,
    }

    # (keyword, color) — first match wins, checked in order
    KEYWORD_COLORS = [
        ("BREAKOUT DETECTED",  C.BOLD + C.MAGENTA),
        ("Breakout detected",  C.BOLD + C.MAGENTA),
        ("LONG",               C.BOLD + C.GREEN),
        ("SHORT",              C.BOLD + C.RED),
        ("Position closed",    C.BOLD + C.YELLOW),
        ("Trade opened",       C.BOLD + C.GREEN),
        ("BOT STARTED",        C.BOLD + C.GREEN),
        ("STARTED",            C.BOLD + C.GREEN),
        ("Shutdown",           C.BOLD + C.YELLOW),
        ("PnL",                C.BOLD + C.YELLOW),
        ("RSI",                C.BLUE),
        ("═",                  C.BOLD + C.BLUE),
        ("─",                  C.BOLD + C.BLUE),
        ("│",                  C.BOLD + C.BLUE),
    ]

    # RSI tag colors
    RSI_TAG_COLORS = {
        "OVERBOUGHT": C.BOLD + C.RED,
        "OVERSOLD":   C.BOLD + C.GREEN,
        "NEUTRAL":    C.BOLD + C.BLUE,
    }

    def _colorize_levels_line(self, msg):
        """Apply per-segment colors to the Levels summary line."""
        import re
        # Color the symbol in bold white
        msg = re.sub(r'(\[)([A-Z]+USD)(\])', rf'\1{C.BOLD}{C.CYAN}\2{C.RESET}\3', msg)
        # Color "Levels (...)" label
        msg = re.sub(r'(Levels \([^)]+\))', rf'{C.BOLD}{C.WHITE}\1{C.RESET}', msg)
        # Color "BUY above: <number>" in green
        msg = re.sub(r'(BUY above: [\d.]+)', rf'{C.BOLD}{C.GREEN}\1{C.RESET}', msg)
        # Color "SELL below: <number>" in red
        msg = re.sub(r'(SELL below: [\d.]+)', rf'{C.BOLD}{C.RED}\1{C.RESET}', msg)
        # Color "Last close: <number>" in yellow
        msg = re.sub(r'(Last close: [\d.]+)', rf'{C.BOLD}{C.YELLOW}\1{C.RESET}', msg)
        # Color "Mark: <number>" in magenta
        msg = re.sub(r'(Mark: [\d.]+)', rf'{C.BOLD}{C.MAGENTA}\1{C.RESET}', msg)
        # Color RSI value and tag
        for tag, color in self.RSI_TAG_COLORS.items():
            msg = re.sub(rf'(RSI\(\d+\): [\d.]+) ({tag})', rf'{C.BOLD}{C.CYAN}\1{C.RESET} {color}\2{C.RESET}', msg)
        # Color box-drawing chars
        msg = msg.replace('│', f'{C.DIM}{C.BLUE}│{C.RESET}')
        return msg

    def format(self, record):
        msg = super().format(record)
        text = record.getMessage()

        # Special multi-color formatting for Levels line
        if "Levels" in text and "BUY above" in text:
            return self._colorize_levels_line(msg)

        # Keyword match first
        for keyword, color in self.KEYWORD_COLORS:
            if keyword in text:
                return f"{color}{msg}{C.RESET}"

        # Fallback: color by level
        color = self.LEVEL_COLORS.get(record.levelno, "")
        return f"{color}{msg}{C.RESET}"


def setup_logger(config):
    """Configure logging: always console (colored) + rotating file."""
    log_cfg = config.get("logging", {})
    log_dir = log_cfg.get("log_dir", "logs")
    max_bytes = log_cfg.get("max_log_size_mb", 10) * 1024 * 1024
    backup_count = log_cfg.get("backup_count", 3)
    colorful = log_cfg.get("colorful_console", True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    time_fmt = "%Y-%m-%d %H:%M:%S"
    log_fmt = "[%(asctime)s] [%(levelname)-8s] %(message)s"

    # ── Console handler (always active) ──
    console_handler = logging.StreamHandler()
    if colorful:
        console_handler.setFormatter(ColorFormatter(log_fmt, datefmt=time_fmt))
    else:
        console_handler.setFormatter(logging.Formatter(log_fmt, datefmt=time_fmt))
    root_logger.addHandler(console_handler)

    # ── Rotating file handler (always active) ──
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "trading_bot.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setFormatter(logging.Formatter(log_fmt, datefmt=time_fmt))
    root_logger.addHandler(file_handler)

    return root_logger

#!/usr/bin/env python3
"""
Log Management Utility
=======================
View, inspect, and delete trading bot log files.

Usage:
    python manage_logs.py list              List all log files with sizes
    python manage_logs.py size              Show total log folder size & config limits
    python manage_logs.py delete            Delete ALL log files (with confirmation)
    python manage_logs.py delete <file>     Delete a specific log file
"""
import sys
import os
import json
import glob
from datetime import datetime

# ── Defaults (overridden by config.json if present) ──
DEFAULT_LOG_DIR = "logs"
DEFAULT_MAX_LOG_SIZE_MB = 10

# ── ANSI helpers ──
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"


def _load_log_config():
    """Read log_dir and max_log_size_mb from config.json."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    log_dir = DEFAULT_LOG_DIR
    max_size_mb = DEFAULT_MAX_LOG_SIZE_MB
    backup_count = 3

    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            cfg = json.load(f)
        log_cfg = cfg.get("logging", {})
        log_dir = log_cfg.get("log_dir", log_dir)
        max_size_mb = log_cfg.get("max_log_size_mb", max_size_mb)
        backup_count = log_cfg.get("backup_count", backup_count)

    return log_dir, max_size_mb, backup_count


def _human_size(size_bytes):
    """Format bytes as human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _get_log_files(log_dir):
    """Return sorted list of log files in the log directory."""
    if not os.path.isdir(log_dir):
        return []
    files = []
    for name in sorted(os.listdir(log_dir)):
        path = os.path.join(log_dir, name)
        if os.path.isfile(path):
            files.append(path)
    return files


def cmd_list(log_dir):
    """List all log files with sizes and last modified time."""
    files = _get_log_files(log_dir)
    if not files:
        print(f"{YELLOW}No log files found in '{log_dir}/'{RESET}")
        return

    print(f"\n{BOLD}Log files in '{log_dir}/':{RESET}\n")
    print(f"  {'File':<35} {'Size':>10}   {'Last Modified'}")
    print(f"  {'─' * 35} {'─' * 10}   {'─' * 20}")

    total = 0
    for path in files:
        name = os.path.basename(path)
        size = os.path.getsize(path)
        mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
        total += size
        print(f"  {name:<35} {_human_size(size):>10}   {mtime}")

    print(f"\n  {BOLD}Total: {_human_size(total)}{RESET}  ({len(files)} file(s))\n")


def cmd_size(log_dir, max_size_mb, backup_count):
    """Show total log folder size and configured limits."""
    files = _get_log_files(log_dir)
    total = sum(os.path.getsize(f) for f in files)

    max_possible = max_size_mb * (1 + backup_count)  # active + backups

    print(f"\n{BOLD}Log Size Info:{RESET}")
    print(f"  Log directory      : {log_dir}/")
    print(f"  Current total size : {_human_size(total)}")
    print(f"  Number of files    : {len(files)}")
    print(f"  Max per file       : {max_size_mb} MB  {DIM}(configurable in config.json → logging.max_log_size_mb){RESET}")
    print(f"  Backup count       : {backup_count}    {DIM}(configurable in config.json → logging.backup_count){RESET}")
    print(f"  Max possible total : {max_possible} MB  {DIM}(1 active + {backup_count} backups){RESET}")
    print()


def cmd_delete(log_dir, target=None):
    """Delete log files. If target is None, delete all (with confirmation)."""
    if target:
        # Delete a specific file
        path = os.path.join(log_dir, target)
        if not os.path.isfile(path):
            print(f"{RED}File not found: {path}{RESET}")
            sys.exit(1)
        size = os.path.getsize(path)
        os.remove(path)
        print(f"{GREEN}Deleted: {target} ({_human_size(size)}){RESET}")
        return

    # Delete all
    files = _get_log_files(log_dir)
    if not files:
        print(f"{YELLOW}No log files to delete.{RESET}")
        return

    total = sum(os.path.getsize(f) for f in files)
    print(f"\n{YELLOW}This will delete {len(files)} file(s) totalling {_human_size(total)} from '{log_dir}/':{RESET}")
    for f in files:
        print(f"  • {os.path.basename(f)}")

    confirm = input(f"\n{BOLD}Are you sure? (y/N): {RESET}").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    deleted = 0
    for path in files:
        try:
            os.remove(path)
            deleted += 1
        except OSError as e:
            print(f"{RED}Failed to delete {os.path.basename(path)}: {e}{RESET}")

    print(f"{GREEN}Deleted {deleted}/{len(files)} file(s).{RESET}")


def main():
    log_dir, max_size_mb, backup_count = _load_log_config()

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "list":
        cmd_list(log_dir)
    elif command == "size":
        cmd_size(log_dir, max_size_mb, backup_count)
    elif command == "delete":
        target = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_delete(log_dir, target)
    else:
        print(f"{RED}Unknown command: {command}{RESET}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

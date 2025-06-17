#!/usr/bin/env python3
"""Simple watchdog to verify ``humed`` daemon is running.

This script checks a pidfile to confirm the ``humed`` process is alive.
It can run once or periodically.  When the daemon is not running an
optional alert command is executed using the system shell.
"""
import os
import argparse
import subprocess
import time

def is_running(pidfile: str) -> bool:
    """Return True if pid from pidfile corresponds to a running process."""
    if not os.path.exists(pidfile):
        return False
    try:
        with open(pidfile) as f:
            pid = int(f.read().strip())
    except Exception:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True

def check_once(pidfile: str, alert_cmd: str | None = None, verbose: bool = False) -> bool:
    """Check if humed is running and optionally execute an alert command."""
    running = is_running(pidfile)
    if running:
        if verbose:
            print('humed is running')
    else:
        if verbose:
            print('humed is NOT running')
        if alert_cmd:
            subprocess.call(alert_cmd, shell=True)
    return running


def watch(pidfile: str,
          alert_cmd: str | None = None,
          interval: int = 0,
          verbose: bool = False,
          iterations: int | None = 1) -> int:
    """Run the watchdog loop.

    If ``iterations`` is ``None`` the loop runs forever. ``interval`` specifies
    the sleep time between checks. The return value corresponds to the last
    check result.
    """
    last_running = True
    count = 0
    while True:
        last_running = check_once(pidfile, alert_cmd, verbose)
        count += 1
        if iterations is not None and count >= iterations:
            break
        if iterations is None and interval <= 0:
            break
        if interval > 0:
            time.sleep(interval)
        else:
            break
    return 0 if last_running else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that humed is running")
    parser.add_argument('--pidfile', default='/var/run/humed.pid',
                        help='Path to humed pidfile')
    parser.add_argument('--alert-cmd', metavar='CMD',
                        help='Command to execute when humed is not running')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--interval', type=int, default=0,
                        help='Seconds between checks. 0 runs a single check')
    args = parser.parse_args()

    iterations = None if args.interval > 0 else 1
    return watch(
        pidfile=args.pidfile,
        alert_cmd=args.alert_cmd,
        interval=args.interval,
        verbose=args.verbose,
        iterations=iterations,
    )

if __name__ == '__main__':
    raise SystemExit(main())

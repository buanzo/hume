#!/usr/bin/env python3
"""Simple watchdog to verify humed daemon is running.

This script checks a pidfile to confirm the humed process is alive.
If the process is not running, an optional alert command can be
executed. The command is run using the system shell.
"""
import os
import argparse
import subprocess

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

def main() -> int:
    parser = argparse.ArgumentParser(description="Check that humed is running")
    parser.add_argument('--pidfile', default='/var/run/humed.pid',
                        help='Path to humed pidfile')
    parser.add_argument('--alert-cmd', metavar='CMD',
                        help='Command to execute when humed is not running')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    args = parser.parse_args()

    running = is_running(args.pidfile)
    if running:
        if args.verbose:
            print('humed is running')
        return 0
    if args.verbose:
        print('humed is NOT running')
    if args.alert_cmd:
        subprocess.call(args.alert_cmd, shell=True)
    return 1

if __name__ == '__main__':
    raise SystemExit(main())

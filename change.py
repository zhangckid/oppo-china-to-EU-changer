#!/usr/bin/env python3
"""Entry point for oppo china to EU changer."""
import sys

if __name__ == "__main__":
    if sys.platform != "linux":
        print("STOP: this version requires a Linux host (/proc, fcntl and Linux Platform Tools).", file=sys.stderr)
        raise SystemExit(2)
    if sys.version_info < (3, 11):
        print("STOP: Python 3.11 or newer is required.", file=sys.stderr)
        raise SystemExit(2)
    from changer.cli import main
    raise SystemExit(main())

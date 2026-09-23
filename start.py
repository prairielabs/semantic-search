#!/usr/bin/env python3
"""Start the connected app from any working directory."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'local-runtime'))
from server import main

if __name__ == '__main__':
    raise SystemExit(main())

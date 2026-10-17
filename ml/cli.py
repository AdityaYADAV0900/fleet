"""Offline ML CLI entrypoint (Phase 4)."""

import sys

from ml.train import main

if __name__ == "__main__":
    sys.exit(main() or 0)

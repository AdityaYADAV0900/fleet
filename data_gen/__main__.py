"""Package entry point for `python -m data_gen`."""

import sys

from data_gen.cli import main

if __name__ == "__main__":
    sys.exit(main())

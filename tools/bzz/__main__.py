"""Punto de entrada de ``python -m tools.bzz``."""

import sys

from tools.bzz.cli import main

if __name__ == "__main__":
    sys.exit(main())

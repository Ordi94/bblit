"""Punto de entrada de ``python -m tools.ghidra``."""

import sys

from tools.ghidra.cli import main

if __name__ == "__main__":
    sys.exit(main())

"""Permite ejecutar ``python -m tools.toolchain``."""

import sys

from tools.toolchain.cli import main

__all__ = ["main"]

if __name__ == "__main__":
    sys.exit(main())

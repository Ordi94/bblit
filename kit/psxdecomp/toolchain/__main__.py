"""Permite ejecutar ``python -m psxdecomp.toolchain``."""

import sys

from psxdecomp.toolchain.cli import main

__all__ = ["main"]

if __name__ == "__main__":
    sys.exit(main())

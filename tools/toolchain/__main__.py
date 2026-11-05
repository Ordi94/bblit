"""Permite ejecutar ``python -m tools.toolchain``: la orden del kit sobre la raiz de este repositorio."""

import sys

from psxdecomp.toolchain.cli import main

from tools.proyecto import RAIZ_REPOSITORIO

if __name__ == "__main__":
    sys.exit(main(raiz_por_omision=RAIZ_REPOSITORIO, prog=f"python -m {__package__}"))

"""Reexportacion de ``psxdecomp.toolchain.cli`` fijada a la raiz de este repositorio."""

from functools import partial
from pathlib import Path

from psxdecomp.toolchain import cli as _kit
from tools.toolchain.contexto import PROYECTO, RAIZ_REPOSITORIO

PROG = "python -m tools.toolchain"
RUTA_LOCK_RELATIVA = Path(PROYECTO.rutas.toolchain_lock)
RUTA_LOCAL_RELATIVA = Path(PROYECTO.rutas.local)

construir_parser = partial(_kit.construir_parser, prog=PROG)
main = partial(_kit.main, raiz_por_omision=RAIZ_REPOSITORIO, prog=PROG)

__all__ = [
    "PROG",
    "RAIZ_REPOSITORIO",
    "RUTA_LOCAL_RELATIVA",
    "RUTA_LOCK_RELATIVA",
    "construir_parser",
    "main",
]

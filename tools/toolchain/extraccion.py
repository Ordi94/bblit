"""Reexportacion de ``psxdecomp.toolchain.extraccion`` con el alias de variables del proyecto."""

from functools import partial

from psxdecomp.toolchain import extraccion as _kit
from psxdecomp.toolchain.extraccion import (
    MAX_BYTES_EXTRAIDOS,
    MAX_MIEMBROS,
    TIMEOUT_7ZIP_S,
    extraer,
    extraer_7z,
    extraer_archivo_simple,
    extraer_rar_iso,
    extraer_zip,
)
from tools.toolchain.contexto import PROYECTO, VARIABLES

localizar_7zip = partial(_kit.localizar_7zip, variables=VARIABLES, archivo_local=PROYECTO.rutas.local)

__all__ = [
    "MAX_BYTES_EXTRAIDOS",
    "MAX_MIEMBROS",
    "TIMEOUT_7ZIP_S",
    "extraer",
    "extraer_7z",
    "extraer_archivo_simple",
    "extraer_rar_iso",
    "extraer_zip",
    "localizar_7zip",
]

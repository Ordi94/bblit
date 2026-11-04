"""Seccion de progreso del README: reexportacion de ``psxdecomp.progreso.readme``.

El codigo vive en el kit. Este modulo conserva la ruta de importacion del repositorio y enlaza, con el
manifiesto de este proyecto (README, comando, variable del disco, macro y funcion de ejemplo), las
funciones que el kit recibe parametrizadas. La orden ``python tools/build.py progreso`` es del kit.
"""

from functools import partial

from psxdecomp.progreso import readme as _kit
from psxdecomp.progreso.readme import (
    HASH_DESCONOCIDO,
    MARCA_FIN,
    MARCA_INICIO,
    MAX_BYTES_README,
    ResumenJuego,
    obtener_hash_corto,
    resumir_juego,
)
from tools.toolchain.contexto import PROYECTO

RUTA_README = PROYECTO.rutas.readme

generar_seccion = partial(_kit.generar_seccion, proyecto=PROYECTO)
aplicar_seccion = partial(_kit.aplicar_seccion, etiqueta=RUTA_README)
actualizar_readme = partial(_kit.actualizar_readme, proyecto=PROYECTO)

__all__ = [
    "HASH_DESCONOCIDO",
    "MARCA_FIN",
    "MARCA_INICIO",
    "MAX_BYTES_README",
    "RUTA_README",
    "ResumenJuego",
    "actualizar_readme",
    "aplicar_seccion",
    "generar_seccion",
    "obtener_hash_corto",
    "resumir_juego",
]

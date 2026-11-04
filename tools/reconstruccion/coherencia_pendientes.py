"""Coherencia entre la linea de pendiente y la ultima medicion: reexportacion del kit.

El codigo vive en ``psxdecomp.diff.coherencia_pendientes``. Este modulo conserva la ruta de importacion
del repositorio y enlaza, con las rutas y convenciones del manifiesto de este proyecto, las funciones
que el kit recibe parametrizadas.
"""

from functools import partial

from psxdecomp.diff import coherencia_pendientes as _kit
from psxdecomp.diff.coherencia_pendientes import MAX_BYTES_RESULTADO
from tools.toolchain.contexto import PROYECTO

leer_puntuacion_medida = partial(_kit.leer_puntuacion_medida, rutas=PROYECTO.rutas)
avisos_puntuacion_pendiente = partial(
    _kit.avisos_puntuacion_pendiente, rutas=PROYECTO.rutas, convenciones=PROYECTO.convenciones
)

__all__ = [
    "MAX_BYTES_RESULTADO",
    "avisos_puntuacion_pendiente",
    "leer_puntuacion_medida",
]

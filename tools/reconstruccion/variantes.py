"""Banco de variantes: reexportacion de ``psxdecomp.diff.variantes``.

El codigo vive en el kit. Este modulo conserva la ruta de importacion del repositorio y enlaza, con las
rutas, convenciones, cadena de compilacion y ejecutable del manifiesto de este proyecto, la funcion que
el kit recibe parametrizada: el resto del repositorio la sigue llamando con la firma de siempre.
"""

from functools import partial

from psxdecomp.diff import variantes as _kit
from psxdecomp.diff.enlace_diff import TIMEOUT_ENLACE_S
from psxdecomp.diff.variantes import (
    MAX_BYTES_VARIANTE,
    MAX_CARACTERES_ERROR,
    MAX_VARIANTES,
    ResultadoVariante,
    formatear_tabla,
    listar_variantes,
    ordenar_resultados,
)
from tools.toolchain.contexto import PROYECTO

probar_variantes = partial(
    _kit.probar_variantes,
    rutas=PROYECTO.rutas,
    convenciones=PROYECTO.convenciones,
    compilacion=PROYECTO.compilacion,
    nombre_ejecutable=PROYECTO.identidad.ejecutable,
)

__all__ = [
    "MAX_BYTES_VARIANTE",
    "MAX_CARACTERES_ERROR",
    "MAX_VARIANTES",
    "TIMEOUT_ENLACE_S",
    "ResultadoVariante",
    "formatear_tabla",
    "listar_variantes",
    "ordenar_resultados",
    "probar_variantes",
]

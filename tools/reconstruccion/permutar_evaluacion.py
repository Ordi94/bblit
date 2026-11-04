"""Medicion de variantes del permutador: reexportacion de ``psxdecomp.permutador.evaluacion``.

El codigo vive en el kit. Este modulo conserva la ruta de importacion del repositorio y enlaza, con las
rutas, convenciones, cadena de compilacion y ejecutable del manifiesto de este proyecto, la funcion que
el kit recibe parametrizada.
"""

from functools import partial

from psxdecomp.permutador import evaluacion as _kit
from psxdecomp.permutador.evaluacion import (
    MAX_CARACTERES_MOTIVO,
    ObjetivoMedicion,
    ResultadoEvaluacion,
    evaluar,
    texto_del_archivo,
)
from tools.toolchain.contexto import PROYECTO

preparar_medicion = partial(
    _kit.preparar_medicion,
    rutas=PROYECTO.rutas,
    convenciones=PROYECTO.convenciones,
    compilacion=PROYECTO.compilacion,
    nombre_ejecutable=PROYECTO.identidad.ejecutable,
)

__all__ = [
    "MAX_CARACTERES_MOTIVO",
    "ObjetivoMedicion",
    "ResultadoEvaluacion",
    "evaluar",
    "preparar_medicion",
    "texto_del_archivo",
]

"""Analisis de los archivos C: reexportacion de ``psxdecomp.diff.fuentes_c``.

El codigo vive en el kit. Este modulo conserva la ruta de importacion del repositorio y enlaza,
con las convenciones y la carpeta de fuentes del manifiesto de este proyecto, las funciones que el
kit recibe parametrizadas: el resto del repositorio las sigue llamando con la firma de siempre.
"""

from functools import partial

from psxdecomp.diff.fuentes_c import (
    MAX_BYTES_FUENTE,
    MAX_CARACTERES_MOTIVO,
    BloqueNoCoincidente,
    EstadoFuncion,
    MarcaAsm,
)
from psxdecomp.diff.fuentes_c import analizar_fuente as _analizar_fuente
from psxdecomp.diff.fuentes_c import analizar_fuentes as _analizar_fuentes
from psxdecomp.diff.fuentes_c import bloques_no_coincidentes as _bloques_no_coincidentes
from psxdecomp.diff.fuentes_c import clasificar_include_asm as _clasificar_include_asm
from psxdecomp.diff.fuentes_c import motivos_no_coincidentes as _motivos_no_coincidentes
from psxdecomp.diff.fuentes_c import pendiente_declarada as _pendiente_declarada
from psxdecomp.diff.fuentes_c import puntuacion_pendiente as _puntuacion_pendiente
from psxdecomp.diff.fuentes_c import ubicar_funcion as _ubicar_funcion
from psxdecomp.diff.fuentes_c import verificar_pendientes as _verificar_pendientes
from tools.toolchain.contexto import PROYECTO

CONVENCIONES = PROYECTO.convenciones
MACRO_NO_COINCIDENTE = CONVENCIONES.macro_no_coincidente

analizar_fuente = partial(_analizar_fuente, convenciones=CONVENCIONES)
analizar_fuentes = partial(_analizar_fuentes, convenciones=CONVENCIONES)
bloques_no_coincidentes = partial(_bloques_no_coincidentes, convenciones=CONVENCIONES)
clasificar_include_asm = partial(_clasificar_include_asm, convenciones=CONVENCIONES)
motivos_no_coincidentes = partial(_motivos_no_coincidentes, convenciones=CONVENCIONES)
pendiente_declarada = partial(_pendiente_declarada, convenciones=CONVENCIONES)
puntuacion_pendiente = partial(_puntuacion_pendiente, convenciones=CONVENCIONES)
ubicar_funcion = partial(_ubicar_funcion, carpeta_fuentes=PROYECTO.rutas.fuentes)
verificar_pendientes = partial(_verificar_pendientes, convenciones=CONVENCIONES)

__all__ = [
    "CONVENCIONES",
    "MACRO_NO_COINCIDENTE",
    "MAX_BYTES_FUENTE",
    "MAX_CARACTERES_MOTIVO",
    "BloqueNoCoincidente",
    "EstadoFuncion",
    "MarcaAsm",
    "analizar_fuente",
    "analizar_fuentes",
    "bloques_no_coincidentes",
    "clasificar_include_asm",
    "motivos_no_coincidentes",
    "pendiente_declarada",
    "puntuacion_pendiente",
    "ubicar_funcion",
    "verificar_pendientes",
]

"""Comparacion de una funcion contra su objetivo: reexportacion de ``psxdecomp.diff.comparacion``.

El codigo vive en el kit. Este modulo conserva la ruta de importacion del repositorio y enlaza,
con las rutas, convenciones, cadena de compilacion y ejecutable del manifiesto de este proyecto,
las funciones que el kit recibe parametrizadas: el resto del repositorio las sigue llamando con la
firma de siempre.
"""

from functools import partial

from psxdecomp.diff import comparacion as _kit
from psxdecomp.diff.comparacion import (
    LIMITE_MINIMO_LINEAS,
    MARGEN_LINEAS,
    TIMEOUT_DIFF_S,
    FuncionSinCError,
    ResultadoDiff,
    comando_diff,
    contar_instrucciones,
    contar_retornos,
    envoltorio_objetivo,
    limite_lineas,
    puntuacion_desde_json,
    puntuar_objeto,
    salida_truncada,
    texto_diff_settings,
    validar_funcion,
)
from tools.toolchain.contexto import PROYECTO

RUTAS = PROYECTO.rutas
CONVENCIONES = PROYECTO.convenciones
COMPILACION = PROYECTO.compilacion
NOMBRE_EJECUTABLE = PROYECTO.identidad.ejecutable
CARPETA_ASM_COINCIDENTE = RUTAS.asm_coincidente
CARPETA_ASM_PENDIENTE = RUTAS.asm_pendiente

elegir_asm_objetivo = partial(_kit.elegir_asm_objetivo, rutas=RUTAS)
carpeta_de_trabajo = partial(_kit.carpeta_de_trabajo, rutas=RUTAS)
comparar_funcion = partial(
    _kit.comparar_funcion,
    rutas=RUTAS,
    convenciones=CONVENCIONES,
    compilacion=COMPILACION,
    nombre_ejecutable=NOMBRE_EJECUTABLE,
)
ruta_resultado = partial(_kit.ruta_resultado, rutas=RUTAS)
guardar_resultado = partial(_kit.guardar_resultado, rutas=RUTAS)
preparar_objetivo = partial(_kit.preparar_objetivo, rutas=RUTAS)

__all__ = [
    "CARPETA_ASM_COINCIDENTE",
    "CARPETA_ASM_PENDIENTE",
    "COMPILACION",
    "CONVENCIONES",
    "LIMITE_MINIMO_LINEAS",
    "MARGEN_LINEAS",
    "NOMBRE_EJECUTABLE",
    "RUTAS",
    "TIMEOUT_DIFF_S",
    "FuncionSinCError",
    "ResultadoDiff",
    "carpeta_de_trabajo",
    "comando_diff",
    "comparar_funcion",
    "contar_instrucciones",
    "contar_retornos",
    "elegir_asm_objetivo",
    "envoltorio_objetivo",
    "guardar_resultado",
    "limite_lineas",
    "preparar_objetivo",
    "puntuacion_desde_json",
    "puntuar_objeto",
    "ruta_resultado",
    "salida_truncada",
    "texto_diff_settings",
    "validar_funcion",
]

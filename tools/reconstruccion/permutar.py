"""Busqueda del permutador: reexportacion de ``psxdecomp.permutador.busqueda``.

El codigo vive en el kit. Este modulo conserva la ruta de importacion del repositorio y enlaza, con las
rutas, convenciones, cadena de compilacion y ejecutable del manifiesto de este proyecto, las funciones
que el kit recibe parametrizadas.
"""

from functools import partial

from psxdecomp.diff.fuentes_c import MAX_BYTES_FUENTE
from psxdecomp.permutador import busqueda as _kit
from psxdecomp.permutador.busqueda import (
    CANTIDADES_DE_MUTACIONES,
    INTENTOS_POR_VARIANTE,
    LIMITE_RONDAS_SIN_MEJORA,
    MAX_ITERACIONES,
    MAX_MINUTOS,
    MAX_PROCESOS,
    MINUTOS_POR_OMISION,
    PESOS_DE_CANTIDAD,
    RONDAS_POR_AVISO,
    RONDAS_VACIAS_MAXIMAS,
    SIN_LIMITE_DE_BYTES,
    Busqueda,
    Evaluador,
    Opciones,
    Resumen,
    formatear_resumen,
    validar_opciones,
)
from tools.toolchain.contexto import PROYECTO

leer_cabeceras = partial(_kit.leer_cabeceras, rutas=PROYECTO.rutas)
permutar_funcion = partial(
    _kit.permutar_funcion,
    rutas=PROYECTO.rutas,
    convenciones=PROYECTO.convenciones,
    compilacion=PROYECTO.compilacion,
    nombre_ejecutable=PROYECTO.identidad.ejecutable,
)

__all__ = [
    "CANTIDADES_DE_MUTACIONES",
    "INTENTOS_POR_VARIANTE",
    "LIMITE_RONDAS_SIN_MEJORA",
    "MAX_BYTES_FUENTE",
    "MAX_ITERACIONES",
    "MAX_MINUTOS",
    "MAX_PROCESOS",
    "MINUTOS_POR_OMISION",
    "PESOS_DE_CANTIDAD",
    "RONDAS_POR_AVISO",
    "RONDAS_VACIAS_MAXIMAS",
    "SIN_LIMITE_DE_BYTES",
    "Busqueda",
    "Evaluador",
    "Opciones",
    "Resumen",
    "formatear_resumen",
    "leer_cabeceras",
    "permutar_funcion",
    "validar_opciones",
]

"""Compilacion de los archivos C: reexportacion de ``psxdecomp.construccion.compilacion``.

El codigo vive en el kit. Este modulo conserva la ruta de importacion del repositorio y enlaza,
con las rutas y convenciones del manifiesto de este proyecto, las funciones que el kit recibe
parametrizadas: el resto del repositorio las sigue llamando con la firma de siempre.
"""

from __future__ import annotations

from functools import partial

from psxdecomp.construccion.compilacion import (
    PREFIJOS_DE_DATOS,
    TIMEOUT_COMPILAR_S,
    TIMEOUT_ENSAMBLAR_S,
    TIMEOUT_PREPROCESAR_S,
    HerramientasCompilacion,
    comando_preprocesar,
    comando_secciones,
    leer_secciones,
    resolver_herramientas_compilacion,
    rutas_intermedias,
)
from psxdecomp.construccion.compilacion import comando_compilar as _comando_compilar
from psxdecomp.construccion.compilacion import comando_maspsx as _comando_maspsx
from psxdecomp.construccion.compilacion import compilar_archivo as _compilar_archivo
from psxdecomp.construccion.compilacion import compilar_fuente as _compilar_fuente
from psxdecomp.construccion.compilacion import construir_mixto as _construir_mixto
from psxdecomp.construccion.compilacion import validar_fuente as _validar_fuente
from psxdecomp.construccion.compilacion import verificar_solo_texto as _verificar_solo_texto
from tools.toolchain.contexto import PROYECTO

RUTAS = PROYECTO.rutas
CONVENCIONES = PROYECTO.convenciones
COMPILACION = PROYECTO.compilacion
VERSION_ASPSX = COMPILACION.version_aspsx
OPCIONES_COMPILADOR = COMPILACION.opciones_compilador
CARPETA_INCLUDE = RUTAS.incluir
CARPETA_MACROS = RUTAS.macros
CARPETA_FUENTES = RUTAS.fuentes
CARPETA_SALIDA = RUTAS.build

comando_compilar = partial(_comando_compilar, max_valor_g=CONVENCIONES.max_valor_g, compilacion=COMPILACION)
comando_maspsx = partial(_comando_maspsx, max_valor_g=CONVENCIONES.max_valor_g, compilacion=COMPILACION)
compilar_archivo = partial(_compilar_archivo, rutas=RUTAS, convenciones=CONVENCIONES, compilacion=COMPILACION)
compilar_fuente = partial(_compilar_fuente, rutas=RUTAS, convenciones=CONVENCIONES, compilacion=COMPILACION)
construir_mixto = partial(_construir_mixto, rutas=RUTAS, convenciones=CONVENCIONES, compilacion=COMPILACION)
validar_fuente = partial(_validar_fuente, rutas=RUTAS)
verificar_solo_texto = partial(_verificar_solo_texto, rutas=RUTAS)


__all__ = [
    "CARPETA_FUENTES",
    "CARPETA_INCLUDE",
    "CARPETA_MACROS",
    "CARPETA_SALIDA",
    "COMPILACION",
    "CONVENCIONES",
    "OPCIONES_COMPILADOR",
    "PREFIJOS_DE_DATOS",
    "RUTAS",
    "TIMEOUT_COMPILAR_S",
    "TIMEOUT_ENSAMBLAR_S",
    "TIMEOUT_PREPROCESAR_S",
    "VERSION_ASPSX",
    "HerramientasCompilacion",
    "comando_compilar",
    "comando_maspsx",
    "comando_preprocesar",
    "comando_secciones",
    "compilar_archivo",
    "compilar_fuente",
    "construir_mixto",
    "leer_secciones",
    "resolver_herramientas_compilacion",
    "rutas_intermedias",
    "validar_fuente",
    "verificar_solo_texto",
]

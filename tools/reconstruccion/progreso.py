"""Medidor de progreso de la descompilacion: reexportacion de ``psxdecomp.progreso``.

El codigo vive en el kit (``calculo``, ``documento`` y ``medicion``). Este modulo conserva la ruta de
importacion del repositorio y enlaza, con el manifiesto de este proyecto (zonas de memoria, rutas,
convenciones y comando), las funciones que el kit recibe parametrizadas. Las constantes de zona y de
ruta se calculan una vez desde el manifiesto; la orden ``python tools/build.py progreso`` es del kit.
"""

from functools import partial

from psxdecomp.progreso import calculo as _calculo
from psxdecomp.progreso import documento as _documento
from psxdecomp.progreso import medicion as _medicion
from psxdecomp.progreso.calculo import (
    ArchivoProgreso,
    FuncionSimbolo,
    Progreso,
    ResumenZona,
    SubsistemaProgreso,
    combinar_simbolos,
)
from psxdecomp.progreso.documento import a_json
from tools.toolchain.contexto import PROYECTO

RUTAS = PROYECTO.rutas
CONVENCIONES = PROYECTO.convenciones
ZONAS = PROYECTO.zonas
COMANDO = PROYECTO.identidad.comando

INICIO_JUEGO = ZONAS.juego_desde
INICIO_LIBRERIAS = ZONAS.librerias_desde
FIN_LIBRERIAS = ZONAS.librerias_hasta
SIMBOLOS_ADICIONALES = RUTAS.simbolos_adicionales
DOCUMENTO_PROGRESO = RUTAS.documento_progreso
CARPETAS_ASM_AJENAS = (*RUTAS.asm_auxiliares, *RUTAS.subcarpetas_ajenas)

leer_simbolos = partial(_calculo.leer_simbolos, convenciones=CONVENCIONES)
zona_de = partial(_calculo.zona_de, zonas=ZONAS)
subsistema_de = partial(_calculo.subsistema_de, convenciones=CONVENCIONES)
calcular_progreso = partial(_calculo.calcular_progreso, zonas=ZONAS, subsistema=subsistema_de)
a_markdown = partial(_documento.a_markdown, comando=COMANDO, rutas=RUTAS, convenciones=CONVENCIONES)
contar_glabel = partial(_medicion.contar_glabel, rutas=RUTAS)
generar_progreso = partial(
    _medicion.generar_progreso, rutas=RUTAS, convenciones=CONVENCIONES, zonas=ZONAS, comando=COMANDO
)

__all__ = [
    "CARPETAS_ASM_AJENAS",
    "COMANDO",
    "CONVENCIONES",
    "DOCUMENTO_PROGRESO",
    "FIN_LIBRERIAS",
    "INICIO_JUEGO",
    "INICIO_LIBRERIAS",
    "RUTAS",
    "SIMBOLOS_ADICIONALES",
    "ZONAS",
    "ArchivoProgreso",
    "FuncionSimbolo",
    "Progreso",
    "ResumenZona",
    "SubsistemaProgreso",
    "a_json",
    "a_markdown",
    "calcular_progreso",
    "combinar_simbolos",
    "contar_glabel",
    "generar_progreso",
    "leer_simbolos",
    "subsistema_de",
    "zona_de",
]

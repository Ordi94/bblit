"""Compilacion de los archivos C: reexportacion de ``psxdecomp.construccion.compilacion``.

El codigo vive en el kit. Este modulo conserva la ruta de importacion del repositorio y enlaza,
con las rutas y convenciones del manifiesto de este proyecto, las funciones que el kit recibe
parametrizadas: el resto del repositorio las sigue llamando con la firma de siempre.

``construir_mixto`` se queda aqui porque orquesta la construccion completa con las funciones de
``infraestructura`` (enlace, ensamblado y lectura de opciones), que todavia no estan en el kit.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
from functools import partial
from pathlib import Path

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
from psxdecomp.construccion.compilacion import validar_fuente as _validar_fuente
from psxdecomp.construccion.compilacion import verificar_solo_texto as _verificar_solo_texto
from tools.reconstruccion.dominio import EjecutableReferencia
from tools.reconstruccion.infraestructura import (
    Ejecutor,
    Herramientas,
    construir_con_compilador,
    ejecutar_proceso,
    leer_valores_g,
)
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
validar_fuente = partial(_validar_fuente, rutas=RUTAS)
verificar_solo_texto = partial(_verificar_solo_texto, rutas=RUTAS)


def construir_mixto(
    raiz: Path,
    referencia: EjecutableReferencia,
    herramientas: Herramientas,
    obtener_compilacion: Callable[[], HerramientasCompilacion],
    ejecutar: Ejecutor = ejecutar_proceso,
    *,
    declaradas: Mapping[str, Collection[str]] | None = None,
) -> Path:
    """
    Construye el ejecutable con los archivos C compilados y el resto ensamblado.

    Contexto:
        Implementa ``build``. El script del enlazador que genera el particionador decide que
        objetos entran y en que orden; los ``src/*.c`` se compilan con ``compilar_fuente`` en la
        construccion normal (sin ``NON_MATCHING``) y exigiendo que solo aporten codigo. Las
        herramientas de compilacion se piden solo cuando aparece el primer archivo C, de modo
        que una construccion solo de ensamblador no necesita el SDK instalado.

    Args:
        raiz (Path): Raiz del repositorio.
        referencia (EjecutableReferencia): Hechos del ejecutable.
        herramientas (Herramientas): Ensamblador, enlazador y objcopy.
        obtener_compilacion (Callable[[], HerramientasCompilacion]): Resuelve las herramientas
            de compilacion; puede lanzar ``FileNotFoundError`` si no estan instaladas.
        ejecutar (Ejecutor, opcional): Ejecutor de procesos, sustituible en pruebas.
        declaradas (Mapping[str, Collection[str]], opcional): Secciones de datos que la particion
            declara por archivo (clave: nombre sin ``src/`` ni ``.c``), de ``secciones_declaradas``.

    Returns:
        Path: Ruta del ejecutable generado (``build/<nombre>``).

    Raises:
        FileNotFoundError: Si falta el script del enlazador, un fuente o una herramienta.
        ValueError: Si un objeto aporta datos o el cuerpo enlazado no mide ``t_size``.
        ProcesoError: Si una herramienta falla.

    Ejemplo:
        destino = construir_mixto(Path("."), referencia, herramientas, lambda: compilacion)
    """
    resueltas: list[HerramientasCompilacion] = []
    valores_g = leer_valores_g(raiz)

    def compilar(fuente: str, objeto: str) -> None:
        if not resueltas:
            resueltas.append(obtener_compilacion())
        permitidas = (declaradas or {}).get(Path(fuente).stem, ())
        compilar_fuente(
            raiz,
            fuente,
            objeto,
            resueltas[0],
            ejecutar,
            secciones_declaradas=permitidas,
            valor_g=valores_g.get(Path(fuente).stem, 0),
        )

    return construir_con_compilador(raiz, referencia, herramientas, compilar, ejecutar)


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

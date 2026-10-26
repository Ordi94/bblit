"""Interfaz de linea de comandos de ``python -m tools.ghidra``.

Subcomandos: ``analizar`` (importa y analiza), ``exportar`` (CSV y C de Ghidra), ``simbolos``
(genera ``config/symbols.txt``) e ``informe`` (cifras de cobertura). Los errores de uso o de
entrada se reportan en una linea, sin trazas ni rutas internas.
"""

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from tools.ghidra.depuracion import depurar_funciones
from tools.ghidra.dominio import calcular_informe, construir_simbolos
from tools.ghidra.ejecucion import (
    NOMBRE_EJECUTABLE,
    SEGUNDOS_MAXIMOS,
    VERSIONES_FIRMAS,
    ConfiguracionGhidra,
    Ejecutor,
    ejecutar_analisis,
    ejecutar_exportacion,
    ejecutar_proceso,
    resolver_ejecutable,
    resolver_instalacion,
)
from tools.ghidra.ejecutable import leer_segmento
from tools.ghidra.lectura import leer_funciones_csv
from tools.ghidra.simbolos import formatear_tabla, parsear_tabla

CARPETA_SCRIPTS = Path(__file__).resolve().parent / "scripts"


def construir_parser() -> argparse.ArgumentParser:
    """
    Define los subcomandos y sus argumentos.

    Contexto:
        Lo usa ``main``; separado para poder inspeccionar el parser sin ejecutar nada.

    Returns:
        argparse.ArgumentParser: Parser con los cuatro subcomandos.

    Ejemplo:
        argumentos = construir_parser().parse_args(["informe", "--funciones", "funciones.csv"])
    """
    parser = argparse.ArgumentParser(prog="python -m tools.ghidra", description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)

    analizar = sub.add_parser("analizar", help="importa el ejecutable y lo analiza con firmas de Psy-Q")
    analizar.add_argument("--exe", type=Path, help=f"ruta de {NOMBRE_EJECUTABLE} (o variable BBLIT_DISC)")
    analizar.add_argument("--proyecto", type=Path, required=True, help="carpeta del proyecto de Ghidra")
    analizar.add_argument("--ghidra", type=Path, help="instalacion de Ghidra (o variable BBLIT_GHIDRA)")
    analizar.add_argument("--semilla", type=Path, help="archivo con una direccion de funcion por linea")
    analizar.add_argument(
        "--versiones-firmas",
        default=",".join(VERSIONES_FIRMAS),
        help="versiones del SDK para pasadas de firmas adicionales, separadas por comas ('' para ninguna)",
    )
    analizar.add_argument("--segundos", type=int, default=SEGUNDOS_MAXIMOS, help="tiempo maximo del proceso")

    exportar = sub.add_parser("exportar", help="exporta funciones, cadenas, referencias y C de Ghidra")
    exportar.add_argument("--proyecto", type=Path, required=True, help="carpeta del proyecto de Ghidra")
    exportar.add_argument("--salida", type=Path, required=True, help="carpeta destino de la exportacion")
    exportar.add_argument("--ghidra", type=Path, help="instalacion de Ghidra (o variable BBLIT_GHIDRA)")
    exportar.add_argument("--programa", default=NOMBRE_EJECUTABLE, help="nombre del programa en el proyecto")
    exportar.add_argument("--sin-decompilar", action="store_true", help="omite los .c por funcion")
    exportar.add_argument("--segundos-por-funcion", type=int, default=60, help="limite del decompilador")
    exportar.add_argument("--segundos", type=int, default=SEGUNDOS_MAXIMOS, help="tiempo maximo del proceso")

    simbolos = sub.add_parser("simbolos", help="genera la tabla de simbolos a partir de funciones.csv")
    simbolos.add_argument("--funciones", type=Path, required=True, help="funciones.csv exportado")
    simbolos.add_argument("--salida", type=Path, required=True, help="archivo symbols.txt a escribir")
    simbolos.add_argument("--exe", type=Path, help=f"ruta de {NOMBRE_EJECUTABLE} (o variable BBLIT_DISC)")

    informe = sub.add_parser("informe", help="imprime conteos y cobertura de funciones.csv")
    informe.add_argument("--funciones", type=Path, required=True, help="funciones.csv exportado")
    informe.add_argument("--verificar", type=Path, help="symbols.txt a validar con el lector propio")
    return parser


def _configuracion(args: argparse.Namespace, entorno: Mapping[str, str]) -> ConfiguracionGhidra:
    """Reune las rutas de Ghidra de los argumentos y del entorno."""
    return ConfiguracionGhidra(
        instalacion=resolver_instalacion(args.ghidra, entorno),
        proyecto=args.proyecto,
        scripts=CARPETA_SCRIPTS,
    )


def _comando_analizar(args: argparse.Namespace, entorno: Mapping[str, str], ejecutor: Ejecutor) -> int:
    """Ejecuta el subcomando ``analizar``."""
    versiones = [v for v in args.versiones_firmas.split(",") if v]
    carga = ejecutar_analisis(
        _configuracion(args, entorno),
        resolver_ejecutable(args.exe, entorno),
        args.semilla,
        versiones,
        segundos=args.segundos,
        ejecutor=ejecutor,
    )
    print(f"analisis completo: base=0x{carga.base:08X} entrada=0x{carga.entrada:08X}")
    return 0


def _comando_exportar(args: argparse.Namespace, entorno: Mapping[str, str], ejecutor: Ejecutor) -> int:
    """Ejecuta el subcomando ``exportar``."""
    ejecutar_exportacion(
        _configuracion(args, entorno),
        args.programa,
        args.salida,
        decompilar=not args.sin_decompilar,
        segundos_por_funcion=args.segundos_por_funcion,
        segundos=args.segundos,
        ejecutor=ejecutor,
    )
    print("exportacion completa")
    return 0


def _comando_simbolos(args: argparse.Namespace, entorno: Mapping[str, str]) -> int:
    """Ejecuta el subcomando ``simbolos``."""
    segmento = leer_segmento(resolver_ejecutable(args.exe, entorno))
    depuracion = depurar_funciones(leer_funciones_csv(args.funciones), segmento)
    simbolos = construir_simbolos(depuracion.funciones)
    texto = formatear_tabla(simbolos)
    parsear_tabla(texto)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(texto, encoding="utf-8", newline="\n")
    print(
        f"{len(simbolos)} simbolos escritos "
        f"({len(depuracion.fusionadas)} fragmentos fusionados, {len(depuracion.descartadas)} descartados, "
        f"{len(depuracion.rescatadas)} huecos de codigo anadidos)"
    )
    return 0


def _comando_informe(args: argparse.Namespace) -> int:
    """Ejecuta el subcomando ``informe``."""
    informe = calcular_informe(leer_funciones_csv(args.funciones))
    print(f"funciones totales: {informe.total}")
    print(f"libreria identificada: {informe.libreria}")
    print(f"  con nombre oficial: {informe.libreria_oficial}")
    print(f"  rutinas internas de objeto: {informe.libreria_local}")
    print(f"  con candidatos alternos: {informe.ambiguas}")
    print(f"juego: {informe.juego}")
    print(f"cobertura del segmento: {informe.porcentaje_cubierto:.2f} % ({informe.bytes_cubiertos} bytes)")
    if args.verificar is not None:
        validos = parsear_tabla(args.verificar.read_text(encoding="utf-8"))
        print(f"symbols.txt valido: {len(validos)} simbolos")
    return 0


def main(
    argv: Sequence[str] | None = None,
    entorno: Mapping[str, str] | None = None,
    ejecutor: Ejecutor = ejecutar_proceso,
) -> int:
    """
    Punto de entrada de la herramienta.

    Contexto:
        Lo invoca ``python -m tools.ghidra``; las pruebas lo llaman con entorno y ejecutor
        propios para no depender de Ghidra ni de variables reales.

    Args:
        argv (Sequence[str] | None, opcional): Argumentos; por defecto los de ``sys.argv``.
        entorno (Mapping[str, str] | None, opcional): Variables de entorno; por defecto las reales.
        ejecutor (Ejecutor, opcional): Lanzador de procesos; por defecto ``ejecutar_proceso``.

    Returns:
        int: 0 si el comando termino bien, 2 si fallo por entrada invalida o error de Ghidra.

    Ejemplo:
        codigo = main(["informe", "--funciones", "funciones.csv"])
    """
    args = construir_parser().parse_args(argv)
    variables = os.environ if entorno is None else entorno
    try:
        if args.comando == "analizar":
            return _comando_analizar(args, variables, ejecutor)
        if args.comando == "exportar":
            return _comando_exportar(args, variables, ejecutor)
        if args.comando == "simbolos":
            return _comando_simbolos(args, variables)
        return _comando_informe(args)
    except (ValueError, TimeoutError) as error:
        print(f"error: {error}", file=sys.stderr)
    except OSError as error:
        print(f"error de entrada/salida: {type(error).__name__}", file=sys.stderr)
    return 2

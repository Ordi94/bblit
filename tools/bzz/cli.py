"""Interfaz de linea de comandos del paquete ``tools.bzz``.

Contexto:
    Capa mas externa: traduce argumentos a llamadas de la capa de lectura y errores a un
    mensaje breve con codigo de salida distinto de cero. Se invoca como
    ``python -m tools.bzz <orden> ...``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from tools.bzz.lectura import desempaquetar, generar_inventario

CODIGO_ERROR = 1
"""Codigo de salida cuando la orden no se pudo completar."""


def construir_parser() -> argparse.ArgumentParser:
    """Crea el analizador de argumentos con las ordenes disponibles.

    Contexto:
        Lo usa ``main``; se expone aparte para poder probar la definicion de las ordenes.

    Returns:
        argparse.ArgumentParser: Analizador con las ordenes ``desempaquetar`` e ``inventario``.

    Ejemplo:
        argumentos = construir_parser().parse_args(["inventario", "disc/fs", "salida.csv"])
    """
    parser = argparse.ArgumentParser(prog="python -m tools.bzz", description="Contenedores BZZ del juego.")
    ordenes = parser.add_subparsers(dest="orden", required=True)
    desempaquetado = ordenes.add_parser("desempaquetar", help="descomprime las secciones de un archivo .BZZ")
    desempaquetado.add_argument("archivo", type=Path, help="archivo .BZZ de origen")
    desempaquetado.add_argument("carpeta_destino", type=Path, help="carpeta donde escribir las secciones")
    inventario = ordenes.add_parser("inventario", help="genera un CSV con una fila por seccion")
    inventario.add_argument("carpeta_fs", type=Path, help="carpeta con los archivos .BZZ")
    inventario.add_argument("salida_csv", type=Path, help="archivo CSV de salida")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Ejecuta la orden indicada en la linea de comandos.

    Contexto:
        Punto de entrada de ``python -m tools.bzz``.

    Args:
        argv (Sequence[str], opcional): Argumentos sin el nombre del programa; por omision
            se toman de ``sys.argv``.

    Returns:
        int: 0 si la orden termino bien, ``CODIGO_ERROR`` si fallo la lectura, la escritura
        o la validacion del contenido.

    Raises:
        SystemExit: Si los argumentos no son validos (lo lanza ``argparse``).

    Ejemplo:
        codigo = main(["inventario", "disc/fs", "inventario.csv"])
    """
    argumentos = construir_parser().parse_args(argv)
    try:
        if argumentos.orden == "desempaquetar":
            manifiesto = desempaquetar(argumentos.archivo, argumentos.carpeta_destino)
            secciones = manifiesto["secciones"]
            total = len(secciones) if isinstance(secciones, list) else 0
            print(f"{total} secciones escritas")
        else:
            filas = generar_inventario(argumentos.carpeta_fs, argumentos.salida_csv)
            print(f"{filas} secciones inventariadas")
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return CODIGO_ERROR
    except OSError as error:
        print(f"error de entrada/salida: {error.strerror or type(error).__name__}", file=sys.stderr)
        return CODIGO_ERROR
    return 0

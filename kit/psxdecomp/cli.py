"""Linea de ordenes del kit: ``python -m psxdecomp.cli comprobar [ruta]``.

Capa de presentacion. Solo interpreta argumentos, imprime y devuelve el codigo de salida; la carga
y validacion del manifiesto son de ``lectura`` y ``dominio``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from psxdecomp.lectura import cargar_proyecto
from psxdecomp.validacion import ManifiestoError


def _construir_parser() -> argparse.ArgumentParser:
    """
    Declara los subcomandos de la linea de ordenes.

    Contexto:
        Separado de ``main`` para que sumar subcomandos no engorde el punto de entrada.

    Returns:
        argparse.ArgumentParser: Analizador con el subcomando ``comprobar``.

    Ejemplo:
        args = _construir_parser().parse_args(["comprobar", "."])
    """
    parser = argparse.ArgumentParser(prog="python -m psxdecomp.cli", description=__doc__)
    subcomandos = parser.add_subparsers(dest="orden")
    comprobar = subcomandos.add_parser("comprobar", help="valida el manifiesto e imprime el resumen")
    comprobar.add_argument("ruta", nargs="?", default=".", help="raiz del proyecto (por omision la actual)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    Punto de entrada de ``python -m psxdecomp.cli``.

    Contexto:
        Permite validar un manifiesto sin ejecutar ninguna otra herramienta del kit.

    Args:
        argv (Sequence[str], opcional): Argumentos; por omision ``sys.argv[1:]``.

    Returns:
        int: ``0`` si el manifiesto es valido, ``1`` si no lo es, ``2`` si falta el subcomando.

    Ejemplo:
        codigo = main(["comprobar", "."])
    """
    parser = _construir_parser()
    args = parser.parse_args(argv)
    if args.orden != "comprobar":
        parser.print_usage(sys.stderr)
        return 2
    try:
        proyecto = cargar_proyecto(Path(args.ruta))
    except ManifiestoError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(proyecto.resumen())
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Interfaz de linea de comandos de `tools.disco`.

Contexto:
    Capa de presentacion: traduce argumentos a llamadas de `tools.disco.imagen` y errores de
    validacion a mensajes breves y codigos de salida, sin volcar trazas ni rutas internas.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from tools.disco import imagen


def construir_parser() -> argparse.ArgumentParser:
    """
    Construye el analizador de argumentos con el subcomando `reempaquetar`.

    Contexto:
        Lo usa `main`; se expone para poder probar los argumentos por separado.

    Returns:
        argparse.ArgumentParser: Analizador listo para `parse_args`.

    Ejemplo:
        argumentos = construir_parser().parse_args(["reempaquetar", "--imagen", "a.bin", ...])
    """
    parser = argparse.ArgumentParser(prog="python -m tools.disco", description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)
    reempaquetar = sub.add_parser("reempaquetar", help="sustituye el ejecutable de la imagen")
    reempaquetar.add_argument("--imagen", type=Path, required=True, help="imagen .bin original")
    reempaquetar.add_argument("--exe", type=Path, required=True, help="ejecutable de reemplazo")
    reempaquetar.add_argument("--salida", type=Path, required=True, help="carpeta de salida")
    reempaquetar.add_argument("--archivo", default="SLUS_008.38", help="archivo a sustituir en el disco")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    Ejecuta el comando solicitado y devuelve el codigo de salida del proceso.

    Contexto:
        Punto de entrada de `python -m tools.disco`.

    Args:
        argv (Sequence[str], opcional): Argumentos; por defecto los de la linea de comandos.

    Returns:
        int: 0 si termino bien, 1 si una validacion o una operacion de archivo fallo.

    Ejemplo:
        codigo = main(["reempaquetar", "--imagen", "a.bin", "--exe", "x", "--salida", "build"])
    """
    argumentos = construir_parser().parse_args(argv)
    try:
        resultado = imagen.reempaquetar(
            argumentos.imagen, argumentos.exe, argumentos.salida, argumentos.archivo
        )
    except ValueError as error:
        print(f"error: {error}")
        return 1
    except OSError as error:
        print(f"error de entrada/salida: {type(error).__name__}")
        return 1
    print(
        f"{resultado.ruta_bin.name}: {resultado.sectores_modificados} de {resultado.sectores_totales} "
        f"sectores modificados, sha1={resultado.sha1}"
    )
    return 0

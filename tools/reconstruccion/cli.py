"""Interfaz de linea de comandos de la reconstruccion: ``python tools/build.py``."""

from __future__ import annotations

import argparse
import dataclasses
from collections.abc import Mapping, Sequence
from pathlib import Path

from psxdecomp.cli import construir_parser as construir_parser_del_kit
from psxdecomp.cli import describir_error_de_sistema, resumir_comparacion
from psxdecomp.cli import main as main_del_kit
from tools.reconstruccion import infraestructura as infra
from tools.reconstruccion.infraestructura import Ejecutor, ProcesoError
from tools.toolchain.contexto import PROYECTO, RAIZ_REPOSITORIO

ERRORES_PROPIOS = (ValueError, ProcesoError)
PROG = PROYECTO.identidad.comando

__all__ = [
    "ERRORES_PROPIOS",
    "PROG",
    "RAIZ_REPOSITORIO",
    "construir_parser",
    "describir_error_de_sistema",
    "main",
    "resumir_comparacion",
]


def construir_parser() -> argparse.ArgumentParser:
    """
    Construye el analizador de argumentos de la CLI del juego.

    Contexto:
        Es el analizador del kit con el manifiesto de este proyecto: las ordenes comunes (``split``,
        ``build``, ``verify``, ``clean``, ``diff``, ``probar``, ``permutar``, ``verificar-config`` y
        ``progreso``) mas las que declaren los plugins del manifiesto. Separado de ``main`` para
        probar la definicion de ordenes por si sola.

    Returns:
        argparse.ArgumentParser: Analizador con las ordenes de la linea de ordenes del juego.

    Ejemplo:
        args = construir_parser().parse_args(["clean"])
    """
    return construir_parser_del_kit(PROYECTO, prog=PROG, descripcion=__doc__)


def main(
    argv: Sequence[str] | None = None,
    entorno: Mapping[str, str] | None = None,
    raiz: Path = RAIZ_REPOSITORIO,
    ejecutar: Ejecutor = infra.ejecutar_proceso,
) -> int:
    """
    Punto de entrada de la CLI de reconstruccion.

    Contexto:
        Lo invoca ``tools/build.py``. Es la linea de ordenes del kit con el manifiesto de este proyecto:
        los errores esperados se imprimen en una linea sin traza ni rutas de la maquina y devuelven 1;
        ``verify`` y ``diff`` devuelven 1 tambien cuando las huellas o las funciones difieren.

    Args:
        argv (Sequence[str], opcional): Argumentos; por defecto ``sys.argv[1:]``.
        entorno (Mapping[str, str], opcional): Variables de entorno; por defecto ``os.environ``.
        raiz (Path, opcional): Raiz del repositorio (sustituible en pruebas).
        ejecutar (Ejecutor, opcional): Ejecutor de procesos (sustituible en pruebas).

    Returns:
        int: 0 si la orden termina bien, 1 en caso contrario.

    Ejemplo:
        codigo = main(["verify"])
    """
    return main_del_kit(
        argv,
        entorno,
        ejecutar,
        proyecto=dataclasses.replace(PROYECTO, raiz=raiz),
        prog=PROG,
        descripcion=__doc__,
    )

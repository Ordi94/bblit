"""Punto de entrada de la linea de ordenes del kit: ``python -m psxdecomp.cli <orden>``.

Capa de aplicacion. Carga el manifiesto, construye el analizador (con los subcomandos comunes y los de
los plugins), ejecuta la orden elegida y convierte los errores esperados en una linea sin traza ni
rutas de la maquina. Un proyecto consumidor reutiliza ``main`` pasando su propio ``Proyecto``.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from psxdecomp.cli.comandos import ORDENES_SIN_PROYECTO
from psxdecomp.cli.contexto import Contexto
from psxdecomp.cli.errores import ERRORES_PROPIOS, PluginInvalidoError, describir_error_de_sistema
from psxdecomp.cli.parser import DESCRIPCION_POR_OMISION, PROG_POR_OMISION, construir_parser
from psxdecomp.construccion.infraestructura import Ejecutor, ejecutar_proceso
from psxdecomp.dominio import Proyecto
from psxdecomp.lectura import cargar_proyecto
from psxdecomp.validacion import ManifiestoError


def _raiz_pedida(argumentos: Sequence[str]) -> str | None:
    """Lee ``--proyecto`` antes del analisis completo: el analizador depende del manifiesto."""
    previo = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    previo.add_argument("--proyecto")
    pedida: str | None = previo.parse_known_args(list(argumentos))[0].proyecto
    return pedida


def _cargar(argumentos: Sequence[str], raiz: Path | None) -> tuple[Proyecto | None, ManifiestoError | None]:
    """
    Carga el manifiesto de ``--proyecto``, de ``raiz`` o de la carpeta actual.

    Contexto:
        Un manifiesto invalido no impide mostrar la ayuda ni ejecutar ``comprobar``: el error se
        devuelve y solo lo lanzan las ordenes que necesitan el proyecto.

    Args:
        argumentos (Sequence[str]): Argumentos de la linea de ordenes.
        raiz (Path | None): Raiz por omision; si falta, la carpeta actual.

    Returns:
        tuple[Proyecto | None, ManifiestoError | None]: El proyecto, o el error de su carga.

    Ejemplo:
        proyecto, fallo = _cargar(["verify"], None)
    """
    pedida = _raiz_pedida(argumentos)
    try:
        return cargar_proyecto(Path(pedida) if pedida else (raiz or Path.cwd())), None
    except ManifiestoError as error:
        return None, error


def main(
    argv: Sequence[str] | None = None,
    entorno: Mapping[str, str] | None = None,
    ejecutar: Ejecutor = ejecutar_proceso,
    *,
    proyecto: Proyecto | None = None,
    raiz: Path | None = None,
    prog: str = PROG_POR_OMISION,
    descripcion: str | None = DESCRIPCION_POR_OMISION,
) -> int:
    """
    Punto de entrada de la linea de ordenes del kit.

    Contexto:
        Lo invoca ``python -m psxdecomp.cli`` (el proyecto sale de ``--proyecto``, de ``raiz`` o de la
        carpeta actual) y los proyectos consumidores que conservan su propia entrada y pasan su
        ``Proyecto``. Los errores esperados se imprimen en una linea y devuelven 1; ``verify`` y ``diff``
        devuelven 1 tambien cuando las huellas o las funciones difieren. Los errores de uso de
        argparse terminan con ``SystemExit(2)``.

    Args:
        argv (Sequence[str], opcional): Argumentos; por defecto ``sys.argv[1:]``.
        entorno (Mapping[str, str], opcional): Variables de entorno; por defecto ``os.environ``.
        ejecutar (Ejecutor, opcional): Ejecutor de procesos (sustituible en pruebas).
        proyecto (Proyecto, opcional): Proyecto ya cargado; sin el, la entrada es la propia del kit
            (acepta ``--proyecto`` y la orden ``comprobar``).
        raiz (Path, opcional): Raiz del proyecto si no se da ``--proyecto``; por omision la actual.
        prog (str, opcional): Nombre del programa en el uso.
        descripcion (str, opcional): Descripcion del programa en la ayuda.

    Returns:
        int: 0 si la orden termina bien, 1 si hay un error esperado o la verificacion falla.

    Ejemplo:
        codigo = main(["verify"])
    """
    argumentos = list(sys.argv[1:] if argv is None else argv)
    entrada_del_kit = proyecto is None
    fallo: ValueError | None = None
    if proyecto is None:
        proyecto, fallo = _cargar(argumentos, raiz)
    try:
        parser = construir_parser(
            proyecto, prog=prog, descripcion=descripcion, entrada_del_kit=entrada_del_kit
        )
    except PluginInvalidoError as error:
        fallo = error
        parser = construir_parser(
            proyecto, prog=prog, descripcion=descripcion, entrada_del_kit=entrada_del_kit, con_plugins=False
        )
    args = parser.parse_args(argumentos)
    variables = entorno if entorno is not None else os.environ
    try:
        if args.orden in ORDENES_SIN_PROYECTO:
            return int(args.manejador(args))
        if fallo is not None:
            raise fallo
        contexto = Contexto(
            proyecto=cast(Proyecto, proyecto), args=args, entorno=variables, ejecutar=ejecutar
        )
        return int(args.manejador(contexto))
    except ERRORES_PROPIOS as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"error: {describir_error_de_sistema(error)}", file=sys.stderr)
        return 1

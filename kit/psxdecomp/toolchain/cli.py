"""Interfaz de linea de comandos del toolchain: ``python -m psxdecomp.toolchain``."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from psxdecomp.dominio import Proyecto
from psxdecomp.lectura import cargar_proyecto
from psxdecomp.toolchain.configuracion import Rutas, leer_local_toml, resolver_rutas
from psxdecomp.toolchain.descarga import SesionHttp
from psxdecomp.toolchain.extraccion import localizar_7zip
from psxdecomp.toolchain.instalacion import (
    carpeta_componente,
    esta_instalado,
    instalar,
    leer_lock,
    resolver_herramienta,
)

PROG_POR_OMISION = "python -m psxdecomp.toolchain"


def construir_parser(prog: str = PROG_POR_OMISION) -> argparse.ArgumentParser:
    """
    Construye el analizador de argumentos de la CLI.

    Contexto:
        Separado de ``main`` para poder probar la definicion de subcomandos por si sola. El texto
        de ayuda no nombra ningun proyecto: los nombres concretos de variable y de archivo salen
        del manifiesto al ejecutar.

    Args:
        prog (str, opcional): Nombre del programa en el uso; por omision la entrada del kit.

    Returns:
        argparse.ArgumentParser: Analizador con los subcomandos ``instalar``, ``verificar``,
        ``listar`` y ``ruta``.

    Ejemplo:
        args = construir_parser().parse_args(["listar"])
    """
    parser = argparse.ArgumentParser(prog=prog, description=__doc__)
    parser.add_argument(
        "--proyecto", help="raiz del proyecto con su manifiesto (por omision la del consumidor o la actual)"
    )
    parser.add_argument(
        "--toolchain",
        help="carpeta de instalacion (por defecto la variable TOOLCHAIN del entorno, su alias, "
        "el archivo local de rutas o ./toolchain)",
    )
    parser.add_argument(
        "--lock", help="archivo de bloqueo (por defecto la ruta toolchain_lock del manifiesto)"
    )
    sub = parser.add_subparsers(dest="orden", required=True)
    instalar_p = sub.add_parser("instalar", help="descarga e instala los componentes verificando SHA-256")
    instalar_p.add_argument(
        "--solo", action="append", metavar="COMPONENTE", help="instala solo ese componente"
    )
    sub.add_parser("verificar", help="comprueba que los componentes estan instalados y vigentes")
    sub.add_parser("listar", help="muestra los componentes del lock")
    ruta_p = sub.add_parser("ruta", help="imprime la ruta de una herramienta instalada")
    ruta_p.add_argument("componente")
    ruta_p.add_argument("alias")
    return parser


def _contexto(args: argparse.Namespace, entorno: Mapping[str, str], proyecto: Proyecto) -> tuple[Rutas, Path]:
    """Resuelve rutas y archivo de bloqueo con las rutas y el alias de variables del manifiesto."""
    local = leer_local_toml(proyecto.ruta_absoluta(proyecto.rutas.local), proyecto.rutas.local)
    rutas = resolver_rutas(
        proyecto.raiz, entorno, local, toolchain=args.toolchain, variables=proyecto.variables()
    )
    lock = Path(args.lock) if args.lock else proyecto.ruta_absoluta(proyecto.rutas.toolchain_lock)
    return rutas, lock


def main(
    argv: Sequence[str] | None = None,
    entorno: Mapping[str, str] | None = None,
    sesion: SesionHttp | None = None,
    *,
    raiz_por_omision: Path | None = None,
    prog: str = PROG_POR_OMISION,
) -> int:
    """
    Punto de entrada de la CLI del toolchain.

    Contexto:
        Lo invoca ``python -m psxdecomp.toolchain`` mediante ``__main__`` y los proyectos
        consumidores que conservan su propia entrada. La raiz del proyecto es ``--proyecto``, o
        ``raiz_por_omision``, o la carpeta actual. Los errores de validacion (incluido el manifiesto)
        se imprimen en una linea sin traza y devuelven codigo 1.

    Args:
        argv (Sequence[str], opcional): Argumentos; por defecto ``sys.argv[1:]``.
        entorno (Mapping[str, str], opcional): Variables de entorno; por defecto ``os.environ``.
        sesion (SesionHttp, opcional): Sesion HTTP para las descargas (sustituible en pruebas).
        raiz_por_omision (Path, opcional): Raiz del proyecto si no se da ``--proyecto``; por omision
            la carpeta actual.
        prog (str, opcional): Nombre del programa que se muestra en el uso.

    Returns:
        int: 0 si la orden termina bien, 1 si hay un error controlado.

    Ejemplo:
        codigo = main(["listar"])
    """
    args = construir_parser(prog).parse_args(argv)
    entorno = entorno if entorno is not None else os.environ
    try:
        raiz = Path(args.proyecto) if args.proyecto else (raiz_por_omision or Path.cwd())
        proyecto = cargar_proyecto(raiz)
        rutas, ruta_lock = _contexto(args, entorno, proyecto)
        lock = leer_lock(ruta_lock)
        if args.orden == "listar":
            for componente in lock.values():
                print(f"{componente.nombre}\t{componente.sha256}\t{componente.fecha_registro}")
            return 0
        if args.orden == "ruta":
            print(
                resolver_herramienta(lock, rutas.toolchain, args.componente, args.alias, proyecto.variables())
            )
            return 0
        if args.orden == "verificar":
            ausentes = [
                nombre
                for nombre, comp in lock.items()
                if not esta_instalado(comp, carpeta_componente(rutas.toolchain, comp))
            ]
            for nombre in lock:
                print(f"{nombre}\t{'FALTA' if nombre in ausentes else 'OK'}")
            return 1 if ausentes else 0
        siete_zip = _buscar_7zip(rutas, entorno, proyecto)
        estados = instalar(lock, rutas.toolchain, args.solo, sesion, siete_zip)
        for nombre, estado in estados.items():
            print(f"{nombre}\t{estado}")
        return 0
    except (ValueError, FileNotFoundError, ConnectionError, TimeoutError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def _buscar_7zip(rutas: Rutas, entorno: Mapping[str, str], proyecto: Proyecto) -> Path | None:
    """Localiza 7-Zip; si no esta devuelve ``None`` y los formatos que lo requieren fallaran con aviso."""
    try:
        return localizar_7zip(rutas.siete_zip, entorno, proyecto.variables(), proyecto.rutas.local)
    except FileNotFoundError:
        return None

"""Interfaz de linea de comandos del toolchain: ``python -m tools.toolchain``."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from tools.toolchain.configuracion import Rutas, leer_local_toml, resolver_rutas
from tools.toolchain.descarga import SesionHttp
from tools.toolchain.extraccion import localizar_7zip
from tools.toolchain.instalacion import (
    carpeta_componente,
    esta_instalado,
    instalar,
    leer_lock,
    resolver_herramienta,
)

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
RUTA_LOCK_RELATIVA = Path("config") / "toolchain.lock.json"
RUTA_LOCAL_RELATIVA = Path("config") / "local.toml"


def construir_parser() -> argparse.ArgumentParser:
    """
    Construye el analizador de argumentos de la CLI.

    Contexto:
        Separado de ``main`` para poder probar la definicion de subcomandos por si sola.

    Returns:
        argparse.ArgumentParser: Analizador con los subcomandos ``instalar``, ``verificar``,
        ``listar`` y ``ruta``.

    Ejemplo:
        args = construir_parser().parse_args(["listar"])
    """
    parser = argparse.ArgumentParser(prog="python -m tools.toolchain", description=__doc__)
    parser.add_argument(
        "--toolchain", help="carpeta de instalacion (por defecto BBLIT_TOOLCHAIN o ./toolchain)"
    )
    parser.add_argument("--lock", help="archivo de bloqueo (por defecto config/toolchain.lock.json)")
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


def _contexto(args: argparse.Namespace, entorno: Mapping[str, str]) -> tuple[Rutas, Path]:
    """Resuelve rutas y archivo de bloqueo a partir de argumentos y configuracion local."""
    local = leer_local_toml(RAIZ_REPOSITORIO / RUTA_LOCAL_RELATIVA)
    rutas = resolver_rutas(RAIZ_REPOSITORIO, entorno, local, toolchain=args.toolchain)
    lock = Path(args.lock) if args.lock else RAIZ_REPOSITORIO / RUTA_LOCK_RELATIVA
    return rutas, lock


def main(
    argv: Sequence[str] | None = None,
    entorno: Mapping[str, str] | None = None,
    sesion: SesionHttp | None = None,
) -> int:
    """
    Punto de entrada de la CLI del toolchain.

    Contexto:
        Lo invoca ``python -m tools.toolchain`` mediante ``__main__``. Los errores de
        validacion se imprimen en una linea sin traza y devuelven codigo 1.

    Args:
        argv (Sequence[str], opcional): Argumentos; por defecto ``sys.argv[1:]``.
        entorno (Mapping[str, str], opcional): Variables de entorno; por defecto ``os.environ``.
        sesion (SesionHttp, opcional): Sesion HTTP para las descargas (sustituible en pruebas).

    Returns:
        int: 0 si la orden termina bien, 1 si hay un error controlado.

    Ejemplo:
        codigo = main(["listar"])
    """
    args = construir_parser().parse_args(argv)
    entorno = entorno if entorno is not None else os.environ
    try:
        rutas, ruta_lock = _contexto(args, entorno)
        lock = leer_lock(ruta_lock)
        if args.orden == "listar":
            for componente in lock.values():
                print(f"{componente.nombre}\t{componente.sha256}\t{componente.fecha_registro}")
            return 0
        if args.orden == "ruta":
            print(resolver_herramienta(lock, rutas.toolchain, args.componente, args.alias))
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
        siete_zip = _buscar_7zip(rutas, entorno)
        estados = instalar(lock, rutas.toolchain, args.solo, sesion, siete_zip)
        for nombre, estado in estados.items():
            print(f"{nombre}\t{estado}")
        return 0
    except (ValueError, FileNotFoundError, ConnectionError, TimeoutError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def _buscar_7zip(rutas: Rutas, entorno: Mapping[str, str]) -> Path | None:
    """Localiza 7-Zip; si no esta devuelve ``None`` y los formatos que lo requieren fallaran con aviso."""
    try:
        return localizar_7zip(rutas.siete_zip, entorno)
    except FileNotFoundError:
        return None

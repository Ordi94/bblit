"""Interfaz de linea de comandos de la reconstruccion: ``python tools/build.py``."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from tools.reconstruccion import infraestructura as infra
from tools.reconstruccion.infraestructura import Ejecutor, ProcesoError
from tools.toolchain.configuracion import leer_local_toml, resolver_rutas
from tools.toolchain.instalacion import leer_lock

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
RUTA_REFERENCIA = Path("config") / "ejecutable.json"
RUTA_LOCK = Path("config") / "toolchain.lock.json"
RUTA_LOCAL = Path("config") / "local.toml"
ERRORES_CONTROLADOS = (ValueError, FileNotFoundError, ProcesoError, OSError)


def construir_parser() -> argparse.ArgumentParser:
    """
    Construye el analizador de argumentos de la CLI.

    Contexto:
        Separado de ``main`` para probar la definicion de ordenes por si sola.

    Returns:
        argparse.ArgumentParser: Analizador con las ordenes ``split``, ``build``, ``verify``
        y ``clean``.

    Ejemplo:
        args = construir_parser().parse_args(["clean"])
    """
    parser = argparse.ArgumentParser(prog="python tools/build.py", description=__doc__)
    parser.add_argument("--disc", help="carpeta del disco (por defecto BBLIT_DISC o config/local.toml)")
    parser.add_argument(
        "--toolchain", help="carpeta del toolchain (por defecto BBLIT_TOOLCHAIN o ./toolchain)"
    )
    sub = parser.add_subparsers(dest="orden", required=True)
    sub.add_parser("split", help="particiona el ejecutable con splat (genera asm/ y el script del enlazador)")
    sub.add_parser("build", help="ensambla, enlaza y genera build/<ejecutable> con su cabecera")
    sub.add_parser("verify", help="compara el ejecutable reconstruido con el original por SHA-256")
    sub.add_parser("clean", help="elimina asm/, expected/ y los artefactos generados en build/")
    return parser


def main(
    argv: Sequence[str] | None = None,
    entorno: Mapping[str, str] | None = None,
    raiz: Path = RAIZ_REPOSITORIO,
    ejecutar: Ejecutor = infra.ejecutar_proceso,
) -> int:
    """
    Punto de entrada de la CLI de reconstruccion.

    Contexto:
        Lo invoca ``tools/build.py``. Los errores esperados se imprimen en una linea sin
        traza y devuelven 1; ``verify`` devuelve 1 tambien cuando las huellas difieren.

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
    args = construir_parser().parse_args(argv)
    variables = entorno if entorno is not None else os.environ
    try:
        referencia = infra.leer_referencia(raiz / RUTA_REFERENCIA)
        if args.orden == "clean":
            eliminadas = infra.limpiar(raiz, referencia.nombre)
            print("eliminado: " + (", ".join(eliminadas) if eliminadas else "nada que eliminar"))
            return 0
        rutas = resolver_rutas(raiz, variables, leer_local_toml(raiz / RUTA_LOCAL), args.disc, args.toolchain)
        if args.orden == "verify":
            coincide, mensaje = infra.verificar(
                raiz, infra.obtener_original(raiz, rutas.disc, referencia), referencia
            )
            print(mensaje)
            return 0 if coincide else 1
        herramientas = infra.resolver_herramientas(
            leer_lock(raiz / RUTA_LOCK), rutas.toolchain, sys.executable
        )
        if args.orden == "split":
            infra.dividir(
                raiz, infra.obtener_original(raiz, rutas.disc, referencia), referencia, herramientas, ejecutar
            )
            print("split completado: asm/ y script del enlazador generados")
            return 0
        destino = infra.construir(raiz, referencia, herramientas, ejecutar)
        print(
            f"build completado: {destino.relative_to(raiz).as_posix()} sha256={infra.sha256_archivo(destino)}"
        )
        return 0
    except ERRORES_CONTROLADOS as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

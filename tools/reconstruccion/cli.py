"""Interfaz de linea de comandos de la reconstruccion: ``python tools/build.py``."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from tools.reconstruccion import compilacion, diff, progreso
from tools.reconstruccion import infraestructura as infra
from tools.reconstruccion.dominio import EjecutableReferencia
from tools.reconstruccion.infraestructura import Ejecutor, ProcesoError
from tools.toolchain.configuracion import Rutas, leer_local_toml, resolver_rutas
from tools.toolchain.instalacion import leer_lock, resolver_herramienta

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
        argparse.ArgumentParser: Analizador con las ordenes ``split``, ``build``, ``verify``,
        ``clean``, ``diff`` y ``progreso``.

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
    sub.add_parser("build", help="compila los src/*.c, ensambla el resto, enlaza y genera build/<ejecutable>")
    sub.add_parser("verify", help="compara el ejecutable reconstruido con el original por SHA-256")
    sub.add_parser("clean", help="elimina asm/, expected/ y los artefactos generados en build/")
    comparar = sub.add_parser("diff", help="compara una funcion compilada desde C con su original")
    comparar.add_argument("funcion", help="nombre de la funcion (por ejemplo func_80036204)")
    sub.add_parser("progreso", help="mide la descompilacion y escribe docs/PROGRESO.md y build/progreso.json")
    return parser


def _ejecutar_clean(raiz: Path, referencia: EjecutableReferencia) -> int:
    """Implementa ``clean``."""
    eliminadas = infra.limpiar(raiz, referencia.nombre)
    print("eliminado: " + (", ".join(eliminadas) if eliminadas else "nada que eliminar"))
    return 0


def _ejecutar_progreso(raiz: Path) -> int:
    """Implementa ``progreso``; devuelve 1 si el ensamblador y el codigo C no cuadran con la tabla."""
    medido = progreso.generar_progreso(raiz)
    print(
        f"progreso: {medido.c_juego.funciones} funciones del juego en C de {medido.juego.funciones} "
        f"({medido.c_juego.bytes} de {medido.juego.bytes} bytes, {medido.porcentaje_bytes_juego:.2f} %); "
        f"{len(medido.no_coincidentes)} NON_MATCHING; docs/PROGRESO.md y build/progreso.json escritos"
    )
    if medido.coherente is False:
        print(
            f"error: {medido.glabel_en_asm} glabel en asm/ + {medido.funciones_en_c} funciones en C no "
            f"suman las {medido.funciones_totales} de la tabla de simbolos: ejecute 'split'",
            file=sys.stderr,
        )
        return 1
    return 0


def _ejecutar_comparacion(raiz: Path, rutas: Rutas, funcion: str, python: str, ejecutar: Ejecutor) -> int:
    """Implementa ``diff``; devuelve 0 solo si la puntuacion es cero."""
    lock = leer_lock(raiz / RUTA_LOCK)
    herramientas = compilacion.resolver_herramientas_compilacion(lock, rutas.toolchain, python)
    script = resolver_herramienta(lock, rutas.toolchain, "asm-differ", "diff")
    resultado = diff.comparar_funcion(raiz, funcion, herramientas, script, ejecutar)
    print(resultado.texto)
    print(f"{resultado.funcion} ({resultado.archivo}): puntuacion {resultado.puntuacion}")
    return 0 if resultado.coincide else 1


def _ejecutar_construccion(
    raiz: Path, rutas: Rutas, referencia: EjecutableReferencia, orden: str, ejecutar: Ejecutor
) -> int:
    """Implementa ``split`` y ``build``."""
    original = infra.obtener_original(raiz, rutas.disc, referencia) if orden == "split" else None
    lock = leer_lock(raiz / RUTA_LOCK)
    herramientas = infra.resolver_herramientas(lock, rutas.toolchain, sys.executable)
    if original is not None:
        infra.dividir(raiz, original, referencia, herramientas, ejecutar)
        print("split completado: asm/ y script del enlazador generados")
        return 0
    destino = compilacion.construir_mixto(
        raiz,
        referencia,
        herramientas,
        lambda: compilacion.resolver_herramientas_compilacion(lock, rutas.toolchain, sys.executable),
        ejecutar,
    )
    print(f"build completado: {destino.relative_to(raiz).as_posix()} sha256={infra.sha256_archivo(destino)}")
    return 0


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
        traza y devuelven 1; ``verify`` y ``diff`` devuelven 1 tambien cuando las huellas o las
        funciones difieren.

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
        if args.orden == "progreso":
            return _ejecutar_progreso(raiz)
        referencia = infra.leer_referencia(raiz / RUTA_REFERENCIA)
        if args.orden == "clean":
            return _ejecutar_clean(raiz, referencia)
        rutas = resolver_rutas(raiz, variables, leer_local_toml(raiz / RUTA_LOCAL), args.disc, args.toolchain)
        if args.orden == "diff":
            return _ejecutar_comparacion(raiz, rutas, args.funcion, sys.executable, ejecutar)
        if args.orden == "verify":
            coincide, mensaje = infra.verificar(
                raiz, infra.obtener_original(raiz, rutas.disc, referencia), referencia
            )
            print(mensaje)
            return 0 if coincide else 1
        return _ejecutar_construccion(raiz, rutas, referencia, args.orden, ejecutar)
    except ERRORES_CONTROLADOS as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

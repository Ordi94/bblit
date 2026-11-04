"""Analizador de argumentos de la linea de ordenes del kit.

Capa de presentacion. Declara los subcomandos comunes y fija, con ``set_defaults``, la funcion que
ejecuta cada uno (``manejador``). Los textos de ayuda nombran las rutas y las variables de entorno
del manifiesto del proyecto, nunca valores propios de un juego: sin manifiesto se usan los valores
por omision del kit.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from psxdecomp.cli import comandos, orden_progreso, plugins
from psxdecomp.dominio import Proyecto, construir_convenciones, construir_rutas
from psxdecomp.entorno import SUFIJO_DISCO, SUFIJO_TOOLCHAIN, Variables

PROG_POR_OMISION = "python -m psxdecomp.cli"
DESCRIPCION_POR_OMISION = "Linea de ordenes del kit de descompilacion: dividir, construir, verificar y medir."


def construir_parser(
    proyecto: Proyecto | None,
    *,
    prog: str = PROG_POR_OMISION,
    descripcion: str | None = DESCRIPCION_POR_OMISION,
    entrada_del_kit: bool = False,
    con_plugins: bool = True,
) -> argparse.ArgumentParser:
    """
    Construye el analizador con los subcomandos comunes y los de los plugins del manifiesto.

    Contexto:
        Separado de ``main`` para probar la definicion de ordenes por si sola. Las rutas y los
        nombres de variable que aparecen en la ayuda salen de ``proyecto``; si es ``None`` (no hay
        manifiesto cargable) se usan los valores por omision del kit.

    Args:
        proyecto (Proyecto | None): Manifiesto cargado, o ``None`` si no se pudo cargar.
        prog (str, opcional): Nombre del programa en el uso.
        descripcion (str | None, opcional): Descripcion del programa.
        entrada_del_kit (bool, opcional): Si es verdadero (``python -m psxdecomp.cli``), anade ``--proyecto``
            y la orden ``comprobar``; la linea de ordenes de un proyecto, que ya conoce su manifiesto, no
            las necesita.
        con_plugins (bool, opcional): Si es falso, no registra los subcomandos de los plugins.

    Returns:
        argparse.ArgumentParser: Analizador con ``split``, ``build``, ``verify``, ``clean``, ``diff``,
        ``probar``, ``permutar``, ``verificar-config``, ``progreso``, ``comprobar`` y los de los plugins.

    Raises:
        PluginInvalidoError: Si un plugin de subcomandos no se puede cargar o rompe el contrato.

    Ejemplo:
        args = construir_parser(proyecto).parse_args(["clean"])
    """
    rutas = proyecto.rutas if proyecto else construir_rutas({})
    variables = proyecto.variables() if proyecto else Variables()
    macro = (proyecto.convenciones if proyecto else construir_convenciones({})).macro_no_coincidente
    parser = argparse.ArgumentParser(prog=prog, description=descripcion)
    if entrada_del_kit:
        parser.add_argument("--proyecto", help="raiz del proyecto con su manifiesto (por omision la actual)")
    parser.add_argument(
        "--disc",
        help=f"carpeta del disco (por defecto {variables.describir(SUFIJO_DISCO)} o {rutas.local})",
    )
    parser.add_argument(
        "--toolchain",
        help=f"carpeta del toolchain (por defecto {variables.describir(SUFIJO_TOOLCHAIN)} o ./toolchain)",
    )
    sub = parser.add_subparsers(dest="orden", required=True)
    sub.add_parser(
        "split", help=f"particiona el ejecutable con splat (genera {rutas.asm}/ y el script del enlazador)"
    ).set_defaults(manejador=comandos.ejecutar_split)
    sub.add_parser(
        "build",
        help=(
            f"compila los {rutas.fuentes}/*.c, ensambla el resto, enlaza y genera {rutas.build}/<ejecutable>"
        ),
    ).set_defaults(manejador=comandos.ejecutar_build)
    sub.add_parser(
        "verify", help="compara el ejecutable reconstruido con el original por SHA-256"
    ).set_defaults(manejador=comandos.ejecutar_verify)
    sub.add_parser(
        "clean",
        help=f"elimina {rutas.asm}/, {rutas.expected}/ y los artefactos generados en {rutas.build}/",
    ).set_defaults(manejador=comandos.ejecutar_clean)
    comparar = sub.add_parser("diff", help="compara una funcion compilada desde C con su original")
    comparar.add_argument("funcion", help="nombre de la funcion")
    comparar.set_defaults(manejador=comandos.ejecutar_diff)
    ensayar = sub.add_parser(
        "probar", help="compara con el original cada variante .c de una carpeta y ordena por puntuacion"
    )
    ensayar.add_argument("funcion", help="nombre de la funcion")
    ensayar.add_argument(
        "carpeta", type=Path, help="carpeta con una variante completa de la funcion por archivo .c"
    )
    ensayar.set_defaults(manejador=comandos.ejecutar_probar)
    buscar = sub.add_parser(
        "permutar",
        help=(
            f"busca con mutaciones la forma de C que hace coincidir una funcion {macro} "
            f"(no toca {rutas.fuentes}/)"
        ),
    )
    buscar.add_argument("funcion", help="nombre de la funcion")
    buscar.add_argument("--iteraciones", type=int, help="variantes a medir como maximo")
    buscar.add_argument("--minutos", type=float, help="duracion maxima de la sesion en minutos")
    buscar.add_argument("--procesos", type=int, default=1, help="mediciones simultaneas (por omision 1)")
    buscar.add_argument("--semilla", type=int, help="semilla aleatoria (por omision, una nueva)")
    buscar.add_argument(
        "--reanudar",
        action="store_true",
        help=f"continua la busqueda guardada en {rutas.build}/permutar/<funcion>/",
    )
    buscar.set_defaults(manejador=comandos.ejecutar_permutar)
    sub.add_parser(
        "verificar-config",
        help=f"falla si una clave de [datos_pequenos] ya esta declarada en {', '.join(rutas.simbolos)}",
    ).set_defaults(manejador=comandos.ejecutar_verificar_config)
    medir = sub.add_parser(
        "progreso",
        help=(
            f"mide la descompilacion y escribe {rutas.documento_progreso}, {rutas.build}/progreso.json "
            f"y la seccion de {rutas.readme}"
        ),
    )
    medir.add_argument(
        "--sin-readme", action="store_true", help=f"no actualiza la seccion de progreso de {rutas.readme}"
    )
    medir.set_defaults(manejador=orden_progreso.ejecutar_progreso)
    if entrada_del_kit:
        comprobar = sub.add_parser("comprobar", help="valida el manifiesto e imprime el resumen")
        comprobar.add_argument(
            "ruta", nargs="?", default=".", help="raiz del proyecto (por omision la actual)"
        )
        comprobar.set_defaults(manejador=comandos.ejecutar_comprobar)
    if proyecto is not None and con_plugins:
        plugins.registrar_subcomandos(sub, proyecto)
    return parser

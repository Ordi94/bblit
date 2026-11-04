"""Interfaz de linea de comandos de la reconstruccion: ``python tools/build.py``."""

from __future__ import annotations

import argparse
import dataclasses
import sys
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

from psxdecomp.cli import Contexto, describir_error_de_sistema, motivo_sin_rutas, resumir_comparacion
from psxdecomp.cli import construir_parser as construir_parser_del_kit
from psxdecomp.cli import main as main_del_kit
from psxdecomp.dominio import Proyecto
from tools.reconstruccion import coherencia_pendientes, progreso, readme_progreso
from tools.reconstruccion import infraestructura as infra
from tools.reconstruccion.infraestructura import Ejecutor, ProcesoError, listar_fuentes_c
from tools.toolchain.contexto import PROYECTO, RAIZ_REPOSITORIO

ERRORES_PROPIOS = (ValueError, ProcesoError)
PROG = "python tools/build.py"

__all__ = [
    "ERRORES_PROPIOS",
    "PROG",
    "RAIZ_REPOSITORIO",
    "construir_parser",
    "describir_error_de_sistema",
    "main",
    "registrar_progreso",
    "resumir_comparacion",
]


def construir_parser() -> argparse.ArgumentParser:
    """
    Construye el analizador de argumentos de la CLI del juego.

    Contexto:
        Es el analizador del kit con el manifiesto de este proyecto: las ordenes comunes (``split``,
        ``build``, ``verify``, ``clean``, ``diff``, ``probar``, ``permutar`` y ``verificar-config``) mas
        las que declaran los plugins del manifiesto, entre ellas ``progreso``. Separado de ``main``
        para probar la definicion de ordenes por si sola.

    Returns:
        argparse.ArgumentParser: Analizador con las ordenes de la linea de ordenes del juego.

    Ejemplo:
        args = construir_parser().parse_args(["clean"])
    """
    return construir_parser_del_kit(PROYECTO, prog=PROG, descripcion=__doc__)


def registrar_progreso(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser], proyecto: Proyecto
) -> None:
    """
    Anade la orden ``progreso`` a la linea de ordenes del kit.

    Contexto:
        Es el plugin de subcomandos que declara ``psxdecomp.toml`` mientras el medidor de progreso y la
        seccion del README siguen viviendo en este proyecto. Los textos de ayuda nombran el documento
        de progreso y el resumen en JSON que fija el manifiesto.

    Args:
        subparsers (argparse._SubParsersAction[argparse.ArgumentParser]): Registro de subcomandos del kit.
        proyecto (Proyecto): Manifiesto del proyecto.

    Ejemplo:
        registrar_progreso(parser.add_subparsers(dest="orden"), proyecto)
    """
    documento = proyecto.rutas.documento_progreso
    medir = subparsers.add_parser(
        "progreso",
        help=f"mide la descompilacion y escribe {documento}, {infra.PROGRESO_JSON} y la seccion del README",
    )
    medir.add_argument(
        "--sin-readme", action="store_true", help="no actualiza la seccion de progreso del README.md"
    )
    medir.set_defaults(manejador=_manejar_progreso)


def _manejar_progreso(contexto: Contexto) -> int:
    """Adapta el contexto del kit a ``_ejecutar_progreso``."""
    return _ejecutar_progreso(contexto.raiz, contexto.ejecutar, not contexto.args.sin_readme)


def _fecha_actual() -> str:
    """Da la fecha local de hoy como ``AAAA-MM-DD`` (sustituible en pruebas)."""
    return date.today().isoformat()


def _actualizar_readme(raiz: Path, medido: progreso.Progreso, ejecutar: Ejecutor) -> None:
    """Reescribe la seccion de progreso del README e informa del resultado."""
    referencia = infra.leer_referencia(raiz / PROYECTO.identidad.referencia)
    cambio = readme_progreso.actualizar_readme(
        raiz,
        medido,
        _fecha_actual(),
        readme_progreso.obtener_hash_corto(raiz, ejecutar),
        referencia.sha256,
    )
    print(f"README.md: seccion de progreso {'actualizada' if cambio else 'sin cambios'}")


def _actualizar_readme_sin_abortar(raiz: Path, medido: progreso.Progreso, ejecutar: Ejecutor) -> None:
    """
    Actualiza la seccion del README y convierte cualquier fallo en un aviso.

    Contexto:
        La seccion del README es secundaria: el documento de progreso y el resumen en JSON ya
        estan escritos cuando se llega aqui, y abortar perderia los avisos de coherencia y de
        rutinas sin explicar que ``progreso`` emite despues.

    Args:
        raiz (Path): Raiz del repositorio.
        medido (progreso.Progreso): Medicion ya calculada.
        ejecutar (Ejecutor): Ejecutor de procesos usado para leer el hash del commit.

    Ejemplo:
        _actualizar_readme_sin_abortar(raiz, medido, ejecutar)
    """
    try:
        _actualizar_readme(raiz, medido, ejecutar)
    except (*ERRORES_PROPIOS, OSError) as error:
        print(
            f"aviso: no se pudo actualizar la seccion de progreso del README: {motivo_sin_rutas(error)}",
            file=sys.stderr,
        )


def _ejecutar_progreso(raiz: Path, ejecutar: Ejecutor, con_readme: bool = True) -> int:
    """Implementa ``progreso``; devuelve 1 si el ensamblador y el codigo C no cuadran con la tabla."""
    medido = progreso.generar_progreso(raiz)
    print(
        f"progreso: {medido.c_juego.funciones} funciones del juego en C de {medido.juego.funciones} "
        f"({medido.c_juego.bytes} de {medido.juego.bytes} bytes, {medido.porcentaje_bytes_juego:.2f} %); "
        f"{len(medido.no_coincidentes)} NON_MATCHING; docs/PROGRESO.md y build/progreso.json escritos"
    )
    if con_readme and (raiz / readme_progreso.RUTA_README).is_file():
        _actualizar_readme_sin_abortar(raiz, medido, ejecutar)
    elif con_readme:
        print("aviso: no existe README.md; seccion de progreso omitida", file=sys.stderr)
    if medido.manuscritas:
        print(f"manuscritas: {len(medido.manuscritas)} rutinas escritas a mano siguen en ensamblador")
    for archivo, funcion in medido.sin_comentario:
        aviso = f"aviso: {archivo}: {funcion} sigue en INCLUDE_ASM sin comentario que lo explique"
        print(aviso, file=sys.stderr)
    for aviso in coherencia_pendientes.avisos_puntuacion_pendiente(raiz, listar_fuentes_c(raiz)):
        print(f"aviso: {aviso}", file=sys.stderr)
    if medido.coherente is False:
        print(
            f"error: {medido.glabel_en_asm} glabel en asm/ + {medido.funciones_en_c} funciones en C no "
            f"suman las {medido.funciones_totales} de la tabla de simbolos: ejecute 'split'",
            file=sys.stderr,
        )
        return 1
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

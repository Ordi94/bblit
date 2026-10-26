"""Interfaz de linea de comandos del overlay: ``python -m tools.overlay``.

Capa mas externa: traduce argumentos a llamadas de las capas de extraccion y particion y los
errores esperados a una linea sin traza con codigo de salida distinto de cero.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from tools.overlay import dominio, extraccion, particion
from tools.overlay.dominio import VARIANTES_CONOCIDAS, VarianteConocida, VarianteExtraida
from tools.reconstruccion import infraestructura as infra
from tools.reconstruccion.infraestructura import Ejecutor, ProcesoError
from tools.toolchain.configuracion import leer_local_toml, resolver_rutas
from tools.toolchain.instalacion import leer_lock

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
RUTA_LOCK = Path("config") / "toolchain.lock.json"
RUTA_LOCAL = Path("config") / "local.toml"
ERRORES_CONTROLADOS = (ValueError, FileNotFoundError, ProcesoError, OSError)
TODAS = "todas"


def construir_parser() -> argparse.ArgumentParser:
    """
    Construye el analizador de argumentos de la CLI.

    Contexto:
        Separado de ``main`` para probar la definicion de ordenes por si sola.

    Returns:
        argparse.ArgumentParser: Analizador con las ordenes ``extraer``, ``simbolos``,
        ``split``, ``build``, ``verify`` y ``ram``.

    Ejemplo:
        args = construir_parser().parse_args(["verify", "--variante", "a"])
    """
    parser = argparse.ArgumentParser(prog="python -m tools.overlay", description=__doc__)
    parser.add_argument("--disc", help="disco (por defecto BBLIT_DISC o config/local.toml)")
    parser.add_argument(
        "--toolchain", help="carpeta del toolchain (por defecto BBLIT_TOOLCHAIN o ./toolchain)"
    )
    orden = parser.add_subparsers(dest="orden", required=True)
    orden.add_parser("extraer", help="extrae las variantes del overlay y escribe config/overlay.json")
    orden.add_parser("simbolos", help="regenera config/symbols_overlay.txt desde los binarios extraidos")
    for nombre, ayuda in (
        ("split", "particiona con splat (genera asm/overlay/<variante>/)"),
        ("build", "ensambla y enlaza (genera build/overlay/<variante>.bin)"),
        ("verify", "compara byte a byte con el binario extraido (OK o FAIL)"),
    ):
        sub = orden.add_parser(nombre, help=ayuda)
        sub.add_argument("--variante", default=TODAS, help="identificador de variante o 'todas'")
    ram = orden.add_parser("ram", help="indica que variante esta cargada en un volcado de RAM")
    ram.add_argument("volcado", type=Path, help="volcado de la RAM completa de la consola")
    return parser


def _seleccionar(variantes: Sequence[VarianteExtraida], pedida: str) -> list[VarianteExtraida]:
    """Filtra las variantes registradas segun ``--variante``."""
    if pedida == TODAS:
        return list(variantes)
    elegidas = [variante for variante in variantes if variante.identificador == pedida]
    if not elegidas:
        validas = ", ".join([*(v.identificador for v in variantes), TODAS])
        raise ValueError(f"variante '{pedida}' no registrada: opciones {validas}")
    return elegidas


def _orden_extraer(raiz: Path, disc: Path | None, conocidas: Sequence[VarianteConocida]) -> int:
    """Ejecuta ``extraer`` e imprime un resumen por variante."""
    variantes, binarios = extraccion.extraer_variantes(disc, conocidas)
    extraccion.escribir_extraccion(raiz, variantes, binarios)
    for variante in variantes:
        print(
            f"{variante.identificador} sha256={variante.sha256} bytes={variante.tamano} "
            f"contenedores={len(variante.archivos)}"
        )
    print(
        f"extraccion completada: {len(variantes)} variantes, "
        f"{sum(len(v.archivos) for v in variantes)} contenedores"
    )
    return 0


def _orden_ram(raiz: Path, volcado: Path, conocidas: Sequence[VarianteConocida]) -> int:
    """Ejecuta ``ram``: compara el volcado con cada variante registrada."""
    if volcado.stat().st_size > dominio.MAX_BYTES_VOLCADO:
        raise ValueError("el volcado excede el tamano permitido")
    ram = volcado.read_bytes()
    variantes = extraccion.leer_variantes(raiz, conocidas)
    binarios = {v.identificador: extraccion.leer_binario(raiz, v) for v in variantes}
    print(f"ranura del cargador: 0x{dominio.valor_ranura(ram):08X}")
    comparaciones = dominio.comparar_con_ram(ram, binarios)
    for comparacion in comparaciones:
        print(dominio.describir_comparacion(comparacion))
    return 0 if any(c.coincide for c in comparaciones) else 1


def _orden_simbolos(raiz: Path, variantes: Sequence[VarianteExtraida]) -> int:
    """Ejecuta ``simbolos``: regenera el archivo de simbolos comun."""
    funciones = particion.generar_simbolos(raiz, list(variantes))
    print(f"simbolos: {len(funciones)} funciones y la ranura del cargador en {particion.RUTA_SIMBOLOS}")
    return 0


def _orden_split(raiz: Path, variantes: Sequence[VarianteExtraida], ejecutar: Ejecutor) -> int:
    """Ejecuta ``split`` sobre las variantes elegidas."""
    for variante in variantes:
        resumen = particion.dividir(raiz, variante, sys.executable, ejecutar)
        print(
            f"split {resumen.identificador}: funciones={resumen.funciones} "
            f"glabel={resumen.glabel} palabras_en_texto={resumen.palabras_en_texto}"
        )
    return 0


def _orden_build(
    raiz: Path, variantes: Sequence[VarianteExtraida], toolchain: Path, ejecutar: Ejecutor
) -> int:
    """Ejecuta ``build`` sobre las variantes elegidas."""
    herramientas = infra.resolver_herramientas(leer_lock(raiz / RUTA_LOCK), toolchain, sys.executable)
    for variante in variantes:
        destino = particion.construir(raiz, variante, herramientas, ejecutar)
        print(f"build {variante.identificador}: {destino.relative_to(raiz).as_posix()}")
    return 0


def _orden_verify(raiz: Path, variantes: Sequence[VarianteExtraida]) -> int:
    """Ejecuta ``verify`` sobre todas las variantes elegidas antes de decidir el codigo de salida."""
    resultados = [particion.verificar(raiz, variante) for variante in variantes]
    for _, mensaje in resultados:
        print(mensaje)
    return 0 if all(coincide for coincide, _ in resultados) else 1


def main(
    argv: Sequence[str] | None = None,
    entorno: Mapping[str, str] | None = None,
    raiz: Path = RAIZ_REPOSITORIO,
    ejecutar: Ejecutor = infra.ejecutar_proceso,
    conocidas: Sequence[VarianteConocida] = VARIANTES_CONOCIDAS,
) -> int:
    """
    Punto de entrada de la CLI del overlay.

    Contexto:
        Lo invoca ``python -m tools.overlay``. Los errores esperados se imprimen en una linea
        sin traza y devuelven 1; ``verify`` devuelve 1 si alguna variante difiere, pero
        verifica todas las pedidas antes de salir.

    Args:
        argv (Sequence[str], opcional): Argumentos; por defecto ``sys.argv[1:]``.
        entorno (Mapping[str, str], opcional): Variables de entorno; por defecto ``os.environ``.
        raiz (Path, opcional): Raiz del repositorio (sustituible en pruebas).
        ejecutar (Ejecutor, opcional): Ejecutor de procesos (sustituible en pruebas).
        conocidas (Sequence[VarianteConocida], opcional): Variantes esperadas (sustituibles en
            pruebas por variantes sinteticas).

    Returns:
        int: 0 si la orden termina bien, 1 en caso contrario.

    Ejemplo:
        codigo = main(["verify"])
    """
    args = construir_parser().parse_args(argv)
    variables = entorno if entorno is not None else os.environ
    try:
        rutas = resolver_rutas(raiz, variables, leer_local_toml(raiz / RUTA_LOCAL), args.disc, args.toolchain)
        if args.orden == "extraer":
            return _orden_extraer(raiz, rutas.disc, conocidas)
        variantes = extraccion.leer_variantes(raiz, conocidas)
        acciones: dict[str, Callable[[], int]] = {
            "simbolos": lambda: _orden_simbolos(raiz, variantes),
            "ram": lambda: _orden_ram(raiz, args.volcado, conocidas),
            "split": lambda: _orden_split(raiz, _seleccionar(variantes, args.variante), ejecutar),
            "build": lambda: _orden_build(
                raiz, _seleccionar(variantes, args.variante), rutas.toolchain, ejecutar
            ),
            "verify": lambda: _orden_verify(raiz, _seleccionar(variantes, args.variante)),
        }
        return acciones[args.orden]()
    except ERRORES_CONTROLADOS as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

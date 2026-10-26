"""Interfaz de linea de comandos de ``python -m tools.ghidra``.

Subcomandos: ``analizar`` (importa y analiza), ``exportar`` (CSV y C de Ghidra), ``simbolos``
(genera ``config/symbols.txt``), ``informe`` (cifras de cobertura), ``borradores`` (C borrador con
``m2c``), ``grafo`` (llamadas y datos compartidos), ``subsistemas`` y ``limites`` (propuestas de
reparto). Los errores de uso o de entrada se reportan en una linea, sin trazas ni rutas internas.
"""

import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from tools.ghidra.borradores import (
    SEGUNDOS_POR_FUNCION,
    LanzadorSeparado,
    asegurar_desensamblado,
    contexto_desde_exportacion,
    ejecutar_separado,
    generar_borradores,
    seleccionar_funciones,
)
from tools.ghidra.datos_pequenos import descubrir_datos_pequenos, leer_gp
from tools.ghidra.depuracion import depurar_funciones, refinar_con_tablas
from tools.ghidra.dominio import (
    DIRECCION_BASE,
    DIRECCION_FIN,
    FIN_CODIGO,
    TAMANO_SEGMENTO,
    Simbolo,
    calcular_informe,
    construir_simbolos,
    fusionar_simbolos,
)
from tools.ghidra.ejecucion import (
    NOMBRE_EJECUTABLE,
    RAIZ_REPOSITORIO,
    SEGUNDOS_MAXIMOS,
    VERSIONES_FIRMAS,
    ConfiguracionGhidra,
    Ejecutor,
    ejecutar_analisis,
    ejecutar_exportacion,
    ejecutar_proceso,
    resolver_ejecutable,
    resolver_instalacion,
)
from tools.ghidra.ejecutable import TAMANO_CABECERA, leer_segmento
from tools.ghidra.ensamblador import FuncionAsm, dividir_por_funcion
from tools.ghidra.exportaciones import leer_cadenas_csv, leer_xrefs_csv
from tools.ghidra.grafo import (
    Grafo,
    comparar_datos,
    comparar_llamadores,
    construir_grafo,
    formatear_datos_csv,
    formatear_grafo_csv,
    formatear_punteros_csv,
    resumir_grafo,
)
from tools.ghidra.lectura import leer_funciones_csv
from tools.ghidra.limites import VENTANAS, calcular_limites, formatear_archivos_csv, proponer_archivos
from tools.ghidra.nombres import Choque, aplicar_nombres, parsear_nombres
from tools.ghidra.simbolos import escribir_atomico, formatear_nuevas_csv, formatear_tabla, parsear_tabla
from tools.ghidra.subsistemas import (
    caracterizar,
    formatear_subsistemas_csv,
    parsear_rangos,
    proponer_rangos,
    resumir_por_nombre,
)
from tools.ghidra.tablas import clasificar_tablas, detectar_corridas, formatear_tablas_csv
from tools.ghidra.zonas import FIN_JUEGO, INICIO_JUEGO, clasificar_zona

CARPETA_SCRIPTS = Path(__file__).resolve().parent / "scripts"
SIMBOLOS_POR_DEFECTO = RAIZ_REPOSITORIO / "config" / "symbols.txt"
M2C_POR_DEFECTO = RAIZ_REPOSITORIO / "toolchain" / "m2c" / "m2c.py"
CARPETA_DESENSAMBLADO = "desensamblado"


def construir_parser() -> argparse.ArgumentParser:
    """
    Define los subcomandos y sus argumentos.

    Contexto:
        Lo usa ``main``; separado para poder inspeccionar el parser sin ejecutar nada.

    Returns:
        argparse.ArgumentParser: Parser con los subcomandos.

    Ejemplo:
        argumentos = construir_parser().parse_args(["informe", "--funciones", "funciones.csv"])
    """
    parser = argparse.ArgumentParser(prog="python -m tools.ghidra", description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)

    analizar = sub.add_parser("analizar", help="importa el ejecutable y lo analiza con firmas de Psy-Q")
    analizar.add_argument("--exe", type=Path, help=f"ruta de {NOMBRE_EJECUTABLE} (o variable BBLIT_DISC)")
    analizar.add_argument("--proyecto", type=Path, required=True, help="carpeta del proyecto de Ghidra")
    analizar.add_argument("--ghidra", type=Path, help="instalacion de Ghidra (o variable BBLIT_GHIDRA)")
    analizar.add_argument("--semilla", type=Path, help="archivo con una direccion de funcion por linea")
    analizar.add_argument(
        "--versiones-firmas",
        default=",".join(VERSIONES_FIRMAS),
        help="versiones del SDK para pasadas de firmas adicionales, separadas por comas ('' para ninguna)",
    )
    analizar.add_argument("--segundos", type=int, default=SEGUNDOS_MAXIMOS, help="tiempo maximo del proceso")

    exportar = sub.add_parser("exportar", help="exporta funciones, cadenas, referencias y C de Ghidra")
    exportar.add_argument("--proyecto", type=Path, required=True, help="carpeta del proyecto de Ghidra")
    exportar.add_argument("--salida", type=Path, required=True, help="carpeta destino de la exportacion")
    exportar.add_argument("--ghidra", type=Path, help="instalacion de Ghidra (o variable BBLIT_GHIDRA)")
    exportar.add_argument("--programa", default=NOMBRE_EJECUTABLE, help="nombre del programa en el proyecto")
    exportar.add_argument("--sin-decompilar", action="store_true", help="omite los .c por funcion")
    exportar.add_argument("--segundos-por-funcion", type=int, default=60, help="limite del decompilador")
    exportar.add_argument("--segundos", type=int, default=SEGUNDOS_MAXIMOS, help="tiempo maximo del proceso")

    simbolos = sub.add_parser("simbolos", help="genera la tabla de simbolos a partir de funciones.csv")
    simbolos.add_argument("--funciones", type=Path, required=True, help="funciones.csv exportado")
    simbolos.add_argument("--salida", type=Path, required=True, help="archivo symbols.txt a escribir")
    simbolos.add_argument("--exe", type=Path, help=f"ruta de {NOMBRE_EJECUTABLE} (o variable BBLIT_DISC)")
    simbolos.add_argument("--tablas", type=Path, help="CSV donde escribir la clasificacion de las tablas")
    simbolos.add_argument(
        "--nombres", type=Path, help="archivo de nombres de funciones (config/nombres_funciones.txt)"
    )
    simbolos.add_argument("--nuevas", type=Path, help="CSV donde escribir las funciones nuevas y fusionadas")

    informe = sub.add_parser("informe", help="imprime conteos y cobertura de funciones.csv")
    informe.add_argument("--funciones", type=Path, required=True, help="funciones.csv exportado")
    informe.add_argument("--verificar", type=Path, help="symbols.txt a validar con el lector propio")

    borradores = sub.add_parser(
        "borradores", help="genera borradores en C con m2c para las funciones del juego"
    )
    _argumentos_analisis(borradores)
    borradores.add_argument("--m2c", type=Path, default=M2C_POR_DEFECTO, help="ruta de m2c.py")
    borradores.add_argument(
        "--segundos-por-funcion", type=int, default=SEGUNDOS_POR_FUNCION, help="limite de m2c por funcion"
    )
    borradores.add_argument(
        "--solo-rango",
        action="store_true",
        help="solo el rango del juego, sin las rutinas de libreria sin firma",
    )

    grafo = sub.add_parser("grafo", help="escribe el grafo de llamadas y los datos compartidos")
    _argumentos_analisis(grafo)

    subsistemas = sub.add_parser("subsistemas", help="caracteriza los subsistemas del juego")
    _argumentos_analisis(subsistemas)
    subsistemas.add_argument(
        "--rangos", type=Path, help="CSV nombre,inicio,fin; sin el se propone uno automatico"
    )

    limites = sub.add_parser("limites", help="propone los limites de las unidades de compilacion originales")
    _argumentos_analisis(limites)
    limites.add_argument(
        "--rangos", type=Path, required=True, help="CSV nombre,inicio,fin de los subsistemas"
    )
    return parser


def _argumentos_analisis(parser: argparse.ArgumentParser) -> None:
    """Agrega los argumentos comunes de los comandos que leen el desensamblado propio."""
    parser.add_argument(
        "--salida", type=Path, required=True, help="carpeta de salida (fuera del repositorio)"
    )
    parser.add_argument(
        "--exportacion", type=Path, required=True, help="carpeta con la exportacion de Ghidra"
    )
    parser.add_argument("--exe", type=Path, help=f"ruta de {NOMBRE_EJECUTABLE} (o variable BBLIT_DISC)")
    parser.add_argument("--simbolos", type=Path, default=SIMBOLOS_POR_DEFECTO, help="tabla de simbolos")


def _configuracion(args: argparse.Namespace, entorno: Mapping[str, str]) -> ConfiguracionGhidra:
    """Reune las rutas de Ghidra de los argumentos y del entorno."""
    return ConfiguracionGhidra(
        instalacion=resolver_instalacion(args.ghidra, entorno),
        proyecto=args.proyecto,
        scripts=CARPETA_SCRIPTS,
    )


def _comando_analizar(args: argparse.Namespace, entorno: Mapping[str, str], ejecutor: Ejecutor) -> int:
    """Ejecuta el subcomando ``analizar``."""
    versiones = [v for v in args.versiones_firmas.split(",") if v]
    carga = ejecutar_analisis(
        _configuracion(args, entorno),
        resolver_ejecutable(args.exe, entorno),
        args.semilla,
        versiones,
        segundos=args.segundos,
        ejecutor=ejecutor,
    )
    print(f"analisis completo: base=0x{carga.base:08X} entrada=0x{carga.entrada:08X}")
    return 0


def _comando_exportar(args: argparse.Namespace, entorno: Mapping[str, str], ejecutor: Ejecutor) -> int:
    """Ejecuta el subcomando ``exportar``."""
    ejecutar_exportacion(
        _configuracion(args, entorno),
        args.programa,
        args.salida,
        decompilar=not args.sin_decompilar,
        segundos_por_funcion=args.segundos_por_funcion,
        segundos=args.segundos,
        ejecutor=ejecutor,
    )
    print("exportacion completa")
    return 0


def _comando_simbolos(args: argparse.Namespace, entorno: Mapping[str, str]) -> int:
    """Ejecuta el subcomando ``simbolos``."""
    segmento = leer_segmento(resolver_ejecutable(args.exe, entorno))
    depuracion = depurar_funciones(leer_funciones_csv(args.funciones), segmento)
    inicios = [f.direccion for f in depuracion.funciones]
    corridas = detectar_corridas(
        segmento, DIRECCION_BASE, (FIN_CODIGO, DIRECCION_FIN), (DIRECCION_BASE, FIN_CODIGO)
    )
    tablas = clasificar_tablas(segmento, DIRECCION_BASE, corridas, inicios, (DIRECCION_BASE, FIN_CODIGO))
    de_puntero = {d for t in tablas if t.tipo == "puntero_a_funcion" for d in t.destinos}
    de_salto = {d for t in tablas if t.tipo == "salto" for d in t.destinos}
    refinado = refinar_con_tablas(depuracion.funciones, segmento, de_puntero, de_salto)
    funciones_finales = construir_simbolos(refinado.funciones)
    del_archivo: dict[int, str] = {}
    choques: list[Choque] = []
    if args.nombres is not None:
        del_archivo = parsear_nombres(args.nombres.read_text(encoding="utf-8"))
        funciones_finales, choques = aplicar_nombres(funciones_finales, refinado.funciones, del_archivo)
    gp = leer_gp(segmento, DIRECCION_BASE, (DIRECCION_BASE, FIN_CODIGO))
    datos = (
        []
        if gp is None
        else descubrir_datos_pequenos(
            segmento, DIRECCION_BASE, (DIRECCION_BASE, FIN_CODIGO), gp, DIRECCION_FIN
        )
    )
    simbolos = fusionar_simbolos(funciones_finales, datos)
    texto = formatear_tabla(simbolos)
    parsear_tabla(texto)
    nombres = {s.direccion: s.nombre for s in simbolos}
    antes = {s.direccion: s.nombre for s in construir_simbolos(depuracion.funciones)}
    de_consumidor = {**{a: nombres[p] for a, p in refinado.fusionadas}, **nombres}
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    if args.tablas is not None:
        escribir_atomico(
            args.tablas, formatear_tablas_csv(tablas, de_consumidor, {d for d, _ in refinado.nuevas})
        )
    if args.nuevas is not None:
        escribir_atomico(
            args.nuevas,
            formatear_nuevas_csv(refinado.nuevas, refinado.fusionadas, simbolos, antes, refinado.por_retorno),
        )
    escribir_atomico(args.salida, texto)
    print(
        f"{len(simbolos)} simbolos escritos "
        f"({len(depuracion.fusionadas)} fragmentos fusionados, {len(depuracion.descartadas)} descartados, "
        f"{len(depuracion.rescatadas)} huecos de codigo anadidos)"
    )
    de_puntero_n = sum(1 for t in tablas if t.tipo == "puntero_a_funcion")
    print(
        f"tablas: {len(tablas)} ({de_puntero_n} de punteros a funcion, "
        f"{len(tablas) - de_puntero_n} de switch); "
        f"{len(refinado.nuevas)} funciones nuevas, {len(refinado.por_retorno)} separadas por retorno, "
        f"{len(refinado.fusionadas)} continuaciones fusionadas, "
        f"{len(refinado.conflictos)} destinos no aplicados"
    )
    if args.nombres is not None:
        print(f"nombres: {len(del_archivo) - len(choques)} aplicados o ya iguales, {len(choques)} choques")
        for choque in choques:
            print(f"choque 0x{choque.direccion:08X} {choque.nombre}: {choque.motivo} ({choque.existente})")
    return 0


def _comando_informe(args: argparse.Namespace) -> int:
    """Ejecuta el subcomando ``informe``."""
    informe = calcular_informe(leer_funciones_csv(args.funciones))
    print(f"funciones totales: {informe.total}")
    print(f"libreria identificada: {informe.libreria}")
    print(f"  con nombre oficial: {informe.libreria_oficial}")
    print(f"  rutinas internas de objeto: {informe.libreria_local}")
    print(f"  con candidatos alternos: {informe.ambiguas}")
    print(f"juego: {informe.juego}")
    print(f"cobertura del segmento: {informe.porcentaje_cubierto:.2f} % ({informe.bytes_cubiertos} bytes)")
    if args.verificar is not None:
        validos = parsear_tabla(args.verificar.read_text(encoding="utf-8"))
        print(f"symbols.txt valido: {len(validos)} simbolos")
    return 0


@dataclass(frozen=True)
class _Analisis:
    """Entradas comunes de ``borradores`` y ``grafo``: simbolos, desensamblado propio y grafo."""

    simbolos: list[Simbolo]
    texto_asm: str
    funciones: list[FuncionAsm]
    grafo: Grafo
    segmento: bytes


def _cargar_analisis(args: argparse.Namespace, entorno: Mapping[str, str], ejecutor: Ejecutor) -> _Analisis:
    """Obtiene el desensamblado propio y construye el grafo."""
    exe = resolver_ejecutable(args.exe, entorno)
    segmento = leer_segmento(exe)
    simbolos = [s for s in parsear_tabla(args.simbolos.read_text(encoding="utf-8")) if s.tipo == "func"]
    texto = asegurar_desensamblado(
        exe,
        args.simbolos,
        args.salida / CARPETA_DESENSAMBLADO,
        base=DIRECCION_BASE,
        tamano_archivo=TAMANO_CABECERA + TAMANO_SEGMENTO,
        lanzador=ejecutor,
    )
    funciones = dividir_por_funcion(texto)
    corridas = detectar_corridas(
        segmento, DIRECCION_BASE, (FIN_CODIGO, DIRECCION_FIN), (INICIO_JUEGO, FIN_JUEGO)
    )
    return _Analisis(simbolos, texto, funciones, construir_grafo(funciones, simbolos, corridas), segmento)


def _comando_borradores(
    args: argparse.Namespace, entorno: Mapping[str, str], ejecutor: Ejecutor, lanzador: LanzadorSeparado
) -> int:
    """Ejecuta el subcomando ``borradores``."""
    analisis = _cargar_analisis(args, entorno, ejecutor)
    funciones = leer_funciones_csv(args.exportacion / "funciones.csv")
    datos = leer_xrefs_csv(args.exportacion / "xrefs_datos.csv")
    elegidas = seleccionar_funciones(
        analisis.simbolos, funciones, "rango" if args.solo_rango else "sin_firma"
    )
    contexto = contexto_desde_exportacion(analisis.simbolos, args.exportacion / "decomp", datos)
    resumen = generar_borradores(
        elegidas=elegidas,
        texto_asm=analisis.texto_asm,
        tablas=analisis.grafo.tablas_salto,
        contexto=contexto,
        salida=args.salida,
        m2c=args.m2c,
        segundos=args.segundos_por_funcion,
        lanzador=lanzador,
    )
    print(
        f"borradores: {resumen.seleccionadas} funciones, {resumen.generadas} generadas, "
        f"{resumen.fallidas} fallidas, {resumen.absorbidas} absorbidas por una funcion contigua "
        f"({resumen.con_marcas} con marcas de m2c)"
    )
    return 0


def _comando_grafo(args: argparse.Namespace, entorno: Mapping[str, str], ejecutor: Ejecutor) -> int:
    """Ejecuta el subcomando ``grafo``."""
    analisis = _cargar_analisis(args, entorno, ejecutor)
    nombres = {s.direccion: s.nombre for s in analisis.simbolos}
    args.salida.mkdir(parents=True, exist_ok=True)
    escribir = {
        "grafo_llamadas.csv": formatear_grafo_csv(analisis.grafo, nombres),
        "datos_compartidos.csv": formatear_datos_csv(analisis.grafo, nombres),
        "punteros_funcion.csv": formatear_punteros_csv(analisis.grafo, nombres),
    }
    for nombre, contenido in escribir.items():
        (args.salida / nombre).write_text(contenido, encoding="utf-8", newline="\n")
    resumen = resumir_grafo(analisis.grafo)
    print(
        f"aristas: {resumen.total} ({resumen.llamadas} sitios de llamada); "
        f"jal {resumen.por_tipo['jal']}, j {resumen.por_tipo['j']}, tabla {resumen.por_tipo['tabla']}, "
        f"indirectas {resumen.indirectas} instrucciones"
    )
    print(
        f"juego->juego {resumen.juego_juego}, juego->libreria {resumen.juego_libreria}, "
        f"juego->externo {resumen.juego_externo}, por tabla {resumen.por_tabla}"
    )
    print(f"switch {resumen.switches}, punteros a funcion {resumen.punteros}, datos {resumen.datos}")
    esperados = {f.direccion: f.llamadores for f in leer_funciones_csv(args.exportacion / "funciones.csv")}
    del_juego = {d: n for d, n in esperados.items() if clasificar_zona(d) in ("arranque", "juego")}
    coinciden, difieren = comparar_llamadores(analisis.grafo, del_juego)
    print(
        f"llamadores contra Ghidra (juego): {coinciden} de {len(del_juego)} coinciden, "
        f"{len(difieren)} difieren"
    )
    referencias = leer_xrefs_csv(args.exportacion / "xrefs_datos.csv")
    datos = comparar_datos(analisis.grafo, {r.direccion: r.funciones for r in referencias})
    print(
        f"datos contra Ghidra: {datos.coinciden} iguales, {datos.contenidos} contenidos, "
        f"{len(datos.difieren)} distintos"
    )
    return 0


def _comando_subsistemas(args: argparse.Namespace, entorno: Mapping[str, str], ejecutor: Ejecutor) -> int:
    """Ejecuta el subcomando ``subsistemas``."""
    analisis = _cargar_analisis(args, entorno, ejecutor)
    cadenas = leer_cadenas_csv(args.exportacion / "strings.csv")
    if args.rangos is None:
        limites = calcular_limites(analisis.simbolos, analisis.grafo, analisis.segmento)
        cortes = [lim.direccion for lim in limites if lim.ventana_limpia == VENTANAS[0]]
        rangos = proponer_rangos(analisis.simbolos, analisis.grafo, cortes)
    else:
        rangos = parsear_rangos(args.rangos.read_text(encoding="utf-8"))
    subsistemas = caracterizar(rangos, analisis.simbolos, analisis.grafo, cadenas)
    args.salida.mkdir(parents=True, exist_ok=True)
    (args.salida / "subsistemas.csv").write_text(
        formatear_subsistemas_csv(subsistemas), encoding="utf-8", newline="\n"
    )
    for nombre, cantidad in resumir_por_nombre(subsistemas).items():
        print(f"{nombre}: {cantidad} funciones")
    print(f"subsistemas: {len(subsistemas)}")
    return 0


def _comando_limites(args: argparse.Namespace, entorno: Mapping[str, str], ejecutor: Ejecutor) -> int:
    """Ejecuta el subcomando ``limites``."""
    analisis = _cargar_analisis(args, entorno, ejecutor)
    rangos = parsear_rangos(args.rangos.read_text(encoding="utf-8"))
    limites = calcular_limites(analisis.simbolos, analisis.grafo, analisis.segmento)
    archivos = proponer_archivos(limites, rangos)
    args.salida.mkdir(parents=True, exist_ok=True)
    (args.salida / "archivos_origen.csv").write_text(
        formatear_archivos_csv(archivos), encoding="utf-8", newline="\n"
    )
    por_confianza = {c: sum(1 for a in archivos if a.confianza == c) for c in ("alta", "media", "baja")}
    print(f"limites: {len(archivos)} archivos propuestos ({por_confianza})")
    print(
        f"relleno de nop observado: {sum(1 for lim in limites if lim.relleno_nop)} cortes de {len(limites)}"
    )
    return 0


def main(
    argv: Sequence[str] | None = None,
    entorno: Mapping[str, str] | None = None,
    ejecutor: Ejecutor = ejecutar_proceso,
    lanzador: LanzadorSeparado = ejecutar_separado,
) -> int:
    """
    Punto de entrada de la herramienta.

    Contexto:
        Lo invoca ``python -m tools.ghidra``; las pruebas lo llaman con entorno y ejecutor
        propios para no depender de Ghidra ni de variables reales.

    Args:
        argv (Sequence[str] | None, opcional): Argumentos; por defecto los de ``sys.argv``.
        entorno (Mapping[str, str] | None, opcional): Variables de entorno; por defecto las reales.
        ejecutor (Ejecutor, opcional): Lanzador de procesos; por defecto ``ejecutar_proceso``.
        lanzador (LanzadorSeparado, opcional): Lanzador de ``m2c`` con salidas separadas.

    Returns:
        int: 0 si el comando termino bien, 2 si fallo por entrada invalida o error de Ghidra.

    Ejemplo:
        codigo = main(["informe", "--funciones", "funciones.csv"])
    """
    args = construir_parser().parse_args(argv)
    variables = os.environ if entorno is None else entorno
    comandos: dict[str, Callable[[], int]] = {
        "analizar": lambda: _comando_analizar(args, variables, ejecutor),
        "exportar": lambda: _comando_exportar(args, variables, ejecutor),
        "simbolos": lambda: _comando_simbolos(args, variables),
        "informe": lambda: _comando_informe(args),
        "borradores": lambda: _comando_borradores(args, variables, ejecutor, lanzador),
        "grafo": lambda: _comando_grafo(args, variables, ejecutor),
        "subsistemas": lambda: _comando_subsistemas(args, variables, ejecutor),
        "limites": lambda: _comando_limites(args, variables, ejecutor),
    }
    try:
        return comandos[args.comando]()
    except (ValueError, TimeoutError) as error:
        print(f"error: {error}", file=sys.stderr)
    except OSError as error:
        print(f"error de entrada/salida: {type(error).__name__}", file=sys.stderr)
    return 2

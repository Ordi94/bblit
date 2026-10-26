"""Interfaz de linea de comandos de la reconstruccion: ``python tools/build.py``."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePath

from tools.reconstruccion import coherencia_pendientes, compilacion, diff, progreso, variantes
from tools.reconstruccion import infraestructura as infra
from tools.reconstruccion.dominio import EjecutableReferencia
from tools.reconstruccion.infraestructura import Ejecutor, ProcesoError, listar_fuentes_c
from tools.toolchain.configuracion import Rutas, leer_local_toml, resolver_rutas
from tools.toolchain.instalacion import leer_lock, resolver_herramienta

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
RUTA_REFERENCIA = Path("config") / "ejecutable.json"
RUTA_LOCK = Path("config") / "toolchain.lock.json"
RUTA_LOCAL = Path("config") / "local.toml"
ERRORES_PROPIOS = (ValueError, ProcesoError)


def construir_parser() -> argparse.ArgumentParser:
    """
    Construye el analizador de argumentos de la CLI.

    Contexto:
        Separado de ``main`` para probar la definicion de ordenes por si sola.

    Returns:
        argparse.ArgumentParser: Analizador con las ordenes ``split``, ``build``, ``verify``,
        ``clean``, ``diff``, ``probar``, ``progreso`` y ``verificar-config``.

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
    ensayar = sub.add_parser(
        "probar", help="compara con el original cada variante .c de una carpeta y ordena por puntuacion"
    )
    ensayar.add_argument("funcion", help="nombre de la funcion (por ejemplo func_80035244)")
    ensayar.add_argument(
        "carpeta", type=Path, help="carpeta con una variante completa de la funcion por archivo .c"
    )
    sub.add_parser("progreso", help="mide la descompilacion y escribe docs/PROGRESO.md y build/progreso.json")
    sub.add_parser(
        "verificar-config",
        help="avisa de las claves de [datos_pequenos] que config/symbols.txt ya declara (solo informa)",
    )
    return parser


def _ejecutar_clean(raiz: Path, referencia: EjecutableReferencia) -> int:
    """Implementa ``clean``."""
    eliminadas = infra.limpiar(raiz, referencia.nombre)
    print("eliminado: " + (", ".join(eliminadas) if eliminadas else "nada que eliminar"))
    return 0


def _ejecutar_verificacion(raiz: Path, rutas: Rutas, referencia: EjecutableReferencia) -> int:
    """Implementa ``verify``; un ejecutable ausente es un FAIL, no un error de uso."""
    original = infra.obtener_original(raiz, rutas.disc, referencia)
    if not (raiz / "build" / referencia.nombre).is_file():
        print(f"FAIL el ejecutable reconstruido no existe: ejecute 'build' (esperado={referencia.sha256})")
        return 1
    coincide, mensaje = infra.verificar(raiz, original, referencia)
    print(mensaje)
    return 0 if coincide else 1


def _imprimir_avisos(avisos: Sequence[str]) -> None:
    """Imprime cada aviso de configuracion por la salida de errores."""
    for aviso in avisos:
        print(f"aviso: {aviso}", file=sys.stderr)


def _avisar_configuracion(raiz: Path) -> None:
    """Avisa de la configuracion repetida al terminar ``split`` sin tumbarlo.

    Es una comprobacion informativa: si no se puede hacer, se dice y se sigue.
    """
    try:
        avisos = infra.verificar_configuracion(raiz)
    except (ValueError, FileNotFoundError, OSError) as error:
        print(f"aviso: no se pudo verificar la configuracion: {error}", file=sys.stderr)
        return
    _imprimir_avisos(avisos)


def _ejecutar_verificacion_configuracion(raiz: Path) -> int:
    """Implementa ``verificar-config``; solo informa, asi que devuelve 0 aunque haya avisos."""
    avisos = infra.verificar_configuracion(raiz)
    _imprimir_avisos(avisos)
    print(f"verificar-config: {len(avisos)} avisos")
    return 0


def _ejecutar_progreso(raiz: Path) -> int:
    """Implementa ``progreso``; devuelve 1 si el ensamblador y el codigo C no cuadran con la tabla."""
    medido = progreso.generar_progreso(raiz)
    print(
        f"progreso: {medido.c_juego.funciones} funciones del juego en C de {medido.juego.funciones} "
        f"({medido.c_juego.bytes} de {medido.juego.bytes} bytes, {medido.porcentaje_bytes_juego:.2f} %); "
        f"{len(medido.no_coincidentes)} NON_MATCHING; docs/PROGRESO.md y build/progreso.json escritos"
    )
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


def resumir_comparacion(resultado: diff.ResultadoDiff) -> list[str]:
    """
    Da las lineas con que ``diff`` cierra su salida, despues de las columnas de ``asm-differ``.

    Contexto:
        Una funcion cuyos bytes enlazados coinciden con el original puntua 0, igual que una que
        coincide instruccion por instruccion; las referencias que el C escribe en forma numerica y
        el original en forma simbolica no son una diferencia. Se conservan como nota aparte, antes
        de la linea de veredicto, para quien quiera normalizarlas.

    Args:
        resultado (diff.ResultadoDiff): Resultado de comparar una funcion.

    Returns:
        list[str]: Aviso de truncado (solo si ``asm-differ`` corto el candidato), nota de
        referencias numericas (solo si los bytes coinciden) y linea de veredicto.

    Ejemplo:
        for linea in resumir_comparacion(resultado):
            print(linea)
    """
    veredicto = f"{resultado.funcion} ({resultado.archivo}): puntuacion {resultado.puntuacion}"
    lineas = []
    if resultado.truncado:
        lineas.append(
            "aviso: asm-differ corto el desensamblado del candidato en el limite de lineas; "
            "la puntuacion y las diferencias mostradas son parciales"
        )
    if not resultado.bytes_iguales:
        return [*lineas, veredicto]
    nota = (
        f"nota: {resultado.referencias_numericas} referencias en forma numerica "
        f"(asm-differ puntua {resultado.puntuacion_asm})"
    )
    return [*lineas, nota, f"{veredicto} (coincide en bytes)"]


def _ejecutar_comparacion(raiz: Path, rutas: Rutas, funcion: str, python: str, ejecutar: Ejecutor) -> int:
    """Implementa ``diff``; devuelve 0 solo si la medicion es completa y coincide."""
    lock = leer_lock(raiz / RUTA_LOCK)
    herramientas = compilacion.resolver_herramientas_compilacion(lock, rutas.toolchain, python)
    script = resolver_herramienta(lock, rutas.toolchain, "asm-differ", "diff")
    resultado = diff.comparar_funcion(raiz, funcion, herramientas, script, ejecutar)
    print(resultado.texto)
    print("\n".join(resumir_comparacion(resultado)))
    return 0 if resultado.coincide else 1


def _ejecutar_probar(
    raiz: Path, rutas: Rutas, funcion: str, carpeta: Path, *, python: str, ejecutar: Ejecutor
) -> int:
    """Implementa ``probar``; devuelve 0 solo si alguna variante tiene puntuacion cero."""
    lock = leer_lock(raiz / RUTA_LOCK)
    herramientas = compilacion.resolver_herramientas_compilacion(lock, rutas.toolchain, python)
    script = resolver_herramienta(lock, rutas.toolchain, "asm-differ", "diff")
    resultados = variantes.probar_variantes(
        raiz, funcion, carpeta, herramientas, script_diff=script, ejecutar=ejecutar
    )
    print(variantes.formatear_tabla(resultados))
    return 0 if resultados[0].coincide else 1


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
        _avisar_configuracion(raiz)
        return 0
    destino = compilacion.construir_mixto(
        raiz,
        referencia,
        herramientas,
        lambda: compilacion.resolver_herramientas_compilacion(lock, rutas.toolchain, sys.executable),
        ejecutar,
        declaradas=infra.leer_secciones_declaradas(raiz),
    )
    print(f"build completado: {destino.relative_to(raiz).as_posix()} sha256={infra.sha256_archivo(destino)}")
    return 0


def _despachar(
    args: argparse.Namespace, raiz: Path, rutas: Rutas, referencia: EjecutableReferencia, ejecutar: Ejecutor
) -> int:
    """Ejecuta las ordenes que necesitan las rutas del disco o del toolchain."""
    if args.orden == "diff":
        return _ejecutar_comparacion(raiz, rutas, args.funcion, sys.executable, ejecutar)
    if args.orden == "probar":
        return _ejecutar_probar(
            raiz, rutas, args.funcion, args.carpeta, python=sys.executable, ejecutar=ejecutar
        )
    if args.orden == "verify":
        return _ejecutar_verificacion(raiz, rutas, referencia)
    return _ejecutar_construccion(raiz, rutas, referencia, args.orden, ejecutar)


def describir_error_de_sistema(error: OSError) -> str:
    """
    Da el texto de un error de entrada/salida sin exponer rutas de la maquina.

    Contexto:
        Lo usa ``main``. Un ``OSError`` nativo (permisos, disco, archivo ausente) lleva en su texto
        la ruta completa; el proyecto tambien lanza ``FileNotFoundError`` con un mensaje propio y
        sin ``errno`` (por ejemplo "falta config/symbols.txt"), que se conserva tal cual porque es
        una instruccion para el usuario y no contiene directorios de la maquina.

    Args:
        error (OSError): Error capturado.

    Returns:
        str: El mensaje propio si el error no trae ``errno``; si no, el tipo de error, el motivo
        del sistema (``strerror``) y solo el nombre base del archivo, nunca el directorio.

    Ejemplo:
        print(describir_error_de_sistema(PermissionError(13, "Acceso denegado", "C:/datos/a.bin")))
    """
    if error.errno is None:
        return str(error)
    detalle = f"error de entrada/salida: {type(error).__name__}"
    if error.strerror:
        detalle += f" ({error.strerror})"
    if error.filename:
        detalle += f": {PurePath(str(error.filename)).name}"
    return detalle


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
        traza ni rutas de la maquina y devuelven 1; ``verify`` y ``diff`` devuelven 1 tambien
        cuando las huellas o las funciones difieren.

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
        if args.orden == "verificar-config":
            return _ejecutar_verificacion_configuracion(raiz)
        referencia = infra.leer_referencia(raiz / RUTA_REFERENCIA)
        if args.orden == "clean":
            return _ejecutar_clean(raiz, referencia)
        rutas = resolver_rutas(raiz, variables, leer_local_toml(raiz / RUTA_LOCAL), args.disc, args.toolchain)
        return _despachar(args, raiz, rutas, referencia, ejecutar)
    except ERRORES_PROPIOS as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"error: {describir_error_de_sistema(error)}", file=sys.stderr)
        return 1

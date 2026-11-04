"""Ordenes comunes de la linea de ordenes: dividir, construir, verificar, limpiar, comparar y buscar.

Capa de aplicacion. Cada funcion recibe un ``Contexto`` y devuelve el codigo de retorno de la orden;
todo lo que depende del proyecto (rutas, convenciones, nombre del ejecutable) sale de su manifiesto.
Los errores esperados se propagan: ``main`` los convierte en una linea ``error: ...``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from psxdecomp.cli import plugins
from psxdecomp.cli.contexto import Contexto, ResultadoVerificacion
from psxdecomp.cli.errores import motivo_sin_rutas
from psxdecomp.construccion import compilacion, infraestructura
from psxdecomp.construccion.dominio import EjecutableReferencia
from psxdecomp.construccion.salidas import calcular_salidas
from psxdecomp.diff import comparacion, variantes
from psxdecomp.lectura import cargar_proyecto
from psxdecomp.permutador import busqueda
from psxdecomp.toolchain.configuracion import Rutas as RutasDeEjecucion
from psxdecomp.toolchain.instalacion import resolver_herramienta

ORDENES_SIN_PROYECTO = frozenset({"comprobar"})


def _preparar(contexto: Contexto) -> tuple[EjecutableReferencia, RutasDeEjecucion]:
    """Lee la referencia del ejecutable y resuelve el disco y el toolchain, en ese orden."""
    return contexto.referencia(), contexto.rutas_toolchain()


def ejecutar_comprobar(args: argparse.Namespace) -> int:
    """
    Implementa ``comprobar``: valida el manifiesto de una carpeta e imprime su resumen.

    Contexto:
        No recibe el contexto: la carpeta es el argumento ``ruta``, de modo que sirve
        tambien para diagnosticar un manifiesto que impide cargar el proyecto.

    Args:
        args (argparse.Namespace): Argumentos de la orden; ``ruta`` es la raiz a comprobar.

    Returns:
        int: ``0`` si el manifiesto es valido.

    Raises:
        ManifiestoError: Si el manifiesto no es valido (``main`` lo imprime sin rutas).

    Ejemplo:
        codigo = ejecutar_comprobar(args)
    """
    print(cargar_proyecto(Path(args.ruta)).resumen())
    return 0


def ejecutar_split(contexto: Contexto) -> int:
    """
    Implementa ``split``: particiona el ejecutable original y avisa de la configuracion repetida.

    Contexto:
        Primer paso del flujo: deja el ensamblador y el script del enlazador que usa ``build``.

    Args:
        contexto (Contexto): Contexto de la orden.

    Returns:
        int: ``0`` si el particionado termina bien.

    Raises:
        ValueError: Si la configuracion o el disco no son validos.
        ProcesoError: Si una herramienta falla.

    Ejemplo:
        codigo = ejecutar_split(contexto)
    """
    proyecto = contexto.proyecto
    referencia, rutas_toolchain = _preparar(contexto)
    original = infraestructura.obtener_original(
        contexto.raiz,
        rutas_toolchain.disc,
        referencia,
        rutas=proyecto.rutas,
        variables=proyecto.variables(),
    )
    herramientas = infraestructura.resolver_herramientas(
        contexto.lock(), rutas_toolchain.toolchain, contexto.python
    )
    infraestructura.dividir(
        contexto.raiz,
        original,
        referencia,
        herramientas,
        contexto.ejecutar,
        rutas=proyecto.rutas,
        convenciones=proyecto.convenciones,
    )
    print(f"split completado: {proyecto.rutas.asm}/ y script del enlazador generados")
    _avisar_configuracion(contexto)
    return 0


def _avisar_configuracion(contexto: Contexto) -> None:
    """
    Avisa de la configuracion repetida al terminar ``split`` sin tumbarlo.

    Contexto:
        Es una comprobacion informativa: si no se puede hacer, se dice y se sigue.

    Args:
        contexto (Contexto): Contexto de la orden.

    Ejemplo:
        _avisar_configuracion(contexto)
    """
    try:
        avisos = infraestructura.verificar_configuracion(
            contexto.raiz, rutas=contexto.proyecto.rutas, convenciones=contexto.proyecto.convenciones
        )
    except (ValueError, FileNotFoundError, OSError) as error:
        print(
            f"aviso: no se pudo verificar la configuracion: {motivo_sin_rutas(error)}",
            file=sys.stderr,
        )
        return
    imprimir_avisos(avisos)


def imprimir_avisos(avisos: Sequence[str]) -> None:
    """
    Imprime cada aviso de configuracion por la salida de errores.

    Contexto:
        Lo usan ``split`` y las ordenes que el proyecto anade con sus plugins.

    Args:
        avisos (Sequence[str]): Textos de aviso, uno por linea.

    Ejemplo:
        imprimir_avisos(["clave repetida"])
    """
    for aviso in avisos:
        print(f"aviso: {aviso}", file=sys.stderr)


def ejecutar_build(contexto: Contexto) -> int:
    """
    Implementa ``build``: compila los C, ensambla el resto y enlaza el ejecutable.

    Contexto:
        Los ganchos ``antes_de_construir`` del manifiesto se invocan antes de compilar, cuando ``split``
        ya dejo el ensamblador.

    Args:
        contexto (Contexto): Contexto de la orden.

    Returns:
        int: ``0`` si la construccion termina bien.

    Raises:
        ValueError: Si la configuracion o un objeto no son validos.
        ProcesoError: Si una herramienta falla.

    Ejemplo:
        codigo = ejecutar_build(contexto)
    """
    proyecto = contexto.proyecto
    referencia, rutas_toolchain = _preparar(contexto)
    lock = contexto.lock()
    herramientas = infraestructura.resolver_herramientas(lock, rutas_toolchain.toolchain, contexto.python)
    plugins.ejecutar_antes_de_construir(proyecto)
    destino = compilacion.construir_mixto(
        contexto.raiz,
        referencia,
        herramientas,
        lambda: compilacion.resolver_herramientas_compilacion(
            lock, rutas_toolchain.toolchain, contexto.python
        ),
        contexto.ejecutar,
        declaradas=infraestructura.leer_secciones_declaradas(contexto.raiz, rutas=proyecto.rutas),
        rutas=proyecto.rutas,
        convenciones=proyecto.convenciones,
        compilacion=proyecto.compilacion,
    )
    print(
        f"build completado: {destino.relative_to(contexto.raiz).as_posix()} "
        f"sha256={infraestructura.sha256_archivo(destino)}"
    )
    return 0


def ejecutar_verify(contexto: Contexto) -> int:
    """
    Implementa ``verify``; un ejecutable ausente es un FAIL, no un error de uso.

    Contexto:
        Despues de imprimir el resultado se invocan los ganchos ``despues_de_verificar``.

    Args:
        contexto (Contexto): Contexto de la orden.

    Returns:
        int: ``0`` si las huellas coinciden, ``1`` si no.

    Raises:
        ValueError: Si la configuracion o el disco no son validos.

    Ejemplo:
        codigo = ejecutar_verify(contexto)
    """
    proyecto = contexto.proyecto
    referencia, rutas_toolchain = _preparar(contexto)
    original = infraestructura.obtener_original(
        contexto.raiz,
        rutas_toolchain.disc,
        referencia,
        rutas=proyecto.rutas,
        variables=proyecto.variables(),
    )
    reconstruido = calcular_salidas(referencia.nombre, proyecto.rutas).ejecutable
    if not (contexto.raiz / reconstruido).is_file():
        resultado = ResultadoVerificacion(
            False,
            f"FAIL el ejecutable reconstruido no existe: ejecute 'build' (esperado={referencia.sha256})",
        )
    else:
        coincide, mensaje = infraestructura.verificar(
            contexto.raiz, original, referencia, rutas=proyecto.rutas
        )
        resultado = ResultadoVerificacion(coincide, mensaje)
    print(resultado.mensaje)
    plugins.ejecutar_despues_de_verificar(proyecto, resultado)
    return 0 if resultado.coincide else 1


def ejecutar_clean(contexto: Contexto) -> int:
    """
    Implementa ``clean``: elimina el ensamblador, lo esperado y los artefactos de la construccion.

    Contexto:
        Respeta las subcarpetas ajenas que declara el manifiesto.

    Args:
        contexto (Contexto): Contexto de la orden.

    Returns:
        int: ``0`` siempre que la limpieza termine.

    Ejemplo:
        codigo = ejecutar_clean(contexto)
    """
    eliminadas = infraestructura.limpiar(
        contexto.raiz, contexto.referencia().nombre, rutas=contexto.proyecto.rutas
    )
    print("eliminado: " + (", ".join(eliminadas) if eliminadas else "nada que eliminar"))
    return 0


def resumir_comparacion(resultado: comparacion.ResultadoDiff) -> list[str]:
    """
    Da las lineas con que ``diff`` cierra su salida, despues de las columnas de ``asm-differ``.

    Contexto:
        Una funcion cuyos bytes enlazados coinciden con el original puntua 0, igual que una que
        coincide instruccion por instruccion; las referencias que el C escribe en forma numerica y
        el original en forma simbolica no son una diferencia. Se conservan como nota aparte, antes
        de la linea de veredicto, para quien quiera normalizarlas.

    Args:
        resultado (comparacion.ResultadoDiff): Resultado de comparar una funcion.

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


def ejecutar_diff(contexto: Contexto) -> int:
    """
    Implementa ``diff``: compara una funcion compilada desde C con su original.

    Contexto:
        Imprime las columnas de ``asm-differ`` y el resumen de ``resumir_comparacion``.

    Args:
        contexto (Contexto): Contexto de la orden; ``args.funcion`` es la funcion a comparar.

    Returns:
        int: ``0`` solo si la medicion es completa y coincide.

    Raises:
        ValueError: Si la funcion no es valida o no figura en los fuentes.
        FuncionSinCError: Si la funcion sigue solo en ensamblador.
        ProcesoError: Si una herramienta falla.

    Ejemplo:
        codigo = ejecutar_diff(contexto)
    """
    proyecto = contexto.proyecto
    _, rutas_toolchain = _preparar(contexto)
    lock = contexto.lock()
    herramientas = compilacion.resolver_herramientas_compilacion(
        lock, rutas_toolchain.toolchain, contexto.python
    )
    script = resolver_herramienta(lock, rutas_toolchain.toolchain, "asm-differ", "diff")
    resultado = comparacion.comparar_funcion(
        contexto.raiz,
        contexto.args.funcion,
        herramientas,
        script,
        contexto.ejecutar,
        rutas=proyecto.rutas,
        convenciones=proyecto.convenciones,
        compilacion=proyecto.compilacion,
        nombre_ejecutable=proyecto.identidad.ejecutable,
    )
    print(resultado.texto)
    print("\n".join(resumir_comparacion(resultado)))
    return 0 if resultado.coincide else 1


def ejecutar_probar(contexto: Contexto) -> int:
    """
    Implementa ``probar``: compara cada variante de una carpeta con el original y las ordena.

    Contexto:
        Las variantes viven fuera de los fuentes: la orden no escribe en ellos.

    Args:
        contexto (Contexto): Contexto de la orden; ``args.funcion`` y ``args.carpeta``.

    Returns:
        int: ``0`` solo si alguna variante tiene puntuacion cero.

    Raises:
        ValueError: Si la funcion o la carpeta de variantes no son validas.
        ProcesoError: Si una herramienta falla al preparar el objetivo.

    Ejemplo:
        codigo = ejecutar_probar(contexto)
    """
    proyecto = contexto.proyecto
    _, rutas_toolchain = _preparar(contexto)
    lock = contexto.lock()
    herramientas = compilacion.resolver_herramientas_compilacion(
        lock, rutas_toolchain.toolchain, contexto.python
    )
    script = resolver_herramienta(lock, rutas_toolchain.toolchain, "asm-differ", "diff")
    resultados = variantes.probar_variantes(
        contexto.raiz,
        contexto.args.funcion,
        contexto.args.carpeta,
        herramientas,
        script_diff=script,
        ejecutar=contexto.ejecutar,
        rutas=proyecto.rutas,
        convenciones=proyecto.convenciones,
        compilacion=proyecto.compilacion,
        nombre_ejecutable=proyecto.identidad.ejecutable,
    )
    print(variantes.formatear_tabla(resultados))
    return 0 if resultados[0].coincide else 1


def ejecutar_permutar(contexto: Contexto) -> int:
    """
    Implementa ``permutar``: busca con mutaciones la forma de C que hace coincidir una funcion.

    Contexto:
        Deja el candidato en ``<build>/permutar/<funcion>/mejor.c``; no escribe en los fuentes.

    Args:
        contexto (Contexto): Contexto de la orden; ``args`` trae los limites de la busqueda.

    Returns:
        int: ``0`` si la funcion coincide, ``1`` si mejoro sin cerrar y ``2`` si no mejoro.

    Raises:
        ValueError: Si las opciones o la funcion no son validas.
        ProcesoError: Si una herramienta falla al preparar el objetivo.

    Ejemplo:
        codigo = ejecutar_permutar(contexto)
    """
    proyecto = contexto.proyecto
    args = contexto.args
    _, rutas_toolchain = _preparar(contexto)
    lock = contexto.lock()
    herramientas = compilacion.resolver_herramientas_compilacion(
        lock, rutas_toolchain.toolchain, contexto.python
    )
    script = resolver_herramienta(lock, rutas_toolchain.toolchain, "asm-differ", "diff")
    opciones = busqueda.Opciones(
        iteraciones=args.iteraciones,
        minutos=args.minutos,
        procesos=args.procesos,
        semilla=args.semilla,
        reanudar=args.reanudar,
    )
    resumen = busqueda.permutar_funcion(
        contexto.raiz,
        args.funcion,
        herramientas,
        script,
        contexto.ejecutar,
        opciones=opciones,
        rutas=proyecto.rutas,
        convenciones=proyecto.convenciones,
        compilacion=proyecto.compilacion,
        nombre_ejecutable=proyecto.identidad.ejecutable,
    )
    print(busqueda.formatear_resumen(resumen, contexto.raiz))
    return resumen.codigo_de_salida


def ejecutar_verificar_config(contexto: Contexto) -> int:
    """
    Implementa ``verificar-config``: cada duplicacion de configuracion es un error.

    Contexto:
        No lee la referencia del ejecutable ni resuelve el disco: solo cruza archivos del proyecto.

    Args:
        contexto (Contexto): Contexto de la orden.

    Returns:
        int: ``1`` si hay alguna duplicacion, ``0`` si no.

    Raises:
        FileNotFoundError: Si falta un archivo de simbolos.

    Ejemplo:
        codigo = ejecutar_verificar_config(contexto)
    """
    errores = infraestructura.verificar_configuracion(
        contexto.raiz, rutas=contexto.proyecto.rutas, convenciones=contexto.proyecto.convenciones
    )
    for error in errores:
        print(f"error: {error}", file=sys.stderr)
    print(f"verificar-config: {len(errores)} errores")
    return 1 if errores else 0

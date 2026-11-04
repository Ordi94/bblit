"""Orden ``progreso``: mide la descompilacion, escribe sus documentos y actualiza la seccion del README.

Capa de aplicacion. Une la medicion (``psxdecomp.progreso``) con el contexto de la linea de ordenes: el
agrupado por subsistemas puede venir del gancho ``entrada_progreso`` del manifiesto, el hash del
commit lo da ``git`` y el SHA-256 esperado sale de la referencia del ejecutable. Los fallos de la
seccion del README, que es secundaria, se convierten en avisos para no perder el resto del informe.
"""

from __future__ import annotations

import sys
from datetime import date

from psxdecomp.cli import plugins
from psxdecomp.cli.contexto import Contexto
from psxdecomp.cli.errores import ERRORES_PROPIOS, motivo_sin_rutas
from psxdecomp.construccion.infraestructura import listar_fuentes_c
from psxdecomp.construccion.salidas import ARCHIVO_PROGRESO
from psxdecomp.diff import coherencia_pendientes
from psxdecomp.progreso import medicion, readme
from psxdecomp.progreso.calculo import Progreso


def _fecha_actual() -> str:
    """Da la fecha local de hoy como ``AAAA-MM-DD`` (sustituible en pruebas)."""
    return date.today().isoformat()


def _actualizar_readme(contexto: Contexto, medido: Progreso) -> None:
    """Reescribe la seccion de progreso del README e informa del resultado."""
    proyecto = contexto.proyecto
    cambio = readme.actualizar_readme(
        contexto.raiz,
        medido,
        _fecha_actual(),
        readme.obtener_hash_corto(contexto.raiz, contexto.ejecutar),
        contexto.referencia().sha256,
        proyecto=proyecto,
    )
    print(f"{proyecto.rutas.readme}: seccion de progreso {'actualizada' if cambio else 'sin cambios'}")


def _actualizar_readme_sin_abortar(contexto: Contexto, medido: Progreso) -> None:
    """
    Actualiza la seccion del README y convierte cualquier fallo en un aviso.

    Contexto:
        La seccion del README es secundaria: el documento de progreso y el resumen en JSON ya
        estan escritos cuando se llega aqui, y abortar perderia los avisos de coherencia y de
        rutinas sin explicar que ``progreso`` emite despues.

    Args:
        contexto (Contexto): Contexto de la orden.
        medido (Progreso): Medicion ya calculada.

    Ejemplo:
        _actualizar_readme_sin_abortar(contexto, medido)
    """
    try:
        _actualizar_readme(contexto, medido)
    except (*ERRORES_PROPIOS, OSError) as error:
        print(
            f"aviso: no se pudo actualizar la seccion de progreso del README: {motivo_sin_rutas(error)}",
            file=sys.stderr,
        )


def ejecutar_progreso(contexto: Contexto) -> int:
    """
    Implementa ``progreso``: mide, escribe el documento y el resumen y actualiza el README.

    Contexto:
        No necesita el disco ni el toolchain. Con ``--sin-readme`` no toca el README. Los avisos de
        rutinas sin comentario y de pendientes desactualizados van a la salida de errores y no cambian
        el codigo de retorno; la incoherencia entre el ensamblador y la tabla de simbolos si.

    Args:
        contexto (Contexto): Contexto de la orden; ``args.sin_readme`` omite la seccion del README.

    Returns:
        int: ``1`` si el ensamblador y el codigo C no cuadran con la tabla de simbolos; ``0`` si no.

    Raises:
        FileNotFoundError: Si falta el archivo de simbolos.
        ValueError: Si la tabla o un archivo C no se pueden interpretar.
        PluginInvalidoError: Si el gancho ``entrada_progreso`` no se carga o da un nombre invalido.

    Ejemplo:
        codigo = ejecutar_progreso(contexto)
    """
    proyecto = contexto.proyecto
    rutas, convenciones = proyecto.rutas, proyecto.convenciones
    medido = medicion.generar_progreso(
        contexto.raiz,
        rutas=rutas,
        convenciones=convenciones,
        zonas=proyecto.zonas,
        comando=proyecto.identidad.comando,
        subsistema=plugins.resolver_agrupador_de_subsistemas(proyecto),
    )
    print(
        f"progreso: {medido.c_juego.funciones} funciones del juego en C de {medido.juego.funciones} "
        f"({medido.c_juego.bytes} de {medido.juego.bytes} bytes, {medido.porcentaje_bytes_juego:.2f} %); "
        f"{len(medido.no_coincidentes)} {convenciones.macro_no_coincidente}; "
        f"{rutas.documento_progreso} y {rutas.build}/{ARCHIVO_PROGRESO} escritos"
    )
    if not contexto.args.sin_readme and proyecto.ruta_absoluta(rutas.readme).is_file():
        _actualizar_readme_sin_abortar(contexto, medido)
    elif not contexto.args.sin_readme:
        print(f"aviso: no existe {rutas.readme}; seccion de progreso omitida", file=sys.stderr)
    if medido.manuscritas:
        print(f"manuscritas: {len(medido.manuscritas)} rutinas escritas a mano siguen en ensamblador")
    for archivo, funcion in medido.sin_comentario:
        aviso = (
            f"aviso: {archivo}: {funcion} sigue en {convenciones.macro_ensamblador} "
            "sin comentario que lo explique"
        )
        print(aviso, file=sys.stderr)
    avisos = coherencia_pendientes.avisos_puntuacion_pendiente(
        contexto.raiz, listar_fuentes_c(contexto.raiz, rutas=rutas), rutas=rutas, convenciones=convenciones
    )
    for aviso in avisos:
        print(f"aviso: {aviso}", file=sys.stderr)
    if medido.coherente is False:
        print(
            f"error: {medido.glabel_en_asm} glabel en {rutas.asm}/ + {medido.funciones_en_c} funciones en C "
            f"no suman las {medido.funciones_totales} de la tabla: ejecute 'split'",
            file=sys.stderr,
        )
        return 1
    return 0

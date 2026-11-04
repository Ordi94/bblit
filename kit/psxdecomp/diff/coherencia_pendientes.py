"""Aviso de coherencia entre la linea de pendiente de un intento y la ultima medicion de ``diff``.

La linea de pendiente (``Pendiente: puntuacion N``, o la que declare ``[convenciones].pendiente``) de
una funcion no coincidente se escribe a mano y se queda vieja cuando cambia la herramienta de medida
(por ejemplo, el limite de lineas de ``asm-differ``). Este modulo la contrasta con
``<build>/diff/<funcion>.resultado.json``, que deja ``diff`` al terminar, y solo cuando esa medicion
es posterior a la ultima edicion del archivo C. Nunca ejecuta ``diff``: sin medicion reciente no dice
nada. Las rutas y la convencion de la linea de pendiente llegan por parametro desde el manifiesto.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from psxdecomp.diff.comparacion import ruta_resultado, validar_funcion
from psxdecomp.diff.fuentes_c import bloques_no_coincidentes, puntuacion_pendiente
from psxdecomp.dominio import Convenciones, Rutas

MAX_BYTES_RESULTADO = 4096


def leer_puntuacion_medida(raiz: Path, funcion: str, referencia_mtime: float, *, rutas: Rutas) -> int | None:
    """
    Lee la ultima puntuacion medida de una funcion si es reciente y tiene la forma esperada.

    Contexto:
        El archivo lo escribe otro proceso en cualquier momento: se trata como entrada no confiable.

    Args:
        raiz (Path): Raiz del proyecto.
        funcion (str): Funcion a consultar.
        referencia_mtime (float): Fecha de modificacion del archivo C; una medicion anterior no es
            reciente.
        rutas (Rutas): Seccion ``[rutas]``; fija la carpeta donde ``diff`` deja sus resultados.

    Returns:
        int | None: La puntuacion, o ``None`` si falta, es anterior a la edicion, es demasiado
        grande, no es JSON, no es de esa funcion, la puntuacion no es un entero no negativo o la
        medicion fue parcial (``truncado``): una cifra parcial no se contrasta con el comentario.

    Ejemplo:
        medida = leer_puntuacion_medida(Path("."), "rutina_a", 0.0, rutas=proyecto.rutas)
    """
    ruta = raiz / ruta_resultado(funcion, rutas=rutas)
    try:
        estado = ruta.stat()
        if estado.st_mtime < referencia_mtime or estado.st_size > MAX_BYTES_RESULTADO:
            return None
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(datos, dict) or datos.get("funcion") != funcion:
        return None
    if datos.get("truncado") is True:
        return None
    puntos = datos.get("puntuacion")
    if isinstance(puntos, bool) or not isinstance(puntos, int) or puntos < 0:
        return None
    return puntos


def avisos_puntuacion_pendiente(
    raiz: Path, textos: Mapping[str, str], *, rutas: Rutas, convenciones: Convenciones
) -> list[str]:
    """
    Avisa de cada intento no coincidente cuya cifra de pendiente difiere de la ultima medicion de ``diff``.

    Contexto:
        Lo imprime la medicion de progreso del proyecto por la salida de errores. Solo informa: la cifra
        se corrige a mano en el comentario, porque ``diff`` no escribe en los fuentes.

    Args:
        raiz (Path): Raiz del proyecto.
        textos (Mapping[str, str]): Texto por archivo C (clave: ruta relativa a la raiz).
        rutas (Rutas): Seccion ``[rutas]`` del manifiesto.
        convenciones (Convenciones): Macro del intento no coincidente y expresion de la linea de
            pendiente.

    Returns:
        list[str]: Un aviso por funcion que difiere, ordenados por archivo y linea; vacia si no hay
        mediciones recientes o todas coinciden.

    Ejemplo:
        avisos = avisos_puntuacion_pendiente(
            Path("."), {"codigo/a.c": texto}, rutas=proyecto.rutas, convenciones=proyecto.convenciones
        )
    """
    avisos: list[str] = []
    for archivo in sorted(textos):
        try:
            referencia = (raiz / archivo).stat().st_mtime
        except OSError:
            continue
        for bloque in bloques_no_coincidentes(textos[archivo], convenciones):
            declarada = puntuacion_pendiente(bloque, convenciones)
            try:
                validar_funcion(bloque.funcion)
            except ValueError:
                continue
            medida = leer_puntuacion_medida(raiz, bloque.funcion, referencia, rutas=rutas)
            if declarada is not None and medida is not None and medida != declarada:
                avisos.append(
                    f"{archivo}:{bloque.linea} {bloque.funcion}: el comentario Pendiente dice "
                    f"{declarada} y la ultima medicion de diff da {medida}"
                )
    return avisos

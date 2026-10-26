"""Aviso de coherencia entre el comentario ``Pendiente`` y la ultima medicion de ``diff``.

El comentario ``Pendiente: puntuacion N`` de una funcion ``NON_MATCHING`` se escribe a mano y se
queda viejo cuando cambia la herramienta de medida (por ejemplo, el limite de lineas de
``asm-differ``). Este modulo lo contrasta con ``build/diff/<funcion>.resultado.json``, que deja
``diff`` al terminar, y solo cuando esa medicion es posterior a la ultima edicion del archivo C.
Nunca ejecuta ``diff``: sin medicion reciente no dice nada.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from tools.reconstruccion.diff import ruta_resultado, validar_funcion
from tools.reconstruccion.fuentes_c import bloques_no_coincidentes, puntuacion_pendiente

MAX_BYTES_RESULTADO = 4096


def leer_puntuacion_medida(raiz: Path, funcion: str, referencia_mtime: float) -> int | None:
    """
    Lee la ultima puntuacion medida de una funcion si es reciente y tiene la forma esperada.

    Contexto:
        El archivo lo escribe otro proceso en cualquier momento: se trata como entrada no confiable.

    Args:
        raiz (Path): Raiz del repositorio.
        funcion (str): Funcion a consultar.
        referencia_mtime (float): Fecha de modificacion del archivo C; una medicion anterior no es
            reciente.

    Returns:
        int | None: La puntuacion, o ``None`` si falta, es anterior a la edicion, es demasiado
        grande, no es JSON, no es de esa funcion o la puntuacion no es un entero no negativo.

    Ejemplo:
        medida = leer_puntuacion_medida(Path("."), "func_80036204", 0.0)
    """
    ruta = raiz / ruta_resultado(funcion)
    try:
        estado = ruta.stat()
        if estado.st_mtime < referencia_mtime or estado.st_size > MAX_BYTES_RESULTADO:
            return None
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(datos, dict) or datos.get("funcion") != funcion:
        return None
    puntos = datos.get("puntuacion")
    if isinstance(puntos, bool) or not isinstance(puntos, int) or puntos < 0:
        return None
    return puntos


def avisos_puntuacion_pendiente(raiz: Path, textos: Mapping[str, str]) -> list[str]:
    """
    Avisa de cada ``NON_MATCHING`` cuya cifra ``Pendiente`` difiere de la ultima medicion de ``diff``.

    Contexto:
        Lo imprime ``progreso`` por la salida de errores. Solo informa: la cifra se corrige a mano
        en el comentario, porque ``diff`` no escribe en ``src/``.

    Args:
        raiz (Path): Raiz del repositorio.
        textos (Mapping[str, str]): Texto por archivo C (clave: ruta relativa a la raiz).

    Returns:
        list[str]: Un aviso por funcion que difiere, ordenados por archivo y linea; vacia si no hay
        mediciones recientes o todas coinciden.

    Ejemplo:
        avisos = avisos_puntuacion_pendiente(Path("."), {"src/a.c": texto})
    """
    avisos: list[str] = []
    for archivo in sorted(textos):
        try:
            referencia = (raiz / archivo).stat().st_mtime
        except OSError:
            continue
        for bloque in bloques_no_coincidentes(textos[archivo]):
            declarada = puntuacion_pendiente(bloque)
            try:
                validar_funcion(bloque.funcion)
            except ValueError:
                continue
            medida = leer_puntuacion_medida(raiz, bloque.funcion, referencia)
            if declarada is not None and medida is not None and medida != declarada:
                avisos.append(
                    f"{archivo}:{bloque.linea} {bloque.funcion}: el comentario Pendiente dice {declarada} "
                    f"y la ultima medicion de diff da {medida}"
                )
    return avisos

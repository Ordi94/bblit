"""Archivo versionado de nombres de funciones y su aplicacion a la tabla de simbolos.

``config/symbols.txt`` se regenera siempre desde las exportaciones de Ghidra y las reglas de
``depuracion``: no se edita a mano. Los nombres que se descubren por otras vias (por ejemplo, la
version de PC del juego) viven en un archivo propio, ``config/nombres_funciones.txt``, con una linea
``0xDIRECCION Nombre  # origen: ...``. Al generar la tabla se aplican a la funcion que empieza en esa
direccion, sin pisar nunca un nombre oficial del SDK identificado por firma.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Final

from tools.ghidra.dominio import (
    LONGITUD_MAXIMA_NOMBRE,
    Funcion,
    Simbolo,
    es_identificador_c,
    tiene_nombre_oficial,
)

MAX_LINEAS_NOMBRES: Final[int] = 10_000
"""Cota de lineas del archivo: el real tiene unas 80."""

_PATRON_LINEA: Final[re.Pattern[str]] = re.compile(
    r"^0x(?P<direccion>[0-9A-Fa-f]{8})\s+(?P<nombre>\S+)\s*(?:#.*)?$"
)


@dataclass(frozen=True, slots=True)
class Choque:
    """Un nombre del archivo que no se aplico y la razon.

    Attributes:
        direccion (int): Direccion de la funcion afectada.
        nombre (str): Nombre propuesto por el archivo.
        motivo (str): ``firma`` (la funcion ya tiene nombre oficial), ``repetido`` (otro simbolo usa ese
            nombre) o ``sin funcion`` (ninguna funcion empieza en esa direccion).
        existente (str): Nombre que se conserva o que ya usa otro simbolo; vacio si no aplica.
    """

    direccion: int
    nombre: str
    motivo: str
    existente: str


def parsear_nombres(texto: str) -> dict[int, str]:
    """
    Lee el archivo de nombres de funciones.

    Contexto:
        Entrada del comando ``simbolos`` (``--nombres``). Es contenido versionado, pero se trata como
        entrada: cada linea se valida y un archivo ambiguo se rechaza entero.

    Args:
        texto (str): Contenido del archivo. Se ignoran lineas vacias y comentarios que empiezan por ``#``.

    Returns:
        dict[int, str]: Direccion a nombre.

    Raises:
        ValueError: Si hay mas de ``MAX_LINEAS_NOMBRES`` lineas, una linea no sigue el formato (con su
            numero), un nombre no es un identificador C valido o excede la longitud maxima, una direccion
            o un nombre aparecen dos veces.

    Ejemplo:
        nombres = parsear_nombres("0x8002FA38 CondCiseq  # origen: version PC")
    """
    lineas = texto.splitlines()
    if len(lineas) > MAX_LINEAS_NOMBRES:
        raise ValueError(f"nombres: mas de {MAX_LINEAS_NOMBRES} lineas")
    nombres: dict[int, str] = {}
    usados: set[str] = set()
    for numero, linea in enumerate(lineas, start=1):
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        coincidencia = _PATRON_LINEA.match(linea.strip())
        if coincidencia is None:
            raise ValueError(f"nombres linea {numero}: formato invalido")
        direccion, nombre = int(coincidencia["direccion"], 16), coincidencia["nombre"]
        if not es_identificador_c(nombre) or len(nombre) > LONGITUD_MAXIMA_NOMBRE:
            raise ValueError(f"nombres linea {numero}: {nombre!r} no es un identificador C valido")
        if direccion in nombres:
            raise ValueError(f"nombres linea {numero}: la direccion 0x{direccion:08X} esta repetida")
        if nombre in usados:
            raise ValueError(f"nombres linea {numero}: el nombre {nombre} esta repetido")
        nombres[direccion] = nombre
        usados.add(nombre)
    return nombres


def aplicar_nombres(
    simbolos: list[Simbolo], funciones: list[Funcion], nombres: Mapping[int, str]
) -> tuple[list[Simbolo], list[Choque]]:
    """
    Aplica los nombres del archivo a los simbolos de funcion que empiezan en esas direcciones.

    Contexto:
        Paso final del comando ``simbolos``, con la tabla ya construida. Un nombre oficial por firma
        siempre gana; un nombre que ya usa otro simbolo (de firma, por defecto o del propio archivo)
        no se aplica, para no generar identificadores duplicados.

    Args:
        simbolos (list[Simbolo]): Tabla de simbolos de funcion (``construir_simbolos``).
        funciones (list[Funcion]): Las funciones de las que salio, para saber cuales tienen firma.
        nombres (Mapping[int, str]): Resultado de ``parsear_nombres``.

    Returns:
        tuple[list[Simbolo], list[Choque]]: Simbolos renombrados, en el mismo orden, y los choques
        ordenados por direccion.

    Ejemplo:
        renombrados, choques = aplicar_nombres(simbolos, refinado.funciones, parsear_nombres(texto))
    """
    por_direccion = {s.direccion: s for s in simbolos}
    con_firma = {f.direccion for f in funciones if tiene_nombre_oficial(f)}
    en_uso = {s.nombre: s.direccion for s in simbolos}
    choques: list[Choque] = []
    aplicados: dict[int, str] = {}
    for direccion in sorted(nombres):
        nombre = nombres[direccion]
        simbolo = por_direccion.get(direccion)
        if simbolo is None:
            choques.append(Choque(direccion, nombre, "sin funcion", ""))
        elif simbolo.nombre == nombre:
            continue
        elif direccion in con_firma:
            choques.append(Choque(direccion, nombre, "firma", simbolo.nombre))
        elif nombre in en_uso:
            choques.append(Choque(direccion, nombre, "repetido", f"0x{en_uso[nombre]:08X}"))
        else:
            aplicados[direccion] = nombre
            en_uso[nombre] = direccion
    renombrados = [
        replace(s, nombre=aplicados[s.direccion]) if s.direccion in aplicados else s for s in simbolos
    ]
    return renombrados, choques

"""Formato de texto de ``config/symbols.txt``.

Una linea por simbolo, con la sintaxis que el desensamblador lee como tabla de nombres:
``nombre = 0xDIRECCION; // type:func size:0xTAMANO``. El modulo convierte en ambos sentidos y
es el unico lugar donde se conoce ese formato.
"""

import csv
import io
import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, cast

from tools.ghidra.dominio import Simbolo, TipoSimbolo, validar_simbolos

_PATRON_LINEA: Final[re.Pattern[str]] = re.compile(
    r"^(?P<nombre>[A-Za-z_][A-Za-z0-9_]*) = 0x(?P<direccion>[0-9A-F]{8}); "
    r"// type:(?P<tipo>func|data) size:0x(?P<tamano>[0-9A-F]{1,8})$"
)

MAX_LINEAS: Final[int] = 100_000
"""Cota de lineas que acepta el lector: una tabla real tiene unos pocos miles."""


def formatear_simbolo(simbolo: Simbolo) -> str:
    """
    Escribe un simbolo como una linea de ``symbols.txt``.

    Contexto:
        Lo usa ``formatear_tabla``; separado para fijar el formato exacto en una sola funcion.

    Args:
        simbolo (Simbolo): Simbolo ya validado.

    Returns:
        str: La linea sin salto de linea, con direccion y tamano en hexadecimal mayuscula.

    Ejemplo:
        linea = formatear_simbolo(Simbolo("DrawSync", 0x80051938, "func", 0x68))
        # "DrawSync = 0x80051938; // type:func size:0x68"
    """
    return f"{simbolo.nombre} = 0x{simbolo.direccion:08X}; // type:{simbolo.tipo} size:0x{simbolo.tamano:X}"


def formatear_tabla(simbolos: list[Simbolo]) -> str:
    """
    Serializa la tabla completa tras validarla.

    Contexto:
        Es lo que escribe el comando ``simbolos`` en ``config/symbols.txt``.

    Args:
        simbolos (list[Simbolo]): Simbolos en orden ascendente de direccion.

    Returns:
        str: Texto con una linea por simbolo y salto de linea final; vacio si no hay simbolos.

    Raises:
        ValueError: Si la tabla no supera ``validar_simbolos``.

    Ejemplo:
        texto = formatear_tabla(construir_simbolos(funciones))
    """
    validar_simbolos(simbolos)
    return "".join(f"{formatear_simbolo(s)}\n" for s in simbolos)


def parsear_tabla(texto: str) -> list[Simbolo]:
    """
    Lee ``symbols.txt`` y valida que cumpla el contrato.

    Contexto:
        Lector propio con el que se comprueba el archivo generado, sin depender de que el
        desensamblador este instalado.

    Args:
        texto (str): Contenido completo del archivo.

    Returns:
        list[Simbolo]: Los simbolos en el orden del archivo.

    Raises:
        ValueError: Si hay mas de ``MAX_LINEAS`` lineas, si una linea no sigue el formato
            (con su numero) o si la tabla no supera ``validar_simbolos``.

    Ejemplo:
        simbolos = parsear_tabla(Path("config/symbols.txt").read_text(encoding="utf-8"))
    """
    lineas = texto.splitlines()
    if len(lineas) > MAX_LINEAS:
        raise ValueError(f"symbols: {len(lineas)} lineas exceden el maximo de {MAX_LINEAS}")
    simbolos: list[Simbolo] = []
    for numero, linea in enumerate(lineas, start=1):
        coincidencia = _PATRON_LINEA.match(linea)
        if coincidencia is None:
            raise ValueError(f"symbols linea {numero}: formato invalido")
        simbolos.append(
            Simbolo(
                nombre=coincidencia["nombre"],
                direccion=int(coincidencia["direccion"], 16),
                tipo=cast(TipoSimbolo, coincidencia["tipo"]),
                tamano=int(coincidencia["tamano"], 16),
            )
        )
    validar_simbolos(simbolos)
    return simbolos


COLUMNAS_NUEVAS: Final[tuple[str, ...]] = (
    "direccion",
    "nombre",
    "tamano",
    "rutina_madre",
    "nombre_madre",
    "operacion",
)


def escribir_atomico(ruta: Path, texto: str) -> None:
    """
    Escribe un archivo de texto sin dejarlo a medias si algo falla.

    Contexto:
        La tabla de simbolos alimenta la particion y la construccion: un archivo truncado dejaria un
        ejecutable que no se puede reconstruir sin avisar. Se escribe en un temporal vecino y se
        reemplaza el destino en una sola operacion; si falla, el archivo anterior queda intacto.

    Args:
        ruta (Path): Archivo destino (su carpeta debe existir).
        texto (str): Contenido en UTF-8 con saltos de linea LF.

    Raises:
        OSError: Si no se puede escribir el temporal o reemplazar el destino.

    Ejemplo:
        escribir_atomico(Path("config/symbols.txt"), texto)
    """
    temporal = ruta.with_name(ruta.name + ".tmp")
    try:
        temporal.write_text(texto, encoding="utf-8", newline="\n")
        os.replace(temporal, ruta)
    finally:
        temporal.unlink(missing_ok=True)


def formatear_nuevas_csv(
    nuevas: Sequence[tuple[int, int]],
    fusionadas: Sequence[tuple[int, int]],
    simbolos: Sequence[Simbolo],
    antes: Mapping[int, str],
) -> str:
    """
    Lista las funciones que la tabla gana al partir bloques y las que pierde al fusionar.

    Contexto:
        Insumo de la particion del ejecutable: dice que simbolos son nuevos, de que rutina madre
        salen y cuales desaparecen absorbidos por otra.

    Args:
        nuevas (Sequence[tuple[int, int]]): Pares ``(direccion, madre)`` de funciones creadas.
        fusionadas (Sequence[tuple[int, int]]): Pares ``(absorbida, principal)``.
        simbolos (Sequence[Simbolo]): Tabla final.
        antes (Mapping[int, str]): Direccion a nombre en la tabla anterior (para las absorbidas).

    Returns:
        str: CSV con LF y las columnas de ``COLUMNAS_NUEVAS``; ``operacion`` es ``partida`` o ``fusionada``.

    Ejemplo:
        texto = formatear_nuevas_csv(refinado.nuevas, refinado.fusionadas, simbolos, nombres_antes)
    """
    por_direccion = {s.direccion: s for s in simbolos}
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(COLUMNAS_NUEVAS)
    for direccion, madre in sorted(nuevas):
        simbolo, padre = por_direccion[direccion], por_direccion[madre]
        escritor.writerow(
            [f"0x{direccion:08X}", simbolo.nombre, simbolo.tamano, f"0x{madre:08X}", padre.nombre, "partida"]
        )
    for absorbida, principal in sorted(fusionadas):
        padre = por_direccion[principal]
        nombre = antes.get(absorbida, "")
        escritor.writerow([f"0x{absorbida:08X}", nombre, 0, f"0x{principal:08X}", padre.nombre, "fusionada"])
    return salida.getvalue()

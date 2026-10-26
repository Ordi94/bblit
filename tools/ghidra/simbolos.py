"""Formato de texto de ``config/symbols.txt``.

Una linea por simbolo, con la sintaxis que el desensamblador lee como tabla de nombres:
``nombre = 0xDIRECCION; // type:func size:0xTAMANO``. El modulo convierte en ambos sentidos y
es el unico lugar donde se conoce ese formato.
"""

import re
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

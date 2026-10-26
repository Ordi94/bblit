"""Lectura defensiva de la exportacion de funciones de Ghidra.

La exportacion es un CSV producido por un proceso externo; aqui se trata como entrada hostil:
se acota el tamano y el numero de filas, se comprueba cada campo y todo error nombra la fila y
el campo sin volcar rutas ni el contenido de la fila.
"""

import csv
import io
from pathlib import Path
from typing import Final

from tools.ghidra.dominio import (
    ALINEACION_FUNCION,
    DIRECCION_BASE,
    DIRECCION_FIN,
    LONGITUD_MAXIMA_NOMBRE,
    TAMANO_SEGMENTO,
    Funcion,
)

COLUMNAS_FUNCIONES: Final[tuple[str, ...]] = (
    "direccion",
    "nombre",
    "tamano",
    "es_libreria",
    "libreria_origen",
    "numero_de_llamadores",
    "nombre_oficial",
    "comentario",
)
"""Cabecera exacta de ``funciones.csv``."""

MAX_BYTES_CSV: Final[int] = 16 * 1024 * 1024
MAX_FILAS: Final[int] = 100_000
MAX_LLAMADORES: Final[int] = 1_000_000
MAX_LONGITUD_ORIGEN: Final[int] = 1024
MAX_LONGITUD_COMENTARIO: Final[int] = 4096


def _entero_hex(valor: str, campo: str, fila: int) -> int:
    """Convierte ``0xNNNN`` a entero o falla nombrando el campo."""
    if not valor.startswith("0x"):
        raise ValueError(f"fila {fila}: {campo} debe empezar por 0x")
    try:
        return int(valor, 16)
    except ValueError:
        raise ValueError(f"fila {fila}: {campo} no es hexadecimal") from None


def _entero_acotado(valor: str, campo: str, fila: int, minimo: int, maximo: int) -> int:
    """Convierte un decimal y comprueba que este en ``[minimo, maximo]``."""
    try:
        numero = int(valor)
    except ValueError:
        raise ValueError(f"fila {fila}: {campo} no es un entero") from None
    if not minimo <= numero <= maximo:
        raise ValueError(f"fila {fila}: {campo}={numero} fuera de rango {minimo}..{maximo}")
    return numero


def _booleano(valor: str, campo: str, fila: int) -> bool:
    """Acepta unicamente ``0`` o ``1``."""
    if valor not in ("0", "1"):
        raise ValueError(f"fila {fila}: {campo} debe ser 0 o 1")
    return valor == "1"


def _texto_acotado(valor: str, campo: str, fila: int, maximo: int, *, obligatorio: bool) -> str:
    """Comprueba longitud y ausencia de caracteres de control (salvo salto de linea en comentarios)."""
    if obligatorio and not valor:
        raise ValueError(f"fila {fila}: {campo} vacio")
    if len(valor) > maximo:
        raise ValueError(f"fila {fila}: {campo} excede {maximo} caracteres")
    if any(ord(c) < 0x20 and c != "\n" for c in valor):
        raise ValueError(f"fila {fila}: {campo} contiene caracteres de control")
    return valor


def _convertir_fila(fila: dict[str, str], numero: int) -> Funcion:
    """Valida una fila del CSV y la convierte en ``Funcion``."""
    direccion = _entero_hex(fila["direccion"], "direccion", numero)
    if not DIRECCION_BASE <= direccion < DIRECCION_FIN:
        raise ValueError(
            f"fila {numero}: direccion=0x{direccion:08X} fuera del segmento "
            f"0x{DIRECCION_BASE:08X}..0x{DIRECCION_FIN:08X}"
        )
    if direccion % ALINEACION_FUNCION != 0:
        raise ValueError(f"fila {numero}: direccion=0x{direccion:08X} no alineada a {ALINEACION_FUNCION}")
    return Funcion(
        direccion=direccion,
        nombre=_texto_acotado(fila["nombre"], "nombre", numero, LONGITUD_MAXIMA_NOMBRE, obligatorio=True),
        tamano=_entero_acotado(fila["tamano"], "tamano", numero, 1, TAMANO_SEGMENTO),
        es_libreria=_booleano(fila["es_libreria"], "es_libreria", numero),
        libreria_origen=_texto_acotado(
            fila["libreria_origen"], "libreria_origen", numero, MAX_LONGITUD_ORIGEN, obligatorio=False
        ),
        llamadores=_entero_acotado(
            fila["numero_de_llamadores"], "numero_de_llamadores", numero, 0, MAX_LLAMADORES
        ),
        nombre_oficial=_booleano(fila["nombre_oficial"], "nombre_oficial", numero),
        comentario=_texto_acotado(
            fila["comentario"], "comentario", numero, MAX_LONGITUD_COMENTARIO, obligatorio=False
        ),
    )


def parsear_funciones_csv(texto: str) -> list[Funcion]:
    """
    Interpreta el contenido de ``funciones.csv``.

    Contexto:
        Primer paso del comando ``simbolos`` y del comando ``informe``; el resto del paquete
        confia en que esta funcion ya valido las cotas.

    Args:
        texto (str): Contenido completo del CSV, con cabecera.

    Returns:
        list[Funcion]: Funciones en el orden del archivo.

    Raises:
        ValueError: Si la cabecera no es exactamente ``COLUMNAS_FUNCIONES``, si hay mas de
            ``MAX_FILAS`` filas, si una fila tiene un numero distinto de campos o si algun campo
            esta fuera de rango (el mensaje nombra la fila y el campo).

    Ejemplo:
        funciones = parsear_funciones_csv(Path("funciones.csv").read_text(encoding="utf-8"))
    """
    lector = csv.reader(io.StringIO(texto, newline=""))
    cabecera = next(lector, None)
    if cabecera is None or tuple(cabecera) != COLUMNAS_FUNCIONES:
        raise ValueError("funciones.csv: la cabecera no coincide con las columnas esperadas")
    funciones: list[Funcion] = []
    for numero, valores in enumerate(lector, start=2):
        if len(funciones) >= MAX_FILAS:
            raise ValueError(f"funciones.csv: mas de {MAX_FILAS} filas")
        if len(valores) != len(COLUMNAS_FUNCIONES):
            raise ValueError(f"fila {numero}: se esperaban {len(COLUMNAS_FUNCIONES)} campos")
        funciones.append(_convertir_fila(dict(zip(COLUMNAS_FUNCIONES, valores, strict=True)), numero))
    return funciones


def leer_funciones_csv(ruta: Path) -> list[Funcion]:
    """
    Lee y valida un ``funciones.csv`` del disco.

    Contexto:
        Capa de entrada/salida sobre ``parsear_funciones_csv``; comprueba el tamano antes de
        cargar el archivo en memoria.

    Args:
        ruta (Path): Ruta del CSV exportado.

    Returns:
        list[Funcion]: Funciones validadas.

    Raises:
        ValueError: Si el archivo supera ``MAX_BYTES_CSV``, no es UTF-8 o su contenido no es
            valido segun ``parsear_funciones_csv``.
        FileNotFoundError: Si la ruta no existe.

    Ejemplo:
        funciones = leer_funciones_csv(Path("analisis/ghidra/funciones.csv"))
    """
    if ruta.stat().st_size > MAX_BYTES_CSV:
        raise ValueError(f"funciones.csv: el archivo excede {MAX_BYTES_CSV} bytes")
    try:
        texto = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ValueError("funciones.csv: la codificacion no es UTF-8") from None
    return parsear_funciones_csv(texto)

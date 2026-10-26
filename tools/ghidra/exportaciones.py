"""Lectura defensiva de las exportaciones de datos de Ghidra: referencias y cadenas.

``xrefs_datos.csv`` (dato, tamano, funciones que lo usan) y ``strings.csv`` (direccion, longitud,
texto) los produce un proceso externo, asi que se tratan como entrada hostil: cabecera exacta,
filas acotadas y cada campo comprobado. Los errores nombran la fila y el campo, nunca el contenido.
"""

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from tools.ghidra.lectura import MAX_BYTES_CSV, MAX_FILAS

COLUMNAS_XREFS: Final[tuple[str, ...]] = (
    "direccion_dato",
    "tamano",
    "funciones_que_lo_usan",
    "lecturas",
    "escrituras",
)
COLUMNAS_CADENAS: Final[tuple[str, ...]] = ("direccion", "longitud", "texto")
MAX_FUNCIONES_POR_DATO: Final[int] = 5_000
"""Cota de funciones por dato: el real llega a unas decenas."""
MAX_LONGITUD_TEXTO: Final[int] = 4096
MAX_CONTADOR: Final[int] = 10_000_000


@dataclass(frozen=True)
class ReferenciaDato:
    """Un dato y las funciones que lo usan segun Ghidra."""

    direccion: int
    tamano: int
    funciones: tuple[int, ...]
    lecturas: int
    escrituras: int


@dataclass(frozen=True)
class Cadena:
    """Cadena de texto hallada por Ghidra en el ejecutable."""

    direccion: int
    longitud: int
    texto: str


def _hexadecimal(valor: str, campo: str, fila: int) -> int:
    """Convierte ``0xNNNN`` a entero (32 bits) o falla nombrando el campo."""
    if not valor.startswith("0x"):
        raise ValueError(f"fila {fila}: {campo} debe empezar por 0x")
    try:
        numero = int(valor, 16)
    except ValueError:
        raise ValueError(f"fila {fila}: {campo} no es hexadecimal") from None
    if not 0 <= numero <= 0xFFFFFFFF:
        raise ValueError(f"fila {fila}: {campo} excede 32 bits")
    return numero


def _contador(valor: str, campo: str, fila: int) -> int:
    """Convierte un decimal no negativo y acotado."""
    try:
        numero = int(valor)
    except ValueError:
        raise ValueError(f"fila {fila}: {campo} no es un entero") from None
    if not 0 <= numero <= MAX_CONTADOR:
        raise ValueError(f"fila {fila}: {campo}={numero} fuera de rango 0..{MAX_CONTADOR}")
    return numero


def _filas(texto: str, cabecera: tuple[str, ...], archivo: str) -> list[tuple[int, list[str]]]:
    """Lee las filas de un CSV comprobando cabecera, numero de filas y numero de campos."""
    lector = csv.reader(io.StringIO(texto, newline=""))
    primera = next(lector, None)
    if primera is None or tuple(primera) != cabecera:
        raise ValueError(f"{archivo}: la cabecera no coincide con las columnas esperadas")
    filas: list[tuple[int, list[str]]] = []
    for numero, valores in enumerate(lector, start=2):
        if len(filas) >= MAX_FILAS:
            raise ValueError(f"{archivo}: mas de {MAX_FILAS} filas")
        if len(valores) != len(cabecera):
            raise ValueError(f"fila {numero}: se esperaban {len(cabecera)} campos")
        filas.append((numero, valores))
    return filas


def parsear_xrefs_csv(texto: str) -> list[ReferenciaDato]:
    """
    Interpreta el contenido de ``xrefs_datos.csv``.

    Contexto:
        Alimenta el contexto de tipos para ``m2c`` y la comprobacion cruzada de los datos
        compartidos que calcula el grafo.

    Args:
        texto (str): Contenido completo del CSV, con cabecera.

    Returns:
        list[ReferenciaDato]: Referencias en el orden del archivo.

    Raises:
        ValueError: Si la cabecera no coincide, hay demasiadas filas o funciones por dato, o un
            campo no es valido (el mensaje nombra la fila y el campo).

    Ejemplo:
        referencias = parsear_xrefs_csv(Path("xrefs_datos.csv").read_text(encoding="utf-8"))
    """
    referencias: list[ReferenciaDato] = []
    for numero, valores in _filas(texto, COLUMNAS_XREFS, "xrefs_datos.csv"):
        partes = [p for p in valores[2].split(";") if p]
        if len(partes) > MAX_FUNCIONES_POR_DATO:
            raise ValueError(f"fila {numero}: funciones_que_lo_usan excede {MAX_FUNCIONES_POR_DATO}")
        referencias.append(
            ReferenciaDato(
                direccion=_hexadecimal(valores[0], "direccion_dato", numero),
                tamano=_contador(valores[1], "tamano", numero),
                funciones=tuple(_hexadecimal(p, "funciones_que_lo_usan", numero) for p in partes),
                lecturas=_contador(valores[3], "lecturas", numero),
                escrituras=_contador(valores[4], "escrituras", numero),
            )
        )
    return referencias


def parsear_cadenas_csv(texto: str) -> list[Cadena]:
    """
    Interpreta el contenido de ``strings.csv``.

    Contexto:
        Las cadenas son la evidencia con la que se nombran los subsistemas y se detectan los
        limites entre archivos de origen.

    Args:
        texto (str): Contenido completo del CSV, con cabecera.

    Returns:
        list[Cadena]: Cadenas en el orden del archivo.

    Raises:
        ValueError: Si la cabecera no coincide, hay demasiadas filas o un campo no es valido.

    Ejemplo:
        cadenas = parsear_cadenas_csv(Path("strings.csv").read_text(encoding="utf-8"))
    """
    cadenas: list[Cadena] = []
    for numero, valores in _filas(texto, COLUMNAS_CADENAS, "strings.csv"):
        if len(valores[2]) > MAX_LONGITUD_TEXTO:
            raise ValueError(f"fila {numero}: texto excede {MAX_LONGITUD_TEXTO} caracteres")
        cadenas.append(
            Cadena(
                direccion=_hexadecimal(valores[0], "direccion", numero),
                longitud=_contador(valores[1], "longitud", numero),
                texto=valores[2],
            )
        )
    return cadenas


def _leer_texto(ruta: Path, archivo: str) -> str:
    """Lee un CSV acotando el tamano y exigiendo UTF-8."""
    if ruta.stat().st_size > MAX_BYTES_CSV:
        raise ValueError(f"{archivo}: el archivo excede {MAX_BYTES_CSV} bytes")
    try:
        return ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ValueError(f"{archivo}: la codificacion no es UTF-8") from None


def leer_xrefs_csv(ruta: Path) -> list[ReferenciaDato]:
    """
    Lee y valida un ``xrefs_datos.csv`` del disco.

    Contexto:
        Capa de entrada/salida sobre ``parsear_xrefs_csv``.

    Args:
        ruta (Path): Ruta del CSV exportado.

    Returns:
        list[ReferenciaDato]: Referencias validadas.

    Raises:
        ValueError: Si el archivo es demasiado grande, no es UTF-8 o su contenido es invalido.
        FileNotFoundError: Si la ruta no existe.

    Ejemplo:
        referencias = leer_xrefs_csv(Path("analisis/ghidra/xrefs_datos.csv"))
    """
    return parsear_xrefs_csv(_leer_texto(ruta, "xrefs_datos.csv"))


def leer_cadenas_csv(ruta: Path) -> list[Cadena]:
    """
    Lee y valida un ``strings.csv`` del disco.

    Contexto:
        Capa de entrada/salida sobre ``parsear_cadenas_csv``.

    Args:
        ruta (Path): Ruta del CSV exportado.

    Returns:
        list[Cadena]: Cadenas validadas.

    Raises:
        ValueError: Si el archivo es demasiado grande, no es UTF-8 o su contenido es invalido.
        FileNotFoundError: Si la ruta no existe.

    Ejemplo:
        cadenas = leer_cadenas_csv(Path("analisis/ghidra/strings.csv"))
    """
    return parsear_cadenas_csv(_leer_texto(ruta, "strings.csv"))

"""Datos sinteticos para las pruebas: ninguna exportacion real entra al repositorio."""

import csv
import io

from tools.ghidra.dominio import Funcion
from tools.ghidra.lectura import COLUMNAS_FUNCIONES


def funcion(
    direccion: int = 0x80014A00,
    nombre: str = "func",
    tamano: int = 8,
    *,
    es_libreria: bool = False,
    libreria_origen: str = "",
    llamadores: int = 0,
    nombre_oficial: bool = False,
    comentario: str = "",
) -> Funcion:
    """Construye una ``Funcion`` con valores por defecto validos."""
    return Funcion(
        direccion=direccion,
        nombre=nombre,
        tamano=tamano,
        es_libreria=es_libreria,
        libreria_origen=libreria_origen,
        llamadores=llamadores,
        nombre_oficial=nombre_oficial,
        comentario=comentario,
    )


def fila(**cambios: str) -> list[str]:
    """Devuelve una fila de ``funciones.csv`` valida con los campos indicados sustituidos."""
    base = {
        "direccion": "0x80014A08",
        "nombre": "FUN_80014a08",
        "tamano": "36",
        "es_libreria": "0",
        "libreria_origen": "",
        "numero_de_llamadores": "1",
        "nombre_oficial": "0",
        "comentario": "",
    }
    base.update(cambios)
    return [base[columna] for columna in COLUMNAS_FUNCIONES]


def csv_funciones(filas: list[list[str]], cabecera: tuple[str, ...] = COLUMNAS_FUNCIONES) -> str:
    """Serializa filas como lo hace el exportador: LF, comillas solo cuando hacen falta."""
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(cabecera)
    escritor.writerows(filas)
    return salida.getvalue()


MUESTRA = csv_funciones(
    [
        fila(
            direccion="0x80014A00",
            nombre="__main",
            tamano="8",
            es_libreria="1",
            libreria_origen="2MBYTE.OBJ/2MBYTE.OBJ|LIBSN.LIB/SNMAIN.OBJ",
            nombre_oficial="1",
        ),
        fila(direccion="0x80016414", nombre="main", tamano="2040"),
        fila(direccion="0x80016C0C", nombre="FUN_80016c0c", tamano="100", numero_de_llamadores="3"),
        fila(
            direccion="0x80045DA0",
            nombre="DecDCTReset",
            tamano="96",
            es_libreria="1",
            libreria_origen="LIBPRESS.LIB/DECDCT.OBJ",
            nombre_oficial="1",
            comentario="Possible A.OBJ/uno\nPossible B.OBJ/dos",
        ),
        fila(
            direccion="0x80045F28",
            nombre="LIBPRESS_OBJ_188",
            tamano="44",
            es_libreria="1",
            libreria_origen="LIBPRESS.LIB/LIBPRESS.OBJ",
        ),
    ]
)

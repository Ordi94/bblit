"""Contexto de tipos en C para ``m2c``.

``m2c`` produce borradores mucho mas legibles cuando conoce los prototipos de las funciones que
se llaman y el tipo de los datos globales. Este modulo los deriva de las exportaciones de Ghidra:
la primera linea de cada ``decomp/<direccion>_<nombre>.c`` trae la firma que Ghidra infirio (con
las firmas de Psy-Q aplicadas en las funciones de libreria), y ``xrefs_datos.csv`` da el tamano
de cada dato. Es logica pura; la lectura de archivos vive en ``borradores``.
"""

import re
from collections.abc import Iterable, Sequence
from typing import Final

from tools.ghidra.dominio import Simbolo
from tools.ghidra.exportaciones import ReferenciaDato

CABECERA_TIPOS: Final[str] = """typedef signed char s8;
typedef unsigned char u8;
typedef signed short s16;
typedef unsigned short u16;
typedef signed int s32;
typedef unsigned int u32;
typedef float f32;
typedef double f64;
"""
"""Tipos enteros fijos que ``m2c`` reconoce y que usa todo el contexto."""

_TIPOS_ESCALARES: Final[dict[str, str]] = {
    "void": "void",
    "int": "s32",
    "long": "s32",
    "undefined4": "s32",
    "uint": "u32",
    "ulong": "u32",
    "unsigned int": "u32",
    "unsigned long": "u32",
    "short": "s16",
    "ushort": "u16",
    "undefined2": "u16",
    "unsigned short": "u16",
    "char": "s8",
    "signed char": "s8",
    "uchar": "u8",
    "byte": "u8",
    "bool": "u8",
    "undefined": "u8",
    "undefined1": "u8",
    "unsigned char": "u8",
    "float": "f32",
    "double": "f64",
}
_CALIFICADORES: Final[frozenset[str]] = frozenset({"const", "volatile", "struct", "union", "enum"})
_COMENTARIOS: Final[re.Pattern[str]] = re.compile(r"/\*.*?\*/", re.DOTALL)
_CABECERA: Final[re.Pattern[str]] = re.compile(
    r"^(?P<retorno>[A-Za-z_][\w \*]*?)\s*\b(?P<nombre>[A-Za-z_]\w*)\s*\((?P<parametros>[^()]*)\)$"
)
_TAMANO_DATO: Final[dict[int, str]] = {1: "u8", 2: "u16", 4: "s32"}
MAX_TAMANO_ARREGLO: Final[int] = 0x10000
"""Cota del tamano de un dato declarado como arreglo de bytes."""


def _tipo_c(texto: str) -> str | None:
    """Traduce un tipo de Ghidra a uno que ``m2c`` conoce; ``None`` si no se puede."""
    palabras = [p for p in texto.replace("*", " * ").split() if p not in _CALIFICADORES]
    if "*" in palabras:
        return "void *"
    base = " ".join(palabras)
    return _TIPOS_ESCALARES.get(base)


def _separar_tipo_y_nombre(declaracion: str) -> str | None:
    """Quita el nombre de un parametro y devuelve su tipo; ``None`` si no hay tipo."""
    texto = declaracion.replace("*", " * ").split()
    if len(texto) < 2:
        return None
    return " ".join(texto[:-1])


def extraer_prototipo(texto_c: str, nombre: str) -> str | None:
    """
    Convierte la firma de una funcion decompilada por Ghidra en un prototipo para ``m2c``.

    Contexto:
        Se aplica a cada ``decomp/<direccion>_<nombre>.c`` al construir ``contexto_m2c.c``. Si la
        firma usa un tipo que no se puede traducir con certeza (estructuras por valor, punteros a
        funcion, convenciones de llamada), se omite el prototipo y ``m2c`` infiere la funcion.

    Args:
        texto_c (str): Contenido del archivo ``.c`` de Ghidra.
        nombre (str): Nombre del simbolo en ``config/symbols.txt``, que sustituye al de Ghidra.

    Returns:
        str | None: Linea ``tipo nombre(tipos);`` o ``None`` si no hay firma traducible.

    Ejemplo:
        linea = extraer_prototipo("int FUN_80018c68(int param_1,MATRIX *param_2) { }", "func_80018C68")
        # "s32 func_80018C68(s32, void *);"
    """
    cabecera = " ".join(_COMENTARIOS.sub("", texto_c).split("{", 1)[0].split())
    coincidencia = _CABECERA.match(cabecera)
    if coincidencia is None:
        return None
    retorno = _tipo_c(coincidencia["retorno"])
    if retorno is None:
        return None
    parametros = coincidencia["parametros"].strip()
    if parametros in ("", "void"):
        return f"{retorno} {nombre}(void);"
    tipos: list[str] = []
    for parametro in parametros.split(","):
        tipo = _separar_tipo_y_nombre(parametro.strip())
        traducido = None if tipo is None else _tipo_c(tipo)
        if traducido is None or traducido == "void":
            return None
        tipos.append(traducido)
    return f"{retorno} {nombre}({', '.join(tipos)});"


def declarar_dato(referencia: ReferenciaDato) -> str | None:
    """
    Declara un dato global a partir de su tamano.

    Contexto:
        Los datos se declaran sin signo en 1 y 2 bytes y con signo en 4: Ghidra no informa la
        signedness y ``m2c`` la corrige si el codigo usa ``lb``/``lh``.

    Args:
        referencia (ReferenciaDato): Dato con su direccion y tamano segun Ghidra.

    Returns:
        str | None: Linea ``extern`` con el nombre ``D_<direccion>``, o ``None`` si el tamano es
        desconocido (0) o excede ``MAX_TAMANO_ARREGLO``.

    Ejemplo:
        linea = declarar_dato(ReferenciaDato(0x80010000, 4, (), 1, 1))  # "extern s32 D_80010000;"
    """
    nombre = f"D_{referencia.direccion:08X}"
    escalar = _TAMANO_DATO.get(referencia.tamano)
    if escalar is not None:
        return f"extern {escalar} {nombre};"
    if 0 < referencia.tamano <= MAX_TAMANO_ARREGLO:
        return f"extern u8 {nombre}[{referencia.tamano}];"
    return None


def construir_contexto(
    simbolos: Sequence[Simbolo],
    prototipos: dict[int, str],
    datos: Iterable[ReferenciaDato],
) -> str:
    """
    Arma el archivo ``contexto_m2c.c``.

    Contexto:
        Se entrega a ``m2c`` con ``--context`` para todas las funciones, de modo que las llamadas
        entre ellas y los accesos a datos queden tipados de forma consistente.

    Args:
        simbolos (Sequence[Simbolo]): Tabla de simbolos; sus rangos de funcion excluyen datos.
        prototipos (dict[int, str]): Prototipo ya traducido por direccion de funcion.
        datos (Iterable[ReferenciaDato]): Datos de ``xrefs_datos.csv``.

    Returns:
        str: Texto C con los tipos, los prototipos por direccion y los datos por direccion.

    Ejemplo:
        texto = construir_contexto(simbolos, prototipos, referencias)
    """
    rangos = sorted((s.direccion, s.direccion + s.tamano) for s in simbolos)
    lineas = [CABECERA_TIPOS]
    lineas += [prototipos[direccion] for direccion in sorted(prototipos)]
    declaraciones: dict[int, str] = {}
    for dato in datos:
        if any(inicio <= dato.direccion < fin for inicio, fin in rangos):
            continue
        linea = declarar_dato(dato)
        if linea is not None:
            declaraciones[dato.direccion] = linea
    lineas += [declaraciones[d] for d in sorted(declaraciones)]
    return "\n".join(lineas) + "\n"

"""La operacion escrita en dos sentencias debe estar declarada junto al codigo y en su tabla.

Partir una operacion en dos sentencias sobre la misma variable solo se admite con las condiciones del
apartado de ``docs/DESCOMPILACION.md`` que la regula. Cada uso lleva junto a las sentencias un comentario
de una linea que empieza por «Operacion en dos sentencias:» y cita la instruccion del original, y la
funcion tiene una fila en la tabla del apartado con sus operaciones numeradas. Estas pruebas cruzan
``src/`` con esa tabla en los dos sentidos para que un uso nuevo no entre sin su fila y una fila no
sobreviva a las sentencias que describia. No comprueban las cifras. Solo leen archivos.
"""

import re
from typing import NamedTuple

from tools.proyecto import RAIZ_REPOSITORIO

ENCABEZADO_DEL_APARTADO = "## Operación escrita en dos sentencias con causa en la expansión"
MARCA = "Operacion en dos sentencias:"
ESTADO_COINCIDE = "coincide"
NUMEROS_EN_LETRA = {"una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8}

_DEFINICION = re.compile(r"^[A-Za-z_][\w \t\*]*?[\s\*](\w+)\([^;]*\)\s*\{?\s*$")
_COMENTARIO_CON_MARCA = re.compile(rf"/\*\s*{re.escape(MARCA)}")
_COMENTARIO_EN_UNA_LINEA = re.compile(rf"^\s*/\*\s*{re.escape(MARCA)}(?:(?!\*/).)*\*/\s*$")
_FILA = re.compile(r"^\|\s*`(\w+)`\s*\|\s*`([^`]+)`\s*\|(.*)\|\s*$")
_SEPARADOR_DE_CELDAS = re.compile(r"(?<!\\)\|")
_NUMERO_DE_OPERACION = re.compile(r"(?:^|\s)\((\d+)\)\s")
_DIRECCION = re.compile(r"\b0x800[0-9A-Fa-f]{5}\b")
_CUENTA_DE_FUNCIONES = re.compile(r"Hay (\w+) funci(?:ón|ones) con usos")
_INCLUDE_ASM = re.compile(r'^\s*INCLUDE_ASM\(\s*"[^"]*"\s*,\s*(\w+)\s*\)\s*;', re.MULTILINE)


class Comentario(NamedTuple):
    """Un comentario de operacion en dos sentencias hallado en un archivo de ``src/``."""

    funcion: str
    archivo: str
    linea: int
    texto: str


class Fila(NamedTuple):
    """Una fila de la tabla de usos, con sus celdas de sentencias, instrucciones, cifras y estado."""

    funcion: str
    archivo: str
    sentencias: str
    instrucciones: str
    cifras: str
    estado: str


def comentarios_de(texto: str, archivo: str) -> list[Comentario]:
    """
    Localiza los comentarios de operacion en dos sentencias de un archivo.

    Contexto:
        Es la mitad «codigo» del cruce entre ``src/`` y la tabla del apartado.

    Args:
        texto (str): Contenido del archivo ``.c``.
        archivo (str): Ruta relativa con la que la tabla nombra el archivo.

    Returns:
        list[Comentario]: Un elemento por comentario, con la funcion cuya definicion lo precede
        (cadena vacia si no lo precede ninguna) y la linea completa donde empieza.

    Ejemplo:
        comentarios_de(fuente, "src/menus_e_interfaz.c")
    """
    hallados: list[Comentario] = []
    funcion = ""
    for numero, linea in enumerate(texto.splitlines(), start=1):
        definicion = _DEFINICION.match(linea)
        if definicion is not None:
            funcion = definicion.group(1)
        if _COMENTARIO_CON_MARCA.search(linea):
            hallados.append(Comentario(funcion, archivo, numero, linea))
    return hallados


def filas_de(documento: str) -> list[Fila]:
    """
    Lee la tabla de usos del apartado que regula la operacion en dos sentencias.

    Contexto:
        Es la mitad «documento» del cruce entre ``src/`` y la tabla del apartado.

    Args:
        documento (str): Contenido de ``docs/DESCOMPILACION.md``.

    Returns:
        list[Fila]: Las filas cuya primera y segunda celda son una funcion y un archivo entre comillas.

    Raises:
        ValueError: Si el documento no tiene el apartado.

    Ejemplo:
        filas = filas_de(documento)
    """
    filas: list[Fila] = []
    for linea in _apartado(documento).splitlines():
        coincidencia = _FILA.match(linea)
        if coincidencia is None:
            continue
        funcion, archivo, resto = coincidencia.groups()
        celdas = [celda.strip() for celda in _SEPARADOR_DE_CELDAS.split(resto)]
        sentencias, instrucciones, cifras, estado = celdas
        filas.append(Fila(funcion, archivo, sentencias, instrucciones, cifras, estado))
    return filas


def _apartado(documento: str) -> str:
    inicio = documento.index(ENCABEZADO_DEL_APARTADO)
    siguiente = documento.find("\n## ", inicio + 1)
    return documento[inicio : siguiente if siguiente != -1 else len(documento)]


def _numeracion(celda: str) -> list[int]:
    return [int(numero) for numero in _NUMERO_DE_OPERACION.findall(celda)]


def incumplimientos(
    comentarios: list[Comentario], filas: list[Fila], pendientes: frozenset[str]
) -> list[str]:
    """
    Cruza los comentarios de ``src/`` con las filas de la tabla.

    Contexto:
        La usan la prueba sobre el repositorio y las pruebas de cada regla con textos de ejemplo.

    Args:
        comentarios (list[Comentario]): Comentarios hallados en ``src/``.
        filas (list[Fila]): Filas de la tabla del apartado.
        pendientes (frozenset[str]): Funciones que siguen en ``INCLUDE_ASM``.

    Returns:
        list[str]: Un mensaje por incumplimiento; vacia si el codigo y la tabla concuerdan.

    Ejemplo:
        assert incumplimientos(comentarios, filas, frozenset()) == []
    """
    errores: list[str] = []
    por_funcion = {fila.funcion: fila for fila in filas}
    if len(por_funcion) != len(filas):
        errores.append("la tabla repite una funcion")
    for comentario in comentarios:
        donde = f"{comentario.archivo}:{comentario.linea} ({comentario.funcion})"
        fila = por_funcion.get(comentario.funcion)
        if fila is None or fila.archivo != comentario.archivo:
            errores.append(f"{donde}: comentario sin fila de esa funcion y archivo en la tabla")
            continue
        if not _COMENTARIO_EN_UNA_LINEA.match(comentario.texto):
            errores.append(f"{donde}: el comentario no abre y cierra en la misma linea")
        citadas = {direccion.lower() for direccion in _DIRECCION.findall(comentario.texto)}
        en_la_fila = {direccion.lower() for direccion in _DIRECCION.findall(fila.instrucciones)}
        if not citadas & en_la_fila:
            errores.append(f"{donde}: el comentario no cita una direccion de la fila")
    for fila in filas:
        numeracion = _numeracion(fila.sentencias)
        if not numeracion or numeracion != list(range(1, len(numeracion) + 1)):
            errores.append(f"{fila.funcion}: las operaciones de la fila no estan numeradas desde (1)")
        if _numeracion(fila.instrucciones) != numeracion or _numeracion(fila.cifras) != numeracion:
            errores.append(
                f"{fila.funcion}: instrucciones o cifras no llevan la numeracion de las sentencias"
            )
        usos = sum(1 for c in comentarios if c.funcion == fila.funcion and c.archivo == fila.archivo)
        if usos != len(numeracion):
            errores.append(
                f"{fila.funcion}: la fila tiene {len(numeracion)} operaciones y src {usos} comentarios"
            )
        if fila.estado == ESTADO_COINCIDE and fila.funcion in pendientes:
            errores.append(f"{fila.funcion}: la fila dice que coincide y la funcion sigue pendiente")
    return errores


def _documento() -> str:
    return (RAIZ_REPOSITORIO / "docs" / "DESCOMPILACION.md").read_text(encoding="utf-8")


def _fuentes() -> dict[str, str]:
    return {
        f"src/{ruta.name}": ruta.read_text(encoding="utf-8")
        for ruta in sorted((RAIZ_REPOSITORIO / "src").glob("*.c"))
    }


def test_cada_comentario_de_src_tiene_su_uso_en_la_tabla_y_cada_fila_sus_comentarios() -> None:
    fuentes = _fuentes()
    comentarios = [c for archivo, texto in fuentes.items() for c in comentarios_de(texto, archivo)]
    pendientes = frozenset(nombre for texto in fuentes.values() for nombre in _INCLUDE_ASM.findall(texto))
    filas = filas_de(_documento())
    assert filas, "la tabla de operaciones en dos sentencias no tiene filas"
    assert incumplimientos(comentarios, filas, pendientes) == []


def test_el_numero_de_funciones_anunciado_es_el_de_filas_de_la_tabla() -> None:
    documento = _documento()
    anunciado = _CUENTA_DE_FUNCIONES.search(_apartado(documento))
    assert anunciado is not None
    assert NUMEROS_EN_LETRA[anunciado.group(1)] == len(filas_de(documento))


FUENTE_DE_EJEMPLO = """void func_80010000(s32 a)
{
    /* Operacion en dos sentencias: el `sll` escribe la variable, como `sll v0,v0,8` (0x80010004). */
    a <<= 8;
    a >>= 8;
}
"""
FILA_DE_EJEMPLO = Fila(
    "func_80010000",
    "src/ejemplo.c",
    "(1) `a <<= 8; a >>= 8;`",
    "(1) `sll v0,v0,8` en `0x80010004`",
    "(1) 10",
    ESTADO_COINCIDE,
)


def _cruce(
    fuente: str = FUENTE_DE_EJEMPLO,
    filas: list[Fila] | None = None,
    pendientes: frozenset[str] = frozenset(),
) -> list[str]:
    return incumplimientos(
        comentarios_de(fuente, "src/ejemplo.c"), [FILA_DE_EJEMPLO] if filas is None else filas, pendientes
    )


def test_un_uso_con_su_comentario_y_su_fila_se_acepta() -> None:
    assert _cruce() == []


def test_un_comentario_sin_fila_en_la_tabla_se_rechaza() -> None:
    assert any("sin fila" in error for error in _cruce(filas=[]))


def test_una_fila_que_nombra_otro_archivo_no_ampara_el_comentario() -> None:
    errores = _cruce(filas=[FILA_DE_EJEMPLO._replace(archivo="src/otro.c")])
    assert any("sin fila" in error for error in errores)
    assert any("src 0 comentarios" in error for error in errores)


def test_una_fila_sin_sus_comentarios_en_src_se_rechaza() -> None:
    assert any("src 0 comentarios" in error for error in _cruce(fuente="void func_80010000(s32 a)\n{\n}\n"))


def test_una_fila_con_mas_operaciones_que_comentarios_se_rechaza() -> None:
    fila = FILA_DE_EJEMPLO._replace(
        sentencias="(1) `a` (2) `b`",
        instrucciones="(1) `0x80010004` (2) `0x80010008`",
        cifras="(1) 10 (2) 20",
    )
    assert any("2 operaciones y src 1" in error for error in _cruce(filas=[fila]))


def test_unas_cifras_sin_la_numeracion_de_las_sentencias_se_rechazan() -> None:
    errores = _cruce(filas=[FILA_DE_EJEMPLO._replace(cifras="10")])
    assert any("numeracion" in error for error in errores)


def test_un_comentario_que_ocupa_dos_lineas_se_rechaza() -> None:
    fuente = FUENTE_DE_EJEMPLO.replace("(0x80010004). */", "(0x80010004).\n     * Sigue. */")
    assert any("misma linea" in error for error in _cruce(fuente=fuente))


def test_un_comentario_que_cita_una_direccion_ajena_a_la_fila_se_rechaza() -> None:
    fuente = FUENTE_DE_EJEMPLO.replace("0x80010004", "0x80010100")
    assert any("direccion de la fila" in error for error in _cruce(fuente=fuente))


def test_una_funcion_pendiente_no_puede_figurar_como_que_coincide() -> None:
    errores = _cruce(pendientes=frozenset({"func_80010000"}))
    assert any("sigue pendiente" in error for error in errores)


def test_una_funcion_con_dos_filas_se_rechaza() -> None:
    errores = _cruce(filas=[FILA_DE_EJEMPLO, FILA_DE_EJEMPLO])
    assert any("repite" in error for error in errores)


def test_las_barras_escapadas_de_una_celda_no_parten_la_fila() -> None:
    documento = (
        f"{ENCABEZADO_DEL_APARTADO}\n\n"
        "| `func_80010000` | `src/ejemplo.c` | (1) `a \\|= 1;` | (1) `0x80010004` | (1) 10 | coincide |\n"
    )
    assert filas_de(documento)[0].sentencias == "(1) `a \\|= 1;`"

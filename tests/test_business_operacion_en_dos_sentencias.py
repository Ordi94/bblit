"""La operacion escrita en dos sentencias debe estar declarada junto al codigo y en su tabla.

Partir una operacion en dos sentencias sobre la misma variable solo se admite con las condiciones del
apartado de ``docs/DESCOMPILACION.md`` que la regula. Cada uso lleva junto a las sentencias un comentario
de una linea que empieza por «Operacion en dos sentencias:» y cita la instruccion del original, y la
funcion tiene una fila en la tabla del apartado con sus operaciones numeradas. Estas pruebas cruzan
``src/`` con esa tabla en los dos sentidos para que un uso nuevo no entre sin su fila y una fila no
sobreviva a las sentencias que describia. El cruce es por operacion: cada operacion numerada tiene
exactamente un comentario, que cita solo direcciones de esa operacion, porque una direccion que solo
perteneciera a la fila dejaria pasar un comentario que justifica unas sentencias con la instruccion de
otras. No comprueban las cifras. Solo leen archivos.
"""

import re
from typing import NamedTuple

from tools.proyecto import RAIZ_REPOSITORIO

from tests.test_business_envolturas_sin_codigo import _cuerpos

ENCABEZADO_DEL_APARTADO = "## Operación escrita en dos sentencias con causa en la expansión"
MARCA = "Operacion en dos sentencias:"
ESTADO_COINCIDE = "coincide"
NUMEROS_EN_LETRA = {"una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8}

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
        list[Comentario]: Un elemento por comentario, con la funcion en cuyo cuerpo esta (cadena
        vacia si esta fuera de todos) y la linea completa donde empieza.

    Ejemplo:
        comentarios_de(fuente, "src/menus_e_interfaz.c")
    """
    lineas = texto.splitlines()
    funcion_de_linea = {
        indice: funcion
        for funcion, inicio, cierre in _cuerpos(lineas)
        for indice in range(inicio, cierre + 1)
    }
    return [
        Comentario(funcion_de_linea.get(indice, ""), archivo, indice + 1, linea)
        for indice, linea in enumerate(lineas)
        if _COMENTARIO_CON_MARCA.search(linea)
    ]


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


def _direcciones(texto: str) -> frozenset[str]:
    return frozenset(direccion.lower() for direccion in _DIRECCION.findall(texto))


def direcciones_por_operacion(celda: str) -> dict[int, frozenset[str]]:
    """
    Asocia cada operacion numerada de una celda con las direcciones que cita su tramo.

    Contexto:
        Se aplica a la columna de instrucciones para saber a que operacion pertenece cada direccion.

    Args:
        celda (str): Celda con tramos encabezados por (1), (2), ...

    Returns:
        dict[int, frozenset[str]]: Direcciones en minusculas desde cada numero hasta el siguiente; la
        clave 0 recoge las que preceden al primer numero y no pertenecen a ninguna operacion. Si un
        numero se repite, sus tramos se unen.

    Ejemplo:
        direcciones_por_operacion("(1) `0x80010004` (2) `0x80010008`")
    """
    partes = _NUMERO_DE_OPERACION.split(celda)
    por_operacion = {0: _direcciones(partes[0])}
    for numero, tramo in zip(partes[1::2], partes[2::2], strict=True):
        por_operacion[int(numero)] = por_operacion.get(int(numero), frozenset()) | _direcciones(tramo)
    return por_operacion


def _incumplimientos_de_emparejamiento(fila: Fila, comentarios: list[Comentario]) -> list[str]:
    """
    Empareja los comentarios de la funcion de una fila con sus operaciones numeradas.

    Contexto:
        Parte de ``incumplimientos`` que exige la correspondencia uno a uno entre comentario y
        operacion.

    Args:
        fila (Fila): Fila de la tabla del apartado.
        comentarios (list[Comentario]): Comentarios de la funcion y el archivo de la fila.

    Returns:
        list[str]: Un mensaje por direccion sin operacion o compartida, por comentario que no cita
        solo direcciones de una operacion y por operacion que no tiene exactamente un comentario.

    Ejemplo:
        errores = _incumplimientos_de_emparejamiento(fila, comentarios)
    """
    errores: list[str] = []
    operaciones = direcciones_por_operacion(fila.instrucciones)
    if operaciones.pop(0):
        errores.append(f"{fila.funcion}: hay una direccion antes de la primera operacion")
    todas = [direccion for direcciones in operaciones.values() for direccion in direcciones]
    if len(todas) != len(set(todas)):
        errores.append(f"{fila.funcion}: una direccion figura en dos operaciones")
    usos = dict.fromkeys(_numeracion(fila.sentencias), 0)
    for comentario in comentarios:
        citadas = _direcciones(comentario.texto)
        candidatas = [n for n in usos if citadas and citadas <= operaciones.get(n, frozenset())]
        if len(candidatas) != 1:
            errores.append(
                f"{comentario.archivo}:{comentario.linea} ({comentario.funcion}): el comentario no cita "
                "solo direcciones de una operacion de la fila"
            )
            continue
        usos[candidatas[0]] += 1
    errores.extend(
        f"{fila.funcion}: la operacion ({numero}) tiene {cuenta} comentarios en src"
        for numero, cuenta in usos.items()
        if cuenta != 1
    )
    return errores


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
        if not comentario.funcion:
            errores.append(f"{comentario.archivo}:{comentario.linea}: comentario fuera de toda funcion")
            continue
        fila = por_funcion.get(comentario.funcion)
        if fila is None or fila.archivo != comentario.archivo:
            errores.append(f"{donde}: comentario sin fila de esa funcion y archivo en la tabla")
            continue
        if not _COMENTARIO_EN_UNA_LINEA.match(comentario.texto):
            errores.append(f"{donde}: el comentario no abre y cierra en la misma linea")
    for fila in filas:
        numeracion = _numeracion(fila.sentencias)
        if not numeracion or numeracion != list(range(1, len(numeracion) + 1)):
            errores.append(f"{fila.funcion}: las operaciones de la fila no estan numeradas desde (1)")
        if _numeracion(fila.instrucciones) != numeracion or _numeracion(fila.cifras) != numeracion:
            errores.append(
                f"{fila.funcion}: instrucciones o cifras no llevan la numeracion de las sentencias"
            )
        propios = [c for c in comentarios if c.funcion == fila.funcion and c.archivo == fila.archivo]
        errores.extend(_incumplimientos_de_emparejamiento(fila, propios))
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
    assert any("(1) tiene 0 comentarios" in error for error in errores)


def test_una_fila_sin_sus_comentarios_en_src_se_rechaza() -> None:
    errores = _cruce(fuente="void func_80010000(s32 a)\n{\n}\n")
    assert any("(1) tiene 0 comentarios" in error for error in errores)


FILA_DE_DOS_OPERACIONES = FILA_DE_EJEMPLO._replace(
    sentencias="(1) `a <<= 8; a >>= 8;` (2) `b = b + a;`",
    instrucciones="(1) `0x80010004` y `0x80010008` (2) `0x8001000C` y `0x80010010`",
    cifras="(1) 10 (2) 20",
)


def _fuente_con_citas(*citas: str) -> str:
    comentarios = "".join(f"    /* {MARCA} como `nop` ({cita}). */\n    a += 1;\n" for cita in citas)
    return f"void func_80010000(s32 a)\n{{\n{comentarios}}}\n"


def _cruce_de_dos_operaciones(*citas: str) -> list[str]:
    return _cruce(fuente=_fuente_con_citas(*citas), filas=[FILA_DE_DOS_OPERACIONES])


def test_cada_operacion_con_un_comentario_que_cita_su_direccion_se_acepta() -> None:
    assert _cruce_de_dos_operaciones("0x80010010", "0x80010004") == []


def test_un_comentario_puede_citar_las_dos_direcciones_de_su_operacion() -> None:
    assert _cruce_de_dos_operaciones("0x80010004 y 0x80010008", "0x8001000c") == []


def test_el_comentario_de_una_operacion_que_cita_la_direccion_de_otra_se_rechaza() -> None:
    errores = _cruce_de_dos_operaciones("0x80010004", "0x80010008")
    assert any("(1) tiene 2 comentarios" in error for error in errores)
    assert any("(2) tiene 0 comentarios" in error for error in errores)


def test_dos_comentarios_para_la_misma_operacion_se_rechazan_aunque_esten_todas_cubiertas() -> None:
    errores = _cruce_de_dos_operaciones("0x80010004", "0x80010004", "0x8001000C")
    assert errores == ["func_80010000: la operacion (1) tiene 2 comentarios en src"]


def test_una_operacion_de_la_fila_sin_comentario_se_rechaza() -> None:
    errores = _cruce_de_dos_operaciones("0x80010004")
    assert errores == ["func_80010000: la operacion (2) tiene 0 comentarios en src"]


def test_un_comentario_que_mezcla_direcciones_de_dos_operaciones_se_rechaza() -> None:
    errores = _cruce_de_dos_operaciones("0x80010004 y 0x8001000C", "0x80010010")
    assert any("de una operacion de la fila" in error for error in errores)


def test_un_comentario_que_ademas_de_la_suya_cita_una_direccion_ajena_se_rechaza() -> None:
    errores = _cruce_de_dos_operaciones("0x80010004 y 0x80020000", "0x8001000C")
    assert any("de una operacion de la fila" in error for error in errores)


def test_un_comentario_sin_direccion_no_corresponde_a_ninguna_operacion() -> None:
    errores = _cruce(fuente=_fuente_con_citas("sin direccion"))
    assert any("de una operacion de la fila" in error for error in errores)


def test_una_direccion_repetida_en_dos_operaciones_de_la_fila_se_rechaza() -> None:
    fila = FILA_DE_DOS_OPERACIONES._replace(instrucciones="(1) `0x80010004` (2) `0x80010004`")
    errores = _cruce(fuente=_fuente_con_citas("0x80010004", "0x80010004"), filas=[fila])
    assert any("figura en dos operaciones" in error for error in errores)


def test_una_direccion_anterior_a_la_primera_operacion_se_rechaza() -> None:
    fila = FILA_DE_EJEMPLO._replace(instrucciones="`0x80010000` (1) `0x80010004`")
    assert any("antes de la primera" in error for error in _cruce(filas=[fila]))


def test_las_direcciones_de_cada_tramo_quedan_asociadas_a_su_numero() -> None:
    assert direcciones_por_operacion(FILA_DE_DOS_OPERACIONES.instrucciones) == {
        0: frozenset(),
        1: frozenset({"0x80010004", "0x80010008"}),
        2: frozenset({"0x8001000c", "0x80010010"}),
    }


def test_un_comentario_con_la_marca_tras_el_cierre_de_una_funcion_se_rechaza() -> None:
    fuente = FUENTE_DE_EJEMPLO + f"\n/* {MARCA} suelto (0x80010004). */\n"
    assert _cruce(fuente=fuente) == ["src/ejemplo.c:8: comentario fuera de toda funcion"]


def test_un_comentario_con_la_marca_antes_de_la_primera_funcion_se_rechaza() -> None:
    fuente = f"/* {MARCA} suelto (0x80010004). */\n" + FUENTE_DE_EJEMPLO
    assert _cruce(fuente=fuente) == ["src/ejemplo.c:1: comentario fuera de toda funcion"]


def test_unas_cifras_sin_la_numeracion_de_las_sentencias_se_rechazan() -> None:
    errores = _cruce(filas=[FILA_DE_EJEMPLO._replace(cifras="10")])
    assert any("numeracion" in error for error in errores)


def test_un_comentario_que_ocupa_dos_lineas_se_rechaza() -> None:
    fuente = FUENTE_DE_EJEMPLO.replace("(0x80010004). */", "(0x80010004).\n     * Sigue. */")
    assert any("misma linea" in error for error in _cruce(fuente=fuente))


def test_un_comentario_que_cita_una_direccion_ajena_a_la_fila_se_rechaza() -> None:
    fuente = FUENTE_DE_EJEMPLO.replace("0x80010004", "0x80010100")
    assert any("de una operacion de la fila" in error for error in _cruce(fuente=fuente))


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

"""Reglas de negocio del aliasing de uniones y de los accesos por indice sin campo.

Dos campos de una misma ``union`` (con nombre o anonima) son el mismo almacenamiento aunque se llamen
distinto: una escritura a uno cambia lo que lee el otro. Las mutaciones que mueven o repiten lecturas de
memoria no pueden cruzar esa escritura, y si pueden cruzar la de un campo ajeno. Un acceso ``p[i]`` sin
campo no dice a que objeto apunta y depende de todo acceso a memoria.
"""

import random
from collections.abc import Callable

import pytest
from tools.reconstruccion import permutar_analisis as an
from tools.reconstruccion import permutar_c as c
from tools.reconstruccion import permutar_mutaciones as mut

CABECERA = """
typedef union Giro {
    s32 total;
    s16 media;
    u8 octeto;
} Giro;
union Etiqueta {
    s32 palabra;
    s16 mitad_baja;
};
typedef struct Pieza {
    u32 flags14;
    s16 radio;
    s32 valor;
    union {
        s32 entero;
        s16 corto;
    } u78;
    union {
        s32 ancho;
        s16 mitad;
    };
    Giro giro;
    s32 vec[4];
} Pieza;
typedef struct Ajeno {
    s32 dato;
    s32 total_ajeno;
} Ajeno;
"""
TIPOS = frozenset({"Pieza", "Ajeno", "Giro"})
FIRMA = "void f(Pieza* o, Ajeno* a, s32* p, s32 x, s32 y)"


def azar(semilla: int) -> random.Random:
    """Generador reproducible; la busqueda es estocastica, no criptografica."""
    return random.Random(semilla)  # noqa: S311


def cuerpo(*lineas: str, firma: str = FIRMA) -> str:
    return firma + "\n{\n" + "\n".join(f"    {linea}" for linea in lineas) + "\n}"


def preparar(texto: str, semilla: int = 0) -> mut.Contexto:
    tabla = an.construir_tabla([CABECERA])
    funcion = c.analizar_funcion(texto, "f", TIPOS)
    return mut.Contexto(funcion, an.Entorno(tabla, funcion), azar(semilla), mut._nombres_de(funcion))


def aplicar(
    mutacion: Callable[[mut.Contexto], str | None], texto: str, semilla: int = 0
) -> tuple[str | None, str]:
    ctx = preparar(texto, semilla)
    descripcion = mutacion(ctx)
    return descripcion, c.imprimir_funcion(ctx.funcion)


def alcanza(escritura: str, lectura: str) -> bool:
    """Indica si la escritura puede cambiar lo que lee la segunda sentencia, con los alias de la cabecera."""
    funcion = c.analizar_funcion(cuerpo(escritura, lectura), "f", TIPOS)
    alias = an.construir_tabla([CABECERA]).alias_de_campos
    primera, segunda = funcion.cuerpo.items
    return an.escritura_alcanza(an.efectos_profundos(primera, alias), an.efectos_de(segunda, alias))


# --- la tabla registra las uniones ------------------------------------------------------------------


def test_la_tabla_registra_las_uniones_con_nombre_y_las_anonimas() -> None:
    tabla = an.construir_tabla([CABECERA])
    assert tabla.uniones["Giro"] == {"total", "media", "octeto"}
    assert tabla.uniones["Etiqueta"] == {"palabra", "mitad_baja"}
    assert tabla.uniones["u78"] == {"entero", "corto"}
    assert tabla.grupos_anonimos == [frozenset({"ancho", "mitad"})]


def test_los_miembros_de_una_union_comparten_representante_y_los_demas_campos_no_tienen_alias() -> None:
    alias = an.construir_tabla([CABECERA]).alias_de_campos
    assert len({alias[n] for n in ("total", "media", "octeto")}) == 1
    assert alias["entero"] == alias["corto"] and alias["ancho"] == alias["mitad"]
    assert alias["total"] != alias["entero"]
    assert not {"flags14", "radio", "valor", "dato", "total_ajeno"} & set(alias)


def test_dos_uniones_que_comparten_un_nombre_de_campo_se_funden_en_un_solo_grupo() -> None:
    tabla = an.construir_tabla(["union A { s32 a; s16 b; };\nunion B { s16 b; u8 c; };\n"])
    assert len({tabla.alias_de_campos[n] for n in "abc"}) == 1


def test_una_union_de_un_solo_miembro_no_crea_alias() -> None:
    tabla = an.construir_tabla(["union Sola { s32 unico; };\ntypedef struct { s32 a; s32 b; } Par;\n"])
    assert tabla.alias_de_campos == {} and tabla.uniones == {} and tabla.grupos_anonimos == []


def test_una_estructura_no_se_toma_por_union() -> None:
    assert an.construir_tabla(["struct Par { s32 a; s32 b; };\n"]).alias_de_campos == {}


def test_la_misma_union_leida_en_dos_textos_conserva_todos_sus_miembros() -> None:
    tabla = an.construir_tabla(["union U { s32 a; s16 b; };\n", "union U { s32 a; s16 b; };\n"])
    assert tabla.uniones["U"] == {"a", "b"}


# --- rutas y conflictos ------------------------------------------------------------------------------


def test_la_ruta_de_dos_miembros_de_una_union_coincide_solo_con_alias() -> None:
    alias = an.construir_tabla([CABECERA]).alias_de_campos
    funcion = c.analizar_funcion(cuerpo("x = o->u78.entero + o->u78.corto;"), "f", TIPOS)
    suma = funcion.cuerpo.items[0].expr.valor  # type: ignore[union-attr]
    izq, der = suma.izq, suma.der
    assert an.ruta_de_memoria(izq) != an.ruta_de_memoria(der)
    assert an.ruta_de_memoria(izq, alias) == an.ruta_de_memoria(der, alias)


@pytest.mark.parametrize(
    ("escritura", "lectura"),
    [
        ("o->u78.corto = 1;", "x = o->u78.entero;"),
        ("o->u78.entero = 1;", "x = o->u78.corto;"),
        ("o->u78.entero = 1;", "x = o->u78.entero;"),
        ("o->giro.media = 1;", "x = o->giro.total;"),
        ("o->giro.octeto = 1;", "x = o->giro.media;"),
        ("o->mitad = 1;", "x = o->ancho;"),
        ("o->ancho = 1;", "x = o->mitad;"),
        ("o->u78 = o->u78;", "x = o->u78.entero;"),
        ("o->u78.corto = 1;", "x = o->u78;"),
        ("*o = *o;", "x = o->u78.entero;"),
        ("*p = 1;", "x = o->u78.entero;"),
    ],
)
def test_una_escritura_a_un_miembro_de_la_union_alcanza_a_todos_sus_hermanos(
    escritura: str, lectura: str
) -> None:
    assert alcanza(escritura, lectura)


@pytest.mark.parametrize(
    ("escritura", "lectura"),
    [
        ("o->radio = 1;", "x = o->u78.entero;"),
        ("a->dato = 1;", "x = o->u78.entero;"),
        ("o->flags14 = 1;", "x = o->ancho;"),
        ("o->u78.corto = 1;", "x = o->giro.total;"),
        ("o->giro.media = 1;", "x = o->ancho;"),
        ("o->vec[1] = 1;", "x = o->u78.corto;"),
        ("o->u78.corto = 1;", "x = a->total_ajeno;"),
    ],
)
def test_una_escritura_a_un_campo_ajeno_no_alcanza_a_la_union(escritura: str, lectura: str) -> None:
    assert not alcanza(escritura, lectura)


def test_sin_la_tabla_de_alias_los_miembros_de_una_union_anonima_se_ven_independientes() -> None:
    # Los miembros de una union con nombre (``o->u78.corto``) ya chocaban sin tabla porque el nodo
    # intermedio ``o->u78`` cuenta como lectura de su prefijo; los de una union anonima, no: sus campos
    # cuelgan directos de la estructura y solo el alias los une.
    funcion = c.analizar_funcion(cuerpo("o->mitad = 1;", "x = o->ancho;"), "f", TIPOS)
    primera, segunda = funcion.cuerpo.items
    assert not an.escritura_alcanza(an.efectos_profundos(primera), an.efectos_de(segunda))


# --- mutaciones que no cruzan un miembro de la misma union -----------------------------------------------


@pytest.mark.parametrize(
    ("hermano", "lectura"),
    [
        ("o->u78.corto = 3;", "y = o->u78.entero;"),
        ("o->giro.media = 3;", "y = o->giro.total;"),
        ("o->mitad = 3;", "y = o->ancho;"),
    ],
)
def test_la_local_de_campo_no_sube_la_lectura_por_encima_de_un_miembro_hermano(
    hermano: str, lectura: str
) -> None:
    texto = cuerpo("x = 1;", hermano, lectura)
    cargada = lectura.removeprefix("y = ").removesuffix(";")
    aplicadas = 0
    for semilla in range(40):
        descripcion, resultado = aplicar(mut.local_de_campo, texto, semilla)
        if descripcion is not None and cargada in descripcion:
            aplicadas += 1
            assert resultado.index(f"tmp1 = {cargada}") > resultado.index(hermano)
    assert aplicadas > 0


def test_la_local_de_campo_si_sube_la_lectura_por_encima_de_un_campo_ajeno() -> None:
    texto = cuerpo("x = 1;", "o->radio = 3;", "y = o->u78.entero;")
    subidas = [
        aplicar(mut.local_de_campo, texto, semilla)[1]
        for semilla in range(40)
        if "tmp1 = o->u78.entero" in aplicar(mut.local_de_campo, texto, semilla)[1]
    ]
    assert any(r.index("tmp1 = o->u78.entero") < r.index("o->radio = 3;") for r in subidas)


def test_el_barrido_de_vecinos_no_sube_la_lectura_por_encima_del_miembro_hermano() -> None:
    texto = cuerpo("x = 1;", "o->u78.corto = 3;", "y = o->u78.entero;")
    tabla = an.construir_tabla([CABECERA])
    cargadas = 0
    for variante, _ in mut.vecinos(c.analizar_funcion(texto, "f", TIPOS), tabla):
        escrito = c.imprimir_funcion(variante)
        if "tmp1 = o->u78.entero;" in escrito:
            cargadas += 1
            assert escrito.index("tmp1 = o->u78.entero;") > escrito.index("o->u78.corto = 3;")
    assert cargadas > 0


@pytest.mark.parametrize(
    ("fuente", "escritura"),
    [
        ("o->u78.entero", "o->u78.corto = i;"),
        ("o->giro.total", "o->giro.media = i;"),
        ("o->ancho", "o->mitad = i;"),
    ],
)
def test_no_se_relee_la_cuenta_si_el_bucle_escribe_un_miembro_hermano(fuente: str, escritura: str) -> None:
    texto = cuerpo("s32 i;", "s32 n;", f"n = {fuente};", "for (i = 0; i < n; i++) {", f"    {escritura}", "}")
    assert aplicar(mut.releer_en_condicion, texto)[0] is None


def test_se_relee_la_cuenta_si_el_bucle_escribe_un_campo_ajeno() -> None:
    texto = cuerpo(
        "s32 i;", "s32 n;", "n = o->u78.entero;", "for (i = 0; i < n; i++) {", "    o->radio = i;", "}"
    )
    assert aplicar(mut.releer_en_condicion, texto)[0] is not None


@pytest.mark.parametrize(
    ("primera", "segunda"),
    [
        ("o->u78.corto = 1;", "x = o->u78.entero;"),
        ("o->u78.corto = 1;", "o->u78.entero = 2;"),
        ("x = o->giro.total;", "o->giro.media = 2;"),
        ("o->mitad = 1;", "x = o->ancho;"),
    ],
)
def test_el_orden_de_sentencias_no_intercambia_miembros_de_la_misma_union(primera: str, segunda: str) -> None:
    assert aplicar(mut.orden_de_sentencias, cuerpo(primera, segunda))[0] is None


@pytest.mark.parametrize(
    ("primera", "segunda"),
    [
        ("o->radio = 1;", "x = o->u78.entero;"),
        ("o->u78.corto = 1;", "x = o->giro.total;"),
        ("o->u78.corto = 1;", "o->ancho = 2;"),
    ],
)
def test_el_orden_de_sentencias_si_intercambia_campos_ajenos_a_la_union(primera: str, segunda: str) -> None:
    assert (
        aplicar(mut.orden_de_sentencias, cuerpo(primera, segunda))[0] == "orden_sentencias(posiciones 0 y 1)"
    )


# --- accesos por indice sin campo --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [
        ("[]", "radio", True),
        ("radio", "[]", True),
        ("[]", "[]", True),
        ("[][]", "u78.entero", True),
        ("*", "radio", True),
        ("vec[]", "radio", False),
        ("vec[]", "vec[]", True),
        ("radio", "valor", False),
        ("u78", "u78.entero", True),
    ],
)
def test_un_indice_sin_campo_es_dependiente_de_toda_ruta_de_memoria(a: str, b: str, esperado: bool) -> None:
    assert an._rutas_en_conflicto(a, b) is esperado


@pytest.mark.parametrize(
    ("primera", "segunda"),
    [
        ("p[x] = y;", "o->radio = 1;"),
        ("o->radio = 1;", "p[x] = y;"),
        ("p[x] = y;", "y = o->valor;"),
        ("p[x] = y;", "p[1] = 2;"),
    ],
)
def test_el_orden_de_sentencias_no_cruza_un_indice_sin_campo_con_un_acceso_a_campo(
    primera: str, segunda: str
) -> None:
    assert aplicar(mut.orden_de_sentencias, cuerpo(primera, segunda))[0] is None


def test_el_orden_de_sentencias_si_intercambia_un_indice_sin_campo_con_una_variable_ajena() -> None:
    assert aplicar(mut.orden_de_sentencias, cuerpo("p[1] = y;", "x = 3;"))[0] is not None
    assert aplicar(mut.orden_de_sentencias, cuerpo("o->valor = 1;", "o->radio = 2;"))[0] is not None

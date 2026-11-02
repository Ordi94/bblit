"""Reglas de negocio de las mutaciones: que cambian el C y que casos no se tocan nunca."""

import random
import re
from collections.abc import Callable

import pytest
from tools.reconstruccion import permutar_analisis as an
from tools.reconstruccion import permutar_c as c
from tools.reconstruccion import permutar_mutaciones as mut

CABECERA = """
typedef struct Objeto {
    u32 flags08;
    s16 radio;
    s32 valor;
    u16 corto;
    s32 *ptr;
    s32 vec[4];
    struct Nodo* siguiente;
} Objeto;
"""
TIPOS = frozenset({"Objeto"})


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


def cuerpo(*lineas: str, firma: str = "void f(Objeto* o, s32 x, s32 y)") -> str:
    return firma + "\n{\n" + "\n".join(f"    {linea}" for linea in lineas) + "\n}"


def azar(semilla: int) -> random.Random:
    """Generador reproducible; la busqueda es estocastica, no criptografica."""
    return random.Random(semilla)  # noqa: S311


class Fijo(random.Random):
    """Generador cuyo ``random()`` devuelve siempre el mismo valor."""

    def __init__(self, valor: float) -> None:
        super().__init__(0)
        self.valor = valor

    def random(self) -> float:
        return self.valor


FIRMA_CON_PUNTERO = "void f(Objeto* o, s32* p, s32 x, s32 y)"


# --- orden de declaraciones -------------------------------------------------------------------------


def test_las_declaraciones_sin_inicial_se_pueden_intercambiar() -> None:
    descripcion, texto = aplicar(mut.orden_de_declaraciones, cuerpo("s32 a;", "s32 b;", "a = 1;"))
    assert descripcion is not None and descripcion.startswith("orden_declaraciones(")
    assert "    s32 b;\n    s32 a;\n" in texto


def test_un_inicializador_no_puede_pasar_antes_de_la_variable_que_usa() -> None:
    assert aplicar(mut.orden_de_declaraciones, cuerpo("s32 a = 1;", "s32 b = a;", "x = b;"))[0] is None


def test_un_inicializador_puede_usar_variables_ajenas_a_la_serie() -> None:
    descripcion, texto = aplicar(mut.orden_de_declaraciones, cuerpo("s32 a = x;", "s32 b = y;"))
    assert descripcion is not None
    assert "    s32 b = y;\n    s32 a = x;\n" in texto


def test_una_serie_de_una_sola_declaracion_no_cambia() -> None:
    assert aplicar(mut.orden_de_declaraciones, cuerpo("s32 a;", "a = 1;"))[0] is None


# --- orden de sentencias ----------------------------------------------------------------------------


def test_dos_asignaciones_a_campos_distintos_se_intercambian() -> None:
    descripcion, texto = aplicar(mut.orden_de_sentencias, cuerpo("o->valor = 1;", "o->radio = 2;"))
    assert descripcion is not None
    assert texto.index("o->radio = 2;") < texto.index("o->valor = 1;")


@pytest.mark.parametrize(
    "lineas",
    [
        ("x = 1;", "y = x;"),
        ("o->valor = 1;", "o->valor = 2;"),
        ("o->valor = x;", "f(o);"),
        ("o->valor = 1;", "return;"),
        ("o->vec[1] = 1;", "o->vec[2] = 2;"),
    ],
)
def test_las_sentencias_con_dependencia_o_barrera_no_se_reordenan(lineas: tuple[str, ...]) -> None:
    assert aplicar(mut.orden_de_sentencias, cuerpo(*lineas))[0] is None


def test_una_variable_cuya_direccion_se_toma_no_se_mueve_respecto_a_una_escritura_por_puntero() -> None:
    firma = "void f(s32* p)"
    con_direccion = cuerpo("s32 a;", "a = 1;", "*p = 2;", "g(&a);", firma=firma)
    assert aplicar(mut.orden_de_sentencias, con_direccion)[0] is None
    sin_direccion = cuerpo("s32 a;", "a = 1;", "*p = 2;", "g(a);", firma=firma)
    assert aplicar(mut.orden_de_sentencias, sin_direccion)[0] is not None


# --- temporales -------------------------------------------------------------------------------------


def test_introducir_un_temporal_declara_la_variable_antes_de_las_sentencias_y_la_asigna_antes_del_uso() -> (
    None
):
    descripciones = set()
    for semilla in range(40):
        descripcion, texto = aplicar(
            mut.introducir_temporal, cuerpo("s32 r;", "r = o->radio + 1;", "o->valor = r;"), semilla
        )
        assert descripcion is not None
        descripciones.add(descripcion)
        assert texto.index("tmp1;") < texto.index("tmp1 = ")
        assert c.imprimir_funcion(c.analizar_funcion(texto, "f", TIPOS)) == texto
    assert any("s16 tmp1 = o->radio" in d for d in descripciones)


def test_un_temporal_de_un_puntero_a_estructura_con_etiqueta_se_declara_con_struct() -> None:
    texto = cuerpo("o->valor = o->siguiente != 0;", firma="void f(Objeto* o)")
    declaraciones = set()
    for semilla in range(60):
        descripcion, resultado = aplicar(mut.introducir_temporal, texto, semilla)
        if descripcion and "Nodo" in descripcion:
            declaraciones.add(descripcion.split(" = ")[0])
            assert "    struct Nodo* tmp1;\n" in resultado
    assert declaraciones == {"introducir_temporal(struct Nodo* tmp1"}


def test_un_temporal_nunca_sale_de_un_operando_que_solo_se_evalua_a_veces() -> None:
    texto = cuerpo("if (o != 0 && o->radio > 1) {", "    o->valor = 0;", "}")
    for semilla in range(40):
        descripcion, resultado = aplicar(mut.introducir_temporal, texto, semilla)
        assert descripcion is not None
        assert "tmp1 = o->radio" not in resultado


def test_un_temporal_no_sale_de_una_rama_de_un_condicional() -> None:
    texto = cuerpo("x = o != 0 ? o->radio : 2;")
    for semilla in range(40):
        resultado = aplicar(mut.introducir_temporal, texto, semilla)[1]
        assert "tmp1 = o->radio" not in resultado


@pytest.mark.parametrize(
    "linea",
    [
        "x = (y = 2) + o->radio;",
        "x = f(1) + o->radio;",
        "x = y++ + o->radio;",
        "x = ++y + o->radio;",
        "f(g(1), o->radio);",
    ],
)
def test_una_sentencia_con_otros_efectos_no_admite_temporales(linea: str) -> None:
    assert aplicar(mut.introducir_temporal, cuerpo(linea, firma="void f(Objeto* o, s32 x, s32 y)"))[0] is None


def test_una_llamada_con_argumentos_puros_admite_un_temporal_de_sus_argumentos() -> None:
    descripcion, texto = aplicar(mut.introducir_temporal, cuerpo("GEO_F(o->radio);"))
    assert descripcion is not None
    assert "tmp1 = o->radio;" in texto or "tmp1 = o;" in texto


def test_la_asignacion_de_un_temporal_puede_subir_por_encima_de_sentencias_independientes() -> None:
    texto = cuerpo("o->valor = 1;", "o->corto = 2;", "y = o->radio;", firma="void f(Objeto* o, s32 y)")
    posiciones = set()
    for semilla in range(80):
        descripcion, resultado = aplicar(mut.introducir_temporal, texto, semilla)
        if descripcion and "o->radio" in descripcion and "tmp1 = o->radio;" in resultado:
            posiciones.add(resultado.index("tmp1 = o->radio;") < resultado.index("o->valor = 1;"))
    assert posiciones == {True, False}


def test_la_asignacion_de_un_temporal_no_sube_por_encima_de_una_escritura_de_su_expresion() -> None:
    texto = cuerpo("o->radio = 3;", "o->corto = 2;", "y = o->radio;", firma="void f(Objeto* o, s32 y)")
    for semilla in range(80):
        descripcion, resultado = aplicar(mut.introducir_temporal, texto, semilla)
        if descripcion and "o->radio" in descripcion and "tmp1 = o->radio;" in resultado:
            assert resultado.index("tmp1 = o->radio;") > resultado.index("o->radio = 3;")


def test_con_la_expresion_repetida_el_temporal_sustituye_todas_o_solo_una_aparicion() -> None:
    vistos = set()
    for semilla in range(60):
        descripcion, texto = aplicar(mut.introducir_temporal, cuerpo("x = o->radio + o->radio;"), semilla)
        if descripcion and "o->radio" in descripcion:
            vistos.add("tmp1 + tmp1" in texto)
    assert vistos == {True, False}


def test_las_expresiones_que_son_destino_o_direccion_no_se_copian() -> None:
    for semilla in range(40):
        resultado = aplicar(mut.introducir_temporal, cuerpo("o->radio = x;", "y = 1;"), semilla)[1]
        assert "tmp1 = o->radio" not in resultado


def test_sin_subexpresiones_con_tipo_conocido_no_hay_temporal() -> None:
    assert aplicar(mut.introducir_temporal, cuerpo("desconocida = otra;"))[0] is None
    assert aplicar(mut.introducir_temporal, cuerpo("while (x) {", "    x = 0;", "}"))[0] is None


def test_eliminar_un_temporal_de_un_solo_uso_lo_sustituye_por_su_expresion() -> None:
    texto = cuerpo("s16 t;", "t = o->radio;", "o->valor = t;")
    descripcion, resultado = aplicar(mut.eliminar_temporal, texto)
    assert descripcion == "eliminar_temporal(t)"
    assert "o->valor = o->radio;" in resultado
    assert "s16 t;" not in resultado and "t = " not in resultado


@pytest.mark.parametrize(
    "lineas",
    [
        ("s16 t;", "t = o->radio;", "o->valor = t + t;"),
        ("s16 t;", "t = o->radio;", "y = 1;", "o->valor = t;"),
        ("s16 t;", "t = o->radio;", "if (x && t) {", "    y = 1;", "}"),
        ("s16 t;", "t = f(1);", "o->valor = t;"),
        ("s16 t;", "t = o->valor;", "o->radio = t;"),
        ("u16 t;", "t = o->radio;", "o->valor = t;"),
        ("u32 t;", "t = o->radio;", "o->valor = t;"),
        ("s16 t;", "t = o->radio;"),
        ("s16 t = 1;", "t = o->radio;", "o->valor = t;"),
    ],
)
def test_un_temporal_que_no_cumple_las_condiciones_no_se_elimina(lineas: tuple[str, ...]) -> None:
    assert aplicar(mut.eliminar_temporal, cuerpo(*lineas))[0] is None


def test_eliminar_un_temporal_de_mayor_ancho_con_el_mismo_tipo_promovido_es_valido() -> None:
    descripcion, resultado = aplicar(
        mut.eliminar_temporal, cuerpo("s32 t;", "t = o->radio;", "o->valor = t;")
    )
    assert descripcion == "eliminar_temporal(t)"
    assert "o->valor = o->radio;" in resultado


# --- ancho de temporales ----------------------------------------------------------------------------


def test_un_temporal_que_recibe_un_s16_se_puede_estrechar_a_s16_pero_no_a_sin_signo() -> None:
    destinos = set()
    for semilla in range(30):
        descripcion, _ = aplicar(
            mut.ancho_de_temporal, cuerpo("s32 r;", "r = o->radio;", "o->valor = r;"), semilla
        )
        if descripcion:
            destinos.add(descripcion.split(" a ")[-1])
    assert destinos == {"s16)"}


def test_una_constante_pequena_admite_todos_los_anchos_si_las_lecturas_no_dependen_del_signo() -> None:
    destinos = set()
    for semilla in range(60):
        descripcion, _ = aplicar(mut.ancho_de_temporal, cuerpo("s32 r;", "r = 5;", "o->valor = r;"), semilla)
        assert descripcion is not None
        destinos.add(descripcion.split(" a ")[-1])
    assert destinos == {"u32)", "s16)", "u16)"}


def test_si_una_lectura_depende_del_signo_no_se_pasa_a_u32() -> None:
    destinos = set()
    for semilla in range(60):
        descripcion, _ = aplicar(
            mut.ancho_de_temporal, cuerpo("s32 r;", "r = 5;", "o->valor = r > 3;"), semilla
        )
        assert descripcion is not None
        destinos.add(descripcion.split(" a ")[-1])
    assert destinos == {"s16)", "u16)"}


@pytest.mark.parametrize(
    "lineas",
    [
        ("s32 r;", "r = 5;", "r++;"),
        ("s32 r;", "r = 5;", "r += 2;"),
        ("s32 r;", "r = 5;", "o->ptr = &r;"),
        ("s32 r;", "o->valor = r;"),
        ("s32 r[2];", "r[0] = 1;"),
        ("u8 r;", "r = 1;"),
        ("s32 r;", "r = f(1);"),
        ("s32 r;", "r = o->valor;"),
    ],
)
def test_las_variables_que_no_admiten_el_cambio_de_ancho_se_dejan(lineas: tuple[str, ...]) -> None:
    assert aplicar(mut.ancho_de_temporal, cuerpo(*lineas))[0] is None


def test_una_variable_que_nunca_se_lee_admite_u32_si_su_constante_cabe() -> None:
    destinos = set()
    for semilla in range(40):
        descripcion, _ = aplicar(mut.ancho_de_temporal, cuerpo("s32 r;", "r = 70000;"), semilla)
        assert descripcion is not None
        destinos.add(descripcion.split(" a ")[-1])
    assert destinos == {"u32)"}


def test_un_inicial_negativo_no_cabe_en_un_tipo_sin_signo() -> None:
    destinos = set()
    for semilla in range(60):
        descripcion, _ = aplicar(mut.ancho_de_temporal, cuerpo("s32 r = -1;", "o->valor = r;"), semilla)
        assert descripcion is not None
        destinos.add(descripcion.split(" a ")[-1])
    assert destinos == {"s16)"}


def test_las_lecturas_por_igualdad_con_un_literal_o_por_negacion_o_argumento_son_insensibles_al_signo() -> (
    None
):
    for lectura in ("x = r == 3;", "x = r != 3;", "x = !r;", "f(r);", "if (r) {\n        x = 1;\n    }"):
        destinos = set()
        for semilla in range(60):
            descripcion, _ = aplicar(mut.ancho_de_temporal, cuerpo("s32 r;", "r = 5;", lectura), semilla)
            assert descripcion is not None
            destinos.add(descripcion.split(" a ")[-1])
        assert "u32)" in destinos, lectura


def test_una_lectura_por_igualdad_con_una_variable_o_negativo_si_depende_del_signo() -> None:
    for lectura in ("x = r == y;", "x = r == -1;", "x = r + 1;", "x = -r;"):
        destinos = set()
        for semilla in range(60):
            descripcion, _ = aplicar(mut.ancho_de_temporal, cuerpo("s32 r;", "r = 5;", lectura), semilla)
            assert descripcion is not None
            destinos.add(descripcion.split(" a ")[-1])
        assert "u32)" not in destinos, lectura


def test_copiar_un_parametro_lo_sustituye_en_todo_el_cuerpo() -> None:
    descripcion, texto = aplicar(
        mut.copiar_parametro, cuerpo("o->radio = 1;", "o->valor = 2;", firma="void f(Objeto* o)")
    )
    assert descripcion == "copiar_parametro(o en tmp1)"
    assert "    Objeto* tmp1;\n    tmp1 = o;\n    tmp1->radio = 1;\n    tmp1->valor = 2;\n" in texto


@pytest.mark.parametrize(
    "lineas",
    [("o = 0;",), ("x = &o;",), ("o++;",)],
)
def test_un_parametro_que_se_escribe_o_cuya_direccion_se_toma_no_se_copia(lineas: tuple[str, ...]) -> None:
    assert aplicar(mut.copiar_parametro, cuerpo(*lineas, firma="void f(Objeto* o)"))[0] is None


def test_un_parametro_sin_usos_o_no_escalar_no_se_copia() -> None:
    assert aplicar(mut.copiar_parametro, cuerpo("x = y;", firma="void f(s32 x, s32 y)"))[0] is not None
    assert aplicar(mut.copiar_parametro, cuerpo("z = 1;", firma="void f(Objeto* o)"))[0] is None
    assert aplicar(mut.copiar_parametro, cuerpo("z = 1;", firma="void f(void)"))[0] is None
    assert aplicar(mut.copiar_parametro, cuerpo("z = 1;", firma="void f(Objeto o)"))[0] is None


# --- expresiones ------------------------------------------------------------------------------------


def test_los_operandos_puros_de_un_operador_conmutativo_se_intercambian() -> None:
    descripcion, texto = aplicar(mut.operandos_conmutados, cuerpo("y = x + o->valor;"))
    assert descripcion == "operandos_conmutados(+)"
    assert "y = o->valor + x;" in texto


def test_una_comparacion_se_invierte_junto_con_sus_operandos() -> None:
    descripcion, texto = aplicar(mut.operandos_conmutados, cuerpo("y = x < o->valor;"))
    assert descripcion == "operandos_conmutados(<)"
    assert "y = o->valor > x;" in texto
    assert "y = o->valor >= x;" in aplicar(mut.operandos_conmutados, cuerpo("y = x <= o->valor;"))[1]


@pytest.mark.parametrize("linea", ["y = f(1) + x;", "y = x - 1;", "y = x && y;", "y = x / 2;"])
def test_no_se_conmutan_operandos_con_efectos_ni_operadores_que_no_lo_son(linea: str) -> None:
    assert aplicar(mut.operandos_conmutados, cuerpo(linea))[0] is None


@pytest.mark.parametrize(
    ("linea", "esperado"),
    [
        ("y = p[x];", "y = *(p + x);"),
        ("y = *(p + x);", "y = p[x];"),
        ("y = o->radio;", "y = (*o).radio;"),
        ("y = (*o).radio;", "y = o->radio;"),
    ],
)
def test_indice_y_puntero_son_la_misma_expresion(linea: str, esperado: str) -> None:
    descripcion, texto = aplicar(mut.indice_o_puntero, cuerpo(linea, firma=FIRMA_CON_PUNTERO))
    assert descripcion is not None
    assert esperado in texto


@pytest.mark.parametrize("linea", ["y = x + 1;", "y = *(p - 1);", "y = *p;", "y = *(x + p);"])
def test_no_hay_conversion_si_la_forma_no_es_equivalente_o_el_puntero_esta_a_la_derecha(linea: str) -> None:
    assert aplicar(mut.indice_o_puntero, cuerpo(linea, firma=FIRMA_CON_PUNTERO))[0] is None


# --- control de flujo -------------------------------------------------------------------------------


def test_negar_empuja_la_negacion_hacia_adentro() -> None:
    sin_literal = Fijo(0.9)
    assert c.imprimir_expresion(mut.negar(c.Unario("!", c.Id("a")), sin_literal)) == "a"
    assert c.imprimir_expresion(mut.negar(c.Binario("<", c.Id("a"), c.Id("b")), sin_literal)) == "a >= b"
    assert c.imprimir_expresion(mut.negar(c.Binario("==", c.Id("a"), c.Id("b")), sin_literal)) == "a != b"
    conjuncion = c.Binario("&&", c.Binario(">", c.Id("a"), c.Num("1")), c.Id("b"))
    assert c.imprimir_expresion(mut.negar(conjuncion, sin_literal)) == "a <= 1 || !b"
    disyuncion = c.Binario("||", c.Id("a"), c.Id("b"))
    assert c.imprimir_expresion(mut.negar(disyuncion, sin_literal)) == "!a && !b"
    assert c.imprimir_expresion(mut.negar(c.Id("a"), sin_literal)) == "!a"
    assert c.imprimir_expresion(mut.negar(c.Binario("<", c.Id("a"), c.Id("b")), Fijo(0.1))) == "!(a < b)"


def test_la_condicion_invertida_intercambia_las_ramas() -> None:
    descripcion, texto = aplicar(
        mut.condicion_invertida,
        cuerpo("if (x < y) {", "    o->valor = 1;", "} else {", "    o->valor = 2;", "}"),
    )
    assert descripcion == "condicion_invertida(x < y)"
    primera = texto.index("o->valor = 2;")
    segunda = texto.index("o->valor = 1;")
    assert primera < segunda


def test_un_if_sin_else_no_se_invierte() -> None:
    assert aplicar(mut.condicion_invertida, cuerpo("if (x) {", "    y = 1;", "}"))[0] is None


def test_un_for_pasa_a_while_con_su_inicio_antes_y_su_paso_al_final() -> None:
    descripcion, texto = aplicar(
        mut.bucle_for_o_while, cuerpo("for (x = 0; x < 4; x++) {", "    y += x;", "}")
    )
    assert descripcion == "bucle(for a while)"
    assert "    x = 0;\n    while (x < 4) {\n        y += x;\n        x++;\n    }\n" in texto


def test_un_for_sin_condicion_ni_inicio_ni_paso_pasa_a_while_infinito() -> None:
    descripcion, texto = aplicar(mut.bucle_for_o_while, cuerpo("for (;;) {", "    y++;", "}"))
    assert descripcion == "bucle(for a while)"
    assert "    while (1) {\n        y++;\n    }\n" in texto


def test_un_while_pasa_a_for_y_a_veces_su_ultima_sentencia_es_el_paso() -> None:
    texto = cuerpo("while (x < 4) {", "    y += x;", "    x++;", "}")
    ctx = preparar(texto)
    ctx.azar = Fijo(0.9)
    assert mut.bucle_for_o_while(ctx) == "bucle(while a for)"
    assert "for (; x < 4; ) {" in c.imprimir_funcion(ctx.funcion)
    ctx = preparar(texto)
    ctx.azar = Fijo(0.1)
    assert mut.bucle_for_o_while(ctx) == "bucle(while a for)"
    assert "for (; x < 4; x++) {\n        y += x;\n    }" in c.imprimir_funcion(ctx.funcion)


def test_un_while_con_cuerpo_vacio_o_comentado_pasa_a_for_sin_mover_nada() -> None:
    ctx = preparar(cuerpo("while (x) {", "}"))
    assert mut.bucle_for_o_while(ctx) == "bucle(while a for)"
    assert "for (; x; ) {" in c.imprimir_funcion(ctx.funcion)
    ctx = preparar(cuerpo("while (x) {", "    /* nota */", "    x++;", "}"))
    ctx.azar = Fijo(0.1)
    assert mut.bucle_for_o_while(ctx) == "bucle(while a for)"
    assert "for (; x; ) {" in c.imprimir_funcion(ctx.funcion)


def test_un_bucle_con_continue_propio_no_se_convierte() -> None:
    assert (
        aplicar(
            mut.bucle_for_o_while,
            cuerpo("for (x = 0; x < 4; x++) {", "    if (y) {", "        continue;", "    }", "}"),
        )[0]
        is None
    )
    assert (
        aplicar(
            mut.bucle_for_o_while,
            cuerpo("while (x) {", "    switch (y) {", "    case 1:", "        continue;", "    }", "}"),
        )[0]
        is None
    )


def test_el_continue_de_un_bucle_interior_no_impide_convertir_el_exterior() -> None:
    texto = cuerpo(
        "while (x) {",
        "    while (y) {",
        "        continue;",
        "    }",
        "    x--;",
        "}",
    )
    ctx = preparar(texto)
    ctx.azar = Fijo(0.9)
    assert mut.bucle_for_o_while(ctx) is not None


def test_una_funcion_sin_bucles_ni_condicionales_no_admite_esas_mutaciones() -> None:
    assert aplicar(mut.bucle_for_o_while, cuerpo("y = 1;"))[0] is None


# --- contexto de los sitios -------------------------------------------------------------------------


def sitios(texto: str) -> dict[str, tuple[bool, bool]]:
    expr = c.analizar_funcion(cuerpo(texto), "f", TIPOS).cuerpo.items[0]
    assert isinstance(expr, c.Expresion)
    return {an.texto_de(s.nodo): (s.perezoso, s.lvalue) for s in mut.sitios_de(expr.expr, expr)}


def test_los_sitios_marcan_la_evaluacion_condicional_y_los_destinos() -> None:
    assert sitios("y = x && o->radio;")["o->radio"] == (True, False)
    assert sitios("y = x ? o->radio : 1;")["x"] == (False, False)
    assert sitios("y = x ? o->radio : 1;")["o->radio"] == (True, False)
    assert sitios("o->valor = x;")["o->valor"] == (False, True)
    assert sitios("o->valor = x;")["o"] == (False, False)
    assert sitios("y = *(&x);")["x"] == (False, True)
    assert sitios("x++;")["x"] == (False, True)
    assert sitios("--x;")["x"] == (False, True)
    assert sitios("f(x);")["f"] == (False, True)
    assert sitios("f(x);")["x"] == (False, False)
    assert sitios("o->vec[x] = 1;")["o->vec"] == (False, True)
    assert sitios("a.b.c = 1;")["a"] == (False, True)
    assert sitios("a->b.c = 1;")["a"] == (False, False)
    assert sitios("a->b.c = 1;")["a->b"] == (False, True)


# --- orquestacion y filtro --------------------------------------------------------------------------

MUESTRA = cuerpo(
    "s32 r;",
    "r = o->radio + 1;",
    "o->valor = r;",
    "o->radio = x;",
    "for (x = 0; x < 3; x++) {",
    "    y += o->vec[x];",
    "}",
    "if (y > 2) {",
    "    o->valor = 1;",
    "} else {",
    "    o->valor = 2;",
    "}",
)


def test_mutar_no_modifica_la_base_y_cada_variante_se_vuelve_a_leer() -> None:
    tabla = an.construir_tabla([CABECERA])
    base = c.analizar_funcion(MUESTRA, "f", TIPOS)
    antes = c.imprimir_funcion(base)
    distintas = set()
    for semilla in range(120):
        variante, aplicadas = mut.mutar(base, tabla, azar(semilla), 1 + semilla % 3)
        assert 1 <= len(aplicadas) <= 3
        texto = c.imprimir_funcion(variante)
        assert c.imprimir_funcion(c.analizar_funcion(texto, "f", TIPOS)) == texto
        distintas.add(texto)
    assert c.imprimir_funcion(base) == antes
    assert len(distintas) > 20


def test_mutar_es_reproducible_con_la_misma_semilla() -> None:
    tabla = an.construir_tabla([CABECERA])
    base = c.analizar_funcion(MUESTRA, "f", TIPOS)
    una = mut.mutar(base, tabla, azar(5), 3)
    otra = mut.mutar(base, tabla, azar(5), 3)
    assert c.imprimir_funcion(una[0]) == c.imprimir_funcion(otra[0])
    assert una[1] == otra[1]


def test_una_funcion_sin_nada_que_mutar_devuelve_cero_mutaciones() -> None:
    tabla = an.construir_tabla([CABECERA])
    base = c.analizar_funcion("void f(void)\n{\n}", "f", TIPOS)
    variante, aplicadas = mut.mutar(base, tabla, azar(1), 2)
    assert aplicadas == []
    assert c.imprimir_funcion(variante) == c.imprimir_funcion(base)


def test_cada_mutacion_registrada_tiene_nombre_peso_y_funcion() -> None:
    nombres = [nombre for nombre, _, _ in mut.MUTACIONES]
    assert len(nombres) == len(set(nombres)) == 10
    assert all(peso > 0 for _, _, peso in mut.MUTACIONES)


# --- vecindario completo -----------------------------------------------------------------------------


def test_los_vecinos_enumeran_cada_mutacion_posible_de_una_en_una() -> None:
    tabla = an.construir_tabla([CABECERA])
    base = c.analizar_funcion(MUESTRA, "f", TIPOS)
    vecinos = list(mut.vecinos(base, tabla))
    descripciones = {descripcion.split("(")[0] for _, descripcion in vecinos}
    assert {
        "introducir_temporal",
        "orden_sentencias",
        "operandos_conmutados",
        "bucle",
        "condicion_invertida",
    } <= descripciones
    textos = {c.imprimir_funcion(v) for v, _ in vecinos}
    assert len(textos) > 15
    assert c.imprimir_funcion(base) not in textos
    for texto in textos:
        assert c.imprimir_funcion(c.analizar_funcion(texto, "f", TIPOS)) == texto


def test_los_vecinos_incluyen_cada_sitio_de_un_temporal() -> None:
    tabla = an.construir_tabla([CABECERA])
    base = c.analizar_funcion(cuerpo("o->valor = o->radio + x;", "y = o->radio;"), "f", TIPOS)
    sitios = {d for _, d in mut.vecinos(base, tabla) if d.startswith("introducir_temporal")}
    assert "introducir_temporal(s16 tmp1 = o->radio)" in sitios
    assert "introducir_temporal(s32 tmp1 = o->radio + x)" in sitios


def test_una_funcion_sin_nada_que_mutar_no_tiene_vecinos() -> None:
    tabla = an.construir_tabla([CABECERA])
    assert list(mut.vecinos(c.analizar_funcion("void f(void)\n{\n}", "f", TIPOS), tabla)) == []


# --- filtro de reglas -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "agregado",
    [
        'void g(void) { __asm__("nop"); }',
        'void g(void) { asm("nop"); }',
        "volatile s32 v;",
        "register s32 r;",
        'GLOBAL_ASM("x");',
    ],
)
def test_una_variante_que_agrega_construcciones_prohibidas_se_descarta(agregado: str) -> None:
    base = "s32 f(void)\n{\n    return 0;\n}"
    assert mut.variante_permitida(base, base)
    assert not mut.variante_permitida(base + "\n" + agregado, base)


def test_las_construcciones_que_ya_estaban_en_el_c_de_partida_se_admiten() -> None:
    base = 's32 f(void)\n{\n    __asm__("nop");\n    return 0;\n}'
    assert mut.variante_permitida(base, base)
    assert not mut.variante_permitida(base + '\n__asm__("nop");', base)


def test_los_comentarios_y_las_cadenas_no_cuentan_como_construcciones_prohibidas() -> None:
    base = "s32 f(void)\n{\n    return 0;\n}"
    variante = (
        's32 f(void)\n{\n    /* volatile register asm( */\n    puts("volatile __asm__");\n    return 0;\n}'
    )
    assert mut.variante_permitida(variante, base)
    assert mut.contar_prohibidos(variante) == [0, 0, 0, 0, 0]


def test_ninguna_mutacion_genera_construcciones_prohibidas() -> None:
    tabla = an.construir_tabla([CABECERA])
    base = c.analizar_funcion(MUESTRA, "f", TIPOS)
    texto_base = c.imprimir_funcion(base)
    for semilla in range(150):
        variante, _ = mut.mutar(base, tabla, azar(semilla), 3)
        assert mut.variante_permitida(c.imprimir_funcion(variante), texto_base)


# --- nombres repetidos entre ambitos ----------------------------------------------------------------

DOS_TMP_HERMANAS = cuerpo(
    "if (x) {",
    "    s16 tmp;",
    "    tmp = o->radio;",
    "    o->valor = tmp;",
    "} else {",
    "    s32 tmp;",
    "    tmp = y;",
    "    o->valor = tmp + tmp;",
    "}",
)


def test_los_nombres_ambiguos_son_los_declarados_dos_veces_o_que_sombrean_un_parametro() -> None:
    ctx = preparar(DOS_TMP_HERMANAS)
    assert mut.nombres_ambiguos(ctx.funcion) == {"tmp"}
    sombra = preparar(cuerpo("s32 x;", "s32 z;", "x = z;"))
    assert mut.nombres_ambiguos(sombra.funcion) == {"x"}
    assert mut.nombres_ambiguos(preparar(cuerpo("s32 a;", "a = x;")).funcion) == set()


def test_eliminar_temporal_no_toca_locales_homonimas_de_bloques_hermanos() -> None:
    for semilla in range(20):
        descripcion, texto = aplicar(mut.eliminar_temporal, DOS_TMP_HERMANAS, semilla)
        assert descripcion is None
        assert texto.count("s16 tmp;") == 1 and texto.count("s32 tmp;") == 1


def test_eliminar_temporal_no_usa_una_expresion_que_menciona_un_nombre_ambiguo() -> None:
    texto = cuerpo(
        "s32 t;",
        "if (x) {",
        "    s32 y;",
        "    y = 1;",
        "}",
        "t = y;",
        "o->valor = t;",
    )
    assert aplicar(mut.eliminar_temporal, texto)[0] is None


def test_ancho_de_temporal_no_toca_locales_homonimas_de_bloques_hermanos() -> None:
    for semilla in range(20):
        descripcion, texto = aplicar(mut.ancho_de_temporal, DOS_TMP_HERMANAS, semilla)
        assert descripcion is None
        assert texto.count("s16 tmp;") == 1 and texto.count("s32 tmp;") == 1


def test_ancho_de_temporal_no_acepta_valores_que_mencionan_un_nombre_ambiguo() -> None:
    texto = cuerpo(
        "s32 r;",
        "if (x) {",
        "    s16 y;",
        "    y = 1;",
        "}",
        "r = y;",
        "o->valor = r;",
    )
    for semilla in range(20):
        assert aplicar(mut.ancho_de_temporal, texto, semilla)[0] is None


def test_copiar_parametro_no_actua_si_una_local_de_un_bloque_anidado_lo_sombrea() -> None:
    texto = cuerpo(
        "o->radio = 1;", "if (x) {", "    s32 y;", "    y = 2;", "}", firma="void f(Objeto* o, s32 x, s32 y)"
    )
    for semilla in range(20):
        descripcion, resultado = aplicar(mut.copiar_parametro, texto, semilla)
        assert descripcion is not None and "(y en" not in descripcion
        assert "s32 y;" in resultado
    solo_homonimo = cuerpo("if (x) {", "    s32 o;", "    o = 2;", "}", firma="void f(s32 o, s32 x)")
    assert "(o en" not in (aplicar(mut.copiar_parametro, solo_homonimo)[0] or "")


def test_introducir_temporal_no_genera_un_nombre_declarado_en_un_bloque_anidado() -> None:
    texto = cuerpo(
        "if (x) {", "    s32 tmp1;", "    tmp1 = y;", "    o->valor = tmp1;", "}", "o->radio = o->valor + 1;"
    )
    for semilla in range(40):
        descripcion, resultado = aplicar(mut.introducir_temporal, texto, semilla)
        assert descripcion is not None and "tmp2" in descripcion
        assert resultado.count("s32 tmp1;") == 1
        assert len(re.findall(r"^ +\S+ tmp2;$", resultado, re.MULTILINE)) == 1


def test_introducir_temporal_no_toma_expresiones_con_nombres_ambiguos() -> None:
    texto = cuerpo("if (x) {", "    s16 y;", "    y = 1;", "}", "o->valor = y + 1;")
    for semilla in range(30):
        descripcion, _ = aplicar(mut.introducir_temporal, texto, semilla)
        assert descripcion is None or ("= y" not in descripcion and "y +" not in descripcion)


def test_con_nombres_unicos_las_mutaciones_siguen_funcionando() -> None:
    texto = cuerpo("s16 a;", "s32 b;", "b = 5;", "a = o->radio;", "o->valor = a + b;")
    assert aplicar(mut.eliminar_temporal, texto)[0] is not None
    assert aplicar(mut.ancho_de_temporal, texto)[0] is not None
    assert aplicar(mut.introducir_temporal, texto)[0] is not None
    assert aplicar(mut.copiar_parametro, texto)[0] is not None


FUENTE_CON_BARRERAS = """typedef struct Objeto {
    s32 valor;
} Objeto;
u8 D_80069458;
Objeto* D_80069698;

void func_Previa(s32 a)
{
    if (a) {
        a = 1;
    }
    return;
}

u32 func_Audio(Objeto* o)
{
    if (D_80069458 == 0) {
        return 0;
    }
    if (o == D_80069698 || o == 0) {
        return D_80069458 | (D_80069458 << 8);
    }
    return (D_80069458 << 8) | (o->valor & 0xFF) | 1;
}
"""


def _sin_espacios(texto: str) -> str:
    return re.sub(r"\s+", "", texto)


def test_una_funcion_con_or_de_bits_y_desplazamientos_se_reescribe_identica_salvo_espacios() -> None:
    """Una funcion que ya cierra con `|`, `||` y `<<` no debe rechazarse ni cambiar de significado.

    El archivo trae antes un `}` seguido de `return;`, que la tabla de tipos no debe tomar por un typedef:
    si lo hiciera, `return D | (...)` se leeria como una declaracion y la funcion no se podria permutar.
    """
    tabla = an.construir_tabla([FUENTE_CON_BARRERAS])
    assert "return" not in tabla.nombres_de_tipo
    inicio, fin = c.localizar_funcion(FUENTE_CON_BARRERAS, "func_Audio")
    original = FUENTE_CON_BARRERAS[inicio:fin]
    funcion = c.analizar_funcion(original, "func_Audio", tabla.nombres_de_tipo)
    reescrito = c.imprimir_funcion(funcion)
    assert _sin_espacios(reescrito) == _sin_espacios(original)
    relectura = c.analizar_funcion(reescrito, "func_Audio", tabla.nombres_de_tipo)
    assert c.imprimir_funcion(relectura) == reescrito


def test_conmutar_operandos_de_un_or_de_bits_conserva_el_significado_al_reescribir() -> None:
    texto = cuerpo("o->valor = x | (y << 8);", firma="void f(Objeto* o, s32 x, s32 y)")
    for semilla in range(20):
        descripcion, resultado = aplicar(mut.operandos_conmutados, texto, semilla)
        assert descripcion is not None
        relectura = c.analizar_funcion(resultado, "f", TIPOS)
        assert c.imprimir_funcion(relectura) == resultado
        assert resultado.count("<< 8") == 1 and "(y << 8)" in resultado


def test_un_puntero_a_arreglo_declarado_con_tipo_entero_base_no_cambia_de_ancho() -> None:
    texto = cuerpo("s16 (*pos)[2];", "s16 r;", "r = 5;", "o->valor = r;")
    for semilla in range(6):
        _, salida = aplicar(mut.ancho_de_temporal, texto, semilla)
        assert "s16 (*pos)[2];" in salida

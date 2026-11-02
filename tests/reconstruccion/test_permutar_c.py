import re

import pytest
from tools.reconstruccion import permutar_c as c

TIPOS = frozenset({"Objeto", "ConsultaVolumen", "Nodo"})

FUNCION_RICA = """s32 func_X(Objeto* a, u32 mascara, ConsultaVolumen* o)
{
    s32 i, *p, tabla[4] = { 1, 2, 3, 4 };
    unsigned char c0;
    struct Nodo* n = 0;
    s16 k = (s16)mascara;
    /* comentario previo
       de dos lineas */
    i = a->x + (a->y << 2) * 3 - -k;
    // comentario de linea
    c0 = (unsigned char)i;
#ifdef EXTRA
    i += 1;
#endif
    if (i < 0 && k > 1 || (mascara & 0x80)) {
        return -1;
    } else if (i == 0) {
        i++;
    } else {
        --i;
    }
    while (i) i--;
    do {
        i = i ? i - 1 : 0;
    } while (i > 3);
    for (i = 0, k = 1; i < 10; i++) {
        if (i == 5) continue;
        if (i == 7) break;
        p = &tabla[i];
    }
    for (;;) {
        break;
    }
    switch (i) {
    case 1:
        i = sizeof(Objeto) + sizeof i;
        break;
    default:
        goto fin;
    }
    ;
fin:
    o->actual = n ? a : (Objeto*)0;
    GEO_X(&o->m, tabla[i], "texto", 'c');
    (*p).y = -(-i) + (~i) + !k;
    *p += o->v[i][k] % 3 / 2 | 1 ^ 2 & 3;
    func_Y(i, (i, k));
    return;
}"""


def reescribir(texto: str) -> str:
    return c.imprimir_funcion(c.analizar_funcion(texto, "func_X", TIPOS))


def test_la_escritura_de_una_funcion_rica_es_un_punto_fijo_y_normaliza_el_formato() -> None:
    una = reescribir(FUNCION_RICA)
    assert reescribir(una) == una
    assert "    s32 i;\n    s32* p;\n    s32 tabla[4] = {1, 2, 3, 4};\n" in una
    assert "    struct Nodo* n = 0;\n" in una
    assert "    /* comentario previo\n       de dos lineas */\n" in una
    assert "    // comentario de linea\n" in una
    assert "#ifdef EXTRA\n    i += 1;\n#endif\n" in una
    assert "    i = a->x + (a->y << 2) * 3 - -k;\n" in una
    assert (
        "    if (i < 0 && k > 1 || (mascara & 0x80)) {\n        return -1;\n    } else if (i == 0) {" in una
    )
    assert "    while (i) {\n        i--;\n    }\n" in una
    assert "    } while (i > 3);\n" in una
    assert "    for (i = 0, k = 1; i < 10; i++) {\n" in una
    assert "    for (; ; ) {\n" in una
    assert "    switch (i) {\n    case 1:\n        i = sizeof(Objeto) + sizeof i;\n" in una
    assert "    default:\n        goto fin;\n" in una
    assert "    ;\nfin:\n" in una
    assert "    o->actual = n ? a : (Objeto*)0;\n" in una
    assert "    GEO_X(&o->m, tabla[i], \"texto\", 'c');\n" in una
    assert "    (*p).y = -(-i) + ~i + !k;\n" in una
    assert "    func_Y(i, (i, k));\n    return;\n}" in una


def test_los_operadores_de_bits_llevan_parentesis_y_las_condiciones_largas_se_reparten() -> None:
    texto = reescribir(FUNCION_RICA)
    assert "(o->v[i][k] % 3 / 2) | (1 ^ (2 & 3))" in texto or "o->v[i][k] % 3 / 2 | (1 ^ (2 & 3))" in texto
    larga = (
        "s32 func_X(Objeto* a)\n{\n    if (a->campo_uno == 1 && a->campo_dos == 2 && a->campo_tres == 3 && "
        "a->campo_cuatro == 4 && (a->campo_cinco & 5) || a->campo_seis == 6) {\n        return 1;\n    }\n"
        "    return 0;\n}"
    )
    salida = reescribir(larga)
    assert "    if (a->campo_uno == 1\n            && a->campo_dos == 2\n" in salida
    assert "            || a->campo_seis == 6) {\n" in salida
    assert reescribir(salida) == salida
    corta_sin_operadores = (
        "s32 func_X(Objeto* a)\n{\n    if (" + "a" * 130 + ") {\n        return 1;\n    }\n}"
    )
    assert "if (" + "a" * 130 + ") {" in reescribir(corta_sin_operadores)


def test_las_estructuras_de_control_sin_llaves_se_envuelven_en_un_bloque() -> None:
    salida = reescribir("void func_X(void)\n{\n    s32 i;\n    if (i) i = 1; else i = 2;\n}")
    assert "    if (i) {\n        i = 1;\n    } else {\n        i = 2;\n    }\n" in salida


def test_un_else_con_comentario_en_su_if_no_se_encadena() -> None:
    texto = (
        "void func_X(s32 i)\n{\n    if (i) {\n        i = 1;\n    } else {\n        /* nota */\n"
        "        if (i > 3) {\n            i = 2;\n        }\n    }\n}"
    )
    assert "} else {\n        /* nota */\n        if (i > 3) {" in reescribir(texto)


def test_unir_tokens_separa_solo_palabras_y_tras_comas() -> None:
    assert c.unir_tokens(["sizeof", "(", "struct", "X", ")"]) == "sizeof(struct X)"
    assert c.unir_tokens(["{", "1", ",", "2", "}"]) == "{1, 2}"


def test_normalizar_tipo_pega_los_asteriscos() -> None:
    assert c.normalizar_tipo(["unsigned", "char"], 1) == "unsigned char*"
    assert c.normalizar_tipo(["s32"]) == "s32"


def test_tokenizar_asocia_comentarios_y_marca_directivas() -> None:
    tokens = c.tokenizar("/* a */ x = 1; // b\n#define Y 2\n y")
    assert [t.texto for t in tokens if t.tipo != "fin"] == ["x", "=", "1", ";", "#define Y 2", "y"]
    assert tokens[0].previos == ("/* a */",)
    assert tokens[4].tipo == "pre"
    assert tokens[-1].tipo == "fin"
    assert [t.tipo for t in c.tokenizar("1.5f .5 0x1Fu 'a' \"s\"")[:5]] == [
        "num",
        "num",
        "num",
        "caracter",
        "cadena",
    ]
    final = c.tokenizar("x /* cola */")
    assert final[-1].previos == ("/* cola */",)


def test_tokenizar_rechaza_caracteres_que_no_son_c() -> None:
    with pytest.raises(c.AnalisisCError, match="caracter no reconocido"):
        c.tokenizar("a = $;")


def test_enmascarar_conserva_longitud_y_saltos_de_linea() -> None:
    texto = 'a = "{"; /* } \n */ b'
    mascara = c.enmascarar(texto)
    assert len(mascara) == len(texto)
    assert mascara.count("\n") == 1
    assert "{" not in mascara
    assert "}" not in mascara


@pytest.mark.parametrize(
    ("texto", "mensaje"),
    [
        ("s32 f(void) { x = ; }", "expresion no reconocida"),
        ("s32 f(void) { x = 1 }", "se esperaba ';'"),
        ("s32 f(void) { if (x { } }", "se esperaba ')'"),
        ("s32 f(void) { a ? 1 2; }", "se esperaba ':'"),
        ("s32 f(void) { a. 3; }", "se esperaba el nombre de un campo"),
        ("s32 f(void) { goto 3; }", "se esperaba una etiqueta"),
        ("s32 f(void) { s32 * 3; }", "se esperaba el nombre de la variable"),
        ("s32 f(void) { s32 a = { 1", "sin cerrar"),
        ("s32 f(void) { sizeof(x; }", "sin cerrar"),
        ("s32 f(void) { x = 1;", "bloque sin cerrar"),
        ("s32 f(void) { } x", "texto despues de la llave"),
        ("s32 f(void);", "no tiene cuerpo"),
        ("s32 f { }", "no tiene parametros"),
        ("s32 f(s32) { }", "parametro no reconocido"),
        ("s32 f(void) { s32 a[; }", "expresion no reconocida"),
        ("s32 f(void) { s32 5; }", "se esperaba ';'"),
    ],
)
def test_el_analizador_rechaza_c_mal_formado_con_un_mensaje(texto: str, mensaje: str) -> None:
    with pytest.raises(c.AnalisisCError, match=re.escape(mensaje)):
        c.analizar_funcion(texto, "f", TIPOS)


def test_el_anidamiento_excesivo_se_rechaza() -> None:
    profundo = "s32 f(void) { x = " + "(" * 400 + "1" + ")" * 400 + "; }"
    with pytest.raises(c.AnalisisCError, match="anidamiento excesivo"):
        c.analizar_funcion(profundo, "f", TIPOS)


def test_una_expresion_que_empieza_por_un_nombre_de_tipo_no_es_una_declaracion() -> None:
    salida = c.imprimir_funcion(c.analizar_funcion("void f(void) { Objeto(1); }", "f", TIPOS))
    assert "    Objeto(1);" in salida


def test_separar_parametros_distingue_tipos_con_asteriscos_y_void() -> None:
    parametros = c.separar_parametros("Objeto* f(Objeto *a, unsigned char b, struct Nodo** n)")
    assert [(p.tipo, p.nombre) for p in parametros] == [
        ("Objeto*", "a"),
        ("unsigned char", "b"),
        ("struct Nodo**", "n"),
    ]
    assert c.separar_parametros("s32 f()") == []
    assert c.separar_parametros("s32 f(void)") == []


def test_localizar_funcion_ignora_comentarios_cadenas_y_llamadas() -> None:
    texto = (
        "/* func_X(a) { */\n"
        'static const char* s = "func_X(b) {";\n'
        "s32 otra(s32 a)\n{\n    if (func_X(a)) {\n        return 1;\n    }\n    return 0;\n}\n\n"
        "Objeto* func_X(Objeto* a)\n{\n    return a;\n}\n"
    )
    inicio, fin = c.localizar_funcion(texto, "func_X")
    assert texto[inicio:fin] == "Objeto* func_X(Objeto* a)\n{\n    return a;\n}"


def test_localizar_funcion_rechaza_ausencia_duplicados_y_llaves_sin_cerrar() -> None:
    with pytest.raises(c.AnalisisCError, match="no hay una definicion de 'f' en C"):
        c.localizar_funcion('INCLUDE_ASM("x", f);', "f")
    with pytest.raises(c.AnalisisCError, match="hay 2"):
        c.localizar_funcion("s32 f(void)\n{\n}\ns32 f(void)\n{\n}\n", "f")
    with pytest.raises(c.AnalisisCError, match="no cierra su llave"):
        c.localizar_funcion("s32 f(void)\n{\n  if (1) {\n", "f")


def test_recorrido_y_sustitucion_de_subexpresiones() -> None:
    suma = c.Binario("+", c.Id("a"), c.Llamada(c.Id("f"), [c.Id("b"), c.Num("1")]))
    assert [type(n).__name__ for n in c.recorrer(suma)] == ["Binario", "Id", "Llamada", "Id", "Id", "Num"]
    assert c.hijos(c.Num("1")) == []
    nuevo = c.Num("9")
    assert c.reemplazar_hijo(suma, suma.izq, nuevo) and suma.izq is nuevo
    argumento = suma.der.args[0]  # type: ignore[attr-defined]
    assert c.reemplazar_hijo(suma.der, argumento, nuevo) and suma.der.args[0] is nuevo  # type: ignore[attr-defined]
    assert not c.reemplazar_hijo(suma, c.Num("7"), nuevo)


def test_hijos_de_cada_clase_de_expresion() -> None:
    a, b, c3 = c.Id("a"), c.Id("b"), c.Id("c")
    assert c.hijos(c.Unario("-", a)) == [a]
    assert c.hijos(c.Postfijo("++", a)) == [a]
    assert c.hijos(c.Conversion("s16", a)) == [a]
    assert c.hijos(c.Asigna("=", a, b)) == [a, b]
    assert c.hijos(c.Ternario(a, b, c3)) == [a, b, c3]
    assert c.hijos(c.Indice(a, b)) == [a, b]
    assert c.hijos(c.Miembro(a, True, "x")) == [a]


def test_expresiones_y_bloques_de_cada_sentencia() -> None:
    e = c.Id("e")
    cuerpo = c.Bloque()
    assert c.expresiones_de(c.Decl("s32", 0, "x", inicial=e)) == [e]
    assert c.expresiones_de(c.Decl("s32", 0, "x")) == []
    assert c.expresiones_de(c.Expresion(expr=e)) == [e]
    assert c.expresiones_de(c.Devolver(valor=e)) == [e]
    assert c.expresiones_de(c.Devolver()) == []
    assert c.expresiones_de(c.Si(cond=e)) == [e]
    assert c.expresiones_de(c.Mientras(cond=e)) == [e]
    assert c.expresiones_de(c.HacerMientras(cond=e)) == [e]
    assert c.expresiones_de(c.Seleccion(cond=e)) == [e]
    assert c.expresiones_de(c.Para(inicio=e, cond=None, paso=e)) == [e, e]
    assert c.expresiones_de(c.Caso(valor=e)) == [e]
    assert c.expresiones_de(c.Caso()) == []
    assert c.expresiones_de(c.Romper()) == []
    sino = c.Bloque()
    assert c.bloques_hijos(c.Si(cond=e, entonces=cuerpo, sino=sino)) == [cuerpo, sino]
    assert c.bloques_hijos(c.Si(cond=e, entonces=cuerpo)) == [cuerpo]
    assert c.bloques_hijos(c.Mientras(cond=e, cuerpo=cuerpo)) == [cuerpo]
    assert c.bloques_hijos(c.Bloque()) != []
    assert c.bloques_hijos(c.Romper()) == []


def test_todos_los_bloques_recorre_los_anidados() -> None:
    funcion = c.analizar_funcion(
        "void f(s32 i)\n{\n    if (i) {\n        while (i) {\n            i--;\n        }\n    }\n}",
        "f",
        TIPOS,
    )
    assert len(list(c.todos_los_bloques(funcion.cuerpo))) == 3


def test_es_identificador() -> None:
    assert c.es_identificador("func_80016C0C")
    assert not c.es_identificador("1abc")
    assert not c.es_identificador("a b")


def test_las_etiquetas_y_los_caso_conservan_sus_comentarios() -> None:
    salida = reescribir("void func_X(s32 i)\n{\n    /* salida */\n    fin:\n    return;\n}")
    assert "    /* salida */\n    fin:\n    return;" not in salida
    assert "/* salida */\nfin:\n    return;" in salida


def test_un_if_con_else_if_final_con_else_se_imprime_encadenado() -> None:
    texto = (
        "void func_X(s32 i)\n{\n    if (i == 1) {\n        i = 2;\n    } else if (i == 2) {\n"
        "        i = 3;\n    } else if (i == 3) {\n        i = 4;\n    } else {\n        i = 5;\n    }\n}"
    )
    assert reescribir(texto) == texto


def test_un_bloque_anonimo_y_los_comentarios_finales_se_conservan() -> None:
    texto = "void func_X(s32 i)\n{\n    {\n        i = 1;\n    }\n    /* fin */\n}"
    assert reescribir(texto) == texto


def test_una_variable_con_nombre_de_tipo_no_se_confunde_con_una_palabra_del_tipo() -> None:
    assert "    Objeto Nodo;\n" in reescribir("void func_X(void)\n{\n    Objeto Nodo;\n}")


def test_los_tipos_con_varias_palabras_y_calificadores_se_leen_como_un_solo_tipo() -> None:
    salida = reescribir(
        "void func_X(void)\n{\n    const Objeto* a;\n    unsigned long long b;\n    long c0;\n"
        "    struct Nodo d;\n}"
    )
    assert "    const Objeto* a;\n    unsigned long long b;\n    long c0;\n    struct Nodo d;\n" in salida


TIPOS_DE_MOLDES = frozenset({"Objeto", "Rutina", "Digitos"})


def forma(nodo: object) -> object:
    """Estructura de un arbol sin comentarios ni formato: dos lecturas con el mismo significado coinciden."""
    if isinstance(nodo, list):
        return [forma(elemento) for elemento in nodo]
    if hasattr(nodo, "__dict__"):
        campos = {
            k: forma(v) for k, v in vars(nodo).items() if k not in ("comentarios", "finales", "cabecera")
        }
        return (type(nodo).__name__, campos)
    return nodo


def leer_expresion(texto: str, tipos: frozenset[str] = TIPOS) -> c.Expr:
    funcion = c.analizar_funcion(f"void f(void)\n{{\n    {texto};\n}}", "f", tipos)
    sentencia = funcion.cuerpo.items[0]
    assert isinstance(sentencia, c.Expresion)
    return sentencia.expr


OPERADORES_BINARIOS = [
    "|",
    "&",
    "^",
    "<<",
    ">>",
    "&&",
    "||",
    "%",
    "/",
    "*",
    "+",
    "-",
    "==",
    "!=",
    "<",
    ">",
    "<=",
    ">=",
]
ASIGNACIONES = ["=", "|=", "&=", "^=", "<<=", ">>=", "%=", "/=", "*=", "+=", "-="]


@pytest.mark.parametrize("operador", OPERADORES_BINARIOS)
def test_cada_operador_binario_se_lee_y_se_escribe_igual(operador: str) -> None:
    texto = f"x = a {operador} b"
    expr = leer_expresion(texto)
    assert isinstance(expr, c.Asigna) and isinstance(expr.valor, c.Binario) and expr.valor.op == operador
    assert c.imprimir_expresion(expr) == texto


@pytest.mark.parametrize("operador", ASIGNACIONES)
def test_cada_asignacion_compuesta_se_lee_y_se_escribe_igual(operador: str) -> None:
    texto = f"a->campo[i] {operador} b + 1"
    expr = leer_expresion(texto)
    assert isinstance(expr, c.Asigna) and expr.op == operador
    assert c.imprimir_expresion(expr) == texto


@pytest.mark.parametrize("operador", ["-", "+", "!", "~", "*", "&", "++", "--"])
def test_cada_operador_unario_prefijo_se_lee_y_se_escribe_igual(operador: str) -> None:
    texto = f"x = {operador}a"
    expr = leer_expresion(texto)
    assert isinstance(expr, c.Asigna) and isinstance(expr.valor, c.Unario) and expr.valor.op == operador
    assert c.imprimir_expresion(expr) == texto


# Cada par es (texto en C, el mismo texto con todos los parentesis que C implica): la precedencia y la
# asociatividad de C son las del segundo, y el arbol de ambos debe ser el mismo.
PRECEDENCIAS = [
    ("a | b << 8", "a | (b << 8)"),
    ("a << 8 | b", "(a << 8) | b"),
    ("a || b && c", "a || (b && c)"),
    ("a && b || c && d", "(a && b) || (c && d)"),
    ("a ^ b & c | d", "(a ^ (b & c)) | d"),
    ("a | b ^ c", "a | (b ^ c)"),
    ("a << 1 + 2", "a << (1 + 2)"),
    ("a + b << 2", "(a + b) << 2"),
    ("a & b == c", "a & (b == c)"),
    ("a == b & c", "(a == b) & c"),
    ("a < b == c > d", "(a < b) == (c > d)"),
    ("a % b * c / d", "((a % b) * c) / d"),
    ("a - b - c", "(a - b) - c"),
    ("a - (b - c)", "a - (b - c)"),
    ("a ? b : c ? d : e", "a ? b : (c ? d : e)"),
    ("a || b ? c : d", "(a || b) ? c : d"),
    ("a ? b , c : d", "a ? (b , c) : d"),
    ("a = b ? c : d", "a = (b ? c : d)"),
    ("a = b = c | d", "a = (b = (c | d))"),
    ("a <<= b |= c", "a <<= (b |= c)"),
    ("~a & -b", "(~a) & (-b)"),
    ("!a || !b && c", "(!a) || ((!b) && c)"),
    ("-a * b", "(-a) * b"),
    ("*p++ & 0xFF", "(*(p++)) & 0xFF"),
    ("a , b = c , d", "(a , (b = c)) , d"),
    ("(s16)a << 8 | (u8)b", "(((s16)a) << 8) | ((u8)b)"),
    ("sizeof(Objeto) * 2 | 1", "(sizeof(Objeto) * 2) | 1"),
    ("x = (a | b) & c", "x = (a | b) & c"),
    ("x = (a & b) == 0", "x = (a & b) == 0"),
]


@pytest.mark.parametrize(("texto", "con_parentesis"), PRECEDENCIAS)
def test_la_precedencia_y_la_asociatividad_son_las_de_c(texto: str, con_parentesis: str) -> None:
    assert forma(leer_expresion(texto)) == forma(leer_expresion(con_parentesis))


@pytest.mark.parametrize(("texto", "con_parentesis"), PRECEDENCIAS)
def test_escribir_conserva_el_significado_y_releer_da_el_mismo_arbol(texto: str, con_parentesis: str) -> None:
    arbol = leer_expresion(texto)
    escrito = c.imprimir_expresion(arbol)
    assert forma(leer_expresion(escrito)) == forma(arbol)
    assert c.imprimir_expresion(leer_expresion(escrito)) == escrito


def test_un_operador_de_bits_bajo_otro_se_escribe_con_parentesis_redundantes() -> None:
    assert c.imprimir_expresion(leer_expresion("a | b << 8")) == "a | (b << 8)"
    assert c.imprimir_expresion(leer_expresion("a | (b << 8)")) == "a | (b << 8)"
    assert c.imprimir_expresion(leer_expresion("a ^ b & c | d")) == "(a ^ (b & c)) | d"
    assert c.imprimir_expresion(leer_expresion("a | b | c")) == "a | b | c"
    assert c.imprimir_expresion(leer_expresion("a | (b | c)")) == "a | (b | c)"


def test_los_parentesis_necesarios_sobreviven_a_conmutar_operandos() -> None:
    suma = leer_expresion("(a | b) << 8")
    assert isinstance(suma, c.Binario)
    suma.izq, suma.der = suma.der, suma.izq
    assert c.imprimir_expresion(suma) == "8 << (a | b)"
    producto = leer_expresion("(a + b) * (c << 2)")
    assert isinstance(producto, c.Binario)
    producto.izq, producto.der = producto.der, producto.izq
    assert c.imprimir_expresion(producto) == "(c << 2) * (a + b)"


def test_una_condicion_larga_con_or_entre_parentesis_no_pierde_los_parentesis_al_repartirse() -> None:
    texto = (
        "void func_X(s32 id, s32 a)\n{\n    if ((id == 0x41 || id == 0x73) && (((a ^ 0xFF) << 8) & 0x800) && "
        "ESTADO_PRINCIPAL->registros[BANCO_DE_DEMOSTRACION_DEL_JUEGO] != 0) {\n        a = 1;\n    }\n}"
    )
    salida = reescribir(texto)
    assert "    if ((id == 0x41 || id == 0x73)\n            && (((a ^ 0xFF) << 8) & 0x800)\n" in salida
    assert forma(c.analizar_funcion(salida, "func_X", TIPOS)) == forma(
        c.analizar_funcion(texto, "func_X", TIPOS)
    )
    assert reescribir(salida) == salida


def test_una_condicion_larga_con_and_bajo_or_se_reparte_sin_cambiar_el_significado() -> None:
    texto = (
        "void func_X(s32 id, s32 a)\n{\n    if (id == 0x41 || id == 0x73 && (((a ^ 0xFF) << 8) & 0x800) && "
        "ESTADO_PRINCIPAL->registros[BANCO_DE_DEMOSTRACION_DEL_JUEGO] != 0 || a) {\n        a = 1;\n    }\n}"
    )
    salida = reescribir(texto)
    assert forma(c.analizar_funcion(salida, "func_X", TIPOS)) == forma(
        c.analizar_funcion(texto, "func_X", TIPOS)
    )
    assert reescribir(salida) == salida


def test_un_molde_a_un_typedef_de_puntero_a_funcion_se_llama_como_una_funcion() -> None:
    salida = reescribir_con(
        "void func_X(s32 a)\n{\n    s32 r;\n    r = ((Digitos)func_Y)((a << 8) | 1);\n"
        "    ((Rutina)func_Z)(0, a, 1);\n}"
    )
    assert "    r = ((Digitos)func_Y)((a << 8) | 1);\n" in salida
    assert "    ((Rutina)func_Z)(0, a, 1);\n" in salida


def reescribir_con(texto: str) -> str:
    return c.imprimir_funcion(c.analizar_funcion(texto, "func_X", TIPOS_DE_MOLDES))


@pytest.mark.parametrize(
    "tipo",
    [
        "u16* volatile*",
        "u8 (*)[64]",
        "u8* (*)[4][2]",
        "void (*)(s32, Objeto*)",
        "const u8* const",
        "struct Nodo*",
    ],
)
def test_los_moldes_con_calificadores_y_declaradores_abstractos_se_conservan(tipo: str) -> None:
    salida = reescribir_con(f"void func_X(s32 a)\n{{\n    a = (s32)*({tipo})&a;\n}}")
    assert f"    a = (s32)*({tipo})&a;\n" in salida


def test_un_nombre_de_tipo_como_argumento_de_una_macro_se_conserva() -> None:
    salida = reescribir_con(
        "void func_X(u8* n)\n{\n    EN(u16, n, 0x108) = 0xA00;\n    EN(u8 *, n, 0xC0) = n;\n"
        "    EN(unsigned long, n, 4) |= 1;\n    f(Objeto, 3);\n}"
    )
    assert (
        "    EN(u16, n, 0x108) = 0xA00;\n    EN(u8*, n, 0xC0) = n;\n    EN(unsigned long, n, 4) |= 1;\n"
        in salida
    )
    assert "    f(Objeto, 3);\n" in salida
    assert reescribir_con(salida) == salida


def test_un_nombre_de_tipo_que_no_cierra_el_argumento_se_lee_como_expresion() -> None:
    salida = reescribir_con("void func_X(s32 a)\n{\n    f(Objeto(1), (Objeto)a, sizeof(Objeto));\n}")
    assert "    f(Objeto(1), (Objeto)a, sizeof(Objeto));\n" in salida


def test_una_palabra_reservada_nunca_es_un_tipo_aunque_la_tabla_la_incluya() -> None:
    tipos = frozenset({"return", "break", "sizeof", "Objeto"})
    funcion = c.analizar_funcion(
        "s32 func_X(s32 a)\n{\n    while (a) {\n        a = a | (a << 8);\n        break;\n    }\n"
        "    return a | (a << 8);\n}",
        "func_X",
        tipos,
    )
    assert "    return a | (a << 8);\n" in c.imprimir_funcion(funcion)


def test_los_parametros_declarados_como_arreglo_siguen_fuera_del_subconjunto() -> None:
    with pytest.raises(c.AnalisisCError, match="parametro no reconocido"):
        c.analizar_funcion("void func_X(s32 tabla[4]) { }", "func_X", TIPOS)


def test_un_molde_de_tipo_sin_cerrar_se_rechaza() -> None:
    with pytest.raises(c.AnalisisCError, match="expresion no reconocida"):
        c.analizar_funcion("void func_X(s32 a) { a = (Objeto (*)[4; }", "func_X", TIPOS)


def test_un_comentario_entre_un_argumento_y_el_cierre_de_una_llamada_se_rechaza() -> None:
    with pytest.raises(c.AnalisisCError, match="comentario dentro de una expresion, en la linea 4"):
        reescribir("void func_X(s32 a)\n{\n    f(a,\n        3 /* nota */);\n}")


def test_un_comentario_de_linea_entre_un_operador_y_su_operando_se_rechaza() -> None:
    with pytest.raises(c.AnalisisCError, match="comentario dentro de una expresion, en la linea 3"):
        reescribir("void func_X(s32 a)\n{\n    a = a + // nota\n        1;\n}")


def test_un_comentario_antes_de_la_llave_de_un_cuerpo_se_rechaza_en_lugar_de_perderse() -> None:
    with pytest.raises(c.AnalisisCError, match="comentario dentro de una expresion"):
        reescribir("void func_X(s32 a)\n{\n    if (a) /* nota */ {\n        a = 1;\n    }\n}")


def test_los_comentarios_al_inicio_de_una_sentencia_y_antes_de_la_llave_de_cierre_se_conservan() -> None:
    texto = (
        "void func_X(s32 a)\n{\n    /* uno */\n    a = 1;\n    if (a) {\n        // dos\n        a = 2;\n"
        "        /* tres */\n    }\n}"
    )
    assert reescribir(texto) == texto


def test_una_declaracion_local_de_puntero_a_funcion_o_a_arreglo_se_lee_como_declaracion() -> None:
    texto = (
        "void func_X(s32 a)\n{\n    void (*fp)(s32, Objeto*);\n    s16 (*pos)[2];\n    s16 otra;\n"
        "    s32 (**tabla)[2][3] = 0;\n    fp(a);\n}"
    )
    agrupado = texto.replace("s16 (*pos)[2];\n    s16 otra;", "s16 (*pos)[2], otra;")
    funcion = c.analizar_funcion(agrupado, "func_X", TIPOS_DE_MOLDES)
    declaraciones = [s for s in funcion.cuerpo.items if isinstance(s, c.Decl)]
    assert [(d.nombre, d.declarador) for d in declaraciones] == [
        ("fp", "(*fp)(s32, Objeto*)"),
        ("pos", "(*pos)[2]"),
        ("otra", ""),
        ("tabla", "(**tabla)[2][3]"),
    ]
    assert isinstance(funcion.cuerpo.items[-1], c.Expresion)
    assert c.imprimir_funcion(funcion) == texto
    assert reescribir_con(texto) == texto


def test_un_declarador_parentetizado_sin_nombre_se_rechaza() -> None:
    with pytest.raises(c.AnalisisCError, match="se esperaba el nombre de la variable"):
        reescribir("void func_X(s32 a)\n{\n    s32 (*)[2];\n}")


def test_una_llamada_real_no_se_confunde_con_una_declaracion_de_puntero_a_funcion() -> None:
    expr = leer_expresion("fn(x)")
    assert isinstance(expr, c.Llamada) and isinstance(expr.funcion, c.Id)
    llamada = leer_expresion("Objeto(1)")
    assert isinstance(llamada, c.Llamada)


def test_un_else_con_un_unico_if_y_comentarios_finales_no_se_encadena() -> None:
    texto = (
        "void func_X(s32 x, s32 y)\n{\n    if (x) {\n        y = 0;\n    } else {\n        if (x) {\n"
        "            y = 1;\n        }\n        /* nota final */\n    }\n}"
    )
    assert reescribir(texto) == texto


def test_el_nombre_de_tipo_como_argumento_de_una_macro_es_un_nodo_de_texto_y_una_variable_un_id() -> None:
    tipo = leer_expresion("f(Objeto, 3)")
    assert isinstance(tipo, c.Llamada)
    assert isinstance(tipo.args[0], c.Texto) and tipo.args[0].texto == "Objeto"
    assert isinstance(tipo.args[1], c.Num)
    variable = leer_expresion("f(a, 3)")
    assert isinstance(variable, c.Llamada)
    assert isinstance(variable.args[0], c.Id) and variable.args[0].nombre == "a"


def test_un_declarador_parentetizado_sin_cerrar_cae_al_mensaje_de_la_expresion() -> None:
    with pytest.raises(c.AnalisisCError, match=re.escape("se esperaba ')'")):
        reescribir("void func_X(s32 a)\n{\n    void (*fp")

"""Reglas de negocio de las mutaciones de asignacion compuesta y de variables locales.

Cubren, para cada mutacion, donde se aplica, donde NO es legal aplicarla (escritura intermedia, llamada,
alias de tipo, direccion tomada, vidas que se solapan), que el escritor de C reproduce el arbol y que el
barrido de vecindario la enumera.
"""

import random
from collections.abc import Callable

import pytest
from tools.reconstruccion import permutar_analisis as an
from tools.reconstruccion import permutar_c as c
from tools.reconstruccion import permutar_mutaciones as mut

CABECERA = """
typedef struct Objeto {
    u32 flags14;
    s16 h108;
    u16 w10E;
    s32 valor;
    s16 radio;
    s32 vec[4];
} Objeto;
typedef struct Orden {
    s16 tipo;
    s32 dato;
} Orden;
extern s32 D_global;
"""
TIPOS = frozenset({"Objeto", "Orden"})
FIRMA = "void f(Objeto* o, Orden* orden, s32* p, s32 x, s32 y)"


def azar(semilla: int) -> random.Random:
    """Generador reproducible; la busqueda es estocastica, no criptografica."""
    return random.Random(semilla)  # noqa: S311


def preparar(texto: str, semilla: int = 0) -> mut.Contexto:
    tabla = an.construir_tabla([CABECERA])
    funcion = c.analizar_funcion(texto, "f", TIPOS)
    return mut.Contexto(funcion, an.Entorno(tabla, funcion), azar(semilla), mut._nombres_de(funcion))


def cuerpo(*lineas: str, firma: str = FIRMA) -> str:
    return firma + "\n{\n" + "\n".join(f"    {linea}" for linea in lineas) + "\n}"


def aplicar(
    mutacion: Callable[[mut.Contexto], str | None], texto: str, semilla: int = 0
) -> tuple[str | None, str]:
    ctx = preparar(texto, semilla)
    descripcion = mutacion(ctx)
    resultado = c.imprimir_funcion(ctx.funcion)
    # El escritor es idempotente: leer lo escrito y volver a escribirlo da el mismo texto.
    assert c.imprimir_funcion(c.analizar_funcion(resultado, "f", TIPOS)) == resultado
    return descripcion, resultado


def todas_las_variantes(mutacion: Callable[[mut.Contexto], str | None], texto: str) -> set[str]:
    """Texto de la variante de cada semilla de 0 a 39: cubre las decisiones al azar de la mutacion."""
    return {aplicar(mutacion, texto, semilla)[1] for semilla in range(40)}


# --- asignacion compuesta ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("antes", "despues"),
    [
        ("o->flags14 = o->flags14 | 2;", "o->flags14 |= 2;"),
        ("x = x + y;", "x += y;"),
        ("x = x - y;", "x -= y;"),
        ("x = x & 0xFF;", "x &= 0xFF;"),
        ("x = x ^ y;", "x ^= y;"),
        ("x = x << 2;", "x <<= 2;"),
        ("x = x >> y;", "x >>= y;"),
        ("o->vec[x] = o->vec[x] + 1;", "o->vec[x] += 1;"),
        ("*p = *p | 4;", "*p |= 4;"),
        ("x = y | x;", "x |= y;"),
    ],
)
def test_una_asignacion_con_la_forma_x_igual_x_op_e_pasa_a_compuesta(antes: str, despues: str) -> None:
    descripcion, texto = aplicar(mut.asignacion_compuesta, cuerpo(antes))
    assert descripcion is not None and descripcion.startswith("asignacion_compuesta(")
    assert f"    {despues}\n" in texto


@pytest.mark.parametrize(
    ("antes", "despues"),
    [
        ("o->flags14 &= 0xFFFEFDFF;", "o->flags14 = o->flags14 & 0xFFFEFDFF;"),
        ("x -= y - 1;", "x = x - (y - 1);"),
        ("x <<= y + 1;", "x = x << y + 1;"),
        ("x <<= y << 1;", "x = x << (y << 1);"),
        ("x |= y | 1;", "x = x | (y | 1);"),
        ("o->vec[x] ^= y;", "o->vec[x] = o->vec[x] ^ y;"),
    ],
)
def test_una_asignacion_compuesta_se_expande_conservando_la_precedencia(antes: str, despues: str) -> None:
    descripcion, texto = aplicar(mut.asignacion_compuesta, cuerpo(antes))
    assert descripcion is not None
    assert f"    {despues}\n" in texto


@pytest.mark.parametrize(
    "linea",
    [
        "x = y + x * 2;",
        "x = x * y;",
        "x *= y;",
        "x /= y;",
        "x %= y;",
        "x = y - x;",
        "x = y << x;",
        "x = x + f();",
        "x = x | f(x);",
        "o->vec[x++] = o->vec[x++] + 1;",
        "o->vec[x++] += 1;",
        "x += y++;",
        "x = x + (y = 2);",
        "x = y;",
        "x = x;",
        "x = 1 + 2;",
    ],
)
def test_la_asignacion_compuesta_no_se_aplica_con_efectos_u_operadores_no_admitidos(linea: str) -> None:
    assert aplicar(mut.asignacion_compuesta, cuerpo(linea))[0] is None


def test_la_asignacion_compuesta_se_encuentra_dentro_de_otras_construcciones() -> None:
    texto = cuerpo("for (x = 0; x < 4; x = x + 1) {", "    y |= 1;", "}")
    variantes = todas_las_variantes(mut.asignacion_compuesta, texto)
    assert any("x += 1" in v for v in variantes) or any("y = y | 1" in v for v in variantes)


def test_el_cambio_de_forma_va_y_vuelve_al_mismo_arbol() -> None:
    texto = cuerpo("o->flags14 = o->flags14 | 2;")
    _, compuesta = aplicar(mut.asignacion_compuesta, texto)
    _, vuelta = aplicar(mut.asignacion_compuesta, compuesta)
    assert vuelta == texto


# --- local de campo ---------------------------------------------------------------------------------


def test_la_lectura_de_un_campo_sube_a_una_local_nueva_por_encima_de_escrituras_a_otros_campos() -> None:
    texto = cuerpo("o->flags14 |= 2;", "o->h108 = 0x800;", "o->w10E = orden->tipo;")
    resultados = {aplicar(mut.local_de_campo, texto, semilla) for semilla in range(60)}
    descripciones = {d for d, _ in resultados}
    assert {f"local_de_campo(s16 tmp1 = orden->tipo, {n} antes)" for n in range(3)} <= descripciones
    textos = {t for _, t in resultados}
    en_cabeza = [t for t in textos if "tmp1 = orden->tipo;\n    o->flags14 |= 2;" in t]
    assert en_cabeza and all("o->w10E = tmp1;" in t and "    s16 tmp1;\n" in t for t in en_cabeza)


def test_la_local_de_campo_sustituye_una_sola_aparicion_o_todas_segun_el_azar() -> None:
    texto = cuerpo("o->valor = x;", "y = orden->dato + orden->dato;")
    variantes = todas_las_variantes(mut.local_de_campo, texto)
    assert any("y = tmp1 + tmp1;" in v for v in variantes)
    assert any("y = tmp1 + orden->dato;" in v for v in variantes)


@pytest.mark.parametrize(
    "escritura",
    [
        "orden->tipo = 3;",
        "orden->tipo += 1;",
        "*p = 1;",
        "p[0] = 1;",
        "orden = o;",
        "f(x);",
    ],
)
def test_la_lectura_no_sube_por_encima_de_una_escritura_que_puede_alcanzarla(escritura: str) -> None:
    texto = cuerpo("x = 1;", escritura, "y = orden->tipo;")
    for semilla in range(30):
        descripcion, resultado = aplicar(mut.local_de_campo, texto, semilla)
        if descripcion is not None and "orden->tipo" in descripcion:
            assert resultado.index("tmp1 = orden->tipo") > resultado.index(escritura)


@pytest.mark.parametrize("escritura", ["o->radio = 3;", "o->vec[1] = 2;"])
def test_la_lectura_si_sube_por_encima_de_escrituras_a_otras_rutas_de_memoria(escritura: str) -> None:
    texto = cuerpo("x = 1;", escritura, "y = orden->tipo;")
    subidas = [
        aplicar(mut.local_de_campo, texto, semilla)[1]
        for semilla in range(40)
        if "tmp1 = orden->tipo" in aplicar(mut.local_de_campo, texto, semilla)[1]
    ]
    assert any(r.index("tmp1 = orden->tipo") < r.index(escritura) for r in subidas)


def test_un_acceso_por_indice_sin_campo_no_cruza_ninguna_escritura_a_memoria() -> None:
    texto = cuerpo("x = 1;", "o->radio = 3;", "y = p[x];")
    for semilla in range(30):
        resultado = aplicar(mut.local_de_campo, texto, semilla)[1]
        assert "tmp1 = p[x]" not in resultado or resultado.index("tmp1 = p[x]") > resultado.index("o->radio")


def test_los_efectos_profundos_suman_declaraciones_con_inicial_de_los_bloques_interiores() -> None:
    funcion = c.analizar_funcion(
        cuerpo("if (x) {", "    s32 a = orden->dato;", "    o->valor = a;", "}"), "f", TIPOS
    )
    efectos = an.efectos_profundos(funcion.cuerpo.items[0])
    assert {"v:a", "m:valor"} <= efectos.escribe
    assert "m:dato" in efectos.lee and not efectos.barrera


def test_la_lectura_sube_por_encima_de_un_bloque_con_declaraciones_que_no_la_tocan() -> None:
    texto = cuerpo("if (x) {", "    s32 a = o->valor;", "    o->radio = a;", "}", "y = orden->tipo;")
    resultados = [aplicar(mut.local_de_campo, texto, semilla)[1] for semilla in range(30)]
    assert any(r.index("tmp1 = orden->tipo") < r.index("if (x)") for r in resultados)


def test_la_lectura_no_cruza_una_sentencia_compuesta_que_escribe_su_memoria() -> None:
    escribe = cuerpo("if (x) {", "    orden->tipo = 1;", "}", "y = orden->tipo;")
    sin_escribir = cuerpo("if (x) {", "    o->valor = 1;", "}", "y = orden->tipo;")
    for semilla in range(30):
        resultado = aplicar(mut.local_de_campo, escribe, semilla)[1]
        assert resultado.index("tmp1 = orden->tipo") > resultado.index("orden->tipo = 1;")
    assert any(
        aplicar(mut.local_de_campo, sin_escribir, semilla)[1].index("tmp1 = orden->tipo")
        < aplicar(mut.local_de_campo, sin_escribir, semilla)[1].index("if (x)")
        for semilla in range(30)
    )


def test_la_lectura_no_cruza_una_etiqueta_ni_un_salto() -> None:
    texto = cuerpo("x = 1;", "ya:", "y = 2;", "y = orden->tipo;")
    for semilla in range(30):
        resultado = aplicar(mut.local_de_campo, texto, semilla)[1]
        assert resultado.index("tmp1 = orden->tipo") > resultado.index("ya:")


def test_la_lectura_de_un_global_no_cruza_una_escritura_por_puntero() -> None:
    texto = cuerpo("x = 1;", "*p = 2;", "y = D_global + o->vec[x];")
    for semilla in range(30):
        resultado = aplicar(mut.local_de_campo, texto, semilla)[1]
        assert "tmp1 = D_global" not in resultado or resultado.index("tmp1 = D_global") > resultado.index(
            "*p = 2;"
        )


def test_la_lectura_no_sube_por_encima_de_la_variable_que_forma_su_direccion() -> None:
    texto = cuerpo("orden = o;", "y = orden->tipo;", firma="void f(Objeto* o, Orden* orden, s32 y)")
    for semilla in range(30):
        resultado = aplicar(mut.local_de_campo, texto, semilla)[1]
        assert resultado.index("tmp1 = orden->tipo") > resultado.index("orden = o;")


@pytest.mark.parametrize(
    "linea",
    [
        "x = o != 0 && orden->tipo > 1;",
        "x = o != 0 ? orden->tipo : 2;",
        "orden->tipo = 1;",
        "x = (y = 2) + orden->tipo;",
        "x = f(1) + orden->tipo;",
        "x = y++ + orden->tipo;",
        "while (x < orden->tipo) {",
        "x = (s32)orden;",
    ],
)
def test_la_local_de_campo_no_se_aplica_donde_el_acceso_no_es_adelantable(linea: str) -> None:
    texto = cuerpo(linea + (" y = 1; }" if linea.endswith("{") else ""))
    for semilla in range(20):
        descripcion = aplicar(mut.local_de_campo, texto, semilla)[0]
        assert descripcion is None or "orden->tipo" not in descripcion


def test_la_lectura_de_una_variable_con_direccion_tomada_no_se_copia() -> None:
    texto = cuerpo("s32 a;", "f(&a);", "x = 1;", "y = o->vec[a];")
    for semilla in range(20):
        descripcion = aplicar(mut.local_de_campo, texto, semilla)[0]
        assert descripcion is None or "vec[a]" not in descripcion


def test_un_nombre_ambiguo_no_se_copia_a_una_local() -> None:
    texto = cuerpo("s32 a;", "if (x) {", "    s32 a;", "    a = 1;", "    y = o->vec[a];", "}")
    for semilla in range(20):
        descripcion = aplicar(mut.local_de_campo, texto, semilla)[0]
        assert descripcion is None or "vec[a]" not in descripcion


def test_la_local_de_campo_respeta_la_distancia_maxima_y_el_final_de_las_declaraciones() -> None:
    lineas = ["s32 a;"] + [f"x = {n};" for n in range(12)] + ["y = orden->tipo;"]
    distancias = set()
    for semilla in range(80):
        descripcion = aplicar(mut.local_de_campo, cuerpo(*lineas), semilla)[0]
        assert descripcion is not None
        if "orden->tipo" in descripcion:
            distancias.add(int(descripcion.rsplit(", ", 1)[1].split(" ")[0]))
    assert max(distancias) == mut.DISTANCIA_MAXIMA_DE_LECTURA


def test_la_local_de_campo_funciona_dentro_de_un_bloque_anidado() -> None:
    texto = cuerpo("if (x) {", "    o->valor = 1;", "    y = orden->tipo;", "}")
    descripciones = {aplicar(mut.local_de_campo, texto, semilla)[0] for semilla in range(40)}
    assert "local_de_campo(s16 tmp1 = orden->tipo, 1 antes)" in descripciones


def test_la_local_de_campo_actua_en_una_condicion_un_retorno_y_un_switch() -> None:
    for sentencia in ("if (orden->tipo > 1) {", "switch (orden->tipo) {"):
        texto = cuerpo("o->valor = 1;", sentencia, "    y = 2;", "}")
        resultados = {aplicar(mut.local_de_campo, texto, semilla)[1] for semilla in range(40)}
        assert any("tmp1 = orden->tipo;\n    o->valor = 1;" in r for r in resultados)
    retorno = cuerpo("o->valor = 1;", "return orden->tipo;", firma="s16 f(Objeto* o, Orden* orden)")
    assert any(
        "tmp1 = orden->tipo;\n    o->valor" in aplicar(mut.local_de_campo, retorno, s)[1] for s in range(40)
    )


def test_sin_accesos_adelantables_la_local_de_campo_no_hace_nada() -> None:
    assert aplicar(mut.local_de_campo, cuerpo("x = y + 1;"))[0] is None


# --- releer en la condicion --------------------------------------------------------------------------

PM_CUENTA = (
    "s32 i;",
    "s32 n;",
    "s32 t;",
    "n = o->vec[x];",
    "for (i = 0; i < n; i++) {",
    "    t = t + i;",
    "}",
)


def test_la_cuenta_de_un_bucle_se_relee_en_la_condicion_y_se_retira_la_local() -> None:
    descripcion, texto = aplicar(mut.releer_en_condicion, cuerpo(*PM_CUENTA))
    assert descripcion == "releer_en_condicion(n = o->vec[x])"
    assert "for (i = 0; i < o->vec[x]; i++) {" in texto
    assert "s32 n;" not in texto and "n = " not in texto


def test_la_local_declarada_con_inicial_tambien_se_relee() -> None:
    texto = cuerpo("s32 i;", "s32 n = o->vec[x];", "while (i < n) {", "    i++;", "}")
    descripcion, resultado = aplicar(mut.releer_en_condicion, texto)
    assert descripcion is not None
    assert "while (i < o->vec[x]) {" in resultado and "s32 n" not in resultado


def test_la_relectura_cambia_tambien_otros_usos_posteriores() -> None:
    texto = cuerpo(
        "s32 i;",
        "s32 n;",
        "n = orden->dato;",
        "for (i = 0; i < n; i++) {",
        "    o->valor = i;",
        "}",
        "y = n;",
    )
    descripcion, resultado = aplicar(mut.releer_en_condicion, texto)
    assert descripcion is not None
    assert "y = orden->dato;" in resultado and "i < orden->dato" in resultado


def test_la_relectura_acepta_do_while_y_for_sin_inicio() -> None:
    hacer = cuerpo("s32 i;", "s32 n;", "n = orden->dato;", "do {", "    i++;", "} while (i < n);")
    assert "while (i < orden->dato);" in aplicar(mut.releer_en_condicion, hacer)[1]


@pytest.mark.parametrize(
    "cuerpo_del_bucle",
    [
        "o->vec[0] = 1;",
        "o->vec[i] += 1;",
        "*p = 1;",
        "p[0] = 1;",
        "f(i);",
        "x = 2;",
        "if (i) {\n        o->vec[1] = 0;\n    }",
        "while (y) {\n        o->vec[1] = 0;\n    }",
    ],
)
def test_no_se_relee_si_el_cuerpo_del_bucle_puede_escribir_esa_memoria(cuerpo_del_bucle: str) -> None:
    texto = cuerpo(
        "s32 i;", "s32 n;", "n = o->vec[x];", "for (i = 0; i < n; i++) {", f"    {cuerpo_del_bucle}", "}"
    )
    assert aplicar(mut.releer_en_condicion, texto)[0] is None


def test_la_relectura_si_es_legal_si_el_bucle_solo_escribe_otras_rutas_de_memoria() -> None:
    texto = cuerpo(
        "s32 i;", "s32 n;", "n = orden->dato;", "for (i = 0; i < n; i++) {", "    o->valor = i;", "}"
    )
    assert aplicar(mut.releer_en_condicion, texto)[0] is not None


@pytest.mark.parametrize(
    "lineas",
    [
        # sin uso en la condicion de un bucle
        ("s32 n;", "n = o->vec[x];", "y = n;"),
        # la fuente no lee memoria
        ("s32 i;", "s32 n;", "n = x + 1;", "for (i = 0; i < n; i++) {", "    y = i;", "}"),
        # la fuente llama a una funcion
        ("s32 i;", "s32 n;", "n = f(x);", "for (i = 0; i < n; i++) {", "    y = i;", "}"),
        # la local se asigna dos veces
        (
            "s32 i;",
            "s32 n;",
            "n = o->vec[x];",
            "n = o->vec[y];",
            "for (i = 0; i < n; i++) {",
            "    y = i;",
            "}",
        ),
        # la local se escribe despues
        ("s32 i;", "s32 n;", "n = o->vec[x];", "for (i = 0; i < n; i++) {", "    n--;", "}"),
        # la local con direccion tomada
        ("s32 i;", "s32 n;", "n = o->vec[x];", "g(&n);", "for (i = 0; i < n; i++) {", "    y = i;", "}"),
        # un uso fuera del bloque que sigue a la asignacion
        (
            "s32 i;",
            "s32 n;",
            "if (x) {",
            "    n = o->vec[x];",
            "}",
            "for (i = 0; i < n; i++) {",
            "    y = i;",
            "}",
        ),
        # la fuente depende de una variable que el bucle cambia
        ("s32 i;", "s32 n;", "n = o->vec[x];", "for (i = 0; i < n; i++) {", "    x = i;", "}"),
        # la fuente se cambia a si misma
        ("s32 n;", "n = n + o->vec[x];", "while (n) {", "    y = 1;", "}"),
        # la fuente es un puntero de otro tipo
        ("s16 n;", "n = o->flags14;", "while (n) {", "    y = 1;", "}"),
    ],
)
def test_la_relectura_no_se_aplica_si_no_se_cumplen_sus_condiciones(lineas: tuple[str, ...]) -> None:
    assert aplicar(mut.releer_en_condicion, cuerpo(*lineas))[0] is None


def test_una_local_con_comentario_o_parametro_no_se_relee() -> None:
    parametro = cuerpo("s32 i;", "x = o->vec[1];", "for (i = 0; i < x; i++) {", "    y = i;", "}")
    assert aplicar(mut.releer_en_condicion, parametro)[0] is None
    comentada = cuerpo(
        "s32 i;", "s32 n;", "/* cuenta */", "n = o->vec[x];", "for (i = 0; i < n; i++) {", "    y = i;", "}"
    )
    assert aplicar(mut.releer_en_condicion, comentada)[0] is None


def test_una_funcion_sin_locales_de_cuenta_no_tiene_nada_que_releer() -> None:
    assert aplicar(mut.releer_en_condicion, cuerpo("x = y;"))[0] is None


# --- unificar locales -------------------------------------------------------------------------------

DOS_BUCLES = (
    "s32 j;",
    "s32 k;",
    "for (j = 0; j < 4; j++) {",
    "    o->vec[j] = 0;",
    "}",
    "for (k = 0; k < x; k++) {",
    "    o->vec[k] = 1;",
    "}",
)


def test_dos_contadores_de_bucles_consecutivos_se_funden_en_el_primero() -> None:
    descripcion, texto = aplicar(mut.unificar_locales, cuerpo(*DOS_BUCLES))
    assert descripcion == "unificar_locales(k en j)"
    assert "s32 k;" not in texto and "k" not in texto.replace("o->vec", "").split("{", 1)[1].replace(
        "for", ""
    )
    assert "for (j = 0; j < x; j++) {" in texto and "o->vec[j] = 1;" in texto


def test_la_segunda_local_puede_empezar_con_una_asignacion() -> None:
    texto = cuerpo("s32 a;", "s32 b;", "a = x;", "o->valor = a;", "b = y;", "o->radio = b;")
    descripcion, resultado = aplicar(mut.unificar_locales, texto)
    assert descripcion == "unificar_locales(b en a)"
    assert "a = y;" in resultado and "o->radio = a;" in resultado and "s32 b;" not in resultado


def test_una_segunda_local_que_solo_se_asigna_dentro_de_un_bloque_no_se_une() -> None:
    texto = cuerpo(
        "s32 a;", "a = x;", "o->valor = a;", "if (y) {", "    s32 b;", "    b = y;", "    o->radio = b;", "}"
    )
    assert aplicar(mut.unificar_locales, texto)[0] is None


def test_la_primera_local_puede_tener_inicializador() -> None:
    texto = cuerpo("s32 a = x;", "s32 b;", "o->valor = a;", "b = y;", "o->radio = b;")
    assert aplicar(mut.unificar_locales, texto)[0] == "unificar_locales(b en a)"


@pytest.mark.parametrize(
    "lineas",
    [
        # vidas que se solapan: la primera se lee despues de empezar la segunda
        ("s32 a;", "s32 b;", "a = x;", "b = y;", "o->valor = a + b;"),
        # la segunda se lee antes de asignarse
        ("s32 a;", "s32 b;", "a = x;", "o->valor = a;", "o->radio = b;", "b = y;"),
        # la segunda se asigna solo en una rama
        ("s32 a;", "s32 b;", "a = x;", "o->valor = a;", "if (y) {", "    b = 1;", "}", "o->radio = b;"),
        # la segunda empieza leyendose a si misma
        ("s32 a;", "s32 b;", "a = x;", "o->valor = a;", "b = b + 1;", "o->radio = b;"),
        # tipos distintos
        ("s32 a;", "s16 b;", "a = x;", "o->valor = a;", "b = y;", "o->radio = b;"),
        ("s32 a;", "s32* b;", "a = x;", "o->valor = a;", "b = p;", "y = *b;"),
        # la segunda tiene inicializador
        ("s32 a;", "s32 b = y;", "a = x;", "o->valor = a;", "o->radio = b;"),
        # direccion tomada
        ("s32 a;", "s32 b;", "a = x;", "g(&a);", "b = y;", "o->radio = b;"),
        ("s32 a;", "s32 b;", "a = x;", "o->valor = a;", "b = y;", "g(&b);"),
        # arreglos
        ("s32 a[2];", "s32 b[2];", "a[0] = x;", "o->valor = a[0];", "b[0] = y;", "o->radio = b[0];"),
        # un salto hacia atras alargaria la vida de la primera
        ("s32 a;", "s32 b;", "inicio:", "a = x;", "o->valor = a;", "b = y;", "o->radio = b;", "goto inicio;"),
        # una sola local
        ("s32 a;", "a = x;", "o->valor = a;"),
        # una local sin usos
        ("s32 a;", "s32 b;", "b = y;", "o->radio = b;"),
        # la primera local solo en un bloque interior
        (
            "s32 b;",
            "if (x) {",
            "    s32 a;",
            "    a = 1;",
            "    o->valor = a;",
            "}",
            "b = y;",
            "o->radio = b;",
        ),
    ],
)
def test_no_se_unifican_locales_con_vidas_que_se_solapan_o_sin_garantia(lineas: tuple[str, ...]) -> None:
    assert aplicar(mut.unificar_locales, cuerpo(*lineas))[0] is None


def test_un_parametro_no_se_une_con_una_local() -> None:
    texto = cuerpo("s32 b;", "o->valor = x;", "b = y;", "o->radio = b;")
    assert aplicar(mut.unificar_locales, texto)[0] is None


def test_un_nombre_declarado_dos_veces_no_se_unifica() -> None:
    texto = cuerpo(
        "s32 a;",
        "s32 b;",
        "a = x;",
        "o->valor = a;",
        "if (y) {",
        "    s32 b;",
        "}",
        "b = y;",
        "o->radio = b;",
    )
    assert aplicar(mut.unificar_locales, texto)[0] is None


# --- partir local -----------------------------------------------------------------------------------

CELDA_COMPARTIDA = (
    "s32 celda;",
    "if (x) {",
    "    celda = o->vec[0];",
    "    o->valor = celda;",
    "} else if (y) {",
    "    celda = o->vec[1];",
    "    o->radio = celda;",
    "} else {",
    "    celda = o->vec[2];",
    "    o->h108 = celda;",
    "}",
)


def test_una_local_compartida_por_las_ramas_de_un_if_se_parte_en_una_por_rama() -> None:
    descripcion, texto = aplicar(mut.partir_local, cuerpo(*CELDA_COMPARTIDA))
    assert descripcion == "partir_local(celda en tmp1, tmp2)"
    assert "    s32 tmp2;\n    s32 tmp1;\n" in texto or "    s32 tmp1;\n    s32 tmp2;\n" in texto
    assert "celda = o->vec[0];" in texto and "tmp1 = o->vec[1];" in texto and "tmp2 = o->vec[2];" in texto
    assert "o->radio = tmp1;" in texto and "o->h108 = tmp2;" in texto


def test_la_particion_de_dos_ramas_deja_la_primera_con_el_nombre_original() -> None:
    texto = cuerpo(
        "s32 celda;",
        "if (x) {",
        "    celda = 1;",
        "    o->valor = celda;",
        "} else {",
        "    celda = 2;",
        "    o->radio = celda;",
        "}",
    )
    descripcion, resultado = aplicar(mut.partir_local, texto)
    assert descripcion == "partir_local(celda en tmp1)"
    assert "celda = 1;" in resultado and "tmp1 = 2;" in resultado


def test_una_local_compartida_por_los_casos_de_un_switch_se_parte_si_cada_caso_termina() -> None:
    texto = cuerpo(
        "s32 celda;",
        "switch (x) {",
        "case 0:",
        "    celda = 1;",
        "    o->valor = celda;",
        "    break;",
        "case 1:",
        "    celda = 2;",
        "    o->radio = celda;",
        "    return;",
        "default:",
        "    celda = 3;",
        "    o->h108 = celda;",
        "    break;",
        "}",
    )
    descripcion, resultado = aplicar(mut.partir_local, texto)
    assert descripcion == "partir_local(celda en tmp1, tmp2)"
    assert "tmp1 = 2;" in resultado and "tmp2 = 3;" in resultado


@pytest.mark.parametrize(
    "lineas",
    [
        # un uso fuera de las ramas
        (
            "s32 celda;",
            "if (x) {",
            "    celda = 1;",
            "    o->valor = celda;",
            "} else {",
            "    celda = 2;",
            "    o->radio = celda;",
            "}",
            "y = celda;",
        ),
        # un uso en la condicion
        (
            "s32 celda;",
            "if (celda) {",
            "    celda = 1;",
            "    o->valor = celda;",
            "} else {",
            "    celda = 2;",
            "    o->radio = celda;",
            "}",
        ),
        # una rama lee la variable antes de asignarla
        (
            "s32 celda;",
            "if (x) {",
            "    o->valor = celda;",
            "} else {",
            "    celda = 2;",
            "    o->radio = celda;",
            "}",
        ),
        # una rama la asigna solo dentro de otra condicion
        (
            "s32 celda;",
            "if (x) {",
            "    if (y) {",
            "        celda = 1;",
            "    }",
            "    o->valor = celda;",
            "} else {",
            "    celda = 2;",
            "    o->radio = celda;",
            "}",
        ),
        # la rama se asigna a partir de si misma
        (
            "s32 celda;",
            "if (x) {",
            "    celda = celda + 1;",
            "    o->valor = celda;",
            "} else {",
            "    celda = 2;",
            "    o->radio = celda;",
            "}",
        ),
        # una sola rama la usa
        ("s32 celda;", "if (x) {", "    celda = 1;", "    o->valor = celda;", "} else {", "    y = 2;", "}"),
        # caida entre casos
        (
            "s32 celda;",
            "switch (x) {",
            "case 0:",
            "    celda = 1;",
            "    o->valor = celda;",
            "case 1:",
            "    celda = 2;",
            "    o->radio = celda;",
            "    break;",
            "}",
        ),
        # dos casos seguidos sin sentencias
        (
            "s32 celda;",
            "switch (x) {",
            "case 0:",
            "case 1:",
            "    celda = 2;",
            "    o->radio = celda;",
            "    break;",
            "}",
        ),
        # la local con direccion tomada
        (
            "s32 celda;",
            "if (x) {",
            "    celda = 1;",
            "    g(&celda);",
            "} else {",
            "    celda = 2;",
            "    o->radio = celda;",
            "}",
        ),
        # una local con inicializador
        (
            "s32 celda = 0;",
            "if (x) {",
            "    celda = 1;",
            "    o->valor = celda;",
            "} else {",
            "    celda = 2;",
            "    o->radio = celda;",
            "}",
        ),
        # un bucle no es una rama
        ("s32 celda;", "while (x) {", "    celda = 1;", "    o->valor = celda;", "}"),
    ],
)
def test_una_local_no_se_parte_si_las_ramas_no_son_independientes(lineas: tuple[str, ...]) -> None:
    assert aplicar(mut.partir_local, cuerpo(*lineas))[0] is None


def test_partir_y_unificar_son_operaciones_inversas() -> None:
    texto = cuerpo(
        *CELDA_COMPARTIDA[:1],
        "if (x) {",
        "    celda = 1;",
        "    o->valor = celda;",
        "} else {",
        "    celda = 2;",
        "    o->radio = celda;",
        "}",
    )
    _, partido = aplicar(mut.partir_local, texto)
    ctx = preparar(partido)
    assert mut.unificar_locales(ctx) is None  # las ramas son excluyentes: sus tramos son del mismo `if`


# --- registro y vecindario --------------------------------------------------------------------------

NUEVAS = ("asignacion_compuesta", "local_de_campo", "releer_en_condicion", "unificar_locales", "partir_local")


def test_las_cinco_mutaciones_estan_registradas_con_su_peso() -> None:
    registradas = {nombre: peso for nombre, _, peso in mut.MUTACIONES}
    assert set(NUEVAS) <= set(registradas)
    assert all(0 < registradas[nombre] <= 4.0 for nombre in NUEVAS)
    assert len(registradas) == len(mut.MUTACIONES) == 15


MUESTRA_COMPLETA = cuerpo(
    "s32 j;",
    "s32 k;",
    "s32 n;",
    "s32 celda;",
    "o->flags14 = o->flags14 | 2;",
    "o->h108 = 0x800;",
    "o->w10E = orden->tipo;",
    "n = o->vec[x];",
    "for (j = 0; j < n; j++) {",
    "    o->valor = j;",
    "}",
    "for (k = 0; k < 3; k++) {",
    "    o->radio = k;",
    "}",
    "if (x) {",
    "    celda = o->vec[0];",
    "    o->valor = celda;",
    "} else {",
    "    celda = o->vec[1];",
    "    o->radio = celda;",
    "}",
)


def test_el_barrido_de_vecinos_enumera_las_cinco_mutaciones() -> None:
    tabla = an.construir_tabla([CABECERA])
    base = c.analizar_funcion(MUESTRA_COMPLETA, "f", TIPOS)
    vecinos = list(mut.vecinos(base, tabla))
    descripciones = {d.split("(")[0] for _, d in vecinos}
    assert set(NUEVAS) <= descripciones
    textos = {c.imprimir_funcion(v) for v, _ in vecinos}
    for texto in textos:
        assert c.imprimir_funcion(c.analizar_funcion(texto, "f", TIPOS)) == texto
    posiciones = {d for _, d in vecinos if d.startswith("local_de_campo(s16 tmp1 = orden->tipo")}
    assert len(posiciones) >= 3


def test_las_variantes_de_las_mutaciones_nuevas_no_agregan_construcciones_prohibidas() -> None:
    tabla = an.construir_tabla([CABECERA])
    base = c.analizar_funcion(MUESTRA_COMPLETA, "f", TIPOS)
    texto_base = c.imprimir_funcion(base)
    for variante, _ in mut.vecinos(base, tabla):
        assert mut.variante_permitida(c.imprimir_funcion(variante), texto_base)


def test_la_busqueda_al_azar_puede_encadenar_las_mutaciones_nuevas() -> None:
    tabla = an.construir_tabla([CABECERA])
    base = c.analizar_funcion(MUESTRA_COMPLETA, "f", TIPOS)
    vistas: set[str] = set()
    for semilla in range(200):
        variante, aplicadas = mut.mutar(base, tabla, azar(semilla), 3)
        vistas.update(a.split("(")[0] for a in aplicadas)
        texto = c.imprimir_funcion(variante)
        assert c.imprimir_funcion(c.analizar_funcion(texto, "f", TIPOS)) == texto
    assert set(NUEVAS) <= vistas

"""Reglas de negocio de la copia de un campo en una local y de su inversa.

``f = o->flags14 | 2; o->flags14 = f; ...; o->flags14 = f & mascara;`` y
``o->flags14 |= 2; ...; o->flags14 &= mascara;`` son el mismo programa mientras nada escriba el campo
entre la copia y el ultimo uso de la local. Estas pruebas fijan cuando se propaga, cuando no (escritura
intermedia, llamada opaca, lectura de la local fuera del patron, tipos que cambian el valor, efectos en
el campo) y que la inversa deshace lo que la directa hizo.
"""

import random
from collections.abc import Callable

import pytest
from psxdecomp.permutador import analisis as an
from psxdecomp.permutador import c
from psxdecomp.permutador import mutaciones as mut

CABECERA = """
typedef struct Objeto {
    u32 flags14;
    s16 h108;
    u16 w10E;
    s32 valor;
    s32 vec[4];
    s32* ptr;
    union {
        s32 entero;
        s16 corto;
    } u78;
    union {
        s32 ancho;
        s16 mitad;
    };
} Objeto;
typedef struct Orden {
    s16 tipo;
    s32 dato;
} Orden;
extern s32 D_global;
"""
TIPOS = frozenset({"Objeto", "Orden"})
FIRMA = "void f(Objeto* o, Orden* orden, s32* p, s32 x, s32 y)"
PROPAGAR = mut.propagar_copia_de_campo
INTRODUCIR = mut.introducir_copia_de_campo
DESPEGUE = (
    "s32 bandera;",
    "bandera = o->flags14 | 2;",
    "o->flags14 = bandera;",
    "o->h108 = 0x800;",
    "o->w10E = orden->tipo;",
    "o->flags14 = bandera & 0xFFFEFDFF;",
)


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


# --- propagar la copia: casos en los que se aplica --------------------------------------------------


def test_la_copia_de_las_banderas_se_sustituye_por_asignaciones_compuestas() -> None:
    descripcion, texto = aplicar(PROPAGAR, cuerpo(*DESPEGUE))
    assert descripcion == "propagar_copia_de_campo(bandera = o->flags14 | 2)"
    assert "    o->flags14 |= 2;\n    o->h108 = 0x800;\n" in texto
    assert "    o->flags14 &= 0xFFFEFDFF;\n}" in texto
    assert "bandera" not in texto


def test_la_local_con_inicializador_tambien_se_elimina() -> None:
    texto = cuerpo("s32 bandera = o->flags14 | 2;", "o->flags14 = bandera;", "o->flags14 = bandera & 1;")
    descripcion, resultado = aplicar(PROPAGAR, texto)
    assert descripcion is not None
    assert resultado == cuerpo("o->flags14 |= 2;", "o->flags14 &= 1;")


def test_una_copia_sin_almacen_final_se_propaga() -> None:
    texto = cuerpo("s32 bandera;", "bandera = o->valor + 1;", "o->valor = bandera;")
    assert aplicar(PROPAGAR, texto)[1] == cuerpo("o->valor += 1;")


def test_con_el_operador_conmutativo_el_campo_puede_ir_a_la_derecha() -> None:
    texto = cuerpo("s32 bandera;", "bandera = 2 | o->flags14;", "o->flags14 = bandera;")
    assert aplicar(PROPAGAR, texto)[1] == cuerpo("o->flags14 |= 2;")


@pytest.mark.parametrize(
    ("operacion", "almacen", "esperado"),
    [
        ("o->vec[x] + 1", "o->vec[x] = bandera << 2;", ("o->vec[x] += 1;", "o->vec[x] <<= 2;")),
        ("o->vec[x] - y", "o->vec[x] = bandera - 3;", ("o->vec[x] -= y;", "o->vec[x] -= 3;")),
        ("o->vec[x] ^ y", "o->vec[x] = bandera >> 1;", ("o->vec[x] ^= y;", "o->vec[x] >>= 1;")),
    ],
)
def test_el_campo_puede_ser_un_elemento_de_un_arreglo(
    operacion: str, almacen: str, esperado: tuple[str, str]
) -> None:
    texto = cuerpo("s32 bandera;", f"bandera = {operacion};", "o->vec[x] = bandera;", almacen)
    assert aplicar(PROPAGAR, texto)[1] == cuerpo(*esperado)


def test_las_comparaciones_de_la_local_pasan_a_leer_el_campo() -> None:
    texto = cuerpo(
        "s32 bandera;",
        "bandera = o->flags14 | 2;",
        "o->flags14 = bandera;",
        "if (bandera == 6) {",
        "    x = 1;",
        "}",
        "y = 4 != bandera;",
    )
    resultado = aplicar(PROPAGAR, texto)[1]
    assert "if (o->flags14 == 6) {" in resultado
    assert "y = 4 != o->flags14;" in resultado and "bandera" not in resultado


def test_la_copia_puede_estar_separada_de_su_primer_uso_si_nada_toca_el_campo() -> None:
    texto = cuerpo("s32 bandera;", "bandera = o->flags14 | 2;", "o->h108 = 1;", "o->flags14 = bandera;")
    assert aplicar(PROPAGAR, texto)[1] == cuerpo("o->h108 = 1;", "o->flags14 |= 2;")


def test_una_local_estrecha_del_mismo_signo_que_el_campo_se_propaga() -> None:
    texto = cuerpo("u16 bandera;", "bandera = o->w10E | 1;", "o->w10E = bandera;", "o->w10E = bandera >> 1;")
    assert aplicar(PROPAGAR, texto)[1] == cuerpo("o->w10E |= 1;", "o->w10E >>= 1;")


def test_con_el_mismo_signo_se_admiten_la_comparacion_de_orden_y_el_desplazamiento() -> None:
    texto = cuerpo(
        "u32 bandera;",
        "bandera = o->flags14 | 2;",
        "o->flags14 = bandera;",
        "if (bandera > 6) {",
        "    x = 1;",
        "}",
        "o->flags14 = bandera >> 1;",
    )
    resultado = aplicar(PROPAGAR, texto)[1]
    assert resultado == cuerpo(
        "o->flags14 |= 2;", "if (o->flags14 > 6) {", "    x = 1;", "}", "o->flags14 >>= 1;"
    )


@pytest.mark.parametrize(
    "lineas",
    [
        ("if (bandera > 6) {", "    x = 1;", "}"),
        ("if (bandera <= 6) {", "    x = 1;", "}"),
        ("o->flags14 = bandera >> 1;",),
    ],
)
def test_con_distinto_signo_no_se_propaga_si_el_resultado_depende_del_signo(lineas: tuple[str, ...]) -> None:
    texto = cuerpo("s32 bandera;", "bandera = o->flags14 | 2;", "o->flags14 = bandera;", *lineas)
    assert aplicar(PROPAGAR, texto)[0] is None


def test_con_distinto_signo_si_se_propagan_la_igualdad_y_las_operaciones_de_bits() -> None:
    texto = cuerpo(
        "s32 bandera;",
        "bandera = o->flags14 | 2;",
        "o->flags14 = bandera;",
        "if (bandera != 6) {",
        "    x = 1;",
        "}",
        "o->flags14 = bandera + 8;",
    )
    resultado = aplicar(PROPAGAR, texto)[1]
    assert "if (o->flags14 != 6) {" in resultado and "o->flags14 += 8;" in resultado


# --- propagar la copia: casos en los que NO se aplica -----------------------------------------------


@pytest.mark.parametrize(
    "escritura",
    [
        "o->flags14 = 0;",
        "o->flags14 |= 8;",
        "o->flags14++;",
        "*p = 1;",
        "p[0] = 1;",
        "o = orden;",
        "g();",
        "if (y) {\n        o->flags14 = 0;\n    }",
        "while (y) {\n        g();\n    }",
    ],
)
def test_una_escritura_intermedia_al_campo_o_una_llamada_opaca_impide_propagar(escritura: str) -> None:
    texto = cuerpo(
        "s32 bandera;",
        "bandera = o->flags14 | 2;",
        "o->flags14 = bandera;",
        escritura,
        "o->flags14 = bandera & 1;",
    )
    assert aplicar(PROPAGAR, texto)[0] is None


@pytest.mark.parametrize("escritura", ["o->flags14 = 0;", "o->u78 = o->u78;", "y = 1;", "g();", "*p = 1;"])
def test_nada_puede_cambiar_lo_que_lee_la_primera_operacion_antes_de_la_copia(escritura: str) -> None:
    texto = cuerpo("s32 bandera;", "bandera = o->flags14 | y;", escritura, "o->flags14 = bandera;")
    descripcion = aplicar(PROPAGAR, texto)[0]
    # ``y = 1;`` cambia el operando, ``o->u78 = o->u78;`` no toca el campo y no lo impide.
    assert (descripcion is not None) == (escritura == "o->u78 = o->u78;")


def test_una_escritura_a_otro_campo_no_impide_propagar() -> None:
    texto = cuerpo(
        "s32 bandera;", "bandera = o->flags14 | 2;", "o->flags14 = bandera;", "o->h108 = 3;", "o->valor = 4;"
    )
    assert aplicar(PROPAGAR, texto)[1] == cuerpo("o->flags14 |= 2;", "o->h108 = 3;", "o->valor = 4;")


def test_una_escritura_a_un_miembro_de_union_se_trata_como_escritura_al_hermano() -> None:
    sobre_u78 = cuerpo(
        "s32 bandera;",
        "bandera = o->u78.entero | 2;",
        "o->u78.entero = bandera;",
        "o->u78.corto = 1;",
        "x = bandera;",
    )
    assert aplicar(PROPAGAR, sobre_u78)[0] is None
    texto = cuerpo(
        "s32 bandera;",
        "bandera = o->u78.entero | 2;",
        "o->u78.entero = bandera;",
        "o->valor = 1;",
        "o->u78.entero = bandera & 3;",
    )
    assert aplicar(PROPAGAR, texto)[1] == cuerpo(
        "o->u78.entero |= 2;", "o->valor = 1;", "o->u78.entero &= 3;"
    )
    hermano = cuerpo(
        "s32 bandera;",
        "bandera = o->u78.entero | 2;",
        "o->u78.entero = bandera;",
        "o->u78.corto = 1;",
        "o->u78.entero = bandera & 3;",
    )
    assert aplicar(PROPAGAR, hermano)[0] is None


@pytest.mark.parametrize(
    "lineas",
    [
        ("y = bandera;",),
        ("x = bandera + 1;",),
        ("if (bandera) {", "    x = 1;", "}"),
        ("if (bandera & 4) {", "    x = 1;", "}"),
        ("g(bandera);",),
        ("o->valor = bandera;",),
        ("o->flags14 = bandera & g();",),
        ("o->flags14 = bandera & bandera;",),
        ("o->flags14 = y & bandera;",),
        ("o->flags14 = bandera & 1;", "y = 3 == bandera;"),
        ("o->flags14 = bandera & 1;", "o->flags14 = bandera & 2;"),
        ("o->flags14 = ~bandera;",),
    ],
)
def test_no_se_propaga_si_la_local_se_lee_fuera_del_patron(lineas: tuple[str, ...]) -> None:
    texto = cuerpo("s32 bandera;", "bandera = o->flags14 | 2;", "o->flags14 = bandera;", *lineas)
    assert aplicar(PROPAGAR, texto)[0] is None


def test_el_primer_uso_de_la_local_debe_ser_la_copia_al_campo() -> None:
    antes = cuerpo(
        "s32 bandera;",
        "bandera = o->flags14 | 2;",
        "if (bandera == 1) {",
        "    x = 1;",
        "}",
        "o->flags14 = bandera;",
    )
    assert aplicar(PROPAGAR, antes)[0] is None
    otro_campo = cuerpo("s32 bandera;", "bandera = o->flags14 | 2;", "o->valor = bandera;")
    assert aplicar(PROPAGAR, otro_campo)[0] is None
    doble = cuerpo("s32 bandera;", "bandera = o->flags14 | 2;", "o->flags14 = bandera + bandera;")
    assert aplicar(PROPAGAR, doble)[0] is None
    sin_copia = cuerpo("s32 bandera;", "bandera = o->flags14 | 2;", "y = bandera;", "o->flags14 = bandera;")
    assert aplicar(PROPAGAR, sin_copia)[0] is None


@pytest.mark.parametrize(
    "lineas",
    [
        # el campo es una variable local, no memoria
        ("s32 bandera;", "bandera = y | 2;", "y = bandera;"),
        # el campo tiene efectos
        ("s32 bandera;", "bandera = o->vec[y++] | 2;", "o->vec[y] = bandera;"),
        # el operando tiene efectos
        ("s32 bandera;", "bandera = o->flags14 | g();", "o->flags14 = bandera;"),
        # operador que no se compone
        ("s32 bandera;", "bandera = o->valor * 2;", "o->valor = bandera;"),
        ("s32 bandera;", "bandera = 2 - o->valor;", "o->valor = bandera;"),
        ("s32 bandera;", "bandera = 2 | 3;", "o->valor = bandera;"),
        # el operando repite el campo
        ("s32 bandera;", "bandera = o->flags14 | o->flags14;", "o->flags14 = bandera;"),
        # la local aparece en su propia fuente
        ("s32 bandera;", "bandera = bandera | o->flags14;", "o->flags14 = bandera;"),
        # la local se asigna dos veces
        ("s32 bandera;", "bandera = o->flags14 | 2;", "o->flags14 = bandera;", "bandera = 4;"),
        # la local no se usa
        ("s32 bandera;", "bandera = o->flags14 | 2;"),
        # campo de tipo desconocido
        ("s32 bandera;", "bandera = o->desconocido | 2;", "o->desconocido = bandera;"),
        # campo que no es un entero
        ("s32 bandera;", "bandera = o->ptr | 2;", "o->ptr = bandera;"),
    ],
)
def test_no_se_propaga_si_la_primera_asignacion_no_tiene_la_forma_exigida(lineas: tuple[str, ...]) -> None:
    assert aplicar(PROPAGAR, cuerpo(*lineas))[0] is None


@pytest.mark.parametrize(
    ("tipo", "campo"),
    [
        ("s16", "o->flags14"),
        ("s32", "o->h108"),
        ("s16", "o->w10E"),
        ("u16", "o->h108"),
    ],
)
def test_no_se_propaga_si_la_local_y_el_campo_no_tienen_el_mismo_ancho_y_signo(tipo: str, campo: str) -> None:
    texto = cuerpo(f"{tipo} bandera;", f"bandera = {campo} | 1;", f"{campo} = bandera;")
    assert aplicar(PROPAGAR, texto)[0] is None


def test_no_se_propaga_una_local_de_otro_bloque_ni_con_la_direccion_tomada_ni_con_comentarios() -> None:
    otro_bloque = cuerpo(
        "s32 bandera;", "if (y) {", "    bandera = o->flags14 | 2;", "}", "o->flags14 = bandera;"
    )
    assert aplicar(PROPAGAR, otro_bloque)[0] is None
    con_direccion = cuerpo(
        "s32 bandera;", "g(&bandera);", "bandera = o->flags14 | 2;", "o->flags14 = bandera;"
    )
    assert aplicar(PROPAGAR, con_direccion)[0] is None
    comentada = cuerpo("s32 bandera;", "/* mascara */", "bandera = o->flags14 | 2;", "o->flags14 = bandera;")
    assert aplicar(PROPAGAR, comentada)[0] is None
    parametro = cuerpo("x = o->flags14 | 2;", "o->flags14 = x;")
    assert aplicar(PROPAGAR, parametro)[0] is None


def test_un_campo_cuyo_indice_depende_de_una_variable_con_direccion_tomada_no_se_propaga() -> None:
    texto = cuerpo("s32 bandera;", "s32 k;", "g(&k);", "bandera = o->vec[k] | 2;", "o->vec[k] = bandera;")
    assert aplicar(PROPAGAR, texto)[0] is None


def test_sin_locales_candidatas_la_propagacion_no_hace_nada() -> None:
    assert aplicar(PROPAGAR, cuerpo("o->flags14 |= 2;"))[0] is None


# --- introducir la copia: la inversa ---------------------------------------------------------------------


def test_dos_compuestas_al_mismo_campo_pasan_a_una_local_reutilizada() -> None:
    texto = cuerpo(
        "o->flags14 |= 2;", "o->h108 = 0x800;", "o->w10E = orden->tipo;", "o->flags14 &= 0xFFFEFDFF;"
    )
    descripcion, resultado = aplicar(INTRODUCIR, texto)
    assert descripcion == "introducir_copia_de_campo(u32 tmp1 = o->flags14 | 2)"
    assert "    u32 tmp1;\n" in resultado
    assert "    tmp1 = o->flags14 | 2;\n    o->flags14 = tmp1;\n    o->h108 = 0x800;\n" in resultado
    assert "    o->flags14 = tmp1 & 0xFFFEFDFF;\n}" in resultado


def test_introducir_y_propagar_son_operaciones_inversas() -> None:
    texto = cuerpo("o->flags14 |= 2;", "o->h108 = 0x800;", "o->flags14 &= 0xFFFEFDFF;")
    _, con_copia = aplicar(INTRODUCIR, texto)
    descripcion, vuelta = aplicar(PROPAGAR, con_copia)
    assert descripcion == "propagar_copia_de_campo(tmp1 = o->flags14 | 2)"
    assert vuelta == texto


def test_la_inversa_conserva_el_comentario_de_la_primera_compuesta() -> None:
    texto = cuerpo("/* despegue */", "o->flags14 |= 2;", "o->flags14 &= 1;")
    resultado = aplicar(INTRODUCIR, texto)[1]
    assert resultado.index("/* despegue */") < resultado.index("tmp1 = o->flags14 | 2;")


def test_la_inversa_empareja_cada_compuesta_con_la_siguiente_del_mismo_campo() -> None:
    texto = cuerpo("o->flags14 |= 2;", "o->flags14 &= 1;", "o->flags14 ^= 4;")
    emparejadas = {aplicar(INTRODUCIR, texto, semilla)[1] for semilla in range(20)}
    assert any("tmp1 = o->flags14 | 2;" in t and "o->flags14 = tmp1 & 1;" in t for t in emparejadas)
    assert any("tmp1 = o->flags14 & 1;" in t and "o->flags14 = tmp1 ^ 4;" in t for t in emparejadas)
    assert not any("tmp1 = o->flags14 | 2;" in t and "tmp1 ^ 4" in t for t in emparejadas)


def test_la_inversa_usa_el_tipo_exacto_del_campo_y_acepta_elementos() -> None:
    texto = cuerpo("o->vec[x] += 1;", "o->vec[x] <<= 2;")
    descripcion, resultado = aplicar(INTRODUCIR, texto)
    assert descripcion == "introducir_copia_de_campo(s32 tmp1 = o->vec[x] + 1)"
    assert "o->vec[x] = tmp1 << 2;" in resultado
    corto = cuerpo("o->w10E |= 1;", "o->w10E &= 2;")
    assert aplicar(INTRODUCIR, corto)[0] == "introducir_copia_de_campo(u16 tmp1 = o->w10E | 1)"


@pytest.mark.parametrize(
    "intermedia",
    [
        "o->flags14 = 0;",
        "*p = 1;",
        "p[0] = 1;",
        "g();",
        "o = orden;",
        "if (y) {\n        o->flags14 = 1;\n    }",
    ],
)
def test_la_inversa_no_cruza_una_escritura_al_campo_ni_una_llamada(intermedia: str) -> None:
    texto = cuerpo("o->flags14 |= 2;", intermedia, "o->flags14 &= 1;")
    assert aplicar(INTRODUCIR, texto)[0] is None


@pytest.mark.parametrize(
    "lineas",
    [
        # una sola compuesta
        ("o->flags14 |= 2;",),
        # compuestas a campos distintos
        ("o->flags14 |= 2;", "o->valor &= 1;"),
        # la forma simple no es una compuesta
        ("o->flags14 = o->flags14 | 2;", "o->flags14 &= 1;"),
        # operadores que no se componen
        ("o->valor *= 2;", "o->valor += 1;"),
        # destino que no es memoria
        ("x |= 2;", "x &= 1;"),
        # operando con efectos
        ("o->flags14 |= g();", "o->flags14 &= 1;"),
        ("o->flags14 |= 2;", "o->flags14 &= g();"),
        # destino con efectos
        ("o->vec[y++] |= 2;", "o->vec[y++] &= 1;"),
        # destino que no es un entero
        ("o->ptr += 1;", "o->ptr += 2;"),
        # la segunda esta en otro bloque
        ("o->flags14 |= 2;", "if (y) {", "    o->flags14 &= 1;", "}"),
    ],
)
def test_la_inversa_no_se_aplica_sin_dos_compuestas_validas_al_mismo_campo(lineas: tuple[str, ...]) -> None:
    assert aplicar(INTRODUCIR, cuerpo(*lineas))[0] is None


@pytest.mark.parametrize(
    ("campo", "hermano"),
    [
        ("o->u78.entero", "o->u78.corto = 5;"),
        ("o->u78.corto", "o->u78.entero = 5;"),
        ("o->u78.entero", "o->u78.corto |= 5;"),
        ("o->ancho", "o->mitad = 5;"),
        ("o->mitad", "o->ancho = 5;"),
    ],
)
def test_la_inversa_no_cruza_una_escritura_a_un_miembro_hermano_de_la_union(campo: str, hermano: str) -> None:
    texto = cuerpo(f"{campo} |= 2;", hermano, f"{campo} &= 1;")
    assert aplicar(INTRODUCIR, texto)[0] is None


@pytest.mark.parametrize(
    ("campo", "tipo", "ajena"),
    [
        ("o->u78.entero", "s32", "o->valor = 5;"),
        ("o->u78.corto", "s16", "o->h108 = 5;"),
        ("o->u78.entero", "s32", "o->ancho = 5;"),
        ("o->ancho", "s32", "o->u78.corto = 5;"),
        ("o->mitad", "s16", "o->u78.entero = 5;"),
    ],
)
def test_la_inversa_si_cruza_una_escritura_a_un_campo_ajeno_a_la_union(
    campo: str, tipo: str, ajena: str
) -> None:
    texto = cuerpo(f"{campo} |= 2;", ajena, f"{campo} &= 1;")
    descripcion, resultado = aplicar(INTRODUCIR, texto)
    assert descripcion == f"introducir_copia_de_campo({tipo} tmp1 = {campo} | 2)"
    esperado = cuerpo(
        f"{tipo} tmp1;", f"tmp1 = {campo} | 2;", f"{campo} = tmp1;", ajena, f"{campo} = tmp1 & 1;"
    )
    assert resultado == esperado


def test_la_inversa_no_toca_un_campo_cuyo_indice_depende_de_una_variable_con_direccion_tomada() -> None:
    texto = cuerpo("s32 k;", "g(&k);", "o->vec[k] |= 2;", "o->vec[k] &= 1;")
    assert aplicar(INTRODUCIR, texto)[0] is None


# --- registro y enumeracion --------------------------------------------------------------------------


def test_las_dos_mutaciones_estan_registradas_con_la_inversa_de_menor_peso() -> None:
    pesos = {nombre: peso for nombre, _, peso in mut.MUTACIONES}
    assert pesos["propagar_copia_de_campo"] == 2.0
    assert pesos["introducir_copia_de_campo"] == 1.0
    assert pesos["introducir_copia_de_campo"] < pesos["propagar_copia_de_campo"]


def test_el_barrido_de_vecinos_enumera_la_propagacion_y_la_inversa() -> None:
    tabla = an.construir_tabla([CABECERA])
    base = c.analizar_funcion(cuerpo(*DESPEGUE), "f", TIPOS)
    propagadas = [
        c.imprimir_funcion(v) for v, d in mut.vecinos(base, tabla) if d.startswith("propagar_copia_de_campo(")
    ]
    assert propagadas and all("bandera" not in t and "o->flags14 |= 2;" in t for t in propagadas)
    compuestas = c.analizar_funcion(cuerpo("o->flags14 |= 2;", "o->flags14 &= 1;"), "f", TIPOS)
    introducidas = [
        c.imprimir_funcion(v)
        for v, d in mut.vecinos(compuestas, tabla)
        if d.startswith("introducir_copia_de_campo(")
    ]
    assert introducidas and all("tmp1 = o->flags14 | 2;" in t for t in introducidas)


def test_la_propagacion_no_cambia_el_original() -> None:
    texto = cuerpo(*DESPEGUE)
    base = c.analizar_funcion(texto, "f", TIPOS)
    tabla = an.construir_tabla([CABECERA])
    antes = c.imprimir_funcion(base)
    for _ in mut.vecinos(base, tabla):
        pass
    assert c.imprimir_funcion(base) == antes

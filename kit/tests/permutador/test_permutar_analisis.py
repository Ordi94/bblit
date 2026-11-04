import pytest
from psxdecomp.permutador import analisis as an
from psxdecomp.permutador import c

CABECERA = """
typedef struct SVECTOR {
    short vx, vy, vz;
    short pad;
} SVECTOR;

typedef struct VECTOR {
    s32 vx;
    s32 vy;
    s32 vz;
} VECTOR;

typedef struct Objeto {
    u32 flags08;
    s16 radio;
    u8 bytes[4];
    unsigned char marca : 4;
    SVECTOR min;
    struct Objeto* sig10;
    union {
        s32 a;
        s32 b;
    } u78;
    s32 *ptr, valor;
    return_no_es_campo;
} Objeto;

extern Objeto* tabla_a;
extern s32 tabla_b;
u8 D_tabla[8];
typedef unsigned char u_char;
    return retornado;
"""

FUENTE = "typedef struct Local { s16 radio; } Local;\nstatic Local D_local;\n"


def tabla() -> an.TablaTipos:
    return an.construir_tabla([CABECERA, FUENTE])


def entorno(fuente: str, nombre: str = "f") -> tuple[an.Entorno, c.Funcion]:
    funcion = c.analizar_funcion(fuente, nombre, frozenset({"Objeto", "SVECTOR", "VECTOR"}))
    return an.Entorno(tabla(), funcion), funcion


def expresion(texto: str) -> c.Expr:
    funcion = c.analizar_funcion(f"void f(void)\n{{\n    {texto};\n}}", "f")
    sentencia = funcion.cuerpo.items[0]
    assert isinstance(sentencia, c.Expresion)
    return sentencia.expr


def test_parsear_tipo_reconoce_enteros_punteros_y_agregados() -> None:
    assert an.parsear_tipo("s16") == an.Tipo("s16", 0, 16, True)
    assert an.parsear_tipo("unsigned char") == an.Tipo("unsigned char", 0, 8, False)
    assert an.parsear_tipo("unsigned") == an.Tipo("unsigned", 0, 32, False)
    assert an.parsear_tipo("volatile u8*").texto == "u8*"
    assert an.parsear_tipo("Objeto", 2).texto == "Objeto**"
    assert an.parsear_tipo("struct Objeto").texto == "struct Objeto"
    assert an.nombre_de_estructura("struct Objeto") == "Objeto"
    assert an.nombre_de_estructura("union U") == "U"
    assert an.nombre_de_estructura("Objeto") == "Objeto"
    agregado = an.parsear_tipo("Objeto")
    assert not agregado.es_entero and not agregado.es_puntero and not agregado.es_escalar
    assert an.parsear_tipo("u8", 1).es_puntero and an.parsear_tipo("u8", 1).es_escalar
    assert agregado.rango == (0, 0)


def test_rango_de_los_enteros_con_y_sin_signo() -> None:
    assert an.tipo_entero("s16").rango == (-32768, 32767)
    assert an.tipo_entero("u16").rango == (0, 65535)
    assert an.tipo_entero("u32").rango == (0, 0xFFFFFFFF)
    with pytest.raises(KeyError):
        an.tipo_entero("float")


def test_la_tabla_recoge_campos_estructuras_globales_y_nombres_de_tipo() -> None:
    t = tabla()
    assert t.campos["radio"] == an.parsear_tipo("s16")
    assert t.campos["vx"] is None
    assert t.campos["bytes"] is None
    assert t.campos["sig10"] == an.parsear_tipo("struct Objeto", 1)
    assert "retornado" not in t.campos
    assert t.estructuras["Objeto"]["flags08"] == an.parsear_tipo("u32")
    assert t.estructuras["Objeto"]["bytes"].arreglo
    assert t.estructuras["VECTOR"]["vx"] == an.parsear_tipo("s32")
    assert t.estructuras["SVECTOR"]["vx"] == an.parsear_tipo("short")
    assert t.estructuras["Objeto"]["valor"] == an.parsear_tipo("s32")
    assert t.estructuras["Objeto"]["ptr"] == an.parsear_tipo("s32", 1)
    assert "a" not in t.estructuras["Objeto"]
    # Un campo cuyo tipo es una union anonima no es un entero ni se puede copiar a un temporal.
    assert t.estructuras["Objeto"]["u78"] == an.Tipo("union")
    assert not t.estructuras["Objeto"]["u78"].es_escalar
    assert t.globales["tabla_a"] == an.parsear_tipo("Objeto", 1)
    assert t.globales["tabla_b"] == an.parsear_tipo("s32")
    assert {"Objeto", "SVECTOR", "u_char", "Local"} <= t.nombres_de_tipo


def test_un_cierre_de_llave_seguido_de_una_palabra_reservada_no_define_un_tipo() -> None:
    fuente = (
        "void g(s32 a)\n{\n    if (a) {\n        a = 1;\n    }\n    return;\n}\n"
        "void h(void)\n{\n    while (1) {\n    } break;\n}\n"
    )
    t = an.construir_tabla([fuente])
    assert not {"return", "break"} & t.nombres_de_tipo
    assert an.nombres_de_typedef("{ } return;") == set()


def test_los_typedef_de_punteros_a_funcion_arreglos_y_varios_declaradores_son_tipos() -> None:
    texto = (
        "typedef void (*Rutina)(Objeto* o, s32 id);\n"
        "typedef u32 ( *Digitos )(s32);\n"
        "typedef u_short TABLA[34816];\n"
        "typedef struct Par { s32 a; union { s32 b; } u; } Par, *PPar;\n"
        "typedef unsigned long u_long;\n"
        "typedef int typedef_sin_cierre"
    )
    assert an.nombres_de_typedef(texto) == {"Rutina", "Digitos", "TABLA", "Par", "PPar", "u_long"}
    assert an.nombres_de_typedef("typedef {} {") == set()


def test_un_tipo_con_calificador_tras_un_asterisco_o_declarador_abstracto_es_opaco() -> None:
    for texto in ("u16* volatile*", "u8 (*)[64]", "void (*)(s32)", "u8* const"):
        tipo = an.parsear_tipo(texto)
        assert not tipo.es_escalar and tipo.texto == texto
    assert an.parsear_tipo("u8 (*)[64]", 1).texto == "u8 (*)[64]*"


def test_las_estructuras_sin_nombre_ni_typedef_se_omiten() -> None:
    t = an.construir_tabla(["struct {\n    s32 oculto;\n};\nstruct Con { s16 visible; };\n"])
    assert list(t.estructuras) == ["Con"]


def test_literales_enteros() -> None:
    assert an.tipo_de_literal("12") == an.S32
    assert an.tipo_de_literal("0x7FFFFFFF") == an.S32
    assert an.tipo_de_literal("0x80000000") == an.U32
    assert an.tipo_de_literal("5u") == an.U32
    assert an.tipo_de_literal("0x1FFFFFFFF") is None
    assert an.tipo_de_literal("1.5") is None
    assert an.tipo_de_literal("08") is None
    assert an.tipo_de_literal("010") == an.S32
    assert an.valor_de_literal(c.Num("0x12C")) == 0x12C
    assert an.valor_de_literal(c.Unario("-", c.Num("1"))) == -1
    assert an.valor_de_literal(c.Unario("-", c.Id("x"))) is None
    assert an.valor_de_literal(c.Num("010")) == 8
    assert an.valor_de_literal(c.Id("x")) is None
    assert an.valor_de_literal(c.Num("5u")) == 5


def test_inferencia_de_tipos_de_expresiones() -> None:
    e, _ = entorno("void f(Objeto* o, s16 k, u32 m)\n{\n    s32 v;\n    u16 w;\n    s32 arreglo[3];\n}")
    infer = e.inferir
    assert infer(c.Id("k")) == an.parsear_tipo("s16")
    assert infer(c.Id("tabla_a")) == an.parsear_tipo("Objeto", 1)
    assert infer(c.Id("desconocida")) is None
    assert infer(c.Num("3")) == an.S32
    assert infer(c.Conversion("u8*", c.Id("o"))) == an.parsear_tipo("u8", 1)
    assert infer(expresion("o->radio")) == an.parsear_tipo("s16")
    assert infer(expresion("o->min.vx")) == an.parsear_tipo("short")
    assert infer(expresion("o->sig10->radio")) == an.parsear_tipo("s16")
    assert infer(expresion("(*o).radio")) == an.parsear_tipo("s16")
    assert infer(expresion("desconocido->radio")) == an.parsear_tipo("s16")
    assert infer(expresion("desconocido->vx")) is None
    assert infer(expresion("*o")) == an.parsear_tipo("Objeto")
    assert infer(expresion("*o->ptr")) == an.parsear_tipo("s32")
    assert infer(expresion("arreglo[1]")) == an.parsear_tipo("s32")
    assert infer(expresion("o->bytes[1]")) == an.parsear_tipo("u8")
    assert infer(expresion("k[1]")) is None
    assert infer(expresion("-k")) == an.S32
    assert infer(expresion("~w")) == an.S32
    assert infer(expresion("!k")) == an.S32
    assert infer(expresion("&k")) is None
    assert infer(expresion("++k")) == an.parsear_tipo("s16")
    assert infer(expresion("k--")) == an.parsear_tipo("s16")
    assert infer(expresion("k = 1")) == an.parsear_tipo("s16")
    assert infer(expresion("k < m")) == an.S32
    assert infer(expresion("k && m")) == an.S32
    assert infer(expresion("(k, m)")) == an.parsear_tipo("u32")
    assert infer(expresion("k + k")) == an.S32
    assert infer(expresion("k + m")) == an.U32
    assert infer(expresion("m >> 2")) == an.U32
    assert infer(expresion("o + 1")) == an.parsear_tipo("Objeto", 1)
    assert infer(expresion("1 + o")) == an.parsear_tipo("Objeto", 1)
    assert infer(expresion("o - o")) == an.S32
    assert infer(expresion("o + o")) is None
    assert infer(expresion("k + desconocida")) is None
    assert infer(expresion("o + desconocida")) is None
    assert infer(expresion("k ? 1 : 2")) == an.S32
    assert infer(expresion("k ? m : 2")) == an.U32
    assert infer(expresion("k ? k : 2")) == an.S32
    assert infer(expresion("k ? o : 0")) == an.parsear_tipo("Objeto", 1)
    assert infer(expresion("k ? 0 : o")) == an.parsear_tipo("Objeto", 1)
    assert infer(expresion("k ? o : o")) == an.parsear_tipo("Objeto", 1)
    assert infer(expresion("k ? o : k")) is None
    assert infer(expresion("k ? o->bytes : o->bytes")) is None
    assert infer(expresion("k ? desconocida : 1")) is None
    assert infer(expresion("k ? 1 : desconocida")) is None
    assert infer(expresion("m % 3")) == an.U32
    assert infer(expresion("k / m")) == an.U32
    assert infer(expresion("k | m")) == an.U32
    assert infer(expresion("k ^ k")) == an.S32
    assert infer(expresion("k << m")) == an.S32
    assert infer(expresion("m << k")) == an.U32
    assert infer(expresion("k & 0xFF")) == an.S32
    assert infer(expresion("k |= m")) == an.parsear_tipo("s16")
    assert infer(expresion("f(1)")) is None
    assert infer(expresion("o->bytes")) == an.Tipo("u8", 0, 8, False, True)
    assert not infer(expresion("o->bytes")).es_escalar  # type: ignore[union-attr]


def test_promocion_y_conversiones_aritmeticas() -> None:
    assert an.promover(an.tipo_entero("u16")) == an.S32
    assert an.promover(an.tipo_entero("s32")) == an.S32
    assert an.promover(an.tipo_entero("u32")) == an.U32
    assert an.promover(None) is None
    assert an.promover(an.parsear_tipo("Objeto", 1)) is None
    assert an.aritmetico(an.tipo_entero("s16"), an.tipo_entero("u32")) == an.U32
    assert an.aritmetico(an.tipo_entero("s16"), an.tipo_entero("s32")) == an.S32
    assert an.aritmetico(an.tipo_entero("s16"), an.parsear_tipo("Objeto", 1)) is None


def test_conserva_valor_exige_que_el_rango_de_origen_quepa() -> None:
    assert an.conserva_valor(an.tipo_entero("u16"), an.tipo_entero("s32"))
    assert an.conserva_valor(an.tipo_entero("s16"), an.tipo_entero("s16"))
    assert not an.conserva_valor(an.tipo_entero("s16"), an.tipo_entero("u16"))
    assert not an.conserva_valor(an.tipo_entero("s32"), an.tipo_entero("s16"))
    assert not an.conserva_valor(an.parsear_tipo("Objeto", 1), an.tipo_entero("s32"))


def test_es_pura_rechaza_llamadas_asignaciones_e_incrementos() -> None:
    assert an.es_pura(expresion("a->b + c[1] * 2"))
    for impura in ("f(1)", "a = 1", "a++", "++a", "--a", "b + (a = 2)"):
        assert not an.es_pura(expresion(impura))


@pytest.mark.parametrize(
    ("texto", "ruta"),
    [
        ("o->radio", "radio"),
        ("o->min.vx", "min.vx"),
        ("o->pel[2]", "pel[]"),
        ("o->pel[2].x", "pel[].x"),
        ("a[1]", "[]"),
        ("*p", "*"),
        ("(*p).x", "x"),
        ("x", None),
        ("f(1)", None),
    ],
)
def test_ruta_de_memoria(texto: str, ruta: str | None) -> None:
    assert an.ruta_de_memoria(expresion(texto)) == ruta


def sentencia(texto: str) -> c.Sentencia:
    return c.analizar_funcion(f"void f(void)\n{{\n    {texto}\n}}", "f").cuerpo.items[0]


def test_efectos_de_asignaciones_lecturas_y_escrituras() -> None:
    e = an.efectos_de(sentencia("o->radio = k + p->valor;"))
    assert e.escribe == {"m:radio"}
    assert e.lee == {"v:o", "v:k", "v:p", "m:valor"}
    assert not e.barrera
    compuesta = an.efectos_de(sentencia("x += 1;"))
    assert compuesta.escribe == {"v:x"} and "v:x" in compuesta.lee
    incremento = an.efectos_de(sentencia("i++;"))
    assert incremento.escribe == {"v:i"} and "v:i" in incremento.lee
    previo = an.efectos_de(sentencia("--i;"))
    assert previo.escribe == {"v:i"}
    direccion = an.efectos_de(sentencia("p = &o->min;"))
    assert "m:min" not in direccion.lee and "v:o" in direccion.lee and not direccion.barrera
    assert an.efectos_de(sentencia("p = &x;")).barrera
    assert an.efectos_de(sentencia("f(1);")).barrera
    assert an.efectos_de(sentencia("return;")).barrera


def test_dos_sentencias_son_independientes_si_no_se_cruzan() -> None:
    def libre(a: str, b: str) -> bool:
        return an.son_independientes(an.efectos_de(sentencia(a)), an.efectos_de(sentencia(b)))

    assert libre("w->cx = o->min.vx;", "w->cy = o->min.vy;")
    assert not libre("w->cx = 1;", "w->cx = 2;")
    assert not libre("w->min.vx = 1;", "w->min = o;")
    assert not libre("x = 1;", "y = x;")
    assert not libre("y = x;", "x = 1;")
    assert libre("x = 1;", "y = 2;")
    assert not libre("a[i] = 1;", "b->p = a[j];")
    assert not libre("*p = 1;", "q->radio = 2;")
    assert not libre("x = 1;", "f(2);")
    assert libre("o->a[1] = 1;", "o->b = 2;")
    assert not libre("o->pel[1] = 1;", "o->pel[2].x = 2;")


def test_identificadores_y_texto_de_una_expresion() -> None:
    e = expresion("a->b + f(c, 1)")
    assert an.identificadores_de(e) == {"a", "f", "c"}
    assert an.texto_de(e) == "a->b + f(c, 1)"


def test_una_local_de_puntero_a_arreglo_o_a_funcion_tiene_tipo_opaco() -> None:
    env, _ = entorno("void f(void)\n{\n    s16 (*pos)[2];\n    void (*fp)(s32);\n    s16 n;\n}")
    for nombre in ("pos", "fp"):
        tipo = env.locales[nombre]
        assert "(" in tipo.base and not tipo.es_escalar and not tipo.arreglo
    assert env.locales["n"].es_entero

import pytest
from tools.ghidra import ensamblador
from tools.ghidra.ensamblador import (
    FuncionAsm,
    Instruccion,
    Referencia,
    Salto,
    analizar_funcion,
    dividir_por_funcion,
    leer_instrucciones,
    resolver_simbolo,
)

from tests.ghidra.escenario import A, B, C, D, texto_asm


def _linea(direccion: int, texto: str) -> str:
    return f"    /* 0 {direccion:08X} 00000000 */  {texto}"


def _funcion(*textos: str, nombre: str = "func_80014AC4", base: int = 0x80014AC4) -> FuncionAsm:
    lineas = (
        [f"glabel {nombre}"]
        + [_linea(base + 4 * i, t) for i, t in enumerate(textos)]
        + [f"endlabel {nombre}"]
    )
    return dividir_por_funcion("\n".join(lineas) + "\n")[0]


def test_divide_el_texto_en_funciones_y_descarta_lo_que_queda_fuera() -> None:
    funciones = dividir_por_funcion(texto_asm())
    assert [f.nombre for f in funciones][:3] == ["func_80014AC4", "func_80014AF8", "func_80014B0C"]
    assert funciones[0].direccion == A
    assert funciones[0].lineas[0] == "glabel func_80014AC4"
    assert funciones[0].lineas[-1] == "endlabel func_80014AC4"
    assert all("ruido" not in linea for f in funciones for linea in f.lineas)


def test_una_funcion_sin_instrucciones_se_rechaza() -> None:
    with pytest.raises(ValueError, match="no contiene instrucciones"):
        dividir_por_funcion("glabel vacia\nendlabel vacia\n")


def test_un_glabel_dentro_de_otra_funcion_se_rechaza() -> None:
    texto = f"glabel a\n{_linea(0x80014AC4, 'nop')}\nglabel b\n"
    with pytest.raises(ValueError, match="linea 3: glabel dentro de la funcion a"):
        dividir_por_funcion(texto)


def test_una_funcion_repetida_se_rechaza() -> None:
    una = f"glabel a\n{_linea(0x80014AC4, 'nop')}\nendlabel a\n"
    with pytest.raises(ValueError, match="funcion a repetida"):
        dividir_por_funcion(una + una)


@pytest.mark.parametrize("texto", ["endlabel a\n", "glabel a\nendlabel b\n"])
def test_un_endlabel_sin_su_glabel_se_rechaza(texto: str) -> None:
    with pytest.raises(ValueError, match="endlabel sin su glabel"):
        dividir_por_funcion(texto)


def test_una_funcion_sin_endlabel_se_rechaza() -> None:
    with pytest.raises(ValueError, match="la funcion a no termina con endlabel"):
        dividir_por_funcion(f"glabel a\n{_linea(0x80014AC4, 'nop')}\n")


def test_las_cotas_de_lineas_y_de_bytes_se_aplican(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ensamblador, "MAX_LINEAS_ASM", 2)
    with pytest.raises(ValueError, match="3 lineas exceden el maximo de 2"):
        dividir_por_funcion("a\nb\nc\n")
    monkeypatch.setattr(ensamblador, "MAX_BYTES_ASM", 4)
    with pytest.raises(ValueError, match="excede 4 bytes"):
        dividir_por_funcion("abcdef")


def test_las_instrucciones_ignoran_etiquetas_directivas_y_palabras_de_datos() -> None:
    funcion = _funcion("addiu      $v0, $zero, 0x1 /* comentario */", "nop")
    funcion = FuncionAsm(
        funcion.nombre,
        funcion.direccion,
        (*funcion.lineas, "  .L80014ACC:", "    /* 0 80014AD0 00002000 */ .word 0x00200000"),
    )
    assert leer_instrucciones(funcion) == [
        Instruccion(0x80014AC4, "addiu", "$v0, $zero, 0x1"),
        Instruccion(0x80014AC8, "nop", ""),
    ]


def test_resuelve_nombres_automaticos_y_de_la_tabla() -> None:
    assert resolver_simbolo("D_80069348", {}) == 0x80069348
    assert resolver_simbolo("jtbl_80067E64", {}) == 0x80067E64
    assert resolver_simbolo("func_80014B04", {}) == 0x80014B04
    assert resolver_simbolo("VSync", {"VSync": 0x80045DA0}) == 0x80045DA0
    assert resolver_simbolo("desconocido", {"VSync": 0x80045DA0}) is None


def test_los_saltos_distinguen_llamadas_directas_indirectas_y_locales() -> None:
    funcion = _funcion(
        "jal        VSync",
        "jal        VSync + 0x4",
        "jal        simbolo_raro",
        "jal        $t0",
        "j          .L80014AE0",
        "j          VSync",
        "jalr       $v0",
        "jr         $t1",
        "jr         $ra",
    )
    analisis = analizar_funcion(funcion, {"VSync": 0x80045DA0})
    assert analisis.saltos == (
        Salto(0x80014AC4, "jal", 0x80045DA0),
        Salto(0x80014AC8, "jal", 0x80045DA4),
        Salto(0x80014ACC, "jal", None),
        Salto(0x80014AD0, "jal", None),
        Salto(0x80014AD8, "j", 0x80045DA0),
        Salto(0x80014ADC, "jalr", None),
        Salto(0x80014AE0, "jr", None),
    )


def test_las_referencias_cubren_hi_lo_gp_y_la_forma_alta_sin_pareja() -> None:
    funcion = _funcion(
        "lui        $a0, %hi(D_80060000)",
        "lw         $v0, %lo(D_80060000 + 0x4)($a0)",
        "lw         $v1, 0x10($gp)",
        "lw         $v1, -0x8($gp)",
        "lui        $a1, (0x80010000 >> 16)",
        "lui        $a2, %hi(no_existe)",
    )
    analisis = analizar_funcion(funcion, {})
    assert analisis.referencias == (
        Referencia("D_80060000", 0x80060000, 0),
        Referencia("D_80060000", 0x80060004, 4),
        Referencia("gp+0x10", 0x80069330, 0),
        Referencia("gp-0x8", 0x80069318, 0),
        Referencia("0x80010000", 0x80010000, 0),
    )
    assert analisis.sin_resolver == 1


def test_el_escenario_completo_se_lee_sin_errores_de_simbolos() -> None:
    funciones = {f.nombre: f for f in dividir_por_funcion(texto_asm())}
    analisis = analizar_funcion(funciones["func_80014B14"], {})
    assert [s.tipo for s in analisis.saltos] == ["jr"]
    assert D == 0x80014B14
    assert B == 0x80014AF8
    assert C == 0x80014B0C

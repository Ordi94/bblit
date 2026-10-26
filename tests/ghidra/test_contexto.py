import pytest
from tools.ghidra.contexto import (
    CABECERA_TIPOS,
    MAX_TAMANO_ARREGLO,
    construir_contexto,
    declarar_dato,
    extraer_prototipo,
)
from tools.ghidra.dominio import Simbolo
from tools.ghidra.exportaciones import ReferenciaDato


@pytest.mark.parametrize(
    ("firma", "esperado"),
    [
        ("int FUN_80018c68(int param_1,MATRIX *param_2)\n\n{\n}", "s32 func_X(s32, void *);"),
        ("void FUN_80016218(void)\n{\n}", "void func_X(void);"),
        ("void FUN_80016218()\n{\n}", "void func_X(void);"),
        (
            "undefined4 FUN_x(uint a, ushort b, short c, byte d, char e, undefined1 f)\n{",
            "s32 func_X(u32, u16, s16, u8, s8, u8);",
        ),
        ("float FUN_x(float a, double b)\n{", "f32 func_X(f32, f64);"),
        ("void * FUN_x(const char *s)\n{", "void * func_X(void *);"),
        (
            "/* WARNING: x */\n/* Possible A/b\n   Possible C/d */\nint DrawSync(int mode)\n{",
            "s32 func_X(s32);",
        ),
        ("MATRIX FUN_x(void)\n{", None),
        ("void FUN_x(MATRIX m)\n{", None),
        ("void FUN_x(void p)\n{", None),
        ("void FUN_x(int)\n{", None),
        ("void FUN_x(int a, code *cb(int))\n{", None),
        ("esto no es una firma", None),
    ],
)
def test_traduce_la_firma_de_ghidra_a_un_prototipo_de_m2c(firma: str, esperado: str | None) -> None:
    assert extraer_prototipo(firma, "func_X") == esperado


def test_declara_los_datos_segun_su_tamano() -> None:
    assert declarar_dato(ReferenciaDato(0x80010000, 4, (), 0, 0)) == "extern s32 D_80010000;"
    assert declarar_dato(ReferenciaDato(0x80010001, 1, (), 0, 0)) == "extern u8 D_80010001;"
    assert declarar_dato(ReferenciaDato(0x80010002, 2, (), 0, 0)) == "extern u16 D_80010002;"
    assert declarar_dato(ReferenciaDato(0x80010010, 16, (), 0, 0)) == "extern u8 D_80010010[16];"
    assert declarar_dato(ReferenciaDato(0x80010020, 0, (), 0, 0)) is None
    assert declarar_dato(ReferenciaDato(0x80010030, MAX_TAMANO_ARREGLO + 1, (), 0, 0)) is None


def test_el_contexto_une_tipos_prototipos_y_datos_fuera_de_las_funciones() -> None:
    simbolos = [Simbolo("main", 0x80016414, "func", 0x7F8)]
    datos = [
        ReferenciaDato(0x80010000, 4, (), 1, 1),
        ReferenciaDato(0x80016420, 4, (), 1, 1),
        ReferenciaDato(0x80010004, 0, (), 1, 1),
    ]
    contexto = construir_contexto(simbolos, {0x80016414: "void main(void);"}, datos)
    assert contexto == CABECERA_TIPOS + "\nvoid main(void);\nextern s32 D_80010000;\n"

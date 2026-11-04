from typing import Any

import pytest
from tools.reconstruccion import fuentes_c
from tools.reconstruccion.fuentes_c import EstadoFuncion, analizar_fuente, analizar_fuentes, ubicar_funcion

CABECERA = '#include "common.h"\n\n'


def test_solo_include_asm_es_ensamblador() -> None:
    texto = CABECERA + 'INCLUDE_ASM("asm/nonmatchings/a", func_80014AC4);\n'
    assert analizar_fuente(texto) == {"func_80014AC4": EstadoFuncion.ENSAMBLADOR}


def test_definicion_normal_es_c_y_el_include_asm_vecino_sigue_siendo_ensamblador() -> None:
    texto = (
        CABECERA
        + 'INCLUDE_ASM("asm/nonmatchings/a", func_A);\n'
        + "s32 func_B(void* a0)\n{\n    return 1;\n}\n"
        + 'INCLUDE_ASM("asm/nonmatchings/a", func_C);\n'
    )
    assert analizar_fuente(texto) == {
        "func_A": EstadoFuncion.ENSAMBLADOR,
        "func_B": EstadoFuncion.C,
        "func_C": EstadoFuncion.ENSAMBLADOR,
    }


def test_intento_bajo_non_matching_con_include_asm_en_else_no_cuenta_como_c() -> None:
    texto = (
        "#ifdef NON_MATCHING\n"
        "s32 func_B(s32 x)\n{\n    return x;\n}\n"
        "#else\n"
        'INCLUDE_ASM("asm/nonmatchings/a", func_B);\n'
        "#endif\n"
    )
    assert analizar_fuente(texto) == {"func_B": EstadoFuncion.NO_COINCIDENTE}


def test_ifndef_non_matching_invierte_las_ramas() -> None:
    texto = (
        "#ifndef NON_MATCHING\n"
        'INCLUDE_ASM("asm/nonmatchings/a", func_B);\n'
        "#else\n"
        "s32 func_B(s32 x)\n{\n    return x;\n}\n"
        "#endif\n"
    )
    assert analizar_fuente(texto) == {"func_B": EstadoFuncion.NO_COINCIDENTE}


def test_las_condiciones_ajenas_se_tratan_como_verdaderas_y_conservan_el_anidamiento() -> None:
    texto = (
        "#if 1\n"
        "#ifdef NON_MATCHING\n"
        "s32 func_B(void)\n{\n    return 0;\n}\n"
        "#else\n"
        'INCLUDE_ASM("asm/nonmatchings/a", func_B);\n'
        "#endif\n"
        "s32 func_C(void)\n{\n    return 1;\n}\n"
        "#else\n"
        "#endif\n"
    )
    estados = analizar_fuente(texto)
    assert estados == {"func_B": EstadoFuncion.NO_COINCIDENTE, "func_C": EstadoFuncion.C}


def test_los_comentarios_no_cuentan_pero_las_cadenas_con_barras_si_se_respetan() -> None:
    texto = (
        '/* INCLUDE_ASM("asm/nonmatchings/a", func_X); */\n'
        '// INCLUDE_ASM("asm/nonmatchings/a", func_Y);\n'
        'INCLUDE_ASM("asm/nonmatchings/a", func_Z);\n'
        'static char* texto = "no es // un comentario";\n'
    )
    assert analizar_fuente(texto) == {"func_Z": EstadoFuncion.ENSAMBLADOR}


def test_las_estructuras_de_control_no_se_toman_por_definiciones() -> None:
    texto = (
        "s32 func_B(s32 x)\n{\n    while (x > 0) {\n        x = x - 1;\n    }\n"
        "    if (x == 0) {\n        return 1;\n    }\n    return 0;\n}\n"
    )
    assert analizar_fuente(texto) == {"func_B": EstadoFuncion.C}


@pytest.mark.parametrize(
    "definicion",
    [
        "struct Ranura *func_80036204(u8 *base)\n{\n    return 0;\n}\n",
        "Ranura *func_80036204(u8 *base)\n{\n    return 0;\n}\n",
    ],
)
def test_una_definicion_que_el_particionador_no_veria_se_rechaza_con_la_forma_correcta(
    definicion: Any,
) -> None:
    with pytest.raises(ValueError, match=r"no la reconoceria el particionador.*Ranura\* func_80036204"):
        analizar_fuente(definicion)


def test_la_forma_con_el_asterisco_pegado_al_tipo_si_se_reconoce() -> None:
    assert analizar_fuente("Ranura* func_80036204(u8* base)\n{\n    return 0;\n}\n") == {
        "func_80036204": EstadoFuncion.C
    }


def test_una_funcion_que_solo_existe_bajo_non_matching_se_rechaza() -> None:
    texto = "#ifdef NON_MATCHING\ns32 func_B(void)\n{\n    return 0;\n}\n#endif\n"
    with pytest.raises(ValueError, match="'func_B' solo existe bajo NON_MATCHING"):
        analizar_fuente(texto)


@pytest.mark.parametrize(
    ("texto", "mensaje"),
    [
        ("#else\n", "linea 1: '#else' sin condicion abierta"),
        ("int a;\n#endif\n", "linea 2: '#endif' sin condicion abierta"),
        ("#ifdef NON_MATCHING\n", "sin '#endif'"),
        ("#if defined(NON_MATCHING)\n#endif\n", "linea 1: use '#ifdef NON_MATCHING' o '#ifndef'"),
        ("#ifdef OTRO_NON_MATCHING\n#endif\n", "linea 1: use '#ifdef NON_MATCHING' o '#ifndef'"),
    ],
)
def test_preprocesador_mal_formado_se_rechaza_con_mensaje(texto: Any, mensaje: Any) -> None:
    with pytest.raises(ValueError, match=mensaje):
        analizar_fuente(texto)


def test_un_archivo_excesivo_se_rechaza(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fuentes_c, "MAX_BYTES_FUENTE", 10)
    with pytest.raises(ValueError, match="excede el tamano permitido"):
        analizar_fuente("x" * 11)


def test_directiva_vacia_y_directivas_desconocidas_se_ignoran() -> None:
    texto = '#\n#include "common.h"\n#define X 1\nINCLUDE_ASM("asm/nonmatchings/a", func_A);\n'
    assert analizar_fuente(texto) == {"func_A": EstadoFuncion.ENSAMBLADOR}


def test_analizar_fuentes_ordena_por_archivo_y_nombra_el_archivo_con_error() -> None:
    estados = analizar_fuentes(
        {
            "src/b.c": 'INCLUDE_ASM("asm/nonmatchings/b", func_B);',
            "src/a.c": 'INCLUDE_ASM("asm/nonmatchings/a", func_A);',
        }
    )
    assert list(estados) == ["src/a.c", "src/b.c"]
    with pytest.raises(ValueError, match=r"^src/malo\.c: linea 1: '#else' sin condicion abierta"):
        analizar_fuentes({"src/malo.c": "#else\n"})


def test_ubicar_funcion_devuelve_archivo_y_estado_o_falla() -> None:
    estados = {
        "src/a.c": {"func_A": EstadoFuncion.ENSAMBLADOR},
        "src/b.c": {"func_B": EstadoFuncion.C},
    }
    assert ubicar_funcion(estados, "func_B") == ("src/b.c", EstadoFuncion.C)
    with pytest.raises(ValueError, match="'func_X' no figura en ningun archivo de src/"):
        ubicar_funcion(estados, "func_X")

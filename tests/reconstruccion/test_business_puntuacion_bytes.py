"""Reglas de negocio de la puntuacion por bytes: forma simbolica y numerica de una referencia no puntuan."""

from pathlib import Path

import pytest
from tools.reconstruccion import cli, diff, progreso
from tools.reconstruccion.diff import ResultadoDiff

from .test_gp import EjecutorEnlace, crear_repo_diff, herramientas_con_enlace


def comparar(raiz: Path, ejecutor: EjecutorEnlace) -> ResultadoDiff:
    return diff.comparar_funcion(raiz, "func_80036204", herramientas_con_enlace(), Path("diff.py"), ejecutor)


def test_si_los_bytes_enlazados_coinciden_la_puntuacion_informada_es_cero(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    resultado = comparar(tmp_path, EjecutorEnlace(70))
    assert resultado.puntuacion == 0
    assert resultado.coincide is True


@pytest.mark.parametrize("puntuacion_asm", [5, 15, 70, 390])
def test_la_puntuacion_no_crece_con_las_referencias_que_solo_cambian_de_forma(
    tmp_path: Path, puntuacion_asm: int
) -> None:
    crear_repo_diff(tmp_path)
    resultado = comparar(tmp_path, EjecutorEnlace(puntuacion_asm))
    assert resultado.puntuacion == 0
    assert resultado.puntuacion_asm == puntuacion_asm
    assert resultado.referencias_numericas == 2


def test_si_los_bytes_difieren_se_conserva_la_puntuacion_de_asm_differ(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    resultado = comparar(tmp_path, EjecutorEnlace(70, difiere=True))
    assert resultado.puntuacion == 70
    assert resultado.puntuacion_asm == 70
    assert resultado.bytes_iguales is False
    assert resultado.coincide is False


def test_sin_elf_ni_direccion_no_se_puede_decidir_y_vale_la_puntuacion_de_asm_differ(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path, con_direccion=False)
    resultado = comparar(tmp_path, EjecutorEnlace(70))
    assert resultado.puntuacion == 70
    assert resultado.bytes_iguales is None
    assert resultado.coincide is False


def test_una_coincidencia_exacta_puntua_cero_sin_necesitar_los_bytes(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    resultado = comparar(tmp_path, EjecutorEnlace(0))
    assert (resultado.puntuacion, resultado.puntuacion_asm, resultado.bytes_iguales) == (0, 0, None)


SALIDAS_QUE_COINCIDEN_EN_BYTES = [
    ("func_8004443C", "src/graficos_y_gte_12.c", 3, 15),
    ("func_80044588", "src/graficos_y_gte_12.c", 1, 5),
    ("CondCigeq", "src/interprete_de_eventos.c", 1, 5),
    ("func_800400C0", "src/graficos_y_gte_10.c", 14, 70),
    ("CondCgeq", "src/interprete_de_eventos.c", 2, 10),
]


CAMPOS = ("funcion", "archivo", "referencias", "puntuacion_asm")


@pytest.mark.parametrize(CAMPOS, SALIDAS_QUE_COINCIDEN_EN_BYTES)
def test_el_resumen_de_una_funcion_que_coincide_en_bytes_dice_cero_y_deja_la_nota_aparte(
    funcion: str, archivo: str, referencias: int, puntuacion_asm: int
) -> None:
    resultado = ResultadoDiff(funcion, archivo, 0, "", True, referencias, puntuacion_asm)
    assert cli.resumir_comparacion(resultado) == [
        f"nota: {referencias} referencias en forma numerica (asm-differ puntua {puntuacion_asm})",
        f"{funcion} ({archivo}): puntuacion 0 (coincide en bytes)",
    ]


def test_el_resumen_de_una_coincidencia_exacta_es_una_sola_linea_sin_nota() -> None:
    resultado = ResultadoDiff("CondTisaz", "src/interprete_de_eventos.c", 0, "", None, 0, 0)
    assert cli.resumir_comparacion(resultado) == ["CondTisaz (src/interprete_de_eventos.c): puntuacion 0"]


def test_el_resumen_de_bytes_distintos_conserva_la_puntuacion_y_no_anade_nota() -> None:
    resultado = ResultadoDiff("func_80036204", "src/a.c", 70, "", False, 0, 70)
    assert cli.resumir_comparacion(resultado) == ["func_80036204 (src/a.c): puntuacion 70"]


def test_el_resumen_sin_decision_por_bytes_conserva_la_puntuacion() -> None:
    resultado = ResultadoDiff("func_80036204", "src/a.c", 70, "", None)
    assert cli.resumir_comparacion(resultado) == ["func_80036204 (src/a.c): puntuacion 70"]


def test_progreso_cuenta_igual_una_funcion_cerrada_exacta_y_una_que_coincide_en_bytes(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "symbols.txt").write_text(
        "func_80014AC4 = 0x80014AC4; // type:func size:0x10\n"
        "func_80014AD4 = 0x80014AD4; // type:func size:0x10\n",
        encoding="utf-8",
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.c").write_text(
        "s32 func_80014AC4(void)\n{\n    return 0;\n}\n\n"
        "/* Coincide en bytes (1 referencia en forma numerica; el diff puntua 5). */\n"
        "s32 func_80014AD4(void)\n{\n    return 1;\n}\n",
        encoding="utf-8",
    )
    medido = progreso.generar_progreso(tmp_path)
    assert medido.funciones_en_c == 2
    assert medido.no_coincidentes == ()
    documento = (tmp_path / "docs" / "PROGRESO.md").read_text(encoding="utf-8")
    assert "referencias en forma numerica" not in documento
    assert "| `src/a.c` | 2 | 0 | 0 | 32 | 32 |" in documento

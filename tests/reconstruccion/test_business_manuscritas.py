"""Reglas de negocio de las rutinas manuscritas: se listan aparte y las INCLUDE_ASM mudas se avisan."""

import json
from pathlib import Path

import pytest
from tools.reconstruccion import cli, fuentes_c, progreso
from tools.reconstruccion.fuentes_c import EstadoFuncion, MarcaAsm
from tools.reconstruccion.progreso import FuncionSimbolo

SIMBOLOS = (
    "func_80014AC4 = 0x80014AC4; // type:func size:0x10\n"
    "func_80014AD4 = 0x80014AD4; // type:func size:0x44\n"
    "func_80014B18 = 0x80014B18; // type:func size:0x20\n"
    "func_80014B38 = 0x80014B38; // type:func size:0x30\n"
)


def asm(funcion: str) -> str:
    return f'INCLUDE_ASM("asm/nonmatchings/a", {funcion});\n'


def test_el_comentario_rutina_escrita_a_mano_en_el_original_marca_la_funcion_como_manuscrita() -> None:
    texto = "/* Rutina escrita a mano en el original: copia cinco palabras. */\n" + asm("func_A")
    assert fuentes_c.clasificar_include_asm(texto) == {"func_A": MarcaAsm.MANUSCRITA}


def test_la_variante_rutina_de_gte_escrita_a_mano_en_el_original_tambien_es_manuscrita() -> None:
    texto = "/*\n * Rutina de GTE escrita a mano en el original (marca\n * Handwritten): carga.\n */\n"
    assert fuentes_c.clasificar_include_asm(texto + asm("func_A")) == {"func_A": MarcaAsm.MANUSCRITA}


def test_la_marca_se_reconoce_aunque_el_comentario_la_parta_en_dos_lineas() -> None:
    texto = "/*\n * rutina escrita a mano\n * en el original.\n */\n" + asm("func_A")
    assert fuentes_c.clasificar_include_asm(texto) == {"func_A": MarcaAsm.MANUSCRITA}


def test_un_comentario_con_otra_razon_no_es_manuscrita_pero_si_justifica_el_ensamblador() -> None:
    texto = "/* Se conserva en ensamblador: GCC asigna otros temporales. */\n" + asm("func_A")
    assert fuentes_c.clasificar_include_asm(texto) == {"func_A": MarcaAsm.JUSTIFICADA}


def test_un_comentario_de_linea_tambien_cuenta_como_comentario_previo() -> None:
    texto = "// Rutina escrita a mano en el original.\n" + asm("func_A")
    assert fuentes_c.clasificar_include_asm(texto) == {"func_A": MarcaAsm.MANUSCRITA}


def test_sin_comentario_encima_la_funcion_queda_sin_comentario() -> None:
    assert fuentes_c.clasificar_include_asm(asm("func_A")) == {"func_A": MarcaAsm.SIN_COMENTARIO}
    assert fuentes_c.clasificar_include_asm("int x;\n" + asm("func_A")) == {"func_A": MarcaAsm.SIN_COMENTARIO}


def test_una_linea_en_blanco_entre_el_comentario_y_la_funcion_los_desvincula() -> None:
    texto = "/* Rutina escrita a mano en el original. */\n\n" + asm("func_A")
    assert fuentes_c.clasificar_include_asm(texto) == {"func_A": MarcaAsm.SIN_COMENTARIO}


def test_el_comentario_de_la_funcion_anterior_no_se_hereda() -> None:
    texto = "/* Rutina escrita a mano en el original. */\n" + asm("func_A") + asm("func_B")
    assert fuentes_c.clasificar_include_asm(texto) == {
        "func_A": MarcaAsm.MANUSCRITA,
        "func_B": MarcaAsm.SIN_COMENTARIO,
    }


def test_un_comentario_al_final_de_una_linea_de_codigo_no_cuenta_como_comentario_previo() -> None:
    texto = "int x; /* rutina escrita a mano en el original */\n" + asm("func_A")
    assert fuentes_c.clasificar_include_asm(texto) == {"func_A": MarcaAsm.SIN_COMENTARIO}


def test_los_include_asm_de_un_intento_non_matching_no_se_clasifican() -> None:
    texto = (
        "#ifdef NON_MATCHING\n/* Pendiente: puntuacion 5 */\ns32 func_A(void)\n{\n    return 0;\n}\n#else\n"
        + asm("func_A")
        + "#endif\n"
        + asm("func_B")
    )
    assert fuentes_c.clasificar_include_asm(texto) == {"func_B": MarcaAsm.SIN_COMENTARIO}


def test_un_archivo_sin_include_asm_no_tiene_marcas() -> None:
    assert fuentes_c.clasificar_include_asm("s32 f(void)\n{\n    return 0;\n}\n") == {}


def tabla() -> list[FuncionSimbolo]:
    return progreso.leer_simbolos(SIMBOLOS)


def test_progreso_lista_aparte_las_manuscritas_con_su_tamano_y_no_las_cuenta_como_c() -> None:
    estados = {
        "src/a.c": {
            "func_80014AC4": EstadoFuncion.C,
            "func_80014AD4": EstadoFuncion.ENSAMBLADOR,
            "func_80014B18": EstadoFuncion.ENSAMBLADOR,
        }
    }
    marcas = {
        "src/a.c": {
            "func_80014AD4": MarcaAsm.MANUSCRITA,
            "func_80014B18": MarcaAsm.JUSTIFICADA,
        }
    }
    medido = progreso.calcular_progreso(tabla(), estados, None, None, marcas)
    assert medido.manuscritas == (("func_80014AD4", 0x44),)
    assert medido.sin_comentario == ()
    assert medido.funciones_en_c == 1


def test_progreso_avisa_de_los_include_asm_sin_comentario_solo_en_archivos_con_funciones_en_c() -> None:
    estados = {
        "src/con_c.c": {"func_80014AC4": EstadoFuncion.C, "func_80014AD4": EstadoFuncion.ENSAMBLADOR},
        "src/sin_c.c": {"func_80014B18": EstadoFuncion.ENSAMBLADOR},
    }
    marcas = {
        "src/con_c.c": {"func_80014AD4": MarcaAsm.SIN_COMENTARIO},
        "src/sin_c.c": {"func_80014B18": MarcaAsm.SIN_COMENTARIO},
    }
    medido = progreso.calcular_progreso(tabla(), estados, None, None, marcas)
    assert medido.sin_comentario == (("src/con_c.c", "func_80014AD4"),)


def test_una_funcion_que_ya_no_esta_en_ensamblador_no_se_lista_como_manuscrita() -> None:
    estados = {"src/a.c": {"func_80014AC4": EstadoFuncion.C, "func_80014B38": EstadoFuncion.NO_COINCIDENTE}}
    marcas = {"src/a.c": {"func_80014AC4": MarcaAsm.MANUSCRITA, "func_80014B38": MarcaAsm.SIN_COMENTARIO}}
    medido = progreso.calcular_progreso(tabla(), estados, None, None, marcas)
    assert medido.manuscritas == () and medido.sin_comentario == ()


def test_sin_marcas_el_progreso_no_inventa_categorias() -> None:
    estados = {"src/a.c": {"func_80014AC4": EstadoFuncion.C, "func_80014AD4": EstadoFuncion.ENSAMBLADOR}}
    medido = progreso.calcular_progreso(tabla(), estados, None)
    assert medido.manuscritas == () and medido.sin_comentario == ()


FUENTE = (
    "s32 func_80014AC4(void)\n{\n    return 0;\n}\n"
    "/* Rutina escrita a mano en el original: copia una matriz. */\n" + asm("func_80014AD4") + "\n"
    + asm("func_80014B18")
)


@pytest.fixture
def repositorio(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "symbols.txt").write_text(SIMBOLOS, encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.c").write_text(FUENTE, encoding="utf-8")
    return tmp_path


def test_el_documento_de_progreso_trae_la_categoria_manuscritas_y_el_aviso(repositorio: Path) -> None:
    progreso.generar_progreso(repositorio)
    documento = (repositorio / "docs" / "PROGRESO.md").read_text(encoding="utf-8")
    manuscritas = "## Rutinas manuscritas (siguen en ensamblador por diseño)\n\n- `func_80014AD4` (68 bytes)"
    aviso = "## `INCLUDE_ASM` sin comentario en archivos con funciones en C\n\n- `func_80014B18` (`src/a.c`)"
    assert manuscritas in documento
    assert aviso in documento


def test_el_documento_de_progreso_dice_ninguna_si_no_hay_manuscritas(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "symbols.txt").write_text(SIMBOLOS, encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.c").write_text(asm("func_80014AC4"), encoding="utf-8")
    progreso.generar_progreso(tmp_path)
    documento = (tmp_path / "docs" / "PROGRESO.md").read_text(encoding="utf-8")
    assert "## Rutinas manuscritas (siguen en ensamblador por diseño)\n\nNinguna.\n" in documento
    assert "sin comentario en archivos" not in documento


def test_el_json_de_progreso_expone_manuscritas_y_sin_comentario(repositorio: Path) -> None:
    progreso.generar_progreso(repositorio)
    datos = json.loads((repositorio / "build" / "progreso.json").read_text(encoding="utf-8"))
    assert datos["manuscritas"] == [{"funcion": "func_80014AD4", "bytes": 0x44}]
    assert datos["sinComentario"] == [{"archivo": "src/a.c", "funcion": "func_80014B18"}]


def test_la_orden_progreso_informa_las_manuscritas_y_avisa_sin_fallar(
    repositorio: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["progreso"], {}, repositorio) == 0
    salida = capsys.readouterr()
    assert "manuscritas: 1 rutinas escritas a mano siguen en ensamblador" in salida.out
    assert "aviso: src/a.c: func_80014B18 sigue en INCLUDE_ASM sin comentario que lo explique" in salida.err

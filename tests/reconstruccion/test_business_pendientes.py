"""Reglas de negocio de la guardia de pendientes: todo intento NON_MATCHING declara su puntuacion."""

from pathlib import Path

import pytest
from tools.reconstruccion import cli, fuentes_c, progreso
from tools.reconstruccion.infraestructura import listar_fuentes_c

RAIZ_REPO = Path(__file__).resolve().parents[2]
SIMBOLOS = "func_80014AC4 = 0x80014AC4; // type:func size:0x10\n"


def bloque(funcion: str, cabecera: str) -> str:
    """Bloque NON_MATCHING con `cabecera` justo debajo del #ifdef."""
    return (
        f"#ifdef NON_MATCHING\n{cabecera}s32 {funcion}(void)\n{{\n    return 0;\n}}\n#else\n"
        f'INCLUDE_ASM("asm/nonmatchings/a", {funcion});\n#endif\n'
    )


PENDIENTE = "/* Pendiente: puntuacion 120 con la configuracion versionada (-G0). Reparto de registros. */\n"


def preparar_repositorio(raiz: Path, fuente: str) -> None:
    (raiz / "config").mkdir()
    (raiz / "config" / "symbols.txt").write_text(SIMBOLOS, encoding="utf-8")
    (raiz / "src").mkdir()
    (raiz / "src" / "a.c").write_text(fuente, encoding="utf-8")


def test_un_bloque_con_la_linea_pendiente_bajo_el_ifdef_se_acepta() -> None:
    fuentes_c.verificar_pendientes({"src/a.c": bloque("func_80014AC4", PENDIENTE)})


def test_un_bloque_sin_comentario_se_rechaza_nombrando_archivo_linea_y_funcion() -> None:
    texto = "int x;\n" + bloque("func_80014AC4", "")
    with pytest.raises(ValueError, match=r"src/a\.c:2 func_80014AC4") as error:
        fuentes_c.verificar_pendientes({"src/a.c": texto})
    assert "primer comentario bajo '#ifdef NON_MATCHING'" in str(error.value)


def test_el_error_lista_todos_los_bloques_afectados_de_todos_los_archivos() -> None:
    sin = bloque("func_A", "")
    with pytest.raises(ValueError, match=r"3 funcion\(es\) NON_MATCHING") as error:
        fuentes_c.verificar_pendientes({"src/b.c": sin, "src/a.c": sin + bloque("func_B", PENDIENTE) + sin})
    mensaje = str(error.value)
    assert mensaje.index("src/a.c:1 func_A") < mensaje.index("src/b.c:1 func_A")
    assert "func_B" not in mensaje


def test_un_comentario_que_no_dice_pendiente_no_vale() -> None:
    texto = bloque("func_A", "/* Reparto de registros distinto. */\n")
    with pytest.raises(ValueError, match="func_A"):
        fuentes_c.verificar_pendientes({"src/a.c": texto})


def test_la_puntuacion_debe_ser_un_numero() -> None:
    texto = bloque("func_A", "/* Pendiente: puntuacion alta. */\n")
    with pytest.raises(ValueError, match="func_A"):
        fuentes_c.verificar_pendientes({"src/a.c": texto})


def test_la_linea_pendiente_no_vale_si_el_comentario_empieza_por_otro_texto() -> None:
    texto = bloque("func_A", "/* Nota previa. Pendiente: puntuacion 5. */\n")
    with pytest.raises(ValueError, match="func_A"):
        fuentes_c.verificar_pendientes({"src/a.c": texto})


def test_la_linea_pendiente_antes_del_ifdef_no_vale() -> None:
    texto = PENDIENTE + bloque("func_A", "")
    with pytest.raises(ValueError, match=r"src/a\.c:2 func_A"):
        fuentes_c.verificar_pendientes({"src/a.c": texto})


def test_la_linea_pendiente_despues_del_codigo_no_vale() -> None:
    texto = (
        "#ifdef NON_MATCHING\ns32 func_A(void)\n{\n    return 0;\n}\n" + PENDIENTE + "#else\n"
        'INCLUDE_ASM("asm/nonmatchings/a", func_A);\n#endif\n'
    )
    with pytest.raises(ValueError, match="func_A"):
        fuentes_c.verificar_pendientes({"src/a.c": texto})


def test_la_linea_pendiente_en_comentario_de_bloque_de_varias_lineas_se_acepta() -> None:
    cabecera = "/*\n * Pendiente: puntuacion 350 con la configuracion versionada.\n * Dos lui.\n */\n"
    fuentes_c.verificar_pendientes({"src/a.c": bloque("func_A", cabecera)})


def test_la_linea_pendiente_en_comentario_de_linea_se_acepta() -> None:
    fuentes_c.verificar_pendientes({"src/a.c": bloque("func_A", "// Pendiente: puntuacion 7\n")})


def test_un_ifdef_escrito_dentro_de_un_comentario_no_abre_un_bloque() -> None:
    texto = "/*\n#ifdef NON_MATCHING\n*/\nint x;\n"
    assert fuentes_c.bloques_no_coincidentes(texto) == []
    fuentes_c.verificar_pendientes({"src/a.c": texto})


def test_un_ifdef_sin_rama_de_ensamblador_no_es_un_intento_de_funcion() -> None:
    texto = (
        "#ifdef NON_MATCHING\nint auxiliar;\n#endif\n"
        "#ifdef NON_MATCHING\nint otro;\n#else\nint ajeno;\n#endif\n"
    )
    assert fuentes_c.bloques_no_coincidentes(texto) == []
    fuentes_c.verificar_pendientes({"src/a.c": texto})


def test_otras_condiciones_dentro_del_bloque_no_cierran_el_bloque_antes_de_tiempo() -> None:
    cabecera = PENDIENTE + "#ifdef OTRA\n#else\n#endif\n"
    texto = bloque("func_A", cabecera) + "#ifndef NON_MATCHING\nint x;\n#endif\n#if 1\n#endif\n"
    bloques = fuentes_c.bloques_no_coincidentes(texto)
    assert [b.funcion for b in bloques] == ["func_A"]
    fuentes_c.verificar_pendientes({"src/a.c": texto})


def test_un_bloque_anidado_en_otra_condicion_se_comprueba() -> None:
    texto = "#if 1\n" + bloque("func_A", "") + "#endif\n"
    with pytest.raises(ValueError, match=r"src/a\.c:2 func_A"):
        fuentes_c.verificar_pendientes({"src/a.c": texto})


def test_dos_bloques_consecutivos_se_comprueban_por_separado() -> None:
    texto = bloque("func_A", PENDIENTE) + bloque("func_B", "")
    with pytest.raises(ValueError, match="func_B") as error:
        fuentes_c.verificar_pendientes({"src/a.c": texto})
    assert "func_A" not in str(error.value)


def test_un_archivo_sin_funciones_en_c_ni_bloques_no_da_error() -> None:
    fuentes_c.verificar_pendientes({"src/vacio.c": "", "src/datos.c": "int tabla[4];\n"})
    assert fuentes_c.verificar_pendientes({}) is None


def test_progreso_termina_con_error_y_no_escribe_nada_si_falta_la_linea_pendiente(tmp_path: Path) -> None:
    preparar_repositorio(tmp_path, bloque("func_80014AC4", ""))
    with pytest.raises(ValueError, match=r"src/a\.c:1 func_80014AC4"):
        progreso.generar_progreso(tmp_path)
    assert not (tmp_path / "docs" / "PROGRESO.md").exists()
    assert not (tmp_path / "build" / "progreso.json").exists()


def test_la_orden_progreso_devuelve_uno_y_dice_archivo_y_funcion(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    preparar_repositorio(tmp_path, bloque("func_80014AC4", ""))
    assert cli.main(["progreso"], {}, tmp_path) == 1
    error = capsys.readouterr().err
    assert error.startswith("error: ") and "src/a.c:1 func_80014AC4" in error


def test_progreso_con_la_linea_pendiente_lista_el_motivo(tmp_path: Path) -> None:
    preparar_repositorio(tmp_path, bloque("func_80014AC4", PENDIENTE))
    medido = progreso.generar_progreso(tmp_path)
    assert medido.no_coincidentes == ("func_80014AC4",)
    assert dict(medido.motivos)["func_80014AC4"].startswith("Pendiente: puntuacion 120")


def test_el_repositorio_tiene_una_linea_pendiente_por_cada_bloque_non_matching() -> None:
    textos = listar_fuentes_c(RAIZ_REPO)
    bloques = sum(len(fuentes_c.bloques_no_coincidentes(texto)) for texto in textos.values())
    pendientes = sum(
        1
        for texto in textos.values()
        for motivo in fuentes_c.motivos_no_coincidentes(texto).values()
        if motivo.startswith("Pendiente: puntuacion")
    )
    assert bloques > 0
    assert bloques == pendientes
    fuentes_c.verificar_pendientes(textos)

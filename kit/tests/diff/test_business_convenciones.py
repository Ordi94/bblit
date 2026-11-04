"""Reglas de negocio del analisis de C que dependen de las convenciones del proyecto."""

import pytest
from psxdecomp.diff import fuentes_c
from psxdecomp.diff.fuentes_c import EstadoFuncion, MarcaAsm
from psxdecomp.dominio import Convenciones, construir_convenciones

POR_DEFECTO = construir_convenciones({})
AJENAS = construir_convenciones(
    {
        "macro_no_coincidente": "SIN_COINCIDIR",
        "macro_ensamblador": "INCLUIR_ENSAMBLADOR",
        "pendiente": r"\APENDIENTE=(\d+)",
        "manuscrita": r"hecha a mano",
    }
)


def asm(funcion: str, macro: str = "INCLUDE_ASM") -> str:
    return f'{macro}("asm/pendientes/a", {funcion});\n'


def bloque(funcion: str, cabecera: str, macro: str = "NON_MATCHING", incluir: str = "INCLUDE_ASM") -> str:
    """Bloque no coincidente con ``cabecera`` justo debajo del ``#ifdef``."""
    return (
        f"#ifdef {macro}\n{cabecera}s32 {funcion}(void)\n{{\n    return 0;\n}}\n#else\n"
        f"{asm(funcion, incluir)}#endif\n"
    )


PENDIENTE = "/* Pendiente: puntuacion 120 con la configuracion versionada. Reparto de registros. */\n"


def verificar(textos: dict[str, str], convenciones: Convenciones = POR_DEFECTO) -> None:
    copia = dict(textos)
    fuentes_c.verificar_pendientes(textos, convenciones)
    assert textos == copia


# --- guardia de pendientes --------------------------------------------------------------------


def test_un_bloque_con_la_linea_pendiente_bajo_el_ifdef_se_acepta() -> None:
    verificar({"src/a.c": bloque("func_A", PENDIENTE)})


def test_un_bloque_sin_comentario_se_rechaza_nombrando_archivo_linea_y_funcion() -> None:
    texto = "int x;\n" + bloque("func_A", "")
    with pytest.raises(ValueError, match=r"src/a\.c:2 func_A") as error:
        verificar({"src/a.c": texto})
    assert "primer comentario bajo '#ifdef NON_MATCHING'" in str(error.value)


def test_el_error_cita_la_expresion_de_pendiente_que_exige_el_proyecto() -> None:
    with pytest.raises(ValueError, match=r"PENDIENTE=") as error:
        verificar({"src/a.c": bloque("func_A", "", "SIN_COINCIDIR", "INCLUIR_ENSAMBLADOR")}, AJENAS)
    assert "SIN_COINCIDIR sin la linea de pendiente" in str(error.value)


def test_el_error_lista_todos_los_bloques_afectados_de_todos_los_archivos() -> None:
    sin = bloque("func_A", "")
    with pytest.raises(ValueError, match=r"3 funcion\(es\) NON_MATCHING") as error:
        verificar({"src/b.c": sin, "src/a.c": sin + bloque("func_B", PENDIENTE) + sin})
    mensaje = str(error.value)
    assert mensaje.index("src/a.c:1 func_A") < mensaje.index("src/b.c:1 func_A")
    assert "func_B" not in mensaje


@pytest.mark.parametrize(
    "cabecera",
    [
        "/* Reparto de registros distinto. */\n",
        "/* Pendiente: puntuacion alta. */\n",
        "/* Nota previa. Pendiente: puntuacion 5. */\n",
    ],
)
def test_un_comentario_que_no_cumple_la_expresion_no_vale(cabecera: str) -> None:
    with pytest.raises(ValueError, match="func_A"):
        verificar({"src/a.c": bloque("func_A", cabecera)})


def test_la_linea_pendiente_antes_del_ifdef_no_vale() -> None:
    with pytest.raises(ValueError, match=r"src/a\.c:2 func_A"):
        verificar({"src/a.c": PENDIENTE + bloque("func_A", "")})


def test_la_linea_pendiente_despues_del_codigo_no_vale() -> None:
    texto = (
        "#ifdef NON_MATCHING\ns32 func_A(void)\n{\n    return 0;\n}\n" + PENDIENTE + "#else\n"
        f"{asm('func_A')}#endif\n"
    )
    with pytest.raises(ValueError, match="func_A"):
        verificar({"src/a.c": texto})


@pytest.mark.parametrize(
    "cabecera",
    [
        "/*\n * Pendiente: puntuacion 350 con la configuracion versionada.\n * Dos lui.\n */\n",
        "// Pendiente: puntuacion 7\n",
    ],
)
def test_la_linea_pendiente_se_acepta_en_comentarios_de_bloque_y_de_linea(cabecera: str) -> None:
    verificar({"src/a.c": bloque("func_A", cabecera)})


def test_un_ifdef_escrito_dentro_de_un_comentario_no_abre_un_bloque() -> None:
    texto = "/*\n#ifdef NON_MATCHING\n*/\nint x;\n"
    assert fuentes_c.bloques_no_coincidentes(texto, POR_DEFECTO) == []
    verificar({"src/a.c": texto})


def test_un_ifdef_sin_rama_de_ensamblador_no_es_un_intento_de_funcion() -> None:
    texto = (
        "#ifdef NON_MATCHING\nint auxiliar;\n#endif\n"
        "#ifdef NON_MATCHING\nint otro;\n#else\nint ajeno;\n#endif\n"
    )
    assert fuentes_c.bloques_no_coincidentes(texto, POR_DEFECTO) == []
    verificar({"src/a.c": texto})


def test_otras_condiciones_dentro_del_bloque_no_cierran_el_bloque_antes_de_tiempo() -> None:
    cabecera = PENDIENTE + "#ifdef OTRA\n#else\n#endif\n"
    texto = bloque("func_A", cabecera) + "#ifndef NON_MATCHING\nint x;\n#endif\n#if 1\n#endif\n"
    assert [b.funcion for b in fuentes_c.bloques_no_coincidentes(texto, POR_DEFECTO)] == ["func_A"]
    verificar({"src/a.c": texto})


def test_un_bloque_anidado_en_otra_condicion_se_comprueba() -> None:
    with pytest.raises(ValueError, match=r"src/a\.c:2 func_A"):
        verificar({"src/a.c": "#if 1\n" + bloque("func_A", "") + "#endif\n"})


def test_dos_bloques_consecutivos_se_comprueban_por_separado() -> None:
    texto = bloque("func_A", PENDIENTE) + bloque("func_B", "")
    with pytest.raises(ValueError, match="func_B") as error:
        verificar({"src/a.c": texto})
    assert "func_A" not in str(error.value)


def test_un_archivo_sin_funciones_en_c_ni_bloques_no_da_error() -> None:
    verificar({"src/vacio.c": "", "src/datos.c": "int tabla[4];\n"})
    verificar({})


# --- puntuacion y motivo ----------------------------------------------------------------------


def test_la_puntuacion_pendiente_se_lee_del_primer_comentario() -> None:
    bloques = fuentes_c.bloques_no_coincidentes(bloque("func_A", PENDIENTE), POR_DEFECTO)
    assert fuentes_c.puntuacion_pendiente(bloques[0], POR_DEFECTO) == 120
    assert fuentes_c.pendiente_declarada(bloques[0], POR_DEFECTO)
    sin = fuentes_c.bloques_no_coincidentes(bloque("func_A", ""), POR_DEFECTO)
    assert fuentes_c.puntuacion_pendiente(sin[0], POR_DEFECTO) is None
    assert not fuentes_c.pendiente_declarada(sin[0], POR_DEFECTO)


def test_los_motivos_son_el_primer_comentario_de_bloque_en_una_linea() -> None:
    motivos = fuentes_c.motivos_no_coincidentes(
        bloque("func_A", "/*\n * Pendiente: puntuacion 9.\n * Dos lui.\n */\n") + bloque("func_B", ""),
        POR_DEFECTO,
    )
    assert motivos == {"func_A": "Pendiente: puntuacion 9. Dos lui."}


def test_el_motivo_se_acota_a_la_longitud_maxima() -> None:
    largo = "/* " + "x" * 2000 + " */\n"
    motivos = fuentes_c.motivos_no_coincidentes(bloque("func_A", largo), POR_DEFECTO)
    assert len(motivos["func_A"]) == fuentes_c.MAX_CARACTERES_MOTIVO


# --- rutinas manuscritas ----------------------------------------------------------------------


def clasificar(texto: str, convenciones: Convenciones = POR_DEFECTO) -> dict[str, MarcaAsm]:
    return fuentes_c.clasificar_include_asm(texto, convenciones)


def test_el_comentario_de_rutina_escrita_a_mano_marca_la_funcion_como_manuscrita() -> None:
    texto = "/* Rutina escrita a mano en el original: copia cinco palabras. */\n" + asm("func_A")
    assert clasificar(texto) == {"func_A": MarcaAsm.MANUSCRITA}


def test_la_variante_con_complemento_tambien_es_manuscrita() -> None:
    texto = "/*\n * Rutina de GTE escrita a mano en el original (marca\n * Handwritten): carga.\n */\n"
    assert clasificar(texto + asm("func_A")) == {"func_A": MarcaAsm.MANUSCRITA}


def test_la_marca_se_reconoce_aunque_el_comentario_la_parta_en_dos_lineas() -> None:
    texto = "/*\n * rutina escrita a mano\n * en el original.\n */\n" + asm("func_A")
    assert clasificar(texto) == {"func_A": MarcaAsm.MANUSCRITA}


def test_un_comentario_con_otra_razon_no_es_manuscrita_pero_si_justifica_el_ensamblador() -> None:
    texto = "/* Se conserva en ensamblador: el compilador asigna otros temporales. */\n" + asm("func_A")
    assert clasificar(texto) == {"func_A": MarcaAsm.JUSTIFICADA}


def test_un_comentario_de_linea_tambien_cuenta_como_comentario_previo() -> None:
    assert clasificar("// Rutina escrita a mano en el original.\n" + asm("func_A")) == {
        "func_A": MarcaAsm.MANUSCRITA
    }


def test_sin_comentario_encima_la_funcion_queda_sin_comentario() -> None:
    assert clasificar(asm("func_A")) == {"func_A": MarcaAsm.SIN_COMENTARIO}
    assert clasificar("int x;\n" + asm("func_A")) == {"func_A": MarcaAsm.SIN_COMENTARIO}


def test_una_linea_en_blanco_entre_el_comentario_y_la_funcion_los_desvincula() -> None:
    texto = "/* Rutina escrita a mano en el original. */\n\n" + asm("func_A")
    assert clasificar(texto) == {"func_A": MarcaAsm.SIN_COMENTARIO}


def test_el_comentario_de_la_funcion_anterior_no_se_hereda() -> None:
    texto = "/* Rutina escrita a mano en el original. */\n" + asm("func_A") + asm("func_B")
    assert clasificar(texto) == {"func_A": MarcaAsm.MANUSCRITA, "func_B": MarcaAsm.SIN_COMENTARIO}


def test_un_comentario_al_final_de_una_linea_de_codigo_no_cuenta_como_comentario_previo() -> None:
    texto = "int x; /* rutina escrita a mano en el original */\n" + asm("func_A")
    assert clasificar(texto) == {"func_A": MarcaAsm.SIN_COMENTARIO}


def test_los_intentos_no_coincidentes_no_se_clasifican() -> None:
    texto = bloque("func_A", PENDIENTE) + asm("func_B")
    assert clasificar(texto) == {"func_B": MarcaAsm.SIN_COMENTARIO}


def test_un_archivo_sin_macros_de_ensamblador_no_tiene_marcas() -> None:
    assert clasificar("s32 f(void)\n{\n    return 0;\n}\n") == {}


# --- convenciones propias de otro proyecto ----------------------------------------------------


def test_las_macros_y_las_frases_de_otro_proyecto_se_reconocen_y_las_del_kit_dejan_de_valer() -> None:
    texto = (
        asm("func_A", "INCLUIR_ENSAMBLADOR")
        + "/* Rutina hecha a mano. */\n"
        + asm("func_B", "INCLUIR_ENSAMBLADOR")
        + bloque("func_C", "/* PENDIENTE=4 */\n", "SIN_COINCIDIR", "INCLUIR_ENSAMBLADOR")
    )
    assert fuentes_c.analizar_fuente(texto, AJENAS) == {
        "func_A": EstadoFuncion.ENSAMBLADOR,
        "func_B": EstadoFuncion.ENSAMBLADOR,
        "func_C": EstadoFuncion.NO_COINCIDENTE,
    }
    assert clasificar(texto, AJENAS) == {"func_A": MarcaAsm.SIN_COMENTARIO, "func_B": MarcaAsm.MANUSCRITA}
    assert fuentes_c.analizar_fuente(texto, POR_DEFECTO) == {"func_C": EstadoFuncion.C}
    verificar({"src/a.c": texto}, AJENAS)


def test_una_funcion_solo_bajo_la_macro_del_proyecto_nombra_ambas_macros_en_el_error() -> None:
    texto = "#ifdef SIN_COINCIDIR\ns32 func_A(void)\n{\n    return 0;\n}\n#endif\n"
    with pytest.raises(
        ValueError, match="'func_A' solo existe bajo SIN_COINCIDIR: falta su INCLUIR_ENSAMBLADOR"
    ):
        fuentes_c.analizar_fuente(texto, AJENAS)


def test_las_directivas_ajenas_o_sin_condicion_abierta_no_producen_bloques() -> None:
    texto = '#include "a.h"\n#define X 1\n#else\n#endif\n'
    assert fuentes_c.bloques_no_coincidentes(texto, POR_DEFECTO) == []

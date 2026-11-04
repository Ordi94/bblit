"""Reglas de negocio del informe: manuscritas aparte, ensamblador sin comentario y pendientes desfasados."""

import json
from pathlib import Path

import pytest
from psxdecomp.cli import main

from progreso.ayudantes import (
    EstadoFuncion,
    MarcaAsm,
    calcular_progreso,
    crear_proyecto_propio,
    escribir,
    leer,
    leer_simbolos,
)

SIMBOLOS = (
    "rutina_a = 0x80010100; // type:func size:0x10\n"
    "rutina_b = 0x80010110; // type:func size:0x44\n"
    "rutina_c = 0x80010160; // type:func size:0x20\n"
    "rutina_d = 0x80010180; // type:func size:0x30\n"
)


def asm(funcion: str) -> str:
    return f'INCLUDE_ASM("ensamblador/pendientes/modulo_a", {funcion});\n'


def test_progreso_lista_aparte_las_manuscritas_con_su_tamano_y_no_las_cuenta_como_c() -> None:
    estados = {
        "src/a.c": {
            "rutina_a": EstadoFuncion.C,
            "rutina_b": EstadoFuncion.ENSAMBLADOR,
            "rutina_c": EstadoFuncion.ENSAMBLADOR,
        }
    }
    marcas = {"src/a.c": {"rutina_b": MarcaAsm.MANUSCRITA, "rutina_c": MarcaAsm.JUSTIFICADA}}
    medido = calcular_progreso(leer_simbolos(SIMBOLOS), estados, None, None, marcas)
    assert medido.manuscritas == (("rutina_b", 0x44),)
    assert medido.sin_comentario == ()
    assert medido.funciones_en_c == 1


def test_progreso_avisa_de_los_include_asm_sin_comentario_solo_en_archivos_con_funciones_en_c() -> None:
    estados = {
        "src/con_c.c": {"rutina_a": EstadoFuncion.C, "rutina_b": EstadoFuncion.ENSAMBLADOR},
        "src/sin_c.c": {"rutina_c": EstadoFuncion.ENSAMBLADOR},
    }
    marcas = {
        "src/con_c.c": {"rutina_b": MarcaAsm.SIN_COMENTARIO},
        "src/sin_c.c": {"rutina_c": MarcaAsm.SIN_COMENTARIO},
    }
    medido = calcular_progreso(leer_simbolos(SIMBOLOS), estados, None, None, marcas)
    assert medido.sin_comentario == (("src/con_c.c", "rutina_b"),)


def test_una_funcion_que_ya_no_esta_en_ensamblador_no_se_lista_como_manuscrita() -> None:
    estados = {"src/a.c": {"rutina_a": EstadoFuncion.C, "rutina_d": EstadoFuncion.NO_COINCIDENTE}}
    marcas = {"src/a.c": {"rutina_a": MarcaAsm.MANUSCRITA, "rutina_d": MarcaAsm.SIN_COMENTARIO}}
    medido = calcular_progreso(leer_simbolos(SIMBOLOS), estados, None, None, marcas)
    assert medido.manuscritas == () and medido.sin_comentario == ()


def test_sin_marcas_el_progreso_no_inventa_categorias() -> None:
    estados = {"src/a.c": {"rutina_a": EstadoFuncion.C, "rutina_b": EstadoFuncion.ENSAMBLADOR}}
    medido = calcular_progreso(leer_simbolos(SIMBOLOS), estados, None)
    assert medido.manuscritas == () and medido.sin_comentario == ()


FUENTE = (
    "int rutina_a(void)\n{\n    return 0;\n}\n"
    "/* Rutina escrita a mano en el original: copia una matriz. */\n"
    + asm("rutina_b")
    + "\n"
    + asm("rutina_c")
)


@pytest.fixture
def repositorio(tmp_path: Path) -> Path:
    propio = crear_proyecto_propio(tmp_path)
    escribir(propio.raiz / "datos" / "simbolos.txt", SIMBOLOS)
    escribir(propio.raiz / "codigo" / "modulo_a.c", FUENTE)
    return propio.raiz


def test_el_documento_de_progreso_trae_la_categoria_manuscritas_y_el_aviso(repositorio: Path) -> None:
    assert main(["progreso", "--sin-readme"], {}, lambda *_: "", raiz=repositorio) == 0
    documento = leer(repositorio / "notas" / "avance.md")
    manuscritas = "## Rutinas manuscritas (siguen en ensamblador por diseño)\n\n- `rutina_b` (68 bytes)"
    aviso = (
        "## `INCLUDE_ASM` sin comentario en archivos con funciones en C\n\n- `rutina_c` (`codigo/modulo_a.c`)"
    )
    assert manuscritas in documento
    assert aviso in documento


def test_el_documento_de_progreso_dice_ninguna_si_no_hay_manuscritas(tmp_path: Path) -> None:
    propio = crear_proyecto_propio(tmp_path)
    escribir(propio.raiz / "codigo" / "modulo_a.c", asm("rutina_a"))
    assert main(["progreso", "--sin-readme"], {}, lambda *_: "", raiz=propio.raiz) == 0
    documento = leer(propio.raiz / "notas" / "avance.md")
    assert "## Rutinas manuscritas (siguen en ensamblador por diseño)\n\nNinguna.\n" in documento
    assert "sin comentario en archivos" not in documento


def test_el_json_de_progreso_expone_manuscritas_y_sin_comentario(repositorio: Path) -> None:
    assert main(["progreso", "--sin-readme"], {}, lambda *_: "", raiz=repositorio) == 0
    datos = json.loads(leer(repositorio / "salida" / "progreso.json"))
    assert datos["manuscritas"] == [{"funcion": "rutina_b", "bytes": 0x44}]
    assert datos["sinComentario"] == [{"archivo": "codigo/modulo_a.c", "funcion": "rutina_c"}]


def test_la_orden_progreso_informa_las_manuscritas_y_avisa_sin_fallar(
    repositorio: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["progreso", "--sin-readme"], {}, lambda *_: "", raiz=repositorio) == 0
    salida = capsys.readouterr()
    assert "manuscritas: 1 rutinas escritas a mano siguen en ensamblador" in salida.out
    assert (
        "aviso: codigo/modulo_a.c: rutina_c sigue en INCLUDE_ASM sin comentario que lo explique" in salida.err
    )


def test_la_orden_progreso_avisa_del_pendiente_que_no_coincide_con_la_ultima_medicion(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    propio = crear_proyecto_propio(tmp_path)
    escribir(
        propio.raiz / "codigo" / "modulo_a.c",
        "#ifdef NON_MATCHING\n/* Pendiente: puntuacion 120 con la configuracion. Reparto de registros. */\n"
        "int rutina_a(void)\n{\n    return 0;\n}\n#else\n" + asm("rutina_a") + "#endif\n",
    )
    medicion = propio.raiz / "salida" / "diff" / "rutina_a.resultado.json"
    escribir(medicion, json.dumps({"funcion": "rutina_a", "puntuacion": 340, "maxLineas": 1024}))
    assert main(["progreso", "--sin-readme"], {}, lambda *_: "", raiz=propio.raiz) == 0
    assert "aviso: codigo/modulo_a.c:1 rutina_a: el comentario Pendiente dice 120" in capsys.readouterr().err

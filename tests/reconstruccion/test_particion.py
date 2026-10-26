"""Particion por subsistema: secciones declaradas, invalidacion de la salida, motivos y subsistemas."""

from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import compilacion as comp
from tools.reconstruccion import dominio, fuentes_c, progreso
from tools.reconstruccion import infraestructura as infra
from tools.reconstruccion.fuentes_c import EstadoFuncion
from tools.reconstruccion.progreso import FuncionSimbolo

from .test_compilacion import (
    SALIDA_OBJDUMP,
    SCRIPT_MIXTO,
    EjecutorC,
    herramientas_base,
    herramientas_compilacion,
    preparar_construccion,
)
from .test_infraestructura import EJECUTABLE, REFERENCIA, Registro

CONFIGURACION: dict[str, Any] = {
    "segments": [
        {
            "name": "main",
            "subsegments": [
                [0x800, "asm", "boot"],
                [0x8C4, "c", "uno"],
                [0x900, "c", "dos"],
                {"start": 0x940, "type": "c", "name": "tres"},
                [0x980, ".rodata", "dos"],
                [0x9C0, ".rdata", "tres"],
                [0xA00, ".data", "uno"],
                [0xA40, "data", "uno"],
                [0xA80, ".rodata", "sin_c"],
                [0xAC0, "rodata", "dos"],
                [0xB00],
                {"start": 0xB40, "type": 7},
                {"start": 0xB80, "type": "bss", "name": "bss"},
            ],
        },
        [0x55800],
    ]
}


def test_secciones_declaradas_une_text_con_los_subsegmentos_con_punto_del_mismo_nombre() -> None:
    declaradas = dominio.secciones_declaradas(CONFIGURACION)
    assert declaradas == {
        "uno": frozenset({".text", ".data"}),
        "dos": frozenset({".text", ".rodata"}),
        "tres": frozenset({".text", ".rodata"}),
    }


@pytest.mark.parametrize(
    "configuracion",
    [
        None,
        [],
        {},
        {"segments": []},
        {"segments": [[0x800]]},
        {"segments": [{"name": "x"}]},
        {"segments": [{"subsegments": 3}]},
    ],
)
def test_secciones_declaradas_rechaza_configuraciones_sin_la_forma_esperada(configuracion: Any) -> None:
    with pytest.raises(ValueError, match=r"falta segments\[0\]\.subsegments"):
        dominio.secciones_declaradas(configuracion)


def test_verificar_solo_texto_acepta_lo_declarado_y_nombra_archivo_y_seccion_en_lo_demas() -> None:
    secciones = {".text": 40, ".rodata": 28, ".data": 0}
    comp.verificar_solo_texto("build/src/uno.c.o", secciones, {".text", ".rodata"})
    with pytest.raises(
        ValueError, match=r"build/src/uno\.c\.o: genera 28 bytes en la seccion inesperada '\.rodata'"
    ):
        comp.verificar_solo_texto("build/src/uno.c.o", secciones, {".text"})
    with pytest.raises(ValueError, match=r"subsegmento '\.rodata' con el nombre del archivo"):
        comp.verificar_solo_texto("build/src/uno.c.o", secciones)


def test_compilar_fuente_acepta_las_secciones_que_declara_el_subsegmento(tmp_path: Path) -> None:
    preparar_construccion(tmp_path, SCRIPT_MIXTO)
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP)
    comp.compilar_fuente(
        tmp_path,
        "src/a.c",
        "build/src/a.c.o",
        herramientas_compilacion(),
        ejecutor,
        secciones_declaradas={".rodata"},
    )
    with pytest.raises(ValueError, match=r"seccion inesperada '.rodata'"):
        comp.compilar_fuente(tmp_path, "src/a.c", "build/src/a.c.o", herramientas_compilacion(), ejecutor)


def test_construir_mixto_aplica_a_cada_c_las_secciones_de_su_nombre(tmp_path: Path) -> None:
    preparar_construccion(tmp_path, SCRIPT_MIXTO)
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP)
    destino = comp.construir_mixto(
        tmp_path,
        REFERENCIA,
        herramientas_base(),
        herramientas_compilacion,
        ejecutor,
        declaradas={"a": frozenset({".text", ".rodata"})},
    )
    assert destino.read_bytes() == EJECUTABLE
    with pytest.raises(ValueError, match=r"a.c.o: genera 29 bytes en la seccion inesperada '.rodata'"):
        comp.construir_mixto(
            tmp_path,
            REFERENCIA,
            herramientas_base(),
            herramientas_compilacion,
            ejecutor,
            declaradas={"otro": {".rodata"}},
        )


def test_leer_secciones_declaradas(tmp_path: Path) -> None:
    assert infra.leer_secciones_declaradas(tmp_path) == {}
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "splat.yaml").write_text(
        "segments:\n  - subsegments:\n      - [0x8C4, c, uno]\n", encoding="utf-8"
    )
    assert infra.leer_secciones_declaradas(tmp_path) == {"uno": frozenset({".text"})}
    (tmp_path / "config" / "splat.yaml").write_text("a: [b", encoding="utf-8")
    with pytest.raises(ValueError, match=r"config/splat.yaml no es YAML valido"):
        infra.leer_secciones_declaradas(tmp_path)


def test_salidas_de_enlace_e_invalidar_salida(tmp_path: Path) -> None:
    salidas = infra.salidas_de_enlace("PRUEBA.EXE")
    assert salidas == ("build/PRUEBA.EXE", "build/SLUS_008.bin", "build/SLUS_008.elf", "build/SLUS_008.map")
    assert infra.invalidar_salida(tmp_path, "PRUEBA.EXE") == []
    (tmp_path / "build").mkdir()
    for ruta in salidas:
        (tmp_path / ruta).write_bytes(b"x")
    (tmp_path / "build" / "ajeno.bin").write_bytes(b"a")
    assert infra.invalidar_salida(tmp_path, "PRUEBA.EXE") == list(salidas)
    assert [p.name for p in (tmp_path / "build").iterdir()] == ["ajeno.bin"]


def test_un_build_que_falla_a_mitad_no_deja_la_salida_anterior(tmp_path: Path) -> None:
    preparar_construccion(tmp_path, SCRIPT_MIXTO)
    comp.construir_mixto(
        tmp_path,
        REFERENCIA,
        herramientas_base(),
        herramientas_compilacion,
        EjecutorC(secciones=SALIDA_OBJDUMP.replace("0000001d", "00000000")),
    )
    assert (tmp_path / "build" / "PRUEBA.EXE").is_file()
    with pytest.raises(ValueError, match="seccion inesperada"):
        comp.construir_mixto(
            tmp_path,
            REFERENCIA,
            herramientas_base(),
            herramientas_compilacion,
            EjecutorC(secciones=SALIDA_OBJDUMP),
        )
    for ruta in infra.salidas_de_enlace("PRUEBA.EXE"):
        assert not (tmp_path / ruta).exists(), ruta
    (tmp_path / infra.SCRIPT_ENLAZADOR).unlink()
    (tmp_path / "build" / "PRUEBA.EXE").write_bytes(b"viejo")
    with pytest.raises(FileNotFoundError, match="ejecute primero 'split'"):
        infra.construir(tmp_path, REFERENCIA, herramientas_base(), Registro())
    assert not (tmp_path / "build" / "PRUEBA.EXE").exists()


def test_motivos_no_coincidentes_toma_el_primer_comentario_de_cada_bloque() -> None:
    texto = (
        "#ifdef NON_MATCHING\n/*\n * Primera linea.\n *\n * Segunda linea.\n */\n"
        "void func_A(void)\n{\n}\n#else\n"
        'INCLUDE_ASM("asm/nonmatchings/a", func_A);\n#endif\n'
        "#ifdef NON_MATCHING\nvoid func_B(void)\n{\n}\n#else\n"
        'INCLUDE_ASM("asm/nonmatchings/a", func_B);\n#endif\n'
        "#ifdef NON_MATCHING\n/* " + "x" * 700 + " */\nvoid func_C(void)\n{\n}\n#else\n"
        'INCLUDE_ASM("asm/nonmatchings/a", func_C);\n#endif\n'
    )
    motivos = fuentes_c.motivos_no_coincidentes(texto)
    assert motivos["func_A"] == "Primera linea. Segunda linea."
    assert "func_B" not in motivos
    assert motivos["func_C"] == "x" * fuentes_c.MAX_CARACTERES_MOTIVO
    assert fuentes_c.motivos_no_coincidentes("int x;\n") == {}


@pytest.mark.parametrize(
    ("archivo", "subsistema"),
    [
        ("src/graficos_y_gte.c", "graficos_y_gte"),
        ("src/graficos_y_gte_10.c", "graficos_y_gte"),
        ("src/logica_de_niveles_3.c", "logica_de_niveles"),
        ("src/tarjeta_de_memoria.c", "tarjeta_de_memoria"),
        ("src/a_2b.c", "a_2b"),
    ],
)
def test_subsistema_de_quita_solo_el_sufijo_numerico(archivo: Any, subsistema: Any) -> None:
    assert progreso.subsistema_de(archivo) == subsistema


def test_el_progreso_suma_los_archivos_de_cada_subsistema_y_conserva_los_motivos() -> None:
    simbolos = [
        FuncionSimbolo("func_80014AC4", 0x80014AC4, 0x10),
        FuncionSimbolo("func_80014AD4", 0x80014AD4, 0x20),
        FuncionSimbolo("func_80014AF4", 0x80014AF4, 0x30),
        FuncionSimbolo("func_80014B24", 0x80014B24, 0x40),
    ]
    estados = {
        "src/g.c": {"func_80014AC4": EstadoFuncion.C},
        "src/g_2.c": {
            "func_80014AD4": EstadoFuncion.NO_COINCIDENTE,
            "func_80014AF4": EstadoFuncion.ENSAMBLADOR,
        },
        "src/otro.c": {"func_80014B24": EstadoFuncion.ENSAMBLADOR},
    }
    medido = progreso.calcular_progreso(
        simbolos, estados, None, {"func_80014AD4": "motivo", "func_ajena": "no"}
    )
    assert [
        (s.nombre, s.archivos, s.c, s.no_coincidentes, s.ensamblador, s.bytes_c, s.bytes_total)
        for s in medido.subsistemas
    ] == [
        ("g", 2, 1, 1, 1, 0x10, 0x60),
        ("otro", 1, 0, 0, 1, 0, 0x40),
    ]
    assert medido.motivos == (("func_80014AD4", "motivo"),)
    datos = progreso.a_json(medido)
    assert datos["motivosNoCoincidentes"] == {"func_80014AD4": "motivo"}
    assert datos["subsistemas"][0] == {
        "subsistema": "g",
        "archivos": 2,
        "funcionesC": 1,
        "noCoincidentes": 1,
        "ensamblador": 1,
        "bytesC": 0x10,
        "bytesTotal": 0x60,
    }
    markdown = progreso.a_markdown(medido)
    assert "| g | 2 | 1 | 1 | 1 | 16 | 96 |" in markdown
    assert "- `func_80014AD4`: motivo" in markdown


def test_generar_progreso_lee_los_motivos_de_los_fuentes(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "symbols.txt").write_text(
        "func_80014AC4 = 0x80014AC4; // type:func size:0x10\n", encoding="utf-8"
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.c").write_text(
        "#ifdef NON_MATCHING\n/* Intento a medias. */\nvoid func_80014AC4(void)\n{\n}\n#else\n"
        'INCLUDE_ASM("asm/nonmatchings/a", func_80014AC4);\n#endif\n',
        encoding="utf-8",
    )
    progreso.generar_progreso(tmp_path)
    assert "- `func_80014AC4`: Intento a medias." in (tmp_path / "docs" / "PROGRESO.md").read_text(
        encoding="utf-8"
    )

import json
from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import progreso
from tools.reconstruccion.fuentes_c import EstadoFuncion
from tools.reconstruccion.progreso import FuncionSimbolo, ResumenZona

SIMBOLOS = """\
// comentario
__main = 0x80014A00; // type:func size:0x8
func_80014A08 = 0x80014A08; // type:func size:0xAC
func_80014AC4 = 0x80014AC4; // type:func size:0x10
func_80014AD4 = 0x80014AD4; // type:func size:0x20
func_80014AF4 = 0x80014AF4; // type:func size:0x30
func_80045DA0 = 0x80045DA0; // type:func size:0x34
D_80069698 = 0x80069698; // size:0x4
D_80069700 = 0x80069700; // type:u32
"""


def tabla() -> list[FuncionSimbolo]:
    return progreso.leer_simbolos(SIMBOLOS)


def test_leer_simbolos_toma_solo_funciones_con_su_tamano() -> None:
    assert [(f.nombre, f.direccion, f.tamano) for f in tabla()] == [
        ("__main", 0x80014A00, 8),
        ("func_80014A08", 0x80014A08, 0xAC),
        ("func_80014AC4", 0x80014AC4, 0x10),
        ("func_80014AD4", 0x80014AD4, 0x20),
        ("func_80014AF4", 0x80014AF4, 0x30),
        ("func_80045DA0", 0x80045DA0, 0x34),
    ]


@pytest.mark.parametrize("linea", ["f = 0x80014AC4; // type:func", "f = 0x80014AC4; // type:func size:0x0"])
def test_leer_simbolos_exige_un_tamano_valido_y_nombra_la_linea(linea: Any) -> None:
    with pytest.raises(ValueError, match="linea 2: 'f' no declara un size valido"):
        progreso.leer_simbolos("// x\n" + linea + "\n")


def test_combinar_simbolos_el_ultimo_manda_por_direccion_y_ordena() -> None:
    base = [FuncionSimbolo("grande", 0x100, 0x40), FuncionSimbolo("otra", 0x200, 4)]
    extra = [FuncionSimbolo("grande", 0x100, 0x10), FuncionSimbolo("nueva", 0x110, 0x30)]
    assert progreso.combinar_simbolos(base, extra) == [
        FuncionSimbolo("grande", 0x100, 0x10),
        FuncionSimbolo("nueva", 0x110, 0x30),
        FuncionSimbolo("otra", 0x200, 4),
    ]
    assert progreso.combinar_simbolos() == []


@pytest.mark.parametrize(
    ("direccion", "zona"),
    [
        (0x80014A00, "arranque"),
        (0x80014AC3, "arranque"),
        (0x80014AC4, "juego"),
        (0x80045D9F, "juego"),
        (0x80045DA0, "libreria"),
        (0x8005DE9F, "libreria"),
        (0x8005DEA0, "otra"),
    ],
)
def test_zona_de_respeta_los_limites_exactos(direccion: Any, zona: Any) -> None:
    assert progreso.zona_de(direccion) == zona


ESTADOS = {
    "src/a.c": {
        "func_80014AC4": EstadoFuncion.C,
        "func_80014AD4": EstadoFuncion.NO_COINCIDENTE,
        "func_80014AF4": EstadoFuncion.ENSAMBLADOR,
        "ayudante": EstadoFuncion.C,
        "func_sin_tabla": EstadoFuncion.ENSAMBLADOR,
    },
    "src/b.c": {"func_80045DA0": EstadoFuncion.C},
}


def test_calcular_progreso_cuenta_por_zona_archivo_y_estado() -> None:
    p = progreso.calcular_progreso(tabla(), ESTADOS, glabel_en_asm=3)
    assert p.arranque == ResumenZona(2, 8 + 0xAC)
    assert p.juego == ResumenZona(3, 0x10 + 0x20 + 0x30)
    assert p.librerias == ResumenZona(1, 0x34)
    assert p.c_juego == ResumenZona(1, 0x10)
    assert p.c_librerias == ResumenZona(1, 0x34)
    assert p.no_coincidentes == ("func_80014AD4",)
    assert p.auxiliares == ("ayudante",)
    assert p.sin_simbolo == ("func_sin_tabla",)
    assert [
        (a.archivo, a.c, a.no_coincidentes, a.ensamblador, a.bytes_c, a.bytes_total) for a in p.archivos
    ] == [
        ("src/a.c", 1, 1, 1, 0x10, 0x60),
        ("src/b.c", 1, 0, 0, 0x34, 0x34),
    ]
    assert p.funciones_totales == 6
    assert p.funciones_en_c == 2
    assert p.porcentaje_bytes_juego == round(100 * 0x10 / 0x60, 2)
    assert p.coherente is False


def test_coherencia_con_el_ensamblador() -> None:
    sin_c = progreso.calcular_progreso(tabla(), {}, glabel_en_asm=6)
    assert sin_c.coherente is True
    assert progreso.calcular_progreso(tabla(), {}, glabel_en_asm=None).coherente is None
    asm_y_c = progreso.calcular_progreso(tabla(), ESTADOS, glabel_en_asm=4)
    assert asm_y_c.coherente is True


def test_porcentaje_sin_codigo_del_juego_es_cero() -> None:
    p = progreso.calcular_progreso([], {}, glabel_en_asm=0)
    assert p.porcentaje_bytes_juego == 0.0
    assert p.funciones_totales == 0


def test_a_json_usa_camel_case_y_refleja_los_conteos() -> None:
    p = progreso.calcular_progreso(tabla(), ESTADOS, glabel_en_asm=4)
    datos = progreso.a_json(p)
    assert datos["totales"] == {
        "arranque": {"funciones": 2, "bytes": 8 + 0xAC},
        "juego": {"funciones": 3, "bytes": 0x60},
        "librerias": {"funciones": 1, "bytes": 0x34},
        "funciones": 6,
    }
    assert datos["descompiladas"]["juego"] == {"funciones": 1, "bytes": 0x10}
    assert datos["descompiladas"]["funciones"] == 2
    assert datos["noCoincidentes"] == ["func_80014AD4"]
    assert datos["archivos"][0] == {
        "archivo": "src/a.c",
        "funcionesC": 1,
        "noCoincidentes": 1,
        "ensamblador": 1,
        "bytesC": 0x10,
        "bytesTotal": 0x60,
    }
    assert datos["coherencia"] == {
        "glabelEnAsm": 4,
        "funcionesEnC": 2,
        "funcionesTotales": 6,
        "coincide": True,
    }
    assert json.loads(json.dumps(datos)) == datos


def test_a_markdown_incluye_resumen_tabla_por_archivo_y_listas() -> None:
    texto = progreso.a_markdown(progreso.calcular_progreso(tabla(), ESTADOS, glabel_en_asm=4))
    assert texto.endswith("\n") and "\r" not in texto
    assert "| Código del juego | 3 | 96 | 1 | 16 |" in texto
    assert "Bytes de código del juego descompilados: 16 de 96 (16.67 %)." in texto
    assert "Funciones marcadas `NON_MATCHING`: 1." in texto
    assert (
        "Coherencia con el ensamblador: correcta (4 `glabel` en `asm/` + 2 en C = 6; la tabla declara 6)."
        in texto
    )
    assert "| `src/a.c` | 1 | 1 | 1 | 16 | 96 |" in texto
    assert "- `func_80014AD4`" in texto
    assert "## Ayudantes definidos en C" in texto and "- `ayudante`" in texto
    assert "## Menciones sin símbolo de función" in texto and "- `func_sin_tabla`" in texto


def test_a_markdown_en_los_casos_vacios_y_de_coherencia_rota_o_sin_medir() -> None:
    vacio = progreso.a_markdown(progreso.calcular_progreso(tabla(), {}, glabel_en_asm=None))
    assert "no medida (ejecute `split`)" in vacio
    assert "Ninguna." in vacio
    assert "Ayudantes" not in vacio and "Menciones" not in vacio
    rota = progreso.a_markdown(progreso.calcular_progreso(tabla(), {}, glabel_en_asm=1))
    assert (
        "Coherencia con el ensamblador: ROTA (1 `glabel` en `asm/` + 0 en C = 1; la tabla declara 6)." in rota
    )


def escribir(ruta: Path, texto: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


def test_contar_glabel_ignora_macros_matchings_y_otras_herramientas(tmp_path: Path) -> None:
    assert progreso.contar_glabel(tmp_path) is None
    escribir(tmp_path / "asm" / "boot.s", "glabel a\n  .L1:\nglabel b\nendlabel b\n")
    escribir(tmp_path / "asm" / "nonmatchings" / "x" / "f.s", "glabel f\ndlabel d\nalabel e\n")
    escribir(tmp_path / "asm" / "include" / "macro.inc", ".macro glabel label\nglabel x\n")
    escribir(tmp_path / "asm" / "matchings" / "x" / "g.s", "glabel g\n")
    escribir(tmp_path / "asm" / "overlay" / "a" / "h.s", "glabel h\n")
    escribir(tmp_path / "asm" / "data" / "data.s", "dlabel D_1\n")
    assert progreso.contar_glabel(tmp_path) == 3


def repo_progreso(raiz: Path) -> None:
    escribir(raiz / "config" / "symbols.txt", SIMBOLOS)
    escribir(
        raiz / "src" / "a.c",
        'INCLUDE_ASM("asm/nonmatchings/a", func_80014AD4);\n'
        "s32 func_80014AC4(void)\n{\n    return 0;\n}\n"
        'INCLUDE_ASM("asm/nonmatchings/a", func_80014AF4);\n',
    )
    escribir(raiz / "asm" / "boot.s", "glabel __main\nglabel func_80014A08\n")
    escribir(raiz / "asm" / "nonmatchings" / "a" / "f.s", "glabel func_80014AD4\nglabel func_80014AF4\n")
    escribir(raiz / "asm" / "libs.s", "glabel func_80045DA0\n")


def test_generar_progreso_escribe_documento_y_json_deterministas(tmp_path: Path) -> None:
    repo_progreso(tmp_path)
    p = progreso.generar_progreso(tmp_path)
    assert p.c_juego == ResumenZona(1, 0x10) and p.coherente is True
    documento = (tmp_path / "docs" / "PROGRESO.md").read_text(encoding="utf-8")
    datos = json.loads((tmp_path / "build" / "progreso.json").read_text(encoding="utf-8"))
    assert datos["descompiladas"]["funciones"] == 1
    assert "| `src/a.c` | 1 | 0 | 2 | 16 | 96 |" in documento
    progreso.generar_progreso(tmp_path)
    assert (tmp_path / "docs" / "PROGRESO.md").read_text(encoding="utf-8") == documento


def test_generar_progreso_aplica_los_simbolos_adicionales_sobre_la_tabla(tmp_path: Path) -> None:
    repo_progreso(tmp_path)
    escribir(
        tmp_path / "config" / "simbolos_adicionales.txt",
        "func_80014AC4 = 0x80014AC4; // type:func size:0x8\n",
    )
    assert progreso.generar_progreso(tmp_path).c_juego == ResumenZona(1, 8)


def test_generar_progreso_sin_tabla_o_con_tabla_excesiva(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(FileNotFoundError, match=r"falta config/symbols.txt"):
        progreso.generar_progreso(tmp_path)
    repo_progreso(tmp_path)
    monkeypatch.setattr(progreso, "MAX_BYTES_SIMBOLOS", 10)
    with pytest.raises(ValueError, match=r"symbols.txt excede el tamano permitido"):
        progreso.generar_progreso(tmp_path)


def test_generar_progreso_sin_asm_no_mide_la_coherencia(tmp_path: Path) -> None:
    escribir(tmp_path / "config" / "symbols.txt", SIMBOLOS)
    p = progreso.generar_progreso(tmp_path)
    assert p.glabel_en_asm is None and p.coherente is None and p.archivos == ()

"""Reglas de negocio del build mixto C + asm: configuracion, fuentes versionadas y ciclo real."""

import re
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from tools.reconstruccion import cli, progreso
from tools.reconstruccion.fuentes_c import EstadoFuncion, analizar_fuentes
from tools.reconstruccion.infraestructura import listar_fuentes_c

from .test_business_reconstruccion import RAIZ_REPO, SHA256_ORIGINAL, entorno_real, sha256

COINCIDENTES = ("func_8002FA38", "func_8002FB18", "func_80036204")
NO_COINCIDENTES = ("func_8002F990", "func_80030D60")


@pytest.fixture(scope="module")
def estados() -> Any:
    return analizar_fuentes(listar_fuentes_c(RAIZ_REPO))


def plano(estados: Any) -> dict[str, EstadoFuncion]:
    return {nombre: estado for archivo in estados.values() for nombre, estado in archivo.items()}


def test_splat_declara_ocho_archivos_c_contiguos_que_cubren_el_codigo_del_juego() -> None:
    config = yaml.safe_load((RAIZ_REPO / "config" / "splat.yaml").read_text(encoding="utf-8"))
    sub = [s for s in config["segments"][0]["subsegments"] if isinstance(s, list)]
    c = [s for s in sub if s[1] == "c"]
    assert len(c) == 8
    assert c[0][0] == 0x800 + (0x80014AC4 - 0x80014A00)
    fin_juego = 0x800 + (0x80045DA0 - 0x80014A00)
    assert [s for s in sub if s[1] == "asm"][-1][0] == fin_juego
    assert [s[0] for s in c] == sorted(s[0] for s in c)
    for desplazamiento, _, nombre in c:
        assert nombre == f"code_{0x80014A00 + desplazamiento - 0x800:08X}"
        assert (RAIZ_REPO / "src" / f"{nombre}.c").is_file()
    assert config["options"]["subalign"] == 4
    assert config["options"]["disassemble_all"] is True
    assert config["options"]["auto_decompile_empty_functions"] is False


def test_las_funciones_que_coinciden_estan_en_c_y_los_intentos_bajo_non_matching(estados: Any) -> None:
    todos = plano(estados)
    for nombre in COINCIDENTES:
        assert todos[nombre] is EstadoFuncion.C, nombre
    for nombre in NO_COINCIDENTES:
        assert todos[nombre] is EstadoFuncion.NO_COINCIDENTE, nombre
    assert sum(1 for e in todos.values() if e is EstadoFuncion.C) == 3


def test_los_simbolos_adicionales_reparten_exactamente_la_funcion_fundida() -> None:
    base = progreso.leer_simbolos((RAIZ_REPO / "config" / "symbols.txt").read_text(encoding="utf-8"))
    texto_extra = (RAIZ_REPO / "config" / "simbolos_adicionales.txt").read_text(encoding="utf-8")
    extra = progreso.leer_simbolos(texto_extra)
    fundida = next(f for f in base if f.nombre == "func_8002F9F8")
    fin = fundida.direccion + fundida.tamano
    partes = [f for f in progreso.combinar_simbolos(extra) if fundida.direccion <= f.direccion < fin]
    cursor = fundida.direccion
    for parte in partes:
        assert parte.direccion == cursor, "las partes deben ser contiguas"
        cursor += parte.tamano
    assert cursor == fin
    por_nombre = {f.nombre: f for f in extra}
    assert (por_nombre["func_8002FA38"].tamano, por_nombre["func_8002FB18"].tamano) == (0x28, 0x20)
    assert por_nombre["func_80030D60"].tamano == 0x44


def test_las_cabeceras_son_c89_y_definen_los_tipos_y_la_macro() -> None:
    comun = (RAIZ_REPO / "include" / "common.h").read_text(encoding="utf-8")
    macro = (RAIZ_REPO / "include" / "macro.h").read_text(encoding="utf-8")
    for tipo in ("u8", "u16", "u32", "s8", "s16", "s32", "vu8", "vu16", "vu32"):
        assert re.search(rf"\b{tipo};", comun), tipo
    assert "NULL" in comun and "#define INCLUDE_ASM(FOLDER, NAME)" in macro
    fuentes = (p.read_text(encoding="utf-8") for p in (RAIZ_REPO / "src").glob("*.c"))
    for texto in (comun, macro, *fuentes):
        sin_cadenas = re.sub(r'"[^"\n]*"', '""', texto)
        assert "//" not in sin_cadenas, "GCC 2.8.1 no admite comentarios de linea"


def test_el_repositorio_no_contiene_rutas_absolutas_de_ninguna_maquina() -> None:
    absoluta = re.compile(r"\b[A-Za-z]:[\\/]+(?:Users|Documents and Settings)[\\/]", re.IGNORECASE)
    archivos = [*(RAIZ_REPO / "src").glob("*.c"), *(RAIZ_REPO / "include").glob("*.h")]
    archivos += [RAIZ_REPO / "docs" / n for n in ("DESCOMPILACION.md", "PROGRESO.md", "TOOLCHAIN.md")]
    archivos += [RAIZ_REPO / "config" / "simbolos_adicionales.txt", RAIZ_REPO / "config" / "splat.yaml"]
    archivos += sorted((RAIZ_REPO / "tools" / "reconstruccion").glob("*.py"))
    for archivo in archivos:
        assert not absoluta.search(archivo.read_text(encoding="utf-8")), archivo.name


def test_las_constantes_de_zona_coinciden_con_el_mapa_de_memoria() -> None:
    mapa = (RAIZ_REPO / "docs" / "MAPA_MEMORIA.md").read_text(encoding="utf-8")
    for valor in (progreso.INICIO_JUEGO, progreso.INICIO_LIBRERIAS, progreso.FIN_LIBRERIAS):
        assert f"0x{valor:08X}" in mapa


@pytest.fixture
def repo_mixto(tmp_path: Path) -> Any:
    rutas, _ = entorno_real(tmp_path)
    raiz = tmp_path / "repo mixto (prueba)"
    shutil.copytree(RAIZ_REPO / "config", raiz / "config", ignore=shutil.ignore_patterns("local.toml"))
    for carpeta in ("include", "src"):
        shutil.copytree(RAIZ_REPO / carpeta, raiz / carpeta)
    return raiz, {"BBLIT_DISC": str(rutas.disc), "BBLIT_TOOLCHAIN": str(rutas.toolchain)}


def test_ciclo_real_con_tres_funciones_en_c_reproduce_el_ejecutable_y_discrimina(
    repo_mixto: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = repo_mixto
    assert cli.main(["split"], variables, raiz) == 0
    fuentes = {p.name: sha256(p) for p in (raiz / "src").glob("*.c")}
    asm_antes = {str(p): sha256(p) for p in (raiz / "asm").rglob("*.s")}
    assert cli.main(["split"], variables, raiz) == 0
    assert {str(p): sha256(p) for p in (raiz / "asm").rglob("*.s")} == asm_antes
    assert {p.name: sha256(p) for p in (raiz / "src").glob("*.c")} == fuentes

    assert cli.main(["build"], variables, raiz) == 0
    assert sha256(raiz / "build" / "SLUS_008.38") == SHA256_ORIGINAL
    capsys.readouterr()
    assert cli.main(["verify"], variables, raiz) == 0
    assert capsys.readouterr().out.startswith("OK ")

    assert cli.main(["diff", "func_80036204"], variables, raiz) == 0
    assert "puntuacion 0" in capsys.readouterr().out
    assert cli.main(["diff", "func_80030D60"], variables, raiz) == 1
    assert re.search(r"puntuacion [1-9]\d*\n$", capsys.readouterr().out)
    assert cli.main(["diff", "func_80014BA0"], variables, raiz) == 1
    assert "'func_80014BA0' sigue en INCLUDE_ASM" in capsys.readouterr().err

    capsys.readouterr()
    assert cli.main(["progreso"], variables, raiz) == 0
    resumen = capsys.readouterr().out
    assert resumen.startswith("progreso: 3 funciones del juego en C de ")
    assert "2 NON_MATCHING" in resumen
    medido = progreso.generar_progreso(raiz)
    assert medido.coherente is True
    assert medido.glabel_en_asm is not None and medido.glabel_en_asm + 3 == medido.funciones_totales
    assert medido.c_juego.bytes == 0x28 + 0x20 + 0x4C

    (raiz / "asm" / "overlay").mkdir()
    (raiz / "asm" / "overlay" / "ajeno.s").write_text("x", encoding="utf-8")
    assert cli.main(["clean"], variables, raiz) == 0
    assert (raiz / "asm" / "overlay" / "ajeno.s").is_file()
    assert not (raiz / "asm" / "boot.s").exists()


def test_una_funcion_con_datos_no_se_cuela_en_el_ejecutable(
    repo_mixto: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = repo_mixto
    assert cli.main(["split"], variables, raiz) == 0
    destino = raiz / "src" / "code_80044588.c"
    destino.write_text(destino.read_text(encoding="utf-8") + "\ns32 D_80061238 = 5;\n", encoding="utf-8")
    assert cli.main(["build"], variables, raiz) == 1
    capturado = capsys.readouterr()
    assert "code_80044588.c.o: genera 4 bytes en la seccion '.data'" in capturado.err
    assert not (raiz / "build" / "SLUS_008.38").exists()

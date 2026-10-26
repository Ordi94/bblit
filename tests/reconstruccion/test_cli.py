import importlib
import json
import runpy
import sys
from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import cli
from tools.reconstruccion import infraestructura as infra

from tests.toolchain.ayudantes import bloque_componente, lock_de

from .test_compilacion import SALIDA_OBJDUMP, EjecutorC
from .test_diff import ASM_FUNCION, EjecutorDiff
from .test_gp import EjecutorEnlace
from .test_infraestructura import EJECUTABLE, REFERENCIA, Registro, referencia_json
from .test_variantes import EjecutorVariantes, crear_repo, crear_variantes


@pytest.fixture
def entorno_repo(tmp_path: Path) -> Any:
    raiz = tmp_path / "repo"
    (raiz / "config").mkdir(parents=True)
    (raiz / "config" / "ejecutable.json").write_text(json.dumps(referencia_json()), encoding="utf-8")
    bloque = bloque_componente(
        b"x", archivos_clave={"as": "bin/as.exe", "ld": "bin/ld.exe", "objcopy": "bin/objcopy.exe"}
    )
    (raiz / "config" / "toolchain.lock.json").write_text(
        json.dumps(lock_de(**{"binutils-mipsel": bloque})), encoding="utf-8"
    )
    herramientas = tmp_path / "tc" / "binutils-mipsel" / "bin"
    herramientas.mkdir(parents=True)
    for nombre in ("as.exe", "ld.exe", "objcopy.exe"):
        (herramientas / nombre).write_bytes(b"")
    disco = tmp_path / "disco (copia)"
    (disco / "fs").mkdir(parents=True)
    (disco / "fs" / "PRUEBA.EXE").write_bytes(EJECUTABLE)
    variables = {"BBLIT_DISC": str(disco), "BBLIT_TOOLCHAIN": str(tmp_path / "tc")}
    return raiz, variables


def ejecutar_cli(raiz: Any, variables: Any, *argv: Any, ejecutor: Any = None) -> Any:
    return cli.main(list(argv), variables, raiz, ejecutor or Registro())


def test_flujo_completo_split_build_verify_clean(
    entorno_repo: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = entorno_repo
    assert ejecutar_cli(raiz, variables, "split") == 0
    assert capsys.readouterr().out == "split completado: asm/ y script del enlazador generados\n"
    (raiz / "asm" / "data").mkdir()
    (raiz / "asm" / "data" / "datos.s").write_text("d", encoding="utf-8")
    assert ejecutar_cli(raiz, variables, "build") == 0
    assert capsys.readouterr().out == f"build completado: build/PRUEBA.EXE sha256={REFERENCIA.sha256}\n"
    assert ejecutar_cli(raiz, variables, "verify") == 0
    assert capsys.readouterr().out == f"OK esperado={REFERENCIA.sha256} obtenido={REFERENCIA.sha256}\n"
    assert ejecutar_cli(raiz, variables, "clean") == 0
    assert capsys.readouterr().out.startswith("eliminado: asm, expected, build/")
    assert ejecutar_cli(raiz, variables, "clean") == 0
    assert capsys.readouterr().out == "eliminado: nada que eliminar\n"


def test_verify_con_huellas_distintas_devuelve_uno(
    entorno_repo: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = entorno_repo
    (raiz / "build").mkdir()
    (raiz / "build" / "PRUEBA.EXE").write_bytes(EJECUTABLE[:-1] + b"\xff")
    assert ejecutar_cli(raiz, variables, "verify") == 1
    salida = capsys.readouterr().out
    assert salida.startswith("FAIL esperado=")
    assert "primera diferencia en el desplazamiento 0x80F (cuerpo)" in salida


def test_disco_por_argumento_y_por_local_toml(
    entorno_repo: Any, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    raiz, variables = entorno_repo
    (raiz / "build").mkdir()
    (raiz / "build" / "PRUEBA.EXE").write_bytes(EJECUTABLE)
    disco = variables["BBLIT_DISC"]
    assert ejecutar_cli(raiz, {}, "--disc", disco, "verify") == 0
    (raiz / "config" / "local.toml").write_text(
        '[rutas]\ndisc = "' + Path(disco).as_posix() + '"\n', encoding="utf-8"
    )
    assert ejecutar_cli(raiz, {}, "verify") == 0
    capsys.readouterr()


def test_sin_disco_configurado_el_error_es_claro(
    entorno_repo: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, _ = entorno_repo
    (raiz / "build").mkdir()
    (raiz / "build" / "PRUEBA.EXE").write_bytes(EJECUTABLE)
    assert ejecutar_cli(raiz, {}, "verify") == 1
    assert capsys.readouterr().err == (
        "error: falta la ubicacion del disco: defina BBLIT_DISC, --disc o 'disc' en config/local.toml\n"
    )


def test_split_con_herramientas_sin_instalar(entorno_repo: Any, capsys: pytest.CaptureFixture[str]) -> None:
    raiz, variables = entorno_repo
    (Path(variables["BBLIT_TOOLCHAIN"]) / "binutils-mipsel" / "bin" / "ld.exe").unlink()
    assert ejecutar_cli(raiz, variables, "split") == 1
    assert "'ld' no esta instalado" in capsys.readouterr().err


def test_build_sin_split_previo(entorno_repo: Any, capsys: pytest.CaptureFixture[str]) -> None:
    raiz, variables = entorno_repo
    assert ejecutar_cli(raiz, variables, "build") == 1
    assert capsys.readouterr().err == "error: falta el script del enlazador: ejecute primero 'split'\n"


def test_fallo_de_una_herramienta_se_informa_sin_traza(
    entorno_repo: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = entorno_repo

    def falla(comando: Any, directorio: Any, timeout_s: Any) -> None:
        raise infra.ProcesoError("splat.exe: termino con codigo 1")

    assert ejecutar_cli(raiz, variables, "split", ejecutor=falla) == 1
    assert capsys.readouterr().err == "error: splat.exe: termino con codigo 1\n"


def test_referencia_ausente(entorno_repo: Any, capsys: pytest.CaptureFixture[str]) -> None:
    raiz, variables = entorno_repo
    (raiz / "config" / "ejecutable.json").unlink()
    assert ejecutar_cli(raiz, variables, "clean") == 1
    assert "no se encontro config/ejecutable.json" in capsys.readouterr().err


def test_orden_obligatoria() -> None:
    with pytest.raises(SystemExit):
        cli.main([])


def test_el_entorno_por_defecto_es_os_environ(
    entorno_repo: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = entorno_repo
    for clave, valor in variables.items():
        monkeypatch.setenv(clave, valor)
    (raiz / "build").mkdir()
    (raiz / "build" / "PRUEBA.EXE").write_bytes(EJECUTABLE)
    assert cli.main(["verify"], raiz=raiz) == 0


def test_script_tools_build_expone_main_y_agrega_la_raiz_al_camino(monkeypatch: pytest.MonkeyPatch) -> None:
    ruta = Path(cli.__file__).resolve().parents[1] / "build.py"
    monkeypatch.setattr(sys, "argv", ["build.py", "clean-no-existe"])
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p != str(ruta.parents[1])])
    with pytest.raises(SystemExit) as salida:
        runpy.run_path(str(ruta), run_name="__main__")
    assert salida.value.code == 2
    assert str(ruta.parents[1]) in sys.path


def test_modulo_build_reexporta_main() -> None:
    assert importlib.import_module("tools.build").main is cli.main


@pytest.fixture
def entorno_completo(entorno_repo: Any, tmp_path: Path) -> Any:
    """Entorno con todos los componentes que usan build con C y diff."""
    raiz, variables = entorno_repo
    sdk = bloque_componente(
        b"s", archivos_clave={"cpppsx": "pssn/bin/CPPPSX.EXE", "cc1psx": "pssn/bin/CC1PSX.EXE"}
    )
    mas = bloque_componente(b"m", archivos_clave={"maspsx": "maspsx.py"})
    diferencias = bloque_componente(b"d", archivos_clave={"diff": "diff.py"})
    binutils = bloque_componente(
        b"b",
        archivos_clave={
            "as": "bin/as.exe",
            "ld": "bin/ld.exe",
            "objcopy": "bin/objcopy.exe",
            "objdump": "bin/objdump.exe",
        },
    )
    (raiz / "config" / "toolchain.lock.json").write_text(
        json.dumps(
            lock_de(
                **{"psyq-4.4": sdk, "maspsx": mas, "asm-differ": diferencias, "binutils-mipsel": binutils}
            )
        ),
        encoding="utf-8",
    )
    toolchain = tmp_path / "tc"
    for relativa in (
        "psyq-4.4/pssn/bin/CPPPSX.EXE",
        "psyq-4.4/pssn/bin/CC1PSX.EXE",
        "maspsx/maspsx.py",
        "asm-differ/diff.py",
        "binutils-mipsel/bin/objdump.exe",
    ):
        (toolchain / relativa).parent.mkdir(parents=True, exist_ok=True)
        (toolchain / relativa).write_bytes(b"")
    return raiz, variables


def test_build_compila_los_archivos_c_del_script_y_diff_informa_la_puntuacion(
    entorno_completo: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = entorno_completo
    assert ejecutar_cli(raiz, variables, "split") == 0
    (raiz / "build" / "SLUS_008.ld").write_text(
        "main\n{\n    build/asm/text.s.o(.text);\n    build/src/code_a.c.o(.text);\n}\n", encoding="utf-8"
    )
    (raiz / "src").mkdir()
    (raiz / "src" / "code_a.c").write_text(
        "s32 func_80036204(s32 x)\n{\n    return x;\n}\n", encoding="utf-8"
    )
    (raiz / "asm" / "matchings" / "code_a").mkdir(parents=True)
    (raiz / "asm" / "matchings" / "code_a" / "func_80036204.s").write_text(ASM_FUNCION, encoding="utf-8")
    capsys.readouterr()
    assert (
        ejecutar_cli(
            raiz,
            variables,
            "build",
            ejecutor=EjecutorC(secciones=SALIDA_OBJDUMP.replace("0000001d", "00000000")),
        )
        == 0
    )
    assert capsys.readouterr().out == f"build completado: build/PRUEBA.EXE sha256={REFERENCIA.sha256}\n"
    assert ejecutar_cli(raiz, variables, "diff", "func_80036204", ejecutor=EjecutorDiff(0)) == 0
    assert capsys.readouterr().out == "TARGET   CURRENT\nfila\nfunc_80036204 (src/code_a.c): puntuacion 0\n"
    assert ejecutar_cli(raiz, variables, "diff", "func_80036204", ejecutor=EjecutorDiff(120)) == 1
    assert capsys.readouterr().out.endswith("puntuacion 120\n")


def test_build_con_c_y_sin_sdk_instalado_explica_la_causa(
    entorno_completo: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = entorno_completo
    assert ejecutar_cli(raiz, variables, "split") == 0
    (raiz / "build" / "SLUS_008.ld").write_text(
        "main\n{\n    build/src/code_a.c.o(.text);\n}\n", encoding="utf-8"
    )
    (raiz / "src").mkdir()
    (raiz / "src" / "code_a.c").write_text("int x;\n", encoding="utf-8")
    (Path(variables["BBLIT_TOOLCHAIN"]) / "psyq-4.4" / "pssn" / "bin" / "CC1PSX.EXE").unlink()
    capsys.readouterr()
    assert ejecutar_cli(raiz, variables, "build") == 1
    assert "'cc1psx' no esta instalado" in capsys.readouterr().err


def test_diff_de_una_funcion_en_include_asm_sale_con_error(
    entorno_completo: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = entorno_completo
    (raiz / "src").mkdir()
    (raiz / "src" / "code_a.c").write_text(
        'INCLUDE_ASM("asm/nonmatchings/code_a", func_X);\n', encoding="utf-8"
    )
    assert ejecutar_cli(raiz, variables, "diff", "func_X") == 1
    assert "'func_X' sigue en INCLUDE_ASM" in capsys.readouterr().err


def test_progreso_escribe_los_archivos_y_resume_en_una_linea(
    entorno_repo: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = entorno_repo
    (raiz / "config" / "symbols.txt").write_text(
        "func_80014AC4 = 0x80014AC4; // type:func size:0x10\n", encoding="utf-8"
    )
    (raiz / "src").mkdir()
    (raiz / "src" / "code_a.c").write_text("s32 func_80014AC4(void)\n{\n    return 0;\n}\n", encoding="utf-8")
    assert ejecutar_cli(raiz, variables, "progreso") == 0
    assert capsys.readouterr().out == (
        "progreso: 1 funciones del juego en C de 1 (16 de 16 bytes, 100.00 %); 0 NON_MATCHING; "
        "docs/PROGRESO.md y build/progreso.json escritos\n"
    )
    assert (raiz / "docs" / "PROGRESO.md").is_file() and (raiz / "build" / "progreso.json").is_file()


def test_progreso_con_ensamblador_desactualizado_devuelve_uno(
    entorno_repo: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = entorno_repo
    (raiz / "config" / "symbols.txt").write_text(
        "func_80014AC4 = 0x80014AC4; // type:func size:0x10\n", encoding="utf-8"
    )
    (raiz / "asm").mkdir()
    (raiz / "asm" / "x.s").write_text("glabel a\nglabel b\n", encoding="utf-8")
    capsys.readouterr()
    assert ejecutar_cli(raiz, variables, "progreso") == 1
    assert "2 glabel en asm/ + 0 funciones en C no suman las 1 de la tabla" in capsys.readouterr().err


def test_progreso_sin_tabla_de_simbolos(entorno_repo: Any, capsys: pytest.CaptureFixture[str]) -> None:
    raiz, variables = entorno_repo
    assert ejecutar_cli(raiz, variables, "progreso") == 1
    assert capsys.readouterr().err == "error: falta config/symbols.txt\n"


def test_un_error_de_permisos_se_informa_sin_traza_y_devuelve_uno(
    entorno_repo: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = entorno_repo

    def denegado(*_: Any) -> Any:
        raise PermissionError("acceso denegado")

    monkeypatch.setattr(infra, "limpiar", denegado)
    assert ejecutar_cli(raiz, variables, "clean") == 1
    capturado = capsys.readouterr()
    assert capturado.err == "error: acceso denegado\n"
    assert "Traceback" not in capturado.err


def test_verify_sin_ejecutable_reconstruido_imprime_fail_y_devuelve_uno(
    entorno_repo: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = entorno_repo
    assert ejecutar_cli(raiz, variables, "verify") == 1
    salida = capsys.readouterr()
    assert salida.out == (
        f"FAIL el ejecutable reconstruido no existe: ejecute 'build' (esperado={REFERENCIA.sha256})\n"
    )
    assert salida.err == ""


def test_cli_probar_imprime_la_tabla_y_el_codigo_depende_de_la_mejor_variante(
    entorno_completo: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = entorno_completo
    crear_repo(raiz)
    carpeta = crear_variantes(raiz.parent / "variantes", ["peor.c", "mejor.c"])
    capsys.readouterr()
    assert (
        ejecutar_cli(raiz, variables, "probar", "func_80036204", str(carpeta), ejecutor=EjecutorVariantes())
        == 0
    )
    assert capsys.readouterr().out.splitlines() == [
        "variante  puntuacion",
        "mejor.c   0",
        "peor.c    120",
    ]
    (carpeta / "mejor.c").unlink()
    assert (
        ejecutar_cli(raiz, variables, "probar", "func_80036204", str(carpeta), ejecutor=EjecutorVariantes())
        == 1
    )
    assert capsys.readouterr().out.splitlines()[1] == "peor.c    120"
    assert (
        ejecutar_cli(
            raiz, variables, "probar", "func_80036204", str(carpeta / "no"), ejecutor=EjecutorVariantes()
        )
        == 1
    )
    assert capsys.readouterr().err == "error: la carpeta de variantes no existe\n"


def test_diff_que_coincide_en_bytes_sale_con_cero_y_avisa_de_las_referencias_numericas(
    entorno_completo: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = entorno_completo
    assert ejecutar_cli(raiz, variables, "split") == 0
    (raiz / "src").mkdir()
    (raiz / "src" / "code_a.c").write_text(
        "s32 func_80036204(s32 x)\n{\n    return x;\n}\n", encoding="utf-8"
    )
    (raiz / "asm" / "matchings" / "code_a").mkdir(parents=True)
    (raiz / "asm" / "matchings" / "code_a" / "func_80036204.s").write_text(ASM_FUNCION, encoding="utf-8")
    (raiz / "build" / "diff").mkdir(parents=True, exist_ok=True)
    (raiz / "build" / "SLUS_008.elf").write_bytes(b"elf")
    (raiz / "config" / "symbols.txt").write_text(
        "func_80036204 = 0x80036204; // type:func size:0x4c\n", encoding="utf-8"
    )
    capsys.readouterr()
    assert ejecutar_cli(raiz, variables, "diff", "func_80036204", ejecutor=EjecutorEnlace(70)) == 0
    assert capsys.readouterr().out.endswith(
        "func_80036204 (src/code_a.c): coincide en bytes; 2 referencias en forma numerica (puntuacion 70)\n"
    )
    assert (
        ejecutar_cli(raiz, variables, "diff", "func_80036204", ejecutor=EjecutorEnlace(70, difiere=True)) == 1
    )
    assert capsys.readouterr().out.endswith("puntuacion 70\n")

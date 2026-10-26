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

from .test_infraestructura import EJECUTABLE, REFERENCIA, Registro, referencia_json


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

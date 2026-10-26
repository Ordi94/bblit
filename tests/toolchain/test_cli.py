import json
import runpy
import sys
from typing import Any

import pytest
import requests
from tools.toolchain import __main__ as punto_entrada
from tools.toolchain import cli
from tools.toolchain.configuracion import resolver_rutas
from tools.toolchain.extraccion import localizar_7zip

from .ayudantes import RespuestaFalsa, SesionFalsa, bloque_componente, lock_de, zip_de

URL = "https://github.com/ejemplo/proyecto/archive/abc123.zip"
ARCHIVO = zip_de({"proy/herramienta.py": b"print('hola')"})


@pytest.fixture
def repo(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    (tmp_path / "config").mkdir()
    bloque = bloque_componente(ARCHIVO, quitar_raiz=True, archivos_clave={"herramienta": "herramienta.py"})
    (tmp_path / "config" / "toolchain.lock.json").write_text(
        json.dumps(lock_de(pieza=bloque)), encoding="utf-8"
    )
    monkeypatch.setattr(cli, "RAIZ_REPOSITORIO", tmp_path)
    return tmp_path


def sesion() -> SesionFalsa:
    return SesionFalsa(RespuestaFalsa(ARCHIVO, URL))


def test_listar_imprime_nombre_huella_y_fecha(repo: Any, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["listar"], entorno={}) == 0
    salida = capsys.readouterr().out.strip().split("\t")
    assert salida[0] == "pieza"
    assert len(salida[1]) == 64
    assert salida[2] == "2026-10-25"


def test_instalar_verificar_y_ruta(repo: Any, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["verificar"], entorno={}) == 1
    assert capsys.readouterr().out == "pieza\tFALTA\n"
    assert cli.main(["instalar"], entorno={}, sesion=sesion()) == 0
    assert capsys.readouterr().out == "pieza\tinstalado\n"
    assert cli.main(["instalar", "--solo", "pieza"], entorno={}, sesion=sesion()) == 0
    assert capsys.readouterr().out == "pieza\tvigente\n"
    assert cli.main(["verificar"], entorno={}) == 0
    assert capsys.readouterr().out == "pieza\tOK\n"
    assert cli.main(["ruta", "pieza", "herramienta"], entorno={}) == 0
    assert capsys.readouterr().out.strip() == str(repo / "toolchain" / "pieza" / "herramienta.py")


def test_toolchain_por_variable_de_entorno_y_por_argumento(
    repo: Any, capsys: pytest.CaptureFixture[str], tmp_path: Any
) -> None:
    por_entorno = tmp_path / "otro entorno (1)"
    assert cli.main(["instalar"], entorno={"BBLIT_TOOLCHAIN": str(por_entorno)}, sesion=sesion()) == 0
    assert (por_entorno / "pieza" / "herramienta.py").is_file()
    por_argumento = tmp_path / "otro arg"
    assert cli.main(["--toolchain", str(por_argumento), "instalar"], entorno={}, sesion=sesion()) == 0
    assert (por_argumento / "pieza" / "herramienta.py").is_file()


def test_lock_por_argumento(repo: Any, tmp_path: Any, capsys: pytest.CaptureFixture[str]) -> None:
    otro = tmp_path / "otro.json"
    otro.write_text(json.dumps(lock_de(distinta=bloque_componente(ARCHIVO))), encoding="utf-8")
    assert cli.main(["--lock", str(otro), "listar"], entorno={}) == 0
    assert capsys.readouterr().out.startswith("distinta\t")


def test_configuracion_local_se_lee_del_repositorio(repo: Any, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / "config" / "local.toml").write_text(
        '[rutas]\ntoolchain = "' + (repo / "tc").as_posix() + '"\n', encoding="utf-8"
    )
    assert cli.main(["instalar"], entorno={}, sesion=sesion()) == 0
    assert (repo / "tc" / "pieza" / "herramienta.py").is_file()


def test_errores_controlados_salen_en_una_linea_con_codigo_1(
    repo: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "config" / "toolchain.lock.json").unlink()
    assert cli.main(["listar"], entorno={}) == 1
    capturado = capsys.readouterr()
    assert capturado.out == ""
    assert capturado.err == "error: no se encontro el archivo de bloqueo del toolchain\n"


def test_componente_inexistente_en_ruta_y_en_instalar(repo: Any, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["ruta", "fantasma", "x"], entorno={}) == 1
    assert "el componente 'fantasma' no figura en el archivo de bloqueo" in capsys.readouterr().err
    assert cli.main(["instalar", "--solo", "fantasma"], entorno={}, sesion=sesion()) == 1
    assert "el componente 'fantasma' no figura" in capsys.readouterr().err


def test_error_de_red_se_informa_sin_traza(repo: Any, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["instalar"], entorno={}, sesion=SesionFalsa(error=requests.ConnectionError("x"))) == 1
    assert capsys.readouterr().err == "error: componente 'pieza': fallo de red al descargar\n"


def test_sin_7zip_la_cli_continua_con_none(repo: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    def sin_7zip(configurado: Any, entorno: Any) -> None:
        raise FileNotFoundError("no hay")

    monkeypatch.setattr(cli, "localizar_7zip", sin_7zip)
    rutas = resolver_rutas(repo, {}, {})
    assert cli._buscar_7zip(rutas, {}) is None
    monkeypatch.setattr(cli, "localizar_7zip", localizar_7zip)


def test_subcomando_obligatorio() -> None:
    with pytest.raises(SystemExit):
        cli.main([], entorno={})


def test_modulo_principal_delega_en_main(
    repo: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delitem(sys.modules, "tools.toolchain.__main__", raising=False)
    monkeypatch.setattr(sys, "argv", ["tools.toolchain", "listar"])
    with pytest.raises(SystemExit) as salida:
        runpy.run_module("tools.toolchain", run_name="__main__")
    assert salida.value.code in (0, 1)
    assert punto_entrada.main is cli.main

import json
import runpy
import shutil
import sys
from typing import Any

import pytest
import requests
from psxdecomp.lectura import cargar_proyecto
from psxdecomp.toolchain import __main__ as punto_entrada
from psxdecomp.toolchain import cli, plataforma
from psxdecomp.toolchain.configuracion import resolver_rutas
from psxdecomp.toolchain.extraccion import localizar_7zip

from manifiestos_de_prueba import MANIFIESTO_MINIMO

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
    (tmp_path / "psxdecomp.toml").write_text(
        MANIFIESTO_MINIMO.replace('nombre = "demo"', 'nombre = "demo"\nprefijo_entorno = "JUEGO"'),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
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
    assert cli.main(["instalar"], entorno={"PSXDECOMP_TOOLCHAIN": str(por_entorno)}, sesion=sesion()) == 0
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
    def sin_7zip(configurado: Any, entorno: Any, variables: Any, archivo_local: Any) -> None:
        raise FileNotFoundError("no hay")

    monkeypatch.setattr(cli, "localizar_7zip", sin_7zip)
    rutas = resolver_rutas(repo, {}, {})
    assert cli._buscar_7zip(rutas, {}, cargar_proyecto(repo)) is None
    monkeypatch.setattr(cli, "localizar_7zip", localizar_7zip)


def test_el_alias_del_manifiesto_elige_el_toolchain_si_no_hay_variable_propia(
    repo: Any, tmp_path: Any
) -> None:
    por_alias = tmp_path / "por alias"
    assert cli.main(["instalar"], entorno={"JUEGO_TOOLCHAIN": str(por_alias)}, sesion=sesion()) == 0
    assert (por_alias / "pieza" / "herramienta.py").is_file()


def test_la_variable_propia_gana_al_alias(repo: Any, tmp_path: Any) -> None:
    propia, alias = tmp_path / "propia", tmp_path / "alias"
    entorno = {"PSXDECOMP_TOOLCHAIN": str(propia), "JUEGO_TOOLCHAIN": str(alias)}
    assert cli.main(["instalar"], entorno=entorno, sesion=sesion()) == 0
    assert (propia / "pieza" / "herramienta.py").is_file()
    assert not alias.exists()


def test_un_binutils_nativo_ausente_nombra_las_dos_variables(
    repo: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "config" / "toolchain.lock.json").write_text(
        json.dumps(
            lock_de(
                **{"binutils-mipsel": bloque_componente(ARCHIVO, archivos_clave={"as": "herramienta.py"})}
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(plataforma, "es_windows", lambda: False)
    monkeypatch.setattr(shutil, "which", lambda nombre: None)
    assert cli.main(["ruta", "binutils-mipsel", "as"], entorno={}) == 1
    assert "PSXDECOMP_BINUTILS_PREFIX (o JUEGO_BINUTILS_PREFIX)" in capsys.readouterr().err


def test_sin_7zip_el_error_nombra_las_dos_variables_y_el_archivo_local(
    repo: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shutil, "which", lambda nombre: None)
    proyecto = cargar_proyecto(repo)
    with pytest.raises(FileNotFoundError) as error:
        localizar_7zip(None, {}, proyecto.variables(), proyecto.rutas.local)
    assert "PSXDECOMP_7ZIP (o JUEGO_7ZIP)" in str(error.value)
    assert "config/local.toml" in str(error.value)


def test_proyecto_por_argumento_gana_a_la_carpeta_actual(
    repo: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    vacia = tmp_path / "vacia"
    vacia.mkdir()
    monkeypatch.chdir(vacia)
    assert cli.main(["listar"], entorno={}) == 1
    assert "no existe psxdecomp.toml" in capsys.readouterr().err
    assert cli.main(["--proyecto", str(repo), "listar"], entorno={}) == 0
    assert capsys.readouterr().out.startswith("pieza	")


def test_la_raiz_por_omision_del_consumidor_se_usa_sin_argumento(
    repo: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path / "..")
    assert cli.main(["listar"], entorno={}, raiz_por_omision=repo) == 0
    assert capsys.readouterr().out.startswith("pieza	")


def test_el_archivo_local_invalido_se_nombra_por_su_ruta_del_manifiesto(
    repo: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "config" / "local.toml").write_text("[rutas\n", encoding="utf-8")
    assert cli.main(["listar"], entorno={}) == 1
    assert capsys.readouterr().err == "error: config/local.toml no es un TOML valido\n"


def test_subcomando_obligatorio() -> None:
    with pytest.raises(SystemExit):
        cli.main([], entorno={})


def test_modulo_principal_delega_en_main(
    repo: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delitem(sys.modules, "psxdecomp.toolchain.__main__", raising=False)
    monkeypatch.setattr(sys, "argv", ["psxdecomp.toolchain", "listar"])
    with pytest.raises(SystemExit) as salida:
        runpy.run_module("psxdecomp.toolchain", run_name="__main__")
    assert salida.value.code in (0, 1)
    assert punto_entrada.main is cli.main

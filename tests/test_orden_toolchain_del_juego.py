"""``python -m tools.toolchain``: la orden del toolchain del kit sobre este repositorio y el alias BBLIT_*."""

import runpy
import shutil
import sys
from pathlib import Path

import pytest
from psxdecomp.toolchain import cli as cli_kit
from psxdecomp.toolchain import configuracion, extraccion, plataforma
from tools.proyecto import PROYECTO, RAIZ_REPOSITORIO, VARIABLES


def ejecutar_modulo(argumentos: list[str], monkeypatch: pytest.MonkeyPatch) -> int | str | None:
    """Ejecuta ``python -m tools.toolchain`` en proceso y devuelve el codigo de salida."""
    monkeypatch.delitem(sys.modules, "tools.toolchain.__main__", raising=False)
    monkeypatch.setattr(sys, "argv", ["tools.toolchain", *argumentos])
    with pytest.raises(SystemExit) as salida:
        runpy.run_module("tools.toolchain", run_name="__main__")
    return salida.value.code


def test_el_kit_que_se_importa_es_el_paquete_instalado_y_no_una_copia_del_repositorio() -> None:
    assert not Path(configuracion.__file__).resolve().is_relative_to(RAIZ_REPOSITORIO)
    assert not (RAIZ_REPOSITORIO / "kit").exists()


def test_las_variables_del_juego_conservan_el_prefijo_historico() -> None:
    assert VARIABLES.nombre_del_proyecto("DISC") == "BBLIT_DISC"
    assert VARIABLES.nombre_del_proyecto("TOOLCHAIN") == "BBLIT_TOOLCHAIN"
    assert VARIABLES.nombre_del_proyecto("7ZIP") == "BBLIT_7ZIP"
    assert VARIABLES.nombre_del_proyecto("WINE") == "BBLIT_WINE"
    assert VARIABLES.nombre_del_proyecto("BINUTILS_PREFIX") == "BBLIT_BINUTILS_PREFIX"


def test_el_alias_historico_resuelve_las_rutas_y_la_variable_propia_gana() -> None:
    rutas = configuracion.resolver_rutas(
        Path("r"), {"BBLIT_DISC": "d", "BBLIT_TOOLCHAIN": "t"}, {}, variables=VARIABLES
    )
    assert (rutas.disc, rutas.toolchain) == (Path("d"), Path("t"))
    entorno = {"BBLIT_TOOLCHAIN": "alias", "PSXDECOMP_TOOLCHAIN": "propio"}
    assert configuracion.resolver_rutas(Path("r"), entorno, {}, variables=VARIABLES).toolchain == Path(
        "propio"
    )


def test_el_alias_historico_configura_wine_y_los_binutils() -> None:
    assert plataforma.comando_wine({"BBLIT_WINE": "wine64"}, VARIABLES) == "wine64"
    assert plataforma.prefijo_binutils({"BBLIT_BINUTILS_PREFIX": "x-"}, VARIABLES) == "x-"
    comando = plataforma.adaptar_comando(
        ["CC1PSX.EXE"], {"BBLIT_WINE": "w"}, windows=False, variables=VARIABLES
    )
    assert comando == ["w", "CC1PSX.EXE"]
    buscado = plataforma.localizar_binutils(
        "ld", {"BBLIT_BINUTILS_PREFIX": "x-"}, lambda nombre: f"/b/{nombre}", variables=VARIABLES
    )
    assert buscado == Path("/b/x-ld")


def test_la_ruta_del_lock_y_del_archivo_local_salen_del_manifiesto() -> None:
    assert (RAIZ_REPOSITORIO / PROYECTO.rutas.toolchain_lock).is_file()
    assert PROYECTO.rutas.local == "config/local.toml"


def test_el_archivo_local_invalido_se_nombra_con_su_ruta_del_manifiesto(tmp_path: Path) -> None:
    ruta = tmp_path / "local.toml"
    ruta.write_text("[rutas\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"^config/local.toml no es un TOML valido$"):
        configuracion.leer_local_toml(ruta, etiqueta=PROYECTO.rutas.local)


def test_sin_7zip_el_error_nombra_la_variable_propia_y_el_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda nombre: None)
    with pytest.raises(FileNotFoundError, match=r"PSXDECOMP_7ZIP \(o BBLIT_7ZIP\)"):
        extraccion.localizar_7zip(None, {}, VARIABLES, PROYECTO.rutas.local)


def test_python_m_tools_toolchain_lista_los_componentes_como_la_entrada_del_kit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert ejecutar_modulo(["listar"], monkeypatch) == 0
    por_el_juego = capsys.readouterr().out
    assert cli_kit.main(["--proyecto", str(RAIZ_REPOSITORIO), "listar"], entorno={}) == 0
    assert capsys.readouterr().out == por_el_juego
    assert por_el_juego.startswith("psyq-4.4\t")
    assert "asm-differ" in por_el_juego


def test_el_uso_de_python_m_tools_toolchain_conserva_su_nombre(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert ejecutar_modulo([], monkeypatch) == 2
    assert "python -m tools.toolchain" in capsys.readouterr().err

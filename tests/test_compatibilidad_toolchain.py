"""Compatibilidad de ``tools.toolchain``: reexporta el kit con las variables historicas del proyecto."""

import importlib
import runpy
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest
from tools.toolchain import __main__ as punto_entrada
from tools.toolchain import (
    cli,
    configuracion,
    contexto,
    descarga,
    dominio,
    extraccion,
    instalacion,
    iso9660,
    plataforma,
)

from psxdecomp.toolchain import cli as cli_kit
from psxdecomp.toolchain import configuracion as configuracion_kit

MODULOS = {
    "cli": cli,
    "configuracion": configuracion,
    "descarga": descarga,
    "dominio": dominio,
    "extraccion": extraccion,
    "instalacion": instalacion,
    "iso9660": iso9660,
    "plataforma": plataforma,
}
ENVUELTOS = {
    ("cli", "construir_parser"),
    ("cli", "main"),
    ("configuracion", "leer_local_toml"),
    ("configuracion", "resolver_rutas"),
    ("extraccion", "localizar_7zip"),
    ("instalacion", "resolver_herramienta"),
    ("plataforma", "adaptar_comando"),
    ("plataforma", "comando_wine"),
    ("plataforma", "localizar_binutils"),
    ("plataforma", "prefijo_binutils"),
}
PROPIOS_DEL_PROYECTO = {"RAIZ_REPOSITORIO", "RUTA_LOCAL_RELATIVA", "RUTA_LOCK_RELATIVA", "PROG"}


def nombres_publicos_del_kit(nombre: str) -> set[str]:
    """Nombres publicos que define el modulo del kit (funciones, clases y constantes)."""
    modulo = importlib.import_module(f"psxdecomp.toolchain.{nombre}")
    return {
        clave
        for clave, valor in vars(modulo).items()
        if not clave.startswith(("_", "SUFIJO_"))
        and clave not in {"VARIABLES_PROPIAS", "UTC"}
        and (clave.isupper() or getattr(valor, "__module__", None) == modulo.__name__)
    }


@pytest.mark.parametrize("nombre", sorted(MODULOS))
def test_cada_modulo_expone_el_api_publico_del_kit(nombre: str) -> None:
    modulo: ModuleType = MODULOS[nombre]
    esperados = nombres_publicos_del_kit(nombre) - {"PROG_POR_OMISION"}
    assert esperados <= set(modulo.__all__)
    for exportado in modulo.__all__:
        assert hasattr(modulo, exportado), exportado


@pytest.mark.parametrize("nombre", sorted(MODULOS))
def test_lo_que_no_depende_del_entorno_es_el_mismo_objeto_del_kit(nombre: str) -> None:
    modulo = MODULOS[nombre]
    kit = importlib.import_module(f"psxdecomp.toolchain.{nombre}")
    for exportado in modulo.__all__:
        if (nombre, exportado) in ENVUELTOS or exportado.startswith("VARIABLE_"):
            continue
        if exportado in PROPIOS_DEL_PROYECTO:
            continue
        assert getattr(modulo, exportado) is getattr(kit, exportado), exportado


def test_el_kit_que_se_importa_es_el_de_esta_copia_del_repositorio() -> None:
    raiz = Path(__file__).resolve().parents[1]
    assert Path(configuracion_kit.__file__).resolve().is_relative_to(raiz / "kit")


def test_las_constantes_de_variable_conservan_el_prefijo_historico_del_proyecto() -> None:
    assert configuracion.VARIABLE_DISCO == "BBLIT_DISC"
    assert configuracion.VARIABLE_TOOLCHAIN == "BBLIT_TOOLCHAIN"
    assert configuracion.VARIABLE_7ZIP == "BBLIT_7ZIP"
    assert plataforma.VARIABLE_WINE == "BBLIT_WINE"
    assert plataforma.VARIABLE_PREFIJO_BINUTILS == "BBLIT_BINUTILS_PREFIX"


def test_el_alias_historico_resuelve_las_rutas_y_la_variable_propia_gana() -> None:
    rutas = configuracion.resolver_rutas(Path("r"), {"BBLIT_DISC": "d", "BBLIT_TOOLCHAIN": "t"}, {})
    assert (rutas.disc, rutas.toolchain) == (Path("d"), Path("t"))
    entorno = {"BBLIT_TOOLCHAIN": "alias", "PSXDECOMP_TOOLCHAIN": "propio"}
    assert configuracion.resolver_rutas(Path("r"), entorno, {}).toolchain == Path("propio")


def test_el_alias_historico_configura_wine_y_los_binutils() -> None:
    assert plataforma.comando_wine({"BBLIT_WINE": "wine64"}) == "wine64"
    assert plataforma.prefijo_binutils({"BBLIT_BINUTILS_PREFIX": "x-"}) == "x-"
    comando = plataforma.adaptar_comando(["CC1PSX.EXE"], {"BBLIT_WINE": "w"}, windows=False)
    assert comando == ["w", "CC1PSX.EXE"]
    assert plataforma.localizar_binutils("ld", {"BBLIT_BINUTILS_PREFIX": "x-"}, lambda n: f"/b/{n}") == Path(
        "/b/x-ld"
    )


def test_la_ruta_del_lock_y_del_archivo_local_salen_del_manifiesto() -> None:
    assert cli.RUTA_LOCK_RELATIVA == Path("config/toolchain.lock.json")
    assert cli.RUTA_LOCAL_RELATIVA == Path("config/local.toml")
    assert cli.RAIZ_REPOSITORIO == contexto.RAIZ_REPOSITORIO
    assert (contexto.RAIZ_REPOSITORIO / cli.RUTA_LOCK_RELATIVA).is_file()


def test_el_archivo_local_invalido_se_nombra_con_su_ruta_del_manifiesto(tmp_path: Path) -> None:
    ruta = tmp_path / "local.toml"
    ruta.write_text("[rutas\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"^config/local.toml no es un TOML valido$"):
        configuracion.leer_local_toml(ruta)


def test_sin_7zip_el_error_nombra_la_variable_propia_y_el_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda nombre: None)
    with pytest.raises(FileNotFoundError, match=r"PSXDECOMP_7ZIP \(o BBLIT_7ZIP\).*config/local.toml"):
        extraccion.localizar_7zip(None, {})


def test_la_entrada_del_proyecto_lista_los_componentes_como_la_del_kit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["listar"], entorno={}) == 0
    por_proyecto = capsys.readouterr().out
    raiz = str(contexto.RAIZ_REPOSITORIO)
    assert cli_kit.main(["--proyecto", raiz, "listar"], entorno={}) == 0
    assert capsys.readouterr().out == por_proyecto
    assert por_proyecto.startswith("psyq-4.4\t")


def test_el_uso_de_la_entrada_del_proyecto_conserva_su_nombre(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        cli.main([])
    assert "python -m tools.toolchain" in capsys.readouterr().err
    assert cli.construir_parser().prog == "python -m tools.toolchain"


def test_el_modulo_principal_delega_en_la_cli_del_proyecto() -> None:
    assert punto_entrada.main is cli.main


def test_python_m_tools_toolchain_ejecuta_la_cli(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delitem(sys.modules, "tools.toolchain.__main__", raising=False)
    monkeypatch.setattr(sys, "argv", ["tools.toolchain", "listar"])
    with pytest.raises(SystemExit) as salida:
        runpy.run_module("tools.toolchain", run_name="__main__")
    assert salida.value.code == 0
    assert "asm-differ" in capsys.readouterr().out

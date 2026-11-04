"""Reglas de negocio de la proteccion del disco original: las cinco formas de configurarlo protegen igual."""

from pathlib import Path
from typing import Any

import pytest
from tools.emulador import cli, sesion
from tools.proyecto import resolver_disco

from tests.emulador.dobles import ClienteFalso, ram_con

CONFIGURACIONES = ["variable_propia", "alias_del_juego", "local_toml", "ambas_variables"]


@pytest.fixture
def repositorio(tmp_path: Path) -> Path:
    """Raiz de repositorio sintetica con carpeta de configuracion y sin `local.toml`."""
    raiz = tmp_path / "repo"
    (raiz / "config").mkdir(parents=True)
    return raiz


@pytest.fixture
def imagen(tmp_path: Path) -> Path:
    """Imagen `.bin` sintetica dentro de una carpeta de disco."""
    carpeta = tmp_path / "disc"
    carpeta.mkdir()
    ruta = carpeta / "juego.bin"
    ruta.write_bytes(b"x")
    return ruta


def _configurar(repositorio: Path, imagen: Path, forma: str) -> dict[str, str]:
    """Configura el disco por una de las vias y devuelve el entorno inyectable correspondiente."""
    if forma == "local_toml":
        (repositorio / "config" / "local.toml").write_text(
            f'[rutas]\ndisc = "{imagen.as_posix()}"\n', encoding="utf-8"
        )
        return {}
    if forma == "variable_propia":
        return {"PSXDECOMP_DISC": str(imagen)}
    if forma == "alias_del_juego":
        return {"BBLIT_DISC": str(imagen)}
    return {"PSXDECOMP_DISC": str(imagen), "BBLIT_DISC": str(imagen.parent / "otro.bin")}


def test_resolver_disco_sin_configuracion_devuelve_none(repositorio: Path) -> None:
    assert resolver_disco({}, repositorio) is None


def test_resolver_disco_el_argumento_manda_sobre_todo(repositorio: Path, imagen: Path) -> None:
    entorno = _configurar(repositorio, imagen, "ambas_variables")
    assert resolver_disco(entorno, repositorio, "explicito.bin") == Path("explicito.bin")


def test_resolver_disco_el_prefijo_propio_manda_sobre_el_alias(repositorio: Path, imagen: Path) -> None:
    entorno = _configurar(repositorio, imagen, "ambas_variables")
    assert resolver_disco(entorno, repositorio) == imagen


def test_resolver_disco_el_alias_manda_sobre_local_toml(repositorio: Path, imagen: Path) -> None:
    _configurar(repositorio, imagen, "local_toml")
    assert resolver_disco({"BBLIT_DISC": "alias.bin"}, repositorio) == Path("alias.bin")


def test_resolver_disco_usa_local_toml_si_no_hay_variables(repositorio: Path, imagen: Path) -> None:
    _configurar(repositorio, imagen, "local_toml")
    assert resolver_disco({}, repositorio) == imagen


def test_resolver_disco_rechaza_un_local_toml_invalido(repositorio: Path) -> None:
    (repositorio / "config" / "local.toml").write_text("esto no es toml [", encoding="utf-8")
    with pytest.raises(ValueError, match="TOML"):
        resolver_disco({}, repositorio)


@pytest.mark.parametrize("subcomando", ["volcar", "capturar"])
@pytest.mark.parametrize("forma", CONFIGURACIONES)
def test_guardado_protege_el_disco_cualquiera_que_sea_su_via_de_configuracion(
    repositorio: Path, imagen: Path, subcomando: str, forma: str
) -> None:
    entorno = _configurar(repositorio, imagen, forma)
    destino = imagen.parent / "salida.bin"
    assert cli.main([subcomando, "--salida", str(destino)], entorno, repositorio) == 1
    assert not destino.exists()


@pytest.mark.parametrize("forma", CONFIGURACIONES)
def test_sesion_protege_el_disco_cualquiera_que_sea_su_via_de_configuracion(
    repositorio: Path, imagen: Path, capsys: pytest.CaptureFixture[str], forma: str
) -> None:
    entorno = _configurar(repositorio, imagen, forma)
    destino = imagen.parent / "sesion"
    assert cli.main(["sesion", "--salida", str(destino)], entorno, repositorio) == 1
    assert "disco original" in capsys.readouterr().out
    assert not destino.exists()


@pytest.mark.parametrize("subcomando", ["volcar", "capturar"])
def test_sin_disco_configurado_el_guardado_no_se_rechaza(
    repositorio: Path, imagen: Path, monkeypatch: pytest.MonkeyPatch, subcomando: str
) -> None:
    monkeypatch.setattr(
        cli, "ClienteRedux", lambda puerto: ClienteFalso(pantallas=[b"p"], rams=[ram_con(0, b"x")])
    )
    destino = imagen.parent / "salida.bin"
    assert cli.main([subcomando, "--salida", str(destino)], {}, repositorio) == 0
    assert destino.is_file()


def test_sin_disco_configurado_la_sesion_no_protege_nada(
    repositorio: Path, imagen: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recibidas: list[sesion.ConfigSesion] = []

    def doble(config: sesion.ConfigSesion) -> dict[str, object]:
        recibidas.append(config)
        return {}

    monkeypatch.setattr(sesion, "ejecutar_sesion", doble)
    assert cli.main(["sesion", "--salida", str(imagen.parent / "s")], {}, repositorio) == 0
    assert recibidas[0].disco is None


def test_la_sesion_usa_el_entorno_inyectado_y_no_el_del_proceso(
    repositorio: Path, imagen: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """El mapping de `main` decide el disco; un `BBLIT_DISC` real distinto no influye."""
    otro = tmp_path / "otro" / "x.bin"
    monkeypatch.setenv("BBLIT_DISC", str(otro))
    recibidas: list[sesion.ConfigSesion] = []

    def doble(config: sesion.ConfigSesion) -> dict[str, Any]:
        recibidas.append(config)
        return {}

    monkeypatch.setattr(sesion, "ejecutar_sesion", doble)
    entorno = {"BBLIT_DISC": str(imagen)}
    assert cli.main(["sesion", "--salida", str(tmp_path / "fuera")], entorno, repositorio) == 0
    assert recibidas[0].disco == imagen


def test_la_sesion_ignora_un_disco_del_proceso_ausente_del_entorno_inyectado(
    repositorio: Path, imagen: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Con el disco solo en `os.environ`, una sesion con entorno vacio no lo protege."""
    monkeypatch.setenv("BBLIT_DISC", str(imagen))
    monkeypatch.setenv("PSXDECOMP_DISC", str(imagen))
    recibidas: list[sesion.ConfigSesion] = []

    def doble(config: sesion.ConfigSesion) -> dict[str, Any]:
        recibidas.append(config)
        return {}

    monkeypatch.setattr(sesion, "ejecutar_sesion", doble)
    assert cli.main(["sesion", "--salida", str(imagen.parent / "s")], {}, repositorio) == 0
    assert recibidas[0].disco is None


@pytest.mark.parametrize("prefijo", ["PSXDECOMP", "BBLIT"])
def test_el_emulador_y_la_bios_aceptan_prefijo_propio_y_alias(
    repositorio: Path, tmp_path: Path, prefijo: str
) -> None:
    entorno = {
        f"{prefijo}_TOOLCHAIN": str(tmp_path / "tc"),
        f"{prefijo}_REDUX": str(tmp_path / "mi redux.exe"),
        f"{prefijo}_BIOS": str(tmp_path / "mi bios.bin"),
    }
    rutas = cli.resolver_rutas_emulador(entorno, repositorio)
    assert rutas.emulador == tmp_path / "mi redux.exe"
    assert rutas.bios == tmp_path / "mi bios.bin"

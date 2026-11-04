"""Reglas de negocio de la resolucion del ejecutable: el disco se configura por las vias del kit."""

from pathlib import Path

import pytest
from tools.ghidra.ejecucion import resolver_ejecutable, resolver_instalacion
from tools.proyecto import RAIZ_REPOSITORIO

CONFIGURACIONES = ["variable_propia", "alias_del_juego", "local_toml", "ambas_variables"]


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    """Raiz de repositorio sintetica con la descripcion real del ejecutable."""
    carpeta = tmp_path / "repo"
    (carpeta / "config").mkdir(parents=True)
    origen = RAIZ_REPOSITORIO / "config" / "ejecutable.json"
    (carpeta / "config" / "ejecutable.json").write_bytes(origen.read_bytes())
    return carpeta


@pytest.fixture
def disco(tmp_path: Path) -> Path:
    """Carpeta de disco extraido con `fs/SLUS_008.38`."""
    exe = tmp_path / "disco" / "fs" / "SLUS_008.38"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"x")
    return exe.parent.parent


@pytest.mark.parametrize("forma", CONFIGURACIONES)
def test_el_ejecutable_se_resuelve_por_cualquiera_de_las_vias_de_configuracion(
    raiz: Path, disco: Path, forma: str
) -> None:
    entorno: dict[str, str] = {}
    if forma == "local_toml":
        (raiz / "config" / "local.toml").write_text(
            f'[rutas]\ndisc = "{disco.as_posix()}"\n', encoding="utf-8"
        )
    elif forma == "variable_propia":
        entorno = {"PSXDECOMP_DISC": str(disco)}
    elif forma == "alias_del_juego":
        entorno = {"BBLIT_DISC": str(disco)}
    else:
        entorno = {"PSXDECOMP_DISC": str(disco), "BBLIT_DISC": "no-existe"}
    assert resolver_ejecutable(None, entorno, raiz) == disco / "fs" / "SLUS_008.38"


def test_el_argumento_manda_sobre_cualquier_configuracion_del_disco(raiz: Path, tmp_path: Path) -> None:
    exe = tmp_path / "SLUS_008.38"
    exe.write_bytes(b"x")
    assert resolver_ejecutable(exe, {"PSXDECOMP_DISC": "no-existe"}, raiz) == exe


def test_sin_disco_ni_argumento_el_mensaje_nombra_las_dos_variables(raiz: Path) -> None:
    with pytest.raises(ValueError, match=r"PSXDECOMP_DISC \(o BBLIT_DISC\)"):
        resolver_ejecutable(None, {}, raiz)


def test_un_local_toml_invalido_se_rechaza_con_mensaje_controlado(raiz: Path) -> None:
    (raiz / "config" / "local.toml").write_text("esto no es toml [", encoding="utf-8")
    with pytest.raises(ValueError, match="TOML"):
        resolver_ejecutable(None, {}, raiz)


@pytest.mark.parametrize("variable", ["PSXDECOMP_GHIDRA", "BBLIT_GHIDRA"])
def test_la_instalacion_de_ghidra_acepta_prefijo_propio_y_alias(tmp_path: Path, variable: str) -> None:
    (tmp_path / "support").mkdir()
    assert resolver_instalacion(None, {variable: str(tmp_path)}) == tmp_path

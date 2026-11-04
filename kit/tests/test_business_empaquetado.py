"""Reglas del empaquetado: el kit declara lo que importa y se puede publicar sin datos de un proyecto."""

import ast
import re
import sys
import tomllib
from pathlib import Path

import pytest

RAIZ_KIT = Path(__file__).resolve().parents[1]
PAQUETE = RAIZ_KIT / "psxdecomp"
MODULO_A_DISTRIBUCION = {"yaml": "pyyaml", "requests": "requests"}
pytestmark = pytest.mark.skipif(
    not PAQUETE.is_dir(), reason="el kit se ejecuta instalado: no hay arbol de fuentes junto a las pruebas"
)


@pytest.fixture(scope="module")
def pyproject() -> dict[str, object]:
    ruta = RAIZ_KIT / "pyproject.toml"
    if not ruta.is_file():
        pytest.skip("el kit se ejecuta instalado: no hay pyproject.toml junto a las pruebas")
    return tomllib.loads(ruta.read_text(encoding="utf-8"))


def _modulos_importados() -> set[str]:
    modulos: set[str] = set()
    for archivo in PAQUETE.rglob("*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.Import):
                modulos.update(alias.name.split(".")[0] for alias in nodo.names)
            elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                modulos.add(nodo.module.split(".")[0])
    return modulos


def _dependencias_declaradas(pyproject: dict[str, object]) -> set[str]:
    proyecto = pyproject["project"]
    assert isinstance(proyecto, dict)
    return {re.split(r"[<>=!~\[ ]", dependencia, maxsplit=1)[0].lower() for dependencia in proyecto["dependencies"]}


def test_toda_importacion_de_terceros_esta_declarada_como_dependencia(pyproject: dict[str, object]) -> None:
    propios = {"psxdecomp", "__future__"}
    terceros = {m for m in _modulos_importados() - propios if m not in sys.stdlib_module_names}
    declaradas = _dependencias_declaradas(pyproject)
    faltantes = {m for m in terceros if MODULO_A_DISTRIBUCION.get(m, m).lower() not in declaradas}
    assert not faltantes


def test_el_kit_nunca_importa_del_proyecto_consumidor() -> None:
    importados = _modulos_importados()
    assert "tools" not in importados


def test_el_paquete_declara_su_tipado_para_los_consumidores() -> None:
    assert (PAQUETE / "py.typed").is_file()


def test_los_metadatos_de_publicacion_estan_completos(pyproject: dict[str, object]) -> None:
    proyecto = pyproject["project"]
    assert isinstance(proyecto, dict)
    assert proyecto["name"] == "psx-decomp-kit"
    assert proyecto["license"] == "MIT"
    assert proyecto["readme"] == "README.md"
    assert proyecto["classifiers"]
    assert {"Repository", "Issues", "Changelog"} <= set(proyecto["urls"])


def test_la_version_del_proyecto_figura_en_el_registro_de_cambios(pyproject: dict[str, object]) -> None:
    proyecto = pyproject["project"]
    assert isinstance(proyecto, dict)
    registro = (RAIZ_KIT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{proyecto['version']}]" in registro


def test_la_licencia_nombra_titular_y_ano() -> None:
    texto = (RAIZ_KIT / "LICENSE").read_text(encoding="utf-8")
    assert re.search(r"Copyright \(c\) 20\d\d \S", texto)


ENTRADAS_ADMITIDAS = frozenset(
    {
        "psxdecomp",
        "tests",
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        ".gitignore",
        # Productos locales de las herramientas de desarrollo; el .gitignore del kit los excluye.
        ".coverage",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "build",
        "dist",
        "psx_decomp_kit.egg-info",
    }
)


def test_la_carpeta_del_kit_solo_contiene_lo_que_se_distribuye() -> None:
    nombres = {ruta.name for ruta in RAIZ_KIT.iterdir()}
    assert nombres <= ENTRADAS_ADMITIDAS, sorted(nombres - ENTRADAS_ADMITIDAS)

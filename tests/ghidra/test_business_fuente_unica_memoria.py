"""La geometria de la memoria tiene una sola fuente: ``ejecutable.json`` y ``[zonas]`` del manifiesto."""

import ast
import json
import shutil
import tomllib
from pathlib import Path
from types import ModuleType

import pytest
from tools.ghidra import dominio, zonas
from tools.proyecto import PROYECTO, RAIZ_REPOSITORIO, cargar

from psxdecomp.proyecto import ManifiestoError

CABECERA = json.loads((RAIZ_REPOSITORIO / "config" / "ejecutable.json").read_text(encoding="utf-8"))[
    "cabecera"
]
ZONAS_TOML = tomllib.loads((RAIZ_REPOSITORIO / "psxdecomp.toml").read_text(encoding="utf-8"))["zonas"]


def enteros_literales(modulo: ModuleType) -> set[int]:
    """Enteros escritos como literal en el codigo de un modulo (no en sus docstrings)."""
    arbol = ast.parse(Path(str(modulo.__file__)).read_text(encoding="utf-8"))
    return {n.value for n in ast.walk(arbol) if isinstance(n, ast.Constant) and type(n.value) is int}


def test_las_constantes_de_memoria_de_ghidra_son_las_de_ejecutable_json() -> None:
    assert int(CABECERA["t_addr"], 16) == dominio.DIRECCION_BASE
    assert int(CABECERA["t_size"], 16) == dominio.TAMANO_SEGMENTO
    assert int(CABECERA["pc0"], 16) == dominio.DIRECCION_ENTRADA
    assert dominio.DIRECCION_FIN == dominio.DIRECCION_BASE + dominio.TAMANO_SEGMENTO


def test_las_zonas_de_ghidra_son_las_del_manifiesto() -> None:
    assert zonas.INICIO_JUEGO == ZONAS_TOML["juego_desde"] == PROYECTO.zonas.juego_desde
    assert zonas.FIN_JUEGO == ZONAS_TOML["librerias_desde"] == PROYECTO.zonas.librerias_desde
    assert dominio.FIN_CODIGO == ZONAS_TOML["librerias_hasta"] == PROYECTO.zonas.librerias_hasta


def test_ningun_modulo_de_ghidra_repite_como_literal_un_valor_del_manifiesto_ni_de_la_cabecera() -> None:
    declarados = {
        int(CABECERA["t_addr"], 16),
        int(CABECERA["t_size"], 16),
        int(CABECERA["pc0"], 16),
        ZONAS_TOML["juego_desde"],
        ZONAS_TOML["librerias_desde"],
        ZONAS_TOML["librerias_hasta"],
    }
    for modulo in (dominio, zonas):
        assert declarados.isdisjoint(enteros_literales(modulo)), modulo.__name__


def test_las_fronteras_de_zona_siguen_los_valores_derivados() -> None:
    assert zonas.clasificar_zona(dominio.DIRECCION_BASE) == "arranque"
    assert zonas.clasificar_zona(zonas.INICIO_JUEGO - 4) == "arranque"
    assert zonas.clasificar_zona(zonas.INICIO_JUEGO) == "juego"
    assert zonas.clasificar_zona(zonas.FIN_JUEGO - 4) == "juego"
    assert zonas.clasificar_zona(zonas.FIN_JUEGO) == "libreria"
    assert zonas.clasificar_zona(dominio.FIN_CODIGO - 4) == "libreria"
    assert zonas.clasificar_zona(dominio.FIN_CODIGO) == "externo"


def test_cargar_lee_el_manifiesto_de_la_raiz_indicada(tmp_path: Path) -> None:
    shutil.copy(RAIZ_REPOSITORIO / "psxdecomp.toml", tmp_path / "psxdecomp.toml")
    proyecto = cargar(tmp_path)
    assert proyecto.raiz == tmp_path
    assert proyecto.zonas == PROYECTO.zonas


def test_cargar_sin_manifiesto_falla_sin_revelar_rutas(tmp_path: Path) -> None:
    with pytest.raises(ManifiestoError, match=r"no existe psxdecomp\.toml") as error:
        cargar(tmp_path)
    assert str(tmp_path) not in str(error.value)

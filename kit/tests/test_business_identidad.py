"""El kit no nombra ningun juego: ni en el codigo, ni en las pruebas, ni en la documentacion."""

from pathlib import Path

import pytest

from identidad_del_juego import PATRONES_PROHIBIDOS, TERMINOS_PROHIBIDOS

RAIZ_KIT = Path(__file__).resolve().parents[1]
PAQUETE = RAIZ_KIT / "psxdecomp"
EXTENSIONES = {".py", ".md", ".toml", ".txt", ".json", ".yaml", ".yml"}
EXENTOS = {"identidad_del_juego.py", "test_business_identidad.py", "test_parser.py"}
TERMINOS_DE_ARBOL = tuple(t for t in TERMINOS_PROHIBIDOS if t not in {"src/", "config/", "NON_MATCHING"})
pytestmark = pytest.mark.skipif(
    not PAQUETE.is_dir(), reason="el kit se ejecuta instalado: no hay arbol de fuentes junto a las pruebas"
)


def _archivos_del_kit() -> list[Path]:
    return [
        ruta
        for ruta in sorted(RAIZ_KIT.rglob("*"))
        if ruta.is_file()
        and ruta.suffix in EXTENSIONES
        and ruta.name not in EXENTOS
        and not {"__pycache__", "build", ".venv"} & set(ruta.parts)
    ]


def test_ningun_archivo_del_kit_contiene_un_termino_que_identifique_un_juego() -> None:
    hallazgos = [
        f"{ruta.relative_to(RAIZ_KIT)}: {termino}"
        for ruta in _archivos_del_kit()
        for termino in TERMINOS_DE_ARBOL
        if termino in ruta.read_text(encoding="utf-8")
    ]
    assert not hallazgos


def test_ningun_archivo_del_kit_usa_nombres_ni_direcciones_de_un_ejecutable_real() -> None:
    hallazgos = [
        f"{ruta.relative_to(RAIZ_KIT)}: {patron.pattern}"
        for ruta in _archivos_del_kit()
        for patron in PATRONES_PROHIBIDOS
        if patron.search(ruta.read_text(encoding="utf-8"))
    ]
    assert not hallazgos


def test_la_exploracion_encuentra_los_archivos_del_kit() -> None:
    nombres = {ruta.name for ruta in _archivos_del_kit()}
    assert {"pyproject.toml", "README.md", "dominio.py"} <= nombres

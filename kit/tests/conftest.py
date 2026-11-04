"""Fixtures compartidas de las pruebas del kit."""

from pathlib import Path

import pytest

from manifiestos_de_prueba import EscribirManifiesto


@pytest.fixture
def escribir_manifiesto(tmp_path: Path) -> EscribirManifiesto:
    """Devuelve una funcion que escribe el texto dado como ``psxdecomp.toml`` de una raiz vacia."""

    def escribir(texto: str) -> Path:
        (tmp_path / "psxdecomp.toml").write_bytes(texto.encode("utf-8"))
        return tmp_path

    return escribir

"""Fixtures compartidas de las pruebas del toolchain."""

import os
from pathlib import Path

import pytest


@pytest.fixture
def sistema_sensible(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hace que ``Path.exists`` distinga mayusculas, como un sistema de archivos de Linux."""

    def existe(self: Path) -> bool:
        if self.parent == self:
            return os.path.lexists(self)
        try:
            return self.name in os.listdir(self.parent)
        except OSError:
            return False

    monkeypatch.setattr(Path, "exists", existe)

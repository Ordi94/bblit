"""Importar el modulo principal de un paquete no ejecuta su linea de ordenes: solo ``python -m`` lo hace."""

import importlib
import sys

import pytest

MODULOS_PRINCIPALES = (
    "tools.bzz.__main__",
    "tools.ghidra.__main__",
    "tools.overlay.__main__",
    "tools.toolchain.__main__",
)


@pytest.mark.parametrize("nombre", MODULOS_PRINCIPALES)
def test_importar_el_modulo_principal_no_ejecuta_la_orden(
    nombre: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delitem(sys.modules, nombre, raising=False)
    monkeypatch.setattr(sys, "argv", ["importacion", "--orden-inexistente"])
    modulo = importlib.import_module(nombre)
    assert callable(modulo.main)

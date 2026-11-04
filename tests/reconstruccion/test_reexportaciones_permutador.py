"""Las reexportaciones de tools/reconstruccion conservan el API publico del permutador del kit."""

import importlib
from types import ModuleType

import pytest

PARES = [
    ("tools.reconstruccion.permutar_c", "psxdecomp.permutador.c"),
    ("tools.reconstruccion.permutar_analisis", "psxdecomp.permutador.analisis"),
    ("tools.reconstruccion.permutar_estado", "psxdecomp.permutador.estado"),
    ("tools.reconstruccion.permutar_mutaciones", "psxdecomp.permutador.mutaciones"),
]


def _cargar(nombre: str) -> ModuleType:
    return importlib.import_module(nombre)


@pytest.mark.parametrize(("reexportacion", "origen"), PARES)
def test_cada_nombre_reexportado_es_el_objeto_del_kit(reexportacion: str, origen: str) -> None:
    modulo = _cargar(reexportacion)
    kit = _cargar(origen)
    assert modulo.__all__, "la reexportacion debe declarar su API"
    for nombre in modulo.__all__:
        assert getattr(modulo, nombre) is getattr(kit, nombre)

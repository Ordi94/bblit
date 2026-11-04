"""Fixtures compartidas de las pruebas del kit."""

import sys
from pathlib import Path

import pytest

from manifiestos_de_prueba import EscribirManifiesto

RAIZ_CONSUMIDOR = Path(__file__).resolve().parents[2]

# Si el kit vive dentro de un proyecto consumidor (hay un manifiesto en la carpeta que lo contiene),
# su raiz se pone en el path para que la prueba de coherencia importe los modulos del consumidor
# tambien al lanzar las pruebas desde ``kit/``. Sin manifiesto, esas pruebas se omiten con motivo.
if (RAIZ_CONSUMIDOR / "psxdecomp.toml").is_file() and str(RAIZ_CONSUMIDOR) not in sys.path:
    sys.path.insert(0, str(RAIZ_CONSUMIDOR))


@pytest.fixture
def escribir_manifiesto(tmp_path: Path) -> EscribirManifiesto:
    """Devuelve una funcion que escribe el texto dado como ``psxdecomp.toml`` de una raiz vacia."""

    def escribir(texto: str) -> Path:
        (tmp_path / "psxdecomp.toml").write_bytes(texto.encode("utf-8"))
        return tmp_path

    return escribir

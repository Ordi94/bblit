"""El kit se instala por commit completo: una etiqueta git se puede reapuntar, un SHA no.

``requirements.txt`` es lo que instala el entorno; si el especificador volviera a una etiqueta o a una rama,
el codigo del kit podria cambiar sin que ninguna revision lo viera.
"""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ESPECIFICADOR = re.compile(
    r"^psx-decomp-kit @ git\+https://github\.com/Ordi94/psx-decomp-kit@(?P<sha>[0-9a-f]{40})$"
)


def _lineas() -> list[str]:
    return (RAIZ / "requirements.txt").read_text(encoding="utf-8").splitlines()


def _indice_del_kit() -> int:
    return next(i for i, linea in enumerate(_lineas()) if linea.startswith("psx-decomp-kit"))


def test_el_kit_se_fija_por_sha_de_commit_de_40_hexadecimales() -> None:
    assert ESPECIFICADOR.match(_lineas()[_indice_del_kit()]) is not None


def test_la_linea_anterior_al_kit_nombra_la_etiqueta_y_como_actualizar() -> None:
    comentario = _lineas()[_indice_del_kit() - 1]
    assert comentario.startswith("#")
    assert re.search(r"\bv\d+\.\d+\.\d+\b", comentario) is not None
    assert "git ls-remote" in comentario

"""Reglas de confinamiento de rutas: lo que el kit acepta bajo la raiz y lo que rechaza."""

from pathlib import Path

import pytest
from psxdecomp import confinamiento
from psxdecomp.validacion import ManifiestoError


def test_una_ruta_que_resuelve_fuera_de_la_raiz_se_rechaza(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    raiz.mkdir()
    confinamiento.comprobar_dentro_de_raiz(raiz, "src/interno", "fuentes", "rutas")
    with pytest.raises(ManifiestoError, match="permanezca dentro de la raiz"):
        confinamiento.comprobar_dentro_de_raiz(raiz, "../hermano", "fuentes", "rutas")


@pytest.mark.parametrize("relativa", ["/x", "C:/x", "\\\\servidor\\x", "a/../..", "a\x00b"])
def test_el_confinamiento_rechaza_rutas_con_raiz_unidad_salto_o_que_no_se_pueden_resolver(
    tmp_path: Path, relativa: str
) -> None:
    assert not confinamiento.esta_confinada(tmp_path, relativa)
    with pytest.raises(ManifiestoError, match="permanezca dentro de la raiz"):
        confinamiento.comprobar_dentro_de_raiz(tmp_path, relativa, "fuentes", "rutas")


def test_el_confinamiento_acepta_rutas_relativas_inexistentes_bajo_la_raiz(tmp_path: Path) -> None:
    assert confinamiento.esta_confinada(tmp_path, "a/b/c.txt")


def test_una_ruta_que_el_sistema_no_puede_resolver_no_esta_confinada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fallar(self: Path, strict: bool = False) -> Path:
        raise OSError("fallo simulado de resolucion")

    monkeypatch.setattr(Path, "resolve", fallar)
    assert not confinamiento.esta_confinada(tmp_path, "src")


def test_un_enlace_simbolico_que_apunta_fuera_de_la_raiz_no_esta_confinado(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    fuera = tmp_path / "fuera"
    raiz.mkdir()
    fuera.mkdir()
    try:
        (raiz / "enlace").symlink_to(fuera, target_is_directory=True)
    except OSError:
        pytest.skip("el sistema no permite crear enlaces simbolicos")
    assert not confinamiento.esta_confinada(raiz, "enlace/dato.txt")

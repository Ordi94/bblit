"""Reglas de negocio de ``extraer`` sobre los finales de linea de ``config/overlay.json``.

Reescribir el archivo con otro final de linea que el de la copia de trabajo lo deja distinto de lo
que git espera: ``git status`` lo marca como modificado aunque el contenido sea el mismo.
"""

from pathlib import Path

import pytest
from tools.overlay import dominio, extraccion

from tests.overlay.ayudantes import construir_overlay, variantes_conocidas

A = construir_overlay(1)
CONOCIDAS = variantes_conocidas({"a": A}, {"a": 1})


def extraer_a(raiz: Path) -> None:
    variantes, binarios = dominio.identificar_variantes(
        dominio.agrupar_por_huella([("A/X.BZZ", A)]), CONOCIDAS
    )
    extraccion.escribir_extraccion(raiz, variantes, binarios)


def ruta_config(raiz: Path) -> Path:
    return raiz / "config" / "overlay.json"


def test_una_config_existente_en_crlf_se_reescribe_en_crlf(tmp_path: Path) -> None:
    extraer_a(tmp_path)
    contenido_lf = ruta_config(tmp_path).read_bytes()
    ruta_config(tmp_path).write_bytes(contenido_lf.replace(b"\n", b"\r\n"))
    extraer_a(tmp_path)
    reescrito = ruta_config(tmp_path).read_bytes()
    assert reescrito == contenido_lf.replace(b"\n", b"\r\n")
    assert b"\r\r" not in reescrito


def test_una_config_existente_en_lf_se_reescribe_en_lf(tmp_path: Path) -> None:
    extraer_a(tmp_path)
    primero = ruta_config(tmp_path).read_bytes()
    extraer_a(tmp_path)
    assert b"\r" not in primero
    assert ruta_config(tmp_path).read_bytes() == primero


def test_sin_config_previa_se_escribe_en_lf(tmp_path: Path) -> None:
    extraer_a(tmp_path)
    assert b"\r" not in ruta_config(tmp_path).read_bytes()


def test_una_config_reescrita_en_crlf_se_sigue_leyendo(tmp_path: Path) -> None:
    extraer_a(tmp_path)
    ruta_config(tmp_path).write_bytes(ruta_config(tmp_path).read_bytes().replace(b"\n", b"\r\n"))
    extraer_a(tmp_path)
    assert [v.identificador for v in extraccion.leer_variantes(tmp_path, CONOCIDAS)] == ["a"]


def test_si_el_archivo_no_se_puede_leer_se_usa_lf(tmp_path: Path) -> None:
    una_carpeta = tmp_path / "carpeta"
    una_carpeta.mkdir()
    assert extraccion.final_de_linea_de(una_carpeta) == "\n"
    assert extraccion.final_de_linea_de(tmp_path / "no_existe.json") == "\n"


@pytest.mark.parametrize(("contenido", "esperado"), [(b"a\r\nb\r\n", "\r\n"), (b"a\nb\n", "\n"), (b"", "\n")])
def test_el_final_de_linea_se_deduce_del_contenido(tmp_path: Path, contenido: bytes, esperado: str) -> None:
    archivo = tmp_path / "x.json"
    archivo.write_bytes(contenido)
    assert extraccion.final_de_linea_de(archivo) == esperado

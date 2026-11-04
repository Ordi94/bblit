"""Reglas de lectura del manifiesto desde disco: archivo, tamano, codificacion y confinamiento."""

from pathlib import Path

import pytest
from psxdecomp import lectura
from psxdecomp.dominio import Proyecto
from psxdecomp.lectura import cargar_proyecto
from psxdecomp.validacion import ManifiestoError

from manifiestos_de_prueba import MANIFIESTO_MINIMO, EscribirManifiesto


def cargar(escribir: EscribirManifiesto, texto: str) -> Proyecto:
    return cargar_proyecto(escribir(texto))


# --- Archivo ausente, ilegible, demasiado grande o malformado ---------------------------------


def test_sin_manifiesto_el_error_no_revela_la_ruta_absoluta(tmp_path: Path) -> None:
    with pytest.raises(ManifiestoError, match=r"no existe psxdecomp.toml") as error:
        cargar_proyecto(tmp_path)
    assert str(tmp_path) not in str(error.value)


def test_una_raiz_que_no_es_carpeta_se_rechaza(tmp_path: Path) -> None:
    archivo = tmp_path / "suelto"
    archivo.write_text("x", encoding="utf-8")
    with pytest.raises(ManifiestoError, match=r"no existe psxdecomp.toml"):
        cargar_proyecto(archivo)


def test_un_toml_malformado_se_reporta_sin_trazas_ni_rutas(
    escribir_manifiesto: EscribirManifiesto, tmp_path: Path
) -> None:
    with pytest.raises(ManifiestoError, match="no es un TOML valido") as error:
        cargar(escribir_manifiesto, "[proyecto\nnombre = ")
    assert str(tmp_path) not in str(error.value)
    assert error.value.__cause__ is None


def test_un_manifiesto_que_no_es_utf8_se_rechaza(tmp_path: Path) -> None:
    (tmp_path / "psxdecomp.toml").write_bytes(b"\xff\xfe\x00\x80")
    with pytest.raises(ManifiestoError, match="UTF-8"):
        cargar_proyecto(tmp_path)


def test_un_manifiesto_que_excede_el_tamano_maximo_se_rechaza(
    escribir_manifiesto: EscribirManifiesto,
) -> None:
    relleno = "# " + "x" * lectura.MAX_BYTES_MANIFIESTO + "\n"
    with pytest.raises(ManifiestoError, match="excede el tamano maximo"):
        cargar(escribir_manifiesto, relleno + MANIFIESTO_MINIMO)


def test_un_manifiesto_en_el_limite_exacto_de_tamano_se_acepta(
    escribir_manifiesto: EscribirManifiesto,
) -> None:
    relleno = "#" * (lectura.MAX_BYTES_MANIFIESTO - len(MANIFIESTO_MINIMO.encode()) - 1) + "\n"
    texto = relleno + MANIFIESTO_MINIMO
    assert len(texto.encode()) == lectura.MAX_BYTES_MANIFIESTO
    assert cargar(escribir_manifiesto, texto).identidad.nombre == "demo"


def crear_raiz_con_enlace(tmp_path: Path, texto: str) -> Path:
    """Crea una raiz con el manifiesto dado y un enlace ``enlace`` hacia una carpeta externa."""
    fuera = tmp_path / "fuera"
    fuera.mkdir()
    raiz = tmp_path / "raiz"
    raiz.mkdir()
    (raiz / "psxdecomp.toml").write_text(texto, encoding="utf-8")
    try:
        (raiz / "enlace").symlink_to(fuera, target_is_directory=True)
    except OSError:
        pytest.skip("el sistema no permite crear enlaces simbolicos")
    return raiz


def test_una_ruta_cuyo_enlace_simbolico_escapa_de_la_raiz_se_rechaza(tmp_path: Path) -> None:
    raiz = crear_raiz_con_enlace(tmp_path, MANIFIESTO_MINIMO + '\n[rutas]\nfuentes = "enlace/src"\n')
    with pytest.raises(ManifiestoError, match=r"\[rutas\]\.fuentes"):
        cargar_proyecto(raiz)


def test_la_referencia_que_escapa_por_enlace_simbolico_tambien_se_rechaza(tmp_path: Path) -> None:
    texto = MANIFIESTO_MINIMO.replace('nombre = "demo"', 'nombre = "demo"\nreferencia = "enlace/e.json"')
    raiz = crear_raiz_con_enlace(tmp_path, texto)
    with pytest.raises(ManifiestoError, match=r"\[proyecto\]\.referencia"):
        cargar_proyecto(raiz)

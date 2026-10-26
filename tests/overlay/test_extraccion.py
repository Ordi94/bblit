import json
import re
from pathlib import Path

import pytest
from tools.bzz.descompresion import descomprimir
from tools.overlay import dominio, extraccion
from tools.overlay.dominio import VarianteConocida, VarianteExtraida

from tests.bzz.ayudantes import construir_bzz, flujo_literales
from tests.overlay.ayudantes import (
    construir_overlay,
    contenedor,
    escribir_sistema_de_archivos,
    variantes_conocidas,
)
from tests.toolchain.ayudantes import construir_iso

A = construir_overlay(1)
B = construir_overlay(2)
CONOCIDAS = variantes_conocidas({"a": A, "b": B}, {"a": 2, "b": 1})
DISCO = {
    "LEVEL1/L01A.BZZ": contenedor(A),
    "LEVEL1/L01B.BZZ": contenedor(A),
    "DEMO/DEMO1.BZZ": contenedor(B),
    "LOADING/CARGA.BZZ": contenedor(None),
}


def test_extraer_codigo_devuelve_la_seccion_de_tipo_dos() -> None:
    assert extraccion.extraer_codigo(contenedor(A)) == A
    assert extraccion.extraer_codigo(contenedor(None)) is None


def test_extraer_codigo_rechaza_dos_secciones_de_codigo() -> None:
    doble = construir_bzz([(2, flujo_literales(A)), (2, flujo_literales(B))])
    with pytest.raises(ValueError, match="hay 2 secciones de tipo 2, se esperaba 1"):
        extraccion.extraer_codigo(doble)


def test_extraer_codigo_rechaza_flujo_corrupto() -> None:
    corrupto = construir_bzz([(2, b"\x0b\x00\x00\x09\x00")])
    with pytest.raises(ValueError, match="seccion 0"):
        extraccion.extraer_codigo(corrupto)


def test_extraer_codigo_rechaza_cabecera_invalida() -> None:
    with pytest.raises(ValueError, match="archivo demasiado corto"):
        extraccion.extraer_codigo(b"corto")


def test_extraer_codigo_valida_el_consumo_del_flujo() -> None:
    flujo = bytearray(flujo_literales(A))
    flujo[1:4] = (len(A) // 2).to_bytes(3, "big")
    with pytest.raises(ValueError, match="bytes"):
        extraccion.extraer_codigo(construir_bzz([(2, bytes(flujo))]))


def test_la_extraccion_es_la_descompresion_del_flujo() -> None:
    assert descomprimir(flujo_literales(A)) == A


def test_contenedores_de_un_sistema_de_archivos_extraido(tmp_path: Path) -> None:
    disco = escribir_sistema_de_archivos(tmp_path / "disco (copia)", DISCO)
    nombres = [nombre for nombre, _ in extraccion.contenedores_del_disco(disco)]
    assert nombres == ["DEMO/DEMO1.BZZ", "LEVEL1/L01A.BZZ", "LEVEL1/L01B.BZZ", "LOADING/CARGA.BZZ"]


def test_contenedores_de_una_imagen_en_las_tres_formas(tmp_path: Path) -> None:
    arbol = {
        "LEVEL1": {"L01A.BZZ": DISCO["LEVEL1/L01A.BZZ"]},
        "LEER.TXT": b"x",
        "DEMO": {"D.BZZ": DISCO["DEMO/DEMO1.BZZ"]},
    }
    imagen = tmp_path / "juego" / "disco.bin"
    imagen.parent.mkdir()
    imagen.write_bytes(construir_iso(arbol, modo2352=True))
    cue = imagen.with_suffix(".cue")
    cue.write_text("FILE disco.bin BINARY\n", encoding="utf-8")
    esperado = [("DEMO/D.BZZ", DISCO["DEMO/DEMO1.BZZ"]), ("LEVEL1/L01A.BZZ", DISCO["LEVEL1/L01A.BZZ"])]
    for disc in (imagen, cue, imagen.parent, tmp_path):
        assert list(extraccion.contenedores_del_disco(disc)) == esperado


def test_contenedores_exigen_disco_existente_con_contenido(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="falta la ubicacion del disco"):
        list(extraccion.contenedores_del_disco(None))
    with pytest.raises(FileNotFoundError, match="no existe"):
        list(extraccion.contenedores_del_disco(tmp_path / "ausente"))
    with pytest.raises(FileNotFoundError, match="no se encontro fs/"):
        list(extraccion.contenedores_del_disco(tmp_path))


def test_contenedores_rechazan_mas_de_la_cota(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dominio, "MAX_ARCHIVOS_BZZ", 1)
    disco = escribir_sistema_de_archivos(tmp_path / "d", DISCO)
    with pytest.raises(ValueError, match="el maximo admitido es 1"):
        list(extraccion.contenedores_del_disco(disco))
    imagen = tmp_path / "i.bin"
    imagen.write_bytes(construir_iso({"A.BZZ": DISCO["LEVEL1/L01A.BZZ"], "B.BZZ": DISCO["LEVEL1/L01B.BZZ"]}))
    with pytest.raises(ValueError, match="el maximo admitido es 1"):
        list(extraccion.contenedores_del_disco(imagen))


def test_contenedores_de_imagen_rechazan_archivos_enormes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(extraccion, "TAMANO_MAXIMO_ARCHIVO", 10)
    imagen = tmp_path / "i.bin"
    imagen.write_bytes(construir_iso({"A.BZZ": DISCO["LEVEL1/L01A.BZZ"]}))
    with pytest.raises(ValueError, match="supera el maximo admitido"):
        list(extraccion.contenedores_del_disco(imagen))


def test_extraer_variantes_desde_fs_e_imagen_son_identicas(tmp_path: Path) -> None:
    disco = escribir_sistema_de_archivos(tmp_path / "d", DISCO)
    imagen = tmp_path / "i.bin"
    arbol = {"LEVEL1": {"L01A.BZZ": DISCO["LEVEL1/L01A.BZZ"], "L01B.BZZ": DISCO["LEVEL1/L01B.BZZ"]}}
    arbol |= {
        "DEMO": {"DEMO1.BZZ": DISCO["DEMO/DEMO1.BZZ"]},
        "LOADING": {"CARGA.BZZ": DISCO["LOADING/CARGA.BZZ"]},
    }
    imagen.write_bytes(construir_iso(arbol))
    desde_fs = extraccion.extraer_variantes(disco, CONOCIDAS)
    assert desde_fs == extraccion.extraer_variantes(imagen, CONOCIDAS)
    assert desde_fs == extraccion.extraer_variantes(disco, CONOCIDAS)
    variantes, binarios = desde_fs
    assert [(v.identificador, v.archivos) for v in variantes] == [
        ("a", ("LEVEL1/L01A.BZZ", "LEVEL1/L01B.BZZ")),
        ("b", ("DEMO/DEMO1.BZZ",)),
    ]
    assert binarios == {"a": A, "b": B}


def test_extraer_variantes_nombra_el_contenedor_defectuoso(tmp_path: Path) -> None:
    disco = escribir_sistema_de_archivos(tmp_path / "d", {**DISCO, "DEMO/ROTO.BZZ": b"corto"})
    with pytest.raises(ValueError, match=re.escape("DEMO/ROTO.BZZ: archivo demasiado corto")):
        extraccion.extraer_variantes(disco, CONOCIDAS)


def test_extraer_variantes_rechaza_un_disco_de_otra_edicion(tmp_path: Path) -> None:
    disco = escribir_sistema_de_archivos(tmp_path / "d", DISCO)
    with pytest.raises(ValueError, match="variante desconocida del overlay"):
        extraccion.extraer_variantes(disco)


def test_escribir_y_leer_la_extraccion(tmp_path: Path) -> None:
    variantes, binarios = dominio.identificar_variantes(
        dominio.agrupar_por_huella([("A/X.BZZ", A), ("A/Y.BZZ", A), ("B/Z.BZZ", B)]), CONOCIDAS
    )
    extraccion.escribir_extraccion(tmp_path, variantes, binarios)
    assert (tmp_path / "expected" / "overlay" / "a.bin").read_bytes() == A
    assert extraccion.leer_variantes(tmp_path, CONOCIDAS) == variantes
    assert json.loads((tmp_path / "config" / "overlay.json").read_text(encoding="utf-8"))["tipoSeccion"] == 2
    assert extraccion.leer_binario(tmp_path, variantes[1]) == B
    primero = (tmp_path / "config" / "overlay.json").read_bytes()
    extraccion.escribir_extraccion(tmp_path, variantes, binarios)
    assert (tmp_path / "config" / "overlay.json").read_bytes() == primero


def test_leer_variantes_rechaza_configuraciones_defectuosas(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="ejecute primero 'extraer'"):
        extraccion.leer_variantes(tmp_path)
    ruta = tmp_path / "config" / "overlay.json"
    ruta.parent.mkdir()
    ruta.write_text("{no es json", encoding="utf-8")
    with pytest.raises(ValueError, match="no es JSON valido"):
        extraccion.leer_variantes(tmp_path)
    ruta.write_bytes(b" " * (dominio.MAX_BYTES_CONFIG + 1))
    with pytest.raises(ValueError, match="excede el tamano permitido"):
        extraccion.leer_variantes(tmp_path)
    ruta.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="debe ser un objeto"):
        extraccion.leer_variantes(tmp_path)


def test_leer_binario_rechaza_archivos_ausentes_alterados_o_enormes(tmp_path: Path) -> None:
    variante = VarianteExtraida("a", dominio.huella_sha256(A), len(A), ("X.BZZ",))
    with pytest.raises(FileNotFoundError, match=re.escape("falta expected/overlay/a.bin")):
        extraccion.leer_binario(tmp_path, variante)
    ruta = tmp_path / "expected" / "overlay" / "a.bin"
    ruta.parent.mkdir(parents=True)
    ruta.write_bytes(A[:-4] + b"\x00\x00\x00\x00")
    with pytest.raises(ValueError, match=re.escape("no coincide con config/overlay.json")):
        extraccion.leer_binario(tmp_path, variante)
    ruta.write_bytes(bytes(dominio.TAMANO_HUECO + 4))
    with pytest.raises(ValueError, match="excede el hueco"):
        extraccion.leer_binario(tmp_path, variante)


def test_las_variantes_conocidas_sinteticas_tienen_huella_y_tamano() -> None:
    assert [isinstance(v, VarianteConocida) for v in CONOCIDAS] == [True, True]
    assert CONOCIDAS[0].sha256 == dominio.huella_sha256(A)

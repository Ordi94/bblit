"""Pruebas de la capa de lectura: archivos, manifiesto, desempaquetado e inventario."""

import csv
import hashlib
import json
import re
from pathlib import Path

import pytest
from tools.bzz import lectura
from tools.bzz.dominio import TAMANO_SECTOR, leer_cabecera
from tools.bzz.lectura import (
    COLUMNAS_INVENTARIO,
    construir_manifiesto,
    descomprimir_secciones,
    desempaquetar,
    generar_inventario,
    leer_archivo_bzz,
)

from tests.bzz.ayudantes import comprimir, construir_bzz, flujo_literales

CONTENIDO_A = b"hola hola hola mundo"
CONTENIDO_B = bytes(range(200)) * 3


def _contenedor() -> bytes:
    secciones = [(1, comprimir(CONTENIDO_A)), (3, comprimir(CONTENIDO_B)), (4, flujo_literales(b"fin"))]
    return construir_bzz(secciones)


def test_lee_el_archivo_completo(tmp_path: Path) -> None:
    ruta = tmp_path / "A.BZZ"
    ruta.write_bytes(b"contenido")
    assert leer_archivo_bzz(ruta) == b"contenido"


def test_rechaza_archivos_mayores_al_maximo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ruta = tmp_path / "A.BZZ"
    ruta.write_bytes(b"0123456789")
    monkeypatch.setattr(lectura, "TAMANO_MAXIMO_ARCHIVO", 9)
    with pytest.raises(ValueError) as error:
        leer_archivo_bzz(ruta)
    assert str(error.value) == "tamano del archivo=10 supera el maximo de 9"


def test_descomprime_cada_seccion_en_orden() -> None:
    elementos = list(descomprimir_secciones(_contenedor()))
    assert [e.seccion.indice for e in elementos] == [0, 1, 2]
    assert [e.datos for e in elementos] == [CONTENIDO_A, CONTENIDO_B, b"fin"]
    assert [e.sha256 for e in elementos] == [hashlib.sha256(e.datos).hexdigest() for e in elementos]
    assert all(e.segundos >= 0 for e in elementos)


def test_acepta_una_cabecera_ya_leida() -> None:
    datos = _contenedor()
    elementos = list(descomprimir_secciones(datos, leer_cabecera(datos)))
    assert len(elementos) == 3


def test_el_error_de_una_seccion_indica_su_indice() -> None:
    # el segundo flujo declara 4999 operaciones pero ocupa un sector exacto de bytes 0xFF
    flujo_corto = bytes([0x0B, 0x00, 0x13, 0x87]) + bytes([0xFF]) * (TAMANO_SECTOR - 4)
    datos = construir_bzz([(1, flujo_literales(b"ok")), (3, flujo_corto)])
    with pytest.raises(ValueError) as error:
        list(descomprimir_secciones(datos))
    assert str(error.value) == (
        "seccion 1: flujo comprimido truncado: se agoto antes de completar las operaciones"
    )


def test_manifiesto_tiene_los_campos_camel_case_exactos() -> None:
    datos = _contenedor()
    cabecera = leer_cabecera(datos)
    manifiesto = construir_manifiesto("X.BZZ", cabecera, list(descomprimir_secciones(datos)))
    assert list(manifiesto) == ["archivo", "version", "secciones"]
    assert manifiesto["archivo"] == "X.BZZ"
    assert manifiesto["version"] == 1
    secciones = manifiesto["secciones"]
    assert isinstance(secciones, list)
    assert list(secciones[1]) == [
        "indice",
        "tipo",
        "offset",
        "tamanoComprimido",
        "tamanoAlineado",
        "tamanoDescomprimido",
        "sha256",
    ]
    assert secciones[1] == {
        "indice": 1,
        "tipo": 3,
        "offset": cabecera.secciones[1].offset,
        "tamanoComprimido": cabecera.secciones[1].tamano,
        "tamanoAlineado": cabecera.secciones[1].tamano_alineado,
        "tamanoDescomprimido": len(CONTENIDO_B),
        "sha256": hashlib.sha256(CONTENIDO_B).hexdigest(),
    }


def test_manifiesto_rechaza_cantidades_distintas() -> None:
    datos = _contenedor()
    with pytest.raises(ValueError) as error:
        construir_manifiesto("X.BZZ", leer_cabecera(datos), [])
    assert str(error.value) == "secciones=0 distinto de la cabecera=3"


def test_desempaquetar_escribe_secciones_y_manifiesto(tmp_path: Path) -> None:
    origen = tmp_path / "NIVEL.BZZ"
    origen.write_bytes(_contenedor())
    destino = tmp_path / "salida" / "nivel"
    manifiesto = desempaquetar(origen, destino)
    assert sorted(p.name for p in destino.iterdir()) == [
        "00_tipo01.bin",
        "01_tipo03.bin",
        "02_tipo04.bin",
        "manifiesto.json",
    ]
    assert (destino / "00_tipo01.bin").read_bytes() == CONTENIDO_A
    assert (destino / "01_tipo03.bin").read_bytes() == CONTENIDO_B
    assert (destino / "02_tipo04.bin").read_bytes() == b"fin"
    assert json.loads((destino / "manifiesto.json").read_text(encoding="utf-8")) == manifiesto
    assert manifiesto["archivo"] == "NIVEL.BZZ"


def test_desempaquetar_no_deja_salidas_si_la_cabecera_es_invalida(tmp_path: Path) -> None:
    origen = tmp_path / "MAL.BZZ"
    origen.write_bytes(bytes(0x800))
    with pytest.raises(ValueError):
        desempaquetar(origen, tmp_path / "salida")
    assert not (tmp_path / "salida").exists()


def test_inventario_escribe_una_fila_por_seccion(tmp_path: Path) -> None:
    carpeta = tmp_path / "fs"
    (carpeta / "B").mkdir(parents=True)
    (carpeta / "A").mkdir()
    (carpeta / "B" / "DOS.BZZ").write_bytes(construir_bzz([(1, flujo_literales(b"dos"))]))
    (carpeta / "A" / "UNO.BZZ").write_bytes(_contenedor())
    (carpeta / "A" / "LEEME.TXT").write_text("no es un contenedor", encoding="utf-8")
    salida = tmp_path / "informes" / "inventario.csv"

    filas = generar_inventario(carpeta, salida)

    assert filas == 4
    with salida.open(newline="", encoding="utf-8") as origen:
        registros = list(csv.reader(origen))
    assert tuple(registros[0]) == COLUMNAS_INVENTARIO
    assert [fila[:3] for fila in registros[1:]] == [
        ["A/UNO.BZZ", "0", "1"],
        ["A/UNO.BZZ", "1", "3"],
        ["A/UNO.BZZ", "2", "4"],
        ["B/DOS.BZZ", "0", "1"],
    ]
    segunda = registros[2]
    assert segunda[3:7] == [
        "4096",
        str(leer_cabecera(_contenedor()).secciones[1].tamano),
        str(len(CONTENIDO_B)),
        hashlib.sha256(CONTENIDO_B).hexdigest(),
    ]
    assert re.fullmatch(r"\d+\.\d{4}", segunda[7])


def test_inventario_nombra_el_archivo_invalido_sin_rutas_absolutas(tmp_path: Path) -> None:
    carpeta = tmp_path / "fs"
    carpeta.mkdir()
    (carpeta / "MAL.BZZ").write_bytes(bytes(0x800))
    with pytest.raises(ValueError) as error:
        generar_inventario(carpeta, tmp_path / "inventario.csv")
    assert str(error.value) == "MAL.BZZ: version=0 no soportada, se esperaba 1"
    assert str(tmp_path) not in str(error.value)


def test_n_reducido_se_detecta_porque_el_consumo_no_concuerda_con_el_tamano() -> None:
    contenido = bytes(range(256)) * 4
    flujo = bytearray(comprimir(contenido))
    n = (flujo[1] << 16) | (flujo[2] << 8) | flujo[3]
    reducido = n // 2
    flujo[1:4] = bytes([(reducido >> 16) & 0xFF, (reducido >> 8) & 0xFF, reducido & 0xFF])
    datos = construir_bzz([(1, bytes(flujo))])
    with pytest.raises(
        ValueError, match=r"^secciones\[0\]: bytes consumidos=\d+ no concuerda con tamano=\d+"
    ):
        list(descomprimir_secciones(datos))


def test_una_seccion_valida_que_consume_un_byte_mas_que_su_tamano_no_falla() -> None:
    # literales con tamano declarado un byte menor al consumido (caso real sin relleno final)
    flujo = flujo_literales(b"abcd")
    datos = bytearray(construir_bzz([(1, flujo)]))
    datos[8 + 4 : 8 + 8] = (len(flujo) - 1).to_bytes(4, "little")
    cabecera_suma = sum(v - 256 if v >= 0x80 else v for v in datos[:0x7FC]) & 0xFFFFFFFF
    datos[0x7FC:0x800] = cabecera_suma.to_bytes(4, "little")
    assert next(iter(descomprimir_secciones(bytes(datos)))).datos == b"abcd"

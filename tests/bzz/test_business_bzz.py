"""Reglas de negocio del contenedor BZZ: invariantes, flujos esperados y casos limite."""

import hashlib
import struct
from pathlib import Path

import pytest
from tools.bzz.descompresion import descomprimir, descomprimir_detallado
from tools.bzz.dominio import TAMANO_SECTOR, TIPOS_ADMITIDOS, leer_cabecera
from tools.bzz.lectura import descomprimir_secciones, desempaquetar

from tests.bzz.ayudantes import alinear, comprimir, construir_bzz, flujo_literales

SECCIONES_TIPICAS = [
    (1, comprimir(b"script " * 40)),
    (2, comprimir(bytes(range(256)) * 20)),
    (3, comprimir(b"textura" * 500)),
    (4, flujo_literales(b"tabla")),
    (5, comprimir(bytes(5000))),
]


def _contenedor_tipico() -> bytes:
    return construir_bzz(SECCIONES_TIPICAS)


def test_la_cabecera_ocupa_un_sector_y_la_primera_seccion_empieza_en_el_segundo() -> None:
    cabecera = leer_cabecera(_contenedor_tipico())
    assert cabecera.secciones[0].offset == TAMANO_SECTOR == 0x800


def test_los_offsets_de_las_secciones_son_crecientes_y_contiguos() -> None:
    secciones = leer_cabecera(_contenedor_tipico()).secciones
    esperado = TAMANO_SECTOR
    for seccion in secciones:
        assert seccion.offset == esperado
        esperado += seccion.tamano_alineado
    assert [s.offset for s in secciones] == sorted({s.offset for s in secciones})


def test_la_cabecera_mas_la_suma_de_alineados_iguala_el_tamano_del_archivo() -> None:
    datos = _contenedor_tipico()
    secciones = leer_cabecera(datos).secciones
    assert TAMANO_SECTOR + sum(s.tamano_alineado for s in secciones) == len(datos)


def test_todo_tamano_alineado_es_multiplo_de_sector_y_el_menor_que_contiene_al_tamano() -> None:
    for seccion in leer_cabecera(_contenedor_tipico()).secciones:
        assert seccion.tamano_alineado % TAMANO_SECTOR == 0
        assert seccion.tamano <= seccion.tamano_alineado
        assert seccion.tamano_alineado == alinear(seccion.tamano)


def test_solo_los_tipos_del_uno_al_diez_son_admitidos() -> None:
    assert TIPOS_ADMITIDOS == frozenset(range(1, 11))
    for tipo in TIPOS_ADMITIDOS:
        assert leer_cabecera(construir_bzz([(tipo, flujo_literales(b"x"))])).secciones[0].tipo == tipo
    for tipo in (0, 11, 255):
        with pytest.raises(ValueError, match=r"no admitido"):
            leer_cabecera(construir_bzz([(tipo, flujo_literales(b"x"))]))


def test_un_contenedor_con_sesenta_y_cuatro_secciones_es_valido_y_con_sesenta_y_cinco_no() -> None:
    assert len(leer_cabecera(construir_bzz([(1, flujo_literales(b"x"))] * 64)).secciones) == 64
    with pytest.raises(ValueError, match=r"^n_secciones=65 fuera de rango 1\.\.64$"):
        leer_cabecera(construir_bzz([(1, flujo_literales(b"x"))] * 65))


def test_comprimir_y_descomprimir_son_inversas_con_referencias_de_todas_las_longitudes() -> None:
    base = bytes((indice * 131 + indice // 7 * 17) % 256 for indice in range(300))
    ruido = bytes((indice * indice) % 4 for indice in range(900))
    contenido = base + base[10:60] + b"a" * 40 + base[100:230] + ruido
    flujo = comprimir(contenido)
    assert len(flujo) < len(contenido)
    assert descomprimir(flujo) == contenido


def test_una_referencia_que_se_solapa_con_su_destino_repite_el_patron_de_la_distancia() -> None:
    contenido = b"abc" + b"abc" * 8
    assert descomprimir(comprimir(contenido)) == contenido


def test_la_referencia_final_de_distancia_cero_no_aporta_bytes_ni_cuenta_como_dato() -> None:
    flujo = bytes([0x0B, 0x00, 0x00, 0x02, 0x03, 0x68, 0x69, 0x00, 0x00])
    resultado = descomprimir_detallado(flujo)
    assert resultado.datos == b"hi"
    assert resultado.relleno_final == 3


def test_el_numero_de_operaciones_es_n_mas_uno_y_no_se_leen_mas() -> None:
    flujo = bytes([0x0B, 0x00, 0x00, 0x01, 0xFF, 0x41, 0x42, 0x43, 0x44, 0x45])
    resultado = descomprimir_detallado(flujo)
    assert resultado.datos == b"AB"
    assert resultado.bytes_consumidos == 7


def test_cada_seccion_se_descomprime_de_forma_independiente() -> None:
    elementos = list(descomprimir_secciones(_contenedor_tipico()))
    assert elementos[0].datos == b"script " * 40
    assert elementos[1].datos == bytes(range(256)) * 20
    assert elementos[2].datos == b"textura" * 500
    assert elementos[3].datos == b"tabla"
    assert elementos[4].datos == bytes(5000)


def test_el_relleno_de_sector_no_altera_el_contenido_descomprimido() -> None:
    flujo = comprimir(b"datos repetidos " * 30)
    assert descomprimir(flujo) == descomprimir(flujo + bytes(TAMANO_SECTOR - len(flujo) % TAMANO_SECTOR))


def test_el_manifiesto_registra_el_sha256_del_contenido_descomprimido(tmp_path: Path) -> None:
    origen = tmp_path / "T.BZZ"
    origen.write_bytes(_contenedor_tipico())
    manifiesto = desempaquetar(origen, tmp_path / "salida")
    secciones = manifiesto["secciones"]
    assert isinstance(secciones, list)
    for entrada in secciones:
        archivo = tmp_path / "salida" / f"{entrada['indice']:02d}_tipo{entrada['tipo']:02d}.bin"
        contenido = archivo.read_bytes()
        assert entrada["tamanoDescomprimido"] == len(contenido)
        assert entrada["sha256"] == hashlib.sha256(contenido).hexdigest()


def test_la_cabecera_corrupta_se_detecta_por_la_suma_de_control() -> None:
    datos = bytearray(_contenedor_tipico())
    struct.pack_into("<I", datos, 8, 5)  # cambia el tipo de la primera entrada sin recalcular la suma
    with pytest.raises(ValueError, match=r"^suma_control="):
        leer_cabecera(bytes(datos))


def test_un_flujo_cortado_en_cualquier_punto_se_rechaza_sin_leer_fuera_de_rango() -> None:
    flujo = comprimir(b"abcabcabc" * 50 + bytes(range(100)))
    for corte in range(0, len(flujo), 7):
        with pytest.raises(ValueError, match=r"truncado|demasiado corto"):
            descomprimir(flujo[:corte])
    with pytest.raises(ValueError, match=r"truncado"):
        descomprimir(flujo[:-1])

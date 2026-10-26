"""Decodificacion de PNG y deteccion de pantalla negra sobre imagenes sinteticas y reales."""

import zlib
from pathlib import Path

import pytest
from tools.emulador import pantalla

from tests.emulador import sintetica

ANALISIS = Path(__file__).resolve().parents[3] / "analisis" / "emulador"


def _degradado(ancho: int, alto: int, canales: int) -> bytes:
    return bytes(
        (x * 7 + y * 13 + c * 29) & 0xFF for y in range(alto) for x in range(ancho) for c in range(canales)
    )


@pytest.mark.parametrize("filtro", [0, 1, 2, 3, 4])
def test_cada_filtro_de_fila_se_revierte_a_los_pixeles_originales(filtro):
    pixeles = _degradado(9, 6, 4)
    png = sintetica.construir_png(9, 6, pixeles, tipo=6, filtros=(filtro,))
    assert pantalla.decodificar_png(png).pixeles == pixeles


def test_filtros_mezclados_por_fila_se_revierten():
    pixeles = _degradado(7, 10, 3)
    png = sintetica.construir_png(7, 10, pixeles, tipo=2, filtros=(1, 2, 3, 4, 0))
    imagen = pantalla.decodificar_png(png)
    assert (imagen.ancho, imagen.alto, imagen.canales) == (7, 10, 3)
    assert imagen.pixeles == pixeles


@pytest.mark.parametrize(
    ("tipo", "canales", "color"), [(0, 1, (0,)), (4, 2, (0,)), (2, 3, (0, 1, 2)), (6, 4, (0, 1, 2))]
)
def test_tipos_de_color_declaran_sus_canales(tipo, canales, color):
    png = sintetica.construir_png(4, 3, _degradado(4, 3, canales), tipo=tipo)
    imagen = pantalla.decodificar_png(png)
    assert imagen.canales == canales
    assert imagen.canales_color == color


def test_png_indexado_se_expande_a_rgb():
    paleta = bytes([0, 0, 0, 255, 128, 0])
    png = sintetica.construir_png(2, 2, bytes([0, 1, 1, 0]), tipo=3, paleta=paleta)
    imagen = pantalla.decodificar_png(png)
    assert imagen.canales == 3
    assert imagen.pixeles == bytes([0, 0, 0, 255, 128, 0, 255, 128, 0, 0, 0, 0])


def test_png_indexado_sin_paleta_se_rechaza():
    png = sintetica.construir_png(2, 2, bytes([0, 0, 0, 0]), tipo=3)
    with pytest.raises(ValueError, match="PLTE"):
        pantalla.decodificar_png(png)


def test_indice_fuera_de_la_paleta_se_rechaza():
    png = sintetica.construir_png(2, 1, bytes([0, 5]), tipo=3, paleta=bytes([0, 0, 0, 1, 1, 1]))
    with pytest.raises(ValueError, match="fuera de rango"):
        pantalla.decodificar_png(png)


def test_png_negro_tiene_fraccion_cero_y_es_negro():
    png = sintetica.png_negro()
    assert pantalla.fraccion_con_contenido(pantalla.decodificar_png(png)) == 0.0
    assert pantalla.es_pantalla_negra(png)


def test_png_con_contenido_no_es_negro_y_mide_su_fraccion():
    png = sintetica.png_con_contenido(64, 48, 200, 600)
    assert pantalla.fraccion_con_contenido(pantalla.decodificar_png(png)) == pytest.approx(600 / (64 * 48))
    assert not pantalla.es_pantalla_negra(png)


def test_gris_con_contenido_usa_el_unico_canal_de_color():
    pixeles = bytes([200] * 10 + [0] * 90)
    png = sintetica.construir_png(10, 10, pixeles, tipo=0)
    assert pantalla.fraccion_con_contenido(pantalla.decodificar_png(png)) == 0.1


def test_el_alfa_no_cuenta_como_contenido():
    pixeles = bytes([0, 0, 0, 255]) * 100
    assert pantalla.es_pantalla_negra(sintetica.construir_png(10, 10, pixeles))


def test_pixeles_por_debajo_del_umbral_no_cuentan():
    pixeles = bytes([20, 20, 20, 255]) * 100
    assert pantalla.es_pantalla_negra(sintetica.construir_png(10, 10, pixeles))


def test_un_png_negro_pesado_sigue_siendo_negro():
    # El tamano del archivo no sirve: con ruido en el alfa un PNG negro pesa mucho mas que uno vacio.
    pixeles = b"".join(bytes([0, 0, 0, 255 - (i % 3)]) for i in range(64 * 48))
    png = sintetica.construir_png(64, 48, pixeles, filtros=(0,))
    assert pantalla.es_pantalla_negra(png)


@pytest.mark.parametrize(
    ("datos", "mensaje"),
    [
        (b"no es un png", "firma"),
        (sintetica.png_negro()[:-5], "IEND"),
    ],
)
def test_png_corrupto_se_rechaza(datos, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        pantalla.decodificar_png(datos)


def test_crc_incorrecto_se_rechaza():
    png = bytearray(sintetica.png_negro())
    png[20] ^= 0xFF
    with pytest.raises(ValueError, match="CRC"):
        pantalla.decodificar_png(bytes(png))


def test_png_sin_ihdr_se_rechaza():
    chunks = b"\x89PNG\r\n\x1a\n" + sintetica._chunk(b"IEND", b"")
    with pytest.raises(ValueError, match="IHDR"):
        pantalla.decodificar_png(chunks)


@pytest.mark.parametrize(
    ("kwargs", "mensaje"),
    [
        ({"profundidad": 16}, "profundidad"),
        ({"entrelazado": 1}, "entrelazado"),
    ],
)
def test_formatos_no_soportados_se_rechazan(kwargs, mensaje):
    png = sintetica.construir_png(2, 2, bytes(16), **kwargs)
    with pytest.raises(ValueError, match=mensaje):
        pantalla.decodificar_png(png)


def test_tipo_de_color_desconocido_se_rechaza():
    png = bytearray(sintetica.construir_png(2, 2, bytes(16)))
    png[25] = 5
    # recalcula el CRC de IHDR tras cambiar el tipo
    ihdr = bytes(png[12:29])
    png[29:33] = zlib.crc32(ihdr).to_bytes(4, "big")
    with pytest.raises(ValueError, match="tipo de color"):
        pantalla.decodificar_png(bytes(png))


def test_dimensiones_excesivas_se_rechazan():
    cabecera = sintetica.struct.pack(">IIBBBBB", 100000, 100000, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + sintetica._chunk(b"IHDR", cabecera) + sintetica._chunk(b"IEND", b"")
    with pytest.raises(ValueError, match="fuera de rango"):
        pantalla.decodificar_png(png)


def test_datos_comprimidos_corruptos_se_rechazan():
    base = sintetica.png_negro(4, 4)
    cabecera = base[8 : 8 + 25]
    png = (
        b"\x89PNG\r\n\x1a\n"
        + cabecera
        + sintetica._chunk(b"IDAT", b"basura")
        + sintetica._chunk(b"IEND", b"")
    )
    with pytest.raises(ValueError, match="corruptos"):
        pantalla.decodificar_png(png)


def test_datos_de_imagen_incompletos_se_rechazan():
    cabecera = sintetica.struct.pack(">IIBBBBB", 4, 4, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + sintetica._chunk(b"IHDR", cabecera)
        + sintetica._chunk(b"IDAT", zlib.compress(bytes(10)))
        + sintetica._chunk(b"IEND", b"")
    )
    with pytest.raises(ValueError, match="se esperaban"):
        pantalla.decodificar_png(png)


def test_filtro_de_fila_desconocido_se_rechaza():
    cabecera = sintetica.struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + sintetica._chunk(b"IHDR", cabecera)
        + sintetica._chunk(b"IDAT", zlib.compress(bytes([9, 0])))
        + sintetica._chunk(b"IEND", b"")
    )
    with pytest.raises(ValueError, match="filtro de fila 9"):
        pantalla.decodificar_png(png)


@pytest.mark.skipif(not (ANALISIS / "e2e_titulo.png").exists(), reason="sin capturas de referencia")
@pytest.mark.parametrize("nombre", ["e2e_titulo.png", "titulo.png", "nivel1.png"])
def test_capturas_reales_con_contenido_no_son_negras(nombre):
    assert not pantalla.es_pantalla_negra((ANALISIS / nombre).read_bytes())


@pytest.mark.skipif(
    not (ANALISIS / "captura_negra.png").exists(), reason="sin la captura negra de referencia"
)
@pytest.mark.parametrize("nombre", ["captura_negra.png", "captura_negra_inicio.png"])
def test_capturas_negras_reales_se_clasifican_como_negras(nombre):
    ruta = ANALISIS / nombre
    assert pantalla.fraccion_con_contenido(pantalla.decodificar_png(ruta.read_bytes())) == 0.0
    assert pantalla.es_pantalla_negra(ruta.read_bytes())


def test_chunk_con_longitud_mayor_que_el_archivo_se_rechaza():
    png = sintetica.png_negro()
    truncado = png[:8] + (10**6).to_bytes(4, "big") + png[12:]
    with pytest.raises(ValueError, match="truncado"):
        pantalla.decodificar_png(truncado)

"""
Decodificacion de PNG con biblioteca estandar y deteccion de pantalla negra.

Contexto:
    Capa de dominio de `tools.emulador`. El tamano del archivo PNG no distingue una captura
    negra de una con contenido (una negra llego a pesar 10.117 bytes), asi que la decision se
    toma sobre los pixeles decodificados. Solo se admiten PNG de 8 bits sin entrelazado, que es
    lo que produce el emulador.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

FIRMA_PNG = b"\x89PNG\r\n\x1a\n"
MAX_PIXELES = 4096 * 4096
UMBRAL_BRILLO = 24
FRACCION_MINIMA_CONTENIDO = 0.002

_CANALES_POR_TIPO = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
_CANALES_COLOR = {0: (0,), 2: (0, 1, 2), 3: (0, 1, 2), 4: (0,), 6: (0, 1, 2)}


@dataclass(frozen=True)
class ImagenPng:
    """
    Imagen decodificada a pixeles de 8 bits por canal.

    Contexto:
        Resultado de `decodificar_png`; la consumen `fraccion_con_contenido` y los tests.

    Attributes:
        ancho (int): Ancho en pixeles.
        alto (int): Alto en pixeles.
        canales (int): Canales por pixel tras expandir la paleta (1, 2, 3 o 4).
        canales_color (tuple[int, ...]): Posiciones de los canales que son color (no alfa).
        pixeles (bytes): Datos de las filas concatenadas, sin los bytes de filtro.
    """

    ancho: int
    alto: int
    canales: int
    canales_color: tuple[int, ...]
    pixeles: bytes


def _leer_chunks(datos: bytes) -> list[tuple[bytes, bytes]]:
    """
    Separa un PNG en sus chunks verificando longitudes y el CRC de cada uno.

    Contexto:
        Primer paso de `decodificar_png`.

    Args:
        datos (bytes): Contenido completo del archivo.

    Returns:
        list[tuple[bytes, bytes]]: Pares (tipo, contenido) hasta IEND inclusive.

    Raises:
        ValueError: Si falta la firma, un chunk esta truncado, el CRC no coincide o falta IEND.

    Ejemplo:
        chunks = _leer_chunks(png)
    """
    if not datos.startswith(FIRMA_PNG):
        raise ValueError("PNG: falta la firma de 8 bytes")
    posicion = len(FIRMA_PNG)
    chunks: list[tuple[bytes, bytes]] = []
    while posicion + 12 <= len(datos):
        (largo,) = struct.unpack(">I", datos[posicion : posicion + 4])
        tipo = datos[posicion + 4 : posicion + 8]
        fin = posicion + 8 + largo
        if fin + 4 > len(datos):
            raise ValueError(f"PNG: el chunk {tipo!r} esta truncado")
        contenido = datos[posicion + 8 : fin]
        (crc,) = struct.unpack(">I", datos[fin : fin + 4])
        if zlib.crc32(tipo + contenido) != crc:
            raise ValueError(f"PNG: CRC incorrecto en el chunk {tipo!r}")
        chunks.append((tipo, contenido))
        if tipo == b"IEND":
            return chunks
        posicion = fin + 4
    raise ValueError("PNG: falta el chunk IEND")


def _paeth(a: int, b: int, c: int) -> int:
    """
    Predictor Paeth del filtro 4 de PNG.

    Contexto:
        Lo usa `_quitar_filtros` por cada byte de una fila con ese filtro.

    Args:
        a (int): Byte a la izquierda.
        b (int): Byte de arriba.
        c (int): Byte arriba a la izquierda.

    Returns:
        int: El vecino mas cercano a `a + b - c`.

    Ejemplo:
        _paeth(10, 20, 10)  # 20
    """
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _quitar_filtros(crudo: bytes, alto: int, fila: int, bpp: int) -> bytes:
    """
    Revierte los filtros por fila de PNG (ninguno, Sub, Up, Average, Paeth).

    Contexto:
        Segundo paso de `decodificar_png`, sobre los datos ya descomprimidos.

    Args:
        crudo (bytes): Filas con un byte de filtro al inicio de cada una.
        alto (int): Numero de filas.
        fila (int): Bytes de datos por fila (sin el byte de filtro).
        bpp (int): Bytes por pixel.

    Returns:
        bytes: Filas reconstruidas, concatenadas.

    Raises:
        ValueError: Si el tamano no coincide o hay un tipo de filtro desconocido.

    Ejemplo:
        pixeles = _quitar_filtros(crudo, 240, 2048, 4)
    """
    if len(crudo) != alto * (fila + 1):
        raise ValueError(f"PNG: se esperaban {alto * (fila + 1)} bytes de imagen y hay {len(crudo)}")
    salida = bytearray()
    anterior = bytearray(fila)
    for y in range(alto):
        inicio = y * (fila + 1)
        filtro = crudo[inicio]
        actual = bytearray(crudo[inicio + 1 : inicio + 1 + fila])
        if filtro == 1:
            for i in range(bpp, fila):
                actual[i] = (actual[i] + actual[i - bpp]) & 0xFF
        elif filtro == 2:
            for i in range(fila):
                actual[i] = (actual[i] + anterior[i]) & 0xFF
        elif filtro == 3:
            for i in range(fila):
                izquierda = actual[i - bpp] if i >= bpp else 0
                actual[i] = (actual[i] + ((izquierda + anterior[i]) >> 1)) & 0xFF
        elif filtro == 4:
            for i in range(fila):
                izquierda = actual[i - bpp] if i >= bpp else 0
                arriba_izq = anterior[i - bpp] if i >= bpp else 0
                actual[i] = (actual[i] + _paeth(izquierda, anterior[i], arriba_izq)) & 0xFF
        elif filtro != 0:
            raise ValueError(f"PNG: filtro de fila {filtro} desconocido (se esperaba 0 a 4)")
        salida += actual
        anterior = actual
    return bytes(salida)


def _expandir_paleta(indices: bytes, paleta: bytes) -> bytes:
    """
    Sustituye cada indice por su color RGB de la paleta.

    Contexto:
        Solo para PNG de tipo 3 (color indexado).

    Args:
        indices (bytes): Un indice por pixel.
        paleta (bytes): Contenido del chunk PLTE (tripletas RGB).

    Returns:
        bytes: Tres bytes por pixel.

    Raises:
        ValueError: Si un indice apunta fuera de la paleta.

    Ejemplo:
        rgb = _expandir_paleta(bytes([0, 1]), paleta)
    """
    entradas = len(paleta) // 3
    if indices and max(indices) >= entradas:
        raise ValueError(f"PNG: indice de paleta fuera de rango (la paleta tiene {entradas} entradas)")
    return b"".join(paleta[i * 3 : i * 3 + 3] for i in indices)


def decodificar_png(datos: bytes) -> ImagenPng:
    """
    Decodifica un PNG de 8 bits sin entrelazado a pixeles planos.

    Contexto:
        Base de la deteccion de pantalla negra; se aplica a lo que devuelve `screen/still`,
        que es entrada externa y por tanto se valida: firma, CRC, dimensiones acotadas y
        tamano de datos exacto.

    Args:
        datos (bytes): Archivo PNG completo.

    Returns:
        ImagenPng: Imagen con pixeles sin filtros.

    Raises:
        ValueError: Si el PNG esta corrupto, usa un formato no soportado (profundidad distinta
            de 8 bits, entrelazado, tipo de color desconocido) o excede `MAX_PIXELES`.

    Ejemplo:
        imagen = decodificar_png(contenido_png)
    """
    chunks = _leer_chunks(datos)
    cabecera = next((c for t, c in chunks if t == b"IHDR"), None)
    if cabecera is None or len(cabecera) != 13:
        raise ValueError("PNG: cabecera IHDR ausente o de tamano incorrecto")
    ancho, alto, profundidad, tipo, _compresion, _filtro, entrelazado = struct.unpack(">IIBBBBB", cabecera)
    if profundidad != 8:
        raise ValueError(f"PNG: profundidad {profundidad} no soportada (se esperaban 8 bits)")
    if entrelazado != 0:
        raise ValueError("PNG: el entrelazado no esta soportado")
    if tipo not in _CANALES_POR_TIPO:
        raise ValueError(f"PNG: tipo de color {tipo} no soportado")
    if ancho == 0 or alto == 0 or ancho * alto > MAX_PIXELES:
        raise ValueError(f"PNG: dimensiones {ancho}x{alto} fuera de rango (hasta {MAX_PIXELES} pixeles)")
    canales = _CANALES_POR_TIPO[tipo]
    fila = ancho * canales
    esperado = alto * (fila + 1)
    descompresor = zlib.decompressobj()
    try:
        crudo = descompresor.decompress(b"".join(c for t, c in chunks if t == b"IDAT"), esperado + 1)
    except zlib.error:
        raise ValueError("PNG: datos de imagen comprimidos corruptos") from None
    pixeles = _quitar_filtros(crudo, alto, fila, canales)
    if tipo == 3:
        paleta = next((c for t, c in chunks if t == b"PLTE"), None)
        if paleta is None:
            raise ValueError("PNG: falta el chunk PLTE en una imagen indexada")
        return ImagenPng(ancho, alto, 3, (0, 1, 2), _expandir_paleta(pixeles, paleta))
    return ImagenPng(ancho, alto, canales, _CANALES_COLOR[tipo], pixeles)


def fraccion_con_contenido(imagen: ImagenPng, umbral: int = UMBRAL_BRILLO) -> float:
    """
    Calcula la fraccion de pixeles cuyo canal de color mas brillante supera el umbral.

    Contexto:
        Medida que usa `es_pantalla_negra` y que se registra al calibrar los tiempos.

    Args:
        imagen (ImagenPng): Imagen decodificada.
        umbral (int, opcional): Brillo (0 a 255) por encima del cual un pixel cuenta.

    Returns:
        float: Valor entre 0.0 (todo negro) y 1.0.

    Ejemplo:
        fraccion_con_contenido(decodificar_png(png))
    """
    planos = [imagen.pixeles[c :: imagen.canales] for c in imagen.canales_color]
    brillo_maximo = map(max, *planos) if len(planos) > 1 else planos[0]
    brillantes = sum(1 for valor in brillo_maximo if valor > umbral)
    return brillantes / (imagen.ancho * imagen.alto)


def es_pantalla_negra(
    datos_png: bytes,
    umbral: int = UMBRAL_BRILLO,
    fraccion_minima: float = FRACCION_MINIMA_CONTENIDO,
) -> bool:
    """
    Decide si una captura esta negra midiendo sus pixeles, no el tamano del archivo.

    Contexto:
        Condicion de espera del hito `pantalla` en la sesion: el juego solo cuenta como
        arrancado cuando la captura deja de ser negra.

    Args:
        datos_png (bytes): Archivo PNG devuelto por `screen/still`.
        umbral (int, opcional): Brillo minimo para que un pixel cuente como contenido.
        fraccion_minima (float, opcional): Fraccion minima de pixeles con contenido.

    Returns:
        bool: True si la fraccion de pixeles con contenido es menor que `fraccion_minima`.

    Raises:
        ValueError: Si el PNG no se puede decodificar.

    Ejemplo:
        if es_pantalla_negra(png): ...
    """
    return fraccion_con_contenido(decodificar_png(datos_png), umbral) < fraccion_minima

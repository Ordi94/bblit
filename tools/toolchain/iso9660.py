"""Lector minimo de imagenes ISO 9660 en bruto (sectores de 2048 o 2352 bytes).

Las imagenes historicas del SDK se distribuyen como volcados de CD (``.bin``) que ningun
extractor generico abre. Este lector recorre el directorio raiz y sus subdirectorios y
extrae archivos concretos. Toda lectura esta acotada: una imagen corrupta o hostil produce
``ValueError`` y nunca un bucle ni una lectura fuera de rango.
"""

from __future__ import annotations

import struct
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import PurePosixPath

from tools.toolchain.dominio import ruta_miembro_segura

TAMANO_DATOS = 2048
TAMANO_SECTOR_BRUTO = 2352
LBA_VOLUMEN_PRIMARIO = 16
MAX_ENTRADAS = 20000
MAX_PROFUNDIDAD = 16
MAX_TAMANO_DIRECTORIO = 4 * 1024 * 1024
MAX_TAMANO_ARCHIVO = 512 * 1024 * 1024
_OFFSET_DATOS_MODO2 = 24
_OFFSET_DATOS_MODO1 = 16
_FLAG_DIRECTORIO = 0x02

LectorSector = Callable[[int], bytes]
"""Funcion que devuelve los 2048 bytes de datos de un sector logico."""


@dataclass(frozen=True)
class EntradaIso:
    """Un archivo de la imagen.

    Attributes:
        ruta: Ruta normalizada con ``/``, sin el sufijo de version ``;1``.
        lba: Sector logico donde empieza el contenido.
        tamano: Longitud del contenido en bytes.
    """

    ruta: PurePosixPath
    lba: int
    tamano: int


def crear_lector(total: int, leer_rango: Callable[[int, int], bytes]) -> LectorSector:
    """
    Crea un lector de sectores de datos sobre una fuente de bytes con acceso por rango.

    Contexto:
        La extraccion lo construye sobre un archivo abierto (lectura por ``seek``) para no
        cargar en memoria imagenes de cientos de megabytes; las pruebas lo construyen sobre
        ``bytes``.

    Args:
        total (int): Tamano total de la imagen en bytes.
        leer_rango (Callable[[int, int], bytes]): Funcion ``(desplazamiento, longitud) -> bytes``.

    Returns:
        LectorSector: Funcion ``lba -> bytes`` que valida el rango y el modo del sector.

    Raises:
        ValueError: Si el tamano no es multiplo de 2352 ni de 2048.

    Ejemplo:
        lector = crear_lector(len(datos), lambda desde, largo: datos[desde : desde + largo])
    """
    if total >= TAMANO_SECTOR_BRUTO and total % TAMANO_SECTOR_BRUTO == 0:
        paso = TAMANO_SECTOR_BRUTO
    elif total >= TAMANO_DATOS and total % TAMANO_DATOS == 0:
        paso = TAMANO_DATOS
    else:
        raise ValueError("la imagen no tiene un tamano de sector reconocido (2048 o 2352)")

    def leer(lba: int) -> bytes:
        if lba < 0 or (lba + 1) * paso > total:
            raise ValueError("sector fuera de los limites de la imagen")
        base = lba * paso
        if paso == TAMANO_DATOS:
            return leer_rango(base, TAMANO_DATOS)
        cabecera = leer_rango(base, 16)
        offset = _OFFSET_DATOS_MODO1 if cabecera[15] == 1 else _OFFSET_DATOS_MODO2
        return leer_rango(base + offset, TAMANO_DATOS)

    return leer


def _leer_extension(lector: LectorSector, lba: int, tamano: int) -> bytes:
    """Concatena los sectores que cubren ``tamano`` bytes empezando en ``lba``."""
    sectores = (tamano + TAMANO_DATOS - 1) // TAMANO_DATOS
    bloque = b"".join(lector(lba + i) for i in range(sectores))
    return bloque[:tamano]


def _registros(directorio: bytes) -> Iterator[tuple[str, int, int, bool]]:
    """Itera los registros de un directorio: (nombre, lba, tamano, es_directorio)."""
    pos = 0
    while pos < len(directorio):
        longitud = directorio[pos]
        if longitud == 0:
            pos = (pos // TAMANO_DATOS + 1) * TAMANO_DATOS
            continue
        if longitud < 34 or pos + longitud > len(directorio):
            raise ValueError("registro de directorio corrupto")
        lba = struct.unpack_from("<I", directorio, pos + 2)[0]
        tamano = struct.unpack_from("<I", directorio, pos + 10)[0]
        banderas = directorio[pos + 25]
        largo_nombre = directorio[pos + 32]
        if 33 + largo_nombre > longitud:
            raise ValueError("nombre de registro fuera de limites")
        nombre = directorio[pos + 33 : pos + 33 + largo_nombre]
        pos += longitud
        if nombre in (b"\x00", b"\x01"):
            continue
        yield nombre.decode("latin-1"), lba, tamano, bool(banderas & _FLAG_DIRECTORIO)


def listar_archivos(lector: LectorSector) -> list[EntradaIso]:
    """
    Recorre toda la imagen y devuelve sus archivos.

    Contexto:
        Primer paso de la extraccion de un componente distribuido como imagen de CD.

    Args:
        lector (LectorSector): Lector de sectores de datos.

    Returns:
        list[EntradaIso]: Archivos con ruta normalizada, sector inicial y tamano.

    Raises:
        ValueError: Si falta el descriptor de volumen, hay mas de ``MAX_ENTRADAS`` entradas,
            los directorios anidan mas de ``MAX_PROFUNDIDAD`` niveles, o algun registro,
            tamano o ruta no cumple las cotas.

    Ejemplo:
        archivos = listar_archivos(crear_lector(datos))
    """
    volumen = lector(LBA_VOLUMEN_PRIMARIO)
    if volumen[1:6] != b"CD001":
        raise ValueError("la imagen no contiene un descriptor de volumen ISO 9660")
    raiz_lba = struct.unpack_from("<I", volumen, 158)[0]
    raiz_tamano = struct.unpack_from("<I", volumen, 166)[0]
    resultado: list[EntradaIso] = []

    def recorrer(lba: int, tamano: int, prefijo: str, profundidad: int) -> None:
        if profundidad > MAX_PROFUNDIDAD:
            raise ValueError("directorios anidados por encima de la cota permitida")
        if tamano > MAX_TAMANO_DIRECTORIO:
            raise ValueError("directorio demasiado grande")
        for nombre, hijo_lba, hijo_tamano, es_dir in _registros(_leer_extension(lector, lba, tamano)):
            if len(resultado) >= MAX_ENTRADAS:
                raise ValueError("la imagen excede el maximo de entradas permitido")
            ruta = f"{prefijo}/{nombre.split(';')[0]}" if prefijo else nombre.split(";")[0]
            if es_dir:
                recorrer(hijo_lba, hijo_tamano, ruta, profundidad + 1)
            else:
                if hijo_tamano > MAX_TAMANO_ARCHIVO:
                    raise ValueError("archivo de la imagen excede el tamano maximo permitido")
                resultado.append(EntradaIso(ruta_miembro_segura(ruta), hijo_lba, hijo_tamano))

    recorrer(raiz_lba, raiz_tamano, "", 0)
    return resultado


def leer_archivo(lector: LectorSector, entrada: EntradaIso) -> bytes:
    """
    Lee el contenido completo de un archivo de la imagen.

    Contexto:
        Segundo paso de la extraccion, aplicado solo a los archivos que pasan el filtro.

    Args:
        lector (LectorSector): Lector de sectores de datos.
        entrada (EntradaIso): Archivo a leer, obtenido de ``listar_archivos``.

    Returns:
        bytes: Contenido exacto del archivo (sin el relleno del ultimo sector).

    Raises:
        ValueError: Si algun sector cae fuera de la imagen.

    Ejemplo:
        datos = leer_archivo(lector, entrada)
    """
    return _leer_extension(lector, entrada.lba, entrada.tamano)

"""Construccion de datos de prueba para el toolchain: locks, respuestas HTTP e imagenes ISO."""

from __future__ import annotations

import hashlib
import io
import struct
import zipfile
from collections.abc import Iterator
from typing import Any

import requests


def sha256_de(datos: bytes) -> str:
    """Huella SHA-256 hexadecimal de unos bytes."""
    return hashlib.sha256(datos).hexdigest()


def bloque_componente(datos: bytes, **cambios: Any) -> dict[str, Any]:
    """Bloque JSON valido de un componente cuyo archivo descargado es ``datos``."""
    bloque: dict[str, Any] = {
        "url": "https://github.com/ejemplo/proyecto/archive/abc123.zip",
        "sha256": sha256_de(datos),
        "fecha_registro": "2026-10-25",
        "formato": "zip",
        "notas": "Componente de prueba.",
    }
    bloque.update(cambios)
    return bloque


def lock_de(**componentes: dict[str, Any]) -> dict[str, Any]:
    """Documento de lock con los componentes dados."""
    return {"version": 1, "componentes": componentes}


def zip_de(miembros: dict[str, bytes]) -> bytes:
    """Zip en memoria con los miembros indicados (nombres tal cual, incluso hostiles)."""
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as zf:
        for nombre, contenido in miembros.items():
            zf.writestr(nombre, contenido)
    return memoria.getvalue()


class RespuestaFalsa:
    """Respuesta HTTP en memoria que imita la parte de ``requests.Response`` usada."""

    def __init__(
        self, cuerpo: bytes, url: str, error: Exception | None = None, falla_a_mitad: bool = False
    ) -> None:
        self._cuerpo = cuerpo
        self.url = url
        self._error = error
        self._falla_a_mitad = falla_a_mitad
        self.cerrada = False

    def raise_for_status(self) -> None:
        """Lanza el error configurado, si lo hay."""
        if self._error is not None:
            raise self._error

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        """Entrega el cuerpo en bloques; opcionalmente corta a la mitad con un error de red."""
        mitad = len(self._cuerpo) // 2
        for inicio in range(0, len(self._cuerpo), max(1, min(chunk_size, 3))):
            if self._falla_a_mitad and inicio >= mitad:
                raise requests.ConnectionError("corte")
            yield self._cuerpo[inicio : inicio + max(1, min(chunk_size, 3))]

    def close(self) -> None:
        """Marca la respuesta como cerrada."""
        self.cerrada = True


class SesionFalsa:
    """Sesion HTTP que siempre devuelve la misma respuesta y registra las llamadas."""

    def __init__(self, respuesta: RespuestaFalsa | None = None, error: Exception | None = None) -> None:
        self.respuesta = respuesta
        self.error = error
        self.llamadas: list[tuple[str, bool, tuple[int, int]]] = []

    def get(self, url: str, *, stream: bool, timeout: tuple[int, int]) -> RespuestaFalsa:
        """Registra la llamada y devuelve la respuesta o lanza el error configurado."""
        self.llamadas.append((url, stream, timeout))
        if self.error is not None:
            raise self.error
        assert self.respuesta is not None
        return self.respuesta


def _registro(nombre: bytes, lba: int, tamano: int, directorio: bool) -> bytes:
    """Registro de directorio ISO 9660 con los campos que lee el lector."""
    longitud = 33 + len(nombre)
    longitud += longitud % 2
    registro = bytearray(longitud)
    registro[0] = longitud
    struct.pack_into("<I", registro, 2, lba)
    struct.pack_into("<I", registro, 10, tamano)
    registro[25] = 2 if directorio else 0
    registro[32] = len(nombre)
    registro[33 : 33 + len(nombre)] = nombre
    return bytes(registro)


def construir_iso(
    arbol: dict[str, Any], modo2352: bool = False, modo_sector: int = 2, alinear_registros: bool = False
) -> bytes:
    """
    Construye una imagen ISO 9660 minima.

    ``arbol`` mapea nombre a bytes (archivo) o a otro diccionario (carpeta). Con
    ``modo2352`` cada sector lleva la cabecera de 16 bytes y el prefijo de modo 2.
    """
    sectores: dict[int, bytes] = {}
    siguiente = [18]

    def reservar(datos: bytes) -> int:
        lba = siguiente[0]
        cuenta = max(1, (len(datos) + 2047) // 2048)
        for i in range(cuenta):
            sectores[lba + i] = datos[i * 2048 : (i + 1) * 2048].ljust(2048, b"\x00")
        siguiente[0] += cuenta
        return lba

    def escribir_directorio(contenido: dict[str, Any]) -> tuple[int, int]:
        registros = [_registro(b"\x00", 0, 0, True), _registro(b"\x01", 0, 0, True)]
        for nombre, valor in contenido.items():
            if isinstance(valor, dict):
                lba_hijo, tamano_hijo = escribir_directorio(valor)
                registros.append(_registro(nombre.encode("latin-1"), lba_hijo, tamano_hijo, True))
            else:
                lba_archivo = reservar(valor)
                registros.append(_registro(f"{nombre};1".encode("latin-1"), lba_archivo, len(valor), False))
        datos = b""
        for registro in registros:
            if alinear_registros and (len(datos) % 2048) + len(registro) > 2048:
                datos += b"\x00" * (2048 - len(datos) % 2048)
            datos += registro
        return reservar(datos), len(datos)

    lba_raiz, tamano_raiz = escribir_directorio(arbol)
    volumen = bytearray(2048)
    volumen[0] = 1
    volumen[1:6] = b"CD001"
    volumen[156 : 156 + 34] = _registro(b"\x00", lba_raiz, tamano_raiz, True)[:34].ljust(34, b"\x00")
    struct.pack_into("<I", volumen, 158, lba_raiz)
    struct.pack_into("<I", volumen, 166, tamano_raiz)
    sectores[16] = bytes(volumen)
    total = max(sectores) + 1
    salida = bytearray()
    for lba in range(total):
        datos = sectores.get(lba, b"\x00" * 2048)
        if modo2352:
            cabecera = bytearray(16)
            cabecera[15] = modo_sector
            relleno = b"\x00" * 8 if modo_sector == 2 else b""
            salida += bytes(cabecera) + relleno + datos + b"\x00" * (2352 - 16 - len(relleno) - 2048)
        else:
            salida += datos
    return bytes(salida)

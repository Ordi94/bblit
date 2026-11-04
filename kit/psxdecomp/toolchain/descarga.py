"""Descarga de componentes con verificacion SHA-256 antes de dejar el archivo en su destino.

Capa de infraestructura (red y disco). El contrato central: el archivo definitivo solo existe
si su huella coincide con la registrada en el lock; cualquier fallo borra el temporal y no
deja nada en el destino.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit

import requests

from tools.toolchain.dominio import (
    Componente,
    host_admitido,
    nombre_archivo_desde_url,
    verificar_sha256,
)

TAMANO_BLOQUE = 1024 * 1024
MAX_BYTES_DESCARGA = 1024 * 1024 * 1024
TIMEOUT_CONEXION_S = 15
TIMEOUT_LECTURA_S = 120


class RespuestaHttp(Protocol):
    """Parte de ``requests.Response`` que usa la descarga (permite sustituirla en pruebas)."""

    url: str

    def raise_for_status(self) -> None:
        """Lanza una excepcion si el estado HTTP indica error."""

    def iter_content(self, chunk_size: int) -> Iterable[bytes]:
        """Itera el cuerpo de la respuesta por bloques."""

    def close(self) -> None:
        """Libera la conexion."""


class SesionHttp(Protocol):
    """Parte de ``requests.Session`` que usa la descarga."""

    def get(self, url: str, *, stream: bool, timeout: tuple[int, int]) -> RespuestaHttp:
        """Abre una peticion GET en modo flujo."""


def descargar_verificado(
    componente: Componente,
    carpeta: Path,
    sesion: SesionHttp | None = None,
    max_bytes: int = MAX_BYTES_DESCARGA,
) -> Path:
    """
    Descarga el archivo de un componente y lo deja en ``carpeta`` solo si la huella coincide.

    Contexto:
        Primer paso de la instalacion de cada componente. Se escribe primero a un archivo
        temporal con sufijo ``.parcial``; solo tras verificar el SHA-256 se renombra, de modo
        que una descarga interrumpida o alterada nunca se confunde con un archivo bueno.

    Args:
        componente (Componente): Componente a descargar (URL y huella esperada).
        carpeta (Path): Carpeta de destino, se crea si no existe.
        sesion (SesionHttp, opcional): Sesion HTTP; por defecto ``requests.Session()``.
        max_bytes (int, opcional): Cota de tamano; se aborta si el cuerpo la supera.

    Returns:
        Path: Ruta del archivo descargado y verificado.

    Raises:
        ValueError: Si la huella no coincide, la URL final sale de los hosts admitidos o el
            cuerpo supera ``max_bytes``.
        ConnectionError: Si hay un fallo de red o un estado HTTP de error.

    Ejemplo:
        ruta = descargar_verificado(componente, Path("toolchain/maspsx"))
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / nombre_archivo_desde_url(componente.url, componente.nombre)
    temporal = destino.with_name(destino.name + ".parcial")
    sesion = sesion if sesion is not None else requests.Session()
    huella = hashlib.sha256()
    recibido = 0
    try:
        respuesta = sesion.get(componente.url, stream=True, timeout=(TIMEOUT_CONEXION_S, TIMEOUT_LECTURA_S))
        try:
            partes = urlsplit(respuesta.url)
            if partes.scheme != "https" or not host_admitido((partes.hostname or "").lower()):
                raise ValueError(f"componente '{componente.nombre}': redireccion a un host no admitido")
            respuesta.raise_for_status()
            with temporal.open("wb") as salida:
                for bloque in respuesta.iter_content(TAMANO_BLOQUE):
                    recibido += len(bloque)
                    if recibido > max_bytes:
                        raise ValueError(
                            f"componente '{componente.nombre}': la descarga excede {max_bytes} bytes"
                        )
                    huella.update(bloque)
                    salida.write(bloque)
        finally:
            respuesta.close()
        verificar_sha256(componente, huella.hexdigest())
        os.replace(temporal, destino)
    except requests.RequestException:
        _borrar_si_existe(temporal)
        raise ConnectionError(f"componente '{componente.nombre}': fallo de red al descargar") from None
    except BaseException:
        _borrar_si_existe(temporal)
        raise
    return destino


def _borrar_si_existe(ruta: Path) -> None:
    """Elimina un archivo temporal ignorando su ausencia."""
    with contextlib.suppress(FileNotFoundError):
        ruta.unlink()

"""Instalacion idempotente de los componentes del toolchain bajo ``toolchain/<componente>/``.

Orquesta descarga verificada, extraccion y comprobacion de archivos clave. Un componente solo
se considera instalado si existe su marca con la huella vigente del lock y todos sus archivos
clave; en cualquier otro caso se reinstala desde cero.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from tools.toolchain.descarga import SesionHttp, descargar_verificado
from tools.toolchain.dominio import Componente, cargar_lock, obtener_componente
from tools.toolchain.extraccion import extraer

NOMBRE_MARCA = "INSTALADO.json"
CARPETA_DESCARGA = "_descarga"
MAX_BYTES_LOCK = 1024 * 1024


def leer_lock(ruta: Path) -> dict[str, Componente]:
    """
    Lee y valida el archivo de bloqueo del toolchain.

    Contexto:
        Primer paso de cualquier operacion que necesite saber que componentes existen.

    Args:
        ruta (Path): Ubicacion de ``toolchain.lock.json``.

    Returns:
        dict[str, Componente]: Componentes validados.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si es demasiado grande, no es JSON o no cumple el esquema.

    Ejemplo:
        lock = leer_lock(Path("config/toolchain.lock.json"))
    """
    if not ruta.is_file():
        raise FileNotFoundError("no se encontro el archivo de bloqueo del toolchain")
    if ruta.stat().st_size > MAX_BYTES_LOCK:
        raise ValueError("el archivo de bloqueo excede el tamano permitido")
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except ValueError:
        raise ValueError("el archivo de bloqueo no es JSON valido") from None
    return cargar_lock(datos)


def carpeta_componente(raiz: Path, componente: Componente) -> Path:
    """
    Devuelve la carpeta de instalacion de un componente.

    Contexto:
        Cada componente vive en su propia carpeta nueva bajo la raiz del toolchain.

    Args:
        raiz (Path): Raiz del toolchain.
        componente (Componente): Componente cuyo directorio se quiere conocer.

    Returns:
        Path: ``raiz / componente.nombre``.

    Ejemplo:
        carpeta = carpeta_componente(Path("toolchain"), componente)
    """
    return raiz / componente.nombre


def faltantes(componente: Componente, carpeta: Path) -> list[str]:
    """
    Lista los archivos clave del componente que no existen en su carpeta.

    Contexto:
        Permite distinguir una instalacion completa de una interrumpida o incompleta.

    Args:
        componente (Componente): Componente con su lista de archivos clave.
        carpeta (Path): Carpeta de instalacion.

    Returns:
        list[str]: Rutas relativas ausentes (vacia si esta completo).

    Ejemplo:
        ausentes = faltantes(componente, Path("toolchain/maspsx"))
    """
    return [ruta for _alias, ruta in componente.archivos_clave if not (carpeta / ruta).is_file()]


def esta_instalado(componente: Componente, carpeta: Path) -> bool:
    """
    Indica si el componente esta instalado con la huella vigente del lock.

    Contexto:
        Decide si ``instalar`` puede saltarse un componente (idempotencia).

    Args:
        componente (Componente): Componente esperado.
        carpeta (Path): Carpeta de instalacion.

    Returns:
        bool: ``True`` si la marca existe, coincide con la huella del lock y no faltan archivos.

    Ejemplo:
        if esta_instalado(componente, carpeta): ...
    """
    marca = carpeta / NOMBRE_MARCA
    if not marca.is_file():
        return False
    try:
        datos = json.loads(marca.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(datos, dict) or datos.get("sha256") != componente.sha256:
        return False
    return not faltantes(componente, carpeta)


def instalar_componente(
    componente: Componente,
    raiz: Path,
    sesion: SesionHttp | None = None,
    siete_zip: Path | None = None,
    conservar_descarga: bool = False,
) -> Path:
    """
    Descarga, verifica, extrae y registra un componente.

    Contexto:
        Unidad de trabajo de ``instalar``. Si la carpeta existe sin marca vigente se borra
        entera antes de empezar, para no mezclar contenido de versiones distintas.

    Args:
        componente (Componente): Componente a instalar.
        raiz (Path): Raiz del toolchain.
        sesion (SesionHttp, opcional): Sesion HTTP, sustituible en pruebas.
        siete_zip (Path, opcional): Ejecutable de 7-Zip para los formatos 7z y rar_iso.
        conservar_descarga (bool, opcional): Si es verdadero no borra el archivo descargado.

    Returns:
        Path: Carpeta del componente ya instalado.

    Raises:
        ValueError: Si la huella no coincide o faltan archivos clave tras extraer.
        ConnectionError: Si falla la red.

    Ejemplo:
        carpeta = instalar_componente(componente, Path("toolchain"))
    """
    carpeta = carpeta_componente(raiz, componente)
    if carpeta.exists():
        shutil.rmtree(carpeta)
    carpeta.mkdir(parents=True)
    descarga = carpeta / CARPETA_DESCARGA
    archivo = descargar_verificado(componente, descarga, sesion)
    cantidad = extraer(componente, archivo, carpeta, siete_zip)
    ausentes = faltantes(componente, carpeta)
    if cantidad == 0 or ausentes:
        raise ValueError(
            f"componente '{componente.nombre}': instalacion incompleta"
            + (f", falta '{ausentes[0]}'" if ausentes else ", no se extrajo ningun archivo")
        )
    if not conservar_descarga:
        shutil.rmtree(descarga)
    marca = {
        "nombre": componente.nombre,
        "sha256": componente.sha256,
        "archivos": cantidad,
        "instalado_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (carpeta / NOMBRE_MARCA).write_text(json.dumps(marca, indent=2) + "\n", encoding="utf-8")
    return carpeta


def instalar(
    lock: dict[str, Componente],
    raiz: Path,
    nombres: Iterable[str] | None = None,
    sesion: SesionHttp | None = None,
    siete_zip: Path | None = None,
) -> dict[str, str]:
    """
    Instala todos los componentes pedidos (o todos los del lock) saltando los ya vigentes.

    Contexto:
        Implementa ``python -m tools.toolchain instalar``.

    Args:
        lock (dict[str, Componente]): Lock validado.
        raiz (Path): Raiz del toolchain.
        nombres (Iterable[str], opcional): Subconjunto a instalar; ``None`` significa todos.
        sesion (SesionHttp, opcional): Sesion HTTP, sustituible en pruebas.
        siete_zip (Path, opcional): Ejecutable de 7-Zip.

    Returns:
        dict[str, str]: Estado por componente: ``"instalado"`` o ``"vigente"``.

    Raises:
        ValueError: Si se pide un componente que no figura en el lock o falla alguna verificacion.

    Ejemplo:
        estados = instalar(lock, Path("toolchain"), nombres=["maspsx"])
    """
    elegidos = [obtener_componente(lock, n) for n in nombres] if nombres is not None else list(lock.values())
    estados: dict[str, str] = {}
    for componente in elegidos:
        carpeta = carpeta_componente(raiz, componente)
        if esta_instalado(componente, carpeta):
            estados[componente.nombre] = "vigente"
            continue
        instalar_componente(componente, raiz, sesion, siete_zip)
        estados[componente.nombre] = "instalado"
    return estados


def resolver_herramienta(lock: dict[str, Componente], raiz: Path, nombre: str, alias: str) -> Path:
    """
    Devuelve la ruta absoluta de una herramienta instalada.

    Contexto:
        La reconstruccion y la comparacion de funciones localizan ``as``, ``ld``,
        ``CC1PSX.EXE``, etc. por componente y alias, nunca por rutas fijas.

    Args:
        lock (dict[str, Componente]): Lock validado.
        raiz (Path): Raiz del toolchain.
        nombre (str): Componente que contiene la herramienta.
        alias (str): Alias declarado en ``archivos_clave``.

    Returns:
        Path: Ruta del archivo.

    Raises:
        ValueError: Si el componente o el alias no existen en el lock.
        FileNotFoundError: Si el archivo no esta instalado.

    Ejemplo:
        ensamblador = resolver_herramienta(lock, Path("toolchain"), "binutils-mipsel", "as")
    """
    componente = obtener_componente(lock, nombre)
    ruta = carpeta_componente(raiz, componente) / componente.ruta_clave(alias)
    if not ruta.is_file():
        raise FileNotFoundError(
            f"componente '{nombre}': '{alias}' no esta instalado; "
            "ejecute 'python -m tools.toolchain instalar'"
        )
    return ruta

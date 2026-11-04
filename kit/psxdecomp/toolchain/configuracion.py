"""Resolucion de rutas de trabajo: argumentos, variables de entorno y archivo local del proyecto.

El repositorio no contiene rutas de ninguna maquina. Cada ruta se obtiene, en este orden de
prioridad, de: argumento explicito, variable de entorno con el prefijo propio del kit, variable con
el alias del proyecto, archivo local ignorado por git (``rutas.local`` del manifiesto) y, por
ultimo, un valor por defecto relativo a la raiz del repositorio.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from psxdecomp.entorno import (
    SUFIJO_7ZIP,
    SUFIJO_DISCO,
    SUFIJO_TOOLCHAIN,
    VARIABLES_PROPIAS,
    Variables,
)

CLAVES_LOCALES = ("disc", "toolchain", "siete_zip")
MAX_BYTES_LOCAL = 64 * 1024
MAX_LARGO_RUTA = 1024


@dataclass(frozen=True)
class Rutas:
    """Rutas resueltas para una ejecucion.

    Attributes:
        raiz: Raiz del repositorio.
        toolchain: Carpeta donde viven los componentes instalados.
        disc: Carpeta del disco (contiene ``fs/`` con el sistema de archivos extraido), o ``None``.
        siete_zip: Ejecutable de 7-Zip si se configuro explicitamente, o ``None``.
    """

    raiz: Path
    toolchain: Path
    disc: Path | None
    siete_zip: Path | None


def leer_local_toml(ruta: Path, etiqueta: str | None = None) -> dict[str, str]:
    """
    Lee el archivo local de rutas y devuelve su tabla ``[rutas]`` validada.

    Contexto:
        Es la fuente de configuracion posterior al entorno; el archivo esta ignorado por git y
        cada desarrollador crea el suyo. Su ubicacion es ``rutas.local`` del manifiesto.

    Args:
        ruta (Path): Ubicacion del archivo; si no existe se devuelve un diccionario vacio.
        etiqueta (str, opcional): Nombre con el que los mensajes de error identifican al archivo
            (normalmente ``rutas.local``); por omision el nombre del archivo.

    Returns:
        dict[str, str]: Pares clave/valor de ``[rutas]`` restringidos a ``CLAVES_LOCALES``.

    Raises:
        ValueError: Si el archivo es demasiado grande, no es TOML valido, la tabla ``rutas``
            no es un objeto, trae claves desconocidas o valores que no son texto acotado.

    Ejemplo:
        local = leer_local_toml(Path("local.toml"), etiqueta="local.toml")
    """
    nombre = etiqueta or ruta.name
    if not ruta.is_file():
        return {}
    if ruta.stat().st_size > MAX_BYTES_LOCAL:
        raise ValueError(f"{nombre} excede el tamano permitido")
    try:
        datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        raise ValueError(f"{nombre} no es un TOML valido") from None
    tabla = datos.get("rutas", {})
    if not isinstance(tabla, dict):
        raise ValueError(f"{nombre}: 'rutas' debe ser una tabla")
    resultado: dict[str, str] = {}
    for clave, valor in tabla.items():
        if clave not in CLAVES_LOCALES:
            raise ValueError(f"{nombre}: clave desconocida '{clave}' en [rutas]")
        if not isinstance(valor, str) or not valor or len(valor) > MAX_LARGO_RUTA:
            raise ValueError(f"{nombre}: '{clave}' debe ser texto no vacio de hasta {MAX_LARGO_RUTA}")
        resultado[clave] = valor
    return resultado


def resolver_rutas(
    raiz: Path,
    entorno: Mapping[str, str],
    local: Mapping[str, str],
    disc: str | None = None,
    toolchain: str | None = None,
    *,
    variables: Variables = VARIABLES_PROPIAS,
) -> Rutas:
    """
    Combina las fuentes de configuracion en un objeto ``Rutas``.

    Contexto:
        Lo usan las CLI que resuelven el disco y el toolchain para no duplicar la politica de
        prioridades: argumento, prefijo propio, alias del proyecto, archivo local, defecto.

    Args:
        raiz (Path): Raiz del repositorio.
        entorno (Mapping[str, str]): Variables de entorno (normalmente ``os.environ``).
        local (Mapping[str, str]): Tabla leida del archivo local de rutas.
        disc (str, opcional): Valor del argumento ``--disc``.
        toolchain (str, opcional): Valor del argumento ``--toolchain``.
        variables (Variables, opcional): Nombres de variable del proyecto; por omision solo el
            prefijo propio del kit.

    Returns:
        Rutas: Rutas resueltas; ``toolchain`` cae por defecto a ``<raiz>/toolchain``.

    Ejemplo:
        rutas = resolver_rutas(Path("."), os.environ, {}, disc=None, toolchain=None)
    """
    bruto_disc = disc or variables.leer(SUFIJO_DISCO, entorno) or local.get("disc")
    bruto_toolchain = toolchain or variables.leer(SUFIJO_TOOLCHAIN, entorno) or local.get("toolchain")
    bruto_7zip = variables.leer(SUFIJO_7ZIP, entorno) or local.get("siete_zip")
    return Rutas(
        raiz=raiz,
        toolchain=Path(bruto_toolchain) if bruto_toolchain else raiz / "toolchain",
        disc=Path(bruto_disc) if bruto_disc else None,
        siete_zip=Path(bruto_7zip) if bruto_7zip else None,
    )

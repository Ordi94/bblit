"""Resolucion de rutas de trabajo: argumentos, variables de entorno y ``config/local.toml``.

El repositorio no contiene rutas de ninguna maquina. Cada ruta se obtiene, en este orden de
prioridad, de: argumento explicito, variable de entorno, archivo local ignorado por git y, por
ultimo, un valor por defecto relativo a la raiz del repositorio.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

VARIABLE_DISCO = "BBLIT_DISC"
VARIABLE_TOOLCHAIN = "BBLIT_TOOLCHAIN"
VARIABLE_7ZIP = "BBLIT_7ZIP"
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


def leer_local_toml(ruta: Path) -> dict[str, str]:
    """
    Lee ``config/local.toml`` y devuelve la tabla ``[rutas]`` validada.

    Contexto:
        Es la tercera fuente de configuracion; el archivo esta ignorado por git y cada
        desarrollador crea el suyo a partir de ``config/local.example.toml``.

    Args:
        ruta (Path): Ubicacion del archivo; si no existe se devuelve un diccionario vacio.

    Returns:
        dict[str, str]: Pares clave/valor de ``[rutas]`` restringidos a ``CLAVES_LOCALES``.

    Raises:
        ValueError: Si el archivo es demasiado grande, no es TOML valido, la tabla ``rutas``
            no es un objeto, trae claves desconocidas o valores que no son texto acotado.

    Ejemplo:
        local = leer_local_toml(Path("config/local.toml"))
    """
    if not ruta.is_file():
        return {}
    if ruta.stat().st_size > MAX_BYTES_LOCAL:
        raise ValueError("config/local.toml excede el tamano permitido")
    try:
        datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        raise ValueError("config/local.toml no es un TOML valido") from None
    tabla = datos.get("rutas", {})
    if not isinstance(tabla, dict):
        raise ValueError("config/local.toml: 'rutas' debe ser una tabla")
    resultado: dict[str, str] = {}
    for clave, valor in tabla.items():
        if clave not in CLAVES_LOCALES:
            raise ValueError(f"config/local.toml: clave desconocida '{clave}' en [rutas]")
        if not isinstance(valor, str) or not valor or len(valor) > MAX_LARGO_RUTA:
            raise ValueError(
                f"config/local.toml: '{clave}' debe ser texto no vacio de hasta {MAX_LARGO_RUTA}"
            )
        resultado[clave] = valor
    return resultado


def resolver_rutas(
    raiz: Path,
    entorno: Mapping[str, str],
    local: Mapping[str, str],
    disc: str | None = None,
    toolchain: str | None = None,
) -> Rutas:
    """
    Combina las fuentes de configuracion en un objeto ``Rutas``.

    Contexto:
        Lo usan las dos CLI (``tools.toolchain`` y ``tools/build.py``) para no duplicar la
        politica de prioridades.

    Args:
        raiz (Path): Raiz del repositorio.
        entorno (Mapping[str, str]): Variables de entorno (normalmente ``os.environ``).
        local (Mapping[str, str]): Tabla leida de ``config/local.toml``.
        disc (str, opcional): Valor del argumento ``--disc``.
        toolchain (str, opcional): Valor del argumento ``--toolchain``.

    Returns:
        Rutas: Rutas resueltas; ``toolchain`` cae por defecto a ``<raiz>/toolchain``.

    Ejemplo:
        rutas = resolver_rutas(Path("."), os.environ, {}, disc=None, toolchain=None)
    """
    bruto_disc = disc or entorno.get(VARIABLE_DISCO) or local.get("disc")
    bruto_toolchain = toolchain or entorno.get(VARIABLE_TOOLCHAIN) or local.get("toolchain")
    bruto_7zip = entorno.get(VARIABLE_7ZIP) or local.get("siete_zip")
    return Rutas(
        raiz=raiz,
        toolchain=Path(bruto_toolchain) if bruto_toolchain else raiz / "toolchain",
        disc=Path(bruto_disc) if bruto_disc else None,
        siete_zip=Path(bruto_7zip) if bruto_7zip else None,
    )

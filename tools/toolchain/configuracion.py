"""Reexportacion de ``psxdecomp.toolchain.configuracion`` con el alias de variables del proyecto."""

from functools import partial

from psxdecomp.entorno import SUFIJO_7ZIP, SUFIJO_DISCO, SUFIJO_TOOLCHAIN
from psxdecomp.toolchain import configuracion as _kit
from psxdecomp.toolchain.configuracion import CLAVES_LOCALES, MAX_BYTES_LOCAL, MAX_LARGO_RUTA, Rutas
from tools.toolchain.contexto import PROYECTO, VARIABLES

VARIABLE_DISCO = VARIABLES.nombre_del_proyecto(SUFIJO_DISCO)
VARIABLE_TOOLCHAIN = VARIABLES.nombre_del_proyecto(SUFIJO_TOOLCHAIN)
VARIABLE_7ZIP = VARIABLES.nombre_del_proyecto(SUFIJO_7ZIP)

leer_local_toml = partial(_kit.leer_local_toml, etiqueta=PROYECTO.rutas.local)
resolver_rutas = partial(_kit.resolver_rutas, variables=VARIABLES)

__all__ = [
    "CLAVES_LOCALES",
    "MAX_BYTES_LOCAL",
    "MAX_LARGO_RUTA",
    "VARIABLE_7ZIP",
    "VARIABLE_DISCO",
    "VARIABLE_TOOLCHAIN",
    "Rutas",
    "leer_local_toml",
    "resolver_rutas",
]

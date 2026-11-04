"""Estado persistente del permutador: reexportacion de ``psxdecomp.permutador.estado``.

El codigo vive en el kit; este modulo conserva la ruta de importacion del repositorio.
"""

from psxdecomp.permutador.estado import (
    ARCHIVOS_DEL_ESTADO,
    BUILD_POR_DEFECTO,
    SUBCARPETA_PERMUTADOR,
    VERSION_ESTADO,
    Estado,
    anadir_registro,
    cargar_actual,
    cargar_estado,
    carpeta_de,
    guardar_actual,
    guardar_estado,
    guardar_mejor,
    reiniciar,
)

__all__ = [
    "ARCHIVOS_DEL_ESTADO",
    "BUILD_POR_DEFECTO",
    "SUBCARPETA_PERMUTADOR",
    "VERSION_ESTADO",
    "Estado",
    "anadir_registro",
    "cargar_actual",
    "cargar_estado",
    "carpeta_de",
    "guardar_actual",
    "guardar_estado",
    "guardar_mejor",
    "reiniciar",
]

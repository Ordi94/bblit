"""Comparacion por bytes tras enlazar: reexportacion de ``psxdecomp.diff.enlace_diff``.

El codigo vive en el kit. Este modulo conserva la ruta de importacion del repositorio y enlaza
la funcion que necesita el ELF de la ultima construccion con la ruta que fija el manifiesto de
este proyecto: el resto del repositorio la sigue llamando con la firma de siempre.
"""

from functools import partial

from psxdecomp.diff import enlace_diff as _kit
from psxdecomp.diff.enlace_diff import (
    TIMEOUT_ENLACE_S,
    FuncionEnObjeto,
    contar_referencias_numericas,
    funcion_en_objeto,
    simbolos_de_elf,
    texto_simbolos_ld,
)
from tools.reconstruccion.infraestructura import ELF_SALIDA

bytes_coinciden = partial(_kit.bytes_coinciden, elf=ELF_SALIDA)

__all__ = [
    "TIMEOUT_ENLACE_S",
    "FuncionEnObjeto",
    "bytes_coinciden",
    "contar_referencias_numericas",
    "funcion_en_objeto",
    "simbolos_de_elf",
    "texto_simbolos_ld",
]

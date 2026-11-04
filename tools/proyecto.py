"""Proyecto del juego: manifiesto cargado una sola vez y nombres de variable de entorno con su alias.

Los paquetes de ``tools`` que se quedan en el repositorio (``ghidra``, ``overlay``, ``emulador``,
``bzz``) consumen el kit ``psxdecomp`` directamente. Este modulo es el unico lugar donde se localiza
la raiz del repositorio y se lee ``psxdecomp.toml``; ningun otro modulo repite rutas, zonas de
memoria ni el prefijo de las variables que el manifiesto ya declara.
"""

from functools import partial
from pathlib import Path
from typing import Final

from psxdecomp.construccion import infraestructura as infra
from psxdecomp.entorno import Variables
from psxdecomp.lectura import cargar_proyecto
from psxdecomp.proyecto import Proyecto

RAIZ_REPOSITORIO: Final[Path] = Path(__file__).resolve().parents[1]
"""Raiz del repositorio: la carpeta que contiene ``tools/`` y ``psxdecomp.toml``."""


def cargar(raiz: Path = RAIZ_REPOSITORIO) -> Proyecto:
    """
    Carga y valida el manifiesto del juego.

    Contexto:
        Lo ejecuta este modulo al importarse para fijar ``PROYECTO``; las pruebas lo llaman con una
        raiz sintetica para comprobar el manifiesto sin tocar el real.

    Args:
        raiz (Path, opcional): Carpeta que contiene ``psxdecomp.toml``; por defecto la del repositorio.

    Returns:
        Proyecto: Manifiesto validado e inmutable.

    Raises:
        ManifiestoError: Si el manifiesto falta o es invalido (``psxdecomp.proyecto``).

    Ejemplo:
        proyecto = cargar()
    """
    return cargar_proyecto(raiz)


PROYECTO: Final[Proyecto] = cargar()
"""Manifiesto del juego, cargado al importar el modulo."""

VARIABLES: Final[Variables] = PROYECTO.variables()
"""Nombres de variable de entorno: prefijo propio del kit con el alias historico del juego."""

ejecutar_proceso: Final = partial(infra.ejecutar_proceso, variables=VARIABLES)
"""Ejecutor de procesos del kit que localiza Wine tambien con el alias historico del juego."""

localizar_imagen: Final = partial(infra.localizar_imagen, variables=VARIABLES)
"""Localiza la imagen del disco; los mensajes nombran las dos variables aceptadas."""

leer_referencia: Final = partial(infra.leer_referencia, etiqueta=PROYECTO.identidad.referencia)
"""Lee las huellas y la cabecera del ejecutable original que declara el manifiesto."""

obtener_original: Final = partial(infra.obtener_original, rutas=PROYECTO.rutas, variables=VARIABLES)
"""Entrega el ejecutable original; si el disco es una imagen, lo extrae a la carpeta de esperados."""

__all__ = [
    "PROYECTO",
    "RAIZ_REPOSITORIO",
    "VARIABLES",
    "cargar",
    "ejecutar_proceso",
    "leer_referencia",
    "localizar_imagen",
    "obtener_original",
]

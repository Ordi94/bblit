"""Proyecto del juego: manifiesto cargado una sola vez y nombres de variable de entorno con su alias.

Los paquetes de ``tools`` que se quedan en el repositorio (``ghidra``, ``overlay``, ``emulador``,
``bzz``) consumen el kit ``psxdecomp`` directamente. Este modulo es el unico lugar donde se localiza
la raiz del repositorio y se lee ``psxdecomp.toml``; ningun otro modulo repite rutas, zonas de
memoria ni el prefijo de las variables que el manifiesto ya declara.
"""

from collections.abc import Mapping
from functools import partial
from pathlib import Path
from typing import Final

from psxdecomp.construccion import infraestructura as infra
from psxdecomp.entorno import Variables
from psxdecomp.lectura import cargar_proyecto
from psxdecomp.proyecto import Proyecto
from psxdecomp.toolchain.configuracion import leer_local_toml, resolver_rutas

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


def resolver_disco(
    entorno: Mapping[str, str], raiz: Path = RAIZ_REPOSITORIO, disc: str | None = None
) -> Path | None:
    """
    Resuelve la ubicacion del disco original con la politica unica del kit.

    Contexto:
        Lo usan las herramientas que necesitan el disco (ghidra para extraer el ejecutable,
        emulador para proteger su carpeta). Aplica la prioridad argumento, ``PSXDECOMP_DISC``,
        ``BBLIT_DISC``, ``config/local.toml``; leer una sola variable a mano dejaria sin efecto las
        otras formas de configurarlo, y la proteccion de solo lectura del disco dependeria de cual
        se uso.

    Args:
        entorno (Mapping[str, str]): Variables de entorno de la invocacion.
        raiz (Path, opcional): Raiz del repositorio (sustituible en pruebas).
        disc (str, opcional): Valor explicito (por ejemplo ``--disc``), que manda sobre el resto.

    Returns:
        Path | None: Ubicacion declarada del disco, o ``None`` si no se configuro por ninguna via.

    Raises:
        ValueError: Si ``config/local.toml`` existe y no es valido.

    Ejemplo:
        disco = resolver_disco(os.environ)
    """
    local = leer_local_toml(raiz / PROYECTO.rutas.local, etiqueta=PROYECTO.rutas.local)
    return resolver_rutas(raiz, entorno, local, disc, variables=VARIABLES).disc


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
    "resolver_disco",
]

"""Confinamiento de rutas del proyecto: la unica regla del kit que consulta el sistema de archivos.

``validacion`` valida datos ya leidos sin tocar disco; esta capa resuelve rutas contra el disco
(enlaces simbolicos incluidos) para comprobar que ninguna sale de la raiz del proyecto. La usan la
lectura del manifiesto y ``Proyecto.ruta_absoluta``, de modo que la regla existe una sola vez.
"""

from __future__ import annotations

from pathlib import Path, PureWindowsPath

from psxdecomp.validacion import fallo


def esta_confinada(raiz: Path, relativa: str) -> bool:
    """
    Indica si una ruta relativa permanece dentro de la raiz del proyecto.

    Contexto:
        Unica regla de confinamiento del kit: la usan tanto la lectura del manifiesto al cargarlo
        (``comprobar_dentro_de_raiz``) como ``Proyecto.ruta_absoluta``. Se aplican dos barreras
        independientes, cada una suficiente por si sola, y no deben simplificarse en una: la
        lexica rechaza lo que ``pathlib`` interpretaria como salto de raiz (en Windows ``/x``
        no es absoluta pero ``raiz / "/x"`` descarta la raiz; ``C:/x`` y las rutas de red tambien),
        y la de resolucion detecta enlaces simbolicos que apuntan fuera. La parte lexica se evalua
        con semantica Windows en cualquier plataforma para que el resultado no dependa del sistema.

    Args:
        raiz (Path): Raiz del proyecto.
        relativa (str): Ruta relativa a comprobar.

    Returns:
        bool: ``True`` solo si la ruta no tiene byte nulo, unidad, raiz ni ``..`` y su resolucion
        queda bajo la raiz resuelta; ``False`` en cualquier otro caso, incluida una ruta que el
        sistema operativo no pueda resolver.

    Ejemplo:
        if not esta_confinada(Path("."), "src"):
            raise ValueError("fuera de la raiz")
    """
    lexica = PureWindowsPath(relativa)
    if "\x00" in relativa or lexica.anchor or lexica.drive or ".." in lexica.parts:
        return False
    try:
        return (raiz / relativa).resolve().is_relative_to(raiz.resolve())
    except (OSError, ValueError):
        return False


def comprobar_dentro_de_raiz(raiz: Path, relativa: str, clave: str, seccion: str) -> None:
    """
    Comprueba que una ruta relativa del manifiesto sigue dentro de la raiz del proyecto.

    Contexto:
        Segunda barrera tras el patron de ``leer_ruta``: si un tramo existente es un enlace
        simbolico que apunta fuera de la raiz, la ruta lexicamente valida escaparia de ella.

    Args:
        raiz (Path): Raiz del proyecto.
        relativa (str): Ruta relativa ya validada.
        clave (str): Clave de origen, para el mensaje.
        seccion (str): Seccion de origen, para el mensaje.

    Raises:
        ManifiestoError: Si ``esta_confinada`` rechaza la ruta.

    Ejemplo:
        comprobar_dentro_de_raiz(Path("."), "src", "fuentes", "rutas")
    """
    if not esta_confinada(raiz, relativa):
        raise fallo(seccion, clave, "una ruta que permanezca dentro de la raiz del proyecto")

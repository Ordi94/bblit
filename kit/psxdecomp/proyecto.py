"""Fachada del manifiesto: reexporta la API publica repartida por capas.

``dominio`` modela y valida, ``lectura`` accede a disco y ``cli`` presenta. Los consumidores del
kit importan desde aqui ``Proyecto``, ``cargar_proyecto`` y ``ManifiestoError`` sin depender de
como se reparte el trabajo internamente.
"""

from psxdecomp.dominio import Convenciones, Identidad, Plugins, Proyecto, Rutas, Zonas
from psxdecomp.lectura import cargar_proyecto
from psxdecomp.validacion import ManifiestoError

__all__ = [
    "Convenciones",
    "Identidad",
    "ManifiestoError",
    "Plugins",
    "Proyecto",
    "Rutas",
    "Zonas",
    "cargar_proyecto",
]

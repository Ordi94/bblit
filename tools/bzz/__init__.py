"""Lectura y descompresion de los contenedores ``.BZZ`` del juego.

Contexto:
    Capas del paquete: ``dominio`` (cabecera y reglas puras), ``descompresion`` (algoritmo
    sobre bytes), ``lectura`` (archivos, manifiesto, inventario) y ``cli``.
"""

from tools.bzz.descompresion import descomprimir
from tools.bzz.dominio import Cabecera, Seccion, leer_cabecera

__all__ = ["Cabecera", "Seccion", "descomprimir", "leer_cabecera"]

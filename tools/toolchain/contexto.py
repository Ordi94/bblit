"""Contexto del proyecto para la reexportacion del toolchain: manifiesto y variables de entorno.

El toolchain vive en el paquete ``psxdecomp.toolchain``; este modulo carga una sola vez el
manifiesto de la raiz del repositorio y entrega los nombres de variable de entorno con el alias
historico del proyecto, de modo que las constantes y funciones reexportadas conserven su
comportamiento sin escribir a mano ningun nombre de variable.
"""

from pathlib import Path

from psxdecomp.lectura import cargar_proyecto

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
PROYECTO = cargar_proyecto(RAIZ_REPOSITORIO)
VARIABLES = PROYECTO.variables()

__all__ = ["PROYECTO", "RAIZ_REPOSITORIO", "VARIABLES"]

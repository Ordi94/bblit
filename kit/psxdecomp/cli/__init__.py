"""Linea de ordenes del kit: ``python -m psxdecomp.cli <orden>``.

Subpaquete por capas: ``errores`` y ``contexto`` (modelo), ``plugins`` (extensiones del manifiesto),
``comandos`` (ordenes), ``parser`` (argumentos y ayuda) y ``principal`` (punto de entrada). Un proyecto
consumidor reutiliza ``main`` y ``construir_parser`` con su propio manifiesto y suma ordenes por plugins.
"""

from psxdecomp.cli.comandos import resumir_comparacion
from psxdecomp.cli.contexto import Contexto, ResultadoVerificacion
from psxdecomp.cli.errores import PluginInvalidoError, describir_error_de_sistema, motivo_sin_rutas
from psxdecomp.cli.parser import construir_parser
from psxdecomp.cli.principal import main

__all__ = [
    "Contexto",
    "PluginInvalidoError",
    "ResultadoVerificacion",
    "construir_parser",
    "describir_error_de_sistema",
    "main",
    "motivo_sin_rutas",
    "resumir_comparacion",
]

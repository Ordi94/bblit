"""Errores de la linea de ordenes y la forma de comunicarlos sin exponer rutas de la maquina.

Capa de dominio de la CLI: no imprime ni toca disco. ``main`` convierte estos errores en una linea
``error: ...`` en la salida de errores y en el codigo de retorno 1.
"""

from __future__ import annotations

from pathlib import PurePath

from psxdecomp.construccion.infraestructura import ProcesoError


class PluginInvalidoError(ValueError):
    """Un plugin del manifiesto no se pudo cargar o rompe el contrato de la linea de ordenes."""


ERRORES_PROPIOS = (ValueError, ProcesoError)
"""Errores esperados de las ordenes: se imprimen en una linea y devuelven 1."""


def describir_error_de_sistema(error: OSError) -> str:
    """
    Da el texto de un error de entrada/salida sin exponer rutas de la maquina.

    Contexto:
        Lo usa ``main``. Un ``OSError`` nativo (permisos, disco, archivo ausente) lleva en su texto
        la ruta completa; el proyecto tambien lanza ``FileNotFoundError`` con un mensaje propio y
        sin ``errno`` (por ejemplo "falta el archivo de simbolos"), que se conserva tal cual porque
        es una instruccion para el usuario y no contiene directorios de la maquina.

    Args:
        error (OSError): Error capturado.

    Returns:
        str: El mensaje propio si el error no trae ``errno``; si no, el tipo de error, el motivo
        del sistema (``strerror``) y solo el nombre base del archivo, nunca el directorio.

    Ejemplo:
        print(describir_error_de_sistema(PermissionError(13, "Acceso denegado", "C:/datos/a.bin")))
    """
    if error.errno is None:
        return str(error)
    detalle = f"error de entrada/salida: {type(error).__name__}"
    if error.strerror:
        detalle += f" ({error.strerror})"
    if error.filename:
        detalle += f": {PurePath(str(error.filename)).name}"
    return detalle


def motivo_sin_rutas(error: Exception) -> str:
    """
    Da el motivo de un fallo sin las rutas de la maquina.

    Contexto:
        Lo usan las ordenes secundarias que convierten un fallo en aviso: un ``OSError`` trae la
        ruta completa en su texto, asi que solo se conserva la descripcion del sistema.

    Args:
        error (Exception): Fallo capturado.

    Returns:
        str: ``strerror`` si el error de entrada/salida nombra una ruta; el mensaje tal cual
        en el resto (los del proyecto ya van redactados sin rutas).

    Ejemplo:
        motivo = motivo_sin_rutas(PermissionError(13, "Acceso denegado", "C:/x"))
    """
    if isinstance(error, OSError) and error.filename is not None:
        return error.strerror or type(error).__name__
    return str(error)

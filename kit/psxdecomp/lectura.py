"""Lectura del manifiesto desde disco: archivo, TOML y confinamiento de las rutas declaradas.

Capa de entrada y salida del cargador. Aqui viven las cotas previas al analisis (existencia, tamano,
UTF-8), la llamada a ``tomllib`` y la comprobacion contra el disco de que ninguna ruta del
manifiesto escapa de la raiz. La validacion de los valores es de ``dominio``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from psxdecomp.confinamiento import comprobar_dentro_de_raiz
from psxdecomp.constantes import NOMBRE_MANIFIESTO
from psxdecomp.dominio import Proyecto, construir_proyecto
from psxdecomp.validacion import ManifiestoError

MAX_BYTES_MANIFIESTO = 64 * 1024


def leer_texto_manifiesto(raiz: Path) -> str:
    """
    Lee el texto del manifiesto aplicando las comprobaciones previas al analisis TOML.

    Contexto:
        Primera barrera de ``cargar_proyecto``: existencia, tamano acotado y codificacion UTF-8.

    Args:
        raiz (Path): Raiz del proyecto.

    Returns:
        str: Contenido del manifiesto.

    Raises:
        ManifiestoError: Si la raiz no es carpeta, el archivo falta, excede el limite, no se puede
            leer o no es UTF-8. Los mensajes no incluyen rutas.

    Ejemplo:
        texto = leer_texto_manifiesto(Path("."))
    """
    ruta = raiz / NOMBRE_MANIFIESTO
    if not raiz.is_dir() or not ruta.is_file():
        raise ManifiestoError(f"no existe {NOMBRE_MANIFIESTO} en la raiz del proyecto indicada")
    if ruta.stat().st_size > MAX_BYTES_MANIFIESTO:
        raise ManifiestoError(f"{NOMBRE_MANIFIESTO}: excede el tamano maximo de {MAX_BYTES_MANIFIESTO} bytes")
    try:
        return ruta.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise ManifiestoError(f"{NOMBRE_MANIFIESTO}: no se pudo leer como texto UTF-8") from None


def comprobar_confinamiento(proyecto: Proyecto) -> None:
    """
    Comprueba contra el disco que la referencia y las rutas declaradas no escapan de la raiz.

    Contexto:
        Segunda barrera tras el patron lexico de cada ruta: un enlace simbolico existente puede
        apuntar fuera de la raiz aunque el texto de la ruta sea inocuo. Se ejecuta sobre el
        ``Proyecto`` ya construido, de modo que el dominio no necesita el disco.

    Args:
        proyecto (Proyecto): Manifiesto construido.

    Raises:
        ManifiestoError: Si alguna ruta, o la referencia, resuelve fuera de la raiz.

    Ejemplo:
        comprobar_confinamiento(construir_proyecto(datos, raiz))
    """
    raiz = proyecto.raiz
    comprobar_dentro_de_raiz(raiz, proyecto.identidad.referencia, "referencia", "proyecto")
    for clave, ruta in proyecto.rutas.pares():
        comprobar_dentro_de_raiz(raiz, ruta, clave, "rutas")


def cargar_proyecto(raiz: Path) -> Proyecto:
    """
    Carga y valida el manifiesto ``psxdecomp.toml`` de la raiz de un proyecto.

    Contexto:
        Punto de entrada del kit: la CLI y cualquier modulo que necesite saber rutas, zonas o
        convenciones del proyecto empiezan aqui y reciben el ``Proyecto`` por parametro.

    Args:
        raiz (Path): Carpeta raiz del proyecto consumidor.

    Returns:
        Proyecto: Manifiesto validado e inmutable.

    Raises:
        ManifiestoError: Si el archivo falta, es muy grande, no es TOML valido, tiene secciones o
            claves desconocidas, o algun valor incumple su contrato. El mensaje dice que campo
            fallo y que se esperaba; nunca incluye rutas absolutas ni trazas.

    Ejemplo:
        proyecto = cargar_proyecto(Path("."))
    """
    texto = leer_texto_manifiesto(raiz)
    try:
        datos = tomllib.loads(texto)
    except tomllib.TOMLDecodeError as error:
        raise ManifiestoError(f"{NOMBRE_MANIFIESTO}: no es un TOML valido ({error})") from None
    proyecto = construir_proyecto(datos, raiz)
    comprobar_confinamiento(proyecto)
    return proyecto

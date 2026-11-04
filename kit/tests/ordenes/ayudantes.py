"""Proyecto inventado y ejecutor simulado para probar la linea de ordenes sin disco ni toolchain reales.

El proyecto vive en una carpeta temporal: manifiesto, referencia del ejecutable, archivo de bloqueo con
unas herramientas vacias y un disco con el sistema de archivos ya extraido. Los procesos externos
(particionador, ensamblador, enlazador) los sustituye ``Registro``, que registra los comandos y deja
los archivos que cada uno produciria.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psxdecomp.dominio import Proyecto
from psxdecomp.lectura import cargar_proyecto

from construccion.test_infraestructura import CABECERA, CUERPO, EJECUTABLE, REFERENCIA, SALIDAS, Registro
from manifiestos_de_prueba import ZONAS_MINIMAS
from toolchain.ayudantes import bloque_componente, lock_de

__all__ = ["CUERPO", "EJECUTABLE", "REFERENCIA", "SALIDAS", "Escenario", "Registro", "crear_escenario"]

NOMBRE_EJECUTABLE = "PRUEBA.EXE"
PREFIJO_ENTORNO = "JUEGO"
PLUGINS_VACIOS = "[plugins]\n"

MANIFIESTO = """\
[proyecto]
nombre = "demo"
ejecutable = "PRUEBA.EXE"
referencia = "datos/ejecutable.json"
prefijo_entorno = "JUEGO"

[rutas]
fuentes = "codigo"
splat = "datos/splat.yaml"
simbolos = ["datos/simbolos.txt"]
opciones_compilacion = "datos/opciones.toml"
toolchain_lock = "datos/lock.json"
local = "datos/local.toml"

"""


@dataclass
class Escenario:
    """
    Proyecto de prueba ya escrito en disco.

    Attributes:
        raiz: Raiz del proyecto.
        entorno: Variables de entorno que apuntan al disco y al toolchain simulados.
        disco: Carpeta del disco con ``fs/<ejecutable>``.
        proyecto: Manifiesto cargado.
    """

    raiz: Path
    entorno: dict[str, str]
    disco: Path
    proyecto: Proyecto


def _referencia_json() -> dict[str, Any]:
    """Referencia del ejecutable de prueba en el formato del archivo versionado."""
    campos = ("pc0", "gp0", "t_addr", "t_size", "d_addr", "d_size", "b_addr", "b_size", "s_addr", "s_size")
    return {
        "nombre": NOMBRE_EJECUTABLE,
        "sha256": REFERENCIA.sha256,
        "sha1": REFERENCIA.sha1,
        "tamano": REFERENCIA.tamano,
        "cabecera": {**{campo: getattr(CABECERA, campo) for campo in campos}, "region": CABECERA.region},
    }


def crear_escenario(base: Path, *, plugins: str = PLUGINS_VACIOS, con_referencia: bool = True) -> Escenario:
    """
    Escribe un proyecto inventado completo bajo ``base`` y lo carga.

    Contexto:
        Base de las pruebas de la linea de ordenes: da un manifiesto con rutas distintas de las del
        kit por omision, la referencia del ejecutable, el archivo de bloqueo y el disco simulado.

    Args:
        base (Path): Carpeta temporal donde crear ``proyecto``, ``herramientas`` y ``disco``.
        plugins (str, opcional): Texto de la seccion ``[plugins]`` del manifiesto.
        con_referencia (bool, opcional): Si es falso, no escribe la referencia del ejecutable.

    Returns:
        Escenario: Raiz, entorno, disco y proyecto cargado.

    Ejemplo:
        escenario = crear_escenario(tmp_path)
    """
    raiz = base / "proyecto"
    (raiz / "datos").mkdir(parents=True)
    (raiz / "psxdecomp.toml").write_text(MANIFIESTO + ZONAS_MINIMAS + "\n" + plugins, encoding="utf-8")
    if con_referencia:
        (raiz / "datos" / "ejecutable.json").write_text(json.dumps(_referencia_json()), encoding="utf-8")
    bloque = bloque_componente(
        b"x", archivos_clave={"as": "bin/as.exe", "ld": "bin/ld.exe", "objcopy": "bin/objcopy.exe"}
    )
    (raiz / "datos" / "lock.json").write_text(
        json.dumps(lock_de(**{"binutils-mipsel": bloque})), encoding="utf-8"
    )
    binarios = base / "herramientas" / "binutils-mipsel" / "bin"
    binarios.mkdir(parents=True)
    for nombre in ("as.exe", "ld.exe", "objcopy.exe"):
        (binarios / nombre).write_bytes(b"")
    disco = base / "disco (copia)"
    (disco / "fs").mkdir(parents=True)
    (disco / "fs" / NOMBRE_EJECUTABLE).write_bytes(EJECUTABLE)
    entorno = {
        f"{PREFIJO_ENTORNO}_DISC": str(disco),
        f"{PREFIJO_ENTORNO}_TOOLCHAIN": str(base / "herramientas"),
    }
    return Escenario(raiz, entorno, disco, cargar_proyecto(raiz))


def escribir_extension(raiz: Path, nombre_modulo: str, cuerpo: str) -> None:
    """
    Escribe un modulo de extension en la raiz del proyecto y olvida cualquier version anterior.

    Contexto:
        Los plugins se importan por nombre desde la raiz del proyecto: cada prueba usa un nombre de
        modulo propio para no compartir estado a traves de ``sys.modules``.

    Args:
        raiz (Path): Raiz del proyecto.
        nombre_modulo (str): Nombre del modulo, sin extension.
        cuerpo (str): Codigo fuente del modulo.

    Ejemplo:
        escribir_extension(raiz, "extension_a", "def gancho(proyecto):\\n    pass\\n")
    """
    (raiz / f"{nombre_modulo}.py").write_text(cuerpo, encoding="utf-8")
    sys.modules.pop(nombre_modulo, None)

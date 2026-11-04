"""Contexto de ejecucion de una orden: el proyecto, los argumentos y las dependencias externas.

Capa de aplicacion de la CLI. Cada orden recibe un ``Contexto`` y pide solo lo que necesita: la
referencia del ejecutable, las rutas del disco y del toolchain o el archivo de bloqueo se leen bajo
demanda y en el mismo orden en que las pedia la linea de ordenes original, de modo que una orden
que no las necesita (``clean`` no resuelve el disco, ``verificar-config`` no lee la referencia) no
falla por su ausencia.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from psxdecomp.construccion.dominio import EjecutableReferencia
from psxdecomp.construccion.infraestructura import Ejecutor, leer_referencia
from psxdecomp.dominio import Proyecto
from psxdecomp.toolchain.configuracion import Rutas as RutasDeEjecucion
from psxdecomp.toolchain.configuracion import leer_local_toml, resolver_rutas
from psxdecomp.toolchain.dominio import Componente
from psxdecomp.toolchain.instalacion import leer_lock


@dataclass(frozen=True)
class ResultadoVerificacion:
    """
    Resultado de comparar el ejecutable reconstruido con el original.

    Attributes:
        coincide: Verdadero si las huellas coinciden.
        mensaje: Texto con el que ``verify`` informa el resultado (incluye el motivo si no coincide).
    """

    coincide: bool
    mensaje: str


@dataclass(frozen=True)
class Contexto:
    """
    Todo lo que una orden necesita para ejecutarse, sin estado global.

    Attributes:
        proyecto: Manifiesto validado del proyecto.
        args: Argumentos ya analizados de la orden.
        entorno: Variables de entorno a consultar (sustituible en pruebas).
        ejecutar: Ejecutor de procesos (sustituible en pruebas).
        python: Interprete con el que se lanza ``maspsx`` y las herramientas de Python.
    """

    proyecto: Proyecto
    args: argparse.Namespace
    entorno: Mapping[str, str]
    ejecutar: Ejecutor
    python: str = field(default_factory=lambda: sys.executable)

    @property
    def raiz(self) -> Path:
        """Raiz del proyecto."""
        return self.proyecto.raiz

    def referencia(self) -> EjecutableReferencia:
        """
        Lee la referencia del ejecutable que declara el manifiesto.

        Contexto:
            La piden las ordenes que comparan, dividen, construyen o limpian.

        Returns:
            EjecutableReferencia: Huellas, tamano y cabecera del ejecutable original.

        Raises:
            FileNotFoundError: Si falta el archivo de referencia.
            ValueError: Si su contenido no es valido.

        Ejemplo:
            referencia = contexto.referencia()
        """
        ruta = self.proyecto.identidad.referencia
        return leer_referencia(self.proyecto.ruta_absoluta(ruta), etiqueta=ruta)

    def rutas_toolchain(self) -> RutasDeEjecucion:
        """
        Resuelve el disco y el toolchain: argumento, variable de entorno, archivo local o defecto.

        Contexto:
            Usa ``--disc`` y ``--toolchain`` de la linea de ordenes y el alias de variables del manifiesto.

        Returns:
            RutasDeEjecucion: Rutas resueltas.

        Raises:
            ValueError: Si una ruta configurada no es valida.

        Ejemplo:
            rutas = contexto.rutas_toolchain()
        """
        local = leer_local_toml(
            self.proyecto.ruta_absoluta(self.proyecto.rutas.local), self.proyecto.rutas.local
        )
        return resolver_rutas(
            self.raiz,
            self.entorno,
            local,
            getattr(self.args, "disc", None),
            getattr(self.args, "toolchain", None),
            variables=self.proyecto.variables(),
        )

    def lock(self) -> dict[str, Componente]:
        """
        Lee el archivo de bloqueo del toolchain que declara el manifiesto.

        Returns:
            dict[str, Componente]: Componentes validados.

        Raises:
            FileNotFoundError: Si falta el archivo.
            ValueError: Si su contenido no es valido.

        Ejemplo:
            componentes = contexto.lock()
        """
        return leer_lock(self.proyecto.ruta_absoluta(self.proyecto.rutas.toolchain_lock))

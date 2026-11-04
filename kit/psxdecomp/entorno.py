"""Variables de entorno del kit: prefijo propio y alias del proyecto consumidor.

Modulo hoja del dominio: no toca disco ni lee ``os.environ`` por su cuenta; recibe el mapeo de
entorno a consultar. Es la unica fuente de la regla de precedencia entre el prefijo propio del kit
(``PSXDECOMP_``) y el alias que un proyecto traia antes de adoptarlo, de modo que ningun modulo
construye nombres de variable por concatenacion.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from psxdecomp.validacion import PATRON_PREFIJO_ENTORNO

PREFIJO_PROPIO = "PSXDECOMP"
PATRON_SUFIJO_ENTORNO = re.compile(r"^[A-Z0-9][A-Z0-9_]{0,63}$")

SUFIJO_DISCO = "DISC"
SUFIJO_TOOLCHAIN = "TOOLCHAIN"
SUFIJO_7ZIP = "7ZIP"
SUFIJO_WINE = "WINE"
SUFIJO_PREFIJO_BINUTILS = "BINUTILS_PREFIX"


@dataclass(frozen=True, slots=True)
class Variables:
    """
    Nombres de variable de entorno de un proyecto: prefijo propio del kit mas un alias opcional.

    Attributes:
        alias: Prefijo que el proyecto usaba antes de adoptar el kit (sin guion bajo final), o
            ``None`` si no tiene. Se acepta solo como respaldo: el prefijo propio manda.
        prefijo_principal: Prefijo propio del kit; solo se cambia en pruebas.
    """

    alias: str | None = None
    prefijo_principal: str = PREFIJO_PROPIO

    def __post_init__(self) -> None:
        """
        Valida los prefijos al construir el objeto.

        Contexto:
            Los prefijos acaban en nombres consultados en el entorno; se exige la misma lista de
            admitidos que el manifiesto para que ningun valor arbitrario llegue a una consulta.

        Raises:
            ValueError: Si algun prefijo no es un identificador en mayusculas.

        Ejemplo:
            Variables(alias="JUEGO")
        """
        for prefijo in (self.prefijo_principal, self.alias):
            if prefijo is not None and PATRON_PREFIJO_ENTORNO.fullmatch(prefijo) is None:
                raise ValueError("el prefijo de variable de entorno debe ser un identificador en mayusculas")

    def nombres(self, sufijo: str) -> tuple[str, ...]:
        """
        Enumera los nombres de variable que se consultan para un sufijo, en orden de precedencia.

        Contexto:
            Primero el prefijo propio y despues el alias; si coinciden se consulta una sola vez.

        Args:
            sufijo (str): Nombre sin prefijo en mayusculas, por ejemplo ``DISC``.

        Returns:
            tuple[str, ...]: Uno o dos nombres completos.

        Raises:
            ValueError: Si ``sufijo`` no es un identificador en mayusculas.

        Ejemplo:
            Variables(alias="JUEGO").nombres("DISC")  # ("PSXDECOMP_DISC", "JUEGO_DISC")
        """
        if PATRON_SUFIJO_ENTORNO.fullmatch(sufijo) is None:
            raise ValueError("el sufijo de variable de entorno debe ser un identificador en mayusculas")
        prefijos = (self.prefijo_principal, self.alias) if self.alias else (self.prefijo_principal,)
        return tuple(f"{prefijo}_{sufijo}" for prefijo in dict.fromkeys(prefijos))

    def nombre_del_proyecto(self, sufijo: str) -> str:
        """
        Devuelve el nombre con el prefijo propio del proyecto (el alias si lo tiene).

        Contexto:
            Lo usan los consumidores que conservan constantes historicas con el nombre antiguo de
            la variable, calculadas desde el manifiesto en vez de escritas a mano.

        Args:
            sufijo (str): Nombre sin prefijo en mayusculas.

        Returns:
            str: Nombre completo con el alias, o con el prefijo propio si no hay alias.

        Raises:
            ValueError: Si ``sufijo`` no es un identificador en mayusculas.

        Ejemplo:
            Variables(alias="JUEGO").nombre_del_proyecto("DISC")  # "JUEGO_DISC"
        """
        return self.nombres(sufijo)[-1]

    def describir(self, sufijo: str) -> str:
        """
        Redacta los nombres aceptados para un sufijo, para los mensajes de error.

        Contexto:
            Un error de configuracion debe nombrar las dos variables validas, no solo una.

        Args:
            sufijo (str): Nombre sin prefijo en mayusculas.

        Returns:
            str: ``PSXDECOMP_X`` o ``PSXDECOMP_X (o ALIAS_X)``.

        Raises:
            ValueError: Si ``sufijo`` no es un identificador en mayusculas.

        Ejemplo:
            Variables(alias="JUEGO").describir("DISC")  # "PSXDECOMP_DISC (o JUEGO_DISC)"
        """
        propio, *alias = self.nombres(sufijo)
        return f"{propio} (o {alias[0]})" if alias else propio

    def definidas(self, sufijo: str, entorno: Mapping[str, str]) -> Iterator[str]:
        """
        Recorre los valores definidos (aunque vacios) en orden de precedencia.

        Contexto:
            Base de las dos politicas de lectura: ``leer`` descarta vacios, y quien necesita
            respetar un valor vacio (un prefijo de binutils vacio es legitimo) toma el primero.

        Args:
            sufijo (str): Nombre sin prefijo en mayusculas.
            entorno (Mapping[str, str]): Entorno a consultar.

        Yields:
            str: Valor de cada variable presente en el entorno.

        Raises:
            ValueError: Si ``sufijo`` no es un identificador en mayusculas.

        Ejemplo:
            primero = next(variables.definidas("WINE", os.environ), None)
        """
        for nombre in self.nombres(sufijo):
            if nombre in entorno:
                yield entorno[nombre]

    def leer(self, sufijo: str, entorno: Mapping[str, str]) -> str | None:
        """
        Resuelve una variable: el prefijo propio manda y el alias es respaldo.

        Contexto:
            Todo el kit lee su configuracion de entorno (disco, toolchain, 7-Zip) por aqui. Una
            variable definida pero vacia cuenta como ausente.

        Args:
            sufijo (str): Nombre sin prefijo en mayusculas, por ejemplo ``DISC``.
            entorno (Mapping[str, str]): Entorno a consultar.

        Returns:
            str | None: Valor de la primera variable definida y no vacia, o ``None``.

        Raises:
            ValueError: Si ``sufijo`` no es un identificador en mayusculas.

        Ejemplo:
            disco = variables.leer("DISC", os.environ)
        """
        return next((valor for valor in self.definidas(sufijo, entorno) if valor), None)


VARIABLES_PROPIAS = Variables()

"""
Cliente HTTP de la API REST local de PCSX-Redux.

Contexto:
    Capa de infraestructura de red de `tools.emulador`. Solo habla con 127.0.0.1, aplica
    tiempos de espera y reintentos, y valida lo que devuelve el emulador (tamano de la RAM,
    firma PNG, forma del JSON) antes de entregarlo al resto del paquete.
"""

from __future__ import annotations

import json
import time
import urllib.request
from collections.abc import Callable

from tools.emulador.dominio import EmuladorError, validar_ram
from tools.emulador.pantalla import FIRMA_PNG

PUERTO_POR_DEFECTO = 8080
TIEMPO_ESPERA = 20.0
REINTENTOS = 2
PAUSA_REINTENTO = 0.25

Solicitud = Callable[[str, str, float], bytes]


def solicitar_http(metodo: str, url: str, tiempo_espera: float) -> bytes:
    """
    Realiza una peticion HTTP y devuelve el cuerpo de la respuesta.

    Contexto:
        Implementacion real del transporte de `ClienteRedux`; los tests la sustituyen.

    Args:
        metodo (str): `GET` o `POST`.
        url (str): URL completa (siempre http hacia 127.0.0.1).
        tiempo_espera (float): Segundos maximos de espera de la respuesta.

    Returns:
        bytes: Cuerpo de la respuesta.

    Raises:
        OSError: Si la conexion falla (URLError es subclase) o el servidor responde con error.
        TimeoutError: Si se agota el tiempo de espera.

    Ejemplo:
        cuerpo = solicitar_http("GET", "http://127.0.0.1:8080/api/v1/execution-flow", 5.0)
    """
    peticion = urllib.request.Request(url, method=metodo, data=b"" if metodo == "POST" else None)  # noqa: S310
    with urllib.request.urlopen(peticion, timeout=tiempo_espera) as respuesta:  # noqa: S310
        cuerpo: bytes = respuesta.read()
    return cuerpo


class ClienteRedux:
    """
    Cliente de las operaciones de la API de PCSX-Redux que usa el oraculo.

    Contexto:
        Lo usan `sesion` y los subcomandos `volcar`, `capturar`, `pausar` y `reanudar`.
    """

    def __init__(
        self,
        puerto: int = PUERTO_POR_DEFECTO,
        solicitud: Solicitud = solicitar_http,
        dormir: Callable[[float], None] = time.sleep,
        tiempo_espera: float = TIEMPO_ESPERA,
        reintentos: int = REINTENTOS,
    ) -> None:
        """
        Crea el cliente para un puerto local.

        Contexto:
            Un cliente por sesion de emulador.

        Args:
            puerto (int, opcional): Puerto del servidor web del emulador (1024 a 65535).
            solicitud (Solicitud, opcional): Transporte HTTP; por defecto el real.
            dormir (Callable, opcional): Funcion de espera entre reintentos.
            tiempo_espera (float, opcional): Segundos maximos por peticion.
            reintentos (int, opcional): Reintentos tras un fallo de conexion.

        Raises:
            ValueError: Si el puerto esta fuera de 1024 a 65535.

        Ejemplo:
            cliente = ClienteRedux(8080)
        """
        if not 1024 <= puerto <= 65535:
            raise ValueError(f"puerto {puerto}: se esperaba un valor entre 1024 y 65535")
        self._base = f"http://127.0.0.1:{puerto}/api/v1/"
        self._solicitud = solicitud
        self._dormir = dormir
        self._tiempo_espera = tiempo_espera
        self._reintentos = reintentos

    def _pedir(self, metodo: str, ruta: str) -> bytes:
        """
        Envia una peticion con reintentos ante fallos de conexion.

        Contexto:
            Base de todas las operaciones publicas.

        Args:
            metodo (str): `GET` o `POST`.
            ruta (str): Ruta relativa a `/api/v1/`, con su cadena de consulta.

        Returns:
            bytes: Cuerpo de la respuesta.

        Raises:
            EmuladorError: Si todos los intentos fallan; el mensaje no incluye la URL ni trazas.

        Ejemplo:
            cuerpo = self._pedir("GET", "execution-flow")
        """
        for intento in range(self._reintentos + 1):
            try:
                return self._solicitud(metodo, self._base + ruta, self._tiempo_espera)
            except OSError:
                if intento < self._reintentos:
                    self._dormir(PAUSA_REINTENTO)
        raise EmuladorError(f"el emulador no responde a {metodo} {ruta}")

    def esta_corriendo(self) -> bool:
        """
        Consulta si la emulacion esta en marcha.

        Contexto:
            Primer hito de la sesion y comprobacion de pausa.

        Returns:
            bool: Valor de `running` en `execution-flow`.

        Raises:
            EmuladorError: Si el emulador no responde o `running` no es booleano.

        Ejemplo:
            cliente.esta_corriendo()
        """
        try:
            estado = json.loads(self._pedir("GET", "execution-flow"))
        except ValueError:
            raise EmuladorError("execution-flow: la respuesta no es JSON") from None
        corriendo = estado.get("running") if isinstance(estado, dict) else None
        if not isinstance(corriendo, bool):
            raise EmuladorError("execution-flow: se esperaba un campo booleano `running`")
        return corriendo

    def pausar(self) -> None:
        """
        Pausa la emulacion para que pantalla y RAM sean del mismo instante.

        Contexto:
            Paso previo a volcar y capturar en la sesion.

        Raises:
            EmuladorError: Si el emulador no responde.

        Ejemplo:
            cliente.pausar()
        """
        self._pedir("POST", "execution-flow?function=pause")

    def reanudar(self) -> None:
        """
        Reanuda la emulacion.

        Contexto:
            Subcomando `reanudar`.

        Raises:
            EmuladorError: Si el emulador no responde.

        Ejemplo:
            cliente.reanudar()
        """
        self._pedir("POST", "execution-flow?function=resume")

    def volcar_ram(self) -> bytes:
        """
        Descarga la RAM principal completa.

        Contexto:
            Cuerpo de `ram.bin`; el offset 0 equivale a la direccion `0x80000000`.

        Returns:
            bytes: Exactamente 2.097.152 bytes.

        Raises:
            EmuladorError: Si el emulador no responde.
            ValueError: Si el tamano devuelto no es el de la RAM.

        Ejemplo:
            ram = cliente.volcar_ram()
        """
        return validar_ram(self._pedir("GET", "cpu/ram/raw"))

    def capturar_pantalla(self) -> bytes:
        """
        Descarga la captura de pantalla actual en PNG.

        Contexto:
            Alimenta la espera del hito `pantalla` y el archivo `pantalla.png`.

        Returns:
            bytes: Archivo PNG.

        Raises:
            EmuladorError: Si el emulador no responde o lo devuelto no es un PNG.

        Ejemplo:
            png = cliente.capturar_pantalla()
        """
        datos = self._pedir("GET", "screen/still")
        if not datos.startswith(FIRMA_PNG):
            raise EmuladorError("screen/still: la respuesta no es un PNG")
        return datos

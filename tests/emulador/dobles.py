"""Dobles compartidos de las pruebas de sesion: reloj, cliente y proceso falsos."""

from collections.abc import Sequence

from tools.emulador.dominio import RAM_TAMANO, EmuladorError


class Reloj:
    """Reloj simulado: `dormir` avanza el tiempo sin esperar."""

    def __init__(self) -> None:
        self.ahora = 0.0
        self.pausas: list[float] = []

    def __call__(self) -> float:
        return self.ahora

    def dormir(self, segundos: float) -> None:
        self.pausas.append(segundos)
        self.ahora += segundos


class ClienteFalso:
    """Cliente con respuestas guiadas; una excepcion en la lista se lanza en su turno."""

    def __init__(
        self,
        corriendo: Sequence[bool | Exception] = (True,),
        pantallas: Sequence[bytes | Exception] = (),
        rams: Sequence[bytes | Exception] = (),
    ) -> None:
        self.corriendo = list(corriendo)
        self.pantallas = list(pantallas)
        self.rams = list(rams)
        self.pausado = False
        self.llamadas: list[str] = []

    @staticmethod
    def _siguiente[T](lista: list[T | Exception]) -> T:
        valor = lista.pop(0) if len(lista) > 1 else lista[0]
        if isinstance(valor, Exception):
            raise valor
        return valor

    def esta_corriendo(self) -> bool:
        self.llamadas.append("esta_corriendo")
        return self._siguiente(self.corriendo)

    def capturar_pantalla(self) -> bytes:
        self.llamadas.append("capturar_pantalla")
        return self._siguiente(self.pantallas)

    def volcar_ram(self) -> bytes:
        self.llamadas.append("volcar_ram")
        return self._siguiente(self.rams)

    def pausar(self) -> None:
        self.llamadas.append("pausar")
        self.pausado = True

    def reanudar(self) -> None:
        self.llamadas.append("reanudar")
        self.pausado = False


def ram_con(offset: int, contenido: bytes) -> bytes:
    """RAM de 2 MiB con `contenido` escrito en `offset`."""
    datos = bytearray(RAM_TAMANO)
    datos[offset : offset + len(contenido)] = contenido
    return bytes(datos)


def fallo(mensaje: str = "fallo") -> EmuladorError:
    """Excepcion de emulador lista para usar en una lista guiada."""
    return EmuladorError(mensaje)

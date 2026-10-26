"""Dobles compartidos de las pruebas de sesion: reloj, cliente y proceso falsos."""

from tools.emulador.dominio import RAM_TAMANO, EmuladorError


class Reloj:
    """Reloj simulado: `dormir` avanza el tiempo sin esperar."""

    def __init__(self):
        self.ahora = 0.0
        self.pausas = []

    def __call__(self):
        return self.ahora

    def dormir(self, segundos):
        self.pausas.append(segundos)
        self.ahora += segundos


class ClienteFalso:
    """Cliente con respuestas guiadas; una excepcion en la lista se lanza en su turno."""

    def __init__(self, corriendo=(True,), pantallas=(), rams=()):
        self.corriendo = list(corriendo)
        self.pantallas = list(pantallas)
        self.rams = list(rams)
        self.pausado = False
        self.llamadas = []

    @staticmethod
    def _siguiente(lista):
        valor = lista.pop(0) if len(lista) > 1 else lista[0]
        if isinstance(valor, Exception):
            raise valor
        return valor

    def esta_corriendo(self):
        self.llamadas.append("esta_corriendo")
        return self._siguiente(self.corriendo)

    def capturar_pantalla(self):
        self.llamadas.append("capturar_pantalla")
        return self._siguiente(self.pantallas)

    def volcar_ram(self):
        self.llamadas.append("volcar_ram")
        return self._siguiente(self.rams)

    def pausar(self):
        self.llamadas.append("pausar")
        self.pausado = True

    def reanudar(self):
        self.llamadas.append("reanudar")
        self.pausado = False


def ram_con(offset, contenido):
    """RAM de 2 MiB con `contenido` escrito en `offset`."""
    datos = bytearray(RAM_TAMANO)
    datos[offset : offset + len(contenido)] = contenido
    return bytes(datos)


def fallo(mensaje="fallo"):
    """Excepcion de emulador lista para usar en una lista guiada."""
    return EmuladorError(mensaje)

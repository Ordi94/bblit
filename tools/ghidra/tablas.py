"""Tablas de punteros a codigo dentro de la zona de datos del ejecutable.

Un ``switch`` compilado y una tabla de rutinas llamadas por indice dejan en los datos corridas de
palabras que apuntan a codigo. Este modulo las localiza leyendo el segmento; quien las usa
(grafo y borradores) decide si son saltos internos de una funcion o llamadas a otras funciones.
"""

import struct
from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

MINIMO_PALABRAS: Final[int] = 2
"""Largo minimo de una corrida: en el ejecutable real las corridas miden 13, 21, 231 y 274."""


@dataclass(frozen=True)
class Corrida:
    """Palabras consecutivas de los datos que apuntan al codigo del juego."""

    direccion: int
    destinos: tuple[int, ...]

    @property
    def fin(self) -> int:
        """Primera direccion posterior a la corrida."""
        return self.direccion + 4 * len(self.destinos)


def detectar_corridas(
    segmento: bytes,
    base: int,
    datos: tuple[int, int],
    codigo: tuple[int, int],
    minimo: int = MINIMO_PALABRAS,
) -> list[Corrida]:
    """
    Busca corridas de palabras alineadas que apuntan a una zona de codigo.

    Contexto:
        Alimenta las aristas "por tabla" del grafo y la creacion de las tablas de salto que
        necesita ``m2c`` para decompilar un ``switch``.

    Args:
        segmento (bytes): Segmento cargado del ejecutable.
        base (int): Direccion virtual del primer byte del segmento.
        datos (tuple[int, int]): Rango ``[inicio, fin)`` donde buscar.
        codigo (tuple[int, int]): Rango ``[inicio, fin)`` al que deben apuntar las palabras.
        minimo (int, opcional): Largo minimo de una corrida.

    Returns:
        list[Corrida]: Corridas en orden ascendente de direccion.

    Raises:
        ValueError: Si el rango de datos no esta alineado a 4 o sale del segmento, o si ``minimo``
            es menor que 1.

    Ejemplo:
        corridas = detectar_corridas(segmento, 0x80014A00, (0x8005DEA0, 0x80069A00), (0x80014AC4, 0x80045DA0))
    """
    inicio, fin = datos
    if minimo < 1:
        raise ValueError("tablas: el largo minimo debe ser al menos 1")
    if inicio % 4 or fin % 4 or inicio < base or fin > base + len(segmento) or inicio > fin:
        raise ValueError("tablas: el rango de datos debe estar alineado a 4 y dentro del segmento")
    corridas: list[Corrida] = []
    actuales: list[int] = []
    for direccion in range(inicio, fin, 4):
        (valor,) = struct.unpack_from("<I", segmento, direccion - base)
        if codigo[0] <= valor < codigo[1] and valor % 4 == 0:
            actuales.append(valor)
            continue
        _cerrar(corridas, direccion, actuales, minimo)
        actuales = []
    _cerrar(corridas, fin, actuales, minimo)
    return corridas


def _cerrar(corridas: list[Corrida], fin: int, destinos: list[int], minimo: int) -> None:
    """Agrega la corrida acumulada si alcanza el largo minimo."""
    if len(destinos) >= minimo:
        corridas.append(Corrida(fin - 4 * len(destinos), tuple(destinos)))


def corrida_que_contiene(corridas: list[Corrida], direccion: int) -> Corrida | None:
    """
    Busca la corrida que contiene una direccion.

    Contexto:
        Resuelve a que tabla pertenece una direccion referenciada por una funcion.

    Args:
        corridas (list[Corrida]): Corridas ordenadas por direccion (salida de ``detectar_corridas``).
        direccion (int): Direccion de dato.

    Returns:
        Corrida | None: La corrida si ``direccion`` cae dentro de ella.

    Ejemplo:
        corrida = corrida_que_contiene(corridas, 0x8005E370)
    """
    posicion = bisect_right([c.direccion for c in corridas], direccion) - 1
    if posicion >= 0 and corridas[posicion].direccion <= direccion < corridas[posicion].fin:
        return corridas[posicion]
    return None


def tramo_de_tabla(corrida: Corrida, direccion: int, fronteras: Iterable[int]) -> tuple[int, ...]:
    """
    Devuelve los destinos de la tabla que empieza en una direccion de la corrida.

    Contexto:
        Una corrida suele ser varias tablas pegadas. Una tabla empieza donde alguna funcion
        referencia el dato y termina en la siguiente direccion referenciada o al acabar la corrida.

    Args:
        corrida (Corrida): Corrida que contiene ``direccion``.
        direccion (int): Direccion donde empieza la tabla (alineada a 4 y dentro de la corrida).
        fronteras (Iterable[int]): Direcciones base referenciadas por cualquier funcion.

    Returns:
        tuple[int, ...]: Destinos desde ``direccion`` hasta la siguiente frontera.

    Raises:
        ValueError: Si ``direccion`` no esta alineada o cae fuera de la corrida.

    Ejemplo:
        destinos = tramo_de_tabla(corrida, 0x8005E370, fronteras)
    """
    if direccion % 4 or not corrida.direccion <= direccion < corrida.fin:
        raise ValueError("tablas: la direccion debe estar alineada y dentro de la corrida")
    siguientes = [f for f in fronteras if direccion < f < corrida.fin]
    tope = min(siguientes) if siguientes else corrida.fin
    primero = (direccion - corrida.direccion) // 4
    return corrida.destinos[primero : primero + (tope - direccion) // 4]

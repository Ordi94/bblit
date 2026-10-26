"""
Modelos y reglas puras del oraculo de emulador.

Contexto:
    Capa de dominio de `tools.emulador`: no toca disco, red ni procesos. Valida volcados de RAM,
    traduce direcciones de la consola a offsets y compara regiones de memoria.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass

RAM_BASE = 0x80000000
RAM_TAMANO = 0x200000
RAM_FIN = RAM_BASE + RAM_TAMANO


@dataclass(frozen=True)
class ResultadoComparacion:
    """
    Resultado de comparar dos regiones de bytes.

    Contexto:
        Lo produce `comparar_regiones` y lo serializa el comando `comparar`.

    Attributes:
        direccion (int): Direccion de consola donde empieza la region comparada.
        bytes_comparados (int): Longitud comparada (el minimo de las dos regiones).
        bytes_iguales (int): Posiciones con el mismo valor.
        bytes_distintos (int): Posiciones con valor distinto.
        primer_offset_distinto (int | None): Offset relativo al inicio de la region, o None.
        longitud_a (int): Longitud disponible de la primera region.
        longitud_b (int): Longitud disponible de la segunda region.
    """

    direccion: int
    bytes_comparados: int
    bytes_iguales: int
    bytes_distintos: int
    primer_offset_distinto: int | None
    longitud_a: int
    longitud_b: int

    @property
    def porcentaje_igual(self) -> float:
        """
        Porcentaje de bytes iguales sobre los comparados.

        Contexto:
            Cifra de resumen que se compara con la tasa documentada de coincidencia.

        Returns:
            float: Valor entre 0 y 100 con cuatro decimales; 100.0 si no hay nada que comparar.

        Ejemplo:
            ResultadoComparacion(0x80000000, 4, 3, 1, 2, 4, 4).porcentaje_igual  # 75.0
        """
        if self.bytes_comparados == 0:
            return 100.0
        return round(100.0 * self.bytes_iguales / self.bytes_comparados, 4)

    @property
    def tamano_distinto(self) -> bool:
        """
        Indica si las dos regiones tenian longitudes distintas.

        Contexto:
            Avisa de que solo se comparo el minimo y el resto quedo fuera.

        Returns:
            bool: True si `longitud_a` difiere de `longitud_b`.

        Ejemplo:
            resultado.tamano_distinto
        """
        return self.longitud_a != self.longitud_b

    def a_json(self) -> dict[str, object]:
        """
        Serializa el resultado con claves en camelCase.

        Contexto:
            Contrato de salida del comando `comparar`.

        Returns:
            dict[str, object]: Diccionario listo para `json.dumps`.

        Ejemplo:
            print(json.dumps(resultado.a_json()))
        """
        return {
            "direccion": f"0x{self.direccion:08X}",
            "bytesComparados": self.bytes_comparados,
            "bytesIguales": self.bytes_iguales,
            "bytesDistintos": self.bytes_distintos,
            "primerOffsetDistinto": self.primer_offset_distinto,
            "porcentajeIgual": self.porcentaje_igual,
            "longitudA": self.longitud_a,
            "longitudB": self.longitud_b,
            "tamanoDistinto": self.tamano_distinto,
        }


def validar_ram(datos: bytes) -> bytes:
    """
    Comprueba que un volcado tiene exactamente el tamano de la RAM principal.

    Contexto:
        Se aplica a lo que devuelve el emulador y a los volcados leidos de disco antes de
        compararlos: un volcado truncado desplazaria todas las conclusiones.

    Args:
        datos (bytes): Contenido del volcado.

    Returns:
        bytes: El mismo contenido, sin copiarlo.

    Raises:
        ValueError: Si el tamano no es 2.097.152 bytes.

    Ejemplo:
        ram = validar_ram(contenido)
    """
    if len(datos) != RAM_TAMANO:
        raise ValueError(f"volcado de RAM: se esperaban {RAM_TAMANO} bytes y hay {len(datos)}")
    return datos


def offset_de_ram(direccion: int, longitud: int = 0) -> int:
    """
    Traduce una direccion de consola al offset dentro del volcado de RAM.

    Contexto:
        Todas las lecturas de regiones pasan por aqui para rechazar direcciones fuera de
        `0x80000000..0x80200000` y regiones que se salgan del final de la RAM.

    Args:
        direccion (int): Direccion virtual de la consola (segmento KSEG0).
        longitud (int, opcional): Longitud de la region que se quiere leer.

    Returns:
        int: Offset de la direccion dentro del volcado.

    Raises:
        ValueError: Si la direccion esta fuera de la RAM, la longitud es negativa o la region
            sobrepasa el final de la RAM.

    Ejemplo:
        offset_de_ram(0x80014A00)  # 0x14A00
    """
    if not RAM_BASE <= direccion < RAM_FIN:
        raise ValueError(f"direccion 0x{direccion:08X}: se esperaba un valor en 0x80000000..0x801FFFFF")
    if longitud < 0:
        raise ValueError(f"longitud {longitud}: se esperaba un valor mayor o igual a 0")
    if direccion + longitud > RAM_FIN:
        raise ValueError(f"region 0x{direccion:08X}+{longitud}: sobrepasa el final de la RAM (0x80200000)")
    return direccion - RAM_BASE


def comparar_regiones(direccion: int, region_a: bytes, region_b: bytes) -> ResultadoComparacion:
    """
    Compara dos regiones byte a byte hasta la longitud de la mas corta.

    Contexto:
        Nucleo del comando `comparar`: mide cuanto del ejecutable sigue intacto en memoria o
        cuanto difieren dos volcados tomados en momentos distintos.

    Args:
        direccion (int): Direccion de consola donde empiezan ambas regiones (solo informativa).
        region_a (bytes): Primera region.
        region_b (bytes): Segunda region.

    Returns:
        ResultadoComparacion: Conteos, primer offset distinto y longitudes originales.

    Raises:
        ValueError: Si la direccion esta fuera de la RAM.

    Ejemplo:
        resultado = comparar_regiones(0x80014A00, ram[0x14A00:], exe[0x800:])
    """
    offset_de_ram(direccion)
    comparados = min(len(region_a), len(region_b))
    vista_a = memoryview(region_a)[:comparados]
    vista_b = memoryview(region_b)[:comparados]
    distintos = sum(map(operator.ne, vista_a, vista_b))
    primero: int | None = None
    if distintos:
        primero = next(i for i, (x, y) in enumerate(zip(vista_a, vista_b, strict=True)) if x != y)
    return ResultadoComparacion(
        direccion=direccion,
        bytes_comparados=comparados,
        bytes_iguales=comparados - distintos,
        bytes_distintos=distintos,
        primer_offset_distinto=primero,
        longitud_a=len(region_a),
        longitud_b=len(region_b),
    )


PREFIJO_EJECUTABLE = 256
_MAGIA_PSX_EXE = b"PS-X EXE"
_CABECERA_PSX_EXE = 0x800


def prefijo_de_ejecutable(datos: bytes, largo: int = PREFIJO_EJECUTABLE) -> tuple[int, bytes]:
    """
    Extrae la direccion de carga y el inicio del texto de un ejecutable PS-X EXE.

    Contexto:
        Permite reconocer en la RAM que la consola ya cargo el ejecutable del juego: es el
        unico hito que distingue el arranque del juego de las pantallas de la BIOS.

    Args:
        datos (bytes): Contenido completo del ejecutable.
        largo (int, opcional): Bytes del texto que se usan como huella.

    Returns:
        tuple[int, bytes]: Direccion de carga y los primeros `largo` bytes del texto.

    Raises:
        ValueError: Si falta la firma `PS-X EXE`, el archivo es mas corto que la cabecera mas
            la huella, o la region de carga se sale de la RAM.

    Ejemplo:
        direccion, huella = prefijo_de_ejecutable(Path("SLUS_008.38").read_bytes())
    """
    if not datos.startswith(_MAGIA_PSX_EXE):
        raise ValueError("ejecutable: falta la firma `PS-X EXE`")
    if len(datos) < _CABECERA_PSX_EXE + largo:
        raise ValueError(f"ejecutable: se esperaban al menos {_CABECERA_PSX_EXE + largo} bytes")
    direccion = int.from_bytes(datos[0x18:0x1C], "little")
    offset_de_ram(direccion, largo)
    return direccion, datos[_CABECERA_PSX_EXE : _CABECERA_PSX_EXE + largo]


class EmuladorError(Exception):
    """
    Fallo operativo al hablar con el emulador o al gestionar sus procesos.

    Contexto:
        Lo lanzan `cliente`, `proceso` y `sesion`; el CLI lo traduce a un mensaje breve y exit 1.
        Se distingue de `ValueError`, que indica una entrada invalida del usuario o del emulador.
    """

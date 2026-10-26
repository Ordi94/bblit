"""Descompresor puro de las secciones del contenedor BZZ.

Contexto:
    Capa de descompresion: opera solo sobre ``bytes`` y no hace entrada/salida. Reproduce la
    rutina de descompresion del ejecutable del juego (un LZSS con ventana de 4 KB y banderas
    por bit); ``docs/FORMATO_BZZ.md`` describe el formato y el algoritmo con detalle.

Formato del flujo, resumido:
    * Byte 0: parametros. Los bits 0-2 (``k``) fijan cuantos bits del codigo de 16 bits van a
      la distancia (``9 + k``) y cuantos al indice de longitud (``7 - k``); los bits 3-4 son la
      escala de las longitudes largas. Los bits 5-7 son cero.
    * Bytes 1-3: ``n`` en big endian. El flujo contiene ``n + 1`` operaciones.
    * Despues, grupos de un byte de banderas (bit menos significativo primero, 1 = literal,
      0 = referencia) seguido de las operaciones que gobierna.
"""

from __future__ import annotations

from dataclasses import dataclass

TAMANO_CABECERA_FLUJO = 4
"""Bytes de la cabecera del flujo: parametros y numero de operaciones."""

K_MINIMO = 3
"""Menor valor de ``k`` que el juego usa; los inferiores tienen un comportamiento no util."""

K_MAXIMO = 7
"""Mayor valor de ``k`` representable en los tres bits bajos del byte de parametros."""

MASCARA_RESERVADA = 0xE0
"""Bits 5-7 del byte de parametros: deben ser cero."""

LIMITE_SALIDA_PREDETERMINADO = 64 * 1024 * 1024
"""Tope por omision de bytes descomprimidos; una seccion real mide menos de 1 MiB."""

LONGITUD_MINIMA = 3
"""Longitud de una referencia con indice 0."""


@dataclass(frozen=True)
class ResultadoDescompresion:
    """Resultado detallado de descomprimir un flujo.

    Attributes:
        datos: Bytes descomprimidos, sin el relleno final.
        bytes_consumidos: Posicion del flujo tras la ultima operacion leida.
        relleno_final: Bytes que habria producido una referencia final de distancia 0, que
            el original copia desde memoria sin inicializar y que por eso se omiten (0 si
            el flujo no termina con ese relleno).
    """

    datos: bytes
    bytes_consumidos: int
    relleno_final: int


def construir_tabla_longitudes(k: int, escala: int) -> tuple[int, ...]:
    """Construye la tabla que traduce el indice de longitud en longitud de copia.

    Contexto:
        La rutina del juego la arma en el scratchpad antes de decodificar; aqui se calcula
        una vez por flujo. Hay ``2 ** (7 - k)`` entradas.

    Args:
        k (int): Bits bajos del byte de parametros, entre 3 y 7.
        escala (int): Bits 3-4 del byte de parametros, entre 0 y 3.

    Returns:
        tuple[int, ...]: Longitud de copia para cada indice. Hasta ``(2 ** (7 - k)) // 2``
        la longitud crece de uno en uno desde 3; despues crece de ``2 ** escala`` en
        ``2 ** escala``.

    Raises:
        ValueError: Si ``k`` o ``escala`` estan fuera de rango.

    Ejemplo:
        tabla = construir_tabla_longitudes(3, 1)  # (3, 4, ..., 10, 12, 14, ..., 26)
    """
    if not K_MINIMO <= k <= K_MAXIMO:
        raise ValueError(f"k={k} fuera de rango {K_MINIMO}..{K_MAXIMO}")
    if not 0 <= escala <= 3:
        raise ValueError(f"escala={escala} fuera de rango 0..3")
    mascara = 0x7F >> k
    umbral = mascara >> 1
    return tuple(
        LONGITUD_MINIMA + (indice if indice <= umbral else umbral + ((indice - umbral) << escala))
        for indice in range(mascara + 1)
    )


def _leer_parametros(datos: bytes) -> tuple[int, int, int]:
    """Extrae y valida los parametros de la cabecera del flujo.

    Contexto:
        Primer paso de ``descomprimir_detallado``.

    Args:
        datos (bytes): Flujo comprimido completo.

    Returns:
        tuple[int, int, int]: ``k``, escala y numero de operaciones menos una (``n``).

    Raises:
        ValueError: Si el flujo mide menos de 4 bytes, usa bits reservados o un ``k`` que el
            juego no emplea.

    Ejemplo:
        k, escala, n = _leer_parametros(bytes([0x0B, 0, 0, 2]))
    """
    if len(datos) < TAMANO_CABECERA_FLUJO:
        raise ValueError(f"flujo demasiado corto: se esperaban al menos {TAMANO_CABECERA_FLUJO} bytes")
    parametros = datos[0]
    if parametros & MASCARA_RESERVADA:
        raise ValueError(f"parametros={parametros:#04x} usa bits reservados (5-7), se esperaba 0")
    k = parametros & 0x07
    if k < K_MINIMO:
        raise ValueError(f"parametros={parametros:#04x} tiene k={k}, se esperaba {K_MINIMO}..{K_MAXIMO}")
    escala = (parametros >> 3) & 0x03
    n = (datos[1] << 16) | (datos[2] << 8) | datos[3]
    return k, escala, n


def descomprimir_detallado(
    datos: bytes,
    limite_salida: int = LIMITE_SALIDA_PREDETERMINADO,
) -> ResultadoDescompresion:
    """Descomprime un flujo y devuelve ademas el detalle de la lectura.

    Contexto:
        Nucleo del descompresor. ``descomprimir`` lo envuelve para quien solo necesita los
        bytes; el inventario y las validaciones usan el detalle (bytes consumidos y relleno).

    Args:
        datos (bytes): Flujo comprimido. Puede incluir relleno de sector tras el final.
        limite_salida (int, opcional): Maximo de bytes descomprimidos admitidos.

    Returns:
        ResultadoDescompresion: Bytes obtenidos, posicion final del flujo y relleno omitido.

    Raises:
        ValueError: Si la cabecera del flujo es invalida, el flujo se acaba antes de cumplir
            sus operaciones, una referencia apunta antes del inicio de la salida, una
            referencia de distancia 0 no es la ultima operacion o la salida supera el
            limite.

    Ejemplo:
        resultado = descomprimir_detallado(bytes([0x0B, 0, 0, 1, 0xFF, 0x68, 0x69]))
    """
    k, escala, n = _leer_parametros(datos)
    tabla = construir_tabla_longitudes(k, escala)
    mascara = 0x7F >> k
    desplazamiento = 7 - k
    salida = bytearray()
    posicion = TAMANO_CABECERA_FLUJO
    banderas = 0
    relleno = 0
    restantes = n + 1
    try:
        while restantes:
            restantes -= 1
            if banderas <= 1:
                banderas = datos[posicion] | 0x100
                posicion += 1
            bit = banderas & 1
            banderas >>= 1
            if bit:
                salida.append(datos[posicion])
                posicion += 1
                continue
            codigo = (datos[posicion] << 8) | datos[posicion + 1]
            posicion += 2
            longitud = tabla[codigo & mascara]
            distancia = codigo >> desplazamiento
            if distancia == 0:
                if restantes:
                    raise ValueError("referencia con distancia=0 antes de la ultima operacion")
                relleno = longitud
                break
            inicio = len(salida) - distancia
            if inicio < 0:
                raise ValueError(
                    f"referencia con distancia={distancia} fuera de la salida ({len(salida)} bytes)",
                )
            if distancia >= longitud:
                salida += salida[inicio : inicio + longitud]
            else:
                salida += (salida[inicio:] * (longitud // distancia + 1))[:longitud]
            if len(salida) > limite_salida:
                raise ValueError(f"salida supera el limite de {limite_salida} bytes")
    except IndexError:
        raise ValueError("flujo comprimido truncado: se agoto antes de completar las operaciones") from None
    if len(salida) > limite_salida:
        raise ValueError(f"salida supera el limite de {limite_salida} bytes")
    return ResultadoDescompresion(datos=bytes(salida), bytes_consumidos=posicion, relleno_final=relleno)


def descomprimir(datos: bytes, limite_salida: int = LIMITE_SALIDA_PREDETERMINADO) -> bytes:
    """Descomprime el flujo de una seccion BZZ.

    Contexto:
        Funcion publica del descompresor, sin entrada/salida: la capa de lectura le pasa
        los bytes de cada seccion (incluido el relleno de sector) y escribe el resultado.

    Args:
        datos (bytes): Flujo comprimido de una seccion.
        limite_salida (int, opcional): Maximo de bytes descomprimidos admitidos.

    Returns:
        bytes: Contenido descomprimido, sin el relleno final no definido del original.

    Raises:
        ValueError: Si el flujo es invalido, esta truncado o excede el limite (ver
            ``descomprimir_detallado``).

    Ejemplo:
        contenido = descomprimir(bytes([0x0B, 0, 0, 1, 0xFF, 0x68, 0x69]))  # b"hi"
    """
    return descomprimir_detallado(datos, limite_salida).datos

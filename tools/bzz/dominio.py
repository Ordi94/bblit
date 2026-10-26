"""Modelo y reglas puras de la cabecera del contenedor BZZ.

Contexto:
    Capa de dominio del paquete: no abre archivos ni descomprime nada. Todo el resto del
    paquete confia en que ``leer_cabecera`` ya valido las cotas de la tabla de secciones,
    por eso aqui se rechaza cualquier dato que no cuadre con el formato que el juego acepta.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

TAMANO_SECTOR = 0x800
"""Tamano de un sector de datos del disco; la cabecera y cada seccion se alinean a el."""

VERSION_SOPORTADA = 1
"""Unico valor del campo de version presente en los archivos del juego."""

MAX_SECCIONES = 64
"""Cota superior del numero de secciones; los archivos reales tienen 3, 4 o 10."""

TIPOS_ADMITIDOS = frozenset(range(1, 11))
"""Tipos de seccion observados en el juego; cualquier otro valor se rechaza."""

TAMANO_ENTRADA = 12
"""Bytes de cada entrada de la tabla: tipo, tamano y tamano alineado (tres u32)."""

OFFSET_TABLA = 8
"""Offset de la primera entrada: tras los campos de version y numero de secciones."""

OFFSET_SUMA_CONTROL = 0x7FC
"""Offset del u32 con la suma de control, al final del primer sector."""


@dataclass(frozen=True)
class Seccion:
    """Entrada de la tabla de secciones junto con su posicion dentro del archivo.

    Attributes:
        indice: Posicion de la entrada en la tabla, desde 0.
        tipo: Identificador del tipo de contenido (1 a 10).
        offset: Posicion del primer byte comprimido dentro del archivo.
        tamano: Longitud en bytes del flujo comprimido, sin el relleno de sector.
        tamano_alineado: ``tamano`` redondeado hacia arriba a un multiplo de ``TAMANO_SECTOR``.
    """

    indice: int
    tipo: int
    offset: int
    tamano: int
    tamano_alineado: int


@dataclass(frozen=True)
class Cabecera:
    """Cabecera ya validada de un archivo BZZ.

    Attributes:
        version: Version del formato (siempre ``VERSION_SOPORTADA``).
        secciones: Secciones en el orden en que aparecen en el archivo.
    """

    version: int
    secciones: tuple[Seccion, ...]


def calcular_suma_control(datos: bytes) -> int:
    """Calcula la suma de control del primer sector del contenedor.

    Contexto:
        El cargador del juego suma como enteros con signo los primeros 0x7FC bytes del
        sector de cabecera y los compara con el u32 almacenado en el offset 0x7FC.
        ``leer_cabecera`` usa esta funcion para detectar cabeceras corruptas.

    Args:
        datos (bytes): Contenido del archivo; solo se leen los primeros 0x7FC bytes.

    Returns:
        int: Suma de bytes con signo, reducida a 32 bits sin signo.

    Raises:
        ValueError: Si ``datos`` tiene menos de 0x7FC bytes.

    Ejemplo:
        suma = calcular_suma_control(contenido_del_archivo)
    """
    if len(datos) < OFFSET_SUMA_CONTROL:
        raise ValueError(f"datos demasiado cortos: se esperaban al menos {OFFSET_SUMA_CONTROL} bytes")
    cabecera = datos[:OFFSET_SUMA_CONTROL]
    suma_sin_signo = sum(cabecera)
    negativos = sum(1 for valor in cabecera if valor >= 0x80)
    return (suma_sin_signo - 256 * negativos) & 0xFFFFFFFF


TOLERANCIA_CONSUMO = 3
"""Diferencia maxima entre los bytes que lee el descompresor y ``tamano`` de la seccion.

El tamano se redondea a multiplo de 4 y la ultima operacion puede leer hasta 3 bytes de
relleno, de modo que en el disco la diferencia observada va de -3 a +3.
"""


def validar_consumo(indice: int, consumidos: int, tamano: int) -> None:
    """Comprueba que el flujo leido concuerda con el tamano declarado de la seccion.

    Contexto:
        Detecta un campo ``n`` corrupto: si es menor al real, el descompresor termina antes
        y devolveria datos truncados sin error. Lo usa ``descomprimir_secciones``.

    Args:
        indice (int): Posicion de la seccion en la tabla.
        consumidos (int): Bytes del flujo que leyo el descompresor.
        tamano (int): Longitud declarada del flujo comprimido.

    Raises:
        ValueError: Si ``consumidos`` difiere de ``tamano`` en mas de ``TOLERANCIA_CONSUMO``.

    Ejemplo:
        validar_consumo(0, 28757, 28760)
    """
    if abs(consumidos - tamano) > TOLERANCIA_CONSUMO:
        raise ValueError(
            f"secciones[{indice}]: bytes consumidos={consumidos} no concuerda con "
            f"tamano={tamano} (diferencia maxima {TOLERANCIA_CONSUMO})",
        )


def nombre_archivo_seccion(indice: int, tipo: int) -> str:
    """Construye el nombre del archivo que guarda una seccion descomprimida.

    Contexto:
        Es la frontera con las herramientas de extraccion posteriores (imagenes, audio,
        modelos), que localizan cada seccion por este nombre.

    Args:
        indice (int): Posicion de la seccion en la tabla.
        tipo (int): Tipo de contenido de la seccion.

    Returns:
        str: Nombre con la forma ``<indice:02d>_tipo<tipo:02d>.bin``.

    Raises:
        ValueError: Si ``indice`` o ``tipo`` son negativos.

    Ejemplo:
        nombre = nombre_archivo_seccion(2, 3)  # "02_tipo03.bin"
    """
    if indice < 0 or tipo < 0:
        raise ValueError(f"indice={indice} y tipo={tipo} deben ser no negativos")
    return f"{indice:02d}_tipo{tipo:02d}.bin"


def _leer_seccion(datos: bytes, indice: int, offset_datos: int) -> Seccion:
    """Interpreta y valida la entrada ``indice`` de la tabla de secciones.

    Contexto:
        Auxiliar de ``leer_cabecera``; ``offset_datos`` es el offset que corresponde a la
        seccion segun las secciones anteriores.

    Args:
        datos (bytes): Contenido completo del archivo.
        indice (int): Posicion de la entrada en la tabla.
        offset_datos (int): Offset del primer byte de la seccion dentro del archivo.

    Returns:
        Seccion: Entrada validada.

    Raises:
        ValueError: Si el tipo no es admitido o los tamanos son incoherentes.

    Ejemplo:
        seccion = _leer_seccion(contenido, 0, TAMANO_SECTOR)
    """
    tipo, tamano, tamano_alineado = struct.unpack_from("<III", datos, OFFSET_TABLA + TAMANO_ENTRADA * indice)
    if tipo not in TIPOS_ADMITIDOS:
        raise ValueError(f"secciones[{indice}].tipo={tipo} no admitido, se esperaba 1..10")
    if tamano == 0:
        raise ValueError(f"secciones[{indice}].tamano=0 invalido, se esperaba al menos 1")
    if tamano > tamano_alineado:
        raise ValueError(
            f"secciones[{indice}].tamano={tamano} excede tamano_alineado={tamano_alineado}",
        )
    if tamano_alineado % TAMANO_SECTOR != 0:
        raise ValueError(
            f"secciones[{indice}].tamano_alineado={tamano_alineado} no es multiplo de {TAMANO_SECTOR}",
        )
    if tamano_alineado - tamano >= TAMANO_SECTOR:
        raise ValueError(
            f"secciones[{indice}].tamano_alineado={tamano_alineado} no es el menor multiplo de "
            f"{TAMANO_SECTOR} que contiene tamano={tamano}",
        )
    return Seccion(
        indice=indice,
        tipo=tipo,
        offset=offset_datos,
        tamano=tamano,
        tamano_alineado=tamano_alineado,
    )


def leer_cabecera(datos: bytes, *, verificar_suma: bool = True) -> Cabecera:
    """Interpreta y valida la cabecera de un contenedor BZZ.

    Contexto:
        Primer paso de ``desempaquetar`` y de ``generar_inventario``: el resto del paquete
        asume que las cotas de la tabla ya fueron comprobadas aqui.

    Args:
        datos (bytes): Contenido completo del archivo .BZZ.
        verificar_suma (bool, opcional): Si es verdadero (valor por defecto) exige que la
            suma de control del offset 0x7FC coincida con la calculada, igual que el
            cargador del juego.

    Returns:
        Cabecera: Version y secciones con su tipo, offset, tamano y tamano alineado.

    Raises:
        ValueError: Si el archivo mide menos de 0x800 bytes, la version no es 1,
            ``n_secciones`` esta fuera de 1..64, alguna entrada es incoherente, la suma de
            tamanos alineados mas el sector de cabecera no iguala el tamano del archivo o
            la suma de control no coincide.

    Ejemplo:
        cabecera = leer_cabecera(Path("L01A.BZZ").read_bytes())
    """
    if len(datos) < TAMANO_SECTOR:
        raise ValueError(f"archivo demasiado corto: se esperaban al menos {TAMANO_SECTOR} bytes")
    version, n_secciones = struct.unpack_from("<II", datos, 0)
    if version != VERSION_SOPORTADA:
        raise ValueError(f"version={version} no soportada, se esperaba {VERSION_SOPORTADA}")
    if not 1 <= n_secciones <= MAX_SECCIONES:
        raise ValueError(f"n_secciones={n_secciones} fuera de rango 1..{MAX_SECCIONES}")
    secciones: list[Seccion] = []
    offset_datos = TAMANO_SECTOR
    for indice in range(n_secciones):
        seccion = _leer_seccion(datos, indice, offset_datos)
        secciones.append(seccion)
        offset_datos += seccion.tamano_alineado
    if offset_datos != len(datos):
        raise ValueError(
            f"suma de tamano_alineado mas cabecera={offset_datos} distinta del tamano del "
            f"archivo={len(datos)}",
        )
    if verificar_suma:
        esperada = struct.unpack_from("<I", datos, OFFSET_SUMA_CONTROL)[0]
        calculada = calcular_suma_control(datos)
        if esperada != calculada:
            raise ValueError(f"suma_control={esperada:#x} distinta de la calculada={calculada:#x}")
    return Cabecera(version=version, secciones=tuple(secciones))

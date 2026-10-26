"""
Reglas puras de la imagen de disco: sectores Mode 2, EDC/ECC e ISO 9660.

Contexto:
    Capa de dominio del paquete `tools.disco`. No hace entrada/salida: recibe y devuelve
    `bytes`, de modo que se prueba con sectores sinteticos. La capa de infraestructura
    (`tools.disco.imagen`) lee y escribe el archivo de la imagen usando estas funciones.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

TAMANO_SECTOR_CRUDO = 2352
TAMANO_DATOS = 2048
TAMANO_SINCRONIA = 12
TAMANO_CABECERA = 4
TAMANO_SUBCABECERA = 8
OFFSET_SUBCABECERA = TAMANO_SINCRONIA + TAMANO_CABECERA
OFFSET_DATOS = OFFSET_SUBCABECERA + TAMANO_SUBCABECERA
OFFSET_EDC = OFFSET_DATOS + TAMANO_DATOS
OFFSET_ECC = OFFSET_EDC + 4
TAMANO_ECC_P = 172
TAMANO_ECC_Q = 104
TAMANO_ECC = TAMANO_ECC_P + TAMANO_ECC_Q
SINCRONIA = b"\x00" + b"\xff" * 10 + b"\x00"
MODO_2 = 2
MASCARA_FORM_2 = 0x20
INDICE_SUBMODO = 2
LBA_DESCRIPTOR_VOLUMEN = 16
MAX_REGISTROS_POR_SECTOR = 128
POLINOMIO_EDC = 0xD8018001
POLINOMIO_CAMPO_ECC = 0x11D
LONGITUD_MINIMA_REGISTRO = 34
INDICADOR_DIRECTORIO = 0x02
OFFSET_RAIZ_EN_DESCRIPTOR = 156


def _construir_tablas() -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    """
    Calcula las tablas de busqueda de EDC y de aritmetica del campo de Galois del ECC.

    Contexto:
        Se ejecuta una sola vez al importar el modulo para poblar `_TABLA_EDC`,
        `_TABLA_ADELANTE` y `_TABLA_ATRAS`.

    Returns:
        tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]: tabla CRC del EDC, tabla de
        multiplicacion por 2 en GF(256) y su inversa auxiliar.

    Ejemplo:
        edc, adelante, atras = _construir_tablas()
    """
    edc_tabla: list[int] = []
    adelante = [0] * 256
    atras = [0] * 256
    for i in range(256):
        edc = i
        for _ in range(8):
            edc = (edc >> 1) ^ (POLINOMIO_EDC if edc & 1 else 0)
        edc_tabla.append(edc)
        doble = ((i << 1) ^ (POLINOMIO_CAMPO_ECC if i & 0x80 else 0)) & 0xFF
        adelante[i] = doble
        atras[i ^ doble] = i
    return tuple(edc_tabla), tuple(adelante), tuple(atras)


_TABLA_EDC, _TABLA_ADELANTE, _TABLA_ATRAS = _construir_tablas()


@dataclass(frozen=True)
class EntradaDirectorio:
    """Registro de directorio ISO 9660 reducido a lo que necesita el reempaquetado."""

    nombre: str
    lba: int
    tamano: int
    es_directorio: bool


def lba_a_offset(lba: int) -> int:
    """
    Convierte un numero de sector logico en el desplazamiento en bytes dentro del `.bin`.

    Contexto:
        Base de toda lectura y escritura por sectores en `tools.disco.imagen`.

    Args:
        lba (int): Sector logico, contado desde el primer sector de la pista.

    Returns:
        int: Desplazamiento en bytes del inicio del sector crudo de 2352 bytes.

    Raises:
        ValueError: Si `lba` es negativo.

    Ejemplo:
        lba_a_offset(16)  # 37632
    """
    if lba < 0:
        raise ValueError(f"lba={lba} fuera de rango: se esperaba un valor >= 0")
    return lba * TAMANO_SECTOR_CRUDO


def es_form_2(subcabecera: bytes) -> bool:
    """
    Indica si una subcabecera Mode 2 corresponde a un sector Form 2.

    Contexto:
        Los sectores de audio XA son Form 2 (sin ECC, 2324 bytes de datos); solo los Form 1
        se pueden reescribir con EDC/ECC. El bit 5 del submodo distingue ambas formas.

    Args:
        subcabecera (bytes): Los 8 bytes de subcabecera del sector.

    Returns:
        bool: True si el bit Form 2 del submodo esta activo.

    Raises:
        ValueError: Si la subcabecera no mide 8 bytes.

    Ejemplo:
        es_form_2(bytes([0, 0, 0x20, 0, 0, 0, 0x20, 0]))  # True
    """
    if len(subcabecera) != TAMANO_SUBCABECERA:
        raise ValueError(f"subcabecera de {len(subcabecera)} bytes: se esperaban {TAMANO_SUBCABECERA}")
    return bool(subcabecera[INDICE_SUBMODO] & MASCARA_FORM_2)


def validar_sector_crudo(sector: bytes) -> None:
    """
    Comprueba que un bloque de 2352 bytes tenga forma de sector Mode 2.

    Contexto:
        Se invoca antes de interpretar o reescribir cualquier sector leido de la imagen,
        para no propagar basura si el archivo no es una imagen MODE2/2352.

    Args:
        sector (bytes): Sector crudo completo.

    Raises:
        ValueError: Si el tamano no es 2352, la sincronia es invalida o el modo no es 2.

    Ejemplo:
        validar_sector_crudo(sector)
    """
    if len(sector) != TAMANO_SECTOR_CRUDO:
        raise ValueError(f"sector de {len(sector)} bytes: se esperaban {TAMANO_SECTOR_CRUDO}")
    if sector[:TAMANO_SINCRONIA] != SINCRONIA:
        raise ValueError("sincronia del sector invalida: se esperaba 00 FF*10 00")
    if sector[TAMANO_SINCRONIA + 3] != MODO_2:
        raise ValueError(f"modo={sector[TAMANO_SINCRONIA + 3]} no soportado: se esperaba {MODO_2}")


def calcular_edc(datos: bytes) -> int:
    """
    Calcula el codigo de deteccion de errores (EDC) de un bloque.

    Contexto:
        En Mode 2 Form 1 el EDC cubre subcabecera y datos del usuario (2056 bytes).

    Args:
        datos (bytes): Bloque sobre el que se calcula el CRC.

    Returns:
        int: Valor de 32 bits del EDC (se almacena en little endian).

    Ejemplo:
        calcular_edc(sector[16:2072])
    """
    edc = 0
    for byte in datos:
        edc = (edc >> 8) ^ _TABLA_EDC[(edc ^ byte) & 0xFF]
    return edc


def _bloque_ecc(origen: bytes, mayor: int, menor: int, mult_mayor: int, inc_menor: int) -> bytes:
    """
    Calcula una familia de paridades Reed-Solomon (P o Q) del ECC.

    Contexto:
        Funcion interna de `calcular_ecc`; P usa (86, 24, 2, 86) y Q usa (52, 43, 86, 88).

    Args:
        origen (bytes): Bytes sobre los que se calcula (empieza en el byte 12 del sector).
        mayor (int): Numero de palabras de paridad por mitad.
        menor (int): Numero de bytes que intervienen en cada palabra.
        mult_mayor (int): Multiplicador del indice de arranque de cada palabra.
        inc_menor (int): Salto entre bytes consecutivos de una palabra.

    Returns:
        bytes: `2 * mayor` bytes de paridad.

    Ejemplo:
        _bloque_ecc(sector[12:2076], 86, 24, 2, 86)
    """
    total = mayor * menor
    mitad_a = bytearray(mayor)
    mitad_b = bytearray(mayor)
    for i in range(mayor):
        indice = (i >> 1) * mult_mayor + (i & 1)
        ecc_a = 0
        ecc_b = 0
        for _ in range(menor):
            temporal = origen[indice]
            indice += inc_menor
            if indice >= total:
                indice -= total
            ecc_a ^= temporal
            ecc_b ^= temporal
            ecc_a = _TABLA_ADELANTE[ecc_a]
        ecc_a = _TABLA_ATRAS[_TABLA_ADELANTE[ecc_a] ^ ecc_b]
        mitad_a[i] = ecc_a
        mitad_b[i] = ecc_a ^ ecc_b
    return bytes(mitad_a + mitad_b)


def calcular_ecc(sector: bytes) -> bytes:
    """
    Calcula los 276 bytes de ECC (paridades P y Q) de un sector Mode 2 Form 1.

    Contexto:
        En Mode 2 la direccion de la cabecera no entra al calculo (se trata como ceros);
        asi los sectores pueden relocalizarse sin recalcular. Las paridades Q cubren
        tambien las P ya calculadas.

    Args:
        sector (bytes): Sector crudo de 2352 bytes; se leen los bytes 12 a 2075.

    Returns:
        bytes: 172 bytes de paridad P seguidos de 104 de paridad Q.

    Raises:
        ValueError: Si el sector no mide 2352 bytes.

    Ejemplo:
        ecc = calcular_ecc(sector)
    """
    if len(sector) != TAMANO_SECTOR_CRUDO:
        raise ValueError(f"sector de {len(sector)} bytes: se esperaban {TAMANO_SECTOR_CRUDO}")
    origen = bytearray(sector[TAMANO_SINCRONIA:OFFSET_ECC])
    origen[:TAMANO_CABECERA] = b"\x00" * TAMANO_CABECERA
    paridad_p = _bloque_ecc(bytes(origen), 86, 24, 2, 86)
    paridad_q = _bloque_ecc(bytes(origen) + paridad_p, 52, 43, 86, 88)
    return paridad_p + paridad_q


def construir_sector_form1(sector_original: bytes, datos: bytes) -> bytes:
    """
    Sustituye los datos de usuario de un sector Form 1 y recalcula EDC y ECC.

    Contexto:
        Operacion central del reempaquetado: conserva sincronia, cabecera y subcabecera del
        sector original (direccion, archivo, canal, submodo) y solo cambia el contenido.

    Args:
        sector_original (bytes): Sector crudo de 2352 bytes que se va a reemplazar.
        datos (bytes): Nuevo contenido de exactamente 2048 bytes.

    Returns:
        bytes: Sector crudo nuevo con EDC y ECC coherentes.

    Raises:
        ValueError: Si el sector es invalido, es Form 2 o `datos` no mide 2048 bytes.

    Ejemplo:
        nuevo = construir_sector_form1(original, contenido)
    """
    extraer_datos(sector_original)
    if len(datos) != TAMANO_DATOS:
        raise ValueError(f"datos de {len(datos)} bytes: se esperaban {TAMANO_DATOS}")
    nuevo = bytearray(sector_original)
    nuevo[OFFSET_DATOS:OFFSET_EDC] = datos
    edc = calcular_edc(bytes(nuevo[OFFSET_SUBCABECERA:OFFSET_EDC]))
    nuevo[OFFSET_EDC:OFFSET_ECC] = struct.pack("<I", edc)
    nuevo[OFFSET_ECC:] = calcular_ecc(bytes(nuevo))
    return bytes(nuevo)


def extraer_datos(sector: bytes) -> bytes:
    """
    Devuelve los 2048 bytes de datos de usuario de un sector Form 1.

    Contexto:
        Lectura del volumen ISO 9660 y comparacion de contenido antes de reescribir.

    Args:
        sector (bytes): Sector crudo de 2352 bytes.

    Returns:
        bytes: Datos de usuario.

    Raises:
        ValueError: Si el sector es invalido o es Form 2.

    Ejemplo:
        datos = extraer_datos(sector)
    """
    validar_sector_crudo(sector)
    if es_form_2(sector[OFFSET_SUBCABECERA:OFFSET_DATOS]):
        raise ValueError("el sector es Form 2: solo los sectores Form 1 tienen 2048 bytes de datos")
    return sector[OFFSET_DATOS:OFFSET_EDC]


def parsear_raiz(descriptor: bytes) -> EntradaDirectorio:
    """
    Lee el registro del directorio raiz dentro del descriptor primario de volumen.

    Contexto:
        Primer paso de la busqueda de un archivo: el sector 16 de la imagen contiene el
        descriptor y en el offset 156 el registro de la raiz.

    Args:
        descriptor (bytes): Datos de usuario (2048 bytes) del sector 16.

    Returns:
        EntradaDirectorio: Raiz con su LBA y tamano.

    Raises:
        ValueError: Si no es un descriptor primario `CD001` o el registro de la raiz es invalido.

    Ejemplo:
        raiz = parsear_raiz(extraer_datos(sector_16))
    """
    if len(descriptor) != TAMANO_DATOS:
        raise ValueError(f"descriptor de {len(descriptor)} bytes: se esperaban {TAMANO_DATOS}")
    if descriptor[0] != 1 or descriptor[1:6] != b"CD001":
        raise ValueError("el sector 16 no es un descriptor primario de volumen ISO 9660")
    inicio = OFFSET_RAIZ_EN_DESCRIPTOR
    entradas = parsear_directorio(descriptor[inicio : inicio + LONGITUD_MINIMA_REGISTRO])
    if len(entradas) != 1 or not entradas[0].es_directorio:
        raise ValueError("registro del directorio raiz invalido")
    return entradas[0]


def parsear_directorio(datos: bytes) -> list[EntradaDirectorio]:
    """
    Interpreta los registros de directorio ISO 9660 contenidos en un bloque.

    Contexto:
        Se aplica a cada sector del directorio. Un byte de longitud cero indica relleno hasta
        el final del sector. Los registros nunca cruzan el limite de sector.

    Args:
        datos (bytes): Bloque con registros consecutivos.

    Returns:
        list[EntradaDirectorio]: Entradas en orden de aparicion, incluidas `.` y `..`
        (nombres de un solo byte 0x00 y 0x01, que se devuelven tal cual).

    Raises:
        ValueError: Si un registro excede el bloque, es mas corto que su minimo o trae un
            nombre que desborda el registro, o si hay mas de 128 registros por bloque.

    Ejemplo:
        entradas = parsear_directorio(extraer_datos(sector))
    """
    entradas: list[EntradaDirectorio] = []
    posicion = 0
    while posicion < len(datos):
        longitud = datos[posicion]
        if longitud == 0:
            break
        if len(entradas) >= MAX_REGISTROS_POR_SECTOR:
            raise ValueError(f"mas de {MAX_REGISTROS_POR_SECTOR} registros de directorio en un bloque")
        if longitud < LONGITUD_MINIMA_REGISTRO or posicion + longitud > len(datos):
            raise ValueError(f"longitud de registro={longitud} fuera de rango en el offset {posicion}")
        registro = datos[posicion : posicion + longitud]
        largo_nombre = registro[32]
        if 33 + largo_nombre > longitud:
            raise ValueError(f"largo de nombre={largo_nombre} desborda el registro de {longitud} bytes")
        lba = struct.unpack_from("<I", registro, 2)[0]
        tamano = struct.unpack_from("<I", registro, 10)[0]
        nombre = registro[33 : 33 + largo_nombre].decode("ascii", errors="replace")
        es_directorio = bool(registro[25] & INDICADOR_DIRECTORIO)
        entradas.append(EntradaDirectorio(nombre, lba, tamano, es_directorio))
        posicion += longitud
    return entradas


def normalizar_nombre(nombre: str) -> str:
    """
    Normaliza un nombre de archivo ISO 9660 para compararlo sin el sufijo de version.

    Contexto:
        El directorio guarda `SLUS_008.38;1`; el usuario escribe `SLUS_008.38`.

    Args:
        nombre (str): Nombre con o sin `;version`.

    Returns:
        str: Nombre en mayusculas sin version.

    Ejemplo:
        normalizar_nombre("slus_008.38;1")  # "SLUS_008.38"
    """
    return nombre.split(";", 1)[0].upper()


def validar_tamano_ejecutable(tamano_nuevo: int, tamano_registrado: int) -> None:
    """
    Verifica que el ejecutable nuevo ocupe exactamente lo registrado en el directorio.

    Contexto:
        La sustitucion in-place solo es posible con el mismo tamano; uno distinto desplaza
        todo el contenido posterior del disco y exige reconstruir la imagen completa.

    Args:
        tamano_nuevo (int): Tamano en bytes del ejecutable aportado.
        tamano_registrado (int): Tamano en bytes que figura en el directorio de la imagen.

    Raises:
        ValueError: Si los tamanos difieren.

    Ejemplo:
        validar_tamano_ejecutable(350208, 350208)
    """
    if tamano_nuevo != tamano_registrado:
        raise ValueError(
            f"tamano del ejecutable={tamano_nuevo} distinto del registrado en la imagen "
            f"({tamano_registrado}): hace falta reconstruir la imagen completa"
        )


def generar_cue(nombre_bin: str) -> str:
    """
    Genera la hoja CUE de una imagen de una sola pista MODE2/2352.

    Contexto:
        Acompana a la imagen reempaquetada; referencia el `.bin` por nombre relativo para que
        la pareja pueda moverse de carpeta.

    Args:
        nombre_bin (str): Nombre de archivo (sin carpetas) del `.bin`.

    Returns:
        str: Contenido del `.cue` con saltos de linea CRLF.

    Raises:
        ValueError: Si el nombre esta vacio, contiene separadores de ruta o comillas.

    Ejemplo:
        generar_cue("bblit_prueba.bin")
    """
    if not nombre_bin or any(c in nombre_bin for c in ("/", "\\", '"')):
        raise ValueError("nombre_bin debe ser un nombre de archivo sin separadores de ruta ni comillas")
    return f'FILE "{nombre_bin}" BINARY\r\n  TRACK 01 MODE2/2352\r\n    INDEX 01 00:00:00\r\n'

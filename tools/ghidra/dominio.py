"""Modelo y reglas puras de la tabla de simbolos del ejecutable.

Este modulo no toca disco ni procesos: recibe funciones ya leidas de la exportacion de Ghidra y
produce simbolos validados en el formato que consume el desensamblador. Todas las decisiones
sobre nombres, tamanos y rangos viven aqui para poder probarlas sin Ghidra.
"""

import re
from collections import Counter
from dataclasses import dataclass
from typing import Final, Literal

DIRECCION_BASE: Final[int] = 0x80014A00
"""Direccion de carga del unico segmento del ejecutable."""

TAMANO_SEGMENTO: Final[int] = 0x55000
"""Tamano en bytes del segmento cargado (codigo, rodata y data del ejecutable)."""

DIRECCION_FIN: Final[int] = DIRECCION_BASE + TAMANO_SEGMENTO
"""Primera direccion posterior al segmento (limite exclusivo)."""

DIRECCION_ENTRADA: Final[int] = 0x80014A08
"""Punto de entrada declarado en la cabecera del ejecutable."""

ALINEACION_FUNCION: Final[int] = 4
"""Las instrucciones MIPS ocupan 4 bytes: toda funcion empieza en multiplo de 4."""

NOMBRE_ENTRADA_C: Final[str] = "main"
"""Nombre que el cargador asigna a la rutina que invoca el codigo de arranque."""

LONGITUD_MAXIMA_NOMBRE: Final[int] = 128
"""Cota de longitud para un simbolo: evita que una exportacion hostil crezca sin limite."""

FIN_CODIGO: Final[int] = 0x8005DEA0
"""Fin de la zona de codigo: la ultima funcion cierra con ``jr ra`` y despues solo hay datos."""

TAMANO_MINIMO_FUNCION: Final[int] = 8
"""Una funcion ocupa al menos un retorno y su ranura de retardo."""

TipoSimbolo = Literal["func", "u8", "u16", "u32"]

_PATRON_IDENTIFICADOR: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PATRON_CARACTER_INVALIDO: Final[re.Pattern[str]] = re.compile(r"[^A-Za-z0-9_]")


@dataclass(frozen=True, slots=True)
class Funcion:
    """Una funcion tal como la exporta Ghidra, ya validada en cotas.

    Contexto:
        Es la fila de ``funciones.csv``; la produce la capa de lectura y la consumen
        ``construir_simbolos`` y ``calcular_informe``.

    Attributes:
        direccion (int): Direccion de la primera instruccion.
        nombre (str): Nombre asignado por Ghidra (firma de libreria o ``FUN_...``).
        tamano (int): Bytes que Ghidra atribuye al cuerpo de la funcion.
        es_libreria (bool): Si una firma de Psy-Q identifica la funcion.
        libreria_origen (str): Libreria y objeto de la firma, separados por ``|`` si hay varios.
        llamadores (int): Cantidad de sitios de llamada distintos que la invocan.
        nombre_oficial (bool): Si ``nombre`` es un simbolo exportado por el SDK.
        comentario (str): Candidatos alternos que Ghidra anoto cuando la firma es ambigua.
    """

    direccion: int
    nombre: str
    tamano: int
    es_libreria: bool
    libreria_origen: str
    llamadores: int
    nombre_oficial: bool
    comentario: str


@dataclass(frozen=True, slots=True)
class Simbolo:
    """Una linea de la tabla de simbolos.

    Contexto:
        Es el elemento de ``config/symbols.txt``; el desensamblador lo lee como unica fuente
        de verdad de nombres.

    Attributes:
        nombre (str): Identificador C valido.
        direccion (int): Direccion dentro del segmento.
        tipo (TipoSimbolo): ``func`` o un tipo de dato del desensamblador (``u8``, ``u16``, ``u32``).
        tamano (int): Bytes que ocupa el simbolo.
    """

    nombre: str
    direccion: int
    tipo: TipoSimbolo
    tamano: int


@dataclass(frozen=True, slots=True)
class Informe:
    """Cifras de cobertura de la identificacion de funciones.

    Contexto:
        Lo imprime el comando ``informe`` y se copia a la documentacion del analisis.

    Attributes:
        total (int): Funciones del segmento.
        libreria (int): Funciones identificadas por firma como de libreria.
        libreria_oficial (int): De las anteriores, las que llevan nombre exportado por el SDK.
        libreria_local (int): De las anteriores, rutinas internas de un objeto sin nombre propio.
        juego (int): Funciones que ninguna firma identifica.
        ambiguas (int): Funciones de libreria con candidatos alternos anotados.
        bytes_cubiertos (int): Bytes del segmento dentro de alguna funcion (sin solapes).
        porcentaje_cubierto (float): ``bytes_cubiertos`` sobre ``TAMANO_SEGMENTO`` en porcentaje.
    """

    total: int
    libreria: int
    libreria_oficial: int
    libreria_local: int
    juego: int
    ambiguas: int
    bytes_cubiertos: int
    porcentaje_cubierto: float


def nombre_por_defecto(direccion: int) -> str:
    """
    Construye el nombre de una funcion sin identificar.

    Contexto:
        Convencion del proyecto para funciones del juego y rutinas de libreria sin nombre
        exportado; ``asignar_nombres`` la usa como respaldo.

    Args:
        direccion (int): Direccion de la funcion.

    Returns:
        str: ``func_`` seguido de la direccion en ocho digitos hexadecimales en mayusculas.

    Raises:
        ValueError: Si la direccion no cabe en 32 bits.

    Ejemplo:
        nombre = nombre_por_defecto(0x80016414)  # "func_80016414"
    """
    if not 0 <= direccion <= 0xFFFFFFFF:
        raise ValueError(f"direccion={direccion} fuera de 32 bits")
    return f"func_{direccion:08X}"


def es_identificador_c(nombre: str) -> bool:
    """
    Indica si un texto es un identificador valido del lenguaje C.

    Contexto:
        Filtro final de ``validar_simbolos`` y del lector de ``symbols.txt``.

    Args:
        nombre (str): Texto a comprobar.

    Returns:
        bool: Verdadero si empieza por letra o guion bajo, solo usa letras ASCII, digitos y
            guion bajo, y no supera ``LONGITUD_MAXIMA_NOMBRE``.

    Ejemplo:
        es_identificador_c("DrawSync")  # True
    """
    return len(nombre) <= LONGITUD_MAXIMA_NOMBRE and _PATRON_IDENTIFICADOR.match(nombre) is not None


def normalizar_nombre(nombre: str) -> str:
    """
    Convierte un nombre arbitrario en un identificador C valido.

    Contexto:
        Los nombres de las firmas pueden traer puntos o empezar por digito (``2MBYTE.OBJ``);
        el desensamblador y el compilador exigen identificadores.

    Args:
        nombre (str): Nombre tal como lo entrega Ghidra.

    Returns:
        str: El nombre con cada caracter no permitido sustituido por guion bajo y con un guion
            bajo delante si empezaba por digito. Un nombre vacio da ``_``.

    Ejemplo:
        normalizar_nombre("2MBYTE.OBJ")  # "_2MBYTE_OBJ"
    """
    limpio = _PATRON_CARACTER_INVALIDO.sub("_", nombre)
    if not limpio or limpio[0].isdigit():
        limpio = f"_{limpio}"
    return limpio


def tiene_nombre_oficial(funcion: Funcion) -> bool:
    """
    Indica si el nombre de la funcion viene de una firma del SDK (o es la entrada ``main``).

    Contexto:
        Un nombre asi tiene prioridad sobre cualquier otro origen, por ejemplo el archivo de nombres.

    Args:
        funcion (Funcion): Funcion exportada por Ghidra.

    Returns:
        bool: Verdadero si la tabla conservara el nombre de Ghidra en lugar de ``func_<direccion>``.

    Ejemplo:
        tiene_nombre_oficial(Funcion(0x80051938, "DrawSync", 0x68, True, "", 0, True, ""))  # True
    """
    return _usa_nombre_propio(funcion)


def _usa_nombre_propio(funcion: Funcion) -> bool:
    """Decide si la funcion conserva el nombre de Ghidra en lugar del generico."""
    if funcion.es_libreria:
        return funcion.nombre_oficial
    return funcion.nombre == NOMBRE_ENTRADA_C


def asignar_nombres(funciones: list[Funcion]) -> dict[int, str]:
    """
    Decide el nombre final de cada funcion.

    Contexto:
        Aplica la regla del contrato de simbolos: nombre oficial del SDK solo cuando una firma
        lo identifica, ``func_80XXXXXX`` para el resto. Un nombre oficial que aparece en varias
        direcciones (copias estaticas del mismo objeto) se desambigua con la direccion, porque
        dos simbolos no pueden compartir identificador.

    Args:
        funciones (list[Funcion]): Funciones del segmento.

    Returns:
        dict[int, str]: Nombre final por direccion.

    Raises:
        ValueError: Si dos funciones comparten direccion.

    Ejemplo:
        nombres = asignar_nombres(funciones)
    """
    direcciones = Counter(f.direccion for f in funciones)
    repetida = next((d for d, n in direcciones.items() if n > 1), None)
    if repetida is not None:
        raise ValueError(f"direccion duplicada 0x{repetida:08X}")
    propios = [normalizar_nombre(f.nombre) if _usa_nombre_propio(f) else None for f in funciones]
    frecuencia = Counter(n for n in propios if n is not None)
    nombres: dict[int, str] = {}
    for funcion, propio in zip(funciones, propios, strict=True):
        if propio is None:
            nombres[funcion.direccion] = nombre_por_defecto(funcion.direccion)
        elif frecuencia[propio] > 1:
            nombres[funcion.direccion] = f"{propio}_{funcion.direccion:08X}"
        else:
            nombres[funcion.direccion] = propio
    return nombres


def _tamanos_efectivos(funciones: list[Funcion]) -> dict[int, int]:
    """Recorta cada cuerpo al inicio de la funcion siguiente y al final del segmento."""
    ordenadas = sorted(funciones, key=lambda f: f.direccion)
    tamanos: dict[int, int] = {}
    for indice, funcion in enumerate(ordenadas):
        limite = DIRECCION_FIN
        if indice + 1 < len(ordenadas):
            limite = min(limite, ordenadas[indice + 1].direccion)
        tamanos[funcion.direccion] = min(funcion.tamano, limite - funcion.direccion)
    return tamanos


def construir_simbolos(funciones: list[Funcion]) -> list[Simbolo]:
    """
    Convierte las funciones exportadas en simbolos ordenados y sin solapes.

    Contexto:
        Paso central del comando ``simbolos``: Ghidra puede atribuir a una funcion bytes que ya
        pertenecen a la siguiente (saltos a etiquetas compartidas, tablas de saltos), asi que
        el tamano se recorta al inicio de la funcion vecina.

    Args:
        funciones (list[Funcion]): Funciones del segmento, en cualquier orden.

    Returns:
        list[Simbolo]: Un simbolo ``func`` por funcion, ordenado por direccion ascendente.

    Raises:
        ValueError: Si hay direcciones duplicadas o el resultado no supera ``validar_simbolos``.

    Ejemplo:
        simbolos = construir_simbolos(funciones)
    """
    nombres = asignar_nombres(funciones)
    tamanos = _tamanos_efectivos(funciones)
    simbolos = [
        Simbolo(nombres[direccion], direccion, "func", tamanos[direccion]) for direccion in sorted(nombres)
    ]
    validar_simbolos(simbolos)
    return simbolos


def validar_simbolos(simbolos: list[Simbolo]) -> None:
    """
    Comprueba las reglas del contrato de la tabla de simbolos.

    Contexto:
        Ultima barrera antes de escribir ``symbols.txt`` y tras leerlo: un archivo invalido
        rompe la particion del ejecutable varias capas mas abajo con mensajes confusos.

    Args:
        simbolos (list[Simbolo]): Simbolos a comprobar, en el orden en que se escribiran.

    Returns:
        None: Retorna sin error si todo es valido.

    Raises:
        ValueError: Con el nombre del simbolo infractor si el nombre no es un identificador C,
            esta repetido, la direccion cae fuera del segmento o de una funcion no esta alineada
            a 4, el tamano es nulo o sobrepasa el segmento, el orden no es ascendente por
            direccion o dos simbolos se solapan.

    Ejemplo:
        validar_simbolos([Simbolo("DrawSync", 0x80051938, "func", 0x68)])
    """
    nombres: set[str] = set()
    previo: Simbolo | None = None
    for simbolo in simbolos:
        _validar_simbolo(simbolo)
        if simbolo.nombre in nombres:
            raise ValueError(f"simbolo {simbolo.nombre}: nombre duplicado")
        nombres.add(simbolo.nombre)
        if previo is not None:
            _validar_vecinos(previo, simbolo)
        previo = simbolo


def _validar_simbolo(simbolo: Simbolo) -> None:
    """Reglas que dependen de un solo simbolo."""
    if not es_identificador_c(simbolo.nombre):
        raise ValueError(f"simbolo {simbolo.nombre!r}: no es un identificador C valido")
    if not DIRECCION_BASE <= simbolo.direccion < DIRECCION_FIN:
        raise ValueError(
            f"simbolo {simbolo.nombre}: direccion 0x{simbolo.direccion:08X} fuera del rango "
            f"0x{DIRECCION_BASE:08X}..0x{DIRECCION_FIN:08X}"
        )
    if simbolo.tipo == "func" and simbolo.direccion % ALINEACION_FUNCION != 0:
        raise ValueError(
            f"simbolo {simbolo.nombre}: direccion 0x{simbolo.direccion:08X} "
            f"no alineada a {ALINEACION_FUNCION}"
        )
    if simbolo.tamano <= 0:
        raise ValueError(f"simbolo {simbolo.nombre}: tamano={simbolo.tamano} debe ser mayor que 0")
    if simbolo.direccion + simbolo.tamano > DIRECCION_FIN:
        raise ValueError(f"simbolo {simbolo.nombre}: el tamano 0x{simbolo.tamano:X} excede el segmento")


def _validar_vecinos(previo: Simbolo, actual: Simbolo) -> None:
    """Reglas entre dos simbolos consecutivos: orden estricto y sin solape (un dato puede contener a otro)."""
    if actual.direccion == previo.direccion:
        raise ValueError(
            f"simbolo {actual.nombre}: direccion 0x{actual.direccion:08X} "
            f"repetida (ya la usa {previo.nombre})"
        )
    if actual.direccion < previo.direccion:
        raise ValueError(f"simbolo {actual.nombre}: fuera de orden ascendente tras {previo.nombre}")
    anidados = previo.tipo != "func" and actual.tipo != "func"
    if previo.direccion + previo.tamano > actual.direccion and not anidados:
        raise ValueError(f"simbolo {previo.nombre}: se solapa con {actual.nombre}")


def calcular_informe(funciones: list[Funcion]) -> Informe:
    """
    Resume cuantas funciones son de libreria, cuantas del juego y cuanto segmento cubren.

    Contexto:
        Alimenta el comando ``informe``; las cifras se copian a la documentacion del analisis.

    Args:
        funciones (list[Funcion]): Funciones del segmento.

    Returns:
        Informe: Conteos y porcentaje de cobertura con tamanos recortados (sin doble conteo).

    Raises:
        ValueError: Si hay direcciones duplicadas.

    Ejemplo:
        informe = calcular_informe(funciones)
    """
    asignar_nombres(funciones)
    cubiertos = sum(_tamanos_efectivos(funciones).values())
    libreria = [f for f in funciones if f.es_libreria]
    oficiales = sum(1 for f in libreria if f.nombre_oficial)
    return Informe(
        total=len(funciones),
        libreria=len(libreria),
        libreria_oficial=oficiales,
        libreria_local=len(libreria) - oficiales,
        juego=len(funciones) - len(libreria),
        ambiguas=sum(1 for f in libreria if f.comentario),
        bytes_cubiertos=cubiertos,
        porcentaje_cubierto=round(100.0 * cubiertos / TAMANO_SEGMENTO, 2),
    )

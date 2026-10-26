"""Propuesta de limites entre las unidades de compilacion originales del codigo del juego.

El ejecutable se enlazo con los archivos objeto uno tras otro, de modo que cada archivo ``.c``
original ocupa un tramo contiguo. Entre dos tramos no hay relleno medible en este binario, asi que
la evidencia sale de la estructura: un corte entre dos funciones consecutivas es limpio cuando
ningun enlace cercano lo cruza (llamada directa, puntero a funcion o dato usado por pocas
funciones), y es mas fiable cuanto mayor es la ventana de vecindad en la que se cumple.
"""

import csv
import io
import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from tools.ghidra.dominio import DIRECCION_BASE, Simbolo
from tools.ghidra.grafo import Grafo
from tools.ghidra.subsistemas import Rango, familia_de_libreria
from tools.ghidra.zonas import clasificar_zona

VENTANAS: Final[tuple[int, int, int]] = (12, 8, 5)
"""Ventanas de vecindad (en funciones), de la mas fiable a la menos fiable."""

MAX_USUARIOS_DATO: Final[int] = 6
"""Un dato usado por mas funciones es estado global y no revela que dos funciones compartan archivo."""

MIN_BYTES_ARCHIVO: Final[int] = 256
"""Distancia minima entre dos cortes propuestos.

Calibrada contra la poblacion real: con 0, 128, 256, 512 y 1024 bytes salen 47, 37, 36, 35 y 30 archivos.
"""

COLUMNAS_ARCHIVOS: Final[tuple[str, ...]] = (
    "direccion",
    "offset_archivo",
    "nombre",
    "confianza",
    "evidencia",
)


@dataclass(frozen=True)
class Limite:
    """Corte entre dos funciones consecutivas del codigo del juego."""

    direccion: int
    anterior: int
    ventana_limpia: int | None
    familias: tuple[str | None, str | None]
    relleno_nop: int


@dataclass(frozen=True)
class ArchivoOrigen:
    """Archivo ``.c`` propuesto: donde empieza, como se llamaria y con que evidencia."""

    direccion: int
    offset_archivo: int
    nombre: str
    confianza: str
    evidencia: str


def enlaces_entre_funciones(grafo: Grafo, posicion: Mapping[int, int]) -> set[tuple[int, int]]:
    """
    Reune los pares de funciones del juego que estan relacionados.

    Contexto:
        Base del calculo de cortes: dos funciones se consideran enlazadas si una llama o salta a la
        otra, si una toma el puntero de la otra o si ambas usan un mismo dato poco compartido.

    Args:
        grafo (Grafo): Grafo de llamadas y datos.
        posicion (Mapping[int, int]): Direccion de funcion del juego a su indice en orden.

    Returns:
        set[tuple[int, int]]: Pares de indices ``(menor, mayor)`` sin repeticiones.

    Ejemplo:
        enlaces = enlaces_entre_funciones(grafo, {0x80014AC4: 0, 0x80014BA0: 1})
    """
    pares: set[tuple[int, int]] = set()
    for arista in grafo.aristas:
        if arista.destino is None or arista.destino not in posicion:
            continue
        if arista.origen in posicion and arista.origen != arista.destino:
            pares.add(_par(posicion[arista.origen], posicion[arista.destino]))
    for origen, destino in grafo.punteros:
        if origen in posicion and destino in posicion and origen != destino:
            pares.add(_par(posicion[origen], posicion[destino]))
    for usuarias in grafo.datos.values():
        indices = sorted({posicion[u] for u in usuarias if u in posicion})
        if 2 <= len(indices) <= MAX_USUARIOS_DATO:
            pares.update((a, b) for i, a in enumerate(indices) for b in indices[i + 1 :])
    return pares


def _par(a: int, b: int) -> tuple[int, int]:
    """Ordena un par de indices."""
    return (a, b) if a < b else (b, a)


def cruces_por_corte(pares: set[tuple[int, int]], cantidad: int, ventana: int) -> list[int]:
    """
    Cuenta, para cada corte entre funciones consecutivas, los enlaces cercanos que lo cruzan.

    Contexto:
        Un enlace entre funciones muy alejadas (un despachador que llama a todo) no dice nada del
        archivo al que pertenecen, asi que solo cuentan los pares a menos de ``ventana`` posiciones.

    Args:
        pares (set[tuple[int, int]]): Resultado de ``enlaces_entre_funciones``.
        cantidad (int): Numero de funciones del juego.
        ventana (int): Distancia maxima en posiciones para que un enlace cuente.

    Returns:
        list[int]: ``cantidad - 1`` valores; el indice ``k`` es el corte entre ``k`` y ``k + 1``.

    Raises:
        ValueError: Si ``ventana`` es menor que 1.

    Ejemplo:
        cruces = cruces_por_corte({(0, 2)}, 4, 12)  # [1, 1, 0]
    """
    if ventana < 1:
        raise ValueError("limites: la ventana debe ser al menos 1")
    cruces = [0] * max(cantidad - 1, 0)
    for a, b in pares:
        if b - a <= ventana:
            for corte in range(a, b):
                cruces[corte] += 1
    return cruces


def _familia_dominante(grafo: Grafo, nombres: Mapping[int, str]) -> dict[int, str | None]:
    """Familia de libreria mas usada por cada funcion (empates resueltos por nombre)."""
    conteos: dict[int, dict[str, int]] = {}
    for arista in grafo.aristas:
        if arista.destino is None:
            continue
        familia = familia_de_libreria(nombres.get(arista.destino, ""))
        if familia is not None and clasificar_zona(arista.destino) == "libreria":
            por_funcion = conteos.setdefault(arista.origen, {})
            por_funcion[familia] = por_funcion.get(familia, 0) + 1
    return {origen: sorted(c.items(), key=lambda p: (-p[1], p[0]))[0][0] for origen, c in conteos.items()}


def _relleno(segmento: bytes, base: int, simbolo: Simbolo) -> int:
    """Palabras nulas que sobran tras la ranura de retardo del ultimo ``jr``."""
    fin = simbolo.direccion + simbolo.tamano
    sobrantes = 0
    while fin - 4 * (sobrantes + 2) >= simbolo.direccion:
        (palabra,) = struct.unpack_from("<I", segmento, fin - 4 * (sobrantes + 1) - base)
        if palabra != 0:
            break
        sobrantes += 1
    return max(sobrantes - 1, 0)


def calcular_limites(simbolos: Sequence[Simbolo], grafo: Grafo, segmento: bytes) -> list[Limite]:
    """
    Calcula el corte entre cada par de funciones consecutivas del juego.

    Contexto:
        Primer paso de ``proponer_archivos``. Mide para cada corte la ventana mas amplia en la que
        ningun enlace lo cruza, la familia de librerias a cada lado y el relleno de ``nop``.

    Args:
        simbolos (Sequence[Simbolo]): Tabla de simbolos.
        grafo (Grafo): Grafo de llamadas y datos.
        segmento (bytes): Segmento cargado del ejecutable.

    Returns:
        list[Limite]: Un limite por cada inicio de funcion del juego salvo el primero.

    Ejemplo:
        limites = calcular_limites(simbolos, grafo, segmento)
    """
    juego = sorted(
        (s for s in simbolos if clasificar_zona(s.direccion) in ("arranque", "juego")),
        key=lambda s: s.direccion,
    )
    posicion = {s.direccion: i for i, s in enumerate(juego)}
    pares = enlaces_entre_funciones(grafo, posicion)
    por_ventana = {w: cruces_por_corte(pares, len(juego), w) for w in VENTANAS}
    familias = _familia_dominante(grafo, {s.direccion: s.nombre for s in simbolos})
    limites: list[Limite] = []
    for corte in range(len(juego) - 1):
        limpia = next((w for w in VENTANAS if por_ventana[w][corte] == 0), None)
        limites.append(
            Limite(
                direccion=juego[corte + 1].direccion,
                anterior=juego[corte].direccion,
                ventana_limpia=limpia,
                familias=(familias.get(juego[corte].direccion), familias.get(juego[corte + 1].direccion)),
                relleno_nop=_relleno(segmento, DIRECCION_BASE, juego[corte]),
            )
        )
    return limites


def proponer_archivos(
    limites: Sequence[Limite], rangos: Sequence[Rango], minimo_bytes: int = MIN_BYTES_ARCHIVO
) -> list[ArchivoOrigen]:
    """
    Convierte los cortes en archivos de origen propuestos.

    Contexto:
        Salida de ``limites``: una lista que una tarjeta posterior puede trasladar a subsegmentos
        de ``splat.yaml`` (offset de archivo, direccion y nombre ``src/<nombre>.c``). Se proponen
        el inicio de cada subsistema y los cortes con evidencia de confianza alta (ventana limpia
        de 12 funciones) o media (ventana de 8, o de 5 con cambio de familia de librerias), siempre
        que dejen al menos ``minimo_bytes`` desde el corte anterior: una funcion suelta sin enlaces
        tiene cortes limpios a ambos lados sin que eso implique que sea un archivo por si sola.

    Args:
        limites (Sequence[Limite]): Resultado de ``calcular_limites``.
        rangos (Sequence[Rango]): Rangos de subsistemas, que dan el nombre base de cada archivo.
        minimo_bytes (int, opcional): Distancia minima entre dos cortes propuestos.

    Returns:
        list[ArchivoOrigen]: Archivos propuestos en orden de direccion.

    Raises:
        ValueError: Si ``minimo_bytes`` es negativo.

    Ejemplo:
        archivos = proponer_archivos(calcular_limites(simbolos, grafo, segmento), rangos)
    """
    if minimo_bytes < 0:
        raise ValueError("limites: el minimo de bytes no puede ser negativo")
    inicios_subsistema = {r.inicio for r in rangos}
    propuestos: list[tuple[int, str, str]] = []
    ultimo: int | None = None
    for limite in limites:
        confianza, evidencia = _evaluar(limite, limite.direccion in inicios_subsistema)
        if confianza not in ("alta", "media"):
            continue
        es_inicio = limite.direccion in inicios_subsistema
        if not es_inicio and ultimo is not None and limite.direccion - ultimo < minimo_bytes:
            continue
        propuestos.append((limite.direccion, confianza, evidencia))
        ultimo = limite.direccion
    return _nombrar(propuestos, rangos)


def _evaluar(limite: Limite, inicio_subsistema: bool) -> tuple[str, str]:
    """Asigna confianza y texto de evidencia a un corte."""
    cambia = limite.familias[0] != limite.familias[1] and None not in limite.familias
    evidencias: list[str] = []
    confianza = "baja"
    if inicio_subsistema:
        evidencias.append("inicio de subsistema")
        confianza = "alta"
    if limite.ventana_limpia is not None:
        evidencias.append(f"ningun enlace cruza el corte en una ventana de {limite.ventana_limpia} funciones")
        if limite.ventana_limpia == VENTANAS[0]:
            confianza = "alta"
        elif limite.ventana_limpia == VENTANAS[1] or cambia:
            confianza = "alta" if confianza == "alta" else "media"
    if cambia:
        evidencias.append(f"cambia la familia de librerias ({limite.familias[0]} a {limite.familias[1]})")
    if limite.relleno_nop:
        evidencias.append(f"{limite.relleno_nop} nop de relleno tras la funcion anterior")
    return confianza, "; ".join(evidencias)


def _nombrar(propuestos: Sequence[tuple[int, str, str]], rangos: Sequence[Rango]) -> list[ArchivoOrigen]:
    """Asigna ``<subsistema>`` o ``<subsistema>_<n>`` a cada archivo propuesto."""
    por_subsistema: dict[str, int] = {}
    archivos: list[ArchivoOrigen] = []
    for direccion, confianza, evidencia in propuestos:
        base = next((r.nombre for r in rangos if r.inicio <= direccion < r.fin), "sin_subsistema")
        numero = por_subsistema.get(base, 0) + 1
        por_subsistema[base] = numero
        nombre = base if numero == 1 else f"{base}_{numero}"
        archivos.append(
            ArchivoOrigen(direccion, direccion - DIRECCION_BASE + 0x800, nombre, confianza, evidencia)
        )
    return archivos


def formatear_archivos_csv(archivos: Sequence[ArchivoOrigen]) -> str:
    """
    Serializa los archivos de origen propuestos como CSV.

    Contexto:
        Formato de ``archivos_origen.csv`` en la carpeta de analisis.

    Args:
        archivos (Sequence[ArchivoOrigen]): Resultado de ``proponer_archivos``.

    Returns:
        str: CSV con LF y columnas de ``COLUMNAS_ARCHIVOS``.

    Ejemplo:
        texto = formatear_archivos_csv(archivos)
    """
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(COLUMNAS_ARCHIVOS)
    for a in archivos:
        escritor.writerow(
            [f"0x{a.direccion:08X}", f"0x{a.offset_archivo:X}", f"src/{a.nombre}.c", a.confianza, a.evidencia]
        )
    return salida.getvalue()

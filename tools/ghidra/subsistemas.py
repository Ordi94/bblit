"""Caracterizacion de subsistemas del juego a partir del grafo y de las librerias que usan.

Un subsistema es un rango (o varios) de direcciones contiguas del codigo del juego. El modulo no
decide los limites a ciegas: propone rangos con los cortes limpios del grafo y las familias de
librerias (``proponer_rangos``) y, dado un conjunto de rangos, calcula la evidencia de cada uno:
funciones, librerias de Sony, cadenas, regiones de datos y dependencias con los demas.
"""

import csv
import io
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Final

from tools.ghidra.dominio import Simbolo
from tools.ghidra.exportaciones import Cadena
from tools.ghidra.grafo import Grafo
from tools.ghidra.zonas import clasificar_zona, region_de_dato

COLUMNAS_RANGOS: Final[tuple[str, ...]] = ("nombre", "inicio", "fin")
COLUMNAS_SUBSISTEMAS: Final[tuple[str, ...]] = (
    "nombre",
    "rangos",
    "funciones",
    "bytes",
    "librerias",
    "cadenas",
    "regiones_de_datos",
    "dependencias",
    "usado_por",
)
CONTROL_PERMITIDO: Final[str] = chr(10) + chr(9)
"""Salto de linea y tabulacion: los mensajes de depuracion reales los llevan y no restan legibilidad."""
MAX_RANGOS: Final[int] = 200
MAX_LONGITUD_NOMBRE: Final[int] = 64
MAX_CADENAS_POR_SUBSISTEMA: Final[int] = 8
MIN_LETRAS_CADENA: Final[int] = 4
_PATRON_NOMBRE: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]*$")

_FAMILIAS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("cd", re.compile(r"^(Cd|Ds)")),
    ("audio_spu", re.compile(r"^(Spu|Ss|_spu)")),
    ("mando", re.compile(r"^(Pad|PAD|_pad|ChangeClearPAD)")),
    (
        "tarjeta_de_memoria",
        re.compile(
            r"^(MemCard|Card|_card|_new_card|_bu_|InitCARD|StartCARD|StopCARD|open$|close$|read$|write$|lseek$|format$|erase$|firstfile|nextfile)"
        ),
    ),
    (
        "graficos",
        re.compile(
            r"^(Gs|Draw|Put|SetDef|SetDisp|MoveImage|ClearImage|LoadImage|StoreImage|ResetGraph|GPU|SetGraph)"
        ),
    ),
    (
        "geometria_gte",
        re.compile(
            r"^(Rot|Apply|Scale|Mul|SquareRoot|ratan|rsin|rcos|Trans|Comp|Normal|OuterProduct|VectorNormal)"
        ),
    ),
    ("sistema", re.compile(r"^(VSync|StartRCnt|SetRCnt|srand|rand|memset|memcpy|printf|ResetCallback)")),
)
"""Familias de librerias por prefijo del nombre; el orden resuelve los empates de forma estable."""


@dataclass(frozen=True)
class Rango:
    """Rango ``[inicio, fin)`` de direcciones asignado a un subsistema."""

    nombre: str
    inicio: int
    fin: int


@dataclass(frozen=True)
class Subsistema:
    """Evidencia reunida para un subsistema."""

    nombre: str
    rangos: tuple[tuple[int, int], ...]
    funciones: tuple[tuple[int, str, int], ...]
    librerias: tuple[tuple[str, int], ...]
    cadenas: tuple[tuple[int, str], ...]
    regiones: tuple[tuple[str, int], ...]
    dependencias: tuple[tuple[str, int, int], ...]
    usado_por: tuple[tuple[str, int], ...]
    llamadas_internas: int

    @property
    def bytes_totales(self) -> int:
        """Suma de los tamanos de sus funciones."""
        return sum(tamano for _, _, tamano in self.funciones)


def familia_de_libreria(nombre: str) -> str | None:
    """
    Clasifica una funcion de libreria en una familia por su nombre.

    Contexto:
        Permite nombrar un subsistema por las librerias que usa (CD, SPU, mando, GTE...).

    Args:
        nombre (str): Nombre de la funcion de libreria.

    Returns:
        str | None: Familia (``cd``, ``audio_spu``, ``mando``, ``tarjeta_de_memoria``,
        ``graficos``, ``geometria_gte`` o ``sistema``) o ``None`` si ninguna encaja.

    Ejemplo:
        familia = familia_de_libreria("CdControlB")  # "cd"
    """
    for familia, patron in _FAMILIAS:
        if patron.match(nombre):
            return familia
    return None


def parsear_rangos(texto: str) -> list[Rango]:
    """
    Interpreta un CSV de rangos de subsistemas.

    Contexto:
        Entrada de ``subsistemas``: la propuesta curada de rangos vive fuera del codigo, en un
        CSV con columnas ``nombre,inicio,fin``; un mismo nombre puede aparecer en varias filas.

    Args:
        texto (str): Contenido del CSV con cabecera.

    Returns:
        list[Rango]: Rangos ordenados por direccion.

    Raises:
        ValueError: Si la cabecera no coincide, hay demasiadas filas, un nombre no es snake_case
            en minusculas, una direccion no es hexadecimal alineada a 4, un rango esta vacio o
            dos rangos se solapan.

    Ejemplo:
        rangos = parsear_rangos(Path("subsistemas_rangos.csv").read_text(encoding="utf-8"))
    """
    lector = csv.reader(io.StringIO(texto, newline=""))
    cabecera = next(lector, None)
    if cabecera is None or tuple(cabecera) != COLUMNAS_RANGOS:
        raise ValueError("rangos: la cabecera debe ser nombre,inicio,fin")
    rangos: list[Rango] = []
    for numero, valores in enumerate(lector, start=2):
        if len(rangos) >= MAX_RANGOS:
            raise ValueError(f"rangos: mas de {MAX_RANGOS} filas")
        if len(valores) != len(COLUMNAS_RANGOS):
            raise ValueError(f"rangos fila {numero}: se esperaban 3 campos")
        nombre = valores[0]
        if len(nombre) > MAX_LONGITUD_NOMBRE or not _PATRON_NOMBRE.match(nombre):
            raise ValueError(f"rangos fila {numero}: nombre invalido")
        inicio, fin = (_direccion(v, numero) for v in valores[1:])
        if inicio >= fin:
            raise ValueError(f"rangos fila {numero}: el rango esta vacio")
        rangos.append(Rango(nombre, inicio, fin))
    rangos.sort(key=lambda r: r.inicio)
    for previo, actual in pairwise(rangos):
        if actual.inicio < previo.fin:
            raise ValueError(f"rangos: {actual.nombre} se solapa con {previo.nombre}")
    return rangos


def _direccion(valor: str, fila: int) -> int:
    """Convierte ``0xNNNNNNNN`` alineada a 4 o falla nombrando la fila."""
    if not valor.startswith("0x"):
        raise ValueError(f"rangos fila {fila}: la direccion debe empezar por 0x")
    try:
        direccion = int(valor, 16)
    except ValueError:
        raise ValueError(f"rangos fila {fila}: la direccion no es hexadecimal") from None
    if direccion % 4 or not 0 <= direccion <= 0xFFFFFFFF:
        raise ValueError(f"rangos fila {fila}: la direccion debe estar alineada a 4 y ser de 32 bits")
    return direccion


def _cadena_legible(texto: str) -> bool:
    """Una cadena sirve de evidencia si tiene letras suficientes y casi todo imprimible."""
    letras = sum(c.isalpha() for c in texto)
    permitidos = all(c.isprintable() or c in CONTROL_PERMITIDO for c in texto)
    return letras >= MIN_LETRAS_CADENA and letras * 2 >= len(texto) and permitidos


def _contar_llamadas(
    grafo: Grafo, dueno: Mapping[int, str], nombres: Mapping[int, str], orden: Sequence[str]
) -> tuple[dict[str, Counter[str]], Counter[str], dict[str, Counter[str]], dict[str, Counter[str]]]:
    """Cuenta por subsistema las librerias invocadas, las llamadas internas y las que cruzan."""
    librerias: dict[str, Counter[str]] = {n: Counter() for n in orden}
    internas: Counter[str] = Counter()
    cruces: dict[str, Counter[str]] = {n: Counter() for n in orden}
    entrantes: dict[str, Counter[str]] = {n: Counter() for n in orden}
    for arista in grafo.aristas:
        origen = dueno.get(arista.origen)
        if origen is None or arista.destino is None:
            continue
        if clasificar_zona(arista.destino) == "libreria":
            librerias[origen][nombres.get(arista.destino, f"func_{arista.destino:08X}")] += 1
        elif arista.destino in dueno and dueno[arista.destino] != origen:
            cruces[origen][dueno[arista.destino]] += 1
            entrantes[dueno[arista.destino]][origen] += 1
        elif arista.destino in dueno:
            internas[origen] += 1
    return librerias, internas, cruces, entrantes


def _contar_datos(
    grafo: Grafo, dueno: Mapping[int, str], orden: Sequence[str]
) -> tuple[dict[str, set[int]], dict[str, Counter[str]], dict[str, Counter[str]]]:
    """Reune por subsistema los datos que usa, los que comparte con otro y las regiones que toca."""
    usuarios: dict[str, set[int]] = defaultdict(set)
    comparte: dict[str, Counter[str]] = {n: Counter() for n in orden}
    regiones: dict[str, Counter[str]] = {n: Counter() for n in orden}
    for dato, usuarias in grafo.datos.items():
        duenos = {dueno[u] for u in usuarias if u in dueno}
        for nombre in duenos:
            regiones[nombre][region_de_dato(dato)] += 1
            usuarios[nombre].add(dato)
            for otro in duenos - {nombre}:
                comparte[nombre][otro] += 1
    return usuarios, comparte, regiones


def caracterizar(
    rangos: Sequence[Rango], simbolos: Sequence[Simbolo], grafo: Grafo, cadenas: Sequence[Cadena]
) -> list[Subsistema]:
    """
    Reune la evidencia de cada subsistema.

    Contexto:
        Es la base de ``docs/SUBSISTEMAS.md``: para cada nombre de ``rangos`` lista sus funciones,
        las librerias que invoca, las cadenas que referencia, las regiones de datos que toca y
        con que otros subsistemas se relaciona (llamadas y datos compartidos).

    Args:
        rangos (Sequence[Rango]): Rangos ya validados (``parsear_rangos``).
        simbolos (Sequence[Simbolo]): Tabla de simbolos.
        grafo (Grafo): Grafo de llamadas y datos.
        cadenas (Sequence[Cadena]): Cadenas exportadas por Ghidra.

    Returns:
        list[Subsistema]: Subsistemas en el orden de su primer rango.

    Ejemplo:
        subsistemas = caracterizar(rangos, simbolos, grafo, cadenas)
    """
    nombres = {s.direccion: s.nombre for s in simbolos}
    tamanos = {s.direccion: s.tamano for s in simbolos}
    dueno: dict[int, str] = {}
    for s in simbolos:
        for rango in rangos:
            if rango.inicio <= s.direccion < rango.fin:
                dueno[s.direccion] = rango.nombre
    orden = list(dict.fromkeys(r.nombre for r in rangos))
    funciones: dict[str, list[tuple[int, str, int]]] = {n: [] for n in orden}
    for direccion in sorted(dueno):
        funciones[dueno[direccion]].append((direccion, nombres[direccion], tamanos[direccion]))
    librerias, internas, cruces, entrantes = _contar_llamadas(grafo, dueno, nombres, orden)
    usuarios, comparte, regiones = _contar_datos(grafo, dueno, orden)
    legibles = [c for c in cadenas if _cadena_legible(c.texto)]
    resultado: list[Subsistema] = []
    for nombre in orden:
        propias = tuple(
            (c.direccion, c.texto.strip())
            for c in legibles
            if any(c.direccion <= d < c.direccion + max(c.longitud, 1) for d in usuarios[nombre])
        )[:MAX_CADENAS_POR_SUBSISTEMA]
        otros = sorted(set(cruces[nombre]) | set(comparte[nombre]))
        resultado.append(
            Subsistema(
                nombre=nombre,
                rangos=tuple((r.inicio, r.fin) for r in rangos if r.nombre == nombre),
                funciones=tuple(funciones[nombre]),
                librerias=tuple(sorted(librerias[nombre].items(), key=lambda p: (-p[1], p[0]))),
                cadenas=propias,
                regiones=tuple(sorted(regiones[nombre].items())),
                dependencias=tuple((o, cruces[nombre][o], comparte[nombre][o]) for o in otros),
                usado_por=tuple(sorted(entrantes[nombre].items())),
                llamadas_internas=internas[nombre],
            )
        )
    return resultado


def proponer_rangos(simbolos: Sequence[Simbolo], grafo: Grafo, cortes: Sequence[int]) -> list[Rango]:
    """
    Propone rangos iniciales partiendo el codigo del juego en los cortes dados.

    Contexto:
        Primer borrador automatico: cada tramo entre dos cortes limpios del grafo recibe el nombre
        de la familia de librerias dominante (o ``logica`` si no usa ninguna) y un indice. Un
        humano lo revisa y lo fusiona antes de publicarlo.

    Args:
        simbolos (Sequence[Simbolo]): Tabla de simbolos (solo se usan las del juego).
        grafo (Grafo): Grafo de llamadas y datos.
        cortes (Sequence[int]): Direcciones de funcion donde empieza un tramo nuevo.

    Returns:
        list[Rango]: Rangos contiguos que cubren el codigo del juego, sin solapes.

    Ejemplo:
        rangos = proponer_rangos(simbolos, grafo, [0x80014AC4, 0x80026118])
    """
    juego = sorted(s.direccion for s in simbolos if clasificar_zona(s.direccion) in ("arranque", "juego"))
    if not juego:
        return []
    nombres = {s.direccion: s.nombre for s in simbolos}
    inicios = sorted({juego[0], *(c for c in cortes if c in set(juego))})
    fin_total = max(s.direccion + s.tamano for s in simbolos if s.direccion in set(juego))
    rangos: list[Rango] = []
    for posicion, inicio in enumerate(inicios):
        fin = inicios[posicion + 1] if posicion + 1 < len(inicios) else fin_total
        familias: Counter[str] = Counter()
        for arista in grafo.aristas:
            if inicio <= arista.origen < fin and arista.destino is not None:
                familia = familia_de_libreria(nombres.get(arista.destino, ""))
                if familia is not None:
                    familias[familia] += 1
        base = sorted(familias.items(), key=lambda p: (-p[1], p[0]))[0][0] if familias else "logica"
        rangos.append(Rango(f"{base}_{posicion + 1:02d}", inicio, fin))
    return rangos


def formatear_subsistemas_csv(subsistemas: Sequence[Subsistema]) -> str:
    """
    Serializa la caracterizacion como CSV.

    Contexto:
        Formato de ``subsistemas.csv`` en la carpeta de analisis; la tabla de
        ``docs/SUBSISTEMAS.md`` se redacta a partir de el.

    Args:
        subsistemas (Sequence[Subsistema]): Resultado de ``caracterizar``.

    Returns:
        str: CSV con LF y columnas de ``COLUMNAS_SUBSISTEMAS``; las listas van separadas por ``;``.

    Ejemplo:
        texto = formatear_subsistemas_csv(caracterizar(rangos, simbolos, grafo, cadenas))
    """
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(COLUMNAS_SUBSISTEMAS)
    for s in subsistemas:
        escritor.writerow(
            [
                s.nombre,
                ";".join(f"0x{i:08X}-0x{f:08X}" for i, f in s.rangos),
                ";".join(f"0x{d:08X}:{n}" for d, n, _ in s.funciones),
                s.bytes_totales,
                ";".join(f"{n}:{v}" for n, v in s.librerias),
                ";".join(f"0x{d:08X}:{t}" for d, t in s.cadenas),
                ";".join(f"{n}:{v}" for n, v in s.regiones),
                ";".join(f"{o}:{ll}:{da}" for o, ll, da in s.dependencias),
                ";".join(f"{o}:{n}" for o, n in s.usado_por),
            ]
        )
    return salida.getvalue()


def resumir_por_nombre(subsistemas: Sequence[Subsistema]) -> Mapping[str, int]:
    """
    Cuenta las funciones de cada subsistema.

    Contexto:
        Resumen para imprimir al terminar el comando ``subsistemas``.

    Args:
        subsistemas (Sequence[Subsistema]): Resultado de ``caracterizar``.

    Returns:
        Mapping[str, int]: Nombre del subsistema a numero de funciones, en el mismo orden.

    Ejemplo:
        conteos = resumir_por_nombre(subsistemas)
    """
    return {s.nombre: len(s.funciones) for s in subsistemas}

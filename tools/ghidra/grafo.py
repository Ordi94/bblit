"""Grafo de llamadas y de datos compartidos entre las funciones del ejecutable.

A partir del desensamblado propio y de las corridas de punteros a codigo de la zona de datos,
construye cuatro tipos de arista entre funciones (``jal``, ``j``, ``tabla`` e ``indirecta``), los
punteros a funcion que se guardan como dato (callbacks) y, por cada dato, el conjunto de funciones
que lo usan. Es logica pura; la lectura de archivos y la escritura de CSV viven en ``cli``.
"""

import csv
import io
from bisect import bisect_right
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from tools.ghidra.dominio import Simbolo
from tools.ghidra.ensamblador import AnalisisFuncion, FuncionAsm, analizar_funcion
from tools.ghidra.tablas import Corrida, corrida_que_contiene, tramo_de_tabla
from tools.ghidra.zonas import ClaseZona, clasificar_zona

TIPOS_ARISTA: Final[tuple[str, ...]] = ("jal", "j", "tabla", "indirecta")
"""Tipos de arista del grafo, en el orden en que se escriben."""

COLUMNAS_GRAFO: Final[tuple[str, ...]] = (
    "origen",
    "nombre_origen",
    "destino",
    "nombre_destino",
    "tipo",
    "es_libreria_destino",
    "clase_destino",
    "veces",
)
COLUMNAS_DATOS: Final[tuple[str, ...]] = ("dato", "numero_de_funciones", "funciones")
COLUMNAS_PUNTEROS: Final[tuple[str, ...]] = ("origen", "nombre_origen", "destino", "nombre_destino")


@dataclass(frozen=True)
class Arista:
    """Relacion entre dos funciones; ``destino`` es ``None`` en las llamadas indirectas."""

    origen: int
    destino: int | None
    tipo: str
    veces: int


@dataclass(frozen=True)
class TablaSalto:
    """Tabla de un ``switch`` usada por una funcion: simbolo, base y destinos dentro de ella."""

    simbolo: str
    direccion: int
    destinos: tuple[int, ...]


@dataclass(frozen=True)
class Grafo:
    """Resultado completo del analisis de llamadas y datos."""

    aristas: tuple[Arista, ...]
    punteros: tuple[tuple[int, int], ...]
    datos: Mapping[int, tuple[int, ...]]
    tablas_salto: Mapping[int, tuple[TablaSalto, ...]]
    saltos_switch: Mapping[int, int]
    destinos_ajenos: int
    sin_resolver: int


@dataclass(frozen=True)
class ResumenGrafo:
    """Conteos verificables del grafo (aristas unicas, salvo ``llamadas`` que cuenta instrucciones)."""

    total: int
    llamadas: int
    por_tipo: Mapping[str, int]
    juego_juego: int
    juego_libreria: int
    juego_externo: int
    por_tabla: int
    indirectas: int
    switches: int
    punteros: int
    datos: int


@dataclass
class _Acumulado:
    """Estado mutable mientras se recorren las funciones."""

    llamadas: dict[tuple[int, int, str], int] = field(default_factory=lambda: defaultdict(int))
    indirectas: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    punteros: set[tuple[int, int]] = field(default_factory=set)
    datos: dict[int, set[int]] = field(default_factory=lambda: defaultdict(set))
    tablas_salto: dict[int, list[TablaSalto]] = field(default_factory=lambda: defaultdict(list))
    switches: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    ajenos: int = 0


class _Rangos:
    """Busqueda de la funcion que contiene una direccion."""

    def __init__(self, simbolos: Sequence[Simbolo]) -> None:
        """Ordena los simbolos de funcion por direccion."""
        ordenados = sorted(simbolos, key=lambda s: s.direccion)
        self.inicios = [s.direccion for s in ordenados]
        self.fines = [s.direccion + s.tamano for s in ordenados]

    def contenedora(self, direccion: int) -> int | None:
        """Devuelve el inicio de la funcion que contiene la direccion, o ``None``."""
        posicion = bisect_right(self.inicios, direccion) - 1
        if posicion >= 0 and direccion < self.fines[posicion]:
            return self.inicios[posicion]
        return None

    def fin(self, inicio: int) -> int:
        """Devuelve el fin exclusivo de la funcion que empieza en ``inicio``."""
        return self.fines[self.inicios.index(inicio)]


def construir_grafo(
    funciones: Sequence[FuncionAsm], simbolos: Sequence[Simbolo], corridas: list[Corrida]
) -> Grafo:
    """
    Construye el grafo de llamadas y de datos compartidos.

    Contexto:
        Insumo del reparto de la descompilacion: dice quien llama a quien, que rutinas solo se
        alcanzan por tabla y que datos comparten las funciones. Tambien lo usa ``borradores``
        para saber que tablas de salto debe entregar a ``m2c``.

    Args:
        funciones (Sequence[FuncionAsm]): Funciones del desensamblado propio.
        simbolos (Sequence[Simbolo]): Tabla de simbolos (``config/symbols.txt``).
        corridas (list[Corrida]): Corridas de punteros a codigo, ordenadas por direccion.

    Returns:
        Grafo: Aristas ``jal``/``j``/``tabla``/``indirecta`` con su cuenta de instrucciones,
        punteros a funcion, datos con las funciones que los usan y tablas de salto por funcion.

    Raises:
        ValueError: Si el desensamblado trae una funcion que no figura en la tabla de simbolos o
            con otra direccion.

    Ejemplo:
        grafo = construir_grafo(dividir_por_funcion(texto), simbolos, corridas)
    """
    nombres = {s.nombre: s.direccion for s in simbolos}
    rangos = _Rangos(simbolos)
    analisis: dict[int, AnalisisFuncion] = {}
    sin_resolver = 0
    for funcion in funciones:
        if nombres.get(funcion.nombre) != funcion.direccion:
            raise ValueError(f"grafo: la funcion {funcion.nombre} no coincide con la tabla de simbolos")
        analisis[funcion.direccion] = analizar_funcion(funcion, nombres)
        sin_resolver += analisis[funcion.direccion].sin_resolver
    fronteras = sorted(
        {r.direccion for a in analisis.values() for r in a.referencias if r.desplazamiento == 0}
    )
    acumulado = _Acumulado()
    contexto = _Contexto(rangos, corridas, fronteras)
    for origen in sorted(analisis):
        _registrar_saltos(origen, analisis[origen], acumulado)
        _registrar_referencias(origen, analisis[origen], contexto, acumulado)
    _cerrar_switches(analisis, acumulado)
    return _empaquetar(acumulado, sin_resolver)


def _registrar_saltos(origen: int, analisis: AnalisisFuncion, acumulado: _Acumulado) -> None:
    """Cuenta los ``jal``/``j`` con destino resuelto y los ``jalr``."""
    for salto in analisis.saltos:
        if salto.tipo == "jalr":
            acumulado.indirectas[origen] += 1
        elif salto.tipo in ("jal", "j") and salto.destino is not None:
            acumulado.llamadas[(origen, salto.destino, salto.tipo)] += 1


@dataclass(frozen=True)
class _Contexto:
    """Datos de solo lectura que comparten los pasos de ``construir_grafo``."""

    rangos: _Rangos
    corridas: list[Corrida]
    fronteras: list[int]


def _registrar_referencias(
    origen: int, analisis: AnalisisFuncion, contexto: _Contexto, acumulado: _Acumulado
) -> None:
    """Clasifica las referencias de una funcion en punteros a funcion, datos y tablas."""
    rangos = contexto.rangos
    for direccion in sorted({r.direccion for r in analisis.referencias}):
        contenedora = rangos.contenedora(direccion)
        if contenedora is not None:
            if direccion == contenedora:
                acumulado.punteros.add((origen, contenedora))
            continue
        acumulado.datos[direccion].add(origen)
        corrida = corrida_que_contiene(contexto.corridas, direccion)
        if corrida is None or direccion % 4:
            continue
        propia = (origen, rangos.fin(origen))
        interiores: list[int] = []
        for destino in tramo_de_tabla(corrida, direccion, contexto.fronteras):
            duena = rangos.contenedora(destino)
            if duena == origen and propia[0] <= destino < propia[1]:
                interiores.append(destino)
            elif duena == destino:
                acumulado.llamadas[(origen, destino, "tabla")] += 1
            else:
                acumulado.ajenos += 1
        if interiores:
            simbolo = next(r.simbolo for r in analisis.referencias if r.direccion == direccion)
            if not simbolo.isidentifier():
                simbolo = f"D_{direccion:08X}"
            acumulado.tablas_salto[origen].append(TablaSalto(simbolo, direccion, tuple(interiores)))


def _cerrar_switches(analisis: Mapping[int, AnalisisFuncion], acumulado: _Acumulado) -> None:
    """Reparte los ``jr`` a registro entre ``switch`` (la funcion tiene tabla propia) e indirectas."""
    for origen, resultado in analisis.items():
        saltos_jr = sum(1 for s in resultado.saltos if s.tipo == "jr")
        if saltos_jr and acumulado.tablas_salto.get(origen):
            acumulado.switches[origen] += saltos_jr
        elif saltos_jr:
            acumulado.indirectas[origen] += saltos_jr


def _empaquetar(acumulado: _Acumulado, sin_resolver: int) -> Grafo:
    """Convierte el acumulado en un ``Grafo`` ordenado y sin estado mutable."""
    orden_tipo = {tipo: indice for indice, tipo in enumerate(TIPOS_ARISTA)}
    aristas = [Arista(o, d, t, veces) for (o, d, t), veces in acumulado.llamadas.items()]
    aristas += [Arista(origen, None, "indirecta", veces) for origen, veces in acumulado.indirectas.items()]
    aristas.sort(key=lambda a: (a.origen, orden_tipo[a.tipo], -1 if a.destino is None else a.destino))
    return Grafo(
        aristas=tuple(aristas),
        punteros=tuple(sorted(acumulado.punteros)),
        datos={dato: tuple(sorted(usuarias)) for dato, usuarias in sorted(acumulado.datos.items())},
        tablas_salto={
            o: tuple(sorted(t, key=lambda x: x.direccion)) for o, t in acumulado.tablas_salto.items()
        },
        saltos_switch=dict(acumulado.switches),
        destinos_ajenos=acumulado.ajenos,
        sin_resolver=sin_resolver,
    )


def resumir_grafo(grafo: Grafo) -> ResumenGrafo:
    """
    Calcula los conteos que se reportan al generar el grafo.

    Contexto:
        Es la medida de efecto del comando ``grafo``: cuantas aristas hay y de que clase.

    Args:
        grafo (Grafo): Resultado de ``construir_grafo``.

    Returns:
        ResumenGrafo: Aristas con destino conocido (unicas), cuenta de instrucciones, reparto por
        tipo, aristas del codigo del juego (incluidas las rutinas de arranque) hacia el juego, las
        librerias y fuera del segmento, y totales de ``switch``, punteros y datos.

    Ejemplo:
        resumen = resumir_grafo(grafo)
    """
    con_destino = [a for a in grafo.aristas if a.destino is not None]
    por_tipo = {tipo: sum(1 for a in grafo.aristas if a.tipo == tipo) for tipo in TIPOS_ARISTA}
    desde_juego = [a for a in con_destino if _es_codigo_del_juego(clasificar_zona(a.origen))]

    def hacia(clase: ClaseZona) -> int:
        return sum(
            1
            for a in desde_juego
            if a.destino is not None and _misma_clase(clasificar_zona(a.destino), clase)
        )

    return ResumenGrafo(
        total=len(con_destino),
        llamadas=sum(a.veces for a in grafo.aristas),
        por_tipo=por_tipo,
        juego_juego=hacia("juego"),
        juego_libreria=hacia("libreria"),
        juego_externo=hacia("externo"),
        por_tabla=por_tipo["tabla"],
        indirectas=sum(a.veces for a in grafo.aristas if a.tipo == "indirecta"),
        switches=sum(grafo.saltos_switch.values()),
        punteros=len(grafo.punteros),
        datos=len(grafo.datos),
    )


def _es_codigo_del_juego(clase: ClaseZona) -> bool:
    """El arranque forma parte del ejecutable del juego a efectos de reparto."""
    return clase in ("arranque", "juego")


def _misma_clase(clase: ClaseZona, esperada: ClaseZona) -> bool:
    """Compara clases tratando el arranque como juego."""
    return _es_codigo_del_juego(clase) if esperada == "juego" else clase == esperada


def formatear_grafo_csv(grafo: Grafo, nombres: Mapping[int, str]) -> str:
    """
    Serializa las aristas como CSV.

    Contexto:
        Formato de ``grafo_llamadas.csv``, consumido por las tarjetas de descompilacion.

    Args:
        grafo (Grafo): Grafo ya construido.
        nombres (Mapping[int, str]): Direccion a nombre de simbolo.

    Returns:
        str: CSV con LF, columnas de ``COLUMNAS_GRAFO``; en las indirectas ``destino`` va vacio.

    Ejemplo:
        texto = formatear_grafo_csv(grafo, nombres)
    """
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(COLUMNAS_GRAFO)
    for arista in grafo.aristas:
        if arista.destino is None:
            escritor.writerow(
                [
                    f"0x{arista.origen:08X}",
                    nombres.get(arista.origen, ""),
                    "",
                    "",
                    arista.tipo,
                    "",
                    "",
                    arista.veces,
                ]
            )
            continue
        clase = clasificar_zona(arista.destino)
        escritor.writerow(
            [
                f"0x{arista.origen:08X}",
                nombres.get(arista.origen, ""),
                f"0x{arista.destino:08X}",
                nombres.get(arista.destino, ""),
                arista.tipo,
                int(clase == "libreria"),
                clase,
                arista.veces,
            ]
        )
    return salida.getvalue()


def formatear_datos_csv(grafo: Grafo, nombres: Mapping[int, str]) -> str:
    """
    Serializa los datos compartidos como CSV.

    Contexto:
        Formato de ``datos_compartidos.csv``: una fila por dato con las funciones que lo usan.

    Args:
        grafo (Grafo): Grafo ya construido.
        nombres (Mapping[int, str]): Direccion a nombre de simbolo.

    Returns:
        str: CSV con LF; las funciones van como ``direccion:nombre`` separadas por ``;``.

    Ejemplo:
        texto = formatear_datos_csv(grafo, nombres)
    """
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(COLUMNAS_DATOS)
    for dato, usuarias in grafo.datos.items():
        listado = ";".join(f"0x{u:08X}:{nombres.get(u, '')}" for u in usuarias)
        escritor.writerow([f"0x{dato:08X}", len(usuarias), listado])
    return salida.getvalue()


def formatear_punteros_csv(grafo: Grafo, nombres: Mapping[int, str]) -> str:
    """
    Serializa los punteros a funcion (callbacks y direcciones tomadas) como CSV.

    Contexto:
        Complementa al grafo: una funcion cuyo puntero se guarda como dato no aparece como
        ``jal`` aunque se invoque mas tarde.

    Args:
        grafo (Grafo): Grafo ya construido.
        nombres (Mapping[int, str]): Direccion a nombre de simbolo.

    Returns:
        str: CSV con LF y columnas de ``COLUMNAS_PUNTEROS``.

    Ejemplo:
        texto = formatear_punteros_csv(grafo, nombres)
    """
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(COLUMNAS_PUNTEROS)
    for origen, destino in grafo.punteros:
        escritor.writerow(
            [f"0x{origen:08X}", nombres.get(origen, ""), f"0x{destino:08X}", nombres.get(destino, "")]
        )
    return salida.getvalue()


@dataclass(frozen=True)
class Comparacion:
    """Resultado de contrastar los datos compartidos con una exportacion independiente."""

    coinciden: int
    contenidos: int
    difieren: tuple[int, ...]


def comparar_llamadores(grafo: Grafo, esperados: Mapping[int, int]) -> tuple[int, tuple[int, ...]]:
    """
    Compara el numero de llamadores propio con el que exporto Ghidra.

    Contexto:
        Valor con esperado conocido: ``numero_de_llamadores`` de ``funciones.csv`` es el numero de
        sitios de llamada directa (``jal`` y ``j``) hacia la funcion; no cuenta punteros tomados
        ni entradas de tablas de datos. El grafo debe reproducirlo.

    Args:
        grafo (Grafo): Grafo ya construido.
        esperados (Mapping[int, int]): Direccion de funcion a numero de llamadores de Ghidra.

    Returns:
        tuple[int, tuple[int, ...]]: Funciones cuyo conteo coincide y direcciones de las que
        difieren, en orden.

    Ejemplo:
        coinciden, difieren = comparar_llamadores(grafo, esperados)
    """
    sitios: dict[int, int] = defaultdict(int)
    for arista in grafo.aristas:
        if arista.destino is not None and arista.tipo in ("jal", "j"):
            sitios[arista.destino] += arista.veces
    difieren = tuple(d for d, esperado in sorted(esperados.items()) if sitios[d] != esperado)
    return len(esperados) - len(difieren), difieren


def comparar_datos(grafo: Grafo, esperados: Mapping[int, Iterable[int]]) -> Comparacion:
    """
    Compara los datos compartidos propios con las referencias que exporto Ghidra.

    Contexto:
        Segunda comprobacion cruzada contra una herramienta independiente: ``xrefs_datos.csv``.
        Ghidra propaga constantes y atribuye accesos a traves de registros base, por lo que
        puede ver mas funciones por dato que la lectura simbolica del desensamblado.

    Args:
        grafo (Grafo): Grafo ya construido.
        esperados (Mapping[int, Iterable[int]]): Dato a funciones que lo usan segun Ghidra.

    Returns:
        Comparacion: Datos conocidos por ambos con el mismo conjunto de funciones, datos donde el
        conjunto propio esta contenido en el de Ghidra (contenidos) y direcciones donde difieren.

    Ejemplo:
        comparacion = comparar_datos(grafo, esperados)
    """
    coinciden = contenidos = 0
    difieren: list[int] = []
    for dato in sorted(set(esperados) & set(grafo.datos)):
        propias, ajenas = set(grafo.datos[dato]), set(esperados[dato])
        if propias == ajenas:
            coinciden += 1
        elif propias < ajenas:
            contenidos += 1
        else:
            difieren.append(dato)
    return Comparacion(coinciden, contenidos, tuple(difieren))

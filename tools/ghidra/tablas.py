"""Tablas de punteros a codigo dentro de la zona de datos del ejecutable.

Un ``switch`` compilado y una tabla de rutinas llamadas por indice dejan en los datos corridas de
palabras que apuntan a codigo. Este modulo las localiza leyendo el segmento; quien las usa
(grafo y borradores) decide si son saltos internos de una funcion o llamadas a otras funciones.
"""

import csv
import io
import struct
from bisect import bisect_right
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Final, Literal

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


def corrida_que_contiene(
    corridas: list[Corrida], direccion: int, inicios: Sequence[int] | None = None
) -> Corrida | None:
    """
    Busca la corrida que contiene una direccion.

    Contexto:
        Resuelve a que tabla pertenece una direccion referenciada por una funcion.

    Args:
        corridas (list[Corrida]): Corridas ordenadas por direccion (salida de ``detectar_corridas``).
        direccion (int): Direccion de dato.
        inicios (Sequence[int] | None, opcional): Direcciones de inicio de ``corridas`` ya ordenadas; evita
            reconstruirlas en cada llamada cuando se consulta muchas veces.

    Returns:
        Corrida | None: La corrida si ``direccion`` cae dentro de ella.

    Ejemplo:
        corrida = corrida_que_contiene(corridas, 0x8005E370)
    """
    posicion = bisect_right([c.direccion for c in corridas] if inicios is None else inicios, direccion) - 1
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


TipoTabla = Literal["salto", "puntero_a_funcion"]
"""Una tabla de ``switch`` (destinos dentro de una funcion) o de punteros a funcion (rutinas)."""

VENTANA_REGISTROS: Final[int] = 100
"""Instrucciones durante las que se sigue el valor de un registro formado con una direccion de tabla."""

_CARGAS: Final[frozenset[int]] = frozenset({0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26})
_ALMACENES: Final[frozenset[int]] = frozenset({0x28, 0x29, 0x2A, 0x2B, 0x2E})
_RAMAS: Final[frozenset[int]] = frozenset({1, 4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17})
_REGISTRO_RETORNO: Final[int] = 31
_OP_LW: Final[int] = 0x23


@dataclass(frozen=True)
class ReferenciaTabla:
    """Instruccion que forma o lee una direccion dentro de una tabla de punteros a codigo.

    ``forma`` es ``direccion`` (la direccion se calcula con ``lui`` mas ``addiu``/``ori``),
    ``indexada`` (se lee con un indice sumado) o ``elemento`` (lectura de una posicion fija).
    ``salto`` y ``tipo_salto`` indican el ``jr``/``jalr`` que usa el valor leido, si lo hay.
    ``manual`` es verdadero si la direccion del elemento se calculo con ``add`` (con desbordamiento),
    una instruccion que el compilador no emite para indexar y que delata un despachador escrito a mano.
    """

    instruccion: int
    direccion: int
    forma: str
    salto: int | None
    tipo_salto: str | None
    manual: bool = False


@dataclass(frozen=True)
class TablaClasificada:
    """Tabla de punteros a codigo con su clasificacion y la evidencia que la respalda."""

    direccion: int
    destinos: tuple[int, ...]
    tipo: TipoTabla
    consumidor: int | None
    evidencia: int | None
    motivo: str


def _destino_gpr(palabra: int) -> int | None:
    """Registro que escribe una instruccion, o ``None`` si no escribe ninguno."""
    operacion = palabra >> 26
    if operacion == 0:
        funcion = palabra & 0x3F
        if funcion in (0x08, 0x0C, 0x0D, 0x11, 0x13, 0x18, 0x19, 0x1A, 0x1B):
            return None
        return (palabra >> 11) & 31
    if operacion == 3:
        return _REGISTRO_RETORNO
    if 8 <= operacion <= 0x0F or operacion in _CARGAS:
        return (palabra >> 16) & 31
    return None


class _Seguimiento:
    """Estado mientras se recorre el codigo: valores de registros y referencias abiertas."""

    def __init__(self, corridas: list[Corrida]) -> None:
        """Crea el seguimiento vacio para unas corridas dadas."""
        self.corridas = corridas
        self.inicios = [c.direccion for c in corridas]
        self.registros: dict[int, tuple[str, int, int, bool]] = {}
        self.valores: dict[int, tuple[int, int]] = {}
        self.pendientes: list[dict[str, int | str | None]] = []

    def procesar(self, indice: int, direccion: int, palabra: int) -> None:
        """Actualiza el estado con una instruccion."""
        self.registros = {r: e for r, e in self.registros.items() if indice - e[2] <= VENTANA_REGISTROS}
        self.valores = {r: e for r, e in self.valores.items() if indice - e[1] <= VENTANA_REGISTROS}
        operacion, rs = palabra >> 26, (palabra >> 21) & 31
        if operacion == 0 and (palabra & 0x3F) in (8, 9) and rs != _REGISTRO_RETORNO and rs in self.valores:
            referencia = self.pendientes[self.valores[rs][0]]
            referencia["salto"] = direccion
            referencia["tipo_salto"] = "jr" if palabra & 0x3F == 8 else "jalr"
        nuevo, leido = self._efecto(indice, direccion, palabra)
        escribe = _destino_gpr(palabra)
        if escribe is not None:
            self.registros.pop(escribe, None)
            self.valores.pop(escribe, None)
            if nuevo is not None:
                self.registros[escribe] = nuevo
            if leido is not None:
                self.valores[escribe] = leido

    def _efecto(
        self, indice: int, direccion: int, palabra: int
    ) -> tuple[tuple[str, int, int, bool] | None, tuple[int, int] | None]:
        """Valor que deja la instruccion en su registro destino y referencia que abre, si alguna."""
        operacion, rs, rt = palabra >> 26, (palabra >> 21) & 31, (palabra >> 16) & 31
        inmediato = palabra & 0xFFFF
        con_signo = inmediato - 0x10000 if inmediato & 0x8000 else inmediato
        if operacion == 0x0F:
            return ("k", inmediato << 16, indice, False), None
        if operacion in (9, 0x0D) and rs in self.registros:
            tipo, valor, _, manual = self.registros[rs]
            suma = (valor + con_signo if operacion == 9 else valor | inmediato) & 0xFFFFFFFF
            if tipo == "k" and corrida_que_contiene(self.corridas, suma, self.inicios) is not None:
                self.pendientes.append(_pendiente(direccion, suma, "direccion", False))
            return (tipo, suma, indice, manual), None
        if operacion == 0 and palabra & 0x3F in (0x20, 0x21):
            origenes = [self.registros[r] for r in (rs, rt) if r in self.registros]
            if len(origenes) == 1:
                return ("b", origenes[0][1], indice, origenes[0][3] or palabra & 0x3F == 0x20), None
            return None, None
        if (operacion in _CARGAS or operacion in _ALMACENES) and rs in self.registros:
            tipo, valor, _, manual = self.registros[rs]
            destino = (valor + con_signo) & 0xFFFFFFFF
            if corrida_que_contiene(self.corridas, destino, self.inicios) is not None and destino % 4 == 0:
                forma = "elemento" if tipo == "k" else "indexada"
                self.pendientes.append(_pendiente(direccion, destino, forma, manual))
                if operacion == _OP_LW:
                    return None, (len(self.pendientes) - 1, indice)
        return None, None


def referencias_a_tablas(
    segmento: bytes, base: int, corridas: list[Corrida], codigo: tuple[int, int]
) -> list[ReferenciaTabla]:
    """
    Busca en el codigo las instrucciones que forman o leen direcciones dentro de las corridas.

    Contexto:
        Primer paso de ``clasificar_tablas``: el consumidor de una tabla (``lw`` seguido de ``jr`` o
        ``jalr``) dice si sus destinos son casos de un ``switch`` o rutinas independientes. Se
        sigue el valor de los registros durante ``VENTANA_REGISTROS`` instrucciones: ``lui`` fija la
        parte alta, ``addiu``/``ori`` la completan y una suma con un indice la deja como base mas
        indice.

    Args:
        segmento (bytes): Segmento cargado del ejecutable.
        base (int): Direccion virtual del primer byte del segmento.
        corridas (list[Corrida]): Corridas de punteros a codigo (``detectar_corridas``).
        codigo (tuple[int, int]): Rango ``[inicio, fin)`` del codigo que se recorre.

    Returns:
        list[ReferenciaTabla]: Referencias en orden de direccion de instruccion.

    Raises:
        ValueError: Si el rango de codigo esta desalineado o fuera del segmento.

    Ejemplo:
        referencias = referencias_a_tablas(segmento, 0x80014A00, corridas, (0x80014A00, 0x8005DEA0))
    """
    inicio, fin = codigo
    if inicio % 4 or fin % 4 or inicio < base or fin > base + len(segmento) or inicio > fin:
        raise ValueError("tablas: el rango de codigo debe estar alineado a 4 y dentro del segmento")
    seguimiento = _Seguimiento(corridas)
    for indice, direccion in enumerate(range(inicio, fin, 4)):
        (palabra,) = struct.unpack_from("<I", segmento, direccion - base)
        seguimiento.procesar(indice, direccion, palabra)
    pendientes = seguimiento.pendientes
    return [
        ReferenciaTabla(
            int(r["instruccion"] or 0),
            int(r["direccion"] or 0),
            str(r["forma"]),
            None if r["salto"] is None else int(r["salto"]),
            None if r["tipo_salto"] is None else str(r["tipo_salto"]),
            bool(r["manual"]),
        )
        for r in pendientes
    ]


def _pendiente(instruccion: int, direccion: int, forma: str, manual: bool) -> dict[str, int | str | None]:
    """Registro mutable de una referencia mientras se busca su ``jr``/``jalr``."""
    return {
        "instruccion": instruccion,
        "direccion": direccion,
        "forma": forma,
        "salto": None,
        "tipo_salto": None,
        "manual": int(manual),
    }


def _palabra(segmento: bytes, base: int, direccion: int) -> int:
    """Palabra de 32 bits (little endian) en una direccion del segmento."""
    return int(struct.unpack_from("<I", segmento, direccion - base)[0])


def segmentos_independientes(
    segmento: bytes, base: int, destinos: Iterable[int], limite: int, inicios: Iterable[int] = ()
) -> tuple[int, int]:
    """
    Cuenta cuantos tramos delimitados por los destinos de una tabla no son rutinas independientes.

    Contexto:
        Los destinos distintos de una tabla, ordenados, parten el codigo en tramos. Si la tabla es de
        punteros a funcion, cada tramo es una rutina: no se bifurca hacia otro tramo y no cae en el
        siguiente. En los casos de un ``switch`` si ocurre (saltos a un final comun, caidas).

    Args:
        segmento (bytes): Segmento cargado del ejecutable.
        base (int): Direccion virtual del primer byte del segmento.
        destinos (Iterable[int]): Destinos de la tabla.
        limite (int): Primera direccion posterior al ultimo tramo.
        inicios (Iterable[int], opcional): Inicios de funcion conocidos; un ``j`` hacia uno de ellos
            es una llamada de cola y no cruza tramos.

    Returns:
        tuple[int, int]: Numero de tramos y numero de ellos que se bifurcan a otro tramo o caen en
        el siguiente.

    Raises:
        ValueError: Si no hay destinos o alguno no esta alineado o esta fuera de ``[destino, limite)``.

    Ejemplo:
        tramos, violaciones = segmentos_independientes(segmento, base, destinos, limite)
    """
    puntos = sorted(set(destinos))
    if not puntos or any(d % 4 or d >= limite for d in puntos):
        raise ValueError("tablas: los destinos deben estar alineados y por debajo del limite")
    conocidos = set(inicios)
    fronteras = [*puntos, limite]
    violaciones = 0
    for inicio, fin in pairwise(fronteras):
        if _tramo_se_cruza(segmento, base, inicio, fin, conocidos):
            violaciones += 1
    return len(puntos), violaciones


def _tramo_se_cruza(segmento: bytes, base: int, inicio: int, fin: int, conocidos: set[int]) -> bool:
    """Indica si un tramo se bifurca fuera de si mismo o cae en el siguiente."""
    for direccion in range(inicio, fin, 4):
        palabra = _palabra(segmento, base, direccion)
        operacion = palabra >> 26
        if operacion in _RAMAS:
            inmediato = palabra & 0xFFFF
            con_signo = inmediato - 0x10000 if inmediato & 0x8000 else inmediato
            if not inicio <= direccion + 4 + 4 * con_signo < fin:
                return True
        elif operacion == 2:
            destino = (direccion & 0xF0000000) | ((palabra & 0x03FFFFFF) << 2)
            if not inicio <= destino < fin and destino not in conocidos:
                return True
    ultima = fin - 8
    if ultima < inicio:
        return True
    palabra = _palabra(segmento, base, ultima)
    operacion, rs, rt = palabra >> 26, (palabra >> 21) & 31, (palabra >> 16) & 31
    es_jr = operacion == 0 and palabra & 0x3F == 8
    es_b = operacion in (4, 0x14) and rs == rt
    return not (operacion == 2 or es_jr or es_b)


def clasificar_tablas(
    segmento: bytes,
    base: int,
    corridas: list[Corrida],
    inicios: Sequence[int],
    codigo: tuple[int, int],
) -> list[TablaClasificada]:
    """
    Clasifica cada tabla de punteros a codigo como de ``switch`` o de punteros a funcion.

    Contexto:
        Una tabla de punteros a funcion se consume con ``jalr``; una tabla de ``switch`` se consume con
        ``lw`` mas ``jr`` y sus destinos son casos de la misma funcion. Hay un caso intermedio, el
        despacho por ``jr`` sin enlace desde rutinas escritas en ensamblador, donde los destinos son
        rutinas completas: se distingue porque los tramos entre destinos son independientes. Solo
        las tablas de punteros a funcion declaran funciones nuevas.

    Args:
        segmento (bytes): Segmento cargado del ejecutable.
        base (int): Direccion virtual del primer byte del segmento.
        corridas (list[Corrida]): Corridas de punteros a codigo.
        inicios (Sequence[int]): Inicios de funcion conocidos, en cualquier orden.
        codigo (tuple[int, int]): Rango ``[inicio, fin)`` del codigo.

    Returns:
        list[TablaClasificada]: Una entrada por tabla (varias tablas pueden compartir corrida) en orden
        de direccion.

    Ejemplo:
        tablas = clasificar_tablas(segmento, 0x80014A00, corridas, inicios, (0x80014A00, 0x8005DEA0))
    """
    referencias = referencias_a_tablas(segmento, base, corridas, codigo)
    ordenados = sorted(inicios)
    resultado: list[TablaClasificada] = []
    for corrida in corridas:
        fronteras = sorted(
            {corrida.direccion}
            | {
                r.direccion
                for r in referencias
                if r.forma != "elemento" and corrida.direccion <= r.direccion < corrida.fin
            }
        )
        for direccion in fronteras:
            destinos = tramo_de_tabla(corrida, direccion, fronteras)
            usos = [r for r in referencias if r.direccion == direccion and r.salto is not None]
            resultado.append(
                _clasificar(
                    segmento,
                    base,
                    direccion=direccion,
                    destinos=destinos,
                    usos=usos,
                    inicios=ordenados,
                    codigo=codigo,
                )
            )
    return resultado


def _clasificar(
    segmento: bytes,
    base: int,
    *,
    direccion: int,
    destinos: tuple[int, ...],
    usos: list[ReferenciaTabla],
    inicios: list[int],
    codigo: tuple[int, int],
) -> TablaClasificada:
    """Clasifica una tabla con sus usos conocidos."""
    consumidor = _funcion_de(inicios, usos[0].salto) if usos and usos[0].salto is not None else None
    siguiente = next((i for i in inicios if i > max(destinos)), codigo[1])
    tramos, cruzados = segmentos_independientes(segmento, base, destinos, siguiente, inicios)
    for uso in usos:
        if uso.tipo_salto == "jalr":
            return TablaClasificada(
                direccion,
                destinos,
                "puntero_a_funcion",
                _funcion_de(inicios, uso.salto or 0),
                uso.salto,
                "se consume con jalr",
            )
    detalle = f"{tramos} tramos, {cruzados} se bifurcan o caen en otro"
    origen = "se consume con lw+jr" if usos else "sin consumo visible (copiada)"
    manual = any(u.manual for u in usos)
    primera = usos[0].salto if usos else None
    if cruzados == 0 and (manual or not usos):
        marca = "; direccion calculada con add (despachador escrito a mano)" if manual else ""
        return TablaClasificada(
            direccion,
            destinos,
            "puntero_a_funcion",
            consumidor,
            primera,
            f"{origen}; rutinas independientes ({detalle}){marca}",
        )
    if not usos and set(destinos) <= set(inicios):
        return TablaClasificada(
            direccion,
            destinos,
            "puntero_a_funcion",
            consumidor,
            primera,
            "todos los destinos ya son inicio de funcion",
        )
    return TablaClasificada(
        direccion, destinos, "salto", consumidor, primera, f"{origen}; casos de un switch ({detalle})"
    )


def _funcion_de(inicios: list[int], direccion: int) -> int | None:
    """Inicio de la funcion que contiene una direccion, o ``None``."""
    posicion = bisect_right(inicios, direccion) - 1
    return inicios[posicion] if posicion >= 0 else None


COLUMNAS_TABLAS: Final[tuple[str, ...]] = (
    "tabla",
    "direccion",
    "entradas",
    "tipo",
    "funcion_consumidora",
    "evidencia",
    "destinos_nuevos",
    "motivo",
)


def formatear_tablas_csv(
    tablas: Sequence[TablaClasificada], nombres: Mapping[int, str], nuevos: Collection[int]
) -> str:
    """
    Serializa la clasificacion de tablas como CSV.

    Contexto:
        Salida ``tablas_de_punteros.csv``: para cada tabla, su tipo, la funcion que la consume, la
        direccion de la instruccion que lee su valor y cuantos de sus destinos se declararon como
        funciones nuevas. Insumo de la particion del ejecutable.

    Args:
        tablas (Sequence[TablaClasificada]): Resultado de ``clasificar_tablas``.
        nombres (Mapping[int, str]): Direccion de funcion a nombre de simbolo.
        nuevos (Collection[int]): Direcciones de las funciones creadas a partir de las tablas.

    Returns:
        str: CSV con LF y las columnas de ``COLUMNAS_TABLAS``.

    Ejemplo:
        texto = formatear_tablas_csv(tablas, nombres, {d for d, _ in refinado.nuevas})
    """
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(COLUMNAS_TABLAS)
    for tabla in sorted(tablas, key=lambda t: t.direccion):
        consumidora = (
            "" if tabla.consumidor is None else nombres.get(tabla.consumidor, f"0x{tabla.consumidor:08X}")
        )
        escritor.writerow(
            [
                f"D_{tabla.direccion:08X}",
                f"0x{tabla.direccion:08X}",
                len(tabla.destinos),
                tabla.tipo,
                consumidora,
                "" if tabla.evidencia is None else f"0x{tabla.evidencia:08X}",
                len({d for d in tabla.destinos if d in nuevos}),
                tabla.motivo,
            ]
        )
    return salida.getvalue()

"""Mutaciones del C de una funcion que conservan su significado.

Cada mutacion recibe el arbol de una funcion y lo cambia en un sitio elegido al azar por una
reformulacion equivalente: reordenar declaraciones o sentencias independientes, introducir o
eliminar un temporal, cambiar el ancho de un temporal, conmutar operandos, pasar de indice a puntero,
cambiar de ``for`` a ``while`` y negar una condicion intercambiando sus ramas. Son las
reformulaciones que alteran el reparto de registros y el orden de las instrucciones del compilador
sin cambiar lo que la funcion hace.

Ninguna mutacion escribe ensamblador, ``volatile``, ``register`` ni barreras: son recursos que el
proyecto no admite como estado final, y ``variante_permitida`` descarta cualquier variante que
aumente su cantidad respecto al C de partida. Las macros de funcion (``GEO_*``, ``gte_*``) y las
llamadas son sentencias opacas: nada se mueve a traves de ellas y sus argumentos no se parten.
"""

from __future__ import annotations

import copy
import itertools
import random
import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from tools.reconstruccion import permutar_analisis as an
from tools.reconstruccion import permutar_c as c

PREFIJO_TEMPORAL = "tmp"
PATRONES_PROHIBIDOS = (
    re.compile(r"__asm__"),
    re.compile(r"\basm\s*\("),
    re.compile(r"\bvolatile\b"),
    re.compile(r"\bregister\b"),
    re.compile(r"\bGLOBAL_ASM\b"),
)
OPERADORES_CONMUTATIVOS = frozenset({"+", "*", "&", "|", "^", "==", "!="})
RELACIONALES_INVERSOS = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}
NEGACION_DE_COMPARACION = {"==": "!=", "!=": "==", "<": ">=", ">=": "<", ">": "<=", "<=": ">"}
PROBABILIDAD_TODAS_LAS_APARICIONES = 0.5
PROBABILIDAD_NEGACION_LITERAL = 0.3


@dataclass
class Contexto:
    """Estado de una ronda de mutaciones sobre una copia de la funcion.

    Attributes:
        funcion: Copia de la funcion que se muta.
        entorno: Tipos de los identificadores de la copia.
        azar: Generador de numeros aleatorios.
        nombres: Identificadores en uso (para no repetir el nombre de un temporal).
    """

    funcion: c.Funcion
    entorno: an.Entorno
    azar: random.Random
    nombres: set[str]

    @property
    def alias(self) -> Mapping[str, str]:
        """Campos que comparten almacenamiento en una ``union``, para los efectos de las sentencias."""
        return self.entorno.tabla.alias_de_campos


@dataclass(frozen=True)
class Sitio:
    """Una subexpresion junto con su contexto.

    Attributes:
        nodo: La subexpresion.
        padre: Nodo o sentencia que la contiene.
        perezoso: Verdadero si solo se evalua a veces (operando derecho de ``&&``, ramas de ``?:``).
        lvalue: Verdadero si es un destino o un operando de ``&`` (no se puede copiar a un temporal).
    """

    nodo: c.Expr
    padre: object
    perezoso: bool
    lvalue: bool


# ---------------------------------------------------------------------------------------------------
# Recorridos
# ---------------------------------------------------------------------------------------------------


def _hijos_con_contexto(  # noqa: PLR0911 - despachador por tipo de nodo
    expr: c.Expr, perezoso: bool, lvalue: bool
) -> list[tuple[c.Expr, bool, bool]]:
    """Hijos de una expresion con las banderas ``perezoso`` y ``lvalue`` que les corresponden."""
    if isinstance(expr, c.Binario) and expr.op in ("&&", "||"):
        return [(expr.izq, perezoso, False), (expr.der, True, False)]
    if isinstance(expr, c.Ternario):
        return [(expr.cond, perezoso, False), (expr.si, True, False), (expr.no, True, False)]
    if isinstance(expr, c.Asigna):
        return [(expr.destino, perezoso, True), (expr.valor, perezoso, False)]
    if isinstance(expr, c.Unario) and expr.op in ("&", "++", "--"):
        return [(expr.operando, perezoso, True)]
    if isinstance(expr, c.Postfijo):
        return [(expr.operando, perezoso, True)]
    if isinstance(expr, c.Llamada):
        return [(expr.funcion, perezoso, True), *((a, perezoso, False) for a in expr.args)]
    if isinstance(expr, c.Miembro):
        return [(expr.base, perezoso, lvalue and not expr.flecha)]
    if isinstance(expr, c.Indice):
        return [(expr.base, perezoso, lvalue), (expr.indice, perezoso, False)]
    return [(hijo, perezoso, False) for hijo in c.hijos(expr)]


def sitios_de(
    raiz: c.Expr, padre: object, *, perezoso: bool = False, lvalue: bool = False
) -> Iterator[Sitio]:
    """
    Recorre una expresion dando cada subexpresion con su contexto de evaluacion.

    Contexto:
        Las mutaciones de temporales y de operandos eligen su sitio entre estos.

    Args:
        raiz (c.Expr): Raiz del recorrido.
        padre (object): Sentencia o nodo que contiene a ``raiz``.
        perezoso (bool, opcional): Si la raiz ya esta en una posicion de evaluacion condicional.
        lvalue (bool, opcional): Si la raiz es un destino.

    Yields:
        Sitio: Cada nodo en preorden.

    Ejemplo:
        sitios = list(sitios_de(sentencia.expr, sentencia))
    """
    yield Sitio(raiz, padre, perezoso, lvalue)
    for hijo, hijo_perezoso, hijo_lvalue in _hijos_con_contexto(raiz, perezoso, lvalue):
        yield from sitios_de(hijo, raiz, perezoso=hijo_perezoso, lvalue=hijo_lvalue)


def _sentencias(funcion: c.Funcion) -> Iterator[tuple[c.Bloque, int, c.Sentencia]]:
    """Cada sentencia de la funcion con su bloque y su posicion."""
    for bloque in c.todos_los_bloques(funcion.cuerpo):
        for indice, sentencia in enumerate(list(bloque.items)):
            yield bloque, indice, sentencia


def _todas_las_expresiones(funcion: c.Funcion) -> Iterator[tuple[c.Sentencia, c.Expr]]:
    """Cada expresion raiz de la funcion con su sentencia."""
    for _, _, sentencia in _sentencias(funcion):
        for raiz in c.expresiones_de(sentencia):
            yield sentencia, raiz


def _nombres_de(funcion: c.Funcion) -> set[str]:
    """Todos los identificadores que aparecen en la funcion, incluidos los declarados."""
    nombres = {p.nombre for p in funcion.parametros}
    for _, _, sentencia in _sentencias(funcion):
        if isinstance(sentencia, c.Decl):
            nombres.add(sentencia.nombre)
        for raiz in c.expresiones_de(sentencia):
            nombres |= an.identificadores_de(raiz)
    return nombres


def nombres_ambiguos(funcion: c.Funcion) -> set[str]:
    """
    Nombres que no identifican a una unica variable dentro de la funcion.

    Contexto:
        El seguimiento de tipos y de usos de las mutaciones de temporales, de ancho y de parametros
        trabaja por nombre, sin ambito lexico: dos locales ``tmp`` en bloques hermanos, o una local
        que sombrea a un parametro, se confundirian en una sola variable y una mutacion podria borrar
        la declaracion equivocada o razonar con el tipo equivocado. Esas mutaciones solo actuan sobre
        nombres que NO estan en este conjunto, ni toman subexpresiones que los mencionen.

    Args:
        funcion (c.Funcion): Funcion que se analiza.

    Returns:
        set[str]: Nombres declarados mas de una vez en cualquier bloque (incluidos los anidados) y
        nombres de local que coinciden con un parametro.

    Ejemplo:
        ambiguos = nombres_ambiguos(funcion)
    """
    parametros = {p.nombre for p in funcion.parametros}
    vistos: set[str] = set()
    ambiguos: set[str] = set()
    for _, _, sentencia in _sentencias(funcion):
        if not isinstance(sentencia, c.Decl):
            continue
        if sentencia.nombre in vistos or sentencia.nombre in parametros:
            ambiguos.add(sentencia.nombre)
        vistos.add(sentencia.nombre)
    return ambiguos


def _fin_de_declaraciones(cuerpo: c.Bloque) -> int:
    """Posicion donde termina la serie inicial de declaraciones de un bloque."""
    posicion = 0
    while posicion < len(cuerpo.items) and isinstance(cuerpo.items[posicion], c.Decl):
        posicion += 1
    return posicion


def _elegir[T](azar: random.Random, opciones: list[T]) -> T | None:
    """Elige un elemento al azar; ``None`` si la lista esta vacia."""
    return azar.choice(opciones) if opciones else None


def _contiene_continuar(bloque: c.Bloque) -> bool:
    """Indica si un cuerpo de bucle tiene un ``continue`` que le pertenezca (no el de un bucle interior)."""
    for sentencia in bloque.items:
        if isinstance(sentencia, c.Continuar):
            return True
        if isinstance(sentencia, c.Mientras | c.HacerMientras | c.Para):
            continue
        if any(_contiene_continuar(hijo) for hijo in c.bloques_hijos(sentencia)):
            return True
    return False


# ---------------------------------------------------------------------------------------------------
# Orden de declaraciones y sentencias
# ---------------------------------------------------------------------------------------------------


def _orden_de_declaraciones_valido(declaraciones: list[c.Decl]) -> bool:
    """Un inicializador solo puede nombrar variables de la serie declaradas antes que el."""
    de_la_serie = {d.nombre for d in declaraciones}
    declaradas: set[str] = set()
    for declaracion in declaraciones:
        if declaracion.inicial is not None:
            usadas = an.identificadores_de(declaracion.inicial) & de_la_serie
            if not usadas <= declaradas:
                return False
        declaradas.add(declaracion.nombre)
    return True


def orden_de_declaraciones(ctx: Contexto) -> str | None:
    """
    Mueve una declaracion local a otra posicion de su serie.

    Contexto:
        El orden de las declaraciones fija la reserva de pila y el numero de pseudoregistro de cada
        variable, que desempata el reparto de registros.

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion de la mutacion, o ``None`` si ningun bloque tiene dos declaraciones
        que se puedan reordenar.

    Ejemplo:
        descripcion = orden_de_declaraciones(contexto)
    """
    candidatos: list[tuple[c.Bloque, int, int]] = []
    for bloque in c.todos_los_bloques(ctx.funcion.cuerpo):
        fin = _fin_de_declaraciones(bloque)
        if fin < 2:
            continue
        declaraciones = [d for d in bloque.items[:fin] if isinstance(d, c.Decl)]
        for origen in range(fin):
            for destino in range(fin):
                if origen == destino:
                    continue
                movida = list(declaraciones)
                movida.insert(destino, movida.pop(origen))
                if _orden_de_declaraciones_valido(movida):
                    candidatos.append((bloque, origen, destino))
    elegido = _elegir(ctx.azar, candidatos)
    if elegido is None:
        return None
    bloque, origen, destino = elegido
    nombre = getattr(bloque.items[origen], "nombre", "")
    bloque.items.insert(destino, bloque.items.pop(origen))
    return f"orden_declaraciones({nombre} a la posicion {destino})"


def _locales_con_direccion(funcion: c.Funcion) -> set[str]:
    """Ubicaciones ``v:nombre`` de las variables a las que la funcion les toma la direccion."""
    return {
        f"v:{nodo.operando.nombre}"
        for _, raiz in _todas_las_expresiones(funcion)
        for nodo in c.recorrer(raiz)
        if isinstance(nodo, c.Unario) and nodo.op == "&" and isinstance(nodo.operando, c.Id)
    }


def orden_de_sentencias(ctx: Contexto) -> str | None:
    """
    Intercambia dos sentencias de expresion consecutivas que no dependen una de la otra.

    Contexto:
        El orden de sentencias independientes cambia la planificacion y la vida de los registros.

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion, o ``None`` si no hay un par intercambiable.

    Ejemplo:
        descripcion = orden_de_sentencias(contexto)
    """
    con_direccion = _locales_con_direccion(ctx.funcion)
    candidatos: list[tuple[c.Bloque, int]] = []
    for bloque in c.todos_los_bloques(ctx.funcion.cuerpo):
        for indice in range(len(bloque.items) - 1):
            a = an.efectos_de(bloque.items[indice], ctx.alias)
            b = an.efectos_de(bloque.items[indice + 1], ctx.alias)
            # Una variable con direccion tomada puede escribirse por un puntero: no se mueve.
            tocadas = a.lee | a.escribe | b.lee | b.escribe
            if an.son_independientes(a, b) and not con_direccion & tocadas:
                candidatos.append((bloque, indice))
    elegido = _elegir(ctx.azar, candidatos)
    if elegido is None:
        return None
    bloque, indice = elegido
    bloque.items[indice], bloque.items[indice + 1] = bloque.items[indice + 1], bloque.items[indice]
    return f"orden_sentencias(posiciones {indice} y {indice + 1})"


# ---------------------------------------------------------------------------------------------------
# Temporales
# ---------------------------------------------------------------------------------------------------


def _nombre_temporal(ctx: Contexto) -> str:
    """Primer nombre ``tmpN`` que no esta en uso."""
    numero = 1
    while f"{PREFIJO_TEMPORAL}{numero}" in ctx.nombres:
        numero += 1
    nombre = f"{PREFIJO_TEMPORAL}{numero}"
    ctx.nombres.add(nombre)
    return nombre


def _declarar_temporal(ctx: Contexto, nombre: str, tipo: an.Tipo) -> None:
    """Anade la declaracion del temporal al final de las declaraciones de la funcion."""
    cuerpo = ctx.funcion.cuerpo
    cuerpo.items.insert(_fin_de_declaraciones(cuerpo), c.Decl(tipo.base, tipo.estrellas, nombre))
    ctx.entorno.locales[nombre] = tipo


def _aparicion_unica_de_asignacion(raiz: c.Expr) -> bool:
    """Una sentencia admite izar una subexpresion si no tiene mas efectos que su asignacion o llamada raiz."""
    asignaciones = [n for n in c.recorrer(raiz) if isinstance(n, c.Asigna)]
    llamadas = [n for n in c.recorrer(raiz) if isinstance(n, c.Llamada)]
    incrementos = [
        n
        for n in c.recorrer(raiz)
        if isinstance(n, c.Postfijo) or (isinstance(n, c.Unario) and n.op in ("++", "--"))
    ]
    if incrementos or len(asignaciones) > 1 or (asignaciones and asignaciones[0] is not raiz):
        return False
    if not llamadas:
        return True
    return len(llamadas) == 1 and llamadas[0] is raiz and all(an.es_pura(a) for a in raiz.args)


def _sitios_izables(ctx: Contexto) -> list[tuple[c.Bloque, int, Sitio, an.Tipo]]:
    """Subexpresiones puras de tipo escalar conocido que se pueden copiar a un temporal."""
    resultado: list[tuple[c.Bloque, int, Sitio, an.Tipo]] = []
    ambiguos = nombres_ambiguos(ctx.funcion)
    for bloque, indice, sentencia in _sentencias(ctx.funcion):
        if isinstance(sentencia, c.Decl | c.Mientras | c.HacerMientras | c.Para | c.Caso):
            continue
        for raiz in c.expresiones_de(sentencia):
            if not _aparicion_unica_de_asignacion(raiz):
                continue
            for sitio in sitios_de(raiz, sentencia):
                tipo = ctx.entorno.inferir(sitio.nodo)
                es_izable = (
                    tipo is not None
                    and tipo.es_escalar
                    and not sitio.perezoso
                    and not sitio.lvalue
                    and an.es_pura(sitio.nodo)
                    and not isinstance(sitio.nodo, c.Num)
                    and not an.identificadores_de(sitio.nodo) & ambiguos
                    and not (sitio.padre is sentencia and isinstance(sentencia, c.Expresion))
                )
                if es_izable and tipo is not None:
                    resultado.append((bloque, indice, sitio, tipo))
    return resultado


def _posicion_de_la_asignacion(
    bloque: c.Bloque, indice: int, asignacion: c.Expresion, azar: random.Random, alias: Mapping[str, str]
) -> int:
    """
    Elige donde colocar la asignacion de un temporal: justo antes de su uso o mas arriba.

    Contexto:
        Adelantar la carga de un valor por encima de sentencias que no lo tocan alarga su vida; es la
        forma en que muchos cierres de registros hacen que el valor ya este cargado. Solo se sube por
        encima de sentencias independientes de la asignacion (sin llamadas ni escrituras que la afecten).

    Args:
        bloque (c.Bloque): Bloque donde esta la sentencia que usa el temporal.
        indice (int): Posicion de esa sentencia.
        asignacion (c.Expresion): Asignacion del temporal.
        azar (random.Random): Generador de numeros aleatorios.
        alias (Mapping[str, str]): Campos que comparten almacenamiento en una ``union``.

    Returns:
        int: Posicion de insercion, entre la mas alta posible y ``indice``.

    Ejemplo:
        posicion = _posicion_de_la_asignacion(bloque, 5, asignacion, azar, alias)
    """
    efectos = an.efectos_de(asignacion, alias)
    mas_alta = indice
    while mas_alta > 0 and an.son_independientes(an.efectos_de(bloque.items[mas_alta - 1], alias), efectos):
        mas_alta -= 1
    return mas_alta + int(azar.random() * (indice - mas_alta + 1))


def introducir_temporal(ctx: Contexto) -> str | None:
    """
    Copia una subexpresion pura a una variable local declarada justo antes de su sentencia.

    Contexto:
        Un temporal alarga la vida de un valor y cambia el reparto de registros; es la reformulacion
        mas productiva en este compilador. Con probabilidad 1/2 sustituye todas las apariciones iguales de
        la expresion en la sentencia.

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion, o ``None`` si ninguna subexpresion es apta.

    Ejemplo:
        descripcion = introducir_temporal(contexto)
    """
    elegido = _elegir(ctx.azar, _sitios_izables(ctx))
    if elegido is None:
        return None
    bloque, indice, sitio, tipo = elegido
    sentencia = bloque.items[indice]
    nombre = _nombre_temporal(ctx)
    clave = an.texto_de(sitio.nodo)
    copia = copy.deepcopy(sitio.nodo)
    if ctx.azar.random() < PROBABILIDAD_TODAS_LAS_APARICIONES:
        for raiz in c.expresiones_de(sentencia):
            for otro in list(sitios_de(raiz, sentencia)):
                if not otro.lvalue and not otro.perezoso and an.texto_de(otro.nodo) == clave:
                    c.reemplazar_hijo(otro.padre, otro.nodo, c.Id(nombre))
    else:
        c.reemplazar_hijo(sitio.padre, sitio.nodo, c.Id(nombre))
    asignacion = c.Expresion(expr=c.Asigna("=", c.Id(nombre), copia))
    # La asignacion se inserta antes que la declaracion: esta se coloca al inicio del cuerpo y
    # desplazaria el indice de la sentencia.
    bloque.items.insert(
        _posicion_de_la_asignacion(bloque, indice, asignacion, ctx.azar, ctx.alias), asignacion
    )
    _declarar_temporal(ctx, nombre, tipo)
    return f"introducir_temporal({tipo.texto} {nombre} = {clave})"


def _usos_de(funcion: c.Funcion, nombre: str) -> list[tuple[c.Sentencia, Sitio]]:
    """Cada aparicion de un identificador con su sentencia."""
    usos: list[tuple[c.Sentencia, Sitio]] = []
    for _, _, sentencia in _sentencias(funcion):
        for raiz in c.expresiones_de(sentencia):
            usos.extend(
                (sentencia, sitio)
                for sitio in sitios_de(raiz, sentencia)
                if isinstance(sitio.nodo, c.Id) and sitio.nodo.nombre == nombre
            )
    return usos


def eliminar_temporal(ctx: Contexto) -> str | None:
    """
    Sustituye un temporal de un solo uso por la expresion que lo calcula.

    Contexto:
        Operacion inversa de ``introducir_temporal``: permite deshacer un temporal que el original
        no tenia, y quitar los del C de partida. Solo se aplica si la asignacion va justo antes del
        uso, no hay otras escrituras y el tipo de la expresion conserva todos los valores del temporal.

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion, o ``None`` si ningun temporal cumple las condiciones.

    Ejemplo:
        descripcion = eliminar_temporal(contexto)
    """
    candidatos: list[tuple[c.Bloque, int, Sitio]] = []
    ambiguos = nombres_ambiguos(ctx.funcion)
    declaradas = {
        s.nombre
        for _, _, s in _sentencias(ctx.funcion)
        if isinstance(s, c.Decl) and not s.inicial and s.nombre not in ambiguos
    }
    for bloque, indice, sentencia in _sentencias(ctx.funcion):
        if not (
            isinstance(sentencia, c.Expresion)
            and isinstance(sentencia.expr, c.Asigna)
            and sentencia.expr.op == "="
            and isinstance(sentencia.expr.destino, c.Id)
            and sentencia.expr.destino.nombre in declaradas
            and indice + 1 < len(bloque.items)
        ):
            continue
        nombre = sentencia.expr.destino.nombre
        usos = _usos_de(ctx.funcion, nombre)
        siguiente = bloque.items[indice + 1]
        lecturas = [u for u in usos if not u[1].lvalue]
        if len(usos) != 2 or len(lecturas) != 1 or lecturas[0][0] is not siguiente:
            continue
        sitio = lecturas[0][1]
        raiz = c.expresiones_de(siguiente)
        origen = ctx.entorno.inferir(sentencia.expr.valor)
        destino = ctx.entorno.locales.get(nombre)
        compatible = (
            origen is not None
            and destino is not None
            and an.promover(origen) == an.promover(destino)
            and (origen.texto == destino.texto or an.conserva_valor(origen, destino))
        )
        if (
            compatible
            and not an.identificadores_de(sentencia.expr.valor) & ambiguos
            and an.es_pura(sentencia.expr.valor)
            and not sitio.perezoso
            and raiz
            and all(_aparicion_unica_de_asignacion(r) for r in raiz)
        ):
            candidatos.append((bloque, indice, sitio))
    elegido = _elegir(ctx.azar, candidatos)
    if elegido is None:
        return None
    bloque, indice, sitio = elegido
    asignacion = bloque.items[indice]
    assert isinstance(asignacion, c.Expresion) and isinstance(asignacion.expr, c.Asigna)  # noqa: S101
    destino_id = asignacion.expr.destino
    assert isinstance(destino_id, c.Id)  # noqa: S101
    c.reemplazar_hijo(sitio.padre, sitio.nodo, asignacion.expr.valor)
    del bloque.items[indice]
    _quitar_declaracion(ctx.funcion, destino_id.nombre)
    return f"eliminar_temporal({destino_id.nombre})"


def _quitar_declaracion(funcion: c.Funcion, nombre: str) -> None:
    """Quita la declaracion de una variable que ya no se usa."""
    for bloque in c.todos_los_bloques(funcion.cuerpo):
        for indice, sentencia in enumerate(bloque.items):
            if isinstance(sentencia, c.Decl) and sentencia.nombre == nombre:
                del bloque.items[indice]
                return


def _ancho_permitido(ctx: Contexto, declaracion: c.Decl, ambiguos: set[str]) -> list[an.Tipo] | None:
    """Tipos a los que una local entera cambia sin perder valores, o ``None`` si no admite el cambio.

    Una variable de nombre ambiguo, o que recibe expresiones que mencionan uno, no admite el cambio.
    """
    if declaracion.nombre in ambiguos:
        return None
    actual = an.parsear_tipo(declaracion.base, declaracion.estrellas)
    if (
        not actual.es_entero
        or declaracion.sufijo
        or declaracion.declarador
        or actual.texto not in an.TIPOS_ENTEROS_PERMITIDOS
    ):
        return None
    fuentes: list[c.Expr] = []
    if declaracion.inicial is not None:
        fuentes.append(declaracion.inicial)
    insensible = True
    for sentencia, sitio in _usos_de(ctx.funcion, declaracion.nombre):
        padre = sitio.padre
        if isinstance(padre, c.Asigna) and padre.destino is sitio.nodo:
            if padre.op != "=":
                return None
            fuentes.append(padre.valor)
            continue
        if sitio.lvalue:
            return None
        insensible = insensible and _uso_insensible_al_signo(sitio, sentencia)
    if not fuentes or any(an.identificadores_de(fuente) & ambiguos for fuente in fuentes):
        return None
    permitidos = []
    for nombre in an.TIPOS_ENTEROS_PERMITIDOS:
        nuevo = an.tipo_entero(nombre)
        if nuevo.texto == actual.texto:
            continue
        if an.promover(nuevo) != an.promover(actual) and not insensible:
            continue
        if all(_cabe(ctx, fuente, actual, nuevo) for fuente in fuentes):
            permitidos.append(nuevo)
    return permitidos


def _uso_insensible_al_signo(sitio: Sitio, sentencia: c.Sentencia) -> bool:
    """Una lectura no depende del signo del tipo si copia el valor tal cual o lo compara por igualdad."""
    padre = sitio.padre
    if isinstance(padre, c.Asigna):
        return padre.valor is sitio.nodo and padre.op == "="
    if isinstance(padre, c.Llamada):
        return sitio.nodo in padre.args
    if isinstance(padre, c.Binario) and padre.op in ("==", "!="):
        otro = padre.der if padre.izq is sitio.nodo else padre.izq
        valor = an.valor_de_literal(otro)
        return valor is not None and valor >= 0
    if isinstance(padre, c.Unario):
        return padre.op == "!"
    return padre is sentencia and isinstance(sentencia, c.Si)


def _cabe(ctx: Contexto, fuente: c.Expr, actual: an.Tipo, nuevo: an.Tipo) -> bool:
    """Indica si el valor de una fuente asignada cabe, sin cambiar, en el tipo actual y en el nuevo."""
    literal = an.valor_de_literal(fuente)
    if literal is not None:
        return all(t.rango[0] <= literal <= t.rango[1] for t in (actual, nuevo))
    tipo = ctx.entorno.inferir(fuente)
    return tipo is not None and an.conserva_valor(tipo, actual) and an.conserva_valor(tipo, nuevo)


def ancho_de_temporal(ctx: Contexto) -> str | None:
    """
    Cambia el tipo entero de una variable local entre ``s32``, ``u32``, ``s16`` y ``u16``.

    Contexto:
        El ancho de una variable decide si el compilador inserta extensiones (``sll``/``sra``) y que
        instruccion de carga usa. Solo se cambia cuando el rango de todo valor que recibe cabe en
        ambos tipos y el cambio no altera el tipo de las expresiones donde se lee (o esas lecturas no
        dependen del signo).

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion, o ``None`` si ninguna variable admite el cambio.

    Ejemplo:
        descripcion = ancho_de_temporal(contexto)
    """
    candidatos: list[tuple[c.Decl, an.Tipo]] = []
    ambiguos = nombres_ambiguos(ctx.funcion)
    for _, _, sentencia in _sentencias(ctx.funcion):
        if isinstance(sentencia, c.Decl):
            permitidos = _ancho_permitido(ctx, sentencia, ambiguos)
            candidatos.extend((sentencia, nuevo) for nuevo in permitidos or [])
    elegido = _elegir(ctx.azar, candidatos)
    if elegido is None:
        return None
    declaracion, nuevo = elegido
    anterior = declaracion.base
    declaracion.base = nuevo.base
    ctx.entorno.locales[declaracion.nombre] = nuevo
    return f"ancho_temporal({declaracion.nombre}: {anterior} a {nuevo.texto})"


def copiar_parametro(ctx: Contexto) -> str | None:
    """
    Copia un parametro a una local al inicio de la funcion y usa la copia en todo el cuerpo.

    Contexto:
        Fija el registro del parametro como un temporal normal y deja libre al registro de argumento.

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion, o ``None`` si ningun parametro escalar es de solo lectura.

    Ejemplo:
        descripcion = copiar_parametro(contexto)
    """
    candidatos: list[tuple[str, an.Tipo]] = []
    ambiguos = nombres_ambiguos(ctx.funcion)
    for declarado in ctx.funcion.parametros:
        if declarado.nombre in ambiguos:
            continue
        tipo = ctx.entorno.locales.get(declarado.nombre)
        usos = _usos_de(ctx.funcion, declarado.nombre)
        escrito = any(
            sitio.lvalue or (isinstance(sitio.padre, c.Unario) and sitio.padre.op == "&") for _, sitio in usos
        )
        if tipo is not None and tipo.es_escalar and usos and not escrito:
            candidatos.append((declarado.nombre, tipo))
    elegido = _elegir(ctx.azar, candidatos)
    if elegido is None:
        return None
    parametro, tipo = elegido
    nombre = _nombre_temporal(ctx)
    for _, sitio in _usos_de(ctx.funcion, parametro):
        c.reemplazar_hijo(sitio.padre, sitio.nodo, c.Id(nombre))
    _declarar_temporal(ctx, nombre, tipo)
    cuerpo = ctx.funcion.cuerpo
    cuerpo.items.insert(
        _fin_de_declaraciones(cuerpo), c.Expresion(expr=c.Asigna("=", c.Id(nombre), c.Id(parametro)))
    )
    return f"copiar_parametro({parametro} en {nombre})"


# ---------------------------------------------------------------------------------------------------
# Expresiones
# ---------------------------------------------------------------------------------------------------


def operandos_conmutados(ctx: Contexto) -> str | None:
    """
    Intercambia los operandos de un operador conmutativo, o invierte una comparacion y los suyos.

    Contexto:
        Con operandos puros el orden no cambia el valor; cambia cual se carga primero y que registro
        recibe cada uno (el que se carga primero va a la izquierda).

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion, o ``None`` si no hay un operador aplicable con operandos puros.

    Ejemplo:
        descripcion = operandos_conmutados(contexto)
    """
    sitios = [
        sitio
        for sentencia, raiz in _todas_las_expresiones(ctx.funcion)
        for sitio in sitios_de(raiz, sentencia)
        if isinstance(sitio.nodo, c.Binario)
        and (sitio.nodo.op in OPERADORES_CONMUTATIVOS or sitio.nodo.op in RELACIONALES_INVERSOS)
        and an.es_pura(sitio.nodo)
    ]
    elegido = _elegir(ctx.azar, sitios)
    if elegido is None:
        return None
    nodo = elegido.nodo
    assert isinstance(nodo, c.Binario)  # noqa: S101
    antes = nodo.op
    nodo.izq, nodo.der = nodo.der, nodo.izq
    nodo.op = RELACIONALES_INVERSOS.get(nodo.op, nodo.op)
    return f"operandos_conmutados({antes})"


def _conversiones_de_acceso(ctx: Contexto) -> list[tuple[Sitio, c.Expr]]:
    """Pares (sitio, reemplazo equivalente) de indice a puntero y de puntero a indice."""
    pares: list[tuple[Sitio, c.Expr]] = []
    for sentencia, raiz in _todas_las_expresiones(ctx.funcion):
        for sitio in sitios_de(raiz, sentencia):
            nodo = sitio.nodo
            if isinstance(nodo, c.Indice):
                suma = c.Binario("+", copy.deepcopy(nodo.base), copy.deepcopy(nodo.indice))
                pares.append((sitio, c.Unario("*", suma)))
            elif isinstance(nodo, c.Unario) and nodo.op == "*" and isinstance(nodo.operando, c.Binario):
                suma = nodo.operando
                derecho = ctx.entorno.inferir(suma.der)
                if suma.op == "+" and not (derecho is not None and derecho.es_puntero):
                    pares.append((sitio, c.Indice(copy.deepcopy(suma.izq), copy.deepcopy(suma.der))))
            elif isinstance(nodo, c.Miembro) and nodo.flecha:
                pares.append((sitio, c.Miembro(c.Unario("*", copy.deepcopy(nodo.base)), False, nodo.campo)))
            elif (
                isinstance(nodo, c.Miembro)
                and isinstance(nodo.base, c.Unario)
                and nodo.base.op == "*"
                and not nodo.flecha
            ):
                pares.append((sitio, c.Miembro(copy.deepcopy(nodo.base.operando), True, nodo.campo)))
    return pares


def indice_o_puntero(ctx: Contexto) -> str | None:
    """
    Reescribe un acceso entre sus formas equivalentes: ``p[i]``/``*(p + i)`` y ``p->c``/``(*p).c``.

    Contexto:
        Las dos formas son identicas en C, pero el compilador las trata distinto al elegir la
        variable de induccion y el modo de direccionamiento.

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion, o ``None`` si no hay un acceso reescribible.

    Ejemplo:
        descripcion = indice_o_puntero(contexto)
    """
    elegido = _elegir(ctx.azar, _conversiones_de_acceso(ctx))
    if elegido is None:
        return None
    sitio, nuevo = elegido
    antes = an.texto_de(sitio.nodo)
    c.reemplazar_hijo(sitio.padre, sitio.nodo, nuevo)
    return f"indice_o_puntero({antes})"


# ---------------------------------------------------------------------------------------------------
# Control de flujo
# ---------------------------------------------------------------------------------------------------


def negar(condicion: c.Expr, azar: random.Random) -> c.Expr:
    """
    Construye la negacion de una condicion, empujandola hacia adentro cuando es posible.

    Contexto:
        Se usa en una posicion de verdad (``if``): ahi ``!!x`` es ``x``, una comparacion se invierte y
        De Morgan conserva el orden de evaluacion y el cortocircuito.

    Args:
        condicion (c.Expr): Condicion a negar.
        azar (random.Random): Decide si se envuelve con ``!`` en lugar de simplificar.

    Returns:
        c.Expr: Condicion contraria.

    Ejemplo:
        contraria = negar(c.Binario("<", c.Id("a"), c.Id("b")), random.Random(1))
    """
    if azar.random() < PROBABILIDAD_NEGACION_LITERAL:
        return c.Unario("!", condicion)
    if isinstance(condicion, c.Unario) and condicion.op == "!":
        return condicion.operando
    if isinstance(condicion, c.Binario) and condicion.op in NEGACION_DE_COMPARACION:
        return c.Binario(NEGACION_DE_COMPARACION[condicion.op], condicion.izq, condicion.der)
    if isinstance(condicion, c.Binario) and condicion.op in ("&&", "||"):
        contraria = "||" if condicion.op == "&&" else "&&"
        return c.Binario(contraria, negar(condicion.izq, azar), negar(condicion.der, azar))
    return c.Unario("!", condicion)


def condicion_invertida(ctx: Contexto) -> str | None:
    """
    Niega la condicion de un ``if`` con ``else`` e intercambia sus ramas.

    Contexto:
        El orden de las ramas decide cual queda como salto y cual como caida, y con ello la
        planificacion de los huecos de salto.

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion, o ``None`` si la funcion no tiene un ``if`` con ``else``.

    Ejemplo:
        descripcion = condicion_invertida(contexto)
    """
    sitios = [s for _, _, s in _sentencias(ctx.funcion) if isinstance(s, c.Si) and s.sino is not None]
    elegido = _elegir(ctx.azar, sitios)
    if elegido is None or elegido.sino is None:
        return None
    antes = an.texto_de(elegido.cond)
    elegido.cond = negar(elegido.cond, ctx.azar)
    elegido.entonces, elegido.sino = elegido.sino, elegido.entonces
    return f"condicion_invertida({antes})"


def _para_a_mientras(bloque: c.Bloque, indice: int, para: c.Para) -> None:
    """Sustituye un ``for`` por su inicio y un ``while`` con el paso al final del cuerpo."""
    nuevos: list[c.Sentencia] = []
    if para.inicio is not None:
        nuevos.append(c.Expresion(expr=para.inicio, comentarios=para.comentarios))
    cuerpo = para.cuerpo
    if para.paso is not None:
        cuerpo.items.append(c.Expresion(expr=para.paso))
    condicion = para.cond if para.cond is not None else c.Num("1")
    nuevos.append(c.Mientras(cond=condicion, cuerpo=cuerpo))
    bloque.items[indice : indice + 1] = nuevos


def _mientras_a_para(bloque: c.Bloque, indice: int, mientras: c.Mientras, azar: random.Random) -> None:
    """Sustituye un ``while`` por un ``for``; con probabilidad 1/2 su ultima sentencia pasa a ser el paso."""
    cuerpo = mientras.cuerpo
    paso = None
    ultima = cuerpo.items[-1] if cuerpo.items else None
    if isinstance(ultima, c.Expresion) and not ultima.comentarios and azar.random() < 0.5:
        paso = ultima.expr
        cuerpo.items.pop()
    bloque.items[indice] = c.Para(None, mientras.cond, paso, cuerpo, comentarios=mientras.comentarios)


def bucle_for_o_while(ctx: Contexto) -> str | None:
    """
    Cambia un bucle ``for`` por ``while`` o un ``while`` por ``for``.

    Contexto:
        El compilador analiza ambos igual en teoria; en la practica la posicion de la inicializacion
        y del paso cambia la numeracion de pseudoregistros. Un bucle con ``continue`` propio no se
        toca: en la forma ``while`` el ``continue`` se saltaria el paso.

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion, o ``None`` si no hay un bucle convertible.

    Ejemplo:
        descripcion = bucle_for_o_while(contexto)
    """
    candidatos = [
        (bloque, indice, sentencia)
        for bloque, indice, sentencia in _sentencias(ctx.funcion)
        if isinstance(sentencia, c.Para | c.Mientras) and not _contiene_continuar(sentencia.cuerpo)
    ]
    elegido = _elegir(ctx.azar, candidatos)
    if elegido is None:
        return None
    bloque, indice, sentencia = elegido
    if isinstance(sentencia, c.Para):
        _para_a_mientras(bloque, indice, sentencia)
        return "bucle(for a while)"
    assert isinstance(sentencia, c.Mientras)  # noqa: S101
    _mientras_a_para(bloque, indice, sentencia, ctx.azar)
    return "bucle(while a for)"


# ---------------------------------------------------------------------------------------------------
# Asignaciones compuestas
# ---------------------------------------------------------------------------------------------------

OPERADORES_COMPUESTOS = frozenset({"+", "-", "|", "&", "^", "<<", ">>"})
OPERADORES_COMPUESTOS_CONMUTATIVOS = frozenset({"+", "|", "&", "^"})
FORMA_EXPANDIR = "expandir"
FORMA_COMPONER_IZQ = "componer_izq"
FORMA_COMPONER_DER = "componer_der"


def _es_destino_de_asignacion(expr: c.Expr) -> bool:
    """Un destino admite la forma compuesta si es una variable, un campo, un indice o ``*p``."""
    return isinstance(expr, c.Id | c.Miembro | c.Indice) or (isinstance(expr, c.Unario) and expr.op == "*")


def _forma_de_composicion(asignacion: c.Asigna) -> str | None:
    """Forma en que una asignacion simple ``x = x op e`` se compone, o ``None`` si no tiene esa forma."""
    valor = asignacion.valor
    if not (isinstance(valor, c.Binario) and valor.op in OPERADORES_COMPUESTOS and an.es_pura(valor)):
        return None
    destino = an.texto_de(asignacion.destino)
    if an.texto_de(valor.izq) == destino:
        return FORMA_COMPONER_IZQ
    if valor.op in OPERADORES_COMPUESTOS_CONMUTATIVOS and an.texto_de(valor.der) == destino:
        return FORMA_COMPONER_DER
    return None


def _formas_de_asignacion(ctx: Contexto) -> list[tuple[c.Asigna, str]]:
    """Asignaciones de la funcion que tienen una forma equivalente, con la forma a la que pasan."""
    formas: list[tuple[c.Asigna, str]] = []
    for sentencia, raiz in _todas_las_expresiones(ctx.funcion):
        for sitio in sitios_de(raiz, sentencia):
            nodo = sitio.nodo
            if not (
                isinstance(nodo, c.Asigna)
                and _es_destino_de_asignacion(nodo.destino)
                and an.es_pura(nodo.destino)
            ):
                continue
            if nodo.op == "=":
                forma = _forma_de_composicion(nodo)
            else:
                forma = (
                    FORMA_EXPANDIR
                    if nodo.op[:-1] in OPERADORES_COMPUESTOS and an.es_pura(nodo.valor)
                    else None
                )
            if forma is not None:
                formas.append((nodo, forma))
    return formas


def asignacion_compuesta(ctx: Contexto) -> str | None:
    """
    Pasa una asignacion entre ``x = x op e`` y ``x op= e`` para ``+ - | & ^ << >>``.

    Contexto:
        Con ``x op= e`` el compilador carga ``x`` una sola vez y conserva el valor en el registro del
        resultado; con ``x = x op e`` en dos sentencias separadas (una de las formas de partida del
        banderin ``|= a ... &= m``) deja una copia ``move`` entre registros. Las dos formas son la
        misma expresion en C: solo se aplican si el destino ``x`` y el operando ``e`` son puros
        (sin llamadas, asignaciones ni incrementos), de modo que ``x`` se evalua una vez en cualquiera
        de las dos y el orden de evaluacion de los operandos no importa. En los operadores
        conmutativos tambien se reconoce ``x = e op x``. Los operadores ``* / %`` no se tocan.

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion, o ``None`` si la funcion no tiene una asignacion en ninguna de las dos
        formas con destino y operando puros.

    Ejemplo:
        descripcion = asignacion_compuesta(contexto)
    """
    elegido = _elegir(ctx.azar, _formas_de_asignacion(ctx))
    if elegido is None:
        return None
    nodo, forma = elegido
    antes = an.texto_de(nodo)
    if forma == FORMA_EXPANDIR:
        nodo.valor = c.Binario(nodo.op[:-1], copy.deepcopy(nodo.destino), nodo.valor)
        nodo.op = "="
    else:
        valor = nodo.valor
        assert isinstance(valor, c.Binario)  # noqa: S101 - ``_forma_de_composicion`` lo garantiza
        nodo.op = f"{valor.op}="
        nodo.valor = valor.der if forma == FORMA_COMPONER_IZQ else valor.izq
    return f"asignacion_compuesta({antes})"


# ---------------------------------------------------------------------------------------------------
# Locales: lectura anticipada, relectura, union y particion
# ---------------------------------------------------------------------------------------------------

DISTANCIA_MAXIMA_DE_LECTURA = 8


def _anidadas(sentencia: c.Sentencia) -> Iterator[c.Sentencia]:
    """Una sentencia y todas las que contiene, en orden de aparicion."""
    yield sentencia
    for bloque in c.bloques_hijos(sentencia):
        for interna in bloque.items:
            yield from _anidadas(interna)


def _nombres_en(sentencia: c.Sentencia) -> set[str]:
    """Identificadores que menciona una sentencia y lo que contiene; una declaracion con inicial cuenta."""
    nombres: set[str] = set()
    for interna in _anidadas(sentencia):
        if isinstance(interna, c.Decl) and interna.inicial is not None:
            nombres.add(interna.nombre)
        for raiz in c.expresiones_de(interna):
            nombres |= an.identificadores_de(raiz)
    return nombres


def _renombrar_en(sentencias: list[c.Sentencia], viejo: str, nuevo: str) -> None:
    """Cambia ``viejo`` por ``nuevo`` en cada aparicion de la variable dentro de las sentencias."""
    for sentencia in sentencias:
        for interna in _anidadas(sentencia):
            for raiz in c.expresiones_de(interna):
                for nodo in c.recorrer(raiz):
                    if isinstance(nodo, c.Id) and nodo.nombre == viejo:
                        nodo.nombre = nuevo


def _asigna_antes_de_leer(sentencia: c.Sentencia, nombre: str) -> bool:
    """La sentencia da valor a la variable sin leerla: ``x = e`` o ``for (x = e; ...)`` ``e`` sin ``x``."""
    expr = sentencia.expr if isinstance(sentencia, c.Expresion) else None
    if isinstance(sentencia, c.Para):
        expr = sentencia.inicio
    return (
        isinstance(expr, c.Asigna)
        and expr.op == "="
        and isinstance(expr.destino, c.Id)
        and expr.destino.nombre == nombre
        and nombre not in an.identificadores_de(expr.valor)
    )


def _empieza_asignando(sentencias: list[c.Sentencia], nombre: str) -> bool:
    """La primera sentencia que menciona la variable le da valor antes de leerla."""
    primera = next((s for s in sentencias if nombre in _nombres_en(s)), None)
    return primera is not None and _asigna_antes_de_leer(primera, nombre)


def _nombres_vedados(ctx: Contexto) -> set[str]:
    """Variables que las mutaciones de locales no tocan: ambiguas, con direccion tomada o parametros."""
    con_direccion = {ubicacion[2:] for ubicacion in _locales_con_direccion(ctx.funcion)}
    return nombres_ambiguos(ctx.funcion) | con_direccion | ctx.entorno.parametros


def _declaraciones_simples(ctx: Contexto) -> dict[str, tuple[c.Bloque, c.Decl]]:
    """Declaraciones de variables escalares o agregadas sin declarador, con su bloque, por nombre."""
    vedados = _nombres_vedados(ctx)
    simples: dict[str, tuple[c.Bloque, c.Decl]] = {}
    for bloque in c.todos_los_bloques(ctx.funcion.cuerpo):
        for sentencia in bloque.items:
            esta_permitida = (
                isinstance(sentencia, c.Decl)
                and not sentencia.sufijo
                and not sentencia.declarador
                and sentencia.nombre not in vedados
            )
            if isinstance(sentencia, c.Decl) and esta_permitida:
                simples[sentencia.nombre] = (bloque, sentencia)
    return simples


def _declarar_como(ctx: Contexto, nombre: str, modelo: c.Decl) -> None:
    """Declara ``nombre`` al inicio de la funcion con el mismo tipo que ``modelo``."""
    cuerpo = ctx.funcion.cuerpo
    cuerpo.items.insert(_fin_de_declaraciones(cuerpo), c.Decl(modelo.base, modelo.estrellas, nombre))
    ctx.entorno.locales[nombre] = ctx.entorno.locales.get(
        modelo.nombre, an.parsear_tipo(modelo.base, modelo.estrellas)
    )


# --- lectura anticipada de un campo --------------------------------------------------------------------


def _posiciones_de_lectura(
    ctx: Contexto, bloque: c.Bloque, indice: int, carga: c.Expr, memoria: dict[int, an.Efectos]
) -> list[int]:
    """
    Posiciones del bloque donde se puede leer ``carga`` en lugar de en la sentencia ``indice``.

    Se sube sentencia a sentencia mientras ninguna de las que se cruzan (con todo lo que contienen)
    escriba lo que la carga lee ni sea una barrera, sin pasar de la serie de declaraciones del bloque
    ni de ``DISTANCIA_MAXIMA_DE_LECTURA`` sentencias. ``memoria`` guarda los efectos ya calculados de
    cada sentencia (por identidad) para no recorrerla otra vez en cada candidato.
    """
    lectura = an.efectos_de(c.Expresion(expr=carga), ctx.alias)
    piso = max(_fin_de_declaraciones(bloque), indice - DISTANCIA_MAXIMA_DE_LECTURA)
    posiciones = [indice]
    posicion = indice
    while posicion > piso:
        vecina = bloque.items[posicion - 1]
        efectos = memoria.setdefault(id(vecina), an.efectos_profundos(vecina, ctx.alias))
        if an.escritura_alcanza(efectos, lectura):
            break
        posicion -= 1
        posiciones.append(posicion)
    return posiciones


def _cargas_adelantables(ctx: Contexto) -> list[tuple[c.Bloque, int, Sitio, an.Tipo, int]]:
    """Accesos escalares a campo o indice con cada posicion anterior donde se pueden leer."""
    vedados = _nombres_vedados(ctx) - ctx.entorno.parametros
    candidatos: list[tuple[c.Bloque, int, Sitio, an.Tipo, int]] = []
    memoria: dict[int, an.Efectos] = {}
    for bloque, indice, sentencia in _sentencias(ctx.funcion):
        if not isinstance(sentencia, c.Expresion | c.Devolver | c.Si | c.Seleccion):
            continue
        for raiz in c.expresiones_de(sentencia):
            if not _aparicion_unica_de_asignacion(raiz):
                continue
            for sitio in sitios_de(raiz, sentencia):
                tipo = ctx.entorno.inferir(sitio.nodo)
                es_carga = (
                    isinstance(sitio.nodo, c.Miembro | c.Indice)
                    and tipo is not None
                    and tipo.es_escalar
                    and not sitio.perezoso
                    and not sitio.lvalue
                    and an.es_pura(sitio.nodo)
                    and not an.identificadores_de(sitio.nodo) & vedados
                )
                if es_carga and tipo is not None:
                    candidatos.extend(
                        (bloque, indice, sitio, tipo, posicion)
                        for posicion in _posiciones_de_lectura(ctx, bloque, indice, sitio.nodo, memoria)
                    )
    return candidatos


def local_de_campo(ctx: Contexto) -> str | None:
    """
    Lee un campo o un elemento en una local nueva, asignada en una sentencia anterior del mismo bloque.

    Contexto:
        Cuando el original carga un valor antes de tocar otros (por ejemplo el tipo de una orden antes
        de modificar las banderas del objeto), la carga es la primera del bloque y el valor ocupa un
        registro propio durante todo el tramo; leerlo donde se usa lo carga mas tarde y con otro
        registro. La lectura solo sube por encima de sentencias que, con todo lo que contienen, no
        escriben esa memoria (ruta de campo solapada, escritura por puntero opaco o cambio de una
        variable de la direccion) y no hacen llamadas ni saltos. Se diferencia de
        ``introducir_temporal`` en que la sentencia que sube puede cruzar un ``if`` o un bucle que no
        toca la memoria y en que cada posicion posible es una variante distinta. La local es siempre
        nueva y del tipo exacto del campo, y las sentencias de usos con efectos propios se excluyen.

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion, o ``None`` si ninguna lectura escalar se puede adelantar.

    Ejemplo:
        descripcion = local_de_campo(contexto)
    """
    elegido = _elegir(ctx.azar, _cargas_adelantables(ctx))
    if elegido is None:
        return None
    bloque, indice, sitio, tipo, posicion = elegido
    sentencia = bloque.items[indice]
    nombre = _nombre_temporal(ctx)
    clave = an.texto_de(sitio.nodo)
    copia = copy.deepcopy(sitio.nodo)
    if ctx.azar.random() < PROBABILIDAD_TODAS_LAS_APARICIONES:
        for raiz in c.expresiones_de(sentencia):
            for otro in list(sitios_de(raiz, sentencia)):
                if not otro.lvalue and not otro.perezoso and an.texto_de(otro.nodo) == clave:
                    c.reemplazar_hijo(otro.padre, otro.nodo, c.Id(nombre))
    else:
        c.reemplazar_hijo(sitio.padre, sitio.nodo, c.Id(nombre))
    bloque.items.insert(posicion, c.Expresion(expr=c.Asigna("=", c.Id(nombre), copia)))
    _declarar_temporal(ctx, nombre, tipo)
    return f"local_de_campo({tipo.texto} {nombre} = {clave}, {indice - posicion} antes)"


# --- relectura en la condicion de un bucle -------------------------------------------------------------


def _carga_de_memoria(expr: c.Expr) -> bool:
    """Una expresion pura que lee memoria: contiene un campo, un indice o una desreferencia."""
    es_acceso = any(
        isinstance(n, c.Miembro | c.Indice) or (isinstance(n, c.Unario) and n.op == "*")
        for n in c.recorrer(expr)
    )
    return es_acceso and an.es_pura(expr)


def _asignacion_unica_de_local(
    sentencia: c.Sentencia, declaraciones: dict[str, tuple[c.Bloque, c.Decl]]
) -> tuple[str, c.Expr] | None:
    """Nombre y fuente si la sentencia da su unico valor a una local simple: ``x = e;`` o ``T x = e;``."""
    if isinstance(sentencia, c.Decl):
        if sentencia.inicial is not None and sentencia.nombre in declaraciones:
            return sentencia.nombre, sentencia.inicial
        return None
    if (
        isinstance(sentencia, c.Expresion)
        and isinstance(sentencia.expr, c.Asigna)
        and sentencia.expr.op == "="
        and isinstance(sentencia.expr.destino, c.Id)
        and sentencia.expr.destino.nombre in declaraciones
        and declaraciones[sentencia.expr.destino.nombre][1].inicial is None
    ):
        return sentencia.expr.destino.nombre, sentencia.expr.valor
    return None


def _es_uso_en_condicion_de_bucle(sentencia: c.Sentencia, nodo: c.Expr) -> bool:
    """El nodo forma parte de la condicion de un ``while``, ``do`` o ``for``."""
    if not isinstance(sentencia, c.Mientras | c.HacerMientras | c.Para) or sentencia.cond is None:
        return False
    return any(hijo is nodo for hijo in c.recorrer(sentencia.cond))


def _lecturas_de_local_guardada(
    ctx: Contexto, bloque: c.Bloque, indice: int, nombre: str, fuente: c.Expr
) -> list[Sitio] | None:
    """
    Lecturas de una local que se pueden sustituir por su fuente, o ``None`` si no se puede.

    Todas las apariciones deben ser lecturas posteriores a la asignacion y del mismo bloque, al menos
    una debe estar en la condicion de un bucle y nada de lo que hay entre la asignacion y la ultima
    lectura (bucles enteros incluidos) puede escribir lo que la fuente lee.
    """
    sentencia = bloque.items[indice]
    usos = _usos_de(ctx.funcion, nombre)
    escrituras = [sitio for _, sitio in usos if sitio.lvalue]
    lecturas = [(s, sitio) for s, sitio in usos if not sitio.lvalue]
    if len(escrituras) != (0 if isinstance(sentencia, c.Decl) else 1) or not lecturas:
        return None
    posteriores = bloque.items[indice + 1 :]
    posicion_de = {id(interna): j for j, s in enumerate(posteriores) for interna in _anidadas(s)}
    if any(id(s) not in posicion_de for s, _ in lecturas):
        return None
    if not any(_es_uso_en_condicion_de_bucle(s, sitio.nodo) for s, sitio in lecturas):
        return None
    lectura = an.efectos_de(c.Expresion(expr=fuente), ctx.alias)
    ultima = max(posicion_de[id(s)] for s, _ in lecturas)
    for intermedia in posteriores[: ultima + 1]:
        if an.escritura_alcanza(an.efectos_profundos(intermedia, ctx.alias), lectura):
            return None
    return [sitio for _, sitio in lecturas]


def _lecturas_releibles(ctx: Contexto) -> list[tuple[c.Bloque, int, str, c.Expr, list[Sitio]]]:
    """Locales de una sola asignacion desde memoria cuyas lecturas se pueden volver a hacer en su sitio."""
    declaraciones = _declaraciones_simples(ctx)
    vedados = _nombres_vedados(ctx) - ctx.entorno.parametros
    resultado: list[tuple[c.Bloque, int, str, c.Expr, list[Sitio]]] = []
    for bloque, indice, sentencia in _sentencias(ctx.funcion):
        asignacion = _asignacion_unica_de_local(sentencia, declaraciones)
        if asignacion is None or sentencia.comentarios:
            continue
        nombre, fuente = asignacion
        origen, destino = ctx.entorno.inferir(fuente), ctx.entorno.locales.get(nombre)
        compatible = (
            origen is not None
            and destino is not None
            and an.promover(origen) == an.promover(destino)
            and (origen.texto == destino.texto or an.conserva_valor(origen, destino))
        )
        identificadores = an.identificadores_de(fuente)
        if not (
            compatible
            and _carga_de_memoria(fuente)
            and nombre not in identificadores
            and not identificadores & vedados
        ):
            continue
        sitios = _lecturas_de_local_guardada(ctx, bloque, indice, nombre, fuente)
        if sitios is not None:
            resultado.append((bloque, indice, nombre, fuente, sitios))
    return resultado


def releer_en_condicion(ctx: Contexto) -> str | None:
    """
    Sustituye una local que guarda una lectura de memoria por esa lectura en cada uso.

    Contexto:
        Si la cuenta de un bucle se guarda en una local, el compilador la carga una vez y la conserva en
        un registro con una copia; si se relee en la condicion, la carga de la guarda del bucle y la
        de la condicion se funden y la copia desaparece. Es la operacion inversa de guardar una
        lectura en una local. Solo se aplica a una local asignada una vez desde una expresion pura que
        lee memoria, con todas sus lecturas posteriores en el mismo bloque, al menos una en la condicion
        de un bucle y sin ninguna escritura que llegue a esa memoria (ni llamada) entre la asignacion y
        la ultima lectura, cuerpos de bucle incluidos. La local y su declaracion desaparecen.

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion, o ``None`` si ninguna local cumple las condiciones.

    Ejemplo:
        descripcion = releer_en_condicion(contexto)
    """
    elegido = _elegir(ctx.azar, _lecturas_releibles(ctx))
    if elegido is None:
        return None
    bloque, indice, nombre, fuente, sitios = elegido
    for sitio in sitios:
        c.reemplazar_hijo(sitio.padre, sitio.nodo, copy.deepcopy(fuente))
    # Primero la asignacion: quitar antes la declaracion del mismo bloque desplazaria su posicion.
    asignacion = bloque.items.pop(indice)
    if not isinstance(asignacion, c.Decl):
        _quitar_declaracion(ctx.funcion, nombre)
    ctx.entorno.locales.pop(nombre, None)
    return f"releer_en_condicion({nombre} = {an.texto_de(fuente)})"


# --- union de dos locales de vidas disjuntas -----------------------------------------------------------


def _locales_unificables(ctx: Contexto) -> list[tuple[str, str]]:
    """
    Pares (primera, segunda) de locales del mismo tipo cuyas vidas no se solapan.

    La vida de una local es el conjunto de sentencias del cuerpo (con todo lo que contienen) que la
    mencionan. La segunda se funde en la primera si todas las sentencias de la primera terminan antes
    de la primera de la segunda, y esa primera sentencia le da valor antes de leerla. Una funcion con
    ``goto`` o etiquetas no se toca: un salto hacia atras alargaria la vida de la primera.
    """
    funcion = ctx.funcion
    cuerpo = funcion.cuerpo
    if any(isinstance(s, c.Etiqueta | c.Saltar) for _, _, s in _sentencias(funcion)):
        return []
    declaraciones = _declaraciones_simples(ctx)
    del_cuerpo = {s.nombre for s in cuerpo.items if isinstance(s, c.Decl)}
    menciones = [_nombres_en(s) for s in cuerpo.items]
    pares: list[tuple[str, str]] = []
    for primera, (_, decl_primera) in declaraciones.items():
        for segunda, (_, decl_segunda) in declaraciones.items():
            if (
                primera == segunda
                or primera not in del_cuerpo
                or decl_segunda.inicial is not None
                or (decl_primera.base, decl_primera.estrellas) != (decl_segunda.base, decl_segunda.estrellas)
            ):
                continue
            en_primera = [i for i, nombres in enumerate(menciones) if primera in nombres]
            en_segunda = [i for i, nombres in enumerate(menciones) if segunda in nombres]
            if (
                en_primera
                and en_segunda
                and max(en_primera) < min(en_segunda)
                and _asigna_antes_de_leer(cuerpo.items[min(en_segunda)], segunda)
            ):
                pares.append((primera, segunda))
    return pares


def unificar_locales(ctx: Contexto) -> str | None:
    """
    Funde dos locales del mismo tipo de vidas disjuntas en una sola.

    Contexto:
        Con una variable menos el compilador numera distinto los pseudoregistros y reparte de otro modo
        los registros salvados: dos contadores de bucles consecutivos pasan a ser el mismo registro.
        Se funde la segunda en la primera cuando todas las sentencias del cuerpo que mencionan la
        primera terminan antes de la primera que menciona la segunda, la segunda se asigna antes de
        leerse en su primera sentencia (una asignacion o el inicio de un ``for``), las dos tienen el mismo
        tipo, ninguna tiene direccion tomada, es parametro o nombre ambiguo, la primera esta
        declarada en el cuerpo de la funcion (para ser visible en todo el tramo) y la segunda no
        tiene inicializador. Se renombran las apariciones de la segunda y se retira su declaracion.

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion, o ``None`` si ningun par de locales cumple las condiciones.

    Ejemplo:
        descripcion = unificar_locales(contexto)
    """
    elegido = _elegir(ctx.azar, _locales_unificables(ctx))
    if elegido is None:
        return None
    primera, segunda = elegido
    _renombrar_en(ctx.funcion.cuerpo.items, segunda, primera)
    _quitar_declaracion(ctx.funcion, segunda)
    ctx.entorno.locales.pop(segunda, None)
    return f"unificar_locales({segunda} en {primera})"


# --- particion de una local compartida entre ramas -----------------------------------------------------


def _ramas_de_si(si: c.Si) -> list[list[c.Sentencia]]:
    """Cuerpos de las ramas de un ``if`` y de su cadena ``else if`` (como las escribe el escritor de C)."""
    ramas = [si.entonces.items]
    actual = si
    while actual.sino is not None:
        sino = actual.sino
        unico = sino.items[0] if len(sino.items) == 1 else None
        if isinstance(unico, c.Si) and not unico.comentarios and not sino.finales:
            actual = unico
            ramas.append(actual.entonces.items)
        else:
            ramas.append(sino.items)
            break
    return ramas


def _segmentos_de_seleccion(seleccion: c.Seleccion) -> list[list[c.Sentencia]]:
    """Sentencias que siguen a cada ``case`` o ``default`` de un ``switch`` (el primer segmento es previo)."""
    segmentos: list[list[c.Sentencia]] = [[]]
    for sentencia in seleccion.cuerpo.items:
        if isinstance(sentencia, c.Caso):
            segmentos.append([])
        else:
            segmentos[-1].append(sentencia)
    return segmentos


def _ramas_independientes(sentencia: c.Sentencia, nombre: str) -> list[list[c.Sentencia]] | None:
    """
    Ramas de un ``if`` o ``switch`` que mencionan la variable, o ``None`` si no se puede partir.

    Cada rama que la menciona debe empezar dandole valor; en un ``switch`` toda rama que la menciona,
    salvo la ultima, debe terminar en ``break`` o ``return`` (si no, caeria en la siguiente).
    """
    if isinstance(sentencia, c.Si):
        ramas = _ramas_de_si(sentencia)
    elif isinstance(sentencia, c.Seleccion):
        ramas = _segmentos_de_seleccion(sentencia)
    else:
        return None
    con_nombre = [rama for rama in ramas if any(nombre in _nombres_en(s) for s in rama)]
    if len(con_nombre) < 2 or not all(_empieza_asignando(rama, nombre) for rama in con_nombre):
        return None
    if isinstance(sentencia, c.Seleccion) and not all(
        rama and isinstance(rama[-1], c.Romper | c.Devolver) for rama in con_nombre[:-1]
    ):
        return None
    return con_nombre


def _locales_partibles(ctx: Contexto) -> list[tuple[str, list[list[c.Sentencia]]]]:
    """Variables locales cuyas apariciones estan todas en dos o mas ramas independientes de una sentencia."""
    resultado: list[tuple[str, list[list[c.Sentencia]]]] = []
    declaraciones = _declaraciones_simples(ctx)
    total = {
        nombre: len(_usos_de(ctx.funcion, nombre))
        for nombre, (_, d) in declaraciones.items()
        if not d.inicial
    }
    for _, _, sentencia in _sentencias(ctx.funcion):
        for nombre, cantidad in total.items():
            ramas = _ramas_independientes(sentencia, nombre)
            if ramas is None:
                continue
            dentro = sum(
                1
                for rama in ramas
                for s in rama
                for interna in _anidadas(s)
                for raiz in c.expresiones_de(interna)
                for nodo in c.recorrer(raiz)
                if isinstance(nodo, c.Id) and nodo.nombre == nombre
            )
            if dentro == cantidad:
                resultado.append((nombre, ramas))
    return resultado


def partir_local(ctx: Contexto) -> str | None:
    """
    Reparte una local usada en varias ramas de un ``if`` o ``switch`` en una local por rama.

    Contexto:
        Operacion inversa de ``unificar_locales``: una variable compartida por ramas excluyentes se
        reparte en un registro comun para todas; con una local por rama cada una vive solo en su
        tramo y el compilador la numera y la reparte aparte. Solo se parte una local sin
        inicializador, sin direccion tomada, cuyas apariciones estan todas dentro de las ramas de una
        misma sentencia (ni en sus condiciones ni fuera de ella), con dos o mas ramas que la mencionen
        y cada una empezando por darle valor. La primera rama conserva el nombre; las demas usan locales
        nuevas del mismo tipo con el nombre ``tmpN``.

    Args:
        ctx (Contexto): Contexto de la ronda.

    Returns:
        str | None: Descripcion, o ``None`` si ninguna local es partible.

    Ejemplo:
        descripcion = partir_local(contexto)
    """
    elegido = _elegir(ctx.azar, _locales_partibles(ctx))
    if elegido is None:
        return None
    nombre, ramas = elegido
    modelo = _declaraciones_simples(ctx)[nombre][1]
    nuevos: list[str] = []
    for rama in ramas[1:]:
        nuevo = _nombre_temporal(ctx)
        _renombrar_en(rama, nombre, nuevo)
        _declarar_como(ctx, nuevo, modelo)
        nuevos.append(nuevo)
    return f"partir_local({nombre} en {', '.join(nuevos)})"


# ---------------------------------------------------------------------------------------------------
# Orquestacion
# ---------------------------------------------------------------------------------------------------

Mutacion = Callable[[Contexto], str | None]
MUTACIONES: tuple[tuple[str, Mutacion, float], ...] = (
    ("orden_sentencias", orden_de_sentencias, 3.0),
    ("orden_declaraciones", orden_de_declaraciones, 2.0),
    ("introducir_temporal", introducir_temporal, 4.0),
    ("eliminar_temporal", eliminar_temporal, 2.0),
    ("ancho_temporal", ancho_de_temporal, 2.0),
    ("copiar_parametro", copiar_parametro, 1.0),
    ("operandos_conmutados", operandos_conmutados, 3.0),
    ("indice_o_puntero", indice_o_puntero, 2.0),
    ("condicion_invertida", condicion_invertida, 2.0),
    ("bucle", bucle_for_o_while, 1.5),
    ("asignacion_compuesta", asignacion_compuesta, 2.0),
    ("local_de_campo", local_de_campo, 3.0),
    ("releer_en_condicion", releer_en_condicion, 1.5),
    ("unificar_locales", unificar_locales, 1.5),
    ("partir_local", partir_local, 1.5),
)
INTENTOS_POR_MUTACION = 12
MAX_VECINOS_POR_MUTACION = 5000


def mutar(
    base: c.Funcion, tabla: an.TablaTipos, azar: random.Random, cantidad: int
) -> tuple[c.Funcion, list[str]]:
    """
    Aplica ``cantidad`` mutaciones al azar a una copia de la funcion.

    Contexto:
        Es lo que el motor de busqueda llama para generar cada variante. Una mutacion que no
        encuentra un sitio aplicable se sustituye por otra; si tras ``INTENTOS_POR_MUTACION`` intentos por
        mutacion no se logra la cantidad pedida, se devuelven las que se pudieron aplicar.

    Args:
        base (c.Funcion): Funcion de partida (no se modifica).
        tabla (an.TablaTipos): Tipos de campos y globales.
        azar (random.Random): Generador de numeros aleatorios.
        cantidad (int): Mutaciones a aplicar.

    Returns:
        tuple[c.Funcion, list[str]]: La funcion mutada y la descripcion de cada mutacion aplicada.

    Ejemplo:
        variante, aplicadas = mutar(base, tabla, random.Random(7), 2)
    """
    funcion = copy.deepcopy(base)
    ctx = Contexto(funcion, an.Entorno(tabla, funcion), azar, _nombres_de(funcion))
    operadores = [m[1] for m in MUTACIONES]
    pesos = [m[2] for m in MUTACIONES]
    aplicadas: list[str] = []
    intentos = 0
    while len(aplicadas) < cantidad and intentos < cantidad * INTENTOS_POR_MUTACION:
        intentos += 1
        descripcion = azar.choices(operadores, weights=pesos)[0](ctx)
        if descripcion is not None:
            aplicadas.append(descripcion)
    return funcion, aplicadas


class _Enumerador(random.Random):
    """Generador que no sortea: toma siempre el elemento ``indice`` y fija los valores de ``random()``."""

    def __init__(self, indice: int, valores: tuple[float, ...]) -> None:
        super().__init__(0)
        self.indice = indice
        self.valores = valores
        self.llamadas = 0
        self.total = 0

    def random(self) -> float:
        """Devuelve los valores fijados, uno por llamada y en orden."""
        valor = self.valores[self.llamadas % len(self.valores)]
        self.llamadas += 1
        return valor

    def choice(self, seq: Any) -> Any:  # noqa: ANN401 - misma firma que ``random.Random.choice``
        """Devuelve el elemento ``indice`` (o el ultimo) y anota cuantos habia."""
        self.total = max(self.total, len(seq))
        return seq[min(self.indice, len(seq) - 1)]


def vecinos(base: c.Funcion, tabla: an.TablaTipos) -> Iterator[tuple[c.Funcion, str]]:
    """
    Enumera, una a una, todas las variantes que resultan de aplicar UNA mutacion a la funcion.

    Contexto:
        El sorteo al azar tarda mucho en dar con una reformulacion concreta cuando hay cientos de
        sitios candidatos (una mejora de una sola mutacion puede tener una probabilidad del 0,1 %
        por variante). Recorrer el vecindario completo antes de sortear garantiza hallar cualquier
        mejora que esta a una mutacion del C original. Las dos decisiones aleatorias que toman las
        mutaciones (una u otra variante, y la posicion de un temporal) se enumeran con los valores 0 y 0,99.

    Args:
        base (c.Funcion): Funcion de partida (no se modifica).
        tabla (an.TablaTipos): Tipos de campos y globales.

    Yields:
        tuple[c.Funcion, str]: Una copia mutada y la descripcion de su mutacion; puede haber repetidas.

    Ejemplo:
        for variante, descripcion in vecinos(base, tabla):
            ...
    """
    for _, mutacion, _ in MUTACIONES:
        for valores in itertools.product((0.0, 0.99), repeat=2):
            indice = 0
            while indice < MAX_VECINOS_POR_MUTACION:
                funcion = copy.deepcopy(base)
                azar = _Enumerador(indice, valores)
                ctx = Contexto(funcion, an.Entorno(tabla, funcion), azar, _nombres_de(funcion))
                descripcion = mutacion(ctx)
                if descripcion is None:
                    break
                yield funcion, descripcion
                indice += 1
                if indice >= azar.total:
                    break


def contar_prohibidos(texto: str) -> list[int]:
    """
    Cuenta las apariciones de cada construccion que el proyecto no admite como estado final.

    Contexto:
        Base de ``variante_permitida``: ensamblador en linea, ``volatile``, ``register`` y ``GLOBAL_ASM``.

    Args:
        texto (str): Texto C.

    Returns:
        list[int]: Una cantidad por patron de ``PATRONES_PROHIBIDOS``, sin contar comentarios ni cadenas.

    Ejemplo:
        cantidades = contar_prohibidos("volatile int x;")
    """
    limpio = c.enmascarar(texto)
    return [len(patron.findall(limpio)) for patron in PATRONES_PROHIBIDOS]


def variante_permitida(texto_variante: str, texto_base: str) -> bool:
    """
    Indica si una variante cumple las reglas del proyecto respecto al C de partida.

    Contexto:
        Filtro final del motor: una variante que tenga mas apariciones de ``__asm__``, ``asm(``,
        ``volatile``, ``register`` o ``GLOBAL_ASM`` que el C de partida se descarta sin compilarla.

    Args:
        texto_variante (str): C de la variante.
        texto_base (str): C de partida.

    Returns:
        bool: Verdadero si ninguna construccion prohibida aumenta.

    Ejemplo:
        permitida = variante_permitida(variante, base)
    """
    return all(
        v <= b for v, b in zip(contar_prohibidos(texto_variante), contar_prohibidos(texto_base), strict=True)
    )

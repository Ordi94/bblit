"""Analisis semantico minimo del C de una funcion: tipos y efectos de las expresiones.

Las mutaciones del permutador solo son validas si no cambian lo que la funcion calcula. Este modulo
responde las dos preguntas de las que depende esa garantia: de que tipo es una expresion (para
declarar un temporal exacto o para ensanchar una variable sin perder valores) y que lee y que escribe
una sentencia (para saber si dos sentencias se pueden intercambiar). Todo es conservador: ante la
duda devuelve ``None`` o declara una dependencia, y la mutacion se descarta.

Hipotesis de aliasing declarada: dos accesos a memoria con rutas de campo distintas (``a->x`` y
``b->y``) no se solapan. Las rutas iguales, las que son prefijo una de otra, los accesos por indice o
por puntero sin campo (``p[i]``, ``*p``) y cualquier llamada se tratan como dependientes. La excepcion a
la primera regla son las ``union``: dos campos de una misma union, con nombre o anonima, son el mismo
almacenamiento aunque se llamen distinto, y una ruta que nombra la union entera o la estructura que la
contiene ya es prefijo de la de sus miembros. Limite conocido: los campos de una estructura anonima
dentro de una union no se funden con los demas miembros de esa union.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from psxdecomp.permutador import c

ANCHOS_ENTEROS = {"s8": (8, True), "u8": (8, False), "s16": (16, True), "u16": (16, False)}
ANCHOS_ENTEROS |= {"s32": (32, True), "u32": (32, False), "char": (8, True), "short": (16, True)}
ANCHOS_ENTEROS |= {"int": (32, True), "long": (32, True)}
CALIFICADORES = frozenset({"const", "volatile", "register", "static", "extern"})
CAMPO_DE_BITS = "*"
COMODIN = "[]"
SIN_ALIAS: Mapping[str, str] = MappingProxyType({})
_PATRON_DECLARACION = re.compile(
    r"^[ \t]+((?:(?:unsigned|signed|const|struct)\s+)*[A-Za-z_]\w*(?:\s+(?:int|char|short|long))?)\s*"
    r"(\**)\s*([A-Za-z_]\w*(?:\s*\[[^\]]*\])*(?:\s*,\s*\**\s*[A-Za-z_]\w*(?:\s*\[[^\]]*\])*)*)\s*;",
    re.MULTILINE,
)
_PATRON_ESTRUCTURA = re.compile(r"\b(struct|union)\s*([A-Za-z_]\w*)?\s*\{")
_PATRON_CAMPO = re.compile(
    r"^\s*((?:(?:unsigned|signed|const|struct|union)\s+)*[A-Za-z_]\w*(?:\s+(?:int|char|short|long))?)\s*"
    r"(\**)\s*([A-Za-z_]\w*(?:\s*\[[^\]]*\])*(?:\s*,\s*\**\s*[A-Za-z_]\w*(?:\s*\[[^\]]*\])*)*)\s*$",
    re.DOTALL,
)
_PATRON_GLOBAL = re.compile(
    r"^(?:extern\s+)?((?:(?:unsigned|signed|const)\s+)*[A-Za-z_]\w*)\s*(\**)\s*([A-Za-z_]\w*)\s*;",
    re.MULTILINE,
)
_PATRON_TYPEDEF = re.compile(r"\btypedef\b")
_PATRON_PUNTERO_A_FUNCION = re.compile(r"\(\s*\*+\s*([A-Za-z_]\w*)\s*\)")
_PATRON_ULTIMO_NOMBRE = re.compile(r"([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)*$")
_PATRON_TIPO_OPACO = re.compile(r"\(|\*\s*(?:const|volatile)\b")
_PALABRAS_QUE_NO_SON_TIPO = frozenset(
    {"return", "goto", "break", "continue", "else", "case", "default", "typedef", "if", "while", "for", "do"}
)
_PATRON_LITERAL = re.compile(r"^(0[xX][0-9a-fA-F]+|\d+)([uUlL]*)$")


@dataclass(frozen=True)
class Tipo:
    """Tipo de una expresion escalar o agregada.

    Attributes:
        base: Nombre del tipo sin asteriscos (``s16``, ``unsigned char``, ``Objeto``).
        estrellas: Niveles de puntero.
        ancho: Bits si es un entero (0 si no lo es).
        con_signo: Si el entero tiene signo.
        arreglo: Si es un arreglo de ``base`` (los demas campos describen el elemento).
    """

    base: str
    estrellas: int = 0
    ancho: int = 0
    con_signo: bool = True
    arreglo: bool = False

    @property
    def es_entero(self) -> bool:
        """Verdadero para un entero que no es puntero."""
        return self.estrellas == 0 and self.ancho > 0 and not self.arreglo

    @property
    def es_puntero(self) -> bool:
        """Verdadero para un puntero."""
        return self.estrellas > 0 and not self.arreglo

    @property
    def es_escalar(self) -> bool:
        """Verdadero para enteros y punteros, los unicos tipos que se copian a un temporal."""
        return (self.es_entero or self.es_puntero) and not self.arreglo

    @property
    def texto(self) -> str:
        """Texto C del tipo."""
        return self.base + "*" * self.estrellas

    @property
    def rango(self) -> tuple[int, int]:
        """Valores representables de un entero (``(0, 0)`` si no lo es)."""
        if not self.es_entero:
            return (0, 0)
        if self.con_signo:
            return (-(1 << (self.ancho - 1)), (1 << (self.ancho - 1)) - 1)
        return (0, (1 << self.ancho) - 1)


S32 = Tipo("s32", 0, 32, True)
U32 = Tipo("u32", 0, 32, False)
TIPOS_ENTEROS_PERMITIDOS = ("s32", "u32", "s16", "u16")


def nombre_de_estructura(base: str) -> str:
    """
    Quita ``struct`` o ``union`` del texto de un tipo para buscar su estructura en la tabla.

    Contexto:
        El texto de un tipo conserva la palabra ``struct`` (un temporal de tipo ``struct Nodo*`` debe
        declararse asi porque la etiqueta no es un nombre de tipo), pero la tabla de campos se
        indexa por el nombre de la estructura.

    Args:
        base (str): Texto del tipo sin asteriscos.

    Returns:
        str: Nombre de la estructura.

    Ejemplo:
        nombre = nombre_de_estructura("struct Nodo")
    """
    return base.removeprefix("struct ").removeprefix("union ")


def tipo_entero(nombre: str) -> Tipo:
    """
    Construye el tipo entero con el nombre del proyecto.

    Contexto:
        La mutacion de ancho elige entre ``s32``, ``u32``, ``s16`` y ``u16``.

    Args:
        nombre (str): Nombre de un tipo entero conocido.

    Returns:
        Tipo: El tipo.

    Raises:
        KeyError: Si el nombre no es un entero conocido.

    Ejemplo:
        tipo = tipo_entero("s16")
    """
    ancho, con_signo = ANCHOS_ENTEROS[nombre]
    return Tipo(nombre, 0, ancho, con_signo)


def parsear_tipo(base: str, estrellas: int = 0) -> Tipo:
    """
    Interpreta el texto de un tipo.

    Contexto:
        Convierte lo que el analizador de C lee (parametros, declaraciones, moldes) a un ``Tipo``.

    Args:
        base (str): Texto sin asteriscos (``unsigned char``).
        estrellas (int, opcional): Niveles de puntero.

    Returns:
        Tipo: Tipo con su ancho cuando es un entero conocido; un tipo agregado (ancho 0) si no lo es.

    Ejemplo:
        tipo = parsear_tipo("u8", 1)
    """
    texto = base.strip()
    if _PATRON_TIPO_OPACO.search(texto):
        return Tipo(" ".join(texto.split()) + "*" * estrellas)
    if texto.endswith("*"):
        return parsear_tipo(texto.rstrip("*").strip(), estrellas + texto.count("*"))
    palabras = [p for p in texto.split() if p not in CALIFICADORES]
    sin_signo = "unsigned" in palabras
    nucleo = [p for p in palabras if p not in ("unsigned", "signed")] or ["int"]
    if len(nucleo) == 1 and nucleo[0] in ANCHOS_ENTEROS:
        ancho, con_signo = ANCHOS_ENTEROS[nucleo[0]]
        return Tipo(" ".join(palabras), estrellas, ancho, False if sin_signo else con_signo)
    return Tipo(" ".join(palabras), estrellas)


@dataclass
class TablaTipos:
    """Tipos de campos, globales y nombres de tipo recogidos de las cabeceras y del archivo.

    Attributes:
        campos: Tipo por nombre de campo; ``None`` si se declara con tipos distintos o es un arreglo.
        estructuras: Campos con su tipo por nombre de estructura (etiqueta o ``typedef``).
        globales: Tipo por nombre de variable global escalar.
        nombres_de_tipo: Nombres definidos con ``typedef``.
        uniones: Miembros de cada ``union`` con nombre (etiqueta, ``typedef`` o declarador).
        grupos_anonimos: Miembros de cada ``union`` sin nombre, cuyos campos se acceden directamente
            desde la estructura que la contiene.
        alias_de_campos: Representante de cada campo que comparte almacenamiento con otro de una
            union. Dos campos con el mismo representante son la misma memoria.
    """

    campos: dict[str, Tipo | None] = field(default_factory=dict)
    estructuras: dict[str, dict[str, Tipo]] = field(default_factory=dict)
    globales: dict[str, Tipo] = field(default_factory=dict)
    nombres_de_tipo: frozenset[str] = frozenset()
    uniones: dict[str, frozenset[str]] = field(default_factory=dict)
    grupos_anonimos: list[frozenset[str]] = field(default_factory=list)
    alias_de_campos: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Agregado:
    """Una ``struct`` o ``union`` con cuerpo hallada en un texto C.

    Attributes:
        nombres: Etiqueta, nombre de ``typedef`` o declarador; vacio si no tiene ninguno.
        cuerpo: Texto de los campos de primer nivel (los cuerpos anidados se sustituyen por blancos).
        es_union: Verdadero si es una ``union``.
    """

    nombres: list[str]
    cuerpo: str
    es_union: bool


def _sin_llaves(texto: str) -> str:
    """Quita de un texto el contenido entre llaves (con las llaves), anidado o no."""
    nivel = 0
    resto: list[str] = []
    for caracter in texto:
        nivel += (caracter == "{") - (caracter == "}")
        if nivel == 0 and caracter != "}":
            resto.append(caracter)
    return "".join(resto)


def _declarados_por(declaracion: str) -> list[str]:
    """Nombres que declara un ``typedef`` sin cuerpos: el de un puntero a funcion o los de cada declarador."""
    puntero = _PATRON_PUNTERO_A_FUNCION.search(declaracion)
    if puntero is not None:
        return [puntero.group(1)]
    nombres: list[str] = []
    for trozo in declaracion.split(","):
        encontrado = _PATRON_ULTIMO_NOMBRE.search(trozo.strip())
        if encontrado is not None:
            nombres.append(encontrado.group(1))
    return nombres


def nombres_de_typedef(limpio: str) -> set[str]:
    """
    Reune los nombres que declara cada ``typedef`` de un texto C ya enmascarado.

    Contexto:
        El analizador de C distingue una declaracion o un molde de una expresion por si el primer nombre
        es un tipo. Solo cuenta lo declarado tras la palabra ``typedef``: un ``}`` seguido de un
        identificador y ``;`` tambien aparece en el cuerpo de las funciones (``} return;``) y no define
        ningun tipo.

    Args:
        limpio (str): Texto sin comentarios ni literales de texto.

    Returns:
        set[str]: Nombres de tipo, incluidos los de punteros a funcion y de arreglos, y los
        declaradores adicionales (``} Nodo, *PNodo;``).

    Ejemplo:
        nombres = nombres_de_typedef("typedef void (*Rutina)(s32); typedef struct { s32 a; } Par;")
    """
    nombres: set[str] = set()
    for inicio in _PATRON_TYPEDEF.finditer(limpio):
        nivel = 0
        for posicion in range(inicio.end(), len(limpio)):
            nivel += (limpio[posicion] == "{") - (limpio[posicion] == "}")
            if limpio[posicion] == ";" and nivel <= 0:
                nombres.update(_declarados_por(_sin_llaves(limpio[inicio.end() : posicion])))
                break
    return nombres - c.PALABRAS_RESERVADAS


def _declaradores(texto: str) -> list[tuple[int, str, bool]]:
    """Separa ``*a, b[3]`` en (estrellas, nombre, es_arreglo)."""
    resultado: list[tuple[int, str, bool]] = []
    for trozo in texto.split(","):
        encontrado = re.fullmatch(r"\s*(\**)\s*([A-Za-z_]\w*)\s*(.*?)\s*", trozo)
        if encontrado is not None:
            resultado.append((len(encontrado.group(1)), encontrado.group(2), bool(encontrado.group(3))))
    return resultado


def _estructuras_de(limpio: str) -> Iterator[Agregado]:
    """Cada estructura o union con cuerpo (tambien las anonimas), con sus nombres y el cuerpo sin anidadas."""
    for encontrado in _PATRON_ESTRUCTURA.finditer(limpio):
        nivel, posicion = 1, encontrado.end()
        cuerpo: list[str] = []
        while posicion < len(limpio) and nivel:
            caracter = limpio[posicion]
            nivel += (caracter == "{") - (caracter == "}")
            if nivel == 1 and caracter not in "{}":
                cuerpo.append(caracter)
            elif nivel > 1:
                cuerpo.append(" ")
            posicion += 1
        cola = re.match(r"\s*([A-Za-z_]\w*)?\s*;", limpio[posicion:])
        nombres = [n for n in (encontrado.group(2), cola.group(1) if cola else None) if n]
        yield Agregado(nombres, "".join(cuerpo), encontrado.group(1) == "union")


def _fusionar_grupos(grupos: Iterable[frozenset[str]]) -> dict[str, str]:
    """
    Une los grupos de campos que comparten algun nombre y da un representante estable por campo.

    Contexto:
        El analisis de efectos identifica un acceso por el nombre de sus campos, sin saber de que
        estructura son. Un mismo nombre puede aparecer en uniones distintas: se fusionan sus grupos,
        lo que solo anade conflictos y por tanto es seguro.

    Args:
        grupos (Iterable[frozenset[str]]): Miembros de cada union.

    Returns:
        dict[str, str]: Representante (el menor nombre del grupo fusionado) por campo.

    Ejemplo:
        alias = _fusionar_grupos([frozenset({"a", "b"}), frozenset({"b", "c"})])
    """
    fusionados: list[set[str]] = []
    for grupo in grupos:
        union = set(grupo)
        for existente in [g for g in fusionados if g & union]:
            union |= existente
            fusionados.remove(existente)
        fusionados.append(union)
    return {nombre: min(g) for g in fusionados for nombre in g}


def _campos_de(cuerpo: str) -> dict[str, Tipo]:
    """Campos de una estructura con su tipo (los campos de bits pierden su ancho; las anidadas se omiten)."""
    campos: dict[str, Tipo] = {}
    for declaracion in cuerpo.split(";"):
        encontrado = _PATRON_CAMPO.match(re.sub(r"\s*:\s*\d+", "", declaracion))
        if encontrado is None or encontrado.group(1).split()[0] in _PALABRAS_QUE_NO_SON_TIPO:
            continue
        for estrellas, nombre, arreglo in _declaradores(f"{encontrado.group(2)}{encontrado.group(3)}"):
            campos[nombre] = replace(parsear_tipo(encontrado.group(1), estrellas), arreglo=arreglo)
    return campos


def construir_tabla(textos: Iterable[str]) -> TablaTipos:
    """
    Recoge de los textos de las cabeceras y del archivo los tipos de campos y globales.

    Contexto:
        Primer paso del permutador: la inferencia de tipos de ``Entorno`` se apoya en esta tabla. Es una
        lectura por expresiones regulares (no un analizador completo): un nombre de campo declarado con
        tipos distintos en estructuras distintas queda sin tipo, y los arreglos y estructuras anidadas
        tampoco se tipan como escalares.

    Args:
        textos (Iterable[str]): Contenido de las cabeceras de ``include/`` y del archivo ``.c``.

    Returns:
        TablaTipos: Tabla con campos, globales y nombres de tipo.

    Ejemplo:
        tabla = construir_tabla([cabecera, fuente])
    """
    tabla = TablaTipos()
    nombres: set[str] = set()
    vistos: dict[str, set[Tipo | None]] = {}
    for texto in textos:
        limpio = c.enmascarar(texto)
        nombres.update(nombres_de_typedef(limpio))
        for encontrado in _PATRON_DECLARACION.finditer(limpio):
            if encontrado.group(1).split()[0] in _PALABRAS_QUE_NO_SON_TIPO:
                continue
            declaradores = _declaradores(f"{encontrado.group(2)}{encontrado.group(3)}")
            for estrellas, nombre, arreglo in declaradores:
                escalar = parsear_tipo(encontrado.group(1), estrellas)
                vistos.setdefault(nombre, set()).add(None if arreglo or not escalar.es_escalar else escalar)
        for agregado in _estructuras_de(limpio):
            campos = _campos_de(agregado.cuerpo)
            for nombre_de_estructura in agregado.nombres:
                tabla.estructuras.setdefault(nombre_de_estructura, {}).update(campos)
            if agregado.es_union and len(campos) > 1:
                miembros = frozenset(campos)
                if not agregado.nombres:
                    tabla.grupos_anonimos.append(miembros)
                for nombre_de_union in agregado.nombres:
                    previos = tabla.uniones.get(nombre_de_union, frozenset())
                    tabla.uniones[nombre_de_union] = previos | miembros
        for encontrado in _PATRON_GLOBAL.finditer(limpio):
            tipo = parsear_tipo(encontrado.group(1), len(encontrado.group(2)))
            if encontrado.group(1) not in _PALABRAS_QUE_NO_SON_TIPO and tipo.es_escalar:
                tabla.globales[encontrado.group(3)] = tipo
    tabla.campos = {
        nombre: (next(iter(tipos)) if len(tipos) == 1 else None) for nombre, tipos in vistos.items()
    }
    tabla.nombres_de_tipo = frozenset(nombres)
    tabla.alias_de_campos = _fusionar_grupos([*tabla.uniones.values(), *tabla.grupos_anonimos])
    return tabla


def _valor_entero(texto: str) -> int | None:
    """Valor de un literal entero sin sufijo: hexadecimal, octal (``010``) o decimal."""
    base = 16 if texto[:2].lower() == "0x" else (8 if len(texto) > 1 and texto[0] == "0" else 10)
    try:
        return int(texto, base)
    except ValueError:
        return None


def tipo_de_literal(texto: str) -> Tipo | None:
    """
    Da el tipo de un literal entero segun C (``int`` si cabe, ``unsigned`` si lleva ``u`` o no cabe).

    Contexto:
        Los literales participan en la inferencia de tipos y en la comprobacion de rango.

    Args:
        texto (str): Texto del literal.

    Returns:
        Tipo | None: ``s32`` o ``u32``; ``None`` si no es un entero que quepa en 32 bits.

    Ejemplo:
        tipo = tipo_de_literal("0x12C")
    """
    encontrado = _PATRON_LITERAL.match(texto)
    valor = None if encontrado is None else _valor_entero(encontrado.group(1))
    if encontrado is None or valor is None or valor > 0xFFFFFFFF:
        return None
    sin_signo = "u" in encontrado.group(2).lower()
    return U32 if sin_signo or valor > 0x7FFFFFFF else S32


def valor_de_literal(expr: c.Expr) -> int | None:
    """
    Da el valor de un literal entero, con signo si va precedido de ``-``.

    Contexto:
        Permite comprobar si una constante cabe en el tipo al que se ensancha o estrecha una variable.

    Args:
        expr (c.Expr): Expresion.

    Returns:
        int | None: Valor, o ``None`` si no es un literal entero.

    Ejemplo:
        valor = valor_de_literal(c.Unario("-", c.Num("1")))
    """
    if isinstance(expr, c.Unario) and expr.op == "-":
        interior = valor_de_literal(expr.operando)
        return None if interior is None else -interior
    if isinstance(expr, c.Num) and tipo_de_literal(expr.texto) is not None:
        return _valor_entero(expr.texto.rstrip("uUlL"))
    return None


class Entorno:
    """Tipos de los identificadores y de los campos visibles desde una funcion."""

    def __init__(self, tabla: TablaTipos, funcion: c.Funcion) -> None:
        """
        Reune los tipos de los parametros y de las variables declaradas de una funcion.

        Args:
            tabla (TablaTipos): Tipos de campos y globales del proyecto.
            funcion (c.Funcion): Funcion analizada.
        """
        self.tabla = tabla
        self.locales: dict[str, Tipo] = {}
        self.parametros = {p.nombre for p in funcion.parametros}
        for parametro in funcion.parametros:
            self.locales[parametro.nombre] = parsear_tipo(parametro.tipo)
        self.registrar_declaraciones(funcion.cuerpo)

    def registrar_declaraciones(self, bloque: c.Bloque) -> None:
        """Anota el tipo de cada variable declarada en el bloque y sus bloques internos."""
        for interno in c.todos_los_bloques(bloque):
            for sentencia in interno.items:
                if isinstance(sentencia, c.Decl):
                    if sentencia.declarador:
                        # Puntero a funcion o a arreglo: el tipo es opaco (el texto lleva parentesis).
                        self.locales[sentencia.nombre] = parsear_tipo(
                            f"{sentencia.base} {sentencia.declarador}", sentencia.estrellas
                        )
                        continue
                    tipo = parsear_tipo(sentencia.base, sentencia.estrellas)
                    self.locales[sentencia.nombre] = replace(tipo, arreglo=bool(sentencia.sufijo))

    def inferir(self, expr: c.Expr) -> Tipo | None:  # noqa: PLR0911 - despachador por tipo de nodo
        """
        Infiere el tipo de una expresion.

        Contexto:
            Decide si un temporal puede declararse con el tipo exacto de la expresion que copia.

        Args:
            expr (c.Expr): Expresion.

        Returns:
            Tipo | None: Tipo si se puede afirmar con seguridad; ``None`` si no.

        Ejemplo:
            tipo = entorno.inferir(c.Miembro(c.Id("o"), True, "radio"))
        """
        if isinstance(expr, c.Id):
            return self.locales.get(expr.nombre) or self.tabla.globales.get(expr.nombre)
        if isinstance(expr, c.Num):
            return tipo_de_literal(expr.texto)
        if isinstance(expr, c.Conversion):
            return parsear_tipo(expr.tipo)
        if isinstance(expr, c.Miembro):
            return self._miembro(expr)
        if isinstance(expr, c.Unario):
            return self._unario(expr)
        if isinstance(expr, c.Binario):
            return self._binario(expr)
        if isinstance(expr, c.Indice):
            return self._elemento(self.inferir(expr.base))
        if isinstance(expr, c.Ternario):
            return self._ternario(expr)
        if isinstance(expr, c.Asigna):
            return self.inferir(expr.destino)
        if isinstance(expr, c.Postfijo):
            return self.inferir(expr.operando)
        return None

    def _desreferenciado(self, tipo: Tipo | None) -> Tipo | None:
        """Tipo apuntado por un puntero conocido."""
        if tipo is None or not tipo.es_puntero:
            return None
        return parsear_tipo(tipo.base, tipo.estrellas - 1)

    def _elemento(self, tipo: Tipo | None) -> Tipo | None:
        """Tipo del elemento de un arreglo o de lo apuntado por un puntero."""
        if tipo is not None and tipo.arreglo:
            return replace(tipo, arreglo=False)
        return self._desreferenciado(tipo)

    def _miembro(self, expr: c.Miembro) -> Tipo | None:
        """Tipo de un campo: por la estructura de la base si se conoce y, si no, por el nombre del campo."""
        base = self.inferir(expr.base)
        propio = self._desreferenciado(base) if expr.flecha else base
        if propio is not None and propio.estrellas == 0 and not propio.arreglo:
            campo = self.tabla.estructuras.get(nombre_de_estructura(propio.base), {}).get(expr.campo)
            if campo is not None:
                return campo
        return self.tabla.campos.get(expr.campo)

    def _unario(self, expr: c.Unario) -> Tipo | None:
        """Tipo de un operador prefijo."""
        if expr.op == "*":
            return self._desreferenciado(self.inferir(expr.operando))
        if expr.op == "!":
            return S32
        if expr.op == "&":
            return None
        interior = self.inferir(expr.operando)
        if expr.op in ("++", "--"):
            return interior
        return promover(interior)

    def _ternario(self, expr: c.Ternario) -> Tipo | None:
        """Tipo comun de las ramas de ``?:``: aritmetico entre enteros; el mismo tipo si coinciden."""
        si, no = self.inferir(expr.si), self.inferir(expr.no)
        if si is None or no is None:
            return None
        if si.es_entero and no.es_entero:
            return aritmetico(si, no)
        if si.es_puntero and valor_de_literal(expr.no) == 0:
            return si
        if no.es_puntero and valor_de_literal(expr.si) == 0:
            return no
        return si if si == no and not si.arreglo else None

    def _binario(self, expr: c.Binario) -> Tipo | None:  # noqa: PLR0911 - una salida por clase de operador
        """Tipo de un operador binario."""
        if expr.op in ("==", "!=", "<", ">", "<=", ">=", "&&", "||"):
            return S32
        izq, der = self.inferir(expr.izq), self.inferir(expr.der)
        if expr.op == ",":
            return der
        if izq is None or der is None:
            return None
        if expr.op in ("+", "-") and (izq.es_puntero or der.es_puntero):
            if izq.es_puntero and der.es_puntero:
                return S32 if expr.op == "-" else None
            return izq if izq.es_puntero else der
        if expr.op in ("<<", ">>"):
            return promover(izq)
        return aritmetico(izq, der)


def promover(tipo: Tipo | None) -> Tipo | None:
    """
    Aplica la promocion entera: un entero de menos de 32 bits pasa a ``s32``.

    Contexto:
        Los operandos de la aritmetica de C se promueven antes de operar.

    Args:
        tipo (Tipo | None): Tipo del operando.

    Returns:
        Tipo | None: ``s32`` o ``u32``; ``None`` si el operando no es un entero conocido.

    Ejemplo:
        resultado = promover(tipo_entero("u16"))
    """
    if tipo is None or not tipo.es_entero:
        return None
    return S32 if tipo.ancho < 32 else (S32 if tipo.con_signo else U32)


def aritmetico(izq: Tipo, der: Tipo) -> Tipo | None:
    """
    Da el tipo de una operacion aritmetica entre dos enteros (conversiones aritmeticas usuales).

    Contexto:
        Parte de ``Entorno.inferir``.

    Args:
        izq (Tipo): Tipo del operando izquierdo.
        der (Tipo): Tipo del operando derecho.

    Returns:
        Tipo | None: ``u32`` si alguno es ``u32`` tras la promocion, ``s32`` en otro caso; ``None`` si
        algun operando no es entero.

    Ejemplo:
        resultado = aritmetico(tipo_entero("s16"), tipo_entero("u32"))
    """
    a, b = promover(izq), promover(der)
    if a is None or b is None:
        return None
    return U32 if (not a.con_signo or not b.con_signo) else S32


def conserva_valor(origen: Tipo, destino: Tipo) -> bool:
    """
    Indica si todo valor de ``origen`` se representa igual en ``destino``.

    Contexto:
        Condicion para ensanchar o cambiar el tipo de un temporal sin alterar lo que calcula.

    Args:
        origen (Tipo): Tipo del valor almacenado.
        destino (Tipo): Tipo de la variable.

    Returns:
        bool: Verdadero si ambos son enteros y el rango de origen cabe en el de destino.

    Ejemplo:
        cabe = conserva_valor(tipo_entero("u16"), tipo_entero("s32"))
    """
    if not (origen.es_entero and destino.es_entero):
        return False
    minimo_o, maximo_o = origen.rango
    minimo_d, maximo_d = destino.rango
    return minimo_d <= minimo_o and maximo_o <= maximo_d


# ---------------------------------------------------------------------------------------------------
# Efectos
# ---------------------------------------------------------------------------------------------------


@dataclass
class Efectos:
    """Lo que una sentencia lee y escribe.

    Attributes:
        lee: Ubicaciones leidas (``v:nombre`` para variables, ``m:ruta`` para memoria).
        escribe: Ubicaciones escritas.
        barrera: Verdadero si la sentencia hace algo que no se puede analizar (llamada, direccion de una
            variable local, flujo de control); nada se mueve a traves de ella.
        alias: Representante de los campos que comparten almacenamiento en una ``union``; las rutas
            de ``lee`` y ``escribe`` se escriben con el.
    """

    lee: set[str] = field(default_factory=set)
    escribe: set[str] = field(default_factory=set)
    barrera: bool = False
    alias: Mapping[str, str] = field(default_factory=lambda: SIN_ALIAS, compare=False, repr=False)


def es_pura(expr: c.Expr) -> bool:
    """
    Indica si evaluar una expresion no tiene efectos (sin llamadas, asignaciones ni incrementos).

    Contexto:
        Solo las expresiones puras se pueden copiar a un temporal, duplicar o reordenar.

    Args:
        expr (c.Expr): Expresion.

    Returns:
        bool: Verdadero si es pura.

    Ejemplo:
        pura = es_pura(c.Binario("+", c.Id("a"), c.Num("1")))
    """
    for nodo in c.recorrer(expr):
        if isinstance(nodo, c.Llamada | c.Asigna | c.Postfijo):
            return False
        if isinstance(nodo, c.Unario) and nodo.op in ("++", "--"):
            return False
    return True


def ruta_de_memoria(expr: c.Expr, alias: Mapping[str, str] = SIN_ALIAS) -> str | None:
    """
    Da la clave de memoria de un acceso (``caja_min.vx``, ``[]``, ``*``) o ``None`` si no es memoria.

    Contexto:
        Dos accesos con rutas de campo distintas se consideran independientes (hipotesis de aliasing del
        modulo), salvo que sus campos sean miembros de una misma ``union``: esos comparten almacenamiento
        y se escriben con el mismo nombre (el representante de ``alias``) para que las rutas coincidan.

    Args:
        expr (c.Expr): Expresion lvalue.
        alias (Mapping[str, str], opcional): ``TablaTipos.alias_de_campos``; sin ella cada campo es
            su propia memoria.

    Returns:
        str | None: Clave del acceso.

    Ejemplo:
        clave = ruta_de_memoria(c.Miembro(c.Id("o"), True, "radio"), tabla.alias_de_campos)
    """
    if isinstance(expr, c.Miembro):
        previa = ruta_de_memoria(expr.base, alias)
        campo = alias.get(expr.campo, expr.campo)
        return f"{previa}.{campo}" if previa and not previa.endswith(CAMPO_DE_BITS) else campo
    if isinstance(expr, c.Indice):
        previa = ruta_de_memoria(expr.base, alias)
        return f"{previa}{COMODIN}" if previa else COMODIN
    if isinstance(expr, c.Unario) and expr.op == "*":
        return CAMPO_DE_BITS
    return None


def _acumular(expr: c.Expr, efectos: Efectos, *, escritura: bool = False, direccion: bool = False) -> None:
    """Anota lecturas y escrituras de una expresion en ``efectos``."""
    if isinstance(expr, c.Llamada):
        efectos.barrera = True
        return
    if isinstance(expr, c.Asigna):
        _acumular(expr.destino, efectos, escritura=True)
        if expr.op != "=":
            _acumular(expr.destino, efectos)
        _acumular(expr.valor, efectos)
        return
    if isinstance(expr, c.Postfijo) or (isinstance(expr, c.Unario) and expr.op in ("++", "--")):
        _acumular(expr.operando, efectos, escritura=True)
        _acumular(expr.operando, efectos)
        return
    if isinstance(expr, c.Unario) and expr.op == "&":
        if isinstance(expr.operando, c.Id):
            efectos.barrera = True
            return
        _acumular(expr.operando, efectos, direccion=True)
        return
    ruta = ruta_de_memoria(expr, efectos.alias)
    if isinstance(expr, c.Id):
        (efectos.escribe if escritura else efectos.lee).add(f"v:{expr.nombre}")
        return
    if ruta is not None and not direccion:
        (efectos.escribe if escritura else efectos.lee).add(f"m:{ruta}")
    for hijo in c.hijos(expr):
        _acumular(hijo, efectos, direccion=False)


def efectos_de(sentencia: c.Sentencia, alias: Mapping[str, str] = SIN_ALIAS) -> Efectos:
    """
    Calcula lo que lee y escribe una sentencia.

    Contexto:
        ``orden_de_sentencias`` solo intercambia dos sentencias si sus efectos no se cruzan.

    Args:
        sentencia (c.Sentencia): Sentencia (solo las de expresion y declaracion con inicial se
            analizan; cualquier otra es una barrera).
        alias (Mapping[str, str], opcional): ``TablaTipos.alias_de_campos``, para que los campos de una
            misma ``union`` se vean como la misma memoria.

    Returns:
        Efectos: Lecturas, escrituras y si es una barrera.

    Ejemplo:
        efectos = efectos_de(c.Expresion(expr=c.Asigna("=", c.Id("a"), c.Num("1"))), tabla.alias_de_campos)
    """
    efectos = Efectos(alias=alias)
    if isinstance(sentencia, c.Expresion):
        _acumular(sentencia.expr, efectos)
    else:
        efectos.barrera = True
    return efectos


def _es_ruta_opaca(ruta: str) -> bool:
    """Un acceso por indice sin campo (``p[i]``) no dice a que objeto apunta: puede solapar memoria ajena."""
    return ruta.replace(COMODIN, "") == ""


def _rutas_en_conflicto(a: str, b: str) -> bool:
    """
    Dos rutas de memoria se solapan si una es prefijo de la otra o alguna es un acceso opaco.

    Un acceso opaco es ``*p`` o un indice sin campo (``p[i]``): no dice a que objeto apunta y puede
    caer sobre cualquier campo. Se trata como dependiente de todo, que es la regla segura y la que
    declara la hipotesis de aliasing del modulo.
    """
    if CAMPO_DE_BITS in (a, b) or _es_ruta_opaca(a) or _es_ruta_opaca(b):
        return True
    partes_a, partes_b = a.replace(COMODIN, ".[]").split("."), b.replace(COMODIN, ".[]").split(".")
    corto = min(len(partes_a), len(partes_b))
    return partes_a[:corto] == partes_b[:corto]


def _se_cruzan(escribe: set[str], otras: set[str]) -> bool:
    """Indica si alguna escritura toca una de las ubicaciones del otro conjunto."""
    for escrita in escribe:
        for otra in otras:
            if escrita[0] != otra[0]:
                continue
            if escrita[0] == "v" and escrita == otra:
                return True
            if escrita[0] == "m" and _rutas_en_conflicto(escrita[2:], otra[2:]):
                return True
    return False


def son_independientes(a: Efectos, b: Efectos) -> bool:
    """
    Indica si dos sentencias consecutivas se pueden intercambiar sin cambiar el resultado.

    Contexto:
        Condicion de la mutacion que reordena sentencias.

    Args:
        a (Efectos): Efectos de la primera.
        b (Efectos): Efectos de la segunda.

    Returns:
        bool: Verdadero si ninguna es una barrera y ninguna escribe algo que la otra lee o escribe.

    Ejemplo:
        libre = son_independientes(efectos_de(s1), efectos_de(s2))
    """
    if a.barrera or b.barrera:
        return False
    return not (_se_cruzan(a.escribe, b.lee | b.escribe) or _se_cruzan(b.escribe, a.lee | a.escribe))


def _acumular_sentencia(sentencia: c.Sentencia, total: Efectos) -> None:
    """Anota en ``total`` lo que una sentencia y todo lo que contiene lee y escribe."""
    if isinstance(sentencia, c.Etiqueta | c.Saltar | c.Preprocesador):
        total.barrera = True
        return
    if isinstance(sentencia, c.Decl):
        if sentencia.inicial is not None:
            _acumular(c.Asigna("=", c.Id(sentencia.nombre), sentencia.inicial), total)
        return
    for raiz in c.expresiones_de(sentencia):
        _acumular(raiz, total)
    for bloque in c.bloques_hijos(sentencia):
        for interna in bloque.items:
            _acumular_sentencia(interna, total)


def efectos_profundos(sentencia: c.Sentencia, alias: Mapping[str, str] = SIN_ALIAS) -> Efectos:
    """
    Calcula lo que lee y escribe una sentencia junto con todas las que contiene.

    Contexto:
        ``efectos_de`` trata cualquier sentencia compuesta como una barrera. Las mutaciones que
        adelantan o retrasan una lectura de memoria necesitan saber si un ``if`` o un bucle entero
        escribe esa memoria; este calculo suma los efectos de todo su contenido. Una llamada, una
        direccion de variable local, un ``goto`` o una etiqueta dentro de la sentencia la vuelven
        barrera: se puede entrar o salir por ellos sin que el analisis lo vea.

    Args:
        sentencia (c.Sentencia): Sentencia de cualquier tipo.
        alias (Mapping[str, str], opcional): ``TablaTipos.alias_de_campos``.

    Returns:
        Efectos: Lecturas y escrituras de toda la sentencia; ``barrera`` si algo no se puede analizar.

    Ejemplo:
        efectos = efectos_profundos(c.Mientras(cond=c.Id("c"), cuerpo=c.Bloque()))
    """
    total = Efectos(alias=alias)
    _acumular_sentencia(sentencia, total)
    return total


def escritura_alcanza(efectos: Efectos, lectura: Efectos) -> bool:
    """
    Indica si lo que hace una sentencia puede cambiar lo que lee una expresion.

    Contexto:
        Condicion de legalidad de las mutaciones que mueven una lectura de memoria por encima de otras
        sentencias o que la repiten en lugar de guardarla en una local: entre el punto original y el
        nuevo no puede haber una escritura que llegue a esa memoria.

    Args:
        efectos (Efectos): Efectos de las sentencias que se cruzan (``efectos_profundos``).
        lectura (Efectos): Efectos de la expresion que se mueve (solo lecturas).

    Returns:
        bool: Verdadero si hay una barrera o una escritura a una ubicacion leida: una variable o una
        ruta de memoria solapada (prefijo, mismo miembro de una ``union``, ``*p`` o un indice sin
        campo ``p[i]``, que se solapan con toda ruta).

    Ejemplo:
        conflicto = escritura_alcanza(efectos_profundos(s), efectos_de(c.Expresion(expr=lectura)))
    """
    return efectos.barrera or lectura.barrera or _se_cruzan(efectos.escribe, lectura.lee)


def identificadores_de(expr: c.Expr) -> set[str]:
    """
    Reune los nombres de variable que aparecen en una expresion.

    Contexto:
        Comprueba que un inicializador o una copia no dependa de otra variable que se esta moviendo.

    Args:
        expr (c.Expr): Expresion.

    Returns:
        set[str]: Nombres (los de funciones llamadas tambien aparecen).

    Ejemplo:
        nombres = identificadores_de(c.Binario("+", c.Id("a"), c.Id("b")))
    """
    return {nodo.nombre for nodo in c.recorrer(expr) if isinstance(nodo, c.Id)}


def texto_de(expr: c.Expr) -> str:
    """
    Escribe una expresion como clave para compararla con otra por su contenido.

    Contexto:
        Las mutaciones que reutilizan un temporal buscan las apariciones iguales de una expresion.

    Args:
        expr (c.Expr): Expresion.

    Returns:
        str: Texto C de la expresion.

    Ejemplo:
        clave = texto_de(c.Id("a"))
    """
    return c.imprimir_expresion(expr)

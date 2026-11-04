"""Analizador y generador de C para el cuerpo de una funcion del juego.

El permutador necesita reescribir el C de una funcion sin cambiar lo que hace: para eso lo lee a un
arbol (declaraciones, sentencias y expresiones), aplica transformaciones sobre el arbol y lo vuelve a
escribir. Este modulo es la capa pura de lectura y escritura; no sabe nada de compiladores ni de
mutaciones.

Alcance: el subconjunto de C89 que usa ``src/`` (declaraciones al inicio del bloque, ``if``,
``while``, ``do``, ``for``, ``switch``, ``goto``, llamadas, macros de funcion que se parecen a
llamadas, moldes y accesos a campos). Cualquier construccion fuera de ese subconjunto se rechaza con
``AnalisisCError`` en lugar de adivinarla: una reescritura que no entiende el original no puede
garantizar que conserva su significado.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

PALABRAS_DE_TIPO = frozenset(
    {
        "unsigned",
        "signed",
        "short",
        "int",
        "long",
        "char",
        "void",
        "struct",
        "union",
        "enum",
        "const",
        "volatile",
        "register",
        "static",
        "extern",
    }
)
TIPOS_DEL_PROYECTO = frozenset({"s8", "u8", "s16", "u16", "s32", "u32", "s64", "u64"})
PALABRAS_RESERVADAS = frozenset(
    {"return", "goto", "break", "continue", "else", "case", "default", "if", "while", "for", "do", "switch"}
    | {"sizeof", "typedef"}
)
OPERADORES_DE_BITS = frozenset({"&", "|", "^", "<<", ">>"})
OPERADORES_DE_ASIGNACION = frozenset({"=", "+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "|=", "^="})
PRECEDENCIA_BINARIA = {
    ",": 1,
    "||": 4,
    "&&": 5,
    "|": 6,
    "^": 7,
    "&": 8,
    "==": 9,
    "!=": 9,
    "<": 10,
    ">": 10,
    "<=": 10,
    ">=": 10,
    "<<": 11,
    ">>": 11,
    "+": 12,
    "-": 12,
    "*": 13,
    "/": 13,
    "%": 13,
}
PRECEDENCIA_ASIGNACION = 2
PRECEDENCIA_TERNARIO = 3
PRECEDENCIA_UNARIA = 14
PRECEDENCIA_POSTFIJA = 15
PRECEDENCIA_ATOMO = 16
_ESPECIFICADORES = frozenset({"unsigned", "signed", "const", "volatile", "register", "static", "extern"})
_CONTINUACIONES_DE_TIPO = frozenset(
    {"unsigned", "signed", "short", "int", "long", "char", "const", "volatile"}
)
SANGRIA = "    "
ANCHO_DE_LINEA = 110
MAX_PROFUNDIDAD = 200

_PATRON_TOKEN = re.compile(
    r"""
      (?P<pre>^[ \t]*\#[^\n]*(?:\\\n[^\n]*)*)
    | (?P<espacio>[ \t\r\f\v]+)
    | (?P<salto>\n)
    | (?P<bloque>/\*.*?\*/)
    | (?P<linea>//[^\n]*)
    | (?P<id>[A-Za-z_]\w*)
    | (?P<num>0[xX][0-9a-fA-F]+[uUlL]*|\d+\.\d*[fF]?|\.\d+[fF]?|\d+[uUlLfF]*)
    | (?P<cadena>"(?:\\.|[^"\\\n])*")
    | (?P<caracter>'(?:\\.|[^'\\\n])*')
    | (?P<op><<=|>>=|\.\.\.|->|\+\+|--|<<|>>|<=|>=|==|!=|&&|\|\||\+=|-=|\*=|/=|%=|&=|\|=|\^=
        |[-+*/%&|^~!<>=?:;,.(){}\[\]])
    """,
    re.VERBOSE | re.DOTALL | re.MULTILINE,
)
_PATRON_ENMASCARAR = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'', re.DOTALL)
_PATRON_IDENTIFICADOR = re.compile(r"^[A-Za-z_]\w*$")


class AnalisisCError(ValueError):
    """El C de la funcion usa algo que el analizador no sabe leer o reescribir sin riesgo."""


# ---------------------------------------------------------------------------------------------------
# Arbol
# ---------------------------------------------------------------------------------------------------


@dataclass(eq=False)
class Expr:
    """Base de las expresiones; la identidad del objeto distingue un sitio de otro."""


@dataclass(eq=False)
class Id(Expr):
    """Identificador (variable, funcion o macro).

    Attributes:
        nombre: Texto del identificador.
    """

    nombre: str


@dataclass(eq=False)
class Num(Expr):
    """Literal numerico, con el texto original (``0x12C``, ``1000``).

    Attributes:
        texto: Texto tal como se escribio.
    """

    texto: str


@dataclass(eq=False)
class Texto(Expr):
    """Atomo que no se analiza: cadena, caracter, ``sizeof`` o nombre de tipo pasado a una macro.

    Attributes:
        texto: Texto tal como se escribio.
    """

    texto: str


@dataclass(eq=False)
class Unario(Expr):
    """Operador prefijo (``- + ! ~ * & ++ --``).

    Attributes:
        op: Operador.
        operando: Expresion afectada.
    """

    op: str
    operando: Expr


@dataclass(eq=False)
class Postfijo(Expr):
    """Incremento o decremento posfijo.

    Attributes:
        op: ``++`` o ``--``.
        operando: Expresion afectada.
    """

    op: str
    operando: Expr


@dataclass(eq=False)
class Binario(Expr):
    """Operador binario, incluida la coma.

    Attributes:
        op: Operador.
        izq: Operando izquierdo.
        der: Operando derecho.
    """

    op: str
    izq: Expr
    der: Expr


@dataclass(eq=False)
class Asigna(Expr):
    """Asignacion simple o compuesta.

    Attributes:
        op: ``=``, ``+=``, etc.
        destino: Lado izquierdo.
        valor: Lado derecho.
    """

    op: str
    destino: Expr
    valor: Expr


@dataclass(eq=False)
class Ternario(Expr):
    """Operador condicional.

    Attributes:
        cond: Condicion.
        si: Valor si es verdadera.
        no: Valor si es falsa.
    """

    cond: Expr
    si: Expr
    no: Expr


@dataclass(eq=False)
class Llamada(Expr):
    """Llamada a funcion o macro de funcion.

    Attributes:
        funcion: Expresion llamada.
        args: Argumentos.
    """

    funcion: Expr
    args: list[Expr]


@dataclass(eq=False)
class Indice(Expr):
    """Acceso por indice.

    Attributes:
        base: Arreglo o puntero.
        indice: Posicion.
    """

    base: Expr
    indice: Expr


@dataclass(eq=False)
class Miembro(Expr):
    """Acceso a un campo con ``.`` o ``->``.

    Attributes:
        base: Estructura o puntero.
        flecha: Verdadero para ``->``.
        campo: Nombre del campo.
    """

    base: Expr
    flecha: bool
    campo: str


@dataclass(eq=False)
class Conversion(Expr):
    """Molde ``(tipo)expresion``.

    Attributes:
        tipo: Texto normalizado del tipo (``u8*``, ``unsigned char``).
        operando: Expresion convertida.
    """

    tipo: str
    operando: Expr


@dataclass(eq=False)
class Sentencia:
    """Base de las sentencias.

    Attributes:
        comentarios: Comentarios que preceden a la sentencia, tal como se escribieron.
    """

    comentarios: tuple[str, ...] = field(default=(), kw_only=True)


@dataclass(eq=False)
class Decl(Sentencia):
    """Declaracion de una variable local (una por declarador).

    Attributes:
        base: Tipo sin asteriscos (``s32``, ``unsigned char``).
        estrellas: Cantidad de ``*`` del declarador.
        nombre: Nombre de la variable.
        sufijo: Dimensiones de arreglo tal como se escribieron (``[3]``) o vacio.
        inicial: Inicializador, o ``None``.
        declarador: Declarador parentetizado de puntero a funcion o a arreglo tal como se escribio
            (``(*fp)(s32)``, ``(*tabla)[2]``), con el nombre dentro; vacio en el resto. Cuando existe,
            el tipo de la variable es opaco para el analisis y ``sufijo`` queda vacio.
    """

    base: str
    estrellas: int
    nombre: str
    sufijo: str = ""
    inicial: Expr | None = None
    declarador: str = ""


@dataclass(eq=False)
class Expresion(Sentencia):
    """Sentencia de expresion.

    Attributes:
        expr: Expresion evaluada.
    """

    expr: Expr = field(default_factory=lambda: Num("0"))


@dataclass(eq=False)
class Bloque(Sentencia):
    """Secuencia de sentencias entre llaves.

    Attributes:
        items: Sentencias en orden (las declaraciones van primero).
        finales: Comentarios antes de la llave de cierre.
    """

    items: list[Sentencia] = field(default_factory=list)
    finales: tuple[str, ...] = ()


@dataclass(eq=False)
class Si(Sentencia):
    """Condicional.

    Attributes:
        cond: Condicion.
        entonces: Rama verdadera.
        sino: Rama falsa, o ``None``.
    """

    cond: Expr = field(default_factory=lambda: Num("0"))
    entonces: Bloque = field(default_factory=Bloque)
    sino: Bloque | None = None


@dataclass(eq=False)
class Mientras(Sentencia):
    """Bucle ``while``.

    Attributes:
        cond: Condicion.
        cuerpo: Cuerpo.
    """

    cond: Expr = field(default_factory=lambda: Num("0"))
    cuerpo: Bloque = field(default_factory=Bloque)


@dataclass(eq=False)
class HacerMientras(Sentencia):
    """Bucle ``do ... while``.

    Attributes:
        cuerpo: Cuerpo.
        cond: Condicion.
    """

    cuerpo: Bloque = field(default_factory=Bloque)
    cond: Expr = field(default_factory=lambda: Num("0"))


@dataclass(eq=False)
class Para(Sentencia):
    """Bucle ``for``.

    Attributes:
        inicio: Expresion inicial o ``None``.
        cond: Condicion o ``None``.
        paso: Expresion de avance o ``None``.
        cuerpo: Cuerpo.
    """

    inicio: Expr | None = None
    cond: Expr | None = None
    paso: Expr | None = None
    cuerpo: Bloque = field(default_factory=Bloque)


@dataclass(eq=False)
class Seleccion(Sentencia):
    """``switch``; sus ``case`` son sentencias ``Caso`` dentro del cuerpo.

    Attributes:
        cond: Expresion evaluada.
        cuerpo: Cuerpo.
    """

    cond: Expr = field(default_factory=lambda: Num("0"))
    cuerpo: Bloque = field(default_factory=Bloque)


@dataclass(eq=False)
class Caso(Sentencia):
    """Etiqueta ``case`` o ``default``.

    Attributes:
        valor: Expresion del ``case``; ``None`` para ``default``.
    """

    valor: Expr | None = None


@dataclass(eq=False)
class Devolver(Sentencia):
    """``return``.

    Attributes:
        valor: Valor devuelto, o ``None``.
    """

    valor: Expr | None = None


@dataclass(eq=False)
class Romper(Sentencia):
    """``break``."""


@dataclass(eq=False)
class Continuar(Sentencia):
    """``continue``."""


@dataclass(eq=False)
class Saltar(Sentencia):
    """``goto``.

    Attributes:
        etiqueta: Nombre de la etiqueta.
    """

    etiqueta: str = ""


@dataclass(eq=False)
class Etiqueta(Sentencia):
    """Etiqueta de ``goto``.

    Attributes:
        nombre: Nombre de la etiqueta.
    """

    nombre: str = ""


@dataclass(eq=False)
class Vacia(Sentencia):
    """Sentencia vacia (``;``)."""


@dataclass(eq=False)
class Preprocesador(Sentencia):
    """Directiva del preprocesador dentro de la funcion; se conserva intacta y no se mueve.

    Attributes:
        texto: Linea completa.
    """

    texto: str = ""


@dataclass(eq=False)
class Parametro:
    """Parametro de la funcion.

    Attributes:
        tipo: Texto del tipo, con los asteriscos pegados (``Objeto*``).
        nombre: Nombre del parametro.
    """

    tipo: str
    nombre: str


@dataclass(eq=False)
class Funcion:
    """Definicion completa de una funcion.

    Attributes:
        cabecera: Texto de la firma tal como se escribio, sin la llave.
        nombre: Nombre de la funcion.
        parametros: Parametros de la firma.
        cuerpo: Cuerpo de la funcion.
    """

    cabecera: str
    nombre: str
    parametros: list[Parametro]
    cuerpo: Bloque


# ---------------------------------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Token:
    """Unidad lexica.

    Attributes:
        tipo: ``id``, ``num``, ``cadena``, ``caracter``, ``op``, ``pre`` o ``fin``.
        texto: Texto del token.
        previos: Comentarios que lo preceden.
        linea: Linea del primer comentario previo (1 es la primera del texto tokenizado); 0 si no hay.
    """

    tipo: str
    texto: str
    previos: tuple[str, ...] = ()
    linea: int = 0


def enmascarar(texto: str) -> str:
    """
    Sustituye comentarios y literales de texto por espacios conservando saltos de linea y longitud.

    Contexto:
        Permite buscar llaves y nombres sin que un comentario o una cadena los confundan, y mapear
        las posiciones encontradas de vuelta al texto original.

    Args:
        texto (str): Texto C.

    Returns:
        str: Texto de la misma longitud con los comentarios y literales en blanco.

    Ejemplo:
        limpio = enmascarar('a = "{"; /* } */')
    """
    return _PATRON_ENMASCARAR.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), texto)


def tokenizar(texto: str, linea_inicial: int = 1) -> list[Token]:
    """
    Divide un texto C en tokens, asociando cada comentario al token siguiente.

    Contexto:
        Primer paso de ``analizar_funcion``.

    Args:
        texto (str): Texto C.
        linea_inicial (int, opcional): Numero de linea de la primera linea de ``texto``.

    Returns:
        list[Token]: Tokens terminados por uno de tipo ``fin`` que recoge los comentarios finales.

    Raises:
        AnalisisCError: Si aparece un caracter que no pertenece a C.

    Ejemplo:
        tokens = tokenizar("a = 1;")
    """
    tokens: list[Token] = []
    previos: list[str] = []
    linea_previos = 0
    posicion = 0
    linea = linea_inicial
    while posicion < len(texto):
        encontrado = _PATRON_TOKEN.match(texto, posicion)
        if encontrado is None:
            raise AnalisisCError(f"caracter no reconocido: {texto[posicion]!r}")
        posicion = encontrado.end()
        tipo = encontrado.lastgroup or ""
        fragmento = encontrado.group(0)
        if tipo in ("bloque", "linea"):
            if not previos:
                linea_previos = linea
            previos.append(fragmento)
        elif tipo not in ("espacio", "salto"):
            tokens.append(Token(tipo, fragmento, tuple(previos), linea_previos if previos else 0))
            previos = []
        linea += fragmento.count("\n")
    tokens.append(Token("fin", "", tuple(previos), linea_previos if previos else 0))
    return tokens


def _es_de_palabra(caracter: str) -> bool:
    """Indica si un caracter puede formar parte de un identificador o de un numero."""
    return caracter.isalnum() or caracter == "_"


def unir_tokens(partes: Iterable[str]) -> str:
    """
    Une textos de tokens separando solo lo necesario para que no se fundan.

    Contexto:
        Los atomos opacos (``sizeof`` y listas de inicializacion) se copian token a token.

    Args:
        partes (Iterable[str]): Textos de tokens.

    Returns:
        str: Texto unido; lleva un espacio entre dos palabras o numeros contiguos y tras cada coma.

    Ejemplo:
        texto = unir_tokens(["sizeof", "(", "struct", "X", ")"])
    """
    resultado = ""
    for parte in partes:
        if resultado and (
            (_es_de_palabra(resultado[-1]) and _es_de_palabra(parte[0])) or resultado[-1] == ","
        ):
            resultado += " "
        resultado += parte
    return resultado


def normalizar_tipo(palabras: Iterable[str], estrellas: int = 0) -> str:
    """
    Da forma canonica al texto de un tipo.

    Contexto:
        Los moldes y las declaraciones se escriben de varias formas (``Objeto *``, ``Objeto*``); el
        generador siempre usa palabras separadas por un espacio y los asteriscos pegados al final.

    Args:
        palabras (Iterable[str]): Palabras del tipo sin asteriscos.
        estrellas (int, opcional): Cantidad de asteriscos.

    Returns:
        str: Texto del tipo.

    Ejemplo:
        tipo = normalizar_tipo(["unsigned", "char"], 1)
    """
    return " ".join(palabras) + "*" * estrellas


class _Analizador:
    """Descenso recursivo sobre los tokens de una funcion."""

    def __init__(self, tokens: list[Token], tipos: frozenset[str]) -> None:
        self.tokens = tokens
        self.pos = 0
        # Posiciones de los tokens cuyos comentarios previos ya tienen dueno en el arbol (el primer
        # token de una sentencia y la llave de cierre de un bloque). Un comentario en cualquier otra
        # posicion no tiene donde guardarse y reescribir sin el cambiaria el texto en silencio.
        self.reclamados: set[int] = set()
        self.tipos = (tipos | TIPOS_DEL_PROYECTO) - PALABRAS_RESERVADAS
        self.profundidad = 0

    # -- utilidades -------------------------------------------------------------------------------

    def actual(self, desplazamiento: int = 0) -> Token:
        """Token en la posicion actual mas un desplazamiento (el ultimo es siempre ``fin``)."""
        return self.tokens[min(self.pos + desplazamiento, len(self.tokens) - 1)]

    def es(self, texto: str, desplazamiento: int = 0) -> bool:
        """Indica si el token pedido es el operador o palabra ``texto``."""
        token = self.actual(desplazamiento)
        return token.texto == texto and token.tipo in ("op", "id")

    def avanzar(self) -> Token:
        """
        Consume y devuelve el token actual.

        Raises:
            AnalisisCError: Si el token lleva comentarios previos que el arbol no puede conservar.
        """
        token = self.actual()
        if token.previos and self.pos not in self.reclamados:
            raise AnalisisCError(f"comentario dentro de una expresion, en la linea {token.linea}")
        if token.tipo != "fin":
            self.pos += 1
        return token

    def consumir(self, texto: str) -> Token:
        """Consume el operador esperado o falla."""
        if not self.es(texto):
            raise AnalisisCError(f"se esperaba '{texto}' y aparece '{self.actual().texto or 'fin'}'")
        return self.avanzar()

    def tomar(self, texto: str) -> bool:
        """Consume el token si coincide; indica si lo hizo."""
        if self.es(texto):
            self.avanzar()
            return True
        return False

    def entrar(self) -> None:
        """Cuenta un nivel de anidamiento, acotado para no agotar la pila."""
        self.profundidad += 1
        if self.profundidad > MAX_PROFUNDIDAD:
            raise AnalisisCError("anidamiento excesivo")

    # -- tipos ------------------------------------------------------------------------------------

    def inicia_tipo(self, desplazamiento: int = 0) -> bool:
        """Indica si el token pedido puede comenzar un tipo."""
        token = self.actual(desplazamiento)
        return token.tipo == "id" and (token.texto in PALABRAS_DE_TIPO or token.texto in self.tipos)

    def leer_tipo(self) -> str:
        """
        Lee un nombre de tipo completo, como el de un molde o el de un argumento de macro.

        Admite palabras de tipo, asteriscos, calificadores de puntero (``u16 * volatile *``) y un
        declarador abstracto de puntero a arreglo o a funcion (``u8 (*)[64]``, ``void (*)(s32)``), que se
        copia tal cual: la reescritura no necesita entenderlo, solo conservarlo.
        """
        texto = normalizar_tipo(self.palabras_de_tipo())
        declarador = False
        while True:
            if self.tomar("*"):
                texto += "*"
            elif self.es("const") or self.es("volatile"):
                texto += " " + self.avanzar().texto
            elif not declarador and self.es("(") and self.es("*", 1):
                texto += " " + self.copiar_balanceado("(", ")")
                declarador = True
            elif declarador and self.es("["):
                texto += self.copiar_balanceado("[", "]")
            elif declarador and self.es("("):
                texto += self.copiar_balanceado("(", ")")
            else:
                return texto

    def tipo_seguido_de(self, cierres: tuple[str, ...], desplazamiento: int = 0) -> bool:
        """Indica si desde el token pedido hay un tipo completo seguido de alguno de los ``cierres``."""
        inicio = self.pos
        self.pos += desplazamiento
        try:
            self.leer_tipo()
            return any(self.es(cierre) for cierre in cierres)
        except AnalisisCError:
            return False
        finally:
            self.pos = inicio

    def palabras_de_tipo(self) -> list[str]:
        """
        Lee las palabras de un tipo: especificadores, un nucleo y sus continuaciones.

        El nucleo es una palabra que nombra el tipo (``char``, ``Objeto``, ``struct X``); tras el solo
        pueden seguir otras palabras de tipo (``unsigned char``, ``long long``), nunca el nombre de la
        variable, que tambien es un identificador. Los llamadores comprueban antes que el token actual
        inicia un tipo, de modo que siempre devuelve al menos una palabra.
        """
        palabras: list[str] = []
        nucleo = False
        while self.inicia_tipo():
            palabra = self.actual().texto
            if nucleo and palabra not in _CONTINUACIONES_DE_TIPO:
                break
            palabras.append(self.avanzar().texto)
            if palabra in ("struct", "union", "enum"):
                palabras.append(self.avanzar().texto)
            nucleo = nucleo or palabra not in _ESPECIFICADORES
        return palabras

    def es_molde(self) -> bool:
        """Indica si un ``(`` en posicion de operando abre un molde."""
        return self.es("(") and self.inicia_tipo(1) and self.tipo_seguido_de((")",), 1)

    # -- expresiones ------------------------------------------------------------------------------

    def expresion(self) -> Expr:
        """Expresion completa, con coma."""
        izq = self.asignacion()
        while self.es(","):
            self.avanzar()
            izq = Binario(",", izq, self.asignacion())
        return izq

    def asignacion(self) -> Expr:
        """Expresion de asignacion (asociativa por la derecha)."""
        self.entrar()
        try:
            izq = self.ternario()
            token = self.actual()
            if token.tipo == "op" and token.texto in OPERADORES_DE_ASIGNACION:
                self.avanzar()
                return Asigna(token.texto, izq, self.asignacion())
            return izq
        finally:
            self.profundidad -= 1

    def ternario(self) -> Expr:
        """Operador condicional."""
        cond = self.binaria(4)
        if not self.tomar("?"):
            return cond
        si = self.expresion()
        self.consumir(":")
        return Ternario(cond, si, self.ternario())

    def binaria(self, minimo: int) -> Expr:
        """Operadores binarios por precedencia ascendente, asociativos por la izquierda."""
        izq = self.unaria()
        while True:
            token = self.actual()
            precedencia = PRECEDENCIA_BINARIA.get(token.texto) if token.tipo == "op" else None
            if precedencia is None or precedencia < minimo or token.texto == ",":
                return izq
            self.avanzar()
            izq = Binario(token.texto, izq, self.binaria(precedencia + 1))

    def unaria(self) -> Expr:
        """Operadores prefijos y moldes."""
        self.entrar()
        try:
            token = self.actual()
            if token.tipo == "op" and token.texto in ("-", "+", "!", "~", "*", "&", "++", "--"):
                self.avanzar()
                return Unario(token.texto, self.unaria())
            if self.es_molde():
                self.consumir("(")
                tipo = self.leer_tipo()
                self.consumir(")")
                return Conversion(tipo, self.unaria())
            if self.es("sizeof"):
                return self.tamano()
            return self.posfija()
        finally:
            self.profundidad -= 1

    def tamano(self) -> Expr:
        """``sizeof`` como atomo opaco: copia los tokens hasta cerrar el parentesis o la expresion."""
        palabra = self.avanzar().texto
        if not self.es("("):
            return Texto(f"{palabra} {imprimir_expresion(self.unaria())}")
        return Texto(palabra + self.copiar_balanceado("(", ")"))

    def copiar_balanceado(self, abre: str, cierra: str) -> str:
        """Copia los tokens desde el delimitador de apertura actual hasta su cierre, ambos incluidos."""
        partes: list[str] = []
        nivel = 0
        while True:
            token = self.avanzar()
            if token.tipo == "fin":
                raise AnalisisCError(f"'{abre}' sin cerrar")
            partes.append(token.texto)
            nivel += (token.texto == abre) - (token.texto == cierra)
            if nivel == 0:
                return unir_tokens(partes)

    def argumento(self) -> Expr:
        """Argumento de una llamada; el de una macro puede ser un nombre de tipo (``EN(u8*, p, 4)``)."""
        if self.inicia_tipo() and self.tipo_seguido_de((",", ")")):
            return Texto(self.leer_tipo())
        return self.asignacion()

    def posfija(self) -> Expr:
        """Llamadas, indices, campos e incrementos posfijos."""
        expr = self.primaria()
        while True:
            if self.tomar("("):
                args: list[Expr] = []
                if not self.es(")"):
                    args.append(self.argumento())
                    while self.tomar(","):
                        args.append(self.argumento())
                self.consumir(")")
                expr = Llamada(expr, args)
            elif self.tomar("["):
                expr = Indice(expr, self.expresion())
                self.consumir("]")
            elif self.es(".") or self.es("->"):
                flecha = self.avanzar().texto == "->"
                nombre = self.avanzar()
                if nombre.tipo != "id":
                    raise AnalisisCError("se esperaba el nombre de un campo")
                expr = Miembro(expr, flecha, nombre.texto)
            elif self.es("++") or self.es("--"):
                expr = Postfijo(self.avanzar().texto, expr)
            else:
                return expr

    def primaria(self) -> Expr:
        """Identificadores, literales y expresiones entre parentesis."""
        token = self.avanzar()
        if token.tipo == "id":
            return Id(token.texto)
        if token.tipo == "num":
            return Num(token.texto)
        if token.tipo in ("cadena", "caracter"):
            return Texto(token.texto)
        if token.texto == "(" and token.tipo == "op":
            expr = self.expresion()
            self.consumir(")")
            return expr
        raise AnalisisCError(f"expresion no reconocida cerca de '{token.texto or 'fin'}'")

    # -- sentencias -------------------------------------------------------------------------------

    def bloque(self) -> Bloque:
        """Bloque entre llaves."""
        self.entrar()
        try:
            previos = self.actual().previos
            self.consumir("{")
            items: list[Sentencia] = []
            while not self.es("}"):
                if self.actual().tipo == "fin":
                    raise AnalisisCError("bloque sin cerrar")
                items.extend(self.sentencias())
            finales = self.actual().previos
            self.reclamados.add(self.pos)
            self.consumir("}")
            return Bloque(items=items, finales=finales, comentarios=previos)
        finally:
            self.profundidad -= 1

    def cuerpo(self) -> Bloque:
        """Cuerpo de una estructura de control: un bloque, o una sentencia que se envuelve en uno."""
        if self.es("{"):
            return self.bloque()
        return Bloque(items=self.sentencias())

    def sentencias(self) -> list[Sentencia]:
        """Una sentencia o una declaracion (que puede producir varias)."""
        token = self.actual()
        previos = token.previos
        self.reclamados.add(self.pos)
        if token.tipo == "pre":
            self.avanzar()
            return [Preprocesador(texto=token.texto.rstrip(), comentarios=previos)]
        if self.inicia_tipo() and (self._es_declarador_parentetizado() or not self._es_expresion_de_tipo()):
            return self.declaracion(previos)
        sentencia = self.sentencia()
        sentencia.comentarios = previos
        return [sentencia] if not isinstance(sentencia, _ConEtiqueta) else sentencia.expandir()

    def _es_expresion_de_tipo(self) -> bool:
        """Un nombre de tipo que no va seguido de un declarador es el inicio de una expresion."""
        siguiente = self.actual(1)
        return siguiente.tipo != "id" and siguiente.texto != "*"

    def _es_declarador_parentetizado(self) -> bool:
        """
        Indica si lo que sigue es ``tipo (*nombre)(...)`` o ``tipo (*nombre)[...]``.

        Es la declaracion de un puntero a funcion o a arreglo; sin esta comprobacion se tomaria por una
        llamada a una funcion llamada como el tipo (``s16 (*pos)[2]`` leido como ``s16(*pos)[2]``).
        """
        inicio = self.pos
        try:
            self.palabras_de_tipo()
            if not (self.es("(") and self.es("*", 1)):
                return False
            self.copiar_balanceado("(", ")")
            return self.es("(") or self.es("[")
        except AnalisisCError:
            return False
        finally:
            self.pos = inicio

    def declaracion(self, previos: tuple[str, ...]) -> list[Sentencia]:
        """Declaracion con uno o varios declaradores."""
        palabras = self.palabras_de_tipo()
        resultado: list[Sentencia] = []
        while True:
            estrellas = 0
            while self.tomar("*"):
                estrellas += 1
            declarador = ""
            sufijo = ""
            if self.es("(") and self.es("*", 1):
                declarador, nombre = self.declarador_parentetizado()
            else:
                token = self.avanzar()
                if token.tipo != "id":
                    raise AnalisisCError("se esperaba el nombre de la variable")
                nombre = token.texto
                while self.tomar("["):
                    sufijo += "[" + (imprimir_expresion(self.expresion()) if not self.es("]") else "") + "]"
                    self.consumir("]")
            inicial = self.inicializador() if self.tomar("=") else None
            resultado.append(Decl(normalizar_tipo(palabras), estrellas, nombre, sufijo, inicial, declarador))
            if not self.tomar(","):
                break
        self.consumir(";")
        resultado[0].comentarios = previos
        return resultado

    def declarador_parentetizado(self) -> tuple[str, str]:
        """
        Lee ``(*nombre)`` seguido de sus dimensiones o parametros, como ``(*pos)[2]`` o ``(*fp)(s32)``.

        Se copia tal cual: la reescritura no necesita entenderlo, solo conservarlo.

        Returns:
            tuple[str, str]: Texto del declarador y nombre de la variable.

        Raises:
            AnalisisCError: Si dentro de los parentesis no hay un nombre.
        """
        self.consumir("(")
        asteriscos = ""
        while self.tomar("*"):
            asteriscos += "*"
        nombre = self.avanzar()
        if nombre.tipo != "id":
            raise AnalisisCError("se esperaba el nombre de la variable")
        self.consumir(")")
        texto = f"({asteriscos}{nombre.texto})"
        while self.es("[") or self.es("("):
            texto += self.copiar_balanceado("[", "]") if self.es("[") else self.copiar_balanceado("(", ")")
        return texto, nombre.texto

    def inicializador(self) -> Expr:
        """Inicializador de una declaracion; una lista entre llaves se conserva como texto."""
        if not self.es("{"):
            return self.asignacion()
        return Texto(self.copiar_balanceado("{", "}"))

    def sentencia(self) -> Sentencia:
        """Sentencia que no es una declaracion."""
        token = self.actual()
        if token.tipo == "op" and token.texto == "{":
            return self.bloque()
        if token.tipo == "op" and token.texto == ";":
            self.avanzar()
            return Vacia()
        if token.tipo == "id":
            manejador = _PALABRAS_DE_SENTENCIA.get(token.texto)
            if manejador is not None:
                self.avanzar()
                return manejador(self)
            if self.es(":", 1):
                self.avanzar()
                self.avanzar()
                return _ConEtiqueta(token.texto)
        expr = self.expresion()
        self.consumir(";")
        return Expresion(expr=expr)

    def condicion(self) -> Expr:
        """Condicion entre parentesis."""
        self.consumir("(")
        expr = self.expresion()
        self.consumir(")")
        return expr

    def _si(self) -> Sentencia:
        cond = self.condicion()
        entonces = self.cuerpo()
        sino = self.cuerpo() if self.tomar("else") else None
        return Si(cond=cond, entonces=entonces, sino=sino)

    def _mientras(self) -> Sentencia:
        cond = self.condicion()
        return Mientras(cond=cond, cuerpo=self.cuerpo())

    def _hacer(self) -> Sentencia:
        cuerpo = self.cuerpo()
        self.consumir("while")
        cond = self.condicion()
        self.consumir(";")
        return HacerMientras(cuerpo=cuerpo, cond=cond)

    def _para(self) -> Sentencia:
        self.consumir("(")
        inicio = None if self.es(";") else self.expresion()
        self.consumir(";")
        cond = None if self.es(";") else self.expresion()
        self.consumir(";")
        paso = None if self.es(")") else self.expresion()
        self.consumir(")")
        return Para(inicio=inicio, cond=cond, paso=paso, cuerpo=self.cuerpo())

    def _seleccion(self) -> Sentencia:
        cond = self.condicion()
        return Seleccion(cond=cond, cuerpo=self.bloque())

    def _caso(self) -> Sentencia:
        valor = self.ternario()
        self.consumir(":")
        return Caso(valor=valor)

    def _predeterminado(self) -> Sentencia:
        self.consumir(":")
        return Caso(valor=None)

    def _devolver(self) -> Sentencia:
        valor = None if self.es(";") else self.expresion()
        self.consumir(";")
        return Devolver(valor=valor)

    def _romper(self) -> Sentencia:
        self.consumir(";")
        return Romper()

    def _continuar(self) -> Sentencia:
        self.consumir(";")
        return Continuar()

    def _saltar(self) -> Sentencia:
        etiqueta = self.avanzar()
        if etiqueta.tipo != "id":
            raise AnalisisCError("se esperaba una etiqueta")
        self.consumir(";")
        return Saltar(etiqueta=etiqueta.texto)


@dataclass(eq=False)
class _ConEtiqueta(Sentencia):
    """Resultado transitorio de leer ``nombre:``: se expande a una ``Etiqueta`` aislada."""

    nombre: str = ""

    def expandir(self) -> list[Sentencia]:
        """Convierte el resultado transitorio en la etiqueta definitiva."""
        return [Etiqueta(nombre=self.nombre, comentarios=self.comentarios)]


_PALABRAS_DE_SENTENCIA = {
    "if": _Analizador._si,
    "while": _Analizador._mientras,
    "do": _Analizador._hacer,
    "for": _Analizador._para,
    "switch": _Analizador._seleccion,
    "case": _Analizador._caso,
    "default": _Analizador._predeterminado,
    "return": _Analizador._devolver,
    "break": _Analizador._romper,
    "continue": _Analizador._continuar,
    "goto": _Analizador._saltar,
}


def separar_parametros(cabecera: str) -> list[Parametro]:
    """
    Extrae los parametros de la firma de una funcion.

    Contexto:
        El entorno de tipos del permutador necesita el tipo de cada parametro.

    Args:
        cabecera (str): Firma sin la llave (``Objeto* f(Objeto* a, u32 mascara)``).

    Returns:
        list[Parametro]: Parametros en orden; vacio para ``()`` y ``(void)``.

    Raises:
        AnalisisCError: Si la firma no tiene parentesis o un parametro no tiene nombre.

    Ejemplo:
        parametros = separar_parametros("s32 f(s32 a, u8* b)")
    """
    abre = cabecera.find("(")
    cierra = cabecera.rfind(")")
    if abre < 0 or cierra < abre:
        raise AnalisisCError("la firma de la funcion no tiene parametros entre parentesis")
    texto = cabecera[abre + 1 : cierra].strip()
    if texto in ("", "void"):
        return []
    parametros: list[Parametro] = []
    for trozo in texto.split(","):
        encontrado = re.fullmatch(r"\s*(.*?)\s*([A-Za-z_]\w*)\s*", trozo, re.DOTALL)
        if encontrado is None or not encontrado.group(1):
            raise AnalisisCError(f"parametro no reconocido: '{trozo.strip()}'")
        estrellas = encontrado.group(1).count("*")
        palabras = encontrado.group(1).replace("*", " ").split()
        parametros.append(Parametro(normalizar_tipo(palabras, estrellas), encontrado.group(2)))
    return parametros


def analizar_funcion(texto: str, nombre: str, tipos: frozenset[str] = frozenset()) -> Funcion:
    """
    Lee la definicion completa de una funcion a un arbol.

    Contexto:
        Primer paso del permutador: el texto sale de ``localizar_funcion``.

    Args:
        texto (str): Definicion (firma y cuerpo).
        nombre (str): Nombre de la funcion.
        tipos (frozenset[str], opcional): Nombres de tipos del proyecto (``typedef``) para distinguir
            declaraciones y moldes de expresiones.

    Returns:
        Funcion: Arbol de la funcion.

    Raises:
        AnalisisCError: Si el texto no es una definicion valida del subconjunto soportado.

    Ejemplo:
        funcion = analizar_funcion("s32 f(s32 a) { return a; }", "f")
    """
    llave = enmascarar(texto).find("{")
    if llave < 0:
        raise AnalisisCError("la definicion no tiene cuerpo")
    cabecera = texto[:llave].rstrip()
    analizador = _Analizador(tokenizar(texto[llave:], texto.count("\n", 0, llave) + 1), tipos)
    cuerpo = analizador.bloque()
    if analizador.actual().tipo != "fin":
        raise AnalisisCError("hay texto despues de la llave de cierre de la funcion")
    return Funcion(cabecera, nombre, separar_parametros(cabecera), cuerpo)


def localizar_funcion(texto: str, nombre: str) -> tuple[int, int]:
    """
    Localiza la definicion de una funcion dentro del texto de un archivo C.

    Contexto:
        El permutador reemplaza solo ese tramo del archivo con cada variante; el resto (cabeceras,
        otras funciones, ``INCLUDE_ASM``) queda igual.

    Args:
        texto (str): Contenido del archivo ``.c``.
        nombre (str): Nombre de la funcion.

    Returns:
        tuple[int, int]: Posicion de inicio (comienzo de la linea de la firma) y de fin (despues de
        la llave de cierre).

    Raises:
        AnalisisCError: Si no hay una definicion o hay mas de una.

    Ejemplo:
        inicio, fin = localizar_funcion(texto, "func_ejemplo")
    """
    limpio = enmascarar(texto)
    patron = re.compile(rf"^(?=[A-Za-z_])[\w \t*]*?\b{re.escape(nombre)}\s*\([^;{{}}]*\)\s*\{{", re.MULTILINE)
    encontrados = list(patron.finditer(limpio))
    if len(encontrados) != 1:
        raise AnalisisCError(
            f"se esperaba una definicion de '{nombre}' y hay {len(encontrados)}"
            if encontrados
            else f"no hay una definicion de '{nombre}' en C"
        )
    inicio = encontrados[0].start()
    nivel = 0
    for posicion in range(encontrados[0].end() - 1, len(limpio)):
        nivel += (limpio[posicion] == "{") - (limpio[posicion] == "}")
        if nivel == 0:
            return inicio, posicion + 1
    raise AnalisisCError(f"la definicion de '{nombre}' no cierra su llave")


# ---------------------------------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------------------------------


def precedencia(expr: Expr) -> int:
    """
    Da la precedencia con que se escribe una expresion (mayor liga mas fuerte).

    Contexto:
        ``imprimir_expresion`` decide con ella si hacen falta parentesis.

    Args:
        expr (Expr): Expresion.

    Returns:
        int: Nivel de precedencia.

    Ejemplo:
        nivel = precedencia(Binario("+", Id("a"), Id("b")))
    """
    if isinstance(expr, Binario):
        return PRECEDENCIA_BINARIA[expr.op]
    if isinstance(expr, Asigna):
        return PRECEDENCIA_ASIGNACION
    if isinstance(expr, Ternario):
        return PRECEDENCIA_TERNARIO
    if isinstance(expr, Unario | Conversion):
        return PRECEDENCIA_UNARIA
    if isinstance(expr, Postfijo | Llamada | Indice | Miembro):
        return PRECEDENCIA_POSTFIJA
    return PRECEDENCIA_ATOMO


def imprimir_expresion(expr: Expr, minimo: int = 0) -> str:
    """
    Escribe una expresion con los parentesis estrictamente necesarios.

    Contexto:
        Segundo paso del permutador: de aqui sale el texto de cada variante.

    Args:
        expr (Expr): Expresion.
        minimo (int, opcional): Precedencia minima que exige el contexto.

    Returns:
        str: Texto C de la expresion.

    Ejemplo:
        texto = imprimir_expresion(Binario("+", Id("a"), Num("1")))
    """
    texto = _texto_expresion(expr)
    return f"({texto})" if precedencia(expr) < minimo else texto


def _operando(operando: Expr, op_padre: str, minimo: int) -> str:
    """Operando de un binario; un operador de bits bajo otro operador distinto lleva parentesis."""
    if isinstance(operando, Binario) and operando.op in OPERADORES_DE_BITS and operando.op != op_padre:
        return f"({_texto_expresion(operando)})"
    return imprimir_expresion(operando, minimo)


def _texto_expresion(expr: Expr) -> str:  # noqa: PLR0911 - despachador por tipo de nodo
    """Texto de una expresion sin envolverla en parentesis."""
    nivel = precedencia(expr)
    if isinstance(expr, Id):
        return expr.nombre
    if isinstance(expr, Num | Texto):
        return expr.texto
    if isinstance(expr, Binario):
        separador = ", " if expr.op == "," else f" {expr.op} "
        return f"{_operando(expr.izq, expr.op, nivel)}{separador}{_operando(expr.der, expr.op, nivel + 1)}"
    if isinstance(expr, Asigna):
        return (
            f"{imprimir_expresion(expr.destino, PRECEDENCIA_TERNARIO)} {expr.op} "
            f"{imprimir_expresion(expr.valor, PRECEDENCIA_ASIGNACION)}"
        )
    if isinstance(expr, Ternario):
        return (
            f"{imprimir_expresion(expr.cond, nivel + 1)} ? {imprimir_expresion(expr.si, 1)} : "
            f"{imprimir_expresion(expr.no, nivel)}"
        )
    if isinstance(expr, Unario):
        operando = imprimir_expresion(expr.operando, nivel)
        if expr.op[0] in "+-&" and operando.startswith(expr.op[0]):
            operando = f"({operando})"
        return f"{expr.op}{operando}"
    if isinstance(expr, Conversion):
        return f"({expr.tipo}){imprimir_expresion(expr.operando, nivel)}"
    if isinstance(expr, Postfijo):
        return f"{imprimir_expresion(expr.operando, nivel)}{expr.op}"
    if isinstance(expr, Llamada):
        argumentos = ", ".join(imprimir_expresion(a, PRECEDENCIA_ASIGNACION) for a in expr.args)
        return f"{imprimir_expresion(expr.funcion, nivel)}({argumentos})"
    if isinstance(expr, Indice):
        return f"{imprimir_expresion(expr.base, nivel)}[{imprimir_expresion(expr.indice)}]"
    assert isinstance(expr, Miembro)  # noqa: S101 - ultima variante del arbol de expresiones
    flecha = "->" if expr.flecha else "."
    return f"{imprimir_expresion(expr.base, nivel)}{flecha}{expr.campo}"


def _lineas_comentarios(comentarios: tuple[str, ...], sangria: str) -> list[str]:
    """Comentarios que preceden a una sentencia, una linea por comentario de linea."""
    lineas: list[str] = []
    for comentario in comentarios:
        partes = comentario.split("\n")
        lineas.append(f"{sangria}{partes[0]}")
        for linea in partes[1:]:
            texto = linea.strip()
            lineas.append(f"{sangria}{' ' if texto.startswith('*') else '   '}{texto}")
    return lineas


def _sentencia_simple(sentencia: Sentencia) -> str | None:  # noqa: PLR0911 - despachador por tipo de nodo
    """Texto de las sentencias de una sola linea, o ``None`` si es una estructura de control."""
    if isinstance(sentencia, Decl):
        estrellas = "*" * sentencia.estrellas
        inicial = ""
        if sentencia.inicial is not None:
            inicial = f" = {imprimir_expresion(sentencia.inicial, PRECEDENCIA_ASIGNACION)}"
        nombre = sentencia.declarador or f"{sentencia.nombre}{sentencia.sufijo}"
        return f"{sentencia.base}{estrellas} {nombre}{inicial};"
    if isinstance(sentencia, Expresion):
        return f"{imprimir_expresion(sentencia.expr)};"
    if isinstance(sentencia, Devolver):
        return "return;" if sentencia.valor is None else f"return {imprimir_expresion(sentencia.valor)};"
    if isinstance(sentencia, Romper):
        return "break;"
    if isinstance(sentencia, Continuar):
        return "continue;"
    if isinstance(sentencia, Saltar):
        return f"goto {sentencia.etiqueta};"
    if isinstance(sentencia, Etiqueta):
        return f"{sentencia.nombre}:"
    if isinstance(sentencia, Caso):
        return "default:" if sentencia.valor is None else f"case {imprimir_expresion(sentencia.valor)}:"
    if isinstance(sentencia, Vacia):
        return ";"
    return None


def imprimir_bloque(bloque: Bloque, nivel: int) -> list[str]:
    """
    Escribe las sentencias de un bloque, sin las llaves, una linea por elemento.

    Contexto:
        Usada por ``imprimir_funcion`` y por las estructuras de control.

    Args:
        bloque (Bloque): Bloque.
        nivel (int): Nivel de sangria de las sentencias.

    Returns:
        list[str]: Lineas de texto.

    Ejemplo:
        lineas = imprimir_bloque(funcion.cuerpo, 1)
    """
    lineas: list[str] = []
    for sentencia in bloque.items:
        lineas.extend(_imprimir_sentencia(sentencia, nivel))
    lineas.extend(_lineas_comentarios(bloque.finales, SANGRIA * nivel))
    return lineas


def _cuerpo_de(cabecera: str, cuerpo: Bloque, nivel: int, cierre: str = "}") -> list[str]:
    """Estructura de control con su cuerpo entre llaves."""
    sangria = SANGRIA * nivel
    apertura = f"{cabecera} {{" if cabecera else "{"
    return [f"{sangria}{apertura}", *imprimir_bloque(cuerpo, nivel + 1), f"{sangria}{cierre}"]


def _imprimir_sentencia(sentencia: Sentencia, nivel: int) -> list[str]:  # noqa: PLR0911
    """Lineas de una sentencia con su sangria y los comentarios que la preceden.

    Las etiquetas (``case``, ``default`` y las de ``goto``) se escriben un nivel por fuera del resto.
    """
    es_etiqueta = isinstance(sentencia, Caso | Etiqueta)
    sangria = SANGRIA * (nivel - 1 if es_etiqueta else nivel)
    lineas = _lineas_comentarios(sentencia.comentarios, sangria)
    if isinstance(sentencia, Preprocesador):
        return [*lineas, sentencia.texto]
    simple = _sentencia_simple(sentencia)
    if simple is not None:
        return [*lineas, f"{sangria}{simple}"]
    if isinstance(sentencia, Bloque):
        return [*lineas, *_cuerpo_de("", sentencia, nivel)]
    if isinstance(sentencia, Si):
        return [*lineas, *_imprimir_si(sentencia, nivel)]
    if isinstance(sentencia, Mientras):
        cabecera = f"while ({imprimir_expresion(sentencia.cond)})"
        return [*lineas, *_cuerpo_de(cabecera, sentencia.cuerpo, nivel)]
    if isinstance(sentencia, HacerMientras):
        return [
            *lineas,
            *_cuerpo_de("do", sentencia.cuerpo, nivel, f"}} while ({imprimir_expresion(sentencia.cond)});"),
        ]
    if isinstance(sentencia, Para):
        partes = [
            imprimir_expresion(e) if e is not None else ""
            for e in (sentencia.inicio, sentencia.cond, sentencia.paso)
        ]
        cabecera = "for (" + "; ".join(partes) + ")"
        return [*lineas, *_cuerpo_de(cabecera, sentencia.cuerpo, nivel)]
    assert isinstance(sentencia, Seleccion)  # noqa: S101 - ultima variante de sentencia
    return [*lineas, *_cuerpo_de(f"switch ({imprimir_expresion(sentencia.cond)})", sentencia.cuerpo, nivel)]


def _cabecera_con_condicion(palabra: str, cond: Expr, nivel: int) -> list[str]:
    """
    Linea de apertura de un ``if``; una cadena larga de ``&&``/``||`` se reparte en varias lineas.

    Cada linea de continuacion empieza por el operador y se sangra dos niveles mas que la apertura.
    """
    sangria = SANGRIA * nivel
    una_linea = f"{sangria}{palabra} ({imprimir_expresion(cond)}) {{"
    if len(una_linea) <= ANCHO_DE_LINEA:
        return [una_linea]
    operandos: list[tuple[str, Expr]] = []
    pendiente = cond
    ligadura = 0
    # Solo se baja por la izquierda mientras el operando se escriba sin parentesis bajo el operador que
    # lo contiene: (a || b) && c lleva parentesis y repartirlo como a || b && c cambiaria su significado.
    while (
        isinstance(pendiente, Binario)
        and pendiente.op in ("&&", "||")
        and PRECEDENCIA_BINARIA[pendiente.op] >= ligadura
    ):
        operandos.append((pendiente.op, pendiente.der))
        ligadura = PRECEDENCIA_BINARIA[pendiente.op]
        pendiente = pendiente.izq
    if not operandos:
        return [una_linea]
    nivel_y = PRECEDENCIA_BINARIA["&&"] + 1
    lineas = [f"{sangria}{palabra} ({_operando(pendiente, '&&', nivel_y)}"]
    for op, operando in reversed(operandos):
        siguiente = _operando(operando, op, PRECEDENCIA_BINARIA[op] + 1)
        lineas.append(f"{sangria}{SANGRIA * 2}{op} {siguiente}")
    lineas[-1] += ") {"
    return lineas


def _imprimir_si(sentencia: Si, nivel: int) -> list[str]:
    """
    ``if`` con su rama ``else``; un ``else`` que solo contiene un ``if`` se escribe ``else if``.

    No se encadena si el ``if`` interno o el bloque ``else`` llevan comentarios: ``else if`` no tiene
    donde escribirlos.
    """
    sangria = SANGRIA * nivel
    lineas = _cabecera_con_condicion("if", sentencia.cond, nivel)
    lineas.extend(imprimir_bloque(sentencia.entonces, nivel + 1))
    sino = sentencia.sino
    while sino is not None:
        if (
            len(sino.items) == 1
            and isinstance(sino.items[0], Si)
            and not sino.items[0].comentarios
            and not sino.finales
        ):
            encadenado = sino.items[0]
            lineas.extend(_cabecera_con_condicion("} else if", encadenado.cond, nivel))
            lineas.extend(imprimir_bloque(encadenado.entonces, nivel + 1))
            sino = encadenado.sino
        else:
            lineas.append(f"{sangria}}} else {{")
            lineas.extend(imprimir_bloque(sino, nivel + 1))
            sino = None
    lineas.append(f"{sangria}}}")
    return lineas


def imprimir_funcion(funcion: Funcion) -> str:
    """
    Escribe la definicion completa de una funcion.

    Contexto:
        Genera el texto que sustituye a la definicion original en cada variante y en ``mejor.c``.

    Args:
        funcion (Funcion): Arbol de la funcion.

    Returns:
        str: Firma y cuerpo, sin salto de linea final.

    Ejemplo:
        texto = imprimir_funcion(analizar_funcion("s32 f(void) { return 0; }", "f"))
    """
    return "\n".join([f"{funcion.cabecera}", "{", *imprimir_bloque(funcion.cuerpo, 1), "}"])


# ---------------------------------------------------------------------------------------------------
# Recorrido
# ---------------------------------------------------------------------------------------------------


def hijos(expr: Expr) -> list[Expr]:  # noqa: PLR0911 - despachador por tipo de nodo
    """
    Da las subexpresiones directas de una expresion, de izquierda a derecha.

    Contexto:
        Base de todos los recorridos del analisis y de las mutaciones.

    Args:
        expr (Expr): Expresion.

    Returns:
        list[Expr]: Subexpresiones (vacio para los atomos).

    Ejemplo:
        partes = hijos(Binario("+", Id("a"), Id("b")))
    """
    if isinstance(expr, Unario | Postfijo | Conversion):
        return [expr.operando]
    if isinstance(expr, Binario):
        return [expr.izq, expr.der]
    if isinstance(expr, Asigna):
        return [expr.destino, expr.valor]
    if isinstance(expr, Ternario):
        return [expr.cond, expr.si, expr.no]
    if isinstance(expr, Llamada):
        return [expr.funcion, *expr.args]
    if isinstance(expr, Indice):
        return [expr.base, expr.indice]
    if isinstance(expr, Miembro):
        return [expr.base]
    return []


def recorrer(expr: Expr) -> Iterator[Expr]:
    """
    Recorre una expresion y todas sus subexpresiones en preorden.

    Contexto:
        Selecciona sitios de mutacion y calcula conjuntos de identificadores y efectos.

    Args:
        expr (Expr): Raiz.

    Yields:
        Expr: Cada nodo, empezando por la raiz.

    Ejemplo:
        nombres = {n.nombre for n in recorrer(expr) if isinstance(n, Id)}
    """
    yield expr
    for hijo in hijos(expr):
        yield from recorrer(hijo)


def reemplazar_hijo(padre: object, viejo: Expr, nuevo: Expr) -> bool:
    """
    Sustituye en un nodo la referencia directa a ``viejo`` por ``nuevo``.

    Contexto:
        Los nodos son mutables; las mutaciones cambian un sitio concreto sin reconstruir el arbol.

    Args:
        padre (object): Nodo de expresion o sentencia que contiene a ``viejo``.
        viejo (Expr): Hijo a sustituir (se busca por identidad).
        nuevo (Expr): Reemplazo.

    Returns:
        bool: Verdadero si ``viejo`` era hijo directo de ``padre``.

    Ejemplo:
        reemplazar_hijo(suma, suma.izq, Num("0"))
    """
    for nombre, valor in vars(padre).items():
        if valor is viejo:
            setattr(padre, nombre, nuevo)
            return True
        if isinstance(valor, list):
            for i, elemento in enumerate(valor):
                if elemento is viejo:
                    valor[i] = nuevo
                    return True
    return False


def expresiones_de(sentencia: Sentencia) -> list[Expr]:  # noqa: PLR0911 - despachador por tipo de nodo
    """
    Da las expresiones raiz que contiene directamente una sentencia (sin entrar en sus bloques).

    Contexto:
        Permite recorrer todas las expresiones de una funcion sentencia por sentencia.

    Args:
        sentencia (Sentencia): Sentencia.

    Returns:
        list[Expr]: Expresiones raiz en orden de aparicion.

    Ejemplo:
        raices = expresiones_de(Expresion(expr=Id("x")))
    """
    if isinstance(sentencia, Decl):
        return [sentencia.inicial] if sentencia.inicial is not None else []
    if isinstance(sentencia, Expresion):
        return [sentencia.expr]
    if isinstance(sentencia, Devolver):
        return [sentencia.valor] if sentencia.valor is not None else []
    if isinstance(sentencia, Si | Mientras | HacerMientras | Seleccion):
        return [sentencia.cond]
    if isinstance(sentencia, Para):
        return [e for e in (sentencia.inicio, sentencia.cond, sentencia.paso) if e is not None]
    if isinstance(sentencia, Caso):
        return [sentencia.valor] if sentencia.valor is not None else []
    return []


def bloques_hijos(sentencia: Sentencia) -> list[Bloque]:
    """
    Da los bloques que contiene directamente una sentencia.

    Contexto:
        Permite descender por la estructura de la funcion.

    Args:
        sentencia (Sentencia): Sentencia.

    Returns:
        list[Bloque]: Bloques hijos (cuerpo, ramas), vacio para las sentencias simples.

    Ejemplo:
        ramas = bloques_hijos(Si(cond=Id("c"), entonces=Bloque()))
    """
    if isinstance(sentencia, Si):
        return [sentencia.entonces] + ([sentencia.sino] if sentencia.sino is not None else [])
    if isinstance(sentencia, Mientras | HacerMientras | Para | Seleccion):
        return [sentencia.cuerpo]
    if isinstance(sentencia, Bloque):
        return [sentencia]
    return []


def todos_los_bloques(bloque: Bloque) -> Iterator[Bloque]:
    """
    Recorre un bloque y todos los que contiene, en preorden.

    Contexto:
        Las mutaciones eligen un bloque de la funcion para actuar sobre sus sentencias.

    Args:
        bloque (Bloque): Raiz.

    Yields:
        Bloque: Cada bloque, empezando por el recibido.

    Ejemplo:
        cantidad = len(list(todos_los_bloques(funcion.cuerpo)))
    """
    yield bloque
    for sentencia in bloque.items:
        for hijo in bloques_hijos(sentencia):
            if hijo is not bloque:
                yield from todos_los_bloques(hijo)


def es_identificador(texto: str) -> bool:
    """
    Indica si un texto es un identificador C valido.

    Contexto:
        Los nombres de funcion y de temporales se validan antes de escribirse en el C.

    Args:
        texto (str): Texto a comprobar.

    Returns:
        bool: Verdadero si es un identificador.

    Ejemplo:
        valido = es_identificador("func_ejemplo")
    """
    return _PATRON_IDENTIFICADOR.match(texto) is not None

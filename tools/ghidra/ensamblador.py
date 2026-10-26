"""Lectura del desensamblado de texto que produce el desensamblador.

Trabaja sobre el texto de ``text.s`` (formato de splat/spimdisasm): lo divide en funciones y
extrae de cada una los saltos (``jal``, ``j``, ``jalr``, ``jr``) y las referencias simbolicas a
direcciones (``%hi``/``%lo``). Es logica pura: no abre archivos, por lo que se prueba con texto
sintetico. Toda entrada se trata como hostil: se acotan lineas y bytes y se rechazan etiquetas mal
formadas con un ``ValueError`` que nombra el problema sin volcar el contenido.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

MAX_LINEAS_ASM: Final[int] = 500_000
"""Cota de lineas aceptadas: el desensamblado real tiene unas 85.000."""

MAX_BYTES_ASM: Final[int] = 64 * 1024 * 1024
"""Cota de tamano del texto: el real ronda 5 MiB."""

_IDENTIFICADOR: Final[str] = r"[A-Za-z_][A-Za-z0-9_]*"
_PATRON_INICIO: Final[re.Pattern[str]] = re.compile(rf"^glabel (?P<nombre>{_IDENTIFICADOR})$")
_PATRON_FIN: Final[re.Pattern[str]] = re.compile(rf"^endlabel (?P<nombre>{_IDENTIFICADOR})$")
_PATRON_INSTRUCCION: Final[re.Pattern[str]] = re.compile(
    r"^\s*/\* [0-9A-F]+ (?P<direccion>[0-9A-F]{8}) [0-9A-F]{8} \*/\s+"
    r"(?P<mnemonico>[a-z][a-z0-9.]*)(?:\s+(?P<operandos>[^/]*?))?\s*(?:/\*.*\*/)?\s*$"
)
_PATRON_REFERENCIA: Final[re.Pattern[str]] = re.compile(
    rf"%(?:hi|lo)\((?P<simbolo>{_IDENTIFICADOR})(?: \+ 0x(?P<desplazamiento>[0-9A-F]+))?\)"
)
_PATRON_ALTA: Final[re.Pattern[str]] = re.compile(r"\(0x(?P<direccion>[0-9A-F]{8}) >> 16\)")
_PATRON_AUTOMATICO: Final[re.Pattern[str]] = re.compile(r"^(?:D|jtbl|func)_(?P<direccion>[0-9A-F]{8})$")
_PATRON_DESTINO: Final[re.Pattern[str]] = re.compile(
    rf"^(?P<simbolo>\.?{_IDENTIFICADOR})(?: \+ 0x(?P<desplazamiento>[0-9A-F]+))?$"
)
_PATRON_GP: Final[re.Pattern[str]] = re.compile(r"(?P<signo>-)?0x(?P<valor>[0-9A-F]+)\(\$gp\)")
_REGISTRO_RETORNO: Final[str] = "$ra"

VALOR_GP: Final[int] = 0x80069320
"""Valor que el arranque del programa deja en ``$gp`` (ver ``docs/MAPA_MEMORIA.md``)."""


@dataclass(frozen=True)
class FuncionAsm:
    """Texto de una funcion del desensamblado, desde su ``glabel`` hasta su ``endlabel``."""

    nombre: str
    direccion: int
    lineas: tuple[str, ...]


@dataclass(frozen=True)
class Instruccion:
    """Una instruccion decodificada del texto: direccion, mnemonico y operandos."""

    direccion: int
    mnemonico: str
    operandos: str


@dataclass(frozen=True)
class Salto:
    """Transferencia de control que sale de la funcion o es indirecta.

    ``destino`` es la direccion resuelta del destino y es ``None`` para ``jalr``/``jr`` o si el
    simbolo no figura en la tabla.
    """

    direccion: int
    tipo: str
    destino: int | None


@dataclass(frozen=True)
class Referencia:
    """Referencia ``%hi``/``%lo`` resuelta: simbolo, direccion efectiva y desplazamiento."""

    simbolo: str
    direccion: int
    desplazamiento: int


@dataclass(frozen=True)
class AnalisisFuncion:
    """Resultado de leer una funcion: saltos, referencias y simbolos que no se pudieron resolver."""

    saltos: tuple[Salto, ...]
    referencias: tuple[Referencia, ...]
    sin_resolver: int


def dividir_por_funcion(texto: str) -> list[FuncionAsm]:
    """
    Divide el texto del desensamblado en funciones.

    Contexto:
        Primer paso de ``borradores`` y de ``grafo``: ambos trabajan sobre una copia propia del
        desensamblado, nunca sobre el ``asm/`` del repositorio.

    Args:
        texto (str): Contenido completo de ``text.s``.

    Returns:
        list[FuncionAsm]: Funciones en el orden del texto. Las lineas que quedan fuera de un
        ``glabel``/``endlabel`` (palabras de datos incrustadas, macros) se descartan.

    Raises:
        ValueError: Si el texto excede las cotas, si un ``glabel`` aparece dentro de otra funcion,
            si un ``endlabel`` no coincide con su ``glabel``, si hay nombres repetidos o si una
            funcion no contiene ninguna instruccion.

    Ejemplo:
        funciones = dividir_por_funcion(Path("text.s").read_text(encoding="utf-8"))
    """
    if len(texto) > MAX_BYTES_ASM:
        raise ValueError(f"desensamblado: el texto excede {MAX_BYTES_ASM} bytes")
    lineas = texto.splitlines()
    if len(lineas) > MAX_LINEAS_ASM:
        raise ValueError(f"desensamblado: {len(lineas)} lineas exceden el maximo de {MAX_LINEAS_ASM}")
    funciones: list[FuncionAsm] = []
    vistos: set[str] = set()
    actual: str | None = None
    cuerpo: list[str] = []
    for numero, linea in enumerate(lineas, start=1):
        inicio = _PATRON_INICIO.match(linea)
        fin = _PATRON_FIN.match(linea)
        if inicio is not None:
            if actual is not None:
                raise ValueError(f"desensamblado linea {numero}: glabel dentro de la funcion {actual}")
            actual = inicio["nombre"]
            if actual in vistos:
                raise ValueError(f"desensamblado linea {numero}: funcion {actual} repetida")
            vistos.add(actual)
            cuerpo = [linea]
        elif fin is not None:
            if actual is None or actual != fin["nombre"]:
                raise ValueError(f"desensamblado linea {numero}: endlabel sin su glabel")
            cuerpo.append(linea)
            funciones.append(_construir_funcion(actual, cuerpo))
            actual = None
        elif actual is not None:
            cuerpo.append(linea)
    if actual is not None:
        raise ValueError(f"desensamblado: la funcion {actual} no termina con endlabel")
    return funciones


def _construir_funcion(nombre: str, cuerpo: list[str]) -> FuncionAsm:
    """Crea la funcion tomando la direccion de su primera instruccion."""
    instrucciones = leer_instrucciones_de(cuerpo)
    if not instrucciones:
        raise ValueError(f"desensamblado: la funcion {nombre} no contiene instrucciones")
    return FuncionAsm(nombre=nombre, direccion=instrucciones[0].direccion, lineas=tuple(cuerpo))


def leer_instrucciones_de(lineas: list[str]) -> list[Instruccion]:
    """
    Extrae las instrucciones de un conjunto de lineas de desensamblado.

    Contexto:
        Apoyo de ``dividir_por_funcion`` y ``leer_instrucciones``; ignora etiquetas locales,
        directivas y palabras de datos.

    Args:
        lineas (list[str]): Lineas de texto.

    Returns:
        list[Instruccion]: Instrucciones con direccion, mnemonico y operandos, en orden.

    Ejemplo:
        instrucciones = leer_instrucciones_de(["/* 0 80014A00 0800E003 */  jr $ra"])
    """
    resultado: list[Instruccion] = []
    for linea in lineas:
        coincidencia = _PATRON_INSTRUCCION.match(linea)
        if coincidencia is not None:
            resultado.append(
                Instruccion(
                    direccion=int(coincidencia["direccion"], 16),
                    mnemonico=coincidencia["mnemonico"],
                    operandos=(coincidencia["operandos"] or "").strip(),
                )
            )
    return resultado


def leer_instrucciones(funcion: FuncionAsm) -> list[Instruccion]:
    """
    Devuelve las instrucciones de una funcion.

    Contexto:
        Lo usan el analisis de saltos y la insercion de etiquetas para los borradores.

    Args:
        funcion (FuncionAsm): Funcion ya dividida.

    Returns:
        list[Instruccion]: Instrucciones en orden de direccion.

    Ejemplo:
        instrucciones = leer_instrucciones(funcion)
    """
    return leer_instrucciones_de(list(funcion.lineas))


def resolver_simbolo(simbolo: str, nombres: Mapping[str, int]) -> int | None:
    """
    Convierte el nombre de un simbolo en su direccion.

    Contexto:
        Los nombres automaticos (``D_``, ``jtbl_``, ``func_`` mas ocho digitos hexadecimales)
        llevan la direccion en el nombre; los demas se buscan en ``config/symbols.txt``.

    Args:
        simbolo (str): Nombre tal como aparece en el desensamblado.
        nombres (Mapping[str, int]): Nombre a direccion de la tabla de simbolos.

    Returns:
        int | None: La direccion, o ``None`` si el nombre no es conocido.

    Ejemplo:
        direccion = resolver_simbolo("D_80069348", {})  # 0x80069348
    """
    automatico = _PATRON_AUTOMATICO.match(simbolo)
    if automatico is not None:
        return int(automatico["direccion"], 16)
    return nombres.get(simbolo)


def analizar_funcion(funcion: FuncionAsm, nombres: Mapping[str, int]) -> AnalisisFuncion:
    """
    Extrae saltos y referencias simbolicas de una funcion.

    Contexto:
        Base del grafo de llamadas: los ``jal``/``j`` hacia otra funcion son aristas, los
        ``jalr``/``jr`` a registro son llamadas indirectas y las referencias ``%hi``/``%lo`` , los
        accesos relativos a ``$gp`` y la forma ``(0xDIRECCION >> 16)`` que el desensamblador deja
        cuando no puede emparejar la parte baja) son datos usados o funciones cuyo puntero se toma.

    Args:
        funcion (FuncionAsm): Funcion ya dividida.
        nombres (Mapping[str, int]): Nombre a direccion de la tabla de simbolos.

    Returns:
        AnalisisFuncion: Saltos (sin los ``j`` a etiquetas locales ni ``jr $ra``) y referencias
        (cada simbolo resuelto, una vez por mencion).

    Ejemplo:
        analisis = analizar_funcion(funcion, nombres)
    """
    saltos: list[Salto] = []
    referencias: list[Referencia] = []
    sin_resolver = 0
    for instruccion in leer_instrucciones(funcion):
        if instruccion.mnemonico in ("jal", "j"):
            salto = _salto_directo(instruccion, nombres)
            if salto is not None:
                saltos.append(salto)
        elif instruccion.mnemonico in ("jalr", "jr") and instruccion.operandos != _REGISTRO_RETORNO:
            saltos.append(Salto(instruccion.direccion, instruccion.mnemonico, None))
        for coincidencia in _PATRON_REFERENCIA.finditer(instruccion.operandos):
            desplazamiento = int(coincidencia["desplazamiento"] or "0", 16)
            base = resolver_simbolo(coincidencia["simbolo"], nombres)
            if base is None:
                sin_resolver += 1
            else:
                referencias.append(Referencia(coincidencia["simbolo"], base + desplazamiento, desplazamiento))
        for relativo in _PATRON_GP.finditer(instruccion.operandos):
            desplazamiento_gp = int(relativo["valor"], 16) * (-1 if relativo["signo"] else 1)
            referencias.append(Referencia(f"gp{desplazamiento_gp:+#x}", VALOR_GP + desplazamiento_gp, 0))
        for alta in _PATRON_ALTA.finditer(instruccion.operandos):
            referencias.append(Referencia(f"0x{alta['direccion']}", int(alta["direccion"], 16), 0))
    return AnalisisFuncion(tuple(saltos), tuple(referencias), sin_resolver)


def _salto_directo(instruccion: Instruccion, nombres: Mapping[str, int]) -> Salto | None:
    """Convierte un ``jal``/``j`` en salto; ``None`` si el destino es una etiqueta local."""
    destino = _PATRON_DESTINO.match(instruccion.operandos)
    if destino is None:
        return Salto(instruccion.direccion, instruccion.mnemonico, None)
    if destino["simbolo"].startswith("."):
        return None
    direccion = resolver_simbolo(destino["simbolo"], nombres)
    if direccion is not None:
        direccion += int(destino["desplazamiento"] or "0", 16)
    return Salto(instruccion.direccion, instruccion.mnemonico, direccion)

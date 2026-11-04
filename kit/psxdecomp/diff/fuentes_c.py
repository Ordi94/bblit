"""Analisis puro de los archivos C del juego: que funciones estan descompiladas y cuales no.

El estado de cada funcion se deriva del propio texto de ``src/*.c`` (nunca de una lista
aparte), de modo que el progreso y el diff no pueden desincronizarse del codigo. Tres estados:

* ``C``: la funcion esta definida en C en la construccion normal; como la construccion es
  byte a byte, que compile ya prueba que coincide con el original.
* ``NO_COINCIDENTE``: hay un intento en C bajo ``#ifdef NON_MATCHING`` y la construccion normal
  sigue usando ``INCLUDE_ASM``.
* ``ENSAMBLADOR``: solo existe ``INCLUDE_ASM``.

Las reglas de deteccion de definiciones replican las del particionador (splat), que lee el
mismo texto para decidir que funciones ya estan en C: si una definicion no la reconoce, el
particionador sigue emitiendo el simbolo como indefinido y el enlazador falla con una
definicion duplicada. Por eso una definicion que el particionador no veria se rechaza aqui con
un mensaje que explica como escribirla.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

MAX_BYTES_FUENTE = 2 * 1024 * 1024
MACRO_NO_COINCIDENTE = "NON_MATCHING"

_COMENTARIOS = re.compile(
    r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
    re.DOTALL | re.MULTILINE,
)
# Misma expresion que usa el particionador para localizar definiciones de funcion: tipo de
# retorno de UNA palabra al inicio de la linea, luego el nombre y la lista de parametros.
_DEFINICION_PARTICIONADOR = re.compile(r"^(?:static\s+)?[^\s]+\s+([^\s(]+)\(([^;)]*)\)[^;]+?{", re.MULTILINE)
# Busqueda amplia: cualquier identificador seguido de parametros y de una llave de apertura.
_DEFINICION_AMPLIA = re.compile(r"\b([A-Za-z_]\w*)\s*\(([^;(){}]*)\)\s*\{")
_INCLUDE_ASM = re.compile(r'\bINCLUDE_ASM\(\s*"[^"]*"\s*,\s*([A-Za-z_]\w*)\s*\)')
_IDENTIFICADOR = re.compile(r"^[A-Za-z_]\w*$")
_PRIMER_COMENTARIO = re.compile(r"/\*(.*?)\*/", re.DOTALL)
# Comentario (de bloque o de linea) que abre la rama de C de un bloque NON_MATCHING.
_COMENTARIO_INICIAL = re.compile(r"\A\s*(/\*.*?\*/|//[^\n]*)", re.DOTALL)
# Lo primero que debe decir ese comentario: la puntuacion pendiente del intento.
_PENDIENTE = re.compile(r"\APendiente:\s*puntuacion\s+(\d+)\b")
# Marca de una rutina que el original escribio a mano ("Rutina de GTE escrita a mano en el original").
_MANUSCRITA = re.compile(
    r"\brutina(?:\s+de\s+\w+)?\s+escrita\s+a\s+mano\s+en\s+el\s+original\b", re.IGNORECASE
)
MAX_CARACTERES_MOTIVO = 600
_PALABRAS_DE_CONTROL = frozenset({"if", "while", "for", "switch", "return", "sizeof", "else", "do"})


class EstadoFuncion(Enum):
    """Situacion de una funcion respecto a su descompilacion.

    Attributes:
        C: definida en C y compilada en la construccion normal.
        NO_COINCIDENTE: intento en C bajo ``NON_MATCHING``; la construccion usa el ensamblador.
        ENSAMBLADOR: solo ``INCLUDE_ASM``.
    """

    C = "c"
    NO_COINCIDENTE = "no_coincidente"
    ENSAMBLADOR = "ensamblador"


class MarcaAsm(Enum):
    """Lo que dice el comentario que precede a una funcion que sigue en ``INCLUDE_ASM``.

    Attributes:
        MANUSCRITA: el comentario declara que la rutina esta escrita a mano en el original.
        JUSTIFICADA: hay un comentario, pero no declara una rutina manuscrita.
        SIN_COMENTARIO: ninguna linea de comentario inmediatamente encima.
    """

    MANUSCRITA = "manuscrita"
    JUSTIFICADA = "justificada"
    SIN_COMENTARIO = "sin_comentario"


@dataclass(frozen=True)
class BloqueNoCoincidente:
    """Un bloque ``#ifdef NON_MATCHING ... #else INCLUDE_ASM(...) #endif`` de un archivo C.

    Attributes:
        funcion: Funcion del ``INCLUDE_ASM`` de la rama ``#else``.
        linea: Linea (desde 1) del ``#ifdef``.
        rama_c: Texto de la rama de C, tal como esta escrito (con sus comentarios).
    """

    funcion: str
    linea: int
    rama_c: str


def _quitar_comentarios(texto: str) -> str:
    """Sustituye cada comentario por un espacio conservando las cadenas literales."""

    def reemplazo(coincidencia: re.Match[str]) -> str:
        return " " if coincidencia.group(0).startswith("/") else coincidencia.group(0)

    return _COMENTARIOS.sub(reemplazo, texto)


def _texto_activo(texto: str, no_coincidente: bool) -> str:
    """
    Devuelve el texto con las lineas de las ramas inactivas reemplazadas por lineas vacias.

    Contexto:
        Evalua solo ``#ifdef/#ifndef NON_MATCHING``, ``#else`` y ``#endif``; cualquier otra
        condicion del preprocesador se trata como verdadera. Conserva el numero de lineas.

    Args:
        texto (str): Fuente sin comentarios.
        no_coincidente (bool): Si ``NON_MATCHING`` se considera definida.

    Returns:
        str: Fuente con solo las lineas activas.

    Raises:
        ValueError: Si hay ``#else`` o ``#endif`` sin condicion abierta, una condicion sin cerrar
            o una condicion sobre ``NON_MATCHING`` que no sea ``#ifdef``/``#ifndef``.
    """
    # Cada elemento: (la rama actual esta activa, la condicion depende de NON_MATCHING).
    pila: list[tuple[bool, bool]] = []
    salida: list[str] = []
    for numero, linea in enumerate(texto.splitlines(), start=1):
        directiva = linea.strip()
        if directiva.startswith("#"):
            palabras = directiva[1:].split()
            nombre = palabras[0] if palabras else ""
            if nombre in ("ifdef", "ifndef", "if"):
                depende = nombre != "if" and len(palabras) > 1 and palabras[1] == MACRO_NO_COINCIDENTE
                if MACRO_NO_COINCIDENTE in directiva and not depende:
                    raise ValueError(f"linea {numero}: use '#ifdef {MACRO_NO_COINCIDENTE}' o '#ifndef'")
                activa = (no_coincidente if nombre == "ifdef" else not no_coincidente) if depende else True
                pila.append((activa, depende))
            elif nombre == "else":
                if not pila:
                    raise ValueError(f"linea {numero}: '#else' sin condicion abierta")
                activa, depende = pila[-1]
                pila[-1] = ((not activa) if depende else activa, depende)
            elif nombre == "endif":
                if not pila:
                    raise ValueError(f"linea {numero}: '#endif' sin condicion abierta")
                pila.pop()
            salida.append("")
            continue
        salida.append(linea if all(activa for activa, _ in pila) else "")
    if pila:
        raise ValueError("hay una condicion '#if' sin '#endif'")
    return "\n".join(salida)


def _definiciones(texto_activo: str) -> set[str]:
    """Nombres de las funciones definidas en el texto, validando que el particionador las vea."""
    vistas = {m.group(1) for m in _DEFINICION_PARTICIONADOR.finditer(texto_activo)}
    invalidas = sorted(nombre for nombre in vistas if not _IDENTIFICADOR.match(nombre))
    amplias = {m.group(1) for m in _DEFINICION_AMPLIA.finditer(texto_activo)} - _PALABRAS_DE_CONTROL
    invalidas += sorted(amplias - vistas)
    if invalidas:
        raise ValueError(
            f"la definicion de '{invalidas[0].lstrip('*')}' no la reconoceria el particionador: "
            "escriba el tipo de retorno como una sola palabra (use typedef) con el '*' pegado al "
            "tipo, por ejemplo 'Ranura* func_80036204(...)'"
        )
    return vistas


def analizar_fuente(texto: str) -> dict[str, EstadoFuncion]:
    """
    Determina el estado de cada funcion mencionada en un archivo C.

    Contexto:
        Es la unica fuente de verdad de ``progreso`` y de ``diff``. Se evalua el texto dos
        veces: con ``NON_MATCHING`` indefinida (la construccion normal) y definida (el intento).

    Args:
        texto (str): Contenido del archivo ``.c``.

    Returns:
        dict[str, EstadoFuncion]: Estado por nombre de funcion, en orden alfabetico.

    Raises:
        ValueError: Si el texto excede ``MAX_BYTES_FUENTE``, el preprocesador esta desbalanceado
            o una definicion no seria reconocida por el particionador.

    Ejemplo:
        estados = analizar_fuente('INCLUDE_ASM("asm/nonmatchings/a", func_80014AC4);')
    """
    if len(texto.encode("utf-8")) > MAX_BYTES_FUENTE:
        raise ValueError("el archivo C excede el tamano permitido")
    limpio = _quitar_comentarios(texto)
    normal = _texto_activo(limpio, no_coincidente=False)
    intento = _texto_activo(limpio, no_coincidente=True)
    definidas = _definiciones(normal)
    en_ensamblador = {m.group(1) for m in _INCLUDE_ASM.finditer(normal)}
    intentos = _definiciones(intento) - definidas
    estados: dict[str, EstadoFuncion] = {}
    huerfanas = intentos - en_ensamblador
    if huerfanas:
        raise ValueError(
            f"'{min(huerfanas)}' solo existe bajo {MACRO_NO_COINCIDENTE}: "
            "falta su INCLUDE_ASM en la rama #else"
        )
    for nombre in sorted(definidas | en_ensamblador):
        if nombre in en_ensamblador:
            estados[nombre] = (
                EstadoFuncion.NO_COINCIDENTE if nombre in intentos else EstadoFuncion.ENSAMBLADOR
            )
        else:
            estados[nombre] = EstadoFuncion.C
    return estados


def ubicar_funcion(
    estados_por_archivo: Mapping[str, Mapping[str, EstadoFuncion]], funcion: str
) -> tuple[str, EstadoFuncion]:
    """
    Busca en que archivo C esta una funcion.

    Contexto:
        ``diff`` necesita saber que archivo compilar para comparar la funcion pedida.

    Args:
        estados_por_archivo (Mapping[str, Mapping[str, EstadoFuncion]]): Estados por archivo
            (clave: ruta relativa como ``src/code_80014AC4.c``).
        funcion (str): Nombre de la funcion.

    Returns:
        tuple[str, EstadoFuncion]: Archivo y estado de la funcion.

    Raises:
        ValueError: Si ningun archivo menciona la funcion.

    Ejemplo:
        archivo, estado = ubicar_funcion(estados, "func_80036204")
    """
    for archivo in sorted(estados_por_archivo):
        estado = estados_por_archivo[archivo].get(funcion)
        if estado is not None:
            return archivo, estado
    raise ValueError(f"la funcion '{funcion}' no figura en ningun archivo de src/")


def analizar_fuentes(textos: Mapping[str, str]) -> dict[str, dict[str, EstadoFuncion]]:
    """
    Analiza el texto de todos los archivos C.

    Contexto:
        Punto comun de ``diff`` y ``progreso`` para obtener el estado de cada funcion.

    Args:
        textos (Mapping[str, str]): Texto por archivo (clave: ruta relativa).

    Returns:
        dict[str, dict[str, EstadoFuncion]]: Estado por funcion y archivo, ordenado por archivo.

    Raises:
        ValueError: Si algun archivo no se puede analizar; el mensaje nombra el archivo.

    Ejemplo:
        estados = analizar_fuentes({"src/a.c": texto})
    """
    estados: dict[str, dict[str, EstadoFuncion]] = {}
    for archivo in sorted(textos):
        try:
            estados[archivo] = analizar_fuente(textos[archivo])
        except ValueError as error:
            raise ValueError(f"{archivo}: {error}") from None
    return estados


def _enmascarar_comentarios(texto: str) -> str:
    """Sustituye cada caracter de un comentario por un espacio, conservando los saltos de linea."""

    def reemplazo(coincidencia: re.Match[str]) -> str:
        literal = coincidencia.group(0)
        return re.sub(r"[^\n]", " ", literal) if literal.startswith("/") else literal

    return _COMENTARIOS.sub(reemplazo, texto)


def _aplanar_comentario(cuerpo: str) -> str:
    """Une en una sola linea el cuerpo de un comentario, sin los asteriscos de margen."""
    lineas = (linea.strip().lstrip("*").strip() for linea in cuerpo.splitlines())
    return " ".join(linea for linea in lineas if linea)


@dataclass
class _Condicional:
    """Condicion ``#if``, ``#ifdef`` o ``#ifndef`` abierta durante el recorrido de un archivo."""

    es_no_coincidente: bool
    inicio: int
    otra_rama: int | None = None


def bloques_no_coincidentes(texto: str) -> list[BloqueNoCoincidente]:
    """
    Localiza cada bloque ``#ifdef NON_MATCHING ... #else INCLUDE_ASM(...) #endif`` de un archivo C.

    Contexto:
        Es la lectura estructural comun de ``progreso``: de ella salen el motivo de cada intento,
        la comprobacion de la linea ``Pendiente`` y la exclusion de estas funciones al clasificar los
        ``INCLUDE_ASM`` sueltos. Las directivas se leen con una pila, de modo que un
        ``NON_MATCHING`` anidado en otra condicion o en otro bloque cierra con su propio ``#endif``;
        los comentarios se enmascaran para que un ``#ifdef`` escrito dentro de uno no cuente. Un
        ``#ifdef NON_MATCHING`` sin rama ``#else`` con ``INCLUDE_ASM`` no es un intento de funcion y
        se ignora.

    Args:
        texto (str): Contenido del archivo ``.c``.

    Returns:
        list[BloqueNoCoincidente]: Bloques en el orden en que se cierran.

    Ejemplo:
        bloques = bloques_no_coincidentes(texto)
    """
    lineas = texto.split("\n")
    mascara = _enmascarar_comentarios(texto).split("\n")
    pila: list[_Condicional] = []
    bloques: list[BloqueNoCoincidente] = []
    for numero, linea in enumerate(mascara):
        directiva = linea.strip()
        if not directiva.startswith("#"):
            continue
        palabras = directiva[1:].split()
        nombre = palabras[0] if palabras else ""
        if nombre in ("if", "ifdef", "ifndef"):
            es_bloque = nombre == "ifdef" and len(palabras) > 1 and palabras[1] == MACRO_NO_COINCIDENTE
            pila.append(_Condicional(es_bloque, numero))
        elif nombre == "else" and pila:
            pila[-1].otra_rama = numero
        elif nombre == "endif" and pila:
            condicional = pila.pop()
            if not condicional.es_no_coincidente or condicional.otra_rama is None:
                continue
            ensamblador = _INCLUDE_ASM.search("\n".join(mascara[condicional.otra_rama + 1 : numero]))
            if ensamblador is not None:
                rama_c = "\n".join(lineas[condicional.inicio + 1 : condicional.otra_rama])
                bloques.append(BloqueNoCoincidente(ensamblador.group(1), condicional.inicio + 1, rama_c))
    return bloques


def puntuacion_pendiente(bloque: BloqueNoCoincidente) -> int | None:
    """
    Lee la puntuacion que un bloque ``NON_MATCHING`` declara en su linea ``Pendiente``.

    Contexto:
        La usan ``pendiente_declarada`` y el aviso de ``progreso`` que la compara con la ultima
        medicion de ``diff``. Solo cuenta el primer comentario de la rama de C, justo debajo del
        ``#ifdef NON_MATCHING``.

    Args:
        bloque (BloqueNoCoincidente): Bloque a leer.

    Returns:
        int | None: La puntuacion declarada, o ``None`` si lo primero de la rama no es un comentario
        que empiece por ``Pendiente: puntuacion`` seguido de un numero.

    Ejemplo:
        puntos = puntuacion_pendiente(bloques_no_coincidentes(texto)[0])
    """
    inicial = _COMENTARIO_INICIAL.match(bloque.rama_c)
    if inicial is None:
        return None
    crudo = inicial.group(1)
    cuerpo = crudo[2:-2] if crudo.startswith("/*") else crudo[2:]
    coincidencia = _PENDIENTE.match(_aplanar_comentario(cuerpo))
    return None if coincidencia is None else int(coincidencia.group(1))


def pendiente_declarada(bloque: BloqueNoCoincidente) -> bool:
    """
    Indica si un bloque ``NON_MATCHING`` abre con la linea ``Pendiente: puntuacion N``.

    Contexto:
        La puntuacion del intento vive en el primer comentario de la rama de C, justo debajo del
        ``#ifdef NON_MATCHING``, porque es donde la lee ``progreso`` para listar el motivo. Un
        comentario anterior al ``#ifdef`` o uno situado despues de codigo no cuentan.

    Args:
        bloque (BloqueNoCoincidente): Bloque a comprobar.

    Returns:
        bool: Verdadero si lo primero bajo el ``#ifdef`` es un comentario cuyo texto empieza por
        ``Pendiente: puntuacion`` seguido de un numero.

    Ejemplo:
        declarada = pendiente_declarada(bloques_no_coincidentes(texto)[0])
    """
    return puntuacion_pendiente(bloque) is not None


def verificar_pendientes(textos: Mapping[str, str]) -> None:
    """
    Exige la linea ``Pendiente: puntuacion N`` en todo bloque ``NON_MATCHING`` de los archivos C.

    Contexto:
        Guardia de ``progreso``: sin esa linea el intento figuraria en el conteo pero sin su
        puntuacion ni su motivo, y ninguna otra comprobacion lo notaria.

    Args:
        textos (Mapping[str, str]): Texto por archivo (clave: ruta relativa).

    Raises:
        ValueError: Si algun bloque no la tiene; el mensaje lista archivo, linea y funcion de todos
            los bloques afectados y dice donde debe ir el comentario.

    Ejemplo:
        verificar_pendientes({"src/a.c": texto})
    """
    faltantes = [
        f"{archivo}:{bloque.linea} {bloque.funcion}"
        for archivo in sorted(textos)
        for bloque in bloques_no_coincidentes(textos[archivo])
        if not pendiente_declarada(bloque)
    ]
    if faltantes:
        raise ValueError(
            f"{len(faltantes)} funcion(es) {MACRO_NO_COINCIDENTE} sin la linea 'Pendiente: puntuacion N' "
            f"en el primer comentario bajo '#ifdef {MACRO_NO_COINCIDENTE}': " + "; ".join(faltantes)
        )


def clasificar_include_asm(texto: str) -> dict[str, MarcaAsm]:
    """
    Clasifica cada ``INCLUDE_ASM`` suelto de un archivo segun el comentario que lo precede.

    Contexto:
        Una funcion que se queda en ensamblador por ser una rutina escrita a mano en el original lo
        declara en el comentario inmediatamente encima. ``progreso`` lista esas rutinas aparte y
        avisa de las que no explican por que siguen en ensamblador. Se ignoran los ``INCLUDE_ASM`` de
        la rama ``#else`` de un bloque ``NON_MATCHING`` (son intentos pendientes, no rutinas de diseno).

    Args:
        texto (str): Contenido del archivo ``.c``.

    Returns:
        dict[str, MarcaAsm]: Marca por nombre de funcion. El comentario cuenta solo si termina en la
        linea anterior al ``INCLUDE_ASM``; una linea en blanco de por medio lo desvincula.

    Raises:
        ValueError: Si el preprocesador del archivo esta desbalanceado.

    Ejemplo:
        marcas = clasificar_include_asm(texto)
    """
    mascara = _enmascarar_comentarios(texto)
    activo = _texto_activo(mascara, no_coincidente=False)
    lineas_mascara = mascara.split("\n")
    comentarios: dict[int, str] = {}
    for coincidencia in _COMENTARIOS.finditer(texto):
        if coincidencia.group(0).startswith("/"):
            comentarios[texto.count("\n", 0, coincidencia.end())] = coincidencia.group(0)
    intentos = {bloque.funcion for bloque in bloques_no_coincidentes(texto)}
    marcas: dict[str, MarcaAsm] = {}
    for ensamblador in _INCLUDE_ASM.finditer(activo):
        if ensamblador.group(1) in intentos:
            continue
        previa = activo.count("\n", 0, ensamblador.start()) - 1
        comentario = comentarios.get(previa)
        if comentario is None or lineas_mascara[previa].strip():
            marcas[ensamblador.group(1)] = MarcaAsm.SIN_COMENTARIO
        elif _MANUSCRITA.search(_aplanar_comentario(comentario)):
            marcas[ensamblador.group(1)] = MarcaAsm.MANUSCRITA
        else:
            marcas[ensamblador.group(1)] = MarcaAsm.JUSTIFICADA
    return marcas


def motivos_no_coincidentes(texto: str) -> dict[str, str]:
    """
    Extrae el motivo escrito junto a cada intento ``NON_MATCHING``.

    Contexto:
        ``progreso`` lista los intentos pendientes con la explicacion que dejo quien los escribio:
        el primer comentario de bloque dentro del ``#ifdef NON_MATCHING`` (puntuacion y
        diferencias conocidas). Un bloque sin comentario no tiene motivo.

    Args:
        texto (str): Contenido del archivo ``.c``.

    Returns:
        dict[str, str]: Motivo por nombre de funcion, en una sola linea y acotado a
        ``MAX_CARACTERES_MOTIVO`` caracteres.

    Ejemplo:
        motivos = motivos_no_coincidentes(texto)
    """
    motivos: dict[str, str] = {}
    for bloque in bloques_no_coincidentes(texto):
        comentario = _PRIMER_COMENTARIO.search(bloque.rama_c)
        if comentario is not None:
            motivos[bloque.funcion] = _aplanar_comentario(comentario.group(1))[:MAX_CARACTERES_MOTIVO]
    return motivos

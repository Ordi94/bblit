"""Analisis puro de los archivos C del proyecto: que funciones estan descompiladas y cuales no.

El estado de cada funcion se deriva del propio texto de los archivos C (nunca de una lista
aparte), de modo que el progreso y el diff no pueden desincronizarse del codigo. Tres estados:

* ``C``: la funcion esta definida en C en la construccion normal; como la construccion es
  byte a byte, que compile ya prueba que coincide con el original.
* ``NO_COINCIDENTE``: hay un intento en C bajo ``#ifdef <macro_no_coincidente>`` y la construccion
  normal sigue usando la macro de ensamblador.
* ``ENSAMBLADOR``: solo existe la macro de ensamblador.

Las reglas de deteccion de definiciones replican las del particionador (splat), que lee el
mismo texto para decidir que funciones ya estan en C: si una definicion no la reconoce, el
particionador sigue emitiendo el simbolo como indefinido y el enlazador falla con una
definicion duplicada. Por eso una definicion que el particionador no veria se rechaza aqui con
un mensaje que explica como escribirla.

Los nombres de las macros, el formato de la linea de pendiente y la frase que marca una rutina
manuscrita son del proyecto: llegan en ``Convenciones`` (seccion ``[convenciones]`` del manifiesto)
y este modulo no conoce ningun valor concreto.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

from psxdecomp.dominio import Convenciones

MAX_BYTES_FUENTE = 2 * 1024 * 1024

_COMENTARIOS = re.compile(
    r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
    re.DOTALL | re.MULTILINE,
)
# Misma expresion que usa el particionador para localizar definiciones de funcion: tipo de
# retorno de UNA palabra al inicio de la linea, luego el nombre y la lista de parametros.
_DEFINICION_PARTICIONADOR = re.compile(r"^(?:static\s+)?[^\s]+\s+([^\s(]+)\(([^;)]*)\)[^;]+?{", re.MULTILINE)
# Busqueda amplia: cualquier identificador seguido de parametros y de una llave de apertura.
_DEFINICION_AMPLIA = re.compile(r"\b([A-Za-z_]\w*)\s*\(([^;(){}]*)\)\s*\{")
_IDENTIFICADOR = re.compile(r"^[A-Za-z_]\w*$")
_PRIMER_COMENTARIO = re.compile(r"/\*(.*?)\*/", re.DOTALL)
# Comentario (de bloque o de linea) que abre la rama de C de un bloque no coincidente.
_COMENTARIO_INICIAL = re.compile(r"\A\s*(/\*.*?\*/|//[^\n]*)", re.DOTALL)
MAX_CARACTERES_MOTIVO = 600
_PALABRAS_DE_CONTROL = frozenset({"if", "while", "for", "switch", "return", "sizeof", "else", "do"})


@dataclass(frozen=True)
class _Patrones:
    """Macros y expresiones del analisis, ya compiladas a partir de las convenciones del proyecto.

    Attributes:
        macro: Nombre de la macro que marca el intento no coincidente.
        macro_ensamblador: Nombre de la macro que incluye el ensamblador original.
        include_asm: Llamada a la macro de ensamblador; su grupo 1 es el nombre de la funcion.
        pendiente: Linea de pendiente al inicio del comentario; su grupo 1 es la puntuacion.
        manuscrita: Frase que declara una rutina escrita a mano en el original.
    """

    macro: str
    macro_ensamblador: str
    include_asm: re.Pattern[str]
    pendiente: re.Pattern[str]
    manuscrita: re.Pattern[str]


@lru_cache(maxsize=8)
def _patrones(convenciones: Convenciones) -> _Patrones:
    """
    Compila una sola vez las expresiones que derivan de las convenciones del proyecto.

    Contexto:
        Todas las funciones publicas de este modulo las necesitan; ``Convenciones`` es inmutable y
        hashable, de modo que la cache nunca devuelve el resultado de otra convencion.

    Args:
        convenciones (Convenciones): Seccion ``[convenciones]`` validada del manifiesto.

    Returns:
        _Patrones: Macros y expresiones compiladas.

    Ejemplo:
        patrones = _patrones(proyecto.convenciones)
    """
    macro = re.escape(convenciones.macro_ensamblador)
    return _Patrones(
        macro=convenciones.macro_no_coincidente,
        macro_ensamblador=convenciones.macro_ensamblador,
        include_asm=re.compile(rf'\b{macro}\(\s*"[^"]*"\s*,\s*([A-Za-z_]\w*)\s*\)'),
        pendiente=re.compile(convenciones.pendiente),
        manuscrita=re.compile(convenciones.manuscrita, re.IGNORECASE),
    )


class EstadoFuncion(Enum):
    """Situacion de una funcion respecto a su descompilacion.

    Attributes:
        C: definida en C y compilada en la construccion normal.
        NO_COINCIDENTE: intento en C bajo la macro no coincidente; la construccion usa el ensamblador.
        ENSAMBLADOR: solo la macro de ensamblador.
    """

    C = "c"
    NO_COINCIDENTE = "no_coincidente"
    ENSAMBLADOR = "ensamblador"


class MarcaAsm(Enum):
    """Lo que dice el comentario que precede a una funcion que sigue incluida desde el ensamblador.

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
    """Un bloque ``#ifdef <macro> ... #else <ensamblador> ... #endif`` de un archivo C.

    Attributes:
        funcion: Funcion de la macro de ensamblador de la rama ``#else``.
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


def _texto_activo(texto: str, no_coincidente: bool, macro: str) -> str:
    """
    Devuelve el texto con las lineas de las ramas inactivas reemplazadas por lineas vacias.

    Contexto:
        Evalua solo ``#ifdef/#ifndef`` de la macro no coincidente, ``#else`` y ``#endif``; cualquier
        otra condicion del preprocesador se trata como verdadera. Conserva el numero de lineas.

    Args:
        texto (str): Fuente sin comentarios.
        no_coincidente (bool): Si la macro no coincidente se considera definida.
        macro (str): Nombre de la macro no coincidente.

    Returns:
        str: Fuente con solo las lineas activas.

    Raises:
        ValueError: Si hay ``#else`` o ``#endif`` sin condicion abierta, una condicion sin cerrar
            o una condicion sobre la macro que no sea ``#ifdef``/``#ifndef``.
    """
    # Cada elemento: (la rama actual esta activa, la condicion depende de la macro).
    pila: list[tuple[bool, bool]] = []
    salida: list[str] = []
    for numero, linea in enumerate(texto.splitlines(), start=1):
        directiva = linea.strip()
        if directiva.startswith("#"):
            palabras = directiva[1:].split()
            nombre = palabras[0] if palabras else ""
            if nombre in ("ifdef", "ifndef", "if"):
                depende = nombre != "if" and len(palabras) > 1 and palabras[1] == macro
                if macro in directiva and not depende:
                    raise ValueError(f"linea {numero}: use '#ifdef {macro}' o '#ifndef'")
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
            "tipo, por ejemplo 'Pieza* rutina_a(...)'"
        )
    return vistas


def analizar_fuente(texto: str, convenciones: Convenciones) -> dict[str, EstadoFuncion]:
    """
    Determina el estado de cada funcion mencionada en un archivo C.

    Contexto:
        Es la unica fuente de verdad de ``progreso`` y de ``diff``. Se evalua el texto dos
        veces: con la macro no coincidente indefinida (la construccion normal) y definida (el intento).

    Args:
        texto (str): Contenido del archivo ``.c``.
        convenciones (Convenciones): Nombres de las macros del proyecto.

    Returns:
        dict[str, EstadoFuncion]: Estado por nombre de funcion, en orden alfabetico.

    Raises:
        ValueError: Si el texto excede ``MAX_BYTES_FUENTE``, el preprocesador esta desbalanceado
            o una definicion no seria reconocida por el particionador.

    Ejemplo:
        estados = analizar_fuente('INCLUDE_ASM("asm/pendientes/a", rutina_a);', convenciones)
    """
    if len(texto.encode("utf-8")) > MAX_BYTES_FUENTE:
        raise ValueError("el archivo C excede el tamano permitido")
    patrones = _patrones(convenciones)
    limpio = _quitar_comentarios(texto)
    normal = _texto_activo(limpio, False, patrones.macro)
    intento = _texto_activo(limpio, True, patrones.macro)
    definidas = _definiciones(normal)
    en_ensamblador = {m.group(1) for m in patrones.include_asm.finditer(normal)}
    intentos = _definiciones(intento) - definidas
    estados: dict[str, EstadoFuncion] = {}
    huerfanas = intentos - en_ensamblador
    if huerfanas:
        raise ValueError(
            f"'{min(huerfanas)}' solo existe bajo {patrones.macro}: "
            f"falta su {patrones.macro_ensamblador} en la rama #else"
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
    estados_por_archivo: Mapping[str, Mapping[str, EstadoFuncion]], funcion: str, carpeta_fuentes: str
) -> tuple[str, EstadoFuncion]:
    """
    Busca en que archivo C esta una funcion.

    Contexto:
        ``diff`` necesita saber que archivo compilar para comparar la funcion pedida.

    Args:
        estados_por_archivo (Mapping[str, Mapping[str, EstadoFuncion]]): Estados por archivo
            (clave: ruta relativa como ``codigo/modulo_a.c``).
        funcion (str): Nombre de la funcion.
        carpeta_fuentes (str): Carpeta de los fuentes C del proyecto (``rutas.fuentes``); solo la
            nombra el mensaje de error.

    Returns:
        tuple[str, EstadoFuncion]: Archivo y estado de la funcion.

    Raises:
        ValueError: Si ningun archivo menciona la funcion.

    Ejemplo:
        archivo, estado = ubicar_funcion(estados, "rutina_a", "codigo")
    """
    for archivo in sorted(estados_por_archivo):
        estado = estados_por_archivo[archivo].get(funcion)
        if estado is not None:
            return archivo, estado
    raise ValueError(f"la funcion '{funcion}' no figura en ningun archivo de {carpeta_fuentes}/")


def analizar_fuentes(
    textos: Mapping[str, str], convenciones: Convenciones
) -> dict[str, dict[str, EstadoFuncion]]:
    """
    Analiza el texto de todos los archivos C.

    Contexto:
        Punto comun de ``diff`` y ``progreso`` para obtener el estado de cada funcion.

    Args:
        textos (Mapping[str, str]): Texto por archivo (clave: ruta relativa).
        convenciones (Convenciones): Nombres de las macros del proyecto.

    Returns:
        dict[str, dict[str, EstadoFuncion]]: Estado por funcion y archivo, ordenado por archivo.

    Raises:
        ValueError: Si algun archivo no se puede analizar; el mensaje nombra el archivo.

    Ejemplo:
        estados = analizar_fuentes({"codigo/a.c": texto}, convenciones)
    """
    estados: dict[str, dict[str, EstadoFuncion]] = {}
    for archivo in sorted(textos):
        try:
            estados[archivo] = analizar_fuente(textos[archivo], convenciones)
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


def bloques_no_coincidentes(texto: str, convenciones: Convenciones) -> list[BloqueNoCoincidente]:
    """
    Localiza cada bloque ``#ifdef <macro> ... #else <ensamblador> ... #endif`` de un archivo C.

    Contexto:
        Es la lectura estructural comun de ``progreso``: de ella salen el motivo de cada intento,
        la comprobacion de la linea de pendiente y la exclusion de estas funciones al clasificar las
        macros de ensamblador sueltas. Las directivas se leen con una pila, de modo que una macro no
        coincidente anidada en otra condicion o en otro bloque cierra con su propio ``#endif``;
        los comentarios se enmascaran para que un ``#ifdef`` escrito dentro de uno no cuente. Un
        ``#ifdef`` de la macro sin rama ``#else`` con la macro de ensamblador no es un intento de
        funcion y se ignora.

    Args:
        texto (str): Contenido del archivo ``.c``.
        convenciones (Convenciones): Nombres de las macros del proyecto.

    Returns:
        list[BloqueNoCoincidente]: Bloques en el orden en que se cierran.

    Ejemplo:
        bloques = bloques_no_coincidentes(texto, convenciones)
    """
    patrones = _patrones(convenciones)
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
            es_bloque = nombre == "ifdef" and len(palabras) > 1 and palabras[1] == patrones.macro
            pila.append(_Condicional(es_bloque, numero))
        elif nombre == "else" and pila:
            pila[-1].otra_rama = numero
        elif nombre == "endif" and pila:
            condicional = pila.pop()
            if not condicional.es_no_coincidente or condicional.otra_rama is None:
                continue
            ensamblador = patrones.include_asm.search("\n".join(mascara[condicional.otra_rama + 1 : numero]))
            if ensamblador is not None:
                rama_c = "\n".join(lineas[condicional.inicio + 1 : condicional.otra_rama])
                bloques.append(BloqueNoCoincidente(ensamblador.group(1), condicional.inicio + 1, rama_c))
    return bloques


def puntuacion_pendiente(bloque: BloqueNoCoincidente, convenciones: Convenciones) -> int | None:
    """
    Lee la puntuacion que un bloque no coincidente declara en su linea de pendiente.

    Contexto:
        La usan ``pendiente_declarada`` y el aviso de ``progreso`` que la compara con la ultima
        medicion de ``diff``. Solo cuenta el primer comentario de la rama de C, justo debajo del
        ``#ifdef`` de la macro no coincidente.

    Args:
        bloque (BloqueNoCoincidente): Bloque a leer.
        convenciones (Convenciones): Aporta la expresion de la linea de pendiente (su grupo 1 es
            el numero).

    Returns:
        int | None: La puntuacion declarada, o ``None`` si lo primero de la rama no es un comentario
        que cumpla la expresion de pendiente.

    Ejemplo:
        puntos = puntuacion_pendiente(bloques_no_coincidentes(texto, convenciones)[0], convenciones)
    """
    inicial = _COMENTARIO_INICIAL.match(bloque.rama_c)
    if inicial is None:
        return None
    crudo = inicial.group(1)
    cuerpo = crudo[2:-2] if crudo.startswith("/*") else crudo[2:]
    coincidencia = _patrones(convenciones).pendiente.match(_aplanar_comentario(cuerpo))
    return None if coincidencia is None else int(coincidencia.group(1))


def pendiente_declarada(bloque: BloqueNoCoincidente, convenciones: Convenciones) -> bool:
    """
    Indica si un bloque no coincidente abre con la linea de pendiente de la convencion.

    Contexto:
        La puntuacion del intento vive en el primer comentario de la rama de C, justo debajo del
        ``#ifdef``, porque es donde la lee ``progreso`` para listar el motivo. Un comentario anterior
        al ``#ifdef`` o uno situado despues de codigo no cuentan.

    Args:
        bloque (BloqueNoCoincidente): Bloque a comprobar.
        convenciones (Convenciones): Aporta la expresion de la linea de pendiente.

    Returns:
        bool: Verdadero si lo primero bajo el ``#ifdef`` es un comentario que cumple la expresion.

    Ejemplo:
        declarada = pendiente_declarada(bloques_no_coincidentes(texto, convenciones)[0], convenciones)
    """
    return puntuacion_pendiente(bloque, convenciones) is not None


def verificar_pendientes(textos: Mapping[str, str], convenciones: Convenciones) -> None:
    """
    Exige la linea de pendiente en todo bloque no coincidente de los archivos C.

    Contexto:
        Guardia de ``progreso``: sin esa linea el intento figuraria en el conteo pero sin su
        puntuacion ni su motivo, y ninguna otra comprobacion lo notaria.

    Args:
        textos (Mapping[str, str]): Texto por archivo (clave: ruta relativa).
        convenciones (Convenciones): Nombres de las macros y expresion de la linea de pendiente.

    Raises:
        ValueError: Si algun bloque no la tiene; el mensaje lista archivo, linea y funcion de todos
            los bloques afectados, dice donde debe ir el comentario y cita la expresion exigida.

    Ejemplo:
        verificar_pendientes({"codigo/a.c": texto}, convenciones)
    """
    faltantes = [
        f"{archivo}:{bloque.linea} {bloque.funcion}"
        for archivo in sorted(textos)
        for bloque in bloques_no_coincidentes(textos[archivo], convenciones)
        if not pendiente_declarada(bloque, convenciones)
    ]
    if faltantes:
        macro = convenciones.macro_no_coincidente
        raise ValueError(
            f"{len(faltantes)} funcion(es) {macro} sin la linea de pendiente "
            f"(expresion {convenciones.pendiente!r}) "
            f"en el primer comentario bajo '#ifdef {macro}': " + "; ".join(faltantes)
        )


def clasificar_include_asm(texto: str, convenciones: Convenciones) -> dict[str, MarcaAsm]:
    """
    Clasifica cada macro de ensamblador suelta de un archivo segun el comentario que la precede.

    Contexto:
        Una funcion que se queda en ensamblador por ser una rutina escrita a mano en el original lo
        declara en el comentario inmediatamente encima. ``progreso`` lista esas rutinas aparte y
        avisa de las que no explican por que siguen en ensamblador. Se ignoran las macros de la rama
        ``#else`` de un bloque no coincidente (son intentos pendientes, no rutinas de diseno).

    Args:
        texto (str): Contenido del archivo ``.c``.
        convenciones (Convenciones): Nombres de las macros y frase que marca una rutina manuscrita.

    Returns:
        dict[str, MarcaAsm]: Marca por nombre de funcion. El comentario cuenta solo si termina en la
        linea anterior a la macro; una linea en blanco de por medio lo desvincula.

    Raises:
        ValueError: Si el preprocesador del archivo esta desbalanceado.

    Ejemplo:
        marcas = clasificar_include_asm(texto, convenciones)
    """
    patrones = _patrones(convenciones)
    mascara = _enmascarar_comentarios(texto)
    activo = _texto_activo(mascara, False, patrones.macro)
    lineas_mascara = mascara.split("\n")
    comentarios: dict[int, str] = {}
    for coincidencia in _COMENTARIOS.finditer(texto):
        if coincidencia.group(0).startswith("/"):
            comentarios[texto.count("\n", 0, coincidencia.end())] = coincidencia.group(0)
    intentos = {bloque.funcion for bloque in bloques_no_coincidentes(texto, convenciones)}
    marcas: dict[str, MarcaAsm] = {}
    for ensamblador in patrones.include_asm.finditer(activo):
        if ensamblador.group(1) in intentos:
            continue
        previa = activo.count("\n", 0, ensamblador.start()) - 1
        comentario = comentarios.get(previa)
        if comentario is None or lineas_mascara[previa].strip():
            marcas[ensamblador.group(1)] = MarcaAsm.SIN_COMENTARIO
        elif patrones.manuscrita.search(_aplanar_comentario(comentario)):
            marcas[ensamblador.group(1)] = MarcaAsm.MANUSCRITA
        else:
            marcas[ensamblador.group(1)] = MarcaAsm.JUSTIFICADA
    return marcas


def motivos_no_coincidentes(texto: str, convenciones: Convenciones) -> dict[str, str]:
    """
    Extrae el motivo escrito junto a cada intento no coincidente.

    Contexto:
        ``progreso`` lista los intentos pendientes con la explicacion que dejo quien los escribio:
        el primer comentario de bloque dentro del ``#ifdef`` (puntuacion y diferencias conocidas).
        Un bloque sin comentario no tiene motivo.

    Args:
        texto (str): Contenido del archivo ``.c``.
        convenciones (Convenciones): Nombres de las macros del proyecto.

    Returns:
        dict[str, str]: Motivo por nombre de funcion, en una sola linea y acotado a
        ``MAX_CARACTERES_MOTIVO`` caracteres.

    Ejemplo:
        motivos = motivos_no_coincidentes(texto, convenciones)
    """
    motivos: dict[str, str] = {}
    for bloque in bloques_no_coincidentes(texto, convenciones):
        comentario = _PRIMER_COMENTARIO.search(bloque.rama_c)
        if comentario is not None:
            motivos[bloque.funcion] = _aplanar_comentario(comentario.group(1))[:MAX_CARACTERES_MOTIVO]
    return motivos

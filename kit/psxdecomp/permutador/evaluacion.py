"""Medicion de una variante de una funcion con la misma cadena y la misma puntuacion que ``diff``.

Una variante es el texto de la definicion de la funcion. Para medirla se reemplaza esa definicion en
el texto del archivo de ``src/`` (sin tocar el archivo), se compila el resultado con las opciones del
archivo (incluido su ``-G``), se comprueba que el objeto define la funcion y se puntua con
``asm-differ`` contra el ensamblador original, exactamente como lo hace ``diff``. Cada medicion
trabaja en su propia carpeta de ``build/diff/``, de modo que varias se pueden lanzar a la vez.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from tools.reconstruccion import fuentes_c
from tools.reconstruccion.compilacion import HerramientasCompilacion, compilar_archivo
from tools.reconstruccion.diff import (
    FuncionSinCError,
    carpeta_de_trabajo,
    preparar_objetivo,
    puntuacion_desde_json,
    puntuar_objeto,
    salida_truncada,
    validar_funcion,
)
from tools.reconstruccion.enlace_diff import TIMEOUT_ENLACE_S, bytes_coinciden, funcion_en_objeto
from tools.reconstruccion.fuentes_c import EstadoFuncion
from tools.reconstruccion.infraestructura import (
    ELF_SALIDA,
    Ejecutor,
    ProcesoError,
    leer_direcciones_de_funciones,
    leer_valores_g,
    listar_fuentes_c,
)
from tools.reconstruccion.permutar_c import localizar_funcion

MAX_CARACTERES_MOTIVO = 120


@dataclass(frozen=True)
class ResultadoEvaluacion:
    """Resultado de medir una variante.

    Attributes:
        puntuacion: Puntuacion como la informa ``diff`` (0 si coincide); ``None`` si se descarto.
        motivo: Por que se descarto (una linea), o ``None`` si se midio.
        coincide: Si las instrucciones o los bytes enlazados coinciden con el original.
    """

    puntuacion: int | None
    motivo: str | None = None
    coincide: bool = False


@dataclass(frozen=True)
class ObjetivoMedicion:
    """Todo lo que hace falta para medir variantes de una funcion.

    Attributes:
        raiz: Raiz del repositorio.
        funcion: Nombre de la funcion.
        archivo: Archivo de ``src/`` que la contiene (``src/<nombre>.c``).
        texto_archivo: Texto del archivo ``src/`` que la contiene.
        inicio: Posicion donde empieza su definicion en ese texto.
        fin: Posicion donde termina.
        valor_g: Umbral ``-G`` del archivo.
        direccion: Direccion de la funcion en el ejecutable, o ``None`` si no se conoce.
        retornos: ``jr $ra`` del original.
        max_lineas: Limite de lineas de ``asm-differ`` que cubre la funcion entera.
        objetivo: Objeto del asm original (ruta relativa a la raiz).
        herramientas: Herramientas de compilacion.
        script_diff: Ruta de ``diff.py`` de ``asm-differ``.
        ejecutar: Ejecutor de procesos.
    """

    raiz: Path
    funcion: str
    archivo: str
    texto_archivo: str
    inicio: int
    fin: int
    valor_g: int
    direccion: int | None
    retornos: int
    max_lineas: int
    objetivo: str
    herramientas: HerramientasCompilacion
    script_diff: Path
    ejecutar: Ejecutor


def preparar_medicion(
    raiz: Path,
    funcion: str,
    herramientas: HerramientasCompilacion,
    script_diff: Path,
    ejecutar: Ejecutor,
    *,
    carpeta: str,
) -> ObjetivoMedicion:
    """
    Reune lo necesario para medir variantes de una funcion: su archivo, su original y las opciones.

    Contexto:
        Primer paso de ``permutar``. Ensambla el asm original una sola vez (en ``carpeta``) y localiza la
        definicion de la funcion en el texto de su archivo de ``src/``.

    Args:
        raiz (Path): Raiz del repositorio.
        funcion (str): Nombre de la funcion.
        herramientas (HerramientasCompilacion): Herramientas de compilacion.
        script_diff (Path): Ruta de ``diff.py`` de ``asm-differ``.
        ejecutar (Ejecutor): Ejecutor de procesos.
        carpeta (str): Carpeta de trabajo de la ejecucion, relativa a la raiz, que recibe el objetivo.

    Returns:
        ObjetivoMedicion: Objetivo listo para ``evaluar``.

    Raises:
        ValueError: Si el nombre no es valido, la funcion no figura en ``src/``, no tiene una unica
            definicion en C o falta el ejecutable de la ultima construccion (``build``).
        FuncionSinCError: Si la funcion sigue solo en ``INCLUDE_ASM``.
        FileNotFoundError: Si falta el asm original (hay que ejecutar ``split``).
        ProcesoError: Si falla el ensamblado del objetivo.

    Ejemplo:
        objetivo = preparar_medicion(Path("."), "func_80016C0C", herramientas, script, ejecutar, carpeta=c)
    """
    validar_funcion(funcion)
    textos = listar_fuentes_c(raiz)
    archivo, estado = fuentes_c.ubicar_funcion(fuentes_c.analizar_fuentes(textos), funcion)
    if estado is EstadoFuncion.ENSAMBLADOR:
        raise FuncionSinCError(f"'{funcion}' sigue en INCLUDE_ASM: no hay C que permutar")
    if not (raiz / ELF_SALIDA).is_file():
        raise ValueError("falta el ejecutable de la ultima construccion: ejecute 'build' antes de permutar")
    texto = textos[archivo]
    inicio, fin = localizar_funcion(texto, funcion)
    objetivo, retornos, max_lineas = preparar_objetivo(
        raiz, funcion, archivo, herramientas, ejecutar, carpeta=carpeta
    )
    return ObjetivoMedicion(
        raiz=raiz,
        funcion=funcion,
        archivo=archivo,
        texto_archivo=texto,
        inicio=inicio,
        fin=fin,
        valor_g=leer_valores_g(raiz).get(Path(archivo).stem, 0),
        direccion=leer_direcciones_de_funciones(raiz).get(funcion),
        retornos=retornos,
        max_lineas=max_lineas,
        objetivo=objetivo,
        herramientas=herramientas,
        script_diff=script_diff,
        ejecutar=ejecutar,
    )


def texto_del_archivo(objetivo: ObjetivoMedicion, texto_funcion: str) -> str:
    """
    Arma el archivo C completo con la definicion de la funcion sustituida.

    Contexto:
        Cada variante se compila como el archivo entero para conservar cabeceras, tipos y el resto de
        funciones, que la definicion usa.

    Args:
        objetivo (ObjetivoMedicion): Objetivo de la medicion.
        texto_funcion (str): Definicion de la variante.

    Returns:
        str: Texto del archivo con la variante en lugar de la definicion original.

    Ejemplo:
        completo = texto_del_archivo(objetivo, variante)
    """
    return objetivo.texto_archivo[: objetivo.inicio] + texto_funcion + objetivo.texto_archivo[objetivo.fin :]


def _primera_linea(mensaje: str) -> str:
    """Primera linea no vacia de un mensaje, acotada para el registro."""
    lineas = [linea.strip() for linea in mensaje.splitlines() if linea.strip()]
    return (lineas[0] if lineas else "fallo sin mensaje")[:MAX_CARACTERES_MOTIVO]


def evaluar(
    objetivo: ObjetivoMedicion, texto_funcion: str, *, comprobar_bytes_bajo: int
) -> ResultadoEvaluacion:
    """
    Compila y puntua una variante.

    Contexto:
        Es lo que cada hilo del motor ejecuta por variante. Un fallo de la variante (no compila, no
        define la funcion, medicion truncada, no enlaza) devuelve un resultado descartado en lugar de
        una excepcion: el motor sigue con las demas.

    Args:
        objetivo (ObjetivoMedicion): Objetivo de la medicion.
        texto_funcion (str): Definicion de la variante.
        comprobar_bytes_bajo (int): Solo se comparan los bytes enlazados si la puntuacion de
            ``asm-differ`` es distinta de cero y menor que este valor (``diff`` cuenta como cero una
            funcion cuyos bytes coinciden aunque ``asm-differ`` la puntue por la forma simbolica).

    Returns:
        ResultadoEvaluacion: Puntuacion informada o motivo del descarte.

    Ejemplo:
        resultado = evaluar(objetivo, texto, comprobar_bytes_bajo=10)
    """
    try:
        with carpeta_de_trabajo(objetivo.raiz, f"permutar-{objetivo.funcion}") as carpeta:
            return _evaluar_en(objetivo, texto_funcion, carpeta, comprobar_bytes_bajo)
    except (ProcesoError, ValueError, OSError) as error:
        return ResultadoEvaluacion(None, _primera_linea(str(error)))


def _evaluar_en(
    objetivo: ObjetivoMedicion, texto_funcion: str, carpeta: str, comprobar_bytes_bajo: int
) -> ResultadoEvaluacion:
    """Compila y puntua dentro de la carpeta de trabajo ya creada."""
    raiz = objetivo.raiz
    fuente = f"{carpeta}/variante.c"
    candidato = f"{carpeta}/variante.c.o"
    copia = f"{carpeta}/{Path(objetivo.objetivo).name}"
    (raiz / fuente).write_text(texto_del_archivo(objetivo, texto_funcion), encoding="utf-8", newline="\n")
    shutil.copyfile(raiz / objetivo.objetivo, raiz / copia)
    compilar_archivo(
        raiz,
        fuente,
        candidato,
        objetivo.herramientas,
        objetivo.ejecutar,
        definiciones=(fuentes_c.MACRO_NO_COINCIDENTE,),
        exigir_solo_texto=False,
        valor_g=objetivo.valor_g,
    )
    tabla = objetivo.ejecutar([str(objetivo.herramientas.objdump), "-t", candidato], raiz, TIMEOUT_ENLACE_S)
    if funcion_en_objeto(tabla, objetivo.funcion) is None:
        return ResultadoEvaluacion(None, f"la variante no define {objetivo.funcion}")
    salida = puntuar_objeto(
        raiz,
        objetivo.herramientas,
        objetivo.script_diff,
        objetivo.ejecutar,
        candidato=candidato,
        objetivo=copia,
        funcion=objetivo.funcion,
        retornos=objetivo.retornos,
        max_lineas=objetivo.max_lineas,
        formato="json",
    )
    puntuacion = puntuacion_desde_json(salida)
    if salida_truncada(salida, objetivo.max_lineas):
        return ResultadoEvaluacion(None, "medicion truncada: la variante supera el limite de lineas")
    if puntuacion == 0:
        return ResultadoEvaluacion(0, coincide=True)
    if puntuacion >= comprobar_bytes_bajo or objetivo.direccion is None:
        return ResultadoEvaluacion(puntuacion)
    iguales = bytes_coinciden(
        raiz,
        objetivo.herramientas,
        objetivo.ejecutar,
        funcion=objetivo.funcion,
        direccion=objetivo.direccion,
        candidato=candidato,
        objetivo=copia,
    )
    if iguales is None:
        return ResultadoEvaluacion(None, "la variante no enlaza en la direccion de la funcion")
    return ResultadoEvaluacion(0, coincide=True) if iguales else ResultadoEvaluacion(puntuacion)

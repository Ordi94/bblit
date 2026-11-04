"""Calculo del progreso: reglas puras sobre la tabla de simbolos y el estado de cada funcion.

Los conteos se derivan del codigo real: el estado de cada funcion sale del texto de los archivos C
(ver ``psxdecomp.diff.fuentes_c``) y su tamano de la tabla de simbolos. Nada se declara a mano. Este
modulo no toca disco ni conoce un proyecto: las zonas de memoria y la regla de agrupacion por
subsistema llegan por parametro.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from psxdecomp.diff.fuentes_c import EstadoFuncion, MarcaAsm
from psxdecomp.dominio import Convenciones, Zonas

_PATRON_TAMANO = re.compile(r"\bsize:0x([0-9A-Fa-f]+)\b")

ZONA_ARRANQUE = "arranque"
ZONA_JUEGO = "juego"
ZONA_LIBRERIA = "libreria"
ZONA_OTRA = "otra"

AgrupadorDeSubsistemas = Callable[[str], str]
"""Regla que da el subsistema de un archivo C a partir de su ruta relativa."""


@dataclass(frozen=True)
class FuncionSimbolo:
    """Funcion declarada en la tabla de simbolos.

    Attributes:
        nombre: Nombre del simbolo.
        direccion: Direccion de memoria de la primera instruccion.
        tamano: Tamano en bytes.
    """

    nombre: str
    direccion: int
    tamano: int


@dataclass(frozen=True)
class ResumenZona:
    """Funciones y bytes de una zona de codigo.

    Attributes:
        funciones: Numero de funciones.
        bytes: Suma de sus tamanos.
    """

    funciones: int
    bytes: int


@dataclass(frozen=True)
class ArchivoProgreso:
    """Estado de las funciones de un archivo C.

    Attributes:
        archivo: Ruta relativa del archivo.
        c: Funciones compiladas desde C.
        no_coincidentes: Funciones con intento en C bajo la macro de no coincidente.
        ensamblador: Funciones que siguen incluidas desde ensamblador.
        bytes_c: Bytes de las funciones en C.
        bytes_total: Bytes de todas las funciones del archivo.
    """

    archivo: str
    c: int
    no_coincidentes: int
    ensamblador: int
    bytes_c: int
    bytes_total: int


@dataclass(frozen=True)
class SubsistemaProgreso:
    """Suma de los archivos C que forman un subsistema.

    Attributes:
        nombre: Nombre del subsistema.
        archivos: Numero de archivos ``.c`` del subsistema.
        c: Funciones compiladas desde C.
        no_coincidentes: Funciones con intento sin coincidir.
        ensamblador: Funciones que siguen incluidas desde ensamblador.
        bytes_c: Bytes de las funciones en C.
        bytes_total: Bytes de todas las funciones.
    """

    nombre: str
    archivos: int
    c: int
    no_coincidentes: int
    ensamblador: int
    bytes_c: int
    bytes_total: int


@dataclass(frozen=True)
class Progreso:
    """Resultado completo del medidor.

    Attributes:
        arranque: Funciones del codigo de arranque (antes del codigo del juego).
        juego: Funciones del codigo del juego.
        librerias: Funciones de las librerias del SDK.
        c_juego: Funciones del juego ya compiladas desde C.
        c_librerias: Funciones de librerias ya compiladas desde C.
        no_coincidentes: Nombres de las funciones con intento sin coincidir.
        motivos: Motivo escrito junto a cada intento, por nombre de funcion.
        archivos: Estado por archivo C.
        subsistemas: Estado por subsistema.
        auxiliares: Funciones definidas en C que no figuran en la tabla (ayudantes locales).
        sin_simbolo: Funciones mencionadas en los fuentes que la tabla no declara.
        glabel_en_asm: ``glabel`` del ensamblador generado, o ``None`` si no hay ensamblador.
        manuscritas: Funciones que siguen en ensamblador porque el original es una rutina escrita
            a mano, con su tamano en bytes.
        sin_comentario: ``(archivo, funcion)`` de las inclusiones de ensamblador sin comentario encima,
            en archivos que ya tienen funciones en C.
        no_coincidentes_juego: Funciones del codigo del juego con intento sin coincidir y sus bytes.
        manuscritas_juego: Funciones manuscritas del codigo del juego y sus bytes.
    """

    arranque: ResumenZona
    juego: ResumenZona
    librerias: ResumenZona
    c_juego: ResumenZona
    c_librerias: ResumenZona
    no_coincidentes: tuple[str, ...]
    motivos: tuple[tuple[str, str], ...]
    archivos: tuple[ArchivoProgreso, ...]
    subsistemas: tuple[SubsistemaProgreso, ...]
    auxiliares: tuple[str, ...]
    sin_simbolo: tuple[str, ...]
    glabel_en_asm: int | None
    manuscritas: tuple[tuple[str, int], ...] = ()
    sin_comentario: tuple[tuple[str, str], ...] = ()
    no_coincidentes_juego: ResumenZona = ResumenZona(0, 0)
    manuscritas_juego: ResumenZona = ResumenZona(0, 0)

    @property
    def funciones_totales(self) -> int:
        """Funciones de la tabla (arranque, juego y librerias)."""
        return self.arranque.funciones + self.juego.funciones + self.librerias.funciones

    @property
    def funciones_en_c(self) -> int:
        """Funciones de la tabla compiladas desde C."""
        return self.c_juego.funciones + self.c_librerias.funciones

    @property
    def porcentaje_bytes_juego(self) -> float:
        """Porcentaje de bytes de codigo del juego descompilados (0 si no hay codigo)."""
        if self.juego.bytes == 0:
            return 0.0
        return round(100 * self.c_juego.bytes / self.juego.bytes, 2)

    @property
    def coherente(self) -> bool | None:
        """Si ``glabel`` en el ensamblador mas funciones en C es igual a las de la tabla.

        ``None`` cuando no se pudo medir porque no existe el ensamblador generado.
        """
        if self.glabel_en_asm is None:
            return None
        return self.glabel_en_asm + self.funciones_en_c == self.funciones_totales


def leer_simbolos(texto: str, convenciones: Convenciones) -> list[FuncionSimbolo]:
    """
    Extrae las funciones de un archivo de simbolos de splat.

    Contexto:
        Lo usa la medicion con la tabla de simbolos del proyecto y con la de simbolos adicionales.
        Las lineas de datos y los comentarios se ignoran; toda funcion debe declarar su tamano.

    Args:
        texto (str): Contenido del archivo.
        convenciones (Convenciones): Aporta ``patron_linea_simbolo`` (nombre, direccion y atributos).

    Returns:
        list[FuncionSimbolo]: Funciones en el orden del archivo.

    Raises:
        ValueError: Si una linea de funcion no declara ``size:`` o su tamano es cero; el
            mensaje nombra la linea.

    Ejemplo:
        funciones = leer_simbolos("f = 0x80110000; // type:func size:0x10", convenciones)
    """
    patron = re.compile(convenciones.patron_linea_simbolo)
    funciones: list[FuncionSimbolo] = []
    for numero, linea in enumerate(texto.splitlines(), start=1):
        coincidencia = patron.match(linea.strip())
        if coincidencia is None or "type:func" not in coincidencia.group(3):
            continue
        tamano = _PATRON_TAMANO.search(coincidencia.group(3))
        if tamano is None or int(tamano.group(1), 16) == 0:
            raise ValueError(f"linea {numero}: '{coincidencia.group(1)}' no declara un size valido")
        funciones.append(
            FuncionSimbolo(coincidencia.group(1), int(coincidencia.group(2), 16), int(tamano.group(1), 16))
        )
    return funciones


def combinar_simbolos(*fuentes: Sequence[FuncionSimbolo]) -> list[FuncionSimbolo]:
    """
    Une varias tablas de simbolos; una funcion posterior reemplaza a la de su misma direccion.

    Contexto:
        El particionador lee los archivos de simbolos en orden y el ultimo que declara una
        direccion manda (asi el archivo de simbolos adicionales reduce una funcion fundida).

    Args:
        *fuentes (Sequence[FuncionSimbolo]): Tablas en el orden en que las lee el particionador.

    Returns:
        list[FuncionSimbolo]: Funciones ordenadas por direccion.

    Ejemplo:
        tabla = combinar_simbolos(base, adicionales)
    """
    por_direccion: dict[int, FuncionSimbolo] = {}
    for fuente in fuentes:
        for funcion in fuente:
            por_direccion[funcion.direccion] = funcion
    return sorted(por_direccion.values(), key=lambda f: f.direccion)


def zona_de(direccion: int, zonas: Zonas) -> str:
    """
    Clasifica una direccion de codigo.

    Contexto:
        Separa el codigo del juego del de las librerias del SDK con los limites del manifiesto
        (inicio inclusivo, fin exclusivo).

    Args:
        direccion (int): Direccion de memoria.
        zonas (Zonas): Limites de memoria del ejecutable.

    Returns:
        str: ``arranque``, ``juego``, ``libreria`` u ``otra``.

    Ejemplo:
        zona = zona_de(0x80120000, zonas)
    """
    if direccion < zonas.juego_desde:
        return ZONA_ARRANQUE
    if direccion < zonas.librerias_desde:
        return ZONA_JUEGO
    if direccion < zonas.librerias_hasta:
        return ZONA_LIBRERIA
    return ZONA_OTRA


def subsistema_de(archivo: str, convenciones: Convenciones) -> str:
    """
    Deduce el subsistema de un archivo ``<fuentes>/<subsistema>[sufijo].c``.

    Contexto:
        Los archivos de un mismo subsistema se numeran; el medidor los suma para informar el avance por
        subsistema, que es la unidad de reparto. Es la regla por omision: un proyecto puede sustituirla
        con el gancho ``entrada_progreso``.

    Args:
        archivo (str): Ruta relativa del archivo C.
        convenciones (Convenciones): Aporta ``sufijo_subsistema``, la expresion que se quita del nombre.

    Returns:
        str: Nombre del archivo sin carpeta, sin ``.c`` y sin el sufijo.

    Ejemplo:
        nombre = subsistema_de("codigo/dibujo_10.c", convenciones)
    """
    return re.sub(convenciones.sufijo_subsistema, "", Path(archivo).stem)


def agrupar_por_subsistema(
    archivos: Sequence[ArchivoProgreso], subsistema: AgrupadorDeSubsistemas
) -> tuple[SubsistemaProgreso, ...]:
    """
    Suma los archivos de cada subsistema, en orden alfabetico.

    Contexto:
        Lo usa ``calcular_progreso`` con la regla por omision o con la del gancho ``entrada_progreso``.

    Args:
        archivos (Sequence[ArchivoProgreso]): Estado por archivo.
        subsistema (AgrupadorDeSubsistemas): Regla que da el subsistema de la ruta de un archivo.

    Returns:
        tuple[SubsistemaProgreso, ...]: Un elemento por subsistema, ordenado por nombre.

    Ejemplo:
        subsistemas = agrupar_por_subsistema(archivos, lambda ruta: "todo")
    """
    grupos: dict[str, list[ArchivoProgreso]] = {}
    for archivo in archivos:
        grupos.setdefault(subsistema(archivo.archivo), []).append(archivo)
    return tuple(
        SubsistemaProgreso(
            nombre,
            len(miembros),
            sum(a.c for a in miembros),
            sum(a.no_coincidentes for a in miembros),
            sum(a.ensamblador for a in miembros),
            sum(a.bytes_c for a in miembros),
            sum(a.bytes_total for a in miembros),
        )
        for nombre, miembros in sorted(grupos.items())
    )


def _resumir(funciones: Sequence[FuncionSimbolo]) -> ResumenZona:
    """Cuenta funciones y bytes de una coleccion."""
    return ResumenZona(len(funciones), sum(f.tamano for f in funciones))


def calcular_progreso(
    simbolos: Sequence[FuncionSimbolo],
    estados: Mapping[str, Mapping[str, EstadoFuncion]],
    glabel_en_asm: int | None,
    motivos: Mapping[str, str] | None = None,
    marcas: Mapping[str, Mapping[str, MarcaAsm]] | None = None,
    *,
    zonas: Zonas,
    subsistema: AgrupadorDeSubsistemas,
) -> Progreso:
    """
    Calcula el progreso a partir de la tabla de simbolos y del estado de cada funcion.

    Contexto:
        Funcion pura: la lectura de archivos la hace ``medicion.generar_progreso``.

    Args:
        simbolos (Sequence[FuncionSimbolo]): Tabla de funciones ya combinada.
        estados (Mapping[str, Mapping[str, EstadoFuncion]]): Estado por funcion y archivo C.
        glabel_en_asm (int, opcional): ``glabel`` contados en el ensamblador; ``None`` si no hay.
        motivos (Mapping[str, str], opcional): Motivo de cada intento no coincidente.
        marcas (Mapping[str, Mapping[str, MarcaAsm]], opcional): Marca de cada inclusion de ensamblador
            suelta, por funcion y archivo C; sin ella no hay rutinas manuscritas ni avisos.
        zonas (Zonas): Limites de memoria del ejecutable.
        subsistema (AgrupadorDeSubsistemas): Regla que agrupa los archivos en subsistemas.

    Returns:
        Progreso: Conteos por zona, por archivo y de coherencia.

    Ejemplo:
        progreso = calcular_progreso(simbolos, estados, 911, zonas=zonas, subsistema=agrupador)
    """
    por_nombre = {f.nombre: f for f in simbolos}
    en_c: list[FuncionSimbolo] = []
    no_coincidentes: list[str] = []
    auxiliares: list[str] = []
    sin_simbolo: list[str] = []
    archivos: list[ArchivoProgreso] = []
    manuscritas: list[tuple[str, int]] = []
    funciones_manuscritas: list[FuncionSimbolo] = []
    funciones_no_coincidentes: list[FuncionSimbolo] = []
    sin_comentario: list[tuple[str, str]] = []
    for archivo in sorted(estados):
        contadores = {estado: 0 for estado in EstadoFuncion}
        bytes_c = bytes_total = 0
        for nombre, estado in estados[archivo].items():
            funcion = por_nombre.get(nombre)
            if funcion is None:
                (auxiliares if estado is EstadoFuncion.C else sin_simbolo).append(nombre)
                continue
            contadores[estado] += 1
            bytes_total += funcion.tamano
            marca = (marcas or {}).get(archivo, {}).get(nombre)
            if estado is EstadoFuncion.ENSAMBLADOR and marca is MarcaAsm.MANUSCRITA:
                manuscritas.append((nombre, funcion.tamano))
                funciones_manuscritas.append(funcion)
            elif estado is EstadoFuncion.ENSAMBLADOR and marca is MarcaAsm.SIN_COMENTARIO:
                sin_comentario.append((archivo, nombre))
            if estado is EstadoFuncion.C:
                en_c.append(funcion)
                bytes_c += funcion.tamano
            elif estado is EstadoFuncion.NO_COINCIDENTE:
                no_coincidentes.append(nombre)
                funciones_no_coincidentes.append(funcion)
        if not any(estado is EstadoFuncion.C for estado in estados[archivo].values()):
            sin_comentario = [par for par in sin_comentario if par[0] != archivo]
        archivos.append(
            ArchivoProgreso(
                archivo,
                contadores[EstadoFuncion.C],
                contadores[EstadoFuncion.NO_COINCIDENTE],
                contadores[EstadoFuncion.ENSAMBLADOR],
                bytes_c,
                bytes_total,
            )
        )

    def en_zona(funciones: Sequence[FuncionSimbolo], zona: str) -> list[FuncionSimbolo]:
        return [f for f in funciones if zona_de(f.direccion, zonas) == zona]

    return Progreso(
        arranque=_resumir(en_zona(simbolos, ZONA_ARRANQUE)),
        juego=_resumir(en_zona(simbolos, ZONA_JUEGO)),
        librerias=_resumir(en_zona(simbolos, ZONA_LIBRERIA)),
        c_juego=_resumir(en_zona(en_c, ZONA_JUEGO)),
        c_librerias=_resumir(en_zona(en_c, ZONA_LIBRERIA)),
        no_coincidentes=tuple(sorted(no_coincidentes)),
        motivos=tuple(sorted((n, m) for n, m in (motivos or {}).items() if n in no_coincidentes)),
        archivos=tuple(archivos),
        subsistemas=agrupar_por_subsistema(archivos, subsistema),
        auxiliares=tuple(sorted(auxiliares)),
        sin_simbolo=tuple(sorted(sin_simbolo)),
        glabel_en_asm=glabel_en_asm,
        manuscritas=tuple(sorted(manuscritas)),
        sin_comentario=tuple(sorted(sin_comentario)),
        no_coincidentes_juego=_resumir(en_zona(funciones_no_coincidentes, ZONA_JUEGO)),
        manuscritas_juego=_resumir(en_zona(funciones_manuscritas, ZONA_JUEGO)),
    )

"""Medidor de progreso de la descompilacion.

Los conteos se derivan del codigo real: el estado de cada funcion sale del texto de
``src/*.c`` (ver ``fuentes_c``) y su tamano de la tabla de simbolos. Nada se declara a mano. Como
control de coherencia se compara con el ensamblador que de verdad queda en ``asm/``: cada funcion
de la tabla debe estar o bien en C o bien como ``glabel`` en el ensamblador generado.

``python tools/build.py progreso`` escribe ``docs/PROGRESO.md`` (legible) y ``build/progreso.json``
(para otras herramientas).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.reconstruccion.fuentes_c import EstadoFuncion, analizar_fuentes
from tools.reconstruccion.infraestructura import PROGRESO_JSON, SIMBOLOS_PROYECTO, listar_fuentes_c

# Rangos de docs/MAPA_MEMORIA.md (limites exactos de las funciones identificadas).
INICIO_JUEGO = 0x80014AC4
INICIO_LIBRERIAS = 0x80045DA0
FIN_LIBRERIAS = 0x8005DEA0
SIMBOLOS_ADICIONALES = "config/simbolos_adicionales.txt"
DOCUMENTO_PROGRESO = "docs/PROGRESO.md"
MAX_BYTES_SIMBOLOS = 4 * 1024 * 1024
CARPETAS_ASM_AJENAS = ("include", "matchings", "overlay")
_PATRON_SIMBOLO = re.compile(r"^([A-Za-z_]\w*)\s*=\s*0x([0-9A-Fa-f]{1,8})\s*;\s*//(.*)$")
_PATRON_TAMANO = re.compile(r"\bsize:0x([0-9A-Fa-f]+)\b")
_PATRON_GLABEL = re.compile(r"^glabel\s+\S+", re.MULTILINE)


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
    """Estado de las funciones de un archivo ``src/*.c``.

    Attributes:
        archivo: Ruta relativa del archivo.
        c: Funciones compiladas desde C.
        no_coincidentes: Funciones con intento en C bajo ``NON_MATCHING``.
        ensamblador: Funciones que siguen en ``INCLUDE_ASM``.
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
class Progreso:
    """Resultado completo del medidor.

    Attributes:
        arranque: Funciones del codigo de arranque (antes del codigo del juego).
        juego: Funciones del codigo del juego.
        librerias: Funciones de las librerias Sony.
        c_juego: Funciones del juego ya compiladas desde C.
        c_librerias: Funciones de librerias ya compiladas desde C.
        no_coincidentes: Nombres de las funciones con intento sin coincidir.
        archivos: Estado por archivo C.
        auxiliares: Funciones definidas en C que no figuran en la tabla (ayudantes locales).
        sin_simbolo: Funciones mencionadas en ``src/`` que la tabla no declara.
        glabel_en_asm: ``glabel`` del ensamblador generado, o ``None`` si no hay ``asm/``.
    """

    arranque: ResumenZona
    juego: ResumenZona
    librerias: ResumenZona
    c_juego: ResumenZona
    c_librerias: ResumenZona
    no_coincidentes: tuple[str, ...]
    archivos: tuple[ArchivoProgreso, ...]
    auxiliares: tuple[str, ...]
    sin_simbolo: tuple[str, ...]
    glabel_en_asm: int | None

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

        ``None`` cuando no se pudo medir porque no existe ``asm/``.
        """
        if self.glabel_en_asm is None:
            return None
        return self.glabel_en_asm + self.funciones_en_c == self.funciones_totales


def leer_simbolos(texto: str) -> list[FuncionSimbolo]:
    """
    Extrae las funciones de un archivo de simbolos de splat.

    Contexto:
        Lee ``config/symbols.txt`` y ``config/simbolos_adicionales.txt``. Las lineas de datos y
        los comentarios se ignoran; toda funcion debe declarar su tamano.

    Args:
        texto (str): Contenido del archivo.

    Returns:
        list[FuncionSimbolo]: Funciones en el orden del archivo.

    Raises:
        ValueError: Si una linea de funcion no declara ``size:`` o su tamano es cero; el
            mensaje nombra la linea.

    Ejemplo:
        funciones = leer_simbolos("f = 0x80014AC4; // type:func size:0x10")
    """
    funciones: list[FuncionSimbolo] = []
    for numero, linea in enumerate(texto.splitlines(), start=1):
        coincidencia = _PATRON_SIMBOLO.match(linea.strip())
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
        direccion manda (asi ``simbolos_adicionales.txt`` reduce una funcion fundida).

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


def zona_de(direccion: int) -> str:
    """
    Clasifica una direccion de codigo.

    Contexto:
        Separa el codigo del juego del de las librerias Sony segun ``docs/MAPA_MEMORIA.md``.

    Args:
        direccion (int): Direccion de memoria.

    Returns:
        str: ``arranque``, ``juego``, ``libreria`` u ``otra``.

    Ejemplo:
        zona = zona_de(0x80036204)
    """
    if direccion < INICIO_JUEGO:
        return "arranque"
    if direccion < INICIO_LIBRERIAS:
        return "juego"
    if direccion < FIN_LIBRERIAS:
        return "libreria"
    return "otra"


def _resumir(funciones: Sequence[FuncionSimbolo]) -> ResumenZona:
    """Cuenta funciones y bytes de una coleccion."""
    return ResumenZona(len(funciones), sum(f.tamano for f in funciones))


def calcular_progreso(
    simbolos: Sequence[FuncionSimbolo],
    estados: Mapping[str, Mapping[str, EstadoFuncion]],
    glabel_en_asm: int | None,
) -> Progreso:
    """
    Calcula el progreso a partir de la tabla de simbolos y del estado de cada funcion.

    Contexto:
        Funcion pura: la lectura de archivos la hace ``generar_progreso``.

    Args:
        simbolos (Sequence[FuncionSimbolo]): Tabla de funciones ya combinada.
        estados (Mapping[str, Mapping[str, EstadoFuncion]]): Estado por funcion y archivo C.
        glabel_en_asm (int, opcional): ``glabel`` contados en ``asm/``; ``None`` si no hay ``asm/``.

    Returns:
        Progreso: Conteos por zona, por archivo y de coherencia.

    Ejemplo:
        progreso = calcular_progreso(simbolos, estados, 911)
    """
    por_nombre = {f.nombre: f for f in simbolos}
    en_c: list[FuncionSimbolo] = []
    no_coincidentes: list[str] = []
    auxiliares: list[str] = []
    sin_simbolo: list[str] = []
    archivos: list[ArchivoProgreso] = []
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
            if estado is EstadoFuncion.C:
                en_c.append(funcion)
                bytes_c += funcion.tamano
            elif estado is EstadoFuncion.NO_COINCIDENTE:
                no_coincidentes.append(nombre)
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
    return Progreso(
        arranque=_resumir([f for f in simbolos if zona_de(f.direccion) == "arranque"]),
        juego=_resumir([f for f in simbolos if zona_de(f.direccion) == "juego"]),
        librerias=_resumir([f for f in simbolos if zona_de(f.direccion) == "libreria"]),
        c_juego=_resumir([f for f in en_c if zona_de(f.direccion) == "juego"]),
        c_librerias=_resumir([f for f in en_c if zona_de(f.direccion) == "libreria"]),
        no_coincidentes=tuple(sorted(no_coincidentes)),
        archivos=tuple(archivos),
        auxiliares=tuple(sorted(auxiliares)),
        sin_simbolo=tuple(sorted(sin_simbolo)),
        glabel_en_asm=glabel_en_asm,
    )


def a_json(progreso: Progreso) -> dict[str, Any]:
    """
    Convierte el progreso al objeto que se guarda en ``build/progreso.json``.

    Contexto:
        Las claves van en camelCase, como el resto de JSON del proyecto.

    Args:
        progreso (Progreso): Resultado del medidor.

    Returns:
        dict[str, Any]: Objeto serializable con ``json.dumps``.

    Ejemplo:
        texto = json.dumps(a_json(progreso))
    """

    def zona(resumen: ResumenZona) -> dict[str, int]:
        return {"funciones": resumen.funciones, "bytes": resumen.bytes}

    return {
        "totales": {
            "arranque": zona(progreso.arranque),
            "juego": zona(progreso.juego),
            "librerias": zona(progreso.librerias),
            "funciones": progreso.funciones_totales,
        },
        "descompiladas": {
            "juego": zona(progreso.c_juego),
            "librerias": zona(progreso.c_librerias),
            "funciones": progreso.funciones_en_c,
            "porcentajeBytesJuego": progreso.porcentaje_bytes_juego,
        },
        "noCoincidentes": list(progreso.no_coincidentes),
        "archivos": [
            {
                "archivo": a.archivo,
                "funcionesC": a.c,
                "noCoincidentes": a.no_coincidentes,
                "ensamblador": a.ensamblador,
                "bytesC": a.bytes_c,
                "bytesTotal": a.bytes_total,
            }
            for a in progreso.archivos
        ],
        "auxiliares": list(progreso.auxiliares),
        "sinSimbolo": list(progreso.sin_simbolo),
        "coherencia": {
            "glabelEnAsm": progreso.glabel_en_asm,
            "funcionesEnC": progreso.funciones_en_c,
            "funcionesTotales": progreso.funciones_totales,
            "coincide": progreso.coherente,
        },
    }


def a_markdown(progreso: Progreso) -> str:
    """
    Genera el contenido de ``docs/PROGRESO.md``.

    Contexto:
        El texto es determinista (sin fechas) para que regenerarlo sin cambios no ensucie el
        historial.

    Args:
        progreso (Progreso): Resultado del medidor.

    Returns:
        str: Documento en Markdown, terminado en salto de linea.

    Ejemplo:
        Path("docs/PROGRESO.md").write_text(a_markdown(progreso), encoding="utf-8")
    """
    lineas = [
        "# Progreso de la descompilación",
        "",
        "Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del",
        "texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la",
        "construcción normal) y de la tabla de símbolos.",
        "",
        "## Resumen",
        "",
        "| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |",
        "|---|---:|---:|---:|---:|",
        f"| Arranque | {progreso.arranque.funciones} | {progreso.arranque.bytes} | 0 | 0 |",
        f"| Código del juego | {progreso.juego.funciones} | {progreso.juego.bytes} | "
        f"{progreso.c_juego.funciones} | {progreso.c_juego.bytes} |",
        f"| Librerías Sony | {progreso.librerias.funciones} | {progreso.librerias.bytes} | "
        f"{progreso.c_librerias.funciones} | {progreso.c_librerias.bytes} |",
        "",
        f"Bytes de código del juego descompilados: {progreso.c_juego.bytes} de {progreso.juego.bytes} "
        f"({progreso.porcentaje_bytes_juego:.2f} %).",
        f"Funciones marcadas `NON_MATCHING`: {len(progreso.no_coincidentes)}.",
    ]
    if progreso.coherente is None:
        lineas.append("Coherencia con el ensamblador: no medida (ejecute `split`).")
    else:
        estado = "correcta" if progreso.coherente else "ROTA"
        lineas.append(
            f"Coherencia con el ensamblador: {estado} ({progreso.glabel_en_asm} `glabel` en `asm/` + "
            f"{progreso.funciones_en_c} en C = {(progreso.glabel_en_asm or 0) + progreso.funciones_en_c}; "
            f"la tabla declara {progreso.funciones_totales})."
        )
    lineas += [
        "",
        "## Por archivo",
        "",
        "| Archivo | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |",
        "|---|---:|---:|---:|---:|---:|",
        *(
            f"| `{a.archivo}` | {a.c} | {a.no_coincidentes} | {a.ensamblador} | "
            f"{a.bytes_c} | {a.bytes_total} |"
            for a in progreso.archivos
        ),
        "",
        "## Funciones `NON_MATCHING`",
        "",
        *(f"- `{nombre}`" for nombre in progreso.no_coincidentes),
    ]
    if not progreso.no_coincidentes:
        lineas.append("Ninguna.")
    if progreso.auxiliares:
        lineas += ["", "## Ayudantes definidos en C (no figuran en la tabla)", ""]
        lineas += [f"- `{nombre}`" for nombre in progreso.auxiliares]
    if progreso.sin_simbolo:
        lineas += ["", "## Menciones sin símbolo de función (datos incrustados en el código; no cuentan)", ""]
        lineas += [f"- `{nombre}`" for nombre in progreso.sin_simbolo]
    return "\n".join(lineas) + "\n"


def contar_glabel(raiz: Path) -> int | None:
    """
    Cuenta los ``glabel`` del ensamblador generado por el particionador.

    Contexto:
        Es la medida independiente del conteo por fuente: cada funcion que no esta en C debe
        figurar como ``glabel`` en ``asm/``. No se cuentan las macros (``asm/include``), el
        ensamblador de las funciones ya en C (``asm/matchings``) ni lo de otras herramientas
        (``asm/overlay``).

    Args:
        raiz (Path): Raiz del repositorio.

    Returns:
        int | None: Numero de ``glabel``, o ``None`` si no existe ``asm/``.

    Ejemplo:
        total = contar_glabel(Path("."))
    """
    carpeta = raiz / "asm"
    if not carpeta.is_dir():
        return None
    total = 0
    for ruta in sorted(carpeta.rglob("*.s")):
        if ruta.relative_to(carpeta).parts[0] in CARPETAS_ASM_AJENAS:
            continue
        total += len(_PATRON_GLABEL.findall(ruta.read_text(encoding="utf-8")))
    return total


def _leer_tabla(ruta: Path) -> list[FuncionSimbolo]:
    """Lee un archivo de simbolos con cota de tamano; vacio si no existe."""
    if not ruta.is_file():
        return []
    if ruta.stat().st_size > MAX_BYTES_SIMBOLOS:
        raise ValueError(f"{ruta.name} excede el tamano permitido")
    return leer_simbolos(ruta.read_text(encoding="utf-8"))


def generar_progreso(raiz: Path) -> Progreso:
    """
    Mide el progreso y escribe ``docs/PROGRESO.md`` y ``build/progreso.json``.

    Contexto:
        Implementa ``progreso``. No necesita el disco ni el toolchain: solo la tabla de simbolos,
        ``src/`` y, si existe, ``asm/``.

    Args:
        raiz (Path): Raiz del repositorio.

    Returns:
        Progreso: Resultado medido.

    Raises:
        FileNotFoundError: Si falta ``config/symbols.txt``.
        ValueError: Si la tabla o algun archivo C no se pueden interpretar.

    Ejemplo:
        progreso = generar_progreso(Path("."))
    """
    if not (raiz / SIMBOLOS_PROYECTO).is_file():
        raise FileNotFoundError(f"falta {SIMBOLOS_PROYECTO}")
    simbolos = combinar_simbolos(
        _leer_tabla(raiz / SIMBOLOS_PROYECTO), _leer_tabla(raiz / SIMBOLOS_ADICIONALES)
    )
    estados = analizar_fuentes(listar_fuentes_c(raiz))
    progreso = calcular_progreso(simbolos, estados, contar_glabel(raiz))
    documento = raiz / DOCUMENTO_PROGRESO
    documento.parent.mkdir(parents=True, exist_ok=True)
    documento.write_text(a_markdown(progreso), encoding="utf-8", newline="\n")
    salida = raiz / PROGRESO_JSON
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(
        json.dumps(a_json(progreso), indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return progreso

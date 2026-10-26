"""Seccion de progreso del README, generada por ``python tools/build.py progreso``.

La seccion vive entre dos marcadores HTML y se reescribe entera en cada ejecucion; el resto del
README no se toca. Los numeros salen de ``Progreso`` (el mismo medidor que ``docs/PROGRESO.md``),
nunca se escriben a mano, de modo que cualquier lector puede reproducirlos con los comandos que la
propia seccion incluye.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tools.reconstruccion.infraestructura import Ejecutor, ProcesoError
from tools.reconstruccion.progreso import Progreso

MARCA_INICIO = "<!-- progreso:inicio -->"
MARCA_FIN = "<!-- progreso:fin -->"
RUTA_README = "README.md"
HASH_DESCONOCIDO = "desconocido"
MAX_BYTES_README = 1024 * 1024
TIMEOUT_GIT_S = 30
_PATRON_HASH = re.compile(r"^[0-9a-f]{4,40}$")


@dataclass(frozen=True)
class ResumenJuego:
    """Cifras del codigo del juego que muestra el README.

    Attributes:
        total: Funciones del codigo del juego.
        coincidentes: Funciones en C cuyo codigo compilado reproduce el original byte a byte.
        no_coincidentes: Funciones en C con intento pendiente de afinar (``NON_MATCHING``).
        manuscritas: Rutinas escritas a mano en el original, conservadas en ensamblador.
        sin_traducir: Funciones restantes, sin intento en C.
        bytes_coincidentes: Bytes de las funciones coincidentes.
        bytes_total: Bytes de todo el codigo del juego.
        porcentaje: Porcentaje de bytes coincidentes (0 si no hay codigo del juego).
    """

    total: int
    coincidentes: int
    no_coincidentes: int
    manuscritas: int
    sin_traducir: int
    bytes_coincidentes: int
    bytes_total: int
    porcentaje: float


def resumir_juego(progreso: Progreso) -> ResumenJuego:
    """
    Reduce el progreso medido a las cifras del codigo del juego.

    Contexto:
        Lo usa ``actualizar_readme``. Las funciones sin traducir son las que no estan en C, ni
        bajo ``NON_MATCHING``, ni son rutinas manuscritas; nunca resulta un valor negativo.

    Args:
        progreso (Progreso): Resultado del medidor.

    Returns:
        ResumenJuego: Cifras listas para mostrar.

    Ejemplo:
        resumen = resumir_juego(progreso)
    """
    atendidas = (
        progreso.c_juego.funciones
        + progreso.no_coincidentes_juego.funciones
        + progreso.manuscritas_juego.funciones
    )
    return ResumenJuego(
        total=progreso.juego.funciones,
        coincidentes=progreso.c_juego.funciones,
        no_coincidentes=progreso.no_coincidentes_juego.funciones,
        manuscritas=progreso.manuscritas_juego.funciones,
        sin_traducir=max(0, progreso.juego.funciones - atendidas),
        bytes_coincidentes=progreso.c_juego.bytes,
        bytes_total=progreso.juego.bytes,
        porcentaje=progreso.porcentaje_bytes_juego,
    )


def obtener_hash_corto(raiz: Path, ejecutar: Ejecutor) -> str:
    """
    Da el hash corto del commit actual del repositorio.

    Contexto:
        Lo usa ``actualizar_readme`` para fechar la seccion. Medir el progreso no debe fallar
        porque no haya ``git`` o porque el directorio no sea un repositorio.

    Args:
        raiz (Path): Raiz del repositorio.
        ejecutar (Ejecutor): Ejecutor de procesos.

    Returns:
        str: Salida de ``git rev-parse --short HEAD``, o ``desconocido`` si el comando falla o su
        salida no es un hash hexadecimal.

    Ejemplo:
        hash_corto = obtener_hash_corto(Path("."), ejecutar_proceso)
    """
    try:
        salida = ejecutar(["git", "rev-parse", "--short", "HEAD"], raiz, TIMEOUT_GIT_S).strip()
    except (ProcesoError, OSError):
        return HASH_DESCONOCIDO
    return salida if _PATRON_HASH.match(salida) else HASH_DESCONOCIDO


def generar_seccion(resumen: ResumenJuego, fecha: str, hash_corto: str, sha256_esperado: str) -> str:
    """
    Genera la seccion del README, marcadores incluidos, con saltos de linea LF.

    Contexto:
        Lo usa ``actualizar_readme``. La tabla muestra solo cifras medidas y el bloque de codigo
        da la forma de reproducirlas y de comprobar una funcion concreta.

    Args:
        resumen (ResumenJuego): Cifras del codigo del juego.
        fecha (str): Fecha de la medicion (``AAAA-MM-DD``).
        hash_corto (str): Hash corto del commit medido.
        sha256_esperado (str): SHA-256 del ejecutable original que ``verify`` exige.

    Returns:
        str: Texto de la seccion, sin salto de linea final.

    Ejemplo:
        texto = generar_seccion(resumen, "2026-10-26", "bf5ae56", "0fad70d9")
    """
    lineas = [
        MARCA_INICIO,
        "## Progreso",
        "",
        f"Medido el {fecha} sobre el commit `{hash_corto}`. Generado por `python tools/build.py progreso`;",
        "no se edita a mano.",
        "",
        "| Estado | Cifra |",
        "|---|---:|",
        f"| Funciones del juego | {resumen.total} |",
        f"| Coincidentes byte a byte | {resumen.coincidentes} |",
        f"| En C, pendientes de afinar (`NON_MATCHING`) | {resumen.no_coincidentes} |",
        f"| Escritas a mano, conservadas en ensamblador | {resumen.manuscritas} |",
        f"| Sin traducir | {resumen.sin_traducir} |",
        f"| Bytes coincidentes | {resumen.bytes_coincidentes} de {resumen.bytes_total} |",
        f"| Porcentaje de bytes coincidentes | {resumen.porcentaje:.2f} % |",
        "",
        "Para reproducirlo (hace falta una copia propia del disco en `BBLIT_DISC`):",
        "",
        "```",
        "python tools/build.py clean",
        "python tools/build.py split",
        "python tools/build.py build",
        f"python tools/build.py verify      # debe imprimir OK con SHA-256 {sha256_esperado}",
        "python tools/build.py progreso",
        "python tools/build.py diff <funcion>   # comprueba una funcion (por ejemplo func_80036204)",
        "```",
        MARCA_FIN,
    ]
    return "\n".join(lineas)


def _salto_de_linea(texto: str) -> str:
    """Devuelve CRLF si el texto usa mas finales CRLF que LF sueltos; si no, LF."""
    crlf = texto.count("\r\n")
    return "\r\n" if crlf and crlf >= texto.count("\n") - crlf else "\n"


def _localizar_marcadores(texto: str) -> tuple[int, int] | None:
    """Da el rango ``[inicio, fin)`` de la seccion existente o ``None`` si no hay marcadores."""
    inicios = texto.count(MARCA_INICIO)
    fines = texto.count(MARCA_FIN)
    if inicios == 0 and fines == 0:
        return None
    if inicios != 1 or fines != 1:
        raise ValueError(
            f"{RUTA_README}: los marcadores de progreso deben aparecer una sola vez cada uno "
            f"(inicio: {inicios}, fin: {fines})"
        )
    inicio = texto.index(MARCA_INICIO)
    fin = texto.index(MARCA_FIN)
    if fin < inicio:
        raise ValueError(f"{RUTA_README}: el marcador de fin de progreso esta antes del de inicio")
    return inicio, fin + len(MARCA_FIN)


def _fin_del_primer_parrafo(lineas: Sequence[str]) -> int:
    """Da el numero de lineas hasta el primer parrafo inclusive; un titulo ni lo es ni lo continua."""
    posicion = 0
    while posicion < len(lineas) and (not lineas[posicion].strip() or lineas[posicion].startswith("#")):
        posicion += 1
    while posicion < len(lineas) and lineas[posicion].strip() and not lineas[posicion].startswith("#"):
        posicion += 1
    return posicion


def aplicar_seccion(texto: str, seccion: str) -> str:
    """
    Coloca la seccion en el texto del README, reemplazando la anterior o insertandola.

    Contexto:
        Lo usa ``actualizar_readme``. Solo se reescribe lo que hay entre los marcadores; el resto de
        bytes, incluidos los finales de linea, queda igual. Sin marcadores, la seccion se inserta
        tras el primer parrafo (los titulos no cuentan como parrafo) o al final si no hay ninguno.

    Args:
        texto (str): Contenido actual del README, con sus finales de linea.
        seccion (str): Seccion generada, con saltos LF y sin salto final.

    Returns:
        str: Contenido nuevo; igual al original si la seccion ya estaba al dia.

    Raises:
        ValueError: Si hay marcadores repetidos, solos o en orden invertido.

    Ejemplo:
        nuevo = aplicar_seccion(texto, generar_seccion(resumen, fecha, hash_corto, sha))
    """
    salto = _salto_de_linea(texto)
    cuerpo = seccion.replace("\n", salto)
    rango = _localizar_marcadores(texto)
    if rango is not None:
        return texto[: rango[0]] + cuerpo + texto[rango[1] :]
    lineas = texto.splitlines(keepends=True)
    corte = _fin_del_primer_parrafo(lineas)
    cabeza = "".join(lineas[:corte])
    cola = "".join(lineas[corte:])
    if cabeza and not cabeza.endswith("\n"):
        cabeza += salto
    separador = salto if cabeza else ""
    resto = cola if cola.startswith(("\n", "\r\n")) or not cola else salto + cola
    return cabeza + separador + cuerpo + salto + resto


def actualizar_readme(
    raiz: Path, progreso: Progreso, fecha: str, hash_corto: str, sha256_esperado: str
) -> bool:
    """
    Reescribe la seccion de progreso del README del repositorio.

    Contexto:
        Implementa el efecto de ``progreso`` sobre ``README.md``. Es idempotente: con las mismas
        cifras, fecha y hash el archivo queda byte a byte igual y no se escribe.

    Args:
        raiz (Path): Raiz del repositorio.
        progreso (Progreso): Resultado del medidor.
        fecha (str): Fecha de la medicion (``AAAA-MM-DD``).
        hash_corto (str): Hash corto del commit medido.
        sha256_esperado (str): SHA-256 del ejecutable original.

    Returns:
        bool: ``True`` si el archivo cambio, ``False`` si ya estaba al dia.

    Raises:
        FileNotFoundError: Si no existe ``README.md`` (no se crea).
        ValueError: Si el README es demasiado grande, no es UTF-8 o sus marcadores son invalidos.

    Ejemplo:
        cambio = actualizar_readme(Path("."), progreso, "2026-10-26", "bf5ae56", sha)
    """
    ruta = raiz / RUTA_README
    if not ruta.is_file():
        raise FileNotFoundError(f"falta {RUTA_README}")
    if ruta.stat().st_size > MAX_BYTES_README:
        raise ValueError(f"{RUTA_README} excede el tamano permitido")
    with ruta.open(encoding="utf-8", newline="") as archivo:
        actual = archivo.read()
    seccion = generar_seccion(resumir_juego(progreso), fecha, hash_corto, sha256_esperado)
    nuevo = aplicar_seccion(actual, seccion)
    if nuevo == actual:
        return False
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        archivo.write(nuevo)
    return True

"""Adaptacion de las herramientas externas al sistema operativo donde corre la reconstruccion.

El SDK original (``CPPPSX.EXE``, ``CC1PSX.EXE``) y los binutils del toolchain son ejecutables de
Windows. En Windows se lanzan tal cual; en cualquier otro sistema:

* los ``.EXE`` se anteponen con Wine (variable ``WINE`` del entorno del kit, por omision ``wine``)
  y se silencia su depuracion con ``WINEDEBUG=-all``, porque su salida mezclada con la del compilador
  corromperia el ensamblador que se lee de la salida estandar;
* ``as``, ``ld``, ``objcopy`` y ``objdump`` de MIPS no se ejecutan con Wine: se usan binutils
  nativos del ``PATH`` con el prefijo de la variable ``BINUTILS_PREFIX`` (por omision
  ``mipsel-none-elf-``). Deben ser la misma version que usa el toolchain de Windows (GNU binutils
  2.40 de ``mipsel-none-elf``, que PSn00bSDK publica tambien para Linux): los binutils de Debian
  (``mipsel-linux-gnu-``) alinean las secciones a 16 bytes en lugar de 4, el ejecutable crece y
  deja de coincidir byte a byte. Un binutils nativo ademas arranca en milisegundos, mientras que
  bajo Wine cada llamada pagaria el arranque del emulador, que en una busqueda de miles de
  variantes es la diferencia entre aprovechar o no la maquina.

``maspsx`` y ``asm-differ`` son Python y no necesitan adaptacion.

Los nombres completos de las variables (``PSXDECOMP_WINE``, ``PSXDECOMP_BINUTILS_PREFIX``) y el
alias que el proyecto consumidor declare en su manifiesto los resuelve ``psxdecomp.entorno``.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from psxdecomp.entorno import SUFIJO_PREFIJO_BINUTILS, SUFIJO_WINE, VARIABLES_PROPIAS, Variables

WINE_POR_OMISION = "wine"
PREFIJO_BINUTILS_NATIVO = "mipsel-none-elf-"
ALIAS_BINUTILS = frozenset({"as", "ld", "objcopy", "objdump"})
EXTENSION_WINDOWS = ".exe"


def es_windows() -> bool:
    """
    Indica si el sistema operativo actual es Windows.

    Contexto:
        Unico punto donde se consulta la plataforma; las pruebas lo sustituyen para simular Linux
        sin tener Wine instalado.

    Returns:
        bool: ``True`` en Windows.

    Ejemplo:
        if not es_windows():
            ...
    """
    return sys.platform == "win32"


def comando_wine(entorno: Mapping[str, str], variables: Variables = VARIABLES_PROPIAS) -> str:
    """
    Devuelve el ejecutable de Wine configurado.

    Contexto:
        Permite apuntar a una instalacion concreta (``wine64``, una ruta absoluta) sin tocar codigo.

    Args:
        entorno (Mapping[str, str]): Variables de entorno.
        variables (Variables, opcional): Nombres de variable del proyecto; por omision solo el
            prefijo propio del kit.

    Returns:
        str: Valor de la variable ``WINE`` (prefijo propio o alias) o ``wine`` si no esta definida
        o esta en blanco.

    Ejemplo:
        wine = comando_wine({"PSXDECOMP_WINE": "/opt/wine/bin/wine"})
    """
    valores = (valor.strip() for valor in variables.definidas(SUFIJO_WINE, entorno))
    return next((valor for valor in valores if valor), WINE_POR_OMISION)


def prefijo_binutils(entorno: Mapping[str, str], variables: Variables = VARIABLES_PROPIAS) -> str:
    """
    Devuelve el prefijo de los binutils MIPS nativos.

    Contexto:
        El valor por omision es el del binutils 2.40 que usa el toolchain de Windows; otros prefijos
        (por ejemplo ``mipsel-linux-gnu-`` de Debian) producen objetos con otra alineacion de
        secciones.

    Args:
        entorno (Mapping[str, str]): Variables de entorno.
        variables (Variables, opcional): Nombres de variable del proyecto; por omision solo el
            prefijo propio del kit.

    Returns:
        str: Valor de la variable ``BINUTILS_PREFIX`` (prefijo propio o alias) o
        ``mipsel-none-elf-`` si ninguna esta definida. Una variable definida pero vacia se respeta
        (binutils sin prefijo).

    Ejemplo:
        prefijo = prefijo_binutils({})
    """
    return next(variables.definidas(SUFIJO_PREFIJO_BINUTILS, entorno), PREFIJO_BINUTILS_NATIVO)


def es_ejecutable_windows(ejecutable: str) -> bool:
    """
    Indica si un ejecutable es un programa de Windows por su extension.

    Contexto:
        La extension se compara sin distinguir mayusculas: el SDK trae ``CC1PSX.EXE`` y el lock
        puede nombrar otros en minusculas.

    Args:
        ejecutable (str): Ruta o nombre del programa.

    Returns:
        bool: ``True`` si termina en ``.exe``.

    Ejemplo:
        es_ejecutable_windows("pssn/bin/CC1PSX.EXE")
    """
    return ejecutable.lower().endswith(EXTENSION_WINDOWS)


def adaptar_comando(
    comando: Sequence[str],
    entorno: Mapping[str, str],
    *,
    windows: bool | None = None,
    variables: Variables = VARIABLES_PROPIAS,
) -> list[str]:
    """
    Antepone Wine a los comandos que lanzan un ejecutable de Windows fuera de Windows.

    Contexto:
        Lo aplica ``ejecutar_proceso`` (reconstruccion) antes de cada lanzamiento. Los argumentos
        se pasan sin cambios: Wine acepta rutas Unix (con espacios incluidos, porque no hay shell)
        y las barras normales que ya usan los comandos.

    Args:
        comando (Sequence[str]): Ejecutable y argumentos.
        entorno (Mapping[str, str]): Variables de entorno, para localizar Wine.
        windows (bool, opcional): Fuerza la plataforma; por omision se consulta ``es_windows``.
        variables (Variables, opcional): Nombres de variable del proyecto, para localizar Wine.

    Returns:
        list[str]: El mismo comando en Windows o si el programa no es ``.exe``; si no, con Wine delante.

    Ejemplo:
        adaptar_comando(["CC1PSX.EXE", "-O2"], {}, windows=False)
    """
    en_windows = es_windows() if windows is None else windows
    if en_windows or not comando or not es_ejecutable_windows(comando[0]):
        return list(comando)
    return [comando_wine(entorno, variables), *comando]


def entorno_proceso(base: Mapping[str, str], *, windows: bool | None = None) -> dict[str, str]:
    """
    Construye el entorno de un proceso externo.

    Contexto:
        Fuerza UTF-8 en Python y, fuera de Windows, silencia la depuracion de Wine. El usuario puede
        fijar ``WINEPREFIX`` o ``WINEDEBUG`` antes de lanzar la herramienta y se respeta.

    Args:
        base (Mapping[str, str]): Entorno de partida (normalmente ``os.environ``).
        windows (bool, opcional): Fuerza la plataforma; por omision se consulta ``es_windows``.

    Returns:
        dict[str, str]: Copia del entorno con las variables necesarias.

    Ejemplo:
        entorno = entorno_proceso(os.environ)
    """
    entorno = {**base, "PYTHONUTF8": "1"}
    if not (es_windows() if windows is None else windows):
        entorno.setdefault("WINEDEBUG", "-all")
    return entorno


def buscar_sin_distinguir_mayusculas(ruta: Path) -> Path | None:
    """
    Resuelve una ruta ignorando mayusculas en cada componente.

    Contexto:
        El lock nombra ``pssn/bin/CC1PSX.EXE`` y un toolchain copiado desde Windows puede traer otra
        capitalizacion; en un sistema de archivos sensible a mayusculas la ruta exacta no existiria.

    Args:
        ruta (Path): Ruta a resolver; su primer componente existente debe coincidir exactamente
            (la raiz del toolchain la fija el usuario).

    Returns:
        Path | None: La ruta existente que coincide, o ``None`` si no hay ninguna.

    Ejemplo:
        real = buscar_sin_distinguir_mayusculas(Path("toolchain/psyq-4.4/pssn/bin/cc1psx.exe"))
    """
    if ruta.exists():
        return ruta
    actual = next((padre for padre in ruta.parents if padre.exists()), None)
    if actual is None:
        return None
    for nombre in ruta.relative_to(actual).parts:
        if not actual.is_dir():
            return None
        coincidencias = [h for h in actual.iterdir() if h.name.lower() == nombre.lower()]
        if len(coincidencias) != 1:
            return None
        actual = coincidencias[0]
    return actual


def localizar_binutils(
    alias: str,
    entorno: Mapping[str, str],
    buscar: Callable[[str], str | None] | None = None,
    variables: Variables = VARIABLES_PROPIAS,
) -> Path | None:
    """
    Localiza un binutils MIPS nativo en el ``PATH``.

    Contexto:
        Sustituye a los ``.exe`` del componente ``binutils-mipsel`` fuera de Windows; ver
        ``resolver_herramienta``.

    Args:
        alias (str): ``as``, ``ld``, ``objcopy`` u ``objdump``.
        entorno (Mapping[str, str]): Variables de entorno, para el prefijo.
        buscar (Callable[[str], str | None], opcional): Buscador de ejecutables; por omision
            ``shutil.which``, resuelto en cada llamada.
        variables (Variables, opcional): Nombres de variable del proyecto, para el prefijo.

    Returns:
        Path | None: Ruta absoluta del binutils, o ``None`` si no esta instalado.

    Raises:
        ValueError: Si el alias no es un binutils conocido.

    Ejemplo:
        ensamblador = localizar_binutils("as", os.environ)
    """
    if alias not in ALIAS_BINUTILS:
        raise ValueError(f"'{alias}' no es un binutils conocido")
    buscador = buscar or shutil.which
    encontrado = buscador(f"{prefijo_binutils(entorno, variables)}{alias}")
    return Path(encontrado) if encontrado else None

"""Compilacion de los archivos C del juego con el compilador original del SDK.

Cada archivo pasa por la misma cadena que uso el estudio: preprocesador del SDK
(``CPPPSX.EXE``), compilador ``CC1PSX.EXE`` (GCC 2.8.1) con ``-O2 -G0``, ``maspsx`` que imita al
ensamblador ``ASPSX`` 2.79 y GNU ``as``. El compilador propio no preprocesa, por eso el paso
previo es obligatorio: sin el, ``#include`` y las macros llegan intactas al compilador y falla.

La capa pura (comandos y lectura de la lista de secciones) no toca disco; ``compilar_fuente``
es la unica funcion que lanza procesos y lo hace mediante el ejecutor recibido.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from tools.reconstruccion.dominio import MAX_VALOR_G, EjecutableReferencia
from tools.reconstruccion.infraestructura import (
    Ejecutor,
    Herramientas,
    construir_con_compilador,
    ejecutar_proceso,
    leer_valores_g,
)
from tools.toolchain.dominio import Componente
from tools.toolchain.instalacion import resolver_herramienta

VERSION_ASPSX = "2.79"
OPCIONES_COMPILADOR = ("-quiet", "-O2")
CARPETA_INCLUDE = "include"
CARPETA_MACROS = "asm/include"
CARPETA_FUENTES = "src"
CARPETA_SALIDA = "build"
TIMEOUT_PREPROCESAR_S = 120
TIMEOUT_COMPILAR_S = 120
TIMEOUT_ENSAMBLAR_S = 120
PREFIJOS_DE_DATOS = (".data", ".rodata", ".rdata", ".bss", ".sdata", ".sbss", ".lit", ".scommon")
_PATRON_DEFINICION = re.compile(r"^[A-Z_][A-Z0-9_]{0,31}$")
_PATRON_SECCION = re.compile(r"^\s*\d+\s+(\S+)\s+([0-9a-fA-F]{8})\s", re.MULTILINE)
_PATRON_RUTA = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*$")


@dataclass(frozen=True)
class HerramientasCompilacion:
    """Ejecutables que intervienen al compilar un archivo C.

    Attributes:
        python: Interprete que ejecuta ``maspsx``.
        preprocesador: ``CPPPSX.EXE``.
        compilador: ``CC1PSX.EXE``.
        maspsx: Script ``maspsx.py``.
        ensamblador: ``mipsel-none-elf-as``.
        objdump: ``mipsel-none-elf-objdump`` (lista las secciones del objeto).
    """

    python: str
    preprocesador: Path
    compilador: Path
    maspsx: Path
    ensamblador: Path
    objdump: Path


def resolver_herramientas_compilacion(
    lock: dict[str, Componente], raiz_toolchain: Path, python: str
) -> HerramientasCompilacion:
    """
    Localiza las herramientas de compilacion instaladas.

    Contexto:
        Complementa a ``infraestructura.resolver_herramientas``: solo las ordenes que compilan
        (``build`` con archivos C y ``diff``) necesitan el SDK y ``maspsx``.

    Args:
        lock (dict[str, Componente]): Lock validado.
        raiz_toolchain (Path): Raiz del toolchain.
        python (str): Interprete que ejecutara ``maspsx``.

    Returns:
        HerramientasCompilacion: Rutas resueltas.

    Raises:
        FileNotFoundError: Si alguna herramienta no esta instalada.
        ValueError: Si el lock no declara un componente o alias.

    Ejemplo:
        herramientas = resolver_herramientas_compilacion(lock, Path("toolchain"), sys.executable)
    """
    return HerramientasCompilacion(
        python=python,
        preprocesador=resolver_herramienta(lock, raiz_toolchain, "psyq-4.4", "cpppsx"),
        compilador=resolver_herramienta(lock, raiz_toolchain, "psyq-4.4", "cc1psx"),
        maspsx=resolver_herramienta(lock, raiz_toolchain, "maspsx", "maspsx"),
        ensamblador=resolver_herramienta(lock, raiz_toolchain, "binutils-mipsel", "as"),
        objdump=resolver_herramienta(lock, raiz_toolchain, "binutils-mipsel", "objdump"),
    )


def comando_preprocesar(
    preprocesador: Path, fuente: str, salida: str, incluir: str, definiciones: Sequence[str] = ()
) -> list[str]:
    """
    Devuelve los argumentos que preprocesan un archivo C.

    Contexto:
        Primer paso de la compilacion; las definiciones permiten compilar el intento en C de
        una funcion con ``NON_MATCHING`` sin tocar la construccion normal.

    Args:
        preprocesador (Path): Ruta de ``CPPPSX.EXE``.
        fuente (str): Archivo ``.c`` de entrada.
        salida (str): Archivo preprocesado.
        incluir (str): Carpeta de cabeceras del proyecto.
        definiciones (Sequence[str], opcional): Macros a definir (``NON_MATCHING``).

    Returns:
        list[str]: Lista de argumentos para ``subprocess`` (sin shell).

    Raises:
        ValueError: Si una definicion no es un identificador de macro en mayusculas.

    Ejemplo:
        comando = comando_preprocesar(Path("CPPPSX.EXE"), "src/a.c", "build/a.i", "include")
    """
    for definicion in definiciones:
        if not _PATRON_DEFINICION.match(definicion):
            raise ValueError("la definicion de preprocesador debe ser un identificador en mayusculas")
    return [
        str(preprocesador),
        f"-I{incluir}",
        *(f"-D{definicion}" for definicion in definiciones),
        fuente,
        "-o",
        salida,
    ]


def comando_compilar(compilador: Path, entrada: str, salida: str, valor_g: int = 0) -> list[str]:
    """
    Devuelve los argumentos que compilan C preprocesado a ensamblador.

    Contexto:
        ``-O2`` es el valor identificado del compilador original. ``-G0`` es el umbral de datos
        pequenos por omision (la cabecera declara ``gp0 = 0``); los archivos cuyo original uso datos
        pequenos declaran otro valor en ``config/opciones_compilacion.toml``.

    Args:
        compilador (Path): Ruta de ``CC1PSX.EXE``.
        entrada (str): Archivo preprocesado.
        salida (str): Ensamblador de salida.
        valor_g (int, opcional): Umbral ``-G`` de datos pequenos.

    Returns:
        list[str]: Lista de argumentos.

    Raises:
        ValueError: Si ``valor_g`` no es un entero entre 0 y ``MAX_VALOR_G``.

    Ejemplo:
        comando = comando_compilar(Path("CC1PSX.EXE"), "build/a.i", "build/a.s", 8)
    """
    if isinstance(valor_g, bool) or not isinstance(valor_g, int) or not 0 <= valor_g <= MAX_VALOR_G:
        raise ValueError(f"el valor de -G debe ser un entero entre 0 y {MAX_VALOR_G}")
    return [str(compilador), *OPCIONES_COMPILADOR, f"-G{valor_g}", entrada, "-o", salida]


def comando_maspsx(
    herramientas: HerramientasCompilacion, entrada: str, objeto: str, incluir: str
) -> list[str]:
    """
    Devuelve los argumentos que ensamblan la salida del compilador con ``maspsx``.

    Contexto:
        ``maspsx`` reescribe el ensamblador como lo haria ASPSX (macros de carga y relleno de
        huecos de salto) y despues invoca a GNU ``as``. Su ruta de ``as`` debe ser absoluta:
        no la resuelve respecto al directorio de trabajo.

    Args:
        herramientas (HerramientasCompilacion): Interprete, ``maspsx.py`` y ensamblador (ruta absoluta).
        entrada (str): Ensamblador producido por el compilador.
        objeto (str): Objeto de salida.
        incluir (str): Carpeta donde estan las macros incluidas por el ensamblador.

    Returns:
        list[str]: Lista de argumentos.

    Ejemplo:
        comando = comando_maspsx(herramientas, "a.s", "a.o", "asm/include")
    """
    return [
        herramientas.python,
        str(herramientas.maspsx),
        f"--aspsx-version={VERSION_ASPSX}",
        "--run-assembler",
        f"--gnu-as-path={herramientas.ensamblador}",
        "-EL",
        "-march=r3000",
        "-mips1",
        "-G0",
        "-I",
        incluir,
        "-o",
        objeto,
        entrada,
    ]


def comando_secciones(objdump: Path, objeto: str) -> list[str]:
    """Devuelve los argumentos que listan las secciones de un objeto."""
    return [str(objdump), "-h", objeto]


def leer_secciones(salida_objdump: str) -> dict[str, int]:
    """
    Extrae nombre y tamano de cada seccion de la salida de ``objdump -h``.

    Contexto:
        Permite comprobar que un objeto solo aporta codigo; ver ``verificar_solo_texto``.

    Args:
        salida_objdump (str): Texto producido por ``objdump -h``.

    Returns:
        dict[str, int]: Tamano en bytes por seccion.

    Ejemplo:
        secciones = leer_secciones(salida)
    """
    return {nombre: int(tamano, 16) for nombre, tamano in _PATRON_SECCION.findall(salida_objdump)}


def verificar_solo_texto(objeto: str, secciones: Mapping[str, int], declaradas: Collection[str] = ()) -> None:
    """
    Rechaza un objeto que aporta secciones de datos que su subsegmento no declara.

    Contexto:
        El script del enlazador solo recoge de un objeto C las secciones que la particion le
        asigna (``.text`` y, si hay un subsegmento ``.rodata`` o ``.data`` con su mismo nombre,
        esas) y descarta el resto en silencio. El compilador del SDK deja las constantes, las
        cadenas y las tablas de salto de un ``switch`` en ``.rdata``: sin subsegmento el
        ejecutable saldria sin ellas (y con el tamano equivocado) sin que ninguna herramienta
        avisara de la causa. Fallar aqui, con el archivo y la seccion, ahorra esa busqueda.

    Args:
        objeto (str): Ruta del objeto (para el mensaje).
        secciones (Mapping[str, int]): Tamano por seccion, de ``leer_secciones``.
        declaradas (Collection[str], opcional): Secciones de datos que el subsegmento del archivo
            declara (por ejemplo ``{".rodata"}``).

    Raises:
        ValueError: Si una seccion de datos con contenido no esta declarada.

    Ejemplo:
        verificar_solo_texto("build/src/a.c.o", {".text": 16, ".rodata": 8}, {".rodata"})
    """
    for nombre in sorted(secciones):
        if secciones[nombre] > 0 and nombre.startswith(PREFIJOS_DE_DATOS) and nombre not in declaradas:
            raise ValueError(
                f"{objeto}: genera {secciones[nombre]} bytes en la seccion inesperada '{nombre}': "
                f"declare en config/splat.yaml un subsegmento '{nombre}' con el nombre del archivo "
                "(ver docs/DESCOMPILACION.md, seccion de rodata por archivo)"
            )


def rutas_intermedias(objeto: str) -> tuple[str, str]:
    """
    Deduce las rutas del preprocesado y del ensamblador a partir del objeto.

    Contexto:
        ``build/src/a.c.o`` produce ``build/src/a.c.i`` y ``build/src/a.c.s`` junto a el.

    Args:
        objeto (str): Ruta relativa del objeto, terminada en ``.c.o``.

    Returns:
        tuple[str, str]: Rutas del preprocesado y del ensamblador.

    Raises:
        ValueError: Si el objeto no termina en ``.c.o`` o su ruta no es relativa y simple.

    Ejemplo:
        preprocesado, ensamblador = rutas_intermedias("build/src/a.c.o")
    """
    if not objeto.endswith(".c.o") or not _PATRON_RUTA.match(objeto) or ".." in objeto.split("/"):
        raise ValueError(f"objeto '{objeto}' no es una ruta de objeto C valida")
    base = objeto[: -len(".o")]
    return f"{base}.i", f"{base}.s"


def validar_fuente(fuente: str) -> None:
    """
    Comprueba que una ruta de fuente pertenece a ``src/`` y es un ``.c`` simple.

    Contexto:
        La ruta sale del script del enlazador o de la linea de ordenes; no se confia en ella
        para construir comandos.

    Args:
        fuente (str): Ruta relativa del archivo C.

    Raises:
        ValueError: Si no esta dentro de ``src/``, no termina en ``.c`` o contiene ``..``.

    Ejemplo:
        validar_fuente("src/code_80014AC4.c")
    """
    partes = fuente.split("/")
    if (
        not fuente.endswith(".c")
        or partes[0] != CARPETA_FUENTES
        or ".." in partes
        or not _PATRON_RUTA.match(fuente)
    ):
        raise ValueError(f"fuente '{fuente}' no es un archivo .c dentro de {CARPETA_FUENTES}/")


def compilar_fuente(
    raiz: Path,
    fuente: str,
    objeto: str,
    herramientas: HerramientasCompilacion,
    ejecutar: Ejecutor,
    *,
    definiciones: Sequence[str] = (),
    exigir_solo_texto: bool = True,
    secciones_declaradas: Collection[str] = (),
    valor_g: int = 0,
) -> None:
    """
    Compila un archivo C de ``src/`` a un objeto ELF reubicable.

    Contexto:
        La usan ``build`` (para cada ``src/*.c`` que enlaza el script) y ``diff`` (para el
        archivo que contiene la funcion). Se ejecuta con el directorio de trabajo en la raiz del
        repositorio porque el ensamblador incluido por ``INCLUDE_ASM`` usa rutas relativas a ella.

    Args:
        raiz (Path): Raiz del repositorio.
        fuente (str): Ruta relativa del ``.c`` dentro de ``src/``.
        objeto (str): Ruta relativa del objeto de salida (termina en ``.c.o``).
        herramientas (HerramientasCompilacion): Herramientas resueltas.
        ejecutar (Ejecutor): Ejecutor de procesos.
        definiciones (Sequence[str], opcional): Macros de preprocesador a definir.
        exigir_solo_texto (bool, opcional): Si es verdadero, falla si el objeto aporta datos no declarados.
        secciones_declaradas (Collection[str], opcional): Secciones de datos que el subsegmento
            del archivo declara y que, por tanto, se aceptan.
        valor_g (int, opcional): Umbral ``-G`` de datos pequenos para este archivo.

    Raises:
        ValueError: Si la fuente o el objeto no son rutas validas, o el objeto aporta datos
            cuando se exige solo codigo.
        FileNotFoundError: Si la fuente no existe.
        ProcesoError: Si alguna herramienta falla o excede su tiempo limite.

    Ejemplo:
        compilar_fuente(Path("."), "src/a.c", "build/src/a.c.o", herramientas, ejecutar_proceso)
    """
    validar_fuente(fuente)
    compilar_archivo(
        raiz,
        fuente,
        objeto,
        herramientas,
        ejecutar,
        definiciones=definiciones,
        exigir_solo_texto=exigir_solo_texto,
        secciones_declaradas=secciones_declaradas,
        valor_g=valor_g,
    )


def compilar_archivo(
    raiz: Path,
    fuente: str,
    objeto: str,
    herramientas: HerramientasCompilacion,
    ejecutar: Ejecutor,
    *,
    definiciones: Sequence[str] = (),
    exigir_solo_texto: bool = True,
    secciones_declaradas: Collection[str] = (),
    valor_g: int = 0,
) -> None:
    """
    Compila un archivo C cualquiera (de ``src/`` o una variante de prueba) a un objeto ELF.

    Contexto:
        Nucleo comun de ``compilar_fuente`` (que solo admite ``src/``) y del banco de variantes
        de ``probar`` (archivos fuera del repositorio). Ejecuta preprocesador, compilador y
        ensamblador con el directorio de trabajo en la raiz del repositorio.

    Args:
        raiz (Path): Raiz del repositorio.
        fuente (str): Ruta del ``.c`` (relativa a la raiz o absoluta).
        objeto (str): Ruta relativa del objeto de salida (termina en ``.c.o``).
        herramientas (HerramientasCompilacion): Herramientas resueltas.
        ejecutar (Ejecutor): Ejecutor de procesos.
        definiciones (Sequence[str], opcional): Macros de preprocesador a definir.
        exigir_solo_texto (bool, opcional): Si es verdadero, falla si el objeto aporta datos no declarados.
        secciones_declaradas (Collection[str], opcional): Secciones de datos aceptadas.
        valor_g (int, opcional): Umbral ``-G`` de datos pequenos.

    Raises:
        ValueError: Si el objeto no es una ruta valida o aporta datos no declarados.
        FileNotFoundError: Si la fuente no existe.
        ProcesoError: Si alguna herramienta falla o excede su tiempo limite.

    Ejemplo:
        compilar_archivo(Path("."), "C:/variantes/a.c", "build/diff/a.c.o", herramientas, ejecutar)
    """
    preprocesado, ensamblador = rutas_intermedias(objeto)
    if not (raiz / fuente).is_file():
        raise FileNotFoundError(f"falta el fuente '{fuente}'")
    (raiz / objeto).parent.mkdir(parents=True, exist_ok=True)
    ejecutar(
        comando_preprocesar(herramientas.preprocesador, fuente, preprocesado, CARPETA_INCLUDE, definiciones),
        raiz,
        TIMEOUT_PREPROCESAR_S,
    )
    ejecutar(
        comando_compilar(herramientas.compilador, preprocesado, ensamblador, valor_g),
        raiz,
        TIMEOUT_COMPILAR_S,
    )
    ejecutar(
        comando_maspsx(herramientas, ensamblador, objeto, CARPETA_MACROS),
        raiz,
        TIMEOUT_ENSAMBLAR_S,
    )
    if exigir_solo_texto:
        salida = ejecutar(comando_secciones(herramientas.objdump, objeto), raiz, TIMEOUT_ENSAMBLAR_S)
        verificar_solo_texto(objeto, leer_secciones(salida), secciones_declaradas)


def construir_mixto(
    raiz: Path,
    referencia: EjecutableReferencia,
    herramientas: Herramientas,
    obtener_compilacion: Callable[[], HerramientasCompilacion],
    ejecutar: Ejecutor = ejecutar_proceso,
    *,
    declaradas: Mapping[str, Collection[str]] | None = None,
) -> Path:
    """
    Construye el ejecutable con los archivos C compilados y el resto ensamblado.

    Contexto:
        Implementa ``build``. El script del enlazador que genera el particionador decide que
        objetos entran y en que orden; los ``src/*.c`` se compilan con ``compilar_fuente`` en la
        construccion normal (sin ``NON_MATCHING``) y exigiendo que solo aporten codigo. Las
        herramientas de compilacion se piden solo cuando aparece el primer archivo C, de modo
        que una construccion solo de ensamblador no necesita el SDK instalado.

    Args:
        raiz (Path): Raiz del repositorio.
        referencia (EjecutableReferencia): Hechos del ejecutable.
        herramientas (Herramientas): Ensamblador, enlazador y objcopy.
        obtener_compilacion (Callable[[], HerramientasCompilacion]): Resuelve las herramientas
            de compilacion; puede lanzar ``FileNotFoundError`` si no estan instaladas.
        ejecutar (Ejecutor, opcional): Ejecutor de procesos, sustituible en pruebas.
        declaradas (Mapping[str, Collection[str]], opcional): Secciones de datos que la particion
            declara por archivo (clave: nombre sin ``src/`` ni ``.c``), de ``secciones_declaradas``.

    Returns:
        Path: Ruta del ejecutable generado (``build/<nombre>``).

    Raises:
        FileNotFoundError: Si falta el script del enlazador, un fuente o una herramienta.
        ValueError: Si un objeto aporta datos o el cuerpo enlazado no mide ``t_size``.
        ProcesoError: Si una herramienta falla.

    Ejemplo:
        destino = construir_mixto(Path("."), referencia, herramientas, lambda: compilacion)
    """
    resueltas: list[HerramientasCompilacion] = []
    valores_g = leer_valores_g(raiz)

    def compilar(fuente: str, objeto: str) -> None:
        if not resueltas:
            resueltas.append(obtener_compilacion())
        permitidas = (declaradas or {}).get(Path(fuente).stem, ())
        compilar_fuente(
            raiz,
            fuente,
            objeto,
            resueltas[0],
            ejecutar,
            secciones_declaradas=permitidas,
            valor_g=valores_g.get(Path(fuente).stem, 0),
        )

    return construir_con_compilador(raiz, referencia, herramientas, compilar, ejecutar)

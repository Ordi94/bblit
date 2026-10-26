"""Acceso a disco y procesos de la reconstruccion: particionar, ensamblar, enlazar y verificar.

Toda ejecucion de herramientas externas recibe una lista de argumentos (nunca una cadena con
shell), un directorio de trabajo, un tiempo limite y se hace en primer plano. Las rutas del
disco pueden contener espacios y parentesis sin que eso afecte a ningun comando.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from tools.reconstruccion import dominio
from tools.reconstruccion.dominio import EjecutableReferencia
from tools.reconstruccion.fuentes_c import MAX_BYTES_FUENTE
from tools.toolchain import iso9660
from tools.toolchain.dominio import Componente
from tools.toolchain.instalacion import resolver_herramienta

TIMEOUT_SPLAT_S = 900
TIMEOUT_ENSAMBLAR_S = 300
TIMEOUT_ENLAZAR_S = 600
MAX_BYTES_REFERENCIA = 64 * 1024
MAX_BYTES_SIMBOLOS = 4 * 1024 * 1024
SCRIPT_ENLAZADOR = "build/SLUS_008.ld"
SIMBOLOS_AUTOMATICOS = ("build/undefined_funcs_auto.txt", "build/undefined_syms_auto.txt")
SIMBOLOS_ENTRADA = "build/simbolos_entrada.txt"
SIMBOLOS_PROYECTO = "config/symbols.txt"
CONFIGURACION_SPLAT = "config/splat.yaml"
OPCIONES_COMPILACION = "config/opciones_compilacion.toml"
SCRIPT_GP = "build/gp.ld"
CARPETA_MACROS = "asm/include"
ELF_SALIDA = "build/SLUS_008.elf"
MAPA_SALIDA = "build/SLUS_008.map"
BINARIO_SALIDA = "build/SLUS_008.bin"
OBJETOS_SALIDA = "build/asm"
OBJETOS_C_SALIDA = "build/src"
CARPETA_DIFF = "build/diff"
PROGRESO_JSON = "build/progreso.json"
# Subcarpetas de asm/ y expected/ que pertenecen a otras herramientas del repositorio
# (reconstruccion de superposiciones): 'split' y 'clean' no las tocan. Lo mismo vale para
# build/overlay, build/emulador y build/bblit_prueba.*, que no figuran en artefactos_de_build.
SUBCARPETAS_AJENAS = ("overlay",)

Ejecutor = Callable[[Sequence[str], Path, int], str]
"""Funcion que ejecuta un comando en un directorio con tiempo limite y devuelve su salida."""

CompiladorC = Callable[[str, str], None]
"""Funcion que compila un archivo C (ruta relativa) a un objeto (ruta relativa)."""


class ProcesoError(RuntimeError):
    """Una herramienta externa termino con error o excedio su tiempo limite."""


def ejecutar_proceso(comando: Sequence[str], directorio: Path, timeout_s: int) -> str:
    """
    Ejecuta un comando en primer plano, sin shell y con tiempo limite.

    Contexto:
        Unico punto por el que la reconstruccion lanza procesos; las pruebas lo sustituyen
        por un doble. Fuerza UTF-8 en el entorno porque la consola de Windows no lo usa por
        defecto y el particionador imprime texto no ASCII.

    Args:
        comando (Sequence[str]): Ejecutable y argumentos como lista.
        directorio (Path): Directorio de trabajo.
        timeout_s (int): Segundos maximos de ejecucion.

    Returns:
        str: Salida estandar del proceso.

    Raises:
        ProcesoError: Si el codigo de salida no es cero o se excede el tiempo limite; el
            mensaje nombra la herramienta y un extracto acotado de su salida de error.

    Ejemplo:
        salida = ejecutar_proceso(["python", "--version"], Path("."), 30)
    """
    herramienta = Path(comando[0]).name
    entorno = {**os.environ, "PYTHONUTF8": "1"}
    try:
        resultado = subprocess.run(
            list(comando),
            cwd=directorio,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
            stdin=subprocess.DEVNULL,
            env=entorno,
        )
    except subprocess.TimeoutExpired:
        raise ProcesoError(f"{herramienta}: excedio el tiempo limite de {timeout_s} s") from None
    if resultado.returncode != 0:
        extracto = (resultado.stderr or resultado.stdout).strip()[-1500:]
        raise ProcesoError(f"{herramienta}: termino con codigo {resultado.returncode}\n{extracto}")
    return resultado.stdout


def sha256_archivo(ruta: Path) -> str:
    """
    Calcula el SHA-256 de un archivo leyendolo por bloques.

    Contexto:
        Base de la verificacion byte a byte: el ejecutable reconstruido y el original se
        comparan por huella.

    Args:
        ruta (Path): Archivo a resumir.

    Returns:
        str: Huella en hexadecimal minusculas.

    Raises:
        FileNotFoundError: Si el archivo no existe.

    Ejemplo:
        huella = sha256_archivo(Path("build/SLUS_008.38"))
    """
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def leer_referencia(ruta: Path) -> EjecutableReferencia:
    """
    Lee y valida ``config/ejecutable.json``.

    Contexto:
        Primer paso de todas las ordenes de construccion.

    Args:
        ruta (Path): Ubicacion del archivo.

    Returns:
        EjecutableReferencia: Hechos del ejecutable validados.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si es demasiado grande, no es JSON o no cumple el esquema.

    Ejemplo:
        referencia = leer_referencia(Path("config/ejecutable.json"))
    """
    if not ruta.is_file():
        raise FileNotFoundError("no se encontro config/ejecutable.json")
    if ruta.stat().st_size > MAX_BYTES_REFERENCIA:
        raise ValueError("config/ejecutable.json excede el tamano permitido")
    try:
        datos: Any = json.loads(ruta.read_text(encoding="utf-8"))
    except ValueError:
        raise ValueError("config/ejecutable.json no es JSON valido") from None
    return dominio.referencia_desde_datos(datos)


def localizar_imagen(disc: Path) -> Path | None:
    """
    Busca la imagen de CD (``.bin``) a partir de lo que el usuario indico como disco.

    Contexto:
        ``BBLIT_DISC`` puede apuntar al propio ``.bin``, a su ``.cue``, a la carpeta que
        contiene el ``.bin`` o a la carpeta superior que lo guarda en una subcarpeta.

    Args:
        disc (Path): Archivo o carpeta indicados.

    Returns:
        Path | None: Ruta de la imagen, o ``None`` si ``disc`` es una carpeta sin ninguna.

    Raises:
        ValueError: Si ``disc`` es un archivo que no es ``.bin`` ni ``.cue``, o si hay mas de
            una imagen candidata.
        FileNotFoundError: Si es un ``.cue`` sin su ``.bin`` hermano.

    Ejemplo:
        imagen = localizar_imagen(Path("disc"))
    """
    if disc.is_file():
        sufijo = disc.suffix.lower()
        if sufijo not in (".bin", ".cue"):
            raise ValueError("BBLIT_DISC debe ser una carpeta, un .bin o un .cue")
        imagen = disc.with_suffix(".bin") if sufijo == ".cue" else disc
        if not imagen.is_file():
            raise FileNotFoundError("el .cue no tiene un .bin hermano")
        return imagen
    candidatas = sorted(disc.glob("*.bin"))
    if not candidatas:
        candidatas = sorted(p for hijo in disc.iterdir() if hijo.is_dir() for p in hijo.glob("*.bin"))
    if len(candidatas) > 1:
        raise ValueError("hay varias imagenes .bin en el disco: indique la ruta exacta de una")
    return candidatas[0] if candidatas else None


def extraer_de_imagen(imagen: Path, referencia: EjecutableReferencia, destino: Path) -> None:
    """
    Extrae el ejecutable del sistema de archivos ISO 9660 de la imagen de CD.

    Contexto:
        Permite construir en una maquina que solo tiene el disco, sin sistema de archivos
        extraido previamente.

    Args:
        imagen (Path): Imagen ``.bin`` (sectores de 2352 o 2048 bytes).
        referencia (EjecutableReferencia): Nombre y tamano esperados del ejecutable.
        destino (Path): Archivo de salida.

    Raises:
        ValueError: Si la imagen no es ISO 9660 valida, no contiene el ejecutable en la raiz
            o su tamano no coincide con el esperado.

    Ejemplo:
        extraer_de_imagen(Path("juego.bin"), referencia, Path("expected/SLUS_008.38"))
    """
    with imagen.open("rb") as fuente:

        def leer_rango(desde: int, largo: int) -> bytes:
            fuente.seek(desde)
            return fuente.read(largo)

        lector = iso9660.crear_lector(imagen.stat().st_size, leer_rango)
        for entrada in iso9660.listar_archivos(lector):
            if str(entrada.ruta).upper() == referencia.nombre.upper():
                if entrada.tamano != referencia.tamano:
                    raise ValueError("el ejecutable de la imagen no tiene el tamano esperado")
                destino.write_bytes(iso9660.leer_archivo(lector, entrada))
                return
    raise ValueError(f"la imagen no contiene {referencia.nombre} en el directorio raiz")


def obtener_original(raiz: Path, disc: Path | None, referencia: EjecutableReferencia) -> Path:
    """
    Obtiene la ruta del ejecutable original a partir de la configuracion del disco.

    Contexto:
        Si el disco ya tiene el sistema de archivos extraido (``fs/<nombre>``) se usa tal
        cual; si solo hay imagen de CD, el ejecutable se extrae a ``expected/``. Nunca se
        escribe en la carpeta del disco.

    Args:
        raiz (Path): Raiz del repositorio (donde vive ``expected/``).
        disc (Path, opcional): Valor de ``BBLIT_DISC``, ``--disc`` o ``config/local.toml``.
        referencia (EjecutableReferencia): Datos del ejecutable.

    Returns:
        Path: Archivo con el ejecutable original.

    Raises:
        ValueError: Si no se configuro el disco, la imagen es ambigua o invalida.
        FileNotFoundError: Si no hay ni ``fs/<nombre>`` ni imagen.

    Ejemplo:
        original = obtener_original(Path("."), Path("disc"), referencia)
    """
    if disc is None:
        raise ValueError(
            "falta la ubicacion del disco: defina BBLIT_DISC, --disc o 'disc' en config/local.toml"
        )
    if not disc.exists():
        raise FileNotFoundError("la ubicacion del disco no existe")
    extraido = disc / "fs" / referencia.nombre
    if disc.is_dir() and extraido.is_file():
        return extraido
    imagen = localizar_imagen(disc)
    if imagen is None:
        raise FileNotFoundError(
            f"no se encontro fs/{referencia.nombre} ni una imagen .bin en la ubicacion del disco"
        )
    destino = raiz / "expected" / referencia.nombre
    destino.parent.mkdir(parents=True, exist_ok=True)
    extraer_de_imagen(imagen, referencia, destino)
    return destino


@dataclass(frozen=True)
class Herramientas:
    """Ejecutables necesarios para particionar y reconstruir.

    Attributes:
        python: Interprete que ejecuta el particionador.
        ensamblador: ``mipsel-none-elf-as``.
        enlazador: ``mipsel-none-elf-ld``.
        objcopy: ``mipsel-none-elf-objcopy``.
    """

    python: str
    ensamblador: Path
    enlazador: Path
    objcopy: Path


def resolver_herramientas(lock: dict[str, Componente], raiz_toolchain: Path, python: str) -> Herramientas:
    """
    Localiza los binutils instalados.

    Contexto:
        Evita rutas fijas: todo sale del lock y de la raiz del toolchain.

    Args:
        lock (dict[str, Componente]): Lock validado.
        raiz_toolchain (Path): Raiz del toolchain.
        python (str): Interprete a usar para el particionador.

    Returns:
        Herramientas: Rutas resueltas.

    Raises:
        FileNotFoundError: Si alguna herramienta no esta instalada.

    Ejemplo:
        herramientas = resolver_herramientas(lock, Path("toolchain"), sys.executable)
    """
    return Herramientas(
        python=python,
        ensamblador=resolver_herramienta(lock, raiz_toolchain, "binutils-mipsel", "as"),
        enlazador=resolver_herramienta(lock, raiz_toolchain, "binutils-mipsel", "ld"),
        objcopy=resolver_herramienta(lock, raiz_toolchain, "binutils-mipsel", "objcopy"),
    )


def _borrar_arbol(ruta: Path) -> bool:
    """Elimina un archivo, enlace o carpeta (aun con atributo de solo lectura); informa si existia."""
    if ruta.is_symlink() or ruta.is_file():
        ruta.unlink()
        return True
    if not ruta.is_dir():
        return False

    def forzar(funcion: Callable[[str], object], destino: str, _error: BaseException) -> None:
        os.chmod(destino, stat.S_IWRITE)
        funcion(destino)

    shutil.rmtree(ruta, onexc=forzar)
    return True


def _borrar_conservando_ajenos(ruta: Path) -> list[str]:
    """
    Elimina una carpeta propia conservando las subcarpetas de ``SUBCARPETAS_AJENAS``.

    Contexto:
        ``asm/`` y ``expected/`` los regenera esta herramienta, pero otras herramientas del
        repositorio guardan ahi sus propias subcarpetas; borrarlas rompe su trabajo en curso.

    Args:
        ruta (Path): Carpeta (o archivo) a eliminar.

    Returns:
        list[str]: Nombres eliminados relativos al padre de ``ruta``: la propia carpeta si no
        tenia contenido ajeno, o ``<carpeta>/<hijo>`` por cada hijo propio si lo tenia.

    Ejemplo:
        eliminados = _borrar_conservando_ajenos(Path("asm"))
    """
    if ruta.is_dir() and any((ruta / ajena).is_dir() for ajena in SUBCARPETAS_AJENAS):
        propios = sorted(h for h in ruta.iterdir() if h.name not in SUBCARPETAS_AJENAS)
        return [f"{ruta.name}/{h.name}" for h in propios if _borrar_arbol(h)]
    return [ruta.name] if _borrar_arbol(ruta) else []


def listar_fuentes_c(raiz: Path) -> dict[str, str]:
    """
    Lee el texto de todos los archivos ``src/*.c``.

    Contexto:
        Los estados de las funciones (progreso y diff) se derivan del texto real de estos
        archivos. Se leen con una cota de tamano porque su contenido lo edita una persona y no
        debe poder agotar la memoria de la herramienta.

    Args:
        raiz (Path): Raiz del repositorio.

    Returns:
        dict[str, str]: Texto por ruta relativa (``src/<archivo>.c``), ordenado por ruta; vacio
        si no existe ``src/``.

    Raises:
        ValueError: Si algun archivo excede ``MAX_BYTES_FUENTE``.

    Ejemplo:
        textos = listar_fuentes_c(Path("."))
    """
    carpeta = raiz / "src"
    textos: dict[str, str] = {}
    if not carpeta.is_dir():
        return textos
    for ruta in sorted(carpeta.glob("*.c")):
        if ruta.stat().st_size > MAX_BYTES_FUENTE:
            raise ValueError(f"src/{ruta.name} excede el tamano permitido")
        textos[f"src/{ruta.name}"] = ruta.read_text(encoding="utf-8")
    return textos


def leer_secciones_declaradas(raiz: Path) -> dict[str, frozenset[str]]:
    """
    Lee ``config/splat.yaml`` y devuelve las secciones que cada archivo C puede generar.

    Contexto:
        La construccion compara cada objeto C contra lo que la particion le asigna; un
        repositorio sin ``splat.yaml`` (pruebas) no declara nada y cada objeto solo puede
        aportar codigo.

    Args:
        raiz (Path): Raiz del repositorio.

    Returns:
        dict[str, frozenset[str]]: Ver ``dominio.secciones_declaradas``; vacio si no hay archivo.

    Raises:
        ValueError: Si el archivo no es YAML valido o no tiene la forma esperada.

    Ejemplo:
        declaradas = leer_secciones_declaradas(Path("."))
    """
    ruta = raiz / CONFIGURACION_SPLAT
    if not ruta.is_file():
        return {}
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ValueError(f"{CONFIGURACION_SPLAT} no es YAML valido") from None
    return dominio.secciones_declaradas(datos)


def leer_valores_g(raiz: Path) -> dict[str, int]:
    """
    Lee ``config/opciones_compilacion.toml`` y devuelve el ``-G`` declarado por archivo C.

    Contexto:
        ``build`` y ``diff`` deben compilar cada archivo con las mismas opciones, asi que ambos
        las obtienen de aqui. Un repositorio sin el archivo compila todo con ``-G0``.

    Args:
        raiz (Path): Raiz del repositorio.

    Returns:
        dict[str, int]: Valor de ``-G`` por nombre de archivo; vacio si no hay archivo.

    Raises:
        ValueError: Si el archivo excede el tamano permitido, no es TOML valido o no cumple el
            esquema de ``dominio.valores_g_por_archivo``.

    Ejemplo:
        valores = leer_valores_g(Path("."))
    """
    datos = _leer_opciones(raiz)
    return {} if datos is None else dominio.valores_g_por_archivo(datos)


def leer_direcciones_de_funciones(raiz: Path) -> dict[str, int]:
    """
    Lee la direccion de cada funcion de ``config/symbols.txt``.

    Contexto:
        Usada por ``diff`` y ``probar`` para enlazar un candidato en la direccion de la funcion.

    Args:
        raiz (Path): Raiz del repositorio.

    Returns:
        dict[str, int]: Direccion por nombre; vacio si no existe el archivo.

    Raises:
        ValueError: Si el archivo excede el tamano permitido.

    Ejemplo:
        direcciones = leer_direcciones_de_funciones(Path("."))
    """
    ruta = raiz / SIMBOLOS_PROYECTO
    if not ruta.is_file():
        return {}
    if ruta.stat().st_size > MAX_BYTES_SIMBOLOS:
        raise ValueError(f"{SIMBOLOS_PROYECTO} excede el tamano permitido")
    return dominio.direcciones_de_funciones(ruta.read_text(encoding="utf-8"))


def leer_gp(raiz: Path) -> int | None:
    """
    Lee el valor de ``_gp`` de ``config/opciones_compilacion.toml``.

    Contexto:
        ``build`` lo usa para definir ``_gp`` en el enlace; sin el, un objeto compilado con
        datos pequenos que use ``$gp`` no resolveria sus referencias.

    Args:
        raiz (Path): Raiz del repositorio.

    Returns:
        int | None: Valor de ``_gp``, o ``None`` si no hay archivo o no lo declara.

    Raises:
        ValueError: Si el archivo es invalido (ver ``leer_valores_g``).

    Ejemplo:
        gp = leer_gp(Path("."))
    """
    datos = _leer_opciones(raiz)
    return None if datos is None else dominio.valor_gp(datos)


def leer_datos_pequenos(raiz: Path) -> dict[str, int]:
    """
    Lee los simbolos de datos pequenos de ``config/opciones_compilacion.toml``.

    Contexto:
        ``build`` los define en el enlace junto a ``_gp``; ``diff`` los toma despues del ELF.

    Args:
        raiz (Path): Raiz del repositorio.

    Returns:
        dict[str, int]: Direccion por simbolo; vacio si no hay archivo o tabla.

    Raises:
        ValueError: Si el archivo es invalido (ver ``leer_valores_g``).

    Ejemplo:
        simbolos = leer_datos_pequenos(Path("."))
    """
    datos = _leer_opciones(raiz)
    return {} if datos is None else dominio.datos_pequenos(datos)


def _leer_opciones(raiz: Path) -> object | None:
    """Carga ``config/opciones_compilacion.toml`` con cota de tamano; ``None`` si no existe."""
    ruta = raiz / OPCIONES_COMPILACION
    if not ruta.is_file():
        return None
    if ruta.stat().st_size > MAX_BYTES_REFERENCIA:
        raise ValueError(f"{OPCIONES_COMPILACION} excede el tamano permitido")
    try:
        return tomllib.loads(ruta.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        raise ValueError(f"{OPCIONES_COMPILACION} no es TOML valido") from None


def artefactos_de_build(nombre_ejecutable: str) -> tuple[str, ...]:
    """
    Lista las rutas dentro de ``build/`` que producen ``split`` y ``build``.

    Contexto:
        ``build/`` puede compartirse con otras herramientas del repositorio (imagenes de
        prueba, por ejemplo), asi que se borra solo lo que esta orden genera.

    Args:
        nombre_ejecutable (str): Nombre del ejecutable reconstruido (``SLUS_008.38``).

    Returns:
        tuple[str, ...]: Rutas relativas a la raiz del repositorio.

    Ejemplo:
        rutas = artefactos_de_build("SLUS_008.38")
    """
    return (
        OBJETOS_SALIDA,
        OBJETOS_C_SALIDA,
        CARPETA_DIFF,
        PROGRESO_JSON,
        SCRIPT_ENLAZADOR,
        SCRIPT_GP,
        *SIMBOLOS_AUTOMATICOS,
        SIMBOLOS_ENTRADA,
        ELF_SALIDA,
        MAPA_SALIDA,
        BINARIO_SALIDA,
        f"build/{nombre_ejecutable}",
    )


def limpiar(raiz: Path, nombre_ejecutable: str) -> list[str]:
    """
    Elimina lo generado: ``asm/``, ``expected/`` y los artefactos de ``build/``.

    Contexto:
        Implementa ``clean``: devuelve el repositorio al estado de recien clonado. ``build/``
        solo se elimina si queda vacia, y de ``asm/`` y ``expected/`` se conservan las
        subcarpetas de ``SUBCARPETAS_AJENAS``, para no destruir salidas de otras herramientas.

    Args:
        raiz (Path): Raiz del repositorio.
        nombre_ejecutable (str): Nombre del ejecutable reconstruido.

    Returns:
        list[str]: Rutas relativas que existian y se eliminaron.

    Ejemplo:
        eliminadas = limpiar(Path("."), "SLUS_008.38")
    """
    eliminadas: list[str] = []
    for nombre in ("asm", "expected"):
        eliminadas += _borrar_conservando_ajenos(raiz / nombre)
    eliminadas += [n for n in artefactos_de_build(nombre_ejecutable) if _borrar_arbol(raiz / n)]
    carpeta_build = raiz / "build"
    if carpeta_build.is_dir() and not any(carpeta_build.iterdir()):
        carpeta_build.rmdir()
        eliminadas.append("build")
    return eliminadas


def dividir(
    raiz: Path,
    original: Path,
    referencia: EjecutableReferencia,
    herramientas: Herramientas,
    ejecutar: Ejecutor = ejecutar_proceso,
) -> None:
    """
    Particiona el ejecutable original con splat generando ``asm/`` y el script del enlazador.

    Contexto:
        Implementa ``split``. Es idempotente: borra su salida anterior antes de generar, de
        modo que ejecutarlo dos veces produce el mismo resultado. El original se copia a
        ``expected/`` para que la configuracion de splat use una ruta relativa al repositorio.

    Args:
        raiz (Path): Raiz del repositorio.
        original (Path): Ejecutable original (solo lectura).
        referencia (EjecutableReferencia): Hechos esperados del ejecutable.
        herramientas (Herramientas): Interprete del particionador.
        ejecutar (Ejecutor, opcional): Ejecutor de procesos, sustituible en pruebas.

    Raises:
        ValueError: Si el SHA-256 del original no es el de la edicion soportada.
        ProcesoError: Si el particionador falla o no genera el script del enlazador.

    Ejemplo:
        dividir(Path("."), Path("disc/fs/SLUS_008.38"), referencia, herramientas)
    """
    if sha256_archivo(original) != referencia.sha256:
        raise ValueError("el ejecutable de origen no coincide con la edicion soportada (SHA-256 distinto)")
    # Solo se borra lo que esta orden produce: 'build/' puede contener salidas de otras
    # herramientas del repositorio.
    _borrar_conservando_ajenos(raiz / "asm")
    for nombre in artefactos_de_build(referencia.nombre):
        _borrar_arbol(raiz / nombre)
    expected = raiz / "expected"
    expected.mkdir(exist_ok=True)
    if original.resolve() != (expected / referencia.nombre).resolve():
        shutil.copyfile(original, expected / referencia.nombre)
    simbolos = raiz / SIMBOLOS_PROYECTO
    existentes = simbolos.read_text(encoding="utf-8") if simbolos.is_file() else ""
    entrada = raiz / SIMBOLOS_ENTRADA
    entrada.parent.mkdir(exist_ok=True)
    entrada.write_text(
        dominio.texto_simbolos_entrada(referencia.cabecera.pc0, existentes), encoding="utf-8", newline="\n"
    )
    ejecutar(dominio.comando_splat(herramientas.python, CONFIGURACION_SPLAT), raiz, TIMEOUT_SPLAT_S)
    if not (raiz / SCRIPT_ENLAZADOR).is_file():
        raise ProcesoError("splat no genero el script del enlazador")
    sanear_funciones_locales(raiz)


def sanear_funciones_locales(raiz: Path) -> list[str]:
    """
    Renombra a ``func_<direccion>`` las funciones que ``splat`` llamo ``.L<direccion>``.

    Contexto:
        Segunda parte de ``split``. Con una tabla de simbolos que no nombra el inicio de una funcion
        a la que otra salta con ``j``, ``splat`` la declara como etiqueta local: el ``.s`` se llama
        ``.L80044904.s`` y el esqueleto ``.c`` lleva ``INCLUDE_ASM(..., .L80044904)``, que no
        compila. Se cambia el nombre en el archivo, en las directivas, en los saltos que la
        referencian (en cualquier ``.s``) y en los esqueletos de ``src/``. Es idempotente.

    Args:
        raiz (Path): Raiz del repositorio.

    Returns:
        list[str]: Nombres originales que se renombraron (ordenados).

    Ejemplo:
        renombradas = sanear_funciones_locales(Path("."))
    """
    ensambladores = sorted((raiz / "asm").rglob("*.s"))
    nombres: set[str] = set()
    for ruta in ensambladores:
        nombres |= dominio.funciones_con_nombre_local(ruta.read_text(encoding="utf-8"))
    if not nombres:
        return []
    fijos = frozenset(nombres)
    fuentes = sorted((raiz / "src").glob("*.c")) if (raiz / "src").is_dir() else []
    for ruta in [*ensambladores, *fuentes]:
        texto = ruta.read_text(encoding="utf-8")
        nuevo = dominio.renombrar_funciones_locales(texto, fijos)
        if nuevo != texto:
            ruta.write_text(nuevo, encoding="utf-8", newline="\n")
    for ruta in ensambladores:
        if ruta.name[:-2] in fijos:
            ruta.rename(ruta.with_name(f"func_{ruta.name[2:]}"))
    return sorted(nombres)


def salidas_de_enlace(nombre_ejecutable: str) -> tuple[str, ...]:
    """
    Lista las rutas que produce el enlace y que representan el resultado de una construccion.

    Contexto:
        Son lo que ``verify`` y los consumidores del ejecutable (reempaquetado, emulador) leen.
        Se invalidan juntas antes de construir.

    Args:
        nombre_ejecutable (str): Nombre del ejecutable reconstruido (``SLUS_008.38``).

    Returns:
        tuple[str, ...]: Rutas relativas a la raiz del repositorio.

    Ejemplo:
        rutas = salidas_de_enlace("SLUS_008.38")
    """
    return (f"build/{nombre_ejecutable}", BINARIO_SALIDA, ELF_SALIDA, MAPA_SALIDA)


def invalidar_salida(raiz: Path, nombre_ejecutable: str) -> list[str]:
    """
    Elimina el ejecutable, el binario plano, el ELF y el mapa de una construccion anterior.

    Contexto:
        Una construccion que falla a mitad no debe dejar la salida de la anterior: ``verify``
        la aprobaria aunque ya no corresponda al codigo fuente. Si la construccion falla, no
        queda ningun ejecutable y ``verify`` informa que no existe.

    Args:
        raiz (Path): Raiz del repositorio.
        nombre_ejecutable (str): Nombre del ejecutable reconstruido.

    Returns:
        list[str]: Rutas relativas que existian y se eliminaron.

    Ejemplo:
        eliminadas = invalidar_salida(Path("."), "SLUS_008.38")
    """
    return [ruta for ruta in salidas_de_enlace(nombre_ejecutable) if _borrar_arbol(raiz / ruta)]


def construir(
    raiz: Path,
    referencia: EjecutableReferencia,
    herramientas: Herramientas,
    ejecutar: Ejecutor = ejecutar_proceso,
) -> Path:
    """
    Ensambla, enlaza y genera el ejecutable completo con su cabecera.

    Contexto:
        Implementa ``build`` cuando todo el codigo es ensamblador. Los objetos a ensamblar salen
        del script del enlazador, de modo que cualquier segmento que el particionador agregue
        entra solo en la construccion. Si el script incluye archivos C hay que usar
        ``construir_con_compilador``. El cuerpo enlazado debe medir exactamente ``t_size``; la
        cabecera se regenera.

    Args:
        raiz (Path): Raiz del repositorio.
        referencia (EjecutableReferencia): Hechos del ejecutable.
        herramientas (Herramientas): Ensamblador, enlazador y objcopy.
        ejecutar (Ejecutor, opcional): Ejecutor de procesos, sustituible en pruebas.

    Returns:
        Path: Ruta del ejecutable generado (``build/<nombre>``).

    Raises:
        FileNotFoundError: Si falta el script del enlazador o un fuente (hay que ejecutar ``split``).
        ValueError: Si el cuerpo enlazado no mide ``t_size`` o el script incluye archivos C.
        ProcesoError: Si una herramienta falla.

    Ejemplo:
        ejecutable = construir(Path("."), referencia, herramientas)
    """
    return construir_con_compilador(raiz, referencia, herramientas, None, ejecutar)


def construir_con_compilador(
    raiz: Path,
    referencia: EjecutableReferencia,
    herramientas: Herramientas,
    compilar_c: CompiladorC | None,
    ejecutar: Ejecutor = ejecutar_proceso,
) -> Path:
    """
    Ensambla o compila cada objeto del script, enlaza y genera el ejecutable con su cabecera.

    Contexto:
        Nucleo comun de ``construir`` (solo ensamblador) y de la construccion mixta C + asm.
        El orden de los objetos lo fija el script del enlazador, no esta funcion: asi el orden
        de enlace es identico al de la particion y el resultado no depende de como se compilen.

    Args:
        raiz (Path): Raiz del repositorio.
        referencia (EjecutableReferencia): Hechos del ejecutable.
        herramientas (Herramientas): Ensamblador, enlazador y objcopy.
        compilar_c (CompiladorC, opcional): Compila un ``src/*.c`` a su objeto; ``None`` si no
            se dispone de compilador.
        ejecutar (Ejecutor, opcional): Ejecutor de procesos, sustituible en pruebas.

    Returns:
        Path: Ruta del ejecutable generado (``build/<nombre>``).

    Raises:
        FileNotFoundError: Si falta el script del enlazador o un fuente (hay que ejecutar ``split``).
        ValueError: Si el script incluye C sin compilador o el cuerpo enlazado no mide ``t_size``.
        ProcesoError: Si una herramienta falla.

    Ejemplo:
        ejecutable = construir_con_compilador(Path("."), referencia, herramientas, compilar)
    """
    invalidar_salida(raiz, referencia.nombre)
    script = raiz / SCRIPT_ENLAZADOR
    if not script.is_file():
        raise FileNotFoundError("falta el script del enlazador: ejecute primero 'split'")
    for objeto in dominio.objetos_del_enlazador(script.read_text(encoding="utf-8")):
        fuente = dominio.fuente_de_objeto(objeto)
        if not (raiz / fuente).is_file():
            raise FileNotFoundError(f"falta el fuente '{fuente}': ejecute primero 'split'")
        (raiz / objeto).parent.mkdir(parents=True, exist_ok=True)
        if fuente.endswith(".c"):
            if compilar_c is None:
                raise ValueError(f"el fuente '{fuente}' es C y no hay compilador disponible")
            compilar_c(fuente, objeto)
            continue
        ejecutar(
            dominio.comando_ensamblar(herramientas.ensamblador, fuente, objeto, CARPETA_MACROS),
            raiz,
            TIMEOUT_ENSAMBLAR_S,
        )
    scripts = [SCRIPT_ENLAZADOR, *(s for s in SIMBOLOS_AUTOMATICOS if (raiz / s).is_file())]
    gp = leer_gp(raiz)
    if gp is not None:
        texto_gp = dominio.texto_gp_ld(gp, leer_datos_pequenos(raiz))
        (raiz / SCRIPT_GP).write_text(texto_gp, encoding="utf-8", newline="\n")
        scripts.append(SCRIPT_GP)
    ejecutar(
        dominio.comando_enlazar(herramientas.enlazador, scripts, ELF_SALIDA, MAPA_SALIDA),
        raiz,
        TIMEOUT_ENLAZAR_S,
    )
    ejecutar(
        dominio.comando_objcopy(herramientas.objcopy, ELF_SALIDA, BINARIO_SALIDA), raiz, TIMEOUT_ENSAMBLAR_S
    )
    ejecutable = dominio.ensamblar_ejecutable(referencia.cabecera, (raiz / BINARIO_SALIDA).read_bytes())
    destino = raiz / "build" / referencia.nombre
    destino.write_bytes(ejecutable)
    return destino


def verificar(raiz: Path, original: Path, referencia: EjecutableReferencia) -> tuple[bool, str]:
    """
    Compara el ejecutable reconstruido con el original.

    Contexto:
        Implementa ``verify``. La comparacion es por SHA-256; si falla, el mensaje agrega
        donde esta la primera diferencia para orientar la depuracion.

    Args:
        raiz (Path): Raiz del repositorio.
        original (Path): Ejecutable original.
        referencia (EjecutableReferencia): Hechos del ejecutable (nombre del archivo).

    Returns:
        tuple[bool, str]: Si coinciden y el mensaje a imprimir.

    Raises:
        FileNotFoundError: Si no existe el ejecutable reconstruido (hay que ejecutar ``build``).

    Ejemplo:
        coincide, mensaje = verificar(Path("."), Path("disc/fs/SLUS_008.38"), referencia)
    """
    construido = raiz / "build" / referencia.nombre
    if not construido.is_file():
        raise FileNotFoundError("no existe el ejecutable reconstruido: ejecute primero 'build'")
    esperado = sha256_archivo(original)
    if esperado != referencia.sha256:
        raise ValueError("el ejecutable original no coincide con la edicion soportada (SHA-256 distinto)")
    coincide, mensaje = dominio.resultado_verificacion(sha256_archivo(construido), esperado)
    if not coincide:
        mensaje += "\n" + dominio.describir_diferencia(construido.read_bytes(), original.read_bytes())
    return coincide, mensaje

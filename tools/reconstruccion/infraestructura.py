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
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.reconstruccion import dominio
from tools.reconstruccion.dominio import EjecutableReferencia
from tools.toolchain import iso9660
from tools.toolchain.dominio import Componente
from tools.toolchain.instalacion import resolver_herramienta

TIMEOUT_SPLAT_S = 900
TIMEOUT_ENSAMBLAR_S = 300
TIMEOUT_ENLAZAR_S = 600
MAX_BYTES_REFERENCIA = 64 * 1024
SCRIPT_ENLAZADOR = "build/SLUS_008.ld"
SIMBOLOS_AUTOMATICOS = ("build/undefined_funcs_auto.txt", "build/undefined_syms_auto.txt")
SIMBOLOS_ENTRADA = "build/simbolos_entrada.txt"
SIMBOLOS_PROYECTO = "config/symbols.txt"
CONFIGURACION_SPLAT = "config/splat.yaml"
CARPETA_MACROS = "asm/include"
ELF_SALIDA = "build/SLUS_008.elf"
MAPA_SALIDA = "build/SLUS_008.map"
BINARIO_SALIDA = "build/SLUS_008.bin"
OBJETOS_SALIDA = "build/asm"

Ejecutor = Callable[[Sequence[str], Path, int], str]
"""Funcion que ejecuta un comando en un directorio con tiempo limite y devuelve su salida."""


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
        SCRIPT_ENLAZADOR,
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
        solo se elimina si queda vacia, para no destruir salidas de otras herramientas.

    Args:
        raiz (Path): Raiz del repositorio.
        nombre_ejecutable (str): Nombre del ejecutable reconstruido.

    Returns:
        list[str]: Rutas relativas que existian y se eliminaron.

    Ejemplo:
        eliminadas = limpiar(Path("."), "SLUS_008.38")
    """
    candidatas = ("asm", "expected", *artefactos_de_build(nombre_ejecutable))
    eliminadas = [nombre for nombre in candidatas if _borrar_arbol(raiz / nombre)]
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
    for nombre in ("asm", *artefactos_de_build(referencia.nombre)):
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


def construir(
    raiz: Path,
    referencia: EjecutableReferencia,
    herramientas: Herramientas,
    ejecutar: Ejecutor = ejecutar_proceso,
) -> Path:
    """
    Ensambla, enlaza y genera el ejecutable completo con su cabecera.

    Contexto:
        Implementa ``build``. Los objetos a ensamblar salen del script del enlazador, de modo
        que cualquier segmento que el particionador agregue entra solo en la construccion.
        El cuerpo enlazado debe medir exactamente ``t_size``; la cabecera se regenera.

    Args:
        raiz (Path): Raiz del repositorio.
        referencia (EjecutableReferencia): Hechos del ejecutable.
        herramientas (Herramientas): Ensamblador, enlazador y objcopy.
        ejecutar (Ejecutor, opcional): Ejecutor de procesos, sustituible en pruebas.

    Returns:
        Path: Ruta del ejecutable generado (``build/<nombre>``).

    Raises:
        FileNotFoundError: Si falta el script del enlazador o un fuente (hay que ejecutar ``split``).
        ValueError: Si el cuerpo enlazado no mide ``t_size``.
        ProcesoError: Si una herramienta falla.

    Ejemplo:
        ejecutable = construir(Path("."), referencia, herramientas)
    """
    script = raiz / SCRIPT_ENLAZADOR
    if not script.is_file():
        raise FileNotFoundError("falta el script del enlazador: ejecute primero 'split'")
    for objeto in dominio.objetos_del_enlazador(script.read_text(encoding="utf-8")):
        fuente = dominio.fuente_de_objeto(objeto)
        if not (raiz / fuente).is_file():
            raise FileNotFoundError(f"falta el fuente '{fuente}': ejecute primero 'split'")
        (raiz / objeto).parent.mkdir(parents=True, exist_ok=True)
        ejecutar(
            dominio.comando_ensamblar(herramientas.ensamblador, fuente, objeto, CARPETA_MACROS),
            raiz,
            TIMEOUT_ENSAMBLAR_S,
        )
    scripts = [SCRIPT_ENLAZADOR, *(s for s in SIMBOLOS_AUTOMATICOS if (raiz / s).is_file())]
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

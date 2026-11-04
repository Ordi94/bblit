"""Acceso a disco y procesos de la reconstruccion: particionar, ensamblar, enlazar y verificar.

Toda ejecucion de herramientas externas recibe una lista de argumentos (nunca una cadena con
shell), un directorio de trabajo, un tiempo limite y se hace en primer plano. Las rutas del
disco pueden contener espacios y parentesis sin que eso afecte a ningun comando.

Nada de lo que depende del proyecto (nombre del ejecutable, carpetas, archivos de configuracion,
convenciones de simbolos) esta fijado aqui: llega por parametro explicito como ``Rutas``,
``Convenciones`` o el nombre del ejecutable, y no hay estado global. Las rutas de ``build/`` se
derivan con ``psxdecomp.construccion.salidas.calcular_salidas``.
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

from psxdecomp.construccion import dominio
from psxdecomp.construccion.dominio import EjecutableReferencia
from psxdecomp.construccion.salidas import calcular_salidas
from psxdecomp.diff.fuentes_c import MAX_BYTES_FUENTE
from psxdecomp.dominio import Convenciones, Rutas
from psxdecomp.entorno import SUFIJO_DISCO, SUFIJO_WINE, VARIABLES_PROPIAS, Variables
from psxdecomp.toolchain import iso9660, plataforma
from psxdecomp.toolchain.dominio import Componente
from psxdecomp.toolchain.instalacion import resolver_herramienta

TIMEOUT_SPLAT_S = 900
TIMEOUT_ENSAMBLAR_S = 300
TIMEOUT_ENLAZAR_S = 600
MAX_BYTES_REFERENCIA = 64 * 1024
MAX_BYTES_SIMBOLOS = 4 * 1024 * 1024

Ejecutor = Callable[[Sequence[str], Path, int], str]
"""Funcion que ejecuta un comando en un directorio con tiempo limite y devuelve su salida."""

CompiladorC = Callable[[str, str], None]
"""Funcion que compila un archivo C (ruta relativa) a un objeto (ruta relativa)."""


class ProcesoError(RuntimeError):
    """Una herramienta externa termino con error o excedio su tiempo limite."""


def _mensaje_ejecutable_ausente(herramienta: str, falta_wine: bool, variables: Variables) -> str:
    """
    Redacta el error de un ejecutable que el sistema no encuentra.

    Contexto:
        Lo usa ``ejecutar_proceso``. No incluye rutas de la maquina (ni el valor de la variable
        de Wine, solo su nombre) y es coherente con el aviso de binutils nativos ausentes.

    Args:
        herramienta (str): Nombre del programa que se queria lanzar.
        falta_wine (bool): ``True`` si el ejecutable ausente es Wine y no el programa.
        variables (Variables): Nombres de variable de entorno del proyecto.

    Returns:
        str: Mensaje que indica que falta y como resolverlo.

    Ejemplo:
        mensaje = _mensaje_ejecutable_ausente("CC1PSX.EXE", True, VARIABLES_PROPIAS)
    """
    if falta_wine:
        return (
            f"{herramienta}: Wine no esta instalado; instale wine y wine32 "
            f"o defina {variables.describir(SUFIJO_WINE)} con el ejecutable de Wine"
        )
    return f"{herramienta}: el ejecutable no esta instalado o no esta en el PATH"


def ejecutar_proceso(
    comando: Sequence[str],
    directorio: Path,
    timeout_s: int,
    *,
    variables: Variables = VARIABLES_PROPIAS,
) -> str:
    """
    Ejecuta un comando en primer plano, sin shell y con tiempo limite.

    Contexto:
        Unico punto por el que la reconstruccion lanza procesos; las pruebas lo sustituyen
        por un doble. Fuerza UTF-8 en el entorno porque la consola de Windows no lo usa por
        defecto y el particionador imprime texto no ASCII. Fuera de Windows antepone Wine a
        los ``.EXE`` del SDK (ver ``psxdecomp.toolchain.plataforma``).

    Args:
        comando (Sequence[str]): Ejecutable y argumentos como lista.
        directorio (Path): Directorio de trabajo.
        timeout_s (int): Segundos maximos de ejecucion.
        variables (Variables, opcional): Nombres de variable de entorno del proyecto, para
            localizar Wine; por omision solo el prefijo propio del kit.

    Returns:
        str: Salida estandar del proceso.

    Raises:
        ProcesoError: Si el codigo de salida no es cero, se excede el tiempo limite o el
            ejecutable (o Wine, para los ``.EXE`` fuera de Windows) no esta instalado; el
            mensaje nombra la herramienta y un extracto acotado de su salida de error.

    Ejemplo:
        salida = ejecutar_proceso(["python", "--version"], Path("."), 30)
    """
    herramienta = Path(comando[0]).name
    entorno = plataforma.entorno_proceso(os.environ)
    lanzado = plataforma.adaptar_comando(comando, entorno, variables=variables)
    try:
        resultado = subprocess.run(
            lanzado,
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
    except FileNotFoundError:
        raise ProcesoError(
            _mensaje_ejecutable_ausente(herramienta, lanzado[0] != comando[0], variables)
        ) from None
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
        huella = sha256_archivo(Path("build/EJEC_001.00"))
    """
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def leer_referencia(ruta: Path, *, etiqueta: str | None = None) -> EjecutableReferencia:
    """
    Lee y valida el archivo de referencia del ejecutable (``identidad.referencia`` del manifiesto).

    Contexto:
        Primer paso de todas las ordenes de construccion. Los mensajes nombran el archivo con
        ``etiqueta`` (la ruta relativa del manifiesto) y nunca con la ruta absoluta de la maquina.

    Args:
        ruta (Path): Ubicacion del archivo.
        etiqueta (str, opcional): Nombre con el que los mensajes de error citan el archivo; por
            omision, el nombre del archivo.

    Returns:
        EjecutableReferencia: Hechos del ejecutable validados.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si es demasiado grande, no es JSON o no cumple el esquema.

    Ejemplo:
        referencia = leer_referencia(Path("datos/ejecutable.json"), etiqueta="datos/ejecutable.json")
    """
    nombre = ruta.name if etiqueta is None else etiqueta
    if not ruta.is_file():
        raise FileNotFoundError(f"no se encontro {nombre}")
    if ruta.stat().st_size > MAX_BYTES_REFERENCIA:
        raise ValueError(f"{nombre} excede el tamano permitido")
    try:
        datos: Any = json.loads(ruta.read_text(encoding="utf-8"))
    except ValueError:
        raise ValueError(f"{nombre} no es JSON valido") from None
    return dominio.referencia_desde_datos(datos)


def localizar_imagen(disc: Path, *, variables: Variables = VARIABLES_PROPIAS) -> Path | None:
    """
    Busca la imagen de CD (``.bin``) a partir de lo que el usuario indico como disco.

    Contexto:
        La variable de entorno del disco puede apuntar al propio ``.bin``, a su ``.cue``, a la
        carpeta que contiene el ``.bin`` o a la carpeta superior que lo guarda en una subcarpeta.

    Args:
        disc (Path): Archivo o carpeta indicados.
        variables (Variables, opcional): Nombres de variable del proyecto, para citar la del disco
            en el mensaje de error.

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
            raise ValueError(f"{variables.describir(SUFIJO_DISCO)} debe ser una carpeta, un .bin o un .cue")
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
        extraer_de_imagen(Path("juego.bin"), referencia, Path("expected/EJEC_001.00"))
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


def obtener_original(
    raiz: Path,
    disc: Path | None,
    referencia: EjecutableReferencia,
    *,
    rutas: Rutas,
    variables: Variables = VARIABLES_PROPIAS,
) -> Path:
    """
    Obtiene la ruta del ejecutable original a partir de la configuracion del disco.

    Contexto:
        Si el disco ya tiene el sistema de archivos extraido (``fs/<nombre>``) se usa tal
        cual; si solo hay imagen de CD, el ejecutable se extrae a la carpeta ``expected`` del
        proyecto. Nunca se escribe en la carpeta del disco.

    Args:
        raiz (Path): Raiz del repositorio (donde vive la carpeta ``expected``).
        disc (Path, opcional): Valor de la variable de entorno del disco, ``--disc`` o el archivo
            local de rutas del proyecto.
        referencia (EjecutableReferencia): Datos del ejecutable.
        rutas (Rutas): Seccion ``[rutas]``: carpeta ``expected`` y archivo local de rutas.
        variables (Variables, opcional): Nombres de variable del proyecto, para citarlas en los
            mensajes de error.

    Returns:
        Path: Archivo con el ejecutable original.

    Raises:
        ValueError: Si no se configuro el disco, la imagen es ambigua o invalida.
        FileNotFoundError: Si no hay ni ``fs/<nombre>`` ni imagen.

    Ejemplo:
        original = obtener_original(Path("."), Path("disc"), referencia, rutas=rutas)
    """
    if disc is None:
        raise ValueError(
            f"falta la ubicacion del disco: defina {variables.describir(SUFIJO_DISCO)}, "
            f"--disc o 'disc' en {rutas.local}"
        )
    if not disc.exists():
        raise FileNotFoundError("la ubicacion del disco no existe")
    extraido = disc / "fs" / referencia.nombre
    if disc.is_dir() and extraido.is_file():
        return extraido
    imagen = localizar_imagen(disc, variables=variables)
    if imagen is None:
        raise FileNotFoundError(
            f"no se encontro fs/{referencia.nombre} ni una imagen .bin en la ubicacion del disco"
        )
    destino = raiz / rutas.expected / referencia.nombre
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


def _borrar_conservando_ajenos(ruta: Path, ajenas: Sequence[str]) -> list[str]:
    """
    Elimina una carpeta propia conservando las subcarpetas que pertenecen a otras herramientas.

    Contexto:
        La carpeta de ensamblador y la de ``expected`` las regenera esta herramienta, pero otras
        herramientas del repositorio guardan ahi sus propias subcarpetas (``rutas.subcarpetas_ajenas``);
        borrarlas rompe su trabajo en curso.

    Args:
        ruta (Path): Carpeta (o archivo) a eliminar.
        ajenas (Sequence[str]): Nombres de subcarpeta que se conservan.

    Returns:
        list[str]: Nombres eliminados relativos al padre de ``ruta``: la propia carpeta si no
        tenia contenido ajeno, o ``<carpeta>/<hijo>`` por cada hijo propio si lo tenia.

    Ejemplo:
        eliminados = _borrar_conservando_ajenos(Path("asm"), ("extra",))
    """
    if ruta.is_dir() and any((ruta / ajena).is_dir() for ajena in ajenas):
        propios = sorted(h for h in ruta.iterdir() if h.name not in ajenas)
        return [f"{ruta.name}/{h.name}" for h in propios if _borrar_arbol(h)]
    return [ruta.name] if _borrar_arbol(ruta) else []


def listar_fuentes_c(raiz: Path, *, rutas: Rutas) -> dict[str, str]:
    """
    Lee el texto de todos los archivos ``.c`` de la carpeta de fuentes.

    Contexto:
        Los estados de las funciones (progreso y diff) se derivan del texto real de estos
        archivos. Se leen con una cota de tamano porque su contenido lo edita una persona y no
        debe poder agotar la memoria de la herramienta.

    Args:
        raiz (Path): Raiz del repositorio.
        rutas (Rutas): Seccion ``[rutas]``; ``fuentes`` es la carpeta de los archivos C.

    Returns:
        dict[str, str]: Texto por ruta relativa (``<fuentes>/<archivo>.c``), ordenado por ruta;
        vacio si no existe la carpeta.

    Raises:
        ValueError: Si algun archivo excede ``MAX_BYTES_FUENTE``.

    Ejemplo:
        textos = listar_fuentes_c(Path("."), rutas=rutas)
    """
    carpeta = raiz / rutas.fuentes
    textos: dict[str, str] = {}
    if not carpeta.is_dir():
        return textos
    for ruta in sorted(carpeta.glob("*.c")):
        if ruta.stat().st_size > MAX_BYTES_FUENTE:
            raise ValueError(f"{rutas.fuentes}/{ruta.name} excede el tamano permitido")
        textos[f"{rutas.fuentes}/{ruta.name}"] = ruta.read_text(encoding="utf-8")
    return textos


def leer_secciones_declaradas(raiz: Path, *, rutas: Rutas) -> dict[str, frozenset[str]]:
    """
    Lee la configuracion del particionador y devuelve las secciones que cada archivo C puede generar.

    Contexto:
        La construccion compara cada objeto C contra lo que la particion le asigna; un
        repositorio sin esa configuracion (pruebas) no declara nada y cada objeto solo puede
        aportar codigo.

    Args:
        raiz (Path): Raiz del repositorio.
        rutas (Rutas): Seccion ``[rutas]``; ``splat`` es la configuracion del particionador.

    Returns:
        dict[str, frozenset[str]]: Ver ``dominio.secciones_declaradas``; vacio si no hay archivo.

    Raises:
        ValueError: Si el archivo no es YAML valido o no tiene la forma esperada.

    Ejemplo:
        declaradas = leer_secciones_declaradas(Path("."), rutas=rutas)
    """
    ruta = raiz / rutas.splat
    if not ruta.is_file():
        return {}
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ValueError(f"{rutas.splat} no es YAML valido") from None
    return dominio.secciones_declaradas(datos)


def leer_valores_g(raiz: Path, *, rutas: Rutas, convenciones: Convenciones) -> dict[str, int]:
    """
    Lee las opciones de compilacion del proyecto y devuelve el ``-G`` declarado por archivo C.

    Contexto:
        ``build`` y ``diff`` deben compilar cada archivo con las mismas opciones, asi que ambos
        las obtienen de aqui. Un repositorio sin el archivo compila todo con ``-G0``.

    Args:
        raiz (Path): Raiz del repositorio.
        rutas (Rutas): Seccion ``[rutas]``; ``opciones_compilacion`` es el archivo TOML.
        convenciones (Convenciones): Seccion ``[convenciones]`` (tope del umbral ``-G``).

    Returns:
        dict[str, int]: Valor de ``-G`` por nombre de archivo; vacio si no hay archivo.

    Raises:
        ValueError: Si el archivo excede el tamano permitido, no es TOML valido o no cumple el
            esquema de ``dominio.valores_g_por_archivo``.

    Ejemplo:
        valores = leer_valores_g(Path("."), rutas=rutas, convenciones=convenciones)
    """
    datos = _leer_opciones(raiz, rutas)
    return {} if datos is None else dominio.valores_g_por_archivo(datos, convenciones)


def _leer_simbolos(raiz: Path, rutas: Rutas) -> list[str]:
    """Lee, con cota de tamano, los archivos de simbolos que existen, en el orden del manifiesto."""
    textos: list[str] = []
    for relativa in rutas.simbolos:
        ruta = raiz / relativa
        if not ruta.is_file():
            continue
        if ruta.stat().st_size > MAX_BYTES_SIMBOLOS:
            raise ValueError(f"{relativa} excede el tamano permitido")
        textos.append(ruta.read_text(encoding="utf-8"))
    return textos


def leer_direcciones_de_funciones(raiz: Path, *, rutas: Rutas, convenciones: Convenciones) -> dict[str, int]:
    """
    Lee la direccion de cada funcion de los archivos de simbolos del proyecto.

    Contexto:
        Usada por ``diff`` y ``probar`` para enlazar un candidato en la direccion de la funcion.
        Si varios archivos declaran el mismo nombre, manda el ultimo en el orden del manifiesto.

    Args:
        raiz (Path): Raiz del repositorio.
        rutas (Rutas): Seccion ``[rutas]``; ``simbolos`` lista los archivos.
        convenciones (Convenciones): Seccion ``[convenciones]`` (formato de las lineas).

    Returns:
        dict[str, int]: Direccion por nombre; vacio si no existe ningun archivo.

    Raises:
        ValueError: Si algun archivo excede el tamano permitido.

    Ejemplo:
        direcciones = leer_direcciones_de_funciones(Path("."), rutas=rutas, convenciones=convenciones)
    """
    direcciones: dict[str, int] = {}
    for texto in _leer_simbolos(raiz, rutas):
        direcciones.update(dominio.direcciones_de_funciones(texto, convenciones))
    return direcciones


def leer_gp(raiz: Path, *, rutas: Rutas) -> int | None:
    """
    Lee el valor de ``_gp`` de las opciones de compilacion del proyecto.

    Contexto:
        ``build`` lo usa para definir ``_gp`` en el enlace; sin el, un objeto compilado con
        datos pequenos que use ``$gp`` no resolveria sus referencias.

    Args:
        raiz (Path): Raiz del repositorio.
        rutas (Rutas): Seccion ``[rutas]``; ``opciones_compilacion`` es el archivo TOML.

    Returns:
        int | None: Valor de ``_gp``, o ``None`` si no hay archivo o no lo declara.

    Raises:
        ValueError: Si el archivo es invalido (ver ``leer_valores_g``).

    Ejemplo:
        gp = leer_gp(Path("."), rutas=rutas)
    """
    datos = _leer_opciones(raiz, rutas)
    return None if datos is None else dominio.valor_gp(datos)


def leer_datos_pequenos(raiz: Path, *, rutas: Rutas, convenciones: Convenciones) -> dict[str, int]:
    """
    Lee los simbolos de datos pequenos de las opciones de compilacion del proyecto.

    Contexto:
        ``build`` los define en el enlace junto a ``_gp``; ``diff`` los toma despues del ELF.

    Args:
        raiz (Path): Raiz del repositorio.
        rutas (Rutas): Seccion ``[rutas]``; ``opciones_compilacion`` es el archivo TOML.
        convenciones (Convenciones): Seccion ``[convenciones]`` (nombre de los simbolos de datos).

    Returns:
        dict[str, int]: Direccion por simbolo; vacio si no hay archivo o tabla.

    Raises:
        ValueError: Si el archivo es invalido (ver ``leer_valores_g``).

    Ejemplo:
        simbolos = leer_datos_pequenos(Path("."), rutas=rutas, convenciones=convenciones)
    """
    datos = _leer_opciones(raiz, rutas)
    return {} if datos is None else dominio.datos_pequenos(datos, convenciones)


def verificar_configuracion(raiz: Path, *, rutas: Rutas, convenciones: Convenciones) -> list[str]:
    """
    Compara ``[datos_pequenos]`` de las opciones de compilacion con los archivos de simbolos.

    Contexto:
        Implementa ``verificar-config`` (que trata cada resultado como error) y el aviso que ``split``
        imprime al terminar sin tumbarse. Solo lee: no modifica ningun archivo ni cambia lo que
        construyen ``build`` o ``verify``.

    Args:
        raiz (Path): Raiz del repositorio.
        rutas (Rutas): Seccion ``[rutas]``; ``simbolos`` y ``opciones_compilacion``.
        convenciones (Convenciones): Seccion ``[convenciones]`` (formato de simbolos).

    Returns:
        list[str]: Hallazgos de ``dominio.avisos_datos_pequenos``; vacia si no hay tabla o no hay
        direcciones repetidas.

    Raises:
        FileNotFoundError: Si falta algun archivo de simbolos declarado.
        ValueError: Si algun archivo excede el tamano permitido o las opciones no son validas (por
            ejemplo, el toml repite una clave).

    Ejemplo:
        avisos = verificar_configuracion(Path("."), rutas=rutas, convenciones=convenciones)
    """
    for relativa in rutas.simbolos:
        if not (raiz / relativa).is_file():
            raise FileNotFoundError(f"falta {relativa}")
    declarados = dominio.simbolos_declarados("\n".join(_leer_simbolos(raiz, rutas)), convenciones)
    return dominio.avisos_datos_pequenos(
        leer_datos_pequenos(raiz, rutas=rutas, convenciones=convenciones),
        declarados,
        ", ".join(rutas.simbolos),
    )


def _leer_opciones(raiz: Path, rutas: Rutas) -> object | None:
    """Carga el archivo de opciones de compilacion con cota de tamano; ``None`` si no existe."""
    ruta = raiz / rutas.opciones_compilacion
    if not ruta.is_file():
        return None
    if ruta.stat().st_size > MAX_BYTES_REFERENCIA:
        raise ValueError(f"{rutas.opciones_compilacion} excede el tamano permitido")
    try:
        return tomllib.loads(ruta.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        raise ValueError(f"{rutas.opciones_compilacion} no es TOML valido") from None


def artefactos_de_build(nombre_ejecutable: str, *, rutas: Rutas) -> tuple[str, ...]:
    """
    Lista las rutas dentro de la carpeta de build que producen ``split`` y ``build``.

    Contexto:
        La carpeta de build puede compartirse con otras herramientas del repositorio (imagenes de
        prueba, por ejemplo), asi que se borra solo lo que esta orden genera.

    Args:
        nombre_ejecutable (str): Nombre del ejecutable reconstruido (``identidad.ejecutable``).
        rutas (Rutas): Seccion ``[rutas]`` del manifiesto.

    Returns:
        tuple[str, ...]: Rutas relativas a la raiz del repositorio.

    Ejemplo:
        artefactos = artefactos_de_build("EJEC_001.00", rutas=rutas)
    """
    salidas = calcular_salidas(nombre_ejecutable, rutas)
    return (
        salidas.objetos_asm,
        salidas.objetos_c,
        salidas.diff,
        salidas.permutar,
        salidas.progreso_json,
        salidas.script_enlazador,
        salidas.script_gp,
        *salidas.simbolos_automaticos,
        salidas.simbolos_entrada,
        salidas.elf,
        salidas.mapa,
        salidas.binario,
        salidas.ejecutable,
    )


def limpiar(raiz: Path, nombre_ejecutable: str, *, rutas: Rutas) -> list[str]:
    """
    Elimina lo generado: el ensamblador del particionador, ``expected`` y los artefactos de build.

    Contexto:
        Implementa ``clean``: devuelve el repositorio al estado de recien clonado. La carpeta de
        build solo se elimina si queda vacia, y del ensamblador y de ``expected`` se conservan las
        subcarpetas de ``rutas.subcarpetas_ajenas``, para no destruir salidas de otras herramientas.

    Args:
        raiz (Path): Raiz del repositorio.
        nombre_ejecutable (str): Nombre del ejecutable reconstruido.
        rutas (Rutas): Seccion ``[rutas]`` del manifiesto.

    Returns:
        list[str]: Rutas relativas que existian y se eliminaron.

    Ejemplo:
        eliminadas = limpiar(Path("."), "EJEC_001.00", rutas=rutas)
    """
    eliminadas: list[str] = []
    for nombre in (rutas.asm, rutas.expected):
        eliminadas += _borrar_conservando_ajenos(raiz / nombre, rutas.subcarpetas_ajenas)
    eliminadas += [n for n in artefactos_de_build(nombre_ejecutable, rutas=rutas) if _borrar_arbol(raiz / n)]
    carpeta_build = raiz / rutas.build
    if carpeta_build.is_dir() and not any(carpeta_build.iterdir()):
        carpeta_build.rmdir()
        eliminadas.append(rutas.build)
    return eliminadas


def dividir(
    raiz: Path,
    original: Path,
    referencia: EjecutableReferencia,
    herramientas: Herramientas,
    ejecutar: Ejecutor = ejecutar_proceso,
    *,
    rutas: Rutas,
    convenciones: Convenciones,
) -> None:
    """
    Particiona el ejecutable original con splat generando el ensamblador y el script del enlazador.

    Contexto:
        Implementa ``split``. Es idempotente: borra su salida anterior antes de generar, de
        modo que ejecutarlo dos veces produce el mismo resultado. El original se copia a la
        carpeta ``expected`` para que la configuracion de splat use una ruta relativa al repositorio.

    Args:
        raiz (Path): Raiz del repositorio.
        original (Path): Ejecutable original (solo lectura).
        referencia (EjecutableReferencia): Hechos esperados del ejecutable.
        herramientas (Herramientas): Interprete del particionador.
        ejecutar (Ejecutor, opcional): Ejecutor de procesos, sustituible en pruebas.
        rutas (Rutas): Seccion ``[rutas]`` del manifiesto.
        convenciones (Convenciones): Seccion ``[convenciones]`` (formato del archivo de simbolos).

    Raises:
        ValueError: Si el SHA-256 del original no es el de la edicion soportada.
        ProcesoError: Si el particionador falla o no genera el script del enlazador.

    Ejemplo:
        dividir(Path("."), Path("disc/fs/EJEC_001.00"), referencia, herramientas, rutas=rutas,
                convenciones=convenciones)
    """
    if sha256_archivo(original) != referencia.sha256:
        raise ValueError("el ejecutable de origen no coincide con la edicion soportada (SHA-256 distinto)")
    salidas = calcular_salidas(referencia.nombre, rutas)
    # Solo se borra lo que esta orden produce: la carpeta de build puede contener salidas de otras
    # herramientas del repositorio.
    _borrar_conservando_ajenos(raiz / rutas.asm, rutas.subcarpetas_ajenas)
    for nombre in artefactos_de_build(referencia.nombre, rutas=rutas):
        _borrar_arbol(raiz / nombre)
    expected = raiz / rutas.expected
    expected.mkdir(exist_ok=True)
    if original.resolve() != (expected / referencia.nombre).resolve():
        shutil.copyfile(original, expected / referencia.nombre)
    existentes = "\n".join(_leer_simbolos(raiz, rutas))
    entrada = raiz / salidas.simbolos_entrada
    entrada.parent.mkdir(exist_ok=True)
    entrada.write_text(
        dominio.texto_simbolos_entrada(referencia.cabecera.pc0, existentes), encoding="utf-8", newline="\n"
    )
    ejecutar(dominio.comando_splat(herramientas.python, rutas.splat), raiz, TIMEOUT_SPLAT_S)
    if not (raiz / salidas.script_enlazador).is_file():
        raise ProcesoError("splat no genero el script del enlazador")
    sanear_funciones_locales(raiz, rutas=rutas)


def sanear_funciones_locales(raiz: Path, *, rutas: Rutas) -> list[str]:
    """
    Renombra a ``func_<direccion>`` las funciones que ``splat`` llamo ``.L<direccion>``.

    Contexto:
        Segunda parte de ``split``. Con una tabla de simbolos que no nombra el inicio de una funcion
        a la que otra salta con ``j``, ``splat`` la declara como etiqueta local: el ``.s`` se llama
        ``.L<direccion>.s`` y el esqueleto ``.c`` lleva una macro de inclusion con ese nombre, que no
        compila. Se cambia el nombre en el archivo, en las directivas, en los saltos que la
        referencian (en cualquier ``.s``) y en los esqueletos de la carpeta de fuentes. Es idempotente.

    Args:
        raiz (Path): Raiz del repositorio.
        rutas (Rutas): Seccion ``[rutas]``; ``asm`` y ``fuentes``.

    Returns:
        list[str]: Nombres originales que se renombraron (ordenados).

    Ejemplo:
        renombradas = sanear_funciones_locales(Path("."), rutas=rutas)
    """
    ensambladores = sorted((raiz / rutas.asm).rglob("*.s"))
    nombres: set[str] = set()
    for ruta in ensambladores:
        nombres |= dominio.funciones_con_nombre_local(ruta.read_text(encoding="utf-8"))
    if not nombres:
        return []
    fijos = frozenset(nombres)
    carpeta_fuentes = raiz / rutas.fuentes
    fuentes = sorted(carpeta_fuentes.glob("*.c")) if carpeta_fuentes.is_dir() else []
    for ruta in [*ensambladores, *fuentes]:
        texto = ruta.read_text(encoding="utf-8")
        nuevo = dominio.renombrar_funciones_locales(texto, fijos)
        if nuevo != texto:
            ruta.write_text(nuevo, encoding="utf-8", newline="\n")
    for ruta in ensambladores:
        if ruta.name[:-2] in fijos:
            ruta.rename(ruta.with_name(f"func_{ruta.name[2:]}"))
    return sorted(nombres)


def salidas_de_enlace(nombre_ejecutable: str, *, rutas: Rutas) -> tuple[str, ...]:
    """
    Lista las rutas que produce el enlace y que representan el resultado de una construccion.

    Contexto:
        Son lo que ``verify`` y los consumidores del ejecutable (reempaquetado, emulador) leen.
        Se invalidan juntas antes de construir.

    Args:
        nombre_ejecutable (str): Nombre del ejecutable reconstruido (``identidad.ejecutable``).
        rutas (Rutas): Seccion ``[rutas]`` del manifiesto.

    Returns:
        tuple[str, ...]: Rutas relativas a la raiz del repositorio.

    Ejemplo:
        salidas = salidas_de_enlace("EJEC_001.00", rutas=rutas)
    """
    salidas = calcular_salidas(nombre_ejecutable, rutas)
    return (salidas.ejecutable, salidas.binario, salidas.elf, salidas.mapa)


def invalidar_salida(raiz: Path, nombre_ejecutable: str, *, rutas: Rutas) -> list[str]:
    """
    Elimina el ejecutable, el binario plano, el ELF y el mapa de una construccion anterior.

    Contexto:
        Una construccion que falla a mitad no debe dejar la salida de la anterior: ``verify``
        la aprobaria aunque ya no corresponda al codigo fuente. Si la construccion falla, no
        queda ningun ejecutable y ``verify`` informa que no existe.

    Args:
        raiz (Path): Raiz del repositorio.
        nombre_ejecutable (str): Nombre del ejecutable reconstruido.
        rutas (Rutas): Seccion ``[rutas]`` del manifiesto.

    Returns:
        list[str]: Rutas relativas que existian y se eliminaron.

    Ejemplo:
        eliminadas = invalidar_salida(Path("."), "EJEC_001.00", rutas=rutas)
    """
    return [ruta for ruta in salidas_de_enlace(nombre_ejecutable, rutas=rutas) if _borrar_arbol(raiz / ruta)]


def construir(
    raiz: Path,
    referencia: EjecutableReferencia,
    herramientas: Herramientas,
    ejecutar: Ejecutor = ejecutar_proceso,
    *,
    rutas: Rutas,
    convenciones: Convenciones,
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
        rutas (Rutas): Seccion ``[rutas]`` del manifiesto.
        convenciones (Convenciones): Seccion ``[convenciones]`` (formato de simbolos).

    Returns:
        Path: Ruta del ejecutable generado (``<build>/<nombre>``).

    Raises:
        FileNotFoundError: Si falta el script del enlazador o un fuente (hay que ejecutar ``split``).
        ValueError: Si el cuerpo enlazado no mide ``t_size`` o el script incluye archivos C.
        ProcesoError: Si una herramienta falla.

    Ejemplo:
        ejecutable = construir(Path("."), referencia, herramientas, rutas=rutas, convenciones=convenciones)
    """
    return construir_con_compilador(
        raiz, referencia, herramientas, None, ejecutar, rutas=rutas, convenciones=convenciones
    )


def construir_con_compilador(
    raiz: Path,
    referencia: EjecutableReferencia,
    herramientas: Herramientas,
    compilar_c: CompiladorC | None,
    ejecutar: Ejecutor = ejecutar_proceso,
    *,
    rutas: Rutas,
    convenciones: Convenciones,
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
        compilar_c (CompiladorC, opcional): Compila un fuente C a su objeto; ``None`` si no
            se dispone de compilador.
        ejecutar (Ejecutor, opcional): Ejecutor de procesos, sustituible en pruebas.
        rutas (Rutas): Seccion ``[rutas]`` del manifiesto.
        convenciones (Convenciones): Seccion ``[convenciones]`` (formato de simbolos).

    Returns:
        Path: Ruta del ejecutable generado (``<build>/<nombre>``).

    Raises:
        FileNotFoundError: Si falta el script del enlazador o un fuente (hay que ejecutar ``split``).
        ValueError: Si el script incluye C sin compilador o el cuerpo enlazado no mide ``t_size``.
        ProcesoError: Si una herramienta falla.

    Ejemplo:
        ejecutable = construir_con_compilador(
            Path("."), referencia, herramientas, compilar, rutas=rutas, convenciones=convenciones
        )
    """
    invalidar_salida(raiz, referencia.nombre, rutas=rutas)
    salidas = calcular_salidas(referencia.nombre, rutas)
    script = raiz / salidas.script_enlazador
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
            dominio.comando_ensamblar(herramientas.ensamblador, fuente, objeto, rutas.macros),
            raiz,
            TIMEOUT_ENSAMBLAR_S,
        )
    scripts = [salidas.script_enlazador, *(s for s in salidas.simbolos_automaticos if (raiz / s).is_file())]
    gp = leer_gp(raiz, rutas=rutas)
    if gp is not None:
        texto_gp = dominio.texto_gp_ld(gp, leer_datos_pequenos(raiz, rutas=rutas, convenciones=convenciones))
        (raiz / salidas.script_gp).write_text(texto_gp, encoding="utf-8", newline="\n")
        scripts.append(salidas.script_gp)
    ejecutar(
        dominio.comando_enlazar(herramientas.enlazador, scripts, salidas.elf, salidas.mapa),
        raiz,
        TIMEOUT_ENLAZAR_S,
    )
    ejecutar(
        dominio.comando_objcopy(herramientas.objcopy, salidas.elf, salidas.binario),
        raiz,
        TIMEOUT_ENSAMBLAR_S,
    )
    ejecutable = dominio.ensamblar_ejecutable(referencia.cabecera, (raiz / salidas.binario).read_bytes())
    destino = raiz / salidas.ejecutable
    destino.write_bytes(ejecutable)
    return destino


def verificar(
    raiz: Path, original: Path, referencia: EjecutableReferencia, *, rutas: Rutas
) -> tuple[bool, str]:
    """
    Compara el ejecutable reconstruido con el original.

    Contexto:
        Implementa ``verify``. La comparacion es por SHA-256; si falla, el mensaje agrega
        donde esta la primera diferencia para orientar la depuracion.

    Args:
        raiz (Path): Raiz del repositorio.
        original (Path): Ejecutable original.
        referencia (EjecutableReferencia): Hechos del ejecutable (nombre del archivo).
        rutas (Rutas): Seccion ``[rutas]`` del manifiesto.

    Returns:
        tuple[bool, str]: Si coinciden y el mensaje a imprimir.

    Raises:
        FileNotFoundError: Si no existe el ejecutable reconstruido (hay que ejecutar ``build``).

    Ejemplo:
        coincide, mensaje = verificar(Path("."), Path("disc/fs/EJEC_001.00"), referencia, rutas=rutas)
    """
    construido = raiz / calcular_salidas(referencia.nombre, rutas).ejecutable
    if not construido.is_file():
        raise FileNotFoundError("no existe el ejecutable reconstruido: ejecute primero 'build'")
    esperado = sha256_archivo(original)
    if esperado != referencia.sha256:
        raise ValueError("el ejecutable original no coincide con la edicion soportada (SHA-256 distinto)")
    coincide, mensaje = dominio.resultado_verificacion(sha256_archivo(construido), esperado)
    if not coincide:
        mensaje += "\n" + dominio.describir_diferencia(construido.read_bytes(), original.read_bytes())
    return coincide, mensaje

"""Invocacion de ``analyzeHeadless`` de Ghidra y verificacion de su salida.

Ghidra es un proceso externo pesado: aqui solo se construyen sus argumentos, se lanza en primer
plano con limite de tiempo y se interpreta el registro que imprimen los scripts propios. La
ejecucion real se inyecta como dependencia para poder probar el resto sin Ghidra instalado.
"""

import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from tools.ghidra.dominio import DIRECCION_BASE, DIRECCION_ENTRADA
from tools.reconstruccion.infraestructura import leer_referencia, obtener_original

VARIABLE_GHIDRA: Final[str] = "BBLIT_GHIDRA"
"""Variable de entorno con la carpeta de instalacion de Ghidra."""

VARIABLE_DISCO: Final[str] = "BBLIT_DISC"
"""Variable de entorno con la carpeta del disco extraido."""

RAIZ_REPOSITORIO: Final[Path] = Path(__file__).resolve().parents[2]
"""Raiz del repositorio: ahi viven ``config/ejecutable.json`` y ``expected/``."""

NOMBRE_EJECUTABLE: Final[str] = "SLUS_008.38"
NOMBRE_PROYECTO: Final[str] = "bblit"
CARGADOR_PSX: Final[str] = "PsxLoader"
"""Clase del cargador PS-X EXE de la extension; ``-loader`` la identifica por su nombre de clase."""

VERSIONES_FIRMAS: Final[tuple[str, ...]] = ("4.6.0", "4.0.0", "4.7.0", "4.4.0")
"""Versiones del SDK cuyas firmas se aplican ademas de la que detecta el cargador.

El ejecutable enlaza librerias de epocas distintas: libetc coincide con el SDK 4.0 y libcd,
libgs y libgte con el 4.6, mientras el cargador solo detecta una version.
"""

SIN_VALOR: Final[str] = "ninguno"
"""Marcador de argumento ausente para los scripts: un guion solo lo tomaria Ghidra por una opcion."""

SEGUNDOS_MAXIMOS: Final[int] = 600
"""Tope por invocacion; el analisis completo tarda unos minutos."""

_CARACTERES_PROHIBIDOS: Final[re.Pattern[str]] = re.compile(r'[&|^%"<>\r\n]')
_PATRON_MARCA: Final[re.Pattern[str]] = re.compile(r"BBLIT (?P<clave>base|entrada)=0x(?P<valor>[0-9A-Fa-f]+)")
_PATRON_CARGADOR: Final[re.Pattern[str]] = re.compile(r"Using Loader: PSX Executables Loader")


@dataclass(frozen=True, slots=True)
class ResultadoEjecucion:
    """Resultado de un proceso externo.

    Contexto:
        Lo devuelve el ejecutor inyectado; ``verificar_carga`` interpreta ``salida``.

    Attributes:
        codigo (int): Codigo de salida del proceso.
        salida (str): Salida estandar y de error combinadas.
    """

    codigo: int
    salida: str


Ejecutor = Callable[[Sequence[str], int], ResultadoEjecucion]


@dataclass(frozen=True, slots=True)
class ConfiguracionGhidra:
    """Rutas necesarias para lanzar ``analyzeHeadless``.

    Contexto:
        La construye la CLI a partir de argumentos y variables de entorno.

    Attributes:
        instalacion (Path): Carpeta de instalacion de Ghidra.
        proyecto (Path): Carpeta donde vive el proyecto de Ghidra.
        scripts (Path): Carpeta con los scripts Java del paquete.
        nombre_proyecto (str): Nombre del proyecto dentro de la carpeta.
    """

    instalacion: Path
    proyecto: Path
    scripts: Path
    nombre_proyecto: str = NOMBRE_PROYECTO

    @property
    def lanzador(self) -> Path:
        """Ruta del script ``analyzeHeadless`` propio de la plataforma."""
        extension = ".bat" if sys.platform == "win32" else ""
        return self.instalacion / "support" / f"analyzeHeadless{extension}"


@dataclass(frozen=True, slots=True)
class Carga:
    """Datos de carga que los scripts imprimen tras importar.

    Contexto:
        Lo devuelve ``verificar_carga`` para dejar constancia de la base y la entrada.

    Attributes:
        base (int): Direccion de inicio del bloque de codigo.
        entrada (int): Punto de entrada del programa.
    """

    base: int
    entrada: int


def resolver_instalacion(argumento: Path | None, entorno: Mapping[str, str]) -> Path:
    """
    Determina la carpeta de Ghidra a partir del argumento o de ``BBLIT_GHIDRA``.

    Contexto:
        Evita rutas absolutas dentro del repositorio: la ubicacion es siempre del equipo.

    Args:
        argumento (Path | None): Valor de ``--ghidra`` si se dio.
        entorno (Mapping[str, str]): Variables de entorno.

    Returns:
        Path: Carpeta de instalacion que contiene ``support``.

    Raises:
        ValueError: Si no se indica ninguna ruta o la carpeta no tiene ``support``.

    Ejemplo:
        instalacion = resolver_instalacion(None, os.environ)
    """
    if argumento is None:
        valor = entorno.get(VARIABLE_GHIDRA)
        if not valor:
            raise ValueError(f"indique --ghidra o defina la variable {VARIABLE_GHIDRA}")
        argumento = Path(valor)
    if not (argumento / "support").is_dir():
        raise ValueError("la carpeta de Ghidra no contiene el subdirectorio support")
    return argumento


def resolver_ejecutable(
    argumento: Path | None, entorno: Mapping[str, str], raiz: Path = RAIZ_REPOSITORIO
) -> Path:
    """
    Determina el ejecutable del juego a partir del argumento o de ``BBLIT_DISC``.

    Contexto:
        Primer paso de ``analizar`` y ``simbolos``. La variable ``BBLIT_DISC`` tiene el mismo
        contrato que en el resto de herramientas (se delega en ``tools.reconstruccion``): carpeta
        con ``fs/SLUS_008.38``, imagen ``.bin``, ``.cue``, carpeta del ``.bin`` o carpeta
        superior. Con una imagen, el ejecutable se extrae a ``expected/`` bajo ``raiz``.

    Args:
        argumento (Path | None): Valor de ``--exe`` si se dio.
        entorno (Mapping[str, str]): Variables de entorno.
        raiz (Path, opcional): Raiz del repositorio (con ``config/ejecutable.json``).

    Returns:
        Path: Ruta del ejecutable existente.

    Raises:
        ValueError: Si no se indica ninguna ruta, la ruta del disco no existe, no contiene el
            ejecutable ni una imagen, o la imagen es ambigua o invalida.

    Ejemplo:
        exe = resolver_ejecutable(None, os.environ)
    """
    if argumento is None:
        carpeta = entorno.get(VARIABLE_DISCO)
        if not carpeta:
            raise ValueError(f"indique --exe o defina la variable {VARIABLE_DISCO}")
        try:
            referencia = leer_referencia(raiz / "config" / "ejecutable.json")
            return obtener_original(raiz, Path(carpeta), referencia)
        except FileNotFoundError as error:
            raise ValueError(f"{VARIABLE_DISCO}: {error}") from None
    if not argumento.is_file():
        raise ValueError(f"el ejecutable {argumento.name} no existe")
    return argumento


def _validar_argumento(valor: str, campo: str) -> str:
    """Rechaza caracteres que el interprete de comandos de Windows reinterpretaria."""
    if _CARACTERES_PROHIBIDOS.search(valor):
        raise ValueError(f"{campo} contiene caracteres no permitidos")
    return valor


def _base_comando(config: ConfiguracionGhidra, segundos: int) -> list[str]:
    """Argumentos comunes: proyecto, scripts y limite de analisis por archivo."""
    if not 1 <= segundos <= SEGUNDOS_MAXIMOS:
        raise ValueError(f"segundos={segundos} fuera de rango 1..{SEGUNDOS_MAXIMOS}")
    return [
        str(config.lanzador),
        _validar_argumento(str(config.proyecto), "proyecto"),
        _validar_argumento(config.nombre_proyecto, "nombre_proyecto"),
    ]


def construir_comando_analisis(
    config: ConfiguracionGhidra,
    ejecutable: Path,
    semilla: Path | None,
    versiones: Sequence[str],
    segundos: int,
) -> list[str]:
    """
    Arma la linea de comandos que importa, siembra, analiza y aplica firmas.

    Contexto:
        Comando ``analizar``. El cargador PSX se pide por nombre para no caer en el cargador
        generico; ``-overwrite`` reemplaza el programa de una corrida previa y vuelve idempotente
        el proceso; el script previo siembra funciones antes del analisis; despues se buscan las
        funciones alcanzables solo por tablas de punteros y se aplican las firmas de las
        versiones adicionales del SDK.

    Args:
        config (ConfiguracionGhidra): Rutas de Ghidra, proyecto y scripts.
        ejecutable (Path): Ejecutable PS-X a importar.
        semilla (Path | None): Archivo con direcciones de funciones conocidas, o ``None``.
        versiones (Sequence[str]): Versiones del SDK para las pasadas de firmas adicionales.
        segundos (int): Limite de Ghidra para el analisis del archivo.

    Returns:
        list[str]: Argumentos listos para ``subprocess``.

    Raises:
        ValueError: Si un argumento contiene caracteres que el interprete reinterpretaria, una
            version no tiene la forma ``N.N.N`` o ``segundos`` esta fuera de rango.

    Ejemplo:
        comando = construir_comando_analisis(config, exe, None, VERSIONES_FIRMAS, 540)
    """
    for version in versiones:
        if re.fullmatch(r"[0-9]+(\.[0-9]+){1,2}", version) is None:
            raise ValueError(f"version de firmas invalida: {version!r}")
    comando = _base_comando(config, segundos)
    comando += ["-import", _validar_argumento(str(ejecutable), "ejecutable"), "-overwrite"]
    comando += ["-loader", CARGADOR_PSX, "-analysisTimeoutPerFile", str(segundos)]
    comando += ["-scriptPath", _validar_argumento(str(config.scripts), "scripts")]
    comando += ["-preScript", "PrepararAnalisis.java"]
    comando += [_validar_argumento(str(semilla), "semilla") if semilla else SIN_VALOR]
    comando += ["-postScript", "DescubrirFunciones.java"]
    if versiones:
        comando += ["-postScript", "AplicarFirmas.java", *versiones]
    return comando


def construir_comando_exportacion(
    config: ConfiguracionGhidra,
    programa: str,
    salida: Path,
    *,
    decompilar: bool,
    segundos_por_funcion: int,
) -> list[str]:
    """
    Arma la linea de comandos que exporta un programa ya analizado.

    Contexto:
        Comando ``exportar``. Se abre el proyecto en solo lectura y sin re-analizar: la
        exportacion no debe alterar el resultado del analisis.

    Args:
        config (ConfiguracionGhidra): Rutas de Ghidra, proyecto y scripts.
        programa (str): Nombre del programa dentro del proyecto.
        salida (Path): Carpeta destino de los CSV y del C decompilado.
        decompilar (bool): Si se produce un ``.c`` por funcion.
        segundos_por_funcion (int): Limite del decompilador por funcion.

    Returns:
        list[str]: Argumentos listos para ``subprocess``.

    Raises:
        ValueError: Si un argumento contiene caracteres que el interprete reinterpretaria o
            ``segundos_por_funcion`` esta fuera de rango.

    Ejemplo:
        comando = construir_comando_exportacion(
            config, "SLUS_008.38", out, decompilar=True, segundos_por_funcion=60
        )
    """
    comando = _base_comando(config, segundos_por_funcion)
    comando += ["-process", _validar_argumento(programa, "programa"), "-noanalysis", "-readOnly"]
    comando += ["-scriptPath", _validar_argumento(str(config.scripts), "scripts")]
    comando += ["-postScript", "ExportarFunciones.java", _validar_argumento(str(salida), "salida")]
    comando += ["si" if decompilar else "no", str(segundos_por_funcion)]
    return comando


def _terminar_arbol(proceso: subprocess.Popen[str]) -> None:
    """Termina el proceso y sus hijos: el lanzador de Ghidra delega en una JVM aparte."""
    try:
        subprocess.run(
            ["taskkill", "/PID", str(proceso.pid), "/T", "/F"],
            capture_output=True,
            check=False,
            timeout=30,
        )
    except OSError:
        pass
    proceso.kill()


def ejecutar_proceso(comando: Sequence[str], segundos: int) -> ResultadoEjecucion:
    """
    Ejecuta un comando en primer plano con limite de tiempo.

    Contexto:
        Ejecutor real que usa la CLI. Si se agota el tiempo se termina todo el arbol de
        procesos para que no quede una JVM huerfana consumiendo CPU.

    Args:
        comando (Sequence[str]): Programa y argumentos.
        segundos (int): Tiempo maximo de ejecucion.

    Returns:
        ResultadoEjecucion: Codigo de salida y salida combinada.

    Raises:
        TimeoutError: Si el proceso no termina dentro de ``segundos``.

    Ejemplo:
        resultado = ejecutar_proceso(["python", "--version"], 10)
    """
    with subprocess.Popen(
        list(comando),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    ) as proceso:
        try:
            salida, _ = proceso.communicate(timeout=segundos)
        except subprocess.TimeoutExpired:
            _terminar_arbol(proceso)
            proceso.communicate()
            raise TimeoutError(f"el proceso excedio {segundos} segundos") from None
        return ResultadoEjecucion(proceso.returncode, salida)


def verificar_carga(salida: str) -> Carga:
    """
    Comprueba en el registro que el ejecutable se cargo con el cargador PSX y los datos esperados.

    Contexto:
        Cierra el comando ``analizar``: un cargador generico produciria un programa sin
        segmentos ni punto de entrada correctos y el analisis seria inservible.

    Args:
        salida (str): Salida combinada de ``analyzeHeadless``.

    Returns:
        Carga: Base y entrada leidas del registro.

    Raises:
        ValueError: Si no se uso el cargador PSX, faltan las marcas de base o entrada, o sus
            valores difieren de ``DIRECCION_BASE`` y ``DIRECCION_ENTRADA``.

    Ejemplo:
        carga = verificar_carga(resultado.salida)
    """
    if _PATRON_CARGADOR.search(salida) is None:
        raise ValueError("el registro no confirma el uso del cargador PSX")
    marcas = {m["clave"]: int(m["valor"], 16) for m in _PATRON_MARCA.finditer(salida)}
    for clave in ("base", "entrada"):
        if clave not in marcas:
            raise ValueError(f"el registro no informa la {clave} del programa")
    if marcas["base"] != DIRECCION_BASE:
        raise ValueError(f"base=0x{marcas['base']:08X}, se esperaba 0x{DIRECCION_BASE:08X}")
    if marcas["entrada"] != DIRECCION_ENTRADA:
        raise ValueError(f"entrada=0x{marcas['entrada']:08X}, se esperaba 0x{DIRECCION_ENTRADA:08X}")
    return Carga(base=marcas["base"], entrada=marcas["entrada"])


def ejecutar_analisis(
    config: ConfiguracionGhidra,
    ejecutable: Path,
    semilla: Path | None,
    versiones: Sequence[str],
    *,
    segundos: int = SEGUNDOS_MAXIMOS,
    ejecutor: Ejecutor = ejecutar_proceso,
) -> Carga:
    """
    Importa y analiza el ejecutable y verifica la carga.

    Contexto:
        Implementacion del comando ``analizar``; la carpeta del proyecto se crea si no existe.

    Args:
        config (ConfiguracionGhidra): Rutas de Ghidra, proyecto y scripts.
        ejecutable (Path): Ejecutable PS-X a importar.
        semilla (Path | None): Archivo de direcciones de funciones, o ``None``.
        versiones (Sequence[str]): Versiones adicionales de firmas.
        segundos (int, opcional): Tiempo maximo del proceso; por defecto ``SEGUNDOS_MAXIMOS``.
        ejecutor (Ejecutor, opcional): Funcion que lanza el proceso; se inyecta en las pruebas.

    Returns:
        Carga: Base y entrada confirmadas por el registro.

    Raises:
        ValueError: Si Ghidra termina con error o la verificacion de carga falla.
        TimeoutError: Si el proceso excede el tiempo.

    Ejemplo:
        carga = ejecutar_analisis(config, exe, semilla, VERSIONES_FIRMAS)
    """
    config.proyecto.mkdir(parents=True, exist_ok=True)
    comando = construir_comando_analisis(config, ejecutable, semilla, versiones, segundos)
    resultado = ejecutor(comando, segundos)
    if resultado.codigo != 0:
        raise ValueError(f"analyzeHeadless termino con codigo {resultado.codigo}")
    return verificar_carga(resultado.salida)


def ejecutar_exportacion(
    config: ConfiguracionGhidra,
    programa: str,
    salida: Path,
    *,
    decompilar: bool = True,
    segundos_por_funcion: int = 60,
    segundos: int = SEGUNDOS_MAXIMOS,
    ejecutor: Ejecutor = ejecutar_proceso,
) -> None:
    """
    Exporta funciones, cadenas, referencias y C decompilado de un programa analizado.

    Contexto:
        Implementacion del comando ``exportar``; produce los archivos que lee el comando
        ``simbolos``.

    Args:
        config (ConfiguracionGhidra): Rutas de Ghidra, proyecto y scripts.
        programa (str): Nombre del programa dentro del proyecto.
        salida (Path): Carpeta destino; se crea si no existe.
        decompilar (bool, opcional): Si se genera un ``.c`` por funcion.
        segundos_por_funcion (int, opcional): Limite del decompilador por funcion.
        segundos (int, opcional): Tiempo maximo del proceso completo.
        ejecutor (Ejecutor, opcional): Funcion que lanza el proceso; se inyecta en las pruebas.

    Returns:
        None: Los resultados quedan en ``salida``.

    Raises:
        ValueError: Si Ghidra termina con error o no produce ``funciones.csv``.
        TimeoutError: Si el proceso excede el tiempo.

    Ejemplo:
        ejecutar_exportacion(config, "SLUS_008.38", Path("analisis/ghidra"))
    """
    salida.mkdir(parents=True, exist_ok=True)
    # Un script que no compila deja a Ghidra con codigo de salida 0: sin borrar la exportacion
    # previa, un resultado viejo pasaria por reciente.
    (salida / "funciones.csv").unlink(missing_ok=True)
    comando = construir_comando_exportacion(
        config, programa, salida, decompilar=decompilar, segundos_por_funcion=segundos_por_funcion
    )
    resultado = ejecutor(comando, segundos)
    if resultado.codigo != 0:
        raise ValueError(f"analyzeHeadless termino con codigo {resultado.codigo}")
    if not (salida / "funciones.csv").is_file():
        raise ValueError("la exportacion no produjo funciones.csv")

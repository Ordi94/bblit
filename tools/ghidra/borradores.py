"""Borradores en C de las funciones del juego, generados con ``m2c``.

El flujo es: desensamblar el ejecutable en una carpeta propia (nunca en el ``asm/`` del
repositorio, cuya forma cambia con la particion), repartir el texto en un archivo por funcion,
construir un contexto de tipos con lo que exporto Ghidra y lanzar ``m2c`` por funcion con un
limite de tiempo. Una funcion que falla no detiene la corrida: queda registrada con su causa.
"""

import csv
import io
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from tools.ghidra.contexto import construir_contexto, extraer_prototipo
from tools.ghidra.dominio import Funcion, Simbolo
from tools.ghidra.ejecucion import ResultadoEjecucion
from tools.ghidra.ensamblador import FuncionAsm, dividir_por_funcion, leer_instrucciones
from tools.ghidra.exportaciones import ReferenciaDato
from tools.ghidra.grafo import TablaSalto
from tools.ghidra.zonas import FIN_JUEGO, INICIO_JUEGO

COLUMNAS_FALLIDAS: Final[tuple[str, ...]] = ("direccion", "nombre", "causa")
COLUMNAS_FUSIONADAS: Final[tuple[str, ...]] = ("direccion", "nombre", "absorbidas")
MAX_FRAGMENTOS: Final[int] = 8
"""Funciones contiguas que se prueban al fusionar: las cadenas reales miden 2."""

SEGUNDOS_POR_FUNCION: Final[int] = 120
"""Limite de ``m2c`` por funcion: en la poblacion real ninguna pasa de unos 2 s."""

MAX_CAUSA: Final[int] = 200
"""Longitud maxima de la causa de un fallo guardada en ``FALLIDAS.csv``."""

OFFSET_DATOS: Final[int] = 0x49CA0
OFFSET_RODATA: Final[int] = 0x53A70
OFFSET_BSS: Final[int] = 0x55800
"""Fronteras de la zona de datos del archivo: replican la particion del repositorio para que los
nombres automaticos de las tablas (``jtbl_...``) coincidan con los del resto del analisis."""

NOMBRE_EJECUTABLE_COPIA: Final[str] = "SLUS_008.38"

ENCABEZADO_ASM: Final[str] = '.set noat\n.set noreorder\n.section .text, "ax"\n\n'
_PATRON_ETIQUETA: Final[re.Pattern[str]] = re.compile(r"\.L(?P<direccion>[0-9A-F]{8})\b")
_PATRON_RAMA: Final[re.Pattern[str]] = re.compile(r"^Cannot find branch target (?P<objetivo>\S+)$")
_PATRON_FALLO: Final[re.Pattern[str]] = re.compile(
    r"^/\*\s*\nDecompilation failure[^\n]*\n\s*\n(?P<causa>[^\n]+)"
)

Ambito = Literal["sin_firma", "rango"]
"""``sin_firma`` (rutinas que ninguna firma de libreria identifica) o ``rango`` (solo el juego)."""

Lanzador = Callable[[Sequence[str], int], ResultadoEjecucion]
"""Ejecuta un comando con limite de segundos y devuelve codigo y salida combinada."""

LanzadorSeparado = Callable[[Sequence[str], int], tuple[int, str, str]]
"""Ejecuta un comando y devuelve codigo de salida, salida estandar y salida de error por separado."""


@dataclass(frozen=True)
class ResumenBorradores:
    """Conteos de una corrida: elegidas, borradores escritos, fallos y funciones absorbidas por otra."""

    seleccionadas: int
    generadas: int
    fallidas: int
    absorbidas: int
    con_marcas: int


def seleccionar_funciones(
    simbolos: Sequence[Simbolo], funciones: Sequence[Funcion], ambito: Ambito = "sin_firma"
) -> list[Simbolo]:
    """
    Elige las funciones para las que se generan borradores.

    Contexto:
        El juego propio (``0x80014AC4..0x80045DA0``) mas las rutinas que ninguna firma de libreria
        reconoce (incluidas las 32 sin fila en Ghidra), que son las que hay que descompilar.

    Args:
        simbolos (Sequence[Simbolo]): Tabla de simbolos de funcion.
        funciones (Sequence[Funcion]): Filas de ``funciones.csv`` (clasificacion de Ghidra).
        ambito (Ambito, opcional): ``sin_firma`` o ``rango``.

    Returns:
        list[Simbolo]: Simbolos elegidos en orden ascendente de direccion.

    Raises:
        ValueError: Si el ambito no es ``sin_firma`` ni ``rango``.

    Ejemplo:
        elegidas = seleccionar_funciones(simbolos, funciones)
    """
    if ambito not in ("sin_firma", "rango"):
        raise ValueError("borradores: el ambito debe ser sin_firma o rango")
    de_libreria = {f.direccion for f in funciones if f.es_libreria}
    if ambito == "rango":
        elegidas = [s for s in simbolos if INICIO_JUEGO <= s.direccion < FIN_JUEGO]
    else:
        elegidas = [s for s in simbolos if s.direccion not in de_libreria]
    return sorted(elegidas, key=lambda s: s.direccion)


def nombre_archivo(simbolo: Simbolo, extension: str) -> str:
    """
    Devuelve el nombre de archivo de una funcion.

    Contexto:
        Convencion de los archivos de salida: la misma que usan las exportaciones de Ghidra
        (direccion en mayusculas y nombre del simbolo).

    Args:
        simbolo (Simbolo): Funcion.
        extension (str): Extension sin punto (``s`` o ``c``).

    Returns:
        str: ``80016414_main.s``, por ejemplo.

    Ejemplo:
        nombre = nombre_archivo(Simbolo("main", 0x80016414, "func", 0x7F8), "s")
    """
    return f"{simbolo.direccion:08X}_{simbolo.nombre}.{extension}"


def construir_config_desensamblador(simbolos: Path, tamano_archivo: int, base: int) -> str:
    """
    Escribe la configuracion de splat para la copia propia del desensamblado.

    Contexto:
        Se genera como JSON (que es YAML valido) con rutas entrecomilladas, de modo que las
        carpetas con espacios no rompen la lectura. Todas las rutas de salida son relativas a la
        carpeta de la configuracion y el ejecutable se espera junto a ella con su nombre original.

    Args:
        simbolos (Path): ``config/symbols.txt``.
        tamano_archivo (int): Tamano del archivo del ejecutable (fin de la ultima zona).
        base (int): Direccion virtual del primer byte del segmento.

    Returns:
        str: Contenido del archivo de configuracion.

    Ejemplo:
        texto = construir_config_desensamblador(simbolos, 0x55800, 0x80014A00)
    """
    configuracion = {
        "options": {
            "platform": "psx",
            "basename": "SLUS_008",
            "base_path": ".",
            "target_path": NOMBRE_EJECUTABLE_COPIA,
            "compiler": "GCC",
            "asm_path": "asm",
            "build_path": "build",
            "ld_script_path": "build/SLUS_008.ld",
            "undefined_funcs_auto_path": "build/funciones_automaticas.txt",
            "undefined_syms_auto_path": "build/simbolos_automaticos.txt",
            "symbol_addrs_path": [simbolos.resolve().as_posix()],
            "find_file_boundaries": False,
            "create_asm_dependencies": False,
        },
        "segments": [
            {
                "name": "main",
                "type": "code",
                "start": 0x800,
                "vram": base,
                "bss_size": 0xE000,
                "subsegments": [
                    [0x800, "asm", "text"],
                    [OFFSET_DATOS, "data", "data"],
                    [OFFSET_RODATA, "rodata", "rodata"],
                    {
                        "start": OFFSET_BSS,
                        "type": "bss",
                        "name": "bss",
                        "vram": base + tamano_archivo - 0x800,
                    },
                ],
            },
            [tamano_archivo],
        ],
    }
    return json.dumps(configuracion, indent=2) + "\n"


def asegurar_desensamblado(
    exe: Path, simbolos: Path, carpeta: Path, *, base: int, tamano_archivo: int, lanzador: Lanzador
) -> str:
    """
    Obtiene el texto del desensamblado propio, generandolo con splat si aun no existe.

    Contexto:
        Primer paso de ``borradores`` y de ``grafo``. Reutiliza la copia de una corrida anterior
        para no repetir el desensamblado; se borra la carpeta para regenerarla.

    Args:
        exe (Path): Ejecutable original.
        simbolos (Path): ``config/symbols.txt``.
        carpeta (Path): Carpeta de trabajo propia (``<salida>/desensamblado``).
        base (int): Direccion virtual del primer byte del segmento.
        tamano_archivo (int): Tamano del archivo del ejecutable.
        lanzador (Lanzador): Ejecuta procesos con limite de tiempo.

    Returns:
        str: Contenido de ``text.s``.

    Raises:
        ValueError: Si splat falla o no deja el desensamblado esperado.
        TimeoutError: Si splat excede el limite de tiempo.

    Ejemplo:
        texto = asegurar_desensamblado(exe, simbolos, carpeta, base=0x80014A00, tamano_archivo=0x55800,
                                       lanzador=ejecutar_proceso)
    """
    texto_s = carpeta / "asm" / "text.s"
    if not texto_s.is_file():
        carpeta.mkdir(parents=True, exist_ok=True)
        configuracion = carpeta / "splat.yaml"
        shutil.copyfile(exe, carpeta / NOMBRE_EJECUTABLE_COPIA)
        configuracion.write_text(
            construir_config_desensamblador(simbolos, tamano_archivo, base),
            encoding="utf-8",
            newline="\n",
        )
        resultado = lanzador([sys.executable, "-X", "utf8", "-m", "splat", "split", str(configuracion)], 600)
        if resultado.codigo != 0 or not texto_s.is_file():
            raise ValueError("desensamblado: splat no pudo generar text.s")
    return texto_s.read_text(encoding="utf-8")


def preparar_asm_funcion(funcion: FuncionAsm, tablas: Sequence[TablaSalto]) -> str:
    """
    Arma el archivo ``.s`` de una funcion listo para ``m2c``.

    Contexto:
        ``m2c`` necesita ver las tablas de un ``switch`` junto a la funcion y que sus destinos sean
        etiquetas. El desensamblador solo las crea para las tablas de la zona de solo lectura;
        aqui se anaden las etiquetas que falten y una seccion ``.rodata`` con cada tabla.

    Args:
        funcion (FuncionAsm): Funcion ya dividida.
        tablas (Sequence[TablaSalto]): Tablas de salto de la funcion (vacio si no tiene).

    Returns:
        str: Texto ensamblable con el encabezado, el cuerpo y las tablas.

    Ejemplo:
        texto = preparar_asm_funcion(funcion, grafo.tablas_salto.get(funcion.direccion, ()))
    """
    destinos = {d for t in tablas for d in t.destinos}
    nombres_tabla = {t.simbolo: nombre_de_tabla(t) for t in tablas}
    existentes = {
        int(m["direccion"], 16) for linea in funcion.lineas for m in _PATRON_ETIQUETA.finditer(linea)
    }
    faltantes = destinos - existentes
    instrucciones = {i.direccion for i in leer_instrucciones(funcion)}
    cuerpo: list[str] = []
    for original in funcion.lineas:
        linea = original
        for antiguo, nuevo in nombres_tabla.items():
            if antiguo != nuevo:
                linea = re.sub(rf"\b{re.escape(antiguo)}\b", nuevo, linea)
        direccion = _direccion_de_linea(linea)
        if direccion in faltantes and direccion in instrucciones:
            cuerpo.append(f"  .L{direccion:08X}:")
            faltantes.discard(direccion)
        cuerpo.append(linea)
    texto = ENCABEZADO_ASM + "\n".join(cuerpo) + "\n"
    for tabla in tablas:
        palabras = "\n".join(f"    .word .L{d:08X}" for d in tabla.destinos)
        nombre = nombres_tabla[tabla.simbolo]
        texto += f"\n.section .rodata\n\ndlabel {nombre}\n{palabras}\nenddlabel {nombre}\n"
    return texto


def nombre_de_tabla(tabla: TablaSalto) -> str:
    """
    Nombre con el que ``m2c`` reconoce una tabla de saltos.

    Contexto:
        ``m2c`` solo trata un dato como tabla de un ``switch`` si su nombre empieza por ``jtbl``;
        las tablas que el desensamblador dejo como ``D_<direccion>`` se renombran en la copia.

    Args:
        tabla (TablaSalto): Tabla de salto.

    Returns:
        str: El mismo simbolo si ya empieza por ``jtbl``; si no, ``jtbl_<direccion>``.

    Ejemplo:
        nombre = nombre_de_tabla(TablaSalto("D_8005E3F0", 0x8005E3F0, ()))  # "jtbl_8005E3F0"
    """
    return tabla.simbolo if tabla.simbolo.startswith("jtbl") else f"jtbl_{tabla.direccion:08X}"


def _direccion_de_linea(linea: str) -> int | None:
    """Direccion de una linea de instruccion del desensamblado, o ``None``."""
    coincidencia = re.match(r"^\s*/\* [0-9A-F]+ (?P<direccion>[0-9A-F]{8}) ", linea)
    return None if coincidencia is None else int(coincidencia["direccion"], 16)


def ejecutar_separado(comando: Sequence[str], segundos: int) -> tuple[int, str, str]:
    """
    Ejecuta un comando en primer plano con limite de tiempo y las salidas separadas.

    Contexto:
        Lanzador real de ``m2c``: el C va por la salida estandar y los avisos por la de error, y
        mezclarlos ensuciaria el borrador.

    Args:
        comando (Sequence[str]): Programa y argumentos.
        segundos (int): Tiempo maximo de ejecucion.

    Returns:
        tuple[int, str, str]: Codigo de salida, salida estandar y salida de error.

    Raises:
        TimeoutError: Si el proceso no termina dentro de ``segundos``.

    Ejemplo:
        codigo, salida, errores = ejecutar_separado(["python", "--version"], 10)
    """
    try:
        resultado = subprocess.run(
            list(comando),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=segundos,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"el proceso excedio {segundos} segundos") from None
    return resultado.returncode, resultado.stdout, resultado.stderr


def causa_de_fallo(codigo: int, salida: str, errores: str) -> str | None:
    """
    Interpreta el resultado de ``m2c`` y devuelve la causa si fallo.

    Contexto:
        ``m2c`` puede salir con 0 y aun asi dejar en la salida un comentario de "Decompilation
        failure" (por ejemplo, un ``jr`` sin tabla de saltos); tambien puede salir con error.

    Args:
        codigo (int): Codigo de salida.
        salida (str): Salida estandar (el C).
        errores (str): Salida de error.

    Returns:
        str | None: Causa en una linea de hasta ``MAX_CAUSA`` caracteres, o ``None`` si el borrador
        es valido.

    Ejemplo:
        causa = causa_de_fallo(0, "s32 f(void) { }", "")
    """
    fallo = _PATRON_FALLO.match(salida)
    if fallo is not None:
        return " ".join(fallo["causa"].split())[:MAX_CAUSA]
    if codigo != 0:
        detalle = next(
            (" ".join(linea.split()) for linea in reversed(errores.splitlines()) if linea.strip()), ""
        )
        return f"codigo de salida {codigo}: {detalle}"[:MAX_CAUSA]
    if not salida.strip():
        return "salida vacia"
    return None


def formatear_fallidas(fallidas: Sequence[tuple[Simbolo, str]]) -> str:
    """
    Serializa las funciones sin borrador como ``FALLIDAS.csv``.

    Contexto:
        Registro de lo que ``m2c`` no pudo decompilar y por que; siempre se escribe, aunque este
        vacio, para que su ausencia no se confunda con una corrida incompleta.

    Args:
        fallidas (Sequence[tuple[Simbolo, str]]): Funcion y causa.

    Returns:
        str: CSV con LF y columnas de ``COLUMNAS_FALLIDAS``.

    Ejemplo:
        texto = formatear_fallidas([(simbolo, "tiempo agotado")])
    """
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(COLUMNAS_FALLIDAS)
    for simbolo, causa in fallidas:
        escritor.writerow([f"0x{simbolo.direccion:08X}", simbolo.nombre, causa])
    return salida.getvalue()


def leer_prototipos(decomp: Path, simbolos: Sequence[Simbolo]) -> dict[int, str]:
    """
    Lee los prototipos de las exportaciones de Ghidra para todos los simbolos.

    Contexto:
        Los archivos se localizan por direccion (``<DIRECCION>_<nombre>.c``) porque el nombre de
        Ghidra y el del simbolo pueden diferir.

    Args:
        decomp (Path): Carpeta ``decomp`` de la exportacion.
        simbolos (Sequence[Simbolo]): Tabla de simbolos.

    Returns:
        dict[int, str]: Prototipo por direccion de funcion, solo para los traducibles.

    Ejemplo:
        prototipos = leer_prototipos(Path("analisis/ghidra/decomp"), simbolos)
    """
    archivos: dict[int, Path] = {}
    for candidato in sorted(decomp.glob("*.c")):
        prefijo = candidato.name.split("_", 1)[0]
        if re.fullmatch(r"[0-9A-Fa-f]{8}", prefijo):
            archivos.setdefault(int(prefijo, 16), candidato)
    prototipos: dict[int, str] = {}
    for simbolo in simbolos:
        archivo = archivos.get(simbolo.direccion)
        if archivo is None:
            continue
        prototipo = extraer_prototipo(archivo.read_text(encoding="utf-8", errors="replace"), simbolo.nombre)
        if prototipo is not None:
            prototipos[simbolo.direccion] = prototipo
    return prototipos


def fusionar_funciones(cadena: Sequence[FuncionAsm]) -> FuncionAsm:
    """
    Une funciones contiguas del desensamblado en una sola.

    Contexto:
        Una rutina muy grande puede haberse partido en varios simbolos (por un ``jr $ra`` en medio
        del cuerpo), de modo que una rama de la primera salta a una etiqueta de la siguiente.
        ``m2c`` necesita ver ambas en una unica funcion para resolver ese salto.

    Args:
        cadena (Sequence[FuncionAsm]): Funciones contiguas, la primera da nombre y direccion.

    Returns:
        FuncionAsm: Funcion con el cuerpo de todas; las cabeceras de las absorbidas pasan a ser
        etiquetas locales.

    Raises:
        ValueError: Si la cadena esta vacia.

    Ejemplo:
        unida = fusionar_funciones([principal, continuacion])
    """
    if not cadena:
        raise ValueError("borradores: no hay funciones que fusionar")
    primera = cadena[0]
    lineas: list[str] = []
    for funcion in cadena:
        for linea in funcion.lineas:
            if linea.startswith("endlabel "):
                continue
            if linea.startswith("glabel ") and funcion is not primera:
                lineas.append(f"  .L{funcion.direccion:08X}:")
                continue
            lineas.append(linea)
    lineas.append(f"endlabel {primera.nombre}")
    return FuncionAsm(primera.nombre, primera.direccion, tuple(lineas))


def buscar_continuacion(causa: str, ordenadas: Sequence[FuncionAsm], posicion: int) -> int | None:
    """
    Localiza la funcion que contiene el destino de una rama que ``m2c`` no encontro.

    Contexto:
        Segunda oportunidad para las funciones cuyo cuerpo continua en la siguiente: el mensaje de
        ``m2c`` nombra la etiqueta o la funcion que falta y se busca entre las posteriores.

    Args:
        causa (str): Causa de fallo registrada para la funcion.
        ordenadas (Sequence[FuncionAsm]): Todas las funciones en orden de direccion.
        posicion (int): Indice de la funcion que fallo.

    Returns:
        int | None: Indice de la funcion que contiene el destino, si esta entre las
        ``MAX_FRAGMENTOS`` siguientes; ``None`` si la causa es otra o el destino no se halla.

    Ejemplo:
        indice = buscar_continuacion("Cannot find branch target .L8004439C", ordenadas, 3)
    """
    coincidencia = _PATRON_RAMA.match(causa)
    if coincidencia is None:
        return None
    objetivo = coincidencia["objetivo"]
    limite = min(len(ordenadas), posicion + 1 + MAX_FRAGMENTOS)
    for indice in range(posicion + 1, limite):
        funcion = ordenadas[indice]
        if objetivo == funcion.nombre or any(
            f"{objetivo}:" in linea or f"jlabel {objetivo}" in linea for linea in funcion.lineas
        ):
            return indice
    return None


def generar_borradores(
    *,
    elegidas: Sequence[Simbolo],
    texto_asm: str,
    tablas: Mapping[int, Sequence[TablaSalto]],
    contexto: str,
    salida: Path,
    m2c: Path,
    segundos: int,
    lanzador: LanzadorSeparado = ejecutar_separado,
) -> ResumenBorradores:
    """
    Escribe el asm por funcion y lanza ``m2c`` sobre cada una.

    Contexto:
        Nucleo del comando ``borradores``. Una funcion cuyo ``m2c`` falla, no termina o excede el
        tiempo se anota en ``FALLIDAS.csv`` y la corrida sigue con la siguiente. Si la causa es una
        rama hacia una funcion contigua, se reintenta con ambas fusionadas y la absorbida se anota
        en ``FUSIONADAS.csv``.

    Args:
        elegidas (Sequence[Simbolo]): Funciones a procesar (ver ``seleccionar_funciones``).
        texto_asm (str): Contenido de ``text.s`` de la copia propia.
        tablas (Mapping[int, Sequence[TablaSalto]]): Tablas de salto por direccion de funcion.
        contexto (str): Contenido de ``contexto_m2c.c``.
        salida (Path): Carpeta de salida (se crean ``asm/``, ``m2c/`` y ``contexto_m2c.c``).
        m2c (Path): Ruta de ``m2c.py``.
        segundos (int): Limite de tiempo por funcion.
        lanzador (LanzadorSeparado, opcional): Ejecuta procesos; por defecto el real.

    Returns:
        ResumenBorradores: Funciones elegidas, borradores generados, fallos, funciones absorbidas
        por otra y borradores que contienen marcas ``M2C_``.

    Raises:
        ValueError: Si una funcion elegida no figura en el desensamblado.

    Ejemplo:
        resumen = generar_borradores(elegidas=elegidas, texto_asm=texto, tablas={}, contexto=ctx,
                                     salida=Path("salida"), m2c=Path("m2c.py"), segundos=120)
    """
    ordenadas = sorted(dividir_por_funcion(texto_asm), key=lambda f: f.direccion)
    posicion_de = {f.direccion: i for i, f in enumerate(ordenadas)}
    carpeta_asm, carpeta_c = salida / "asm", salida / "m2c"
    carpeta_asm.mkdir(parents=True, exist_ok=True)
    carpeta_c.mkdir(parents=True, exist_ok=True)
    ruta_contexto = salida / "contexto_m2c.c"
    ruta_contexto.write_text(contexto, encoding="utf-8", newline="\n")

    def decompilar(
        simbolo: Simbolo, funcion: FuncionAsm, tablas_funcion: Sequence[TablaSalto]
    ) -> tuple[str | None, str]:
        ruta_asm = carpeta_asm / nombre_archivo(simbolo, "s")
        ruta_asm.write_text(preparar_asm_funcion(funcion, tablas_funcion), encoding="utf-8", newline="\n")
        comando = [
            sys.executable,
            "-X",
            "utf8",
            str(m2c),
            "--target",
            "mipsel-gcc-c",
            "--context",
            str(ruta_contexto),
            str(ruta_asm),
        ]
        try:
            codigo, texto_c, errores = lanzador(comando, segundos)
        except TimeoutError:
            return f"tiempo agotado ({segundos} s)", ""
        return causa_de_fallo(codigo, texto_c, errores), texto_c

    fallidas: list[tuple[Simbolo, str]] = []
    fusionadas: list[tuple[Simbolo, list[Simbolo]]] = []
    absorbidas: set[int] = set()
    con_marcas = 0
    for simbolo in elegidas:
        if simbolo.direccion in absorbidas:
            continue
        indice = posicion_de.get(simbolo.direccion)
        if indice is None or ordenadas[indice].nombre != simbolo.nombre:
            raise ValueError(f"borradores: {simbolo.nombre} no figura en el desensamblado")
        causa, texto_c = decompilar(simbolo, ordenadas[indice], tablas.get(simbolo.direccion, ()))
        unidas: list[Simbolo] = []
        if causa is not None:
            continuacion = buscar_continuacion(causa, ordenadas, indice)
            if continuacion is not None:
                cadena = ordenadas[indice : continuacion + 1]
                tablas_cadena = [t for f in cadena for t in tablas.get(f.direccion, ())]
                causa_unida, texto_unido = decompilar(simbolo, fusionar_funciones(cadena), tablas_cadena)
                if causa_unida is None:
                    causa, texto_c = None, texto_unido
                    unidas = [Simbolo(f.nombre, f.direccion, "func", 0) for f in cadena[1:]]
        if causa is not None:
            fallidas.append((simbolo, causa))
            continue
        if unidas:
            absorbidas.update(u.direccion for u in unidas)
            fusionadas.append((simbolo, unidas))
        (carpeta_c / nombre_archivo(simbolo, "c")).write_text(texto_c, encoding="utf-8", newline="\n")
        con_marcas += "M2C_" in texto_c
    (carpeta_c / "FALLIDAS.csv").write_text(formatear_fallidas(fallidas), encoding="utf-8", newline="\n")
    (carpeta_c / "FUSIONADAS.csv").write_text(
        formatear_fusionadas(fusionadas), encoding="utf-8", newline="\n"
    )
    elegidas_absorbidas = sum(1 for s in elegidas if s.direccion in absorbidas)
    return ResumenBorradores(
        seleccionadas=len(elegidas),
        generadas=len(elegidas) - len(fallidas) - elegidas_absorbidas,
        fallidas=len(fallidas),
        absorbidas=elegidas_absorbidas,
        con_marcas=con_marcas,
    )


def formatear_fusionadas(fusionadas: Sequence[tuple[Simbolo, Sequence[Simbolo]]]) -> str:
    """
    Serializa las funciones que se decompilaron junto a sus continuaciones.

    Contexto:
        Registro de las rutinas que el desensamblador separo en varios simbolos pero que forman una
        sola funcion; sirve para corregir la tabla de simbolos mas adelante.

    Args:
        fusionadas (Sequence[tuple[Simbolo, Sequence[Simbolo]]]): Funcion principal y continuaciones.

    Returns:
        str: CSV con LF; las absorbidas van como ``direccion:nombre`` separadas por ``;``.

    Ejemplo:
        texto = formatear_fusionadas([(principal, [continuacion])])
    """
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(COLUMNAS_FUSIONADAS)
    for principal, continuaciones in fusionadas:
        listado = ";".join(f"0x{c.direccion:08X}:{c.nombre}" for c in continuaciones)
        escritor.writerow([f"0x{principal.direccion:08X}", principal.nombre, listado])
    return salida.getvalue()


def contexto_desde_exportacion(
    simbolos: Sequence[Simbolo], decomp: Path, datos: Sequence[ReferenciaDato]
) -> str:
    """
    Construye el texto de ``contexto_m2c.c`` a partir de las exportaciones de Ghidra.

    Contexto:
        Une la lectura de prototipos (disco) con la construccion pura del contexto.

    Args:
        simbolos (Sequence[Simbolo]): Tabla de simbolos.
        decomp (Path): Carpeta ``decomp`` de la exportacion.
        datos (Sequence[ReferenciaDato]): Datos de ``xrefs_datos.csv``.

    Returns:
        str: Contenido de ``contexto_m2c.c``.

    Ejemplo:
        contexto = contexto_desde_exportacion(simbolos, Path("analisis/ghidra/decomp"), datos)
    """
    return construir_contexto(simbolos, leer_prototipos(decomp, simbolos), datos)

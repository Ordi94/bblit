"""Comparacion de una funcion compilada contra su objetivo original con ``asm-differ``.

``python tools/build.py diff <funcion>`` hace tres cosas: compila el archivo C que contiene la
funcion (con ``NON_MATCHING`` definida, para ver tambien los intentos que la construccion normal
no usa), ensambla el asm original de la funcion como objetivo y ejecuta ``asm-differ`` sobre
ambos objetos. La puntuacion 0 significa que las instrucciones y los simbolos coinciden o que,
tras enlazar, los bytes de la funcion son los del original aunque ``asm-differ`` puntue la forma
simbolica frente a la numerica de una referencia (esa puntuacion queda en ``puntuacion_asm``).

Una funcion que sigue en ``INCLUDE_ASM`` no se compara: el objeto candidato contendria el mismo
ensamblador que el objetivo y la puntuacion 0 seria una coincidencia falsa.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tools.reconstruccion import dominio, fuentes_c
from tools.reconstruccion.compilacion import (
    CARPETA_MACROS,
    HerramientasCompilacion,
    compilar_fuente,
)
from tools.reconstruccion.enlace_diff import bytes_coinciden, contar_referencias_numericas
from tools.reconstruccion.fuentes_c import EstadoFuncion
from tools.reconstruccion.infraestructura import (
    CARPETA_DIFF,
    Ejecutor,
    leer_direcciones_de_funciones,
    leer_valores_g,
    listar_fuentes_c,
)

TIMEOUT_DIFF_S = 300
LIMITE_MINIMO_LINEAS = 1024
MARGEN_LINEAS = 64
CARPETA_ASM_COINCIDENTE = "asm/matchings"
CARPETA_ASM_PENDIENTE = "asm/nonmatchings"
_PATRON_FUNCION = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_PATRON_RETORNO = re.compile(r"^\s*/\*.*?\*/\s+jr\s+\$ra\b", re.MULTILINE)
_PATRON_INSTRUCCION = re.compile(r"^\s*/\*.*?\*/\s+[A-Za-z.]", re.MULTILINE)


@dataclass(frozen=True)
class ResultadoDiff:
    """Resultado de comparar una funcion.

    Attributes:
        funcion: Nombre de la funcion comparada.
        archivo: Archivo C que la contiene.
        puntuacion: Puntuacion informada: 0 si las instrucciones coinciden o si los bytes enlazados
            coinciden con los del original; en otro caso la de ``asm-differ``.
        texto: Diferencias instruccion por instruccion, listas para imprimir.
        bytes_iguales: Si los bytes de la funcion enlazada coinciden con los del original (``None``
            si no se pudo comparar o la puntuacion ya era cero).
        referencias_numericas: Filas cuya unica diferencia es una referencia escrita como numero.
        puntuacion_asm: Puntuacion que dio ``asm-differ`` antes de comparar los bytes (``None`` si
            no se registro).
    """

    funcion: str
    archivo: str
    puntuacion: int
    texto: str
    bytes_iguales: bool | None = None
    referencias_numericas: int = 0
    puntuacion_asm: int | None = None

    @property
    def coincide(self) -> bool:
        """Verdadero si la puntuacion es cero o si los bytes enlazados son iguales."""
        return self.puntuacion == 0 or self.bytes_iguales is True


class FuncionSinCError(ValueError):
    """La funcion existe pero todavia no tiene C que comparar."""


def validar_funcion(nombre: str) -> str:
    """
    Valida el nombre de una funcion recibido por linea de ordenes.

    Contexto:
        El nombre termina formando rutas (``asm/nonmatchings/<archivo>/<nombre>.s``) y argumentos
        de procesos: solo se aceptan identificadores C razonables.

    Args:
        nombre (str): Nombre pedido por el usuario.

    Returns:
        str: El mismo nombre, validado.

    Raises:
        ValueError: Si no es un identificador de hasta 64 caracteres.

    Ejemplo:
        funcion = validar_funcion("func_80036204")
    """
    if not _PATRON_FUNCION.match(nombre):
        raise ValueError("el nombre de la funcion debe ser un identificador C de hasta 64 caracteres")
    return nombre


def contar_retornos(asm: str) -> int:
    """
    Cuenta las instrucciones ``jr $ra`` de un ensamblador generado por el particionador.

    Contexto:
        ``asm-differ`` corta el desensamblado tras N retornos (``-s`` repetido N veces); sin ese
        corte, el objeto candidato (un archivo C entero) se volcaria hasta el final de la seccion.

    Args:
        asm (str): Contenido del ``.s`` de la funcion objetivo.

    Returns:
        int: Numero de retornos.

    Ejemplo:
        retornos = contar_retornos(texto)
    """
    return len(_PATRON_RETORNO.findall(asm))


def contar_instrucciones(asm: str) -> int:
    """
    Cuenta las instrucciones de un ensamblador generado por el particionador.

    Contexto:
        ``asm-differ`` descarta lo que pasa de ``--max-lines`` instrucciones y puntua solo lo que
        queda; ``diff`` usa este numero para que el limite cubra la funcion entera.

    Args:
        asm (str): Contenido del ``.s`` de la funcion objetivo.

    Returns:
        int: Numero de instrucciones, incluidas las de los huecos de salto (0 si no hay ninguna).

    Ejemplo:
        total = contar_instrucciones(texto)
    """
    return len(_PATRON_INSTRUCCION.findall(asm))


def limite_lineas(instrucciones: int) -> int:
    """
    Calcula el ``--max-lines`` de ``asm-differ`` para una funcion de ``instrucciones`` instrucciones.

    Contexto:
        El candidato puede ser algo mas largo que el original; el margen evita que el corte caiga
        justo en su ultima instruccion. Nunca baja del limite por omision de la herramienta, para
        que las funciones pequenas se comporten como antes.

    Args:
        instrucciones (int): Instrucciones del original (no negativo).

    Returns:
        int: Instrucciones mas el margen, y como minimo ``LIMITE_MINIMO_LINEAS``.

    Raises:
        ValueError: Si ``instrucciones`` es negativo.

    Ejemplo:
        limite = limite_lineas(4971)
    """
    if instrucciones < 0:
        raise ValueError("el numero de instrucciones no puede ser negativo")
    return max(LIMITE_MINIMO_LINEAS, instrucciones + MARGEN_LINEAS)


def envoltorio_objetivo(ruta_asm: str) -> str:
    """
    Genera el ensamblador que envuelve el ``.s`` de una funcion para producir un objeto.

    Contexto:
        Los ``.s`` del particionador usan las macros ``glabel``/``endlabel`` y suponen ``$at``
        manual y huecos de salto rellenados a mano, igual que ``INCLUDE_ASM``.

    Args:
        ruta_asm (str): Ruta relativa a la raiz del repositorio del ``.s`` de la funcion.

    Returns:
        str: Texto del ensamblador envoltorio.

    Ejemplo:
        texto = envoltorio_objetivo("asm/matchings/a/func_X.s")
    """
    return f'.include "macro.inc"\n.section .text\n.set noat\n.set noreorder\n.include "{ruta_asm}"\n'


def texto_diff_settings(objdump: Path) -> str:
    """
    Genera el ``diff_settings.py`` que ``asm-differ`` exige en su directorio de trabajo.

    Contexto:
        ``asm-differ`` importa ese modulo del directorio actual. Se genera en ``build/diff/`` con
        la ruta de ``objdump`` resuelta en ese momento, de modo que el repositorio no contiene
        rutas de ninguna maquina.

    Args:
        objdump (Path): Ruta de ``mipsel-none-elf-objdump``.

    Returns:
        str: Codigo Python del modulo.

    Ejemplo:
        texto = texto_diff_settings(Path("objdump.exe"))
    """
    return (
        "def apply(config, args):\n"
        '    config["arch"] = "mipsel"\n'
        '    config["baseimg"] = "objetivo.bin"\n'
        '    config["myimg"] = "candidato.bin"\n'
        '    config["mapfile"] = "ninguno.map"\n'
        f'    config["objdump_executable"] = {json.dumps(str(objdump))}\n'
    )


def comando_diff(
    python: str,
    script: Path,
    candidato: str,
    objetivo: str,
    funcion: str,
    *,
    retornos: int,
    formato: str,
    max_lineas: int = LIMITE_MINIMO_LINEAS,
) -> list[str]:
    """
    Devuelve los argumentos que ejecutan ``asm-differ`` sobre dos objetos.

    Contexto:
        El comando se ejecuta con el directorio de trabajo en ``build/diff/``, por eso los
        objetos se pasan por nombre.

    Args:
        python (str): Interprete.
        script (Path): Ruta de ``diff.py`` de ``asm-differ``.
        candidato (str): Objeto compilado desde C.
        objetivo (str): Objeto ensamblado desde el asm original.
        funcion (str): Funcion a comparar.
        retornos (int): Retornos tras los cuales se corta el desensamblado (al menos 1).
        formato (str): ``json`` o ``plain``.
        max_lineas (int, opcional): Instrucciones que ``asm-differ`` compara como maximo; por
            omision, el limite de la herramienta.

    Returns:
        list[str]: Lista de argumentos.

    Raises:
        ValueError: Si el formato no es ``json`` ni ``plain``, o ``max_lineas`` no es positivo.

    Ejemplo:
        comando = comando_diff("python", Path("diff.py"), "c.o", "t.o", "func_X", retornos=1, formato="json")
    """
    if formato not in ("json", "plain"):
        raise ValueError("el formato debe ser 'json' o 'plain'")
    if max_lineas < 1:
        raise ValueError("el limite de lineas debe ser positivo")
    return [
        python,
        str(script),
        "-o",
        "--file",
        candidato,
        "--ref-file",
        objetivo,
        "--no-pager",
        f"--max-lines={max_lineas}",
        f"--format={formato}",
        *(["-s"] * max(1, retornos)),
        funcion,
    ]


def puntuacion_desde_json(salida: str) -> int:
    """
    Lee la puntuacion de la salida JSON de ``asm-differ``.

    Contexto:
        La salida de otro programa es una entrada no confiable: se exige la forma esperada.

    Args:
        salida (str): Texto JSON producido con ``--format=json``.

    Returns:
        int: Puntuacion (``current_score``).

    Raises:
        ValueError: Si no es JSON, no es un objeto o ``current_score`` no es un entero no negativo.

    Ejemplo:
        puntos = puntuacion_desde_json('{"current_score": 0}')
    """
    try:
        datos = json.loads(salida)
    except ValueError:
        raise ValueError("asm-differ no devolvio JSON valido") from None
    puntos = datos.get("current_score") if isinstance(datos, dict) else None
    if isinstance(puntos, bool) or not isinstance(puntos, int) or puntos < 0:
        raise ValueError("asm-differ no informo una puntuacion valida")
    return puntos


def elegir_asm_objetivo(archivo: str, funcion: str, existe: Callable[[str], bool]) -> str:
    """
    Elige el ``.s`` original de una funcion.

    Contexto:
        Una funcion ya escrita en C tiene su asm original en ``asm/matchings/`` (lo genera el
        particionador al estar activada la opcion de desensamblarlo todo); una que sigue en
        ``INCLUDE_ASM`` lo tiene en ``asm/nonmatchings/``.

    Args:
        archivo (str): Archivo C de la funcion (``src/<segmento>.c``).
        funcion (str): Nombre de la funcion.
        existe (Callable[[str], bool]): Indica si una ruta relativa existe.

    Returns:
        str: Ruta relativa del ``.s``.

    Raises:
        FileNotFoundError: Si no existe en ninguna de las dos carpetas.

    Ejemplo:
        ruta = elegir_asm_objetivo("src/code_80032874.c", "func_80036204", existe)
    """
    segmento = Path(archivo).stem
    for carpeta in (CARPETA_ASM_COINCIDENTE, CARPETA_ASM_PENDIENTE):
        ruta = f"{carpeta}/{segmento}/{funcion}.s"
        if existe(ruta):
            return ruta
    raise FileNotFoundError(f"no existe el asm original de '{funcion}': ejecute primero 'split'")


def comparar_funcion(
    raiz: Path,
    funcion: str,
    herramientas: HerramientasCompilacion,
    script_diff: Path,
    ejecutar: Ejecutor,
) -> ResultadoDiff:
    """
    Compara una funcion compilada desde C con su objetivo original.

    Contexto:
        Implementa ``diff``. Todo lo que genera va a ``build/diff/``, que ``clean`` elimina.

    Args:
        raiz (Path): Raiz del repositorio.
        funcion (str): Nombre de la funcion.
        herramientas (HerramientasCompilacion): Herramientas de compilacion.
        script_diff (Path): Ruta de ``diff.py`` de ``asm-differ``.
        ejecutar (Ejecutor): Ejecutor de procesos.

    Returns:
        ResultadoDiff: Puntuacion y diferencias.

    Raises:
        ValueError: Si el nombre no es valido, la funcion no figura en ``src/`` o la salida de
            ``asm-differ`` no tiene la forma esperada.
        FuncionSinCError: Si la funcion sigue solo en ``INCLUDE_ASM``.
        FileNotFoundError: Si falta el asm original (hay que ejecutar ``split``).
        ProcesoError: Si una herramienta falla.

    Ejemplo:
        resultado = comparar_funcion(Path("."), "func_80036204", herramientas, script, ejecutar)
    """
    validar_funcion(funcion)
    textos = listar_fuentes_c(raiz)
    estados = fuentes_c.analizar_fuentes(textos)
    archivo, estado = fuentes_c.ubicar_funcion(estados, funcion)
    if estado is EstadoFuncion.ENSAMBLADOR:
        raise FuncionSinCError(
            f"'{funcion}' sigue en INCLUDE_ASM: escriba su C (bajo NON_MATCHING si aun no coincide)"
        )
    objetivo, retornos, max_lineas = preparar_objetivo(raiz, funcion, archivo, herramientas, ejecutar)
    candidato = f"{CARPETA_DIFF}/{Path(archivo).name}.o"
    compilar_fuente(
        raiz,
        archivo,
        candidato,
        herramientas,
        ejecutar,
        definiciones=(fuentes_c.MACRO_NO_COINCIDENTE,),
        exigir_solo_texto=False,
        valor_g=leer_valores_g(raiz).get(Path(archivo).stem, 0),
    )

    def lanzar(formato: str) -> str:
        return puntuar_objeto(
            raiz,
            herramientas,
            script_diff,
            ejecutar,
            candidato=candidato,
            objetivo=objetivo,
            funcion=funcion,
            retornos=retornos,
            max_lineas=max_lineas,
            formato=formato,
        )

    puntuacion = puntuacion_desde_json(lanzar("json"))
    texto = lanzar("plain").rstrip("\n")
    iguales = None
    referencias = 0
    direccion = leer_direcciones_de_funciones(raiz).get(funcion)
    if puntuacion != 0 and direccion is not None:
        iguales = bytes_coinciden(
            raiz,
            herramientas,
            ejecutar,
            funcion=funcion,
            direccion=direccion,
            candidato=candidato,
            objetivo=objetivo,
        )
        referencias = contar_referencias_numericas(texto) if iguales else 0
    informada = 0 if iguales else puntuacion
    return ResultadoDiff(funcion, archivo, informada, texto, iguales, referencias, puntuacion)


def preparar_objetivo(
    raiz: Path, funcion: str, archivo: str, herramientas: HerramientasCompilacion, ejecutar: Ejecutor
) -> tuple[str, int, int]:
    """
    Ensambla el asm original de una funcion como objetivo de comparacion.

    Contexto:
        Primer paso comun de ``diff`` y de ``probar``: el objetivo se genera una vez y se
        compara contra uno o muchos candidatos.

    Args:
        raiz (Path): Raiz del repositorio.
        funcion (str): Nombre de la funcion (ya validado).
        archivo (str): Archivo C que la contiene (``src/<segmento>.c``).
        herramientas (HerramientasCompilacion): Herramientas de compilacion.
        ejecutar (Ejecutor): Ejecutor de procesos.

    Returns:
        tuple[str, int, int]: Ruta relativa del objeto objetivo, numero de ``jr $ra`` del original y
        limite de lineas de ``asm-differ`` que cubre la funcion entera.

    Raises:
        FileNotFoundError: Si falta el asm original (hay que ejecutar ``split``).
        ProcesoError: Si el ensamblador falla.

    Ejemplo:
        objetivo, retornos, max_lineas = preparar_objetivo(Path("."), "func_80036204", "src/a.c", herramientas, ejecutar)
    """
    ruta_asm = elegir_asm_objetivo(archivo, funcion, lambda ruta: (raiz / ruta).is_file())
    asm = (raiz / ruta_asm).read_text(encoding="utf-8")
    retornos = contar_retornos(asm)
    max_lineas = limite_lineas(contar_instrucciones(asm))
    (raiz / CARPETA_DIFF).mkdir(parents=True, exist_ok=True)
    envoltorio = f"{CARPETA_DIFF}/{funcion}.objetivo.s"
    objetivo = f"{CARPETA_DIFF}/{funcion}.objetivo.o"
    (raiz / envoltorio).write_text(envoltorio_objetivo(ruta_asm), encoding="utf-8", newline="\n")
    ejecutar(
        dominio.comando_ensamblar(herramientas.ensamblador, envoltorio, objetivo, CARPETA_MACROS),
        raiz,
        TIMEOUT_DIFF_S,
    )
    return objetivo, retornos, max_lineas


def puntuar_objeto(
    raiz: Path,
    herramientas: HerramientasCompilacion,
    script_diff: Path,
    ejecutar: Ejecutor,
    *,
    candidato: str,
    objetivo: str,
    funcion: str,
    retornos: int,
    max_lineas: int,
    formato: str,
) -> str:
    """
    Ejecuta ``asm-differ`` sobre un objeto candidato y el objetivo.

    Contexto:
        Se ejecuta dentro de ``build/diff/`` porque ``asm-differ`` importa ``diff_settings.py``
        del directorio de trabajo; este se genera aqui con la ruta de ``objdump`` resuelta.

    Args:
        raiz (Path): Raiz del repositorio.
        herramientas (HerramientasCompilacion): Herramientas de compilacion.
        script_diff (Path): Ruta de ``diff.py`` de ``asm-differ``.
        ejecutar (Ejecutor): Ejecutor de procesos.
        candidato (str): Objeto candidato (ruta relativa a la raiz, dentro de ``build/diff/``).
        objetivo (str): Objeto objetivo (idem).
        funcion (str): Funcion a comparar.
        retornos (int): Retornos tras los cuales se corta el desensamblado.
        max_lineas (int): Instrucciones que ``asm-differ`` compara como maximo (ver ``limite_lineas``).
        formato (str): ``json`` o ``plain``.

    Returns:
        str: Salida de ``asm-differ``.

    Raises:
        ValueError: Si el formato no es valido.
        ProcesoError: Si ``asm-differ`` falla.

    Ejemplo:
        salida = puntuar_objeto(Path("."), herramientas, script, ejecutar, candidato=c, objetivo=t,
            funcion="f", retornos=1, max_lineas=1024, formato="json")
    """
    carpeta = raiz / CARPETA_DIFF
    (carpeta / "diff_settings.py").write_text(
        texto_diff_settings(herramientas.objdump), encoding="utf-8", newline="\n"
    )
    comando = comando_diff(
        herramientas.python,
        script_diff,
        Path(candidato).name,
        Path(objetivo).name,
        funcion,
        retornos=retornos,
        formato=formato,
        max_lineas=max_lineas,
    )
    return ejecutar(comando, carpeta, TIMEOUT_DIFF_S)

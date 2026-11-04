"""Comparacion de una funcion compilada contra su objetivo original con ``asm-differ``.

La orden ``diff <funcion>`` del proyecto hace tres cosas: compila el archivo C que contiene la
funcion (con ``NON_MATCHING`` definida, para ver tambien los intentos que la construccion normal
no usa), ensambla el asm original de la funcion como objetivo y ejecuta ``asm-differ`` sobre
ambos objetos. La puntuacion 0 significa que las instrucciones y los simbolos coinciden o que,
tras enlazar, los bytes de la funcion son los del original aunque ``asm-differ`` puntue la forma
simbolica frente a la numerica de una referencia (esa puntuacion queda en ``puntuacion_asm``).

Una funcion que sigue en ``INCLUDE_ASM`` no se compara: el objeto candidato contendria el mismo
ensamblador que el objetivo y la puntuacion 0 seria una coincidencia falsa.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from psxdecomp.construccion import dominio
from psxdecomp.construccion.compilacion import HerramientasCompilacion, compilar_fuente
from psxdecomp.construccion.infraestructura import (
    Ejecutor,
    leer_direcciones_de_funciones,
    leer_valores_g,
    listar_fuentes_c,
)
from psxdecomp.construccion.salidas import SUBCARPETA_DIFF as _SUBCARPETA_DIFF
from psxdecomp.construccion.salidas import calcular_salidas
from psxdecomp.diff import fuentes_c
from psxdecomp.diff.enlace_diff import bytes_coinciden, contar_referencias_numericas
from psxdecomp.diff.fuentes_c import EstadoFuncion
from psxdecomp.dominio import Compilacion, Convenciones, Rutas

TIMEOUT_DIFF_S = 300
LIMITE_MINIMO_LINEAS = 1024
MARGEN_LINEAS = 64
"""Instrucciones que se suman a las del original para fijar el limite de ``asm-differ``.

Cubre el caso en que el candidato en C es mas largo que el original. Medido con la carpeta de trabajo
de la comparacion en 93 funciones de un proyecto real (30 ya cerradas en C, repartidas por tamano de 2
a 198 instrucciones, y las 63 pendientes, de 12 a 4971): en las cerradas el candidato nunca supera al
original (rango -3 a 0); en las pendientes la diferencia va de -405 a +41 instrucciones (mediana -1,
percentil 90 en +4, percentil 99 y maximo en +41; las tres mayores: +41, +24 y +14). El menor
margen que lo cubre todo es 41; se redondea hacia arriba a la potencia de 2 siguiente, 64, que deja
23 instrucciones de holgura. Si un intento temprano aun asi lo supera, ``diff`` lo detecta y lo
avisa (ver ``salida_truncada``) en lugar de informar una puntuacion parcial sin decirlo.
"""
_PATRON_FUNCION = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_PATRON_RETORNO = re.compile(r"^\s*/\*.*?\*/\s+jr\s+\$ra\b", re.MULTILINE)
_PATRON_INSTRUCCION = re.compile(r"^\s*/\*.*?\*/\s+[A-Za-z.]", re.MULTILINE)
_MNEMONICOS_NO_INSTRUCCION = frozenset({"<label>", "<data-ref>", "ERROR"})
_MNEMONICO_CORTE = "..."


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
            si no se pudo comparar o la puntuacion ya era cero sin truncado).
        referencias_numericas: Filas cuya unica diferencia es una referencia escrita como numero.
        puntuacion_asm: Puntuacion que dio ``asm-differ`` antes de comparar los bytes (``None`` si
            no se registro).
        truncado: Si ``asm-differ`` corto el desensamblado del candidato en el limite de lineas, de
            modo que la puntuacion y el texto son parciales.
    """

    funcion: str
    archivo: str
    puntuacion: int
    texto: str
    bytes_iguales: bool | None = None
    referencias_numericas: int = 0
    puntuacion_asm: int | None = None
    truncado: bool = False

    @property
    def coincide(self) -> bool:
        """
        Verdadero si los bytes enlazados son iguales o si la medicion es completa y puntua cero.

        Una medicion truncada solo cubre una ventana del candidato: su puntuacion cero no basta, y
        solo el enlace byte a byte de la funcion completa puede darla por coincidente.
        """
        return self.bytes_iguales is True or (not self.truncado and self.puntuacion == 0)


class FuncionSinCError(ValueError):
    """La funcion existe pero todavia no tiene C que comparar."""


def validar_funcion(nombre: str) -> str:
    """
    Valida el nombre de una funcion recibido por linea de ordenes.

    Contexto:
        El nombre termina formando rutas (``<asm_pendiente>/<archivo>/<nombre>.s``) y argumentos
        de procesos: solo se aceptan identificadores C razonables.

    Args:
        nombre (str): Nombre pedido por el usuario.

    Returns:
        str: El mismo nombre, validado.

    Raises:
        ValueError: Si no es un identificador de hasta 64 caracteres.

    Ejemplo:
        funcion = validar_funcion("rutina_a")
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
        texto = envoltorio_objetivo("ensamblador/cerradas/a/rutina_a.s")
    """
    return f'.include "macro.inc"\n.section .text\n.set noat\n.set noreorder\n.include "{ruta_asm}"\n'


def texto_diff_settings(objdump: Path) -> str:
    """
    Genera el ``diff_settings.py`` que ``asm-differ`` exige en su directorio de trabajo.

    Contexto:
        ``asm-differ`` importa ese modulo del directorio actual. Se genera en la carpeta de trabajo con
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
        El comando se ejecuta con el directorio de trabajo en la carpeta de la comparacion, por eso los
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
        comando = comando_diff(
            "python", Path("diff.py"), "c.o", "t.o", "rutina_a", retornos=1, formato="json"
        )
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


def salida_truncada(salida: str, max_lineas: int) -> bool:
    """
    Indica si ``asm-differ`` corto el desensamblado del candidato en el limite de lineas.

    Contexto:
        Si el candidato supera ``--max-lines`` instrucciones, ``asm-differ`` descarta el resto y
        puntua solo lo que queda, sin avisar. ``comparar_funcion`` usa esta comprobacion para
        anotar el resultado en lugar de dar una cifra parcial por completa. El corte se reconoce
        por la fila ``...`` que ``asm-differ`` anade, o porque el candidato ya llega al limite.

    Args:
        salida (str): Texto JSON producido con ``--format=json`` (ya validado por
            ``puntuacion_desde_json``).
        max_lineas (int): Limite con que se lanzo ``asm-differ``.

    Returns:
        bool: Verdadero si hubo corte; falso si no, o si las filas no tienen la forma esperada.

    Ejemplo:
        truncado = salida_truncada(salida_json, 1024)
    """
    filas = json.loads(salida).get("rows")
    if not isinstance(filas, list):
        return False
    instrucciones = 0
    for fila in filas:
        columna = fila.get("current") if isinstance(fila, dict) else None
        mnemonico = columna.get("mnemonic") if isinstance(columna, dict) else None
        if mnemonico == _MNEMONICO_CORTE:
            return True
        if isinstance(mnemonico, str) and mnemonico not in _MNEMONICOS_NO_INSTRUCCION:
            instrucciones += 1
    return instrucciones >= max_lineas


def elegir_asm_objetivo(archivo: str, funcion: str, existe: Callable[[str], bool], *, rutas: Rutas) -> str:
    """
    Elige el ``.s`` original de una funcion.

    Contexto:
        Una funcion ya escrita en C tiene su asm original en ``rutas.asm_coincidente`` (lo genera el
        particionador al estar activada la opcion de desensamblarlo todo); una que sigue en
        ensamblador lo tiene en ``rutas.asm_pendiente``.

    Args:
        archivo (str): Archivo C de la funcion (``<fuentes>/<segmento>.c``).
        funcion (str): Nombre de la funcion.
        existe (Callable[[str], bool]): Indica si una ruta relativa existe.
        rutas (Rutas): Seccion ``[rutas]``: carpetas del ensamblador original.

    Returns:
        str: Ruta relativa del ``.s``.

    Raises:
        FileNotFoundError: Si no existe en ninguna de las dos carpetas.

    Ejemplo:
        ruta = elegir_asm_objetivo("codigo/modulo_a.c", "rutina_a", existe, rutas=rutas)
    """
    segmento = Path(archivo).stem
    for carpeta in (rutas.asm_coincidente, rutas.asm_pendiente):
        ruta = f"{carpeta}/{segmento}/{funcion}.s"
        if existe(ruta):
            return ruta
    raise FileNotFoundError(f"no existe el asm original de '{funcion}': ejecute primero 'split'")


@contextlib.contextmanager
def carpeta_de_trabajo(raiz: Path, etiqueta: str, *, rutas: Rutas) -> Iterator[str]:
    """
    Crea una carpeta de trabajo exclusiva dentro de la carpeta de la comparacion y la elimina al terminar.

    Contexto:
        ``diff`` y ``probar`` generan objetos, enlaces y ``diff_settings.py`` con nombres que
        dependen del archivo C o de la variante, no de quien los pide: dos ejecuciones
        concurrentes sobre funciones del mismo archivo se pisarian el objeto candidato y una leeria
        el resultado de la otra. Cada ejecucion trabaja en su propia carpeta, con el PID y un
        sufijo aleatorio (el PID solo no basta si dos comparaciones corren en hilos del mismo
        proceso).

    Args:
        raiz (Path): Raiz del repositorio.
        etiqueta (str): Nombre que identifica la ejecucion (la funcion); forma parte del nombre.
        rutas (Rutas): Seccion ``[rutas]``; la carpeta de la comparacion es ``<build>/diff``.

    Yields:
        str: Ruta de la carpeta relativa a la raiz, con barras normales.

    Raises:
        OSError: Si no se puede crear la carpeta.

    Ejemplo:
        with carpeta_de_trabajo(Path("."), "rutina_a", rutas=rutas) as carpeta:
            candidato = f"{carpeta}/code_a.c.o"
    """
    carpeta_diff = f"{rutas.build}/{_SUBCARPETA_DIFF}"
    base = raiz / carpeta_diff
    base.mkdir(parents=True, exist_ok=True)
    creada = Path(tempfile.mkdtemp(prefix=f"{etiqueta}-{os.getpid()}-", dir=base))
    try:
        yield f"{carpeta_diff}/{creada.name}"
    finally:
        shutil.rmtree(creada, ignore_errors=True)


def comparar_funcion(
    raiz: Path,
    funcion: str,
    herramientas: HerramientasCompilacion,
    script_diff: Path,
    ejecutar: Ejecutor,
    *,
    rutas: Rutas,
    convenciones: Convenciones,
    compilacion: Compilacion,
    nombre_ejecutable: str,
) -> ResultadoDiff:
    """
    Compara una funcion compilada desde C con su objetivo original.

    Contexto:
        Implementa ``diff``. Los intermedios van a una carpeta exclusiva de la ejecucion dentro de
        ``<build>/diff/`` (ver ``carpeta_de_trabajo``), que se elimina al terminar; solo la puntuacion
        queda en ``<build>/diff/<funcion>.resultado.json``, escrita de forma atomica.

    Args:
        raiz (Path): Raiz del repositorio.
        funcion (str): Nombre de la funcion.
        herramientas (HerramientasCompilacion): Herramientas de compilacion.
        script_diff (Path): Ruta de ``diff.py`` de ``asm-differ``.
        ejecutar (Ejecutor): Ejecutor de procesos.
        rutas (Rutas): Seccion ``[rutas]`` del manifiesto.
        convenciones (Convenciones): Seccion ``[convenciones]`` (macros y formato de simbolos).
        compilacion (Compilacion): Seccion ``[compilacion]`` (version de ``ASPSX`` y opciones).
        nombre_ejecutable (str): Nombre del ejecutable reconstruido; fija el ELF contra el que se
            resuelven los simbolos al comparar por bytes.

    Returns:
        ResultadoDiff: Puntuacion y diferencias.

    Raises:
        ValueError: Si el nombre no es valido, la funcion no figura en la carpeta de fuentes o la
            salida de ``asm-differ`` no tiene la forma esperada.
        FuncionSinCError: Si la funcion sigue solo en ensamblador.
        FileNotFoundError: Si falta el asm original (hay que ejecutar ``split``).
        ProcesoError: Si una herramienta falla.

    Ejemplo:
        resultado = comparar_funcion(
            Path("."), "rutina_a", herramientas, script, ejecutar,
            rutas=rutas, convenciones=convenciones, compilacion=compilacion,
            nombre_ejecutable="EJEC_001.00",
        )
    """
    validar_funcion(funcion)
    textos = listar_fuentes_c(raiz, rutas=rutas)
    estados = fuentes_c.analizar_fuentes(textos, convenciones)
    archivo, estado = fuentes_c.ubicar_funcion(estados, funcion, rutas.fuentes)
    if estado is EstadoFuncion.ENSAMBLADOR:
        raise FuncionSinCError(
            f"'{funcion}' sigue en {convenciones.macro_ensamblador}: escriba su C "
            f"(bajo {convenciones.macro_no_coincidente} si aun no coincide)"
        )
    with carpeta_de_trabajo(raiz, funcion, rutas=rutas) as carpeta:
        return _comparar_en(
            raiz,
            funcion,
            archivo=archivo,
            carpeta=carpeta,
            herramientas=herramientas,
            script_diff=script_diff,
            ejecutar=ejecutar,
            rutas=rutas,
            convenciones=convenciones,
            compilacion=compilacion,
            nombre_ejecutable=nombre_ejecutable,
        )


def _comparar_en(
    raiz: Path,
    funcion: str,
    *,
    archivo: str,
    carpeta: str,
    herramientas: HerramientasCompilacion,
    script_diff: Path,
    ejecutar: Ejecutor,
    rutas: Rutas,
    convenciones: Convenciones,
    compilacion: Compilacion,
    nombre_ejecutable: str,
) -> ResultadoDiff:
    """Compila el candidato y puntua la funcion dentro de la carpeta de trabajo ya creada."""
    objetivo, retornos, max_lineas = preparar_objetivo(
        raiz, funcion, archivo, herramientas, ejecutar, carpeta=carpeta, rutas=rutas
    )
    candidato = f"{carpeta}/{Path(archivo).name}.o"
    compilar_fuente(
        raiz,
        archivo,
        candidato,
        herramientas,
        ejecutar,
        definiciones=(convenciones.macro_no_coincidente,),
        exigir_solo_texto=False,
        valor_g=leer_valores_g(raiz, rutas=rutas, convenciones=convenciones).get(Path(archivo).stem, 0),
        rutas=rutas,
        convenciones=convenciones,
        compilacion=compilacion,
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

    salida_json = lanzar("json")
    puntuacion = puntuacion_desde_json(salida_json)
    truncado = salida_truncada(salida_json, max_lineas)
    texto = lanzar("plain").rstrip("\n")
    iguales = None
    referencias = 0
    direccion = leer_direcciones_de_funciones(raiz, rutas=rutas, convenciones=convenciones).get(funcion)
    # Una medicion truncada solo cubre una ventana del candidato: aunque puntue 0, el enlace byte a
    # byte de la funcion completa es la unica prueba definitiva de que la cola tambien coincide.
    if (puntuacion != 0 or truncado) and direccion is not None:
        iguales = bytes_coinciden(
            raiz,
            herramientas,
            ejecutar,
            funcion=funcion,
            direccion=direccion,
            candidato=candidato,
            objetivo=objetivo,
            elf=calcular_salidas(nombre_ejecutable, rutas).elf,
        )
        referencias = contar_referencias_numericas(texto) if iguales else 0
    informada = 0 if iguales else puntuacion
    guardar_resultado(raiz, funcion, informada, max_lineas, truncado=truncado, rutas=rutas)
    return ResultadoDiff(funcion, archivo, informada, texto, iguales, referencias, puntuacion, truncado)


def ruta_resultado(funcion: str, *, rutas: Rutas) -> str:
    """
    Da la ruta, relativa a la raiz, donde ``diff`` deja la ultima puntuacion de una funcion.

    Contexto:
        La comparten ``diff`` (que la escribe) y el aviso de ``progreso`` (que la lee).

    Args:
        funcion (str): Nombre de la funcion (ya validado).
        rutas (Rutas): Seccion ``[rutas]``; el resultado vive en ``<build>/diff``.

    Returns:
        str: Ruta dentro de la carpeta de la comparacion.

    Ejemplo:
        ruta = ruta_resultado("rutina_a", rutas=rutas)
    """
    return f"{rutas.build}/{_SUBCARPETA_DIFF}/{funcion}.resultado.json"


def guardar_resultado(
    raiz: Path, funcion: str, puntuacion: int, max_lineas: int, *, rutas: Rutas, truncado: bool = False
) -> None:
    """
    Registra la puntuacion informada por ``diff`` para que otras ordenes la contrasten sin repetirlo.

    Contexto:
        ``progreso`` compara con ella la cifra del comentario de pendiente de cada intento no coincidente.
        Vive en la carpeta de la comparacion, que ``clean`` elimina, y no se versiona. Se escribe a un archivo
        temporal de la misma carpeta y se renombra sobre el destino: un lector concurrente ve el
        resultado anterior completo o el nuevo completo, nunca uno a medias.

    Args:
        raiz (Path): Raiz del repositorio.
        funcion (str): Funcion comparada.
        puntuacion (int): Puntuacion informada.
        max_lineas (int): Limite de lineas con que se midio.
        rutas (Rutas): Seccion ``[rutas]`` del manifiesto.
        truncado (bool, opcional): Si la medicion es parcial porque ``asm-differ`` corto el
            candidato en el limite.

    Ejemplo:
        guardar_resultado(Path("."), "rutina_a", 0, 1024, rutas=rutas)
    """
    datos = {"funcion": funcion, "puntuacion": puntuacion, "maxLineas": max_lineas, "truncado": truncado}
    destino = raiz / ruta_resultado(funcion, rutas=rutas)
    destino.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporal = tempfile.mkstemp(prefix=f"{funcion}.", suffix=".tmp", dir=destino.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as salida:
            salida.write(json.dumps(datos) + "\n")
        os.replace(temporal, destino)
    except BaseException:
        Path(temporal).unlink(missing_ok=True)
        raise


def preparar_objetivo(
    raiz: Path,
    funcion: str,
    archivo: str,
    herramientas: HerramientasCompilacion,
    ejecutar: Ejecutor,
    *,
    carpeta: str,
    rutas: Rutas,
) -> tuple[str, int, int]:
    """
    Ensambla el asm original de una funcion como objetivo de comparacion.

    Contexto:
        Primer paso comun de ``diff`` y de ``probar``: el objetivo se genera una vez y se
        compara contra uno o muchos candidatos.

    Args:
        raiz (Path): Raiz del repositorio.
        funcion (str): Nombre de la funcion (ya validado).
        archivo (str): Archivo C que la contiene (``<fuentes>/<segmento>.c``).
        herramientas (HerramientasCompilacion): Herramientas de compilacion.
        ejecutar (Ejecutor): Ejecutor de procesos.
        carpeta (str): Carpeta de trabajo de la ejecucion, relativa a la raiz (ver
            ``carpeta_de_trabajo``); recibe el envoltorio y el objeto objetivo.
        rutas (Rutas): Seccion ``[rutas]``: carpetas del ensamblador original y de macros.

    Returns:
        tuple[str, int, int]: Ruta relativa del objeto objetivo, numero de ``jr $ra`` del original y
        limite de lineas de ``asm-differ`` que cubre la funcion entera.

    Raises:
        FileNotFoundError: Si falta el asm original (hay que ejecutar ``split``).
        ProcesoError: Si el ensamblador falla.

    Ejemplo:
        objetivo, retornos, lineas = preparar_objetivo(
            Path("."), "f", "codigo/a.c", herramientas, ejecutar, carpeta="salida/diff/f-1-x", rutas=rutas
        )
    """
    ruta_asm = elegir_asm_objetivo(archivo, funcion, lambda ruta: (raiz / ruta).is_file(), rutas=rutas)
    asm = (raiz / ruta_asm).read_text(encoding="utf-8")
    retornos = contar_retornos(asm)
    max_lineas = limite_lineas(contar_instrucciones(asm))
    (raiz / carpeta).mkdir(parents=True, exist_ok=True)
    envoltorio = f"{carpeta}/{funcion}.objetivo.s"
    objetivo = f"{carpeta}/{funcion}.objetivo.o"
    (raiz / envoltorio).write_text(envoltorio_objetivo(ruta_asm), encoding="utf-8", newline="\n")
    ejecutar(
        dominio.comando_ensamblar(herramientas.ensamblador, envoltorio, objetivo, rutas.macros),
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
        Se ejecuta dentro de la carpeta de trabajo del candidato (la de ``carpeta_de_trabajo``)
        porque ``asm-differ`` importa ``diff_settings.py`` del directorio de trabajo; este se
        genera aqui con la ruta de ``objdump`` resuelta.

    Args:
        raiz (Path): Raiz del repositorio.
        herramientas (HerramientasCompilacion): Herramientas de compilacion.
        script_diff (Path): Ruta de ``diff.py`` de ``asm-differ``.
        ejecutar (Ejecutor): Ejecutor de procesos.
        candidato (str): Objeto candidato (ruta relativa a la raiz, dentro de su carpeta de trabajo).
        objetivo (str): Objeto objetivo (en la misma carpeta).
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
    carpeta = raiz / PurePosixPath(candidato).parent
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

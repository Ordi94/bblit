"""Banco de variantes: compara muchas formulaciones en C de una funcion contra su original.

``python tools/build.py probar <funcion> <carpeta>`` toma cada ``.c`` de la carpeta como una
variante completa de la funcion (con sus ``#include``, tipos y declaraciones externas), la compila
con la cadena real del proyecto, la compara con ``asm-differ`` contra el ensamblador original y
muestra una tabla ordenada de variante a puntuacion. No escribe en ``src/``: todo el trabajo queda
en ``build/diff/``. Sirve para decidir que formulacion escribir en ``src/`` antes de usar ``diff``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from tools.reconstruccion import fuentes_c
from tools.reconstruccion.compilacion import HerramientasCompilacion, compilar_archivo
from tools.reconstruccion.diff import (
    preparar_objetivo,
    puntuacion_desde_json,
    puntuar_objeto,
    validar_funcion,
)
from tools.reconstruccion.enlace_diff import TIMEOUT_ENLACE_S, bytes_coinciden, funcion_en_objeto
from tools.reconstruccion.infraestructura import (
    CARPETA_DIFF,
    Ejecutor,
    ProcesoError,
    leer_direcciones_de_funciones,
    leer_valores_g,
    listar_fuentes_c,
)

MAX_VARIANTES = 200
MAX_BYTES_VARIANTE = 256 * 1024
MAX_CARACTERES_ERROR = 120
_PATRON_VARIANTE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}\.c$")


@dataclass(frozen=True)
class ResultadoVariante:
    """Resultado de compilar y comparar una variante.

    Attributes:
        nombre: Nombre del archivo de la variante.
        puntuacion: Puntuacion de ``asm-differ`` (0 es coincidencia exacta); ``None`` si fallo.
        error: Primera linea del error si la variante no compilo o no se pudo comparar.
        bytes_iguales: Si los bytes enlazados de la funcion coinciden con los del original aunque la
            puntuacion no sea cero (``None`` si no se pudo comparar).
    """

    nombre: str
    puntuacion: int | None
    error: str | None = None
    bytes_iguales: bool | None = None

    @property
    def coincide(self) -> bool:
        """Verdadero si la puntuacion es cero o los bytes enlazados son iguales."""
        return self.puntuacion == 0 or self.bytes_iguales is True


def listar_variantes(carpeta: Path) -> list[Path]:
    """
    Lista los archivos ``.c`` de una carpeta de variantes, validando cantidad, nombre y tamano.

    Contexto:
        La carpeta la indica el usuario: se acota todo lo que se va a compilar. Solo se leen
        los ``.c`` del primer nivel; los nombres deben ser simples porque forman parte de rutas
        de objetos y de argumentos de procesos.

    Args:
        carpeta (Path): Carpeta con las variantes.

    Returns:
        list[Path]: Rutas de las variantes, ordenadas por nombre.

    Raises:
        FileNotFoundError: Si la carpeta no existe.
        ValueError: Si no hay variantes, hay mas de ``MAX_VARIANTES``, un nombre no es simple o
            una variante excede ``MAX_BYTES_VARIANTE``.

    Ejemplo:
        variantes = listar_variantes(Path("variantes"))
    """
    if not carpeta.is_dir():
        raise FileNotFoundError("la carpeta de variantes no existe")
    archivos = sorted(p for p in carpeta.iterdir() if p.suffix == ".c" and p.is_file())
    if not archivos:
        raise ValueError("la carpeta de variantes no contiene archivos .c")
    if len(archivos) > MAX_VARIANTES:
        raise ValueError(f"hay mas de {MAX_VARIANTES} variantes")
    for archivo in archivos:
        if not _PATRON_VARIANTE.match(archivo.name):
            raise ValueError(f"nombre de variante no valido: '{archivo.name}'")
        if archivo.stat().st_size > MAX_BYTES_VARIANTE:
            raise ValueError(f"la variante '{archivo.name}' excede el tamano permitido")
    return archivos


def ordenar_resultados(resultados: list[ResultadoVariante]) -> list[ResultadoVariante]:
    """
    Ordena las variantes de menor a mayor puntuacion, dejando al final las que fallaron.

    Contexto:
        Primero va la mejor formulacion; a igual puntuacion, por nombre.

    Args:
        resultados (list[ResultadoVariante]): Resultados sin ordenar.

    Returns:
        list[ResultadoVariante]: Resultados ordenados.

    Ejemplo:
        ordenados = ordenar_resultados(resultados)
    """
    return sorted(
        resultados, key=lambda r: (r.puntuacion is None, not r.coincide, r.puntuacion or 0, r.nombre)
    )


def formatear_tabla(resultados: list[ResultadoVariante]) -> str:
    """
    Da forma de tabla de texto a los resultados ya ordenados.

    Contexto:
        Es lo que imprime ``probar``: una fila por variante con su puntuacion o su error.

    Args:
        resultados (list[ResultadoVariante]): Resultados (normalmente de ``ordenar_resultados``).

    Returns:
        str: Texto con cabecera y una fila por variante, sin salto de linea final.

    Ejemplo:
        print(formatear_tabla(ordenar_resultados(resultados)))
    """
    ancho = max([len("variante"), *(len(r.nombre) for r in resultados)])
    filas = [f"{'variante':<{ancho}}  puntuacion"]
    for r in resultados:
        valor = str(r.puntuacion) if r.puntuacion is not None else f"error: {r.error}"
        if r.bytes_iguales and r.puntuacion:
            valor += " (bytes iguales)"
        filas.append(f"{r.nombre:<{ancho}}  {valor}")
    return "\n".join(filas)


def _primera_linea(mensaje: str) -> str:
    """Primera linea no vacia de un mensaje, acotada para la tabla."""
    lineas = [linea.strip() for linea in mensaje.splitlines() if linea.strip()]
    return (lineas[0] if lineas else "fallo sin mensaje")[:MAX_CARACTERES_ERROR]


def _define_funcion(
    raiz: Path, herramientas: HerramientasCompilacion, ejecutar: Ejecutor, objeto: str, funcion: str
) -> bool:
    """
    Indica si un objeto compilado define la funcion pedida en ``.text``.

    Contexto:
        ``asm-differ`` compara lo que encuentre bajo el nombre pedido y, si el objeto no lo define,
        puntua el hueco contra el original con un numero alto pero valido. Sin esta comprobacion
        una variante vacia o de otra funcion pareceria una formulacion mediocre en lugar de un
        error. Se consulta la tabla de simbolos del objeto, que es la misma fuente que usa la
        comparacion por bytes.

    Args:
        raiz (Path): Raiz del repositorio.
        herramientas (HerramientasCompilacion): Herramientas de compilacion (``objdump``).
        ejecutar (Ejecutor): Ejecutor de procesos.
        objeto (str): Objeto compilado de la variante (ruta relativa a la raiz).
        funcion (str): Nombre de la funcion esperada.

    Returns:
        bool: ``True`` si el objeto define ``funcion`` en ``.text`` con tamano mayor que cero.

    Raises:
        ProcesoError: Si ``objdump`` falla.

    Ejemplo:
        if not _define_funcion(raiz, herramientas, ejecutar, "build/diff/probar.a.c.o", "func_X"):
            ...
    """
    tabla = ejecutar([str(herramientas.objdump), "-t", objeto], raiz, TIMEOUT_ENLACE_S)
    return funcion_en_objeto(tabla, funcion) is not None


def probar_variantes(
    raiz: Path,
    funcion: str,
    carpeta: Path,
    herramientas: HerramientasCompilacion,
    *,
    script_diff: Path,
    ejecutar: Ejecutor,
) -> list[ResultadoVariante]:
    """
    Compila cada variante y la compara con el ensamblador original de la funcion.

    Contexto:
        Implementa ``probar``. El objetivo se ensambla una vez; cada variante se compila con las
        mismas opciones que el archivo ``src/`` donde vive la funcion (incluido su ``-G``). Un
        fallo de una variante (no compila, no define la funcion) se registra en su fila, sin
        puntuacion, y no detiene a las demas.

    Args:
        raiz (Path): Raiz del repositorio.
        funcion (str): Nombre de la funcion a comparar.
        carpeta (Path): Carpeta con las variantes ``.c``.
        herramientas (HerramientasCompilacion): Herramientas de compilacion.
        script_diff (Path): Ruta de ``diff.py`` de ``asm-differ``.
        ejecutar (Ejecutor): Ejecutor de procesos.

    Returns:
        list[ResultadoVariante]: Un resultado por variante, ordenado de mejor a peor.

    Raises:
        ValueError: Si el nombre no es valido, la funcion no figura en ``src/`` o la carpeta no
            es utilizable.
        FileNotFoundError: Si falta la carpeta o el asm original (hay que ejecutar ``split``).
        ProcesoError: Si falla el ensamblado del objetivo.

    Ejemplo:
        resultados = probar_variantes(
            Path("."), "func_80035244", Path("v"), herramientas, script_diff=script, ejecutar=ejecutar
        )
    """
    validar_funcion(funcion)
    variantes = listar_variantes(carpeta)
    estados = fuentes_c.analizar_fuentes(listar_fuentes_c(raiz))
    archivo, _ = fuentes_c.ubicar_funcion(estados, funcion)
    valor_g = leer_valores_g(raiz).get(Path(archivo).stem, 0)
    direccion = leer_direcciones_de_funciones(raiz).get(funcion)
    objetivo, retornos, max_lineas = preparar_objetivo(raiz, funcion, archivo, herramientas, ejecutar)
    resultados: list[ResultadoVariante] = []
    for variante in variantes:
        objeto = f"{CARPETA_DIFF}/probar.{variante.name}.o"
        try:
            compilar_archivo(
                raiz,
                str(variante.resolve()),
                objeto,
                herramientas,
                ejecutar,
                exigir_solo_texto=False,
                valor_g=valor_g,
            )
            if not _define_funcion(raiz, herramientas, ejecutar, objeto, funcion):
                resultados.append(ResultadoVariante(variante.name, None, f"la variante no define {funcion}"))
                continue
            salida = puntuar_objeto(
                raiz,
                herramientas,
                script_diff,
                ejecutar,
                candidato=objeto,
                objetivo=objetivo,
                funcion=funcion,
                retornos=retornos,
                max_lineas=max_lineas,
                formato="json",
            )
            puntuacion = puntuacion_desde_json(salida)
            iguales = None
            if puntuacion != 0 and direccion is not None:
                iguales = bytes_coinciden(
                    raiz,
                    herramientas,
                    ejecutar,
                    funcion=funcion,
                    direccion=direccion,
                    candidato=objeto,
                    objetivo=objetivo,
                )
            resultados.append(ResultadoVariante(variante.name, puntuacion, None, iguales))
        except (ProcesoError, ValueError, OSError) as error:
            resultados.append(ResultadoVariante(variante.name, None, _primera_linea(str(error))))
    return ordenar_resultados(resultados)

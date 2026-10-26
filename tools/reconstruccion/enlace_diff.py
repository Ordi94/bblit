"""Comparacion de una funcion por sus bytes tras enlazar, para distinguir forma de referencia de bytes.

``asm-differ`` compara instruccion por instruccion con los simbolos tal como los escribe el
objeto: el original dice ``%hi(D_80010040)`` y un C que usa un puntero a la direccion constante
dice ``0x8001``, aunque tras enlazar los dos produzcan los mismos bytes. Para no penalizar eso, la
funcion candidata y el objetivo se enlazan por separado en la direccion que tienen en el ejecutable,
resolviendo los simbolos contra el ELF de la ultima construccion correcta, y se comparan los bytes
de la funcion. Si coinciden, la funcion cuenta como coincidente con un aviso por las referencias
que el C escribe en forma numerica.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from tools.reconstruccion.compilacion import HerramientasCompilacion
from tools.reconstruccion.infraestructura import CARPETA_DIFF, ELF_SALIDA, Ejecutor, ProcesoError

TIMEOUT_ENLACE_S = 120
_PATRON_VALOR = re.compile(r"^[0-9a-f]{8,16}$")
_PATRON_NOMBRE = re.compile(r"^[A-Za-z_.$][A-Za-z0-9_.$]*$")
_PATRON_MARCA_SIMBOLICA = re.compile(r"\si\s{2,}[0-9a-f]+:")


@dataclass(frozen=True)
class FuncionEnObjeto:
    """Posicion de una funcion dentro de la seccion ``.text`` de un objeto.

    Attributes:
        desplazamiento: Bytes desde el inicio de ``.text`` hasta la funcion.
        tamano: Tamano de la funcion en bytes.
    """

    desplazamiento: int
    tamano: int


def simbolos_de_elf(salida_objdump: str) -> dict[str, int]:
    """
    Extrae nombre y direccion de los simbolos definidos de la salida de ``objdump -t``.

    Contexto:
        Los simbolos del ELF de la ultima construccion son la referencia para enlazar una sola
        funcion: cada referencia externa del objeto se resuelve a su direccion real. Las
        direcciones de MIPS aparecen extendidas con signo a 64 bits; se conservan los 32 bajos.

    Args:
        salida_objdump (str): Texto producido por ``objdump -t`` sobre el ELF.

    Returns:
        dict[str, int]: Direccion por simbolo (los no definidos y los nombres raros se ignoran).

    Ejemplo:
        simbolos = simbolos_de_elf(salida)
    """
    simbolos: dict[str, int] = {}
    for linea in salida_objdump.splitlines():
        campos = linea.split()
        if len(campos) < 4 or not _PATRON_VALOR.match(campos[0]) or campos[-3] == "*UND*":
            continue
        nombre = campos[-1]
        if _PATRON_NOMBRE.match(nombre):
            simbolos[nombre] = int(campos[0][-8:], 16)
    return simbolos


def texto_simbolos_ld(simbolos: dict[str, int]) -> str:
    """
    Genera un script del enlazador que fija la direccion de cada simbolo.

    Contexto:
        Se pasa con ``-T`` junto al ``-Ttext`` de la funcion; el enlazador acepta asignaciones
        que redefinen simbolos ya definidos por el objeto, de modo que no hay conflicto con la
        propia funcion ni con sus vecinas.

    Args:
        simbolos (dict[str, int]): Direccion por simbolo, de ``simbolos_de_elf``.

    Returns:
        str: Una asignacion por simbolo, ordenadas por nombre.

    Ejemplo:
        texto = texto_simbolos_ld({"func_X": 0x80014AC4})
    """
    return "".join(f"{nombre} = 0x{simbolos[nombre]:08X};\n" for nombre in sorted(simbolos))


def funcion_en_objeto(salida_objdump: str, funcion: str) -> FuncionEnObjeto | None:
    """
    Localiza una funcion en la tabla de simbolos de un objeto (``objdump -t``).

    Contexto:
        Da el desplazamiento y el tamano necesarios para enlazar el objeto de modo que la
        funcion caiga en su direccion y para recortar sus bytes.

    Args:
        salida_objdump (str): Texto de ``objdump -t`` sobre el objeto.
        funcion (str): Nombre de la funcion.

    Returns:
        FuncionEnObjeto | None: Posicion, o ``None`` si el objeto no define la funcion en ``.text``
        con un tamano mayor que cero.

    Ejemplo:
        posicion = funcion_en_objeto(salida, "func_80036204")
    """
    for linea in salida_objdump.splitlines():
        campos = linea.split()
        if len(campos) >= 5 and campos[-1] == funcion and campos[-3] == ".text":
            tamano = int(campos[-2], 16)
            if tamano > 0 and _PATRON_VALOR.match(campos[0]):
                return FuncionEnObjeto(int(campos[0], 16), tamano)
    return None


def contar_referencias_numericas(texto_plano: str) -> int:
    """
    Cuenta las filas de un diff plano cuya unica diferencia es la forma de una referencia.

    Contexto:
        Cuando los bytes enlazados coinciden, las marcas ``i`` (inmediato distinto) que deja
        ``asm-differ`` son referencias que el C escribe como numero y el original como simbolo.

    Args:
        texto_plano (str): Salida de ``asm-differ --format=plain``.

    Returns:
        int: Numero de filas con marca ``i``.

    Ejemplo:
        n = contar_referencias_numericas(texto)
    """
    return len(_PATRON_MARCA_SIMBOLICA.findall(texto_plano))


def bytes_coinciden(
    raiz: Path,
    herramientas: HerramientasCompilacion,
    ejecutar: Ejecutor,
    *,
    funcion: str,
    direccion: int,
    candidato: str,
    objetivo: str,
) -> bool | None:
    """
    Compara los bytes de una funcion candidata y de su objetivo tras enlazarlos.

    Contexto:
        Segundo criterio de coincidencia de ``diff`` y de ``probar``. Necesita el ELF de la
        ultima construccion correcta (``build/SLUS_008.elf``) y el enlazador y ``objcopy`` en las
        herramientas; si falta algo no se puede decidir.

    Args:
        raiz (Path): Raiz del repositorio.
        herramientas (HerramientasCompilacion): Herramientas con enlazador y ``objcopy``.
        ejecutar (Ejecutor): Ejecutor de procesos.
        funcion (str): Nombre de la funcion.
        direccion (int): Direccion de la funcion en el ejecutable.
        candidato (str): Objeto compilado desde C (ruta relativa dentro de ``build/diff/``).
        objetivo (str): Objeto del asm original (ruta relativa dentro de ``build/diff/``).

    Returns:
        bool | None: ``True`` si los bytes son iguales, ``False`` si difieren y ``None`` si no se
        pudo comparar (sin ELF, sin enlazador, la funcion no esta en un objeto o el objeto referencia
        un simbolo que el ejecutable no define).

    Raises:
        ProcesoError: Si ``objdump`` o ``objcopy`` fallan.

    Ejemplo:
        iguales = bytes_coinciden(
            Path("."), h, e, funcion="func_X", direccion=0x80014AC4,
            candidato="build/diff/a.o", objetivo="build/diff/t.o",
        )
    """
    enlazador, objcopy = herramientas.enlazador, herramientas.objcopy
    if enlazador is None or objcopy is None or not (raiz / ELF_SALIDA).is_file():
        return None
    simbolos = simbolos_de_elf(
        ejecutar([str(herramientas.objdump), "-t", ELF_SALIDA], raiz, TIMEOUT_ENLACE_S)
    )
    referencias = f"{CARPETA_DIFF}/referencias.ld"
    (raiz / referencias).write_text(texto_simbolos_ld(simbolos), encoding="utf-8", newline="\n")

    def enlazar(objeto: str) -> bytes | None:
        tabla = ejecutar([str(herramientas.objdump), "-t", objeto], raiz, TIMEOUT_ENLACE_S)
        posicion = funcion_en_objeto(tabla, funcion)
        if posicion is None or posicion.desplazamiento > direccion:
            return None
        base = f"{CARPETA_DIFF}/{Path(objeto).name}"
        inicio = f"-Ttext=0x{direccion - posicion.desplazamiento:08X}"
        try:
            ejecutar(
                [
                    str(enlazador),
                    "-EL",
                    "--no-warn-rwx-segments",
                    "-e",
                    "0",
                    inicio,
                    "-T",
                    referencias,
                    objeto,
                    "-o",
                    f"{base}.elf",
                ],
                raiz,
                TIMEOUT_ENLACE_S,
            )
        except ProcesoError:
            return None
        ejecutar(
            [str(objcopy), "-O", "binary", "-j", ".text", f"{base}.elf", f"{base}.bin"],
            raiz,
            TIMEOUT_ENLACE_S,
        )
        datos = (raiz / f"{base}.bin").read_bytes()
        return datos[posicion.desplazamiento : posicion.desplazamiento + posicion.tamano]

    del_candidato = enlazar(candidato)
    del_objetivo = enlazar(objetivo)
    if del_candidato is None or del_objetivo is None:
        return None
    return del_candidato == del_objetivo

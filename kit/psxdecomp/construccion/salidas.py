"""Nombres de los artefactos que produce la construccion, derivados del manifiesto.

Capa de dominio: funciones puras sobre cadenas, sin acceso a disco. Concentran en un solo lugar
las rutas de ``build/`` que antes eran constantes de un ejecutable concreto, de modo que
``split``, ``build``, ``verify``, ``clean`` y ``diff`` coincidan siempre en donde esta cada salida.

Suposicion: el particionador nombra el script del enlazador y las salidas del enlace con el nombre
del ejecutable sin su ultima extension (``EJEC_001.00`` produce ``EJEC_001.ld``). Un proyecto cuyo
particionador use otro nombre base debe llamarlo igual que su ejecutable.
"""

from __future__ import annotations

from dataclasses import dataclass

from psxdecomp.dominio import Rutas

SUBCARPETA_DIFF = "diff"
SUBCARPETA_PERMUTAR = "permutar"
ARCHIVO_PROGRESO = "progreso.json"


@dataclass(frozen=True, slots=True)
class SalidasDeBuild:
    """
    Rutas, relativas a la raiz del proyecto, de lo que genera la construccion.

    Attributes:
        ejecutable: Ejecutable reconstruido con su cabecera.
        script_enlazador: Script del enlazador que genera el particionador.
        elf: ELF enlazado.
        mapa: Mapa del enlace.
        binario: Cuerpo plano del ejecutable, sin cabecera.
        script_gp: Script con la definicion de ``_gp`` y de los datos pequenos.
        simbolos_entrada: Simbolos de entrada que se le pasan al particionador.
        simbolos_automaticos: Simbolos que el particionador deduce y el enlace consume.
        objetos_asm: Carpeta de los objetos ensamblados.
        objetos_c: Carpeta de los objetos compilados desde C.
        diff: Carpeta de trabajo de la comparacion de funciones.
        permutar: Carpeta del estado del permutador.
        progreso_json: Resumen de progreso en JSON.
    """

    ejecutable: str
    script_enlazador: str
    elf: str
    mapa: str
    binario: str
    script_gp: str
    simbolos_entrada: str
    simbolos_automaticos: tuple[str, str]
    objetos_asm: str
    objetos_c: str
    diff: str
    permutar: str
    progreso_json: str


def calcular_salidas(nombre_ejecutable: str, rutas: Rutas) -> SalidasDeBuild:
    """
    Deriva las rutas de las salidas de la construccion del nombre del ejecutable y del manifiesto.

    Contexto:
        Lo usan la infraestructura de construccion, la comparacion de funciones y la reexportacion
        del proyecto consumidor. Las carpetas de objetos reflejan las de origen (``<build>/<asm>``
        y ``<build>/<fuentes>``), que es como el particionador los nombra en el script del enlazador.

    Args:
        nombre_ejecutable (str): Nombre del ejecutable reconstruido (``identidad.ejecutable``).
        rutas (Rutas): Seccion ``[rutas]`` del manifiesto.

    Returns:
        SalidasDeBuild: Rutas relativas, con barras normales.

    Ejemplo:
        salidas = calcular_salidas("EJEC_001.00", rutas)  # salidas.elf == "build/EJEC_001.elf"
    """
    build = rutas.build
    base = f"{build}/{nombre_ejecutable.rsplit('.', 1)[0]}"
    return SalidasDeBuild(
        ejecutable=f"{build}/{nombre_ejecutable}",
        script_enlazador=f"{base}.ld",
        elf=f"{base}.elf",
        mapa=f"{base}.map",
        binario=f"{base}.bin",
        script_gp=f"{build}/gp.ld",
        simbolos_entrada=f"{build}/simbolos_entrada.txt",
        simbolos_automaticos=(f"{build}/undefined_funcs_auto.txt", f"{build}/undefined_syms_auto.txt"),
        objetos_asm=f"{build}/{rutas.asm}",
        objetos_c=f"{build}/{rutas.fuentes}",
        diff=f"{build}/{SUBCARPETA_DIFF}",
        permutar=f"{build}/{SUBCARPETA_PERMUTAR}",
        progreso_json=f"{build}/{ARCHIVO_PROGRESO}",
    )

"""Medicion del progreso sobre el disco: lee simbolos, fuentes y ensamblador y escribe sus resultados.

Capa de aplicacion. Reune las piezas puras (``calculo``, ``documento``) con la lectura de la tabla de
simbolos, de los archivos C y del ensamblador generado, y escribe el documento de progreso y el
resumen en JSON. Rutas, zonas y convenciones llegan del manifiesto; nada del proyecto se supone.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from psxdecomp.construccion.infraestructura import MAX_BYTES_SIMBOLOS, listar_fuentes_c
from psxdecomp.construccion.salidas import ARCHIVO_PROGRESO
from psxdecomp.diff.fuentes_c import (
    analizar_fuentes,
    clasificar_include_asm,
    motivos_no_coincidentes,
    verificar_pendientes,
)
from psxdecomp.dominio import Convenciones, Rutas, Zonas
from psxdecomp.progreso import calculo, documento
from psxdecomp.progreso.calculo import AgrupadorDeSubsistemas, FuncionSimbolo, Progreso

_PATRON_GLABEL = re.compile(r"^glabel\s+\S+", re.MULTILINE)


def contar_glabel(raiz: Path, *, rutas: Rutas) -> int | None:
    """
    Cuenta los ``glabel`` del ensamblador generado por el particionador.

    Contexto:
        Es la medida independiente del conteo por fuente: cada funcion que no esta en C debe figurar
        como ``glabel`` en la carpeta de ensamblador. No se cuentan las carpetas auxiliares
        (``rutas.asm_auxiliares``: macros y ensamblador de las funciones ya en C) ni las de otras
        herramientas (``rutas.subcarpetas_ajenas``).

    Args:
        raiz (Path): Raiz del proyecto.
        rutas (Rutas): Carpeta del ensamblador, auxiliares y subcarpetas ajenas.

    Returns:
        int | None: Numero de ``glabel``, o ``None`` si no existe la carpeta de ensamblador.

    Ejemplo:
        total = contar_glabel(Path("."), rutas=rutas)
    """
    carpeta = raiz / rutas.asm
    if not carpeta.is_dir():
        return None
    omitidas = (*rutas.asm_auxiliares, *rutas.subcarpetas_ajenas)
    total = 0
    for ruta in sorted(carpeta.rglob("*.s")):
        if ruta.relative_to(carpeta).parts[0] in omitidas:
            continue
        total += len(_PATRON_GLABEL.findall(ruta.read_text(encoding="utf-8")))
    return total


def _leer_tabla(ruta: Path, convenciones: Convenciones) -> list[FuncionSimbolo]:
    """Lee un archivo de simbolos con cota de tamano; vacio si no existe."""
    if not ruta.is_file():
        return []
    if ruta.stat().st_size > MAX_BYTES_SIMBOLOS:
        raise ValueError(f"{ruta.name} excede el tamano permitido")
    return calculo.leer_simbolos(ruta.read_text(encoding="utf-8"), convenciones)


def generar_progreso(
    raiz: Path,
    *,
    rutas: Rutas,
    convenciones: Convenciones,
    zonas: Zonas,
    comando: str,
    subsistema: AgrupadorDeSubsistemas | None = None,
) -> Progreso:
    """
    Mide el progreso y escribe el documento de progreso y el resumen en JSON.

    Contexto:
        Implementa ``progreso``. No necesita el disco ni el toolchain: solo la tabla de simbolos, los
        fuentes y, si existe, el ensamblador generado. Los nombres de las salidas son los del manifiesto
        (``rutas.documento_progreso`` y ``<build>/progreso.json``).

    Args:
        raiz (Path): Raiz del proyecto.
        rutas (Rutas): Carpetas y archivos del proyecto.
        convenciones (Convenciones): Macros, linea de pendiente y formato de los simbolos.
        zonas (Zonas): Limites de memoria del ejecutable.
        comando (str): Comando con el que el proyecto invoca al kit; se cita en el documento.
        subsistema (AgrupadorDeSubsistemas, opcional): Regla que agrupa los archivos en subsistemas;
            por omision, el nombre del archivo sin ``convenciones.sufijo_subsistema``.

    Returns:
        Progreso: Resultado medido.

    Raises:
        FileNotFoundError: Si falta el primer archivo de simbolos.
        ValueError: Si la tabla o algun archivo C no se pueden interpretar, o si algun bloque
            no coincidente no tiene la linea de pendiente (nada se escribe).

    Ejemplo:
        progreso = generar_progreso(
            Path("."), rutas=r, convenciones=c, zonas=z, comando="python -m psxdecomp.cli"
        )
    """
    principal = rutas.simbolos[0]
    if not (raiz / principal).is_file():
        raise FileNotFoundError(f"falta {principal}")
    simbolos = calculo.combinar_simbolos(
        *(_leer_tabla(raiz / ruta, convenciones) for ruta in (*rutas.simbolos, rutas.simbolos_adicionales))
    )
    textos = listar_fuentes_c(raiz, rutas=rutas)
    motivos: dict[str, str] = {}
    for texto in textos.values():
        motivos.update(motivos_no_coincidentes(texto, convenciones))
    estados = analizar_fuentes(textos, convenciones)
    verificar_pendientes(textos, convenciones)
    marcas = {archivo: clasificar_include_asm(texto, convenciones) for archivo, texto in textos.items()}
    progreso = calculo.calcular_progreso(
        simbolos,
        estados,
        contar_glabel(raiz, rutas=rutas),
        motivos,
        marcas,
        zonas=zonas,
        subsistema=subsistema or (lambda archivo: calculo.subsistema_de(archivo, convenciones)),
    )
    destino = raiz / rutas.documento_progreso
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        documento.a_markdown(progreso, comando=comando, rutas=rutas, convenciones=convenciones),
        encoding="utf-8",
        newline="\n",
    )
    salida = raiz / rutas.build / ARCHIVO_PROGRESO
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(
        json.dumps(documento.a_json(progreso), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return progreso

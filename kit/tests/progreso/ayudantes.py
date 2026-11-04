"""Proyectos inventados y atajos para probar el medidor de progreso con datos que no son de ningun juego.

Hay dos proyectos: ``PROYECTO_BASE`` usa las rutas y convenciones por defecto del kit, y
``crear_proyecto_propio`` escribe en disco uno con rutas, comando, variable de entorno y funcion de
ejemplo propios para demostrar que nada de lo que genera el medidor esta escrito a mano.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psxdecomp.diff.fuentes_c import EstadoFuncion, MarcaAsm
from psxdecomp.dominio import Proyecto, construir_proyecto
from psxdecomp.lectura import cargar_proyecto
from psxdecomp.progreso import calculo, documento, medicion
from psxdecomp.progreso.calculo import FuncionSimbolo, Progreso, ResumenZona

from construccion.test_infraestructura import CABECERA, REFERENCIA
from manifiestos_de_prueba import MANIFIESTO_MINIMO

__all__ = [
    "COMANDO_PROPIO",
    "PROYECTO_BASE",
    "PROYECTO_PROPIO",
    "SHA_INVENTADO",
    "EstadoFuncion",
    "FuncionSimbolo",
    "MarcaAsm",
    "ProyectoPropio",
    "ResumenZona",
    "a_json",
    "a_markdown",
    "calcular_progreso",
    "combinar_simbolos",
    "contar_glabel",
    "crear_proyecto_propio",
    "escribir",
    "generar_progreso",
    "leer",
    "leer_simbolos",
    "subsistema_de",
    "zona_de",
]

SHA_INVENTADO = REFERENCIA.sha256
COMANDO_PROPIO = "demo-decomp"

MANIFIESTO_BASE = (
    MANIFIESTO_MINIMO
    + """
[rutas]
subcarpetas_ajenas = ["modulo_ajeno"]
asm_auxiliares = ["include", "matchings"]
"""
)
PROYECTO_BASE = construir_proyecto(tomllib.loads(MANIFIESTO_BASE), Path("."))
CONVENCIONES = PROYECTO_BASE.convenciones
ZONAS = PROYECTO_BASE.zonas

MANIFIESTO_PROPIO = f"""\
[proyecto]
nombre = "demo"
ejecutable = "PRUEBA.EXE"
referencia = "datos/ejecutable.json"
prefijo_entorno = "JUEGO"
comando = "{COMANDO_PROPIO}"
funcion_ejemplo = "rutina_ejemplo"

[rutas]
fuentes = "codigo"
asm = "ensamblador"
asm_coincidente = "ensamblador/cerradas"
asm_pendiente = "ensamblador/pendientes"
macros = "ensamblador/macros"
build = "salida"
simbolos = ["datos/simbolos.txt"]
simbolos_adicionales = "datos/extra.txt"
documento_progreso = "notas/avance.md"
readme = "LEEME.md"
subcarpetas_ajenas = ["externo"]
asm_auxiliares = ["macros", "cerradas"]

[zonas]
juego_desde = 0x80110100
librerias_desde = 0x80120000
librerias_hasta = 0x80130000

[plugins]
"""

PROYECTO_PROPIO = construir_proyecto(tomllib.loads(MANIFIESTO_PROPIO), Path("."))


def leer_simbolos(texto: str) -> list[FuncionSimbolo]:
    """Lee un texto de simbolos con las convenciones por defecto."""
    return calculo.leer_simbolos(texto, CONVENCIONES)


def combinar_simbolos(*fuentes: list[FuncionSimbolo]) -> list[FuncionSimbolo]:
    """Une tablas de simbolos; la ultima manda por direccion."""
    return calculo.combinar_simbolos(*fuentes)


def zona_de(direccion: int) -> str:
    """Clasifica una direccion con las zonas del proyecto base."""
    return calculo.zona_de(direccion, ZONAS)


def subsistema_de(archivo: str) -> str:
    """Da el subsistema de un archivo con el sufijo por defecto."""
    return calculo.subsistema_de(archivo, CONVENCIONES)


def calcular_progreso(
    simbolos: list[FuncionSimbolo],
    estados: dict[str, dict[str, EstadoFuncion]],
    glabel_en_asm: int | None,
    motivos: dict[str, str] | None = None,
    marcas: dict[str, dict[str, MarcaAsm]] | None = None,
) -> Progreso:
    """Calcula el progreso con las zonas y el agrupado por defecto del proyecto base."""
    return calculo.calcular_progreso(
        simbolos, estados, glabel_en_asm, motivos, marcas, zonas=ZONAS, subsistema=subsistema_de
    )


def a_json(progreso: Progreso) -> dict[str, Any]:
    """Convierte el progreso al objeto del resumen en JSON."""
    return documento.a_json(progreso)


def a_markdown(progreso: Progreso) -> str:
    """Genera el documento de progreso del proyecto base."""
    return documento.a_markdown(
        progreso,
        comando=PROYECTO_BASE.identidad.comando,
        rutas=PROYECTO_BASE.rutas,
        convenciones=CONVENCIONES,
    )


def contar_glabel(raiz: Path) -> int | None:
    """Cuenta los ``glabel`` del ensamblador del proyecto base bajo ``raiz``."""
    return medicion.contar_glabel(raiz, rutas=PROYECTO_BASE.rutas)


def generar_progreso(raiz: Path) -> Progreso:
    """Mide el progreso del proyecto base bajo ``raiz`` y escribe sus salidas."""
    return medicion.generar_progreso(
        raiz,
        rutas=PROYECTO_BASE.rutas,
        convenciones=CONVENCIONES,
        zonas=ZONAS,
        comando=PROYECTO_BASE.identidad.comando,
    )


@dataclass(frozen=True)
class ProyectoPropio:
    """
    Proyecto inventado con rutas propias, ya escrito en disco.

    Attributes:
        raiz: Raiz del proyecto.
        proyecto: Manifiesto cargado.
    """

    raiz: Path
    proyecto: Proyecto


def _referencia_json() -> dict[str, Any]:
    """Referencia del ejecutable inventado en el formato del archivo versionado."""
    campos = ("pc0", "gp0", "t_addr", "t_size", "d_addr", "d_size", "b_addr", "b_size", "s_addr", "s_size")
    return {
        "nombre": REFERENCIA.nombre,
        "sha256": REFERENCIA.sha256,
        "sha1": REFERENCIA.sha1,
        "tamano": REFERENCIA.tamano,
        "cabecera": {**{campo: getattr(CABECERA, campo) for campo in campos}, "region": CABECERA.region},
    }


def escribir(ruta: Path, texto: str) -> None:
    """Escribe un archivo de texto sin traducir saltos de linea, creando las carpetas."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        archivo.write(texto)


def leer(ruta: Path) -> str:
    """Lee un archivo de texto sin traducir saltos de linea."""
    with ruta.open(encoding="utf-8", newline="") as archivo:
        return archivo.read()


def crear_proyecto_propio(
    raiz: Path, *, extra_manifiesto: str = "", con_readme: str | None = None
) -> ProyectoPropio:
    """
    Escribe un proyecto inventado con una funcion en C y su referencia, y lo carga.

    Contexto:
        Base de las pruebas de la orden ``progreso`` y de la seccion del README: la tabla de simbolos
        declara una funcion del juego y otra de las librerias, y ``codigo/modulo_a.c`` define la primera.

    Args:
        raiz (Path): Carpeta vacia donde escribir el proyecto.
        extra_manifiesto (str, opcional): Texto que se anade al final del manifiesto (por ejemplo, claves
            de ``[plugins]``).
        con_readme (str, opcional): Contenido del README; sin el, no se escribe.

    Returns:
        ProyectoPropio: Raiz y proyecto cargado.

    Ejemplo:
        propio = crear_proyecto_propio(tmp_path, con_readme="# titulo\n\nparrafo\n")
    """
    escribir(raiz / "psxdecomp.toml", MANIFIESTO_PROPIO + extra_manifiesto)
    escribir(
        raiz / "datos" / "simbolos.txt",
        "rutina_a = 0x80110100; // type:func size:0x10\nrutina_b = 0x80120000; // type:func size:0x20\n",
    )
    escribir(raiz / "datos" / "ejecutable.json", json.dumps(_referencia_json()))
    escribir(raiz / "codigo" / "modulo_a.c", "int rutina_a(void)\n{\n    return 0;\n}\n")
    if con_readme is not None:
        escribir(raiz / "LEEME.md", con_readme)
    return ProyectoPropio(raiz, cargar_proyecto(raiz))

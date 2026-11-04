"""Ayudantes de las pruebas del banco de variantes y del aviso de coherencia de pendientes.

Definen un proyecto inventado (carpeta de fuentes ``codigo``, ensamblador en ``ensamblador/...``,
salidas en ``salida``) y dobles de proceso que simulan el compilador, ``asm-differ`` y el enlace con
puntuaciones configurables por variante.
"""

import json
from pathlib import Path
from typing import Any, ClassVar

from psxdecomp.construccion.compilacion import HerramientasCompilacion
from psxdecomp.construccion.infraestructura import ProcesoError
from psxdecomp.diff import variantes
from psxdecomp.diff.variantes import ResultadoVariante
from psxdecomp.dominio import (
    Compilacion,
    Convenciones,
    construir_compilacion,
    construir_convenciones,
    construir_rutas,
)

from construccion.test_compilacion import herramientas

from .test_comparacion import ASM_FUNCION, EJECUTABLE, EjecutorDiff
from .test_enlace_diff import CUERPO_OBJETO, ELF, TABLA_ELF, TABLA_OBJETO, herramientas_con_enlace

RUTAS = construir_rutas(
    {
        "fuentes": "codigo",
        "asm_coincidente": "ensamblador/cerradas",
        "asm_pendiente": "ensamblador/pendientes",
        "macros": "ensamblador/macros",
        "build": "salida",
        "simbolos": ["datos/simbolos.txt"],
        "opciones_compilacion": "datos/opciones.toml",
    }
)
CONVENCIONES = construir_convenciones({})
COMPILACION = construir_compilacion({})
FUNCION = "rutina_a"
SIMBOLOS = "rutina_a = 0x80100100; // type:func size:0x4c\n"


class EjecutorVariantes(EjecutorDiff):
    """Compila y puntua con puntuaciones por variante; una variante ``rota`` no compila."""

    PUNTUACIONES: ClassVar[dict[str, int]] = {"mejor.c": 0, "peor.c": 120, "otra.c": 9800, "vacia.c": 400}
    FILAS: ClassVar[dict[str, int]] = {}
    TABLA_CON_FUNCION = (
        "SYMBOL TABLE:\n00000000 l    d  .text\t00000000 .text\n00000000 g     F .text\t00000020 rutina_a\n"
    )
    TABLA_DE_OTRA_FUNCION = "SYMBOL TABLE:\n00000000 g     F .text\t00000020 rutina_zeta\n"
    TABLA_VACIA = "SYMBOL TABLE:\n00000000 l    d  .text\t00000000 .text\n"

    def __init__(self) -> None:
        super().__init__(0)

    def __call__(self, comando: Any, directorio: Any, timeout_s: Any) -> Any:
        salida = super().__call__(comando, directorio, timeout_s)
        nombre = Path(comando[0]).name
        if nombre == "objdump.exe" and "-t" in comando:
            if "otra.c" in comando[-1]:
                return self.TABLA_DE_OTRA_FUNCION
            return self.TABLA_VACIA if "vacia.c" in comando[-1] else self.TABLA_CON_FUNCION
        if nombre == "CC1PSX.EXE" and "rota" in comando[-3]:
            raise ProcesoError("CC1PSX.EXE: termino con codigo 33\nerror de sintaxis")
        if nombre == "CC1PSX.EXE" and "disco" in comando[-3]:
            raise OSError("disco lleno")
        if "--format=json" in comando:
            variante = comando[comando.index("--file") + 1].split("probar.")[1].removesuffix(".o")
            if variante == "ilegible.c":
                return "no es json"
            cuerpo: dict[str, Any] = {"current_score": self.PUNTUACIONES[variante]}
            if variante in self.FILAS:
                cuerpo["rows"] = [{"current": {"mnemonic": "addiu"}}] * self.FILAS[variante]
            return json.dumps(cuerpo)
        return salida


class EjecutorVariantesEnlace(EjecutorVariantes):
    """Responde tambien al enlace por bytes: los objetos de variante igualan o no al objetivo."""

    def __init__(self, *, difiere: bool = False) -> None:
        super().__init__()
        self.difiere = difiere

    def __call__(self, comando: Any, directorio: Any, timeout_s: Any) -> Any:
        nombre = Path(comando[0]).name
        sin_funcion = "otra.c" in comando[-1] or "vacia.c" in comando[-1]
        if nombre == "objdump.exe" and comando[1] == "-t" and not sin_funcion:
            self.comandos.append(list(comando))
            return TABLA_ELF if comando[2] == ELF else TABLA_OBJETO
        if nombre == "ld.exe":
            self.comandos.append(list(comando))
            return ""
        if nombre == "objcopy.exe":
            self.comandos.append(list(comando))
            cuerpo = CUERPO_OBJETO
            if self.difiere and "objetivo" not in comando[-1]:
                cuerpo = CUERPO_OBJETO[:-1] + b"\x00"
            (directorio / comando[-1]).write_bytes(cuerpo)
            return ""
        return super().__call__(comando, directorio, timeout_s)


def crear_repo(raiz: Path, *, simbolos: bool = False) -> None:
    """Crea un proyecto con una funcion pendiente en ``codigo/modulo_a.c`` y su ensamblador original."""
    (raiz / "codigo").mkdir(parents=True)
    (raiz / "codigo" / "modulo_a.c").write_text(
        'INCLUDE_ASM("ensamblador/pendientes/modulo_a", rutina_a);\n', encoding="utf-8"
    )
    destino = raiz / "ensamblador" / "pendientes" / "modulo_a"
    destino.mkdir(parents=True)
    (destino / "rutina_a.s").write_text(ASM_FUNCION, encoding="utf-8")
    if simbolos:
        (raiz / "datos").mkdir(exist_ok=True)
        (raiz / "datos" / "simbolos.txt").write_text(SIMBOLOS, encoding="utf-8")


def escribir_opciones(raiz: Path, texto: str) -> None:
    """Escribe las opciones de compilacion en la ruta que declara el manifiesto de estas pruebas."""
    (raiz / "datos").mkdir(parents=True, exist_ok=True)
    (raiz / RUTAS.opciones_compilacion).write_text(texto, encoding="utf-8")


def crear_variantes(carpeta: Path, nombres: list[str]) -> Path:
    """Crea una carpeta con una variante minima por cada nombre."""
    carpeta.mkdir(exist_ok=True)
    for nombre in nombres:
        (carpeta / nombre).write_text("int x;\n", encoding="utf-8")
    return carpeta


def probar(
    raiz: Path,
    carpeta: Path,
    ejecutor: Any,
    *,
    herramientas_c: HerramientasCompilacion | None = None,
    convenciones: Convenciones = CONVENCIONES,
    compilacion: Compilacion = COMPILACION,
    funcion: str = FUNCION,
) -> list[ResultadoVariante]:
    """Ejecuta ``probar_variantes`` con el manifiesto, el ejecutable y el ``asm-differ`` de estas pruebas."""
    return variantes.probar_variantes(
        raiz,
        funcion,
        carpeta,
        herramientas_c if herramientas_c is not None else herramientas(),
        script_diff=Path("diff.py"),
        ejecutar=ejecutor,
        rutas=RUTAS,
        convenciones=convenciones,
        compilacion=compilacion,
        nombre_ejecutable=EJECUTABLE,
    )


__all__ = [
    "COMPILACION",
    "CONVENCIONES",
    "FUNCION",
    "RUTAS",
    "SIMBOLOS",
    "EjecutorVariantes",
    "EjecutorVariantesEnlace",
    "crear_repo",
    "crear_variantes",
    "escribir_opciones",
    "herramientas_con_enlace",
    "probar",
]

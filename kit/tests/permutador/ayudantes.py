"""Doble de la cadena de compilacion y repositorio sintetico para las pruebas de evaluacion y busqueda."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from psxdecomp.construccion.infraestructura import ProcesoError
from psxdecomp.dominio import (
    Compilacion,
    Convenciones,
    Rutas,
    construir_compilacion,
    construir_convenciones,
    construir_rutas,
)

EJECUTABLE = "EJEC_001.00"
ELF = "salida/EJEC_001.elf"
FUNCION = "rutina_a"
DIRECCION = 0x80100100
ARCHIVO = "codigo/modulo_a.c"
CARPETA_ASM_PENDIENTE = "ensamblador/pendientes/modulo_a"

RUTAS: Rutas = construir_rutas(
    {
        "fuentes": "codigo",
        "asm_coincidente": "ensamblador/cerradas",
        "asm_pendiente": "ensamblador/pendientes",
        "macros": "ensamblador/macros",
        "build": "salida",
        "incluir": "cabeceras",
        "opciones_compilacion": "datos/opciones.toml",
        "simbolos": ["datos/simbolos.txt"],
    }
)
CONVENCIONES: Convenciones = construir_convenciones({})
CONVENCIONES_PROPIAS: Convenciones = construir_convenciones(
    {"macro_no_coincidente": "NO_COINCIDE", "macro_ensamblador": "ENSAMBLAR"}
)
COMPILACION: Compilacion = construir_compilacion({})

ASM_FUNCION = """
nonmatching rutina_a, 0x10

glabel rutina_a
    /* 100 80100100 21188000 */  addu       $v1, $a0, $zero
    /* 130 80100130 0800E003 */  jr         $ra
    /* 134 80100134 000040AC */   sw        $zero, 0x0($v0)
endlabel rutina_a
"""
TABLA_DE_SIMBOLOS = """
c.o:     file format elf32-littlemips

SYMBOL TABLE:
00000000 g     F .text\t00000010 rutina_a
"""
CABECERA_DE_ARCHIVO = "typedef int s32;\n"
CUERPO_FUNCION = "s32 rutina_a(s32 x)\n{\n    s32 y;\n    y = x + 1;\n    return y;\n}"


def archivo_c(convenciones: Convenciones = CONVENCIONES) -> str:
    """
    Arma el archivo C de la funcion pendiente con las macros de las convenciones dadas.

    Contexto:
        Permite ejercitar las mismas pruebas con macros distintas de las por defecto.

    Args:
        convenciones (Convenciones, opcional): Convenciones cuyas macros usa el archivo.

    Returns:
        str: Texto del archivo: el intento en C bajo la macro de no coincidencia y el ensamblador
        original bajo la contraria.

    Ejemplo:
        texto = archivo_c(CONVENCIONES_PROPIAS)
    """
    return (
        CABECERA_DE_ARCHIVO
        + f"#ifdef {convenciones.macro_no_coincidente}\n"
        + "/* Pendiente: puntuacion 40 */\n"
        + CUERPO_FUNCION
        + f'\n#else\n{convenciones.macro_ensamblador}("{CARPETA_ASM_PENDIENTE}", {FUNCION});\n#endif\n'
    )


ARCHIVO_C = archivo_c()


class EjecutorPermutar:
    """Ejecutor falso: crea los objetos, devuelve la tabla de simbolos y puntua segun el C de la variante."""

    def __init__(
        self,
        puntuar: Callable[[str], int] = lambda texto: 40,
        *,
        define_funcion: bool = True,
        falla_si: Callable[[str], bool] = lambda texto: False,
        filas: list[Any] | None = None,
    ) -> None:
        self.puntuar = puntuar
        self.define_funcion = define_funcion
        self.falla_si = falla_si
        self.filas = filas
        self.comandos: list[list[str]] = []

    def __call__(self, comando: Any, directorio: Path, timeout_s: int) -> str:
        self.comandos.append(list(comando))
        nombre = Path(comando[0]).name
        if nombre == "as.exe" or "--run-assembler" in comando:
            (directorio / comando[comando.index("-o") + 1]).write_bytes(b"objeto")
        if nombre == "CC1PSX.EXE":
            fuente = directorio / comando[-3].removesuffix(".i")
            if fuente.is_file() and self.falla_si(fuente.read_text(encoding="utf-8")):
                raise ProcesoError(
                    "CC1PSX.EXE: termino con codigo 1\nvariante.c:3: error: sintaxis\notra linea"
                )
        if nombre == "objdump.exe":
            return TABLA_DE_SIMBOLOS if self.define_funcion else "sin simbolos"
        if "--format=json" in comando:
            fuente = (directorio / "variante.c").read_text(encoding="utf-8")
            datos: dict[str, Any] = {"current_score": self.puntuar(fuente)}
            if self.filas is not None:
                datos["rows"] = self.filas
            return json.dumps(datos)
        return ""


def crear_repositorio(
    raiz: Path,
    *,
    con_elf: bool = True,
    con_simbolos: bool = False,
    valor_g: int | None = None,
    rutas: Rutas = RUTAS,
    convenciones: Convenciones = CONVENCIONES,
    nombre_elf: str = ELF,
) -> None:
    """
    Crea un repositorio minimo con una funcion pendiente y su ensamblador original.

    Contexto:
        Base de las pruebas de ``evaluacion`` y ``busqueda``; las carpetas salen de ``rutas`` salvo el
        ELF, que se coloca en ``nombre_elf`` para poder probar que se busca el del ejecutable pedido.

    Args:
        raiz (Path): Carpeta (aun inexistente) que sera la raiz del proyecto.
        con_elf (bool, opcional): Si existe el ELF de la ultima construccion.
        con_simbolos (bool, opcional): Si se declara la direccion de la funcion.
        valor_g (int | None, opcional): ``-G`` del archivo, o ``None`` si no se configura.
        rutas (Rutas, opcional): Rutas del proyecto sintetico.
        convenciones (Convenciones, opcional): Macros que usa el archivo C.
        nombre_elf (str, opcional): Ruta relativa del ELF cuando ``con_elf`` es verdadero.

    Ejemplo:
        crear_repositorio(tmp_path / "r", con_simbolos=True, valor_g=8)
    """
    (raiz / rutas.fuentes).mkdir(parents=True)
    (raiz / ARCHIVO).write_text(archivo_c(convenciones), encoding="utf-8")
    carpeta_asm = raiz / CARPETA_ASM_PENDIENTE
    carpeta_asm.mkdir(parents=True)
    (carpeta_asm / f"{FUNCION}.s").write_text(ASM_FUNCION, encoding="utf-8")
    if con_elf:
        (raiz / nombre_elf).parent.mkdir(parents=True, exist_ok=True)
        (raiz / nombre_elf).write_bytes(b"elf")
    if con_simbolos:
        (raiz / "datos").mkdir(exist_ok=True)
        (raiz / "datos" / "simbolos.txt").write_text(
            f"{FUNCION} = 0x{DIRECCION:08X}; // type:func size:0x10\n", encoding="utf-8"
        )
    if valor_g is not None:
        (raiz / "datos").mkdir(exist_ok=True)
        (raiz / "datos" / "opciones.toml").write_text(
            f"[archivos.modulo_a]\ng = {valor_g}\n", encoding="utf-8"
        )

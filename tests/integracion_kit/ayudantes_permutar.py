"""Doble de pruebas de la cadena de compilacion y de ``asm-differ`` para las pruebas del permutador."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from psxdecomp.construccion.infraestructura import ProcesoError

FUNCION = "func_80036204"
ASM_FUNCION = """
nonmatching func_80036204, 0x10

glabel func_80036204
    /* 22004 80036204 21188000 */  addu       $v1, $a0, $zero
    /* 22030 80036230 0800E003 */  jr         $ra
    /* 22034 80036234 000040AC */   sw        $zero, 0x0($v0)
endlabel func_80036204
"""
TABLA_DE_SIMBOLOS = """
c.o:     file format elf32-littlemips

SYMBOL TABLE:
00000000 g     F .text\t00000010 func_80036204
"""
CABECERA_DE_ARCHIVO = "typedef int s32;\n"
CUERPO_FUNCION = "s32 func_80036204(s32 x)\n{\n    s32 y;\n    y = x + 1;\n    return y;\n}"
ARCHIVO_C = (
    CABECERA_DE_ARCHIVO
    + "#ifdef NON_MATCHING\n"
    + "/* Pendiente: puntuacion 40 */\n"
    + CUERPO_FUNCION
    + '\n#else\nINCLUDE_ASM("asm/nonmatchings/code_a", func_80036204);\n#endif\n'
)


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

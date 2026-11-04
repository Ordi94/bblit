"""Ayudantes del consumidor para el banco de variantes: ejecutor con puntuaciones y repositorios."""

import json
from pathlib import Path
from typing import Any, ClassVar

from tools.reconstruccion import infraestructura as infra
from tools.reconstruccion.infraestructura import ProcesoError

from .ayudantes_diff import ASM_FUNCION
from .test_compilacion import EjecutorC


class EjecutorVariantes(EjecutorC):
    """Compila y puntua con puntuaciones por variante; una variante 'rota' no compila."""

    PUNTUACIONES: ClassVar[dict[str, int]] = {"mejor.c": 0, "peor.c": 120, "otra.c": 9800, "vacia.c": 400}
    TABLA_CON_FUNCION = (
        "SYMBOL TABLE:\n"
        "00000000 l    d  .text\t00000000 .text\n"
        "00000000 g     F .text\t00000020 func_80036204\n"
    )
    TABLA_DE_OTRA_FUNCION = "SYMBOL TABLE:\n00000000 g     F .text\t00000020 func_80099999\n"
    TABLA_VACIA = "SYMBOL TABLE:\n00000000 l    d  .text\t00000000 .text\n"
    FILAS: ClassVar[dict[str, int]] = {}

    def __call__(self, comando: Any, directorio: Any, timeout_s: Any) -> Any:
        salida = super().__call__(comando, directorio, timeout_s)
        nombre = Path(comando[0]).name
        if nombre == "objdump.exe" and "-t" in comando:
            if "otra.c" in comando[-1]:
                return self.TABLA_DE_OTRA_FUNCION
            return self.TABLA_VACIA if "vacia.c" in comando[-1] else self.TABLA_CON_FUNCION
        if nombre == "CC1PSX.EXE" and "rota" in comando[-3]:
            raise ProcesoError("CC1PSX.EXE: termino con codigo 33\nparse error")
        if "--format=json" in comando:
            variante = comando[comando.index("--file") + 1].split("probar.")[1].removesuffix(".o")
            if variante == "ilegible.c":
                return "no es json"
            salida_json: dict[str, Any] = {"current_score": self.PUNTUACIONES[variante]}
            if variante in self.FILAS:
                filas = [{"current": {"mnemonic": "addiu"}}] * self.FILAS[variante]
                salida_json["rows"] = filas
            return json.dumps(salida_json)
        return salida


def crear_repo(raiz: Path) -> None:
    (raiz / "src").mkdir(parents=True)
    (raiz / "src" / "code_a.c").write_text(
        'INCLUDE_ASM("asm/nonmatchings/code_a", func_80036204);\n', encoding="utf-8"
    )
    (raiz / "asm" / "nonmatchings" / "code_a").mkdir(parents=True)
    (raiz / "asm" / "nonmatchings" / "code_a" / "func_80036204.s").write_text(ASM_FUNCION, encoding="utf-8")


def crear_variantes(carpeta: Path, nombres: list[str]) -> Path:
    carpeta.mkdir(exist_ok=True)
    for nombre in nombres:
        (carpeta / nombre).write_text("int x;\n", encoding="utf-8")
    return carpeta


def escribir_opciones(raiz: Path, texto: str) -> None:
    (raiz / "config").mkdir(parents=True, exist_ok=True)
    (raiz / infra.OPCIONES_COMPILACION).write_text(texto, encoding="utf-8")

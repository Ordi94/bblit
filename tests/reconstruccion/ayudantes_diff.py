"""Ayudantes del consumidor: asm de una funcion, ejecutor de ``diff`` y repositorio con dos archivos."""

import json
from pathlib import Path
from typing import Any

import pytest

from .test_compilacion import SALIDA_OBJDUMP, EjecutorC

ASM_FUNCION = """
nonmatching func_80036204, 0x4C

glabel func_80036204
    /* 22004 80036204 21188000 */  addu       $v1, $a0, $zero
    /* 22010 80036210 0D004010 */  beqz       $v0, .L80036248
    /* 22030 80036230 0800E003 */  jr         $ra
    /* 22034 80036234 000040AC */   sw        $zero, 0x0($v0)
  .L80036248:
    /* 22048 80036248 0800E003 */  jr         $ra
    /* 2204C 8003624C 21100000 */   addu      $v0, $zero, $zero
endlabel func_80036204
"""


class EjecutorDiff(EjecutorC):
    """Simula el ensamblador, el compilador y asm-differ con una puntuacion configurable."""

    def __init__(self, puntuacion: int, json_valido: bool = True, filas: list[Any] | None = None) -> None:
        super().__init__(secciones=SALIDA_OBJDUMP)
        self.puntuacion = puntuacion
        self.json_valido = json_valido
        self.filas = filas

    def __call__(self, comando: Any, directorio: Any, timeout_s: Any) -> Any:
        super().__call__(comando, directorio, timeout_s)
        if "--format=json" in comando:
            if not self.json_valido:
                return "basura"
            salida: dict[str, Any] = {"current_score": self.puntuacion}
            if self.filas is not None:
                salida["rows"] = self.filas
            return json.dumps(salida)
        if "--format=plain" in comando:
            return "TARGET   CURRENT\nfila\n\n"
        return ""


@pytest.fixture
def repo_diff(tmp_path: Path) -> Any:
    raiz = tmp_path / "repo con espacios (x)"
    (raiz / "src").mkdir(parents=True)
    (raiz / "src" / "code_a.c").write_text(
        'INCLUDE_ASM("asm/nonmatchings/code_a", func_ASM);\n'
        "s32 func_80036204(s32 x)\n{\n    return x;\n}\n"
        "#ifdef NON_MATCHING\ns32 func_NM(s32 x)\n{\n    return x;\n}\n#else\n"
        'INCLUDE_ASM("asm/nonmatchings/code_a", func_NM);\n#endif\n',
        encoding="utf-8",
    )
    (raiz / "asm" / "matchings" / "code_a").mkdir(parents=True)
    (raiz / "asm" / "matchings" / "code_a" / "func_80036204.s").write_text(ASM_FUNCION, encoding="utf-8")
    (raiz / "asm" / "nonmatchings" / "code_a").mkdir(parents=True)
    (raiz / "asm" / "nonmatchings" / "code_a" / "func_NM.s").write_text(ASM_FUNCION, encoding="utf-8")
    return raiz

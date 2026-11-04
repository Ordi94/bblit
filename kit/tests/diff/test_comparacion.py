import json
import re
from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import diff
from tools.reconstruccion.diff import FuncionSinCError

from .test_compilacion import SALIDA_OBJDUMP, EjecutorC, herramientas_compilacion

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


def test_validar_funcion_acepta_identificadores_y_rechaza_el_resto() -> None:
    assert diff.validar_funcion("func_80036204") == "func_80036204"
    for malo in ("", "1abc", "a-b", "a b", "../x", "x" * 65, "a;b"):
        with pytest.raises(ValueError, match="identificador C de hasta 64 caracteres"):
            diff.validar_funcion(malo)


def test_contar_retornos_cuenta_solo_instrucciones_jr_ra() -> None:
    assert diff.contar_retornos(ASM_FUNCION) == 2
    assert diff.contar_retornos("    /* 0 0 0 */  jr         $v0\n") == 0
    assert diff.contar_retornos("# jr $ra en un comentario\n") == 0


def test_envoltorio_objetivo_carga_macros_y_el_asm() -> None:
    assert diff.envoltorio_objetivo("asm/matchings/a/f.s") == (
        '.include "macro.inc"\n.section .text\n.set noat\n.set noreorder\n.include "asm/matchings/a/f.s"\n'
    )


def test_texto_diff_settings_es_python_valido_y_escapa_la_ruta() -> None:
    ruta = Path("C:\\Mi Carpeta (x86)\\objdump.exe")
    texto = diff.texto_diff_settings(ruta)
    espacio: dict[str, Any] = {}
    exec(texto, espacio)  # noqa: S102 - el modulo generado es el objeto de la prueba
    config: dict[str, Any] = {}
    espacio["apply"](config, None)
    assert config["arch"] == "mipsel"
    assert config["objdump_executable"] == str(ruta)


def test_comando_diff_corta_en_tantos_retornos_como_el_original() -> None:
    comando = diff.comando_diff("py", Path("diff.py"), "c.o", "t.o", "func_X", retornos=3, formato="json")
    assert comando == [
        "py",
        "diff.py",
        "-o",
        "--file",
        "c.o",
        "--ref-file",
        "t.o",
        "--no-pager",
        "--max-lines=1024",
        "--format=json",
        "-s",
        "-s",
        "-s",
        "func_X",
    ]
    sin_retornos = diff.comando_diff("py", Path("diff.py"), "c.o", "t.o", "f", retornos=0, formato="plain")
    assert sin_retornos.count("-s") == 1
    with pytest.raises(ValueError, match="'json' o 'plain'"):
        diff.comando_diff("py", Path("diff.py"), "c.o", "t.o", "f", retornos=1, formato="html")


@pytest.mark.parametrize(
    "salida",
    ["no es json", "[]", '{"current_score": "0"}', '{"current_score": -1}', '{"current_score": true}', "{}"],
)
def test_puntuacion_desde_json_rechaza_formas_inesperadas(salida: Any) -> None:
    with pytest.raises(ValueError, match="asm-differ no"):
        diff.puntuacion_desde_json(salida)


def test_puntuacion_desde_json() -> None:
    assert diff.puntuacion_desde_json('{"current_score": 505, "rows": []}') == 505
    assert diff.puntuacion_desde_json('{"current_score": 0}') == 0


def test_elegir_asm_objetivo_prefiere_matchings_y_cae_a_nonmatchings() -> None:
    existentes = {"asm/matchings/code_a/f.s", "asm/nonmatchings/code_a/f.s", "asm/nonmatchings/code_a/g.s"}
    assert (
        diff.elegir_asm_objetivo("src/code_a.c", "f", existentes.__contains__) == "asm/matchings/code_a/f.s"
    )
    assert (
        diff.elegir_asm_objetivo("src/code_a.c", "g", existentes.__contains__)
        == "asm/nonmatchings/code_a/g.s"
    )
    with pytest.raises(FileNotFoundError, match=r"no existe el asm original de 'h'.*split"):
        diff.elegir_asm_objetivo("src/code_a.c", "h", existentes.__contains__)


def test_resultado_diff_coincide_solo_con_puntuacion_cero() -> None:
    assert diff.ResultadoDiff("f", "src/a.c", 0, "").coincide is True
    assert diff.ResultadoDiff("f", "src/a.c", 10, "").coincide is False


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


def test_comparar_funcion_ensambla_el_objetivo_compila_con_non_matching_y_lee_la_puntuacion(
    repo_diff: Any,
) -> None:
    ejecutor = EjecutorDiff(0)
    resultado = diff.comparar_funcion(
        repo_diff, "func_80036204", herramientas_compilacion(), Path("diff.py"), ejecutor
    )
    assert resultado == diff.ResultadoDiff(
        "func_80036204", "src/code_a.c", 0, "TARGET   CURRENT\nfila", puntuacion_asm=0
    )
    nombres = [Path(c[0]).name for c in ejecutor.comandos]
    assert nombres == ["as.exe", "CPPPSX.EXE", "CC1PSX.EXE", "py", "py", "py"]
    ensamblado = ejecutor.comandos[0]
    carpeta = ensamblado[-2].rsplit("/", 1)[0]
    assert re.fullmatch(r"build/diff/func_80036204-\d+-\w+", carpeta)
    assert ensamblado[-3:] == [
        "-o",
        f"{carpeta}/func_80036204.objetivo.o",
        f"{carpeta}/func_80036204.objetivo.s",
    ]
    assert "-DNON_MATCHING" in ejecutor.comandos[1]
    assert ejecutor.comandos[4][-1] == "func_80036204" and ejecutor.comandos[4].count("-s") == 2
    assert ejecutor.directorios[4] == repo_diff / carpeta
    # Los intermedios solo existen mientras dura la comparacion: la carpeta exclusiva se elimina.
    assert not (repo_diff / carpeta).exists()
    assert [p.name for p in (repo_diff / "build" / "diff").iterdir()] == ["func_80036204.resultado.json"]


def test_los_intermedios_de_la_comparacion_son_el_envoltorio_y_la_configuracion_de_asm_differ(
    repo_diff: Any,
) -> None:
    visto: dict[str, str] = {}

    class EjecutorEspia(EjecutorDiff):
        def __call__(self, comando: Any, directorio: Any, timeout_s: Any) -> Any:
            if "--format=json" in comando:
                visto["configuracion"] = (directorio / "diff_settings.py").read_text(encoding="utf-8")
                visto["envoltorio"] = (directorio / "func_80036204.objetivo.s").read_text(encoding="utf-8")
            return super().__call__(comando, directorio, timeout_s)

    diff.comparar_funcion(
        repo_diff, "func_80036204", herramientas_compilacion(), Path("diff.py"), EjecutorEspia(0)
    )
    assert '.include "asm/matchings/code_a/func_80036204.s"' in visto["envoltorio"]
    assert "objdump_executable" in visto["configuracion"]


def test_comparar_funcion_no_coincidente_usa_el_asm_pendiente_y_informa_la_puntuacion(repo_diff: Any) -> None:
    resultado = diff.comparar_funcion(
        repo_diff, "func_NM", herramientas_compilacion(), Path("diff.py"), EjecutorDiff(505)
    )
    assert resultado.puntuacion == 505 and resultado.coincide is False


def test_comparar_funcion_solo_en_include_asm_se_rechaza_sin_lanzar_procesos(repo_diff: Any) -> None:
    ejecutor = EjecutorDiff(0)
    with pytest.raises(FuncionSinCError, match="'func_ASM' sigue en INCLUDE_ASM"):
        diff.comparar_funcion(repo_diff, "func_ASM", herramientas_compilacion(), Path("diff.py"), ejecutor)
    assert ejecutor.comandos == []


def test_comparar_funcion_desconocida_nombre_invalido_y_sin_asm(repo_diff: Any) -> None:
    ejecutor = EjecutorDiff(0)
    with pytest.raises(ValueError, match="'func_nada' no figura en ningun archivo de src/"):
        diff.comparar_funcion(repo_diff, "func_nada", herramientas_compilacion(), Path("diff.py"), ejecutor)
    with pytest.raises(ValueError, match="identificador C"):
        diff.comparar_funcion(repo_diff, "../x", herramientas_compilacion(), Path("diff.py"), ejecutor)
    (repo_diff / "asm" / "matchings" / "code_a" / "func_80036204.s").unlink()
    with pytest.raises(FileNotFoundError, match="ejecute primero 'split'"):
        diff.comparar_funcion(
            repo_diff, "func_80036204", herramientas_compilacion(), Path("diff.py"), ejecutor
        )
    assert ejecutor.comandos == []


def test_comparar_funcion_con_salida_ilegible_de_asm_differ(repo_diff: Any) -> None:
    with pytest.raises(ValueError, match="asm-differ no devolvio JSON valido"):
        diff.comparar_funcion(
            repo_diff,
            "func_80036204",
            herramientas_compilacion(),
            Path("diff.py"),
            EjecutorDiff(0, json_valido=False),
        )

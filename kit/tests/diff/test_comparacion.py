"""Comparacion de una funcion compilada contra su objetivo, con las rutas y convenciones de un proyecto."""

import json
import re
from pathlib import Path
from typing import Any

import pytest
from psxdecomp.construccion.compilacion import HerramientasCompilacion
from psxdecomp.diff import comparacion as diff
from psxdecomp.diff.comparacion import FuncionSinCError
from psxdecomp.dominio import Convenciones, construir_compilacion, construir_convenciones, construir_rutas

from construccion.test_compilacion import SALIDA_OBJDUMP, Ejecutor, herramientas

RUTAS = construir_rutas(
    {
        "fuentes": "codigo",
        "asm_coincidente": "ensamblador/cerradas",
        "asm_pendiente": "ensamblador/pendientes",
        "macros": "ensamblador/macros",
        "build": "salida",
        "simbolos": ["datos/simbolos.txt"],
    }
)
CONVENCIONES = construir_convenciones({})
COMPILACION = construir_compilacion({})
EJECUTABLE = "EJEC_001.00"

ASM_FUNCION = """
nonmatching rutina_a, 0x4C

glabel rutina_a
    /* 100 80100100 21188000 */  addu       $v1, $a0, $zero
    /* 110 80100110 0D004010 */  beqz       $v0, .L80100148
    /* 130 80100130 0800E003 */  jr         $ra
    /* 134 80100134 000040AC */   sw        $zero, 0x0($v0)
  .L80100148:
    /* 148 80100148 0800E003 */  jr         $ra
    /* 14C 8010014C 21100000 */   addu      $v0, $zero, $zero
endlabel rutina_a
"""


def test_validar_funcion_acepta_identificadores_y_rechaza_el_resto() -> None:
    assert diff.validar_funcion("rutina_a") == "rutina_a"
    for malo in ("", "1abc", "a-b", "a b", "../x", "x" * 65, "a;b"):
        with pytest.raises(ValueError, match="identificador C de hasta 64 caracteres"):
            diff.validar_funcion(malo)


def test_contar_retornos_cuenta_solo_instrucciones_jr_ra() -> None:
    assert diff.contar_retornos(ASM_FUNCION) == 2
    assert diff.contar_retornos("    /* 0 0 0 */  jr         $v0\n") == 0
    assert diff.contar_retornos("# jr $ra en un comentario\n") == 0


def test_contar_instrucciones_y_limite_de_lineas() -> None:
    assert diff.contar_instrucciones(ASM_FUNCION) == 6
    assert diff.limite_lineas(0) == diff.LIMITE_MINIMO_LINEAS
    assert diff.limite_lineas(4971) == 4971 + diff.MARGEN_LINEAS
    with pytest.raises(ValueError, match="no puede ser negativo"):
        diff.limite_lineas(-1)


def test_envoltorio_objetivo_carga_macros_y_el_asm() -> None:
    assert diff.envoltorio_objetivo("ensamblador/cerradas/a/f.s") == (
        '.include "macro.inc"\n.section .text\n.set noat\n.set noreorder\n'
        '.include "ensamblador/cerradas/a/f.s"\n'
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
    comando = diff.comando_diff("py", Path("diff.py"), "c.o", "t.o", "rutina_a", retornos=3, formato="json")
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
        "rutina_a",
    ]
    sin_retornos = diff.comando_diff("py", Path("diff.py"), "c.o", "t.o", "f", retornos=0, formato="plain")
    assert sin_retornos.count("-s") == 1
    with pytest.raises(ValueError, match="'json' o 'plain'"):
        diff.comando_diff("py", Path("diff.py"), "c.o", "t.o", "f", retornos=1, formato="html")
    with pytest.raises(ValueError, match="limite de lineas debe ser positivo"):
        diff.comando_diff("py", Path("d.py"), "c.o", "t.o", "f", retornos=1, formato="json", max_lineas=0)


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


def fila(mnemonico: str) -> dict[str, Any]:
    return {"current": {"mnemonic": mnemonico}}


def test_salida_truncada_reconoce_la_fila_de_corte_o_el_limite_alcanzado() -> None:
    assert diff.salida_truncada(json.dumps({"rows": [fila("nop"), fila("...")]}), 1024) is True
    assert diff.salida_truncada(json.dumps({"rows": [fila("nop")] * 3}), 3) is True
    assert diff.salida_truncada(json.dumps({"rows": [fila("nop")] * 2}), 3) is False
    etiquetas = [fila("<label>"), fila("<data-ref>"), fila("ERROR")]
    assert diff.salida_truncada(json.dumps({"rows": etiquetas}), 1) is False
    assert diff.salida_truncada(json.dumps({"rows": [None, {"current": None}, {"current": {}}]}), 1) is False
    assert diff.salida_truncada(json.dumps({"rows": "no es lista"}), 1) is False
    assert diff.salida_truncada(json.dumps({}), 1) is False


def test_elegir_asm_objetivo_prefiere_las_cerradas_y_cae_a_las_pendientes() -> None:
    existentes = {
        "ensamblador/cerradas/modulo_a/f.s",
        "ensamblador/pendientes/modulo_a/f.s",
        "ensamblador/pendientes/modulo_a/g.s",
    }
    assert (
        diff.elegir_asm_objetivo("codigo/modulo_a.c", "f", existentes.__contains__, rutas=RUTAS)
        == "ensamblador/cerradas/modulo_a/f.s"
    )
    assert (
        diff.elegir_asm_objetivo("codigo/modulo_a.c", "g", existentes.__contains__, rutas=RUTAS)
        == "ensamblador/pendientes/modulo_a/g.s"
    )
    with pytest.raises(FileNotFoundError, match=r"no existe el asm original de 'h'.*split"):
        diff.elegir_asm_objetivo("codigo/modulo_a.c", "h", existentes.__contains__, rutas=RUTAS)


def test_resultado_diff_coincide_solo_con_puntuacion_cero_o_bytes_iguales() -> None:
    assert diff.ResultadoDiff("f", "codigo/a.c", 0, "").coincide is True
    assert diff.ResultadoDiff("f", "codigo/a.c", 10, "").coincide is False
    assert diff.ResultadoDiff("f", "codigo/a.c", 10, "", bytes_iguales=True).coincide is True
    assert diff.ResultadoDiff("f", "codigo/a.c", 0, "", truncado=True).coincide is False


def comparar_funcion(
    raiz: Path,
    funcion: str,
    herramientas_c: HerramientasCompilacion,
    script_diff: Path,
    ejecutar: Any,
    *,
    convenciones: Convenciones = CONVENCIONES,
) -> diff.ResultadoDiff:
    """Compara una funcion con las rutas, la cadena de compilacion y el ejecutable de estas pruebas."""
    return diff.comparar_funcion(
        raiz,
        funcion,
        herramientas_c,
        script_diff,
        ejecutar,
        rutas=RUTAS,
        convenciones=convenciones,
        compilacion=COMPILACION,
        nombre_ejecutable=EJECUTABLE,
    )


class EjecutorDiff(Ejecutor):
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
    (raiz / "codigo").mkdir(parents=True)
    (raiz / "codigo" / "modulo_a.c").write_text(
        'INCLUDE_ASM("ensamblador/pendientes/modulo_a", rutina_ensamblador);\n'
        "s32 rutina_a(s32 x)\n{\n    return x;\n}\n"
        "#ifdef NON_MATCHING\ns32 rutina_pendiente(s32 x)\n{\n    return x;\n}\n#else\n"
        'INCLUDE_ASM("ensamblador/pendientes/modulo_a", rutina_pendiente);\n#endif\n',
        encoding="utf-8",
    )
    (raiz / "ensamblador" / "cerradas" / "modulo_a").mkdir(parents=True)
    (raiz / "ensamblador" / "cerradas" / "modulo_a" / "rutina_a.s").write_text(ASM_FUNCION, encoding="utf-8")
    (raiz / "ensamblador" / "pendientes" / "modulo_a").mkdir(parents=True)
    (raiz / "ensamblador" / "pendientes" / "modulo_a" / "rutina_pendiente.s").write_text(
        ASM_FUNCION, encoding="utf-8"
    )
    return raiz


def test_comparar_funcion_ensambla_el_objetivo_compila_con_la_macro_y_lee_la_puntuacion(
    repo_diff: Any,
) -> None:
    ejecutor = EjecutorDiff(0)
    resultado = comparar_funcion(repo_diff, "rutina_a", herramientas(), Path("diff.py"), ejecutor)
    assert resultado == diff.ResultadoDiff(
        "rutina_a", "codigo/modulo_a.c", 0, "TARGET   CURRENT\nfila", puntuacion_asm=0
    )
    nombres = [Path(c[0]).name for c in ejecutor.comandos]
    assert nombres == ["as.exe", "CPPPSX.EXE", "CC1PSX.EXE", "py", "py", "py"]
    ensamblado = ejecutor.comandos[0]
    carpeta = ensamblado[-2].rsplit("/", 1)[0]
    assert re.fullmatch(r"salida/diff/rutina_a-\d+-\w+", carpeta)
    assert ensamblado[-3:] == [
        "-o",
        f"{carpeta}/rutina_a.objetivo.o",
        f"{carpeta}/rutina_a.objetivo.s",
    ]
    assert "ensamblador/macros" in ensamblado
    assert "-DNON_MATCHING" in ejecutor.comandos[1]
    assert ejecutor.comandos[4][-1] == "rutina_a" and ejecutor.comandos[4].count("-s") == 2
    assert ejecutor.directorios[4] == repo_diff / carpeta
    # Los intermedios solo existen mientras dura la comparacion: la carpeta exclusiva se elimina.
    assert not (repo_diff / carpeta).exists()
    assert [p.name for p in (repo_diff / "salida" / "diff").iterdir()] == ["rutina_a.resultado.json"]


def test_la_macro_de_intentos_pendientes_la_fija_la_convencion_del_proyecto(repo_diff: Any) -> None:
    (repo_diff / "codigo" / "modulo_a.c").write_text(
        "#ifdef INTENTO\ns32 rutina_pendiente(s32 x)\n{\n    return x;\n}\n#else\n"
        'INCLUDE_ASM("ensamblador/pendientes/modulo_a", rutina_pendiente);\n#endif\n',
        encoding="utf-8",
    )
    ejecutor = EjecutorDiff(5)
    comparar_funcion(
        repo_diff,
        "rutina_pendiente",
        herramientas(),
        Path("diff.py"),
        ejecutor,
        convenciones=construir_convenciones({"macro_no_coincidente": "INTENTO"}),
    )
    assert "-DINTENTO" in ejecutor.comandos[1] and "-DNON_MATCHING" not in ejecutor.comandos[1]


def test_los_intermedios_de_la_comparacion_son_el_envoltorio_y_la_configuracion_de_asm_differ(
    repo_diff: Any,
) -> None:
    visto: dict[str, str] = {}

    class EjecutorEspia(EjecutorDiff):
        def __call__(self, comando: Any, directorio: Any, timeout_s: Any) -> Any:
            if "--format=json" in comando:
                visto["configuracion"] = (directorio / "diff_settings.py").read_text(encoding="utf-8")
                visto["envoltorio"] = (directorio / "rutina_a.objetivo.s").read_text(encoding="utf-8")
            return super().__call__(comando, directorio, timeout_s)

    comparar_funcion(repo_diff, "rutina_a", herramientas(), Path("diff.py"), EjecutorEspia(0))
    assert '.include "ensamblador/cerradas/modulo_a/rutina_a.s"' in visto["envoltorio"]
    assert "objdump_executable" in visto["configuracion"]


def test_comparar_funcion_pendiente_usa_el_asm_pendiente_y_informa_la_puntuacion(repo_diff: Any) -> None:
    resultado = comparar_funcion(
        repo_diff, "rutina_pendiente", herramientas(), Path("diff.py"), EjecutorDiff(505)
    )
    assert resultado.puntuacion == 505 and resultado.coincide is False
    guardado = json.loads(
        (repo_diff / diff.ruta_resultado("rutina_pendiente", rutas=RUTAS)).read_text("utf-8")
    )
    assert guardado == {
        "funcion": "rutina_pendiente",
        "puntuacion": 505,
        "maxLineas": 1024,
        "truncado": False,
    }


def test_comparar_funcion_solo_en_ensamblador_se_rechaza_sin_lanzar_procesos(repo_diff: Any) -> None:
    ejecutor = EjecutorDiff(0)
    with pytest.raises(FuncionSinCError, match="'rutina_ensamblador' sigue en INCLUDE_ASM"):
        comparar_funcion(repo_diff, "rutina_ensamblador", herramientas(), Path("diff.py"), ejecutor)
    assert ejecutor.comandos == []


def test_comparar_funcion_desconocida_nombre_invalido_y_sin_asm(repo_diff: Any) -> None:
    ejecutor = EjecutorDiff(0)
    with pytest.raises(ValueError, match="'rutina_nada' no figura en ningun archivo de codigo/"):
        comparar_funcion(repo_diff, "rutina_nada", herramientas(), Path("diff.py"), ejecutor)
    with pytest.raises(ValueError, match="identificador C"):
        comparar_funcion(repo_diff, "../x", herramientas(), Path("diff.py"), ejecutor)
    (repo_diff / "ensamblador" / "cerradas" / "modulo_a" / "rutina_a.s").unlink()
    with pytest.raises(FileNotFoundError, match="ejecute primero 'split'"):
        comparar_funcion(repo_diff, "rutina_a", herramientas(), Path("diff.py"), ejecutor)
    assert ejecutor.comandos == []


def test_comparar_funcion_con_salida_ilegible_de_asm_differ(repo_diff: Any) -> None:
    with pytest.raises(ValueError, match="asm-differ no devolvio JSON valido"):
        comparar_funcion(
            repo_diff,
            "rutina_a",
            herramientas(),
            Path("diff.py"),
            EjecutorDiff(0, json_valido=False),
        )


def test_guardar_resultado_es_atomico_y_no_deja_temporales_si_falla(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    diff.guardar_resultado(tmp_path, "rutina_a", 7, 1024, rutas=RUTAS, truncado=True)
    ruta = tmp_path / diff.ruta_resultado("rutina_a", rutas=RUTAS)
    assert json.loads(ruta.read_text("utf-8")) == {
        "funcion": "rutina_a",
        "puntuacion": 7,
        "maxLineas": 1024,
        "truncado": True,
    }

    def falla(origen: Any, destino: Any) -> None:
        raise OSError("disco lleno")

    monkeypatch.setattr("psxdecomp.diff.comparacion.os.replace", falla)
    with pytest.raises(OSError, match="disco lleno"):
        diff.guardar_resultado(tmp_path, "rutina_a", 9, 1024, rutas=RUTAS)
    assert [p.name for p in ruta.parent.iterdir()] == ["rutina_a.resultado.json"]
    assert json.loads(ruta.read_text("utf-8"))["puntuacion"] == 7


def test_dos_comparaciones_de_la_misma_funcion_usan_carpetas_de_trabajo_distintas(tmp_path: Path) -> None:
    with (
        diff.carpeta_de_trabajo(tmp_path, "rutina_a", rutas=RUTAS) as primera,
        diff.carpeta_de_trabajo(tmp_path, "rutina_a", rutas=RUTAS) as segunda,
    ):
        assert primera != segunda
        assert (tmp_path / primera).is_dir() and (tmp_path / segunda).is_dir()
    assert not (tmp_path / primera).exists() and not (tmp_path / segunda).exists()


def test_preparar_objetivo_devuelve_retornos_y_limite_de_la_funcion(repo_diff: Any) -> None:
    ejecutor = EjecutorDiff(0)
    objetivo, retornos, max_lineas = diff.preparar_objetivo(
        repo_diff,
        "rutina_a",
        "codigo/modulo_a.c",
        herramientas(),
        ejecutor,
        carpeta="salida/diff/x",
        rutas=RUTAS,
    )
    assert objetivo == "salida/diff/x/rutina_a.objetivo.o"
    assert (retornos, max_lineas) == (2, diff.LIMITE_MINIMO_LINEAS)
    assert (repo_diff / "salida/diff/x/rutina_a.objetivo.s").is_file()

"""Reglas de negocio del limite de lineas de ``diff``: la puntuacion cubre la funcion entera."""

import json
from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import cli, diff

from .test_compilacion import herramientas_compilacion
from .test_diff import ASM_FUNCION, EjecutorDiff, repo_diff  # noqa: F401 - fixture reutilizada
from .test_gp import EjecutorEnlace, crear_repo_diff, herramientas_con_enlace


def asm_sintetico(instrucciones: int) -> str:
    """Genera un ``.s`` con tantas instrucciones como se pida y un unico retorno al final."""
    filas = [f"    /* {i:X} {0x80036204 + 4 * i:08X} 00000000 */  nop" for i in range(instrucciones - 1)]
    filas.append(f"    /* F 80000000 0800E003 */  jr         $ra\n{'':4}")
    return "glabel func_80036204\n" + "\n".join(filas) + "\nendlabel func_80036204\n"


def limite_usado(ejecutor: EjecutorDiff) -> int:
    """Devuelve el valor de ``--max-lines`` con que se lanzo ``asm-differ``."""
    comando = next(c for c in ejecutor.comandos if "--format=json" in c)
    return int(next(a for a in comando if a.startswith("--max-lines=")).split("=")[1])


def test_contar_instrucciones_incluye_huecos_de_salto_y_omite_etiquetas() -> None:
    assert diff.contar_instrucciones(ASM_FUNCION) == 6
    assert diff.contar_instrucciones("") == 0


@pytest.mark.parametrize(
    ("instrucciones", "esperado"),
    [(0, 1024), (1, 1024), (960, 1024), (961, 1025), (1738, 1802), (4971, 5035)],
)
def test_el_limite_es_instrucciones_mas_margen_y_nunca_menos_de_1024(
    instrucciones: int, esperado: int
) -> None:
    assert diff.limite_lineas(instrucciones) == esperado


def test_un_numero_de_instrucciones_negativo_se_rechaza() -> None:
    with pytest.raises(ValueError, match="no puede ser negativo"):
        diff.limite_lineas(-1)


@pytest.mark.parametrize("malo", [0, -5])
def test_un_limite_de_lineas_no_positivo_se_rechaza(malo: int) -> None:
    with pytest.raises(ValueError, match="positivo"):
        diff.comando_diff(
            "py", Path("diff.py"), "c.o", "t.o", "f", retornos=1, formato="json", max_lineas=malo
        )


def test_una_funcion_pequena_conserva_el_limite_por_omision(repo_diff: Any) -> None:  # noqa: F811
    ejecutor = EjecutorDiff(0)
    diff.comparar_funcion(repo_diff, "func_80036204", herramientas_compilacion(), Path("diff.py"), ejecutor)
    assert limite_usado(ejecutor) == 1024


def test_una_funcion_de_mas_de_1024_instrucciones_se_compara_entera(repo_diff: Any) -> None:  # noqa: F811
    ruta = repo_diff / "asm" / "matchings" / "code_a" / "func_80036204.s"
    ruta.write_text(asm_sintetico(2000), encoding="utf-8")
    ejecutor = EjecutorDiff(0)
    diff.comparar_funcion(repo_diff, "func_80036204", herramientas_compilacion(), Path("diff.py"), ejecutor)
    assert limite_usado(ejecutor) == 2064


def test_una_funcion_vacia_usa_el_limite_minimo(repo_diff: Any) -> None:  # noqa: F811
    ruta = repo_diff / "asm" / "matchings" / "code_a" / "func_80036204.s"
    ruta.write_text("glabel func_80036204\nendlabel func_80036204\n", encoding="utf-8")
    ejecutor = EjecutorDiff(0)
    diff.comparar_funcion(repo_diff, "func_80036204", herramientas_compilacion(), Path("diff.py"), ejecutor)
    assert limite_usado(ejecutor) == 1024


def test_preparar_objetivo_informa_el_limite_de_la_funcion(repo_diff: Any) -> None:  # noqa: F811
    ruta = repo_diff / "asm" / "matchings" / "code_a" / "func_80036204.s"
    ruta.write_text(asm_sintetico(1500), encoding="utf-8")
    objetivo, retornos, max_lineas = diff.preparar_objetivo(
        repo_diff, "func_80036204", "src/code_a.c", herramientas_compilacion(), EjecutorDiff(0)
    )
    assert (objetivo, retornos, max_lineas) == ("build/diff/func_80036204.objetivo.o", 1, 1564)


def fila(mnemonico: str | None) -> dict[str, Any]:
    """Fila de la salida JSON de ``asm-differ`` cuya columna del candidato tiene ese mnemonico."""
    columna: dict[str, Any] = {"text": []}
    if mnemonico is not None:
        columna["mnemonic"] = mnemonico
    return {"base": {"text": []}, "current": columna}


def comparar_con_filas(raiz: Path, filas: list[Any]) -> diff.ResultadoDiff:
    return diff.comparar_funcion(
        raiz, "func_80036204", herramientas_compilacion(), Path("diff.py"), EjecutorDiff(0, filas=filas)
    )


def test_si_el_candidato_llega_exactamente_al_limite_se_anota_el_truncado(repo_diff: Any) -> None:  # noqa: F811
    resultado = comparar_con_filas(repo_diff, [fila("addiu")] * 1024)
    assert resultado.truncado is True
    guardado = json.loads((repo_diff / diff.ruta_resultado("func_80036204")).read_text(encoding="utf-8"))
    assert guardado["truncado"] is True


def test_si_el_candidato_cabe_por_una_instruccion_no_hay_truncado(repo_diff: Any) -> None:  # noqa: F811
    resultado = comparar_con_filas(repo_diff, [fila("addiu")] * 1023)
    assert resultado.truncado is False
    guardado = json.loads((repo_diff / diff.ruta_resultado("func_80036204")).read_text(encoding="utf-8"))
    assert guardado["truncado"] is False


def test_la_fila_de_corte_de_asm_differ_basta_para_anotar_el_truncado(repo_diff: Any) -> None:  # noqa: F811
    assert comparar_con_filas(repo_diff, [fila("addiu"), fila("...")]).truncado is True


def test_etiquetas_referencias_a_datos_y_filas_sin_instruccion_no_cuentan_para_el_limite() -> None:
    filas = [fila("addiu")] * 1020 + [fila("<label>"), fila("<data-ref>"), fila("ERROR"), fila(None)]
    assert diff.salida_truncada(json.dumps({"rows": filas}), 1024) is False


@pytest.mark.parametrize(
    "salida",
    [{}, {"rows": "no es una lista"}, {"rows": [1, "x", {"current": 3}, {"current": {"mnemonic": 7}}]}],
)
def test_una_salida_sin_filas_validas_no_se_considera_truncada(salida: dict[str, Any]) -> None:
    assert diff.salida_truncada(json.dumps(salida), 1) is False


def test_diff_imprime_un_aviso_claro_si_la_salida_esta_truncada() -> None:
    parcial = diff.ResultadoDiff("f", "src/a.c", 70, "", truncado=True)
    completo = diff.ResultadoDiff("f", "src/a.c", 70, "")
    lineas = cli.resumir_comparacion(parcial)
    assert lineas[0].startswith("aviso: asm-differ corto el desensamblado") and "parciales" in lineas[0]
    assert lineas[-1] == "f (src/a.c): puntuacion 70"
    assert cli.resumir_comparacion(completo) == ["f (src/a.c): puntuacion 70"]
    con_bytes = diff.ResultadoDiff("f", "src/a.c", 0, "", True, 2, 70, True)
    assert len(cli.resumir_comparacion(con_bytes)) == 3


def test_el_truncado_se_distingue_con_el_limite_real_de_una_funcion_de_mas_de_1024_instrucciones(
    repo_diff: Any,  # noqa: F811
) -> None:
    ruta = repo_diff / "asm" / "matchings" / "code_a" / "func_80036204.s"
    ruta.write_text(asm_sintetico(1500), encoding="utf-8")
    limite = 1500 + diff.MARGEN_LINEAS
    exacto = comparar_con_filas(repo_diff, [fila("addiu")] * limite)
    uno_menos = comparar_con_filas(repo_diff, [fila("addiu")] * (limite - 1))
    con_el_minimo = comparar_con_filas(repo_diff, [fila("addiu")] * diff.LIMITE_MINIMO_LINEAS)
    assert exacto.truncado is True
    assert uno_menos.truncado is False
    assert con_el_minimo.truncado is False, "un candidato de 1024 filas cabe en el limite de 1564"


def comparar_truncado_con_enlace(raiz: Path, *, difiere: bool) -> diff.ResultadoDiff:
    """Compara con puntuacion parcial 0, candidato truncado y enlace byte a byte configurable."""
    ejecutor = EjecutorEnlace(0, difiere=difiere)
    ejecutor.filas = [fila("addiu")] * 1024
    return diff.comparar_funcion(raiz, "func_80036204", herramientas_con_enlace(), Path("diff.py"), ejecutor)


def test_puntuacion_cero_truncada_con_bytes_distintos_no_coincide(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    resultado = comparar_truncado_con_enlace(tmp_path, difiere=True)
    assert (resultado.puntuacion, resultado.truncado, resultado.bytes_iguales) == (0, True, False)
    assert resultado.coincide is False


def test_puntuacion_cero_truncada_con_bytes_iguales_coincide_porque_el_enlace_es_la_prueba_definitiva(
    tmp_path: Path,
) -> None:
    crear_repo_diff(tmp_path)
    resultado = comparar_truncado_con_enlace(tmp_path, difiere=False)
    assert (resultado.puntuacion, resultado.truncado, resultado.bytes_iguales) == (0, True, True)
    assert resultado.coincide is True, "el enlace de la funcion completa es la prueba definitiva"


def test_resultado_truncado_con_puntuacion_cero_no_coincide_sin_prueba_de_bytes() -> None:
    assert diff.ResultadoDiff("f", "src/a.c", 0, "", truncado=True).coincide is False
    assert diff.ResultadoDiff("f", "src/a.c", 0, "", truncado=False).coincide is True
    assert diff.ResultadoDiff("f", "src/a.c", 0, "", False, truncado=True).coincide is False


def test_puntuacion_cero_truncada_sin_poder_enlazar_no_coincide(repo_diff: Any) -> None:  # noqa: F811
    resultado = comparar_con_filas(repo_diff, [fila("addiu")] * 1024)
    assert (resultado.puntuacion, resultado.truncado, resultado.bytes_iguales) == (0, True, None)
    assert resultado.coincide is False

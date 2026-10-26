"""Reglas de negocio del limite de lineas de ``diff``: la puntuacion cubre la funcion entera."""

from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import diff

from .test_compilacion import herramientas_compilacion
from .test_diff import ASM_FUNCION, EjecutorDiff, repo_diff  # noqa: F401 - fixture reutilizada


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
def test_el_limite_es_instrucciones_mas_margen_y_nunca_menos_de_1024(instrucciones: int, esperado: int) -> None:
    assert diff.limite_lineas(instrucciones) == esperado


def test_un_numero_de_instrucciones_negativo_se_rechaza() -> None:
    with pytest.raises(ValueError, match="no puede ser negativo"):
        diff.limite_lineas(-1)


@pytest.mark.parametrize("malo", [0, -5])
def test_un_limite_de_lineas_no_positivo_se_rechaza(malo: int) -> None:
    with pytest.raises(ValueError, match="positivo"):
        diff.comando_diff("py", Path("diff.py"), "c.o", "t.o", "f", retornos=1, formato="json", max_lineas=malo)


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

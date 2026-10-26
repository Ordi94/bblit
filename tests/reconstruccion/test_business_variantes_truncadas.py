"""Reglas de negocio de ``probar``: una medicion cortada por ``asm-differ`` no es una coincidencia."""

from pathlib import Path
from typing import Any, ClassVar

import pytest
from tools.reconstruccion import diff, variantes
from tools.reconstruccion.variantes import ResultadoVariante

from .test_cli import ejecutar_cli, entorno_completo, entorno_repo  # noqa: F401 - fixtures reutilizadas
from .test_compilacion import SALIDA_OBJDUMP, herramientas_compilacion
from .test_variantes import EjecutorVariantes, crear_repo, crear_variantes


class EjecutorTruncando(EjecutorVariantes):
    """Una variante llega exactamente al limite de filas y otra queda una por debajo."""

    PUNTUACIONES: ClassVar[dict[str, int]] = {"cortada.c": 0, "completa.c": 0}
    FILAS: ClassVar[dict[str, int]] = {
        "cortada.c": diff.LIMITE_MINIMO_LINEAS,
        "completa.c": diff.LIMITE_MINIMO_LINEAS - 1,
    }


def test_una_variante_truncada_con_puntuacion_cero_no_se_reporta_como_coincidente(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    crear_repo(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["cortada.c", "completa.c"])
    resultados = variantes.probar_variantes(
        raiz,
        "func_80036204",
        carpeta,
        herramientas_compilacion(),
        script_diff=Path("diff.py"),
        ejecutar=EjecutorTruncando(secciones=SALIDA_OBJDUMP),
    )
    assert [(r.nombre, r.puntuacion, r.truncado, r.coincide) for r in resultados] == [
        ("completa.c", 0, False, True),
        ("cortada.c", 0, True, False),
    ]
    assert variantes.formatear_tabla(resultados).splitlines() == [
        "variante    puntuacion",
        "completa.c  0",
        "cortada.c   0 (medicion truncada)",
    ]


def test_una_variante_truncada_no_gana_a_una_completa_peor_puntuada() -> None:
    resultados = [ResultadoVariante("a.c", 0, truncado=True), ResultadoVariante("b.c", 40)]
    ordenados = variantes.ordenar_resultados(resultados)
    assert [r.nombre for r in ordenados] == ["b.c", "a.c"]
    assert ordenados[0].coincide is False
    assert not ResultadoVariante("c.c", 50, bytes_iguales=True, truncado=True).coincide


def test_probar_por_linea_de_ordenes_falla_si_la_unica_variante_con_cero_esta_truncada(
    entorno_completo: Any,  # noqa: F811
    capsys: pytest.CaptureFixture[str],
) -> None:
    raiz, variables = entorno_completo
    crear_repo(raiz)
    carpeta = crear_variantes(raiz.parent / "variantes", ["cortada.c"])
    capsys.readouterr()
    codigo = ejecutar_cli(
        raiz, variables, "probar", "func_80036204", str(carpeta), ejecutor=EjecutorTruncando()
    )
    assert codigo == 1
    assert capsys.readouterr().out.splitlines()[1] == "cortada.c  0 (medicion truncada)"

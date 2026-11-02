from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import cli

from .ayudantes_permutar import ARCHIVO_C, ASM_FUNCION, FUNCION, EjecutorPermutar
from .test_cli import ejecutar_cli, entorno_completo, entorno_repo  # noqa: F401 - fixtures y ayudante


def test_el_analizador_de_argumentos_acepta_las_opciones_de_permutar() -> None:
    args = cli.construir_parser().parse_args(
        [
            "permutar",
            FUNCION,
            "--iteraciones",
            "50",
            "--minutos",
            "2.5",
            "--procesos",
            "4",
            "--semilla",
            "7",
            "--reanudar",
        ]
    )
    assert (args.orden, args.funcion, args.iteraciones, args.minutos) == ("permutar", FUNCION, 50, 2.5)
    assert (args.procesos, args.semilla, args.reanudar) == (4, 7, True)
    por_omision = cli.construir_parser().parse_args(["permutar", FUNCION])
    assert (por_omision.iteraciones, por_omision.minutos, por_omision.procesos) == (None, None, 1)
    assert por_omision.semilla is None and por_omision.reanudar is False


def preparar_repositorio(raiz: Path) -> None:
    (raiz / "src").mkdir(exist_ok=True)
    (raiz / "src" / "code_a.c").write_text(ARCHIVO_C, encoding="utf-8")
    (raiz / "asm" / "nonmatchings" / "code_a").mkdir(parents=True, exist_ok=True)
    (raiz / "asm" / "nonmatchings" / "code_a" / f"{FUNCION}.s").write_text(ASM_FUNCION, encoding="utf-8")
    (raiz / "build").mkdir(exist_ok=True)
    (raiz / "build" / "SLUS_008.elf").write_bytes(b"elf")


def test_permutar_imprime_el_resumen_y_el_codigo_depende_del_resultado(
    entorno_completo: Any,  # noqa: F811
    capsys: pytest.CaptureFixture[str],
) -> None:
    raiz, variables = entorno_completo
    preparar_repositorio(raiz)
    capsys.readouterr()
    mejora = EjecutorPermutar(lambda texto: 40 - 10 * texto.count("tmp1 ="))
    argumentos = ("permutar", FUNCION, "--iteraciones", "30", "--procesos", "2", "--semilla", "3")
    assert ejecutar_cli(raiz, variables, *argumentos, ejecutor=mejora) == 1
    salida = capsys.readouterr().out
    assert "iteraciones en" in salida and "(2 procesos, semilla 3)" in salida
    assert "puntuacion de partida 40, mejor" in salida
    assert "candidato: build/permutar/func_80036204/mejor.c" in salida
    sin_mejora = EjecutorPermutar(lambda texto: 40)
    assert ejecutar_cli(raiz, variables, "permutar", FUNCION, "--iteraciones", "5", ejecutor=sin_mejora) == 2
    assert "(sin mejora)" in capsys.readouterr().out
    cierra = EjecutorPermutar(lambda texto: 0)
    assert ejecutar_cli(raiz, variables, "permutar", FUNCION, "--iteraciones", "5", ejecutor=cierra) == 0
    assert "(coincide con el original)" in capsys.readouterr().out


def test_permutar_informa_los_errores_de_uso_sin_traza(
    entorno_completo: Any,  # noqa: F811
    capsys: pytest.CaptureFixture[str],
) -> None:
    raiz, variables = entorno_completo
    preparar_repositorio(raiz)
    capsys.readouterr()
    ejecutor = EjecutorPermutar()
    assert ejecutar_cli(raiz, variables, "permutar", FUNCION, "--procesos", "0", ejecutor=ejecutor) == 1
    assert "error: --procesos debe estar entre 1 y 16" in capsys.readouterr().err
    assert (
        ejecutar_cli(
            raiz, variables, "permutar", FUNCION, "--reanudar", "--iteraciones", "3", ejecutor=ejecutor
        )
        == 1
    )
    assert "no hay una busqueda anterior" in capsys.readouterr().err
    (raiz / "build" / "SLUS_008.elf").unlink()
    assert ejecutar_cli(raiz, variables, "permutar", FUNCION, "--iteraciones", "3", ejecutor=ejecutor) == 1
    assert "ejecute 'build' antes de permutar" in capsys.readouterr().err

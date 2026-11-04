"""Reglas de la linea de ordenes: codigos de salida, flujos de texto y ejecucion como modulo."""

import runpy

import pytest
from psxdecomp.cli import main

from manifiestos_de_prueba import MANIFIESTO_MINIMO, EscribirManifiesto


def test_comprobar_imprime_el_resumen_y_sale_con_cero(
    escribir_manifiesto: EscribirManifiesto, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz = escribir_manifiesto(MANIFIESTO_MINIMO)
    assert main(["comprobar", str(raiz)]) == 0
    assert "proyecto: demo" in capsys.readouterr().out


def test_comprobar_sin_ruta_usa_la_carpeta_actual(
    escribir_manifiesto: EscribirManifiesto,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(escribir_manifiesto(MANIFIESTO_MINIMO))
    assert main(["comprobar"]) == 0
    assert "ejecutable: EJEC_001.00" in capsys.readouterr().out


def test_comprobar_un_manifiesto_invalido_sale_con_uno_y_el_error_va_a_stderr(
    escribir_manifiesto: EscribirManifiesto, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz = escribir_manifiesto("[proyecto]\n")
    assert main(["comprobar", str(raiz)]) == 1
    captura = capsys.readouterr()
    assert captura.out == ""
    assert captura.err.startswith("error: psxdecomp.toml:")
    assert str(raiz) not in captura.err


def test_sin_la_opcion_comprobar_se_muestra_el_uso_y_sale_con_dos(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err


def test_main_sin_argumentos_explicitos_lee_los_de_la_linea_de_ordenes(
    escribir_manifiesto: EscribirManifiesto,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raiz = escribir_manifiesto(MANIFIESTO_MINIMO)
    monkeypatch.setattr("sys.argv", ["psxdecomp.cli", "comprobar", str(raiz)])
    assert main() == 0
    assert "proyecto: demo" in capsys.readouterr().out


@pytest.mark.filterwarnings("ignore:.*found in sys.modules:RuntimeWarning")
def test_el_modulo_ejecutado_con_menos_m_termina_con_el_codigo_de_main(
    escribir_manifiesto: EscribirManifiesto, monkeypatch: pytest.MonkeyPatch
) -> None:
    raiz = escribir_manifiesto(MANIFIESTO_MINIMO)
    monkeypatch.setattr("sys.argv", ["psxdecomp.cli", "comprobar", str(raiz)])
    with pytest.raises(SystemExit) as salida:
        runpy.run_module("psxdecomp.cli", run_name="__main__")
    assert salida.value.code == 0

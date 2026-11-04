"""Reglas de la linea de ordenes: codigos de salida, flujos de texto y ejecucion como modulo."""

import importlib
import runpy

import pytest
from psxdecomp.cli import describir_error_de_sistema, main, motivo_sin_rutas

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


def test_importar_el_modulo_de_entrada_no_ejecuta_la_linea_de_ordenes() -> None:
    modulo = importlib.import_module("psxdecomp.cli.__main__")
    assert modulo.main is main


def test_motivo_sin_rutas_conserva_solo_la_descripcion_del_sistema() -> None:
    assert motivo_sin_rutas(PermissionError(13, "Acceso denegado", "C:/privado/a.bin")) == "Acceso denegado"
    assert motivo_sin_rutas(OSError(5, "", "C:/privado/a.bin")) == "OSError"
    assert motivo_sin_rutas(ValueError("mensaje propio")) == "mensaje propio"
    assert motivo_sin_rutas(OSError("sin nombre de archivo")) == "sin nombre de archivo"


def test_describir_error_de_sistema_nunca_incluye_el_directorio() -> None:
    assert describir_error_de_sistema(FileNotFoundError("falta el archivo de simbolos")) == (
        "falta el archivo de simbolos"
    )
    assert describir_error_de_sistema(PermissionError(13, "Acceso denegado", "C:/privado/a.bin")) == (
        "error de entrada/salida: PermissionError (Acceso denegado): a.bin"
    )
    assert describir_error_de_sistema(OSError(5, "")) == "error de entrada/salida: OSError"
    assert describir_error_de_sistema(OSError(5, "Fallo")) == "error de entrada/salida: OSError (Fallo)"

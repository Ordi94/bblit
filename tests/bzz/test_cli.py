"""Pruebas de la interfaz de linea de comandos."""

import json
import runpy
import sys
from pathlib import Path

import pytest
from tools.bzz import cli

from tests.bzz.ayudantes import construir_bzz, flujo_literales


def test_desempaquetar_informa_cuantas_secciones_escribio(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    origen = tmp_path / "X.BZZ"
    origen.write_bytes(construir_bzz([(1, flujo_literales(b"a")), (2, flujo_literales(b"bc"))]))
    codigo = cli.main(["desempaquetar", str(origen), str(tmp_path / "salida")])
    assert codigo == 0
    assert capsys.readouterr().out == "2 secciones escritas\n"
    manifiesto = json.loads((tmp_path / "salida" / "manifiesto.json").read_text(encoding="utf-8"))
    assert [s["tipo"] for s in manifiesto["secciones"]] == [1, 2]


def test_inventario_informa_cuantas_secciones_inventario(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    carpeta = tmp_path / "fs"
    carpeta.mkdir()
    (carpeta / "X.BZZ").write_bytes(construir_bzz([(1, flujo_literales(b"a"))]))
    codigo = cli.main(["inventario", str(carpeta), str(tmp_path / "inv.csv")])
    assert codigo == 0
    assert capsys.readouterr().out == "1 secciones inventariadas\n"
    assert (
        (tmp_path / "inv.csv").read_text(encoding="utf-8").splitlines()[0].startswith("archivo,indice,tipo")
    )


def test_un_contenedor_invalido_devuelve_error_sin_rutas(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    origen = tmp_path / "MAL.BZZ"
    origen.write_bytes(bytes(0x800))
    codigo = cli.main(["desempaquetar", str(origen), str(tmp_path / "salida")])
    assert codigo == cli.CODIGO_ERROR
    capturado = capsys.readouterr()
    assert capturado.err == "error: version=0 no soportada, se esperaba 1\n"
    assert capturado.out == ""


def test_un_archivo_inexistente_devuelve_error_de_entrada_salida(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    codigo = cli.main(["desempaquetar", str(tmp_path / "NO_EXISTE.BZZ"), str(tmp_path / "salida")])
    assert codigo == cli.CODIGO_ERROR
    error = capsys.readouterr().err
    assert error.startswith("error de entrada/salida: ")
    assert str(tmp_path) not in error


def test_un_error_de_entrada_salida_sin_texto_usa_el_nombre_de_la_excepcion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fallar(*_: object) -> int:
        raise OSError

    monkeypatch.setattr(cli, "generar_inventario", fallar)
    assert cli.main(["inventario", str(tmp_path), str(tmp_path / "x.csv")]) == cli.CODIGO_ERROR
    assert capsys.readouterr().err == "error de entrada/salida: OSError\n"


def test_sin_orden_el_analizador_termina_con_codigo_dos() -> None:
    with pytest.raises(SystemExit) as salida:
        cli.main([])
    assert salida.value.code == 2


def test_el_modulo_se_ejecuta_como_programa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    carpeta = tmp_path / "fs"
    carpeta.mkdir()
    (carpeta / "X.BZZ").write_bytes(construir_bzz([(1, flujo_literales(b"a"))]))
    monkeypatch.setattr(sys, "argv", ["tools.bzz", "inventario", str(carpeta), str(tmp_path / "inv.csv")])
    with pytest.raises(SystemExit) as salida:
        runpy.run_module("tools.bzz", run_name="__main__")
    assert salida.value.code == 0

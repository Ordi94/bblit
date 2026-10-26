import csv
import io
from pathlib import Path

import pytest
from tools.ghidra import simbolos as modulo_simbolos
from tools.ghidra.cli import main
from tools.ghidra.dominio import Simbolo
from tools.ghidra.simbolos import COLUMNAS_NUEVAS, escribir_atomico, formatear_nuevas_csv

from tests.ghidra.ensamblaje import programa, retorno
from tests.ghidra.segmentos import escribir_ejecutable
from tests.ghidra.sintetica import csv_funciones, fila

M = 0x80020000


def test_escribir_atomico_reemplaza_el_archivo_y_no_deja_temporales(tmp_path: Path) -> None:
    destino = tmp_path / "symbols.txt"
    destino.write_text("anterior\n", encoding="utf-8")
    escribir_atomico(destino, "nuevo\n")
    assert destino.read_text(encoding="utf-8") == "nuevo\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["symbols.txt"]


def test_si_el_reemplazo_falla_queda_el_archivo_anterior_y_ningun_temporal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destino = tmp_path / "symbols.txt"
    destino.write_text("anterior\n", encoding="utf-8")

    def falla(_origen: Path, _destino: Path) -> None:
        raise OSError("disco lleno")

    monkeypatch.setattr(modulo_simbolos.os, "replace", falla)
    with pytest.raises(OSError, match="disco lleno"):
        escribir_atomico(destino, "nuevo\n")
    assert destino.read_text(encoding="utf-8") == "anterior\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["symbols.txt"]


def test_el_csv_de_funciones_nuevas_lista_las_partidas_y_las_fusionadas() -> None:
    simbolos = [Simbolo("func_80020000", M, "func", 8), Simbolo("func_80020008", M + 8, "func", 8)]
    texto = formatear_nuevas_csv([(M + 8, M)], [(M + 0x100, M)], simbolos, {M + 0x100: "func_80020100"})
    filas = list(csv.reader(io.StringIO(texto)))
    assert tuple(filas[0]) == COLUMNAS_NUEVAS
    assert filas[1] == ["0x80020008", "func_80020008", "8", "0x80020000", "func_80020000", "partida"]
    assert filas[2] == ["0x80020100", "func_80020100", "0", "0x80020000", "func_80020000", "fusionada"]
    assert texto.count("\n") == 3


@pytest.fixture
def entradas(tmp_path: Path) -> dict[str, Path]:
    """Un bloque de cuatro rutinas hoja y una funcion posterior; la tabla de punteros esta en los datos."""
    palabras = programa(M, [*retorno(), *retorno(), *retorno(), *retorno(), *retorno()])
    palabras |= programa(M + 40, retorno())
    for indice, destino in enumerate((M, M + 8, M + 16, M + 24, M + 32)):
        palabras[0x8005F000 + 4 * indice] = destino
    exe = escribir_ejecutable(tmp_path / "SLUS_008.38", palabras)
    filas = [
        fila(direccion=f"0x{M:08X}", nombre="FUN_80020000", tamano="40"),
        fila(direccion=f"0x{M + 40:08X}", nombre="FUN_80020028", tamano="8"),
    ]
    funciones = tmp_path / "funciones.csv"
    funciones.write_text(csv_funciones(filas), encoding="utf-8", newline="")
    return {"exe": exe, "funciones": funciones}


def _simbolos(entradas: dict[str, Path], destino: Path, *extra: str) -> list[str]:
    return [
        "simbolos",
        "--funciones",
        str(entradas["funciones"]),
        "--salida",
        str(destino),
        "--exe",
        str(entradas["exe"]),
        *extra,
    ]


def test_el_comando_simbolos_parte_el_bloque_y_escribe_las_dos_listas(
    tmp_path: Path, entradas: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    destino, tablas, nuevas = tmp_path / "symbols.txt", tmp_path / "tablas.csv", tmp_path / "nuevas.csv"
    assert main(_simbolos(entradas, destino, "--tablas", str(tablas), "--nuevas", str(nuevas))) == 0
    salida = capsys.readouterr().out.splitlines()
    assert salida[1] == (
        "tablas: 1 (1 de punteros a funcion, 0 de switch); 4 funciones nuevas, "
        "0 continuaciones fusionadas, 0 destinos no aplicados"
    )
    lineas = destino.read_text(encoding="utf-8").splitlines()
    assert [linea for linea in lineas if "size:0x8" in linea and "80020" in linea][:2] == [
        "func_80020000 = 0x80020000; // type:func size:0x8",
        "func_80020008 = 0x80020008; // type:func size:0x8",
    ]
    assert len([linea for linea in lineas if linea.startswith("func_800200")]) == 6
    fila_tabla = list(csv.reader(tablas.open(encoding="utf-8", newline="")))[1]
    assert fila_tabla[:4] == ["D_8005F000", "0x8005F000", "5", "puntero_a_funcion"]
    assert fila_tabla[6] == "4"
    assert len(list(csv.reader(nuevas.open(encoding="utf-8", newline="")))) == 5


def test_dos_ejecuciones_producen_la_misma_tabla(tmp_path: Path, entradas: dict[str, Path]) -> None:
    primera, segunda = tmp_path / "a.txt", tmp_path / "b.txt"
    assert main(_simbolos(entradas, primera)) == 0
    assert main(_simbolos(entradas, segunda)) == 0
    assert primera.read_bytes() == segunda.read_bytes()


def test_si_falla_la_escritura_de_las_listas_la_tabla_anterior_no_se_toca(
    tmp_path: Path, entradas: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    destino = tmp_path / "symbols.txt"
    destino.write_text("anterior\n", encoding="utf-8")
    carpeta = tmp_path / "es_una_carpeta"
    carpeta.mkdir()
    assert main(_simbolos(entradas, destino, "--tablas", str(carpeta))) == 2
    assert destino.read_text(encoding="utf-8") == "anterior\n"
    assert capsys.readouterr().err.startswith("error de entrada/salida:")

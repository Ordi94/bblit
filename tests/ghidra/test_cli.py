import runpy
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest
from tools.ghidra.cli import construir_parser, main
from tools.ghidra.ejecucion import ResultadoEjecucion

from tests.ghidra.segmentos import cierre, escribir_ejecutable
from tests.ghidra.sintetica import MUESTRA, csv_funciones, fila

REGISTRO_VALIDO = (
    "INFO  Using Loader: PSX Executables Loader (ProgramLoader)\n"
    "BBLIT base=0x80014A00\n"
    "BBLIT entrada=0x80014A08\n"
)


class EjecutorDoble:
    """Registra los comandos y, si se pide, crea el CSV que produciria Ghidra."""

    def __init__(self, resultado: ResultadoEjecucion, crear: Path | None = None) -> None:
        self.resultado = resultado
        self.crear = crear
        self.comandos: list[list[str]] = []

    def __call__(self, comando: Sequence[str], segundos: int) -> ResultadoEjecucion:
        self.comandos.append(list(comando))
        if self.crear is not None:
            self.crear.write_text("x", encoding="utf-8")
        return self.resultado


@pytest.fixture
def entorno(tmp_path: Path) -> dict[str, str]:
    (tmp_path / "ghidra" / "support").mkdir(parents=True)
    (tmp_path / "disc" / "fs").mkdir(parents=True)
    (tmp_path / "disc" / "fs" / "SLUS_008.38").write_bytes(b"x")
    return {"BBLIT_GHIDRA": str(tmp_path / "ghidra"), "BBLIT_DISC": str(tmp_path / "disc")}


@pytest.fixture
def ejecutable(tmp_path: Path) -> Path:
    palabras: dict[int, int] = {}
    for direccion, tamano in [
        (0x80014A00, 8),
        (0x80016414, 2040),
        (0x80016C0C, 100),
        (0x80045DA0, 96),
        (0x80045F28, 44),
    ]:
        palabras |= cierre(direccion, tamano)
    return escribir_ejecutable(tmp_path / "SLUS_008.38", palabras)


@pytest.fixture
def funciones_csv(tmp_path: Path) -> Path:
    ruta = tmp_path / "funciones.csv"
    ruta.write_text(MUESTRA, encoding="utf-8", newline="")
    return ruta


def test_analizar_usa_las_variables_de_entorno_e_imprime_la_carga(
    tmp_path: Path, entorno: dict[str, str], capsys: pytest.CaptureFixture[str]
) -> None:
    doble = EjecutorDoble(ResultadoEjecucion(0, REGISTRO_VALIDO))
    codigo = main(["analizar", "--proyecto", str(tmp_path / "proyecto")], entorno, doble)
    assert codigo == 0
    assert capsys.readouterr().out == "analisis completo: base=0x80014A00 entrada=0x80014A08\n"
    comando = doble.comandos[0]
    assert comando[comando.index("-import") + 1] == str(tmp_path / "disc" / "fs" / "SLUS_008.38")
    assert comando[-5:] == ["AplicarFirmas.java", "4.6.0", "4.0.0", "4.7.0", "4.4.0"]


def test_analizar_acepta_semilla_y_versiones_propias(tmp_path: Path, entorno: dict[str, str]) -> None:
    doble = EjecutorDoble(ResultadoEjecucion(0, REGISTRO_VALIDO))
    semilla = tmp_path / "semilla.txt"
    argumentos = [
        "analizar",
        "--proyecto",
        str(tmp_path / "proyecto"),
        "--semilla",
        str(semilla),
        "--versiones-firmas",
        "4.5.0",
        "--segundos",
        "90",
    ]
    assert main(argumentos, entorno, doble) == 0
    comando = doble.comandos[0]
    assert comando[comando.index("-preScript") + 2] == str(semilla)
    assert comando[-2:] == ["AplicarFirmas.java", "4.5.0"]
    assert comando[comando.index("-analysisTimeoutPerFile") + 1] == "90"


def test_analizar_sin_versiones_omite_la_pasada_adicional(tmp_path: Path, entorno: dict[str, str]) -> None:
    doble = EjecutorDoble(ResultadoEjecucion(0, REGISTRO_VALIDO))
    argumentos = ["analizar", "--proyecto", str(tmp_path / "p"), "--versiones-firmas", ""]
    assert main(argumentos, entorno, doble) == 0
    assert "AplicarFirmas.java" not in doble.comandos[0]


def test_analizar_reporta_en_una_linea_un_error_de_carga(
    tmp_path: Path, entorno: dict[str, str], capsys: pytest.CaptureFixture[str]
) -> None:
    doble = EjecutorDoble(ResultadoEjecucion(0, "nada"))
    assert main(["analizar", "--proyecto", str(tmp_path / "p")], entorno, doble) == 2
    capturado = capsys.readouterr()
    assert capturado.out == ""
    assert capturado.err == "error: el registro no confirma el uso del cargador PSX\n"


def test_analizar_sin_ghidra_configurado_falla_con_instruccion(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    doble = EjecutorDoble(ResultadoEjecucion(0, ""))
    assert main(["analizar", "--proyecto", str(tmp_path / "p")], {}, doble) == 2
    assert capsys.readouterr().err == "error: indique --ghidra o defina la variable BBLIT_GHIDRA\n"


def test_analizar_reporta_el_tiempo_agotado(
    tmp_path: Path, entorno: dict[str, str], capsys: pytest.CaptureFixture[str]
) -> None:
    def agotado(_comando: Sequence[str], segundos: int) -> ResultadoEjecucion:
        raise TimeoutError(f"el proceso excedio {segundos} segundos")

    assert main(["analizar", "--proyecto", str(tmp_path / "p"), "--segundos", "7"], entorno, agotado) == 2
    assert capsys.readouterr().err == "error: el proceso excedio 7 segundos\n"


def test_exportar_lanza_ghidra_y_confirma(
    tmp_path: Path, entorno: dict[str, str], capsys: pytest.CaptureFixture[str]
) -> None:
    salida = tmp_path / "salida"
    salida.mkdir()
    doble = EjecutorDoble(ResultadoEjecucion(0, ""), crear=salida / "funciones.csv")
    argumentos = ["exportar", "--proyecto", str(tmp_path / "p"), "--salida", str(salida)]
    assert main(argumentos, entorno, doble) == 0
    assert capsys.readouterr().out == "exportacion completa\n"
    assert doble.comandos[0][-2:] == ["si", "60"]


def test_exportar_sin_decompilar_y_con_limite_propio(tmp_path: Path, entorno: dict[str, str]) -> None:
    salida = tmp_path / "salida"
    salida.mkdir()
    doble = EjecutorDoble(ResultadoEjecucion(0, ""), crear=salida / "funciones.csv")
    argumentos = [
        "exportar",
        "--proyecto",
        str(tmp_path / "p"),
        "--salida",
        str(salida),
        "--sin-decompilar",
        "--segundos-por-funcion",
        "9",
        "--programa",
        "OTRO",
    ]
    assert main(argumentos, entorno, doble) == 0
    assert doble.comandos[0][-2:] == ["no", "9"]
    assert doble.comandos[0][doble.comandos[0].index("-process") + 1] == "OTRO"


def test_simbolos_escribe_la_tabla_exacta(
    tmp_path: Path, funciones_csv: Path, ejecutable: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destino = tmp_path / "config" / "symbols.txt"
    assert (
        main(
            [
                "simbolos",
                "--funciones",
                str(funciones_csv),
                "--salida",
                str(destino),
                "--exe",
                str(ejecutable),
            ]
        )
        == 0
    )
    esperado = (
        "5 simbolos escritos (0 fragmentos fusionados, 0 descartados, 0 huecos de codigo anadidos)\n"
        "tablas: 0 (0 de punteros a funcion, 0 de switch); 0 funciones nuevas, "
        "0 separadas por retorno, 0 continuaciones fusionadas, 0 destinos no aplicados\n"
    )
    assert capsys.readouterr().out == esperado
    assert destino.read_text(encoding="utf-8") == (
        "__main = 0x80014A00; // type:func size:0x8\n"
        "main = 0x80016414; // type:func size:0x7F8\n"
        "func_80016C0C = 0x80016C0C; // type:func size:0x64\n"
        "DecDCTReset = 0x80045DA0; // type:func size:0x60\n"
        "func_80045F28 = 0x80045F28; // type:func size:0x2C\n"
    )


def test_simbolos_rechaza_un_csv_invalido_sin_escribir(
    tmp_path: Path, ejecutable: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    entrada = tmp_path / "f.csv"
    entrada.write_text(csv_funciones([fila(direccion="0x80014A0A")]), encoding="utf-8", newline="")
    destino = tmp_path / "symbols.txt"
    assert (
        main(["simbolos", "--funciones", str(entrada), "--salida", str(destino), "--exe", str(ejecutable)])
        == 2
    )
    assert capsys.readouterr().err == "error: fila 2: direccion=0x80014A0A no alineada a 4\n"
    assert not destino.exists()


def test_simbolos_con_archivo_inexistente_no_vuelca_la_ruta(
    tmp_path: Path, ejecutable: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argumentos = [
        "simbolos",
        "--funciones",
        str(tmp_path / "no.csv"),
        "--salida",
        str(tmp_path / "s.txt"),
        "--exe",
        str(ejecutable),
    ]
    assert main(argumentos) == 2
    assert capsys.readouterr().err == "error de entrada/salida: FileNotFoundError\n"


def test_informe_imprime_conteos_y_cobertura(funciones_csv: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["informe", "--funciones", str(funciones_csv)]) == 0
    assert capsys.readouterr().out == (
        "funciones totales: 5\n"
        "libreria identificada: 3\n"
        "  con nombre oficial: 2\n"
        "  rutinas internas de objeto: 1\n"
        "  con candidatos alternos: 1\n"
        "juego: 2\n"
        "cobertura del segmento: 0.66 % (2288 bytes)\n"
    )


def test_informe_verifica_un_symbols_valido(
    tmp_path: Path, funciones_csv: Path, ejecutable: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destino = tmp_path / "symbols.txt"
    assert (
        main(
            [
                "simbolos",
                "--funciones",
                str(funciones_csv),
                "--salida",
                str(destino),
                "--exe",
                str(ejecutable),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert main(["informe", "--funciones", str(funciones_csv), "--verificar", str(destino)]) == 0
    assert capsys.readouterr().out.endswith("symbols.txt valido: 5 simbolos\n")


def test_informe_rechaza_un_symbols_invalido(
    tmp_path: Path, funciones_csv: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destino = tmp_path / "symbols.txt"
    destino.write_text("basura\n", encoding="utf-8")
    assert main(["informe", "--funciones", str(funciones_csv), "--verificar", str(destino)]) == 2
    assert capsys.readouterr().err == "error: symbols linea 1: formato invalido\n"


def test_el_parser_exige_un_subcomando() -> None:
    with pytest.raises(SystemExit) as salida:
        construir_parser().parse_args([])
    assert salida.value.code == 2


def test_python_m_tools_ghidra_ejecuta_main(
    funciones_csv: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["tools.ghidra", "informe", "--funciones", str(funciones_csv)])
    with pytest.raises(SystemExit) as salida:
        runpy.run_module("tools.ghidra", run_name="__main__")
    assert salida.value.code == 0
    assert capsys.readouterr().out.startswith("funciones totales: 5\n")

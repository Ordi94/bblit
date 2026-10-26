import csv
from collections.abc import Sequence
from pathlib import Path

import pytest
from tools.ghidra.cli import construir_parser, main
from tools.ghidra.dominio import Simbolo
from tools.ghidra.ejecucion import ResultadoEjecucion
from tools.ghidra.simbolos import formatear_tabla

from tests.ghidra.escenario import VSYNC, A, B, C, D, E, G, nombre, palabras_programa, simbolos, texto_asm
from tests.ghidra.segmentos import escribir_ejecutable
from tests.ghidra.sintetica import csv_funciones, fila

LLAMADORES = {B: 2, C: 1}


class Splat:
    """Doble de splat: deja el desensamblado sintetico donde la herramienta lo espera."""

    def __init__(self) -> None:
        self.comandos: list[Sequence[str]] = []

    def __call__(self, comando: Sequence[str], segundos: int) -> ResultadoEjecucion:
        self.comandos.append(comando)
        configuracion = Path(comando[-1])
        (configuracion.parent / "asm").mkdir(parents=True, exist_ok=True)
        (configuracion.parent / "asm" / "text.s").write_text(texto_asm(), encoding="utf-8", newline="\n")
        return ResultadoEjecucion(0, "")


class M2c:
    """Doble de m2c: devuelve un borrador valido, salvo para una funcion que falla."""

    def __init__(self, falla: str = "") -> None:
        self.falla = falla
        self.comandos: list[Sequence[str]] = []

    def __call__(self, comando: Sequence[str], segundos: int) -> tuple[int, str, str]:
        self.comandos.append(comando)
        if self.falla and self.falla in comando[-1]:
            return 1, "", "no se pudo"
        return 0, "void f(void) {\n}\n", ""


@pytest.fixture
def entradas(tmp_path: Path) -> dict[str, Path]:
    exe = escribir_ejecutable(tmp_path / "SLUS_008.38", palabras_programa())
    tabla = tmp_path / "symbols.txt"
    tabla.write_text(formatear_tabla(simbolos()), encoding="utf-8", newline="\n")
    exportacion = tmp_path / "exportacion con espacios"
    (exportacion / "decomp").mkdir(parents=True)
    filas = [
        fila(
            direccion=f"0x{s.direccion:08X}",
            nombre=f"FUN_{s.direccion:08x}",
            tamano=str(s.tamano),
            es_libreria="1" if s.direccion == VSYNC else "0",
            numero_de_llamadores=str(LLAMADORES.get(s.direccion, 0)),
        )
        for s in simbolos()
    ]
    (exportacion / "funciones.csv").write_text(csv_funciones(filas), encoding="utf-8", newline="")
    (exportacion / "xrefs_datos.csv").write_text(
        "direccion_dato,tamano,funciones_que_lo_usan,lecturas,escrituras\n"
        f"0x80060000,4,0x{A:08X},1,0\n0x80010000,4,0x{B:08X};0x{D:08X},1,0\n",
        encoding="utf-8",
        newline="",
    )
    (exportacion / "strings.csv").write_text(
        'direccion,longitud,texto\n0x80060000,10,"hola mundo"\n', encoding="utf-8", newline=""
    )
    (exportacion / "decomp" / f"{A:08X}_FUN_80014ac4.c").write_text(
        "void FUN_80014ac4(void)\n{\n}\n", encoding="utf-8"
    )
    rangos = tmp_path / "rangos.csv"
    rangos.write_text(
        "nombre,inicio,fin\n"
        f"arranque,0x{A:08X},0x{B:08X}\nlogica,0x{B:08X},0x{D:08X}\ndespacho,0x{D:08X},0x{G + 8:08X}\n",
        encoding="utf-8",
    )
    return {
        "exe": exe,
        "simbolos": tabla,
        "exportacion": exportacion,
        "rangos": rangos,
        "salida": tmp_path / "salida",
    }


def _argumentos(comando: str, entradas: dict[str, Path], *extra: str) -> list[str]:
    return [
        comando,
        "--salida",
        str(entradas["salida"]),
        "--exportacion",
        str(entradas["exportacion"]),
        "--exe",
        str(entradas["exe"]),
        "--simbolos",
        str(entradas["simbolos"]),
        *extra,
    ]


def test_borradores_genera_un_archivo_por_funcion_y_resume(
    entradas: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    splat, m2c = Splat(), M2c(falla=nombre(E))
    assert main(_argumentos("borradores", entradas, "--m2c", "m2c.py"), {}, splat, m2c) == 0
    assert capsys.readouterr().out == (
        "borradores: 6 funciones, 5 generadas, 1 fallidas, 0 absorbidas por una funcion contigua (0 con marcas de m2c)\n"  # noqa: E501
    )
    salida = entradas["salida"]
    assert (salida / "m2c" / f"{A:08X}_{nombre(A)}.c").is_file()
    assert (salida / "asm" / f"{D:08X}_{nombre(D)}.s").is_file()
    assert "func_80014AC4" in (salida / "contexto_m2c.c").read_text(encoding="utf-8")
    assert (
        (salida / "m2c" / "FALLIDAS.csv")
        .read_text(encoding="utf-8")
        .splitlines()[1]
        .startswith(f"0x{E:08X},")
    )
    assert len(splat.comandos) == 1
    assert "m2c.py" in m2c.comandos[0]
    assert "--solo-rango" not in splat.comandos[0]


def test_borradores_solo_rango_y_reutiliza_el_desensamblado(
    entradas: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    splat = Splat()
    assert main(_argumentos("borradores", entradas, "--solo-rango"), {}, splat, M2c()) == 0
    assert "6 funciones, 6 generadas" in capsys.readouterr().out
    assert main(_argumentos("borradores", entradas, "--segundos-por-funcion", "5"), {}, splat, M2c()) == 0
    assert len(splat.comandos) == 1


def test_grafo_escribe_los_tres_csv_y_compara_con_ghidra(
    entradas: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(_argumentos("grafo", entradas), {}, Splat()) == 0
    assert capsys.readouterr().out.splitlines() == [
        "aristas: 4 (7 sitios de llamada); jal 2, j 1, tabla 1, indirectas 2 instrucciones",
        "juego->juego 3, juego->libreria 1, juego->externo 0, por tabla 1",
        "switch 1, punteros a funcion 1, datos 5",
        "llamadores contra Ghidra (juego): 6 de 6 coinciden, 0 difieren",
        "datos contra Ghidra: 1 iguales, 1 contenidos, 0 distintos",
    ]
    salida = entradas["salida"]
    filas = list(csv.reader((salida / "grafo_llamadas.csv").open(encoding="utf-8", newline="")))
    assert len(filas) == 7
    assert (salida / "datos_compartidos.csv").is_file()
    assert (salida / "punteros_funcion.csv").is_file()


def test_subsistemas_con_rangos_propios_y_con_propuesta_automatica(
    entradas: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    splat = Splat()
    assert main(_argumentos("subsistemas", entradas, "--rangos", str(entradas["rangos"])), {}, splat) == 0
    assert capsys.readouterr().out.splitlines() == [
        "arranque: 1 funciones",
        "logica: 2 funciones",
        "despacho: 3 funciones",
        "subsistemas: 3",
    ]
    assert (entradas["salida"] / "subsistemas.csv").is_file()
    assert main(_argumentos("subsistemas", entradas), {}, splat) == 0
    automatico = capsys.readouterr().out.splitlines()
    assert automatico[-1] == "subsistemas: 3"
    assert automatico[0].startswith("sistema_01: ")


def test_limites_escribe_los_archivos_de_origen(
    entradas: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(_argumentos("limites", entradas, "--rangos", str(entradas["rangos"])), {}, Splat()) == 0
    salida = capsys.readouterr().out.splitlines()
    assert salida[0] == "limites: 2 archivos propuestos ({'alta': 2, 'media': 0, 'baja': 0})"
    assert salida[1] == "relleno de nop observado: 0 cortes de 5"
    filas = list(csv.reader((entradas["salida"] / "archivos_origen.csv").open(encoding="utf-8", newline="")))
    assert [f[2] for f in filas[1:]] == ["src/logica.c", "src/despacho.c"]


def test_los_errores_de_entrada_se_reportan_en_una_linea(
    entradas: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    entradas["simbolos"].unlink()
    assert main(_argumentos("grafo", entradas), {}, Splat()) == 2
    assert capsys.readouterr().err == "error de entrada/salida: FileNotFoundError\n"


def test_el_parser_exige_la_salida_y_la_exportacion() -> None:
    parser = construir_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["grafo", "--salida", "x"])
    argumentos = parser.parse_args(["limites", "--salida", "x", "--exportacion", "y", "--rangos", "z"])
    assert argumentos.comando == "limites"


def test_unos_rangos_invalidos_se_reportan_con_error_y_codigo_2(
    entradas: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    entradas["rangos"].write_text("nombre,inicio\n", encoding="utf-8")
    assert main(_argumentos("subsistemas", entradas, "--rangos", str(entradas["rangos"])), {}, Splat()) == 2
    capturado = capsys.readouterr()
    assert capturado.out == ""
    assert capturado.err == "error: rangos: la cabecera debe ser nombre,inicio,fin\n"


def test_un_tiempo_agotado_del_desensamblador_se_reporta_con_codigo_2(
    entradas: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    def agotado(_comando: Sequence[str], segundos: int) -> ResultadoEjecucion:
        raise TimeoutError(f"el proceso excedio {segundos} segundos")

    assert main(_argumentos("grafo", entradas), {}, agotado) == 2
    assert capsys.readouterr().err == "error: el proceso excedio 600 segundos\n"


def test_los_simbolos_de_datos_de_la_tabla_no_cuentan_como_funciones_en_el_grafo(
    entradas: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    con_datos = [
        *simbolos(),
        Simbolo("D_80069338", 0x80069338, "u8", 1),
        Simbolo("D_80069350", 0x80069350, "u32", 4),
    ]
    entradas["simbolos"].write_text(formatear_tabla(con_datos), encoding="utf-8", newline="\n")
    assert main(_argumentos("grafo", entradas), {}, Splat()) == 0
    assert capsys.readouterr().out.splitlines()[0].startswith("aristas: 4 (7 sitios de llamada)")

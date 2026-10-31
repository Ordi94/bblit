"""Reglas de negocio de ``reempaquetar`` ante archivos de entrada ausentes.

El ejecutable reconstruido es un artefacto de ``build``: ``split`` y ``clean`` lo eliminan. Quien lo
pide sin haberlo producido recibe un mensaje que nombra la orden que lo genera, un codigo propio y
ninguna traza ni ruta de la maquina.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from tools.disco import cli

from tests.disco import sintetica


def ejecutar(tmp_path: Path, imagen: Path, exe: Path) -> int:
    return cli.main(
        ["reempaquetar", "--imagen", str(imagen), "--exe", str(exe), "--salida", str(tmp_path / "s")]
    )


@pytest.fixture
def imagen(tmp_path: Path) -> Path:
    ruta = tmp_path / "imagen.bin"
    sintetica.construir_imagen(ruta)
    return ruta


def test_sin_ejecutable_reconstruido_el_mensaje_nombra_la_orden_que_lo_produce(
    tmp_path: Path, imagen: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    codigo = ejecutar(tmp_path, imagen, tmp_path / "build" / "SLUS_008.38")
    salida = capsys.readouterr().out
    assert codigo == cli.CODIGO_ENTRADA_AUSENTE == 2
    assert salida == (
        "error: --exe: no existe el archivo indicado; ejecute 'python tools/build.py build' "
        "antes de reempaquetar\n"
    )


def test_el_mensaje_de_ejecutable_ausente_no_filtra_rutas_ni_trazas(
    tmp_path: Path, imagen: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ejecutar(tmp_path, imagen, tmp_path / "build" / "SLUS_008.38")
    captura = capsys.readouterr()
    assert str(tmp_path) not in captura.out and "Traceback" not in captura.out + captura.err
    assert "FileNotFoundError" not in captura.out


def test_una_carpeta_no_cuenta_como_ejecutable(
    tmp_path: Path, imagen: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    carpeta = tmp_path / "SLUS_008.38"
    carpeta.mkdir()
    assert ejecutar(tmp_path, imagen, carpeta) == 2
    assert capsys.readouterr().out.startswith("error: --exe: no existe el archivo indicado")


def test_sin_imagen_el_mensaje_nombra_la_opcion_y_no_sugiere_build(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exe = tmp_path / "SLUS_008.38"
    exe.write_bytes(sintetica.contenido_exe())
    assert ejecutar(tmp_path, tmp_path / "no_esta.bin", exe) == 2
    assert capsys.readouterr().out == "error: --imagen: no existe el archivo indicado\n"


def test_con_los_dos_archivos_presentes_no_hay_error_de_entrada(tmp_path: Path, imagen: Path) -> None:
    exe = tmp_path / "SLUS_008.38"
    exe.write_bytes(sintetica.contenido_exe())
    assert (
        cli.comprobar_entradas(
            cli.construir_parser().parse_args(
                ["reempaquetar", "--imagen", str(imagen), "--exe", str(exe), "--salida", str(tmp_path)]
            )
        )
        is None
    )


def test_el_proceso_termina_con_codigo_2_y_sin_traza(tmp_path: Path, imagen: Path) -> None:
    resultado = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.disco",
            "reempaquetar",
            "--imagen",
            str(imagen),
            "--exe",
            str(tmp_path / "ausente"),
            "--salida",
            str(tmp_path / "s"),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        cwd=Path(__file__).parents[2],
    )
    assert resultado.returncode == 2
    assert "Traceback" not in resultado.stderr

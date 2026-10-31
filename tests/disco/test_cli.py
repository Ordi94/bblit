import runpy
from pathlib import Path

import pytest
from tools.disco import cli

from tests.disco import sintetica


def preparar(tmp_path: Path) -> tuple[Path, Path]:
    ruta = tmp_path / "imagen.bin"
    sintetica.construir_imagen(ruta)
    exe = tmp_path / "SLUS_008.38"
    exe.write_bytes(sintetica.contenido_exe())
    return ruta, exe


def test_main_reempaqueta_e_informa_el_resumen(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ruta, exe = preparar(tmp_path)
    codigo = cli.main(
        ["reempaquetar", "--imagen", str(ruta), "--exe", str(exe), "--salida", str(tmp_path / "s")]
    )
    salida = capsys.readouterr().out
    assert codigo == 0
    assert salida.startswith("bblit_prueba.bin: 0 de 25 sectores modificados, sha1=")
    assert (tmp_path / "s" / "bblit_prueba.cue").exists()


def test_main_devuelve_1_con_mensaje_corto_si_la_validacion_falla(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta, exe = preparar(tmp_path)
    exe.write_bytes(b"corto")
    codigo = cli.main(
        ["reempaquetar", "--imagen", str(ruta), "--exe", str(exe), "--salida", str(tmp_path / "s")]
    )
    assert codigo == 1
    assert capsys.readouterr().out.startswith("error: tamano del ejecutable=5 distinto del registrado")


def test_main_no_filtra_rutas_cuando_falla_la_escritura(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ruta, exe = preparar(tmp_path)
    ocupado = tmp_path / "ocupado"
    ocupado.write_bytes(b"x")
    codigo = cli.main(["reempaquetar", "--imagen", str(ruta), "--exe", str(exe), "--salida", str(ocupado)])
    salida = capsys.readouterr().out
    assert codigo == 1
    assert salida.startswith("error de entrada/salida: ") and str(tmp_path) not in salida


def test_modulo_principal_termina_con_el_codigo_de_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ruta, exe = preparar(tmp_path)
    argv = [
        "tools.disco",
        "reempaquetar",
        "--imagen",
        str(ruta),
        "--exe",
        str(exe),
        "--salida",
        str(tmp_path / "s"),
    ]
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit) as info:
        runpy.run_module("tools.disco", run_name="__main__")
    assert info.value.code == 0

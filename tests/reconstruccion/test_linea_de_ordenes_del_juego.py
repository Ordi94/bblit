"""La linea de ordenes del juego es la del kit con su manifiesto: ordenes, ayuda y plugin de progreso."""

import argparse

import pytest
from tools.reconstruccion import cli
from tools.toolchain.contexto import PROYECTO, RAIZ_REPOSITORIO

from psxdecomp.cli import main as main_del_kit

ORDENES = ["split", "build", "verify", "clean", "diff", "probar", "permutar", "verificar-config", "progreso"]


def ayuda(*orden: str, capsys: pytest.CaptureFixture[str]) -> str:
    """Texto de ayuda de la orden pedida (o general), con los espacios normalizados."""
    with pytest.raises(SystemExit) as salida:
        cli.construir_parser().parse_args([*orden, "--help"])
    assert salida.value.code == 0
    return " ".join(capsys.readouterr().out.split())


def test_la_ayuda_general_lista_las_ordenes_comunes_y_progreso(capsys: pytest.CaptureFixture[str]) -> None:
    texto = ayuda(capsys=capsys)
    assert texto.startswith("usage: python tools/build.py [-h] [--disc DISC]")
    assert "{" + ",".join(ORDENES) + "}" in texto


def test_el_manifiesto_registra_progreso_como_plugin_de_subcomandos() -> None:
    assert PROYECTO.plugins.subcomandos == ("tools.reconstruccion.cli:registrar_progreso",)
    args = cli.construir_parser().parse_args(["progreso", "--sin-readme"])
    assert args.orden == "progreso"
    assert args.sin_readme is True
    assert args.manejador is cli._manejar_progreso


def test_la_ayuda_de_cada_orden_nombra_las_rutas_del_manifiesto_y_no_un_ejecutable_concreto(
    capsys: pytest.CaptureFixture[str],
) -> None:
    for orden in ORDENES:
        texto = ayuda(orden, capsys=capsys)
        assert "SLUS" not in texto
        assert "func_80" not in texto
    general = ayuda(capsys=capsys)
    assert f"{PROYECTO.rutas.fuentes}/*.c" in general
    assert f"{PROYECTO.rutas.build}/permutar/<funcion>/" in ayuda("permutar", capsys=capsys)
    assert PROYECTO.rutas.simbolos[0] in general
    assert PROYECTO.rutas.documento_progreso in general
    assert f"{PROYECTO.rutas.build}/progreso.json" in general


def test_las_opciones_globales_nombran_las_dos_variables_de_entorno_y_el_archivo_local(
    capsys: pytest.CaptureFixture[str],
) -> None:
    texto = ayuda(capsys=capsys)
    assert "PSXDECOMP_DISC (o BBLIT_DISC) o config/local.toml" in texto
    assert "PSXDECOMP_TOOLCHAIN (o BBLIT_TOOLCHAIN) o ./toolchain" in texto


def test_la_linea_de_ordenes_del_juego_no_ofrece_comprobar_ni_proyecto(
    capsys: pytest.CaptureFixture[str],
) -> None:
    texto = ayuda(capsys=capsys)
    assert "comprobar" not in texto
    assert "--proyecto" not in texto


def test_la_entrada_del_kit_sobre_este_repositorio_tambien_ofrece_progreso(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as salida:
        main_del_kit(["--help"], {}, raiz=RAIZ_REPOSITORIO)
    assert salida.value.code == 0
    texto = " ".join(capsys.readouterr().out.split())
    assert "progreso" in texto
    assert "comprobar" in texto


def test_registrar_progreso_usa_el_documento_y_el_resumen_del_manifiesto() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="orden")
    cli.registrar_progreso(subparsers, PROYECTO)
    assert "progreso" in subparsers.choices
    ayuda_progreso = " ".join(parser.format_help().split())
    assert PROYECTO.rutas.documento_progreso in ayuda_progreso
    assert f"{PROYECTO.rutas.build}/progreso.json" in ayuda_progreso

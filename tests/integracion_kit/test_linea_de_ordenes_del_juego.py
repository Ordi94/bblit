"""La linea de ordenes del juego es la del kit con su manifiesto: ordenes y ayuda, progreso incluido."""

import pytest
from tools.proyecto import PROYECTO, RAIZ_REPOSITORIO

from psxdecomp.cli import main as main_del_kit
from psxdecomp.cli import orden_progreso

from .proyecto_real import cli

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


def test_progreso_es_una_orden_del_kit_y_no_un_plugin_del_juego() -> None:
    assert PROYECTO.plugins.subcomandos == ()
    args = cli.construir_parser().parse_args(["progreso", "--sin-readme"])
    assert args.orden == "progreso"
    assert args.sin_readme is True
    assert args.manejador is orden_progreso.ejecutar_progreso
    assert not hasattr(cli, "registrar_progreso")


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


def test_la_ayuda_de_progreso_nombra_el_documento_el_resumen_y_el_readme_del_manifiesto(
    capsys: pytest.CaptureFixture[str],
) -> None:
    general = ayuda(capsys=capsys)
    assert PROYECTO.rutas.documento_progreso in general
    assert f"{PROYECTO.rutas.build}/progreso.json" in general
    assert PROYECTO.rutas.readme in general
    assert PROYECTO.rutas.readme in ayuda("progreso", capsys=capsys)

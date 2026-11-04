"""Analizador de la linea de ordenes: los textos de ayuda salen del manifiesto, no de un juego."""

import pytest
from psxdecomp.cli import PluginInvalidoError, construir_parser
from psxdecomp.dominio import Proyecto
from psxdecomp.lectura import cargar_proyecto

from identidad_del_juego import TERMINOS_PROHIBIDOS
from manifiestos_de_prueba import MANIFIESTO_COMPLETO, EscribirManifiesto


@pytest.fixture
def proyecto_completo(escribir_manifiesto: EscribirManifiesto) -> Proyecto:
    return cargar_proyecto(escribir_manifiesto(MANIFIESTO_COMPLETO))


def texto_de_ayuda(proyecto: Proyecto | None, capsys: pytest.CaptureFixture[str], *orden: str) -> str:
    """Ayuda de la orden pedida (o general) con los espacios normalizados: argparse reparte las lineas."""
    parser = construir_parser(proyecto, con_plugins=False)
    with pytest.raises(SystemExit) as salida:
        parser.parse_args([*orden, "--help"])
    assert salida.value.code == 0
    return " ".join(capsys.readouterr().out.split())


def test_la_ayuda_general_nombra_las_rutas_y_las_variables_del_manifiesto(
    proyecto_completo: Proyecto, capsys: pytest.CaptureFixture[str]
) -> None:
    texto = texto_de_ayuda(proyecto_completo, capsys)
    assert "codigo/*.c" in texto
    assert "salida/<ejecutable>" in texto
    assert "ensamblador/ y el script" in texto
    assert "esperado/" in texto
    assert "PSXDECOMP_DISC (o OTRO_DISC) o datos/local.toml" in texto
    assert "datos/a.txt, datos/b.txt" in texto
    assert "NO_COINCIDE" in texto


def test_la_ayuda_de_los_subcomandos_no_contiene_literales_de_un_juego(
    proyecto_completo: Proyecto, capsys: pytest.CaptureFixture[str]
) -> None:
    ordenes = ("split", "build", "verify", "clean", "diff", "probar", "permutar", "verificar-config")
    for orden in ((), *((nombre,) for nombre in ordenes)):
        texto = texto_de_ayuda(proyecto_completo, capsys, *orden)
        for prohibido in (*TERMINOS_PROHIBIDOS, "func_80"):
            assert prohibido not in texto, (orden, prohibido)


def test_la_ayuda_de_permutar_nombra_la_carpeta_de_estado_del_manifiesto(
    proyecto_completo: Proyecto, capsys: pytest.CaptureFixture[str]
) -> None:
    assert "salida/permutar/<funcion>/" in texto_de_ayuda(proyecto_completo, capsys, "permutar")


def test_sin_manifiesto_la_ayuda_usa_los_valores_por_omision_del_kit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    texto = texto_de_ayuda(None, capsys)
    assert "PSXDECOMP_DISC" in texto
    assert "(o " not in texto


def test_la_entrada_del_kit_anade_proyecto_y_comprobar_y_la_de_un_proyecto_no(
    proyecto_completo: Proyecto,
) -> None:
    kit = construir_parser(proyecto_completo, entrada_del_kit=True, con_plugins=False).format_help()
    propio = construir_parser(proyecto_completo, con_plugins=False).format_help()
    assert "--proyecto" in kit
    assert "comprobar" in kit
    assert "--proyecto" not in propio
    assert "comprobar" not in propio


def test_los_plugins_declarados_se_registran_salvo_que_se_pidan_sin_ellos(
    proyecto_completo: Proyecto,
) -> None:
    with pytest.raises(PluginInvalidoError, match=r"paquete\.modulo"):
        construir_parser(proyecto_completo)
    assert construir_parser(proyecto_completo, con_plugins=False) is not None

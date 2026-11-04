"""Gancho ``entrada_progreso``: un proyecto sustituye la regla de subsistemas por la suya."""

import json
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from psxdecomp.cli import PluginInvalidoError, main
from psxdecomp.cli.plugins import resolver_agrupador_de_subsistemas
from psxdecomp.lectura import cargar_proyecto

from ordenes.ayudantes import escribir_extension
from progreso.ayudantes import PROYECTO_BASE, crear_proyecto_propio, escribir, leer

MODULO = "extension_entrada_progreso"
MANIFIESTO_GANCHO = f'entrada_progreso = "{MODULO}:agrupar"\n'
CUERPO_AGRUPADOR = """\
def agrupar(proyecto, archivo):
    return "bloque-" + proyecto.identidad.nombre + "-" + archivo.rsplit("/", 1)[-1][:1]
"""


@pytest.fixture(autouse=True)
def limpiar_modulo() -> Iterator[None]:
    yield
    sys.modules.pop(MODULO, None)


def proyecto_con_gancho(raiz: Path, cuerpo: str = CUERPO_AGRUPADOR) -> Path:
    crear_proyecto_propio(raiz, extra_manifiesto=MANIFIESTO_GANCHO)
    escribir_extension(raiz, MODULO, cuerpo)
    escribir(raiz / "codigo" / "otro_b.c", "int rutina_b(void)\n{\n    return 0;\n}\n")
    return raiz


def test_sin_el_gancho_no_hay_agrupador_y_se_usa_el_sufijo_de_las_convenciones() -> None:
    assert resolver_agrupador_de_subsistemas(PROYECTO_BASE) is None


def test_el_manifiesto_con_el_gancho_lo_conserva_y_sin_el_gancho_es_nulo(tmp_path: Path) -> None:
    con = crear_proyecto_propio(tmp_path / "con", extra_manifiesto=MANIFIESTO_GANCHO).proyecto
    sin = crear_proyecto_propio(tmp_path / "sin").proyecto
    assert con.plugins.entrada_progreso == f"{MODULO}:agrupar"
    assert sin.plugins.entrada_progreso is None


def test_el_gancho_recibe_el_proyecto_y_el_archivo_y_decide_el_subsistema(tmp_path: Path) -> None:
    raiz = proyecto_con_gancho(tmp_path)
    agrupar = resolver_agrupador_de_subsistemas(cargar_proyecto(raiz))
    assert agrupar is not None
    assert agrupar("codigo/modulo_a.c") == "bloque-demo-m"


def test_la_orden_progreso_agrupa_por_el_criterio_del_gancho_y_no_por_el_sufijo(tmp_path: Path) -> None:
    raiz = proyecto_con_gancho(tmp_path)
    assert main(["progreso", "--sin-readme"], {}, lambda *_: "", raiz=raiz) == 0
    datos = json.loads(leer(raiz / "salida" / "progreso.json"))
    assert [s["subsistema"] for s in datos["subsistemas"]] == ["bloque-demo-m", "bloque-demo-o"]
    assert "| bloque-demo-m | 1 |" in leer(raiz / "notas" / "avance.md")


def test_sin_el_gancho_la_orden_agrupa_por_el_nombre_del_archivo_sin_sufijo(tmp_path: Path) -> None:
    raiz = crear_proyecto_propio(tmp_path).raiz
    escribir(raiz / "codigo" / "modulo_a_2.c", "int rutina_b(void)\n{\n    return 0;\n}\n")
    assert main(["progreso", "--sin-readme"], {}, lambda *_: "", raiz=raiz) == 0
    datos = json.loads(leer(raiz / "salida" / "progreso.json"))
    assert [(s["subsistema"], s["archivos"]) for s in datos["subsistemas"]] == [("modulo_a", 2)]


@pytest.mark.parametrize("devuelto", ["", "a|b", "con`comilla", "x" * 65, "salto\nde linea", "None"])
def test_un_nombre_de_subsistema_invalido_detiene_la_orden_con_un_error_de_plugin(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], devuelto: str
) -> None:
    valor = "None" if devuelto == "None" else repr(devuelto)
    raiz = proyecto_con_gancho(tmp_path, f"def agrupar(proyecto, archivo):\n    return {valor}\n")
    assert main(["progreso", "--sin-readme"], {}, lambda *_: "", raiz=raiz) == 1
    errores = capsys.readouterr().err
    assert f"plugin '{MODULO}:agrupar': debe devolver el nombre del subsistema" in errores
    assert not (raiz / "notas" / "avance.md").exists()


def test_un_gancho_que_no_existe_se_informa_con_la_referencia(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz = crear_proyecto_propio(tmp_path, extra_manifiesto=MANIFIESTO_GANCHO).raiz
    assert main(["progreso", "--sin-readme"], {}, lambda *_: "", raiz=raiz) == 1
    assert f"plugin '{MODULO}:agrupar': no se pudo importar el modulo '{MODULO}'" in capsys.readouterr().err


def test_el_resolutor_exige_una_referencia_valida_en_el_manifiesto(tmp_path: Path) -> None:
    with pytest.raises(PluginInvalidoError, match="no se pudo importar"):
        resolver_agrupador_de_subsistemas(
            crear_proyecto_propio(
                tmp_path, extra_manifiesto='entrada_progreso = "inexistente_xyz:f"\n'
            ).proyecto
        )

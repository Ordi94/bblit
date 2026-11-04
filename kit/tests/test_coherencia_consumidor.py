"""Coherencia entre el manifiesto del repositorio consumidor y los archivos que lo acompanan.

El proyecto consumidor ya no repite en su codigo las rutas, zonas ni convenciones del manifiesto: las
lee de el. Lo que sigue pudiendo desviarse es lo que el manifiesto declara sobre otros archivos del
proyecto: las referencias de los plugins deben resolverse y el nombre del ejecutable debe coincidir con
el de su archivo de referencia. Se omite si el kit se ejecuta fuera de un repositorio consumidor.
"""

import json
from pathlib import Path

import pytest
from psxdecomp.cli.plugins import resolver_referencia
from psxdecomp.proyecto import Proyecto, cargar_proyecto

RAIZ_CONSUMIDOR = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not (RAIZ_CONSUMIDOR / "psxdecomp.toml").is_file(), reason="no hay manifiesto consumidor en la raiz"
)


@pytest.fixture(scope="module")
def proyecto() -> Proyecto:
    return cargar_proyecto(RAIZ_CONSUMIDOR)


def test_el_manifiesto_del_consumidor_declara_plugins_que_se_pueden_resolver(proyecto: Proyecto) -> None:
    plugins = proyecto.plugins
    assert plugins.entrada_progreso is None or callable(
        resolver_referencia(plugins.entrada_progreso, proyecto.raiz)
    )
    referencias: tuple[str, ...] = (
        *plugins.subcomandos,
        *plugins.antes_de_construir,
        *plugins.despues_de_verificar,
    )
    for referencia in referencias:
        assert callable(resolver_referencia(referencia, proyecto.raiz))


def test_el_ejecutable_coincide_con_la_referencia_versionada(proyecto: Proyecto) -> None:
    referencia = json.loads(proyecto.ruta_absoluta(proyecto.identidad.referencia).read_text(encoding="utf-8"))
    assert referencia["nombre"] == proyecto.identidad.ejecutable


def test_las_zonas_del_manifiesto_caen_dentro_del_segmento_de_la_referencia(proyecto: Proyecto) -> None:
    cabecera = json.loads(proyecto.ruta_absoluta(proyecto.identidad.referencia).read_text(encoding="utf-8"))[
        "cabecera"
    ]
    base = int(cabecera["t_addr"], 16)
    fin = base + int(cabecera["t_size"], 16)
    zonas = proyecto.zonas
    assert base <= zonas.juego_desde < zonas.librerias_desde < zonas.librerias_hasta <= fin

"""Coherencia entre el manifiesto del juego y los archivos que lo acompanan.

``psxdecomp.toml`` es la unica fuente de verdad de rutas, zonas y convenciones; el codigo del juego
(``tools/proyecto.py``) lo lee, no lo repite. Lo que si puede desviarse es lo que el manifiesto declara
sobre otros archivos: las referencias de los plugins deben resolverse, el nombre del ejecutable debe
coincidir con ``config/ejecutable.json`` y las zonas de memoria deben caer dentro de su segmento.
"""

import json

import pytest
from psxdecomp.cli.plugins import resolver_referencia
from psxdecomp.proyecto import Proyecto
from tools.proyecto import PROYECTO, RAIZ_REPOSITORIO, cargar


@pytest.fixture(scope="module")
def proyecto() -> Proyecto:
    return cargar(RAIZ_REPOSITORIO)


def _referencia(proyecto: Proyecto) -> dict[str, object]:
    texto = proyecto.ruta_absoluta(proyecto.identidad.referencia).read_text(encoding="utf-8")
    datos: dict[str, object] = json.loads(texto)
    return datos


def test_el_proyecto_que_usan_las_herramientas_es_el_del_manifiesto_del_repositorio(
    proyecto: Proyecto,
) -> None:
    assert PROYECTO == proyecto
    assert proyecto.raiz == RAIZ_REPOSITORIO


def test_el_manifiesto_declara_plugins_que_se_pueden_resolver(proyecto: Proyecto) -> None:
    plugins = proyecto.plugins
    if plugins.entrada_progreso is not None:
        assert callable(resolver_referencia(plugins.entrada_progreso, proyecto.raiz))
    referencias: tuple[str, ...] = (
        *plugins.subcomandos,
        *plugins.antes_de_construir,
        *plugins.despues_de_verificar,
    )
    for referencia in referencias:
        assert callable(resolver_referencia(referencia, proyecto.raiz))


def test_el_ejecutable_coincide_con_la_referencia_versionada(proyecto: Proyecto) -> None:
    assert _referencia(proyecto)["nombre"] == proyecto.identidad.ejecutable


def test_las_zonas_del_manifiesto_caen_dentro_del_segmento_de_la_referencia(proyecto: Proyecto) -> None:
    cabecera = _referencia(proyecto)["cabecera"]
    assert isinstance(cabecera, dict)
    base = int(cabecera["t_addr"], 16)
    fin = base + int(cabecera["t_size"], 16)
    zonas = proyecto.zonas
    assert base <= zonas.juego_desde < zonas.librerias_desde < zonas.librerias_hasta <= fin

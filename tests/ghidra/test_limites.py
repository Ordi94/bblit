import csv
import io

import pytest
from tools.ghidra.ensamblador import dividir_por_funcion
from tools.ghidra.grafo import Grafo, construir_grafo
from tools.ghidra.limites import (
    COLUMNAS_ARCHIVOS,
    VENTANAS,
    ArchivoOrigen,
    Limite,
    calcular_limites,
    cruces_por_corte,
    enlaces_entre_funciones,
    formatear_archivos_csv,
    proponer_archivos,
)
from tools.ghidra.subsistemas import Rango
from tools.ghidra.tablas import detectar_corridas

from tests.ghidra.escenario import A, B, C, D, E, G, palabras_programa, simbolos, texto_asm
from tests.ghidra.segmentos import BASE, segmento


def _grafo() -> Grafo:
    corridas = detectar_corridas(
        segmento(palabras_programa()), BASE, (0x8005DEA0, 0x80069A00), (0x80014AC4, 0x80045DA0)
    )
    return construir_grafo(dividir_por_funcion(texto_asm()), simbolos(), corridas)


def _vacio(**datos: tuple[int, ...]) -> Grafo:
    return Grafo((), (), {int(k[1:], 16): v for k, v in datos.items()}, {}, {}, 0, 0)


def test_los_enlaces_son_llamadas_punteros_y_datos_poco_compartidos() -> None:
    posicion = {A: 0, B: 1, C: 2, D: 3, E: 4, G: 5}
    assert enlaces_entre_funciones(_grafo(), posicion) == {(0, 1), (0, 2), (1, 2), (3, 4)}


def test_un_dato_de_estado_global_no_enlaza_funciones() -> None:
    posicion = {A: 0, B: 1, C: 2, D: 3, E: 4, G: 5, 0x100: 6, 0x104: 7, 0x108: 8}
    pocos = _vacio(d80010000=(A, G, 0x999))
    muchos = _vacio(d80010000=(A, B, C, D, E, G, 0x100))
    assert enlaces_entre_funciones(pocos, posicion) == {(0, 5)}
    assert enlaces_entre_funciones(muchos, posicion) == set()


def test_los_cruces_solo_cuentan_enlaces_dentro_de_la_ventana() -> None:
    pares = {(0, 1), (0, 3), (1, 2)}
    assert cruces_por_corte(pares, 4, 12) == [2, 2, 1]
    assert cruces_por_corte(pares, 4, 2) == [1, 1, 0]
    assert cruces_por_corte(set(), 0, 5) == []
    with pytest.raises(ValueError, match="la ventana debe ser al menos 1"):
        cruces_por_corte(pares, 4, 0)


def test_calcula_para_cada_corte_la_ventana_limpia_y_la_familia() -> None:
    limites = calcular_limites(simbolos(), _grafo(), segmento(palabras_programa()))
    assert [(lim.direccion, lim.anterior) for lim in limites] == [(B, A), (C, B), (D, C), (E, D), (G, E)]
    assert [lim.ventana_limpia for lim in limites] == [None, None, 12, None, 12]
    assert limites[0].familias == ("sistema", None)
    assert all(lim.relleno_nop == 0 for lim in limites)


def test_cuenta_el_relleno_de_nop_tras_la_ranura_de_retardo() -> None:
    palabras = {k: v for k, v in palabras_programa().items() if not B <= k < C}
    palabras[B + 4] = 0x03E00008  # jr ra en la segunda palabra: las tres ultimas son ranura y relleno
    limites = calcular_limites(simbolos(), _grafo(), segmento(palabras))
    assert limites[1].relleno_nop == 2


def _limite(
    direccion: int,
    ventana: int | None,
    familias: tuple[str | None, str | None] = (None, None),
    relleno: int = 0,
) -> Limite:
    return Limite(direccion, direccion - 4, ventana, familias, relleno)


def test_la_confianza_depende_de_la_ventana_la_familia_y_el_inicio_de_subsistema() -> None:
    rangos = [Rango("motor", 0x80014A00, 0x80015000), Rango("audio", 0x80015000, 0x80016000)]
    limites = [
        _limite(0x80015000, None),  # inicio de subsistema
        _limite(0x80015100, 12),  # alta
        _limite(0x80015200, 8),  # media
        _limite(0x80015300, 5, ("cd", "graficos")),  # media por cambio de familia
        _limite(0x80015400, 5),  # baja: se descarta
        _limite(0x80015500, None, ("cd", "graficos")),  # solo familia: baja, se descarta
        _limite(0x80015600, 8, relleno=3),  # con relleno
    ]
    archivos = proponer_archivos(limites, rangos, 0)
    assert [(a.direccion, a.confianza) for a in archivos] == [
        (0x80015000, "alta"),
        (0x80015100, "alta"),
        (0x80015200, "media"),
        (0x80015300, "media"),
        (0x80015600, "media"),
    ]
    assert archivos[0].evidencia == "inicio de subsistema"
    assert archivos[3].evidencia == (
        "ningun enlace cruza el corte en una ventana de 5 funciones; cambia la familia de librerias (cd a graficos)"  # noqa: E501
    )
    assert archivos[4].evidencia.endswith("3 nop de relleno tras la funcion anterior")
    assert [a.nombre for a in archivos] == ["audio", "audio_2", "audio_3", "audio_4", "audio_5"]


def test_un_inicio_de_subsistema_con_ventana_conserva_la_confianza_alta() -> None:
    rangos = [Rango("motor", 0x80014A00, 0x80015000)]
    archivos = proponer_archivos([_limite(0x80014A00, 8), _limite(0x80014F00, 5, ("cd", "mando"))], rangos, 0)
    assert [a.confianza for a in archivos] == ["alta", "media"]


def test_los_cortes_demasiado_juntos_se_descartan_salvo_los_inicios_de_subsistema() -> None:
    rangos = [Rango("motor", 0x80014A00, 0x80015000), Rango("audio", 0x80014A20, 0x80016000)]
    limites = [
        _limite(0x80014A10, VENTANAS[0]),
        _limite(0x80014A18, VENTANAS[0]),
        _limite(0x80014A20, VENTANAS[0]),
    ]
    archivos = proponer_archivos(limites, rangos, 256)
    assert [a.direccion for a in archivos] == [0x80014A10, 0x80014A20]
    with pytest.raises(ValueError, match="no puede ser negativo"):
        proponer_archivos(limites, rangos, -1)


def test_el_nombre_y_el_offset_siguen_el_formato_de_splat() -> None:
    archivos = proponer_archivos([_limite(0x80016C0C, 12)], [], 0)
    assert archivos == [
        ArchivoOrigen(
            0x80016C0C,
            0x2A0C,
            "sin_subsistema",
            "alta",
            "ningun enlace cruza el corte en una ventana de 12 funciones",
        )
    ]
    filas = list(csv.reader(io.StringIO(formatear_archivos_csv(archivos))))
    assert tuple(filas[0]) == COLUMNAS_ARCHIVOS
    assert filas[1][:4] == ["0x80016C0C", "0x2A0C", "src/sin_subsistema.c", "alta"]

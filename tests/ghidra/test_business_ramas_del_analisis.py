"""Reglas del analisis de llamadas y de limites en los casos que no deben producir enlaces ni tablas."""

from collections import Counter

from tools.ghidra.depuracion import _salta_dentro
from tools.ghidra.dominio import Funcion
from tools.ghidra.ensamblador import AnalisisFuncion, Referencia
from tools.ghidra.grafo import Arista, Grafo, _Acumulado, _Contexto, _Rangos, _registrar_referencias
from tools.ghidra.limites import enlaces_entre_funciones
from tools.ghidra.subsistemas import _contar_llamadas
from tools.ghidra.tablas import Corrida

from tests.ghidra.escenario import TABLA, A, B, E, simbolos
from tests.ghidra.segmentos import BASE, JR_RA, NOP, segmento

DESTINO_SIN_DUENO = 0x80020000
"""Direccion del juego que ningun subsistema contiene ni pertenece a las librerias."""


def _registrar(origen: int, referencias: tuple[Referencia, ...], corridas: list[Corrida]) -> _Acumulado:
    fronteras = sorted({r.direccion for r in referencias if r.desplazamiento == 0})
    contexto = _Contexto(_Rangos(simbolos()), corridas, fronteras)
    acumulado = _Acumulado()
    _registrar_referencias(origen, AnalisisFuncion((), referencias, 0), contexto, acumulado)
    return acumulado


def _funcion(direccion: int, tamano: int) -> Funcion:
    return Funcion(direccion, f"FUN_{direccion:08X}", tamano, False, "", 0, False, "")


def test_una_referencia_al_interior_de_una_funcion_no_es_un_puntero_a_funcion() -> None:
    acumulado = _registrar(A, (Referencia("interior", B + 4, 0),), [])
    assert acumulado.punteros == set()
    assert not acumulado.datos


def test_una_referencia_al_inicio_de_una_funcion_si_es_un_puntero_a_funcion() -> None:
    acumulado = _registrar(A, (Referencia("inicio", B, 0),), [])
    assert acumulado.punteros == {(A, B)}


def test_una_tabla_cuyos_destinos_son_otras_funciones_no_declara_tabla_de_salto_propia() -> None:
    corrida = Corrida(TABLA, (E,))
    acumulado = _registrar(A, (Referencia("D_8005E000", TABLA, 0),), [corrida])
    assert acumulado.llamadas == {(A, E, "tabla"): 1}
    assert not acumulado.tablas_salto


def test_los_enlaces_ignoran_llamadas_recursivas_y_de_funciones_fuera_del_corte() -> None:
    grafo = Grafo(
        aristas=(
            Arista(A, B, "jal", 1),
            Arista(DESTINO_SIN_DUENO, B, "jal", 1),
            Arista(B, B, "jal", 1),
        ),
        punteros=((A, DESTINO_SIN_DUENO), (B, DESTINO_SIN_DUENO), (B, B)),
        datos={},
        tablas_salto={},
        saltos_switch={},
        destinos_ajenos=0,
        sin_resolver=0,
    )
    assert enlaces_entre_funciones(grafo, {A: 0, B: 1}) == {(0, 1)}


def test_una_llamada_a_codigo_del_juego_sin_subsistema_no_cuenta_como_interna_ni_como_cruce() -> None:
    grafo = Grafo((Arista(A, DESTINO_SIN_DUENO, "jal", 1),), (), {}, {}, {}, 0, 0)
    librerias, internas, cruces, entrantes = _contar_llamadas(grafo, {A: "uno"}, {}, ("uno",))
    assert librerias == {"uno": Counter()}
    assert internas == Counter()
    assert cruces == {"uno": Counter()}
    assert entrantes == {"uno": Counter()}


def test_un_salto_que_sale_de_ambas_funciones_no_es_un_salto_al_interior_de_la_otra() -> None:
    origen = _funcion(BASE + 0x100, 16)
    destino = _funcion(BASE + 0x200, 16)
    beq_fuera = (4 << 26) | 0x0080
    palabras = {origen.direccion: beq_fuera, origen.direccion + 4: NOP, origen.direccion + 8: JR_RA}
    assert _salta_dentro(segmento(palabras), origen, destino) is False

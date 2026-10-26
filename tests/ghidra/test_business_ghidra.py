"""Reglas del contrato de la tabla de simbolos y de la verificacion de la carga."""

from pathlib import Path

import pytest
from tools.ghidra.depuracion import depurar_funciones
from tools.ghidra.dominio import (
    DIRECCION_BASE,
    DIRECCION_ENTRADA,
    DIRECCION_FIN,
    Simbolo,
    calcular_informe,
    construir_simbolos,
)
from tools.ghidra.ejecucion import verificar_carga
from tools.ghidra.lectura import parsear_funciones_csv
from tools.ghidra.simbolos import formatear_tabla, parsear_tabla

from tests.ghidra.segmentos import BASE, INSTRUCCION, cierre, segmento
from tests.ghidra.sintetica import MUESTRA, funcion

RAIZ = Path(__file__).resolve().parents[2]


def test_funcion_de_libreria_identificada_por_firma_lleva_el_nombre_oficial() -> None:
    simbolos = construir_simbolos(
        [funcion(0x80051938, "DrawSync", 0x68, es_libreria=True, nombre_oficial=True)]
    )
    assert simbolos == [Simbolo("DrawSync", 0x80051938, "func", 0x68)]


def test_funcion_del_juego_sin_identificar_lleva_func_con_su_direccion() -> None:
    simbolos = construir_simbolos([funcion(0x80016C0C, "FUN_80016c0c", 0x64)])
    assert simbolos == [Simbolo("func_80016C0C", 0x80016C0C, "func", 0x64)]


def test_rutina_interna_de_libreria_sin_nombre_exportado_no_inventa_nombre() -> None:
    simbolos = construir_simbolos([funcion(0x80045F28, "LIBPRESS_OBJ_188", 0x2C, es_libreria=True)])
    assert simbolos[0].nombre == "func_80045F28"


def test_el_nombre_que_el_cargador_da_a_la_rutina_principal_se_conserva() -> None:
    simbolos = construir_simbolos([funcion(0x80016414, "main", 0x7F8)])
    assert simbolos[0].nombre == "main"


def test_un_nombre_del_juego_que_imita_a_uno_de_libreria_no_se_toma_como_oficial() -> None:
    simbolos = construir_simbolos([funcion(0x80016C0C, "DrawSync", 0x64, es_libreria=False)])
    assert simbolos[0].nombre == "func_80016C0C"


def test_las_direcciones_de_funcion_exportadas_estan_alineadas_a_cuatro() -> None:
    simbolos = construir_simbolos(parsear_funciones_csv(MUESTRA))
    assert all(s.direccion % 4 == 0 for s in simbolos)


def test_la_tabla_generada_esta_ordenada_sin_direcciones_ni_nombres_repetidos() -> None:
    funciones = [funcion(0x80014A00 + 0x10 * i, f"FUN_{i}", 0x10) for i in (5, 1, 3, 2, 4)]
    simbolos = construir_simbolos(funciones)
    direcciones = [s.direccion for s in simbolos]
    assert direcciones == sorted(set(direcciones))
    assert len({s.nombre for s in simbolos}) == len(simbolos)


def test_dos_copias_estaticas_de_una_rutina_de_libreria_no_comparten_nombre() -> None:
    funciones = [
        funcion(0x8004E188, "memclr", 0x2C, es_libreria=True, nombre_oficial=True),
        funcion(0x8004E2B0, "memclr", 0x2C, es_libreria=True, nombre_oficial=True),
    ]
    assert [s.nombre for s in construir_simbolos(funciones)] == ["memclr_8004E188", "memclr_8004E2B0"]


def test_el_tamano_nunca_invade_a_la_funcion_vecina() -> None:
    funciones = [funcion(0x80014A00, "a", 0x5000), funcion(0x80014A20, "b", 0x20)]
    primero, segundo = construir_simbolos(funciones)
    assert primero.direccion + primero.tamano == segundo.direccion


def test_ningun_simbolo_sale_del_segmento_del_ejecutable() -> None:
    simbolos = construir_simbolos([funcion(DIRECCION_FIN - 4, "ultima", 0x1000)])
    assert simbolos[0].direccion + simbolos[0].tamano == DIRECCION_FIN


def test_una_funcion_fuera_del_segmento_se_rechaza_nombrando_el_simbolo() -> None:
    with pytest.raises(ValueError, match=r"simbolo func_80010000: direccion 0x80010000 fuera del rango"):
        construir_simbolos([funcion(0x80010000, "FUN_80010000", 8)])


def test_un_simbolo_duplicado_se_rechaza_al_leer_la_tabla() -> None:
    texto = "a = 0x80014A00; // type:func size:0x4\na = 0x80014A04; // type:func size:0x4\n"
    with pytest.raises(ValueError, match=r"simbolo a: nombre duplicado"):
        parsear_tabla(texto)


def test_la_cobertura_es_la_suma_de_los_tamanos_sobre_el_segmento() -> None:
    funciones = [funcion(DIRECCION_BASE, "a", 0x55000 // 2)]
    assert calcular_informe(funciones).porcentaje_cubierto == 50.0


def test_el_juego_es_lo_que_ninguna_firma_identifica() -> None:
    informe = calcular_informe(parsear_funciones_csv(MUESTRA))
    assert (informe.libreria, informe.juego, informe.total) == (3, 2, 5)
    assert informe.libreria + informe.juego == informe.total


def test_una_carga_con_otra_base_se_considera_fallida() -> None:
    registro = "Using Loader: PSX Executables Loader\nBBLIT base=0x80010000\nBBLIT entrada=0x80014A08\n"
    with pytest.raises(ValueError, match=r"base=0x80010000, se esperaba 0x80014A00"):
        verificar_carga(registro)


def test_el_punto_de_entrada_esta_dentro_del_segmento_cargado() -> None:
    assert DIRECCION_BASE <= DIRECCION_ENTRADA < DIRECCION_FIN


def test_la_tabla_de_simbolos_del_repositorio_cumple_el_contrato() -> None:
    ruta = RAIZ / "config" / "symbols.txt"
    texto = ruta.read_text(encoding="utf-8")
    simbolos = parsear_tabla(texto)
    assert formatear_tabla(simbolos) == texto
    por_nombre = {s.nombre: s for s in simbolos}
    assert por_nombre["main"].direccion == 0x80016414
    assert por_nombre["DrawSync"].direccion == 0x80051938
    assert por_nombre["VSync"].direccion == 0x8004D8C0
    assert por_nombre["CdReadSync"].direccion == 0x800494FC
    assert not any(s.nombre.startswith("FUN_") for s in simbolos)


def test_un_fragmento_interior_de_cuatro_bytes_no_se_emite_como_funcion() -> None:
    inicio = BASE + 0x100
    palabras = {inicio + 8: INSTRUCCION, inicio + 0x10: INSTRUCCION, **cierre(inicio + 0x14, 0x18)}
    candidatas = [funcion(inicio, "SpuSetReverb", 0x10), funcion(inicio + 0x10, "S_SR_OBJ_B0", 4)]
    candidatas.append(funcion(inicio + 0x14, "S_SR_OBJ_B4", 0x18))
    resultado = depurar_funciones(candidatas, segmento(palabras))
    simbolos = construir_simbolos(resultado.funciones)
    assert [(s.direccion, s.tamano) for s in simbolos] == [(inicio, 0x2C)]


def test_ninguna_funcion_de_la_tabla_del_repositorio_mide_menos_de_ocho_bytes() -> None:
    texto = (RAIZ / "config" / "symbols.txt").read_text(encoding="utf-8")
    assert all(s.tamano >= 8 for s in parsear_tabla(texto) if s.tipo == "func")


def test_una_funcion_cuyo_cuerpo_no_tiene_salto_final_no_se_emite() -> None:
    inicio = BASE + 0x100
    resultado = depurar_funciones([funcion(inicio, "FUN_x", 0x10)], segmento({inicio: INSTRUCCION}))
    assert resultado.funciones == []

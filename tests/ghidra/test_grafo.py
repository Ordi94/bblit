import csv
import io

import pytest
from tools.ghidra.ensamblador import dividir_por_funcion
from tools.ghidra.grafo import (
    COLUMNAS_DATOS,
    COLUMNAS_GRAFO,
    COLUMNAS_PUNTEROS,
    Arista,
    Grafo,
    TablaSalto,
    comparar_datos,
    comparar_llamadores,
    construir_grafo,
    formatear_datos_csv,
    formatear_grafo_csv,
    formatear_punteros_csv,
    resumir_grafo,
)
from tools.ghidra.tablas import detectar_corridas

from tests.ghidra.escenario import (
    D_DESTINO_1,
    D_DESTINO_2,
    TABLA,
    VSYNC,
    A,
    B,
    C,
    D,
    E,
    G,
    segmento_programa,
    simbolos,
    texto_asm,
)
from tests.ghidra.segmentos import BASE


def _grafo() -> Grafo:
    corridas = detectar_corridas(
        segmento_programa(), BASE, (0x8005DEA0, 0x80069A00), (0x80014AC4, 0x80045DA0)
    )
    return construir_grafo(dividir_por_funcion(texto_asm()), simbolos(), corridas)


def _nombres() -> dict[int, str]:
    return {s.direccion: s.nombre for s in simbolos()}


def test_las_aristas_cubren_los_cuatro_tipos_con_su_numero_de_instrucciones() -> None:
    assert _grafo().aristas == (
        Arista(A, B, "jal", 2),
        Arista(A, VSYNC, "jal", 1),
        Arista(A, None, "indirecta", 1),
        Arista(B, C, "j", 1),
        Arista(D, E, "tabla", 1),
        Arista(G, None, "indirecta", 1),
    )


def test_un_jr_con_tabla_propia_es_un_switch_y_sin_ella_es_indirecta() -> None:
    grafo = _grafo()
    assert dict(grafo.saltos_switch) == {D: 1}
    assert grafo.tablas_salto[D] == (TablaSalto("D_8005E000", TABLA, (D_DESTINO_1, D_DESTINO_2)),)
    assert G not in grafo.saltos_switch


def test_toma_de_puntero_y_datos_compartidos() -> None:
    grafo = _grafo()
    assert grafo.punteros == ((A, C),)
    assert dict(grafo.datos) == {
        0x80010000: (B,),
        TABLA: (D,),
        0x80060000: (A,),
        0x80069318: (B,),
        0x80069330: (B,),
    }
    assert (grafo.destinos_ajenos, grafo.sin_resolver) == (0, 0)


def test_el_resumen_cuenta_aristas_y_clases_de_destino() -> None:
    resumen = resumir_grafo(_grafo())
    assert (resumen.total, resumen.llamadas) == (4, 7)
    assert dict(resumen.por_tipo) == {"jal": 2, "j": 1, "tabla": 1, "indirecta": 2}
    assert (resumen.juego_juego, resumen.juego_libreria, resumen.juego_externo) == (3, 1, 0)
    assert (resumen.por_tabla, resumen.indirectas, resumen.switches) == (1, 2, 1)
    assert (resumen.punteros, resumen.datos) == (1, 5)


def test_una_funcion_que_no_esta_en_la_tabla_de_simbolos_se_rechaza() -> None:
    with pytest.raises(ValueError, match="func_80014AC4 no coincide con la tabla de simbolos"):
        construir_grafo(dividir_por_funcion(texto_asm()), simbolos()[1:], [])


def test_una_tabla_con_destinos_de_otra_funcion_los_cuenta_como_ajenos() -> None:
    grafo = _grafo()
    corridas = detectar_corridas(
        segmento_programa(), BASE, (0x8005DEA0, 0x80069A00), (0x80014AC4, 0x80045DA0)
    )
    # Mueve el segundo destino al interior de la funcion C (que no es inicio de funcion).
    datos = bytearray(segmento_programa())
    desplazamiento = TABLA + 4 - BASE
    datos[desplazamiento : desplazamiento + 4] = (C + 4).to_bytes(4, "little")
    corridas = detectar_corridas(bytes(datos), BASE, (0x8005DEA0, 0x80069A00), (0x80014AC4, 0x80045DA0))
    modificado = construir_grafo(dividir_por_funcion(texto_asm()), simbolos(), corridas)
    assert modificado.destinos_ajenos == 1
    assert modificado.tablas_salto[D][0].destinos == (D_DESTINO_1,)
    assert grafo.destinos_ajenos == 0


def test_el_csv_del_grafo_deja_vacio_el_destino_de_las_indirectas() -> None:
    texto = formatear_grafo_csv(_grafo(), _nombres())
    filas = list(csv.reader(io.StringIO(texto)))
    assert tuple(filas[0]) == COLUMNAS_GRAFO
    assert filas[1] == [
        "0x80014AC4",
        "func_80014AC4",
        "0x80014AF8",
        "func_80014AF8",
        "jal",
        "0",
        "juego",
        "2",
    ]
    assert filas[2] == ["0x80014AC4", "func_80014AC4", "0x80045DA0", "VSync", "jal", "1", "libreria", "1"]
    assert filas[3] == ["0x80014AC4", "func_80014AC4", "", "", "indirecta", "", "", "1"]
    assert len(filas) == 7


def test_los_csv_de_datos_y_punteros() -> None:
    grafo = _grafo()
    datos = list(csv.reader(io.StringIO(formatear_datos_csv(grafo, _nombres()))))
    assert tuple(datos[0]) == COLUMNAS_DATOS
    assert datos[1] == ["0x80010000", "1", "0x80014AF8:func_80014AF8"]
    punteros = list(csv.reader(io.StringIO(formatear_punteros_csv(grafo, _nombres()))))
    assert tuple(punteros[0]) == COLUMNAS_PUNTEROS
    assert punteros[1] == ["0x80014AC4", "func_80014AC4", "0x80014B0C", "func_80014B0C"]


def test_la_salida_es_determinista() -> None:
    assert formatear_grafo_csv(_grafo(), _nombres()) == formatear_grafo_csv(_grafo(), _nombres())
    assert formatear_datos_csv(_grafo(), _nombres()) == formatear_datos_csv(_grafo(), _nombres())


def test_compara_el_numero_de_llamadores_con_el_de_ghidra() -> None:
    grafo = _grafo()
    assert comparar_llamadores(grafo, {B: 2, C: 1, E: 0, A: 0}) == (4, ())
    assert comparar_llamadores(grafo, {B: 3, C: 1}) == (1, (B,))


def test_compara_los_datos_compartidos_con_los_de_ghidra() -> None:
    comparacion = comparar_datos(
        _grafo(),
        {0x80060000: [A], 0x80069330: [B, G], 0x80010000: [D], 0x99999999: [A]},
    )
    assert (comparacion.coinciden, comparacion.contenidos) == (1, 1)
    assert comparacion.difieren == (0x80010000,)


def test_una_tabla_referenciada_solo_por_la_forma_alta_recibe_un_nombre_de_dato() -> None:
    corridas = detectar_corridas(
        segmento_programa(), BASE, (0x8005DEA0, 0x80069A00), (0x80014AC4, 0x80045DA0)
    )
    texto = texto_asm().replace("%hi(D_8005E000)", "(0x8005E000 >> 16)")
    grafo = construir_grafo(dividir_por_funcion(texto), simbolos(), corridas)
    assert grafo.tablas_salto[D][0].simbolo == "D_8005E000"

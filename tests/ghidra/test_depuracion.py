import random
from itertools import pairwise

import pytest
from tools.ghidra.depuracion import Depuracion, depurar_funciones, es_terminador, es_transferencia
from tools.ghidra.dominio import DIRECCION_ENTRADA, FIN_CODIGO, Funcion, Simbolo, construir_simbolos
from tools.ghidra.ejecutable import palabra_en

from tests.ghidra.segmentos import BASE, DATO, INSTRUCCION, JR_RA, NOP, SALTO, cierre, segmento
from tests.ghidra.sintetica import funcion

A = BASE + 0x100
B = A + 0x10


@pytest.mark.parametrize(
    ("palabra", "esperado"),
    [
        (JR_RA, True),
        (0x00400008, True),
        (SALTO | 0x12345, True),
        (0x0C000000, False),
        (INSTRUCCION, False),
        (NOP, False),
        (0x00400009, False),
    ],
)
def test_es_terminador(palabra: int, esperado: bool) -> None:
    assert es_terminador(palabra) is esperado


def test_funcion_valida_minima_de_ocho_bytes_se_acepta() -> None:
    resultado = depurar_funciones([funcion(A, "FUN_a", 8)], segmento(cierre(A, 8)))
    assert resultado == Depuracion([funcion(A, "FUN_a", 8)], [], [], [], [])


def test_fragmento_de_cuatro_bytes_tras_una_funcion_terminada_se_descarta() -> None:
    palabras = {**cierre(A, 0x10), B: INSTRUCCION}
    resultado = depurar_funciones([funcion(A, "FUN_a", 0x10), funcion(B, "FUN_b", 4)], segmento(palabras))
    assert resultado.funciones == [funcion(A, "FUN_a", 0x10)]
    assert resultado.descartadas == [B]
    assert resultado.fusionadas == []


def test_fragmento_pegado_a_una_funcion_sin_terminador_se_fusiona_ampliando_su_tamano() -> None:
    palabras = {A: INSTRUCCION, A + 8: INSTRUCCION, **cierre(B, 0x18)}
    resultado = depurar_funciones([funcion(A, "FUN_a", 0x10), funcion(B, "FUN_b", 0x18)], segmento(palabras))
    assert resultado.funciones == [funcion(A, "FUN_a", 0x28)]
    assert resultado.fusionadas == [B]
    assert resultado.descartadas == []


def test_funcion_y_fragmento_sin_ningun_terminador_se_descartan_juntos() -> None:
    palabras = {A: INSTRUCCION, A + 8: INSTRUCCION, B: INSTRUCCION}
    resultado = depurar_funciones([funcion(A, "FUN_a", 0x10), funcion(B, "FUN_b", 4)], segmento(palabras))
    assert resultado.funciones == []
    assert resultado.descartadas == [A, B]
    assert resultado.fusionadas == []


def test_cadena_de_fragmentos_se_absorbe_en_la_primera_funcion() -> None:
    palabras = {A + 4: INSTRUCCION, **cierre(A + 0x20, 0x10)}
    candidatas = [funcion(A, "a", 0x10), funcion(A + 0x10, "b", 0x10), funcion(A + 0x20, "c", 0x10)]
    resultado = depurar_funciones(candidatas, segmento(palabras))
    assert resultado.funciones == [funcion(A, "a", 0x30)]
    assert resultado.fusionadas == [A + 0x10, A + 0x20]


def test_funcion_aislada_sin_terminador_se_descarta() -> None:
    resultado = depurar_funciones([funcion(A, "FUN_a", 0x10)], segmento({A: INSTRUCCION}))
    assert resultado.funciones == []
    assert resultado.descartadas == [A]


def test_un_terminador_en_la_ultima_palabra_no_cierra_hasta_prolongar_el_cuerpo_con_su_ranura() -> None:
    resultado = depurar_funciones([funcion(A, "FUN_a", 0x10)], segmento({A + 0xC: JR_RA}))
    assert resultado.funciones == [funcion(A, "FUN_a", 0x14)]


def test_el_punto_de_entrada_se_acepta_aunque_no_termine_en_salto() -> None:
    palabras = {DIRECCION_ENTRADA: INSTRUCCION}
    resultado = depurar_funciones([funcion(DIRECCION_ENTRADA, "start", 0x24)], segmento(palabras))
    assert resultado.funciones == [funcion(DIRECCION_ENTRADA, "start", 0x24)]


def test_una_funcion_que_empieza_dentro_de_otra_sin_terminador_se_fusiona() -> None:
    palabras = {A: INSTRUCCION, A + 4: INSTRUCCION, **cierre(A + 0x10, 0x20)}
    resultado = depurar_funciones([funcion(A, "a", 0x20), funcion(A + 0x10, "b", 0x20)], segmento(palabras))
    assert resultado.funciones == [funcion(A, "a", 0x30)]


def test_un_solape_con_la_funcion_previa_terminada_se_conserva_y_se_recorta_al_construir() -> None:
    palabras = {**cierre(A, 8), **cierre(A + 8, 0x10)}
    candidatas = [funcion(A, "FUN_a", 0x20), funcion(A + 8, "FUN_b", 0x10)]
    resultado = depurar_funciones(candidatas, segmento(palabras))
    assert [(f.direccion, f.tamano) for f in resultado.funciones] == [(A, 8), (A + 8, 0x10)]
    assert construir_simbolos(resultado.funciones) == [
        Simbolo(f"func_{A:08X}", A, "func", 8),
        Simbolo(f"func_{A + 8:08X}", A + 8, "func", 0x10),
    ]


def test_el_inicio_de_la_funcion_previa_no_se_toma_como_su_cierre() -> None:
    palabras = {A: INSTRUCCION, A + 8: JR_RA}
    resultado = depurar_funciones([funcion(A, "a", 8), funcion(A + 4, "b", 0xC)], segmento(palabras))
    assert resultado.fusionadas == [A + 4]
    assert resultado.funciones == [funcion(A, "a", 0x10)]


def test_el_cuerpo_se_recorta_al_final_del_segmento_al_buscar_el_terminador() -> None:
    ultima = 0x80069A00 - 8
    resultado = depurar_funciones([funcion(ultima, "fin", 0x100)], segmento({ultima: JR_RA}))
    assert resultado.descartadas == []
    assert [f.direccion for f in resultado.funciones] == [ultima]


def test_direcciones_duplicadas_se_rechazan() -> None:
    with pytest.raises(ValueError, match="direccion duplicada"):
        depurar_funciones([funcion(A, "a", 8), funcion(A, "b", 8)], segmento({}))


def test_hueco_de_codigo_terminado_entre_funciones_se_anade_como_funcion() -> None:
    hueco = A + 0x10
    palabras = {**cierre(A, 0x10), hueco: INSTRUCCION, **cierre(hueco, 0x10), **cierre(A + 0x20, 8)}
    resultado = depurar_funciones([funcion(A, "a", 0x10), funcion(A + 0x20, "b", 8)], segmento(palabras))
    assert [(f.direccion, f.nombre, f.tamano, f.es_libreria) for f in resultado.funciones] == [
        (A, "a", 0x10, False),
        (hueco, f"FUN_{hueco:08x}", 0x10, False),
        (A + 0x20, "b", 8, False),
    ]
    assert resultado.rescatadas == [hueco]


def test_hueco_sin_terminador_antes_de_una_funcion_local_se_une_a_ella() -> None:
    siguiente = A + 0x10
    palabras = {A: INSTRUCCION, A + 4: INSTRUCCION, **cierre(siguiente, 0x10)}
    local = funcion(siguiente, "LIB_OBJ_10", 0x10, es_libreria=True)
    resultado = depurar_funciones([local], segmento(palabras))
    assert [(f.direccion, f.tamano) for f in resultado.funciones] == [(A, 0x20)]
    assert resultado.rescatadas == [A]


def test_hueco_sin_terminador_antes_de_una_funcion_oficial_queda_como_rutina_propia() -> None:
    siguiente = A + 0x10
    palabras = {A: INSTRUCCION, A + 4: INSTRUCCION, **cierre(siguiente, 0x10)}
    oficial = funcion(siguiente, "DrawSync", 0x10, es_libreria=True, nombre_oficial=True)
    resultado = depurar_funciones([oficial], segmento(palabras))
    assert [(f.direccion, f.tamano) for f in resultado.funciones] == [(A, 0x10), (siguiente, 0x10)]
    assert resultado.funciones[1].nombre == "DrawSync"


def test_hueco_corto_sin_terminador_antes_de_una_funcion_oficial_se_registra_como_huerfano() -> None:
    oficial = funcion(A + 4, "DrawSync", 8, es_libreria=True, nombre_oficial=True)
    resultado = depurar_funciones([oficial], segmento({A: INSTRUCCION, **cierre(A + 4, 8)}))
    assert [f.direccion for f in resultado.funciones] == [A + 4]
    assert resultado.huerfanos == [(A, 4)]
    assert resultado.rescatadas == []


def test_una_tercera_funcion_no_rescata_como_hueco_bytes_ya_cubiertos_por_funciones_solapadas() -> None:
    palabras = {**cierre(A, 8), A + 0x18: JR_RA, **cierre(A + 0x20, 8)}
    candidatas = [
        funcion(A, "FUN_a", 0x20),
        funcion(A + 8, "FUN_b", 0x20),
        funcion(A + 0x20, "FUN_c", 8),
    ]
    resultado = depurar_funciones(candidatas, segmento(palabras))
    assert [(f.direccion, f.tamano) for f in resultado.funciones] == [(A, 8), (A + 8, 0x18), (A + 0x20, 8)]
    assert resultado.rescatadas == []


def test_hueco_de_datos_o_ceros_no_genera_funcion() -> None:
    palabras = {A: DATO, A + 4: DATO, **cierre(A + 0x10, 8)}
    resultado = depurar_funciones([funcion(A + 0x10, "b", 8)], segmento(palabras))
    assert [f.direccion for f in resultado.funciones] == [A + 0x10]
    assert resultado.rescatadas == []


def test_hueco_final_antes_del_fin_del_codigo_se_completa() -> None:
    ultimo = FIN_CODIGO - 0x10
    palabras = {ultimo: INSTRUCCION, **cierre(ultimo, 0x10)}
    resultado = depurar_funciones([], segmento(palabras))
    assert [(f.direccion, f.tamano) for f in resultado.funciones] == [(ultimo, 0x10)]


RAMA_ATRAS = 0x1000FFFE
"""``b`` hacia atras: ``beq zero,zero,-2``."""


@pytest.mark.parametrize(
    ("palabra", "esperado"),
    [
        (JR_RA, True),
        (SALTO | 0x12345, True),
        (RAMA_ATRAS, True),
        (0x50000001, True),
        (0x04010001, True),
        (0x04030001, True),
        (0x10400001, False),
        (0x14400001, False),
        (0x04000001, False),
        (0x04110001, False),
        (0x0C000000, False),
        (0x0040F809, False),
        (INSTRUCCION, False),
        (NOP, False),
    ],
)
def test_es_transferencia_solo_acepta_saltos_que_no_continuan(palabra: int, esperado: bool) -> None:
    assert es_transferencia(palabra) is esperado


def test_jr_ra_en_una_ranura_intermedia_con_ultima_instruccion_que_no_salta_se_rechaza() -> None:
    palabras = {A: JR_RA, A + 4: NOP, A + 8: INSTRUCCION, A + 0xC: INSTRUCCION}
    resultado = depurar_funciones([funcion(A, "FUN_a", 0x10)], segmento(palabras))
    assert resultado.funciones == []
    assert resultado.descartadas == [A]


def test_fragmento_tras_una_funcion_con_retorno_intermedio_y_cierre_que_no_salta_se_fusiona() -> None:
    palabras = {A: JR_RA, A + 8: INSTRUCCION, A + 0xC: INSTRUCCION, **cierre(B, 0x10)}
    resultado = depurar_funciones([funcion(A, "FUN_a", 0x10), funcion(B, "FUN_b", 0x10)], segmento(palabras))
    assert resultado.funciones == [funcion(A, "FUN_a", 0x20)]
    assert resultado.fusionadas == [B]


def test_funcion_que_cierra_con_rama_hacia_atras_y_retorno_en_medio_se_acepta() -> None:
    palabras = {A + 8: JR_RA, A + 0x18: RAMA_ATRAS}
    resultado = depurar_funciones([funcion(A, "FUN_a", 0x20)], segmento(palabras))
    assert resultado.funciones == [funcion(A, "FUN_a", 0x20)]
    assert resultado.descartadas == []


def test_una_rama_final_sin_ninguna_salida_real_no_cierra_la_funcion() -> None:
    resultado = depurar_funciones([funcion(A, "FUN_a", 0x20)], segmento({A + 0x18: RAMA_ATRAS}))
    assert resultado.funciones == []


def test_funcion_que_termina_en_jr_ra_se_acepta() -> None:
    resultado = depurar_funciones([funcion(A, "FUN_a", 0x20)], segmento(cierre(A, 0x20)))
    assert resultado.funciones == [funcion(A, "FUN_a", 0x20)]


def test_cuerpo_cortado_antes_del_epilogo_se_prolonga_hasta_el_cierre() -> None:
    palabras = {A: INSTRUCCION, A + 0x10: JR_RA}
    resultado = depurar_funciones([funcion(A, "DrawSync", 8, nombre_oficial=True)], segmento(palabras))
    assert resultado.funciones == [funcion(A, "DrawSync", 0x18, nombre_oficial=True)]


def test_la_prolongacion_no_pasa_del_siguiente_candidato() -> None:
    palabras = {A: INSTRUCCION, B + 8: JR_RA}
    candidatas = [funcion(A, "FUN_a", 8), funcion(B, "FUN_b", 8)]
    resultado = depurar_funciones(candidatas, segmento(palabras))
    assert resultado.descartadas == [A]
    assert resultado.funciones == [funcion(A, "FUN_b", 0x20)]
    assert resultado.rescatadas == [A]


def test_cuerpo_que_se_solapa_con_el_siguiente_candidato_se_evalua_recortado() -> None:
    palabras = {A + 8: 0x03400008, A + 0x14: INSTRUCCION, B: INSTRUCCION, **cierre(B, 0x10)}
    siguiente = funcion(A + 0x10, "FUN_b", 0x10)
    resultado = depurar_funciones([funcion(A, "FUN_a", 0x30), siguiente], segmento(palabras))
    assert [f.direccion for f in resultado.funciones] == [A, A + 0x10]


def test_tramo_final_de_codigo_sin_salto_se_registra_como_descartado() -> None:
    ultimo = FIN_CODIGO - 0x10
    resultado = depurar_funciones([], segmento({ultimo: INSTRUCCION, ultimo + 4: INSTRUCCION}))
    assert resultado.funciones == []
    assert resultado.descartadas == [ultimo]


def _escenario(semilla: int) -> tuple[list[Funcion], bytes]:
    """Genera candidatos y palabras pseudoaleatorios pero deterministas cerca del inicio del codigo."""
    azar = random.Random(semilla)  # noqa: S311
    vocabulario = [JR_RA, NOP, NOP, INSTRUCCION, INSTRUCCION, RAMA_ATRAS, DATO, SALTO | 0x100]
    palabras = {BASE + 0x40 + 4 * i: azar.choice(vocabulario) for i in range(64)}
    candidatas = []
    direccion = BASE + 0x40
    while direccion < BASE + 0x140:
        tamano = azar.choice([4, 8, 12, 16, 24, 40])
        candidatas.append(
            funcion(direccion, f"FUN_{direccion:08x}", tamano, nombre_oficial=azar.random() < 0.2)
        )
        direccion += azar.choice([4, 8, 8, 12, 16, 32])
    return candidatas, segmento(palabras)


@pytest.mark.parametrize("semilla", range(25))
def test_propiedad_la_salida_no_solapa_cierra_o_continua_y_no_pierde_bytes(semilla: int) -> None:
    candidatas, datos = _escenario(semilla)
    resultado = depurar_funciones(candidatas, datos)
    funciones = resultado.funciones
    for actual, siguiente in pairwise(funciones):
        fin = actual.direccion + actual.tamano
        assert fin <= siguiente.direccion
        cierra = es_transferencia(palabra_en(datos, fin - 8))
        assert cierra or fin == siguiente.direccion
    assert all(f.tamano >= 8 for f in funciones)
    registrados = {d for f in funciones for d in range(f.direccion, f.direccion + f.tamano, 4)}
    registrados |= {d for inicio, largo in resultado.huerfanos for d in range(inicio, inicio + largo, 4)}
    sin_registro = [
        d for d in range(BASE, FIN_CODIGO, 4) if d not in registrados and palabra_en(datos, d) != NOP
    ]
    assert sin_registro == []

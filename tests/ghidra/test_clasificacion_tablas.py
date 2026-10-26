import csv
import io

import pytest
from tools.ghidra import tablas
from tools.ghidra.tablas import (
    COLUMNAS_TABLAS,
    Corrida,
    TablaClasificada,
    clasificar_tablas,
    corrida_que_contiene,
    formatear_tablas_csv,
    referencias_a_tablas,
    segmentos_independientes,
)

from tests.ghidra.ensamblaje import (
    AT,
    NOP,
    RA,
    T0,
    T1,
    V0,
    V1,
    add,
    addiu,
    addu,
    beq,
    bne,
    j,
    jalr,
    jr,
    lui,
    lw,
    ori,
    programa,
    retorno,
    sll,
    sw,
)
from tests.ghidra.segmentos import BASE, segmento

CODIGO = (BASE, 0x8005DEA0)
TABLA = 0x8005E000
HI, LO = (TABLA + 0x8000) >> 16, TABLA & 0xFFFF
HI_ORI = TABLA >> 16
D = 0x80014AC4
"""Inicio del programa de prueba."""


def _corridas(*destinos: int) -> list[Corrida]:
    return [Corrida(TABLA, tuple(destinos))]


def _bytes(*partes: dict[int, int]) -> bytes:
    palabras: dict[int, int] = {}
    for parte in partes:
        palabras |= parte
    return segmento(palabras)


def _despachador_manual(direccion: int) -> dict[int, int]:
    """Estilo escrito a mano: direccion con addiu, indice con add, lw y jr sin comprobar el rango."""
    return programa(
        direccion,
        [
            lui(T1, HI),
            addiu(T1, T1, LO),
            sll(T0, T0, 2),
            add(T0, T0, T1),
            lw(T0, 0, T0),
            NOP,
            jr(T0),
            NOP,
            *retorno(),
        ],
    )


def _conmutador_gcc(direccion: int) -> dict[int, int]:
    """Estilo del compilador: lui, suma con addu y desplazamiento en el lw."""
    return programa(direccion, [lui(AT, HI), addu(AT, AT, V0), lw(V0, LO, AT), NOP, jr(V0), NOP, *retorno()])


def test_el_despachador_manual_se_reconoce_por_el_add_y_el_jr_sin_enlace() -> None:
    datos = _bytes(_despachador_manual(D))
    referencias = referencias_a_tablas(datos, BASE, _corridas(D, D), CODIGO)
    assert [(r.forma, r.tipo_salto, r.manual) for r in referencias] == [
        ("direccion", None, False),
        ("indexada", "jr", True),
    ]
    assert referencias[1].instruccion == D + 16
    assert referencias[1].salto == D + 24
    assert referencias[1].direccion == TABLA


def test_el_conmutador_del_compilador_usa_addu_y_no_es_manual() -> None:
    referencias = referencias_a_tablas(_bytes(_conmutador_gcc(D)), BASE, _corridas(D, D), CODIGO)
    assert [(r.forma, r.tipo_salto, r.manual) for r in referencias] == [("indexada", "jr", False)]


def test_un_jalr_sobre_el_valor_leido_es_el_consumo_y_un_jr_ra_no() -> None:
    codigo = programa(D, [lui(T1, HI_ORI), ori(T1, T1, LO), lw(T0, 0, T1), NOP, jalr(T0), NOP, *retorno()])
    referencias = referencias_a_tablas(_bytes(codigo), BASE, _corridas(D, D), CODIGO)
    assert [(r.forma, r.tipo_salto) for r in referencias] == [("direccion", None), ("elemento", "jalr")]


def test_una_escritura_o_una_lectura_fija_son_referencias_de_elemento_sin_consumo() -> None:
    codigo = programa(D, [lui(T1, HI), sw(T0, LO + 4, T1), lw(T0, LO, T1), *retorno()])
    referencias = referencias_a_tablas(_bytes(codigo), BASE, _corridas(D, D, D), CODIGO)
    assert [(r.forma, r.salto) for r in referencias] == [("elemento", None), ("elemento", None)]


def test_las_direcciones_fuera_de_las_corridas_o_desalineadas_no_son_referencias() -> None:
    codigo = programa(
        D,
        [
            lui(T1, HI),
            lw(T0, LO + 0x400, T1),
            lw(T0, LO + 2, T1),
            lui(T1, 0x8001),
            addiu(T1, T1, 0x10),
            *retorno(),
        ],
    )
    assert referencias_a_tablas(_bytes(codigo), BASE, _corridas(D, D), CODIGO) == []


def test_un_registro_sobrescrito_o_sumado_con_otro_conocido_pierde_la_direccion() -> None:
    codigo = programa(
        D,
        [
            lui(T1, HI),
            0x0C000000,  # jal: escribe ra y no toca t1
            addiu(T1, 0, 1),  # sobrescribe t1
            lw(T0, LO, T1),
            lui(V0, HI),
            lui(V1, HI),
            addu(T0, V0, V1),  # dos conocidos: no hay base mas indice
            lw(T0, LO, T0),
            *retorno(),
        ],
    )
    assert referencias_a_tablas(_bytes(codigo), BASE, _corridas(D, D), CODIGO) == []


def test_la_direccion_deja_de_seguirse_pasada_la_ventana(monkeypatch: pytest.MonkeyPatch) -> None:
    codigo = programa(D, [lui(T1, HI), NOP, NOP, NOP, lw(T0, LO, T1), NOP, jr(T0), NOP])
    monkeypatch.setattr(tablas, "VENTANA_REGISTROS", 2)
    assert referencias_a_tablas(_bytes(codigo), BASE, _corridas(D, D), CODIGO) == []
    monkeypatch.setattr(tablas, "VENTANA_REGISTROS", 100)
    assert len(referencias_a_tablas(_bytes(codigo), BASE, _corridas(D, D), CODIGO)) == 1


def test_el_valor_leido_deja_de_seguirse_si_se_sobrescribe() -> None:
    codigo = programa(D, [lui(T1, HI), lw(T0, LO, T1), addiu(T0, 0, 5), jr(T0), NOP])
    referencias = referencias_a_tablas(_bytes(codigo), BASE, _corridas(D, D), CODIGO)
    assert [r.tipo_salto for r in referencias] == [None]


@pytest.mark.parametrize(
    "rango",
    [
        (BASE + 2, 0x80014B00),
        (BASE, 0x80014B02),
        (BASE - 4, 0x80014B00),
        (BASE, 0x80070000),
        (0x80014B00, BASE),
    ],
)
def test_el_rango_de_codigo_debe_estar_alineado_y_dentro_del_segmento(rango: tuple[int, int]) -> None:
    with pytest.raises(ValueError, match="rango de codigo"):
        referencias_a_tablas(segmento({}), BASE, [], rango)


def _tres_rutinas(base: int) -> dict[int, int]:
    """Tres rutinas hoja contiguas de 8 bytes, la ultima con un valor en la ranura."""
    return programa(base, [*retorno(), *retorno(), jr(RA), addiu(V0, 0, 1)])


def test_los_tramos_de_rutinas_hoja_son_independientes() -> None:
    datos = _bytes(_tres_rutinas(D))
    assert segmentos_independientes(datos, BASE, [D, D + 8, D + 16, D], D + 24) == (3, 0)


def test_un_tramo_que_se_bifurca_cae_en_el_siguiente_o_es_demasiado_corto_cuenta_como_cruzado() -> None:
    bifurca = programa(D, [beq(0, V0, D, D + 16), NOP, *retorno(), *retorno()])
    cae = programa(D, [NOP, NOP, NOP, NOP, *retorno()])
    corto = programa(D, [jr(RA), jr(RA), NOP])
    salta_fuera = programa(D, [j(D + 0x400), NOP, *retorno()])
    assert segmentos_independientes(_bytes(bifurca), BASE, [D, D + 16], D + 24) == (2, 1)
    assert segmentos_independientes(_bytes(cae), BASE, [D, D + 16], D + 24) == (2, 1)
    assert segmentos_independientes(_bytes(corto), BASE, [D, D + 4], D + 12) == (2, 1)
    assert segmentos_independientes(_bytes(salta_fuera), BASE, [D], D + 16) == (1, 1)


def test_un_j_a_un_inicio_de_funcion_conocido_es_una_llamada_de_cola() -> None:
    cola = programa(D, [j(D + 0x400), NOP])
    assert segmentos_independientes(_bytes(cola), BASE, [D], D + 8, inicios=[D + 0x400]) == (1, 0)


def test_un_tramo_que_termina_en_un_salto_incondicional_con_beq_cero_es_correcto() -> None:
    bucle = programa(D, [beq(0, 0, D, D), NOP])
    assert segmentos_independientes(_bytes(bucle), BASE, [D], D + 8) == (1, 0)


@pytest.mark.parametrize("destinos", [[], [D + 2], [D + 64]])
def test_los_destinos_deben_estar_alineados_y_por_debajo_del_limite(destinos: list[int]) -> None:
    with pytest.raises(ValueError, match="alineados y por debajo del limite"):
        segmentos_independientes(segmento({}), BASE, destinos, D + 16)


def _clasificar(datos: bytes, destinos: tuple[int, ...], inicios: list[int]) -> TablaClasificada:
    (tabla,) = clasificar_tablas(datos, BASE, _corridas(*destinos), inicios, CODIGO)
    return tabla


def test_una_tabla_consumida_con_jalr_es_de_punteros_a_funcion() -> None:
    codigo = programa(D, [lui(T1, HI_ORI), ori(T1, T1, LO), lw(T0, 0, T1), NOP, jalr(T0), NOP, *retorno()])
    rutinas = programa(D + 0x40, [*retorno(), *retorno()])
    tabla = _clasificar(_bytes(codigo, rutinas), (D + 0x40, D + 0x48), [D, D + 0x40])
    assert (tabla.tipo, tabla.consumidor, tabla.evidencia, tabla.motivo) == (
        "puntero_a_funcion",
        D,
        D + 16,
        "se consume con jalr",
    )


def test_el_despachador_manual_con_rutinas_independientes_es_de_punteros() -> None:
    rutinas = _tres_rutinas(D + 0x40)
    tabla = _clasificar(
        _bytes(_despachador_manual(D), rutinas), (D + 0x40, D + 0x48, D + 0x50), [D, D + 0x58]
    )
    assert tabla.tipo == "puntero_a_funcion"
    assert tabla.consumidor == D
    assert tabla.evidencia == D + 24
    assert "despachador escrito a mano" in tabla.motivo
    assert "0 se bifurcan" in tabla.motivo


def test_un_conmutador_del_compilador_es_de_salto_aunque_sus_casos_sean_independientes() -> None:
    tabla = _clasificar(
        _bytes(_conmutador_gcc(D), _tres_rutinas(D + 0x40)), (D + 0x40, D + 0x48, D + 0x50), [D, D + 0x58]
    )
    assert tabla.tipo == "salto"
    assert "casos de un switch" in tabla.motivo


def test_un_despachador_manual_cuyos_tramos_se_cruzan_es_de_salto() -> None:
    cruzados = programa(D + 0x40, [beq(0, V0, D + 0x40, D + 0x48), NOP, *retorno()])
    tabla = _clasificar(_bytes(_despachador_manual(D), cruzados), (D + 0x40, D + 0x48), [D])
    assert tabla.tipo == "salto"


def test_una_tabla_copiada_se_clasifica_por_sus_tramos_o_porque_ya_son_funciones() -> None:
    limpio = _bytes(_tres_rutinas(D))
    cruzado = _bytes(programa(D, [bne(V0, 0, D, D + 16), NOP, *retorno(), *retorno()]))
    independiente = _clasificar(limpio, (D, D + 8, D + 16), [D + 24])
    assert (independiente.tipo, independiente.consumidor, independiente.evidencia) == (
        "puntero_a_funcion",
        None,
        None,
    )
    assert "sin consumo visible (copiada)" in independiente.motivo
    assert _clasificar(cruzado, (D, D + 16), []).tipo == "salto"
    ya_funciones = _clasificar(cruzado, (D, D + 16), [D, D + 16])
    assert (ya_funciones.tipo, ya_funciones.motivo) == (
        "puntero_a_funcion",
        "todos los destinos ya son inicio de funcion",
    )


def test_una_corrida_con_varias_tablas_se_parte_en_las_direcciones_referenciadas() -> None:
    primera = programa(D, [lui(T1, HI_ORI), ori(T1, T1, LO), lw(T0, 0, T1), NOP, jalr(T0), NOP, *retorno()])
    segunda = programa(
        D + 0x20, [lui(T1, HI_ORI), ori(T1, T1, LO + 8), lw(T0, 0, T1), NOP, jalr(T0), NOP, *retorno()]
    )
    rutinas = _tres_rutinas(D + 0x80)
    destinos = (D + 0x80, D + 0x88, D + 0x90)
    clasificadas = clasificar_tablas(
        _bytes(primera, segunda, rutinas), BASE, _corridas(*destinos), [D, D + 0x20], CODIGO
    )
    assert [(t.direccion, len(t.destinos), t.consumidor) for t in clasificadas] == [
        (TABLA, 2, D),
        (TABLA + 8, 1, D + 0x20),
    ]


def test_el_csv_de_tablas_nombra_la_consumidora_y_cuenta_los_destinos_nuevos() -> None:
    clasificadas = [
        TablaClasificada(TABLA + 8, (D + 8,), "salto", None, None, "sin consumo visible"),
        TablaClasificada(TABLA, (D, D + 8, D + 8), "puntero_a_funcion", D, D + 24, "se consume con jalr"),
        TablaClasificada(TABLA + 16, (D,), "salto", 0x80014000, 0x80014010, "otro"),
    ]
    filas = list(csv.reader(io.StringIO(formatear_tablas_csv(clasificadas, {D: "func_80014AC4"}, {D + 8}))))
    assert tuple(filas[0]) == COLUMNAS_TABLAS
    assert filas[1] == [
        "D_8005E000",
        "0x8005E000",
        "3",
        "puntero_a_funcion",
        "func_80014AC4",
        "0x80014ADC",
        "1",
        "se consume con jalr",
    ]
    assert filas[2][4:7] == ["", "", "1"]
    assert filas[3][4] == "0x80014000"


def test_el_seguimiento_calcula_los_inicios_una_vez_y_los_reutiliza_en_cada_consulta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La optimizacion: ninguna consulta reconstruye la lista de inicios de las corridas."""
    consultadas: list[list[int]] = []
    original = tablas.bisect_right

    def registra(inicios: list[int], valor: int) -> int:
        consultadas.append(inicios)
        return original(inicios, valor)

    monkeypatch.setattr(tablas, "bisect_right", registra)
    codigo = programa(D, [lui(T1, HI), lw(T0, LO, T1), lw(T0, LO + 4, T1), lw(T0, LO, T1), *retorno()])
    referencias = referencias_a_tablas(_bytes(codigo), BASE, _corridas(D, D), CODIGO)
    assert len(referencias) == 3
    assert len(consultadas) >= 3
    assert all(lista is consultadas[0] for lista in consultadas)
    consultadas.clear()
    corrida_que_contiene(_corridas(D, D), TABLA)
    corrida_que_contiene(_corridas(D, D), TABLA)
    assert consultadas[0] is not consultadas[1]

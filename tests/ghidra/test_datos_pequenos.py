import pytest
from tools.ghidra.datos_pequenos import COTA_DIRECCION_TOMADA, descubrir_datos_pequenos, leer_gp
from tools.ghidra.dominio import Simbolo

from tests.ghidra.ensamblaje import NOP, T0, addiu, lui, lw, programa, retorno
from tests.ghidra.segmentos import BASE, segmento

GP = 0x80069320
CODIGO = (BASE, 0x8005DEA0)
LIMITE = 0x80069A00
R_GP = 28
D = 0x80014AC4


def _acceso(operacion: int, desplazamiento: int, registro: int = T0) -> int:
    """Instruccion de memoria sobre ``$gp`` con el codigo de operacion dado."""
    return operacion << 26 | R_GP << 21 | registro << 16 | desplazamiento & 0xFFFF


def _datos(*palabras: int) -> list[Simbolo]:
    datos = segmento(programa(D, [*palabras, *retorno()]))
    return descubrir_datos_pequenos(datos, BASE, CODIGO, GP, LIMITE)


def test_el_valor_de_gp_sale_del_codigo_de_arranque() -> None:
    arranque = programa(BASE + 0x88, [lui(R_GP, 0x8007), addiu(R_GP, R_GP, -0x6CE0)])
    assert leer_gp(segmento(arranque), BASE, CODIGO) == GP


def test_sin_arranque_reconocible_no_hay_gp() -> None:
    sin_par = programa(BASE, [lui(R_GP, 0x8007), NOP, addiu(R_GP, R_GP, -0x6CE0)])
    otro_registro = programa(BASE, [lui(T0, 0x8007), addiu(R_GP, R_GP, 1)])
    solo_lui = programa(BASE, [lui(R_GP, 0x8007), addiu(T0, R_GP, 4)])
    for palabras in (sin_par, otro_registro, solo_lui, {}):
        assert leer_gp(segmento(palabras), BASE, CODIGO) is None


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
def test_los_rangos_de_codigo_invalidos_se_rechazan(rango: tuple[int, int]) -> None:
    with pytest.raises(ValueError, match="rango de codigo"):
        leer_gp(segmento({}), BASE, rango)
    with pytest.raises(ValueError, match="rango de codigo"):
        descubrir_datos_pequenos(segmento({}), BASE, rango, GP, LIMITE)


def test_el_tipo_y_el_tamano_salen_del_acceso_mas_ancho() -> None:
    datos = _datos(
        _acceso(0x24, 0x18),  # lbu
        _acceso(0x25, 0x20),  # lhu
        lw(T0, 0x30, R_GP),
        _acceso(0x20, 0x48),  # lb
        _acceso(0x23, 0x48),  # lw sobre el mismo dato
    )
    assert datos == [
        Simbolo("D_80069338", 0x80069338, "u8", 1),
        Simbolo("D_80069340", 0x80069340, "u16", 2),
        Simbolo("D_80069350", 0x80069350, "u32", 4),
        Simbolo("D_80069368", 0x80069368, "u32", 4),
    ]


def test_un_acceso_ancho_puede_contener_a_la_variable_siguiente() -> None:
    datos = _datos(lw(T0, 0x3C, R_GP), _acceso(0x25, 0x3E))
    assert [(s.nombre, s.tamano) for s in datos] == [("D_8006935C", 4), ("D_8006935E", 2)]


def test_si_solo_se_toma_la_direccion_el_tamano_es_la_distancia_al_siguiente_con_tope() -> None:
    cerca = _datos(addiu(T0, R_GP, 0x10), lw(T0, 0x18, R_GP))
    assert [(s.nombre, s.tipo, s.tamano) for s in cerca] == [
        ("D_80069330", "u8", 8),
        ("D_80069338", "u32", 4),
    ]
    lejos = _datos(addiu(T0, R_GP, 0x10), lw(T0, 0x400, R_GP))
    assert lejos[0].tamano == COTA_DIRECCION_TOMADA
    ultima = _datos(addiu(T0, R_GP, 0x7000))
    assert ultima == []


def test_se_ignoran_otros_registros_la_escritura_de_gp_y_las_direcciones_fuera_del_segmento() -> None:
    datos = _datos(
        lw(T0, 0x18, T0),  # otra base
        addiu(R_GP, R_GP, 0x10),  # modifica gp, no toma una direccion
        _acceso(0x23, 0x7000),  # mas alla del limite
        _acceso(0x0C, 0x20),  # andi
        0x27BDFFE0,  # addiu sp
    )
    assert datos == []


def test_los_desplazamientos_negativos_apuntan_a_los_datos_pequenos_anteriores() -> None:
    datos = _datos(_acceso(0x23, -0x8))
    assert datos == [Simbolo("D_80069318", 0x80069318, "u32", 4)]

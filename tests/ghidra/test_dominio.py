import pytest
from tools.ghidra.dominio import (
    DIRECCION_BASE,
    DIRECCION_FIN,
    LONGITUD_MAXIMA_NOMBRE,
    Informe,
    Simbolo,
    asignar_nombres,
    calcular_informe,
    construir_simbolos,
    es_identificador_c,
    fusionar_simbolos,
    nombre_por_defecto,
    normalizar_nombre,
    validar_simbolos,
)

from tests.ghidra.sintetica import funcion


def test_nombre_por_defecto_usa_ocho_digitos_en_mayusculas() -> None:
    assert nombre_por_defecto(0x80016414) == "func_80016414"
    assert nombre_por_defecto(0x8004E86C) == "func_8004E86C"


@pytest.mark.parametrize("direccion", [-1, 0x100000000])
def test_nombre_por_defecto_rechaza_direcciones_fuera_de_32_bits(direccion: int) -> None:
    with pytest.raises(ValueError, match="fuera de 32 bits"):
        nombre_por_defecto(direccion)


@pytest.mark.parametrize(
    ("nombre", "esperado"),
    [
        ("DrawSync", True),
        ("_make_packet", True),
        ("__main", True),
        ("a1", True),
        ("1abc", False),
        ("a-b", False),
        ("a b", False),
        ("", False),
        ("a" * LONGITUD_MAXIMA_NOMBRE, True),
        ("a" * (LONGITUD_MAXIMA_NOMBRE + 1), False),
    ],
)
def test_es_identificador_c(nombre: str, esperado: bool) -> None:
    assert es_identificador_c(nombre) is esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("2MBYTE.OBJ", "_2MBYTE_OBJ"),
        ("a-b c", "a_b_c"),
        ("", "_"),
        ("DrawSync", "DrawSync"),
        ("9", "_9"),
    ],
)
def test_normalizar_nombre(entrada: str, esperado: str) -> None:
    assert normalizar_nombre(entrada) == esperado


def test_asignar_nombres_aplica_la_regla_de_cada_tipo_de_funcion() -> None:
    funciones = [
        funcion(0x80014A00, "DrawSync", es_libreria=True, nombre_oficial=True),
        funcion(0x80014A10, "LIBPRESS_OBJ_188", es_libreria=True),
        funcion(0x80014A20, "FUN_80014a20"),
        funcion(0x80014A30, "main"),
        funcion(0x80014A40, "2MBYTE.OBJ", es_libreria=True, nombre_oficial=True),
    ]
    assert asignar_nombres(funciones) == {
        0x80014A00: "DrawSync",
        0x80014A10: "func_80014A10",
        0x80014A20: "func_80014A20",
        0x80014A30: "main",
        0x80014A40: "_2MBYTE_OBJ",
    }


def test_asignar_nombres_desambigua_nombres_oficiales_repetidos_con_la_direccion() -> None:
    funciones = [
        funcion(0x8004E188, "memclr", es_libreria=True, nombre_oficial=True),
        funcion(0x8004E2B0, "memclr", es_libreria=True, nombre_oficial=True),
        funcion(0x8004E558, "memset", es_libreria=True, nombre_oficial=True),
    ]
    assert asignar_nombres(funciones) == {
        0x8004E188: "memclr_8004E188",
        0x8004E2B0: "memclr_8004E2B0",
        0x8004E558: "memset",
    }


def test_asignar_nombres_rechaza_direcciones_duplicadas() -> None:
    with pytest.raises(ValueError, match="direccion duplicada 0x80014A00"):
        asignar_nombres([funcion(0x80014A00, "a"), funcion(0x80014A00, "b")])


def test_construir_simbolos_ordena_por_direccion_y_recorta_el_tamano_a_la_funcion_siguiente() -> None:
    funciones = [
        funcion(0x80014A40, "FUN_b", tamano=0x20),
        funcion(0x80014A00, "FUN_a", tamano=0x100),
    ]
    assert construir_simbolos(funciones) == [
        Simbolo("func_80014A00", 0x80014A00, "func", 0x40),
        Simbolo("func_80014A40", 0x80014A40, "func", 0x20),
    ]


def test_construir_simbolos_recorta_la_ultima_funcion_al_final_del_segmento() -> None:
    ultima = DIRECCION_FIN - 8
    simbolos = construir_simbolos([funcion(ultima, "FUN_z", tamano=0x100)])
    assert simbolos == [Simbolo("func_800699F8", ultima, "func", 8)]


def test_construir_simbolos_vacio_devuelve_lista_vacia() -> None:
    assert construir_simbolos([]) == []


def test_validar_simbolos_acepta_una_tabla_correcta() -> None:
    validar_simbolos(
        [
            Simbolo("DrawSync", 0x80051938, "func", 0x68),
            Simbolo("D_80060000", 0x80060001, "u32", 4),
        ]
    )


@pytest.mark.parametrize(
    ("simbolos", "mensaje"),
    [
        ([Simbolo("1x", 0x80014A00, "func", 4)], r"simbolo '1x': no es un identificador C valido"),
        ([Simbolo("f", DIRECCION_BASE - 4, "func", 4)], r"simbolo f: direccion 0x800149FC fuera del rango"),
        ([Simbolo("f", DIRECCION_FIN, "func", 4)], r"simbolo f: direccion 0x80069A00 fuera del rango"),
        ([Simbolo("f", 0x80014A02, "func", 4)], r"simbolo f: direccion 0x80014A02 no alineada a 4"),
        ([Simbolo("f", 0x80014A00, "func", 0)], r"simbolo f: tamano=0 debe ser mayor que 0"),
        ([Simbolo("f", DIRECCION_FIN - 4, "func", 8)], r"simbolo f: el tamano 0x8 excede el segmento"),
        (
            [Simbolo("f", 0x80014A00, "func", 4), Simbolo("f", 0x80014A10, "func", 4)],
            r"simbolo f: nombre duplicado",
        ),
        (
            [Simbolo("a", 0x80014A00, "func", 4), Simbolo("b", 0x80014A00, "func", 4)],
            r"simbolo b: direccion 0x80014A00 repetida \(ya la usa a\)",
        ),
        (
            [Simbolo("a", 0x80014A10, "func", 4), Simbolo("b", 0x80014A00, "func", 4)],
            r"simbolo b: fuera de orden ascendente tras a",
        ),
        (
            [Simbolo("a", 0x80014A00, "func", 0x10), Simbolo("b", 0x80014A08, "func", 4)],
            r"simbolo a: se solapa con b",
        ),
    ],
)
def test_validar_simbolos_rechaza_con_el_nombre_del_infractor(simbolos: list[Simbolo], mensaje: str) -> None:
    with pytest.raises(ValueError, match=mensaje):
        validar_simbolos(simbolos)


def test_validar_simbolos_no_exige_alineacion_a_los_datos() -> None:
    validar_simbolos([Simbolo("D_80060001", 0x80060001, "u8", 1)])


def test_calcular_informe_cuenta_libreria_juego_y_cobertura() -> None:
    funciones = [
        funcion(0x80014A00, "DrawSync", tamano=0x1000, es_libreria=True, nombre_oficial=True),
        funcion(0x80015A00, "LIBPRESS_OBJ_188", tamano=0x1000, es_libreria=True),
        funcion(
            0x80016A00,
            "CdSync",
            tamano=0x1000,
            es_libreria=True,
            nombre_oficial=True,
            comentario="Possible X",
        ),
        funcion(0x80017A00, "FUN_80017a00", tamano=0x2000),
    ]
    assert calcular_informe(funciones) == Informe(
        total=4,
        libreria=3,
        libreria_oficial=2,
        libreria_local=1,
        juego=1,
        ambiguas=1,
        bytes_cubiertos=0x5000,
        porcentaje_cubierto=round(100.0 * 0x5000 / 0x55000, 2),
    )


def test_calcular_informe_no_cuenta_dos_veces_los_bytes_solapados() -> None:
    funciones = [funcion(0x80014A00, "a", tamano=0x1000), funcion(0x80014A10, "b", tamano=0x10)]
    assert calcular_informe(funciones).bytes_cubiertos == 0x10 + 0x10


def test_calcular_informe_rechaza_direcciones_duplicadas() -> None:
    with pytest.raises(ValueError, match="direccion duplicada"):
        calcular_informe([funcion(0x80014A00, "a"), funcion(0x80014A00, "b")])


def test_un_dato_puede_contener_al_siguiente_pero_una_funcion_no_puede_solaparse() -> None:
    validar_simbolos(
        [Simbolo("D_80069350", 0x80069350, "u32", 4), Simbolo("D_80069352", 0x80069352, "u16", 2)]
    )
    with pytest.raises(ValueError, match="se solapa con D_80069352"):
        validar_simbolos([Simbolo("f", 0x80069350, "func", 8), Simbolo("D_80069352", 0x80069352, "u16", 2)])
    with pytest.raises(ValueError, match="se solapa con f"):
        validar_simbolos([Simbolo("D_80069350", 0x80069350, "u32", 8), Simbolo("f", 0x80069354, "func", 8)])


def test_fusionar_simbolos_ordena_por_direccion_entradas_desordenadas() -> None:
    funciones = [Simbolo("g", 0x80014B00, "func", 8), Simbolo("f", 0x80014A00, "func", 8)]
    datos = [Simbolo("D_80060001", 0x80060001, "u8", 1), Simbolo("D_80014A80", 0x80014A80, "u32", 4)]
    fusion = fusionar_simbolos(funciones, datos)
    assert [s.nombre for s in fusion] == ["f", "D_80014A80", "g", "D_80060001"]
    validar_simbolos(fusion)


def test_fusionar_simbolos_con_listas_vacias() -> None:
    dato = Simbolo("D_80060000", 0x80060000, "u32", 4)
    assert fusionar_simbolos([], []) == []
    assert fusionar_simbolos([], [dato]) == [dato]
    assert fusionar_simbolos([Simbolo("f", 0x80014A00, "func", 8)], [])[0].nombre == "f"


def test_fusionar_simbolos_nombra_funcion_y_dato_si_comparten_direccion() -> None:
    funciones = [Simbolo("f", 0x80014A00, "func", 8)]
    datos = [Simbolo("D_80014A00", 0x80014A00, "u32", 4)]
    with pytest.raises(
        ValueError, match=r"direccion 0x80014A00 compartida por la funcion f y el dato D_80014A00"
    ):
        fusionar_simbolos(funciones, datos)

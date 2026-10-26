import json
import re
import struct

import pytest
from tools.overlay import dominio
from tools.overlay.dominio import GrupoCodigo, VarianteConocida, VarianteExtraida

from tests.overlay.ayudantes import (
    ADDIU_SP,
    EPILOGO_SP,
    FIN_CODIGO,
    FUNCIONES_SINTETICAS,
    JR_RA,
    OFFSET_EPILOGO,
    construir_overlay,
    salto,
)


def conocidas_de(*binarios: bytes) -> tuple[VarianteConocida, ...]:
    return tuple(
        VarianteConocida(identificador, dominio.huella_sha256(datos), len(datos), cantidad)
        for (identificador, datos, cantidad) in zip("ab", binarios, (2, 1), strict=False)
    )


def grupos_de(*binarios: bytes) -> dict[str, GrupoCodigo]:
    secciones = []
    for posicion, datos in enumerate(binarios):
        secciones.append((f"CARPETA/ARCHIVO{posicion}.BZZ", datos))
    secciones.append(("CARPETA/OTRO.BZZ", binarios[0]))
    return dominio.agrupar_por_huella(secciones)


def test_constantes_de_las_variantes_conocidas() -> None:
    assert [(v.identificador, v.tamano, v.cantidad_archivos) for v in dominio.VARIANTES_CONOCIDAS] == [
        ("a", 17076, 48),
        ("b", 17072, 24),
        ("c", 17080, 4),
    ]
    assert sum(v.cantidad_archivos for v in dominio.VARIANTES_CONOCIDAS) == 76
    assert dominio.TAMANO_HUECO == 0x4800


def test_huella_sha256_de_cadena_vacia() -> None:
    assert dominio.huella_sha256(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


@pytest.mark.parametrize("nombre", ["LEVEL1/L01A.BZZ", "CC/CC1A.BZZ", "A.BZZ", "DEMO/DEMO3C1.BZZ"])
def test_nombre_bzz_valido(nombre: str) -> None:
    assert dominio.validar_nombre_bzz(nombre) == nombre


@pytest.mark.parametrize(
    "nombre",
    ["../L01A.BZZ", "/L01A.BZZ", "LEVEL1/L01A.bzz", "LEVEL1\\L01A.BZZ", "L01A.TXT", "", "A" * 130 + ".BZZ"],
)
def test_nombre_bzz_invalido(nombre: str) -> None:
    with pytest.raises(ValueError, match="nombre de contenedor BZZ no valido"):
        dominio.validar_nombre_bzz(nombre)


@pytest.mark.parametrize("tamano", [4, 17076, dominio.TAMANO_HUECO])
def test_tamano_de_codigo_valido(tamano: int) -> None:
    assert dominio.validar_tamano_codigo(tamano) == tamano


@pytest.mark.parametrize("tamano", [0, 3, 17075, dominio.TAMANO_HUECO + 4, -4])
def test_tamano_de_codigo_invalido(tamano: int) -> None:
    with pytest.raises(ValueError, match="tamano de la seccion de codigo"):
        dominio.validar_tamano_codigo(tamano)


def test_agrupar_ordena_y_agrupa_por_huella() -> None:
    a, b = construir_overlay(1), construir_overlay(2)
    grupos = grupos_de(a, b)
    assert grupos[dominio.huella_sha256(a)].archivos == ("CARPETA/ARCHIVO0.BZZ", "CARPETA/OTRO.BZZ")
    assert grupos[dominio.huella_sha256(b)].archivos == ("CARPETA/ARCHIVO1.BZZ",)
    assert list(grupos) == sorted(grupos)


def test_agrupar_rechaza_nombres_repetidos() -> None:
    with pytest.raises(ValueError, match=re.escape("contenedor repetido: A.BZZ")):
        dominio.agrupar_por_huella([("A.BZZ", bytes(8)), ("A.BZZ", bytes(8))])


def test_agrupar_rechaza_tamano_invalido() -> None:
    with pytest.raises(ValueError, match="tamano de la seccion de codigo"):
        dominio.agrupar_por_huella([("A.BZZ", bytes(7))])


def test_identificar_devuelve_variantes_en_orden() -> None:
    a, b = construir_overlay(1), construir_overlay(2)
    variantes, binarios = dominio.identificar_variantes(grupos_de(a, b), conocidas_de(a, b))
    assert [(v.identificador, v.tamano, len(v.archivos)) for v in variantes] == [
        ("a", len(a), 2),
        ("b", len(b), 1),
    ]
    assert binarios == {"a": a, "b": b}


def test_identificar_rechaza_huella_desconocida() -> None:
    a, b = construir_overlay(1), construir_overlay(2)
    with pytest.raises(ValueError, match="variante desconocida del overlay: sha256="):
        dominio.identificar_variantes(grupos_de(a, b), conocidas_de(a))


def test_identificar_exige_todas_las_variantes() -> None:
    a, b = construir_overlay(1), construir_overlay(2)
    with pytest.raises(ValueError, match="falta la variante 'b'"):
        dominio.identificar_variantes(grupos_de(a), conocidas_de(a, b))


def test_identificar_exige_la_cantidad_de_contenedores() -> None:
    a = construir_overlay(1)
    conocidas = (VarianteConocida("a", dominio.huella_sha256(a), len(a), 5),)
    with pytest.raises(ValueError, match="variante 'a': 2 contenedores, se esperaban 5"):
        dominio.identificar_variantes(grupos_de(a), conocidas)


def test_identificar_usa_las_variantes_reales_por_omision() -> None:
    with pytest.raises(ValueError, match="variante desconocida"):
        dominio.identificar_variantes(grupos_de(construir_overlay(1)))


def variantes_registradas() -> tuple[list[VarianteExtraida], tuple[VarianteConocida, ...]]:
    a, b = construir_overlay(1), construir_overlay(2)
    variantes, _ = dominio.identificar_variantes(grupos_de(a, b), conocidas_de(a, b))
    return variantes, conocidas_de(a, b)


def test_serializar_y_leer_configuracion_son_inversas() -> None:
    variantes, conocidas = variantes_registradas()
    texto = dominio.serializar_config(variantes)
    assert texto.endswith("}\n")
    datos = json.loads(texto)
    assert datos["direccionCarga"] == "0x80010200"
    assert datos["tipoSeccion"] == 2
    assert dominio.variantes_desde_config(datos, conocidas) == variantes


def test_serializar_es_determinista() -> None:
    variantes, _ = variantes_registradas()
    assert dominio.serializar_config(variantes) == dominio.serializar_config(list(variantes))


def corromper(cambio: dict[str, object]) -> tuple[object, tuple[VarianteConocida, ...]]:
    variantes, conocidas = variantes_registradas()
    datos = json.loads(dominio.serializar_config(variantes))
    datos.update(cambio)
    return datos, conocidas


@pytest.mark.parametrize(
    ("cambio", "mensaje"),
    [
        ({"direccionCarga": "0x80010000"}, "campo 'direccionCarga'"),
        ({"tipoSeccion": 3}, "campo 'tipoSeccion'"),
        ({"tipoSeccion": True}, "campo 'tipoSeccion'"),
        ({"variantes": []}, "campo 'variantes'"),
        ({"variantes": "x"}, "campo 'variantes'"),
        ({"variantes": [1]}, "cada elemento debe ser un objeto"),
    ],
)
def test_configuracion_rechaza_campos_invalidos(cambio: dict[str, object], mensaje: str) -> None:
    datos, conocidas = corromper(cambio)
    with pytest.raises(ValueError, match=mensaje):
        dominio.variantes_desde_config(datos, conocidas)


def test_configuracion_rechaza_un_documento_que_no_es_objeto() -> None:
    with pytest.raises(ValueError, match="debe ser un objeto"):
        dominio.variantes_desde_config([])


def test_configuracion_rechaza_variantes_repetidas() -> None:
    variantes, conocidas = variantes_registradas()
    datos = json.loads(dominio.serializar_config(variantes))
    datos["variantes"] = [datos["variantes"][0], datos["variantes"][0]]
    with pytest.raises(ValueError, match="identificadores repetidos"):
        dominio.variantes_desde_config(datos, conocidas)


@pytest.mark.parametrize(
    ("campo", "valor", "mensaje"),
    [
        ("id", "z", "campo 'id': variante no reconocida"),
        ("id", 3, "campo 'id': tipo no valido"),
        ("sha256", "0" * 64, "campo 'sha256' de la variante 'a'"),
        ("sha256", "XYZ", "campo 'sha256' de la variante 'a'"),
        ("sha256", 5, "campo 'sha256': tipo no valido"),
        ("tamano", 12, "campo 'tamano' de la variante 'a'"),
        ("tamano", True, "campo 'tamano': tipo no valido"),
        ("archivos", "x", "campo 'archivos': tipo no valido"),
        ("archivos", ["A.BZZ"], "campo 'archivos' de la variante 'a'"),
        ("archivos", ["B.BZZ", "A.BZZ"], "campo 'archivos' de la variante 'a'"),
        ("archivos", ["../A.BZZ", "B.BZZ"], "nombre de contenedor BZZ no valido"),
    ],
)
def test_configuracion_rechaza_variantes_invalidas(campo: str, valor: object, mensaje: str) -> None:
    variantes, conocidas = variantes_registradas()
    datos = json.loads(dominio.serializar_config(variantes))
    datos["variantes"][0][campo] = valor
    with pytest.raises(ValueError, match=mensaje):
        dominio.variantes_desde_config(datos, conocidas)


def test_fin_de_codigo_es_el_ultimo_jr_ra_con_su_ranura() -> None:
    assert dominio.fin_de_codigo(construir_overlay()) == FIN_CODIGO


def test_fin_de_codigo_rechaza_longitud_no_multiplo_de_cuatro() -> None:
    with pytest.raises(ValueError, match="multiplo de 4"):
        dominio.fin_de_codigo(bytes(7))


def test_fin_de_codigo_rechaza_codigo_sin_retorno() -> None:
    with pytest.raises(ValueError, match="ningun 'jr ra'"):
        dominio.fin_de_codigo(bytes(16))
    with pytest.raises(ValueError, match="ningun 'jr ra'"):
        dominio.fin_de_codigo(struct.pack("<I", JR_RA))


def test_descubrir_funciones_encuentra_entradas_saltos_y_prologos() -> None:
    assert dominio.descubrir_funciones(construir_overlay()) == FUNCIONES_SINTETICAS


def test_descubrir_funciones_exige_el_salto_inicial() -> None:
    datos = bytearray(construir_overlay())
    datos[4:8] = struct.pack("<I", 0)
    with pytest.raises(ValueError, match="desplazamiento 4 debe contener un salto"):
        dominio.descubrir_funciones(bytes(datos))


def test_descubrir_funciones_rechaza_entradas_fuera_del_codigo() -> None:
    corto = struct.pack("<4I", 0, salto(2, 8), 0, 0) + struct.pack("<2I", JR_RA, 0)
    with pytest.raises(ValueError, match="punto de entrada 0x58 fuera del codigo"):
        dominio.descubrir_funciones(corto)


def test_descubrir_funciones_rechaza_destinos_de_salto_fuera_del_codigo() -> None:
    datos = bytearray(construir_overlay())
    struct.pack_into("<I", datos, 0x200, salto(3, 0x3000))
    with pytest.raises(ValueError, match="destino de salto 0x3000 fuera del codigo"):
        dominio.descubrir_funciones(bytes(datos))


def test_nombre_de_funcion_usa_la_direccion_virtual() -> None:
    assert dominio.nombre_funcion(4) == "func_80010204"
    assert dominio.nombre_funcion(0x28E4) == "func_80012AE4"


def test_texto_de_simbolos_y_su_lectura_son_inversos() -> None:
    texto = dominio.texto_simbolos([0x58, 0x4])
    lineas = texto.splitlines()
    assert lineas[0].startswith("// Funciones del overlay")
    assert lineas[2] == "ranura_cargador = 0x80010200; // type:func"
    assert lineas[3] == "func_80010204 = 0x80010204; // type:func"
    assert dominio.funciones_de_simbolos(texto) == [0, 4, 0x58]


def test_funciones_de_simbolos_ignora_otros_tipos_y_comentarios() -> None:
    texto = "// nota\nD_80012B54 = 0x80012B54; // type:jtbl\nfunc_80010204 = 0x80010204; // type:func\n"
    assert dominio.funciones_de_simbolos(texto) == [4]


def test_funciones_de_simbolos_rechaza_direcciones_fuera_del_hueco() -> None:
    with pytest.raises(ValueError, match="fuera del hueco del overlay"):
        dominio.funciones_de_simbolos("func_80014A00 = 0x80014A00; // type:func\n")


def test_contar_glabel_y_palabras() -> None:
    asm = (
        "glabel func_80010204\n    /* 4 */ j x\nglabel func_8001020C\n"
        "dlabel D_1\n    /* 0 80010200 00000000 */ .word 0x00000000\n    .word 0x1\n    sw $a0, 0($a1)\n"
    )
    assert dominio.contar_glabel(asm) == 2
    assert dominio.contar_palabras(asm) == 2
    assert dominio.contar_glabel("  glabel x\nalabel y\n") == 0
    assert dominio.contar_palabras("nop\n") == 0


SCRIPT_SPLAT = """SECTIONS
{
    .overlay_a 0x80010200 : AT(overlay_a_ROM_START) SUBALIGN(16)
    {
        build/overlay/a/asm/overlay/a/codigo.s.o(.text);
        . = ALIGN(., 16);
        build/overlay/a/asm/overlay/a/data/tablas.data.s.o(.data);
        build/overlay/a/asm/overlay/a/codigo.s.o(.rodata);
    }
}
"""


def test_entradas_del_enlazador_conservan_el_orden() -> None:
    assert dominio.entradas_del_enlazador(SCRIPT_SPLAT) == [
        ("build/overlay/a/asm/overlay/a/codigo.s.o", ".text"),
        ("build/overlay/a/asm/overlay/a/data/tablas.data.s.o", ".data"),
        ("build/overlay/a/asm/overlay/a/codigo.s.o", ".rodata"),
    ]


def test_fuente_de_objeto() -> None:
    assert (
        dominio.fuente_de_objeto("build/overlay/a/asm/overlay/a/codigo.s.o", "a") == "asm/overlay/a/codigo.s"
    )


@pytest.mark.parametrize(
    "objeto",
    [
        "build/overlay/b/asm/overlay/b/codigo.s.o",
        "build/overlay/a/asm/overlay/a/codigo.s",
        "build/overlay/a/asm/overlay/a/../../../x.s.o",
        "build/overlay/a/otra/codigo.s.o",
    ],
)
def test_fuente_de_objeto_rechaza_rutas_ajenas(objeto: str) -> None:
    with pytest.raises(ValueError, match="no corresponde a un fuente de la variante 'a'"):
        dominio.fuente_de_objeto(objeto, "a")


def test_script_de_enlace_no_alinea_y_concatena_en_orden() -> None:
    entradas = dominio.entradas_del_enlazador(SCRIPT_SPLAT)
    script = dominio.generar_script_enlace(entradas)
    assert ".overlay 0x80010200 : AT(0)" in script
    assert "ALIGN" not in script
    assert "SUBALIGN" not in script
    posiciones = [script.index(f"{objeto}({seccion})") for objeto, seccion in entradas]
    assert posiciones == sorted(posiciones)
    assert "/DISCARD/" in script


def test_script_de_enlace_exige_entradas() -> None:
    with pytest.raises(ValueError, match="no referencia ningun objeto"):
        dominio.generar_script_enlace([])


@pytest.mark.parametrize(
    ("obtenido", "esperado", "posicion"),
    [(b"abc", b"abc", None), (b"abd", b"abc", 2), (b"ab", b"abc", 2), (b"abc", b"ab", 2), (b"", b"", None)],
)
def test_primera_diferencia(obtenido: bytes, esperado: bytes, posicion: int | None) -> None:
    assert dominio.primera_diferencia(obtenido, esperado) == posicion


def test_resultado_de_verificacion_ok() -> None:
    coincide, mensaje = dominio.resultado_verificacion("a", b"xyz", b"xyz")
    assert coincide
    assert mensaje == f"OK a sha256={dominio.huella_sha256(b'xyz')} bytes=3"


def test_resultado_de_verificacion_fail_indica_el_desplazamiento() -> None:
    coincide, mensaje = dominio.resultado_verificacion("b", b"xYz", b"xyz")
    assert not coincide
    assert (
        mensaje == "FAIL b primera diferencia en el desplazamiento 0x1 (obtenido 3 bytes, esperado 3 bytes)"
    )


def test_resultado_de_verificacion_fail_por_tamano() -> None:
    coincide, mensaje = dominio.resultado_verificacion("c", b"xy", b"xyz")
    assert not coincide
    assert "0x2" in mensaje


def ram_con(overlay: bytes, ranura: int = 0x8006B2F8, tamano: int = 0x40000) -> bytes:
    ram = bytearray(tamano)
    ram[0x10200 : 0x10200 + len(overlay)] = overlay
    struct.pack_into("<I", ram, 0x10200, ranura)
    return bytes(ram)


def test_valor_de_la_ranura() -> None:
    assert dominio.valor_ranura(ram_con(construir_overlay())) == 0x8006B2F8


def test_desplazamiento_en_ram_rechaza_volcados_cortos_y_enormes() -> None:
    assert dominio.desplazamiento_en_ram(bytes(0x20000), 16) == 0x10200
    with pytest.raises(ValueError, match="demasiado corto"):
        dominio.desplazamiento_en_ram(bytes(0x10200), 16)
    with pytest.raises(ValueError, match="supera el maximo"):
        dominio.desplazamiento_en_ram(bytes(dominio.MAX_BYTES_VOLCADO + 1), 16)


def test_comparar_con_ram_acepta_solo_la_diferencia_de_la_ranura() -> None:
    a, b = construir_overlay(1), construir_overlay(2)
    resultados = dominio.comparar_con_ram(ram_con(a), {"a": a, "b": b})
    assert [(r.identificador, r.coincide) for r in resultados] == [("a", True), ("b", False)]
    assert resultados[0].rangos == ((0, 4),)
    assert resultados[0].bytes_distintos == 4
    assert resultados[1].bytes_distintos > 4
    assert resultados[1].rangos[0] == (0, 4)


def test_comparar_con_ram_identica_no_tiene_rangos() -> None:
    a = bytearray(construir_overlay(1))
    a[0:4] = struct.pack("<I", 0x8006B2F8)
    (resultado,) = dominio.comparar_con_ram(ram_con(bytes(a)), {"a": bytes(a)})
    assert resultado.coincide
    assert resultado.rangos == ()
    assert resultado.bytes_distintos == 0


def test_comparar_con_ram_detecta_una_diferencia_en_el_ultimo_byte() -> None:
    a = construir_overlay(1)
    ram = bytearray(ram_con(a))
    ram[0x10200 + len(a) - 1] ^= 0xFF
    (resultado,) = dominio.comparar_con_ram(bytes(ram), {"a": a})
    assert not resultado.coincide
    assert resultado.rangos == ((0, 4), (len(a) - 1, len(a)))


def test_describir_comparacion() -> None:
    a = construir_overlay(1)
    (resultado,) = dominio.comparar_con_ram(ram_con(a), {"a": a})
    assert (
        dominio.describir_comparacion(resultado) == f"COINCIDE a bytes={len(a)} distintos=4 rangos: 0x0-0x4"
    )
    limpio = dominio.ComparacionRam("b", 8, 0, (), True)
    assert dominio.describir_comparacion(limpio) == "COINCIDE b bytes=8 distintos=0"


def test_describir_comparacion_limita_los_rangos() -> None:
    rangos = tuple((i * 8, i * 8 + 1) for i in range(20))
    texto = dominio.describir_comparacion(dominio.ComparacionRam("c", 200, 20, rangos, False))
    assert texto.startswith("DIFIERE c bytes=200 distintos=20 rangos: 0x0-0x1")
    assert texto.endswith(" y 4 mas")
    assert texto.count("-0x") == dominio.MAX_RANGOS_INFORMADOS


def test_instrucciones_de_referencia_de_los_ayudantes() -> None:
    assert JR_RA == 0x03E00008
    assert ADDIU_SP >> 16 == 0x27BD


def test_un_epilogo_con_inmediato_positivo_no_es_inicio_de_funcion() -> None:
    datos = construir_overlay()
    palabra = struct.unpack_from("<I", datos, OFFSET_EPILOGO)[0]
    assert palabra == EPILOGO_SP
    assert palabra >> 16 == ADDIU_SP >> 16
    inicios = dominio.descubrir_funciones(datos)
    assert OFFSET_EPILOGO not in inicios
    assert 0x1000 in inicios

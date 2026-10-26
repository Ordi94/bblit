import struct
from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import dominio
from tools.reconstruccion.dominio import CabeceraPsx

CAMPOS = {
    "pc0": "0x80014A08",
    "gp0": 0,
    "t_addr": "0x80014A00",
    "t_size": "0x55000",
    "d_addr": "0x0",
    "d_size": "0",
    "b_addr": "0x0",
    "b_size": "0x0",
    "s_addr": "0x801FFFF0",
    "s_size": "0x0",
    "region": "Sony Computer Entertainment Inc. for North America area",
}


def referencia_datos(**cambios: Any) -> Any:
    datos = {
        "nombre": "SLUS_008.38",
        "sha256": "a" * 64,
        "sha1": "b" * 40,
        "tamano": 0x800 + 0x55000,
        "cabecera": dict(CAMPOS),
    }
    datos.update(cambios)
    return datos


def test_cabecera_desde_datos_acepta_hexadecimal_y_decimal() -> None:
    cabecera = dominio.cabecera_desde_datos(CAMPOS)
    assert cabecera.pc0 == 0x80014A08
    assert cabecera.gp0 == 0
    assert cabecera.t_size == 0x55000
    assert cabecera.d_size == 0
    assert cabecera.s_addr == 0x801FFFF0
    assert cabecera.region.endswith("North America area")


@pytest.mark.parametrize(
    ("campo", "valor", "mensaje"),
    [
        ("pc0", None, "campo 'pc0': se esperaba un numero"),
        ("pc0", True, "campo 'pc0': se esperaba un numero"),
        ("pc0", 1.5, "campo 'pc0': se esperaba un numero"),
        ("pc0", "zz", "campo 'pc0': numero no valido"),
        ("pc0", "0xZZ", "campo 'pc0': numero no valido"),
        ("pc0", -1, "fuera del rango de 32 bits"),
        ("pc0", 2**32, "fuera del rango de 32 bits"),
        ("region", 5, "campo 'region'"),
        ("region", "caf\u00e9", "campo 'region'"),
        ("region", "a\x00b", "campo 'region'"),
        ("region", "x" * 0x800, "no cabe en la cabecera"),
    ],
)
def test_cabecera_con_campos_invalidos(campo: Any, valor: Any, mensaje: Any) -> None:
    datos = dict(CAMPOS)
    datos[campo] = valor
    with pytest.raises(ValueError, match=mensaje):
        dominio.cabecera_desde_datos(datos)


def test_cabecera_que_no_es_objeto() -> None:
    with pytest.raises(ValueError, match="la cabecera debe ser un objeto"):
        dominio.cabecera_desde_datos([1])


def test_referencia_valida() -> None:
    referencia = dominio.referencia_desde_datos(referencia_datos())
    assert referencia.nombre == "SLUS_008.38"
    assert referencia.tamano == 350208
    assert referencia.cabecera.t_addr == 0x80014A00


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"nombre": "../x"}, "campo 'nombre'"),
        ({"nombre": 5}, "campo 'nombre'"),
        ({"sha256": "A" * 64}, "campo 'sha256'"),
        ({"sha256": None}, "campo 'sha256'"),
        ({"sha1": "b" * 39}, "campo 'sha1'"),
        ({"tamano": 5}, "campo 'tamano': no coincide"),
        ({"tamano": "x"}, "campo 'tamano'"),
    ],
)
def test_referencia_invalida(cambios: Any, mensaje: Any) -> None:
    with pytest.raises(ValueError, match=mensaje):
        dominio.referencia_desde_datos(referencia_datos(**cambios))


def test_referencia_que_no_es_objeto() -> None:
    with pytest.raises(ValueError, match="debe ser un objeto"):
        dominio.referencia_desde_datos("texto")


def test_serializar_y_leer_cabecera_son_inversas() -> None:
    cabecera = dominio.cabecera_desde_datos(CAMPOS)
    datos = dominio.serializar_cabecera(cabecera)
    assert len(datos) == 0x800
    assert dominio.leer_cabecera(datos) == cabecera


def test_leer_cabecera_con_region_que_ocupa_hasta_el_final() -> None:
    cabecera = CabeceraPsx(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "r" * (0x800 - 0x4C - 1))
    assert dominio.leer_cabecera(dominio.serializar_cabecera(cabecera)).region == "r" * (0x800 - 0x4C - 1)
    crudo = bytearray(dominio.serializar_cabecera(cabecera))
    crudo[0x7FF] = ord("z")
    assert dominio.leer_cabecera(bytes(crudo)).region == "r" * (0x800 - 0x4C - 1) + "z"


@pytest.mark.parametrize("datos", [b"", b"PS-X EXE", b"X" * 0x800, b"PS-X EXF" + b"\x00" * 0x800])
def test_leer_cabecera_invalida(datos: Any) -> None:
    with pytest.raises(ValueError, match="cabecera PS-X EXE valida"):
        dominio.leer_cabecera(datos)


def test_ensamblar_ejecutable_valida_la_longitud_del_cuerpo() -> None:
    cabecera = CabeceraPsx(0, 0, 0x80010000, 8, 0, 0, 0, 0, 0, 0, "r")
    ejecutable = dominio.ensamblar_ejecutable(cabecera, b"12345678")
    assert ejecutable[0x800:] == b"12345678"
    assert ejecutable[:8] == b"PS-X EXE"
    with pytest.raises(ValueError, match="el cuerpo enlazado mide 3 bytes y la cabecera declara t_size=8"):
        dominio.ensamblar_ejecutable(cabecera, b"123")


def test_describir_diferencia() -> None:
    base = bytes(0x900)
    assert dominio.describir_diferencia(base, base) == "sin diferencias"
    cabecera = bytearray(base)
    cabecera[0x10] = 1
    assert (
        dominio.describir_diferencia(bytes(cabecera), base)
        == "primera diferencia en el desplazamiento 0x10 (cabecera)"
    )
    cuerpo = bytearray(base)
    cuerpo[0x800] = 1
    assert (
        dominio.describir_diferencia(bytes(cuerpo), base)
        == "primera diferencia en el desplazamiento 0x800 (cuerpo)"
    )
    assert dominio.describir_diferencia(base[:10], base) == "tamanos distintos: 10 y 2304 bytes"


def test_resultado_de_verificacion() -> None:
    assert dominio.resultado_verificacion("a" * 64, "a" * 64) == (
        True,
        f"OK esperado={'a' * 64} obtenido={'a' * 64}",
    )
    assert dominio.resultado_verificacion("b" * 64, "a" * 64) == (
        False,
        f"FAIL esperado={'a' * 64} obtenido={'b' * 64}",
    )


def test_simbolo_de_entrada_se_genera_si_nadie_lo_declaro() -> None:
    assert dominio.texto_simbolos_entrada(0x80014A08, "") == "func_80014A08 = 0x80014A08; // type:func\n"
    otros = "otra = 0x80014A0C; // type:func\n"
    assert dominio.texto_simbolos_entrada(0x80014A08, otros) == "func_80014A08 = 0x80014A08; // type:func\n"


@pytest.mark.parametrize(
    "existente", ["main = 0x80014A08; // type:func", "inicio=0x80014a08;", "x = 0x080014A08 ;"]
)
def test_simbolo_de_entrada_no_se_duplica(existente: Any) -> None:
    assert dominio.texto_simbolos_entrada(0x80014A08, existente) == ""


SCRIPT = """
    .main 0x80014A00 : AT(main_ROM_START) SUBALIGN(16)
    {
        build/asm/text.s.o(.text);
        build/asm/data/data.data.s.o(.data);
        build/asm/text.s.o(.rodata);
        /* build/ignorado.o sin parentesis */
    }
"""


def test_objetos_del_enlazador_sin_repetidos_y_en_orden() -> None:
    assert dominio.objetos_del_enlazador(SCRIPT) == ["build/asm/text.s.o", "build/asm/data/data.data.s.o"]
    assert dominio.objetos_del_enlazador("nada") == []


def test_fuente_de_objeto() -> None:
    assert dominio.fuente_de_objeto("build/asm/data/data.data.s.o") == "asm/data/data.data.s"


@pytest.mark.parametrize("objeto", ["asm/text.s.o", "build/src/main.c.o", "build/../x.s.o", "build/a.s"])
def test_fuente_de_objeto_desconocida(objeto: Any) -> None:
    with pytest.raises(ValueError, match="no corresponde a un ensamblador fuente conocido"):
        dominio.fuente_de_objeto(objeto)


def test_comandos_son_listas_con_cada_ruta_como_un_unico_argumento() -> None:
    ruta = Path("D:/mi disco (copia)/binutils/as.exe")
    comando = dominio.comando_ensamblar(ruta, "asm/mi archivo (1).s", "build/mi objeto.o", "asm/inc luir")
    assert comando == [
        str(ruta),
        "-EL",
        "-march=r3000",
        "-mips1",
        "-G0",
        "-I",
        "asm/inc luir",
        "-o",
        "build/mi objeto.o",
        "asm/mi archivo (1).s",
    ]
    enlazar = dominio.comando_enlazar(Path("ld.exe"), ["a b.ld", "c.txt"], "build/x.elf", "build/x.map")
    assert enlazar == [
        "ld.exe",
        "-EL",
        "--no-warn-rwx-segments",
        "-T",
        "a b.ld",
        "-T",
        "c.txt",
        "-o",
        "build/x.elf",
        "-Map",
        "build/x.map",
    ]
    assert dominio.comando_objcopy(Path("oc.exe"), "e.elf", "e.bin") == [
        "oc.exe",
        "-O",
        "binary",
        "e.elf",
        "e.bin",
    ]
    assert dominio.comando_splat("py", "config/splat.yaml") == [
        "py",
        "-X",
        "utf8",
        "-m",
        "splat",
        "split",
        "config/splat.yaml",
    ]


def test_estructura_binaria_de_la_cabecera_campo_a_campo() -> None:
    datos = dominio.serializar_cabecera(dominio.cabecera_desde_datos(CAMPOS))
    assert struct.unpack_from("<10I", datos, 0x10) == (
        0x80014A08,
        0,
        0x80014A00,
        0x55000,
        0,
        0,
        0,
        0,
        0x801FFFF0,
        0,
    )

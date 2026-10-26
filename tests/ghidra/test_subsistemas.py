import csv
import io

import pytest
from tools.ghidra import subsistemas
from tools.ghidra.dominio import Simbolo
from tools.ghidra.ensamblador import dividir_por_funcion
from tools.ghidra.exportaciones import Cadena
from tools.ghidra.grafo import construir_grafo
from tools.ghidra.subsistemas import (
    COLUMNAS_SUBSISTEMAS,
    Rango,
    caracterizar,
    familia_de_libreria,
    formatear_subsistemas_csv,
    parsear_rangos,
    proponer_rangos,
    resumir_por_nombre,
)
from tools.ghidra.tablas import detectar_corridas

from tests.ghidra.escenario import VSYNC, A, B, C, D, E, G, segmento_programa, simbolos, texto_asm
from tests.ghidra.segmentos import BASE

CABECERA = "nombre,inicio,fin\n"


def _grafo():
    corridas = detectar_corridas(
        segmento_programa(), BASE, (0x8005DEA0, 0x80069A00), (0x80014AC4, 0x80045DA0)
    )
    return construir_grafo(dividir_por_funcion(texto_asm()), simbolos(), corridas)


RANGOS = [
    Rango("arranque", A, B),
    Rango("logica", B, D),
    Rango("despacho", D, E),
    Rango("despacho", E, G + 8),
]


@pytest.mark.parametrize(
    ("nombre", "familia"),
    [
        ("CdControlB", "cd"),
        ("SpuSetKey", "audio_spu"),
        ("PadGetState", "mando"),
        ("MemCardExist", "tarjeta_de_memoria"),
        ("open", "tarjeta_de_memoria"),
        ("DrawOTag", "graficos"),
        ("RotMatrixZYX", "geometria_gte"),
        ("ratan2", "geometria_gte"),
        ("VSync", "sistema"),
        ("func_8004FADC", None),
    ],
)
def test_clasifica_las_librerias_por_familia(nombre: str, familia: str | None) -> None:
    assert familia_de_libreria(nombre) == familia


def test_los_rangos_se_leen_ordenados_y_un_nombre_puede_repetirse() -> None:
    texto = CABECERA + "b,0x80014B00,0x80014C00\na,0x80014A00,0x80014B00\nb,0x80014C00,0x80014C10\n"
    assert parsear_rangos(texto) == [
        Rango("a", 0x80014A00, 0x80014B00),
        Rango("b", 0x80014B00, 0x80014C00),
        Rango("b", 0x80014C00, 0x80014C10),
    ]


@pytest.mark.parametrize(
    ("texto", "mensaje"),
    [
        ("", "la cabecera debe ser nombre,inicio,fin"),
        ("nombre,inicio\n", "la cabecera debe ser nombre,inicio,fin"),
        (CABECERA + "a,0x80014A00\n", "fila 2: se esperaban 3 campos"),
        (CABECERA + "A,0x80014A00,0x80014B00\n", "fila 2: nombre invalido"),
        (CABECERA + "1a,0x80014A00,0x80014B00\n", "fila 2: nombre invalido"),
        (CABECERA + "a,0x80014B00,0x80014B00\n", "fila 2: el rango esta vacio"),
        (CABECERA + "a,80014A00,0x80014B00\n", "fila 2: la direccion debe empezar por 0x"),
        (CABECERA + "a,0xZZ,0x80014B00\n", "fila 2: la direccion no es hexadecimal"),
        (CABECERA + "a,0x80014A02,0x80014B00\n", "fila 2: la direccion debe estar alineada a 4"),
        (
            CABECERA + "a,0x100000000,0x100000004\n",
            "fila 2: la direccion debe estar alineada a 4 y ser de 32 bits",
        ),
        (CABECERA + "a,0x80014A00,0x80014B00\nb,0x80014AF0,0x80014C00\n", "b se solapa con a"),
    ],
)
def test_rechaza_rangos_invalidos(texto: str, mensaje: str) -> None:
    with pytest.raises(ValueError, match=mensaje):
        parsear_rangos(texto)


def test_rechaza_demasiados_rangos_y_nombres_demasiado_largos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subsistemas, "MAX_RANGOS", 1)
    with pytest.raises(ValueError, match="mas de 1 filas"):
        parsear_rangos(CABECERA + "a,0x80014A00,0x80014B00\nb,0x80014B00,0x80014C00\n")
    monkeypatch.setattr(subsistemas, "MAX_LONGITUD_NOMBRE", 2)
    with pytest.raises(ValueError, match="nombre invalido"):
        parsear_rangos(CABECERA + "abc,0x80014A00,0x80014B00\n")


def test_caracteriza_funciones_librerias_cadenas_regiones_y_dependencias() -> None:
    cadenas = [
        Cadena(0x80060000, 10, "hola mundo"),
        Cadena(0x80060010, 2, "\x01\x02"),
        Cadena(0x80069330, 4, "dato"),
    ]
    resultado = {s.nombre: s for s in caracterizar(RANGOS, simbolos(), _grafo(), cadenas)}
    assert list(resultado) == ["arranque", "logica", "despacho"]
    arranque, logica, despacho = resultado["arranque"], resultado["logica"], resultado["despacho"]
    assert [f[0] for f in arranque.funciones] == [A]
    assert arranque.librerias == (("VSync", 1),)
    assert arranque.cadenas == ((0x80060000, "hola mundo"),)
    assert dict(arranque.regiones) == {"datos_y_tablas": 1}
    assert arranque.dependencias == (("logica", 1, 0),)
    assert arranque.bytes_totales == 0x34
    assert [f[0] for f in logica.funciones] == [B, C]
    assert logica.llamadas_internas == 1
    assert dict(logica.regiones) == {"estado_global": 1, "datos_pequenos": 2}
    assert logica.usado_por == (("arranque", 1),)
    assert logica.cadenas == ((0x80069330, "dato"),)
    assert [f[0] for f in despacho.funciones] == [D, E, G]
    assert despacho.rangos == ((D, E), (E, G + 8))
    assert despacho.llamadas_internas == 1
    assert dict(despacho.regiones) == {"datos_y_tablas": 1}
    assert despacho.dependencias == ()
    assert despacho.librerias == ()


def test_las_dependencias_incluyen_los_datos_compartidos() -> None:
    grafo = _grafo()
    compartido = type(grafo)(
        aristas=grafo.aristas,
        punteros=grafo.punteros,
        datos={**grafo.datos, 0x80010000: (A, B, E)},
        tablas_salto=grafo.tablas_salto,
        saltos_switch=grafo.saltos_switch,
        destinos_ajenos=0,
        sin_resolver=0,
    )
    resultado = {s.nombre: s for s in caracterizar(RANGOS, simbolos(), compartido, [])}
    assert ("despacho", 0, 1) in resultado["arranque"].dependencias
    assert ("arranque", 0, 1) in resultado["despacho"].dependencias


def test_propone_rangos_por_familia_dominante_entre_los_cortes() -> None:
    rangos = proponer_rangos(simbolos(), _grafo(), [B, D, 0x1234, B])
    assert rangos == [
        Rango("sistema_01", A, B),
        Rango("logica_02", B, D),
        Rango("logica_03", D, G + 8),
    ]
    assert proponer_rangos([Simbolo("VSync", VSYNC, "func", 8)], _grafo(), []) == []


def test_el_csv_de_subsistemas_y_el_resumen() -> None:
    resultado = caracterizar(RANGOS, simbolos(), _grafo(), [])
    filas = list(csv.reader(io.StringIO(formatear_subsistemas_csv(resultado))))
    assert tuple(filas[0]) == COLUMNAS_SUBSISTEMAS
    assert filas[1][:2] == ["arranque", f"0x{A:08X}-0x{B:08X}"]
    assert filas[1][4] == "VSync:1"
    assert filas[2][-1] == "arranque:1"
    assert dict(resumir_por_nombre(resultado)) == {"arranque": 1, "logica": 2, "despacho": 3}


def test_una_cadena_con_salto_de_linea_o_tabulacion_sirve_de_evidencia() -> None:
    cadenas = [
        Cadena(0x80060000, 12, "hola mundo\n"),
        Cadena(0x80069330, 8, "con\ttab ok"),
        Cadena(0x80060010, 6, "ab\x01cde"),
    ]
    resultado = {s.nombre: s for s in caracterizar(RANGOS, simbolos(), _grafo(), cadenas)}
    assert resultado["arranque"].cadenas == ((0x80060000, "hola mundo"),)
    assert resultado["logica"].cadenas == ((0x80069330, "con\ttab ok"),)

"""Reglas de negocio del overlay: variantes, carga, determinismo y diferencias esperadas."""

import json
import re
import struct
from pathlib import Path

import pytest
from tools.overlay import cli, dominio, extraccion
from tools.reconstruccion.infraestructura import ProcesoError

from tests.overlay.ayudantes import (
    FUNCIONES_SINTETICAS,
    Registro,
    construir_overlay,
    contenedor,
    escribir_sistema_de_archivos,
    variantes_conocidas,
)

A = construir_overlay(1)
B = construir_overlay(2)
CONOCIDAS = variantes_conocidas({"a": A, "b": B}, {"a": 3, "b": 1})
DISCO = {
    "LEVEL1/L01A.BZZ": contenedor(A),
    "LEVEL1/L01B.BZZ": contenedor(A),
    "LEVEL1/TITLE.BZZ": contenedor(A),
    "DEMO/DEMO1.BZZ": contenedor(B),
    "LOADING/CARGA.BZZ": contenedor(None),
}


def test_el_overlay_se_carga_en_la_base_documentada() -> None:
    assert dominio.DIRECCION_CARGA == 0x80010200
    assert dominio.FIN_HUECO == 0x80014A00
    assert dominio.TIPO_SECCION_CODIGO == 2


def test_hay_tres_variantes_con_los_tamanos_documentados() -> None:
    tamanos = {v.identificador: v.tamano for v in dominio.VARIANTES_CONOCIDAS}
    assert tamanos == {"a": 17076, "b": 17072, "c": 17080}
    assert len({v.sha256 for v in dominio.VARIANTES_CONOCIDAS}) == 3


def test_el_overlay_esta_en_setenta_y_seis_contenedores() -> None:
    assert sum(v.cantidad_archivos for v in dominio.VARIANTES_CONOCIDAS) == 76


def test_cada_variante_cabe_en_el_hueco_antes_del_ejecutable() -> None:
    for variante in dominio.VARIANTES_CONOCIDAS:
        assert dominio.DIRECCION_CARGA + variante.tamano <= dominio.FIN_HUECO
        assert variante.tamano % 4 == 0


def test_las_variantes_difieren_en_pocas_palabras_pero_no_en_el_tamano_del_hueco() -> None:
    diferencias = sum(1 for x, y in zip(A, B, strict=True) if x != y)
    assert 0 < diferencias < len(A) // 10


def test_la_extraccion_es_determinista(tmp_path: Path) -> None:
    disco = escribir_sistema_de_archivos(tmp_path / "disco", DISCO)
    salidas = []
    for corrida in ("uno", "dos"):
        raiz = tmp_path / corrida
        variantes, binarios = extraccion.extraer_variantes(disco, CONOCIDAS)
        extraccion.escribir_extraccion(raiz, variantes, binarios)
        salidas.append(
            [(raiz / "config" / "overlay.json").read_bytes()]
            + [(raiz / "expected" / "overlay" / f"{v.identificador}.bin").read_bytes() for v in variantes]
        )
    assert salidas[0] == salidas[1]


def test_contenedores_con_el_mismo_codigo_forman_una_unica_variante(tmp_path: Path) -> None:
    disco = escribir_sistema_de_archivos(tmp_path / "disco", DISCO)
    variantes, _ = extraccion.extraer_variantes(disco, CONOCIDAS)
    assert variantes[0].archivos == ("LEVEL1/L01A.BZZ", "LEVEL1/L01B.BZZ", "LEVEL1/TITLE.BZZ")


def test_un_contenedor_sin_seccion_de_codigo_no_aporta_variante(tmp_path: Path) -> None:
    disco = escribir_sistema_de_archivos(tmp_path / "disco", DISCO)
    variantes, _ = extraccion.extraer_variantes(disco, CONOCIDAS)
    asignados = {archivo for variante in variantes for archivo in variante.archivos}
    assert "LOADING/CARGA.BZZ" not in asignados
    assert len(asignados) == 4


def test_un_overlay_mayor_que_el_hueco_se_rechaza_nombrando_el_contenedor(tmp_path: Path) -> None:
    grande = bytes(dominio.TAMANO_HUECO + 4)
    disco = escribir_sistema_de_archivos(tmp_path / "disco", {"DEMO/GRANDE.BZZ": contenedor(grande)})
    with pytest.raises(ValueError, match=re.escape("DEMO/GRANDE.BZZ: tamano de la seccion de codigo")):
        extraccion.extraer_variantes(disco, CONOCIDAS)


def test_una_edicion_con_codigo_distinto_se_rechaza_en_vez_de_aceptarse(tmp_path: Path) -> None:
    disco = escribir_sistema_de_archivos(
        tmp_path / "disco", {**DISCO, "DEMO/NUEVO.BZZ": contenedor(construir_overlay(7))}
    )
    with pytest.raises(ValueError, match="variante desconocida del overlay"):
        extraccion.extraer_variantes(disco, CONOCIDAS)


def test_si_falta_una_variante_la_extraccion_no_es_completa(tmp_path: Path) -> None:
    sin_b = {nombre: datos for nombre, datos in DISCO.items() if nombre != "DEMO/DEMO1.BZZ"}
    disco = escribir_sistema_de_archivos(tmp_path / "disco", sin_b)
    with pytest.raises(ValueError, match="falta la variante 'b'"):
        extraccion.extraer_variantes(disco, CONOCIDAS)


def test_los_puntos_de_entrada_del_ejecutable_son_inicios_de_funcion() -> None:
    inicios = dominio.descubrir_funciones(A)
    assert set(dominio.OFFSETS_ENTRADA) <= set(inicios)
    assert [0x80010200 + offset for offset in dominio.OFFSETS_ENTRADA] == [
        0x80010204,
        0x8001020C,
        0x80010258,
        0x80012AB0,
        0x80012AE4,
    ]


def test_las_funciones_son_comunes_aunque_los_datos_y_el_final_difieran() -> None:
    sin_una_palabra = A[:0x28E0] + A[0x28E4:]
    assert dominio.descubrir_funciones(sin_una_palabra) == dominio.descubrir_funciones(A)
    assert dominio.fin_de_codigo(sin_una_palabra) == dominio.fin_de_codigo(A) - 4
    assert dominio.descubrir_funciones(B) == dominio.descubrir_funciones(A) == FUNCIONES_SINTETICAS


def test_la_ranura_del_cargador_es_la_unica_diferencia_esperada_con_la_ram() -> None:
    ram = bytearray(0x40000)
    ram[0x10200 : 0x10200 + len(A)] = A
    ram[0x10200:0x10204] = struct.pack("<I", 0x8006B2F8)
    (coincidencia,) = dominio.comparar_con_ram(bytes(ram), {"a": A})
    assert coincidencia.coincide
    assert coincidencia.rangos == ((0, 4),)
    ram[0x10200 + 0x154] ^= 1
    (alterada,) = dominio.comparar_con_ram(bytes(ram), {"a": A})
    assert not alterada.coincide
    assert alterada.rangos == ((0, 4), (0x154, 0x155))


def test_dos_variantes_se_distinguen_por_la_ram() -> None:
    ram = bytearray(0x40000)
    ram[0x10200 : 0x10200 + len(B)] = B
    resultados = {c.identificador: c.coincide for c in dominio.comparar_con_ram(bytes(ram), {"a": A, "b": B})}
    assert resultados == {"a": False, "b": True}


def test_el_primer_cambio_de_un_binario_reconstruido_se_localiza_con_su_desplazamiento() -> None:
    alterado = bytearray(A)
    alterado[0x28F0] ^= 0x10
    coincide, mensaje = dominio.resultado_verificacion("a", bytes(alterado), A)
    assert not coincide
    assert "0x28F0" in mensaje


def test_el_archivo_de_simbolos_no_declara_nada_fuera_del_hueco() -> None:
    texto = dominio.texto_simbolos(dominio.descubrir_funciones(A))
    for offset in dominio.funciones_de_simbolos(texto):
        assert 0 <= offset < dominio.TAMANO_HUECO
    assert texto.count("type:func") == len(FUNCIONES_SINTETICAS) + 1


def test_la_configuracion_registra_huella_tamano_y_contenedores(tmp_path: Path) -> None:
    disco = escribir_sistema_de_archivos(tmp_path / "disco", DISCO)
    raiz = tmp_path / "repo"
    (raiz / "config").mkdir(parents=True)
    assert cli.main(["extraer"], {"BBLIT_DISC": str(disco)}, raiz, Registro({}), CONOCIDAS) == 0
    datos = json.loads((raiz / "config" / "overlay.json").read_text(encoding="utf-8"))
    assert [(v["id"], v["tamano"], len(v["archivos"])) for v in datos["variantes"]] == [
        ("a", len(A), 3),
        ("b", len(B), 1),
    ]
    assert all(len(v["sha256"]) == 64 for v in datos["variantes"])


def test_una_particion_con_palabras_sin_decodificar_no_se_acepta(tmp_path: Path) -> None:
    disco = escribir_sistema_de_archivos(tmp_path / "disco", DISCO)
    raiz = tmp_path / "repo"
    (raiz / "config").mkdir(parents=True)
    for identificador in ("a", "b"):
        (raiz / "config" / f"splat_overlay_{identificador}.yaml").write_text("x: 1\n", encoding="utf-8")
    entorno = {"BBLIT_DISC": str(disco)}
    registro = Registro({}, palabras=3)
    assert cli.main(["extraer"], entorno, raiz, registro, CONOCIDAS) == 0
    assert cli.main(["simbolos"], entorno, raiz, registro, CONOCIDAS) == 0
    assert cli.main(["split"], entorno, raiz, registro, CONOCIDAS) == 1


def test_proceso_error_es_un_error_controlado_de_la_cli() -> None:
    assert ProcesoError in cli.ERRORES_CONTROLADOS

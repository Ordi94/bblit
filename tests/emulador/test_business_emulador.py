"""Reglas de negocio del oraculo: entradas rechazadas, deteccion de pantalla y apagado garantizado."""

import pytest
from tools.emulador import cli, comparacion, pantalla, sesion
from tools.emulador.cliente import ClienteRedux
from tools.emulador.dominio import RAM_TAMANO, EmuladorError, comparar_regiones, offset_de_ram

from tests.emulador import sintetica
from tests.emulador.dobles import ClienteFalso, Reloj, ram_con


def test_ram_de_tamano_distinto_se_rechaza_al_comparar(tmp_path):
    truncado = tmp_path / "ram.bin"
    truncado.write_bytes(bytes(RAM_TAMANO - 4096))
    with pytest.raises(ValueError, match="2097152"):
        comparacion.comparar_volcados(truncado, truncado, 0x80000000)


def test_ram_de_tamano_distinto_se_rechaza_al_descargarla_del_emulador():
    cliente = ClienteRedux(8080, lambda m, u, t: bytes(1000), lambda s: None)
    with pytest.raises(ValueError, match="2097152"):
        cliente.volcar_ram()


@pytest.mark.parametrize("direccion", [0x80200000, 0x7FFFFFFF, 0x00014A00, 0xA0000000])
def test_direccion_fuera_de_ram_se_rechaza(direccion):
    with pytest.raises(ValueError, match="direccion"):
        offset_de_ram(direccion)


def test_region_que_se_sale_de_la_ram_se_rechaza():
    with pytest.raises(ValueError, match="sobrepasa"):
        offset_de_ram(0x801FFF00, 0x200)


def test_el_codigo_cargado_en_ram_coincide_con_el_ejecutable():
    exe = sintetica.ejecutable_psx(0x80014A00)
    ram = ram_con(0x14A00, exe[0x800:])
    resultado = comparar_regiones(0x80014A00, ram[0x14A00 : 0x14A00 + 512], exe[0x800:])
    assert resultado.porcentaje_igual == 100.0


def test_un_cambio_en_el_codigo_se_localiza_en_su_offset_exacto():
    exe = sintetica.ejecutable_psx()
    modificada = bytearray(exe[0x800:])
    modificada[0x42] ^= 0xFF
    resultado = comparar_regiones(0x80014A00, bytes(modificada), exe[0x800:])
    assert resultado.bytes_distintos == 1
    assert resultado.primer_offset_distinto == 0x42


def test_archivo_mas_corto_que_la_region_compara_solo_el_minimo():
    resultado = comparar_regiones(0x80014A00, bytes(100), bytes(60))
    assert resultado.bytes_comparados == 60
    assert resultado.tamano_distinto


def test_pantalla_negra_se_decide_por_pixeles_no_por_tamano_de_archivo():
    negro_pesado = sintetica.construir_png(
        64, 48, b"".join(bytes([0, 0, 0, 255 - (i % 7)]) for i in range(64 * 48))
    )
    claro_ligero = sintetica.construir_png(8, 8, bytes([255, 255, 255, 255]) * 64)
    assert len(negro_pesado) > len(claro_ligero)
    assert pantalla.es_pantalla_negra(negro_pesado)
    assert not pantalla.es_pantalla_negra(claro_ligero)


def test_un_logo_pequeno_sobre_fondo_negro_cuenta_como_contenido():
    # El logo de la consola ocupa pocos pixeles sobre negro: la cota debe verlo.
    logo = sintetica.png_con_contenido(512, 240, 255, 512 * 240 // 40)
    assert not pantalla.es_pantalla_negra(logo)


def test_el_apagado_ocurre_aunque_la_espera_falle(tmp_path):
    reloj = Reloj()
    terminados = []
    config = sesion.ConfigSesion(
        imagen=tmp_path / "i.cue",
        bios=tmp_path / "b.bin",
        ejecutable=tmp_path / "r.exe",
        carpeta_trabajo=tmp_path / "t",
        salida=tmp_path / "s",
        tope_hito=3.0,
    )
    with pytest.raises(EmuladorError):
        sesion.ejecutar_sesion(
            config,
            cliente=ClienteFalso(pantallas=[sintetica.png_negro()]),
            lanzar=lambda *a: 42,
            terminar=terminados.append,
            listar=lambda: [],
            puerto_en_uso=lambda puerto: False,
            reloj=reloj,
            dormir=reloj.dormir,
        )
    assert terminados == [42]


def test_apagar_no_depende_del_cliente_http(monkeypatch):
    def cliente_roto(puerto):
        raise AssertionError("apagar no debe crear un cliente HTTP")

    terminados = []
    monkeypatch.setattr(cli, "ClienteRedux", cliente_roto)
    monkeypatch.setattr(cli.proceso, "terminar_procesos", terminados.append)
    monkeypatch.setattr(cli.proceso, "listar_procesos", lambda: [])
    monkeypatch.setattr(cli.proceso, "puerto_ocupado", lambda puerto: False)
    assert cli.main(["apagar"]) == 0
    assert terminados == [None]

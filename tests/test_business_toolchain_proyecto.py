"""Reglas del proyecto sobre el toolchain: lock versionado y cabecera del ejecutable de referencia."""

import json
import struct
from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import dominio as reconstruccion

from psxdecomp.toolchain import instalacion
from psxdecomp.toolchain.dominio import host_admitido

RAIZ_REPO = Path(__file__).resolve().parents[1]


def test_la_cabecera_psx_exe_generada_coincide_campo_a_campo_con_los_hechos_verificados() -> None:
    datos = json.loads((RAIZ_REPO / "config" / "ejecutable.json").read_text(encoding="utf-8"))
    referencia = reconstruccion.referencia_desde_datos(datos)
    cabecera = reconstruccion.serializar_cabecera(referencia.cabecera)
    assert len(cabecera) == 0x800
    assert cabecera[:8] == b"PS-X EXE"
    pc0, gp0, t_addr, t_size, d_addr, d_size, b_addr, b_size, s_addr, s_size = struct.unpack_from(
        "<10I", cabecera, 0x10
    )
    assert (pc0, gp0, t_addr, t_size) == (0x80014A08, 0, 0x80014A00, 0x55000)
    assert (d_addr, d_size, b_addr, b_size) == (0, 0, 0, 0)
    assert (s_addr, s_size) == (0x801FFFF0, 0)
    region = b"Sony Computer Entertainment Inc. for North America area"
    assert cabecera[0x4C : 0x4C + len(region)] == region
    assert set(cabecera[0x4C + len(region) :]) == {0}
    assert set(cabecera[8:0x10]) == {0}
    assert set(cabecera[0x38:0x4C]) == {0}
    assert referencia.tamano == 350208
    assert referencia.sha256 == "0fad70d9b4cb324d78f113f7fd70c0aa954388fefad01af373509e0473c87df0"


@pytest.fixture(scope="module")
def lock() -> Any:
    """Lock versionado: debe cubrir todo lo que exige la reconstruccion y el analisis de funciones."""
    return instalacion.leer_lock(RAIZ_REPO / "config" / "toolchain.lock.json")


def test_todos_los_componentes_usan_https_en_hosts_admitidos_y_huella_completa(lock: Any) -> None:
    for componente in lock.values():
        assert componente.url.startswith("https://")
        assert host_admitido(componente.url.split("/")[2])
        assert len(componente.sha256) == 64
        assert componente.notas


def test_psyq_4_4_trae_compilador_281_ensamblador_enlazador_dmpsx_bibliotecas_y_cabeceras(lock: Any) -> None:
    psyq = dict(lock["psyq-4.4"].archivos_clave)
    assert psyq["cc1psx"].endswith("CC1PSX.EXE")
    assert psyq["aspsx"].endswith("ASPSX.EXE")
    assert psyq["psylink"].endswith("PSYLINK.EXE")
    assert psyq["dmpsx"].endswith("DMPSX.EXE")
    assert psyq["libapi"].endswith(".LIB")
    assert psyq["libgpu_h"].endswith(".H")
    assert "GCC 2.8.1" in lock["psyq-4.4"].notas


def test_psyq_4_1_aporta_el_compilador_272(lock: Any) -> None:
    assert lock["psyq-4.1"].formato == "rar_iso"
    assert "2.7.2" in lock["psyq-4.1"].notas
    assert lock["psyq-4.1"].ruta_clave("cc1psx") == "GNU/CC1PSX.EXE"


def test_binutils_mipsel_little_endian_con_las_cuatro_herramientas(lock: Any) -> None:
    claves = dict(lock["binutils-mipsel"].archivos_clave)
    assert set(claves) == {"as", "ld", "objcopy", "objdump"}
    assert all("mipsel" in ruta for ruta in claves.values())


def test_herramientas_de_decompilacion_estan_fijadas_a_un_commit(lock: Any) -> None:
    esperadas = (
        ("maspsx", "maspsx", "maspsx.py"),
        ("m2c", "m2c", "m2c.py"),
        ("asm-differ", "diff", "diff.py"),
    )
    for nombre, alias, archivo in esperadas:
        assert lock[nombre].quitar_raiz is True
        assert lock[nombre].ruta_clave(alias) == archivo
        assert "/archive/" in lock[nombre].url
        assert len(lock[nombre].url.rsplit("/", 1)[1].removesuffix(".zip")) == 40


def test_el_lock_real_del_repositorio_es_valido() -> None:
    lock = instalacion.leer_lock(RAIZ_REPO / "config" / "toolchain.lock.json")
    assert set(lock) >= {"psyq-4.4", "psyq-4.1", "binutils-mipsel", "maspsx", "m2c", "asm-differ"}
    assert lock["psyq-4.4"].ruta_clave("cc1psx") == "pssn/bin/CC1PSX.EXE"
    assert lock["binutils-mipsel"].ruta_clave("as") == "bin/mipsel-none-elf-as.exe"

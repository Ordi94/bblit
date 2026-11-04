"""Reglas de negocio de la ejecucion multiplataforma de la cadena de compilacion."""

import shutil
from pathlib import Path
from typing import Any

import pytest
from psxdecomp.toolchain import instalacion, plataforma
from psxdecomp.toolchain.dominio import Componente, cargar_lock

from .ayudantes import bloque_componente, lock_de, zip_de

LOCK_BINUTILS = cargar_lock(
    lock_de(
        **{
            "binutils-mipsel": bloque_componente(
                zip_de({"bin/mipsel-none-elf-as.exe": b"x"}),
                archivos_clave={"as": "bin/mipsel-none-elf-as.exe", "otro": "bin/otro.EXE"},
                nativo_fuera_de_windows=True,
            ),
            "psyq-4.4": bloque_componente(
                zip_de({"pssn/bin/CC1PSX.EXE": b"x"}), archivos_clave={"cc1psx": "pssn/bin/CC1PSX.EXE"}
            ),
        }
    )
)


def simular_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(plataforma, "es_windows", lambda: False)


def test_en_linux_el_ensamblador_es_el_binutils_nativo_y_no_el_exe_del_toolchain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    monkeypatch.setattr(shutil, "which", lambda nombre: f"/usr/bin/{nombre}")
    ruta = instalacion.resolver_herramienta(LOCK_BINUTILS, tmp_path, "binutils-mipsel", "as", entorno={})
    assert ruta == Path("/usr/bin/mipsel-none-elf-as")


def test_el_prefijo_de_binutils_se_configura_por_el_entorno_inyectado(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    monkeypatch.setattr(shutil, "which", lambda nombre: f"/opt/{nombre}")
    entorno = {"PSXDECOMP_BINUTILS_PREFIX": "otro-"}
    ruta = instalacion.resolver_herramienta(LOCK_BINUTILS, tmp_path, "binutils-mipsel", "as", entorno=entorno)
    assert ruta == Path("/opt/otro-as")


def test_sin_binutils_nativo_el_error_dice_que_instalar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    monkeypatch.setattr(shutil, "which", lambda nombre: None)
    with pytest.raises(FileNotFoundError, match=r"mipsel-none-elf-as.*agregue al PATH"):
        instalacion.resolver_herramienta(LOCK_BINUTILS, tmp_path, "binutils-mipsel", "as", entorno={})


def test_sin_entorno_inyectado_se_consulta_el_del_proceso(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    monkeypatch.setattr(shutil, "which", lambda nombre: f"/opt/{nombre}")
    monkeypatch.setenv("PSXDECOMP_BINUTILS_PREFIX", "proceso-")
    ruta = instalacion.resolver_herramienta(LOCK_BINUTILS, tmp_path, "binutils-mipsel", "as")
    assert ruta == Path("/opt/proceso-as")


def lock_con_binutils_llamado(nombre: str, *, nativo: bool | None) -> dict[str, Componente]:
    """Lock con un unico componente de binutils bajo ``nombre``; ``None`` omite el campo."""
    cambios: dict[str, Any] = {} if nativo is None else {"nativo_fuera_de_windows": nativo}
    return cargar_lock(
        lock_de(
            **{
                nombre: bloque_componente(
                    zip_de({"bin/mipsel-none-elf-as.exe": b"x"}),
                    archivos_clave={"as": "bin/mipsel-none-elf-as.exe"},
                    **cambios,
                )
            }
        )
    )


def test_la_resolucion_nativa_no_depende_del_nombre_del_componente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    monkeypatch.setattr(shutil, "which", lambda nombre: f"/usr/bin/{nombre}")
    lock = lock_con_binutils_llamado("ensamblador-propio", nativo=True)
    ruta = instalacion.resolver_herramienta(lock, tmp_path, "ensamblador-propio", "as", entorno={})
    assert ruta == Path("/usr/bin/mipsel-none-elf-as")


@pytest.mark.parametrize("nativo", [None, False])
def test_sin_la_marca_un_componente_llamado_binutils_mipsel_no_usa_el_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, nativo: bool | None
) -> None:
    simular_linux(monkeypatch)
    monkeypatch.setattr(shutil, "which", lambda nombre: pytest.fail("no debe consultar el PATH"))
    lock = lock_con_binutils_llamado("binutils-mipsel", nativo=nativo)
    with pytest.raises(FileNotFoundError, match="'as' no esta instalado"):
        instalacion.resolver_herramienta(lock, tmp_path, "binutils-mipsel", "as", entorno={})


def test_en_linux_los_alias_que_no_son_binutils_siguen_saliendo_del_toolchain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    carpeta = tmp_path / "binutils-mipsel" / "bin"
    carpeta.mkdir(parents=True)
    (carpeta / "otro.EXE").write_bytes(b"x")
    ruta = instalacion.resolver_herramienta(LOCK_BINUTILS, tmp_path, "binutils-mipsel", "otro")
    assert ruta == carpeta / "otro.EXE"


def test_en_linux_los_exe_del_sdk_se_encuentran_aunque_cambie_la_capitalizacion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sistema_sensible: None
) -> None:
    simular_linux(monkeypatch)
    carpeta = tmp_path / "psyq-4.4" / "pssn" / "BIN"
    carpeta.mkdir(parents=True)
    (carpeta / "cc1psx.exe").write_bytes(b"x")
    assert not (tmp_path / "psyq-4.4" / "pssn" / "bin" / "CC1PSX.EXE").exists()
    ruta = instalacion.resolver_herramienta(LOCK_BINUTILS, tmp_path, "psyq-4.4", "cc1psx")
    assert ruta == carpeta / "cc1psx.exe"


def test_en_linux_un_exe_que_no_existe_con_ninguna_capitalizacion_da_error_claro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sistema_sensible: None
) -> None:
    simular_linux(monkeypatch)
    carpeta = tmp_path / "psyq-4.4" / "pssn" / "BIN"
    carpeta.mkdir(parents=True)
    (carpeta / "otro.exe").write_bytes(b"x")
    with pytest.raises(FileNotFoundError, match="'cc1psx' no esta instalado"):
        instalacion.resolver_herramienta(LOCK_BINUTILS, tmp_path, "psyq-4.4", "cc1psx")


def test_en_linux_un_exe_ausente_se_informa_como_no_instalado(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    with pytest.raises(FileNotFoundError, match="'cc1psx' no esta instalado"):
        instalacion.resolver_herramienta(LOCK_BINUTILS, tmp_path, "psyq-4.4", "cc1psx")


def test_en_windows_los_binutils_salen_del_toolchain_sin_consultar_el_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(plataforma, "es_windows", lambda: True)
    monkeypatch.setattr(shutil, "which", lambda nombre: pytest.fail("no debe consultar el PATH"))
    carpeta = tmp_path / "binutils-mipsel" / "bin"
    carpeta.mkdir(parents=True)
    (carpeta / "mipsel-none-elf-as.exe").write_bytes(b"x")
    ruta = instalacion.resolver_herramienta(LOCK_BINUTILS, tmp_path, "binutils-mipsel", "as")
    assert ruta == carpeta / "mipsel-none-elf-as.exe"

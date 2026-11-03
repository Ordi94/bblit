"""Reglas de negocio de la ejecucion multiplataforma de la cadena de compilacion."""

import subprocess
from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import infraestructura as infra
from tools.toolchain import instalacion, plataforma
from tools.toolchain.dominio import cargar_lock

from .ayudantes import bloque_componente, lock_de, zip_de

LOCK_BINUTILS = cargar_lock(
    lock_de(
        **{
            "binutils-mipsel": bloque_componente(
                zip_de({"bin/mipsel-none-elf-as.exe": b"x"}),
                archivos_clave={"as": "bin/mipsel-none-elf-as.exe", "otro": "bin/otro.EXE"},
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
    monkeypatch.setattr(plataforma.shutil, "which", lambda nombre: f"/usr/bin/{nombre}")
    monkeypatch.delenv("BBLIT_BINUTILS_PREFIX", raising=False)
    ruta = instalacion.resolver_herramienta(LOCK_BINUTILS, tmp_path, "binutils-mipsel", "as")
    assert ruta == Path("/usr/bin/mipsel-none-elf-as")


def test_el_prefijo_de_binutils_se_configura_por_entorno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    monkeypatch.setattr(plataforma.shutil, "which", lambda nombre: f"/opt/{nombre}")
    monkeypatch.setenv("BBLIT_BINUTILS_PREFIX", "otro-")
    ruta = instalacion.resolver_herramienta(LOCK_BINUTILS, tmp_path, "binutils-mipsel", "as")
    assert ruta == Path("/opt/otro-as")


def test_sin_binutils_nativo_el_error_dice_que_instalar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    monkeypatch.setattr(plataforma.shutil, "which", lambda nombre: None)
    monkeypatch.delenv("BBLIT_BINUTILS_PREFIX", raising=False)
    with pytest.raises(FileNotFoundError, match=r"mipsel-none-elf-as.*agregue al PATH"):
        instalacion.resolver_herramienta(LOCK_BINUTILS, tmp_path, "binutils-mipsel", "as")


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
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    carpeta = tmp_path / "psyq-4.4" / "pssn" / "bin"
    carpeta.mkdir(parents=True)
    (carpeta / "CC1PSX.EXE").write_bytes(b"x")
    ruta = instalacion.resolver_herramienta(LOCK_BINUTILS, tmp_path, "psyq-4.4", "cc1psx")
    assert ruta.name == "CC1PSX.EXE"


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
    monkeypatch.setattr(plataforma.shutil, "which", lambda nombre: pytest.fail("no debe consultar el PATH"))
    carpeta = tmp_path / "binutils-mipsel" / "bin"
    carpeta.mkdir(parents=True)
    (carpeta / "mipsel-none-elf-as.exe").write_bytes(b"x")
    ruta = instalacion.resolver_herramienta(LOCK_BINUTILS, tmp_path, "binutils-mipsel", "as")
    assert ruta == carpeta / "mipsel-none-elf-as.exe"


class EjecucionFalsa:
    """Captura la llamada a ``subprocess.run`` que haria ``ejecutar_proceso``."""

    def __init__(self) -> None:
        self.comando: list[str] = []
        self.entorno: dict[str, str] = {}

    def __call__(self, comando: list[str], **opciones: Any) -> subprocess.CompletedProcess[str]:
        self.comando = comando
        self.entorno = opciones["env"]
        return subprocess.CompletedProcess(comando, 0, stdout="ok", stderr="")


def test_en_linux_ejecutar_proceso_lanza_los_exe_con_wine_y_sin_ruido_de_depuracion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    falsa = EjecucionFalsa()
    monkeypatch.setattr(infra.subprocess, "run", falsa)
    monkeypatch.delenv("WINEDEBUG", raising=False)
    monkeypatch.delenv("BBLIT_WINE", raising=False)
    ruta = "/root/tool chain/pssn/bin/CPPPSX.EXE"
    assert infra.ejecutar_proceso([ruta, "-Iinclude", "src/a.c"], tmp_path, 5) == "ok"
    assert falsa.comando == ["wine", ruta, "-Iinclude", "src/a.c"]
    assert falsa.entorno["WINEDEBUG"] == "-all"
    assert falsa.entorno["PYTHONUTF8"] == "1"


def test_en_linux_un_fallo_de_wine_nombra_el_programa_y_no_a_wine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)

    def falla(comando: list[str], **opciones: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(comando, 3, stdout="", stderr="boom")

    monkeypatch.setattr(infra.subprocess, "run", falla)
    with pytest.raises(infra.ProcesoError, match=r"CC1PSX\.EXE: termino con codigo 3"):
        infra.ejecutar_proceso(["/t/CC1PSX.EXE"], tmp_path, 5)


def test_en_linux_los_binutils_nativos_se_lanzan_sin_wine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    falsa = EjecucionFalsa()
    monkeypatch.setattr(infra.subprocess, "run", falsa)
    infra.ejecutar_proceso(["/usr/bin/mipsel-none-elf-objdump", "-t", "a.o"], tmp_path, 5)
    assert falsa.comando[0] == "/usr/bin/mipsel-none-elf-objdump"

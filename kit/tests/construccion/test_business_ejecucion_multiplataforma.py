"""Reglas de negocio de la ejecucion multiplataforma de procesos de la cadena de compilacion."""

import subprocess
from pathlib import Path
from typing import Any

import pytest
from psxdecomp.construccion import infraestructura as infra
from psxdecomp.entorno import Variables
from psxdecomp.toolchain import plataforma


def simular_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(plataforma, "es_windows", lambda: False)


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
    monkeypatch.setattr(subprocess, "run", falsa)
    monkeypatch.delenv("WINEDEBUG", raising=False)
    monkeypatch.delenv("PSXDECOMP_WINE", raising=False)
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

    monkeypatch.setattr(subprocess, "run", falla)
    with pytest.raises(infra.ProcesoError, match=r"CC1PSX\.EXE: termino con codigo 3"):
        infra.ejecutar_proceso(["/t/CC1PSX.EXE"], tmp_path, 5)


def test_en_linux_los_binutils_nativos_se_lanzan_sin_wine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    falsa = EjecucionFalsa()
    monkeypatch.setattr(subprocess, "run", falsa)
    infra.ejecutar_proceso(["/usr/bin/mipsel-none-elf-objdump", "-t", "a.o"], tmp_path, 5)
    assert falsa.comando[0] == "/usr/bin/mipsel-none-elf-objdump"


def lanzar_inexistente(comando: list[str], **opciones: Any) -> subprocess.CompletedProcess[str]:
    raise FileNotFoundError(2, "No such file", "/ruta/privada/de/la/maquina")


def test_en_linux_sin_wine_el_error_dice_que_instalar_y_no_filtra_rutas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    monkeypatch.setattr(subprocess, "run", lanzar_inexistente)
    monkeypatch.setenv("PSXDECOMP_WINE", "/opt/secreto/wine")
    with pytest.raises(infra.ProcesoError) as error:
        infra.ejecutar_proceso(["/t/CC1PSX.EXE"], tmp_path, 5, variables=Variables(alias="JUEGO"))
    mensaje = str(error.value)
    assert "CC1PSX.EXE: Wine no esta instalado" in mensaje
    assert "wine32" in mensaje
    assert "PSXDECOMP_WINE (o JUEGO_WINE)" in mensaje
    assert "/opt/secreto" not in mensaje
    assert "/ruta/privada" not in mensaje


def test_en_windows_un_ejecutable_ausente_da_proceso_error_claro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(plataforma, "es_windows", lambda: True)
    monkeypatch.setattr(subprocess, "run", lanzar_inexistente)
    with pytest.raises(infra.ProcesoError) as error:
        infra.ejecutar_proceso(["C:/privado/tool/CC1PSX.EXE"], tmp_path, 5)
    mensaje = str(error.value)
    assert mensaje == "CC1PSX.EXE: el ejecutable no esta instalado o no esta en el PATH"


def test_en_linux_un_binutils_nativo_ausente_da_proceso_error_sin_mencionar_wine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    monkeypatch.setattr(subprocess, "run", lanzar_inexistente)
    with pytest.raises(
        infra.ProcesoError, match="mipsel-none-elf-as: el ejecutable no esta instalado"
    ) as error:
        infra.ejecutar_proceso(["/x/mipsel-none-elf-as"], tmp_path, 5)
    assert "Wine" not in str(error.value)


def test_el_alias_del_proyecto_localiza_wine_cuando_el_prefijo_propio_no_esta_definido(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    simular_linux(monkeypatch)
    falsa = EjecucionFalsa()
    monkeypatch.setattr(subprocess, "run", falsa)
    monkeypatch.delenv("PSXDECOMP_WINE", raising=False)
    monkeypatch.setenv("JUEGO_WINE", "wine64")
    infra.ejecutar_proceso(["/t/CPPPSX.EXE"], tmp_path, 5, variables=Variables(alias="JUEGO"))
    assert falsa.comando[0] == "wine64"

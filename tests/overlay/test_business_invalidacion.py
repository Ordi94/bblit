"""Reglas de negocio de la invalidacion de la salida del overlay.

Un build que falla no puede dejar un binario que ``verify`` apruebe: la salida de la corrida
anterior se elimina antes de ensamblar y ``verify`` informa de la variante sin binario.
"""

import json
from pathlib import Path

import pytest
from tools.overlay import cli
from tools.reconstruccion.infraestructura import ProcesoError

from tests.overlay.ayudantes import (
    Registro,
    construir_overlay,
    contenedor,
    escribir_sistema_de_archivos,
    variantes_conocidas,
)
from tests.toolchain.ayudantes import bloque_componente, lock_de

A = construir_overlay(1)
B = construir_overlay(2)
CONOCIDAS = variantes_conocidas({"a": A, "b": B}, {"a": 1, "b": 1})
DISCO = {"LEVEL1/L01A.BZZ": contenedor(A), "DEMO/DEMO1.BZZ": contenedor(B)}
Repo = tuple[Path, dict[str, str]]


class EjecutorQueFallaEn:
    """Delega en un ``Registro`` y falla al ensamblar el fuente de la variante indicada."""

    def __init__(self, variante_rota: str) -> None:
        self.delegado = Registro({"a": A, "b": B})
        self.variante_rota = variante_rota

    def __call__(self, comando: object, directorio: Path, timeout_s: int) -> str:
        partes = [str(parte) for parte in comando]  # type: ignore[attr-defined]
        if Path(partes[0]).name == "as.exe" and partes[-1] == f"asm/overlay/{self.variante_rota}/codigo.s":
            raise ProcesoError("opcode inexistente")
        return self.delegado(comando, directorio, timeout_s)


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    raiz = tmp_path / "repo"
    (raiz / "config").mkdir(parents=True)
    for identificador in ("a", "b"):
        (raiz / "config" / f"splat_overlay_{identificador}.yaml").write_text(
            "segments: []\n", encoding="utf-8"
        )
    bloque = bloque_componente(
        b"x", archivos_clave={"as": "bin/as.exe", "ld": "bin/ld.exe", "objcopy": "bin/objcopy.exe"}
    )
    (raiz / "config" / "toolchain.lock.json").write_text(
        json.dumps(lock_de(**{"binutils-mipsel": bloque})), encoding="utf-8"
    )
    herramientas = tmp_path / "tc" / "binutils-mipsel" / "bin"
    herramientas.mkdir(parents=True)
    for nombre in ("as.exe", "ld.exe", "objcopy.exe"):
        (herramientas / nombre).write_bytes(b"")
    disco = escribir_sistema_de_archivos(tmp_path / "disco (copia)", DISCO)
    entorno = {"BBLIT_DISC": str(disco), "BBLIT_TOOLCHAIN": str(tmp_path / "tc")}
    registro = Registro({"a": A, "b": B})
    for orden in ("extraer", "simbolos", "split", "build"):
        assert cli.main([orden], entorno, raiz, registro, CONOCIDAS) == 0
    return raiz, entorno


def correr(repo: Repo, *argv: str, ejecutor: object | None = None) -> int:
    raiz, entorno = repo
    return cli.main(list(argv), entorno, raiz, ejecutor or Registro({"a": A, "b": B}), CONOCIDAS)  # type: ignore[arg-type]


def test_build_con_fuente_roto_deja_verify_en_fail_en_vez_de_aprobar_el_binario_anterior(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    assert correr(repo, "verify") == 0
    capsys.readouterr()
    assert correr(repo, "build", ejecutor=EjecutorQueFallaEn("a")) == 1
    assert "error: opcode inexistente" in capsys.readouterr().err
    assert correr(repo, "verify") == 1
    assert capsys.readouterr().out.splitlines() == [
        "FAIL a el binario reconstruido no existe",
        "FAIL b el binario reconstruido no existe",
    ]


def test_un_fallo_en_la_segunda_variante_deja_la_primera_construida_y_la_segunda_sin_binario(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, _ = repo
    assert correr(repo, "build", ejecutor=EjecutorQueFallaEn("b")) == 1
    assert (raiz / "build" / "overlay" / "a.bin").is_file()
    assert not (raiz / "build" / "overlay" / "b.bin").exists()
    assert not (raiz / "build" / "overlay" / "b.elf").exists()
    capsys.readouterr()
    assert correr(repo, "verify") == 1
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0].startswith("OK a ")
    assert lineas[1] == "FAIL b el binario reconstruido no existe"


def test_un_fallo_en_la_primera_variante_invalida_tambien_las_posteriores(repo: Repo) -> None:
    raiz, _ = repo
    assert correr(repo, "build", ejecutor=EjecutorQueFallaEn("a")) == 1
    assert not (raiz / "build" / "overlay" / "b.bin").exists()


def test_build_sin_toolchain_tambien_invalida_la_salida_anterior(repo: Repo) -> None:
    raiz, entorno = repo
    (Path(entorno["BBLIT_TOOLCHAIN"]) / "binutils-mipsel" / "bin" / "ld.exe").unlink()
    assert correr(repo, "build") == 1
    assert not (raiz / "build" / "overlay" / "a.bin").exists()
    assert correr(repo, "verify") == 1


def test_build_de_una_variante_no_toca_la_salida_de_las_demas(repo: Repo) -> None:
    raiz, _ = repo
    assert correr(repo, "build", "--variante", "a", ejecutor=EjecutorQueFallaEn("a")) == 1
    assert not (raiz / "build" / "overlay" / "a.bin").exists()
    assert (raiz / "build" / "overlay" / "b.bin").is_file()


def test_verify_informa_todas_las_variantes_aunque_falte_el_binario_de_la_primera(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, _ = repo
    (raiz / "build" / "overlay" / "a.bin").unlink()
    capsys.readouterr()
    assert correr(repo, "verify") == 1
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == "FAIL a el binario reconstruido no existe"
    assert lineas[1].startswith("OK b ")


def test_reconstruir_tras_corregir_el_fuente_restablece_el_ok(repo: Repo) -> None:
    assert correr(repo, "build", ejecutor=EjecutorQueFallaEn("a")) == 1
    assert correr(repo, "build") == 0
    assert correr(repo, "verify") == 0

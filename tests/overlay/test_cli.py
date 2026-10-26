import json
import runpy
import struct
import sys
from pathlib import Path

import pytest
from tools.overlay import cli, dominio

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
CONOCIDAS = variantes_conocidas({"a": A, "b": B}, {"a": 2, "b": 1})
DISCO = {
    "LEVEL1/L01A.BZZ": contenedor(A),
    "LEVEL1/L01B.BZZ": contenedor(A),
    "DEMO/DEMO1.BZZ": contenedor(B),
    "LOADING/CARGA.BZZ": contenedor(None),
}


@pytest.fixture
def entorno(tmp_path: Path) -> tuple[Path, dict[str, str]]:
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
    return raiz, {"BBLIT_DISC": str(disco), "BBLIT_TOOLCHAIN": str(tmp_path / "tc")}


def ejecutar(entorno: tuple[Path, dict[str, str]], *argv: str, registro: Registro | None = None) -> int:
    raiz, variables = entorno
    return cli.main(list(argv), variables, raiz, registro or Registro({"a": A, "b": B}), CONOCIDAS)


def test_extraer_escribe_binarios_y_configuracion(
    entorno: tuple[Path, dict[str, str]], capsys: pytest.CaptureFixture[str]
) -> None:
    assert ejecutar(entorno, "extraer") == 0
    salida = capsys.readouterr().out.splitlines()
    assert salida == [
        f"a sha256={dominio.huella_sha256(A)} bytes={len(A)} contenedores=2",
        f"b sha256={dominio.huella_sha256(B)} bytes={len(B)} contenedores=1",
        "extraccion completada: 2 variantes, 3 contenedores",
    ]
    raiz = entorno[0]
    assert (raiz / "expected" / "overlay" / "b.bin").read_bytes() == B
    primero = (raiz / "config" / "overlay.json").read_bytes()
    assert ejecutar(entorno, "extraer") == 0
    assert (raiz / "config" / "overlay.json").read_bytes() == primero


def test_extraer_sin_disco_informa_el_error(
    entorno: tuple[Path, dict[str, str]], capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, _ = entorno
    assert cli.main(["extraer"], {}, raiz, Registro({}), CONOCIDAS) == 1
    assert "error: falta la ubicacion del disco" in capsys.readouterr().err


def test_extraer_acepta_el_disco_como_argumento(
    entorno: tuple[Path, dict[str, str]], capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = entorno
    argumento = variables["BBLIT_DISC"]
    assert cli.main(["--disc", argumento, "extraer"], {}, raiz, Registro({}), CONOCIDAS) == 0
    assert "extraccion completada" in capsys.readouterr().out


def test_las_ordenes_posteriores_exigen_la_extraccion(
    entorno: tuple[Path, dict[str, str]], capsys: pytest.CaptureFixture[str]
) -> None:
    for orden in ("simbolos", "split", "build", "verify"):
        assert ejecutar(entorno, orden) == 1
        assert "ejecute primero 'extraer'" in capsys.readouterr().err


def test_cadena_completa_con_ejecutor_falso(
    entorno: tuple[Path, dict[str, str]], capsys: pytest.CaptureFixture[str]
) -> None:
    ejecutar(entorno, "extraer")
    capsys.readouterr()
    assert ejecutar(entorno, "simbolos") == 0
    assert (
        capsys.readouterr().out
        == "simbolos: 8 funciones y la ranura del cargador en config/symbols_overlay.txt\n"
    )
    assert ejecutar(entorno, "split") == 0
    assert capsys.readouterr().out.splitlines() == [
        "split a: funciones=9 glabel=9 palabras_en_texto=0",
        "split b: funciones=9 glabel=9 palabras_en_texto=0",
    ]
    assert ejecutar(entorno, "build") == 0
    assert capsys.readouterr().out.splitlines() == [
        "build a: build/overlay/a.bin",
        "build b: build/overlay/b.bin",
    ]
    assert ejecutar(entorno, "verify") == 0
    lineas = capsys.readouterr().out.splitlines()
    assert [linea.split()[:2] for linea in lineas] == [["OK", "a"], ["OK", "b"]]


def test_verify_devuelve_uno_si_alguna_variante_difiere(
    entorno: tuple[Path, dict[str, str]], capsys: pytest.CaptureFixture[str]
) -> None:
    alterado = bytearray(B)
    alterado[8] ^= 1
    registro = Registro({"a": A, "b": bytes(alterado)})
    ejecutar(entorno, "extraer")
    ejecutar(entorno, "simbolos")
    ejecutar(entorno, "split", registro=registro)
    ejecutar(entorno, "build", registro=registro)
    capsys.readouterr()
    assert ejecutar(entorno, "verify") == 1
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0].startswith("OK a ")
    assert lineas[1].startswith("FAIL b primera diferencia en el desplazamiento 0x8")


def test_variante_unica_y_variante_desconocida(
    entorno: tuple[Path, dict[str, str]], capsys: pytest.CaptureFixture[str]
) -> None:
    ejecutar(entorno, "extraer")
    ejecutar(entorno, "simbolos")
    capsys.readouterr()
    assert ejecutar(entorno, "split", "--variante", "b") == 0
    assert capsys.readouterr().out.splitlines() == ["split b: funciones=9 glabel=9 palabras_en_texto=0"]
    assert ejecutar(entorno, "split", "--variante", "z") == 1
    assert "variante 'z' no registrada: opciones a, b, todas" in capsys.readouterr().err


def test_build_sin_herramientas_instaladas_informa_el_error(
    entorno: tuple[Path, dict[str, str]], capsys: pytest.CaptureFixture[str]
) -> None:
    ejecutar(entorno, "extraer")
    ejecutar(entorno, "simbolos")
    ejecutar(entorno, "split")
    (entorno[0].parent / "tc" / "binutils-mipsel" / "bin" / "ld.exe").unlink()
    capsys.readouterr()
    assert ejecutar(entorno, "build") == 1
    assert "error:" in capsys.readouterr().err


def volcado(tmp_path: Path, overlay: bytes, tamano: int = 0x40000) -> Path:
    ram = bytearray(tamano)
    ram[0x10200 : 0x10200 + len(overlay)] = overlay
    if tamano > 0x10204:
        struct.pack_into("<I", ram, 0x10200, 0x8006B2F8)
    ruta = tmp_path / "ram.bin"
    ruta.write_bytes(bytes(ram))
    return ruta


def test_ram_indica_la_variante_cargada(
    entorno: tuple[Path, dict[str, str]], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ejecutar(entorno, "extraer")
    capsys.readouterr()
    assert ejecutar(entorno, "ram", str(volcado(tmp_path, B))) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[0] == "ranura del cargador: 0x8006B2F8"
    assert lineas[1].startswith("DIFIERE a ")
    assert lineas[2] == f"COINCIDE b bytes={len(B)} distintos=4 rangos: 0x0-0x4"


def test_ram_devuelve_uno_si_ninguna_variante_coincide(
    entorno: tuple[Path, dict[str, str]], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ejecutar(entorno, "extraer")
    capsys.readouterr()
    assert ejecutar(entorno, "ram", str(volcado(tmp_path, construir_overlay(9)))) == 1
    assert "COINCIDE" not in capsys.readouterr().out


def test_ram_rechaza_volcados_invalidos(
    entorno: tuple[Path, dict[str, str]], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ejecutar(entorno, "extraer")
    capsys.readouterr()
    assert ejecutar(entorno, "ram", str(volcado(tmp_path, B, tamano=0x100))) == 1
    assert "demasiado corto" in capsys.readouterr().err
    grande = tmp_path / "grande.bin"
    grande.write_bytes(bytes(dominio.MAX_BYTES_VOLCADO + 1))
    assert ejecutar(entorno, "ram", str(grande)) == 1
    assert "excede el tamano permitido" in capsys.readouterr().err
    assert ejecutar(entorno, "ram", str(tmp_path / "no_existe.bin")) == 1
    assert "error:" in capsys.readouterr().err


def test_modulo_principal_ejecuta_la_cli(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["tools.overlay", "--help"])
    with pytest.raises(SystemExit) as salida:
        runpy.run_module("tools.overlay", run_name="__main__")
    assert salida.value.code == 0
    assert "python -m tools.overlay" in capsys.readouterr().out


def test_el_analizador_define_todas_las_ordenes() -> None:
    parser = cli.construir_parser()
    for orden in ("extraer", "simbolos", "split", "build", "verify"):
        assert parser.parse_args([orden]).orden == orden
    assert parser.parse_args(["verify", "--variante", "a"]).variante == "a"
    assert parser.parse_args(["ram", "volcado.bin"]).volcado == Path("volcado.bin")

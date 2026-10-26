"""Corrida real contra el disco del usuario; se omite si no hay disco o toolchain configurados.

Todo se escribe en una carpeta temporal con copia de la configuracion del repositorio, de modo
que no interfiere con ``asm/``, ``build/`` ni ``expected/`` del repositorio.
"""

import os
import shutil
from pathlib import Path

import pytest
from tools.overlay import cli, dominio, extraccion
from tools.reconstruccion.infraestructura import ejecutar_proceso

RAIZ = Path(__file__).resolve().parents[2]
DISCO = os.environ.get("BBLIT_DISC")
TOOLCHAIN = Path(os.environ.get("BBLIT_TOOLCHAIN", str(RAIZ / "toolchain")))

sin_disco = pytest.mark.skipif(not DISCO, reason="BBLIT_DISC no esta definida")
sin_herramientas = pytest.mark.skipif(
    not DISCO or not (TOOLCHAIN / "binutils-mipsel").is_dir(),
    reason="falta BBLIT_DISC o el toolchain instalado",
)


@sin_disco
def test_extraccion_real_coincide_con_las_variantes_documentadas() -> None:
    variantes, binarios = extraccion.extraer_variantes(Path(str(DISCO)))
    assert [(v.identificador, v.tamano, len(v.archivos)) for v in variantes] == [
        ("a", 17076, 48),
        ("b", 17072, 24),
        ("c", 17080, 4),
    ]
    assert [v.sha256[:16] for v in variantes] == ["3e45e436f793ec64", "9b5b5e2c1a05b7f6", "67cbfff30aa3d00b"]
    assert sum(len(v.archivos) for v in variantes) == 76
    assert not any(nombre.startswith("LOADING/") for v in variantes for nombre in v.archivos)
    assert all(
        dominio.huella_sha256(datos) == v.sha256
        for v, datos in zip(variantes, binarios.values(), strict=True)
    )


@sin_disco
def test_las_funciones_reales_son_las_mismas_en_las_tres_variantes() -> None:
    _, binarios = extraccion.extraer_variantes(Path(str(DISCO)))
    conjuntos = {
        identificador: dominio.descubrir_funciones(datos) for identificador, datos in binarios.items()
    }
    assert len(set(conjuntos.values())) == 1
    assert len(conjuntos["a"]) == 35
    assert {i: dominio.fin_de_codigo(d) for i, d in binarios.items()} == {
        "a": 0x2954,
        "b": 0x2950,
        "c": 0x2954,
    }
    assert all(binarios[i][:4] == bytes(4) for i in binarios)


@sin_herramientas
def test_cadena_real_extraer_split_build_verify(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    raiz = tmp_path / "repo"
    (raiz / "config").mkdir(parents=True)
    for archivo in (
        "symbols_overlay.txt",
        "toolchain.lock.json",
        "splat_overlay_a.yaml",
        "splat_overlay_b.yaml",
    ):
        shutil.copy(RAIZ / "config" / archivo, raiz / "config" / archivo)
    shutil.copy(RAIZ / "config" / "splat_overlay_c.yaml", raiz / "config" / "splat_overlay_c.yaml")
    entorno = {"BBLIT_DISC": str(DISCO), "BBLIT_TOOLCHAIN": str(TOOLCHAIN)}
    capsys.readouterr()
    for orden in (["extraer"], ["simbolos"], ["split"], ["build"], ["verify"]):
        assert cli.main(orden, entorno, raiz, ejecutar_proceso) == 0, orden
    lineas = capsys.readouterr().out.splitlines()
    verificaciones = [linea for linea in lineas if linea.startswith(("OK", "FAIL"))]
    assert [linea.split()[:2] for linea in verificaciones] == [["OK", "a"], ["OK", "b"], ["OK", "c"]]
    assert (raiz / "config" / "symbols_overlay.txt").read_text(encoding="utf-8") == (
        RAIZ / "config" / "symbols_overlay.txt"
    ).read_text(encoding="utf-8")

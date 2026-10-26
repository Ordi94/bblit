"""Sesion real contra PCSX-Redux; se omite si falta BBLIT_DISC, el emulador o la imagen de prueba."""

import hashlib
import json
import os
from pathlib import Path

import pytest
from tools.emulador import cli, proceso
from tools.emulador.dominio import RAM_TAMANO
from tools.emulador.pantalla import es_pantalla_negra

RAIZ = Path(__file__).resolve().parents[2]
EMULADOR = Path(os.environ.get("BBLIT_REDUX", RAIZ / cli.EMULADOR_POR_DEFECTO))
BIOS = Path(os.environ.get("BBLIT_BIOS", RAIZ / cli.BIOS_POR_DEFECTO))
IMAGEN = RAIZ / cli.IMAGEN_POR_DEFECTO
PUERTO_PRUEBA = 8091

pytestmark = pytest.mark.skipif(
    not (os.environ.get("BBLIT_DISC") and EMULADOR.is_file() and BIOS.is_file() and IMAGEN.is_file()),
    reason="requiere BBLIT_DISC, el emulador, la BIOS y build/bblit_prueba.cue",
)


def test_sesion_real_deja_ram_y_pantalla_y_no_deja_procesos(tmp_path, capsys):
    if proceso.puerto_ocupado(PUERTO_PRUEBA) or proceso.listar_procesos():
        pytest.skip("hay un emulador en ejecucion; no se interfiere con el")
    try:
        codigo = cli.main(
            [
                "sesion",
                "--imagen",
                str(IMAGEN),
                "--bios",
                str(BIOS),
                "--emulador",
                str(EMULADOR),
                "--trabajo",
                str(tmp_path / "trabajo"),
                "--salida",
                str(tmp_path / "salida"),
                "--puerto",
                str(PUERTO_PRUEBA),
                "--espera-hito",
                "pantalla",
                "--tope",
                "60",
            ]
        )
    finally:
        proceso.terminar_procesos(None)
    assert codigo == 0
    salida = tmp_path / "salida"
    ram = (salida / "ram.bin").read_bytes()
    resumen = json.loads((salida / "sesion.json").read_text(encoding="utf-8"))
    assert len(ram) == RAM_TAMANO
    assert resumen["sha256Ram"] == hashlib.sha256(ram).hexdigest()
    assert not es_pantalla_negra((salida / "pantalla.png").read_bytes())
    assert resumen["segundosHastaRunning"] < 10
    assert proceso.listar_procesos() == []
    assert not proceso.puerto_ocupado(PUERTO_PRUEBA)

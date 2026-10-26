"""Gestion de procesos con ejecutores dobles; las funciones reales se ejercitan con procesos inocuos."""

import socket
import sys
import time

import pytest
from tools.emulador import proceso
from tools.emulador.dominio import EmuladorError

SALIDA_CON_PROCESOS = (
    '"pcsx-redux.exe","1234","Console","1","50,000 K"\n'
    '"pcsx-redux.main.exe","5678","Console","1","90,000 K"\n'
)
SALIDA_SIN_PROCESOS = "INFO: No tasks are running which match the specified criteria.\n"


def test_listar_procesos_extrae_los_nombres_de_imagen():
    ordenes = []

    def ejecutor(orden):
        ordenes.append(list(orden))
        return SALIDA_CON_PROCESOS

    assert proceso.listar_procesos(ejecutor) == ["pcsx-redux.exe", "pcsx-redux.main.exe"]
    assert ordenes[0][:3] == ["tasklist", "/FI", "IMAGENAME eq pcsx-redux*"]


def test_listar_procesos_sin_coincidencias_devuelve_lista_vacia():
    assert proceso.listar_procesos(lambda orden: SALIDA_SIN_PROCESOS) == []


def test_terminar_procesos_mata_el_arbol_y_despues_por_nombre():
    ordenes = []
    proceso.terminar_procesos(4321, lambda orden: ordenes.append(list(orden)) or "")
    assert ordenes == [
        ["taskkill", "/F", "/T", "/PID", "4321"],
        ["taskkill", "/F", "/T", "/IM", "pcsx-redux*"],
    ]


def test_terminar_procesos_sin_pid_solo_termina_por_nombre():
    ordenes = []
    proceso.terminar_procesos(None, lambda orden: ordenes.append(list(orden)) or "")
    assert ordenes == [["taskkill", "/F", "/T", "/IM", "pcsx-redux*"]]


def test_construir_argumentos_resuelve_rutas_y_activa_el_servidor_web(tmp_path):
    exe, cue, bios = tmp_path / "r.exe", tmp_path / "i.cue", tmp_path / "b.bin"
    argumentos = proceso.construir_argumentos(exe, cue, bios, 8123)
    assert argumentos == [
        str(exe.resolve()),
        "-portable",
        "-loadiso",
        str(cue.resolve()),
        "-bios",
        str(bios.resolve()),
        "-run",
        "-webserver",
        "-webserver-port",
        "8123",
    ]


def test_lanzar_emulador_crea_la_carpeta_y_delega_en_el_lanzador(tmp_path):
    for nombre in ("r.exe", "i.cue", "b.bin"):
        (tmp_path / nombre).write_bytes(b"x")
    llamadas = []

    def lanzador(argumentos, carpeta):
        llamadas.append((list(argumentos), carpeta))
        return 99

    trabajo = tmp_path / "trabajo" / "emulador"
    pid = proceso.lanzar_emulador(
        tmp_path / "r.exe", tmp_path / "i.cue", tmp_path / "b.bin", trabajo, 8080, lanzador=lanzador
    )
    assert pid == 99
    assert trabajo.is_dir()
    assert llamadas[0][1] == trabajo.resolve()
    assert llamadas[0][0][0] == str((tmp_path / "r.exe").resolve())


@pytest.mark.parametrize("faltante", ["r.exe", "i.cue", "b.bin"])
def test_lanzar_emulador_rechaza_archivos_inexistentes_sin_crear_nada(tmp_path, faltante):
    for nombre in ("r.exe", "i.cue", "b.bin"):
        if nombre != faltante:
            (tmp_path / nombre).write_bytes(b"x")
    trabajo = tmp_path / "trabajo"
    with pytest.raises(EmuladorError, match="no existe"):
        proceso.lanzar_emulador(
            tmp_path / "r.exe", tmp_path / "i.cue", tmp_path / "b.bin", trabajo, 8080, lanzador=lambda a, c: 1
        )
    assert not trabajo.exists()


def test_puerto_ocupado_detecta_un_oyente_real():
    with socket.socket() as servidor:
        servidor.bind(("127.0.0.1", 0))
        servidor.listen()
        puerto = servidor.getsockname()[1]
        assert proceso.puerto_ocupado(puerto)
    assert not proceso.puerto_ocupado(puerto)


def test_ejecutar_orden_devuelve_la_salida_estandar():
    assert proceso.ejecutar_orden([sys.executable, "-c", "print('hola')"]).strip() == "hola"


def test_ejecutar_orden_ignora_el_codigo_de_salida():
    assert (
        proceso.ejecutar_orden([sys.executable, "-c", "import sys; print('x'); sys.exit(3)"]).strip() == "x"
    )


def test_lanzar_proceso_devuelve_el_pid_y_usa_la_carpeta_de_trabajo(tmp_path):
    pid = proceso.lanzar_proceso(
        [sys.executable, "-c", "from pathlib import Path; Path('marca.txt').write_text('ok')"], tmp_path
    )
    assert pid > 0
    for _ in range(100):
        if (tmp_path / "marca.txt").exists():
            break
        time.sleep(0.1)
    assert (tmp_path / "marca.txt").read_text() == "ok"

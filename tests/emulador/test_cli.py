"""Subcomandos del CLI con dobles de cliente, procesos y sesion."""

import json
import runpy
from pathlib import Path
from typing import Any

import pytest
from tools.emulador import cli, proceso, sesion
from tools.emulador.dominio import RAM_TAMANO, EmuladorError
from tools.proyecto import RAIZ_REPOSITORIO

from tests.emulador import sintetica
from tests.emulador.dobles import ClienteFalso, ram_con


class ClienteConPuertos(ClienteFalso):
    """Cliente falso que ademas registra los puertos con que se le construyo."""

    puertos: list[int]


def _salida_json(capsys: pytest.CaptureFixture[str]) -> Any:
    return json.loads(capsys.readouterr().out)


@pytest.fixture
def cliente_falso(monkeypatch: pytest.MonkeyPatch) -> ClienteConPuertos:
    cliente = ClienteConPuertos(pantallas=[sintetica.png_negro()], rams=[ram_con(0, b"x")])
    puertos: list[int] = []

    def fabrica(puerto: int) -> ClienteConPuertos:
        puertos.append(puerto)
        return cliente

    monkeypatch.setattr(cli, "ClienteRedux", fabrica)
    cliente.puertos = puertos
    return cliente


def test_comparar_con_archivo_imprime_json_camel_case(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ram = tmp_path / "ram.bin"
    ram.write_bytes(ram_con(0x14A00, bytes(range(8))))
    exe = tmp_path / "exe.bin"
    exe.write_bytes(b"\x00" * 0x800 + bytes(range(8)))
    codigo = cli.main(
        [
            "comparar",
            "--volcado",
            str(ram),
            "--direccion",
            "0x80014A00",
            "--archivo",
            str(exe),
            "--offset-archivo",
            "0x800",
        ]
    )
    assert codigo == 0
    salida = _salida_json(capsys)
    assert salida["bytesComparados"] == 8
    assert salida["bytesIguales"] == 8
    assert salida["primerOffsetDistinto"] is None
    assert salida["porcentajeIgual"] == 100.0


def test_comparar_dos_volcados(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a, b = tmp_path / "a.bin", tmp_path / "b.bin"
    a.write_bytes(ram_con(0x100, b"abc"))
    b.write_bytes(ram_con(0x100, b"abX"))
    codigo = cli.main(
        [
            "comparar",
            "--volcado",
            str(a),
            "--volcado-b",
            str(b),
            "--direccion",
            "0x80000100",
            "--longitud",
            "3",
        ]
    )
    assert codigo == 0
    salida = _salida_json(capsys)
    assert (salida["bytesIguales"], salida["bytesDistintos"], salida["primerOffsetDistinto"]) == (2, 1, 2)


def test_comparar_con_direccion_invalida_falla_con_exit_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ram = tmp_path / "ram.bin"
    ram.write_bytes(bytes(RAM_TAMANO))
    codigo = cli.main(["comparar", "--volcado", str(ram), "--direccion", "0x1000", "--volcado-b", str(ram)])
    assert codigo == 1
    assert "direccion 0x00001000" in capsys.readouterr().out


def test_comparar_con_archivo_inexistente_no_filtra_la_ruta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ram = tmp_path / "ram.bin"
    ram.write_bytes(bytes(RAM_TAMANO))
    codigo = cli.main(
        [
            "comparar",
            "--volcado",
            str(ram),
            "--direccion",
            "0x80000000",
            "--archivo",
            str(tmp_path / "no.bin"),
        ]
    )
    assert codigo == 1
    salida = capsys.readouterr().out
    assert "FileNotFoundError" in salida
    assert str(tmp_path) not in salida


def test_comparar_rechaza_un_entero_mal_escrito() -> None:
    with pytest.raises(SystemExit):
        cli.main(["comparar", "--volcado", "a", "--direccion", "xyz", "--volcado-b", "b"])


def test_comparar_exige_archivo_o_segundo_volcado() -> None:
    with pytest.raises(SystemExit):
        cli.main(["comparar", "--volcado", "a", "--direccion", "0x80000000"])


def test_volcar_guarda_la_ram_en_el_puerto_indicado(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], cliente_falso: ClienteConPuertos
) -> None:
    destino = tmp_path / "sub" / "ram.bin"
    assert cli.main(["volcar", "--salida", str(destino), "--puerto", "8123"]) == 0
    assert len(destino.read_bytes()) == RAM_TAMANO
    assert cliente_falso.puertos == [8123]
    assert _salida_json(capsys) == {"salida": "ram.bin", "bytes": RAM_TAMANO}


def test_capturar_guarda_la_pantalla(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], cliente_falso: ClienteConPuertos
) -> None:
    destino = tmp_path / "p.png"
    assert cli.main(["capturar", "--salida", str(destino)]) == 0
    assert destino.read_bytes() == sintetica.png_negro()
    assert cliente_falso.puertos == [8080]
    assert _salida_json(capsys)["bytes"] == len(sintetica.png_negro())


def test_volcar_rechaza_salida_dentro_del_disco(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    cliente_falso: ClienteConPuertos,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "disc").mkdir()
    (tmp_path / "disc" / "juego.bin").write_bytes(b"x")
    monkeypatch.setenv("BBLIT_DISC", str(tmp_path / "disc" / "juego.bin"))
    assert cli.main(["volcar", "--salida", str(tmp_path / "disc" / "ram.bin")]) == 1
    assert "disco original" in capsys.readouterr().out
    assert cliente_falso.puertos == []


def test_capturar_rechaza_salida_dentro_del_disco(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    cliente_falso: ClienteConPuertos,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "disc").mkdir()
    (tmp_path / "disc" / "juego.bin").write_bytes(b"x")
    monkeypatch.setenv("BBLIT_DISC", str(tmp_path / "disc" / "juego.bin"))
    assert cli.main(["capturar", "--salida", str(tmp_path / "disc" / "p.png")]) == 1
    assert "disco original" in capsys.readouterr().out
    assert cliente_falso.puertos == []
    assert not (tmp_path / "disc" / "p.png").exists()


@pytest.mark.parametrize("subcomando", ["capturar", "volcar"])
def test_salida_fuera_del_disco_no_se_rechaza(
    tmp_path: Path, cliente_falso: ClienteConPuertos, monkeypatch: pytest.MonkeyPatch, subcomando: str
) -> None:
    (tmp_path / "disc").mkdir()
    (tmp_path / "disc" / "juego.bin").write_bytes(b"x")
    monkeypatch.setenv("BBLIT_DISC", str(tmp_path / "disc" / "juego.bin"))
    destino = tmp_path / "analisis" / "salida.bin"
    assert cli.main([subcomando, "--salida", str(destino)]) == 0
    assert destino.is_file()


def test_pausar_y_reanudar(capsys: pytest.CaptureFixture[str], cliente_falso: ClienteConPuertos) -> None:
    assert cli.main(["pausar"]) == 0
    assert _salida_json(capsys) == {"estado": "pausado"}
    assert cliente_falso.pausado
    assert cli.main(["reanudar"]) == 0
    assert _salida_json(capsys) == {"estado": "en marcha"}
    assert not cliente_falso.pausado


def test_un_emulador_que_no_responde_da_exit_1(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    class Mudo:
        def pausar(self) -> None:
            raise EmuladorError("el emulador no responde a POST execution-flow")

    monkeypatch.setattr(cli, "ClienteRedux", lambda puerto: Mudo())
    assert cli.main(["pausar"]) == 1
    assert "no responde" in capsys.readouterr().out


def test_apagar_termina_por_nombre_aunque_no_haya_cliente(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    terminados: list[int | None] = []
    monkeypatch.setattr(proceso, "terminar_procesos", terminados.append)
    monkeypatch.setattr(proceso, "listar_procesos", lambda: [])
    monkeypatch.setattr(proceso, "puerto_ocupado", lambda puerto: False)
    assert cli.main(["apagar"]) == 0
    assert terminados == [None]
    assert _salida_json(capsys) == {"procesosVivos": 0, "puerto": 8080}


@pytest.mark.parametrize(("vivos", "ocupado"), [(["pcsx-redux.main.exe"], False), ([], True)])
def test_apagar_falla_si_queda_algo(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, vivos: list[str], ocupado: bool
) -> None:
    monkeypatch.setattr(proceso, "terminar_procesos", lambda pid: None)
    monkeypatch.setattr(proceso, "listar_procesos", lambda: vivos)
    monkeypatch.setattr(proceso, "puerto_ocupado", lambda puerto: ocupado)
    assert cli.main(["apagar"]) == 1
    assert "siguen" in capsys.readouterr().out


def test_arrancar_lanza_espera_running_y_deja_el_emulador_vivo(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, cliente_falso: ClienteConPuertos
) -> None:
    llamadas: dict[str, Any] = {}
    monkeypatch.setattr(proceso, "puerto_ocupado", lambda puerto: False)
    monkeypatch.setattr(proceso, "lanzar_emulador", lambda *a: llamadas.setdefault("lanzar", a) and 555)
    monkeypatch.setattr(sesion, "esperar_running", lambda *a: 0.75)
    monkeypatch.setattr(proceso, "terminar_procesos", lambda pid: llamadas.setdefault("terminar", pid))
    assert cli.main(["arrancar", "--puerto", "8200"]) == 0
    assert _salida_json(capsys) == {"pid": 555, "puerto": 8200, "segundosHastaRunning": 0.75}
    assert "terminar" not in llamadas
    assert llamadas["lanzar"][4] == 8200


def test_arrancar_con_puerto_ocupado_falla_sin_lanzar(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    lanzado = []
    monkeypatch.setattr(proceso, "puerto_ocupado", lambda puerto: True)
    monkeypatch.setattr(proceso, "lanzar_emulador", lambda *a: lanzado.append(a))
    assert cli.main(["arrancar"]) == 1
    assert "ya esta ocupado" in capsys.readouterr().out
    assert lanzado == []


def test_arrancar_termina_lo_lanzado_si_no_llega_a_running(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, cliente_falso: ClienteConPuertos
) -> None:
    terminados: list[int | None] = []
    monkeypatch.setattr(proceso, "puerto_ocupado", lambda puerto: False)
    monkeypatch.setattr(proceso, "lanzar_emulador", lambda *a: 321)

    def sin_running(*argumentos: Any) -> None:
        raise EmuladorError("el emulador no llego a `running`")

    monkeypatch.setattr(sesion, "esperar_running", sin_running)
    monkeypatch.setattr(proceso, "terminar_procesos", terminados.append)
    assert cli.main(["arrancar"]) == 1
    assert terminados == [321]


def test_sesion_traduce_los_argumentos_a_la_configuracion(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    recibido: dict[str, Any] = {}

    def falsa(config: sesion.ConfigSesion) -> dict[str, str]:
        recibido["config"] = config
        return {"sha256Ram": "abc"}

    monkeypatch.setattr(sesion, "ejecutar_sesion", falsa)
    codigo = cli.main(
        [
            "sesion",
            "--imagen",
            "x.cue",
            "--bios",
            "b.bin",
            "--emulador",
            "r.exe",
            "--trabajo",
            "t",
            "--salida",
            str(tmp_path),
            "--puerto",
            "8300",
            "--espera-hito",
            "ejecutable",
            "--exe-juego",
            "SLUS",
            "--tope",
            "30",
            "--retardo",
            "2.5",
        ]
    )
    assert codigo == 0
    config = recibido["config"]
    assert (config.hito, config.puerto, config.tope_hito, config.retardo_extra) == (
        "ejecutable",
        8300,
        30.0,
        2.5,
    )
    assert str(config.exe_juego) == "SLUS"
    assert _salida_json(capsys) == {"sha256Ram": "abc"}


def test_sesion_usa_los_valores_por_defecto_y_las_variables_del_entorno(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    recibido: dict[str, Any] = {}
    monkeypatch.setenv("BBLIT_REDUX", "otro/redux.exe")
    monkeypatch.setenv("BBLIT_BIOS", "otra/bios.bin")
    monkeypatch.setattr(sesion, "ejecutar_sesion", lambda config: recibido.setdefault("c", config) and {})
    assert cli.main(["sesion", "--salida", str(tmp_path)]) == 0
    config = recibido["c"]
    assert config.ejecutable.as_posix() == "otro/redux.exe"
    assert config.bios.as_posix() == "otra/bios.bin"
    assert config.imagen == RAIZ_REPOSITORIO / cli.IMAGEN_POR_DEFECTO
    assert config.carpeta_trabajo == RAIZ_REPOSITORIO / cli.TRABAJO_POR_DEFECTO
    assert (config.hito, config.puerto, config.tope_hito) == ("pantalla", 8080, 90.0)


def test_sesion_con_fallo_de_hito_da_exit_1(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def falla(config: sesion.ConfigSesion) -> dict[str, object]:
        raise EmuladorError("la pantalla sigue negra tras 90 s")

    monkeypatch.setattr(sesion, "ejecutar_sesion", falla)
    assert cli.main(["sesion", "--salida", str(tmp_path)]) == 1
    assert "sigue negra" in capsys.readouterr().out


def test_punto_de_entrada_del_modulo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["tools.emulador", "comparar"])
    with pytest.raises(SystemExit) as salida:
        runpy.run_module("tools.emulador", run_name="__main__")
    assert salida.value.code == 2

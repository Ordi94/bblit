"""Reglas de negocio de la resolucion de rutas del emulador: toolchain compartido y raiz del repositorio."""

from pathlib import Path

import pytest
from tools.emulador import cli

from tests.emulador.dobles import ClienteFalso, ram_con


@pytest.fixture
def repositorio(tmp_path: Path) -> Path:
    """Raiz de repositorio con espacios en la ruta y sin carpeta toolchain propia."""
    raiz = tmp_path / "mi repositorio"
    (raiz / "config").mkdir(parents=True)
    return raiz


@pytest.fixture
def otro_directorio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Directorio de trabajo distinto de la raiz del repositorio."""
    carpeta = tmp_path / "otro cwd"
    carpeta.mkdir()
    monkeypatch.chdir(carpeta)
    return carpeta


def test_el_emulador_y_la_bios_se_buscan_en_el_toolchain_indicado_por_la_variable(
    repositorio: Path, tmp_path: Path, otro_directorio: Path
) -> None:
    toolchain = tmp_path / "toolchain compartido"
    rutas = cli.resolver_rutas_emulador({"BBLIT_TOOLCHAIN": str(toolchain)}, repositorio)
    assert rutas.emulador == toolchain / "pcsx-redux" / "pcsx-redux.exe"
    assert rutas.bios == toolchain / "duckstation" / "bios" / "ps-22a.bin"


def test_las_variables_del_emulador_y_la_bios_anulan_al_toolchain(repositorio: Path, tmp_path: Path) -> None:
    entorno = {
        "BBLIT_TOOLCHAIN": str(tmp_path / "toolchain"),
        "BBLIT_REDUX": str(tmp_path / "mi redux" / "redux.exe"),
        "BBLIT_BIOS": str(tmp_path / "mi bios.bin"),
    }
    rutas = cli.resolver_rutas_emulador(entorno, repositorio)
    assert rutas.emulador == tmp_path / "mi redux" / "redux.exe"
    assert rutas.bios == tmp_path / "mi bios.bin"


def test_una_variable_vacia_se_trata_como_ausente(repositorio: Path, tmp_path: Path) -> None:
    entorno = {"BBLIT_TOOLCHAIN": str(tmp_path / "tc"), "BBLIT_REDUX": "", "BBLIT_BIOS": ""}
    rutas = cli.resolver_rutas_emulador(entorno, repositorio)
    assert rutas.emulador == tmp_path / "tc" / "pcsx-redux" / "pcsx-redux.exe"
    assert rutas.bios == tmp_path / "tc" / "duckstation" / "bios" / "ps-22a.bin"


def test_sin_variables_el_toolchain_por_defecto_cuelga_de_la_raiz_y_no_del_directorio_actual(
    repositorio: Path, otro_directorio: Path
) -> None:
    rutas = cli.resolver_rutas_emulador({}, repositorio)
    assert rutas.emulador == repositorio / "toolchain" / "pcsx-redux" / "pcsx-redux.exe"
    assert rutas.bios == repositorio / "toolchain" / "duckstation" / "bios" / "ps-22a.bin"
    assert not str(rutas.emulador).startswith(str(otro_directorio))


def test_la_imagen_y_la_carpeta_de_trabajo_cuelgan_de_la_raiz_aunque_se_lance_desde_otra_carpeta(
    repositorio: Path, otro_directorio: Path
) -> None:
    rutas = cli.resolver_rutas_emulador({}, repositorio)
    assert rutas.imagen == repositorio / "build" / "bblit_prueba.cue"
    assert rutas.trabajo == repositorio / "build" / "emulador"
    assert rutas.imagen.is_absolute() and rutas.trabajo.is_absolute()


def test_config_local_toml_fija_el_toolchain_sin_variable(repositorio: Path, tmp_path: Path) -> None:
    toolchain = tmp_path / "desde local"
    texto = f'[rutas]\ntoolchain = "{toolchain.as_posix()}"\n'
    (repositorio / "config" / "local.toml").write_text(texto, encoding="utf-8")
    assert cli.resolver_rutas_emulador({}, repositorio).emulador == (
        toolchain / "pcsx-redux" / "pcsx-redux.exe"
    )


def test_la_variable_del_toolchain_gana_a_config_local_toml(repositorio: Path, tmp_path: Path) -> None:
    (repositorio / "config" / "local.toml").write_text(
        f'[rutas]\ntoolchain = "{(tmp_path / "local").as_posix()}"\n', encoding="utf-8"
    )
    rutas = cli.resolver_rutas_emulador({"BBLIT_TOOLCHAIN": str(tmp_path / "entorno")}, repositorio)
    assert rutas.bios == tmp_path / "entorno" / "duckstation" / "bios" / "ps-22a.bin"


def test_el_parser_usa_las_rutas_resueltas_como_valor_por_defecto(repositorio: Path, tmp_path: Path) -> None:
    entorno = {"BBLIT_TOOLCHAIN": str(tmp_path / "tc")}
    for subcomando in ("arrancar", "sesion"):
        argumentos = ["--salida", str(tmp_path)] if subcomando == "sesion" else []
        leidos = cli.construir_parser(entorno, repositorio).parse_args([subcomando, *argumentos])
        assert leidos.emulador == tmp_path / "tc" / "pcsx-redux" / "pcsx-redux.exe"
        assert leidos.bios == tmp_path / "tc" / "duckstation" / "bios" / "ps-22a.bin"
        assert leidos.imagen == repositorio / "build" / "bblit_prueba.cue"
        assert leidos.trabajo == repositorio / "build" / "emulador"


def test_un_argumento_explicito_gana_a_las_variables_y_al_toolchain(
    repositorio: Path, tmp_path: Path
) -> None:
    entorno = {"BBLIT_TOOLCHAIN": str(tmp_path / "tc"), "BBLIT_REDUX": str(tmp_path / "redux.exe")}
    leidos = cli.construir_parser(entorno, repositorio).parse_args(["arrancar", "--emulador", "otro.exe"])
    assert leidos.emulador == Path("otro.exe")


def test_sesion_desde_otra_carpeta_con_solo_el_toolchain_define_usa_el_emulador_del_toolchain(
    repositorio: Path, tmp_path: Path, otro_directorio: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recibido = {}
    monkeypatch.setattr(cli.sesion, "ejecutar_sesion", lambda config: recibido.setdefault("c", config) and {})
    entorno = {"BBLIT_TOOLCHAIN": str(tmp_path / "tc")}
    assert cli.main(["sesion", "--salida", str(tmp_path / "salida")], entorno, repositorio) == 0
    assert recibido["c"].ejecutable == tmp_path / "tc" / "pcsx-redux" / "pcsx-redux.exe"
    assert recibido["c"].bios == tmp_path / "tc" / "duckstation" / "bios" / "ps-22a.bin"


def test_un_local_toml_invalido_se_informa_sin_traza_y_con_codigo_uno(
    repositorio: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repositorio / "config" / "local.toml").write_text("esto no es toml [", encoding="utf-8")
    assert cli.main(["apagar"], {}, repositorio) == 1
    assert capsys.readouterr().out == "error: config/local.toml no es un TOML valido\n"


@pytest.mark.parametrize("subcomando", ["volcar", "capturar"])
def test_guardado_toma_el_disco_del_entorno_inyectado_y_no_del_proceso(tmp_path, monkeypatch, subcomando):
    """BBLIT_DISC sale del entorno que recibe `main`, no de `os.environ`."""
    (tmp_path / "disc").mkdir()
    disco = tmp_path / "disc" / "juego.bin"
    disco.write_bytes(b"x")
    monkeypatch.delenv("BBLIT_DISC", raising=False)
    codigo = cli.main(
        [subcomando, "--salida", str(tmp_path / "disc" / "salida.bin")], entorno={"BBLIT_DISC": str(disco)}
    )
    assert codigo == 1
    assert not (tmp_path / "disc" / "salida.bin").exists()


@pytest.mark.parametrize("subcomando", ["volcar", "capturar"])
def test_guardado_ignora_el_disco_del_proceso_si_el_entorno_inyectado_difiere(
    tmp_path, monkeypatch, subcomando
):
    """Un BBLIT_DISC real distinto no protege nada: manda el mapping inyectado."""
    (tmp_path / "disc").mkdir()
    disco = tmp_path / "disc" / "juego.bin"
    disco.write_bytes(b"x")
    monkeypatch.setenv("BBLIT_DISC", str(disco))
    monkeypatch.setattr(
        cli, "ClienteRedux", lambda puerto: ClienteFalso(pantallas=[b"p"], rams=[ram_con(0, b"x")])
    )
    destino = tmp_path / "disc" / "salida.bin"
    assert (
        cli.main(
            [subcomando, "--salida", str(destino)], entorno={"BBLIT_DISC": str(tmp_path / "otro" / "x.bin")}
        )
        == 0
    )
    assert destino.is_file()

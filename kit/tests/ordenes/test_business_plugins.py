"""Reglas de los plugins del manifiesto: subcomandos propios y ganchos de construccion y verificacion."""

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from psxdecomp.cli import PluginInvalidoError, main
from psxdecomp.cli.plugins import resolver_referencia

from ordenes.ayudantes import EJECUTABLE, REFERENCIA, Escenario, Registro, crear_escenario, escribir_extension

MODULO = "extension_demo_ordenes"
GANCHOS = f"""\
[plugins]
subcomandos = ["{MODULO}:registrar"]
antes_de_construir = ["{MODULO}:antes", "{MODULO}:antes_segundo"]
despues_de_verificar = ["{MODULO}:despues"]
"""
CUERPO_EXTENSION = """\
def registrar(subparsers, proyecto):
    saludo = subparsers.add_parser("saludar", help="saluda con el nombre del proyecto")
    saludo.add_argument("--en-voz-alta", action="store_true")
    saludo.set_defaults(manejador=saludar)


def saludar(contexto):
    print("hola " + contexto.proyecto.identidad.nombre + (" !" if contexto.args.en_voz_alta else ""))
    return 7


def anotar(proyecto, texto):
    with open(proyecto.raiz / "ganchos.txt", "a", encoding="utf-8") as archivo:
        archivo.write(texto + "\\n")


def antes(proyecto):
    anotar(proyecto, "antes")


def antes_segundo(proyecto):
    anotar(proyecto, "antes_segundo")


def despues(proyecto, resultado):
    anotar(proyecto, "despues " + str(resultado.coincide))
"""


@pytest.fixture(autouse=True)
def limpiar_modulo() -> Iterator[None]:
    yield
    sys.modules.pop(MODULO, None)


@pytest.fixture
def escenario(tmp_path: Path) -> Escenario:
    nuevo = crear_escenario(tmp_path, plugins=GANCHOS)
    escribir_extension(nuevo.raiz, MODULO, CUERPO_EXTENSION)
    return nuevo


def ejecutar(escenario: Escenario, *argv: str) -> int:
    return main(list(argv), escenario.entorno, Registro(), raiz=escenario.raiz)


def anotaciones(escenario: Escenario) -> list[str]:
    ruta = escenario.raiz / "ganchos.txt"
    return ruta.read_text(encoding="utf-8").splitlines() if ruta.is_file() else []


def preparar_construccion(escenario: Escenario) -> None:
    assert ejecutar(escenario, "split") == 0
    (escenario.raiz / "asm" / "data").mkdir()
    (escenario.raiz / "asm" / "data" / "datos.s").write_text("d", encoding="utf-8")


def dejar_ejecutable(escenario: Escenario, contenido: bytes) -> None:
    (escenario.raiz / "build").mkdir(exist_ok=True)
    (escenario.raiz / "build" / "PRUEBA.EXE").write_bytes(contenido)


def test_un_plugin_anade_un_subcomando_que_recibe_el_contexto_y_decide_el_codigo(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    assert ejecutar(escenario, "saludar", "--en-voz-alta") == 7
    assert capsys.readouterr().out == "hola demo !\n"


def test_los_ganchos_de_construccion_se_invocan_en_el_orden_declarado_antes_de_compilar(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    preparar_construccion(escenario)
    assert anotaciones(escenario) == []
    assert ejecutar(escenario, "build") == 0
    assert anotaciones(escenario) == ["antes", "antes_segundo"]
    capsys.readouterr()


def test_un_gancho_que_falla_con_un_error_esperado_detiene_la_construccion_sin_generar_nada(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    escenario = crear_escenario(tmp_path, plugins=GANCHOS)
    escribir_extension(
        escenario.raiz,
        MODULO,
        CUERPO_EXTENSION + '\n\ndef antes(proyecto):\n    raise ValueError("falta el paso previo")\n',
    )
    preparar_construccion(escenario)
    assert ejecutar(escenario, "build") == 1
    assert capsys.readouterr().err.endswith("error: falta el paso previo\n")
    assert not (escenario.raiz / "build" / "PRUEBA.EXE").exists()


def test_los_ganchos_posteriores_a_verify_reciben_el_resultado_cuando_coincide(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    dejar_ejecutable(escenario, EJECUTABLE)
    assert ejecutar(escenario, "verify") == 0
    assert anotaciones(escenario) == ["despues True"]
    capsys.readouterr()


def test_los_ganchos_posteriores_a_verify_tambien_se_invocan_si_no_coincide_o_falta_el_ejecutable(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    assert ejecutar(escenario, "verify") == 1
    dejar_ejecutable(escenario, EJECUTABLE[:-1] + b"\xff")
    assert ejecutar(escenario, "verify") == 1
    assert anotaciones(escenario) == ["despues False", "despues False"]
    capsys.readouterr()


def test_el_codigo_de_verify_depende_del_resultado_y_no_del_valor_que_devuelve_un_gancho(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    escribir_extension(
        escenario.raiz, MODULO, CUERPO_EXTENSION + "\n\ndef despues(proyecto, resultado):\n    return 99\n"
    )
    dejar_ejecutable(escenario, EJECUTABLE)
    assert ejecutar(escenario, "verify") == 0
    assert f"OK esperado={REFERENCIA.sha256}" in capsys.readouterr().out


def test_un_gancho_posterior_que_falla_con_un_error_esperado_hace_fallar_verify(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    escribir_extension(
        escenario.raiz,
        MODULO,
        CUERPO_EXTENSION
        + '\n\ndef despues(proyecto, resultado):\n    raise ValueError("comprobacion extra")\n',
    )
    dejar_ejecutable(escenario, EJECUTABLE)
    assert ejecutar(escenario, "verify") == 1
    assert capsys.readouterr().err == "error: comprobacion extra\n"


def test_el_modulo_de_un_plugin_se_busca_en_la_raiz_del_proyecto_solo_durante_la_importacion(
    escenario: Escenario,
) -> None:
    raiz = str(escenario.raiz)
    assert raiz not in sys.path
    funcion = resolver_referencia(f"{MODULO}:saludar", escenario.raiz)
    assert callable(funcion)
    assert raiz not in sys.path


def test_si_la_raiz_ya_estaba_en_el_camino_de_busqueda_no_se_quita(
    escenario: Escenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.syspath_prepend(str(escenario.raiz))
    resolver_referencia(f"{MODULO}:saludar", escenario.raiz)
    assert str(escenario.raiz) in sys.path


@pytest.mark.parametrize(
    ("referencia", "mensaje"),
    [
        ("modulo_inexistente_xyz:funcion", "no se pudo importar el modulo 'modulo_inexistente_xyz'"),
        (f"{MODULO}:no_existe", "'no_existe' no existe o no es invocable"),
        (f"{MODULO}:CONSTANTE", "'CONSTANTE' no existe o no es invocable"),
    ],
)
def test_una_referencia_rota_da_un_error_que_nombra_el_plugin_y_no_rutas(
    escenario: Escenario, referencia: str, mensaje: str
) -> None:
    escribir_extension(escenario.raiz, MODULO, CUERPO_EXTENSION + "\nCONSTANTE = 3\n")
    with pytest.raises(PluginInvalidoError, match=mensaje) as error:
        resolver_referencia(referencia, escenario.raiz)
    assert str(escenario.raiz) not in str(error.value)


def test_un_gancho_mal_declarado_falla_solo_la_orden_que_lo_usa(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plugins = '[plugins]\nantes_de_construir = ["modulo_inexistente_xyz:antes"]\n'
    escenario = crear_escenario(tmp_path, plugins=plugins)
    preparar_construccion(escenario)
    assert ejecutar(escenario, "build") == 1
    assert "plugin 'modulo_inexistente_xyz:antes': no se pudo importar" in capsys.readouterr().err
    assert ejecutar(escenario, "clean") == 0


def test_un_subcomando_que_repite_un_nombre_comun_es_un_error_y_no_una_sustitucion(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    escenario = crear_escenario(tmp_path, plugins=f'[plugins]\nsubcomandos = ["{MODULO}:registrar"]\n')
    escribir_extension(
        escenario.raiz,
        MODULO,
        "def registrar(subparsers, proyecto):\n"
        '    subparsers.add_parser("clean").set_defaults(manejador=print)\n',
    )
    assert ejecutar(escenario, "clean") == 1
    error = capsys.readouterr().err
    assert error.startswith(f"error: plugin '{MODULO}:registrar': ")
    assert "conflicting subparser" in error


def test_un_subcomando_sin_manejador_es_un_error_del_plugin(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    escenario = crear_escenario(tmp_path, plugins=f'[plugins]\nsubcomandos = ["{MODULO}:registrar"]\n')
    escribir_extension(
        escenario.raiz,
        MODULO,
        'def registrar(subparsers, proyecto):\n    subparsers.add_parser("huerfano")\n',
    )
    assert ejecutar(escenario, "clean") == 1
    assert capsys.readouterr().err == (
        f"error: plugin '{MODULO}:registrar': el subcomando 'huerfano' no fija un manejador\n"
    )


def test_un_plugin_roto_no_impide_mostrar_la_ayuda_ni_comprobar_el_manifiesto(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plugins = '[plugins]\nsubcomandos = ["modulo_inexistente_xyz:registrar"]\n'
    escenario = crear_escenario(tmp_path, plugins=plugins)
    with pytest.raises(SystemExit) as salida:
        ejecutar(escenario, "--help")
    assert salida.value.code == 0
    assert "split" in capsys.readouterr().out
    assert main(["comprobar", str(escenario.raiz)]) == 0
    capsys.readouterr()
    assert ejecutar(escenario, "clean") == 1
    assert "no se pudo importar el modulo 'modulo_inexistente_xyz'" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("cuerpo", "tipo"),
    [
        ("def saludar(:\n    pass\n", "SyntaxError"),
        ('raise RuntimeError("boom en C:/datos/privado/secreto.txt")\n', "RuntimeError"),
    ],
)
def test_un_modulo_que_falla_al_cargarse_da_un_error_del_plugin_con_el_tipo_y_sin_rutas(
    escenario: Escenario, cuerpo: str, tipo: str
) -> None:
    escribir_extension(escenario.raiz, MODULO, cuerpo)
    with pytest.raises(PluginInvalidoError) as error:
        resolver_referencia(f"{MODULO}:saludar", escenario.raiz)
    assert str(error.value) == f"plugin '{MODULO}:saludar': el modulo '{MODULO}' fallo al cargarse ({tipo})"
    assert error.value.__cause__ is None
    assert str(escenario.raiz) not in str(error.value)
    assert "secreto" not in str(error.value)


def test_un_gancho_cuyo_modulo_lanza_al_cargarse_termina_la_orden_con_una_linea(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    escenario = crear_escenario(tmp_path, plugins=f'[plugins]\nantes_de_construir = ["{MODULO}:antes"]\n')
    escribir_extension(escenario.raiz, MODULO, 'raise RuntimeError("boom")\n')
    preparar_construccion(escenario)
    assert ejecutar(escenario, "build") == 1
    linea_final = capsys.readouterr().err.splitlines()[-1]
    assert linea_final == (
        f"error: plugin '{MODULO}:antes': el modulo '{MODULO}' fallo al cargarse (RuntimeError)"
    )

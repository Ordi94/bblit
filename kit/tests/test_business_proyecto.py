"""Reglas del manifiesto del proyecto: contrato, valores por defecto, errores y entorno."""

import dataclasses
import runpy
from pathlib import Path

import pytest
from psxdecomp import proyecto as modulo
from psxdecomp.proyecto import Proyecto, cargar_proyecto, main
from psxdecomp.validacion import ManifiestoError

from manifiestos_de_prueba import (
    MANIFIESTO_COMPLETO,
    MANIFIESTO_MINIMO,
    PROYECTO_MINIMO,
    ZONAS_MINIMAS,
    EscribirManifiesto,
)


def cargar(escribir: EscribirManifiesto, texto: str) -> Proyecto:
    return cargar_proyecto(escribir(texto))


def con_zonas(juego: object, librerias: object, hasta: object) -> str:
    """Manifiesto minimo con las tres zonas indicadas, tal como se escribirian en TOML."""
    zonas = f"[zonas]\njuego_desde = {juego}\nlibrerias_desde = {librerias}\nlibrerias_hasta = {hasta}\n"
    return PROYECTO_MINIMO + "\n" + zonas


# --- Caso feliz y valores por defecto ---------------------------------------------------------


def test_el_manifiesto_minimo_carga_con_rutas_y_convenciones_por_defecto(
    escribir_manifiesto: EscribirManifiesto,
) -> None:
    proyecto = cargar(escribir_manifiesto, MANIFIESTO_MINIMO)
    assert proyecto.identidad.nombre == "demo"
    assert proyecto.identidad.referencia == "config/ejecutable.json"
    assert proyecto.identidad.prefijo_entorno == "PSXDECOMP"
    assert (proyecto.rutas.fuentes, proyecto.rutas.incluir, proyecto.rutas.asm) == ("src", "include", "asm")
    assert proyecto.rutas.simbolos == ("config/symbols.txt",)
    assert proyecto.rutas.subcarpetas_ajenas == ()
    assert proyecto.convenciones.macro_no_coincidente == "NON_MATCHING"
    assert proyecto.convenciones.macro_ensamblador == "INCLUDE_ASM"
    assert proyecto.plugins.subcomandos == ()


def test_el_manifiesto_completo_conserva_cada_valor_declarado(
    escribir_manifiesto: EscribirManifiesto,
) -> None:
    proyecto = cargar(escribir_manifiesto, MANIFIESTO_COMPLETO)
    assert proyecto.identidad.ejecutable == "EJEC_002.11"
    assert proyecto.rutas.simbolos == ("datos/a.txt", "datos/b.txt")
    assert proyecto.rutas.asm_auxiliares == ("macros", "comunes")
    assert proyecto.rutas.documento_progreso == "notas/avance.md"
    assert proyecto.zonas.librerias_hasta == 0x80030000
    assert proyecto.convenciones.pendiente == r"\APendiente (\d+)"
    assert proyecto.plugins.despues_de_verificar == ("paquete.hook:despues", "otro:despues")


def test_el_proyecto_cargado_es_inmutable(escribir_manifiesto: EscribirManifiesto) -> None:
    proyecto = cargar(escribir_manifiesto, MANIFIESTO_MINIMO)
    with pytest.raises(dataclasses.FrozenInstanceError):
        proyecto.zonas.juego_desde = 0  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        proyecto.rutas = proyecto.rutas  # type: ignore[misc]


# --- Archivo ausente, ilegible, demasiado grande o malformado ---------------------------------


def test_sin_manifiesto_el_error_no_revela_la_ruta_absoluta(tmp_path: Path) -> None:
    with pytest.raises(ManifiestoError, match=r"no existe psxdecomp.toml") as error:
        cargar_proyecto(tmp_path)
    assert str(tmp_path) not in str(error.value)


def test_una_raiz_que_no_es_carpeta_se_rechaza(tmp_path: Path) -> None:
    archivo = tmp_path / "suelto"
    archivo.write_text("x", encoding="utf-8")
    with pytest.raises(ManifiestoError, match=r"no existe psxdecomp.toml"):
        cargar_proyecto(archivo)


def test_un_toml_malformado_se_reporta_sin_trazas_ni_rutas(
    escribir_manifiesto: EscribirManifiesto, tmp_path: Path
) -> None:
    with pytest.raises(ManifiestoError, match="no es un TOML valido") as error:
        cargar(escribir_manifiesto, "[proyecto\nnombre = ")
    assert str(tmp_path) not in str(error.value)
    assert error.value.__cause__ is None


def test_un_manifiesto_que_no_es_utf8_se_rechaza(tmp_path: Path) -> None:
    (tmp_path / "psxdecomp.toml").write_bytes(b"\xff\xfe\x00\x80")
    with pytest.raises(ManifiestoError, match="UTF-8"):
        cargar_proyecto(tmp_path)


def test_un_manifiesto_que_excede_el_tamano_maximo_se_rechaza(
    escribir_manifiesto: EscribirManifiesto,
) -> None:
    relleno = "# " + "x" * modulo.MAX_BYTES_MANIFIESTO + "\n"
    with pytest.raises(ManifiestoError, match="excede el tamano maximo"):
        cargar(escribir_manifiesto, relleno + MANIFIESTO_MINIMO)


def test_un_manifiesto_en_el_limite_exacto_de_tamano_se_acepta(
    escribir_manifiesto: EscribirManifiesto,
) -> None:
    relleno = "#" * (modulo.MAX_BYTES_MANIFIESTO - len(MANIFIESTO_MINIMO.encode()) - 1) + "\n"
    texto = relleno + MANIFIESTO_MINIMO
    assert len(texto.encode()) == modulo.MAX_BYTES_MANIFIESTO
    assert cargar(escribir_manifiesto, texto).identidad.nombre == "demo"


# --- Secciones y claves: lista de admitidos ---------------------------------------------------


def test_una_seccion_desconocida_se_rechaza(escribir_manifiesto: EscribirManifiesto) -> None:
    with pytest.raises(ManifiestoError, match=r"\[raiz\]\.extra"):
        cargar(escribir_manifiesto, MANIFIESTO_MINIMO + "\n[extra]\na = 1\n")


@pytest.mark.parametrize(
    ("seccion", "texto"),
    [
        ("proyecto", MANIFIESTO_MINIMO.replace('nombre = "demo"', 'nombre = "demo"\ncolor = "rojo"')),
        ("rutas", MANIFIESTO_MINIMO + '\n[rutas]\nfuente = "src"\n'),
        ("zonas", MANIFIESTO_MINIMO.replace("juego_desde", "extra = 1\njuego_desde")),
        ("convenciones", MANIFIESTO_MINIMO + '\n[convenciones]\nmacro = "X"\n'),
        ("plugins", MANIFIESTO_MINIMO + "\n[plugins]\nhook = []\n"),
    ],
)
def test_una_clave_desconocida_en_cualquier_seccion_es_un_error(
    escribir_manifiesto: EscribirManifiesto, seccion: str, texto: str
) -> None:
    with pytest.raises(ManifiestoError, match=rf"\[{seccion}\]\."):
        cargar(escribir_manifiesto, texto)


def test_la_seccion_proyecto_es_obligatoria(escribir_manifiesto: EscribirManifiesto) -> None:
    with pytest.raises(ManifiestoError, match=r"\[proyecto\]: se esperaba la seccion"):
        cargar(escribir_manifiesto, ZONAS_MINIMAS)


def test_la_seccion_zonas_es_obligatoria(escribir_manifiesto: EscribirManifiesto) -> None:
    with pytest.raises(ManifiestoError, match=r"\[zonas\]: se esperaba la seccion"):
        cargar(escribir_manifiesto, PROYECTO_MINIMO)


def test_una_seccion_que_no_es_tabla_se_rechaza(escribir_manifiesto: EscribirManifiesto) -> None:
    with pytest.raises(ManifiestoError, match=r"\[rutas\]: se esperaba una tabla"):
        cargar(escribir_manifiesto, "rutas = 3\n" + MANIFIESTO_MINIMO)


def test_el_nombre_del_proyecto_es_obligatorio(escribir_manifiesto: EscribirManifiesto) -> None:
    with pytest.raises(ManifiestoError, match=r"\[proyecto\]\.nombre"):
        cargar(escribir_manifiesto, MANIFIESTO_MINIMO.replace('nombre = "demo"\n', ""))


def test_el_ejecutable_es_obligatorio(escribir_manifiesto: EscribirManifiesto) -> None:
    with pytest.raises(ManifiestoError, match=r"\[proyecto\]\.ejecutable"):
        cargar(escribir_manifiesto, MANIFIESTO_MINIMO.replace('ejecutable = "EJEC_001.00"\n', ""))


@pytest.mark.parametrize("prefijo", ["minuscula", "TERMINA_", "_EMPIEZA", "CON ESPACIO", "A" * 40, ""])
def test_un_prefijo_de_entorno_fuera_de_la_lista_de_admitidos_se_rechaza(
    escribir_manifiesto: EscribirManifiesto, prefijo: str
) -> None:
    texto = MANIFIESTO_MINIMO.replace('nombre = "demo"', f'nombre = "demo"\nprefijo_entorno = "{prefijo}"')
    with pytest.raises(ManifiestoError, match=r"\[proyecto\]\.prefijo_entorno"):
        cargar(escribir_manifiesto, texto)


# --- Rutas ------------------------------------------------------------------------------------


@pytest.mark.parametrize("ruta", ["../fuera", "/absoluta", "C:/disco", "con\\\\barra", "a/../b", "x" * 201])
def test_una_ruta_del_manifiesto_que_sale_de_la_raiz_se_rechaza(
    escribir_manifiesto: EscribirManifiesto, ruta: str
) -> None:
    texto = MANIFIESTO_MINIMO + f'\n[rutas]\nfuentes = "{ruta}"\n'
    with pytest.raises(ManifiestoError, match=r"\[rutas\]\.fuentes") as error:
        cargar(escribir_manifiesto, texto)
    assert ruta not in str(error.value)


@pytest.mark.parametrize("valor", ['["../x"]', "[]", '"texto"'])
def test_una_ruta_de_simbolos_invalida_o_lista_vacia_se_rechaza(
    escribir_manifiesto: EscribirManifiesto, valor: str
) -> None:
    with pytest.raises(ManifiestoError, match=r"\[rutas\]\.simbolos"):
        cargar(escribir_manifiesto, MANIFIESTO_MINIMO + f"\n[rutas]\nsimbolos = {valor}\n")


def test_una_subcarpeta_ajena_con_separadores_se_rechaza(escribir_manifiesto: EscribirManifiesto) -> None:
    with pytest.raises(ManifiestoError, match=r"\[rutas\]\.subcarpetas_ajenas"):
        cargar(escribir_manifiesto, MANIFIESTO_MINIMO + '\n[rutas]\nsubcarpetas_ajenas = ["a/b"]\n')


def crear_raiz_con_enlace(tmp_path: Path, texto: str) -> Path:
    """Crea una raiz con el manifiesto dado y un enlace ``enlace`` hacia una carpeta externa."""
    fuera = tmp_path / "fuera"
    fuera.mkdir()
    raiz = tmp_path / "raiz"
    raiz.mkdir()
    (raiz / "psxdecomp.toml").write_text(texto, encoding="utf-8")
    try:
        (raiz / "enlace").symlink_to(fuera, target_is_directory=True)
    except OSError:
        pytest.skip("el sistema no permite crear enlaces simbolicos")
    return raiz


def test_una_ruta_cuyo_enlace_simbolico_escapa_de_la_raiz_se_rechaza(tmp_path: Path) -> None:
    raiz = crear_raiz_con_enlace(tmp_path, MANIFIESTO_MINIMO + '\n[rutas]\nfuentes = "enlace/src"\n')
    with pytest.raises(ManifiestoError, match=r"\[rutas\]\.fuentes"):
        cargar_proyecto(raiz)


def test_la_referencia_que_escapa_por_enlace_simbolico_tambien_se_rechaza(tmp_path: Path) -> None:
    texto = MANIFIESTO_MINIMO.replace('nombre = "demo"', 'nombre = "demo"\nreferencia = "enlace/e.json"')
    raiz = crear_raiz_con_enlace(tmp_path, texto)
    with pytest.raises(ManifiestoError, match=r"\[proyecto\]\.referencia"):
        cargar_proyecto(raiz)


# --- Zonas ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "campo"),
    [
        (con_zonas("0x7FFFFFFF", "0x80020000", "0x80030000"), "juego_desde"),
        (con_zonas("0x80010100", "0x80020000", "0x80800001"), "librerias_hasta"),
        (con_zonas('"0x80010100"', "0x80020000", "0x80030000"), "juego_desde"),
        (con_zonas("true", "0x80020000", "0x80030000"), "juego_desde"),
        (
            PROYECTO_MINIMO + "\n[zonas]\njuego_desde = 0x80010100\nlibrerias_desde = 0x80020000\n",
            "librerias_hasta",
        ),
    ],
)
def test_una_zona_fuera_de_rango_mal_tipada_o_ausente_se_rechaza(
    escribir_manifiesto: EscribirManifiesto, texto: str, campo: str
) -> None:
    with pytest.raises(ManifiestoError, match=rf"\[zonas\]\.{campo}"):
        cargar(escribir_manifiesto, texto)


@pytest.mark.parametrize(
    ("desde", "librerias", "hasta"),
    [
        (0x80020000, 0x80020000, 0x80030000),
        (0x80030000, 0x80020000, 0x80040000),
        (0x80010000, 0x80020000, 0x80020000),
        (0x80010000, 0x80040000, 0x80030000),
    ],
)
def test_las_zonas_deben_estar_en_orden_estricto(
    escribir_manifiesto: EscribirManifiesto, desde: int, librerias: int, hasta: int
) -> None:
    with pytest.raises(ManifiestoError, match="juego_desde < librerias_desde < librerias_hasta"):
        cargar(escribir_manifiesto, con_zonas(desde, librerias, hasta))


def test_las_zonas_con_los_extremos_del_rango_ram_se_aceptan(escribir_manifiesto: EscribirManifiesto) -> None:
    texto = con_zonas("0x80000000", "0x80000001", "0x80800000")
    assert cargar(escribir_manifiesto, texto).zonas.librerias_hasta == 0x80800000


# --- Convenciones y plugins -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("clave", "valor"),
    [
        ("pendiente", "'(sin cerrar'"),
        ("pendiente", "'Pendiente sin grupo'"),
        ("pendiente", "'(a)(b)'"),
        ("pendiente", "''"),
        ("sufijo_subsistema", "'['"),
        ("sufijo_subsistema", "7"),
        ("macro_no_coincidente", "'minuscula'"),
        ("macro_ensamblador", "'CON ESPACIO'"),
        ("macro_ensamblador", "'" + "A" * 33 + "'"),
    ],
)
def test_las_convenciones_con_expresion_invalida_o_macro_fuera_de_lista_se_rechazan(
    escribir_manifiesto: EscribirManifiesto, clave: str, valor: str
) -> None:
    with pytest.raises(ManifiestoError, match=rf"\[convenciones\]\.{clave}"):
        cargar(escribir_manifiesto, MANIFIESTO_MINIMO + f"\n[convenciones]\n{clave} = {valor}\n")


@pytest.mark.parametrize(
    "lista",
    [
        "['sin-dos-puntos']",
        "['modulo:']",
        "[':funcion']",
        "['a b:c']",
        "['a..b:c']",
        "[3]",
        "'texto'",
        "['ok:bien', 'ok:bien']",
    ],
)
def test_una_referencia_de_plugin_con_forma_invalida_se_rechaza(
    escribir_manifiesto: EscribirManifiesto, lista: str
) -> None:
    with pytest.raises(ManifiestoError, match=r"\[plugins\]\.subcomandos"):
        cargar(escribir_manifiesto, MANIFIESTO_MINIMO + f"\n[plugins]\nsubcomandos = {lista}\n")


# --- Variables de entorno ---------------------------------------------------------------------


def test_la_variable_propia_manda_sobre_el_alias_del_manifiesto(
    escribir_manifiesto: EscribirManifiesto,
) -> None:
    proyecto = cargar(escribir_manifiesto, MANIFIESTO_COMPLETO)
    entorno = {"PSXDECOMP_DISC": "propia", "OTRO_DISC": "alias"}
    assert proyecto.variable_entorno("DISC", entorno) == "propia"


def test_sin_variable_propia_se_acepta_el_alias_del_manifiesto(
    escribir_manifiesto: EscribirManifiesto,
) -> None:
    proyecto = cargar(escribir_manifiesto, MANIFIESTO_COMPLETO)
    assert proyecto.variable_entorno("DISC", {"OTRO_DISC": "alias"}) == "alias"


def test_una_variable_vacia_cuenta_como_ausente_y_pasa_al_alias(
    escribir_manifiesto: EscribirManifiesto,
) -> None:
    proyecto = cargar(escribir_manifiesto, MANIFIESTO_COMPLETO)
    assert proyecto.variable_entorno("DISC", {"PSXDECOMP_DISC": "", "OTRO_DISC": "alias"}) == "alias"


def test_sin_ninguna_variable_definida_el_resultado_es_nulo(escribir_manifiesto: EscribirManifiesto) -> None:
    proyecto = cargar(escribir_manifiesto, MANIFIESTO_COMPLETO)
    assert proyecto.variable_entorno("DISC", {"TOOLCHAIN": "x"}) is None


def test_con_el_prefijo_por_defecto_solo_se_consulta_la_variable_propia(
    escribir_manifiesto: EscribirManifiesto,
) -> None:
    proyecto = cargar(escribir_manifiesto, MANIFIESTO_MINIMO)
    assert proyecto.variable_entorno("DISC", {"PSXDECOMP_DISC": "valor"}) == "valor"


def test_sin_entorno_explicito_se_consulta_el_entorno_del_proceso(
    escribir_manifiesto: EscribirManifiesto, monkeypatch: pytest.MonkeyPatch
) -> None:
    proyecto = cargar(escribir_manifiesto, MANIFIESTO_COMPLETO)
    monkeypatch.delenv("PSXDECOMP_DISC", raising=False)
    monkeypatch.setenv("OTRO_DISC", "del-proceso")
    assert proyecto.variable_entorno("DISC") == "del-proceso"


@pytest.mark.parametrize("sufijo", ["disc", "", "CON ESPACIO", "A=B", "1INICIO", "X" * 65])
def test_un_sufijo_de_variable_fuera_de_la_lista_de_admitidos_se_rechaza(
    escribir_manifiesto: EscribirManifiesto, sufijo: str
) -> None:
    proyecto = cargar(escribir_manifiesto, MANIFIESTO_MINIMO)
    with pytest.raises(ValueError, match="identificador en mayusculas"):
        proyecto.variable_entorno(sufijo, {})


# --- Rutas absolutas y resumen ----------------------------------------------------------------


def test_la_ruta_absoluta_se_resuelve_bajo_la_raiz(escribir_manifiesto: EscribirManifiesto) -> None:
    proyecto = cargar(escribir_manifiesto, MANIFIESTO_MINIMO)
    assert proyecto.ruta_absoluta(proyecto.rutas.fuentes) == proyecto.raiz / "src"


@pytest.mark.parametrize("relativa", ["../fuera", "a/../../b", str(Path.cwd())])
def test_la_ruta_absoluta_rechaza_rutas_que_no_son_relativas_a_la_raiz(
    escribir_manifiesto: EscribirManifiesto, relativa: str
) -> None:
    proyecto = cargar(escribir_manifiesto, MANIFIESTO_MINIMO)
    with pytest.raises(ValueError, match="relativa"):
        proyecto.ruta_absoluta(relativa)


def test_el_resumen_muestra_las_zonas_en_hexadecimal_y_no_filtra_la_raiz(
    escribir_manifiesto: EscribirManifiesto, tmp_path: Path
) -> None:
    resumen = cargar(escribir_manifiesto, MANIFIESTO_COMPLETO).resumen()
    assert "0x80010100" in resumen
    assert "0x80020000-0x80030000" in resumen
    assert "subcarpetas_ajenas: extra" in resumen
    assert str(tmp_path) not in resumen


def test_el_resumen_indica_que_no_hay_subcarpetas_ajenas(escribir_manifiesto: EscribirManifiesto) -> None:
    assert "subcarpetas_ajenas: -" in cargar(escribir_manifiesto, MANIFIESTO_MINIMO).resumen()


# --- Linea de ordenes -------------------------------------------------------------------------


def test_comprobar_imprime_el_resumen_y_sale_con_cero(
    escribir_manifiesto: EscribirManifiesto, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz = escribir_manifiesto(MANIFIESTO_MINIMO)
    assert main(["--comprobar", str(raiz)]) == 0
    assert "proyecto: demo" in capsys.readouterr().out


def test_comprobar_sin_ruta_usa_la_carpeta_actual(
    escribir_manifiesto: EscribirManifiesto,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(escribir_manifiesto(MANIFIESTO_MINIMO))
    assert main(["--comprobar"]) == 0
    assert "ejecutable: EJEC_001.00" in capsys.readouterr().out


def test_comprobar_un_manifiesto_invalido_sale_con_uno_y_el_error_va_a_stderr(
    escribir_manifiesto: EscribirManifiesto, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz = escribir_manifiesto("[proyecto]\n")
    assert main(["--comprobar", str(raiz)]) == 1
    captura = capsys.readouterr()
    assert captura.out == ""
    assert captura.err.startswith("error: psxdecomp.toml:")
    assert str(raiz) not in captura.err


def test_sin_la_opcion_comprobar_se_muestra_el_uso_y_sale_con_dos(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err


def test_main_sin_argumentos_explicitos_lee_los_de_la_linea_de_ordenes(
    escribir_manifiesto: EscribirManifiesto,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raiz = escribir_manifiesto(MANIFIESTO_MINIMO)
    monkeypatch.setattr("sys.argv", ["psxdecomp.proyecto", "--comprobar", str(raiz)])
    assert main() == 0
    assert "proyecto: demo" in capsys.readouterr().out


@pytest.mark.filterwarnings("ignore:.*found in sys.modules:RuntimeWarning")
def test_el_modulo_ejecutado_con_menos_m_termina_con_el_codigo_de_main(
    escribir_manifiesto: EscribirManifiesto, monkeypatch: pytest.MonkeyPatch
) -> None:
    raiz = escribir_manifiesto(MANIFIESTO_MINIMO)
    monkeypatch.setattr("sys.argv", ["psxdecomp.proyecto", "--comprobar", str(raiz)])
    with pytest.raises(SystemExit) as salida:
        runpy.run_module("psxdecomp.proyecto", run_name="__main__")
    assert salida.value.code == 0

"""Reglas del modelo del manifiesto: contrato, valores por defecto, errores y entorno (sin tocar disco)."""

import dataclasses
import tomllib
from pathlib import Path

import pytest
from psxdecomp import dominio, lectura, proyecto, validacion
from psxdecomp.dominio import Proyecto, construir_proyecto
from psxdecomp.validacion import ManifiestoError

from manifiestos_de_prueba import (
    MANIFIESTO_COMPLETO,
    MANIFIESTO_MINIMO,
    PROYECTO_MINIMO,
    ZONAS_MINIMAS,
)

RAIZ_FICTICIA = Path("raiz-ficticia")


def cargar(texto: str) -> Proyecto:
    """Construye el proyecto desde texto TOML analizado en memoria, sin escribir ningun archivo."""
    return construir_proyecto(tomllib.loads(texto), RAIZ_FICTICIA)


def con_zonas(juego: object, librerias: object, hasta: object) -> str:
    """Manifiesto minimo con las tres zonas indicadas, tal como se escribirian en TOML."""
    zonas = f"[zonas]\njuego_desde = {juego}\nlibrerias_desde = {librerias}\nlibrerias_hasta = {hasta}\n"
    return PROYECTO_MINIMO + "\n" + zonas


# --- Caso feliz y valores por defecto ---------------------------------------------------------


def test_el_manifiesto_minimo_carga_con_rutas_y_convenciones_por_defecto() -> None:
    proyecto = cargar(MANIFIESTO_MINIMO)
    assert proyecto.identidad.nombre == "demo"
    assert proyecto.identidad.referencia == "config/ejecutable.json"
    assert proyecto.identidad.prefijo_entorno == "PSXDECOMP"
    assert (proyecto.rutas.fuentes, proyecto.rutas.incluir, proyecto.rutas.asm) == ("src", "include", "asm")
    assert proyecto.rutas.simbolos == ("config/symbols.txt",)
    assert proyecto.rutas.subcarpetas_ajenas == ()
    assert proyecto.convenciones.macro_no_coincidente == "NON_MATCHING"
    assert proyecto.convenciones.macro_ensamblador == "INCLUDE_ASM"
    assert proyecto.rutas.macros == "asm/include"
    assert proyecto.convenciones.max_valor_g == 64
    assert proyecto.convenciones.patron_simbolo_datos == r"^D_([0-9A-F]{8})$"
    assert r"escrita\s+a\s+mano" in proyecto.convenciones.manuscrita
    assert proyecto.plugins.subcomandos == ()


def test_el_manifiesto_completo_conserva_cada_valor_declarado() -> None:
    proyecto = cargar(MANIFIESTO_COMPLETO)
    assert proyecto.identidad.ejecutable == "EJEC_002.11"
    assert proyecto.rutas.simbolos == ("datos/a.txt", "datos/b.txt")
    assert proyecto.rutas.asm_auxiliares == ("macros", "comunes")
    assert proyecto.rutas.documento_progreso == "notas/avance.md"
    assert proyecto.zonas.librerias_hasta == 0x80030000
    assert proyecto.convenciones.pendiente == r"\APendiente (\d+)"
    assert proyecto.rutas.macros == "ensamblador/macros"
    assert proyecto.convenciones.manuscrita == "a mano"
    assert proyecto.convenciones.patron_simbolo_datos == "^X_([0-9A-F]{8})$"
    assert proyecto.convenciones.patron_linea_simbolo == r"^(\w+) @ 0x([0-9A-F]+) (.*)$"
    assert proyecto.convenciones.max_valor_g == 16
    assert proyecto.plugins.despues_de_verificar == ("paquete.hook:despues", "otro:despues")


def test_el_proyecto_cargado_es_inmutable() -> None:
    proyecto = cargar(MANIFIESTO_MINIMO)
    with pytest.raises(dataclasses.FrozenInstanceError):
        proyecto.zonas.juego_desde = 0  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        proyecto.rutas = proyecto.rutas  # type: ignore[misc]


# --- Secciones y claves: lista de admitidos ---------------------------------------------------


def test_una_seccion_desconocida_se_rechaza() -> None:
    with pytest.raises(ManifiestoError, match=r"\[raiz\]\.extra"):
        cargar(MANIFIESTO_MINIMO + "\n[extra]\na = 1\n")


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
def test_una_clave_desconocida_en_cualquier_seccion_es_un_error(seccion: str, texto: str) -> None:
    with pytest.raises(ManifiestoError, match=rf"\[{seccion}\]\."):
        cargar(texto)


def test_la_seccion_proyecto_es_obligatoria() -> None:
    with pytest.raises(ManifiestoError, match=r"\[proyecto\]: se esperaba la seccion"):
        cargar(ZONAS_MINIMAS)


def test_la_seccion_zonas_es_obligatoria() -> None:
    with pytest.raises(ManifiestoError, match=r"\[zonas\]: se esperaba la seccion"):
        cargar(PROYECTO_MINIMO)


def test_una_seccion_que_no_es_tabla_se_rechaza() -> None:
    with pytest.raises(ManifiestoError, match=r"\[rutas\]: se esperaba una tabla"):
        cargar("rutas = 3\n" + MANIFIESTO_MINIMO)


def test_el_nombre_del_proyecto_es_obligatorio() -> None:
    with pytest.raises(ManifiestoError, match=r"\[proyecto\]\.nombre"):
        cargar(MANIFIESTO_MINIMO.replace('nombre = "demo"\n', ""))


def test_el_ejecutable_es_obligatorio() -> None:
    with pytest.raises(ManifiestoError, match=r"\[proyecto\]\.ejecutable"):
        cargar(MANIFIESTO_MINIMO.replace('ejecutable = "EJEC_001.00"\n', ""))


@pytest.mark.parametrize("prefijo", ["minuscula", "TERMINA_", "_EMPIEZA", "CON ESPACIO", "A" * 40, ""])
def test_un_prefijo_de_entorno_fuera_de_la_lista_de_admitidos_se_rechaza(prefijo: str) -> None:
    texto = MANIFIESTO_MINIMO.replace('nombre = "demo"', f'nombre = "demo"\nprefijo_entorno = "{prefijo}"')
    with pytest.raises(ManifiestoError, match=r"\[proyecto\]\.prefijo_entorno"):
        cargar(texto)


# --- Rutas ------------------------------------------------------------------------------------


@pytest.mark.parametrize("ruta", ["../fuera", "/absoluta", "C:/disco", "con\\\\barra", "a/../b", "x" * 201])
def test_una_ruta_del_manifiesto_que_sale_de_la_raiz_se_rechaza(ruta: str) -> None:
    texto = MANIFIESTO_MINIMO + f'\n[rutas]\nfuentes = "{ruta}"\n'
    with pytest.raises(ManifiestoError, match=r"\[rutas\]\.fuentes") as error:
        cargar(texto)
    assert ruta not in str(error.value)


@pytest.mark.parametrize("valor", ['["../x"]', "[]", '"texto"'])
def test_una_ruta_de_simbolos_invalida_o_lista_vacia_se_rechaza(valor: str) -> None:
    with pytest.raises(ManifiestoError, match=r"\[rutas\]\.simbolos"):
        cargar(MANIFIESTO_MINIMO + f"\n[rutas]\nsimbolos = {valor}\n")


def test_una_subcarpeta_ajena_con_separadores_se_rechaza() -> None:
    with pytest.raises(ManifiestoError, match=r"\[rutas\]\.subcarpetas_ajenas"):
        cargar(MANIFIESTO_MINIMO + '\n[rutas]\nsubcarpetas_ajenas = ["a/b"]\n')


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
def test_una_zona_fuera_de_rango_mal_tipada_o_ausente_se_rechaza(texto: str, campo: str) -> None:
    with pytest.raises(ManifiestoError, match=rf"\[zonas\]\.{campo}"):
        cargar(texto)


@pytest.mark.parametrize(
    ("desde", "librerias", "hasta"),
    [
        (0x80020000, 0x80020000, 0x80030000),
        (0x80030000, 0x80020000, 0x80040000),
        (0x80010000, 0x80020000, 0x80020000),
        (0x80010000, 0x80040000, 0x80030000),
    ],
)
def test_las_zonas_deben_estar_en_orden_estricto(desde: int, librerias: int, hasta: int) -> None:
    with pytest.raises(ManifiestoError, match="juego_desde < librerias_desde < librerias_hasta"):
        cargar(con_zonas(desde, librerias, hasta))


def test_las_zonas_con_los_extremos_del_rango_ram_se_aceptan() -> None:
    texto = con_zonas("0x80000000", "0x80000001", "0x80800000")
    assert cargar(texto).zonas.librerias_hasta == 0x80800000


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
        ("manuscrita", "'(sin cerrar'"),
        ("patron_simbolo_datos", "'sin grupo'"),
        ("patron_simbolo_datos", "'(a)(b)'"),
        ("patron_linea_simbolo", "'(a)'"),
        ("max_valor_g", "-1"),
        ("max_valor_g", "4097"),
        ("max_valor_g", "true"),
        ("max_valor_g", "'8'"),
        ("macro_ensamblador", "'" + "A" * 33 + "'"),
    ],
)
def test_las_convenciones_con_expresion_invalida_o_macro_fuera_de_lista_se_rechazan(
    clave: str, valor: str
) -> None:
    with pytest.raises(ManifiestoError, match=rf"\[convenciones\]\.{clave}"):
        cargar(MANIFIESTO_MINIMO + f"\n[convenciones]\n{clave} = {valor}\n")


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
def test_una_referencia_de_plugin_con_forma_invalida_se_rechaza(lista: str) -> None:
    with pytest.raises(ManifiestoError, match=r"\[plugins\]\.subcomandos"):
        cargar(MANIFIESTO_MINIMO + f"\n[plugins]\nsubcomandos = {lista}\n")


# --- Variables de entorno ---------------------------------------------------------------------


def test_la_variable_propia_manda_sobre_el_alias_del_manifiesto() -> None:
    proyecto = cargar(MANIFIESTO_COMPLETO)
    entorno = {"PSXDECOMP_DISC": "propia", "OTRO_DISC": "alias"}
    assert proyecto.variable_entorno("DISC", entorno) == "propia"


def test_sin_variable_propia_se_acepta_el_alias_del_manifiesto() -> None:
    proyecto = cargar(MANIFIESTO_COMPLETO)
    assert proyecto.variable_entorno("DISC", {"OTRO_DISC": "alias"}) == "alias"


def test_una_variable_vacia_cuenta_como_ausente_y_pasa_al_alias() -> None:
    proyecto = cargar(MANIFIESTO_COMPLETO)
    assert proyecto.variable_entorno("DISC", {"PSXDECOMP_DISC": "", "OTRO_DISC": "alias"}) == "alias"


def test_sin_ninguna_variable_definida_el_resultado_es_nulo() -> None:
    proyecto = cargar(MANIFIESTO_COMPLETO)
    assert proyecto.variable_entorno("DISC", {"TOOLCHAIN": "x"}) is None


def test_con_el_prefijo_por_defecto_solo_se_consulta_la_variable_propia() -> None:
    proyecto = cargar(MANIFIESTO_MINIMO)
    assert proyecto.variable_entorno("DISC", {"PSXDECOMP_DISC": "valor"}) == "valor"


def test_sin_entorno_explicito_se_consulta_el_entorno_del_proceso(monkeypatch: pytest.MonkeyPatch) -> None:
    proyecto = cargar(MANIFIESTO_COMPLETO)
    monkeypatch.delenv("PSXDECOMP_DISC", raising=False)
    monkeypatch.setenv("OTRO_DISC", "del-proceso")
    assert proyecto.variable_entorno("DISC") == "del-proceso"


@pytest.mark.parametrize("sufijo", ["disc", "", "CON ESPACIO", "A=B", "-INICIO", "X" * 65])
def test_un_sufijo_de_variable_fuera_de_la_lista_de_admitidos_se_rechaza(sufijo: str) -> None:
    proyecto = cargar(MANIFIESTO_MINIMO)
    with pytest.raises(ValueError, match="identificador en mayusculas"):
        proyecto.variable_entorno(sufijo, {})


# --- Rutas absolutas y resumen ----------------------------------------------------------------


def test_la_ruta_absoluta_se_resuelve_bajo_la_raiz() -> None:
    proyecto = cargar(MANIFIESTO_MINIMO)
    assert proyecto.ruta_absoluta(proyecto.rutas.fuentes) == proyecto.raiz / "src"


@pytest.mark.parametrize("relativa", ["src", "a/b/c.txt", "config/splat.yaml", "a.b/c-d"])
def test_la_ruta_absoluta_acepta_rutas_relativas_que_quedan_dentro_de_la_raiz(relativa: str) -> None:
    proyecto = cargar(MANIFIESTO_MINIMO)
    assert proyecto.ruta_absoluta(relativa) == proyecto.raiz / relativa


@pytest.mark.parametrize(
    "relativa",
    [
        "../fuera",
        "a/../..",
        "a/../../b",
        "/x",
        "\\x",
        "C:/x",
        "C:x",
        "\\\\servidor\\x",
        "//servidor/x",
        "a\x00b",
        str(Path.cwd()),
    ],
)
def test_la_ruta_absoluta_rechaza_rutas_que_no_son_relativas_a_la_raiz(relativa: str) -> None:
    proyecto = cargar(MANIFIESTO_MINIMO)
    with pytest.raises(ValueError, match="relativa"):
        proyecto.ruta_absoluta(relativa)


def test_el_resumen_muestra_las_zonas_en_hexadecimal_y_no_filtra_la_raiz() -> None:
    resumen = cargar(MANIFIESTO_COMPLETO).resumen()
    assert "0x80010100" in resumen
    assert "0x80020000-0x80030000" in resumen
    assert "subcarpetas_ajenas: extra" in resumen
    assert str(RAIZ_FICTICIA) not in resumen
    assert str(RAIZ_FICTICIA.resolve()) not in resumen


def test_el_resumen_indica_que_no_hay_subcarpetas_ajenas() -> None:
    assert "subcarpetas_ajenas: -" in cargar(MANIFIESTO_MINIMO).resumen()


# --- Separacion de capas ----------------------------------------------------------------------


def test_construir_el_proyecto_no_consulta_el_sistema_de_archivos(monkeypatch: pytest.MonkeyPatch) -> None:
    def prohibido(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("el dominio no debe tocar el disco al construir")

    for operacion in ("resolve", "exists", "is_file", "is_dir", "stat", "read_text"):
        monkeypatch.setattr(Path, operacion, prohibido)
    assert cargar(MANIFIESTO_COMPLETO).identidad.nombre == "otro"


def test_los_pares_de_rutas_nombran_la_clave_y_expanden_los_simbolos() -> None:
    pares = cargar(MANIFIESTO_COMPLETO).rutas.pares()
    assert ("fuentes", "codigo") in pares
    assert ("simbolos", "datos/a.txt") in pares
    assert ("simbolos", "datos/b.txt") in pares
    assert all(clave != "subcarpetas_ajenas" for clave, _ in pares)


def test_la_fachada_reexporta_la_api_publica_de_cada_capa() -> None:
    assert proyecto.Proyecto is dominio.Proyecto
    assert proyecto.cargar_proyecto is lectura.cargar_proyecto
    assert proyecto.ManifiestoError is validacion.ManifiestoError

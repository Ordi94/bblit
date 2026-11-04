"""Opciones de compilacion y simbolos, parametrizados por las convenciones del proyecto."""

from dataclasses import replace
from typing import Any

import pytest
from psxdecomp.construccion import dominio
from psxdecomp.dominio import Convenciones, construir_convenciones

POR_DEFECTO = construir_convenciones({})
OTRAS = construir_convenciones(
    {
        "patron_simbolo_datos": r"^dato_([0-9a-f]{6})$",
        "patron_linea_simbolo": r"^(\w+) @ 0x([0-9a-f]+) (.*)$",
        "max_valor_g": 4,
    }
)

# --- $gp y datos pequenos ---------------------------------------------------------------------


def test_valor_gp_lee_la_tabla_enlace_y_valida_el_valor() -> None:
    assert dominio.valor_gp({}) is None
    assert dominio.valor_gp({"enlace": {"gp": 0x80150000}}) == 0x80150000
    for malo in (0, -4, True, "0x80150000", 0x80150001, 0x1_0000_0000):
        with pytest.raises(ValueError, match=r"enlace.gp"):
            dominio.valor_gp({"enlace": {"gp": malo}})
    malos_enlace: list[Any] = [[], {"otra": 1}, {"gp": 4, "otra": 1}]
    for malo_enlace in malos_enlace:
        with pytest.raises(ValueError, match="'enlace' solo admite la clave 'gp'"):
            dominio.valor_gp({"enlace": malo_enlace})
    with pytest.raises(ValueError, match="se esperaba una tabla"):
        dominio.valor_gp([])


def test_datos_pequenos_exige_nombre_con_su_direccion() -> None:
    assert dominio.datos_pequenos({}, POR_DEFECTO) == {}
    validos = {"datos_pequenos": {"D_80120010": 0x80120010, "D_80120020": 0x80120020}}
    assert dominio.datos_pequenos(validos, POR_DEFECTO) == {
        "D_80120010": 0x80120010,
        "D_80120020": 0x80120020,
    }
    casos = [
        ({"datos_pequenos": []}, "debe ser una tabla"),
        ({"datos_pequenos": {"x_80120010": 0x80120010}}, "no valido"),
        ({"datos_pequenos": {"D_80020010a": 0x80120010}}, "no cumple el patron de datos"),
        ({"datos_pequenos": {"D_80120010": True}}, "direccion de 'D_80120010' no valida"),
        ({"datos_pequenos": {"D_80120010": "x"}}, "direccion de 'D_80120010' no valida"),
        ({"datos_pequenos": {"D_80120010": 0}}, "direccion de 'D_80120010' no valida"),
        ({"datos_pequenos": {"D_80120010": 0x1_0000_0000}}, "direccion de 'D_80120010' no valida"),
        ({"datos_pequenos": {"D_80120010": 0x80120014}}, "no coincide con su direccion"),
    ]
    for datos, mensaje in casos:
        with pytest.raises(ValueError, match=mensaje):
            dominio.datos_pequenos(datos, POR_DEFECTO)
    with pytest.raises(ValueError, match="se esperaba una tabla"):
        dominio.datos_pequenos([], POR_DEFECTO)


def test_el_nombre_de_un_dato_pequeno_se_valida_con_el_patron_del_proyecto() -> None:
    datos = {"datos_pequenos": {"dato_020010": 0x20010 + 0x4}}
    with pytest.raises(ValueError, match="no coincide con su direccion"):
        dominio.datos_pequenos(datos, OTRAS)
    assert dominio.datos_pequenos({"datos_pequenos": {"dato_020010": 0x20010}}, OTRAS) == {
        "dato_020010": 0x20010
    }
    with pytest.raises(ValueError, match="no cumple el patron de datos"):
        dominio.datos_pequenos({"datos_pequenos": {"D_80120010": 0x80120010}}, OTRAS)


def test_texto_gp_ld_define_gp_y_los_datos_pequenos_ordenados() -> None:
    assert dominio.texto_gp_ld(0x80150000) == "_gp = 0x80150000;\n"
    texto = dominio.texto_gp_ld(0x80150000, {"D_80120020": 0x80120020, "D_80120010": 0x80120010})
    assert texto == "_gp = 0x80150000;\nD_80120010 = 0x80120010;\nD_80120020 = 0x80120020;\n"


# --- valor -G por archivo ---------------------------------------------------------------------


def test_valores_g_por_archivo_admite_las_tablas_enlace_y_datos_pequenos() -> None:
    datos = {"archivos": {"a": {"g": 8}, "b": {}}, "enlace": {"gp": 4}, "datos_pequenos": {}}
    assert dominio.valores_g_por_archivo(datos, POR_DEFECTO) == {"a": 8, "b": 0}


def test_el_tope_de_g_lo_fija_la_convencion_del_proyecto() -> None:
    assert dominio.valores_g_por_archivo({"archivos": {"a": {"g": 4}}}, OTRAS) == {"a": 4}
    with pytest.raises(ValueError, match=r"'a.g' debe ser un entero entre 0 y 4"):
        dominio.valores_g_por_archivo({"archivos": {"a": {"g": 5}}}, OTRAS)
    assert dominio.valores_g_por_archivo({"archivos": {"a": {"g": 64}}}, POR_DEFECTO) == {"a": 64}
    with pytest.raises(ValueError, match=r"'a.g' debe ser un entero entre 0 y 64"):
        dominio.valores_g_por_archivo({"archivos": {"a": {"g": 65}}}, POR_DEFECTO)


@pytest.mark.parametrize(
    ("datos", "mensaje"),
    [
        ([], "solo se admiten las tablas"),
        ({"otra": {}}, "solo se admiten las tablas"),
        ({"archivos": []}, "'archivos' debe ser una tabla"),
        ({"archivos": {"1malo": {}}}, "archivo '1malo' no valido"),
        ({"archivos": {"a": 3}}, "archivo 'a' no valido"),
        ({"archivos": {"a": {"h": 1}}}, "clave desconocida 'h'"),
        ({"archivos": {"a": {"g": True}}}, "'a.g' debe ser un entero"),
        ({"archivos": {"a": {"g": "8"}}}, "'a.g' debe ser un entero"),
        ({"archivos": {"a": {"g": -1}}}, "'a.g' debe ser un entero"),
    ],
)
def test_las_opciones_por_archivo_invalidas_se_rechazan_nombrando_el_campo(datos: Any, mensaje: str) -> None:
    with pytest.raises(ValueError, match=mensaje):
        dominio.valores_g_por_archivo(datos, POR_DEFECTO)


# --- archivo de simbolos ----------------------------------------------------------------------

TEXTO_SIMBOLOS = (
    "rutina_a = 0x80120100; // type:func size:0x4c\n"
    "D_80120010 = 0x80120010; // type:s32\n"
    "  rutina_b = 0x80120200; // type:func\n"
    "sin_tipo = 0x80120300; // size:0x4\n"
    "basura sin forma\n"
)


def test_direcciones_de_funciones_solo_toma_las_funciones() -> None:
    assert dominio.direcciones_de_funciones(TEXTO_SIMBOLOS, POR_DEFECTO) == {
        "rutina_a": 0x80120100,
        "rutina_b": 0x80120200,
    }


def test_simbolos_declarados_agrupa_por_direccion_con_su_tipo() -> None:
    declarados = dominio.simbolos_declarados(TEXTO_SIMBOLOS, POR_DEFECTO)
    assert declarados[0x80120100] == [dominio.SimboloDeclarado("rutina_a", "func")]
    assert declarados[0x80120010] == [dominio.SimboloDeclarado("D_80120010", "s32")]
    assert declarados[0x80120300] == [dominio.SimboloDeclarado("sin_tipo", "")]
    assert len(declarados) == 4


def test_la_forma_de_las_lineas_de_simbolos_la_fija_la_convencion_del_proyecto() -> None:
    texto = "rutina_c @ 0x20400 type:func\nrutina_d = 0x80120500; // type:func\n"
    assert dominio.direcciones_de_funciones(texto, OTRAS) == {"rutina_c": 0x20400}
    assert dominio.direcciones_de_funciones(texto, POR_DEFECTO) == {"rutina_d": 0x80120500}
    assert list(dominio.simbolos_declarados(texto, OTRAS)) == [0x20400]


def test_los_avisos_de_datos_pequenos_distinguen_tres_casos_y_nombran_el_archivo_de_simbolos() -> None:
    texto = (
        "D_80120010 = 0x80120010; // type:s32\n"
        "otro_nombre = 0x80120020; // type:s32\n"
        "D_80120030 = 0x80120030; // type:func\n"
    )
    declarados = dominio.simbolos_declarados(texto, POR_DEFECTO)
    datos = {
        "D_80120010": 0x80120010,
        "D_80120020": 0x80120020,
        "D_80120030": 0x80120030,
        "D_80120040": 0x80120040,
    }
    avisos = dominio.avisos_datos_pequenos(datos, declarados, "datos/simbolos.txt")
    assert avisos == [
        "[datos_pequenos] D_80120010 = 0x80120010: mismo nombre: ya figura en datos/simbolos.txt, "
        "la clave puede retirarse",
        "[datos_pequenos] D_80120020 = 0x80120020: otro nombre: datos/simbolos.txt declara otro_nombre "
        "en esa direccion",
        "[datos_pequenos] D_80120030 = 0x80120030: otro tipo: datos/simbolos.txt lo declara como funcion",
    ]


def test_las_expresiones_se_compilan_una_vez_por_convencion() -> None:
    igual = replace(POR_DEFECTO)
    assert igual == POR_DEFECTO
    assert dominio._patron_linea_simbolo(igual) is dominio._patron_linea_simbolo(POR_DEFECTO)
    assert dominio._patron_simbolo_datos(igual) is dominio._patron_simbolo_datos(POR_DEFECTO)
    assert isinstance(POR_DEFECTO, Convenciones)


# --- particion --------------------------------------------------------------------------------

CONFIGURACION = {
    "segments": [
        {
            "subsegments": [
                [0x100, "c", "uno"],
                [0x200, ".data", "uno"],
                {"type": "c", "name": "dos"},
                {"type": ".rodata", "name": "dos"},
                {"type": "rodata", "name": "dos"},
                {"type": ".rodata", "name": "huerfano"},
                [0x300, "asm", "tres"],
                "ignorada",
                {"type": 5, "name": "malo"},
            ]
        }
    ]
}


def test_secciones_declaradas_une_text_con_los_subsegmentos_con_punto_del_mismo_nombre() -> None:
    assert dominio.secciones_declaradas(CONFIGURACION) == {
        "uno": frozenset({".text", ".data"}),
        "dos": frozenset({".text", ".rodata"}),
    }


@pytest.mark.parametrize(
    "configuracion",
    [
        None,
        [],
        {},
        {"segments": []},
        {"segments": [[0x800]]},
        {"segments": [{"name": "x"}]},
        {"segments": [{"subsegments": 3}]},
    ],
)
def test_secciones_declaradas_rechaza_configuraciones_sin_la_forma_esperada(configuracion: Any) -> None:
    with pytest.raises(ValueError, match=r"falta segments\[0\]\.subsegments"):
        dominio.secciones_declaradas(configuracion)

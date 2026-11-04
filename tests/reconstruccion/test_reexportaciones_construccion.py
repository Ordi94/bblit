"""Las reexportaciones de tools/reconstruccion conservan el API publico del kit con las firmas de siempre."""

import importlib
from functools import partial
from types import ModuleType

import pytest
from tools.toolchain.contexto import PROYECTO

PARES = [
    ("tools.reconstruccion.dominio", "psxdecomp.construccion.dominio"),
    ("tools.reconstruccion.fuentes_c", "psxdecomp.diff.fuentes_c"),
    ("tools.reconstruccion.compilacion", "psxdecomp.construccion.compilacion"),
]

# Funciones que el kit recibe parametrizadas y la reexportacion enlaza con el manifiesto de este proyecto.
ENLAZADAS = {
    "tools.reconstruccion.dominio": {
        "avisos_datos_pequenos": {"archivo_simbolos": ", ".join(PROYECTO.rutas.simbolos)},
        "datos_pequenos": {"convenciones": PROYECTO.convenciones},
        "direcciones_de_funciones": {"convenciones": PROYECTO.convenciones},
        "simbolos_declarados": {"convenciones": PROYECTO.convenciones},
        "valores_g_por_archivo": {"convenciones": PROYECTO.convenciones},
    },
    "tools.reconstruccion.fuentes_c": {
        "analizar_fuente": {"convenciones": PROYECTO.convenciones},
        "analizar_fuentes": {"convenciones": PROYECTO.convenciones},
        "bloques_no_coincidentes": {"convenciones": PROYECTO.convenciones},
        "clasificar_include_asm": {"convenciones": PROYECTO.convenciones},
        "motivos_no_coincidentes": {"convenciones": PROYECTO.convenciones},
        "pendiente_declarada": {"convenciones": PROYECTO.convenciones},
        "puntuacion_pendiente": {"convenciones": PROYECTO.convenciones},
        "ubicar_funcion": {"carpeta_fuentes": PROYECTO.rutas.fuentes},
        "verificar_pendientes": {"convenciones": PROYECTO.convenciones},
    },
    "tools.reconstruccion.compilacion": {
        "comando_compilar": {
            "max_valor_g": PROYECTO.convenciones.max_valor_g,
            "compilacion": PROYECTO.compilacion,
        },
        "comando_maspsx": {
            "max_valor_g": PROYECTO.convenciones.max_valor_g,
            "compilacion": PROYECTO.compilacion,
        },
        "compilar_archivo": {
            "rutas": PROYECTO.rutas,
            "convenciones": PROYECTO.convenciones,
            "compilacion": PROYECTO.compilacion,
        },
        "compilar_fuente": {
            "rutas": PROYECTO.rutas,
            "convenciones": PROYECTO.convenciones,
            "compilacion": PROYECTO.compilacion,
        },
        "validar_fuente": {"rutas": PROYECTO.rutas},
        "verificar_solo_texto": {"rutas": PROYECTO.rutas},
    },
}

# Nombres que solo existen en la reexportacion (constantes del proyecto o codigo que aun no esta en el kit).
PROPIOS = {
    "tools.reconstruccion.dominio": {"CONVENCIONES", "MAX_VALOR_G"},
    "tools.reconstruccion.fuentes_c": {"CONVENCIONES", "MACRO_NO_COINCIDENTE"},
    "tools.reconstruccion.compilacion": {
        "CARPETA_FUENTES",
        "CARPETA_INCLUDE",
        "CARPETA_MACROS",
        "CARPETA_SALIDA",
        "COMPILACION",
        "CONVENCIONES",
        "OPCIONES_COMPILADOR",
        "RUTAS",
        "VERSION_ASPSX",
        "construir_mixto",
    },
}


def _cargar(nombre: str) -> ModuleType:
    return importlib.import_module(nombre)


@pytest.mark.parametrize(("reexportacion", "origen"), PARES)
def test_cada_nombre_reexportado_es_el_objeto_del_kit_o_su_envoltorio_enlazado(
    reexportacion: str, origen: str
) -> None:
    modulo = _cargar(reexportacion)
    kit = _cargar(origen)
    enlazadas = ENLAZADAS[reexportacion]
    assert modulo.__all__, "la reexportacion debe declarar su API"
    for nombre in modulo.__all__:
        if nombre in PROPIOS[reexportacion]:
            continue
        objeto = getattr(modulo, nombre)
        if nombre in enlazadas:
            assert isinstance(objeto, partial)
            assert objeto.func is getattr(kit, nombre)
            assert objeto.args == ()
            assert objeto.keywords == enlazadas[nombre]
        else:
            assert objeto is getattr(kit, nombre)


@pytest.mark.parametrize(("reexportacion", "origen"), PARES)
def test_el_kit_no_pierde_ningun_nombre_publico_en_la_reexportacion(reexportacion: str, origen: str) -> None:
    modulo = _cargar(reexportacion)
    kit = _cargar(origen)
    publicos = {
        nombre
        for nombre, valor in vars(kit).items()
        if not nombre.startswith("_")
        and getattr(valor, "__module__", origen) == origen
        and not isinstance(valor, ModuleType)
    }
    assert publicos <= set(modulo.__all__), sorted(publicos - set(modulo.__all__))


def test_los_nombres_propios_de_la_reexportacion_derivan_del_manifiesto() -> None:
    compilacion = _cargar("tools.reconstruccion.compilacion")
    assert compilacion.RUTAS is PROYECTO.rutas
    assert compilacion.CARPETA_INCLUDE == PROYECTO.rutas.incluir
    assert compilacion.CARPETA_MACROS == PROYECTO.rutas.macros
    assert compilacion.CARPETA_FUENTES == PROYECTO.rutas.fuentes
    assert compilacion.CARPETA_SALIDA == PROYECTO.rutas.build
    assert _cargar("tools.reconstruccion.dominio").MAX_VALOR_G == PROYECTO.convenciones.max_valor_g
    assert _cargar("tools.reconstruccion.fuentes_c").MACRO_NO_COINCIDENTE == "NON_MATCHING"

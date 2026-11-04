"""Las reexportaciones de tools/reconstruccion conservan el API publico del kit con las firmas de siempre."""

import importlib
from collections.abc import Mapping
from functools import partial
from types import ModuleType

import pytest
from tools.toolchain.contexto import PROYECTO

PARES = [
    ("tools.reconstruccion.dominio", "psxdecomp.construccion.dominio"),
    ("tools.reconstruccion.fuentes_c", "psxdecomp.diff.fuentes_c"),
    ("tools.reconstruccion.compilacion", "psxdecomp.construccion.compilacion"),
    ("tools.reconstruccion.infraestructura", "psxdecomp.construccion.infraestructura"),
    ("tools.reconstruccion.enlace_diff", "psxdecomp.diff.enlace_diff"),
    ("tools.reconstruccion.diff", "psxdecomp.diff.comparacion"),
    ("tools.reconstruccion.variantes", "psxdecomp.diff.variantes"),
    ("tools.reconstruccion.coherencia_pendientes", "psxdecomp.diff.coherencia_pendientes"),
    ("tools.reconstruccion.permutar_evaluacion", "psxdecomp.permutador.evaluacion"),
    ("tools.reconstruccion.permutar", "psxdecomp.permutador.busqueda"),
]

RUTAS: Mapping[str, object] = {"rutas": PROYECTO.rutas}
RUTAS_Y_CONVENCIONES: Mapping[str, object] = {"rutas": PROYECTO.rutas, "convenciones": PROYECTO.convenciones}
CADENA_COMPLETA: Mapping[str, object] = {
    "rutas": PROYECTO.rutas,
    "convenciones": PROYECTO.convenciones,
    "compilacion": PROYECTO.compilacion,
    "nombre_ejecutable": PROYECTO.identidad.ejecutable,
}

# Funciones que el kit recibe parametrizadas y la reexportacion enlaza con el manifiesto de este proyecto.
ENLAZADAS: Mapping[str, Mapping[str, Mapping[str, object]]] = {
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
        "construir_mixto": {
            "rutas": PROYECTO.rutas,
            "convenciones": PROYECTO.convenciones,
            "compilacion": PROYECTO.compilacion,
        },
    },
    "tools.reconstruccion.infraestructura": {
        "ejecutar_proceso": {"variables": PROYECTO.variables()},
        "leer_referencia": {"etiqueta": PROYECTO.identidad.referencia},
        "localizar_imagen": {"variables": PROYECTO.variables()},
        "obtener_original": {"rutas": PROYECTO.rutas, "variables": PROYECTO.variables()},
        "listar_fuentes_c": RUTAS,
        "leer_secciones_declaradas": RUTAS,
        "leer_valores_g": RUTAS_Y_CONVENCIONES,
        "leer_direcciones_de_funciones": RUTAS_Y_CONVENCIONES,
        "leer_gp": RUTAS,
        "leer_datos_pequenos": RUTAS_Y_CONVENCIONES,
        "verificar_configuracion": RUTAS_Y_CONVENCIONES,
        "artefactos_de_build": RUTAS,
        "limpiar": RUTAS,
        "dividir": RUTAS_Y_CONVENCIONES,
        "sanear_funciones_locales": RUTAS,
        "salidas_de_enlace": RUTAS,
        "invalidar_salida": RUTAS,
        "construir": RUTAS_Y_CONVENCIONES,
        "construir_con_compilador": RUTAS_Y_CONVENCIONES,
        "verificar": RUTAS,
    },
    "tools.reconstruccion.enlace_diff": {
        "bytes_coinciden": {"elf": "build/SLUS_008.elf"},
    },
    "tools.reconstruccion.diff": {
        "elegir_asm_objetivo": RUTAS,
        "carpeta_de_trabajo": RUTAS,
        "comparar_funcion": {
            "rutas": PROYECTO.rutas,
            "convenciones": PROYECTO.convenciones,
            "compilacion": PROYECTO.compilacion,
            "nombre_ejecutable": PROYECTO.identidad.ejecutable,
        },
        "ruta_resultado": RUTAS,
        "guardar_resultado": RUTAS,
        "preparar_objetivo": RUTAS,
    },
    "tools.reconstruccion.variantes": {"probar_variantes": CADENA_COMPLETA},
    "tools.reconstruccion.coherencia_pendientes": {
        "leer_puntuacion_medida": RUTAS,
        "avisos_puntuacion_pendiente": RUTAS_Y_CONVENCIONES,
    },
    "tools.reconstruccion.permutar_evaluacion": {"preparar_medicion": CADENA_COMPLETA},
    "tools.reconstruccion.permutar": {"leer_cabeceras": RUTAS, "permutar_funcion": CADENA_COMPLETA},
}

# Nombres que solo existen en la reexportacion (constantes del proyecto o codigo que aun no esta en el kit).
PROPIOS: dict[str, set[str]] = {
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
    },
    "tools.reconstruccion.infraestructura": {
        "BINARIO_SALIDA",
        "CARPETA_DIFF",
        "CARPETA_MACROS",
        "CARPETA_PERMUTAR",
        "CONFIGURACION_SPLAT",
        "CONVENCIONES",
        "ELF_SALIDA",
        "MAPA_SALIDA",
        "NOMBRE_EJECUTABLE",
        "OBJETOS_C_SALIDA",
        "OBJETOS_SALIDA",
        "OPCIONES_COMPILACION",
        "PROGRESO_JSON",
        "RUTAS",
        "SALIDAS",
        "SCRIPT_ENLAZADOR",
        "SCRIPT_GP",
        "SIMBOLOS_AUTOMATICOS",
        "SIMBOLOS_ENTRADA",
        "SIMBOLOS_PROYECTO",
        "SUBCARPETAS_AJENAS",
    },
    "tools.reconstruccion.enlace_diff": set(),
    "tools.reconstruccion.diff": {
        "CARPETA_ASM_COINCIDENTE",
        "CARPETA_ASM_PENDIENTE",
        "COMPILACION",
        "CONVENCIONES",
        "NOMBRE_EJECUTABLE",
        "RUTAS",
    },
    "tools.reconstruccion.variantes": set(),
    "tools.reconstruccion.coherencia_pendientes": set(),
    "tools.reconstruccion.permutar_evaluacion": set(),
    "tools.reconstruccion.permutar": set(),
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


def test_las_constantes_derivadas_del_manifiesto_conservan_los_valores_de_siempre() -> None:
    infra = _cargar("tools.reconstruccion.infraestructura")
    assert infra.SCRIPT_ENLAZADOR == "build/SLUS_008.ld"
    assert infra.ELF_SALIDA == "build/SLUS_008.elf"
    assert infra.MAPA_SALIDA == "build/SLUS_008.map"
    assert infra.BINARIO_SALIDA == "build/SLUS_008.bin"
    assert infra.SIMBOLOS_AUTOMATICOS == ("build/undefined_funcs_auto.txt", "build/undefined_syms_auto.txt")
    assert infra.SIMBOLOS_ENTRADA == "build/simbolos_entrada.txt"
    assert infra.SIMBOLOS_PROYECTO == "config/symbols.txt"
    assert infra.CONFIGURACION_SPLAT == "config/splat.yaml"
    assert infra.OPCIONES_COMPILACION == "config/opciones_compilacion.toml"
    assert infra.SCRIPT_GP == "build/gp.ld"
    assert infra.CARPETA_MACROS == "asm/include"
    assert infra.OBJETOS_SALIDA == "build/asm"
    assert infra.OBJETOS_C_SALIDA == "build/src"
    assert infra.CARPETA_DIFF == "build/diff"
    assert infra.CARPETA_PERMUTAR == "build/permutar"
    assert infra.PROGRESO_JSON == "build/progreso.json"
    assert infra.SUBCARPETAS_AJENAS == ("overlay",)
    diff = _cargar("tools.reconstruccion.diff")
    assert diff.CARPETA_ASM_COINCIDENTE == "asm/matchings"
    assert diff.CARPETA_ASM_PENDIENTE == "asm/nonmatchings"


def test_las_funciones_enlazadas_conservan_el_nombre_y_el_ejecutor_por_defecto() -> None:
    infra = _cargar("tools.reconstruccion.infraestructura")
    assert infra.dividir.func.__name__ == "dividir"
    assert infra.dividir.func.__defaults__ == (infra.ejecutar_proceso.func,)
    assert infra.construir.func.__defaults__ == (infra.ejecutar_proceso.func,)
    assert infra.construir_con_compilador.func.__defaults__ == (infra.ejecutar_proceso.func,)

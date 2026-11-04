"""Capa de enlace entre el kit y el manifiesto real del juego, para las pruebas de integracion.

Las pruebas de este paquete ejercen el kit contra ``psxdecomp.toml`` y los datos reales del
repositorio. El kit no conoce ningun proyecto: recibe rutas, convenciones y cadena de compilacion
por parametro en cada llamada. Repetir esos tres argumentos en cada una de las cientos de llamadas
de estas pruebas las volveria ilegibles y, peor, permitiria que dos pruebas usaran valores distintos
sin que nadie lo notara. Por eso este modulo los fija una sola vez, con el manifiesto cargado por
``tools.proyecto``, y expone cada funcion del kit con su firma corta. No tiene logica propia: cada
nombre es una funcion o una constante de ``psxdecomp`` con los argumentos del proyecto ya aplicados.
"""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from functools import partial
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

from tools.proyecto import PROYECTO, RAIZ_REPOSITORIO, VARIABLES, ejecutar_proceso

from psxdecomp.cli import construir_parser as _construir_parser
from psxdecomp.cli import describir_error_de_sistema, resumir_comparacion
from psxdecomp.cli import main as _main
from psxdecomp.cli.errores import ERRORES_PROPIOS
from psxdecomp.construccion import compilacion as _compilacion
from psxdecomp.construccion import dominio as _dominio
from psxdecomp.construccion import infraestructura as _infraestructura
from psxdecomp.construccion.infraestructura import Ejecutor
from psxdecomp.construccion.salidas import calcular_salidas
from psxdecomp.diff import coherencia_pendientes as _coherencia
from psxdecomp.diff import comparacion as _comparacion
from psxdecomp.diff import enlace_diff as _enlace_diff
from psxdecomp.diff import fuentes_c as _fuentes_c
from psxdecomp.diff import variantes as _variantes
from psxdecomp.permutador import busqueda as _busqueda
from psxdecomp.permutador import evaluacion as _evaluacion
from psxdecomp.progreso import calculo as _calculo
from psxdecomp.progreso import documento as _documento
from psxdecomp.progreso import medicion as _medicion
from psxdecomp.progreso import readme as _readme

RUTAS = PROYECTO.rutas
CONVENCIONES = PROYECTO.convenciones
COMPILACION = PROYECTO.compilacion
ZONAS = PROYECTO.zonas
COMANDO = PROYECTO.identidad.comando
NOMBRE_EJECUTABLE = PROYECTO.identidad.ejecutable
SALIDAS = calcular_salidas(NOMBRE_EJECUTABLE, RUTAS)
PROG = COMANDO
DESCRIPCION = "Interfaz de linea de comandos de la reconstruccion: ``python tools/build.py``."


def _espacio(
    modulo: ModuleType,
    fijos: Mapping[str, Mapping[str, Any]] | None = None,
    constantes: Mapping[str, Any] | None = None,
    *otros: ModuleType,
) -> SimpleNamespace:
    """Copia los nombres publicos de modulos del kit y fija argumentos de las funciones indicadas."""
    espacio = SimpleNamespace()
    for origen in (modulo, *otros):
        for nombre in dir(origen):
            if not nombre.startswith("__"):
                setattr(espacio, nombre, getattr(origen, nombre))
    for nombre, argumentos in (fijos or {}).items():
        setattr(espacio, nombre, partial(getattr(espacio, nombre), **argumentos))
    for nombre, valor in (constantes or {}).items():
        setattr(espacio, nombre, valor)
    return espacio


_DATOS = {"rutas": RUTAS, "convenciones": CONVENCIONES}
_CADENA = {**_DATOS, "compilacion": COMPILACION, "nombre_ejecutable": NOMBRE_EJECUTABLE}

infra = _espacio(
    _infraestructura,
    {
        "ejecutar_proceso": {"variables": VARIABLES},
        "leer_referencia": {"etiqueta": PROYECTO.identidad.referencia},
        "localizar_imagen": {"variables": VARIABLES},
        "obtener_original": {"rutas": RUTAS, "variables": VARIABLES},
        "listar_fuentes_c": {"rutas": RUTAS},
        "leer_secciones_declaradas": {"rutas": RUTAS},
        "leer_valores_g": _DATOS,
        "leer_direcciones_de_funciones": _DATOS,
        "leer_gp": {"rutas": RUTAS},
        "leer_datos_pequenos": _DATOS,
        "verificar_configuracion": _DATOS,
        "artefactos_de_build": {"rutas": RUTAS},
        "limpiar": {"rutas": RUTAS},
        "dividir": _DATOS,
        "sanear_funciones_locales": {"rutas": RUTAS},
        "salidas_de_enlace": {"rutas": RUTAS},
        "invalidar_salida": {"rutas": RUTAS},
        "construir": _DATOS,
        "construir_con_compilador": _DATOS,
        "verificar": {"rutas": RUTAS},
    },
    {
        "RUTAS": RUTAS,
        "CONVENCIONES": CONVENCIONES,
        "NOMBRE_EJECUTABLE": NOMBRE_EJECUTABLE,
        "SALIDAS": SALIDAS,
        "SCRIPT_ENLAZADOR": SALIDAS.script_enlazador,
        "SIMBOLOS_AUTOMATICOS": SALIDAS.simbolos_automaticos,
        "SIMBOLOS_ENTRADA": SALIDAS.simbolos_entrada,
        "SIMBOLOS_PROYECTO": RUTAS.simbolos[0],
        "CONFIGURACION_SPLAT": RUTAS.splat,
        "OPCIONES_COMPILACION": RUTAS.opciones_compilacion,
        "SCRIPT_GP": SALIDAS.script_gp,
        "CARPETA_MACROS": RUTAS.macros,
        "ELF_SALIDA": SALIDAS.elf,
        "MAPA_SALIDA": SALIDAS.mapa,
        "BINARIO_SALIDA": SALIDAS.binario,
        "OBJETOS_SALIDA": SALIDAS.objetos_asm,
        "OBJETOS_C_SALIDA": SALIDAS.objetos_c,
        "CARPETA_DIFF": SALIDAS.diff,
        "CARPETA_PERMUTAR": SALIDAS.permutar,
        "PROGRESO_JSON": SALIDAS.progreso_json,
        "SUBCARPETAS_AJENAS": RUTAS.subcarpetas_ajenas,
    },
)

comp = _espacio(
    _compilacion,
    {
        "comando_compilar": {"max_valor_g": CONVENCIONES.max_valor_g, "compilacion": COMPILACION},
        "comando_maspsx": {"max_valor_g": CONVENCIONES.max_valor_g, "compilacion": COMPILACION},
        "compilar_archivo": {**_DATOS, "compilacion": COMPILACION},
        "compilar_fuente": {**_DATOS, "compilacion": COMPILACION},
        "construir_mixto": {**_DATOS, "compilacion": COMPILACION},
        "validar_fuente": {"rutas": RUTAS},
        "verificar_solo_texto": {"rutas": RUTAS},
    },
    {
        "RUTAS": RUTAS,
        "COMPILACION": COMPILACION,
        "VERSION_ASPSX": COMPILACION.version_aspsx,
        "OPCIONES_COMPILADOR": COMPILACION.opciones_compilador,
        "CARPETA_INCLUDE": RUTAS.incluir,
        "CARPETA_MACROS": RUTAS.macros,
        "CARPETA_FUENTES": RUTAS.fuentes,
        "CARPETA_SALIDA": RUTAS.build,
    },
)

dominio = _espacio(
    _dominio,
    {
        "avisos_datos_pequenos": {"archivo_simbolos": ", ".join(RUTAS.simbolos)},
        "datos_pequenos": {"convenciones": CONVENCIONES},
        "direcciones_de_funciones": {"convenciones": CONVENCIONES},
        "simbolos_declarados": {"convenciones": CONVENCIONES},
        "valores_g_por_archivo": {"convenciones": CONVENCIONES},
    },
    {"CONVENCIONES": CONVENCIONES, "MAX_VALOR_G": CONVENCIONES.max_valor_g},
)

diff = _espacio(
    _comparacion,
    {
        "elegir_asm_objetivo": {"rutas": RUTAS},
        "carpeta_de_trabajo": {"rutas": RUTAS},
        "comparar_funcion": _CADENA,
        "ruta_resultado": {"rutas": RUTAS},
        "guardar_resultado": {"rutas": RUTAS},
        "preparar_objetivo": {"rutas": RUTAS},
    },
    {
        "RUTAS": RUTAS,
        "CONVENCIONES": CONVENCIONES,
        "COMPILACION": COMPILACION,
        "NOMBRE_EJECUTABLE": NOMBRE_EJECUTABLE,
        "CARPETA_ASM_COINCIDENTE": RUTAS.asm_coincidente,
        "CARPETA_ASM_PENDIENTE": RUTAS.asm_pendiente,
    },
)

fuentes_c = _espacio(
    _fuentes_c,
    {
        **{
            nombre: {"convenciones": CONVENCIONES}
            for nombre in (
                "analizar_fuente",
                "analizar_fuentes",
                "bloques_no_coincidentes",
                "clasificar_include_asm",
                "motivos_no_coincidentes",
                "pendiente_declarada",
                "puntuacion_pendiente",
                "verificar_pendientes",
            )
        },
        "ubicar_funcion": {"carpeta_fuentes": RUTAS.fuentes},
    },
    {"MACRO_NO_COINCIDENTE": CONVENCIONES.macro_no_coincidente},
)

variantes = _espacio(_variantes, {"probar_variantes": _CADENA})
enlace_diff = _espacio(_enlace_diff, {"bytes_coinciden": {"elf": SALIDAS.elf}})
coherencia_pendientes = _espacio(
    _coherencia,
    {"leer_puntuacion_medida": {"rutas": RUTAS}, "avisos_puntuacion_pendiente": _DATOS},
)
permutar = _espacio(
    _busqueda,
    {"leer_cabeceras": {"rutas": RUTAS}, "permutar_funcion": _CADENA},
)
permutar_evaluacion = _espacio(_evaluacion, {"preparar_medicion": _CADENA})
readme_progreso = _espacio(
    _readme,
    {
        "generar_seccion": {"proyecto": PROYECTO},
        "aplicar_seccion": {"etiqueta": RUTAS.readme},
        "actualizar_readme": {"proyecto": PROYECTO},
    },
    {"RUTA_README": RUTAS.readme},
)
progreso = _espacio(
    _calculo,
    {
        "leer_simbolos": {"convenciones": CONVENCIONES},
        "zona_de": {"zonas": ZONAS},
        "subsistema_de": {"convenciones": CONVENCIONES},
        "a_markdown": {"comando": COMANDO, "rutas": RUTAS, "convenciones": CONVENCIONES},
        "contar_glabel": {"rutas": RUTAS},
        "generar_progreso": {
            "rutas": RUTAS,
            "convenciones": CONVENCIONES,
            "zonas": ZONAS,
            "comando": COMANDO,
        },
    },
    {
        "COMANDO": COMANDO,
        "INICIO_JUEGO": ZONAS.juego_desde,
        "INICIO_LIBRERIAS": ZONAS.librerias_desde,
        "FIN_LIBRERIAS": ZONAS.librerias_hasta,
        "SIMBOLOS_ADICIONALES": RUTAS.simbolos_adicionales,
        "DOCUMENTO_PROGRESO": RUTAS.documento_progreso,
        "CARPETAS_ASM_AJENAS": (*RUTAS.asm_auxiliares, *RUTAS.subcarpetas_ajenas),
    },
    _documento,
    _medicion,
)
# ``calcular_progreso`` necesita la regla de agrupado ya enlazada: se fija despues de crearla.
progreso.calcular_progreso = partial(
    _calculo.calcular_progreso, zonas=ZONAS, subsistema=progreso.subsistema_de
)


def construir_parser() -> Any:
    """Analizador de la linea de ordenes del juego: el del kit con el manifiesto real."""
    return _construir_parser(PROYECTO, prog=PROG, descripcion=DESCRIPCION)


def main(
    argv: Sequence[str] | None = None,
    entorno: Mapping[str, str] | None = None,
    raiz: Path = RAIZ_REPOSITORIO,
    ejecutar: Ejecutor = ejecutar_proceso,
) -> int:
    """Ejecuta la linea de ordenes del kit con el manifiesto real sobre una raiz sustituible."""
    return _main(
        argv,
        entorno,
        ejecutar,
        proyecto=replace(PROYECTO, raiz=raiz),
        prog=PROG,
        descripcion=DESCRIPCION,
    )


cli = SimpleNamespace(
    main=main,
    construir_parser=construir_parser,
    describir_error_de_sistema=describir_error_de_sistema,
    resumir_comparacion=resumir_comparacion,
    ERRORES_PROPIOS=ERRORES_PROPIOS,
    PROG=PROG,
    RAIZ_REPOSITORIO=RAIZ_REPOSITORIO,
)

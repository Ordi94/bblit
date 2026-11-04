"""Acceso a disco y procesos: reexportacion de ``psxdecomp.construccion.infraestructura``.

El codigo vive en el kit. Este modulo conserva la ruta de importacion del repositorio y enlaza, con
el manifiesto de este proyecto (rutas, convenciones, nombre del ejecutable y variables de entorno),
las funciones que el kit recibe parametrizadas: el resto del repositorio las sigue llamando con la
firma de siempre. Las constantes de ruta (``SCRIPT_ENLAZADOR``, ``ELF_SALIDA``...) se calculan una
vez desde el manifiesto con las mismas reglas que usa el kit.

Los limites de tamano (``MAX_BYTES_*``) se reexportan como valores: la lectura de archivos
ocurre en el kit, asi que un cambio de limite en las pruebas se hace sobre
``psxdecomp.construccion.infraestructura``.
"""

from functools import partial

from psxdecomp.construccion import infraestructura as _kit
from psxdecomp.construccion.infraestructura import (
    MAX_BYTES_REFERENCIA,
    MAX_BYTES_SIMBOLOS,
    TIMEOUT_ENLAZAR_S,
    TIMEOUT_ENSAMBLAR_S,
    TIMEOUT_SPLAT_S,
    CompiladorC,
    Ejecutor,
    Herramientas,
    ProcesoError,
    extraer_de_imagen,
    resolver_herramientas,
    sha256_archivo,
)
from psxdecomp.construccion.salidas import calcular_salidas
from psxdecomp.diff.fuentes_c import MAX_BYTES_FUENTE
from tools.toolchain.contexto import PROYECTO, VARIABLES

RUTAS = PROYECTO.rutas
CONVENCIONES = PROYECTO.convenciones
NOMBRE_EJECUTABLE = PROYECTO.identidad.ejecutable
SALIDAS = calcular_salidas(NOMBRE_EJECUTABLE, RUTAS)

SCRIPT_ENLAZADOR = SALIDAS.script_enlazador
SIMBOLOS_AUTOMATICOS = SALIDAS.simbolos_automaticos
SIMBOLOS_ENTRADA = SALIDAS.simbolos_entrada
SIMBOLOS_PROYECTO = RUTAS.simbolos[0]
CONFIGURACION_SPLAT = RUTAS.splat
OPCIONES_COMPILACION = RUTAS.opciones_compilacion
SCRIPT_GP = SALIDAS.script_gp
CARPETA_MACROS = RUTAS.macros
ELF_SALIDA = SALIDAS.elf
MAPA_SALIDA = SALIDAS.mapa
BINARIO_SALIDA = SALIDAS.binario
OBJETOS_SALIDA = SALIDAS.objetos_asm
OBJETOS_C_SALIDA = SALIDAS.objetos_c
CARPETA_DIFF = SALIDAS.diff
CARPETA_PERMUTAR = SALIDAS.permutar
PROGRESO_JSON = SALIDAS.progreso_json
SUBCARPETAS_AJENAS = RUTAS.subcarpetas_ajenas

ejecutar_proceso = partial(_kit.ejecutar_proceso, variables=VARIABLES)
leer_referencia = partial(_kit.leer_referencia, etiqueta=PROYECTO.identidad.referencia)
localizar_imagen = partial(_kit.localizar_imagen, variables=VARIABLES)
obtener_original = partial(_kit.obtener_original, rutas=RUTAS, variables=VARIABLES)
listar_fuentes_c = partial(_kit.listar_fuentes_c, rutas=RUTAS)
leer_secciones_declaradas = partial(_kit.leer_secciones_declaradas, rutas=RUTAS)
leer_valores_g = partial(_kit.leer_valores_g, rutas=RUTAS, convenciones=CONVENCIONES)
leer_direcciones_de_funciones = partial(
    _kit.leer_direcciones_de_funciones, rutas=RUTAS, convenciones=CONVENCIONES
)
leer_gp = partial(_kit.leer_gp, rutas=RUTAS)
leer_datos_pequenos = partial(_kit.leer_datos_pequenos, rutas=RUTAS, convenciones=CONVENCIONES)
verificar_configuracion = partial(_kit.verificar_configuracion, rutas=RUTAS, convenciones=CONVENCIONES)
artefactos_de_build = partial(_kit.artefactos_de_build, rutas=RUTAS)
limpiar = partial(_kit.limpiar, rutas=RUTAS)
dividir = partial(_kit.dividir, rutas=RUTAS, convenciones=CONVENCIONES)
sanear_funciones_locales = partial(_kit.sanear_funciones_locales, rutas=RUTAS)
salidas_de_enlace = partial(_kit.salidas_de_enlace, rutas=RUTAS)
invalidar_salida = partial(_kit.invalidar_salida, rutas=RUTAS)
construir = partial(_kit.construir, rutas=RUTAS, convenciones=CONVENCIONES)
construir_con_compilador = partial(_kit.construir_con_compilador, rutas=RUTAS, convenciones=CONVENCIONES)
verificar = partial(_kit.verificar, rutas=RUTAS)

__all__ = [
    "BINARIO_SALIDA",
    "CARPETA_DIFF",
    "CARPETA_MACROS",
    "CARPETA_PERMUTAR",
    "CONFIGURACION_SPLAT",
    "CONVENCIONES",
    "ELF_SALIDA",
    "MAPA_SALIDA",
    "MAX_BYTES_FUENTE",
    "MAX_BYTES_REFERENCIA",
    "MAX_BYTES_SIMBOLOS",
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
    "TIMEOUT_ENLAZAR_S",
    "TIMEOUT_ENSAMBLAR_S",
    "TIMEOUT_SPLAT_S",
    "CompiladorC",
    "Ejecutor",
    "Herramientas",
    "ProcesoError",
    "artefactos_de_build",
    "construir",
    "construir_con_compilador",
    "dividir",
    "ejecutar_proceso",
    "extraer_de_imagen",
    "invalidar_salida",
    "leer_datos_pequenos",
    "leer_direcciones_de_funciones",
    "leer_gp",
    "leer_referencia",
    "leer_secciones_declaradas",
    "leer_valores_g",
    "limpiar",
    "listar_fuentes_c",
    "localizar_imagen",
    "obtener_original",
    "resolver_herramientas",
    "salidas_de_enlace",
    "sanear_funciones_locales",
    "sha256_archivo",
    "verificar",
    "verificar_configuracion",
]

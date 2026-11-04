"""Reglas puras de la reconstruccion: reexportacion de ``psxdecomp.construccion.dominio``.

El codigo vive en el kit. Este modulo conserva la ruta de importacion del repositorio y enlaza,
con las convenciones del manifiesto de este proyecto, las funciones que el kit recibe parametrizadas
(formato del archivo de simbolos, nombres de los datos pequenos y tope del umbral ``-G``): el resto
del repositorio las sigue llamando con la firma de siempre.
"""

from functools import partial

from psxdecomp.construccion.dominio import (
    CLAVES_OPCIONES_ARCHIVO,
    MAGIA_PSX_EXE,
    MAX_U32,
    OFFSET_REGION,
    TAMANO_CABECERA,
    CabeceraPsx,
    EjecutableReferencia,
    SimboloDeclarado,
    cabecera_desde_datos,
    comando_enlazar,
    comando_ensamblar,
    comando_objcopy,
    comando_splat,
    describir_diferencia,
    ensamblar_ejecutable,
    fuente_de_objeto,
    funciones_con_nombre_local,
    leer_cabecera,
    objetos_del_enlazador,
    referencia_desde_datos,
    renombrar_funciones_locales,
    resultado_verificacion,
    secciones_declaradas,
    serializar_cabecera,
    texto_gp_ld,
    texto_simbolos_entrada,
    valor_gp,
)
from psxdecomp.construccion.dominio import avisos_datos_pequenos as _avisos_datos_pequenos
from psxdecomp.construccion.dominio import datos_pequenos as _datos_pequenos
from psxdecomp.construccion.dominio import direcciones_de_funciones as _direcciones_de_funciones
from psxdecomp.construccion.dominio import simbolos_declarados as _simbolos_declarados
from psxdecomp.construccion.dominio import valores_g_por_archivo as _valores_g_por_archivo
from tools.toolchain.contexto import PROYECTO

CONVENCIONES = PROYECTO.convenciones
MAX_VALOR_G = CONVENCIONES.max_valor_g

avisos_datos_pequenos = partial(_avisos_datos_pequenos, archivo_simbolos=", ".join(PROYECTO.rutas.simbolos))
datos_pequenos = partial(_datos_pequenos, convenciones=CONVENCIONES)
direcciones_de_funciones = partial(_direcciones_de_funciones, convenciones=CONVENCIONES)
simbolos_declarados = partial(_simbolos_declarados, convenciones=CONVENCIONES)
valores_g_por_archivo = partial(_valores_g_por_archivo, convenciones=CONVENCIONES)

__all__ = [
    "CLAVES_OPCIONES_ARCHIVO",
    "CONVENCIONES",
    "MAGIA_PSX_EXE",
    "MAX_U32",
    "MAX_VALOR_G",
    "OFFSET_REGION",
    "TAMANO_CABECERA",
    "CabeceraPsx",
    "EjecutableReferencia",
    "SimboloDeclarado",
    "avisos_datos_pequenos",
    "cabecera_desde_datos",
    "comando_enlazar",
    "comando_ensamblar",
    "comando_objcopy",
    "comando_splat",
    "datos_pequenos",
    "describir_diferencia",
    "direcciones_de_funciones",
    "ensamblar_ejecutable",
    "fuente_de_objeto",
    "funciones_con_nombre_local",
    "leer_cabecera",
    "objetos_del_enlazador",
    "referencia_desde_datos",
    "renombrar_funciones_locales",
    "resultado_verificacion",
    "secciones_declaradas",
    "serializar_cabecera",
    "simbolos_declarados",
    "texto_gp_ld",
    "texto_simbolos_entrada",
    "valor_gp",
    "valores_g_por_archivo",
]

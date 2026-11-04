"""Manifiestos sinteticos y tipos compartidos por las pruebas del kit (datos inventados)."""

from collections.abc import Callable
from pathlib import Path

EscribirManifiesto = Callable[[str], Path]

PROYECTO_MINIMO = """\
[proyecto]
nombre = "demo"
ejecutable = "EJEC_001.00"
"""

ZONAS_MINIMAS = """\
[zonas]
juego_desde = 0x80010100
librerias_desde = 0x80020000
librerias_hasta = 0x80030000
"""

MANIFIESTO_MINIMO = PROYECTO_MINIMO + "\n" + ZONAS_MINIMAS

MANIFIESTO_COMPLETO = """\
[proyecto]
nombre = "otro"
ejecutable = "EJEC_002.11"
referencia = "datos/ejecutable.json"
prefijo_entorno = "OTRO"

[rutas]
fuentes = "codigo"
incluir = "cabeceras"
asm = "ensamblador"
build = "salida"
expected = "esperado"
splat = "datos/splat.yaml"
simbolos = ["datos/a.txt", "datos/b.txt"]
simbolos_adicionales = "datos/extra.txt"
opciones_compilacion = "datos/opciones.toml"
toolchain_lock = "datos/lock.json"
local = "datos/local.toml"
documento_progreso = "notas/avance.md"
subcarpetas_ajenas = ["extra"]
asm_auxiliares = ["macros", "comunes"]

[zonas]
juego_desde = 0x80010100
librerias_desde = 0x80020000
librerias_hasta = 0x80030000

[convenciones]
macro_no_coincidente = "NO_COINCIDE"
macro_ensamblador = "ENSAMBLAR"
pendiente = '\\APendiente (\\d+)'
sufijo_subsistema = '-\\d+$'

[plugins]
subcomandos = ["paquete.modulo:registrar"]
antes_de_construir = ["paquete.hook:antes"]
despues_de_verificar = ["paquete.hook:despues", "otro:despues"]
"""

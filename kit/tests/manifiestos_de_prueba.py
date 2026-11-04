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
juego_desde = 0x80110100
librerias_desde = 0x80120000
librerias_hasta = 0x80130000
"""

MANIFIESTO_MINIMO = PROYECTO_MINIMO + "\n" + ZONAS_MINIMAS

MANIFIESTO_COMPLETO = """\
[proyecto]
nombre = "otro"
ejecutable = "EJEC_002.11"
referencia = "datos/ejecutable.json"
prefijo_entorno = "OTRO"
comando = "otro-decomp --raiz ."
funcion_ejemplo = "rutina_demo"

[rutas]
fuentes = "codigo"
incluir = "cabeceras"
asm = "ensamblador"
macros = "ensamblador/macros"
asm_coincidente = "ensamblador/cerradas"
asm_pendiente = "ensamblador/pendientes"
build = "salida"
expected = "esperado"
splat = "datos/splat.yaml"
simbolos = ["datos/a.txt", "datos/b.txt"]
simbolos_adicionales = "datos/extra.txt"
opciones_compilacion = "datos/opciones.toml"
toolchain_lock = "datos/lock.json"
local = "datos/local.toml"
documento_progreso = "notas/avance.md"
readme = "LEEME.md"
subcarpetas_ajenas = ["extra"]
asm_auxiliares = ["macros", "comunes"]

[zonas]
juego_desde = 0x80110100
librerias_desde = 0x80120000
librerias_hasta = 0x80130000

[convenciones]
macro_no_coincidente = "NO_COINCIDE"
macro_ensamblador = "ENSAMBLAR"
pendiente = '\\APendiente (\\d+)'
sufijo_subsistema = '-\\d+$'
manuscrita = 'a mano'
patron_simbolo_datos = '^X_([0-9A-F]{8})$'
patron_linea_simbolo = '^(\\w+) @ 0x([0-9A-F]+) (.*)$'
max_valor_g = 16

[compilacion]
version_aspsx = "2.67"
opciones_compilador = ["-quiet", "-O1", "-fno-builtin"]

[plugins]
subcomandos = ["paquete.modulo:registrar"]
antes_de_construir = ["paquete.hook:antes"]
despues_de_verificar = ["paquete.hook:despues", "otro:despues"]
entrada_progreso = "paquete.progreso:agrupar"
"""

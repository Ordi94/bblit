"""Coherencia entre el manifiesto del repositorio consumidor y las constantes vigentes de ``tools/``.

Mientras los modulos de ``tools/`` conservan sus propias constantes, el manifiesto es una segunda
copia de los mismos valores. Esta prueba las compara una a una para que la copia no se desvie; cuando
los modulos pasen a leer el manifiesto, las constantes desapareceran y la prueba con ellas. Se omite
si el kit se ejecuta fuera del repositorio consumidor (sin manifiesto o sin ``tools``), y entonces el
motivo del salto aparece en el resumen de la ejecucion.
"""

import json
from pathlib import Path
from types import ModuleType

import pytest
from psxdecomp.proyecto import Proyecto, cargar_proyecto

RAIZ_CONSUMIDOR = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not (RAIZ_CONSUMIDOR / "psxdecomp.toml").is_file(), reason="no hay manifiesto consumidor en la raiz"
)


@pytest.fixture(scope="module")
def proyecto() -> Proyecto:
    return cargar_proyecto(RAIZ_CONSUMIDOR)


def modulo(nombre: str) -> ModuleType:
    encontrado: ModuleType = pytest.importorskip(
        f"tools.{nombre}",
        reason="el proyecto consumidor no ofrece el paquete tools: la coherencia no se ejercita",
    )
    return encontrado


def test_el_manifiesto_del_consumidor_es_valido_y_no_declara_plugins_inexistentes(proyecto: Proyecto) -> None:
    assert proyecto.plugins.subcomandos == ()
    assert proyecto.plugins.antes_de_construir == ()
    assert proyecto.plugins.despues_de_verificar == ()


def test_el_ejecutable_coincide_con_la_referencia_versionada(proyecto: Proyecto) -> None:
    referencia = json.loads(proyecto.ruta_absoluta(proyecto.identidad.referencia).read_text(encoding="utf-8"))
    assert referencia["nombre"] == proyecto.identidad.ejecutable


def test_los_nombres_de_salida_derivan_del_ejecutable(proyecto: Proyecto) -> None:
    infra = modulo("reconstruccion.infraestructura")
    base = f"{proyecto.rutas.build}/{proyecto.identidad.ejecutable.rsplit('.', 1)[0]}"
    assert infra.SCRIPT_ENLAZADOR == f"{base}.ld"
    assert infra.ELF_SALIDA == f"{base}.elf"
    assert infra.MAPA_SALIDA == f"{base}.map"
    assert infra.BINARIO_SALIDA == f"{base}.bin"


def test_las_rutas_de_infraestructura_coinciden_con_el_manifiesto(proyecto: Proyecto) -> None:
    infra = modulo("reconstruccion.infraestructura")
    rutas = proyecto.rutas
    assert infra.SIMBOLOS_PROYECTO in rutas.simbolos
    assert infra.CONFIGURACION_SPLAT == rutas.splat
    assert infra.OPCIONES_COMPILACION == rutas.opciones_compilacion
    assert infra.CARPETA_MACROS == f"{rutas.asm}/include"
    assert infra.CARPETA_PERMUTAR.startswith(f"{rutas.build}/")
    assert infra.SCRIPT_ENLAZADOR.startswith(f"{rutas.build}/")
    assert infra.OBJETOS_C_SALIDA == f"{rutas.build}/{rutas.fuentes}"
    assert infra.OBJETOS_SALIDA == f"{rutas.build}/{rutas.asm}"
    assert infra.SUBCARPETAS_AJENAS == rutas.subcarpetas_ajenas


def test_las_rutas_de_compilacion_coinciden_con_el_manifiesto(proyecto: Proyecto) -> None:
    compilacion = modulo("reconstruccion.compilacion")
    rutas = proyecto.rutas
    assert compilacion.CARPETA_INCLUDE == rutas.incluir
    assert compilacion.CARPETA_MACROS == rutas.macros == f"{rutas.asm}/include"
    assert compilacion.RUTAS == rutas
    assert compilacion.CARPETA_FUENTES == rutas.fuentes
    assert compilacion.CARPETA_SALIDA == rutas.build


def test_las_rutas_de_la_linea_de_ordenes_coinciden_con_el_manifiesto(proyecto: Proyecto) -> None:
    cli = modulo("reconstruccion.cli")
    assert cli.RUTA_REFERENCIA.as_posix() == proyecto.identidad.referencia
    assert cli.RUTA_LOCK.as_posix() == proyecto.rutas.toolchain_lock
    assert cli.RUTA_LOCAL.as_posix() == proyecto.rutas.local


def test_las_rutas_y_zonas_del_medidor_de_progreso_coinciden_con_el_manifiesto(proyecto: Proyecto) -> None:
    progreso = modulo("reconstruccion.progreso")
    assert progreso.SIMBOLOS_ADICIONALES == proyecto.rutas.simbolos_adicionales
    assert progreso.DOCUMENTO_PROGRESO == proyecto.rutas.documento_progreso
    ignoradas = set(proyecto.rutas.subcarpetas_ajenas) | set(proyecto.rutas.asm_auxiliares)
    assert set(progreso.CARPETAS_ASM_AJENAS) == ignoradas
    assert progreso.INICIO_JUEGO == proyecto.zonas.juego_desde
    assert progreso.INICIO_LIBRERIAS == proyecto.zonas.librerias_desde
    assert progreso.FIN_LIBRERIAS == proyecto.zonas.librerias_hasta


def test_las_zonas_del_analisis_de_ghidra_coinciden_con_el_manifiesto(proyecto: Proyecto) -> None:
    zonas = modulo("ghidra.zonas")
    dominio = modulo("ghidra.dominio")
    assert zonas.INICIO_JUEGO == proyecto.zonas.juego_desde
    assert zonas.FIN_JUEGO == proyecto.zonas.librerias_desde
    assert dominio.FIN_CODIGO == proyecto.zonas.librerias_hasta


def test_las_convenciones_de_comentario_coinciden_con_el_manifiesto(proyecto: Proyecto) -> None:
    fuentes = modulo("reconstruccion.fuentes_c")
    progreso = modulo("reconstruccion.progreso")
    convenciones = proyecto.convenciones
    dominio = modulo("reconstruccion.dominio")
    assert fuentes.CONVENCIONES == convenciones
    assert dominio.CONVENCIONES == convenciones
    assert fuentes.MACRO_NO_COINCIDENTE == convenciones.macro_no_coincidente
    assert dominio.MAX_VALOR_G == convenciones.max_valor_g
    assert progreso._PATRON_SUFIJO_NUMERICO.pattern == convenciones.sufijo_subsistema


def test_las_variables_de_entorno_del_toolchain_usan_el_prefijo_del_manifiesto(proyecto: Proyecto) -> None:
    configuracion = modulo("toolchain.configuracion")
    prefijo = proyecto.identidad.prefijo_entorno
    assert configuracion.VARIABLE_DISCO == f"{prefijo}_DISC"
    assert configuracion.VARIABLE_TOOLCHAIN == f"{prefijo}_TOOLCHAIN"
    assert configuracion.VARIABLE_7ZIP == f"{prefijo}_7ZIP"


def test_el_alias_del_prefijo_del_manifiesto_resuelve_las_variables_vigentes(proyecto: Proyecto) -> None:
    configuracion = modulo("toolchain.configuracion")
    entorno = {configuracion.VARIABLE_DISCO: "valor"}
    assert proyecto.variable_entorno("DISC", entorno) == "valor"

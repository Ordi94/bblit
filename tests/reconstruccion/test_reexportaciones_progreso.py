"""Las reexportaciones del medidor y de la seccion del README reflejan el manifiesto de este proyecto."""

from tools.reconstruccion import progreso, readme_progreso
from tools.toolchain.contexto import PROYECTO

from psxdecomp.progreso import calculo, documento, medicion, readme

SIMBOLO = "f = 0x{:08X}; // type:func size:0x10"


def test_las_zonas_y_las_rutas_salen_del_manifiesto() -> None:
    assert progreso.INICIO_JUEGO == PROYECTO.zonas.juego_desde
    assert progreso.INICIO_LIBRERIAS == PROYECTO.zonas.librerias_desde
    assert progreso.FIN_LIBRERIAS == PROYECTO.zonas.librerias_hasta
    assert progreso.SIMBOLOS_ADICIONALES == PROYECTO.rutas.simbolos_adicionales
    assert progreso.DOCUMENTO_PROGRESO == PROYECTO.rutas.documento_progreso
    assert set(progreso.CARPETAS_ASM_AJENAS) == {"include", "matchings", "overlay"}
    assert progreso.COMANDO == "python tools/build.py"
    assert readme_progreso.RUTA_README == PROYECTO.rutas.readme == "README.md"


def test_las_funciones_enlazan_el_manifiesto_con_el_kit() -> None:
    zonas = PROYECTO.zonas
    assert progreso.zona_de(zonas.juego_desde - 1) == "arranque"
    assert progreso.zona_de(zonas.juego_desde) == "juego"
    assert progreso.zona_de(zonas.librerias_desde) == "libreria"
    assert progreso.zona_de(zonas.librerias_hasta) == "otra"
    assert progreso.subsistema_de("src/graficos_y_gte_10.c") == "graficos_y_gte"
    assert [f.direccion for f in progreso.leer_simbolos(SIMBOLO.format(zonas.juego_desde))] == [
        zonas.juego_desde
    ]


def test_las_clases_y_las_funciones_puras_son_las_del_kit() -> None:
    assert progreso.Progreso is calculo.Progreso
    assert progreso.FuncionSimbolo is calculo.FuncionSimbolo
    assert progreso.combinar_simbolos is calculo.combinar_simbolos
    assert progreso.a_json is documento.a_json
    assert readme_progreso.ResumenJuego is readme.ResumenJuego
    assert readme_progreso.resumir_juego is readme.resumir_juego
    assert readme_progreso.obtener_hash_corto is readme.obtener_hash_corto
    assert readme_progreso.MARCA_INICIO == readme.MARCA_INICIO
    assert readme_progreso.MAX_BYTES_README == readme.MAX_BYTES_README


def test_el_texto_del_readme_nombra_el_comando_y_la_variable_de_este_proyecto() -> None:
    resumen = readme_progreso.ResumenJuego(1, 1, 0, 0, 0, 16, 16, 100.0)
    seccion = readme_progreso.generar_seccion(resumen, "2026-01-01", "abcdef0", "ab" * 32)
    assert "`python tools/build.py progreso`" in seccion
    assert "`BBLIT_DISC`" in seccion
    assert f"python tools/build.py verify      # debe imprimir OK con SHA-256 {'ab' * 32}" in seccion
    assert "(por ejemplo func_80036204)" in seccion


def test_los_modulos_del_kit_que_enlaza_son_los_de_medicion() -> None:
    assert callable(medicion.generar_progreso) and callable(progreso.generar_progreso)

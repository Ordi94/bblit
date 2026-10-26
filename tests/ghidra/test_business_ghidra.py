"""Reglas del contrato de la tabla de simbolos y de la verificacion de la carga."""

import re
from pathlib import Path

import pytest
from tools.ghidra.borradores import generar_borradores, seleccionar_funciones
from tools.ghidra.depuracion import depurar_funciones
from tools.ghidra.dominio import (
    DIRECCION_BASE,
    DIRECCION_ENTRADA,
    DIRECCION_FIN,
    Simbolo,
    calcular_informe,
    construir_simbolos,
)
from tools.ghidra.ejecucion import verificar_carga
from tools.ghidra.ensamblador import dividir_por_funcion
from tools.ghidra.grafo import (
    TIPOS_ARISTA,
    comparar_llamadores,
    construir_grafo,
    formatear_grafo_csv,
)
from tools.ghidra.lectura import parsear_funciones_csv
from tools.ghidra.limites import MAX_USUARIOS_DATO
from tools.ghidra.simbolos import formatear_tabla, parsear_tabla
from tools.ghidra.subsistemas import parsear_rangos
from tools.ghidra.tablas import detectar_corridas
from tools.ghidra.zonas import FIN_JUEGO, INICIO_JUEGO, clasificar_zona

from tests.ghidra import escenario
from tests.ghidra.segmentos import BASE, INSTRUCCION, cierre, segmento
from tests.ghidra.sintetica import MUESTRA, funcion

RAIZ = Path(__file__).resolve().parents[2]


def test_funcion_de_libreria_identificada_por_firma_lleva_el_nombre_oficial() -> None:
    simbolos = construir_simbolos(
        [funcion(0x80051938, "DrawSync", 0x68, es_libreria=True, nombre_oficial=True)]
    )
    assert simbolos == [Simbolo("DrawSync", 0x80051938, "func", 0x68)]


def test_funcion_del_juego_sin_identificar_lleva_func_con_su_direccion() -> None:
    simbolos = construir_simbolos([funcion(0x80016C0C, "FUN_80016c0c", 0x64)])
    assert simbolos == [Simbolo("func_80016C0C", 0x80016C0C, "func", 0x64)]


def test_rutina_interna_de_libreria_sin_nombre_exportado_no_inventa_nombre() -> None:
    simbolos = construir_simbolos([funcion(0x80045F28, "LIBPRESS_OBJ_188", 0x2C, es_libreria=True)])
    assert simbolos[0].nombre == "func_80045F28"


def test_el_nombre_que_el_cargador_da_a_la_rutina_principal_se_conserva() -> None:
    simbolos = construir_simbolos([funcion(0x80016414, "main", 0x7F8)])
    assert simbolos[0].nombre == "main"


def test_un_nombre_del_juego_que_imita_a_uno_de_libreria_no_se_toma_como_oficial() -> None:
    simbolos = construir_simbolos([funcion(0x80016C0C, "DrawSync", 0x64, es_libreria=False)])
    assert simbolos[0].nombre == "func_80016C0C"


def test_las_direcciones_de_funcion_exportadas_estan_alineadas_a_cuatro() -> None:
    simbolos = construir_simbolos(parsear_funciones_csv(MUESTRA))
    assert all(s.direccion % 4 == 0 for s in simbolos)


def test_la_tabla_generada_esta_ordenada_sin_direcciones_ni_nombres_repetidos() -> None:
    funciones = [funcion(0x80014A00 + 0x10 * i, f"FUN_{i}", 0x10) for i in (5, 1, 3, 2, 4)]
    simbolos = construir_simbolos(funciones)
    direcciones = [s.direccion for s in simbolos]
    assert direcciones == sorted(set(direcciones))
    assert len({s.nombre for s in simbolos}) == len(simbolos)


def test_dos_copias_estaticas_de_una_rutina_de_libreria_no_comparten_nombre() -> None:
    funciones = [
        funcion(0x8004E188, "memclr", 0x2C, es_libreria=True, nombre_oficial=True),
        funcion(0x8004E2B0, "memclr", 0x2C, es_libreria=True, nombre_oficial=True),
    ]
    assert [s.nombre for s in construir_simbolos(funciones)] == ["memclr_8004E188", "memclr_8004E2B0"]


def test_el_tamano_nunca_invade_a_la_funcion_vecina() -> None:
    funciones = [funcion(0x80014A00, "a", 0x5000), funcion(0x80014A20, "b", 0x20)]
    primero, segundo = construir_simbolos(funciones)
    assert primero.direccion + primero.tamano == segundo.direccion


def test_ningun_simbolo_sale_del_segmento_del_ejecutable() -> None:
    simbolos = construir_simbolos([funcion(DIRECCION_FIN - 4, "ultima", 0x1000)])
    assert simbolos[0].direccion + simbolos[0].tamano == DIRECCION_FIN


def test_una_funcion_fuera_del_segmento_se_rechaza_nombrando_el_simbolo() -> None:
    with pytest.raises(ValueError, match=r"simbolo func_80010000: direccion 0x80010000 fuera del rango"):
        construir_simbolos([funcion(0x80010000, "FUN_80010000", 8)])


def test_un_simbolo_duplicado_se_rechaza_al_leer_la_tabla() -> None:
    texto = "a = 0x80014A00; // type:func size:0x4\na = 0x80014A04; // type:func size:0x4\n"
    with pytest.raises(ValueError, match=r"simbolo a: nombre duplicado"):
        parsear_tabla(texto)


def test_la_cobertura_es_la_suma_de_los_tamanos_sobre_el_segmento() -> None:
    funciones = [funcion(DIRECCION_BASE, "a", 0x55000 // 2)]
    assert calcular_informe(funciones).porcentaje_cubierto == 50.0


def test_el_juego_es_lo_que_ninguna_firma_identifica() -> None:
    informe = calcular_informe(parsear_funciones_csv(MUESTRA))
    assert (informe.libreria, informe.juego, informe.total) == (3, 2, 5)
    assert informe.libreria + informe.juego == informe.total


def test_una_carga_con_otra_base_se_considera_fallida() -> None:
    registro = "Using Loader: PSX Executables Loader\nBBLIT base=0x80010000\nBBLIT entrada=0x80014A08\n"
    with pytest.raises(ValueError, match=r"base=0x80010000, se esperaba 0x80014A00"):
        verificar_carga(registro)


def test_el_punto_de_entrada_esta_dentro_del_segmento_cargado() -> None:
    assert DIRECCION_BASE <= DIRECCION_ENTRADA < DIRECCION_FIN


def test_la_tabla_de_simbolos_del_repositorio_cumple_el_contrato() -> None:
    ruta = RAIZ / "config" / "symbols.txt"
    texto = ruta.read_text(encoding="utf-8")
    simbolos = parsear_tabla(texto)
    assert formatear_tabla(simbolos) == texto
    por_nombre = {s.nombre: s for s in simbolos}
    assert por_nombre["main"].direccion == 0x80016414
    assert por_nombre["DrawSync"].direccion == 0x80051938
    assert por_nombre["VSync"].direccion == 0x8004D8C0
    assert por_nombre["CdReadSync"].direccion == 0x800494FC
    assert not any(s.nombre.startswith("FUN_") for s in simbolos)


def test_un_fragmento_interior_de_cuatro_bytes_no_se_emite_como_funcion() -> None:
    inicio = BASE + 0x100
    palabras = {inicio + 8: INSTRUCCION, inicio + 0x10: INSTRUCCION, **cierre(inicio + 0x14, 0x18)}
    candidatas = [funcion(inicio, "SpuSetReverb", 0x10), funcion(inicio + 0x10, "S_SR_OBJ_B0", 4)]
    candidatas.append(funcion(inicio + 0x14, "S_SR_OBJ_B4", 0x18))
    resultado = depurar_funciones(candidatas, segmento(palabras))
    simbolos = construir_simbolos(resultado.funciones)
    assert [(s.direccion, s.tamano) for s in simbolos] == [(inicio, 0x2C)]


def test_ninguna_funcion_de_la_tabla_del_repositorio_mide_menos_de_ocho_bytes() -> None:
    texto = (RAIZ / "config" / "symbols.txt").read_text(encoding="utf-8")
    assert all(s.tamano >= 8 for s in parsear_tabla(texto) if s.tipo == "func")


def test_una_funcion_cuyo_cuerpo_no_tiene_salto_final_no_se_emite() -> None:
    inicio = BASE + 0x100
    resultado = depurar_funciones([funcion(inicio, "FUN_x", 0x10)], segmento({inicio: INSTRUCCION}))
    assert resultado.funciones == []


# --- Reglas del analisis de llamadas, borradores y subsistemas -------------------------------


def _grafo_del_escenario(funciones: list | None = None):  # type: ignore[no-untyped-def]
    corridas = detectar_corridas(
        escenario.segmento_programa(), BASE, (0x8005DEA0, 0x80069A00), (INICIO_JUEGO, FIN_JUEGO)
    )
    lista = dividir_por_funcion(escenario.texto_asm()) if funciones is None else funciones
    return construir_grafo(lista, escenario.simbolos(), corridas)


def test_el_codigo_del_juego_empieza_y_termina_en_inicios_de_funcion_de_la_tabla_del_repositorio() -> None:
    simbolos = parsear_tabla((RAIZ / "config" / "symbols.txt").read_text(encoding="utf-8"))
    direcciones = {s.direccion for s in simbolos}
    assert INICIO_JUEGO in direcciones
    assert FIN_JUEGO in direcciones
    del_juego = [s for s in simbolos if clasificar_zona(s.direccion) == "juego"]
    assert del_juego, "la tabla debe tener funciones en el rango del juego"
    assert max(s.direccion + s.tamano for s in del_juego) <= FIN_JUEGO


def test_las_rutinas_de_libreria_identificadas_por_firma_no_reciben_borrador() -> None:
    simbolos = [Simbolo("VSync", 0x80045E00, "func", 0x20), Simbolo("main", 0x80016414, "func", 0x7F8)]
    filas = [funcion(0x80045E00, "VSync", 0x20, es_libreria=True), funcion(0x80016414, "main", 0x7F8)]
    assert [s.nombre for s in seleccionar_funciones(simbolos, filas)] == ["main"]


def test_el_grafo_usa_exactamente_cuatro_tipos_de_arista_y_el_escenario_los_ejerce() -> None:
    assert TIPOS_ARISTA == ("jal", "j", "tabla", "indirecta")
    assert {a.tipo for a in _grafo_del_escenario().aristas} == set(TIPOS_ARISTA)


def test_un_jal_a_una_funcion_de_libreria_se_etiqueta_como_libreria_y_uno_al_juego_no() -> None:
    nombres = {s.direccion: s.nombre for s in escenario.simbolos()}
    filas = [f for f in formatear_grafo_csv(_grafo_del_escenario(), nombres).splitlines()[1:] if ",jal," in f]
    assert any(f.split(",")[3] == "VSync" and f.split(",")[5:7] == ["1", "libreria"] for f in filas)
    assert any(f.split(",")[5:7] == ["0", "juego"] for f in filas)


def test_un_jr_a_registro_es_switch_solo_si_la_funcion_tiene_tabla_propia() -> None:
    grafo = _grafo_del_escenario()
    assert escenario.D in grafo.saltos_switch
    assert escenario.G not in grafo.saltos_switch
    assert any(a.origen == escenario.G and a.tipo == "indirecta" for a in grafo.aristas)
    assert not any(a.origen == escenario.D and a.tipo == "indirecta" for a in grafo.aristas)


def test_las_rutinas_que_solo_se_llaman_por_tabla_aparecen_como_aristas_de_tabla() -> None:
    grafo = _grafo_del_escenario()
    por_tabla = {(a.origen, a.destino) for a in grafo.aristas if a.tipo == "tabla"}
    assert por_tabla == {(escenario.D, escenario.E)}
    assert comparar_llamadores(grafo, {escenario.E: 0}) == (1, ())


def test_el_orden_de_las_funciones_de_entrada_no_cambia_la_salida() -> None:
    nombres = {s.direccion: s.nombre for s in escenario.simbolos()}
    funciones = dividir_por_funcion(escenario.texto_asm())
    directa = formatear_grafo_csv(_grafo_del_escenario(funciones), nombres)
    invertida = formatear_grafo_csv(_grafo_del_escenario(list(reversed(funciones))), nombres)
    assert directa == invertida


def test_un_dato_usado_por_mas_funciones_que_el_limite_no_cuenta_como_evidencia_de_archivo() -> None:
    assert MAX_USUARIOS_DATO == 6


def test_dos_subsistemas_no_pueden_repartirse_las_mismas_direcciones() -> None:
    texto = "nombre,inicio,fin\nmotor,0x80014A00,0x80015000\naudio,0x80014F00,0x80016000\n"
    with pytest.raises(ValueError, match="audio se solapa con motor"):
        parsear_rangos(texto)


def test_una_funcion_cuyo_borrador_agota_el_tiempo_queda_registrada_y_la_corrida_sigue(
    tmp_path: Path,
) -> None:
    def lanzador(comando, segundos):  # type: ignore[no-untyped-def]
        if "func_80014AC4" in comando[-1]:
            raise TimeoutError("agotado")
        return 0, "void f(void) {\n}\n", ""

    resumen = generar_borradores(
        elegidas=escenario.simbolos()[:2],
        texto_asm=escenario.texto_asm(),
        tablas={},
        contexto="",
        salida=tmp_path / "salida",
        m2c=Path("m2c.py"),
        segundos=3,
        lanzador=lanzador,
    )
    assert (resumen.generadas, resumen.fallidas) == (1, 1)
    registro = (tmp_path / "salida" / "m2c" / "FALLIDAS.csv").read_text(encoding="utf-8")
    assert "func_80014AC4,tiempo agotado (3 s)" in registro


def test_los_documentos_de_reparto_son_acotados_y_no_filtran_rutas_ni_vocabulario_interno() -> (
    None
):

    subsistemas = (RAIZ / "docs" / "SUBSISTEMAS.md").read_text(encoding="utf-8")
    origen = (RAIZ / "docs" / "ARCHIVOS_ORIGEN.md").read_text(encoding="utf-8")
    cuerpo = subsistemas.split("## Subsistemas", 1)[1].split("## Las tres funciones gigantes", 1)[0]
    assert 6 <= len(re.findall(r"^### \d+\. ", cuerpo, flags=re.MULTILINE)) <= 15
    for texto in (subsistemas, origen):
        assert not re.search(r"[A-Za-z]:[\/]", texto)
        assert not re.search(r"TASK_|Gate [123]|ola_0|agent_0|TAREA_|\bRA-?\d\d\b", texto)

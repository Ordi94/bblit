"""Nombres de las salidas de la construccion: cada campo se deriva de la parte correcta del manifiesto."""

from psxdecomp.construccion.salidas import SalidasDeBuild, calcular_salidas
from psxdecomp.dominio import construir_rutas


def test_cada_salida_se_deriva_de_la_carpeta_de_build_de_ensamblador_o_de_fuentes_que_le_corresponde() -> (
    None
):
    rutas = construir_rutas({"build": "salida", "asm": "ensamblador", "fuentes": "codigo"})
    salidas = calcular_salidas("EJEC_001.00", rutas)
    assert salidas.ejecutable == "salida/EJEC_001.00"
    assert salidas.objetos_asm == "salida/ensamblador"
    assert salidas.objetos_c == "salida/codigo"
    assert salidas.script_enlazador == "salida/EJEC_001.ld"
    assert salidas.elf == "salida/EJEC_001.elf"
    assert salidas.mapa == "salida/EJEC_001.map"
    assert salidas.binario == "salida/EJEC_001.bin"
    assert salidas.script_gp == "salida/gp.ld"
    assert salidas.simbolos_entrada == "salida/simbolos_entrada.txt"
    assert salidas.simbolos_automaticos == (
        "salida/undefined_funcs_auto.txt",
        "salida/undefined_syms_auto.txt",
    )
    assert salidas.diff == "salida/diff"
    assert salidas.permutar == "salida/permutar"
    assert salidas.progreso_json == "salida/progreso.json"


def test_las_carpetas_de_objetos_no_se_confunden_aunque_build_asm_y_fuentes_sean_distintos() -> None:
    rutas = construir_rutas({"build": "salida", "asm": "ensamblador", "fuentes": "codigo"})
    salidas = calcular_salidas("EJEC_001.00", rutas)
    assert len({rutas.build, rutas.asm, rutas.fuentes}) == 3
    assert salidas.objetos_asm != salidas.objetos_c
    assert salidas.objetos_asm.endswith(rutas.asm)
    assert salidas.objetos_c.endswith(rutas.fuentes)
    assert isinstance(salidas, SalidasDeBuild)


def test_el_nombre_base_es_el_del_ejecutable_sin_su_ultima_extension() -> None:
    rutas = construir_rutas({})
    assert calcular_salidas("EJEC.A.01", rutas).elf == "build/EJEC.A.elf"
    assert calcular_salidas("SIN_EXTENSION", rutas).elf == "build/SIN_EXTENSION.elf"

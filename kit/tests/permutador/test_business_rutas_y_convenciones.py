"""El permutador respeta las rutas, las macros y el ejecutable que fija el manifiesto."""

import json
from pathlib import Path

import pytest
from psxdecomp.diff.comparacion import FuncionSinCError
from psxdecomp.dominio import Convenciones
from psxdecomp.permutador import busqueda as pm
from psxdecomp.permutador import estado as est
from psxdecomp.permutador import evaluacion as ev

from construccion.test_compilacion import herramientas
from permutador.ayudantes import (
    ARCHIVO,
    COMPILACION,
    CONVENCIONES,
    CONVENCIONES_PROPIAS,
    CUERPO_FUNCION,
    EJECUTABLE,
    FUNCION,
    RUTAS,
    EjecutorPermutar,
    crear_repositorio,
)


def preparar(
    raiz: Path,
    ejecutor: EjecutorPermutar,
    *,
    convenciones: Convenciones = CONVENCIONES,
    nombre: str = EJECUTABLE,
) -> ev.ObjetivoMedicion:
    return ev.preparar_medicion(
        raiz,
        FUNCION,
        herramientas(),
        Path("diff.py"),
        ejecutor,
        carpeta="salida/diff/objetivo",
        rutas=RUTAS,
        convenciones=convenciones,
        compilacion=COMPILACION,
        nombre_ejecutable=nombre,
    )


def correr(
    raiz: Path,
    ejecutor: EjecutorPermutar,
    opciones: pm.Opciones,
    *,
    convenciones: Convenciones = CONVENCIONES,
) -> pm.Resumen:
    return pm.permutar_funcion(
        raiz,
        FUNCION,
        herramientas(),
        Path("diff.py"),
        ejecutor,
        opciones=opciones,
        rutas=RUTAS,
        convenciones=convenciones,
        compilacion=COMPILACION,
        nombre_ejecutable=EJECUTABLE,
        salida=lambda aviso: None,
    )


def test_la_macro_de_no_coincidencia_del_manifiesto_es_la_que_se_define_al_compilar(tmp_path: Path) -> None:
    crear_repositorio(tmp_path, convenciones=CONVENCIONES_PROPIAS)
    ejecutor = EjecutorPermutar(lambda texto: 25)
    objetivo = preparar(tmp_path, ejecutor, convenciones=CONVENCIONES_PROPIAS)
    assert objetivo.convenciones is CONVENCIONES_PROPIAS
    ejecutor.comandos.clear()
    assert ev.evaluar(objetivo, CUERPO_FUNCION, comprobar_bytes_bajo=0) == ev.ResultadoEvaluacion(25)
    assert "-DNO_COINCIDE" in ejecutor.comandos[0]
    assert "-DNON_MATCHING" not in ejecutor.comandos[0]


def test_una_funcion_solo_en_ensamblador_no_se_permuta_con_la_macro_propia_del_proyecto(
    tmp_path: Path,
) -> None:
    crear_repositorio(tmp_path)
    (tmp_path / ARCHIVO).write_text(
        'ENSAMBLAR("ensamblador/pendientes/modulo_a", rutina_a);\n', encoding="utf-8"
    )
    ejecutor = EjecutorPermutar()
    with pytest.raises(FuncionSinCError, match="'rutina_a' sigue en ENSAMBLAR: no hay C que permutar"):
        preparar(tmp_path, ejecutor, convenciones=CONVENCIONES_PROPIAS)
    assert ejecutor.comandos == []


def test_una_funcion_solo_en_ensamblador_no_se_permuta_con_las_macros_por_defecto(tmp_path: Path) -> None:
    crear_repositorio(tmp_path)
    (tmp_path / ARCHIVO).write_text(
        'INCLUDE_ASM("ensamblador/pendientes/modulo_a", rutina_a);\n', encoding="utf-8"
    )
    with pytest.raises(FuncionSinCError, match="'rutina_a' sigue en INCLUDE_ASM"):
        preparar(tmp_path, EjecutorPermutar())


def test_el_elf_de_la_ultima_construccion_se_busca_por_el_nombre_del_ejecutable(tmp_path: Path) -> None:
    crear_repositorio(tmp_path, con_elf=False)
    (tmp_path / "salida").mkdir()
    (tmp_path / "salida" / "OTRO_002.elf").write_bytes(b"elf")
    with pytest.raises(ValueError, match="falta el ejecutable de la ultima construccion"):
        preparar(tmp_path, EjecutorPermutar())
    objetivo = preparar(tmp_path, EjecutorPermutar(), nombre="OTRO_002.00")
    assert objetivo.elf == "salida/OTRO_002.elf"


def test_sin_el_elf_de_la_ultima_construccion_no_se_mide_nada(tmp_path: Path) -> None:
    crear_repositorio(tmp_path, con_elf=False)
    ejecutor = EjecutorPermutar()
    with pytest.raises(ValueError, match="ejecute 'build' antes de permutar"):
        correr(tmp_path, ejecutor, pm.Opciones(iteraciones=3))
    assert ejecutor.comandos == []
    assert not (tmp_path / "salida" / "permutar").exists()


def test_el_archivo_de_opciones_y_el_de_simbolos_se_leen_de_las_rutas_del_manifiesto(tmp_path: Path) -> None:
    crear_repositorio(tmp_path, con_simbolos=True, valor_g=4)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "opciones_compilacion.toml").write_text(
        "[archivos.modulo_a]\ng = 32\n", encoding="utf-8"
    )
    (tmp_path / "config" / "symbols.txt").write_text(
        "rutina_a = 0x80200000; // type:func size:0x10\n", encoding="utf-8"
    )
    objetivo = preparar(tmp_path, EjecutorPermutar())
    assert objetivo.valor_g == 4
    assert objetivo.direccion == 0x80100100


def test_la_busqueda_solo_escribe_bajo_la_carpeta_de_build_del_manifiesto(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    crear_repositorio(raiz, convenciones=CONVENCIONES_PROPIAS)
    antes = {p: p.read_bytes() for p in raiz.rglob("*") if p.is_file()}
    llamadas: list[str] = []

    def puntuar(texto: str) -> int:
        llamadas.append(texto)
        return 40 if len(llamadas) <= 2 else 39

    resultado = correr(
        raiz,
        EjecutorPermutar(puntuar),
        pm.Opciones(iteraciones=12, procesos=2, semilla=5),
        convenciones=CONVENCIONES_PROPIAS,
    )
    despues = {p for p in raiz.rglob("*") if p.is_file()}
    nuevos = despues - set(antes)
    assert all(p.is_relative_to(raiz / "salida" / "permutar" / FUNCION) for p in nuevos)
    assert all(p.read_bytes() == contenido for p, contenido in antes.items())
    assert not (raiz / "build").exists() and not (raiz / "src").exists()
    assert resultado.candidato == raiz / "salida" / "permutar" / FUNCION / "mejor.c"


def test_la_carpeta_de_estado_contiene_exactamente_los_cuatro_archivos_del_formato(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    crear_repositorio(raiz)
    llamadas: list[str] = []

    def puntuar(texto: str) -> int:
        llamadas.append(texto)
        return 40 if len(llamadas) <= 2 else 39

    resultado = correr(raiz, EjecutorPermutar(puntuar), pm.Opciones(iteraciones=12, procesos=2, semilla=5))
    carpeta = raiz / "salida" / "permutar" / FUNCION
    assert est.ARCHIVOS_DEL_ESTADO == ("mejor.c", "actual.c", "estado.json", "registro.jsonl")
    assert {p.name for p in carpeta.iterdir()} == set(est.ARCHIVOS_DEL_ESTADO)
    assert resultado.puntuacion_mejor == 39
    datos = json.loads((carpeta / "estado.json").read_text(encoding="utf-8"))
    assert datos["funcion"] == FUNCION and datos["semilla"] == 5
    primera = json.loads((carpeta / "registro.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert primera["puntuacion"] == 39 and primera["mutaciones"]


def test_reanudar_sin_estado_previo_falla_aunque_la_carpeta_de_build_sea_propia(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    crear_repositorio(raiz)
    with pytest.raises(ValueError, match="no hay una busqueda anterior"):
        correr(raiz, EjecutorPermutar(), pm.Opciones(iteraciones=2, reanudar=True))
    assert not (raiz / "build").exists()

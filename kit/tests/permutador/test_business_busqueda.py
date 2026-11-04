"""Reglas de negocio de la busqueda: escalada, limites, reanudacion y fuentes intactas."""

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from psxdecomp.diff.comparacion import FuncionSinCError
from psxdecomp.permutador import analisis as an
from psxdecomp.permutador import busqueda as pm
from psxdecomp.permutador import c
from psxdecomp.permutador import estado as est
from psxdecomp.permutador import evaluacion as ev
from psxdecomp.permutador import mutaciones as mut

from construccion.test_compilacion import herramientas
from permutador.ayudantes import (
    ARCHIVO,
    ARCHIVO_C,
    COMPILACION,
    CONVENCIONES,
    CUERPO_FUNCION,
    EJECUTABLE,
    FUNCION,
    RUTAS,
    EjecutorPermutar,
    crear_repositorio,
)

CABECERA = "typedef struct Objeto {\n    s16 radio;\n    s32 valor;\n} Objeto;\n"
FUNCION_RICA = (
    "s32 rutina_a(Objeto* o, s32 x)\n{\n    s32 y;\n    y = o->radio + x;\n    o->valor = y;\n"
    "    return y + o->valor;\n}"
)


class Reloj:
    """Reloj falso que avanza una cantidad fija en cada lectura."""

    def __init__(self, paso: float) -> None:
        self.ahora = 0.0
        self.paso = paso

    def __call__(self) -> float:
        self.ahora += self.paso
        return self.ahora


def evaluador_por_temporales(cierre: int | None = None) -> pm.Evaluador:
    """Puntua 50 menos 10 por cada temporal asignado; con ``cierre`` coincide al llegar a ese numero."""

    def evaluar(texto: str, umbral: int) -> ev.ResultadoEvaluacion:
        cantidad = texto.count("tmp1 =") + texto.count("tmp2 =") + texto.count("tmp3 =")
        if cierre is not None and cantidad >= cierre:
            return ev.ResultadoEvaluacion(0, coincide=True)
        return ev.ResultadoEvaluacion(50 - 10 * cantidad)

    return evaluar


def crear_busqueda(
    tmp_path: Path,
    evaluador: pm.Evaluador,
    opciones: pm.Opciones,
    *,
    texto: str = FUNCION_RICA,
    partida: int = 50,
    reloj: Any = None,
    avisos: list[str] | None = None,
) -> pm.Busqueda:
    tabla = an.construir_tabla([CABECERA])
    base = c.analizar_funcion(texto, FUNCION, frozenset({"Objeto"}))
    carpeta = tmp_path / "estado"
    estado = est.Estado(FUNCION, "codigo/modulo_a.c", 5, partida, partida, partida)
    return pm.Busqueda(
        base,
        tabla,
        evaluador,
        estado=estado,
        carpeta=carpeta,
        opciones=opciones,
        salida=(avisos if avisos is not None else []).append,
        reloj=reloj or Reloj(0.001),
    )


# --- opciones ---------------------------------------------------------------------------------------


def test_sin_limite_alguno_la_busqueda_dura_diez_minutos_por_omision() -> None:
    assert pm.validar_opciones(pm.Opciones(procesos=4)).minutos == pm.MINUTOS_POR_OMISION
    assert pm.validar_opciones(pm.Opciones(iteraciones=5)).minutos is None
    assert pm.validar_opciones(pm.Opciones(minutos=2.5)).iteraciones is None


@pytest.mark.parametrize(
    ("opciones", "mensaje"),
    [
        (pm.Opciones(iteraciones=0), "--iteraciones"),
        (pm.Opciones(iteraciones=pm.MAX_ITERACIONES + 1), "--iteraciones"),
        (pm.Opciones(minutos=0), "--minutos"),
        (pm.Opciones(minutos=-1), "--minutos"),
        (pm.Opciones(minutos=pm.MAX_MINUTOS + 1), "--minutos"),
        (pm.Opciones(procesos=0), "--procesos"),
        (pm.Opciones(procesos=pm.MAX_PROCESOS + 1), "--procesos"),
        (pm.Opciones(semilla=-3), "--semilla"),
    ],
)
def test_las_opciones_fuera_de_rango_se_rechazan(opciones: pm.Opciones, mensaje: str) -> None:
    with pytest.raises(ValueError, match=mensaje):
        pm.validar_opciones(opciones)


def test_leer_cabeceras_toma_los_h_de_la_carpeta_de_inclusion_y_omite_los_demasiado_grandes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert pm.leer_cabeceras(tmp_path, rutas=RUTAS) == []
    (tmp_path / "cabeceras" / "psyq").mkdir(parents=True)
    (tmp_path / "cabeceras" / "a.h").write_text("A", encoding="utf-8")
    (tmp_path / "cabeceras" / "psyq" / "B.H").write_text("B", encoding="utf-8")
    (tmp_path / "cabeceras" / "c.txt").write_text("C", encoding="utf-8")
    (tmp_path / "cabeceras" / "grande.h").write_text("x" * 50, encoding="utf-8")
    monkeypatch.setattr(pm, "MAX_BYTES_FUENTE", 10)
    assert pm.leer_cabeceras(tmp_path, rutas=RUTAS) == ["A", "B"]


def test_leer_cabeceras_ignora_la_carpeta_de_inclusion_por_defecto_si_el_manifiesto_fija_otra(
    tmp_path: Path,
) -> None:
    (tmp_path / "include").mkdir()
    (tmp_path / "include" / "ajena.h").write_text("AJENA", encoding="utf-8")
    (tmp_path / "cabeceras").mkdir()
    (tmp_path / "cabeceras" / "propia.h").write_text("PROPIA", encoding="utf-8")
    assert pm.leer_cabeceras(tmp_path, rutas=RUTAS) == ["PROPIA"]


# --- resumen ----------------------------------------------------------------------------------------


def resumen(mejor: int, partida: int = 50, **cambios: Any) -> pm.Resumen:
    base = {
        "funcion": FUNCION,
        "semilla": 3,
        "procesos": 4,
        "iteraciones": 120,
        "puntuacion_partida": partida,
        "puntuacion_mejor": mejor,
        "candidato": Path("repo/build/permutar/f/mejor.c"),
        "segundos": 90.0,
    }
    return pm.Resumen(**{**base, **cambios})


def test_el_codigo_de_salida_distingue_cerrar_mejorar_y_no_mejorar() -> None:
    assert resumen(0).codigo_de_salida == 0
    assert resumen(30).codigo_de_salida == 1
    assert resumen(50).codigo_de_salida == 2


def test_el_resumen_impreso_incluye_iteraciones_puntuaciones_candidato_y_tiempo() -> None:
    texto = pm.formatear_resumen(
        resumen(30, descartadas=Counter({"regla": 2, "evaluacion": 5})), Path("repo")
    )
    assert texto.splitlines() == [
        "rutina_a: 120 iteraciones en 1.5 min (4 procesos, semilla 3)",
        "puntuacion de partida 50, mejor 30 (mejora sin cerrar)",
        "candidato: build/permutar/f/mejor.c",
        "descartadas: evaluacion 5, regla 2",
    ]
    assert "(coincide con el original)" in pm.formatear_resumen(resumen(0), Path("repo"))
    assert "(sin mejora)" in pm.formatear_resumen(resumen(50), Path("repo"))
    assert "descartadas: ninguna" in pm.formatear_resumen(resumen(50), Path("repo"))
    interrumpido = pm.formatear_resumen(resumen(50, interrumpida=True), Path("repo"))
    assert interrumpido.splitlines()[-1] == "busqueda interrumpida: reanude con --reanudar"


# --- escalada ---------------------------------------------------------------------------------------


def test_la_escalada_avanza_cuando_una_variante_mejora_y_guarda_el_mejor_con_su_registro(
    tmp_path: Path,
) -> None:
    avisos: list[str] = []
    busqueda = crear_busqueda(
        tmp_path, evaluador_por_temporales(), pm.Opciones(iteraciones=60, procesos=3), avisos=avisos
    )
    resultado = busqueda.ejecutar()
    assert resultado.puntuacion_mejor < 50
    assert resultado.codigo_de_salida == 1
    assert resultado.iteraciones == 60
    carpeta = tmp_path / "estado"
    mejor = (carpeta / "mejor.c").read_text(encoding="utf-8")
    assert mejor.startswith(f"/* Candidato del permutador: puntuacion {resultado.puntuacion_mejor} ")
    lineas = [json.loads(x) for x in (carpeta / "registro.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [x["puntuacion"] for x in lineas] == sorted((x["puntuacion"] for x in lineas), reverse=True)
    assert lineas[-1]["puntuacion"] == resultado.puntuacion_mejor
    assert all(x["mutaciones"] for x in lineas)
    assert any(a.startswith("iteracion ") for a in avisos)
    estado = est.cargar_estado(carpeta, FUNCION)
    assert estado.iteraciones == 60 and estado.puntuacion_mejor == resultado.puntuacion_mejor
    assert c.analizar_funcion(est.cargar_actual(carpeta), FUNCION, frozenset({"Objeto"}))


def test_el_barrido_halla_una_mejora_de_una_sola_mutacion_antes_de_sortear(tmp_path: Path) -> None:
    def evaluar(texto: str, umbral: int) -> ev.ResultadoEvaluacion:
        return ev.ResultadoEvaluacion(30 if "tmp1 = o->radio;" in texto else 50)

    busqueda = crear_busqueda(tmp_path, evaluar, pm.Opciones(iteraciones=300, procesos=2))
    busqueda.iniciar_barrido()
    resultado = busqueda.ejecutar()
    assert resultado.puntuacion_mejor == 30
    registro = (tmp_path / "estado" / "registro.jsonl").read_text(encoding="utf-8").splitlines()
    primera = json.loads(registro[0])
    assert primera["puntuacion"] == 30 and len(primera["mutaciones"]) == 1


def test_el_barrido_no_mide_dos_veces_el_mismo_texto_y_termina_dando_paso_al_sorteo(tmp_path: Path) -> None:
    vistos: list[str] = []

    def evaluar(texto: str, umbral: int) -> ev.ResultadoEvaluacion:
        vistos.append(texto)
        return ev.ResultadoEvaluacion(50)

    busqueda = crear_busqueda(tmp_path, evaluar, pm.Opciones(iteraciones=400, procesos=4))
    busqueda.iniciar_barrido()
    busqueda.ejecutar()
    assert len(vistos) == len(set(vistos)) > 300
    assert busqueda.barrido is None


def test_la_busqueda_se_detiene_en_cuanto_una_variante_coincide(tmp_path: Path) -> None:
    busqueda = crear_busqueda(
        tmp_path, evaluador_por_temporales(cierre=1), pm.Opciones(iteraciones=500, procesos=2)
    )
    resultado = busqueda.ejecutar()
    assert resultado.puntuacion_mejor == 0 and resultado.codigo_de_salida == 0
    assert resultado.iteraciones < 500


def test_sin_ninguna_mejora_se_reinicia_cada_doce_rondas_y_el_codigo_es_dos(tmp_path: Path) -> None:
    busqueda = crear_busqueda(
        tmp_path, lambda texto, umbral: ev.ResultadoEvaluacion(50), pm.Opciones(iteraciones=60, procesos=1)
    )
    resultado = busqueda.ejecutar()
    assert resultado.codigo_de_salida == 2
    estado = est.cargar_estado(tmp_path / "estado", FUNCION)
    assert estado.rondas_sin_mejora == 60 % pm.LIMITE_RONDAS_SIN_MEJORA
    assert estado.puntuacion_mejor == 50


def test_tras_estancarse_la_escalada_reinicia_desde_el_original_o_desde_el_mejor(tmp_path: Path) -> None:
    def evaluar(texto: str, umbral: int) -> ev.ResultadoEvaluacion:
        return ev.ResultadoEvaluacion(30 if "tmp1 =" in texto else 50)

    busqueda = crear_busqueda(tmp_path, evaluar, pm.Opciones(iteraciones=500, procesos=1))
    origenes = set()
    reiniciar = busqueda._reiniciar

    def espia(azar: Any) -> None:
        reiniciar(azar)
        origenes.add("original" if busqueda.actual is busqueda.base else "mejor")

    busqueda._reiniciar = espia  # type: ignore[method-assign]
    resultado = busqueda.ejecutar()
    assert resultado.puntuacion_mejor == 30
    assert origenes == {"original", "mejor"}


def test_las_variantes_descartadas_se_cuentan_por_motivo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def evaluar(texto: str, umbral: int) -> ev.ResultadoEvaluacion:
        return ev.ResultadoEvaluacion(None, "no compila") if "tmp1" in texto else ev.ResultadoEvaluacion(50)

    original = mut.variante_permitida
    monkeypatch.setattr(mut, "variante_permitida", lambda v, b: original(v, b) and "tmp2" not in v)
    busqueda = crear_busqueda(tmp_path, evaluar, pm.Opciones(iteraciones=80, procesos=2))
    resultado = busqueda.ejecutar()
    assert resultado.descartadas["evaluacion"] > 0
    assert resultado.descartadas["regla"] > 0
    assert resultado.iteraciones == 80


def test_una_ronda_donde_todo_se_descarta_cuenta_como_ronda_sin_mejora(tmp_path: Path) -> None:
    busqueda = crear_busqueda(
        tmp_path, lambda texto, umbral: ev.ResultadoEvaluacion(None, "no compila"), pm.Opciones(iteraciones=6)
    )
    resultado = busqueda.ejecutar()
    assert resultado.puntuacion_mejor == 50
    assert est.cargar_estado(tmp_path / "estado", FUNCION).rondas_sin_mejora == 6


def test_la_busqueda_respeta_el_limite_de_tiempo_de_la_sesion(tmp_path: Path) -> None:
    reloj = Reloj(20.0)
    busqueda = crear_busqueda(
        tmp_path,
        lambda texto, umbral: ev.ResultadoEvaluacion(50),
        pm.Opciones(minutos=1, procesos=2),
        reloj=reloj,
    )
    resultado = busqueda.ejecutar()
    assert 2 <= resultado.iteraciones <= 8


def test_el_ultimo_lote_no_pasa_del_limite_de_iteraciones(tmp_path: Path) -> None:
    busqueda = crear_busqueda(
        tmp_path, lambda texto, umbral: ev.ResultadoEvaluacion(50), pm.Opciones(iteraciones=7, procesos=3)
    )
    assert busqueda.ejecutar().iteraciones == 7


def test_una_funcion_sin_mutaciones_posibles_termina_tras_cinco_rondas_vacias(tmp_path: Path) -> None:
    busqueda = crear_busqueda(
        tmp_path,
        lambda texto, umbral: ev.ResultadoEvaluacion(50),
        pm.Opciones(iteraciones=1000, procesos=2),
        texto="void rutina_a(void)\n{\n    return;\n}",
    )
    resultado = busqueda.ejecutar()
    assert resultado.iteraciones == pm.RONDAS_VACIAS_MAXIMAS * 2
    assert resultado.puntuacion_mejor == 50


def test_nunca_se_mide_dos_veces_el_mismo_texto(tmp_path: Path) -> None:
    vistos: list[str] = []

    def evaluar(texto: str, umbral: int) -> ev.ResultadoEvaluacion:
        vistos.append(texto)
        return ev.ResultadoEvaluacion(50)

    crear_busqueda(tmp_path, evaluar, pm.Opciones(iteraciones=120, procesos=4)).ejecutar()
    assert len(vistos) == len(set(vistos))


def test_ctrl_c_guarda_el_estado_y_devuelve_un_resumen_interrumpido(tmp_path: Path) -> None:
    def evaluar(texto: str, umbral: int) -> ev.ResultadoEvaluacion:
        raise KeyboardInterrupt

    resultado = crear_busqueda(tmp_path, evaluar, pm.Opciones(iteraciones=20, procesos=2)).ejecutar()
    assert resultado.interrumpida
    assert (tmp_path / "estado" / "estado.json").is_file()


def test_la_misma_semilla_produce_la_misma_busqueda(tmp_path: Path) -> None:
    def correr(destino: str) -> list[str]:
        textos: list[str] = []

        def evaluar(texto: str, umbral: int) -> ev.ResultadoEvaluacion:
            textos.append(texto)
            return ev.ResultadoEvaluacion(50)

        crear_busqueda(tmp_path / destino, evaluar, pm.Opciones(iteraciones=30, procesos=1)).ejecutar()
        return textos

    assert correr("a") == correr("b")


def test_el_aviso_de_progreso_sale_cada_veinticinco_rondas(tmp_path: Path) -> None:
    avisos: list[str] = []
    crear_busqueda(
        tmp_path,
        lambda texto, umbral: ev.ResultadoEvaluacion(50),
        pm.Opciones(iteraciones=50, procesos=1),
        avisos=avisos,
    ).ejecutar()
    assert avisos == ["25 variantes, mejor 50", "50 variantes, mejor 50"]


# --- de punta a punta con la cadena simulada --------------------------------------------------------


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    repo = tmp_path / "repo con espacios (x)"
    crear_repositorio(repo)
    (repo / "cabeceras").mkdir()
    (repo / "cabeceras" / "tipos.h").write_text(CABECERA, encoding="utf-8")
    return repo


def correr(
    raiz: Path, ejecutor: EjecutorPermutar, opciones: pm.Opciones, avisos: list[str] | None = None
) -> pm.Resumen:
    return pm.permutar_funcion(
        raiz,
        FUNCION,
        herramientas(),
        Path("diff.py"),
        ejecutor,
        opciones=opciones,
        rutas=RUTAS,
        convenciones=CONVENCIONES,
        compilacion=COMPILACION,
        nombre_ejecutable=EJECUTABLE,
        salida=(avisos if avisos is not None else []).append,
        reloj=Reloj(0.01),
    )


def test_permutar_no_toca_la_carpeta_de_fuentes_y_deja_el_candidato_y_el_estado_en_build(
    raiz: Path,
) -> None:
    antes = (raiz / ARCHIVO).read_bytes()
    ejecutor = EjecutorPermutar(lambda texto: 40 - 5 * texto.count("tmp1 ="))
    resultado = correr(raiz, ejecutor, pm.Opciones(iteraciones=24, procesos=3, semilla=2))
    assert (raiz / ARCHIVO).read_bytes() == antes
    assert resultado.puntuacion_partida == 40
    assert resultado.candidato == raiz / "salida" / "permutar" / FUNCION / "mejor.c"
    assert resultado.candidato.is_file()
    assert resultado.semilla == 2
    guardados = {p.name for p in (raiz / "salida" / "permutar" / FUNCION).iterdir()}
    assert {"estado.json", "mejor.c", "actual.c"} <= guardados <= set(est.ARCHIVOS_DEL_ESTADO)
    assert [p.name for p in (raiz / "salida" / "diff").iterdir()] == []


def test_el_candidato_se_puede_aplicar_en_el_archivo_y_compila_de_nuevo(raiz: Path) -> None:
    ejecutor = EjecutorPermutar(lambda texto: 40 - 5 * texto.count("tmp1 ="))
    resultado = correr(raiz, ejecutor, pm.Opciones(iteraciones=30, procesos=2, semilla=4))
    candidato = resultado.candidato.read_text(encoding="utf-8").split("\n", 1)[1].rstrip("\n")
    archivo = ARCHIVO_C.replace(CUERPO_FUNCION, candidato)
    assert candidato in archivo
    assert c.analizar_funcion(candidato, FUNCION, frozenset({"Objeto"}))


def test_reanudar_continua_con_los_contadores_acumulados_y_el_mismo_estado(raiz: Path) -> None:
    ejecutor = EjecutorPermutar(lambda texto: 40 - 5 * texto.count("tmp1 ="))
    primera = correr(raiz, ejecutor, pm.Opciones(iteraciones=12, procesos=2, semilla=9))
    carpeta = raiz / "salida" / "permutar" / FUNCION
    antes = est.cargar_estado(carpeta, FUNCION)
    segunda = correr(raiz, ejecutor, pm.Opciones(iteraciones=10, procesos=2, reanudar=True))
    despues = est.cargar_estado(carpeta, FUNCION)
    assert antes.iteraciones == 12 and despues.iteraciones == 22
    assert despues.semilla == 9 == segunda.semilla
    assert segunda.iteraciones == 10
    assert despues.puntuacion_mejor <= primera.puntuacion_mejor
    assert despues.puntuacion_partida == 40


def test_reanudar_sin_busqueda_anterior_falla_con_un_mensaje(raiz: Path) -> None:
    with pytest.raises(ValueError, match="no hay una busqueda anterior"):
        correr(raiz, EjecutorPermutar(), pm.Opciones(iteraciones=2, reanudar=True))


def test_sin_reanudar_se_descarta_el_estado_anterior(raiz: Path) -> None:
    ejecutor = EjecutorPermutar(lambda texto: 40 - 5 * texto.count("tmp1 ="))
    correr(raiz, ejecutor, pm.Opciones(iteraciones=10, procesos=2, semilla=1))
    correr(raiz, ejecutor, pm.Opciones(iteraciones=4, procesos=2, semilla=2))
    estado = est.cargar_estado(raiz / "salida" / "permutar" / FUNCION, FUNCION)
    assert estado.iteraciones == 4 and estado.semilla == 2


def test_sin_semilla_se_elige_una_y_queda_registrada(raiz: Path) -> None:
    resultado = correr(raiz, EjecutorPermutar(), pm.Opciones(iteraciones=2))
    assert resultado.semilla >= 0
    assert est.cargar_estado(raiz / "salida" / "permutar" / FUNCION, FUNCION).semilla == resultado.semilla


def test_una_funcion_que_ya_coincide_no_se_busca(raiz: Path) -> None:
    ejecutor = EjecutorPermutar(lambda texto: 0)
    resultado = correr(raiz, ejecutor, pm.Opciones(iteraciones=50, procesos=4))
    assert resultado.codigo_de_salida == 0
    assert resultado.iteraciones == 0
    assert resultado.candidato.is_file()
    again = correr(raiz, ejecutor, pm.Opciones(iteraciones=50, reanudar=True))
    assert again.iteraciones == 0 and again.puntuacion_mejor == 0


def test_si_la_reescritura_no_reproduce_la_puntuacion_del_original_no_se_permuta(raiz: Path) -> None:
    llamadas: list[str] = []

    def puntuar(texto: str) -> int:
        llamadas.append(texto)
        return 40 if len(llamadas) == 1 else 41

    with pytest.raises(ValueError, match="no reproduce su puntuacion \\(40 frente a 41\\)"):
        correr(raiz, EjecutorPermutar(puntuar), pm.Opciones(iteraciones=5))


def test_si_el_c_vigente_no_se_puede_medir_se_explica_el_motivo(raiz: Path) -> None:
    with pytest.raises(ValueError, match=r"no se puede medir: CC1PSX\.EXE: termino con codigo 1"):
        correr(raiz, EjecutorPermutar(falla_si=lambda texto: True), pm.Opciones(iteraciones=5))


def test_las_funciones_que_no_se_pueden_permutar_se_rechazan_antes_de_medir(raiz: Path) -> None:
    ejecutor = EjecutorPermutar()
    (raiz / ARCHIVO).write_text(
        'INCLUDE_ASM("ensamblador/pendientes/modulo_a", rutina_a);\n', encoding="utf-8"
    )
    with pytest.raises(FuncionSinCError):
        correr(raiz, ejecutor, pm.Opciones(iteraciones=5))
    with pytest.raises(ValueError, match="--procesos"):
        correr(raiz, ejecutor, pm.Opciones(iteraciones=5, procesos=99))
    with pytest.raises(ValueError, match="identificador C"):
        pm.permutar_funcion(
            raiz,
            "../x",
            herramientas(),
            Path("diff.py"),
            ejecutor,
            opciones=pm.Opciones(iteraciones=1),
            rutas=RUTAS,
            convenciones=CONVENCIONES,
            compilacion=COMPILACION,
            nombre_ejecutable=EJECUTABLE,
        )
    assert ejecutor.comandos == []


def test_un_c_fuera_del_subconjunto_soportado_se_rechaza_con_su_causa(raiz: Path) -> None:
    (raiz / ARCHIVO).write_text(
        CABECERA + "#ifdef NON_MATCHING\n"
        "s32 rutina_a(s32 x)\n{\n    return x $ 2;\n}\n"
        '#else\nINCLUDE_ASM("ensamblador/pendientes/modulo_a", rutina_a);\n#endif\n',
        encoding="utf-8",
    )
    with pytest.raises(c.AnalisisCError, match="caracter no reconocido"):
        correr(raiz, EjecutorPermutar(), pm.Opciones(iteraciones=5))

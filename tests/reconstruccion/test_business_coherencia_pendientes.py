"""Reglas de negocio del aviso de coherencia: el comentario Pendiente contra la ultima medicion de diff."""

import json
import os
from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import cli, coherencia_pendientes, diff, fuentes_c

from .test_business_pendientes import PENDIENTE, bloque, preparar_repositorio
from .test_compilacion import herramientas_compilacion
from .test_diff import EjecutorDiff, repo_diff  # noqa: F401 - fixture reutilizada
from .test_gp import EjecutorEnlace, crear_repo_diff, herramientas_con_enlace

FUNCION = "func_80014AC4"


def escribir_medicion(raiz: Path, contenido: Any, nombre: str = FUNCION) -> Path:
    ruta = raiz / "build" / "diff" / f"{nombre}.resultado.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido if isinstance(contenido, str) else json.dumps(contenido), encoding="utf-8")
    return ruta


def medicion(puntuacion: int) -> dict[str, Any]:
    return {"funcion": FUNCION, "puntuacion": puntuacion, "maxLineas": 1024}


def avisos(raiz: Path) -> list[str]:
    texto = (raiz / "src" / "a.c").read_text(encoding="utf-8")
    return coherencia_pendientes.avisos_puntuacion_pendiente(raiz, {"src/a.c": texto})


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    preparar_repositorio(tmp_path, bloque(FUNCION, PENDIENTE))
    return tmp_path


def test_si_la_medicion_reciente_coincide_con_el_comentario_no_hay_aviso(raiz: Path) -> None:
    escribir_medicion(raiz, medicion(120))
    assert avisos(raiz) == []


def test_si_la_medicion_reciente_difiere_del_comentario_se_avisa_con_ambas_cifras(raiz: Path) -> None:
    escribir_medicion(raiz, medicion(340))
    assert avisos(raiz) == [
        "src/a.c:1 func_80014AC4: el comentario Pendiente dice 120 y la ultima medicion de diff da 340"
    ]


def test_sin_medicion_no_se_avisa_ni_se_ejecuta_diff(raiz: Path) -> None:
    assert avisos(raiz) == []
    assert not (raiz / "build").exists()


def test_una_medicion_anterior_a_la_ultima_edicion_del_c_no_es_reciente(raiz: Path) -> None:
    ruta = escribir_medicion(raiz, medicion(340))
    antes = (raiz / "src" / "a.c").stat().st_mtime - 100
    os.utime(ruta, (antes, antes))
    assert avisos(raiz) == []


@pytest.mark.parametrize(
    "contenido",
    [
        "no es json",
        "[]",
        {"funcion": "otra", "puntuacion": 340},
        {"funcion": FUNCION, "puntuacion": "340"},
        {"funcion": FUNCION, "puntuacion": -1},
        {"funcion": FUNCION, "puntuacion": True},
        {"funcion": FUNCION},
        "x" * 5000,
    ],
)
def test_una_medicion_ilegible_o_de_otra_funcion_se_ignora(raiz: Path, contenido: Any) -> None:
    escribir_medicion(raiz, contenido)
    assert avisos(raiz) == []


def test_un_bloque_sin_linea_pendiente_no_genera_aviso(tmp_path: Path) -> None:
    preparar_repositorio(tmp_path, bloque(FUNCION, ""))
    escribir_medicion(tmp_path, medicion(340))
    assert avisos(tmp_path) == []


def test_un_archivo_ausente_o_un_nombre_invalido_se_omiten(tmp_path: Path) -> None:
    texto = bloque("f" * 65, PENDIENTE)
    preparar_repositorio(tmp_path, texto)
    assert coherencia_pendientes.avisos_puntuacion_pendiente(tmp_path, {"src/a.c": texto}) == []
    assert coherencia_pendientes.avisos_puntuacion_pendiente(tmp_path, {"src/no_existe.c": texto}) == []


def test_puntuacion_pendiente_lee_el_numero_del_primer_comentario() -> None:
    bloques = fuentes_c.bloques_no_coincidentes(bloque(FUNCION, PENDIENTE))
    assert fuentes_c.puntuacion_pendiente(bloques[0]) == 120
    sin = fuentes_c.bloques_no_coincidentes(bloque(FUNCION, "int x;\n"))
    assert fuentes_c.puntuacion_pendiente(sin[0]) is None


def test_progreso_imprime_el_aviso_por_la_salida_de_errores_sin_fallar(
    raiz: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    escribir_medicion(raiz, medicion(340))
    assert cli.main(["progreso"], {}, raiz) in (0, 1)
    assert "aviso: src/a.c:1 func_80014AC4: el comentario Pendiente dice 120" in capsys.readouterr().err


def test_diff_deja_la_puntuacion_informada_y_el_limite_para_el_aviso(repo_diff: Any) -> None:  # noqa: F811
    diff.comparar_funcion(
        repo_diff, "func_80036204", herramientas_compilacion(), Path("diff.py"), EjecutorDiff(0)
    )
    datos = json.loads((repo_diff / diff.ruta_resultado("func_80036204")).read_text(encoding="utf-8"))
    assert datos == {"funcion": "func_80036204", "puntuacion": 0, "maxLineas": 1024}


def leer_medicion_guardada(raiz: Path, funcion: str) -> dict[str, Any]:
    ruta = raiz / diff.ruta_resultado(funcion)
    datos: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
    return datos


def test_diff_guarda_la_puntuacion_de_asm_differ_si_los_bytes_no_son_iguales(repo_diff: Any) -> None:  # noqa: F811
    resultado = diff.comparar_funcion(
        repo_diff, "func_NM", herramientas_compilacion(), Path("diff.py"), EjecutorDiff(505)
    )
    datos = leer_medicion_guardada(repo_diff, "func_NM")
    assert (resultado.puntuacion, datos["puntuacion"]) == (505, 505)


def test_diff_guarda_la_puntuacion_enlazada_si_los_bytes_difieren(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    resultado = diff.comparar_funcion(
        tmp_path,
        "func_80036204",
        herramientas_con_enlace(),
        Path("diff.py"),
        EjecutorEnlace(505, difiere=True),
    )
    datos = leer_medicion_guardada(tmp_path, "func_80036204")
    assert resultado.bytes_iguales is False
    assert (resultado.puntuacion, datos["puntuacion"]) == (505, 505)


def test_diff_guarda_cero_si_los_bytes_son_iguales_aunque_asm_differ_puntue_mas(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    resultado = diff.comparar_funcion(
        tmp_path, "func_80036204", herramientas_con_enlace(), Path("diff.py"), EjecutorEnlace(5)
    )
    datos = leer_medicion_guardada(tmp_path, "func_80036204")
    assert (resultado.bytes_iguales, resultado.puntuacion_asm) == (True, 5)
    assert (resultado.puntuacion, datos["puntuacion"]) == (0, 0)

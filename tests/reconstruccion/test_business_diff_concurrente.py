"""Reglas de negocio de ``diff`` y ``probar`` con varias ejecuciones simultaneas.

Dos comparaciones sobre funciones del mismo archivo C comparten el nombre del objeto candidato; si
compartieran carpeta, una leeria el objeto de la otra y daria una puntuacion falsa. Cada ejecucion
trabaja en una carpeta exclusiva y solo deja la puntuacion final, escrita de forma atomica.
"""

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import diff, variantes
from tools.reconstruccion.infraestructura import ProcesoError

from .test_compilacion import SALIDA_OBJDUMP, herramientas_compilacion
from .test_diff import ASM_FUNCION
from .test_variantes import EjecutorVariantes, crear_repo, crear_variantes

PUNTUACIONES = {"func_A": 111, "func_B": 222}


class EjecutorConcurrente:
    """
    Ejecutor falso seguro entre hilos que reproduce la carrera de dos comparaciones.

    La compilacion escribe en el objeto candidato el nombre de la funcion que se compara; antes de
    puntuar, ambos hilos esperan en una barrera (las dos compilaciones ya terminaron) y luego cada
    uno lee su candidato: la puntuacion sale de lo que lee, igual que ``asm-differ`` puntua el objeto
    que encuentra. Con una carpeta compartida el segundo escritor gana y un hilo lee el de otro.
    """

    def __init__(self) -> None:
        self.local = threading.local()
        self.barrera = threading.Barrier(2, timeout=10)
        self.carpetas: set[str] = set()

    def __call__(self, comando: Any, directorio: Path, timeout_s: int) -> str:
        if "--run-assembler" in comando:
            candidato = directorio / comando[comando.index("-o") + 1]
            candidato.write_text(self.local.funcion, encoding="utf-8")
            self.carpetas.add(candidato.parent.name)
        elif "--format=json" in comando:
            self.barrera.wait()
            leido = (directorio / comando[comando.index("--file") + 1]).read_text(encoding="utf-8")
            return json.dumps({"current_score": PUNTUACIONES[leido]})
        elif "--format=plain" in comando:
            return "TARGET   CURRENT\nfila\n"
        return ""


@pytest.fixture
def repo_dos_funciones(tmp_path: Path) -> Path:
    raiz = tmp_path / "repo"
    (raiz / "src").mkdir(parents=True)
    (raiz / "src" / "code_a.c").write_text(
        "#ifdef NON_MATCHING\ns32 func_A(s32 x)\n{\n    return x;\n}\n#else\n"
        'INCLUDE_ASM("asm/nonmatchings/code_a", func_A);\n#endif\n'
        "#ifdef NON_MATCHING\ns32 func_B(s32 x)\n{\n    return x + 1;\n}\n#else\n"
        'INCLUDE_ASM("asm/nonmatchings/code_a", func_B);\n#endif\n',
        encoding="utf-8",
    )
    (raiz / "asm" / "nonmatchings" / "code_a").mkdir(parents=True)
    for nombre in PUNTUACIONES:
        (raiz / "asm" / "nonmatchings" / "code_a" / f"{nombre}.s").write_text(ASM_FUNCION, encoding="utf-8")
    return raiz


def comparar(raiz: Path, ejecutor: EjecutorConcurrente, funcion: str) -> diff.ResultadoDiff:
    ejecutor.local.funcion = funcion
    return diff.comparar_funcion(raiz, funcion, herramientas_compilacion(), Path("diff.py"), ejecutor)


def test_dos_diff_concurrentes_sobre_funciones_del_mismo_archivo_dan_cada_uno_su_puntuacion(
    repo_dos_funciones: Path,
) -> None:
    ejecutor = EjecutorConcurrente()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futuros = {f: pool.submit(comparar, repo_dos_funciones, ejecutor, f) for f in PUNTUACIONES}
    resultados = {f: futuro.result() for f, futuro in futuros.items()}
    assert {f: r.puntuacion for f, r in resultados.items()} == PUNTUACIONES
    assert len(ejecutor.carpetas) == 2


def test_cada_diff_deja_su_propia_puntuacion_guardada_y_ningun_intermedio(repo_dos_funciones: Path) -> None:
    ejecutor = EjecutorConcurrente()
    with ThreadPoolExecutor(max_workers=2) as pool:
        for futuro in [pool.submit(comparar, repo_dos_funciones, ejecutor, f) for f in PUNTUACIONES]:
            futuro.result()
    carpeta = repo_dos_funciones / "build" / "diff"
    assert sorted(p.name for p in carpeta.iterdir()) == [
        "func_A.resultado.json",
        "func_B.resultado.json",
    ]
    for funcion, puntos in PUNTUACIONES.items():
        guardado = json.loads((repo_dos_funciones / diff.ruta_resultado(funcion)).read_text(encoding="utf-8"))
        assert (guardado["funcion"], guardado["puntuacion"]) == (funcion, puntos)


def test_la_carpeta_de_trabajo_es_exclusiva_aunque_el_proceso_sea_el_mismo(tmp_path: Path) -> None:
    with (
        diff.carpeta_de_trabajo(tmp_path, "func_X") as una,
        diff.carpeta_de_trabajo(tmp_path, "func_X") as otra,
    ):
        assert una != otra
        assert una.startswith(f"build/diff/func_X-{os.getpid()}-")
        assert (tmp_path / una).is_dir() and (tmp_path / otra).is_dir()
    assert list((tmp_path / "build" / "diff").iterdir()) == []


def test_si_la_comparacion_falla_la_carpeta_de_trabajo_se_elimina(repo_dos_funciones: Path) -> None:
    def ejecutor_roto(comando: Any, directorio: Path, timeout_s: int) -> str:
        if "--run-assembler" in comando:
            raise ProcesoError("maspsx fallo")
        return ""

    with pytest.raises(ProcesoError, match="maspsx fallo"):
        diff.comparar_funcion(
            repo_dos_funciones, "func_A", herramientas_compilacion(), Path("diff.py"), ejecutor_roto
        )
    assert list((repo_dos_funciones / "build" / "diff").iterdir()) == []


def test_el_resultado_se_escribe_completo_o_no_se_escribe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    diff.guardar_resultado(tmp_path, "func_A", 10, 1024)
    anterior = (tmp_path / diff.ruta_resultado("func_A")).read_text(encoding="utf-8")

    def fallar(origen: Any, destino: Any) -> None:
        raise OSError("disco lleno")

    monkeypatch.setattr(diff.os, "replace", fallar)
    with pytest.raises(OSError, match="disco lleno"):
        diff.guardar_resultado(tmp_path, "func_A", 999, 1024)
    assert (tmp_path / diff.ruta_resultado("func_A")).read_text(encoding="utf-8") == anterior
    assert sorted(p.name for p in (tmp_path / "build" / "diff").iterdir()) == ["func_A.resultado.json"]


def test_probar_no_deja_carpetas_de_trabajo_y_no_pisa_la_de_diff(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    crear_repo(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["mejor.c", "peor.c"])
    variantes.probar_variantes(
        raiz,
        "func_80036204",
        carpeta,
        herramientas_compilacion(),
        script_diff=Path("diff.py"),
        ejecutar=EjecutorVariantes(secciones=SALIDA_OBJDUMP),
    )
    assert list((raiz / "build" / "diff").iterdir()) == []

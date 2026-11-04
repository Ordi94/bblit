"""Ordenes diff, probar y permutar: reciben del manifiesto lo que deben y devuelven el codigo correcto.

La comparacion, el banco de variantes y la busqueda se sustituyen por dobles: esta capa solo debe
resolver las herramientas del lock, pasar las secciones del manifiesto y traducir el resultado a texto
y codigo de retorno.
"""

from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from psxdecomp.cli import comandos, main, resumir_comparacion
from psxdecomp.construccion import compilacion
from psxdecomp.diff import comparacion, variantes
from psxdecomp.diff.comparacion import ResultadoDiff
from psxdecomp.diff.variantes import ResultadoVariante
from psxdecomp.dominio import Compilacion, Convenciones, Rutas
from psxdecomp.permutador import busqueda

from ordenes.ayudantes import Escenario, Registro, crear_escenario

HERRAMIENTAS = object()
SCRIPT = Path("herramientas/asm-differ/diff.py")


@pytest.fixture
def escenario(tmp_path: Path) -> Escenario:
    return crear_escenario(tmp_path)


@pytest.fixture
def llamadas(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Sustituye la resolucion de herramientas y registra con que se las invoca."""
    registro: dict[str, Any] = {}

    def resolver_compilacion(lock: Any, raiz_toolchain: Path, python: str) -> Any:
        registro["compilacion"] = (sorted(lock), raiz_toolchain.name, python)
        return HERRAMIENTAS

    def resolver(lock: Any, raiz_toolchain: Path, componente: str, alias: str) -> Path:
        registro["script"] = (componente, alias)
        return SCRIPT

    monkeypatch.setattr(compilacion, "resolver_herramientas_compilacion", resolver_compilacion)
    monkeypatch.setattr(comandos, "resolver_herramienta", resolver)
    return registro


def ejecutar(escenario: Escenario, *argv: str) -> int:
    return main(list(argv), escenario.entorno, Registro(), raiz=escenario.raiz)


def resultado_diff(**cambios: Any) -> ResultadoDiff:
    datos: dict[str, Any] = {
        "funcion": "rutina_a",
        "archivo": "codigo/modulo_a.c",
        "puntuacion": 0,
        "texto": "cols",
    }
    datos.update(cambios)
    return ResultadoDiff(**datos)


def test_diff_pasa_las_secciones_del_manifiesto_y_el_nombre_del_ejecutable(
    escenario: Escenario,
    llamadas: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    recibido: dict[str, Any] = {}

    def comparar(
        raiz: Path, funcion: str, herramientas: Any, script: Path, ejecutar_: Any, **kwargs: Any
    ) -> Any:
        recibido.update(raiz=raiz, funcion=funcion, herramientas=herramientas, script=script, **kwargs)
        return resultado_diff()

    monkeypatch.setattr(comparacion, "comparar_funcion", comparar)
    assert ejecutar(escenario, "diff", "rutina_a") == 0
    assert capsys.readouterr().out == "cols\nrutina_a (codigo/modulo_a.c): puntuacion 0\n"
    assert recibido["funcion"] == "rutina_a"
    assert recibido["herramientas"] is HERRAMIENTAS
    assert recibido["script"] == SCRIPT
    assert recibido["nombre_ejecutable"] == "PRUEBA.EXE"
    assert isinstance(recibido["rutas"], Rutas)
    assert recibido["rutas"].fuentes == "codigo"
    assert isinstance(recibido["convenciones"], Convenciones)
    assert isinstance(recibido["compilacion"], Compilacion)
    assert llamadas["script"] == ("asm-differ", "diff")
    assert llamadas["compilacion"][:2] == (["binutils-mipsel"], "herramientas")


def test_diff_devuelve_uno_si_la_funcion_no_coincide(
    escenario: Escenario,
    llamadas: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(comparacion, "comparar_funcion", lambda *a, **k: resultado_diff(puntuacion=40))
    assert ejecutar(escenario, "diff", "rutina_a") == 1
    assert capsys.readouterr().out.endswith("rutina_a (codigo/modulo_a.c): puntuacion 40\n")
    assert "script" in llamadas


def test_resumir_comparacion_solo_da_el_veredicto_si_los_bytes_no_son_iguales() -> None:
    assert resumir_comparacion(resultado_diff(puntuacion=12)) == [
        "rutina_a (codigo/modulo_a.c): puntuacion 12"
    ]


def test_resumir_comparacion_avisa_de_la_medicion_parcial_antes_del_veredicto() -> None:
    lineas = resumir_comparacion(resultado_diff(puntuacion=3, truncado=True))
    assert lineas[0].startswith("aviso: asm-differ corto el desensamblado")
    assert lineas[1] == "rutina_a (codigo/modulo_a.c): puntuacion 3"


def test_resumir_comparacion_anade_la_nota_de_referencias_numericas_si_los_bytes_coinciden() -> None:
    lineas = resumir_comparacion(
        resultado_diff(puntuacion=0, bytes_iguales=True, referencias_numericas=2, puntuacion_asm=14)
    )
    assert lineas == [
        "nota: 2 referencias en forma numerica (asm-differ puntua 14)",
        "rutina_a (codigo/modulo_a.c): puntuacion 0 (coincide en bytes)",
    ]


def test_probar_imprime_la_tabla_y_sale_con_cero_solo_si_la_mejor_variante_coincide(
    escenario: Escenario,
    llamadas: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    recibido: dict[str, Any] = {}

    def probar(raiz: Path, funcion: str, carpeta: Path, herramientas: Any, **kwargs: Any) -> Any:
        recibido.update(funcion=funcion, carpeta=carpeta, **kwargs)
        return [ResultadoVariante("a.c", 0), ResultadoVariante("b.c", 7)]

    monkeypatch.setattr(variantes, "probar_variantes", probar)
    assert ejecutar(escenario, "probar", "rutina_a", "variantes") == 0
    assert capsys.readouterr().out == "variante  puntuacion\na.c       0\nb.c       7\n"
    assert recibido["carpeta"] == Path("variantes")
    assert recibido["script_diff"] == SCRIPT
    assert recibido["nombre_ejecutable"] == "PRUEBA.EXE"
    assert recibido["rutas"].fuentes == "codigo"
    monkeypatch.setattr(variantes, "probar_variantes", lambda *a, **k: [ResultadoVariante("c.c", 9)])
    assert ejecutar(escenario, "probar", "rutina_a", "variantes") == 1
    assert "script" in llamadas


@pytest.mark.parametrize(("mejor", "esperado"), [(0, 0), (30, 1), (40, 2)])
def test_permutar_devuelve_cero_si_coincide_uno_si_mejora_y_dos_si_no_mejora(
    escenario: Escenario,
    llamadas: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mejor: int,
    esperado: int,
) -> None:
    recibido: dict[str, Any] = {}

    def permutar(
        raiz: Path, funcion: str, herramientas: Any, script: Path, ejecutar_: Any, **kwargs: Any
    ) -> Any:
        recibido.update(raiz=raiz, funcion=funcion, script=script, **kwargs)
        return busqueda.Resumen(
            funcion=funcion,
            semilla=7,
            procesos=2,
            iteraciones=10,
            puntuacion_partida=40,
            puntuacion_mejor=mejor,
            candidato=raiz / "build" / "permutar" / funcion / "mejor.c",
            segundos=60.0,
            descartadas=Counter(),
        )

    monkeypatch.setattr(busqueda, "permutar_funcion", permutar)
    argumentos = ["permutar", "rutina_a", "--minutos", "2", "--procesos", "2", "--semilla", "7", "--reanudar"]
    assert ejecutar(escenario, *argumentos) == esperado
    salida = capsys.readouterr().out
    assert "rutina_a: 10 iteraciones en 1.0 min (2 procesos, semilla 7)" in salida
    assert "candidato: build/permutar/rutina_a/mejor.c" in salida
    opciones = recibido["opciones"]
    assert (
        opciones.iteraciones,
        opciones.minutos,
        opciones.procesos,
        opciones.semilla,
        opciones.reanudar,
    ) == (
        None,
        2.0,
        2,
        7,
        True,
    )
    assert recibido["nombre_ejecutable"] == "PRUEBA.EXE"
    assert recibido["rutas"].fuentes == "codigo"
    assert "script" in llamadas

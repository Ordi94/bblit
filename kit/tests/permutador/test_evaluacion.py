"""Medicion de variantes de una funcion con las rutas, convenciones y cadena de un proyecto."""

import dataclasses
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from psxdecomp.diff.comparacion import FuncionSinCError
from psxdecomp.permutador import evaluacion as ev

from construccion.test_compilacion import herramientas
from permutador.ayudantes import (
    ARCHIVO,
    ARCHIVO_C,
    COMPILACION,
    CONVENCIONES,
    CUERPO_FUNCION,
    DIRECCION,
    EJECUTABLE,
    ELF,
    FUNCION,
    RUTAS,
    EjecutorPermutar,
    crear_repositorio,
)


def preparar(raiz: Path, ejecutor: EjecutorPermutar) -> ev.ObjetivoMedicion:
    return ev.preparar_medicion(
        raiz,
        FUNCION,
        herramientas(),
        Path("diff.py"),
        ejecutor,
        carpeta="salida/diff/objetivo",
        rutas=RUTAS,
        convenciones=CONVENCIONES,
        compilacion=COMPILACION,
        nombre_ejecutable=EJECUTABLE,
    )


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    repo = tmp_path / "repo con espacios (x)"
    crear_repositorio(repo, con_simbolos=True, valor_g=8)
    return repo


def test_preparar_medicion_localiza_la_definicion_y_reune_las_opciones_del_archivo(raiz: Path) -> None:
    objetivo = preparar(raiz, EjecutorPermutar())
    assert objetivo.archivo == ARCHIVO
    assert objetivo.texto_archivo[objetivo.inicio : objetivo.fin] == CUERPO_FUNCION
    assert objetivo.valor_g == 8
    assert objetivo.direccion == DIRECCION
    assert objetivo.retornos == 1
    assert objetivo.max_lineas == 1024
    assert objetivo.elf == ELF
    assert objetivo.rutas is RUTAS and objetivo.convenciones is CONVENCIONES
    assert objetivo.compilacion is COMPILACION
    assert (raiz / objetivo.objetivo).is_file()


def test_sin_configuracion_el_archivo_se_compila_con_g_cero_y_sin_direccion(tmp_path: Path) -> None:
    crear_repositorio(tmp_path / "r")
    objetivo = preparar(tmp_path / "r", EjecutorPermutar())
    assert objetivo.valor_g == 0
    assert objetivo.direccion is None


def test_preparar_medicion_rechaza_lo_que_no_se_puede_permutar(tmp_path: Path) -> None:
    sin_elf = tmp_path / "a"
    crear_repositorio(sin_elf, con_elf=False)
    with pytest.raises(ValueError, match="ejecute 'build' antes de permutar"):
        preparar(sin_elf, EjecutorPermutar())
    solo_ensamblador = tmp_path / "b"
    crear_repositorio(solo_ensamblador)
    (solo_ensamblador / ARCHIVO).write_text(
        'INCLUDE_ASM("ensamblador/pendientes/modulo_a", rutina_a);\n', encoding="utf-8"
    )
    with pytest.raises(FuncionSinCError, match="no hay C que permutar"):
        preparar(solo_ensamblador, EjecutorPermutar())
    ejecutor = EjecutorPermutar()
    with pytest.raises(ValueError, match="identificador C"):
        ev.preparar_medicion(
            sin_elf,
            "../x",
            herramientas(),
            Path("diff.py"),
            ejecutor,
            carpeta="salida/diff/x",
            rutas=RUTAS,
            convenciones=CONVENCIONES,
            compilacion=COMPILACION,
            nombre_ejecutable=EJECUTABLE,
        )
    assert ejecutor.comandos == []


def test_texto_del_archivo_sustituye_solo_la_definicion(raiz: Path) -> None:
    objetivo = preparar(raiz, EjecutorPermutar())
    nueva = "s32 rutina_a(s32 x)\n{\n    return 0;\n}"
    assert ev.texto_del_archivo(objetivo, nueva) == ARCHIVO_C.replace(CUERPO_FUNCION, nueva)


def test_evaluar_compila_con_la_macro_y_el_g_del_archivo_y_devuelve_la_puntuacion(raiz: Path) -> None:
    ejecutor = EjecutorPermutar(lambda texto: 25)
    objetivo = preparar(raiz, ejecutor)
    ejecutor.comandos.clear()
    resultado = ev.evaluar(objetivo, CUERPO_FUNCION, comprobar_bytes_bajo=25)
    assert resultado == ev.ResultadoEvaluacion(25)
    nombres = [Path(c[0]).name for c in ejecutor.comandos]
    assert nombres == ["CPPPSX.EXE", "CC1PSX.EXE", "py", "objdump.exe", "py"]
    assert "-DNON_MATCHING" in ejecutor.comandos[0]
    assert "-Icabeceras" in ejecutor.comandos[0]
    assert "-G8" in ejecutor.comandos[1]
    carpeta = ejecutor.comandos[0][-1].rsplit("/", 1)[0]
    assert carpeta.startswith("salida/diff/permutar-rutina_a-")
    assert not (raiz / carpeta).exists()


def test_una_variante_que_puntua_cero_coincide(raiz: Path) -> None:
    objetivo = preparar(raiz, EjecutorPermutar(lambda texto: 0))
    assert ev.evaluar(objetivo, CUERPO_FUNCION, comprobar_bytes_bajo=10) == ev.ResultadoEvaluacion(
        0, coincide=True
    )


def test_una_variante_que_no_compila_se_descarta_con_la_primera_linea_del_error(raiz: Path) -> None:
    ejecutor = EjecutorPermutar(falla_si=lambda texto: "roto" in texto)
    objetivo = preparar(raiz, ejecutor)
    roto = CUERPO_FUNCION.replace("return y;", "return roto;")
    assert ev.evaluar(objetivo, roto, comprobar_bytes_bajo=10) == ev.ResultadoEvaluacion(
        None, "CC1PSX.EXE: termino con codigo 1"
    )
    assert ev.evaluar(objetivo, CUERPO_FUNCION, comprobar_bytes_bajo=10).puntuacion == 40


def test_un_fallo_sin_mensaje_se_descarta_con_un_motivo_generico(raiz: Path) -> None:
    ejecutor = EjecutorPermutar()
    objetivo = preparar(raiz, ejecutor)

    def falla_en_blanco(*args: object) -> str:
        raise ValueError("\n  \n")

    objetivo_sin_mensaje = dataclasses.replace(objetivo, ejecutar=falla_en_blanco)
    resultado = ev.evaluar(objetivo_sin_mensaje, CUERPO_FUNCION, comprobar_bytes_bajo=10)
    assert resultado == ev.ResultadoEvaluacion(None, "fallo sin mensaje")


def test_una_variante_que_no_define_la_funcion_se_descarta(raiz: Path) -> None:
    ejecutor = EjecutorPermutar(define_funcion=False)
    objetivo = preparar(raiz, ejecutor)
    assert ev.evaluar(objetivo, CUERPO_FUNCION, comprobar_bytes_bajo=10) == ev.ResultadoEvaluacion(
        None, "la variante no define rutina_a"
    )


def test_una_medicion_truncada_se_descarta(raiz: Path) -> None:
    filas = [{"current": {"mnemonic": "..."}}]
    objetivo = preparar(raiz, EjecutorPermutar(filas=filas))
    resultado = ev.evaluar(objetivo, CUERPO_FUNCION, comprobar_bytes_bajo=10)
    assert resultado.puntuacion is None and "truncada" in (resultado.motivo or "")


def test_una_salida_ilegible_de_asm_differ_se_descarta(raiz: Path) -> None:
    objetivo = preparar(raiz, EjecutorPermutar(lambda texto: -1))
    resultado = ev.evaluar(objetivo, CUERPO_FUNCION, comprobar_bytes_bajo=10)
    assert resultado.puntuacion is None
    assert resultado.motivo == "asm-differ no informo una puntuacion valida"


@pytest.mark.parametrize(
    ("iguales", "esperado"),
    [
        (True, ev.ResultadoEvaluacion(0, coincide=True)),
        (False, ev.ResultadoEvaluacion(5)),
        (None, ev.ResultadoEvaluacion(None, "la variante no enlaza en la direccion de la funcion")),
    ],
)
def test_una_variante_mejor_que_el_umbral_se_compara_por_bytes_contra_el_elf_del_ejecutable(
    raiz: Path, monkeypatch: pytest.MonkeyPatch, iguales: bool | None, esperado: ev.ResultadoEvaluacion
) -> None:
    llamadas: list[tuple[int, str]] = []

    def comparar(*args: object, **kwargs: object) -> bool | None:
        llamadas.append((kwargs["direccion"], kwargs["elf"]))  # type: ignore[arg-type]
        return iguales

    monkeypatch.setattr(ev, "bytes_coinciden", comparar)
    objetivo = preparar(raiz, EjecutorPermutar(lambda texto: 5))
    assert ev.evaluar(objetivo, CUERPO_FUNCION, comprobar_bytes_bajo=10) == esperado
    assert llamadas == [(DIRECCION, ELF)]


def test_una_variante_que_no_mejora_el_umbral_no_se_compara_por_bytes(
    raiz: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def comparar(*args: object, **kwargs: object) -> bool | None:
        raise AssertionError("no debia compararse")

    monkeypatch.setattr(ev, "bytes_coinciden", comparar)
    objetivo = preparar(raiz, EjecutorPermutar(lambda texto: 5))
    assert ev.evaluar(objetivo, CUERPO_FUNCION, comprobar_bytes_bajo=5) == ev.ResultadoEvaluacion(5)


def test_sin_direccion_conocida_no_se_compara_por_bytes(tmp_path: Path) -> None:
    crear_repositorio(tmp_path / "r")
    objetivo = preparar(tmp_path / "r", EjecutorPermutar(lambda texto: 5))
    assert ev.evaluar(objetivo, CUERPO_FUNCION, comprobar_bytes_bajo=10) == ev.ResultadoEvaluacion(5)


def test_varias_mediciones_a_la_vez_no_se_mezclan_y_no_dejan_carpetas(raiz: Path) -> None:
    ejecutor = EjecutorPermutar(len)
    objetivo = preparar(raiz, ejecutor)
    textos = [CUERPO_FUNCION.replace("y = x + 1;", f"y = x + {n};" + " " * n) for n in range(2, 14)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        resultados = list(pool.map(lambda t: ev.evaluar(objetivo, t, comprobar_bytes_bajo=0), textos))
    assert [r.puntuacion for r in resultados] == [len(ev.texto_del_archivo(objetivo, t)) for t in textos]
    sobrantes = [p.name for p in (raiz / "salida" / "diff").iterdir() if p.name != "objetivo"]
    assert sobrantes == []

"""Opciones de compilacion por archivo y reexportacion del banco de variantes (``probar``).

El banco de variantes vive en el kit y sus reglas se prueban alli; estas pruebas comprueban que el
enlace con el manifiesto de este proyecto compone las rutas y la cadena de compilacion correctas.
"""

from pathlib import Path
from typing import Any

import pytest
from psxdecomp.construccion import infraestructura as infra_kit

from .ayudantes_diff import ASM_FUNCION, EjecutorDiff
from .ayudantes_infra import REFERENCIA
from .ayudantes_variantes import EjecutorVariantes, crear_repo, crear_variantes, escribir_opciones
from .proyecto_real import comp, diff, dominio, infra, variantes
from .test_compilacion import (
    SALIDA_OBJDUMP,
    SCRIPT_MIXTO,
    EjecutorC,
    herramientas_base,
    herramientas_compilacion,
    preparar_construccion,
)

# ---------------------------------------------------------------- opciones por archivo


def test_valores_g_por_archivo_acepta_la_forma_documentada() -> None:
    datos = {"archivos": {"uno": {"g": 8}, "dos": {}, "tres": {"g": 0}, "cuatro": {"g": 64}}}
    assert dominio.valores_g_por_archivo(datos) == {"uno": 8, "dos": 0, "tres": 0, "cuatro": 64}
    assert dominio.valores_g_por_archivo({}) == {}


@pytest.mark.parametrize(
    ("datos", "mensaje"),
    [
        ([], "solo se admiten las tablas 'archivos', 'enlace' y 'datos_pequenos'"),
        ({"otra": {}}, "solo se admiten las tablas 'archivos', 'enlace' y 'datos_pequenos'"),
        ({"archivos": []}, "'archivos' debe ser una tabla"),
        ({"archivos": {"1malo": {"g": 8}}}, "archivo '1malo' no valido"),
        ({"archivos": {"a-b": {"g": 8}}}, "archivo 'a-b' no valido"),
        ({"archivos": {"uno": 8}}, "archivo 'uno' no valido"),
        ({"archivos": {"uno": {"x": 1}}}, "'uno' tiene la clave desconocida 'x'"),
        ({"archivos": {"uno": {"g": True}}}, r"'uno\.g' debe ser un entero entre 0 y 64"),
        ({"archivos": {"uno": {"g": "8"}}}, r"'uno\.g' debe ser un entero entre 0 y 64"),
        ({"archivos": {"uno": {"g": -1}}}, r"'uno\.g' debe ser un entero entre 0 y 64"),
        ({"archivos": {"uno": {"g": 65}}}, r"'uno\.g' debe ser un entero entre 0 y 64"),
    ],
)
def test_valores_g_por_archivo_rechaza_entradas_no_confiables(datos: Any, mensaje: Any) -> None:
    with pytest.raises(ValueError, match=mensaje):
        dominio.valores_g_por_archivo(datos)


def test_leer_valores_g(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert infra.leer_valores_g(tmp_path) == {}
    escribir_opciones(tmp_path, "[archivos.a]\ng = 8\n")
    assert infra.leer_valores_g(tmp_path) == {"a": 8}
    escribir_opciones(tmp_path, "[archivos.a\n")
    with pytest.raises(ValueError, match=r"opciones_compilacion\.toml no es TOML valido"):
        infra.leer_valores_g(tmp_path)
    escribir_opciones(tmp_path, "[archivos.a]\ng = 99\n")
    with pytest.raises(ValueError, match="entero entre 0 y 64"):
        infra.leer_valores_g(tmp_path)
    monkeypatch.setattr(infra_kit, "MAX_BYTES_REFERENCIA", 3)
    with pytest.raises(ValueError, match="excede el tamano permitido"):
        infra.leer_valores_g(tmp_path)


def test_comando_compilar_lleva_el_valor_de_g() -> None:
    assert comp.comando_compilar(Path("CC1PSX.EXE"), "a.i", "a.s", 8)[1:4] == ["-quiet", "-O2", "-G8"]
    assert comp.comando_compilar(Path("CC1PSX.EXE"), "a.i", "a.s")[3] == "-G0"
    for malo in (-1, 65, True, "8"):
        with pytest.raises(ValueError, match="entero entre 0 y 64"):
            comp.comando_compilar(Path("CC1PSX.EXE"), "a.i", "a.s", malo)


def comando_de_compilador(ejecutor: EjecutorC) -> list[str]:
    return next(c for c in ejecutor.comandos if Path(c[0]).name == "CC1PSX.EXE")


def test_compilar_fuente_pasa_g_y_compilar_archivo_acepta_rutas_absolutas(tmp_path: Path) -> None:
    preparar_construccion(tmp_path, SCRIPT_MIXTO)
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP.replace("0000001d", "00000000"))
    comp.compilar_fuente(
        tmp_path, "src/a.c", "build/src/a.c.o", herramientas_compilacion(), ejecutor, valor_g=8
    )
    assert "-G8" in comando_de_compilador(ejecutor)
    fuera = tmp_path.parent / f"{tmp_path.name}_variante.c"
    fuera.write_text("int x;\n", encoding="utf-8")
    otro = EjecutorC()
    comp.compilar_archivo(
        tmp_path, str(fuera), "build/diff/v.c.o", herramientas_compilacion(), otro, exigir_solo_texto=False
    )
    assert otro.comandos[0][-3] == str(fuera)
    with pytest.raises(FileNotFoundError, match="falta el fuente"):
        comp.compilar_archivo(
            tmp_path, str(fuera) + "x", "build/diff/v.c.o", herramientas_compilacion(), otro
        )


def test_construir_mixto_aplica_el_g_solo_al_archivo_que_lo_declara(tmp_path: Path) -> None:
    preparar_construccion(tmp_path, SCRIPT_MIXTO)
    (tmp_path / "src" / "b.c").write_text("int y;\n", encoding="utf-8")
    (tmp_path / infra.SCRIPT_ENLAZADOR).write_text(
        "main\n{\n    build/src/a.c.o(.text);\n    build/src/b.c.o(.text);\n}\n", encoding="utf-8"
    )
    escribir_opciones(tmp_path, "[archivos.a]\ng = 8\n")
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP.replace("0000001d", "00000000"))
    comp.construir_mixto(tmp_path, REFERENCIA, herramientas_base(), herramientas_compilacion, ejecutor)
    gs = [c[3] for c in ejecutor.comandos if Path(c[0]).name == "CC1PSX.EXE"]
    assert gs == ["-G8", "-G0"]


# ---------------------------------------------------------------- probar_variantes (reexportacion)


def test_probar_variantes_ordena_y_aisla_los_fallos_de_cada_variante(tmp_path: Path) -> None:
    raiz = tmp_path / "repo con espacios"
    crear_repo(raiz)
    escribir_opciones(raiz, "[archivos.code_a]\ng = 8\n")
    carpeta = crear_variantes(tmp_path / "v", ["peor.c", "mejor.c", "rota.c", "ilegible.c"])
    ejecutor = EjecutorVariantes(secciones=SALIDA_OBJDUMP)
    resultados = variantes.probar_variantes(
        raiz,
        "func_80036204",
        carpeta,
        herramientas_compilacion(),
        script_diff=Path("diff.py"),
        ejecutar=ejecutor,
    )
    assert [(r.nombre, r.puntuacion) for r in resultados] == [
        ("mejor.c", 0),
        ("peor.c", 120),
        ("ilegible.c", None),
        ("rota.c", None),
    ]
    assert resultados[3].error == "CC1PSX.EXE: termino con codigo 33"
    assert resultados[2].error == "asm-differ no devolvio JSON valido"
    gs = {c[3] for c in ejecutor.comandos if Path(c[0]).name == "CC1PSX.EXE"}
    assert gs == {"-G8"}
    ensamblados = [c for c in ejecutor.comandos if Path(c[0]).name == "as.exe"]
    assert len(ensamblados) == 1, "el objetivo se ensambla una sola vez"
    assert not (raiz / "src" / "mejor.c").exists()


# ---------------------------------------------------------------- diff usa el g del archivo


def test_diff_compila_con_el_g_declarado_para_el_archivo(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    (raiz / "src").mkdir(parents=True)
    (raiz / "src" / "code_a.c").write_text(
        "s32 func_80036204(s32 x)\n{\n    return x;\n}\n", encoding="utf-8"
    )
    (raiz / "asm" / "matchings" / "code_a").mkdir(parents=True)
    (raiz / "asm" / "matchings" / "code_a" / "func_80036204.s").write_text(ASM_FUNCION, encoding="utf-8")
    escribir_opciones(raiz, "[archivos.code_a]\ng = 4\n")
    ejecutor = EjecutorDiff(0)
    diff.comparar_funcion(raiz, "func_80036204", herramientas_compilacion(), Path("diff.py"), ejecutor)
    assert "-G4" in comando_de_compilador(ejecutor)

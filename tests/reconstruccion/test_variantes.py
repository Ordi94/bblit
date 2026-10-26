"""Opciones de compilacion por archivo y banco de variantes (``probar``)."""

import json
from pathlib import Path
from typing import Any, ClassVar

import pytest
from tools.reconstruccion import compilacion as comp
from tools.reconstruccion import diff, dominio, variantes
from tools.reconstruccion import infraestructura as infra
from tools.reconstruccion.infraestructura import ProcesoError
from tools.reconstruccion.variantes import ResultadoVariante

from .test_compilacion import (
    SALIDA_OBJDUMP,
    SCRIPT_MIXTO,
    EjecutorC,
    herramientas_base,
    herramientas_compilacion,
    preparar_construccion,
)
from .test_diff import ASM_FUNCION, EjecutorDiff
from .test_infraestructura import REFERENCIA

# ---------------------------------------------------------------- opciones por archivo


def test_valores_g_por_archivo_acepta_la_forma_documentada() -> None:
    datos = {"archivos": {"uno": {"g": 8}, "dos": {}, "tres": {"g": 0}, "cuatro": {"g": 64}}}
    assert dominio.valores_g_por_archivo(datos) == {"uno": 8, "dos": 0, "tres": 0, "cuatro": 64}
    assert dominio.valores_g_por_archivo({}) == {}


@pytest.mark.parametrize(
    ("datos", "mensaje"),
    [
        ([], "solo se admite la tabla 'archivos'"),
        ({"otra": {}}, "solo se admite la tabla 'archivos'"),
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


def escribir_opciones(raiz: Path, texto: str) -> None:
    (raiz / "config").mkdir(parents=True, exist_ok=True)
    (raiz / infra.OPCIONES_COMPILACION).write_text(texto, encoding="utf-8")


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
    monkeypatch.setattr(infra, "MAX_BYTES_REFERENCIA", 3)
    with pytest.raises(ValueError, match="excede el tamano permitido"):
        infra.leer_valores_g(tmp_path)


def test_comando_compilar_lleva_el_valor_de_g() -> None:
    assert comp.comando_compilar(Path("CC1PSX.EXE"), "a.i", "a.s", 8)[1:4] == ["-quiet", "-O2", "-G8"]
    assert comp.comando_compilar(Path("CC1PSX.EXE"), "a.i", "a.s")[3] == "-G0"
    for malo in (-1, 65, True, "8"):
        with pytest.raises(ValueError, match="entero entre 0 y 64"):
            comp.comando_compilar(Path("CC1PSX.EXE"), "a.i", "a.s", malo)  # type: ignore[arg-type]


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


# ---------------------------------------------------------------- listar y formatear


def crear_variantes(carpeta: Path, nombres: list[str]) -> Path:
    carpeta.mkdir(exist_ok=True)
    for nombre in nombres:
        (carpeta / nombre).write_text("int x;\n", encoding="utf-8")
    return carpeta


def test_listar_variantes_ordena_y_solo_toma_archivos_c(tmp_path: Path) -> None:
    carpeta = crear_variantes(tmp_path / "v", ["b.c", "a.c", "nota.txt"])
    (carpeta / "sub.c").mkdir()
    assert [p.name for p in variantes.listar_variantes(carpeta)] == ["a.c", "b.c"]


def test_listar_variantes_rechaza_carpetas_y_nombres_inutilizables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(FileNotFoundError, match="la carpeta de variantes no existe"):
        variantes.listar_variantes(tmp_path / "no_existe")
    with pytest.raises(ValueError, match=r"no contiene archivos .c"):
        variantes.listar_variantes(crear_variantes(tmp_path / "vacia", ["nota.txt"]))
    with pytest.raises(ValueError, match=r"nombre de variante no valido: 'a b.c'"):
        variantes.listar_variantes(crear_variantes(tmp_path / "malo", ["a b.c"]))
    grande = crear_variantes(tmp_path / "grande", ["a.c", "b.c", "c.c"])
    monkeypatch.setattr(variantes, "MAX_VARIANTES", 2)
    with pytest.raises(ValueError, match="hay mas de 2 variantes"):
        variantes.listar_variantes(grande)
    monkeypatch.setattr(variantes, "MAX_VARIANTES", 200)
    monkeypatch.setattr(variantes, "MAX_BYTES_VARIANTE", 3)
    with pytest.raises(ValueError, match=r"la variante 'a.c' excede el tamano permitido"):
        variantes.listar_variantes(grande)


def test_ordenar_resultados_deja_al_final_las_que_fallaron_y_desempata_por_nombre() -> None:
    resultados = [
        ResultadoVariante("e.c", None, "no compila"),
        ResultadoVariante("b.c", 20),
        ResultadoVariante("c.c", 0),
        ResultadoVariante("a.c", 20),
    ]
    assert [r.nombre for r in variantes.ordenar_resultados(resultados)] == ["c.c", "a.c", "b.c", "e.c"]


def test_formatear_tabla_alinea_las_columnas() -> None:
    tabla = variantes.formatear_tabla(
        [ResultadoVariante("larga_variante.c", 0), ResultadoVariante("b.c", None, "no compila")]
    )
    assert tabla.splitlines() == [
        "variante          puntuacion",
        "larga_variante.c  0",
        "b.c               error: no compila",
    ]


# ---------------------------------------------------------------- probar_variantes


class EjecutorVariantes(EjecutorC):
    """Compila y puntua con puntuaciones por variante; una variante 'rota' no compila."""

    PUNTUACIONES: ClassVar[dict[str, int]] = {"mejor.c": 0, "peor.c": 120}

    def __call__(self, comando: Any, directorio: Any, timeout_s: Any) -> Any:
        salida = super().__call__(comando, directorio, timeout_s)
        nombre = Path(comando[0]).name
        if nombre == "CC1PSX.EXE" and "rota" in comando[-3]:
            raise ProcesoError("CC1PSX.EXE: termino con codigo 33\nparse error")
        if "--format=json" in comando:
            variante = comando[comando.index("--file") + 1].split("probar.")[1].removesuffix(".o")
            if variante == "ilegible.c":
                return "no es json"
            return json.dumps({"current_score": self.PUNTUACIONES[variante]})
        return salida


def crear_repo(raiz: Path) -> None:
    (raiz / "src").mkdir(parents=True)
    (raiz / "src" / "code_a.c").write_text(
        'INCLUDE_ASM("asm/nonmatchings/code_a", func_80036204);\n', encoding="utf-8"
    )
    (raiz / "asm" / "nonmatchings" / "code_a").mkdir(parents=True)
    (raiz / "asm" / "nonmatchings" / "code_a" / "func_80036204.s").write_text(ASM_FUNCION, encoding="utf-8")


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


def test_probar_variantes_valida_la_funcion_y_exige_que_figure_en_src(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    crear_repo(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["mejor.c"])
    ejecutor = EjecutorVariantes()
    for funcion, mensaje in (
        ("../x", "identificador C"),
        ("func_nada", "no figura en ningun archivo de src/"),
    ):
        with pytest.raises(ValueError, match=mensaje):
            variantes.probar_variantes(
                raiz,
                funcion,
                carpeta,
                herramientas_compilacion(),
                script_diff=Path("d.py"),
                ejecutar=ejecutor,
            )
    assert ejecutor.comandos == []


def test_un_mensaje_de_error_vacio_se_resume() -> None:
    assert variantes._primera_linea("") == "fallo sin mensaje"
    assert variantes._primera_linea("\n\n x" + "y" * 300).startswith("x")
    assert len(variantes._primera_linea("z" * 500)) == variantes.MAX_CARACTERES_ERROR


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

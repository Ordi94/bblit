"""Banco de variantes: listado, ordenamiento, tabla y comparacion con las rutas de un proyecto."""

from pathlib import Path

import pytest
from psxdecomp.diff import variantes
from psxdecomp.diff.variantes import ResultadoVariante

from construccion.test_compilacion import herramientas

from .ayudantes_variantes import (
    EjecutorVariantes,
    EjecutorVariantesEnlace,
    crear_repo,
    crear_variantes,
    herramientas_con_enlace,
    probar,
)
from .test_enlace_diff import preparar_elf


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


def test_formatear_tabla_alinea_las_columnas_y_anota_bytes_iguales_y_truncado() -> None:
    tabla = variantes.formatear_tabla(
        [
            ResultadoVariante("larga_variante.c", 0),
            ResultadoVariante("parecida.c", 70, None, True),
            ResultadoVariante("distinta.c", 70, None, False),
            ResultadoVariante("cortada.c", 0, truncado=True),
            ResultadoVariante("b.c", None, "no compila"),
        ]
    )
    assert tabla.splitlines() == [
        "variante          puntuacion",
        "larga_variante.c  0",
        "parecida.c        70 (bytes iguales)",
        "distinta.c        70",
        "cortada.c         0 (medicion truncada)",
        "b.c               error: no compila",
    ]


def test_un_mensaje_de_error_vacio_se_resume_y_se_acota() -> None:
    assert variantes._primera_linea("") == "fallo sin mensaje"
    assert variantes._primera_linea("\n\n x" + "y" * 300).startswith("x")
    assert len(variantes._primera_linea("z" * 500)) == variantes.MAX_CARACTERES_ERROR


def test_probar_variantes_ordena_y_aisla_los_fallos_de_cada_variante(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto con espacios"
    crear_repo(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["peor.c", "mejor.c", "rota.c", "ilegible.c", "disco.c"])
    ejecutor = EjecutorVariantes()
    resultados = probar(raiz, carpeta, ejecutor)
    assert [(r.nombre, r.puntuacion) for r in resultados] == [
        ("mejor.c", 0),
        ("peor.c", 120),
        ("disco.c", None),
        ("ilegible.c", None),
        ("rota.c", None),
    ]
    errores = {r.nombre: r.error for r in resultados}
    assert errores["rota.c"] == "CC1PSX.EXE: termino con codigo 33"
    assert errores["ilegible.c"] == "asm-differ no devolvio JSON valido"
    assert errores["disco.c"] == "disco lleno"
    ensamblados = [c for c in ejecutor.comandos if Path(c[0]).name == "as.exe"]
    assert len(ensamblados) == 1, "el objetivo se ensambla una sola vez"
    assert not (raiz / "codigo" / "mejor.c").exists(), "las variantes no se copian a los fuentes"


def test_probar_variantes_marca_como_error_la_variante_que_no_define_la_funcion(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["peor.c", "otra.c", "mejor.c", "vacia.c"])
    ejecutor = EjecutorVariantes()
    resultados = probar(raiz, carpeta, ejecutor)
    assert [(r.nombre, r.puntuacion, r.error) for r in resultados] == [
        ("mejor.c", 0, None),
        ("peor.c", 120, None),
        ("otra.c", None, "la variante no define rutina_a"),
        ("vacia.c", None, "la variante no define rutina_a"),
    ]
    assert variantes.formatear_tabla(resultados).splitlines()[-2:] == [
        "otra.c    error: la variante no define rutina_a",
        "vacia.c   error: la variante no define rutina_a",
    ]
    assert len([c for c in ejecutor.comandos if "--format=json" in c]) == 2


def test_probar_variantes_valida_la_funcion_y_exige_que_figure_en_los_fuentes(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["mejor.c"])
    ejecutor = EjecutorVariantes()
    for funcion, mensaje in (
        ("../x", "identificador C"),
        ("rutina_nada", "no figura en ningun archivo de codigo/"),
    ):
        with pytest.raises(ValueError, match=mensaje):
            probar(raiz, carpeta, ejecutor, funcion=funcion)
    assert ejecutor.comandos == []


def test_probar_variantes_marca_los_bytes_iguales_si_el_enlace_los_confirma(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz, simbolos=True)
    preparar_elf(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["peor.c", "mejor.c"])
    resultados = probar(raiz, carpeta, EjecutorVariantesEnlace(), herramientas_c=herramientas_con_enlace())
    assert [(r.nombre, r.puntuacion, r.bytes_iguales) for r in resultados] == [
        ("mejor.c", 0, None),
        ("peor.c", 120, True),
    ]
    assert all(r.coincide for r in resultados)


def test_probar_variantes_sin_enlazador_deja_los_bytes_sin_decidir(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz, simbolos=True)
    carpeta = crear_variantes(tmp_path / "v", ["peor.c"])
    resultados = probar(raiz, carpeta, EjecutorVariantes(), herramientas_c=herramientas())
    assert resultados == [ResultadoVariante("peor.c", 120, None, None, False)]
    assert not resultados[0].coincide

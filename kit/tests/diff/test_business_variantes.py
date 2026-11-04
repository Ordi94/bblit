"""Reglas de negocio del banco de variantes: ranking honesto, limites de entrada y manifiesto respetado."""

from pathlib import Path
from typing import ClassVar

import pytest
from psxdecomp.diff import comparacion as diff
from psxdecomp.diff import variantes
from psxdecomp.diff.variantes import ResultadoVariante
from psxdecomp.dominio import construir_compilacion, construir_convenciones

from .ayudantes_variantes import (
    EjecutorVariantes,
    EjecutorVariantesEnlace,
    crear_repo,
    crear_variantes,
    escribir_opciones,
    herramientas_con_enlace,
    probar,
)
from .test_enlace_diff import preparar_elf


class EjecutorTruncando(EjecutorVariantes):
    """Una variante llega exactamente al limite de filas y otra queda una por debajo."""

    PUNTUACIONES: ClassVar[dict[str, int]] = {"cortada.c": 0, "completa.c": 0}
    FILAS: ClassVar[dict[str, int]] = {
        "cortada.c": diff.LIMITE_MINIMO_LINEAS,
        "completa.c": diff.LIMITE_MINIMO_LINEAS - 1,
    }


# --- orden y desempate -------------------------------------------------------------------------


def test_a_igual_puntuacion_manda_el_nombre_de_la_variante() -> None:
    resultados = [ResultadoVariante(n, 30) for n in ("c.c", "a.c", "b.c")]
    assert [r.nombre for r in variantes.ordenar_resultados(resultados)] == ["a.c", "b.c", "c.c"]


def test_una_variante_con_bytes_iguales_va_antes_que_otra_de_menor_puntuacion_que_no_coincide() -> None:
    resultados = [ResultadoVariante("a.c", 50, None, False), ResultadoVariante("b.c", 70, None, True)]
    assert [r.nombre for r in variantes.ordenar_resultados(resultados)] == ["b.c", "a.c"]


def test_las_variantes_con_error_van_al_final_aunque_su_nombre_sea_menor() -> None:
    resultados = [ResultadoVariante("a.c", None, "no compila"), ResultadoVariante("z.c", 9999)]
    assert [r.nombre for r in variantes.ordenar_resultados(resultados)] == ["z.c", "a.c"]


def test_una_variante_truncada_no_gana_a_una_completa_peor_puntuada() -> None:
    resultados = [ResultadoVariante("a.c", 0, truncado=True), ResultadoVariante("b.c", 40)]
    ordenados = variantes.ordenar_resultados(resultados)
    assert [r.nombre for r in ordenados] == ["b.c", "a.c"]
    assert ordenados[0].coincide is False


# --- coincidencia ------------------------------------------------------------------------------


def test_un_resultado_coincide_con_puntuacion_cero_o_con_bytes_iguales() -> None:
    assert ResultadoVariante("a.c", 0).coincide is True
    assert ResultadoVariante("a.c", 70, None, True).coincide is True
    assert ResultadoVariante("a.c", 70, None, False).coincide is False
    assert ResultadoVariante("a.c", 70, None, None).coincide is False


def test_un_resultado_truncado_nunca_coincide_aunque_puntue_cero_o_tenga_bytes_iguales() -> None:
    assert not ResultadoVariante("a.c", 0, truncado=True).coincide
    assert not ResultadoVariante("c.c", 50, bytes_iguales=True, truncado=True).coincide


def test_una_variante_truncada_con_puntuacion_cero_no_se_reporta_como_coincidente(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["cortada.c", "completa.c"])
    resultados = probar(raiz, carpeta, EjecutorTruncando())
    assert [(r.nombre, r.puntuacion, r.truncado, r.coincide) for r in resultados] == [
        ("completa.c", 0, False, True),
        ("cortada.c", 0, True, False),
    ]
    assert variantes.formatear_tabla(resultados).splitlines() == [
        "variante    puntuacion",
        "completa.c  0",
        "cortada.c   0 (medicion truncada)",
    ]


def test_la_unica_variante_que_no_define_la_funcion_no_deja_mejor_candidata(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["vacia.c"])
    resultados = probar(raiz, carpeta, EjecutorVariantes())
    assert resultados == [ResultadoVariante("vacia.c", None, "la variante no define rutina_a")]
    assert not resultados[0].coincide


def test_una_variante_de_otra_funcion_no_se_puntua_contra_el_original(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["otra.c"])
    ejecutor = EjecutorVariantes()
    resultados = probar(raiz, carpeta, ejecutor)
    assert resultados[0].puntuacion is None and resultados[0].bytes_iguales is None
    assert not [c for c in ejecutor.comandos if "--format=json" in c]


def test_la_puntuacion_cero_no_consulta_el_enlace_por_bytes(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz, simbolos=True)
    preparar_elf(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["mejor.c"])
    ejecutor = EjecutorVariantesEnlace()
    resultados = probar(raiz, carpeta, ejecutor, herramientas_c=herramientas_con_enlace())
    assert resultados[0].bytes_iguales is None
    assert not [c for c in ejecutor.comandos if Path(c[0]).name in ("ld.exe", "objcopy.exe")]


def test_bytes_distintos_tras_el_enlace_no_hacen_coincidir_a_una_variante_con_puntuacion(
    tmp_path: Path,
) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz, simbolos=True)
    preparar_elf(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["peor.c"])
    ejecutor = EjecutorVariantesEnlace(difiere=True)
    resultados = probar(raiz, carpeta, ejecutor, herramientas_c=herramientas_con_enlace())
    assert (resultados[0].bytes_iguales, resultados[0].coincide) == (False, False)


# --- limites de entrada ------------------------------------------------------------------------


def test_la_carpeta_acepta_exactamente_el_maximo_de_variantes_y_rechaza_una_mas(tmp_path: Path) -> None:
    nombres = [f"v{n:03d}.c" for n in range(variantes.MAX_VARIANTES)]
    carpeta = crear_variantes(tmp_path / "v", nombres)
    assert len(variantes.listar_variantes(carpeta)) == variantes.MAX_VARIANTES
    (carpeta / "extra.c").write_text("int x;\n", encoding="utf-8")
    with pytest.raises(ValueError, match=f"hay mas de {variantes.MAX_VARIANTES} variantes"):
        variantes.listar_variantes(carpeta)


def test_una_variante_acepta_exactamente_el_tamano_maximo_y_rechaza_un_byte_mas(tmp_path: Path) -> None:
    carpeta = crear_variantes(tmp_path / "v", [])
    (carpeta / "justa.c").write_bytes(b"x" * variantes.MAX_BYTES_VARIANTE)
    assert [p.name for p in variantes.listar_variantes(carpeta)] == ["justa.c"]
    (carpeta / "grande.c").write_bytes(b"x" * (variantes.MAX_BYTES_VARIANTE + 1))
    with pytest.raises(ValueError, match=r"la variante 'grande.c' excede el tamano permitido"):
        variantes.listar_variantes(carpeta)


def test_el_nombre_de_variante_admite_hasta_65_caracteres_con_la_extension(tmp_path: Path) -> None:
    carpeta = crear_variantes(tmp_path / "v", ["a" * 63 + ".c"])
    assert len(variantes.listar_variantes(carpeta)) == 1
    otra = crear_variantes(tmp_path / "w", ["a" * 64 + ".c"])
    with pytest.raises(ValueError, match="nombre de variante no valido"):
        variantes.listar_variantes(otra)


@pytest.mark.parametrize("nombre", ["a;b.c", "a b.c", "-a.c", ".oculta.c", "a$b.c", "ñ.c"])
def test_el_nombre_de_variante_solo_admite_caracteres_simples(tmp_path: Path, nombre: str) -> None:
    carpeta = crear_variantes(tmp_path / "v", [nombre])
    with pytest.raises(ValueError, match="nombre de variante no valido"):
        variantes.listar_variantes(carpeta)


def test_un_error_largo_de_una_variante_se_acota_a_su_primera_linea() -> None:
    mensaje = "\n\n  primera " + "x" * 400 + "\nsegunda"
    resumen = variantes._primera_linea(mensaje)
    assert resumen.startswith("primera") and "segunda" not in resumen
    assert len(resumen) == variantes.MAX_CARACTERES_ERROR


# --- rutas y convenciones propias del proyecto ----------------------------------------------------


def comandos_del_compilador(ejecutor: EjecutorVariantes) -> list[list[str]]:
    return [c for c in ejecutor.comandos if Path(c[0]).name == "CC1PSX.EXE"]


def test_el_g_del_archivo_se_lee_de_la_ruta_de_opciones_que_declara_el_manifiesto(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz)
    escribir_opciones(raiz, "[archivos.modulo_a]\ng = 8\n")
    carpeta = crear_variantes(tmp_path / "v", ["peor.c", "mejor.c"])
    ejecutor = EjecutorVariantes()
    probar(raiz, carpeta, ejecutor)
    assert {c[3] for c in comandos_del_compilador(ejecutor)} == {"-G8"}


def test_sin_opciones_declaradas_las_variantes_se_compilan_con_g_cero(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["mejor.c"])
    ejecutor = EjecutorVariantes()
    probar(raiz, carpeta, ejecutor)
    assert {c[3] for c in comandos_del_compilador(ejecutor)} == {"-G0"}


def test_un_g_sobre_el_tope_de_las_convenciones_se_rechaza_antes_de_compilar(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz)
    escribir_opciones(raiz, "[archivos.modulo_a]\ng = 8\n")
    carpeta = crear_variantes(tmp_path / "v", ["mejor.c"])
    ejecutor = EjecutorVariantes()
    with pytest.raises(ValueError, match="entero entre 0 y 4"):
        probar(raiz, carpeta, ejecutor, convenciones=construir_convenciones({"max_valor_g": 4}))
    assert ejecutor.comandos == []


def test_la_cadena_de_compilacion_del_manifiesto_manda_sobre_la_del_kit(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["mejor.c"])
    ejecutor = EjecutorVariantes()
    compilacion = construir_compilacion({"version_aspsx": "2.67", "opciones_compilador": ["-quiet", "-O1"]})
    probar(raiz, carpeta, ejecutor, compilacion=compilacion)
    assert comandos_del_compilador(ejecutor)[0][1:3] == ["-quiet", "-O1"]
    maspsx = [c for c in ejecutor.comandos if "--run-assembler" in c and any("probar." in a for a in c)]
    assert maspsx and "--aspsx-version=2.67" in maspsx[0]


def test_la_macro_de_intentos_del_proyecto_decide_que_funciones_existen(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz)
    (raiz / "codigo" / "modulo_a.c").write_text(
        "#ifdef NO_COINCIDE\ns32 rutina_a(s32 x)\n{\n    return x;\n}\n#endif\n", encoding="utf-8"
    )
    carpeta = crear_variantes(tmp_path / "v", ["mejor.c"])
    convenciones = construir_convenciones({"macro_no_coincidente": "NO_COINCIDE"})
    with pytest.raises(ValueError, match="solo existe bajo NO_COINCIDE"):
        probar(raiz, carpeta, EjecutorVariantes(), convenciones=convenciones)
    sin_la_macro = construir_convenciones({"macro_no_coincidente": "OTRA_MACRO"})
    assert probar(raiz, carpeta, EjecutorVariantes(), convenciones=sin_la_macro)[0].puntuacion == 0


def test_las_variantes_no_se_buscan_en_la_carpeta_de_fuentes_por_defecto(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz)
    (raiz / "src").mkdir()
    (raiz / "src" / "otro.c").write_text(
        'INCLUDE_ASM("asm/nonmatchings/otro", rutina_a);\n', encoding="utf-8"
    )
    carpeta = crear_variantes(tmp_path / "v", ["mejor.c"])
    resultados = probar(raiz, carpeta, EjecutorVariantes())
    assert resultados[0].puntuacion == 0


def test_la_direccion_de_la_funcion_se_toma_de_los_simbolos_del_manifiesto_y_el_elf_de_su_build(
    tmp_path: Path,
) -> None:
    raiz = tmp_path / "proyecto"
    crear_repo(raiz, simbolos=True)
    preparar_elf(raiz)
    carpeta = crear_variantes(tmp_path / "v", ["peor.c"])
    ejecutor = EjecutorVariantesEnlace()
    probar(raiz, carpeta, ejecutor, herramientas_c=herramientas_con_enlace())
    enlaces = [c for c in ejecutor.comandos if Path(c[0]).name == "ld.exe"]
    assert enlaces and "-Ttext=0x801000F0" in enlaces[0]
    consultas = [c[2] for c in ejecutor.comandos if Path(c[0]).name == "objdump.exe" and c[1] == "-t"]
    assert "salida/EJEC_001.elf" in consultas

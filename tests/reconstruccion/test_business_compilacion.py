"""Reglas de negocio del build mixto C + asm: particion por subsistema, fuentes versionadas y ciclo real."""

import re
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from tools.reconstruccion import cli, dominio, progreso
from tools.reconstruccion.fuentes_c import EstadoFuncion, analizar_fuentes
from tools.reconstruccion.infraestructura import leer_valores_g, listar_fuentes_c

from .test_business_reconstruccion import RAIZ_REPO, SHA256_ORIGINAL, entorno_real, sha256

VARIANTE_BUENA = """#include "common.h"

typedef struct Ranura {
    s32 dato;
    u32 marca;
} Ranura;

Ranura* func_80036204(u8* base, s32 paso, s32 total)
{
    u8* p;
    u8* fin;

    p = base;
    fin = p + total;
    while (p < fin) {
        if (((Ranura*)p)->marca & 1) {
            ((Ranura*)p)->marca = 0;
            ((Ranura*)p)->dato = 0;
            return (Ranura*)p;
        }
        p = base + paso;
        base = p;
    }
    return 0;
}
"""
COINCIDENTES = ("func_8002FA38", "func_8002FB18", "func_80036204", "func_8001CE64", "func_80030D60")
NO_COINCIDENTES = ("func_8002F990", "func_80035244")
INICIO_JUEGO = 0x80014AC4
FIN_JUEGO = 0x80045DA0


@pytest.fixture(scope="module")
def estados() -> Any:
    return analizar_fuentes(listar_fuentes_c(RAIZ_REPO))


@pytest.fixture(scope="module")
def configuracion() -> Any:
    return yaml.safe_load((RAIZ_REPO / "config" / "splat.yaml").read_text(encoding="utf-8"))


def plano(estados: Any) -> dict[str, EstadoFuncion]:
    return {nombre: estado for archivo in estados.values() for nombre, estado in archivo.items()}


def subsegmentos(configuracion: Any) -> list[list[Any]]:
    return [s for s in configuracion["segments"][0]["subsegments"] if isinstance(s, list)]


def direccion(desplazamiento: int) -> int:
    return 0x80014A00 + desplazamiento - 0x800


def test_splat_reparte_el_codigo_del_juego_en_archivos_por_subsistema(configuracion: Any) -> None:
    sub = subsegmentos(configuracion)
    c = [s for s in sub if s[1] == "c"]
    assert len(c) == 25
    assert direccion(c[0][0]) == INICIO_JUEGO
    assert [s[0] for s in c] == sorted(s[0] for s in c)
    asm_final = [s for s in sub if s[1] == "asm"][-1]
    assert direccion(asm_final[0]) == FIN_JUEGO
    nombres = [s[2] for s in c]
    assert len(set(nombres)) == len(nombres)
    assert not any(nombre.startswith("code_") for nombre in nombres)
    assert sorted(p.stem for p in (RAIZ_REPO / "src").glob("*.c")) == sorted(nombres)
    assert configuracion["options"]["subalign"] == 4
    assert configuracion["options"]["disassemble_all"] is True
    assert configuracion["options"]["auto_decompile_empty_functions"] is False


def test_cada_corte_cae_en_el_inicio_de_una_funcion_y_figura_en_la_propuesta(configuracion: Any) -> None:
    simbolos = progreso.leer_simbolos((RAIZ_REPO / "config" / "symbols.txt").read_text(encoding="utf-8"))
    inicios = {f.direccion for f in simbolos}
    propuesta = (RAIZ_REPO / "docs" / "ARCHIVOS_ORIGEN.md").read_text(encoding="utf-8")
    for desplazamiento, tipo, nombre in (s[:3] for s in subsegmentos(configuracion) if s[1] == "c"):
        assert tipo == "c"
        assert direccion(desplazamiento) in inicios, nombre
        assert f"`src/{nombre}.c`" in propuesta, nombre


def test_los_cortes_descartados_se_documentan_con_su_razon() -> None:
    texto = (RAIZ_REPO / "docs" / "DESCOMPILACION.md").read_text(encoding="utf-8")
    for descartado in (
        "graficos_y_gte_2",
        "logica_de_niveles_4",
        "graficos_y_gte_11",
        "arranque_y_bucle_principal`",
    ):
        assert descartado in texto, descartado


def test_el_parche_de_simbolos_esta_retirado(configuracion: Any) -> None:
    assert not (RAIZ_REPO / "config" / "simbolos_adicionales.txt").exists()
    assert configuracion["options"]["symbol_addrs_path"] == [
        "config/symbols.txt",
        "build/simbolos_entrada.txt",
    ]


def test_los_datos_y_el_rodata_por_archivo_siguen_el_orden_de_direcciones_y_nombran_un_archivo(
    configuracion: Any,
) -> None:
    sub = subsegmentos(configuracion)
    nombres_c = {s[2] for s in sub if s[1] == "c"}
    inicios = [s[0] for s in sub]
    assert inicios == sorted(inicios)
    con_punto = [s for s in sub if s[1] in (".rodata", ".data")]
    assert {s[2] for s in con_punto if s[1] == ".rodata"} == {
        "camara_y_bucle_logico",
        "gestion_y_dibujo_de_objetos",
        "menus_e_interfaz",
        "audio_xa_y_spu",
        "cargador_de_niveles_y_cd",
    }
    assert [(s[1], s[2]) for s in con_punto if s[1] == ".data"] == [(".data", "tarjeta_de_memoria")]
    assert {s[2] for s in con_punto} <= nombres_c
    compartida = [s for s in sub if s[1] == "data" and s[2] == "tablas_compartidas"]
    assert [direccion(s[0]) for s in compartida] == [0x8005E35C]


def test_la_tabla_compartida_ocupa_exactamente_las_37_entradas_del_despachador(configuracion: Any) -> None:
    datos = [s for s in subsegmentos(configuracion) if s[1] == "data"]
    inicio = next(direccion(s[0]) for s in datos if s[2] == "tablas_compartidas")
    siguiente = min(direccion(s[0]) for s in datos if direccion(s[0]) > inicio)
    assert siguiente - inicio == 37 * 4


def test_las_funciones_que_coinciden_estan_en_c_y_los_intentos_bajo_non_matching(estados: Any) -> None:
    todos = plano(estados)
    for nombre in COINCIDENTES:
        assert todos[nombre] is EstadoFuncion.C, nombre
    for nombre in NO_COINCIDENTES:
        assert todos[nombre] is EstadoFuncion.NO_COINCIDENTE, nombre
    assert sum(1 for e in todos.values() if e is EstadoFuncion.C) == len(COINCIDENTES)


def test_las_cabeceras_son_c89_y_definen_los_tipos_y_la_macro() -> None:
    comun = (RAIZ_REPO / "include" / "common.h").read_text(encoding="utf-8")
    macro = (RAIZ_REPO / "include" / "macro.h").read_text(encoding="utf-8")
    gte = (RAIZ_REPO / "include" / "gte.h").read_text(encoding="utf-8")
    for tipo in ("u8", "u16", "u32", "s8", "s16", "s32", "vu8", "vu16", "vu32"):
        assert re.search(rf"\b{tipo};", comun), tipo
    assert "NULL" in comun and "#define INCLUDE_ASM(FOLDER, NAME)" in macro
    fuentes = (p.read_text(encoding="utf-8") for p in (RAIZ_REPO / "src").glob("*.c"))
    for texto in (comun, macro, gte, *fuentes):
        sin_cadenas = re.sub(r'"[^"\n]*"', '""', texto)
        assert "//" not in sin_cadenas, "GCC 2.8.1 no admite comentarios de linea"


def comandos_de_inline_c() -> list[str]:
    """Nombres de los comandos GTE de INLINE_C.H (macros con dos nop y una ficha .word)."""
    texto = (RAIZ_REPO / "include" / "psyq" / "INLINE_C.H").read_text(encoding="latin-1").replace("\r", "")
    bloques = re.findall(
        r'#define (gte_\w+)\(\)\s*__asm__ volatile \(\s*\\\s*"nop;"\s*\\\s*"nop;"\s*\\\s*"\.word', texto
    )
    return bloques


def test_gte_h_redefine_todos_los_comandos_de_inline_c_con_el_mnemonico() -> None:
    gte = (RAIZ_REPO / "include" / "gte.h").read_text(encoding="utf-8")
    comandos = comandos_de_inline_c()
    assert len(comandos) == 65
    macros = set(
        re.findall(
            r"^\.macro (\w+)",
            (RAIZ_REPO / "asm" / "include" / "gte_macros.inc").read_text(encoding="utf-8"),
            re.M,
        )
    )
    for nombre in comandos:
        assert f"#undef {nombre}\n#define {nombre}()" in gte, nombre
    mnemonicos = re.findall(r'__asm__ volatile \("nop; nop; (\w+)', gte)
    assert len(mnemonicos) == 64
    assert set(mnemonicos) <= macros
    assert ".word" not in re.sub(r"/\*.*?\*/", "", gte, flags=re.S)


def test_la_configuracion_declara_las_secciones_de_cada_archivo(configuracion: Any) -> None:
    declaradas = dominio.secciones_declaradas(configuracion)
    assert len(declaradas) == 25
    assert declaradas["camara_y_bucle_logico"] == frozenset({".text", ".rodata"})
    assert declaradas["tarjeta_de_memoria"] == frozenset({".text", ".data"})
    assert declaradas["audio_xa_y_spu"] == frozenset({".text", ".rodata"})


def test_macro_h_define_include_rodata_en_la_seccion_de_solo_lectura() -> None:
    macro = (RAIZ_REPO / "include" / "macro.h").read_text(encoding="utf-8")
    cuerpo = macro[macro.index("#define INCLUDE_RODATA(FOLDER, NAME)") :]
    assert '".section .rodata\\n"' in cuerpo and '".section .text\\n"' in cuerpo
    for archivo in ("audio_xa_y_spu", "cargador_de_niveles_y_cd"):
        texto = (RAIZ_REPO / "src" / f"{archivo}.c").read_text(encoding="utf-8")
        assert f'INCLUDE_RODATA("asm/nonmatchings/{archivo}", D_' in texto


def test_la_cadena_de_la_tarjeta_de_memoria_vive_en_c_y_cubre_exactamente_su_tramo(
    configuracion: Any,
) -> None:
    texto = (RAIZ_REPO / "src" / "tarjeta_de_memoria.c").read_text(encoding="utf-8")
    cadena = "bu00:BASLUS-00838 BBLIT"
    assert f'char D_8005E04C[] = "{cadena}";' in texto
    datos = [s for s in subsegmentos(configuracion) if s[1] in ("data", ".data")]
    inicios = [direccion(s[0]) for s in datos]
    propia = inicios.index(0x8005E04C)
    assert datos[propia][1:] == [".data", "tarjeta_de_memoria"]
    assert inicios[propia + 1] - 0x8005E04C == len(cadena) + 1


def test_el_g_por_archivo_esta_declarado_con_su_evidencia() -> None:
    assert leer_valores_g(RAIZ_REPO) == {"camara_y_bucle_logico": 8}
    texto = (RAIZ_REPO / "config" / "opciones_compilacion.toml").read_text(encoding="utf-8")
    assert "desplazamiento($gp)" in texto


def test_el_repositorio_no_contiene_rutas_absolutas_de_ninguna_maquina() -> None:
    absoluta = re.compile(r"\b[A-Za-z]:[\\/]+(?:Users|Documents and Settings)[\\/]", re.IGNORECASE)
    archivos = [*(RAIZ_REPO / "src").glob("*.c"), *(RAIZ_REPO / "include").glob("*.h")]
    archivos += [RAIZ_REPO / "docs" / n for n in ("DESCOMPILACION.md", "PROGRESO.md", "TOOLCHAIN.md")]
    archivos += [RAIZ_REPO / "config" / "splat.yaml"]
    archivos += sorted((RAIZ_REPO / "tools" / "reconstruccion").glob("*.py"))
    for archivo in archivos:
        assert not absoluta.search(archivo.read_text(encoding="utf-8")), archivo.name


def test_las_constantes_de_zona_coinciden_con_el_mapa_de_memoria() -> None:
    mapa = (RAIZ_REPO / "docs" / "MAPA_MEMORIA.md").read_text(encoding="utf-8")
    for valor in (progreso.INICIO_JUEGO, progreso.INICIO_LIBRERIAS, progreso.FIN_LIBRERIAS):
        assert f"0x{valor:08X}" in mapa


@pytest.fixture
def repo_mixto(tmp_path: Path) -> Any:
    rutas, _ = entorno_real(tmp_path)
    raiz = tmp_path / "repo mixto (prueba)"
    shutil.copytree(RAIZ_REPO / "config", raiz / "config", ignore=shutil.ignore_patterns("local.toml"))
    for carpeta in ("include", "src"):
        shutil.copytree(RAIZ_REPO / carpeta, raiz / carpeta)
    return raiz, {"BBLIT_DISC": str(rutas.disc), "BBLIT_TOOLCHAIN": str(rutas.toolchain)}


def test_ciclo_real_con_cinco_funciones_en_c_reproduce_el_ejecutable_y_discrimina(
    repo_mixto: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = repo_mixto
    assert cli.main(["split"], variables, raiz) == 0
    fuentes = {p.name: sha256(p) for p in (raiz / "src").glob("*.c")}
    asm_antes = {str(p): sha256(p) for p in (raiz / "asm").rglob("*.s")}
    assert cli.main(["split"], variables, raiz) == 0
    assert {str(p): sha256(p) for p in (raiz / "asm").rglob("*.s")} == asm_antes
    assert {p.name: sha256(p) for p in (raiz / "src").glob("*.c")} == fuentes

    assert cli.main(["build"], variables, raiz) == 0
    assert sha256(raiz / "build" / "SLUS_008.38") == SHA256_ORIGINAL
    capsys.readouterr()
    assert cli.main(["verify"], variables, raiz) == 0
    assert capsys.readouterr().out.startswith("OK ")

    for funcion in ("func_80036204", "func_8001CE64", "func_80030D60"):
        assert cli.main(["diff", funcion], variables, raiz) == 0
        assert "puntuacion 0" in capsys.readouterr().out
    assert cli.main(["diff", "func_80035244"], variables, raiz) == 1
    assert capsys.readouterr().out.endswith("puntuacion 600\n")
    assert cli.main(["diff", "func_80014BA0"], variables, raiz) == 1
    assert "'func_80014BA0' sigue en INCLUDE_ASM" in capsys.readouterr().err

    carpeta = raiz.parent / "variantes"
    carpeta.mkdir()
    (carpeta / "buena.c").write_text(VARIANTE_BUENA, encoding="utf-8")
    (carpeta / "mala.c").write_text(
        VARIANTE_BUENA.replace("return 0;\n}\n", "return base;\n}\n"), encoding="utf-8"
    )
    (carpeta / "rota.c").write_text("esto no es C\n", encoding="utf-8")
    capsys.readouterr()
    assert cli.main(["probar", "func_80036204", str(carpeta)], variables, raiz) == 0
    filas = capsys.readouterr().out.splitlines()
    assert filas[0].split() == ["variante", "puntuacion"]
    assert filas[1].split() == ["buena.c", "0"]
    assert int(filas[2].split()[1]) > 0 and filas[2].split()[0] == "mala.c"
    assert filas[3].startswith("rota.c") and "error:" in filas[3]

    capsys.readouterr()
    assert cli.main(["progreso"], variables, raiz) == 0
    resumen = capsys.readouterr().out
    assert resumen.startswith("progreso: 5 funciones del juego en C de ")
    assert "2 NON_MATCHING" in resumen
    medido = progreso.generar_progreso(raiz)
    assert medido.coherente is True
    assert medido.glabel_en_asm is not None and medido.glabel_en_asm + 5 == medido.funciones_totales
    assert medido.c_juego.bytes == 0x28 + 0x20 + 0x4C + 0xEC + 0x44
    assert medido.juego.bytes == 201416

    (raiz / "asm" / "overlay").mkdir()
    (raiz / "asm" / "overlay" / "ajeno.s").write_text("x", encoding="utf-8")
    assert cli.main(["clean"], variables, raiz) == 0
    assert (raiz / "asm" / "overlay" / "ajeno.s").is_file()
    assert not (raiz / "asm" / "boot.s").exists()


def test_un_build_fallido_no_deja_ejecutable_y_verify_da_fail(
    repo_mixto: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = repo_mixto
    assert cli.main(["split"], variables, raiz) == 0
    assert cli.main(["build"], variables, raiz) == 0
    assert cli.main(["verify"], variables, raiz) == 0
    destino = raiz / "src" / "inicializacion_de_motor.c"
    destino.write_text(destino.read_text(encoding="utf-8") + "\ns32 D_80061238 = 5;\n", encoding="utf-8")
    capsys.readouterr()
    assert cli.main(["build"], variables, raiz) == 1
    capturado = capsys.readouterr()
    assert "inicializacion_de_motor.c.o: genera 4 bytes en la seccion inesperada '.data'" in capturado.err
    for salida in ("SLUS_008.38", "SLUS_008.bin", "SLUS_008.elf", "SLUS_008.map"):
        assert not (raiz / "build" / salida).exists(), salida
    assert cli.main(["verify"], variables, raiz) == 1
    assert capsys.readouterr().out.startswith("FAIL el ejecutable reconstruido no existe")


def test_los_datos_declarados_se_aceptan_y_los_no_declarados_se_rechazan_con_archivo_y_seccion(
    repo_mixto: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = repo_mixto
    assert cli.main(["split"], variables, raiz) == 0
    capsys.readouterr()
    assert cli.main(["build"], variables, raiz) == 0
    objeto = raiz / "build" / "src" / "camara_y_bucle_logico.c.o"
    assert objeto.is_file()
    configuracion = (raiz / "config" / "splat.yaml").read_text(encoding="utf-8")
    sin_subsegmento = re.sub(
        r"      - \[0x[0-9A-F]+, \.rodata, camara_y_bucle_logico\][^\n]*\n", "", configuracion
    )
    assert sin_subsegmento != configuracion
    (raiz / "config" / "splat.yaml").write_text(sin_subsegmento, encoding="utf-8")
    capsys.readouterr()
    assert cli.main(["build"], variables, raiz) == 1
    assert (
        "camara_y_bucle_logico.c.o: genera 28 bytes en la seccion inesperada '.rodata'"
        in capsys.readouterr().err
    )

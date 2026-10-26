import csv
import io
import json
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest
from tools.ghidra.borradores import (
    COLUMNAS_FALLIDAS,
    ENCABEZADO_ASM,
    asegurar_desensamblado,
    buscar_continuacion,
    causa_de_fallo,
    construir_config_desensamblador,
    contexto_desde_exportacion,
    ejecutar_separado,
    formatear_fallidas,
    formatear_fusionadas,
    fusionar_funciones,
    generar_borradores,
    leer_prototipos,
    nombre_archivo,
    nombre_de_tabla,
    preparar_asm_funcion,
    seleccionar_funciones,
)
from tools.ghidra.dominio import Simbolo
from tools.ghidra.ejecucion import ResultadoEjecucion
from tools.ghidra.ensamblador import FuncionAsm, dividir_por_funcion
from tools.ghidra.exportaciones import ReferenciaDato
from tools.ghidra.grafo import TablaSalto

from tests.ghidra.escenario import (
    D_DESTINO_1,
    D_DESTINO_2,
    TABLA,
    A,
    B,
    C,
    D,
    E,
    G,
    nombre,
    simbolos,
    texto_asm,
)
from tests.ghidra.sintetica import funcion

TABLA_D = TablaSalto("D_8005E000", TABLA, (D_DESTINO_1, D_DESTINO_2))


def _funciones_asm() -> dict[str, FuncionAsm]:
    return {f.nombre: f for f in dividir_por_funcion(texto_asm())}


def test_el_ambito_por_defecto_son_las_rutinas_que_ninguna_firma_identifica() -> None:
    tabla = [
        Simbolo("__main", 0x80014A00, "func", 8),
        Simbolo("func_80014A08", 0x80014A08, "func", 0xAC),
        Simbolo("main", 0x80016414, "func", 0x7F8),
        Simbolo("VSync", 0x80045E00, "func", 0x20),
        Simbolo("func_80046000", 0x80046000, "func", 0x20),
        Simbolo("func_80046100", 0x80046100, "func", 0x20),
    ]
    filas = [
        funcion(0x80014A00, "__main", 8, es_libreria=True),
        funcion(0x80014A08, "start", 0xAC),
        funcion(0x80016414, "main", 0x7F8),
        funcion(0x80045E00, "VSync", 0x20, es_libreria=True),
        funcion(0x80046000, "LIBPRESS_OBJ_1", 0x20, es_libreria=True),
    ]
    por_defecto = seleccionar_funciones(tabla, filas)
    assert [s.nombre for s in por_defecto] == ["func_80014A08", "main", "func_80046100"]
    solo_rango = seleccionar_funciones(tabla, filas, "rango")
    assert [s.nombre for s in solo_rango] == ["main"]


def test_un_ambito_desconocido_se_rechaza() -> None:
    with pytest.raises(ValueError, match="sin_firma o rango"):
        seleccionar_funciones([], [], "todo")  # type: ignore[arg-type]


def test_los_archivos_de_salida_llevan_la_direccion_en_mayusculas_y_el_nombre() -> None:
    assert nombre_archivo(Simbolo("main", 0x80016414, "func", 0x7F8), "s") == "80016414_main.s"
    assert nombre_archivo(Simbolo("main", 0x80016414, "func", 0x7F8), "c") == "80016414_main.c"


def test_la_configuracion_del_desensamblador_es_json_con_rutas_relativas_a_la_carpeta() -> None:
    texto = construir_config_desensamblador(Path("config/symbols.txt"), 0x55800, 0x80014A00)
    configuracion = json.loads(texto)
    opciones = configuracion["options"]
    assert opciones["target_path"] == "SLUS_008.38"
    assert opciones["asm_path"] == "asm"
    assert opciones["symbol_addrs_path"][0].endswith("config/symbols.txt")
    segmentos = configuracion["segments"][0]["subsegments"]
    assert segmentos[0] == [0x800, "asm", "text"]
    assert segmentos[-1] == {"start": 0x55800, "type": "bss", "name": "bss", "vram": 0x80069A00}
    assert configuracion["segments"][1] == [0x55800]


def test_genera_el_desensamblado_con_el_lanzador_y_lo_reutiliza(tmp_path: Path) -> None:
    exe = tmp_path / "original.bin"
    exe.write_bytes(b"exe")
    carpeta = tmp_path / "con espacios" / "desensamblado"
    llamadas: list[Sequence[str]] = []

    def lanzador(comando: Sequence[str], segundos: int) -> ResultadoEjecucion:
        llamadas.append(comando)
        (carpeta / "asm").mkdir(parents=True)
        (carpeta / "asm" / "text.s").write_text("texto del desensamblado\n", encoding="utf-8")
        return ResultadoEjecucion(0, "")

    kwargs = {"base": 0x80014A00, "tamano_archivo": 0x55800, "lanzador": lanzador}
    assert (
        asegurar_desensamblado(exe, tmp_path / "symbols.txt", carpeta, **kwargs)
        == "texto del desensamblado\n"
    )
    assert (
        asegurar_desensamblado(exe, tmp_path / "symbols.txt", carpeta, **kwargs)
        == "texto del desensamblado\n"
    )
    assert len(llamadas) == 1
    assert llamadas[0][:5] == [sys.executable, "-X", "utf8", "-m", "splat"]
    assert (carpeta / "SLUS_008.38").read_bytes() == b"exe"
    assert json.loads((carpeta / "splat.yaml").read_text(encoding="utf-8"))["options"]["platform"] == "psx"


def test_si_splat_falla_se_informa_sin_volcar_rutas(tmp_path: Path) -> None:
    exe = tmp_path / "original.bin"
    exe.write_bytes(b"exe")
    with pytest.raises(ValueError, match="splat no pudo generar text.s"):  # noqa: RUF043
        asegurar_desensamblado(
            exe,
            tmp_path / "symbols.txt",
            tmp_path / "salida",
            base=0x80014A00,
            tamano_archivo=0x55800,
            lanzador=lambda _c, _s: ResultadoEjecucion(1, "error"),
        )


def test_el_asm_de_una_funcion_sin_tablas_lleva_solo_el_encabezado_y_el_cuerpo() -> None:
    texto = preparar_asm_funcion(_funciones_asm()[nombre(A)], ())
    assert texto.startswith(ENCABEZADO_ASM + "glabel func_80014AC4\n")
    assert texto.endswith("endlabel func_80014AC4\n")
    assert ".rodata" not in texto


def test_las_tablas_de_salto_se_renombran_y_sus_destinos_reciben_etiqueta() -> None:
    texto = preparar_asm_funcion(_funciones_asm()[nombre(D)], (TABLA_D,))
    assert "%hi(jtbl_8005E000)" in texto
    assert "D_8005E000" not in texto
    assert f"  .L{D_DESTINO_1:08X}:\n" in texto
    assert f"  .L{D_DESTINO_2:08X}:\n" in texto
    assert (
        f"dlabel jtbl_8005E000\n    .word .L{D_DESTINO_1:08X}\n    .word .L{D_DESTINO_2:08X}\nenddlabel jtbl_8005E000\n"  # noqa: E501
        in texto
    )
    assert texto.count(f".L{D_DESTINO_1:08X}:") == 1


def test_una_etiqueta_existente_no_se_duplica_y_un_nombre_jtbl_no_se_cambia() -> None:
    original = _funciones_asm()[nombre(D)]
    lineas = list(original.lineas)
    indice = next(i for i, linea in enumerate(lineas) if f"{D_DESTINO_1:08X} " in linea)
    lineas.insert(indice, f"  jlabel .L{D_DESTINO_1:08X}")
    con_etiqueta = FuncionAsm(original.nombre, original.direccion, tuple(lineas))
    tabla = TablaSalto("jtbl_80067E64", TABLA, (D_DESTINO_1,))
    texto = preparar_asm_funcion(con_etiqueta, (tabla,))
    assert texto.count(f".L{D_DESTINO_1:08X}") == 2  # el jlabel original y el .word de la tabla
    assert "dlabel jtbl_80067E64" in texto
    assert nombre_de_tabla(tabla) == "jtbl_80067E64"
    assert nombre_de_tabla(TABLA_D) == "jtbl_8005E000"


def test_causa_de_fallo_distingue_fallo_de_m2c_codigo_de_salida_y_salida_vacia() -> None:
    fallo = (
        "/*\nDecompilation failure in function f:\n\nUnable to determine jump table.\n\nMas detalle.\n*/\n"
    )
    assert causa_de_fallo(0, fallo, "") == "Unable to determine jump table."
    assert (
        causa_de_fallo(1, "", "linea 1\n\nTraceback x\nValueError: boom \n")
        == "codigo de salida 1: ValueError: boom"
    )
    assert causa_de_fallo(2, "", "") == "codigo de salida 2: "
    assert causa_de_fallo(0, "  \n", "") == "salida vacia"
    assert causa_de_fallo(0, "void f(void) {\n}\n", "aviso") is None


def test_el_csv_de_fallidas_y_el_de_fusionadas() -> None:
    simbolo = Simbolo("func_80014AC4", A, "func", 0x34)
    filas = list(csv.reader(io.StringIO(formatear_fallidas([(simbolo, "tiempo agotado, 5 s")]))))
    assert tuple(filas[0]) == COLUMNAS_FALLIDAS
    assert filas[1] == ["0x80014AC4", "func_80014AC4", "tiempo agotado, 5 s"]
    vacio = formatear_fallidas([])
    assert vacio == "direccion,nombre,causa\n"
    fusion = formatear_fusionadas([(simbolo, [Simbolo("func_80014AF8", B, "func", 0)])])
    assert fusion == "direccion,nombre,absorbidas\n0x80014AC4,func_80014AC4,0x80014AF8:func_80014AF8\n"


def test_fusionar_une_las_funciones_y_vuelve_etiqueta_la_cabecera_de_las_absorbidas() -> None:
    funciones = _funciones_asm()
    unida = fusionar_funciones([funciones[nombre(B)], funciones[nombre(C)]])
    assert unida.nombre == nombre(B)
    assert unida.direccion == B
    assert unida.lineas[0] == f"glabel {nombre(B)}"
    assert unida.lineas[-1] == f"endlabel {nombre(B)}"
    assert f"  .L{C:08X}:" in unida.lineas
    assert not any(linea.startswith("endlabel") for linea in unida.lineas[:-1])
    with pytest.raises(ValueError, match="no hay funciones que fusionar"):
        fusionar_funciones([])


def test_busca_la_continuacion_por_nombre_por_etiqueta_o_por_jlabel() -> None:
    ordenadas = [_funciones_asm()[nombre(x)] for x in (A, B, C)]
    con_etiqueta = FuncionAsm(
        ordenadas[2].nombre, ordenadas[2].direccion, (*ordenadas[2].lineas, "  .L80014B10:")
    )
    con_jlabel = FuncionAsm(
        ordenadas[2].nombre, ordenadas[2].direccion, (*ordenadas[2].lineas, "  jlabel .L80014B11")
    )
    assert buscar_continuacion(f"Cannot find branch target {nombre(C)}", ordenadas, 0) == 2
    assert buscar_continuacion("Cannot find branch target .L80014B10", [*ordenadas[:2], con_etiqueta], 0) == 2
    assert buscar_continuacion("Cannot find branch target .L80014B11", [*ordenadas[:2], con_jlabel], 0) == 2
    assert buscar_continuacion("Cannot find branch target .L80014B10", ordenadas, 0) is None
    assert buscar_continuacion(f"Cannot find branch target {nombre(A)}", ordenadas, 1) is None
    assert buscar_continuacion("Unable to determine jump table", ordenadas, 0) is None


def test_ejecutar_separado_devuelve_codigo_y_las_dos_salidas() -> None:
    codigo = "import sys; print('salida'); print('error', file=sys.stderr); sys.exit(3)"
    assert ejecutar_separado([sys.executable, "-c", codigo], 30) == (3, "salida\n", "error\n")


def test_ejecutar_separado_informa_el_tiempo_agotado() -> None:
    with pytest.raises(TimeoutError, match="excedio 1 segundos"):
        ejecutar_separado([sys.executable, "-c", "import time; time.sleep(30)"], 1)


class M2cDoble:
    """Simula m2c decidiendo el resultado por el nombre del archivo de entrada."""

    def __init__(self, respuestas: dict[str, object]) -> None:
        self.respuestas = respuestas
        self.entradas: list[str] = []

    def __call__(self, comando: Sequence[str], segundos: int) -> tuple[int, str, str]:
        ruta = Path(comando[-1])
        self.entradas.append(ruta.name)
        texto = ruta.read_text(encoding="utf-8")
        respuesta = self.respuestas[ruta.name.split("_", 1)[0]]
        if callable(respuesta):
            return respuesta(texto)  # type: ignore[no-any-return]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta  # type: ignore[return-value]


def _generar(tmp_path: Path, doble: M2cDoble, elegidas: list[Simbolo]) -> tuple[object, Path]:
    salida = tmp_path / "salida con espacios"
    tablas = {D: (TABLA_D,)}
    resumen = generar_borradores(
        elegidas=elegidas,
        texto_asm=texto_asm(),
        tablas=tablas,
        contexto="contexto\n",
        salida=salida,
        m2c=Path("m2c.py"),
        segundos=7,
        lanzador=doble,
    )
    return resumen, salida


def test_genera_borradores_registra_fallos_y_fusiona_las_funciones_partidas(tmp_path: Path) -> None:
    ok = (0, "void f(void) {\n}\n", "")
    marcas = (0, "void f(void) {\n    M2C_ERROR(x);\n}\n", "")
    doble = M2cDoble(
        {
            f"{A:08X}": marcas,
            f"{B:08X}": lambda texto: (
                ok
                if f".L{C:08X}:" in texto
                else (
                    0,
                    f"/*\nDecompilation failure in function b:\n\nCannot find branch target {nombre(C)}\n\n*/\n",  # noqa: E501
                    "",
                )
            ),
            f"{C:08X}": ok,
            f"{D:08X}": (
                0,
                "/*\nDecompilation failure in function d:\n\nUnable to determine jump table\n\n*/\n",
                "",
            ),
            f"{E:08X}": TimeoutError("agotado"),
            f"{G:08X}": (1, "", "boom"),
        }
    )
    elegidas = [s for s in simbolos() if s.direccion in (A, B, C, D, E, G)]
    resumen, salida = _generar(tmp_path, doble, elegidas)
    assert (resumen.seleccionadas, resumen.generadas, resumen.fallidas) == (6, 2, 3)  # type: ignore[attr-defined]
    assert (resumen.absorbidas, resumen.con_marcas) == (1, 1)  # type: ignore[attr-defined]
    assert sorted(p.name for p in (salida / "m2c").glob("*.c")) == [
        "80014AC4_func_80014AC4.c",
        "80014AF8_func_80014AF8.c",
    ]
    assert (salida / "contexto_m2c.c").read_text(encoding="utf-8") == "contexto\n"
    filas = list(csv.reader((salida / "m2c" / "FALLIDAS.csv").open(encoding="utf-8", newline="")))
    assert [f[1:] for f in filas[1:]] == [
        ["func_80014B14", "Unable to determine jump table"],
        ["func_80014B44", "tiempo agotado (7 s)"],
        ["func_80014B4C", "codigo de salida 1: boom"],
    ]
    fusionadas = (salida / "m2c" / "FUSIONADAS.csv").read_text(encoding="utf-8")
    assert fusionadas.splitlines()[1] == f"0x{B:08X},{nombre(B)},0x{C:08X}:{nombre(C)}"
    asm_d = (salida / "asm" / f"{D:08X}_{nombre(D)}.s").read_text(encoding="utf-8")
    assert "dlabel jtbl_8005E000" in asm_d
    assert f"{C:08X}_{nombre(C)}.s" not in doble.entradas


def test_si_la_fusion_tambien_falla_se_conserva_la_causa_original(tmp_path: Path) -> None:
    fallo = (
        0,
        f"/*\nDecompilation failure in function b:\n\nCannot find branch target {nombre(C)}\n\n*/\n",
        "",
    )
    doble = M2cDoble({f"{B:08X}": fallo, f"{C:08X}": (0, "void c(void) {\n}\n", "")})
    elegidas = [s for s in simbolos() if s.direccion in (B, C)]
    resumen, salida = _generar(tmp_path, doble, elegidas)
    assert (resumen.generadas, resumen.fallidas, resumen.absorbidas) == (1, 1, 0)  # type: ignore[attr-defined]
    assert (salida / "m2c" / "FUSIONADAS.csv").read_text(encoding="utf-8") == "direccion,nombre,absorbidas\n"


def test_una_funcion_elegida_que_falta_en_el_desensamblado_se_rechaza(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="func_80000000 no figura en el desensamblado"):
        _generar(tmp_path, M2cDoble({}), [Simbolo("func_80000000", 0x80000000, "func", 8)])
    with pytest.raises(ValueError, match="func_80014AC4 no figura en el desensamblado"):
        _generar(tmp_path, M2cDoble({}), [Simbolo("func_80014AC4", B, "func", 8)])


def test_lee_los_prototipos_por_direccion_ignorando_nombres_ajenos(tmp_path: Path) -> None:
    decomp = tmp_path / "decomp"
    decomp.mkdir()
    (decomp / "80016414_main.c").write_text("void main(void)\n{\n}\n", encoding="utf-8")
    (decomp / "80016414_otro.c").write_text("int otro(int a)\n{\n}\n", encoding="utf-8")
    (decomp / "80016C0C_f.c").write_text("MATRIX f(void)\n{\n}\n", encoding="utf-8")
    (decomp / "notas_x.c").write_text("int g(void) {", encoding="utf-8")
    (decomp / "leeme.txt").write_text("x", encoding="utf-8")
    tabla = [
        Simbolo("main", 0x80016414, "func", 0x7F8),
        Simbolo("func_80016C0C", 0x80016C0C, "func", 0x10),
        Simbolo("func_80016C1C", 0x80016C1C, "func", 0x10),
    ]
    assert leer_prototipos(decomp, tabla) == {0x80016414: "void main(void);"}
    contexto = contexto_desde_exportacion(tabla, decomp, [ReferenciaDato(0x80010000, 4, (), 1, 1)])
    assert "void main(void);\nextern s32 D_80010000;\n" in contexto

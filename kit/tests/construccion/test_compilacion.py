"""Compilacion de archivos C con el compilador original, con las rutas y convenciones de un proyecto."""

from pathlib import Path
from typing import Any

import pytest
from psxdecomp.construccion import compilacion as comp
from psxdecomp.construccion.compilacion import HerramientasCompilacion
from psxdecomp.dominio import construir_compilacion, construir_convenciones, construir_rutas
from psxdecomp.toolchain.dominio import cargar_lock

from toolchain.ayudantes import bloque_componente, lock_de

RUTAS = construir_rutas({})
RUTAS_PROPIAS = construir_rutas(
    {"fuentes": "codigo", "incluir": "cabeceras", "macros": "ensamblador/macros", "splat": "datos/part.yaml"}
)
CONVENCIONES = construir_convenciones({})
CONVENCIONES_ESTRECHAS = construir_convenciones({"max_valor_g": 4})
COMPILACION = construir_compilacion({})
COMPILACION_PROPIA = construir_compilacion(
    {"version_aspsx": "2.67", "opciones_compilador": ["-quiet", "-O1"]}
)

SALIDA_OBJDUMP = """
salida/a.c.o:     file format elf32-littlemips

Sections:
Idx Name          Size      VMA       LMA       File off  Algn
  0 .text         000000d8  00000000  00000000  00000034  2**2
                  CONTENTS, ALLOC, LOAD, RELOC, READONLY, CODE
  1 .data         00000000  00000000  00000000  0000750c  2**0
  2 .rodata       0000001d  00000000  00000000  00000150  2**3
  3 .reginfo      00000018  00000000  00000000  0000750c  2**2
"""


class ProcesoSimuladoError(RuntimeError):
    """Fallo de una herramienta simulado por el ejecutor de prueba."""


def herramientas() -> HerramientasCompilacion:
    return HerramientasCompilacion(
        python="py",
        preprocesador=Path("CPPPSX.EXE"),
        compilador=Path("CC1PSX.EXE"),
        maspsx=Path("maspsx.py"),
        ensamblador=Path("as.exe"),
        objdump=Path("objdump.exe"),
    )


class Ejecutor:
    """Registra cada comando, crea el objeto que produciria maspsx y entrega la lista de secciones."""

    def __init__(self, secciones: str = "", falla_en: str | None = None) -> None:
        self.comandos: list[list[str]] = []
        self.directorios: list[Path] = []
        self.tiempos: list[int] = []
        self.secciones = secciones
        self.falla_en = falla_en

    def __call__(self, comando: Any, directorio: Any, timeout_s: Any) -> str:
        self.comandos.append(list(comando))
        self.directorios.append(directorio)
        self.tiempos.append(timeout_s)
        nombre = Path(comando[0]).name
        if nombre == self.falla_en:
            raise ProcesoSimuladoError(f"{nombre}: termino con codigo 1")
        if nombre == "objdump.exe":
            return self.secciones
        if "--run-assembler" in comando:
            (directorio / comando[comando.index("-o") + 1]).write_bytes(b"objeto")
        return ""


# --- comandos ---------------------------------------------------------------------------------


def test_comando_preprocesar_incluye_la_carpeta_y_las_definiciones() -> None:
    assert comp.comando_preprocesar(Path("CPPPSX.EXE"), "src/a.c", "salida/a.c.i", "include") == [
        "CPPPSX.EXE",
        "-Iinclude",
        "src/a.c",
        "-o",
        "salida/a.c.i",
    ]
    comando = comp.comando_preprocesar(Path("c.exe"), "src/a.c", "o.i", "include", ("NON_MATCHING", "X_1"))
    assert comando[1:4] == ["-Iinclude", "-DNON_MATCHING", "-DX_1"]


@pytest.mark.parametrize("definicion", ["minuscula", "A B", "X=1", "", "A;rm"])
def test_comando_preprocesar_rechaza_definiciones_que_no_son_macros(definicion: Any) -> None:
    with pytest.raises(ValueError, match="identificador en mayusculas"):
        comp.comando_preprocesar(Path("c.exe"), "src/a.c", "o.i", "include", (definicion,))


def test_comando_compilar_fija_las_opciones_del_compilador_original() -> None:
    comando = comp.comando_compilar(Path("CC1PSX.EXE"), "a.i", "a.s", max_valor_g=64, compilacion=COMPILACION)
    assert comando == ["CC1PSX.EXE", "-quiet", "-O2", "-G0", "a.i", "-o", "a.s"]
    asignado = comp.comando_compilar(
        Path("CC1PSX.EXE"), "a.i", "a.s", 8, max_valor_g=64, compilacion=COMPILACION
    )
    assert asignado[3] == "-G8"


def test_comando_compilar_usa_las_opciones_del_manifiesto_y_no_las_del_kit() -> None:
    comando = comp.comando_compilar(
        Path("CC1PSX.EXE"), "a.i", "a.s", max_valor_g=64, compilacion=COMPILACION_PROPIA
    )
    assert comando == ["CC1PSX.EXE", "-quiet", "-O1", "-G0", "a.i", "-o", "a.s"]


def test_comando_compilar_sin_opciones_declaradas_solo_lleva_el_umbral_g() -> None:
    sin_opciones = construir_compilacion({"opciones_compilador": []})
    comando = comp.comando_compilar(
        Path("CC1PSX.EXE"), "a.i", "a.s", 4, max_valor_g=64, compilacion=sin_opciones
    )
    assert comando == ["CC1PSX.EXE", "-G4", "a.i", "-o", "a.s"]


def test_comando_maspsx_usa_la_version_del_manifiesto_y_no_la_del_kit() -> None:
    comando = comp.comando_maspsx(
        herramientas(), "a.s", "a.o", "m", max_valor_g=64, compilacion=COMPILACION_PROPIA
    )
    assert comando[2] == "--aspsx-version=2.67"


def test_comando_maspsx_usa_la_version_de_aspsx_y_el_ensamblador_por_ruta() -> None:
    comando = comp.comando_maspsx(
        herramientas(), "a.s", "a.o", "asm/macros", max_valor_g=64, compilacion=COMPILACION
    )
    assert comando == [
        "py",
        "maspsx.py",
        "--aspsx-version=2.80",
        "--use-comm-section",
        "--run-assembler",
        "--gnu-as-path=as.exe",
        "-EL",
        "-march=r3000",
        "-mips1",
        "-G0",
        "-I",
        "asm/macros",
        "-o",
        "a.o",
        "a.s",
    ]


@pytest.mark.parametrize("valor", [-1, 5, True, "8", 1.5])
def test_el_umbral_g_fuera_del_tope_del_proyecto_se_rechaza_en_los_dos_comandos(valor: Any) -> None:
    with pytest.raises(ValueError, match="entero entre 0 y 4"):
        comp.comando_compilar(Path("c.exe"), "a.i", "a.s", valor, max_valor_g=4, compilacion=COMPILACION)
    with pytest.raises(ValueError, match="entero entre 0 y 4"):
        comp.comando_maspsx(herramientas(), "a.s", "a.o", "m", valor, max_valor_g=4, compilacion=COMPILACION)


def test_el_tope_del_umbral_g_lo_decide_el_proyecto_y_no_el_kit() -> None:
    asignado = comp.comando_compilar(Path("c.exe"), "a.i", "a.s", 64, max_valor_g=64, compilacion=COMPILACION)
    assert asignado[3] == "-G64"
    with pytest.raises(ValueError, match="entero entre 0 y 63"):
        comp.comando_compilar(Path("c.exe"), "a.i", "a.s", 64, max_valor_g=63, compilacion=COMPILACION)


def test_comando_secciones() -> None:
    assert comp.comando_secciones(Path("objdump.exe"), "a.o") == ["objdump.exe", "-h", "a.o"]


# --- secciones --------------------------------------------------------------------------------


def test_leer_secciones_extrae_nombre_y_tamano() -> None:
    assert comp.leer_secciones(SALIDA_OBJDUMP) == {
        ".text": 0xD8,
        ".data": 0,
        ".rodata": 0x1D,
        ".reginfo": 0x18,
    }
    assert comp.leer_secciones("sin secciones") == {}


def test_verificar_solo_texto_acepta_codigo_y_secciones_de_control() -> None:
    secciones = {".text": 100, ".data": 0, ".bss": 0, ".reginfo": 24, ".pdr": 8}
    comp.verificar_solo_texto("a.o", secciones, rutas=RUTAS)


@pytest.mark.parametrize(
    "seccion", [".data", ".rodata", ".rdata", ".bss", ".sdata", ".sbss", ".lit8", ".scommon"]
)
def test_verificar_solo_texto_rechaza_datos_con_el_nombre_de_la_seccion(seccion: Any) -> None:
    with pytest.raises(ValueError, match=f"a.o: genera 4 bytes en la seccion inesperada '{seccion}'"):
        comp.verificar_solo_texto("a.o", {".text": 8, seccion: 4}, rutas=RUTAS)


def test_el_error_de_seccion_inesperada_nombra_el_archivo_de_particion_del_manifiesto() -> None:
    with pytest.raises(ValueError, match=r"declare en datos/part\.yaml un subsegmento '\.rodata'"):
        comp.verificar_solo_texto("a.o", {".text": 8, ".rodata": 4}, rutas=RUTAS_PROPIAS)


def test_verificar_solo_texto_acepta_datos_de_una_seccion_declarada_y_no_exime_a_las_demas() -> None:
    comp.verificar_solo_texto("a.o", {".text": 8, ".rodata": 4}, {".rodata"}, rutas=RUTAS)
    with pytest.raises(ValueError, match=r"seccion inesperada '.rodata'"):
        comp.verificar_solo_texto("a.o", {".text": 8, ".rodata": 4}, {".data"}, rutas=RUTAS)


# --- rutas ------------------------------------------------------------------------------------


def test_rutas_intermedias_junto_al_objeto() -> None:
    assert comp.rutas_intermedias("salida/a.c.o") == ("salida/a.c.i", "salida/a.c.s")


@pytest.mark.parametrize(
    "objeto", ["salida/a.s.o", "salida/a.o", "salida/../x.c.o", "salida/a b.c.o", "/abs/a.c.o", ""]
)
def test_rutas_intermedias_rechaza_rutas_dudosas(objeto: Any) -> None:
    with pytest.raises(ValueError, match="no es una ruta de objeto C valida"):
        comp.rutas_intermedias(objeto)


def test_validar_fuente_acepta_solo_c_dentro_de_la_carpeta_de_fuentes_del_proyecto() -> None:
    comp.validar_fuente("src/modulo_a.c", RUTAS)
    comp.validar_fuente("codigo/modulo_a.c", RUTAS_PROPIAS)
    for malo in ("asm/a.c", "src/a.s", "src/../a.c", "src/a b.c", "src", "../src/a.c", "srcx/a.c"):
        with pytest.raises(ValueError, match=r"no es un archivo .c dentro de src/"):
            comp.validar_fuente(malo, RUTAS)
    with pytest.raises(ValueError, match=r"no es un archivo .c dentro de codigo/"):
        comp.validar_fuente("src/modulo_a.c", RUTAS_PROPIAS)


# --- compilar ---------------------------------------------------------------------------------


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    carpeta = tmp_path / "proyecto con espacios"
    for nombre in ("src", "codigo"):
        (carpeta / nombre).mkdir(parents=True)
        (carpeta / nombre / "a.c").write_text("int x;\n", encoding="utf-8")
    return carpeta


def compilar(raiz: Path, ejecutor: Ejecutor, fuente: str = "src/a.c", **opciones: Any) -> None:
    rutas = opciones.pop("rutas", RUTAS)
    convenciones = opciones.pop("convenciones", CONVENCIONES)
    compilacion = opciones.pop("compilacion", COMPILACION)
    comp.compilar_fuente(
        raiz,
        fuente,
        "salida/a.c.o",
        herramientas(),
        ejecutor,
        rutas=rutas,
        convenciones=convenciones,
        compilacion=compilacion,
        **opciones,
    )


def test_compilar_fuente_encadena_preprocesador_compilador_ensamblador_y_comprueba_secciones(
    raiz: Path,
) -> None:
    ejecutor = Ejecutor(secciones=SALIDA_OBJDUMP.replace("0000001d", "00000000"))
    compilar(raiz, ejecutor)
    assert [Path(c[0]).name for c in ejecutor.comandos] == ["CPPPSX.EXE", "CC1PSX.EXE", "py", "objdump.exe"]
    assert ejecutor.comandos[0][-3:] == ["src/a.c", "-o", "salida/a.c.i"]
    assert ejecutor.comandos[1][-3:] == ["salida/a.c.i", "-o", "salida/a.c.s"]
    assert ejecutor.comandos[2][-3:] == ["-o", "salida/a.c.o", "salida/a.c.s"]
    assert ejecutor.directorios == [raiz] * 4
    esperados = [comp.TIMEOUT_PREPROCESAR_S, comp.TIMEOUT_COMPILAR_S] + [comp.TIMEOUT_ENSAMBLAR_S] * 2
    assert ejecutor.tiempos == esperados
    assert (raiz / "salida" / "a.c.o").read_bytes() == b"objeto"


def test_compilar_fuente_usa_las_cabeceras_y_macros_declaradas_en_el_manifiesto(raiz: Path) -> None:
    ejecutor = Ejecutor(secciones=SALIDA_OBJDUMP.replace("0000001d", "00000000"))
    compilar(raiz, ejecutor, "codigo/a.c", rutas=RUTAS_PROPIAS)
    assert "-Icabeceras" in ejecutor.comandos[0]
    ensamblado = ejecutor.comandos[2]
    assert ensamblado[ensamblado.index("-I") + 1] == "ensamblador/macros"
    ejecutor = Ejecutor(secciones=SALIDA_OBJDUMP.replace("0000001d", "00000000"))
    compilar(raiz, ejecutor)
    assert "-Iinclude" in ejecutor.comandos[0]
    ensamblado = ejecutor.comandos[2]
    assert ensamblado[ensamblado.index("-I") + 1] == "asm/include"


def test_compilar_fuente_pasa_la_version_y_las_opciones_del_manifiesto_a_cada_herramienta(raiz: Path) -> None:
    ejecutor = Ejecutor()
    compilar(raiz, ejecutor, exigir_solo_texto=False, compilacion=COMPILACION_PROPIA)
    _, compilador, ensamblador = ejecutor.comandos
    assert compilador[1:3] == ["-quiet", "-O1"]
    assert "--aspsx-version=2.67" in ensamblador
    assert "--aspsx-version=2.80" not in ensamblador


def test_compilar_fuente_aplica_el_tope_del_umbral_g_del_proyecto(raiz: Path) -> None:
    ejecutor = Ejecutor()
    with pytest.raises(ValueError, match="entero entre 0 y 4"):
        compilar(raiz, ejecutor, valor_g=8, convenciones=CONVENCIONES_ESTRECHAS)
    assert [Path(c[0]).name for c in ejecutor.comandos] == ["CPPPSX.EXE"]
    compilar(raiz, Ejecutor(), valor_g=8, exigir_solo_texto=False)


def test_compilar_fuente_con_datos_falla_y_sin_exigencia_lo_permite(raiz: Path) -> None:
    ejecutor = Ejecutor(secciones=SALIDA_OBJDUMP)
    with pytest.raises(ValueError, match=r"genera 29 bytes en la seccion inesperada '.rodata'"):
        compilar(raiz, ejecutor)
    ejecutor = Ejecutor(secciones=SALIDA_OBJDUMP)
    compilar(raiz, ejecutor, definiciones=("NON_MATCHING",), exigir_solo_texto=False)
    assert [Path(c[0]).name for c in ejecutor.comandos] == ["CPPPSX.EXE", "CC1PSX.EXE", "py"]
    assert "-DNON_MATCHING" in ejecutor.comandos[0]


def test_compilar_fuente_acepta_datos_de_una_seccion_declarada_por_el_subsegmento(raiz: Path) -> None:
    ejecutor = Ejecutor(secciones=SALIDA_OBJDUMP)
    compilar(raiz, ejecutor, secciones_declaradas={".rodata"})
    assert Path(ejecutor.comandos[-1][0]).name == "objdump.exe"


def test_compilar_archivo_admite_un_fuente_fuera_de_la_carpeta_de_fuentes(raiz: Path) -> None:
    (raiz / "variantes").mkdir()
    (raiz / "variantes" / "v1.c").write_text("int y;\n", encoding="utf-8")
    ejecutor = Ejecutor()
    comp.compilar_archivo(
        raiz,
        "variantes/v1.c",
        "salida/v1.c.o",
        herramientas(),
        ejecutor,
        exigir_solo_texto=False,
        rutas=RUTAS,
        convenciones=CONVENCIONES,
        compilacion=COMPILACION,
    )
    assert ejecutor.comandos[0][-3:] == ["variantes/v1.c", "-o", "salida/v1.c.i"]


def test_compilar_fuente_sin_archivo_o_con_rutas_invalidas(raiz: Path) -> None:
    ejecutor = Ejecutor()
    with pytest.raises(FileNotFoundError, match=r"falta el fuente 'src/falta.c'"):
        compilar(raiz, ejecutor, "src/falta.c")
    with pytest.raises(ValueError, match="dentro de src/"):
        compilar(raiz, ejecutor, "../a.c")
    with pytest.raises(ValueError, match="ruta de objeto C valida"):
        comp.compilar_fuente(
            raiz,
            "src/a.c",
            "../a.c.o",
            herramientas(),
            ejecutor,
            rutas=RUTAS,
            convenciones=CONVENCIONES,
            compilacion=COMPILACION,
        )
    assert ejecutor.comandos == []


def test_un_fallo_del_compilador_se_propaga_sin_ensamblar(raiz: Path) -> None:
    ejecutor = Ejecutor(falla_en="CC1PSX.EXE")
    with pytest.raises(ProcesoSimuladoError, match=r"CC1PSX.EXE"):
        compilar(raiz, ejecutor)
    assert [Path(c[0]).name for c in ejecutor.comandos] == ["CPPPSX.EXE", "CC1PSX.EXE"]


# --- herramientas -----------------------------------------------------------------------------


def lock_completo() -> Any:
    sdk = bloque_componente(
        b"s", archivos_clave={"cpppsx": "pssn/bin/CPPPSX.EXE", "cc1psx": "pssn/bin/CC1PSX.EXE"}
    )
    mas = bloque_componente(b"m", archivos_clave={"maspsx": "maspsx.py"})
    bin_ = bloque_componente(
        b"b",
        archivos_clave={
            "as": "bin/as.exe",
            "ld": "bin/ld.exe",
            "objcopy": "bin/o.exe",
            "objdump": "bin/d.exe",
        },
    )
    return cargar_lock(lock_de(**{"psyq-4.4": sdk, "maspsx": mas, "binutils-mipsel": bin_}))


def test_resolver_herramientas_compilacion_localiza_cada_ejecutable(tmp_path: Path) -> None:
    for relativa in ("psyq-4.4/pssn/bin/CPPPSX.EXE", "psyq-4.4/pssn/bin/CC1PSX.EXE", "maspsx/maspsx.py"):
        (tmp_path / relativa).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relativa).write_bytes(b"")
    for nombre in ("as.exe", "d.exe", "ld.exe", "o.exe"):
        (tmp_path / "binutils-mipsel" / "bin").mkdir(parents=True, exist_ok=True)
        (tmp_path / "binutils-mipsel" / "bin" / nombre).write_bytes(b"")
    resueltas = comp.resolver_herramientas_compilacion(lock_completo(), tmp_path, "py")
    assert resueltas.python == "py"
    assert resueltas.preprocesador == tmp_path / "psyq-4.4" / "pssn" / "bin" / "CPPPSX.EXE"
    assert resueltas.compilador.name == "CC1PSX.EXE"
    assert resueltas.maspsx == tmp_path / "maspsx" / "maspsx.py"
    assert resueltas.ensamblador.name == "as.exe" and resueltas.objdump.name == "d.exe"
    assert resueltas.enlazador is not None and resueltas.enlazador.name == "ld.exe"
    assert resueltas.objcopy is not None and resueltas.objcopy.name == "o.exe"


def test_resolver_herramientas_compilacion_sin_sdk_instalado(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"psyq-4.4"):
        comp.resolver_herramientas_compilacion(lock_completo(), tmp_path, "py")

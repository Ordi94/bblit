from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import compilacion as comp
from tools.reconstruccion import infraestructura as infra
from tools.reconstruccion.compilacion import HerramientasCompilacion
from tools.reconstruccion.infraestructura import Herramientas, ProcesoError
from tools.toolchain.dominio import cargar_lock

from tests.toolchain.ayudantes import bloque_componente, lock_de

from .test_infraestructura import CUERPO, EJECUTABLE, REFERENCIA, Registro

SALIDA_OBJDUMP = """
build/src/a.c.o:     file format elf32-littlemips

Sections:
Idx Name          Size      VMA       LMA       File off  Algn
  0 .text         000074d8  00000000  00000000  00000034  2**2
                  CONTENTS, ALLOC, LOAD, RELOC, READONLY, CODE
  1 .data         00000000  00000000  00000000  0000750c  2**0
  2 .rodata       0000001d  00000000  00000000  00000150  2**3
  3 .reginfo      00000018  00000000  00000000  0000750c  2**2
"""


def herramientas_compilacion() -> HerramientasCompilacion:
    return HerramientasCompilacion(
        python="py",
        preprocesador=Path("CPPPSX.EXE"),
        compilador=Path("CC1PSX.EXE"),
        maspsx=Path("maspsx.py"),
        ensamblador=Path("as.exe"),
        objdump=Path("objdump.exe"),
    )


class EjecutorC(Registro):
    """Registro que ademas produce los archivos de la compilacion y la lista de secciones."""

    def __init__(self, secciones: str = "", **opciones: Any) -> None:
        super().__init__(**opciones)
        self.secciones = secciones

    def __call__(self, comando: Any, directorio: Any, timeout_s: Any) -> Any:
        salida = super().__call__(comando, directorio, timeout_s)
        if Path(comando[0]).name == "objdump.exe":
            return self.secciones
        if "--run-assembler" in comando:
            (directorio / comando[comando.index("-o") + 1]).write_bytes(b"objeto")
        return salida


def test_comando_preprocesar_incluye_la_carpeta_y_las_definiciones() -> None:
    assert comp.comando_preprocesar(Path("CPPPSX.EXE"), "src/a.c", "build/src/a.c.i", "include") == [
        "CPPPSX.EXE",
        "-Iinclude",
        "src/a.c",
        "-o",
        "build/src/a.c.i",
    ]
    comando = comp.comando_preprocesar(Path("c.exe"), "src/a.c", "o.i", "include", ("NON_MATCHING", "X_1"))
    assert comando[1:4] == ["-Iinclude", "-DNON_MATCHING", "-DX_1"]


@pytest.mark.parametrize("definicion", ["non_matching", "A B", "X=1", "", "A;rm"])
def test_comando_preprocesar_rechaza_definiciones_que_no_son_macros(definicion: Any) -> None:
    with pytest.raises(ValueError, match="identificador en mayusculas"):
        comp.comando_preprocesar(Path("c.exe"), "src/a.c", "o.i", "include", (definicion,))


def test_comando_compilar_fija_las_opciones_del_compilador_original() -> None:
    assert comp.comando_compilar(Path("CC1PSX.EXE"), "a.i", "a.s") == [
        "CC1PSX.EXE",
        "-quiet",
        "-O2",
        "-G0",
        "a.i",
        "-o",
        "a.s",
    ]


def test_comando_maspsx_usa_aspsx_280_porque_el_original_usa_gp_allow_la_y_el_ensamblador_por_ruta() -> None:
    assert comp.comando_maspsx(herramientas_compilacion(), "a.s", "a.o", "asm/include") == [
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
        "asm/include",
        "-o",
        "a.o",
        "a.s",
    ]


def test_comando_secciones() -> None:
    assert comp.comando_secciones(Path("objdump.exe"), "a.o") == ["objdump.exe", "-h", "a.o"]


def test_leer_secciones_extrae_nombre_y_tamano() -> None:
    assert comp.leer_secciones(SALIDA_OBJDUMP) == {
        ".text": 0x74D8,
        ".data": 0,
        ".rodata": 0x1D,
        ".reginfo": 0x18,
    }
    assert comp.leer_secciones("sin secciones") == {}


def test_verificar_solo_texto_acepta_codigo_y_secciones_de_control() -> None:
    comp.verificar_solo_texto("a.o", {".text": 100, ".data": 0, ".bss": 0, ".reginfo": 24, ".pdr": 8})


@pytest.mark.parametrize(
    "seccion", [".data", ".rodata", ".rdata", ".bss", ".sdata", ".sbss", ".lit8", ".scommon"]
)
def test_verificar_solo_texto_rechaza_datos_con_el_nombre_de_la_seccion(seccion: Any) -> None:
    with pytest.raises(ValueError, match=f"a.o: genera 4 bytes en la seccion inesperada '{seccion}'"):
        comp.verificar_solo_texto("a.o", {".text": 8, seccion: 4})


def test_verificar_solo_texto_acepta_datos_cuando_la_seccion_esta_declarada() -> None:
    """Una seccion de datos con contenido se acepta si el subsegmento del archivo la declara."""
    comp.verificar_solo_texto("a.o", {".text": 8, ".rodata": 4}, {".rodata"})


def test_verificar_solo_texto_rechaza_datos_si_solo_se_declara_otra_seccion() -> None:
    """Declarar una seccion no exime a las demas: .rodata con contenido sigue siendo un error."""
    with pytest.raises(ValueError, match=r"seccion inesperada '.rodata'"):
        comp.verificar_solo_texto("a.o", {".text": 8, ".rodata": 4}, {".data"})


def test_rutas_intermedias_junto_al_objeto() -> None:
    assert comp.rutas_intermedias("build/src/a.c.o") == ("build/src/a.c.i", "build/src/a.c.s")


@pytest.mark.parametrize(
    "objeto", ["build/src/a.s.o", "build/src/a.o", "build/../x.c.o", "build/a b.c.o", "/abs/a.c.o", ""]
)
def test_rutas_intermedias_rechaza_rutas_dudosas(objeto: Any) -> None:
    with pytest.raises(ValueError, match="no es una ruta de objeto C valida"):
        comp.rutas_intermedias(objeto)


def test_validar_fuente_acepta_solo_c_dentro_de_src() -> None:
    comp.validar_fuente("src/code_80014AC4.c")
    for malo in ("asm/a.c", "src/a.s", "src/../a.c", "src/a b.c", "src", "../src/a.c"):
        with pytest.raises(ValueError, match=r"no es un archivo .c dentro de src/"):
            comp.validar_fuente(malo)


@pytest.fixture
def repo(tmp_path: Path) -> Any:
    raiz = tmp_path / "repo con espacios"
    (raiz / "src").mkdir(parents=True)
    (raiz / "src" / "a.c").write_text("int x;\n", encoding="utf-8")
    return raiz


def test_compilar_fuente_encadena_preprocesador_compilador_ensamblador_y_comprueba_secciones(
    repo: Any,
) -> None:
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP.replace("0000001d", "00000000"))
    comp.compilar_fuente(repo, "src/a.c", "build/src/a.c.o", herramientas_compilacion(), ejecutor)
    nombres = [Path(c[0]).name for c in ejecutor.comandos]
    assert nombres == ["CPPPSX.EXE", "CC1PSX.EXE", "py", "objdump.exe"]
    assert ejecutor.comandos[0][-3:] == ["src/a.c", "-o", "build/src/a.c.i"]
    assert ejecutor.comandos[1][-3:] == ["build/src/a.c.i", "-o", "build/src/a.c.s"]
    assert ejecutor.comandos[2][-3:] == ["-o", "build/src/a.c.o", "build/src/a.c.s"]
    assert ejecutor.directorios == [repo] * 4
    assert (
        ejecutor.tiempos
        == [comp.TIMEOUT_PREPROCESAR_S, comp.TIMEOUT_COMPILAR_S] + [comp.TIMEOUT_ENSAMBLAR_S] * 2
    )
    assert (repo / "build" / "src" / "a.c.o").read_bytes() == b"objeto"


def test_compilar_fuente_con_datos_falla_y_sin_exigencia_lo_permite(repo: Any) -> None:
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP)
    with pytest.raises(ValueError, match=r"genera 29 bytes en la seccion inesperada '.rodata'"):
        comp.compilar_fuente(repo, "src/a.c", "build/src/a.c.o", herramientas_compilacion(), ejecutor)
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP)
    comp.compilar_fuente(
        repo,
        "src/a.c",
        "build/diff/a.c.o",
        herramientas_compilacion(),
        ejecutor,
        definiciones=("NON_MATCHING",),
        exigir_solo_texto=False,
    )
    assert [Path(c[0]).name for c in ejecutor.comandos] == ["CPPPSX.EXE", "CC1PSX.EXE", "py"]
    assert "-DNON_MATCHING" in ejecutor.comandos[0]


def test_compilar_fuente_acepta_datos_de_una_seccion_declarada_por_el_subsegmento(repo: Any) -> None:
    """Con .rodata declarada, un objeto que la llena compila y se verifica sin error."""
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP)
    comp.compilar_fuente(
        repo,
        "src/a.c",
        "build/src/a.c.o",
        herramientas_compilacion(),
        ejecutor,
        secciones_declaradas={".rodata"},
    )
    assert [Path(c[0]).name for c in ejecutor.comandos][-1] == "objdump.exe"


def test_compilar_fuente_sin_archivo_o_con_rutas_invalidas(repo: Any) -> None:
    ejecutor = EjecutorC()
    with pytest.raises(FileNotFoundError, match=r"falta el fuente 'src/falta.c'"):
        comp.compilar_fuente(repo, "src/falta.c", "build/src/falta.c.o", herramientas_compilacion(), ejecutor)
    with pytest.raises(ValueError, match="dentro de src/"):
        comp.compilar_fuente(repo, "../a.c", "build/src/a.c.o", herramientas_compilacion(), ejecutor)
    with pytest.raises(ValueError, match="ruta de objeto C valida"):
        comp.compilar_fuente(repo, "src/a.c", "../a.c.o", herramientas_compilacion(), ejecutor)
    assert ejecutor.comandos == []


def test_un_fallo_del_compilador_se_propaga_sin_ensamblar(repo: Any) -> None:
    llamadas: list[str] = []

    def ejecutor(comando: Any, directorio: Any, timeout_s: Any) -> str:
        llamadas.append(Path(comando[0]).name)
        if "CC1PSX.EXE" in comando[0]:
            raise ProcesoError("CC1PSX.EXE: termino con codigo 1")
        return ""

    with pytest.raises(ProcesoError, match=r"CC1PSX.EXE"):
        comp.compilar_fuente(repo, "src/a.c", "build/src/a.c.o", herramientas_compilacion(), ejecutor)
    assert llamadas == ["CPPPSX.EXE", "CC1PSX.EXE"]


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
    herramientas = comp.resolver_herramientas_compilacion(lock_completo(), tmp_path, "py")
    assert herramientas.python == "py"
    assert herramientas.preprocesador == tmp_path / "psyq-4.4" / "pssn" / "bin" / "CPPPSX.EXE"
    assert herramientas.compilador.name == "CC1PSX.EXE"
    assert herramientas.maspsx == tmp_path / "maspsx" / "maspsx.py"
    assert herramientas.ensamblador.name == "as.exe" and herramientas.objdump.name == "d.exe"
    assert herramientas.enlazador is not None and herramientas.enlazador.name == "ld.exe"
    assert herramientas.objcopy is not None and herramientas.objcopy.name == "o.exe"


def test_resolver_herramientas_compilacion_sin_sdk_instalado(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"psyq-4.4"):
        comp.resolver_herramientas_compilacion(lock_completo(), tmp_path, "py")


def preparar_construccion(raiz: Path, script: str) -> None:
    (raiz / "build").mkdir(parents=True)
    (raiz / infra.SCRIPT_ENLAZADOR).write_text(script, encoding="utf-8")
    (raiz / "asm").mkdir()
    (raiz / "asm" / "boot.s").write_text("b", encoding="utf-8")
    (raiz / "src").mkdir()
    (raiz / "src" / "a.c").write_text("int x;\n", encoding="utf-8")


SCRIPT_MIXTO = (
    "main\n{\n    build/asm/boot.s.o(.text);\n    build/src/a.c.o(.text);\n    build/src/a.c.o(.data);\n}\n"
)


def herramientas_base() -> Herramientas:
    return Herramientas("py", Path("as.exe"), Path("ld.exe"), Path("objcopy.exe"))


def test_construir_mixto_respeta_el_orden_del_script_y_compila_los_c(tmp_path: Path) -> None:
    preparar_construccion(tmp_path, SCRIPT_MIXTO)
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP.replace("0000001d", "00000000"))
    peticiones: list[int] = []

    def obtener() -> HerramientasCompilacion:
        peticiones.append(1)
        return herramientas_compilacion()

    destino = comp.construir_mixto(tmp_path, REFERENCIA, herramientas_base(), obtener, ejecutor)
    assert destino.read_bytes() == EJECUTABLE
    nombres = [Path(c[0]).name for c in ejecutor.comandos]
    assert nombres == ["as.exe", "CPPPSX.EXE", "CC1PSX.EXE", "py", "objdump.exe", "ld.exe", "objcopy.exe"]
    assert peticiones == [1], "las herramientas de compilacion se resuelven una sola vez"


def test_construir_mixto_acepta_datos_declarados_por_la_particion_del_archivo(tmp_path: Path) -> None:
    """La seccion declarada para a.c se acepta aunque el objeto la llene."""
    preparar_construccion(tmp_path, SCRIPT_MIXTO)
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP)
    destino = comp.construir_mixto(
        tmp_path,
        REFERENCIA,
        herramientas_base(),
        herramientas_compilacion,
        ejecutor,
        declaradas={"a": {".rodata"}},
    )
    assert destino.read_bytes() == EJECUTABLE


def test_construir_mixto_rechaza_datos_no_declarados_con_otro_archivo_declarado(tmp_path: Path) -> None:
    """Las secciones declaradas de otro archivo no eximen a a.c de declarar las suyas."""
    preparar_construccion(tmp_path, SCRIPT_MIXTO)
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP)
    with pytest.raises(ValueError, match=r"seccion inesperada '.rodata'"):
        comp.construir_mixto(
            tmp_path,
            REFERENCIA,
            herramientas_base(),
            herramientas_compilacion,
            ejecutor,
            declaradas={"b": {".rodata"}},
        )


def test_construir_mixto_sin_archivos_c_no_pide_el_sdk(tmp_path: Path) -> None:
    preparar_construccion(tmp_path, "main\n{\n    build/asm/boot.s.o(.text);\n}\n")

    def obtener() -> HerramientasCompilacion:
        raise AssertionError("no debe pedirse el compilador")

    destino = comp.construir_mixto(tmp_path, REFERENCIA, herramientas_base(), obtener, EjecutorC())
    assert destino.read_bytes() == EJECUTABLE


def test_construir_mixto_sin_sdk_instalado_falla_con_la_causa(tmp_path: Path) -> None:
    preparar_construccion(tmp_path, SCRIPT_MIXTO)

    def obtener() -> HerramientasCompilacion:
        raise FileNotFoundError("componente 'psyq-4.4': 'cc1psx' no esta instalado")

    with pytest.raises(FileNotFoundError, match=r"psyq-4.4"):
        comp.construir_mixto(tmp_path, REFERENCIA, herramientas_base(), obtener, EjecutorC())


def test_construir_sin_compilador_rechaza_el_script_con_c(tmp_path: Path) -> None:
    preparar_construccion(tmp_path, SCRIPT_MIXTO)
    with pytest.raises(ValueError, match=r"el fuente 'src/a.c' es C y no hay compilador disponible"):
        infra.construir(tmp_path, REFERENCIA, herramientas_base(), Registro())


def test_construir_mixto_valida_la_longitud_del_cuerpo(tmp_path: Path) -> None:
    preparar_construccion(tmp_path, SCRIPT_MIXTO)
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP.replace("0000001d", "00000000"), cuerpo=CUERPO[:-1])
    with pytest.raises(ValueError, match="el cuerpo enlazado mide 15 bytes"):
        comp.construir_mixto(tmp_path, REFERENCIA, herramientas_base(), herramientas_compilacion, ejecutor)


def test_el_ejecutor_por_defecto_de_construir_mixto_es_ejecutar_proceso() -> None:
    assert comp.construir_mixto.__defaults__ == (infra.ejecutar_proceso,)
    assert comp.compilar_fuente.__kwdefaults__ == {
        "definiciones": (),
        "exigir_solo_texto": True,
        "secciones_declaradas": (),
        "valor_g": 0,
    }


MENSAJE_G_INVALIDO = "el valor de -G debe ser un entero entre 0 y 64"


@pytest.mark.parametrize("valor_g", [0, 1, 8, 64])
def test_los_comandos_llevan_el_g_pedido(valor_g: int) -> None:
    compilador = comp.comando_compilar(Path("CC1PSX.EXE"), "a.i", "a.s", valor_g)
    ensamblador = comp.comando_maspsx(herramientas_compilacion(), "a.s", "a.o", "asm/include", valor_g)
    assert compilador[3] == f"-G{valor_g}"
    assert f"-G{valor_g}" in ensamblador
    assert sum(1 for a in ensamblador if a.startswith("-G")) == 1


@pytest.mark.parametrize("valor_g", [-1, 65, 1000, True, False, "8", 8.0, None])
def test_los_comandos_rechazan_un_g_fuera_de_rango_o_no_entero(valor_g: Any) -> None:
    with pytest.raises(ValueError, match=MENSAJE_G_INVALIDO):
        comp.comando_compilar(Path("CC1PSX.EXE"), "a.i", "a.s", valor_g)
    with pytest.raises(ValueError, match=MENSAJE_G_INVALIDO):
        comp.comando_maspsx(herramientas_compilacion(), "a.s", "a.o", "asm/include", valor_g)


def test_el_g_del_toml_llega_a_los_comandos_reales_del_compilador_y_de_maspsx(tmp_path: Path) -> None:
    preparar_construccion(tmp_path, SCRIPT_MIXTO)
    (tmp_path / "src" / "b.c").write_text("int y;\n", encoding="utf-8")
    (tmp_path / infra.SCRIPT_ENLAZADOR).write_text(
        "main\n{\n    build/src/a.c.o(.text);\n    build/src/b.c.o(.text);\n}\n", encoding="utf-8"
    )
    (tmp_path / "config").mkdir()
    (tmp_path / infra.OPCIONES_COMPILACION).write_text("[archivos.a]\ng = 8\n", encoding="utf-8")
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP.replace("0000001d", "00000000"))
    comp.construir_mixto(tmp_path, REFERENCIA, herramientas_base(), herramientas_compilacion, ejecutor)

    def g_por_archivo(programa: str, indice_archivo: int) -> dict[str, list[str]]:
        comandos = [c for c in ejecutor.comandos if Path(c[0]).name == programa and "-o" in c]
        resultado: dict[str, list[str]] = {}
        for comando in comandos:
            archivo = Path(comando[indice_archivo]).name.split(".")[0]
            resultado[archivo] = [a for a in comando if a.startswith("-G")]
        return resultado

    assert g_por_archivo("CC1PSX.EXE", -1) == {"a": ["-G8"], "b": ["-G0"]}
    ensamblados = {
        Path(c[c.index("-o") + 1]).name.split(".")[0]: [a for a in c if a.startswith("-G")]
        for c in ejecutor.comandos
        if "--run-assembler" in c
    }
    assert ensamblados == {"a": ["-G8"], "b": ["-G0"]}

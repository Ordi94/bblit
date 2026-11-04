"""Reglas de negocio de la construccion mixta: C compilado y ensamblador, en el orden del script de enlace."""

from pathlib import Path
from typing import Any

import pytest
from psxdecomp.construccion import compilacion as comp
from psxdecomp.construccion import infraestructura as infra
from psxdecomp.construccion.compilacion import HerramientasCompilacion
from psxdecomp.construccion.infraestructura import Herramientas
from psxdecomp.dominio import construir_compilacion, construir_convenciones, construir_rutas

from .test_compilacion import SALIDA_OBJDUMP, herramientas
from .test_infraestructura import CUERPO, EJECUTABLE, REFERENCIA, SALIDAS, Registro

RUTAS = construir_rutas({})
CONVENCIONES = construir_convenciones({})
COMPILACION = construir_compilacion({})
SCRIPT_MIXTO = (
    "main\n{\n    build/asm/boot.s.o(.text);\n    build/src/a.c.o(.text);\n    build/src/a.c.o(.data);\n}\n"
)
SIN_DATOS = SALIDA_OBJDUMP.replace("0000001d", "00000000")


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


def herramientas_base() -> Herramientas:
    return Herramientas("py", Path("as.exe"), Path("ld.exe"), Path("objcopy.exe"))


def preparar(raiz: Path, script: str) -> None:
    (raiz / "build").mkdir(parents=True)
    (raiz / SALIDAS.script_enlazador).write_text(script, encoding="utf-8")
    (raiz / "asm").mkdir()
    (raiz / "asm" / "boot.s").write_text("b", encoding="utf-8")
    (raiz / "src").mkdir()
    (raiz / "src" / "a.c").write_text("int x;\n", encoding="utf-8")


def construir(raiz: Path, obtener: Any, ejecutor: Any, declaradas: dict[str, set[str]] | None = None) -> Path:
    return comp.construir_mixto(
        raiz,
        REFERENCIA,
        herramientas_base(),
        obtener,
        ejecutor,
        declaradas=declaradas,
        rutas=RUTAS,
        convenciones=CONVENCIONES,
        compilacion=COMPILACION,
    )


def test_construir_mixto_respeta_el_orden_del_script_y_compila_los_c(tmp_path: Path) -> None:
    preparar(tmp_path, SCRIPT_MIXTO)
    ejecutor = EjecutorC(secciones=SIN_DATOS)
    peticiones: list[int] = []

    def obtener() -> HerramientasCompilacion:
        peticiones.append(1)
        return herramientas()

    destino = construir(tmp_path, obtener, ejecutor)
    assert destino.read_bytes() == EJECUTABLE
    nombres = [Path(c[0]).name for c in ejecutor.comandos]
    assert nombres == ["as.exe", "CPPPSX.EXE", "CC1PSX.EXE", "py", "objdump.exe", "ld.exe", "objcopy.exe"]
    assert peticiones == [1], "las herramientas de compilacion se resuelven una sola vez"


def test_construir_mixto_acepta_datos_declarados_por_la_particion_del_archivo(tmp_path: Path) -> None:
    """La seccion declarada para a.c se acepta aunque el objeto la llene."""
    preparar(tmp_path, SCRIPT_MIXTO)
    destino = construir(tmp_path, herramientas, EjecutorC(secciones=SALIDA_OBJDUMP), {"a": {".rodata"}})
    assert destino.read_bytes() == EJECUTABLE


def test_construir_mixto_rechaza_datos_no_declarados_con_otro_archivo_declarado(tmp_path: Path) -> None:
    """Las secciones declaradas de otro archivo no eximen a a.c de declarar las suyas."""
    preparar(tmp_path, SCRIPT_MIXTO)
    with pytest.raises(ValueError, match=r"seccion inesperada '.rodata'"):
        construir(tmp_path, herramientas, EjecutorC(secciones=SALIDA_OBJDUMP), {"b": {".rodata"}})


def test_construir_mixto_sin_archivos_c_no_pide_el_sdk(tmp_path: Path) -> None:
    preparar(tmp_path, "main\n{\n    build/asm/boot.s.o(.text);\n}\n")

    def obtener() -> HerramientasCompilacion:
        raise AssertionError("no debe pedirse el compilador")

    assert construir(tmp_path, obtener, EjecutorC()).read_bytes() == EJECUTABLE


def test_construir_mixto_sin_sdk_instalado_falla_con_la_causa(tmp_path: Path) -> None:
    preparar(tmp_path, SCRIPT_MIXTO)

    def obtener() -> HerramientasCompilacion:
        raise FileNotFoundError("componente 'sdk': 'compilador' no esta instalado")

    with pytest.raises(FileNotFoundError, match=r"componente 'sdk'"):
        construir(tmp_path, obtener, EjecutorC())


def test_construir_sin_compilador_rechaza_el_script_con_c(tmp_path: Path) -> None:
    preparar(tmp_path, SCRIPT_MIXTO)
    with pytest.raises(ValueError, match=r"el fuente 'src/a.c' es C y no hay compilador disponible"):
        infra.construir(
            tmp_path, REFERENCIA, herramientas_base(), Registro(), rutas=RUTAS, convenciones=CONVENCIONES
        )


def test_construir_mixto_valida_la_longitud_del_cuerpo(tmp_path: Path) -> None:
    preparar(tmp_path, SCRIPT_MIXTO)
    ejecutor = EjecutorC(secciones=SIN_DATOS, cuerpo=CUERPO[:-1])
    with pytest.raises(ValueError, match="el cuerpo enlazado mide 15 bytes"):
        construir(tmp_path, herramientas, ejecutor)


def test_el_ejecutor_por_defecto_de_construir_mixto_es_ejecutar_proceso() -> None:
    assert comp.construir_mixto.__defaults__ == (infra.ejecutar_proceso,)


def test_el_g_del_archivo_de_opciones_llega_a_los_comandos_del_compilador_y_de_maspsx(tmp_path: Path) -> None:
    preparar(tmp_path, SCRIPT_MIXTO)
    (tmp_path / "src" / "b.c").write_text("int y;\n", encoding="utf-8")
    (tmp_path / SALIDAS.script_enlazador).write_text(
        "main\n{\n    build/src/a.c.o(.text);\n    build/src/b.c.o(.text);\n}\n", encoding="utf-8"
    )
    (tmp_path / "config").mkdir()
    (tmp_path / RUTAS.opciones_compilacion).write_text("[archivos.a]\ng = 8\n", encoding="utf-8")
    ejecutor = EjecutorC(secciones=SIN_DATOS)
    construir(tmp_path, herramientas, ejecutor)

    compilados = {
        Path(c[-1]).name.split(".")[0]: [a for a in c if a.startswith("-G")]
        for c in ejecutor.comandos
        if Path(c[0]).name == "CC1PSX.EXE"
    }
    ensamblados = {
        Path(c[c.index("-o") + 1]).name.split(".")[0]: [a for a in c if a.startswith("-G")]
        for c in ejecutor.comandos
        if "--run-assembler" in c
    }
    assert compilados == {"a": ["-G8"], "b": ["-G0"]}
    assert ensamblados == {"a": ["-G8"], "b": ["-G0"]}

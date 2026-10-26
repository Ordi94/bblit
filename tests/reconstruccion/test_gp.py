"""Soporte de ``$gp`` y datos pequenos, y comparacion por bytes tras enlazar."""

from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import compilacion as comp
from tools.reconstruccion import diff, dominio, enlace_diff, variantes
from tools.reconstruccion import infraestructura as infra
from tools.reconstruccion.compilacion import HerramientasCompilacion
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
from .test_variantes import EjecutorVariantes, crear_variantes, escribir_opciones

# ---------------------------------------------------------------- dominio


def test_valor_gp_lee_la_tabla_enlace_y_valida_el_valor() -> None:
    assert dominio.valor_gp({}) is None
    assert dominio.valor_gp({"enlace": {"gp": 0x80069320}}) == 0x80069320
    for malo in (0, -4, True, "0x80069320", 0x80069321, 0x1_0000_0000):
        with pytest.raises(ValueError, match=r"enlace.gp"):
            dominio.valor_gp({"enlace": {"gp": malo}})
    malos_enlace: list[Any] = [[], {"otra": 1}, {"gp": 4, "otra": 1}]
    for malo_enlace in malos_enlace:
        with pytest.raises(ValueError, match="'enlace' solo admite la clave 'gp'"):
            dominio.valor_gp({"enlace": malo_enlace})
    with pytest.raises(ValueError, match="se esperaba una tabla"):
        dominio.valor_gp([])


def test_valores_g_por_archivo_admite_las_tablas_enlace_y_datos_pequenos() -> None:
    datos = {"archivos": {"a": {"g": 8}}, "enlace": {"gp": 4}, "datos_pequenos": {}}
    assert dominio.valores_g_por_archivo(datos) == {"a": 8}


def test_datos_pequenos_exige_nombre_con_su_direccion() -> None:
    assert dominio.datos_pequenos({}) == {}
    validos = {"datos_pequenos": {"D_800694A8": 0x800694A8, "D_80069338": 0x80069338}}
    assert dominio.datos_pequenos(validos) == {"D_800694A8": 0x800694A8, "D_80069338": 0x80069338}
    casos = [
        ({"datos_pequenos": []}, "debe ser una tabla"),
        ({"datos_pequenos": {"x_800694A8": 0x800694A8}}, "no valido"),
        ({"datos_pequenos": {"D_800694a8": 0x800694A8}}, "no valido"),
        ({"datos_pequenos": {"D_800694A8": True}}, "direccion de 'D_800694A8' no valida"),
        ({"datos_pequenos": {"D_800694A8": "x"}}, "direccion de 'D_800694A8' no valida"),
        ({"datos_pequenos": {"D_800694A8": 0}}, "direccion de 'D_800694A8' no valida"),
        ({"datos_pequenos": {"D_800694A8": 0x1_0000_0000}}, "direccion de 'D_800694A8' no valida"),
        ({"datos_pequenos": {"D_800694A8": 0x800694AC}}, "no coincide con su direccion"),
    ]
    for datos, mensaje in casos:
        with pytest.raises(ValueError, match=mensaje):
            dominio.datos_pequenos(datos)
    with pytest.raises(ValueError, match="se esperaba una tabla"):
        dominio.datos_pequenos([])


def test_texto_gp_ld_define_gp_y_los_datos_pequenos_ordenados() -> None:
    assert dominio.texto_gp_ld(0x80069320) == "_gp = 0x80069320;\n"
    texto = dominio.texto_gp_ld(0x80069320, {"D_800694A8": 0x800694A8, "D_80069338": 0x80069338})
    assert texto == "_gp = 0x80069320;\nD_80069338 = 0x80069338;\nD_800694A8 = 0x800694A8;\n"


def test_direcciones_de_funciones_solo_toma_las_funciones() -> None:
    texto = (
        "func_80036204 = 0x80036204; // type:func size:0x4c\n"
        "D_80069338 = 0x80069338; // type:s32\n"
        "  func_8001CE64 = 0x8001CE64; // type:func\n"
        "basura sin forma\n"
    )
    assert dominio.direcciones_de_funciones(texto) == {
        "func_80036204": 0x80036204,
        "func_8001CE64": 0x8001CE64,
    }


# ---------------------------------------------------------------- infraestructura


def test_leer_gp_datos_pequenos_y_direcciones(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert infra.leer_gp(tmp_path) is None
    assert infra.leer_datos_pequenos(tmp_path) == {}
    assert infra.leer_direcciones_de_funciones(tmp_path) == {}
    escribir_opciones(tmp_path, "[enlace]\ngp = 0x80069320\n\n[datos_pequenos]\nD_800694A8 = 0x800694A8\n")
    assert infra.leer_gp(tmp_path) == 0x80069320
    assert infra.leer_datos_pequenos(tmp_path) == {"D_800694A8": 0x800694A8}
    escribir_opciones(tmp_path, "[datos_pequenos]\nD_800694A8 = 1\n")
    with pytest.raises(ValueError, match="no coincide con su direccion"):
        infra.leer_datos_pequenos(tmp_path)
    simbolos = tmp_path / infra.SIMBOLOS_PROYECTO
    simbolos.write_text("func_80036204 = 0x80036204; // type:func size:0x4c\n", encoding="utf-8")
    assert infra.leer_direcciones_de_funciones(tmp_path) == {"func_80036204": 0x80036204}
    monkeypatch.setattr(infra, "MAX_BYTES_SIMBOLOS", 3)
    with pytest.raises(ValueError, match="excede el tamano permitido"):
        infra.leer_direcciones_de_funciones(tmp_path)


def comando_de(ejecutor: EjecutorC, nombre: str) -> list[str]:
    return next(c for c in ejecutor.comandos if Path(c[0]).name == nombre)


def test_build_escribe_gp_ld_y_lo_enlaza_despues_del_script_principal(tmp_path: Path) -> None:
    preparar_construccion(tmp_path, SCRIPT_MIXTO)
    escribir_opciones(
        tmp_path,
        "[enlace]\ngp = 0x80069320\n\n[datos_pequenos]\nD_80069338 = 0x80069338\n",
    )
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP.replace("0000001d", "00000000"))
    comp.construir_mixto(tmp_path, REFERENCIA, herramientas_base(), herramientas_compilacion, ejecutor)
    assert (tmp_path / infra.SCRIPT_GP).read_text(encoding="utf-8") == (
        "_gp = 0x80069320;\nD_80069338 = 0x80069338;\n"
    )
    enlace = comando_de(ejecutor, "ld.exe")
    assert enlace.index(infra.SCRIPT_ENLAZADOR) < enlace.index(infra.SCRIPT_GP)


def test_build_sin_gp_declarado_no_genera_gp_ld(tmp_path: Path) -> None:
    preparar_construccion(tmp_path, SCRIPT_MIXTO)
    ejecutor = EjecutorC(secciones=SALIDA_OBJDUMP.replace("0000001d", "00000000"))
    comp.construir_mixto(tmp_path, REFERENCIA, herramientas_base(), herramientas_compilacion, ejecutor)
    assert not (tmp_path / infra.SCRIPT_GP).exists()
    assert infra.SCRIPT_GP not in comando_de(ejecutor, "ld.exe")


def test_clean_conoce_gp_ld_como_artefacto_propio() -> None:
    assert infra.SCRIPT_GP in infra.artefactos_de_build("SLUS_008.38")


# ---------------------------------------------------------------- comparacion por bytes tras enlazar

TABLA_ELF = (
    "build/SLUS_008.elf:     file format elf32-tradlittlemips\n\n"
    "SYMBOL TABLE:\n"
    "ffffffff80036204 g     F .text\t0000004c func_80036204\n"
    "ffffffff80069338 g     O .sbss\t00000004 D_80069338\n"
    "00000000         *UND*\t00000000 externo\n"
    "ffffffff80010000 g       .data\t00000000 nombre-raro\n"
    "corta\n"
)
TABLA_OBJETO = (
    "SYMBOL TABLE:\n"
    "00000010 g     F .text\t0000004c func_80036204\n"
    "00000000 g     F .text\t00000000 func_vacia\n"
    "00000020 g     O .data\t0000004c func_en_datos\n"
)
CUERPO_OBJETO = bytes(range(16)) + bytes([0xAA]) * 0x4C
TEXTO_CON_REFERENCIAS = (
    "TARGET  CURRENT\n  5 \ti  4a: lui a0,%hi(X)\n  6 \ti  4e: addiu a0\n  7 \t   52: nop\n"
)


class EjecutorEnlace(EjecutorDiff):
    """Responde a ``objdump -t``, ``ld`` y ``objcopy`` de la comparacion por bytes."""

    def __init__(self, puntuacion: int, *, difiere: bool = False, falla_ld: bool = False) -> None:
        super().__init__(puntuacion)
        self.difiere = difiere
        self.falla_ld = falla_ld

    def __call__(self, comando: Any, directorio: Any, timeout_s: Any) -> Any:
        nombre = Path(comando[0]).name
        if nombre == "objdump.exe" and comando[1] == "-t":
            self.comandos.append(list(comando))
            return TABLA_ELF if comando[2] == infra.ELF_SALIDA else TABLA_OBJETO
        if nombre == "ld.exe":
            self.comandos.append(list(comando))
            if self.falla_ld:
                raise ProcesoError("ld.exe: termino con codigo 1")
            return ""
        if nombre == "objcopy.exe":
            self.comandos.append(list(comando))
            cuerpo = CUERPO_OBJETO
            if self.difiere and "objetivo" not in comando[-1]:
                cuerpo = CUERPO_OBJETO[:-1] + b"\x00"
            (directorio / comando[-1]).write_bytes(cuerpo)
            return ""
        salida = super().__call__(comando, directorio, timeout_s)
        if "--format=plain" in comando:
            return TEXTO_CON_REFERENCIAS
        return salida


def herramientas_con_enlace() -> HerramientasCompilacion:
    base = herramientas_compilacion()
    return HerramientasCompilacion(
        python=base.python,
        preprocesador=base.preprocesador,
        compilador=base.compilador,
        maspsx=base.maspsx,
        ensamblador=base.ensamblador,
        objdump=base.objdump,
        enlazador=Path("ld.exe"),
        objcopy=Path("objcopy.exe"),
    )


def preparar_elf(raiz: Path) -> None:
    (raiz / "build" / "diff").mkdir(parents=True, exist_ok=True)
    (raiz / infra.ELF_SALIDA).write_bytes(b"elf")


def comparar_bytes(raiz: Path, ejecutor: EjecutorEnlace, direccion: int = 0x80036204) -> bool | None:
    return enlace_diff.bytes_coinciden(
        raiz,
        herramientas_con_enlace(),
        ejecutor,
        funcion="func_80036204",
        direccion=direccion,
        candidato="build/diff/cand.o",
        objetivo="build/diff/objetivo.o",
    )


def test_simbolos_de_elf_conserva_32_bits_e_ignora_indefinidos_y_nombres_raros() -> None:
    assert enlace_diff.simbolos_de_elf(TABLA_ELF) == {
        "func_80036204": 0x80036204,
        "D_80069338": 0x80069338,
    }


def test_texto_simbolos_ld_ordena_por_nombre() -> None:
    assert enlace_diff.texto_simbolos_ld({"b": 0x20, "a": 0x10}) == "a = 0x00000010;\nb = 0x00000020;\n"


def test_funcion_en_objeto_da_desplazamiento_y_tamano() -> None:
    assert enlace_diff.funcion_en_objeto(TABLA_OBJETO, "func_80036204") == enlace_diff.FuncionEnObjeto(
        0x10, 0x4C
    )
    assert enlace_diff.funcion_en_objeto(TABLA_OBJETO, "func_vacia") is None
    assert enlace_diff.funcion_en_objeto(TABLA_OBJETO, "func_en_datos") is None
    assert enlace_diff.funcion_en_objeto(TABLA_OBJETO, "no_existe") is None


def test_contar_referencias_numericas_cuenta_las_marcas_i() -> None:
    assert enlace_diff.contar_referencias_numericas(TEXTO_CON_REFERENCIAS) == 2
    assert enlace_diff.contar_referencias_numericas("sin marcas\n") == 0


def test_bytes_coinciden_enlaza_cada_objeto_en_la_direccion_de_la_funcion(tmp_path: Path) -> None:
    preparar_elf(tmp_path)
    ejecutor = EjecutorEnlace(70)
    assert comparar_bytes(tmp_path, ejecutor) is True
    enlaces = [c for c in ejecutor.comandos if Path(c[0]).name == "ld.exe"]
    assert len(enlaces) == 2
    assert "-Ttext=0x800361F4" in enlaces[0]
    assert (tmp_path / "build" / "diff" / "referencias.ld").read_text(encoding="utf-8") == (
        "D_80069338 = 0x80069338;\nfunc_80036204 = 0x80036204;\n"
    )


def test_bytes_coinciden_distingue_bytes_distintos(tmp_path: Path) -> None:
    preparar_elf(tmp_path)
    assert comparar_bytes(tmp_path, EjecutorEnlace(70, difiere=True)) is False


def test_bytes_coinciden_no_decide_sin_los_requisitos(tmp_path: Path) -> None:
    ejecutor = EjecutorEnlace(70)
    assert comparar_bytes(tmp_path, ejecutor) is None, "sin ELF"
    assert ejecutor.comandos == []
    preparar_elf(tmp_path)
    sin_enlazador = herramientas_compilacion()
    assert (
        enlace_diff.bytes_coinciden(
            tmp_path,
            sin_enlazador,
            ejecutor,
            funcion="f",
            direccion=1,
            candidato="a.o",
            objetivo="b.o",
        )
        is None
    )
    assert comparar_bytes(tmp_path, EjecutorEnlace(70), direccion=0x5) is None, "desplazamiento mayor"
    assert comparar_bytes(tmp_path, EjecutorEnlace(70, falla_ld=True)) is None, "simbolo sin resolver"


def test_bytes_coinciden_sin_la_funcion_en_el_objeto(tmp_path: Path) -> None:
    preparar_elf(tmp_path)
    assert (
        enlace_diff.bytes_coinciden(
            tmp_path,
            herramientas_con_enlace(),
            EjecutorEnlace(70),
            funcion="no_existe",
            direccion=0x80036204,
            candidato="build/diff/cand.o",
            objetivo="build/diff/objetivo.o",
        )
        is None
    )


# ---------------------------------------------------------------- diff, probar y cli con bytes iguales


def crear_repo_diff(raiz: Path, *, con_direccion: bool = True) -> None:
    (raiz / "src").mkdir(parents=True)
    (raiz / "src" / "code_a.c").write_text(
        "s32 func_80036204(s32 x)\n{\n    return x;\n}\n", encoding="utf-8"
    )
    (raiz / "asm" / "matchings" / "code_a").mkdir(parents=True)
    (raiz / "asm" / "matchings" / "code_a" / "func_80036204.s").write_text(ASM_FUNCION, encoding="utf-8")
    preparar_elf(raiz)
    if con_direccion:
        (raiz / infra.SIMBOLOS_PROYECTO).parent.mkdir(parents=True, exist_ok=True)
        (raiz / infra.SIMBOLOS_PROYECTO).write_text(
            "func_80036204 = 0x80036204; // type:func size:0x4c\n", encoding="utf-8"
        )


def test_diff_con_bytes_iguales_coincide_y_cuenta_las_referencias_numericas(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    resultado = diff.comparar_funcion(
        tmp_path, "func_80036204", herramientas_con_enlace(), Path("diff.py"), EjecutorEnlace(70)
    )
    assert resultado.puntuacion == 0 and resultado.puntuacion_asm == 70
    assert resultado.bytes_iguales is True and resultado.referencias_numericas == 2
    assert resultado.coincide is True


def test_diff_con_bytes_distintos_no_coincide(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    resultado = diff.comparar_funcion(
        tmp_path,
        "func_80036204",
        herramientas_con_enlace(),
        Path("diff.py"),
        EjecutorEnlace(70, difiere=True),
    )
    assert resultado.bytes_iguales is False and resultado.referencias_numericas == 0
    assert resultado.coincide is False


def test_diff_no_enlaza_si_la_puntuacion_ya_es_cero_o_no_hay_direccion(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    cero = EjecutorEnlace(0)
    resultado = diff.comparar_funcion(
        tmp_path, "func_80036204", herramientas_con_enlace(), Path("d.py"), cero
    )
    assert resultado.coincide is True and resultado.bytes_iguales is None
    assert not [c for c in cero.comandos if Path(c[0]).name == "ld.exe"]
    (tmp_path / infra.SIMBOLOS_PROYECTO).unlink()
    sin_direccion = EjecutorEnlace(70)
    resultado = diff.comparar_funcion(
        tmp_path, "func_80036204", herramientas_con_enlace(), Path("d.py"), sin_direccion
    )
    assert resultado.coincide is False and resultado.bytes_iguales is None


def test_la_tabla_de_variantes_marca_las_que_solo_difieren_en_la_forma_de_referencia() -> None:
    tabla = variantes.formatear_tabla(
        [ResultadoVariante("a.c", 70, None, True), ResultadoVariante("b.c", 70, None, False)]
    )
    assert tabla.splitlines() == [
        "variante  puntuacion",
        "a.c       70 (bytes iguales)",
        "b.c       70",
    ]
    ordenadas = variantes.ordenar_resultados(
        [ResultadoVariante("a.c", 50, None, False), ResultadoVariante("b.c", 70, None, True)]
    )
    assert [r.nombre for r in ordenadas] == ["b.c", "a.c"]
    assert ResultadoVariante("b.c", 70, None, True).coincide is True


class EjecutorProbarEnlace(EjecutorVariantes):
    """Variantes puntuadas con 70 cuyo enlace produce los mismos bytes que el objetivo."""

    PUNTUACIONES = {"parecida.c": 70}  # noqa: RUF012 - sustituye el atributo de clase de la base

    def __call__(self, comando: Any, directorio: Any, timeout_s: Any) -> Any:
        nombre = Path(comando[0]).name
        if nombre == "objdump.exe" and comando[1] == "-t":
            return TABLA_ELF if comando[2] == infra.ELF_SALIDA else TABLA_OBJETO
        if nombre == "ld.exe":
            return ""
        if nombre == "objcopy.exe":
            (directorio / comando[-1]).write_bytes(CUERPO_OBJETO)
            return ""
        return super().__call__(comando, directorio, timeout_s)


def test_probar_variantes_marca_los_bytes_iguales(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    (raiz / "src").mkdir(parents=True)
    (raiz / "src" / "code_a.c").write_text(
        'INCLUDE_ASM("asm/nonmatchings/code_a", func_80036204);\n', encoding="utf-8"
    )
    (raiz / "asm" / "nonmatchings" / "code_a").mkdir(parents=True)
    (raiz / "asm" / "nonmatchings" / "code_a" / "func_80036204.s").write_text(ASM_FUNCION, encoding="utf-8")
    preparar_elf(raiz)
    (raiz / "config").mkdir()
    (raiz / infra.SIMBOLOS_PROYECTO).write_text(
        "func_80036204 = 0x80036204; // type:func size:0x4c\n", encoding="utf-8"
    )
    carpeta = crear_variantes(tmp_path / "v", ["parecida.c"])
    resultados = variantes.probar_variantes(
        raiz,
        "func_80036204",
        carpeta,
        herramientas_con_enlace(),
        script_diff=Path("diff.py"),
        ejecutar=EjecutorProbarEnlace(secciones=SALIDA_OBJDUMP),
    )
    assert [(r.nombre, r.puntuacion, r.bytes_iguales) for r in resultados] == [("parecida.c", 70, True)]
    assert resultados[0].coincide is True


# ---------------------------------------------------------------- build, diff y probar comparten opciones


def banderas(ejecutor: EjecutorC, nombre: str) -> list[list[str]]:
    """Banderas (argumentos con guion) de cada invocacion del programa ``nombre``."""
    comandos = [c for c in ejecutor.comandos if Path(c[0]).name == nombre]
    return [[a for a in c if a.startswith("-") and a != "-DNON_MATCHING"] for c in comandos]


def test_build_diff_y_probar_compilan_un_archivo_con_las_mismas_opciones(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    preparar_construccion(raiz, SCRIPT_MIXTO)
    (raiz / "src" / "a.c").write_text("s32 func_80036204(s32 x)\n{\n    return x;\n}\n", encoding="utf-8")
    (raiz / "asm" / "matchings" / "a").mkdir(parents=True)
    (raiz / "asm" / "matchings" / "a" / "func_80036204.s").write_text(ASM_FUNCION, encoding="utf-8")
    escribir_opciones(raiz, "[archivos.a]\ng = 8\n")
    secciones = SALIDA_OBJDUMP.replace("0000001d", "00000000")

    en_build = EjecutorC(secciones=secciones)
    comp.construir_mixto(raiz, REFERENCIA, herramientas_base(), herramientas_compilacion, en_build)
    en_diff = EjecutorDiff(0)
    diff.comparar_funcion(raiz, "func_80036204", herramientas_compilacion(), Path("diff.py"), en_diff)
    en_probar = EjecutorVariantes(secciones=secciones)
    carpeta = crear_variantes(tmp_path / "v", ["mejor.c"])
    variantes.probar_variantes(
        raiz,
        "func_80036204",
        carpeta,
        herramientas_compilacion(),
        script_diff=Path("diff.py"),
        ejecutar=en_probar,
    )

    for programa in ("CC1PSX.EXE", "CPPPSX.EXE"):
        assert banderas(en_build, programa) == banderas(en_diff, programa) == banderas(en_probar, programa)
    assert banderas(en_build, "CC1PSX.EXE") == [["-quiet", "-O2", "-G8", "-o"]]
    ensamblados = [b for b in banderas(en_build, "py") if "--run-assembler" in b]
    assert ensamblados and "-G8" in ensamblados[0] and "--use-comm-section" in ensamblados[0]
    assert ensamblados == [b for b in banderas(en_diff, "py") if "--run-assembler" in b]
    assert ensamblados == [b for b in banderas(en_probar, "py") if "--run-assembler" in b]

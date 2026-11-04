"""Comparacion por bytes tras enlazar: simbolos del ELF, funcion dentro del objeto y veredicto final."""

from pathlib import Path
from typing import Any

from psxdecomp.construccion.compilacion import HerramientasCompilacion
from psxdecomp.construccion.infraestructura import ProcesoError
from psxdecomp.diff import comparacion as diff
from psxdecomp.diff import enlace_diff

from construccion.test_compilacion import herramientas

from .test_comparacion import ASM_FUNCION, EJECUTABLE, RUTAS, EjecutorDiff, comparar_funcion

ELF = "salida/EJEC_001.elf"
TABLA_ELF = (
    "salida/EJEC_001.elf:     file format elf32-tradlittlemips\n\n"
    "SYMBOL TABLE:\n"
    "ffffffff80100100 g     F .text\t0000004c rutina_a\n"
    "ffffffff80100200 g     O .sbss\t00000004 D_80100200\n"
    "00000000         *UND*\t00000000 externo\n"
    "ffffffff80100000 g       .data\t00000000 nombre-raro\n"
    "corta\n"
)
TABLA_OBJETO = (
    "SYMBOL TABLE:\n"
    "00000010 g     F .text\t0000004c rutina_a\n"
    "00000000 g     F .text\t00000000 rutina_vacia\n"
    "00000020 g     O .data\t0000004c rutina_en_datos\n"
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
            return TABLA_ELF if comando[2] == ELF else TABLA_OBJETO
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
    base = herramientas()
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
    (raiz / "salida" / "diff").mkdir(parents=True, exist_ok=True)
    (raiz / ELF).write_bytes(b"elf")


def comparar_bytes(raiz: Path, ejecutor: EjecutorEnlace, direccion: int = 0x80100100) -> bool | None:
    return enlace_diff.bytes_coinciden(
        raiz,
        herramientas_con_enlace(),
        ejecutor,
        funcion="rutina_a",
        direccion=direccion,
        candidato="salida/diff/cand.o",
        objetivo="salida/diff/objetivo.o",
        elf=ELF,
    )


def test_simbolos_de_elf_conserva_32_bits_e_ignora_indefinidos_y_nombres_raros() -> None:
    assert enlace_diff.simbolos_de_elf(TABLA_ELF) == {"rutina_a": 0x80100100, "D_80100200": 0x80100200}


def test_texto_simbolos_ld_ordena_por_nombre() -> None:
    assert enlace_diff.texto_simbolos_ld({"b": 0x20, "a": 0x10}) == "a = 0x00000010;\nb = 0x00000020;\n"


def test_funcion_en_objeto_da_desplazamiento_y_tamano() -> None:
    assert enlace_diff.funcion_en_objeto(TABLA_OBJETO, "rutina_a") == enlace_diff.FuncionEnObjeto(0x10, 0x4C)
    assert enlace_diff.funcion_en_objeto(TABLA_OBJETO, "rutina_vacia") is None
    assert enlace_diff.funcion_en_objeto(TABLA_OBJETO, "rutina_en_datos") is None
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
    assert "-Ttext=0x801000F0" in enlaces[0]
    assert (tmp_path / "salida" / "diff" / "referencias.ld").read_text(encoding="utf-8") == (
        "D_80100200 = 0x80100200;\nrutina_a = 0x80100100;\n"
    )


def test_bytes_coinciden_distingue_bytes_distintos(tmp_path: Path) -> None:
    preparar_elf(tmp_path)
    assert comparar_bytes(tmp_path, EjecutorEnlace(70, difiere=True)) is False


def test_bytes_coinciden_no_decide_sin_los_requisitos(tmp_path: Path) -> None:
    ejecutor = EjecutorEnlace(70)
    assert comparar_bytes(tmp_path, ejecutor) is None, "sin ELF"
    assert ejecutor.comandos == []
    preparar_elf(tmp_path)
    sin_enlazador = herramientas()
    assert (
        enlace_diff.bytes_coinciden(
            tmp_path,
            sin_enlazador,
            ejecutor,
            funcion="f",
            direccion=1,
            candidato="a.o",
            objetivo="b.o",
            elf=ELF,
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
            direccion=0x80100100,
            candidato="salida/diff/cand.o",
            objetivo="salida/diff/objetivo.o",
            elf=ELF,
        )
        is None
    )


def crear_repo_diff(raiz: Path, *, con_direccion: bool = True) -> None:
    (raiz / "codigo").mkdir(parents=True)
    (raiz / "codigo" / "modulo_a.c").write_text(
        "s32 rutina_a(s32 x)\n{\n    return x;\n}\n", encoding="utf-8"
    )
    (raiz / "ensamblador" / "cerradas" / "modulo_a").mkdir(parents=True)
    (raiz / "ensamblador" / "cerradas" / "modulo_a" / "rutina_a.s").write_text(ASM_FUNCION, encoding="utf-8")
    preparar_elf(raiz)
    if con_direccion:
        (raiz / "datos").mkdir(parents=True, exist_ok=True)
        (raiz / "datos" / "simbolos.txt").write_text(
            "rutina_a = 0x80100100; // type:func size:0x4c\n", encoding="utf-8"
        )


def comparar(raiz: Path, ejecutor: EjecutorEnlace) -> diff.ResultadoDiff:
    return comparar_funcion(raiz, "rutina_a", herramientas_con_enlace(), Path("diff.py"), ejecutor)


def test_diff_con_bytes_iguales_coincide_y_cuenta_las_referencias_numericas(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    resultado = comparar(tmp_path, EjecutorEnlace(70))
    assert resultado.puntuacion == 0 and resultado.puntuacion_asm == 70
    assert resultado.bytes_iguales is True and resultado.referencias_numericas == 2
    assert resultado.coincide is True


def test_el_elf_de_la_comparacion_sale_del_nombre_del_ejecutable_del_proyecto(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    (tmp_path / ELF).unlink()
    (tmp_path / "salida" / "OTRO_002.elf").write_bytes(b"elf")
    assert comparar(tmp_path, EjecutorEnlace(70)).bytes_iguales is None
    assert EJECUTABLE == "EJEC_001.00"


def test_diff_con_bytes_distintos_no_coincide(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    resultado = comparar(tmp_path, EjecutorEnlace(70, difiere=True))
    assert resultado.bytes_iguales is False and resultado.referencias_numericas == 0
    assert resultado.coincide is False


def test_diff_no_enlaza_si_la_puntuacion_ya_es_cero_o_no_hay_direccion(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    cero = EjecutorEnlace(0)
    resultado = comparar(tmp_path, cero)
    assert resultado.coincide is True and resultado.bytes_iguales is None
    assert not [c for c in cero.comandos if Path(c[0]).name == "ld.exe"]
    (tmp_path / "datos" / "simbolos.txt").unlink()
    resultado = comparar(tmp_path, EjecutorEnlace(70))
    assert resultado.coincide is False and resultado.bytes_iguales is None


def test_una_medicion_truncada_se_resuelve_enlazando_aunque_puntue_cero(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    ejecutor = EjecutorEnlace(0)
    ejecutor.filas = [{"current": {"mnemonic": "..."}}]
    resultado = comparar(tmp_path, ejecutor)
    assert resultado.truncado is True and resultado.bytes_iguales is True
    assert resultado.coincide is True


def test_una_medicion_truncada_con_bytes_distintos_no_coincide(tmp_path: Path) -> None:
    crear_repo_diff(tmp_path)
    ejecutor = EjecutorEnlace(0, difiere=True)
    ejecutor.filas = [{"current": {"mnemonic": "..."}}]
    resultado = comparar(tmp_path, ejecutor)
    assert resultado.truncado is True and resultado.bytes_iguales is False
    assert resultado.coincide is False and resultado.puntuacion == 0
    assert RUTAS.build == "salida"

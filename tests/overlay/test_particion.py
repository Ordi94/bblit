import re
from pathlib import Path

import pytest
from tools.overlay import dominio, extraccion, particion
from tools.overlay.dominio import VarianteExtraida
from tools.reconstruccion.infraestructura import Herramientas, ProcesoError

from tests.overlay.ayudantes import FUNCIONES_SINTETICAS, Registro, construir_overlay

A = construir_overlay(1)
B = construir_overlay(2)
VARIANTE_A = VarianteExtraida("a", dominio.huella_sha256(A), len(A), ("X/A.BZZ",))
VARIANTE_B = VarianteExtraida("b", dominio.huella_sha256(B), len(B), ("X/B.BZZ",))
HERRAMIENTAS = Herramientas("py", Path("bin/as.exe"), Path("bin/ld.exe"), Path("bin/objcopy.exe"))


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    (tmp_path / "expected" / "overlay").mkdir(parents=True)
    (tmp_path / "expected" / "overlay" / "a.bin").write_bytes(A)
    (tmp_path / "expected" / "overlay" / "b.bin").write_bytes(B)
    (tmp_path / "config").mkdir()
    for identificador in ("a", "b"):
        (tmp_path / "config" / f"splat_overlay_{identificador}.yaml").write_text(
            "segments: []\n", encoding="utf-8"
        )
    return tmp_path


def con_simbolos(raiz: Path) -> Path:
    particion.generar_simbolos(raiz, [VARIANTE_A, VARIANTE_B])
    return raiz


def test_generar_simbolos_escribe_las_funciones_comunes(raiz: Path) -> None:
    funciones = particion.generar_simbolos(raiz, [VARIANTE_A, VARIANTE_B])
    assert tuple(funciones) == FUNCIONES_SINTETICAS
    texto = (raiz / "config" / "symbols_overlay.txt").read_text(encoding="utf-8")
    assert texto == dominio.texto_simbolos(FUNCIONES_SINTETICAS)
    assert "\r" not in texto


def test_generar_simbolos_exige_inicios_comunes(raiz: Path) -> None:
    distinto = bytearray(B)
    distinto[0x2000:0x2004] = (0x27BDFFD8).to_bytes(4, "little")
    (raiz / "expected" / "overlay" / "b.bin").write_bytes(bytes(distinto))
    variante = VarianteExtraida("b", dominio.huella_sha256(bytes(distinto)), len(distinto), ("X/B.BZZ",))
    with pytest.raises(ValueError, match="la variante 'b' no comparte los inicios de funcion"):
        particion.generar_simbolos(raiz, [VARIANTE_A, variante])


def test_dividir_ejecuta_splat_y_contrasta_los_conteos(raiz: Path) -> None:
    con_simbolos(raiz)
    ejecutor = Registro({})
    resumen = particion.dividir(raiz, VARIANTE_A, "py", ejecutor)
    assert resumen == particion.ResumenParticion("a", 9, 9, 0)
    assert ejecutor.comandos == [["py", "-X", "utf8", "-m", "splat", "split", "config/splat_overlay_a.yaml"]]
    assert ejecutor.directorios == [raiz]
    assert ejecutor.tiempos == [particion.TIMEOUT_SPLAT_S]


def test_dividir_es_idempotente_y_borra_la_salida_anterior(raiz: Path) -> None:
    con_simbolos(raiz)
    viejo = raiz / "asm" / "overlay" / "a" / "viejo.s"
    viejo.parent.mkdir(parents=True)
    viejo.write_text("x", encoding="utf-8")
    suelto = raiz / "build" / "overlay" / "a.elf"
    suelto.parent.mkdir(parents=True)
    suelto.write_text("x", encoding="utf-8")
    ajeno = raiz / "build" / "overlay" / "b.elf"
    ajeno.write_text("x", encoding="utf-8")
    particion.dividir(raiz, VARIANTE_A, "py", Registro({}))
    particion.dividir(raiz, VARIANTE_A, "py", Registro({}))
    assert not viejo.exists()
    assert not suelto.exists()
    assert ajeno.exists()


def test_dividir_rechaza_conteos_que_no_cuadran(raiz: Path) -> None:
    con_simbolos(raiz)
    with pytest.raises(
        ValueError, match=re.escape("variante 'a': 8 funciones en el asm y 9 en config/symbols_overlay.txt")
    ):
        particion.dividir(raiz, VARIANTE_A, "py", Registro({}, glabels=8))


def test_dividir_rechaza_palabras_sin_decodificar_en_el_texto(raiz: Path) -> None:
    con_simbolos(raiz)
    with pytest.raises(ValueError, match="variante 'a': 2 palabras sin decodificar en el texto"):
        particion.dividir(raiz, VARIANTE_A, "py", Registro({}, palabras=2))


def test_dividir_exige_script_del_enlazador(raiz: Path) -> None:
    con_simbolos(raiz)
    with pytest.raises(ProcesoError, match="no genero el script del enlazador"):
        particion.dividir(raiz, VARIANTE_A, "py", Registro({}, genera_script=False))


def test_dividir_exige_simbolos_configuracion_y_binario(raiz: Path) -> None:
    with pytest.raises(FileNotFoundError, match="ejecute primero 'simbolos'"):
        particion.dividir(raiz, VARIANTE_A, "py", Registro({}))
    (raiz / "config" / "symbols_overlay.txt").write_text("// nada\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no declara ninguna funcion"):
        particion.dividir(raiz, VARIANTE_A, "py", Registro({}))
    con_simbolos(raiz)
    (raiz / "config" / "splat_overlay_a.yaml").unlink()
    with pytest.raises(FileNotFoundError, match=re.escape("falta config/splat_overlay_a.yaml")):
        particion.dividir(raiz, VARIANTE_A, "py", Registro({}))
    (raiz / "expected" / "overlay" / "a.bin").unlink()
    with pytest.raises(FileNotFoundError, match=re.escape("falta expected/overlay/a.bin")):
        particion.dividir(raiz, VARIANTE_A, "py", Registro({}))


def preparar_construccion(raiz: Path, binarios: dict[str, bytes]) -> Registro:
    con_simbolos(raiz)
    ejecutor = Registro(binarios)
    particion.dividir(raiz, VARIANTE_A, "py", ejecutor)
    return ejecutor


def test_construir_ensambla_enlaza_y_extrae_la_imagen(raiz: Path) -> None:
    ejecutor = preparar_construccion(raiz, {"a": A})
    ejecutor.comandos.clear()
    destino = particion.construir(raiz, VARIANTE_A, HERRAMIENTAS, ejecutor)
    assert destino == raiz / "build" / "overlay" / "a.bin"
    assert destino.read_bytes() == A
    nombres = [Path(comando[0]).name for comando in ejecutor.comandos]
    assert nombres == ["as.exe", "as.exe", "ld.exe", "objcopy.exe"]
    ensamblado = ejecutor.comandos[0]
    assert ensamblado[-1] == "asm/overlay/a/codigo.s"
    assert ensamblado[ensamblado.index("-I") + 1] == "asm/overlay/a/include"
    enlace = ejecutor.comandos[2]
    assert enlace.count("-T") == 2
    assert enlace[enlace.index("-T") + 1] == "build/overlay/a.enlace.ld"
    assert "build/overlay/a_undefined_syms_auto.txt" in enlace
    guion = (raiz / "build" / "overlay" / "a.enlace.ld").read_text(encoding="utf-8")
    assert "ALIGN" not in guion
    assert guion.index("codigo.s.o(.text)") < guion.index("tablas.data.s.o(.data)")


def test_construir_omite_los_simbolos_automaticos_ausentes(raiz: Path) -> None:
    ejecutor = preparar_construccion(raiz, {"a": A})
    (raiz / "build" / "overlay" / "a_undefined_syms_auto.txt").unlink()
    ejecutor.comandos.clear()
    particion.construir(raiz, VARIANTE_A, HERRAMIENTAS, ejecutor)
    assert ejecutor.comandos[2].count("-T") == 1


def test_construir_exige_split_previo(raiz: Path) -> None:
    with pytest.raises(FileNotFoundError, match="ejecute primero 'split'"):
        particion.construir(raiz, VARIANTE_A, HERRAMIENTAS, Registro({}))
    ejecutor = preparar_construccion(raiz, {"a": A})
    (raiz / "asm" / "overlay" / "a" / "codigo.s").unlink()
    with pytest.raises(FileNotFoundError, match=re.escape("falta el fuente 'asm/overlay/a/codigo.s'")):
        particion.construir(raiz, VARIANTE_A, HERRAMIENTAS, ejecutor)


def test_construir_rechaza_objetos_ajenos_a_la_variante(raiz: Path) -> None:
    ejecutor = preparar_construccion(raiz, {"a": A})
    script = raiz / "build" / "overlay" / "a.ld"
    script.write_text("        build/overlay/b/asm/overlay/b/codigo.s.o(.text);\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no corresponde a un fuente de la variante 'a'"):
        particion.construir(raiz, VARIANTE_A, HERRAMIENTAS, ejecutor)


def test_verificar_ok_si_el_binario_es_identico(raiz: Path) -> None:
    ejecutor = preparar_construccion(raiz, {"a": A})
    particion.construir(raiz, VARIANTE_A, HERRAMIENTAS, ejecutor)
    coincide, mensaje = particion.verificar(raiz, VARIANTE_A)
    assert coincide
    assert mensaje == f"OK a sha256={VARIANTE_A.sha256} bytes={len(A)}"


def test_verificar_fail_con_el_desplazamiento_de_la_primera_diferencia(raiz: Path) -> None:
    alterado = bytearray(A)
    alterado[0x154] ^= 0xFF
    ejecutor = preparar_construccion(raiz, {"a": bytes(alterado)})
    particion.construir(raiz, VARIANTE_A, HERRAMIENTAS, ejecutor)
    coincide, mensaje = particion.verificar(raiz, VARIANTE_A)
    assert not coincide
    assert mensaje.startswith("FAIL a primera diferencia en el desplazamiento 0x154")


def test_verificar_fail_si_el_binario_es_mas_corto(raiz: Path) -> None:
    ejecutor = preparar_construccion(raiz, {"a": A[:-4]})
    particion.construir(raiz, VARIANTE_A, HERRAMIENTAS, ejecutor)
    coincide, mensaje = particion.verificar(raiz, VARIANTE_A)
    assert not coincide
    assert f"0x{len(A) - 4:X}" in mensaje


def test_verificar_rechaza_binarios_enormes(raiz: Path) -> None:
    enorme = raiz / "build" / "overlay" / "a.bin"
    enorme.parent.mkdir(parents=True)
    enorme.write_bytes(bytes(dominio.TAMANO_HUECO + 4))
    coincide, mensaje = particion.verificar(raiz, VARIANTE_A)
    assert not coincide
    assert mensaje == "FAIL a el binario reconstruido excede el hueco del overlay"


def test_las_rutas_de_la_cadena_quedan_dentro_de_las_carpetas_del_overlay(raiz: Path) -> None:
    ejecutor = preparar_construccion(raiz, {"a": A})
    particion.construir(raiz, VARIANTE_A, HERRAMIENTAS, ejecutor)
    escritos = {p.relative_to(raiz).parts[0] for p in raiz.rglob("*") if p.is_file()}
    assert escritos == {"expected", "config", "asm", "build"}
    assert all(p.relative_to(raiz).parts[1] == "overlay" for p in (raiz / "build").rglob("*") if p.is_file())
    assert all(p.relative_to(raiz).parts[1] == "overlay" for p in (raiz / "asm").rglob("*") if p.is_file())
    assert extraccion.CARPETA_EXTRAIDOS == Path("expected") / "overlay"


def test_verificar_sin_binario_reconstruido_es_fail_de_esa_variante(raiz: Path) -> None:
    coincide, mensaje = particion.verificar(raiz, VARIANTE_A)
    assert not coincide
    assert mensaje == "FAIL a el binario reconstruido no existe"


def test_verificar_sigue_exigiendo_el_binario_extraido(raiz: Path) -> None:
    (raiz / "expected" / "overlay" / "a.bin").unlink()
    with pytest.raises(FileNotFoundError, match=re.escape("falta expected/overlay/a.bin")):
        particion.verificar(raiz, VARIANTE_A)


def test_salidas_de_construccion_no_incluyen_la_salida_de_split() -> None:
    assert particion.salidas_de_construccion("a") == (
        "build/overlay/a",
        "build/overlay/a.enlace.ld",
        "build/overlay/a.elf",
        "build/overlay/a.map",
        "build/overlay/a.bin",
    )


def test_invalidar_salida_elimina_la_construccion_y_conserva_la_de_split(raiz: Path) -> None:
    ejecutor = preparar_construccion(raiz, {"a": A})
    particion.construir(raiz, VARIANTE_A, HERRAMIENTAS, ejecutor)
    eliminadas = particion.invalidar_salida(raiz, "a")
    assert eliminadas == [
        "build/overlay/a",
        "build/overlay/a.enlace.ld",
        "build/overlay/a.elf",
        "build/overlay/a.bin",
    ]
    assert not (raiz / "build" / "overlay" / "a").exists()
    assert (raiz / "build" / "overlay" / "a.ld").is_file()
    assert (raiz / "build" / "overlay" / "a_undefined_syms_auto.txt").is_file()
    assert (raiz / "asm" / "overlay" / "a" / "codigo.s").is_file()


def test_invalidar_salida_sin_construccion_previa_no_es_un_error(raiz: Path) -> None:
    assert particion.invalidar_salida(raiz, "a") == []
    preparar_construccion(raiz, {"a": A})
    assert particion.invalidar_salida(raiz, "a") == []


def test_construir_elimina_el_binario_anterior_antes_de_ensamblar(raiz: Path) -> None:
    ejecutor = preparar_construccion(raiz, {"a": A})
    particion.construir(raiz, VARIANTE_A, HERRAMIENTAS, ejecutor)
    visto: list[bool] = []

    def fallar_al_ensamblar(comando: object, directorio: Path, timeout_s: int) -> str:
        visto.append((raiz / "build" / "overlay" / "a.bin").exists())
        raise ProcesoError("opcode inexistente")

    with pytest.raises(ProcesoError, match="opcode inexistente"):
        particion.construir(raiz, VARIANTE_A, HERRAMIENTAS, fallar_al_ensamblar)
    assert visto == [False]
    assert particion.verificar(raiz, VARIANTE_A) == (False, "FAIL a el binario reconstruido no existe")


def test_construir_sin_split_previo_conserva_la_salida_existente(raiz: Path) -> None:
    binario = raiz / "build" / "overlay" / "a.bin"
    binario.parent.mkdir(parents=True)
    binario.write_bytes(A)
    with pytest.raises(FileNotFoundError, match="ejecute primero 'split'"):
        particion.construir(raiz, VARIANTE_A, HERRAMIENTAS, Registro({}))
    assert binario.read_bytes() == A

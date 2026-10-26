"""Reglas de negocio de la seccion de progreso del README: cifras, marcadores, finales de linea."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import cli, readme_progreso
from tools.reconstruccion.fuentes_c import EstadoFuncion, MarcaAsm
from tools.reconstruccion.infraestructura import ProcesoError
from tools.reconstruccion.progreso import FuncionSimbolo, calcular_progreso
from tools.reconstruccion.readme_progreso import (
    MARCA_FIN,
    MARCA_INICIO,
    ResumenJuego,
    aplicar_seccion,
    generar_seccion,
    resumir_juego,
)

from .test_infraestructura import REFERENCIA, referencia_json

SHA = "0fad70d9b4cb324d78f113f7fd70c0aa954388fefad01af373509e0473c87df0"
RESUMEN = ResumenJuego(450, 362, 60, 16, 12, 59692, 201416, 29.64)
SECCION = generar_seccion(RESUMEN, "2026-10-26", "bf5ae56", SHA)
README = "# titulo\n\nPrimer parrafo\nsegunda linea.\n\nSegundo parrafo.\n\n## Otra\n"


def progreso_de_prueba() -> Any:
    simbolos = [
        FuncionSimbolo("func_80014AC4", 0x80014AC4, 0x10),
        FuncionSimbolo("func_80014AD4", 0x80014AD4, 0x20),
        FuncionSimbolo("func_80014AF4", 0x80014AF4, 0x30),
        FuncionSimbolo("func_80014B24", 0x80014B24, 0x40),
        FuncionSimbolo("func_80014B64", 0x80014B64, 0x50),
        FuncionSimbolo("func_80045DA0", 0x80045DA0, 0x60),
        FuncionSimbolo("func_80045E00", 0x80045E00, 0x70),
    ]
    estados = {
        "src/a.c": {
            "func_80014AC4": EstadoFuncion.C,
            "func_80014AD4": EstadoFuncion.NO_COINCIDENTE,
            "func_80014AF4": EstadoFuncion.ENSAMBLADOR,
            "func_80014B24": EstadoFuncion.ENSAMBLADOR,
            "func_80045DA0": EstadoFuncion.NO_COINCIDENTE,
            "func_80045E00": EstadoFuncion.ENSAMBLADOR,
        }
    }
    marcas = {
        "src/a.c": {
            "func_80014AF4": MarcaAsm.MANUSCRITA,
            "func_80014B24": MarcaAsm.JUSTIFICADA,
            "func_80045E00": MarcaAsm.MANUSCRITA,
        }
    }
    return calcular_progreso(simbolos, estados, None, {}, marcas)


def test_las_cifras_del_juego_ignoran_las_librerias_y_el_resto_es_sin_traducir() -> None:
    resumen = resumir_juego(progreso_de_prueba())
    assert (resumen.total, resumen.coincidentes, resumen.no_coincidentes) == (5, 1, 1)
    assert (resumen.manuscritas, resumen.sin_traducir) == (1, 2)
    assert (resumen.bytes_coincidentes, resumen.bytes_total, resumen.porcentaje) == (16, 0xF0, 6.67)


def test_sin_codigo_del_juego_todas_las_cifras_son_cero_y_el_porcentaje_no_divide() -> None:
    resumen = resumir_juego(calcular_progreso([], {}, None))
    assert resumen == ResumenJuego(0, 0, 0, 0, 0, 0, 0, 0.0)
    assert "| Porcentaje de bytes coincidentes | 0.00 % |" in generar_seccion(resumen, "2026-10-26", "a", SHA)


def test_sin_traducir_nunca_es_negativo_si_la_tabla_y_las_fuentes_discrepan() -> None:
    progreso = progreso_de_prueba()
    exceso = replace(progreso, manuscritas_juego=progreso.juego)
    assert resumir_juego(exceso).sin_traducir == 0


def test_la_seccion_trae_fecha_hash_tabla_y_comandos_de_reproduccion() -> None:
    assert SECCION.startswith(MARCA_INICIO + "\n## Progreso\n")
    assert SECCION.endswith("```\n" + MARCA_FIN)
    assert "2026-10-26" in SECCION and "`bf5ae56`" in SECCION
    for fila in (
        "| Funciones del juego | 450 |",
        "| Coincidentes byte a byte | 362 |",
        "| En C, pendientes de afinar (`NON_MATCHING`) | 60 |",
        "| Escritas a mano, conservadas en ensamblador | 16 |",
        "| Sin traducir | 12 |",
        "| Bytes coincidentes | 59692 de 201416 |",
        "| Porcentaje de bytes coincidentes | 29.64 % |",
    ):
        assert fila in SECCION
    for orden in ("clean", "split", "build", "verify", "progreso", "diff <funcion>"):
        assert f"python tools/build.py {orden}" in SECCION
    assert SHA in SECCION
    assert "\r" not in SECCION


def test_sin_marcadores_la_seccion_se_inserta_tras_el_primer_parrafo_sin_contar_el_titulo() -> None:
    nuevo = aplicar_seccion(README, SECCION)
    assert nuevo == (
        "# titulo\n\nPrimer parrafo\nsegunda linea.\n\n" + SECCION + "\n\nSegundo parrafo.\n\n## Otra\n"
    )


def test_con_marcadores_solo_se_reemplaza_lo_que_hay_entre_ellos() -> None:
    previo = "intro\n\n" + MARCA_INICIO + "\nviejo\n" + MARCA_FIN + "\n\nfinal\n"
    assert aplicar_seccion(previo, SECCION) == "intro\n\n" + SECCION + "\n\nfinal\n"


def test_aplicar_dos_veces_la_misma_seccion_no_cambia_nada() -> None:
    una = aplicar_seccion(README, SECCION)
    assert aplicar_seccion(una, SECCION) == una


@pytest.mark.parametrize(
    "texto",
    [
        f"a\n\n{MARCA_INICIO}\n{MARCA_FIN}\n{MARCA_INICIO}\n{MARCA_FIN}\n",
        f"a\n\n{MARCA_INICIO}\nsin cierre\n",
        f"a\n\n{MARCA_FIN}\nsin apertura\n",
        f"a\n\n{MARCA_FIN}\n{MARCA_INICIO}\n",
    ],
)
def test_marcadores_duplicados_huerfanos_o_invertidos_se_rechazan(texto: str) -> None:
    with pytest.raises(ValueError, match=r"marcadores de progreso|antes del de inicio"):
        aplicar_seccion(texto, SECCION)


def test_un_readme_con_crlf_conserva_sus_finales_de_linea_en_la_insercion_y_el_reemplazo() -> None:
    crlf = README.replace("\n", "\r\n")
    nuevo = aplicar_seccion(crlf, SECCION)
    assert nuevo.count("\n") == nuevo.count("\r\n")
    assert nuevo == aplicar_seccion(crlf, SECCION.replace("\n", "\n"))
    otra = generar_seccion(RESUMEN, "2026-10-27", "1234abc", SHA)
    reemplazado = aplicar_seccion(nuevo, otra)
    assert reemplazado.count("\n") == reemplazado.count("\r\n")
    assert "2026-10-27" in reemplazado and "2026-10-26" not in reemplazado


def test_un_readme_con_lf_no_recibe_ningun_cr() -> None:
    assert "\r" not in aplicar_seccion(README, SECCION)


def test_un_readme_mixto_sin_marcadores_solo_toca_la_seccion_nueva() -> None:
    mixto = "# t\r\n\r\nparrafo\n\nfin\n"
    nuevo = aplicar_seccion(mixto, SECCION)
    assert nuevo.startswith("# t\r\n\r\nparrafo\n")
    assert nuevo.endswith("\n\nfin\n")


def test_un_readme_sin_parrafo_ni_salto_final_recibe_la_seccion_al_final() -> None:
    assert aplicar_seccion("", SECCION) == SECCION + "\n"
    assert aplicar_seccion("# solo titulo", SECCION) == "# solo titulo\n\n" + SECCION + "\n"
    assert aplicar_seccion("unico parrafo", SECCION) == "unico parrafo\n\n" + SECCION + "\n"


def test_si_el_parrafo_no_va_seguido_de_linea_en_blanco_se_separa_la_seccion() -> None:
    assert aplicar_seccion("parrafo\n## Siguiente\n", SECCION) == (
        "parrafo\n\n" + SECCION + "\n\n## Siguiente\n"
    )


def escribir(ruta: Path, contenido: str) -> None:
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        archivo.write(contenido)


def leer(ruta: Path) -> str:
    with ruta.open(encoding="utf-8", newline="") as archivo:
        return archivo.read()


def test_actualizar_readme_escribe_una_vez_y_la_segunda_ejecucion_no_cambia_el_archivo(
    tmp_path: Path,
) -> None:
    escribir(tmp_path / "README.md", README)
    progreso = progreso_de_prueba()
    assert readme_progreso.actualizar_readme(tmp_path, progreso, "2026-10-26", "bf5ae56", SHA) is True
    primero = (tmp_path / "README.md").read_bytes()
    assert readme_progreso.actualizar_readme(tmp_path, progreso, "2026-10-26", "bf5ae56", SHA) is False
    assert (tmp_path / "README.md").read_bytes() == primero


def test_actualizar_readme_conserva_crlf_del_archivo(tmp_path: Path) -> None:
    escribir(tmp_path / "README.md", README.replace("\n", "\r\n"))
    readme_progreso.actualizar_readme(tmp_path, progreso_de_prueba(), "2026-10-26", "bf5ae56", SHA)
    bruto = (tmp_path / "README.md").read_bytes()
    assert bruto.count(b"\n") == bruto.count(b"\r\n")


def test_sin_readme_se_informa_con_error_de_archivo_ausente(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"falta README.md"):
        readme_progreso.actualizar_readme(tmp_path, progreso_de_prueba(), "2026-10-26", "a", SHA)


def test_un_readme_enorme_o_que_no_es_utf8_se_rechaza(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_bytes(b"x" * (readme_progreso.MAX_BYTES_README + 1))
    with pytest.raises(ValueError, match="excede el tamano permitido"):
        readme_progreso.actualizar_readme(tmp_path, progreso_de_prueba(), "2026-10-26", "a", SHA)
    (tmp_path / "README.md").write_bytes(b"\xff\xfe\xfa")
    with pytest.raises(ValueError, match="codec"):
        readme_progreso.actualizar_readme(tmp_path, progreso_de_prueba(), "2026-10-26", "a", SHA)


@pytest.mark.parametrize(
    ("salida", "esperado"),
    [("bf5ae56\n", "bf5ae56"), ("no es un hash", "desconocido"), ("", "desconocido")],
)
def test_el_hash_corto_solo_acepta_hexadecimal(tmp_path: Path, salida: str, esperado: str) -> None:
    assert readme_progreso.obtener_hash_corto(tmp_path, lambda *_: salida) == esperado


@pytest.mark.parametrize("error", [ProcesoError("git fallo"), FileNotFoundError("git")])
def test_sin_git_el_hash_es_desconocido_y_no_se_interrumpe_la_medicion(
    tmp_path: Path, error: Exception
) -> None:
    def fallar(*_: Any) -> str:
        raise error

    assert readme_progreso.obtener_hash_corto(tmp_path, fallar) == "desconocido"


def preparar_repo(raiz: Path, readme: str | None) -> None:
    (raiz / "config").mkdir(parents=True)
    (raiz / "config" / "symbols.txt").write_text(
        "func_80014AC4 = 0x80014AC4; // type:func size:0x10\n", encoding="utf-8"
    )
    (raiz / "config" / "ejecutable.json").write_text(json.dumps(referencia_json()), encoding="utf-8")
    (raiz / "src").mkdir()
    (raiz / "src" / "code_a.c").write_text("s32 func_80014AC4(void)\n{\n    return 0;\n}\n", encoding="utf-8")
    if readme is not None:
        escribir(raiz / "README.md", readme)


@pytest.fixture
def fecha_fija(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_fecha_actual", lambda: "2026-10-26")


def test_progreso_actualiza_el_readme_con_el_hash_del_commit_y_es_idempotente(
    tmp_path: Path, fecha_fija: None, capsys: pytest.CaptureFixture[str]
) -> None:
    preparar_repo(tmp_path, README)
    ejecutor = lambda *_: "abc1234\n"  # noqa: E731
    assert cli.main(["progreso"], {}, tmp_path, ejecutor) == 0
    assert "README.md: seccion de progreso actualizada" in capsys.readouterr().out
    texto = leer(tmp_path / "README.md")
    assert "`abc1234`" in texto and "| Coincidentes byte a byte | 1 |" in texto and REFERENCIA.sha256 in texto
    assert cli.main(["progreso"], {}, tmp_path, ejecutor) == 0
    assert "README.md: seccion de progreso sin cambios" in capsys.readouterr().out
    assert leer(tmp_path / "README.md") == texto


def test_progreso_con_sin_readme_no_toca_el_archivo(tmp_path: Path, fecha_fija: None) -> None:
    preparar_repo(tmp_path, README)
    assert cli.main(["progreso", "--sin-readme"], {}, tmp_path, lambda *_: "abc1234") == 0
    assert leer(tmp_path / "README.md") == README


def test_progreso_sin_readme_avisa_y_termina_bien(
    tmp_path: Path, fecha_fija: None, capsys: pytest.CaptureFixture[str]
) -> None:
    preparar_repo(tmp_path, None)
    assert cli.main(["progreso"], {}, tmp_path, lambda *_: "abc1234") == 0
    assert "aviso: no existe README.md" in capsys.readouterr().err
    assert not (tmp_path / "README.md").exists()


AVISO_README = "aviso: no se pudo actualizar la seccion de progreso del README: "


def _progreso_con_causa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, causa: str, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str, str]:
    """Ejecuta ``progreso`` con una causa de fallo del README y da (codigo, stdout, stderr)."""
    roto = f"x\n\n{MARCA_INICIO}\n{MARCA_INICIO}\n{MARCA_FIN}\n"
    preparar_repo(tmp_path, roto if causa == "marcadores" else README)
    if causa == "referencia_ausente":
        (tmp_path / "config" / "ejecutable.json").unlink()
    elif causa == "referencia_invalida":
        (tmp_path / "config" / "ejecutable.json").write_text("{no es json", encoding="utf-8")
    elif causa == "readme_no_escribible":

        def fallar(*_: Any, **__: Any) -> bool:
            raise PermissionError(13, "Acceso denegado", str(tmp_path / "README.md"))

        monkeypatch.setattr(readme_progreso, "actualizar_readme", fallar)
    codigo = cli.main(["progreso"], {}, tmp_path, lambda *_: "abc1234")
    captura = capsys.readouterr()
    return codigo, captura.out, captura.err


@pytest.mark.parametrize(
    ("causa", "motivo"),
    [
        ("referencia_ausente", "no se encontro config/ejecutable.json"),
        ("referencia_invalida", "config/ejecutable.json no es JSON valido"),
        ("readme_no_escribible", "Acceso denegado"),
        ("marcadores", "marcadores de progreso"),
    ],
)
def test_un_fallo_del_readme_no_aborta_progreso_y_deja_los_demas_resultados(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fecha_fija: None,
    capsys: pytest.CaptureFixture[str],
    causa: str,
    motivo: str,
) -> None:
    codigo, salida, errores = _progreso_con_causa(tmp_path, monkeypatch, causa, capsys)
    assert codigo == 0
    assert (tmp_path / "docs" / "PROGRESO.md").is_file()
    assert (tmp_path / "build" / "progreso.json").is_file()
    assert "docs/PROGRESO.md y build/progreso.json escritos" in salida
    assert "README.md: seccion de progreso" not in salida
    assert AVISO_README in errores and motivo in errores
    assert str(tmp_path) not in errores


def test_un_fallo_del_readme_no_cambia_los_demas_avisos_ni_el_codigo_de_salida(
    tmp_path: Path, fecha_fija: None, capsys: pytest.CaptureFixture[str]
) -> None:
    preparar_repo(tmp_path, README)
    (tmp_path / "config" / "ejecutable.json").unlink()
    (tmp_path / "asm").mkdir()
    (tmp_path / "asm" / "x.s").write_text("glabel a\nglabel b\n", encoding="utf-8")
    codigo = cli.main(["progreso"], {}, tmp_path, lambda *_: "abc1234")
    errores = capsys.readouterr().err
    assert codigo == 1
    assert AVISO_README in errores
    assert "glabel en asm/ + 1 funciones en C no suman las 1 de la tabla" in errores
    assert leer(tmp_path / "README.md") == README


def test_la_fecha_actual_tiene_formato_iso() -> None:
    assert len(cli._fecha_actual()) == 10 and cli._fecha_actual()[4] == "-"

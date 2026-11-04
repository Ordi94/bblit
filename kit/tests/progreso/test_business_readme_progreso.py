"""Reglas de negocio de la seccion de progreso del README: cifras, marcadores, finales de linea y textos."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from psxdecomp.cli import main, orden_progreso
from psxdecomp.construccion.infraestructura import ProcesoError
from psxdecomp.dominio import Proyecto
from psxdecomp.progreso import readme
from psxdecomp.progreso.readme import (
    MARCA_FIN,
    MARCA_INICIO,
    ResumenJuego,
    aplicar_seccion,
    generar_seccion,
    resumir_juego,
)

from progreso.ayudantes import (
    COMANDO_PROPIO,
    PROYECTO_BASE,
    PROYECTO_PROPIO,
    SHA_INVENTADO,
    EstadoFuncion,
    FuncionSimbolo,
    MarcaAsm,
    calcular_progreso,
    crear_proyecto_propio,
    escribir,
    leer,
)

SHA = SHA_INVENTADO
RESUMEN = ResumenJuego(450, 362, 60, 16, 12, 59692, 201416, 29.64)
SECCION = generar_seccion(RESUMEN, "2026-10-26", "bf5ae56", SHA, PROYECTO_PROPIO)
README = "# titulo\n\nPrimer parrafo\nsegunda linea.\n\nSegundo parrafo.\n\n## Otra\n"
AVISO_README = "aviso: no se pudo actualizar la seccion de progreso del README: "


def progreso_de_prueba() -> Any:
    simbolos = [
        FuncionSimbolo("rutina_a", 0x80110100, 0x10),
        FuncionSimbolo("rutina_b", 0x80110110, 0x20),
        FuncionSimbolo("rutina_c", 0x80110130, 0x30),
        FuncionSimbolo("rutina_d", 0x80110160, 0x40),
        FuncionSimbolo("rutina_e", 0x801101A0, 0x50),
        FuncionSimbolo("rutina_f", 0x80120000, 0x60),
        FuncionSimbolo("rutina_g", 0x80120060, 0x70),
    ]
    estados = {
        "src/a.c": {
            "rutina_a": EstadoFuncion.C,
            "rutina_b": EstadoFuncion.NO_COINCIDENTE,
            "rutina_c": EstadoFuncion.ENSAMBLADOR,
            "rutina_d": EstadoFuncion.ENSAMBLADOR,
            "rutina_f": EstadoFuncion.NO_COINCIDENTE,
            "rutina_g": EstadoFuncion.ENSAMBLADOR,
        }
    }
    marcas = {
        "src/a.c": {
            "rutina_c": MarcaAsm.MANUSCRITA,
            "rutina_d": MarcaAsm.JUSTIFICADA,
            "rutina_g": MarcaAsm.MANUSCRITA,
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
    assert "| Porcentaje de bytes coincidentes | 0.00 % |" in generar_seccion(
        resumen, "2026-10-26", "a", SHA, PROYECTO_PROPIO
    )


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
        assert f"{COMANDO_PROPIO} {orden}" in SECCION
    assert SHA in SECCION
    assert "\r" not in SECCION


def test_el_comando_la_variable_del_disco_y_la_funcion_de_ejemplo_salen_del_manifiesto() -> None:
    assert f"`{COMANDO_PROPIO} progreso`;" in SECCION
    assert "copia propia del disco en `JUEGO_DISC`" in SECCION
    assert f"{COMANDO_PROPIO} verify      # debe imprimir OK con SHA-256 {SHA}" in SECCION
    assert (
        f"{COMANDO_PROPIO} diff <funcion>   # comprueba una funcion (por ejemplo rutina_ejemplo)" in SECCION
    )


def test_sin_funcion_de_ejemplo_la_seccion_no_cita_ninguna_y_el_comando_por_defecto_es_el_del_kit() -> None:
    seccion = generar_seccion(RESUMEN, "2026-10-26", "bf5ae56", SHA, PROYECTO_BASE)
    assert "python -m psxdecomp.cli diff <funcion>   # comprueba una funcion\n" in seccion
    assert "por ejemplo" not in seccion
    assert "`PSXDECOMP_DISC`" in seccion


def test_la_macro_de_no_coincidente_de_la_fila_es_la_del_manifiesto() -> None:
    propio = replace(
        PROYECTO_PROPIO, convenciones=replace(PROYECTO_PROPIO.convenciones, macro_no_coincidente="PENDIENTE")
    )
    assert "| En C, pendientes de afinar (`PENDIENTE`) | 60 |" in generar_seccion(
        RESUMEN, "2026-10-26", "bf5ae56", SHA, propio
    )


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


MARCADORES_INVALIDOS = [
    f"a\n\n{MARCA_INICIO}\n{MARCA_FIN}\n{MARCA_INICIO}\n{MARCA_FIN}\n",
    f"a\n\n{MARCA_INICIO}\nsin cierre\n",
    f"a\n\n{MARCA_FIN}\nsin apertura\n",
    f"a\n\n{MARCA_FIN}\n{MARCA_INICIO}\n",
    f"a\n\n{MARCA_INICIO}\n{MARCA_INICIO}\n{MARCA_FIN}\n",
    f"a\n\n{MARCA_INICIO}\n{MARCA_FIN}\n{MARCA_FIN}\n",
]


@pytest.mark.parametrize("texto", MARCADORES_INVALIDOS)
def test_marcadores_duplicados_huerfanos_o_invertidos_se_rechazan(texto: str) -> None:
    with pytest.raises(ValueError, match=r"marcadores de progreso|antes del de inicio"):
        aplicar_seccion(texto, SECCION)


def test_el_error_de_marcadores_nombra_el_archivo_que_se_le_indica() -> None:
    with pytest.raises(ValueError, match=r"^LEEME.md: los marcadores"):
        aplicar_seccion(MARCADORES_INVALIDOS[1], SECCION, "LEEME.md")


def test_un_readme_con_crlf_conserva_sus_finales_de_linea_en_la_insercion_y_el_reemplazo() -> None:
    crlf = README.replace("\n", "\r\n")
    nuevo = aplicar_seccion(crlf, SECCION)
    assert nuevo.count("\n") == nuevo.count("\r\n")
    otra = generar_seccion(RESUMEN, "2026-10-27", "1234abc", SHA, PROYECTO_PROPIO)
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


def actualizar(raiz: Path, proyecto: Proyecto = PROYECTO_PROPIO) -> bool:
    return readme.actualizar_readme(
        raiz, progreso_de_prueba(), "2026-10-26", "bf5ae56", SHA, proyecto=replace(proyecto, raiz=raiz)
    )


def test_actualizar_readme_escribe_una_vez_y_la_segunda_ejecucion_no_cambia_el_archivo(
    tmp_path: Path,
) -> None:
    escribir(tmp_path / "LEEME.md", README)
    assert actualizar(tmp_path) is True
    primero = (tmp_path / "LEEME.md").read_bytes()
    assert actualizar(tmp_path) is False
    assert (tmp_path / "LEEME.md").read_bytes() == primero


def test_actualizar_readme_usa_la_ruta_del_manifiesto_y_su_defecto() -> None:
    assert PROYECTO_PROPIO.rutas.readme == "LEEME.md"
    assert PROYECTO_BASE.rutas.readme == "README.md"


def test_actualizar_readme_conserva_crlf_del_archivo(tmp_path: Path) -> None:
    escribir(tmp_path / "LEEME.md", README.replace("\n", "\r\n"))
    actualizar(tmp_path)
    bruto = (tmp_path / "LEEME.md").read_bytes()
    assert bruto.count(b"\n") == bruto.count(b"\r\n")


def test_sin_readme_se_informa_con_error_de_archivo_ausente(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"falta LEEME.md"):
        actualizar(tmp_path)


def test_un_readme_enorme_o_que_no_es_utf8_se_rechaza(tmp_path: Path) -> None:
    (tmp_path / "LEEME.md").write_bytes(b"x" * (readme.MAX_BYTES_README + 1))
    with pytest.raises(ValueError, match=r"LEEME.md excede el tamano permitido"):
        actualizar(tmp_path)
    (tmp_path / "LEEME.md").write_bytes(b"\xff\xfe\xfa")
    with pytest.raises(ValueError, match="codec"):
        actualizar(tmp_path)


@pytest.mark.parametrize(
    ("salida", "esperado"),
    [("bf5ae56\n", "bf5ae56"), ("no es un hash", "desconocido"), ("", "desconocido")],
)
def test_el_hash_corto_solo_acepta_hexadecimal(tmp_path: Path, salida: str, esperado: str) -> None:
    assert readme.obtener_hash_corto(tmp_path, lambda *_: salida) == esperado


@pytest.mark.parametrize("error", [ProcesoError("git fallo"), FileNotFoundError("git")])
def test_sin_git_el_hash_es_desconocido_y_no_se_interrumpe_la_medicion(
    tmp_path: Path, error: Exception
) -> None:
    def fallar(*_: Any) -> str:
        raise error

    assert readme.obtener_hash_corto(tmp_path, fallar) == "desconocido"


def ejecutar(raiz: Path, *argv: str) -> int:
    return main(list(argv), {}, lambda *_: "abc1234\n", raiz=raiz)


@pytest.fixture
def fecha_fija(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orden_progreso, "_fecha_actual", lambda: "2026-10-26")


def test_progreso_actualiza_el_readme_con_el_hash_del_commit_y_es_idempotente(
    tmp_path: Path, fecha_fija: None, capsys: pytest.CaptureFixture[str]
) -> None:
    crear_proyecto_propio(tmp_path, con_readme=README)
    assert ejecutar(tmp_path, "progreso") == 0
    assert "LEEME.md: seccion de progreso actualizada" in capsys.readouterr().out
    texto = leer(tmp_path / "LEEME.md")
    assert "`abc1234`" in texto and "| Coincidentes byte a byte | 1 |" in texto and SHA in texto
    assert ejecutar(tmp_path, "progreso") == 0
    assert "LEEME.md: seccion de progreso sin cambios" in capsys.readouterr().out
    assert leer(tmp_path / "LEEME.md") == texto


def test_progreso_con_sin_readme_no_toca_el_archivo(tmp_path: Path, fecha_fija: None) -> None:
    crear_proyecto_propio(tmp_path, con_readme=README)
    assert ejecutar(tmp_path, "progreso", "--sin-readme") == 0
    assert leer(tmp_path / "LEEME.md") == README


def test_progreso_sin_readme_avisa_y_termina_bien(
    tmp_path: Path, fecha_fija: None, capsys: pytest.CaptureFixture[str]
) -> None:
    crear_proyecto_propio(tmp_path)
    assert ejecutar(tmp_path, "progreso") == 0
    assert "aviso: no existe LEEME.md" in capsys.readouterr().err
    assert not (tmp_path / "LEEME.md").exists()


def _progreso_con_causa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, causa: str, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str, str]:
    """Ejecuta ``progreso`` con una causa de fallo del README y da (codigo, stdout, stderr)."""
    roto = f"x\n\n{MARCA_INICIO}\n{MARCA_INICIO}\n{MARCA_FIN}\n"
    crear_proyecto_propio(tmp_path, con_readme=roto if causa == "marcadores" else README)
    if causa == "referencia_ausente":
        (tmp_path / "datos" / "ejecutable.json").unlink()
    elif causa == "referencia_invalida":
        (tmp_path / "datos" / "ejecutable.json").write_text("{no es json", encoding="utf-8")
    elif causa == "readme_no_escribible":

        def fallar(*_: Any, **__: Any) -> bool:
            raise PermissionError(13, "Acceso denegado", str(tmp_path / "LEEME.md"))

        monkeypatch.setattr(readme, "actualizar_readme", fallar)
    codigo = ejecutar(tmp_path, "progreso")
    captura = capsys.readouterr()
    return codigo, captura.out, captura.err


@pytest.mark.parametrize(
    ("causa", "motivo"),
    [
        ("referencia_ausente", "no se encontro datos/ejecutable.json"),
        ("referencia_invalida", "datos/ejecutable.json no es JSON valido"),
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
    assert (tmp_path / "notas" / "avance.md").is_file()
    assert (tmp_path / "salida" / "progreso.json").is_file()
    assert "notas/avance.md y salida/progreso.json escritos" in salida
    assert "LEEME.md: seccion de progreso" not in salida
    assert AVISO_README in errores and motivo in errores
    assert str(tmp_path) not in errores


def test_un_fallo_del_readme_no_cambia_los_demas_avisos_ni_el_codigo_de_salida(
    tmp_path: Path, fecha_fija: None, capsys: pytest.CaptureFixture[str]
) -> None:
    crear_proyecto_propio(tmp_path, con_readme=README)
    (tmp_path / "datos" / "ejecutable.json").unlink()
    escribir(tmp_path / "ensamblador" / "x.s", "glabel a\nglabel b\n")
    codigo = ejecutar(tmp_path, "progreso")
    errores = capsys.readouterr().err
    assert codigo == 1
    assert AVISO_README in errores
    assert "glabel en ensamblador/ + 1 funciones en C no suman las 2 de la tabla" in errores
    assert leer(tmp_path / "LEEME.md") == README


@pytest.mark.parametrize("marcadores", MARCADORES_INVALIDOS)
@pytest.mark.parametrize(("glabel", "esperado"), [(1, 0), (5, 1)])
def test_con_marcadores_del_readme_desparejados_o_duplicados_progreso_no_aborta(
    tmp_path: Path,
    fecha_fija: None,
    capsys: pytest.CaptureFixture[str],
    marcadores: str,
    glabel: int,
    esperado: int,
) -> None:
    sano = tmp_path / "sano"
    roto = tmp_path / "roto"
    for carpeta, contenido in ((sano, README), (roto, marcadores)):
        crear_proyecto_propio(carpeta, con_readme=contenido)
        escribir(carpeta / "ensamblador" / "x.s", "glabel x\n" * glabel)
    assert ejecutar(sano, "progreso", "--sin-readme") == esperado
    capsys.readouterr()
    assert ejecutar(roto, "progreso") == esperado
    errores = capsys.readouterr().err
    assert AVISO_README in errores
    assert "marcadores de progreso" in errores or "antes del de inicio" in errores
    assert str(roto) not in errores
    assert leer(roto / "LEEME.md") == marcadores
    assert (roto / "notas" / "avance.md").read_bytes() == (sano / "notas" / "avance.md").read_bytes()
    assert (roto / "salida" / "progreso.json").read_bytes() == (
        sano / "salida" / "progreso.json"
    ).read_bytes()


def test_la_fecha_actual_tiene_formato_iso() -> None:
    assert len(orden_progreso._fecha_actual()) == 10 and orden_progreso._fecha_actual()[4] == "-"

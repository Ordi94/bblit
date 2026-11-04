"""Ordenes comunes de la linea de ordenes con un proyecto inventado y ejecutores simulados."""

from pathlib import Path
from typing import Any

import pytest
from psxdecomp.cli import main
from psxdecomp.construccion import infraestructura as infra_kit

from ordenes.ayudantes import EJECUTABLE, REFERENCIA, Escenario, Registro, crear_escenario


@pytest.fixture
def escenario(tmp_path: Path) -> Escenario:
    return crear_escenario(tmp_path)


def ejecutar(escenario: Escenario, *argv: str, entorno: Any = None, ejecutor: Any = None) -> int:
    """Lanza la linea de ordenes sobre el proyecto del escenario."""
    return main(
        list(argv),
        escenario.entorno if entorno is None else entorno,
        ejecutor or Registro(),
        raiz=escenario.raiz,
    )


def dejar_ejecutable(escenario: Escenario, contenido: bytes = EJECUTABLE) -> None:
    (escenario.raiz / "build").mkdir(exist_ok=True)
    (escenario.raiz / "build" / "PRUEBA.EXE").write_bytes(contenido)


def test_flujo_completo_split_build_verify_clean(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    assert ejecutar(escenario, "split") == 0
    assert capsys.readouterr().out == "split completado: asm/ y script del enlazador generados\n"
    (escenario.raiz / "asm" / "data").mkdir()
    (escenario.raiz / "asm" / "data" / "datos.s").write_text("d", encoding="utf-8")
    assert ejecutar(escenario, "build") == 0
    assert capsys.readouterr().out == f"build completado: build/PRUEBA.EXE sha256={REFERENCIA.sha256}\n"
    assert ejecutar(escenario, "verify") == 0
    assert capsys.readouterr().out == f"OK esperado={REFERENCIA.sha256} obtenido={REFERENCIA.sha256}\n"
    assert ejecutar(escenario, "clean") == 0
    assert capsys.readouterr().out.startswith("eliminado: asm, expected, build/")
    assert ejecutar(escenario, "clean") == 0
    assert capsys.readouterr().out == "eliminado: nada que eliminar\n"


def test_verify_con_huellas_distintas_devuelve_uno_y_orienta_la_depuracion(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    dejar_ejecutable(escenario, EJECUTABLE[:-1] + b"\xff")
    assert ejecutar(escenario, "verify") == 1
    salida = capsys.readouterr().out
    assert salida.startswith("FAIL esperado=")
    assert "primera diferencia en el desplazamiento" in salida


def test_verify_sin_ejecutable_reconstruido_es_un_fail_y_no_un_error_de_uso(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    assert ejecutar(escenario, "verify") == 1
    capturado = capsys.readouterr()
    assert capturado.out == (
        f"FAIL el ejecutable reconstruido no existe: ejecute 'build' (esperado={REFERENCIA.sha256})\n"
    )
    assert capturado.err == ""


def test_el_disco_se_toma_del_argumento_y_del_archivo_local(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    dejar_ejecutable(escenario)
    assert ejecutar(escenario, "--disc", str(escenario.disco), "verify", entorno={}) == 0
    (escenario.raiz / "datos" / "local.toml").write_text(
        '[rutas]\ndisc = "' + escenario.disco.as_posix() + '"\n', encoding="utf-8"
    )
    assert ejecutar(escenario, "verify", entorno={}) == 0
    capsys.readouterr()


def test_sin_disco_configurado_el_error_nombra_las_dos_variables_y_el_archivo_local(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    dejar_ejecutable(escenario)
    assert ejecutar(escenario, "verify", entorno={}) == 1
    assert capsys.readouterr().err == (
        "error: falta la ubicacion del disco: defina PSXDECOMP_DISC (o JUEGO_DISC), "
        "--disc o 'disc' en datos/local.toml\n"
    )


def test_split_con_herramientas_sin_instalar_informa_cual_falta(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    (Path(escenario.entorno["JUEGO_TOOLCHAIN"]) / "binutils-mipsel" / "bin" / "ld.exe").unlink()
    assert ejecutar(escenario, "split") == 1
    assert "'ld' no esta instalado" in capsys.readouterr().err


def test_split_avisa_de_los_datos_pequenos_repetidos_sin_cambiar_su_resultado(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    (escenario.raiz / "datos" / "simbolos.txt").write_text(
        "D_80100330 = 0x80100330; // type:u8 size:0x8\n", encoding="utf-8"
    )
    (escenario.raiz / "datos" / "opciones.toml").write_text(
        "[datos_pequenos]\nD_80100330 = 0x80100330\n", encoding="utf-8"
    )
    assert ejecutar(escenario, "split") == 0
    salida = capsys.readouterr()
    assert salida.out == "split completado: asm/ y script del enlazador generados\n"
    assert salida.err == (
        "aviso: [datos_pequenos] D_80100330 = 0x80100330: "
        "mismo nombre: ya figura en datos/simbolos.txt, la clave puede retirarse\n"
    )


def test_split_no_falla_si_no_puede_verificar_la_configuracion(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    assert ejecutar(escenario, "split") == 0
    salida = capsys.readouterr()
    assert salida.out == "split completado: asm/ y script del enlazador generados\n"
    assert salida.err == "aviso: no se pudo verificar la configuracion: falta datos/simbolos.txt\n"


def test_verificar_config_sin_duplicados_devuelve_cero_y_no_lee_la_referencia(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    (escenario.raiz / "datos" / "ejecutable.json").unlink()
    (escenario.raiz / "datos" / "simbolos.txt").write_text("", encoding="utf-8")
    assert ejecutar(escenario, "verificar-config") == 0
    assert capsys.readouterr().out == "verificar-config: 0 errores\n"


def test_verificar_config_con_una_clave_repetida_devuelve_uno(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    (escenario.raiz / "datos" / "simbolos.txt").write_text(
        "D_80100330 = 0x80100330; // type:u8 size:0x8\n", encoding="utf-8"
    )
    (escenario.raiz / "datos" / "opciones.toml").write_text(
        "[datos_pequenos]\nD_80100330 = 0x80100330\n", encoding="utf-8"
    )
    assert ejecutar(escenario, "verificar-config") == 1
    salida = capsys.readouterr()
    assert salida.out == "verificar-config: 1 errores\n"
    assert salida.err.startswith("error: [datos_pequenos] D_80100330")


def test_clean_lee_la_referencia_pero_no_resuelve_el_disco(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    assert ejecutar(escenario, "clean", entorno={}) == 0
    assert capsys.readouterr().out == "eliminado: nada que eliminar\n"
    (escenario.raiz / "datos" / "ejecutable.json").unlink()
    assert ejecutar(escenario, "clean", entorno={}) == 1
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("error", "esperado"),
    [
        (PermissionError("acceso denegado"), "error: acceso denegado\n"),
        (
            PermissionError(13, "Acceso denegado", "C:/privado/datos.bin"),
            "error: error de entrada/salida: PermissionError (Acceso denegado): datos.bin\n",
        ),
        (OSError(5, ""), "error: error de entrada/salida: OSError\n"),
    ],
)
def test_un_error_del_sistema_se_informa_sin_traza_ni_rutas(
    escenario: Escenario,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: OSError,
    esperado: str,
) -> None:
    def fallo(*_: Any, **__: Any) -> Any:
        raise error

    monkeypatch.setattr(infra_kit, "limpiar", fallo)
    assert ejecutar(escenario, "clean") == 1
    capturado = capsys.readouterr()
    assert capturado.err == esperado
    assert "Traceback" not in capturado.err
    assert "privado" not in capturado.err


def test_un_manifiesto_invalido_solo_impide_las_ordenes_que_necesitan_el_proyecto(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "psxdecomp.toml").write_text("[proyecto]\n", encoding="utf-8")
    assert main(["clean"], {}, raiz=tmp_path) == 1
    captura = capsys.readouterr()
    assert captura.err.startswith("error: psxdecomp.toml:")
    assert str(tmp_path) not in captura.err
    assert main(["comprobar", str(tmp_path)]) == 1
    with pytest.raises(SystemExit) as salida:
        main(["--help"], {}, raiz=tmp_path)
    assert salida.value.code == 0
    assert "usage: python -m psxdecomp.cli" in capsys.readouterr().out


def test_proyecto_elige_otra_raiz_y_sin_el_se_usa_la_carpeta_actual(
    escenario: Escenario, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    otra = tmp_path / "otra"
    otra.mkdir()
    assert main(["--proyecto", str(escenario.raiz), "clean"], escenario.entorno, Registro()) == 0
    assert capsys.readouterr().out == "eliminado: nada que eliminar\n"
    monkeypatch.chdir(escenario.raiz)
    assert main(["clean"], escenario.entorno, Registro()) == 0
    monkeypatch.chdir(otra)
    assert main(["clean"], escenario.entorno, Registro()) == 1
    assert capsys.readouterr().err.startswith("error: ")


def test_el_proyecto_inyectado_evita_cargar_el_manifiesto_y_no_ofrece_comprobar(
    escenario: Escenario, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["clean"], escenario.entorno, Registro(), proyecto=escenario.proyecto, raiz=tmp_path) == 0
    assert capsys.readouterr().out == "eliminado: nada que eliminar\n"
    with pytest.raises(SystemExit) as salida:
        main(["comprobar"], escenario.entorno, Registro(), proyecto=escenario.proyecto)
    assert salida.value.code == 2
    capsys.readouterr()


def test_sin_orden_argparse_termina_con_dos(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as salida:
        main([], {})
    assert salida.value.code == 2
    assert "usage" in capsys.readouterr().err


def test_el_entorno_por_omision_es_el_del_proceso(
    escenario: Escenario, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dejar_ejecutable(escenario)
    monkeypatch.setenv("PSXDECOMP_DISC", str(escenario.disco))
    assert main(["verify"], raiz=escenario.raiz) == 0
    assert "OK esperado=" in capsys.readouterr().out


def test_comprobar_con_un_manifiesto_de_otra_carpeta_imprime_su_resumen(
    escenario: Escenario, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["comprobar", str(escenario.raiz)]) == 0
    assert "ejecutable: PRUEBA.EXE" in capsys.readouterr().out


def test_split_no_expone_rutas_si_el_sistema_niega_el_acceso_a_la_configuracion(
    escenario: Escenario, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    ruta = str(escenario.raiz / "datos" / "opciones.toml")

    def negar(*args: Any, **kwargs: Any) -> list[str]:
        raise PermissionError(13, "Acceso denegado", ruta)

    monkeypatch.setattr(infra_kit, "verificar_configuracion", negar)
    assert ejecutar(escenario, "split") == 0
    salida = capsys.readouterr()
    assert ruta not in salida.err
    assert str(escenario.raiz) not in salida.err
    assert salida.err == "aviso: no se pudo verificar la configuracion: Acceso denegado\n"

import sys
from pathlib import Path

import pytest
from psxdecomp.entorno import Variables
from psxdecomp.toolchain import plataforma


def test_es_windows_sigue_a_sys_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    assert plataforma.es_windows() is True
    monkeypatch.setattr(sys, "platform", "linux")
    assert plataforma.es_windows() is False


def test_comando_wine_por_omision_y_configurado() -> None:
    assert plataforma.comando_wine({}) == "wine"
    assert plataforma.comando_wine({"PSXDECOMP_WINE": "  "}) == "wine"
    assert plataforma.comando_wine({"PSXDECOMP_WINE": "/opt/wine/bin/wine64"}) == "/opt/wine/bin/wine64"


def test_prefijo_binutils_por_omision_configurado_y_vacio() -> None:
    assert plataforma.prefijo_binutils({}) == "mipsel-none-elf-"
    assert plataforma.prefijo_binutils({"PSXDECOMP_BINUTILS_PREFIX": "x-"}) == "x-"
    assert plataforma.prefijo_binutils({"PSXDECOMP_BINUTILS_PREFIX": ""}) == ""


@pytest.mark.parametrize(
    ("ejecutable", "esperado"),
    [
        ("pssn/bin/CC1PSX.EXE", True),
        ("cpppsx.exe", True),
        ("/usr/bin/mipsel-none-elf-as", False),
        ("maspsx.py", False),
        ("exe", False),
    ],
)
def test_es_ejecutable_windows_por_extension(ejecutable: str, esperado: bool) -> None:
    assert plataforma.es_ejecutable_windows(ejecutable) is esperado


def test_adaptar_comando_en_windows_no_cambia_nada() -> None:
    comando = ["C:/sdk/CC1PSX.EXE", "-O2"]
    assert plataforma.adaptar_comando(comando, {}, windows=True) == comando


def test_adaptar_comando_antepone_wine_a_los_exe_fuera_de_windows() -> None:
    comando = ["/root/toolchain/psyq-4.4/pssn/bin/CC1PSX.EXE", "-O2", "build/a b.i"]
    adaptado = plataforma.adaptar_comando(comando, {"PSXDECOMP_WINE": "wine64"}, windows=False)
    assert adaptado == ["wine64", *comando]


def test_adaptar_comando_no_toca_los_programas_nativos_ni_el_comando_vacio() -> None:
    nativo = ["/usr/bin/mipsel-none-elf-as", "a.s"]
    assert plataforma.adaptar_comando(nativo, {}, windows=False) == nativo
    assert plataforma.adaptar_comando([], {}, windows=False) == []


def test_adaptar_comando_consulta_la_plataforma_real_por_omision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(plataforma, "es_windows", lambda: False)
    assert plataforma.adaptar_comando(["A.EXE"], {}) == ["wine", "A.EXE"]


def test_entorno_proceso_fuerza_utf8_y_silencia_wine_fuera_de_windows() -> None:
    entorno = plataforma.entorno_proceso({"HOME": "/root"}, windows=False)
    assert entorno == {"HOME": "/root", "PYTHONUTF8": "1", "WINEDEBUG": "-all"}


def test_entorno_proceso_respeta_la_depuracion_elegida_por_el_usuario() -> None:
    entorno = plataforma.entorno_proceso({"WINEDEBUG": "err+all", "WINEPREFIX": "/p"}, windows=False)
    assert entorno["WINEDEBUG"] == "err+all"
    assert entorno["WINEPREFIX"] == "/p"


def test_entorno_proceso_en_windows_no_agrega_variables_de_wine(monkeypatch: pytest.MonkeyPatch) -> None:
    assert plataforma.entorno_proceso({}, windows=True) == {"PYTHONUTF8": "1"}
    monkeypatch.setattr(plataforma, "es_windows", lambda: True)
    assert "WINEDEBUG" not in plataforma.entorno_proceso({})


def test_buscar_devuelve_la_ruta_si_existe(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x")
    assert plataforma.buscar_sin_distinguir_mayusculas(tmp_path / "a.txt") == tmp_path / "a.txt"


def test_buscar_resuelve_diferencias_de_mayusculas(tmp_path: Path, sistema_sensible: None) -> None:
    carpeta = tmp_path / "pssn" / "BIN"
    carpeta.mkdir(parents=True)
    (carpeta / "CC1PSX.EXE").write_text("x")
    encontrada = plataforma.buscar_sin_distinguir_mayusculas(tmp_path / "pssn" / "bin" / "cc1psx.exe")
    assert encontrada == carpeta / "CC1PSX.EXE"


def test_buscar_rechaza_coincidencias_ambiguas_o_ausentes(
    tmp_path: Path, sistema_sensible: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "A.EXE").write_text("x")
    assert plataforma.buscar_sin_distinguir_mayusculas(tmp_path / "otro.exe") is None
    # Dos nombres que solo difieren en mayusculas no pueden coexistir en Windows: se simulan.
    monkeypatch.setattr(Path, "iterdir", lambda self: iter([self / "A.EXE", self / "a.exe"]))
    assert plataforma.buscar_sin_distinguir_mayusculas(tmp_path / "A.exe") is None


def test_buscar_rechaza_un_ancestro_que_no_es_carpeta(tmp_path: Path, sistema_sensible: None) -> None:
    (tmp_path / "archivo").write_text("x")
    assert plataforma.buscar_sin_distinguir_mayusculas(tmp_path / "archivo" / "dentro") is None


def test_buscar_sin_ningun_ancestro_existente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "exists", lambda self: False)
    assert plataforma.buscar_sin_distinguir_mayusculas(Path("no/existe/nada")) is None


def test_localizar_binutils_usa_el_prefijo_y_el_buscador_inyectado() -> None:
    consultas: list[str] = []

    def buscar(nombre: str) -> str | None:
        consultas.append(nombre)
        return f"/usr/bin/{nombre}" if "objdump" in nombre else None

    assert plataforma.localizar_binutils("objdump", {}, buscar) == Path("/usr/bin/mipsel-none-elf-objdump")
    assert plataforma.localizar_binutils("ld", {"PSXDECOMP_BINUTILS_PREFIX": "x-"}, buscar) is None
    assert consultas == ["mipsel-none-elf-objdump", "x-ld"]


def test_localizar_binutils_rechaza_alias_desconocidos() -> None:
    with pytest.raises(ValueError, match="no es un binutils conocido"):
        plataforma.localizar_binutils("gcc", {}, lambda nombre: nombre)


def test_localizar_binutils_usa_which_por_omision() -> None:
    assert plataforma.localizar_binutils("as", {"PSXDECOMP_BINUTILS_PREFIX": "prefijo-inexistente-"}) is None


def test_el_alias_del_proyecto_configura_wine_y_el_prefijo_de_binutils() -> None:
    variables = Variables(alias="JUEGO")
    assert plataforma.comando_wine({"JUEGO_WINE": "wine64"}, variables) == "wine64"
    assert (
        plataforma.comando_wine({"PSXDECOMP_WINE": "propio", "JUEGO_WINE": "wine64"}, variables) == "propio"
    )
    assert plataforma.comando_wine({"PSXDECOMP_WINE": "  ", "JUEGO_WINE": "wine64"}, variables) == "wine64"
    assert plataforma.comando_wine({"JUEGO_WINE": "wine64"}) == "wine"
    assert plataforma.prefijo_binutils({"JUEGO_BINUTILS_PREFIX": "x-"}, variables) == "x-"
    assert (
        plataforma.prefijo_binutils(
            {"PSXDECOMP_BINUTILS_PREFIX": "", "JUEGO_BINUTILS_PREFIX": "x-"}, variables
        )
        == ""
    )
    adaptado = plataforma.adaptar_comando(
        ["CC1PSX.EXE"], {"JUEGO_WINE": "wine64"}, windows=False, variables=variables
    )
    assert adaptado == ["wine64", "CC1PSX.EXE"]
    assert plataforma.localizar_binutils(
        "ld", {"JUEGO_BINUTILS_PREFIX": "x-"}, lambda n: f"/b/{n}", variables
    ) == Path("/b/x-ld")

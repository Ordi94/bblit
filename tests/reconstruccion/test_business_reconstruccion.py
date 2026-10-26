"""Reglas de negocio de la reconstruccion: configuracion del particionador y ciclo real split/build/verify."""

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from tools.reconstruccion import cli, dominio
from tools.reconstruccion import infraestructura as infra
from tools.toolchain.configuracion import leer_local_toml, resolver_rutas
from tools.toolchain.instalacion import leer_lock, resolver_herramienta

RAIZ_REPO = Path(__file__).resolve().parents[2]
SHA256_ORIGINAL = "0fad70d9b4cb324d78f113f7fd70c0aa954388fefad01af373509e0473c87df0"


@pytest.fixture(scope="module")
def configuracion() -> Any:
    return yaml.safe_load((RAIZ_REPO / "config" / "splat.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def referencia() -> Any:
    return infra.leer_referencia(RAIZ_REPO / "config" / "ejecutable.json")


def test_la_referencia_del_ejecutable_declara_los_hechos_verificados(referencia: Any) -> None:
    assert referencia.nombre == "SLUS_008.38"
    assert referencia.sha256 == SHA256_ORIGINAL
    assert referencia.tamano == 350208 == 0x800 + 0x55000
    assert referencia.cabecera.pc0 == 0x80014A08
    assert referencia.cabecera.t_addr == 0x80014A00
    assert referencia.cabecera.gp0 == 0


def test_splat_describe_un_ejecutable_psx_con_un_unico_segmento_cargado(configuracion: Any) -> None:
    opciones = configuracion["options"]
    assert opciones["platform"] == "psx"
    assert opciones["basename"] == "SLUS_008"
    assert opciones["target_path"] == "expected/SLUS_008.38"
    assert not Path(opciones["target_path"]).is_absolute()
    (segmento, fin) = configuracion["segments"]
    assert segmento["start"] == 0x800
    assert segmento["vram"] == 0x80014A00
    assert fin == [0x55800]


def test_splat_ordena_texto_datos_rodata_y_bss_como_los_agrupa_el_enlazador(configuracion: Any) -> None:
    subsegmentos = configuracion["segments"][0]["subsegments"]
    tipos = [s[1] if isinstance(s, list) else s["type"] for s in subsegmentos]
    assert tipos[0] == "asm" and tipos[-1] == "bss"
    assert tipos.count("c") == 25
    assert tipos.index("asm", 1) == 26, "el ensamblador de librerias sigue al ultimo archivo C"
    assert {"data", "rodata", ".rodata"} <= set(tipos)
    inicios = [s[0] if isinstance(s, list) else s["start"] for s in subsegmentos]
    assert inicios == sorted(inicios)
    assert inicios[0] == 0x800
    assert all(inicio % 4 == 0 for inicio in inicios)
    bss = subsegmentos[-1]
    assert bss["start"] == 0x55800
    assert bss["vram"] == 0x80014A00 + 0x55000


def test_splat_consume_symbols_txt_del_proyecto_y_el_simbolo_de_entrada(configuracion: Any) -> None:
    assert configuracion["options"]["symbol_addrs_path"] == [
        "config/symbols.txt",
        "build/simbolos_entrada.txt",
    ]
    assert configuracion["sha1"] == "3b091486c2463f4dbe82e045072c390e226caa37"


def test_la_configuracion_no_contiene_rutas_de_ninguna_maquina() -> None:
    for nombre in ("splat.yaml", "ejecutable.json", "toolchain.lock.json", "local.example.toml"):
        texto = (RAIZ_REPO / "config" / nombre).read_text(encoding="utf-8")
        assert "Users" not in texto and "Desktop" not in texto, nombre


def entorno_real(tmp_path: Path) -> Any:
    local = leer_local_toml(RAIZ_REPO / "config" / "local.toml")
    rutas = resolver_rutas(RAIZ_REPO, os.environ, local)
    referencia = infra.leer_referencia(RAIZ_REPO / "config" / "ejecutable.json")
    try:
        original = infra.obtener_original(tmp_path / "comprobacion", rutas.disc, referencia)
    except (ValueError, FileNotFoundError):
        pytest.skip("requiere el disco original (BBLIT_DISC o config/local.toml)")
    try:
        lock = leer_lock(RAIZ_REPO / "config" / "toolchain.lock.json")
        for alias in ("as", "ld", "objcopy", "objdump"):
            resolver_herramienta(lock, rutas.toolchain, "binutils-mipsel", alias)
        resolver_herramienta(lock, rutas.toolchain, "psyq-4.4", "cc1psx")
        resolver_herramienta(lock, rutas.toolchain, "psyq-4.4", "cpppsx")
        resolver_herramienta(lock, rutas.toolchain, "maspsx", "maspsx")
        resolver_herramienta(lock, rutas.toolchain, "asm-differ", "diff")
    except FileNotFoundError:
        pytest.skip("requiere el toolchain instalado (python -m tools.toolchain instalar)")
    return rutas, original


@pytest.fixture
def repo_aislado(tmp_path: Path) -> Any:
    rutas, _ = entorno_real(tmp_path)
    raiz = tmp_path / "repo con espacios (prueba)"
    shutil.copytree(RAIZ_REPO / "config", raiz / "config", ignore=shutil.ignore_patterns("local.toml"))
    shutil.copytree(RAIZ_REPO / "include", raiz / "include")
    shutil.copytree(RAIZ_REPO / "src", raiz / "src")
    variables = {"BBLIT_DISC": str(rutas.disc), "BBLIT_TOOLCHAIN": str(rutas.toolchain)}
    return raiz, variables


def sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def test_ciclo_real_split_build_verify_clean_reproduce_el_ejecutable_byte_a_byte(
    repo_aislado: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = repo_aislado
    assert cli.main(["split"], variables, raiz) == 0
    assert (raiz / "expected" / "SLUS_008.38").stat().st_size == 350208
    texto = raiz / "asm" / "boot.s"

    def huella_de_asm() -> list[str]:
        return [sha256(p) for p in sorted((raiz / "asm").rglob("*.s"))]

    primera = huella_de_asm()
    fuentes = {p.name: sha256(p) for p in (raiz / "src").glob("*.c")}
    assert len(fuentes) == 25
    assert cli.main(["split"], variables, raiz) == 0
    assert huella_de_asm() == primera, "split debe ser idempotente"
    assert {p.name: sha256(p) for p in (raiz / "src").glob("*.c")} == fuentes
    assert "glabel func_80014A08" in texto.read_text(encoding="utf-8")

    assert cli.main(["build"], variables, raiz) == 0
    construido = raiz / "build" / "SLUS_008.38"
    assert construido.stat().st_size == 0x55800
    assert sha256(construido) == SHA256_ORIGINAL

    capsys.readouterr()
    assert cli.main(["verify"], variables, raiz) == 0
    assert capsys.readouterr().out == f"OK esperado={SHA256_ORIGINAL} obtenido={SHA256_ORIGINAL}\n"

    assert cli.main(["clean"], variables, raiz) == 0
    assert sorted(p.name for p in raiz.iterdir()) == ["config", "include", "src"]


def test_ciclo_real_con_symbols_txt_que_renombra_la_entrada_sigue_siendo_identico(repo_aislado: Any) -> None:
    raiz, variables = repo_aislado
    # Con una tabla de simbolos distinta los .c se regeneran desde cero; como el esqueleto no trae
    # la cadena que posee el subsegmento '.data', ese tramo vuelve a ser ensamblador.
    shutil.rmtree(raiz / "src")
    configuracion = (raiz / "config" / "splat.yaml").read_text(encoding="utf-8")
    sin_cadena = "".join(
        linea for linea in configuracion.splitlines(keepends=True) if ", .data, " not in linea
    )
    (raiz / "config" / "splat.yaml").write_text(sin_cadena, encoding="utf-8")
    (raiz / "config" / "symbols.txt").write_text(
        "inicio_del_juego = 0x80014A08; // type:func\n", encoding="utf-8"
    )
    assert cli.main(["split"], variables, raiz) == 0
    texto = (raiz / "asm" / "boot.s").read_text(encoding="utf-8")
    assert "glabel inicio_del_juego" in texto
    assert "func_80014A08" not in texto.replace("D_80014A08", "")
    assert (raiz / "build" / "simbolos_entrada.txt").read_text(encoding="utf-8") == ""
    assert cli.main(["build"], variables, raiz) == 0
    assert sha256(raiz / "build" / "SLUS_008.38") == SHA256_ORIGINAL


def test_verify_detecta_un_solo_byte_alterado_en_el_cuerpo(
    repo_aislado: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz, variables = repo_aislado
    assert cli.main(["split"], variables, raiz) == 0
    assert cli.main(["build"], variables, raiz) == 0
    construido = raiz / "build" / "SLUS_008.38"
    datos = bytearray(construido.read_bytes())
    datos[0x1234] ^= 0x01
    construido.write_bytes(bytes(datos))
    capsys.readouterr()
    assert cli.main(["verify"], variables, raiz) == 1
    salida = capsys.readouterr().out
    assert salida.startswith("FAIL esperado=" + SHA256_ORIGINAL)
    assert salida.rstrip().endswith("primera diferencia en el desplazamiento 0x1234 (cuerpo)")


def test_la_cabecera_regenerada_es_identica_a_la_del_original_cuando_hay_disco(tmp_path: Path) -> None:
    _, ruta_original = entorno_real(tmp_path)
    original = ruta_original.read_bytes()
    referencia = infra.leer_referencia(RAIZ_REPO / "config" / "ejecutable.json")
    assert dominio.serializar_cabecera(referencia.cabecera) == original[:0x800]
    assert dominio.leer_cabecera(original) == referencia.cabecera
    assert json.loads((RAIZ_REPO / "config" / "ejecutable.json").read_text(encoding="utf-8"))[
        "tamano"
    ] == len(original)

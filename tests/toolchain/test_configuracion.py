from pathlib import Path
from typing import Any

import pytest
from tools.toolchain import configuracion
from tools.toolchain.configuracion import leer_local_toml, resolver_rutas

RAIZ = Path("repo")


def test_local_inexistente_devuelve_vacio(tmp_path: Path) -> None:
    assert leer_local_toml(tmp_path / "local.toml") == {}


def test_local_valido(tmp_path: Path) -> None:
    ruta = tmp_path / "local.toml"
    ruta.write_text('[rutas]\ndisc = "D:/disco (copia)"\nsiete_zip = "C:/7z.exe"\n', encoding="utf-8")
    assert leer_local_toml(ruta) == {"disc": "D:/disco (copia)", "siete_zip": "C:/7z.exe"}


def test_local_sin_tabla_rutas_es_valido(tmp_path: Path) -> None:
    ruta = tmp_path / "local.toml"
    ruta.write_text("otra = 1\n", encoding="utf-8")
    assert leer_local_toml(ruta) == {}


@pytest.mark.parametrize(
    ("texto", "mensaje"),
    [
        ("[rutas\n", "no es un TOML valido"),
        ("rutas = 5\n", "'rutas' debe ser una tabla"),
        ('[rutas]\nraro = "x"\n', "clave desconocida 'raro'"),
        ("[rutas]\ndisc = 5\n", "'disc' debe ser texto no vacio"),
        ('[rutas]\ndisc = ""\n', "'disc' debe ser texto no vacio"),
        ('[rutas]\ndisc = "' + "x" * 1025 + '"\n', "'disc' debe ser texto no vacio"),
    ],
)
def test_local_invalido(tmp_path: Path, texto: Any, mensaje: Any) -> None:
    ruta = tmp_path / "local.toml"
    ruta.write_text(texto, encoding="utf-8")
    with pytest.raises(ValueError, match=mensaje):
        leer_local_toml(ruta)


def test_local_con_bytes_no_utf8(tmp_path: Path) -> None:
    ruta = tmp_path / "local.toml"
    ruta.write_bytes(b'[rutas]\ndisc = "\xff\xfe"\n')
    with pytest.raises(ValueError, match="no es un TOML valido"):
        leer_local_toml(ruta)


def test_local_demasiado_grande(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ruta = tmp_path / "local.toml"
    ruta.write_text("[rutas]\n", encoding="utf-8")
    monkeypatch.setattr(configuracion, "MAX_BYTES_LOCAL", 2)
    with pytest.raises(ValueError, match="excede el tamano permitido"):
        leer_local_toml(ruta)


def test_prioridad_argumento_sobre_entorno_sobre_local() -> None:
    entorno = {"BBLIT_DISC": "entorno/disc", "BBLIT_TOOLCHAIN": "entorno/tc", "BBLIT_7ZIP": "entorno/7z"}
    local = {"disc": "local/disc", "toolchain": "local/tc", "siete_zip": "local/7z"}
    rutas = resolver_rutas(RAIZ, entorno, local, disc="arg/disc", toolchain="arg/tc")
    assert (rutas.disc, rutas.toolchain, rutas.siete_zip) == (
        Path("arg/disc"),
        Path("arg/tc"),
        Path("entorno/7z"),
    )
    rutas = resolver_rutas(RAIZ, entorno, local)
    assert (rutas.disc, rutas.toolchain) == (Path("entorno/disc"), Path("entorno/tc"))
    rutas = resolver_rutas(RAIZ, {}, local)
    assert (rutas.disc, rutas.toolchain, rutas.siete_zip) == (
        Path("local/disc"),
        Path("local/tc"),
        Path("local/7z"),
    )


def test_valores_por_defecto() -> None:
    rutas = resolver_rutas(RAIZ, {}, {})
    assert rutas.raiz == RAIZ
    assert rutas.toolchain == RAIZ / "toolchain"
    assert rutas.disc is None
    assert rutas.siete_zip is None

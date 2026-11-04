"""Reglas de negocio del toolchain: integridad de lo descargado, errores claros y lock del proyecto."""

import ast
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import psxdecomp.toolchain as toolchain_kit
import pytest
from psxdecomp.toolchain import extraccion, instalacion
from psxdecomp.toolchain.dominio import cargar_lock

from .ayudantes import RespuestaFalsa, SesionFalsa, bloque_componente, lock_de, sha256_de, zip_de

URL = "https://github.com/ejemplo/proyecto/archive/abc123.zip"
CARPETA_TOOLCHAIN = Path(toolchain_kit.__file__).resolve().parent


def lock_con(archivo: bytes, **cambios: Any) -> Any:
    bloque = bloque_componente(
        archivo, quitar_raiz=True, archivos_clave={"herramienta": "herramienta.py"}, **cambios
    )
    return cargar_lock(lock_de(pieza=bloque))


def archivos_bajo(carpeta: Path) -> list[str]:
    return sorted(p.relative_to(carpeta).as_posix() for p in carpeta.rglob("*") if p.is_file())


def test_una_huella_distinta_detiene_la_instalacion_y_no_deja_archivos() -> None:
    bueno = zip_de({"p/herramienta.py": b"bueno"})
    manipulado = zip_de({"p/herramienta.py": b"troyano"})
    with tempfile.TemporaryDirectory() as temporal:
        raiz = Path(temporal)
        lock = lock_con(bueno)
        with pytest.raises(ValueError, match="componente 'pieza': huella SHA-256 distinta") as error:
            instalacion.instalar(lock, raiz, sesion=SesionFalsa(RespuestaFalsa(manipulado, URL)))
        assert sha256_de(bueno) in str(error.value)
        assert sha256_de(manipulado) in str(error.value)
        assert archivos_bajo(raiz) == []


def test_una_descarga_cortada_no_deja_nada_y_el_reintento_funciona(tmp_path: Path) -> None:
    archivo = zip_de({"p/herramienta.py": b"contenido"})
    lock = lock_con(archivo)
    with pytest.raises(ConnectionError, match="componente 'pieza': fallo de red"):
        instalacion.instalar(
            lock, tmp_path, sesion=SesionFalsa(RespuestaFalsa(archivo, URL, falla_a_mitad=True))
        )
    assert not any(p.suffix == ".parcial" for p in tmp_path.rglob("*"))
    assert instalacion.instalar(lock, tmp_path, sesion=SesionFalsa(RespuestaFalsa(archivo, URL))) == {
        "pieza": "instalado"
    }
    assert (tmp_path / "pieza" / "herramienta.py").read_bytes() == b"contenido"


def test_un_servidor_que_redirige_a_un_host_ajeno_es_rechazado(tmp_path: Path) -> None:
    archivo = zip_de({"p/herramienta.py": b"x"})
    sesion = SesionFalsa(RespuestaFalsa(archivo, "https://descargas.malicioso.example/pieza.zip"))
    with pytest.raises(ValueError, match="redireccion a un host no admitido"):
        instalacion.instalar(lock_con(archivo), tmp_path, sesion=sesion)
    assert archivos_bajo(tmp_path) == []


def test_componente_ausente_del_lock_falla_nombrandolo(tmp_path: Path) -> None:
    lock = lock_con(zip_de({"p/herramienta.py": b"x"}))
    with pytest.raises(ValueError) as error:
        instalacion.resolver_herramienta(lock, tmp_path, "binutils-mipsel", "as")
    assert str(error.value) == "el componente 'binutils-mipsel' no figura en el archivo de bloqueo"


def test_herramienta_no_instalada_indica_el_comando_para_instalarla(tmp_path: Path) -> None:
    lock = lock_con(zip_de({"p/herramienta.py": b"x"}))
    with pytest.raises(FileNotFoundError) as error:
        instalacion.resolver_herramienta(lock, tmp_path, "pieza", "herramienta")
    assert str(error.value) == (
        "componente 'pieza': 'herramienta' no esta instalado; "
        "ejecute 'python -m psxdecomp.toolchain instalar'"
    )


def test_un_zip_con_rutas_hostiles_no_escribe_fuera_de_la_carpeta_del_componente(tmp_path: Path) -> None:
    hostil = zip_de({"p/herramienta.py": b"ok", "p/../../fuera.txt": b"malo", "/abs.txt": b"malo"})
    with pytest.raises(ValueError):
        instalacion.instalar(
            lock_con(hostil), tmp_path / "toolchain", sesion=SesionFalsa(RespuestaFalsa(hostil, URL))
        )
    assert not (tmp_path / "fuera.txt").exists()
    assert not (tmp_path / "toolchain" / "fuera.txt").exists()


def test_rutas_con_espacios_y_parentesis_viajan_como_un_unico_argumento(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Any:
    capturado = {}

    def falso_run(comando: Any, **opciones: Any) -> Any:
        capturado["comando"] = comando
        capturado["opciones"] = opciones
        (Path(next(a for a in comando if a.startswith("-o"))[2:]) / "x").mkdir(parents=True, exist_ok=True)
        (Path(next(a for a in comando if a.startswith("-o"))[2:]) / "x" / "f").write_bytes(b"1")
        return subprocess.CompletedProcess(comando, 0, "", "")

    monkeypatch.setattr(subprocess, "run", falso_run)
    componente = cargar_lock(lock_de(pieza=bloque_componente(b"x", formato="7z")))["pieza"]
    destino = tmp_path / "Mi Disco (copia 2)" / "tool chain"
    archivo = tmp_path / "Runtime Library (4.4).7z"
    extraccion.extraer_7z(componente, archivo, destino, Path("7-Zip/7z.exe"))
    comando = capturado["comando"]
    assert f"-o{destino}" in comando
    assert str(archivo) in comando
    assert capturado["opciones"].get("shell") is None
    assert all(isinstance(a, str) for a in comando)


PROHIBIDOS = ("urllib3", "httpx", "aiohttp", "urllib.request", "socket")


def modulos_importados(fuente: str) -> set[str]:
    """Nombres de modulo importados por un fuente, incluyendo `from urllib import request`."""
    encontrados: set[str] = set()
    for nodo in ast.walk(ast.parse(fuente)):
        if isinstance(nodo, ast.Import):
            encontrados.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            encontrados.add(nodo.module)
            encontrados.update(f"{nodo.module}.{alias.name}" for alias in nodo.names)
    return encontrados


def importes_prohibidos(fuente: str) -> list[str]:
    """Importes de librerias de red distintas de requests."""
    return sorted(
        m for m in modulos_importados(fuente) if any(m == p or m.startswith(p + ".") for p in PROHIBIDOS)
    )


def test_requests_es_la_unica_dependencia_de_red() -> None:
    carpeta = CARPETA_TOOLCHAIN
    modulos = sorted(carpeta.glob("*.py"))
    assert len(modulos) >= 9
    for modulo in modulos:
        assert importes_prohibidos(modulo.read_text(encoding="utf-8")) == [], modulo.name
    assert "requests" in modulos_importados((carpeta / "descarga.py").read_text(encoding="utf-8"))


def test_el_detector_de_importes_prohibidos_senala_un_modulo_sintetico(tmp_path: Path) -> None:
    sintetico = tmp_path / "malo.py"
    lineas = [
        "import socket",
        "import urllib3",
        "from urllib import request",
        "from urllib.request import urlopen",
        "import requests",
        "import json",
    ]
    sintetico.write_text(chr(10).join(lineas), encoding="utf-8")
    assert importes_prohibidos(sintetico.read_text(encoding="utf-8")) == [
        "socket",
        "urllib.request",
        "urllib.request.urlopen",
        "urllib3",
    ]
    limpio = tmp_path / "limpio.py"
    limpio.write_text(chr(10).join(["import requests", "import json"]), encoding="utf-8")
    assert importes_prohibidos(limpio.read_text(encoding="utf-8")) == []

import json
import re
from pathlib import Path
from typing import Any

import pytest
from tools.toolchain import instalacion
from tools.toolchain.dominio import cargar_lock

from .ayudantes import RespuestaFalsa, SesionFalsa, bloque_componente, lock_de, zip_de

URL = "https://github.com/ejemplo/proyecto/archive/abc123.zip"
ARCHIVO = zip_de({"proy-1/herramienta.py": b"print('hola')", "proy-1/extra.txt": b"x"})


def lock_ejemplo(**cambios: Any) -> Any:
    bloque = bloque_componente(
        ARCHIVO, quitar_raiz=True, archivos_clave={"herramienta": "herramienta.py"}, **cambios
    )
    return cargar_lock(lock_de(pieza=bloque))


def sesion() -> SesionFalsa:
    return SesionFalsa(RespuestaFalsa(ARCHIVO, URL))


def test_instala_descarga_extrae_marca_y_borra_la_descarga(tmp_path: Path) -> None:
    lock = lock_ejemplo()
    estados = instalacion.instalar(lock, tmp_path, sesion=sesion())
    carpeta = tmp_path / "pieza"
    assert estados == {"pieza": "instalado"}
    assert (carpeta / "herramienta.py").read_bytes() == b"print('hola')"
    assert not (carpeta / instalacion.CARPETA_DESCARGA).exists()
    marca = json.loads((carpeta / instalacion.NOMBRE_MARCA).read_text(encoding="utf-8"))
    assert marca["sha256"] == lock["pieza"].sha256
    assert marca["archivos"] == 2
    assert instalacion.esta_instalado(lock["pieza"], carpeta) is True


def test_segunda_instalacion_es_vigente_y_no_toca_la_red(tmp_path: Path) -> None:
    lock = lock_ejemplo()
    instalacion.instalar(lock, tmp_path, sesion=sesion())
    segunda = sesion()
    assert instalacion.instalar(lock, tmp_path, sesion=segunda) == {"pieza": "vigente"}
    assert segunda.llamadas == []


def test_conservar_descarga(tmp_path: Path) -> None:
    lock = lock_ejemplo()
    carpeta = instalacion.instalar_componente(lock["pieza"], tmp_path, sesion(), conservar_descarga=True)
    assert (carpeta / instalacion.CARPETA_DESCARGA / "abc123.zip").is_file()


def test_reinstala_desde_cero_si_la_carpeta_estaba_a_medias(tmp_path: Path) -> None:
    lock = lock_ejemplo()
    (tmp_path / "pieza").mkdir()
    (tmp_path / "pieza" / "basura.txt").write_text("restos")
    instalacion.instalar(lock, tmp_path, sesion=sesion())
    assert not (tmp_path / "pieza" / "basura.txt").exists()


def test_solo_instala_los_componentes_pedidos(tmp_path: Path) -> None:
    lock = cargar_lock(lock_de(a=bloque_componente(ARCHIVO), b=bloque_componente(ARCHIVO)))
    assert instalacion.instalar(lock, tmp_path, nombres=["b"], sesion=sesion()) == {"b": "instalado"}
    assert not (tmp_path / "a").exists()


def test_componente_pedido_que_no_esta_en_el_lock(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="el componente 'fantasma' no figura"):
        instalacion.instalar(lock_ejemplo(), tmp_path, nombres=["fantasma"], sesion=sesion())


def test_instalacion_incompleta_por_archivo_clave_ausente(tmp_path: Path) -> None:
    bloque = bloque_componente(ARCHIVO, quitar_raiz=True, archivos_clave={"falta": "no_esta.exe"})
    lock = cargar_lock(lock_de(pieza=bloque))
    with pytest.raises(ValueError, match=re.escape("instalacion incompleta, falta 'no_esta.exe'")):
        instalacion.instalar(lock, tmp_path, sesion=sesion())
    assert not (tmp_path / "pieza" / instalacion.NOMBRE_MARCA).exists()


def test_instalacion_incompleta_por_extraccion_vacia(tmp_path: Path) -> None:
    lock = cargar_lock(lock_de(pieza=bloque_componente(ARCHIVO, extraer=["no/coincide/*"])))
    with pytest.raises(ValueError, match="no se extrajo ningun archivo"):
        instalacion.instalar_componente(lock["pieza"], tmp_path, sesion())


@pytest.mark.parametrize("contenido", [None, "no es json", "[1, 2]", '{"sha256": "otra"}'])
def test_marca_ausente_corrupta_o_de_otra_huella_no_cuenta_como_instalado(
    tmp_path: Path, contenido: Any
) -> None:
    lock = lock_ejemplo()
    instalacion.instalar(lock, tmp_path, sesion=sesion())
    marca = tmp_path / "pieza" / instalacion.NOMBRE_MARCA
    if contenido is None:
        marca.unlink()
    else:
        marca.write_text(contenido, encoding="utf-8")
    assert instalacion.esta_instalado(lock["pieza"], tmp_path / "pieza") is False


def test_archivo_clave_borrado_invalida_la_instalacion(tmp_path: Path) -> None:
    lock = lock_ejemplo()
    instalacion.instalar(lock, tmp_path, sesion=sesion())
    (tmp_path / "pieza" / "herramienta.py").unlink()
    assert instalacion.faltantes(lock["pieza"], tmp_path / "pieza") == ["herramienta.py"]
    assert instalacion.esta_instalado(lock["pieza"], tmp_path / "pieza") is False


def test_resolver_herramienta_instalada_y_ausente(tmp_path: Path) -> None:
    lock = lock_ejemplo()
    with pytest.raises(FileNotFoundError, match="'pieza': 'herramienta' no esta instalado"):
        instalacion.resolver_herramienta(lock, tmp_path, "pieza", "herramienta")
    instalacion.instalar(lock, tmp_path, sesion=sesion())
    ruta = instalacion.resolver_herramienta(lock, tmp_path, "pieza", "herramienta")
    assert ruta == tmp_path / "pieza" / "herramienta.py"
    with pytest.raises(ValueError, match="no declara el archivo clave 'otra'"):
        instalacion.resolver_herramienta(lock, tmp_path, "pieza", "otra")


def test_leer_lock_valido(tmp_path: Path) -> None:
    ruta = tmp_path / "lock.json"
    ruta.write_text(json.dumps(lock_de(pieza=bloque_componente(ARCHIVO))), encoding="utf-8")
    assert list(instalacion.leer_lock(ruta)) == ["pieza"]


def test_leer_lock_inexistente_demasiado_grande_o_corrupto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(FileNotFoundError, match="no se encontro el archivo de bloqueo"):
        instalacion.leer_lock(tmp_path / "no.json")
    ruta = tmp_path / "lock.json"
    ruta.write_text("{no es json", encoding="utf-8")
    with pytest.raises(ValueError, match="no es JSON valido"):
        instalacion.leer_lock(ruta)
    monkeypatch.setattr(instalacion, "MAX_BYTES_LOCK", 3)
    with pytest.raises(ValueError, match="excede el tamano permitido"):
        instalacion.leer_lock(ruta)


def test_el_lock_real_del_repositorio_es_valido() -> None:
    lock = instalacion.leer_lock(Path(__file__).resolve().parents[2] / "config" / "toolchain.lock.json")
    assert set(lock) >= {"psyq-4.4", "psyq-4.1", "binutils-mipsel", "maspsx", "m2c", "asm-differ"}
    assert lock["psyq-4.4"].ruta_clave("cc1psx") == "pssn/bin/CC1PSX.EXE"
    assert lock["binutils-mipsel"].ruta_clave("as") == "bin/mipsel-none-elf-as.exe"

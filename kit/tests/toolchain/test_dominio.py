from pathlib import PurePosixPath
from typing import Any

import pytest
from tools.toolchain import dominio
from tools.toolchain.dominio import Componente, cargar_lock, parsear_componente

from .ayudantes import bloque_componente, lock_de


def test_componente_minimo_se_parsea_con_valores_por_defecto() -> None:
    componente = parsear_componente("maspsx", bloque_componente(b"x"))
    assert componente.nombre == "maspsx"
    assert componente.formato == "zip"
    assert componente.extraer == ()
    assert componente.archivos_clave == ()
    assert componente.quitar_raiz is False


def test_componente_completo_normaliza_rutas_y_patrones() -> None:
    bloque = bloque_componente(
        b"x",
        extraer=["Bin\\*.EXE", "psx/lib/*"],
        archivos_clave={"as": "bin\\as.exe"},
        quitar_raiz=True,
        formato="7z",
    )
    componente = parsear_componente("binutils", bloque)
    assert componente.extraer == ("Bin/*.EXE", "psx/lib/*")
    assert componente.archivos_clave == (("as", "bin/as.exe"),)
    assert componente.quitar_raiz is True
    assert componente.ruta_clave("as") == "bin/as.exe"


def test_ruta_clave_inexistente_nombra_componente_y_alias() -> None:
    componente = parsear_componente("m2c", bloque_componente(b"x"))
    with pytest.raises(ValueError, match="'m2c' no declara el archivo clave 'ld'"):
        componente.ruta_clave("ld")


@pytest.mark.parametrize("nombre", ["", "Mayuscula", "-inicio", "con espacio", "a" * 70, "a/b"])
def test_nombre_de_componente_invalido(nombre: Any) -> None:
    with pytest.raises(ValueError, match="nombre de componente no valido"):
        parsear_componente(nombre, bloque_componente(b"x"))


def test_bloque_que_no_es_objeto() -> None:
    with pytest.raises(ValueError, match="'m2c': el bloque debe ser un objeto"):
        parsear_componente("m2c", [1, 2])


@pytest.mark.parametrize("sha", [None, "", "abc", "g" * 64, "a" * 63, 5])
def test_sha256_invalido(sha: Any) -> None:
    with pytest.raises(ValueError, match="'m2c'"):
        parsear_componente("m2c", bloque_componente(b"x", sha256=sha))


def test_sha256_en_mayusculas_se_normaliza() -> None:
    componente = parsear_componente("m2c", bloque_componente(b"x", sha256="A" * 64))
    assert componente.sha256 == "a" * 64


def test_formato_no_admitido() -> None:
    with pytest.raises(ValueError, match="formato 'tar' no admitido"):
        parsear_componente("m2c", bloque_componente(b"x", formato="tar"))


@pytest.mark.parametrize("fecha", [None, "", "25/10/2026", "2026-13-40", "2026-10-250"])
def test_fecha_invalida(fecha: Any) -> None:
    with pytest.raises(ValueError, match="fecha_registro"):
        parsear_componente("m2c", bloque_componente(b"x", fecha_registro=fecha))


def test_notas_excesivas_o_vacias() -> None:
    with pytest.raises(ValueError, match="notas"):
        parsear_componente("m2c", bloque_componente(b"x", notas="x" * 2001))
    with pytest.raises(ValueError, match="notas"):
        parsear_componente("m2c", bloque_componente(b"x", notas="  "))


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/a/b.zip",
        "https://usuario:clave@github.com/a/b.zip",
        "https://evil.example.com/a.zip",
        "https://github.com.evil.example/a.zip",
        "ftp://github.com/a.zip",
    ],
)
def test_url_rechazada(url: Any) -> None:
    with pytest.raises(ValueError, match="'m2c'"):
        parsear_componente("m2c", bloque_componente(b"x", url=url))


@pytest.mark.parametrize(
    ("host", "esperado"),
    [
        ("github.com", True),
        ("codeload.github.com", True),
        ("release-assets.githubusercontent.com", True),
        ("archive.org", True),
        ("ia800000.us.archive.org", True),
        ("psx.arthus.net", True),
        ("notgithub.com", False),
        ("github.com.evil.org", False),
        ("", False),
    ],
)
def test_host_admitido(host: Any, esperado: Any) -> None:
    assert dominio.host_admitido(host) is esperado


@pytest.mark.parametrize("patrones", ["no es lista", [1], [""], ["/abs/*"], ["a/../b"], ["x"] * 65])
def test_patrones_invalidos(patrones: Any) -> None:
    with pytest.raises(ValueError, match="'m2c'"):
        parsear_componente("m2c", bloque_componente(b"x", extraer=patrones))


@pytest.mark.parametrize(
    "claves",
    [[1], {"A": "x"}, {"as": ""}, {"as": "../fuera"}, {"as": "/abs"}, {f"k{i}": "x" for i in range(65)}],
)
def test_archivos_clave_invalidos(claves: Any) -> None:
    with pytest.raises(ValueError):
        parsear_componente("m2c", bloque_componente(b"x", archivos_clave=claves))


def test_quitar_raiz_debe_ser_booleano() -> None:
    with pytest.raises(ValueError, match="quitar_raiz"):
        parsear_componente("m2c", bloque_componente(b"x", quitar_raiz="si"))


@pytest.mark.parametrize("valor", [None, [], {}, {"version": 2, "componentes": {"a": {}}}, {"version": 1}])
def test_lock_con_estructura_invalida(valor: Any) -> None:
    with pytest.raises(ValueError):
        cargar_lock(valor)


def test_lock_con_demasiados_componentes() -> None:
    bloque = bloque_componente(b"x")
    exceso = {f"c{i}": bloque for i in range(65)}
    with pytest.raises(ValueError, match="entre 1 y 64"):
        cargar_lock({"version": 1, "componentes": exceso})


def test_lock_conserva_el_orden_del_archivo() -> None:
    lock = cargar_lock(lock_de(zeta=bloque_componente(b"z"), alfa=bloque_componente(b"a")))
    assert list(lock) == ["zeta", "alfa"]


def test_obtener_componente_existente_y_ausente() -> None:
    lock = cargar_lock(lock_de(m2c=bloque_componente(b"x")))
    assert isinstance(dominio.obtener_componente(lock, "m2c"), Componente)
    with pytest.raises(ValueError, match="el componente 'asm-differ' no figura en el archivo de bloqueo"):
        dominio.obtener_componente(lock, "asm-differ")


def test_verificar_sha256_acepta_igual_sin_importar_mayusculas() -> None:
    componente = parsear_componente("m2c", bloque_componente(b"x"))
    dominio.verificar_sha256(componente, componente.sha256.upper())


def test_verificar_sha256_rechaza_distinta_y_nombra_ambas() -> None:
    componente = parsear_componente("m2c", bloque_componente(b"x"))
    with pytest.raises(ValueError) as error:
        dominio.verificar_sha256(componente, "0" * 64)
    assert str(error.value) == (
        f"componente 'm2c': huella SHA-256 distinta a la registrada "
        f"(esperada {componente.sha256}, obtenida {'0' * 64})"
    )


@pytest.mark.parametrize(
    ("url", "esperado"),
    [
        ("https://archive.org/download/x/Runtime%20Library%204.4.7z", "Runtime Library 4.4.7z"),
        ("https://github.com/o/p/archive/abc.zip", "abc.zip"),
    ],
)
def test_nombre_de_archivo_desde_url(url: Any, esperado: Any) -> None:
    assert dominio.nombre_archivo_desde_url(url, "c") == esperado


@pytest.mark.parametrize(
    "url",
    [
        "https://archive.org/",
        "https://archive.org/a/%2e%2e",
        "https://archive.org/a/%00x",
        "https://archive.org/a/..zip",
    ],
)
def test_nombre_de_archivo_invalido(url: Any) -> None:
    with pytest.raises(ValueError, match="'c'"):
        dominio.nombre_archivo_desde_url(url, "c")


@pytest.mark.parametrize(
    ("miembro", "esperado"),
    [
        ("bin\\as.exe", "bin/as.exe"),
        ("./bin//as.exe", "bin/as.exe"),
        ("a/b/", "a/b"),
    ],
)
def test_ruta_miembro_segura_normaliza(miembro: Any, esperado: Any) -> None:
    assert dominio.ruta_miembro_segura(miembro) == PurePosixPath(esperado)


@pytest.mark.parametrize(
    "miembro",
    ["", "/etc/passwd", "C:/x", "c:\\x", "a/../../b", "..", ".", "./", "a\x00b", "x" * 300],
)
def test_ruta_miembro_peligrosa(miembro: Any) -> None:
    with pytest.raises(ValueError):
        dominio.ruta_miembro_segura(miembro)


def test_coincide_patron() -> None:
    ruta = PurePosixPath("PSX/LIB/LIBAPI.LIB")
    assert dominio.coincide_patron(ruta, ()) is True
    assert dominio.coincide_patron(ruta, ("psx/lib/*",)) is True
    assert dominio.coincide_patron(ruta, ("pssn/bin/*", "psx/lib/libapi.lib")) is True
    assert dominio.coincide_patron(ruta, ("pssn/bin/*",)) is False

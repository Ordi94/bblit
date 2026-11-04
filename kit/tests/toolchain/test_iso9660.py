import struct
from typing import Any

import pytest
from tools.toolchain import iso9660
from tools.toolchain.iso9660 import crear_lector, leer_archivo, listar_archivos

from .ayudantes import construir_iso


def lector_de(imagen: bytes) -> Any:
    return crear_lector(len(imagen), lambda desde, largo: imagen[desde : desde + largo])


ARBOL = {
    "GNU": {"CC1PSX.EXE": b"compilador", "DOS": {"VIEJO.EXE": b"dos"}},
    "LEEME.TXT": b"hola" * 600,
}


@pytest.mark.parametrize("modo2352", [False, True])
def test_lista_y_lee_archivos_en_ambos_formatos_de_sector(modo2352: Any) -> None:
    imagen = construir_iso(ARBOL, modo2352=modo2352)
    lector = lector_de(imagen)
    entradas = {str(e.ruta): e for e in listar_archivos(lector)}
    assert sorted(entradas) == ["GNU/CC1PSX.EXE", "GNU/DOS/VIEJO.EXE", "LEEME.TXT"]
    assert leer_archivo(lector, entradas["GNU/CC1PSX.EXE"]) == b"compilador"
    assert leer_archivo(lector, entradas["LEEME.TXT"]) == b"hola" * 600
    assert entradas["LEEME.TXT"].tamano == 2400


def test_sectores_modo1_usan_desplazamiento_16() -> None:
    imagen = construir_iso({"A.BIN": b"datos"}, modo2352=True, modo_sector=1)
    lector = lector_de(imagen)
    (entrada,) = listar_archivos(lector)
    assert leer_archivo(lector, entrada) == b"datos"


def test_tamano_de_imagen_irreconocible() -> None:
    with pytest.raises(ValueError, match="tamano de sector reconocido"):
        crear_lector(1000, lambda desde, largo: b"")


def test_sector_fuera_de_limites() -> None:
    imagen = construir_iso({"A": b"x"})
    lector = lector_de(imagen)
    with pytest.raises(ValueError, match="fuera de los limites"):
        lector(len(imagen) // 2048)
    with pytest.raises(ValueError, match="fuera de los limites"):
        lector(-1)


def test_imagen_sin_descriptor_de_volumen() -> None:
    imagen = bytearray(construir_iso({"A": b"x"}))
    imagen[16 * 2048 + 1 : 16 * 2048 + 6] = b"XXXXX"
    with pytest.raises(ValueError, match="descriptor de volumen"):
        listar_archivos(lector_de(bytes(imagen)))


def test_registro_corrupto_por_longitud_menor_a_la_minima() -> None:
    imagen = bytearray(construir_iso({"A": b"x"}))
    volumen = imagen[16 * 2048 : 17 * 2048]
    lba_raiz = struct.unpack_from("<I", volumen, 158)[0]
    imagen[lba_raiz * 2048] = 10
    with pytest.raises(ValueError, match="registro de directorio corrupto"):
        listar_archivos(lector_de(bytes(imagen)))


def test_registro_con_nombre_fuera_de_limites() -> None:
    imagen = bytearray(construir_iso({"A": b"x"}))
    volumen = imagen[16 * 2048 : 17 * 2048]
    lba_raiz = struct.unpack_from("<I", volumen, 158)[0]
    tercer = lba_raiz * 2048 + 68
    imagen[tercer + 32] = 200
    with pytest.raises(ValueError, match="nombre de registro fuera de limites"):
        listar_archivos(lector_de(bytes(imagen)))


def test_registro_que_se_sale_del_directorio() -> None:
    imagen = bytearray(construir_iso({"A": b"x"}))
    volumen = imagen[16 * 2048 : 17 * 2048]
    lba_raiz = struct.unpack_from("<I", volumen, 158)[0]
    imagen[lba_raiz * 2048 + 68] = 255
    with pytest.raises(ValueError, match="registro de directorio corrupto"):
        listar_archivos(lector_de(bytes(imagen)))


def test_directorios_demasiado_anidados() -> None:
    arbol: dict[str, Any] = {"F.TXT": b"x"}
    for _ in range(iso9660.MAX_PROFUNDIDAD + 2):
        arbol = {"D": arbol}
    with pytest.raises(ValueError, match="anidados"):
        listar_archivos(lector_de(construir_iso(arbol)))


def test_demasiadas_entradas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(iso9660, "MAX_ENTRADAS", 2)
    imagen = construir_iso({"A": b"1", "B": b"2", "C": b"3"})
    with pytest.raises(ValueError, match="maximo de entradas"):
        listar_archivos(lector_de(imagen))


def test_directorio_demasiado_grande(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(iso9660, "MAX_TAMANO_DIRECTORIO", 10)
    with pytest.raises(ValueError, match="directorio demasiado grande"):
        listar_archivos(lector_de(construir_iso({"A": b"1"})))


def test_archivo_demasiado_grande(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(iso9660, "MAX_TAMANO_ARCHIVO", 3)
    with pytest.raises(ValueError, match="excede el tamano maximo"):
        listar_archivos(lector_de(construir_iso({"A": b"1234"})))


def test_ruta_hostil_dentro_de_la_imagen_se_rechaza() -> None:
    imagen = construir_iso({"..": {"X": b"1"}})
    with pytest.raises(ValueError):
        listar_archivos(lector_de(imagen))


def test_directorio_con_registros_alineados_a_sector_salta_el_relleno() -> None:
    arbol = {f"ARCHIVO_{i:03d}.DAT": bytes([i]) for i in range(80)}
    imagen = construir_iso(arbol, alinear_registros=True)
    lector = lector_de(imagen)
    entradas = listar_archivos(lector)
    assert len(entradas) == 80
    assert {str(e.ruta): leer_archivo(lector, e) for e in entradas}["ARCHIVO_079.DAT"] == bytes([79])


def anidar(niveles: int) -> dict[str, Any]:
    arbol: dict[str, Any] = {"F.TXT": b"x"}
    for _ in range(niveles):
        arbol = {"D": arbol}
    return arbol


def test_anidamiento_en_el_limite_exacto_se_procesa_y_un_nivel_mas_falla() -> None:
    entradas = listar_archivos(lector_de(construir_iso(anidar(iso9660.MAX_PROFUNDIDAD))))
    assert [e.ruta.name for e in entradas] == ["F.TXT"]
    with pytest.raises(ValueError, match="anidados"):
        listar_archivos(lector_de(construir_iso(anidar(iso9660.MAX_PROFUNDIDAD + 1))))

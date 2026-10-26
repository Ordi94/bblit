from typing import Any

import pytest
import requests
from tools.toolchain import descarga
from tools.toolchain.descarga import descargar_verificado
from tools.toolchain.dominio import parsear_componente

from .ayudantes import RespuestaFalsa, SesionFalsa, bloque_componente

CONTENIDO = b"contenido del componente de prueba" * 4
URL = "https://github.com/ejemplo/proyecto/archive/abc123.zip"


def componente(contenido: bytes = CONTENIDO, **cambios: Any) -> Any:
    return parsear_componente("pieza", bloque_componente(contenido, **cambios))


def test_descarga_correcta_deja_el_archivo_con_su_nombre_y_sin_temporales(tmp_path: Any) -> None:
    respuesta = RespuestaFalsa(CONTENIDO, URL)
    sesion = SesionFalsa(respuesta)
    destino = descargar_verificado(componente(), tmp_path / "pieza", sesion)
    assert destino == tmp_path / "pieza" / "abc123.zip"
    assert destino.read_bytes() == CONTENIDO
    assert sorted(p.name for p in (tmp_path / "pieza").iterdir()) == ["abc123.zip"]
    assert respuesta.cerrada is True
    assert sesion.llamadas == [(URL, True, (15, 120))]


def test_sesion_por_defecto_es_requests(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    respuesta = RespuestaFalsa(CONTENIDO, URL)
    sesion = SesionFalsa(respuesta)
    monkeypatch.setattr(requests, "Session", lambda: sesion)
    assert descargar_verificado(componente(), tmp_path).read_bytes() == CONTENIDO


def test_huella_distinta_rechaza_y_no_deja_nada_en_destino(tmp_path: Any) -> None:
    sesion = SesionFalsa(RespuestaFalsa(b"otro contenido", URL))
    with pytest.raises(ValueError, match="componente 'pieza': huella SHA-256 distinta"):
        descargar_verificado(componente(), tmp_path, sesion)
    assert list(tmp_path.iterdir()) == []


def test_huella_distinta_no_pisa_un_archivo_bueno_previo(tmp_path: Any) -> None:
    (tmp_path / "abc123.zip").write_bytes(CONTENIDO)
    sesion = SesionFalsa(RespuestaFalsa(b"alterado", URL))
    with pytest.raises(ValueError):
        descargar_verificado(componente(), tmp_path, sesion)
    assert (tmp_path / "abc123.zip").read_bytes() == CONTENIDO
    assert [p.name for p in tmp_path.iterdir()] == ["abc123.zip"]


def test_redireccion_a_host_no_admitido(tmp_path: Any) -> None:
    sesion = SesionFalsa(RespuestaFalsa(CONTENIDO, "https://evil.example.com/x.zip"))
    with pytest.raises(ValueError, match="redireccion a un host no admitido"):
        descargar_verificado(componente(), tmp_path, sesion)
    assert list(tmp_path.iterdir()) == []


def test_redireccion_a_http_plano(tmp_path: Any) -> None:
    sesion = SesionFalsa(RespuestaFalsa(CONTENIDO, "http://github.com/x.zip"))
    with pytest.raises(ValueError, match="redireccion a un host no admitido"):
        descargar_verificado(componente(), tmp_path, sesion)


def test_estado_http_de_error_se_convierte_en_error_de_conexion(tmp_path: Any) -> None:
    respuesta = RespuestaFalsa(b"", URL, error=requests.HTTPError("404"))
    with pytest.raises(ConnectionError, match="componente 'pieza': fallo de red"):
        descargar_verificado(componente(), tmp_path, SesionFalsa(respuesta))
    assert respuesta.cerrada is True
    assert list(tmp_path.iterdir()) == []


def test_error_al_abrir_la_conexion(tmp_path: Any) -> None:
    sesion = SesionFalsa(error=requests.ConnectTimeout("lento"))
    with pytest.raises(ConnectionError, match="fallo de red"):
        descargar_verificado(componente(), tmp_path, sesion)


def test_corte_a_mitad_de_descarga_no_deja_parciales(tmp_path: Any) -> None:
    respuesta = RespuestaFalsa(CONTENIDO, URL, falla_a_mitad=True)
    with pytest.raises(ConnectionError):
        descargar_verificado(componente(), tmp_path, SesionFalsa(respuesta))
    assert list(tmp_path.iterdir()) == []


def test_cuerpo_que_excede_la_cota(tmp_path: Any) -> None:
    with pytest.raises(ValueError, match="la descarga excede 10 bytes"):
        descargar_verificado(
            componente(), tmp_path, SesionFalsa(RespuestaFalsa(CONTENIDO, URL)), max_bytes=10
        )
    assert list(tmp_path.iterdir()) == []


def test_borrar_si_existe_tolera_ausencia(tmp_path: Any) -> None:
    descarga._borrar_si_existe(tmp_path / "no_existe")

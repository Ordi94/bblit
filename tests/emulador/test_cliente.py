"""Cliente HTTP con transporte doble y, para el transporte real, un servidor local efimero."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from tools.emulador import cliente
from tools.emulador.dominio import RAM_TAMANO, EmuladorError

from tests.emulador import sintetica


class Transporte:
    """Doble del transporte: responde segun la ruta y registra las peticiones."""

    def __init__(self, respuestas):
        self.respuestas = respuestas
        self.peticiones = []

    def __call__(self, metodo, url, tiempo_espera):
        self.peticiones.append((metodo, url, tiempo_espera))
        respuesta = self.respuestas[url.split("/api/v1/")[1]]
        if isinstance(respuesta, list):
            respuesta = respuesta.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


def _cliente(respuestas, **kwargs):
    transporte = Transporte(respuestas)
    pausas = []
    return cliente.ClienteRedux(8080, transporte, pausas.append, **kwargs), transporte, pausas


def test_esta_corriendo_lee_el_campo_running():
    c, transporte, _ = _cliente({"execution-flow": json.dumps({"running": True}).encode()})
    assert c.esta_corriendo() is True
    assert transporte.peticiones[0][:2] == ("GET", "http://127.0.0.1:8080/api/v1/execution-flow")


@pytest.mark.parametrize("cuerpo", [b"no json", b"[1]", b'{"running": "si"}', b"{}"])
def test_esta_corriendo_rechaza_respuestas_inesperadas(cuerpo):
    c, _, _ = _cliente({"execution-flow": cuerpo})
    with pytest.raises(EmuladorError, match="execution-flow"):
        c.esta_corriendo()


def test_pausar_y_reanudar_usan_post_con_la_funcion_correcta():
    c, transporte, _ = _cliente({"execution-flow?function=pause": b"", "execution-flow?function=resume": b""})
    c.pausar()
    c.reanudar()
    assert [p[0] for p in transporte.peticiones] == ["POST", "POST"]
    assert transporte.peticiones[0][1].endswith("function=pause")
    assert transporte.peticiones[1][1].endswith("function=resume")


def test_volcar_ram_valida_el_tamano():
    c, _, _ = _cliente({"cpu/ram/raw": bytes(RAM_TAMANO)})
    assert len(c.volcar_ram()) == RAM_TAMANO
    corto, _, _ = _cliente({"cpu/ram/raw": bytes(10)})
    with pytest.raises(ValueError, match="2097152"):
        corto.volcar_ram()


def test_capturar_pantalla_exige_un_png():
    png = sintetica.png_negro()
    c, _, _ = _cliente({"screen/still": png})
    assert c.capturar_pantalla() == png
    roto, _, _ = _cliente({"screen/still": b"<html>"})
    with pytest.raises(EmuladorError, match="no es un PNG"):
        roto.capturar_pantalla()


def test_reintenta_ante_fallos_de_conexion_y_luego_responde():
    c, transporte, pausas = _cliente({"execution-flow": [OSError("x"), b'{"running": false}']})
    assert c.esta_corriendo() is False
    assert len(transporte.peticiones) == 2
    assert pausas == [cliente.PAUSA_REINTENTO]


def test_agota_los_reintentos_sin_filtrar_la_url():
    c, transporte, _ = _cliente({"execution-flow": [OSError("a"), OSError("b"), OSError("c")]})
    with pytest.raises(EmuladorError) as info:
        c.esta_corriendo()
    assert len(transporte.peticiones) == 3
    assert "127.0.0.1" not in str(info.value)


@pytest.mark.parametrize("puerto", [0, 80, 1023, 65536])
def test_rechaza_puertos_fuera_de_rango(puerto):
    with pytest.raises(ValueError, match="puerto"):
        cliente.ClienteRedux(puerto)


def test_transporte_real_contra_un_servidor_local():
    visto = {}

    class Manejador(BaseHTTPRequestHandler):
        def _responder(self):
            visto["metodo"] = self.command
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"cuerpo")

        do_GET = _responder  # noqa: N815
        do_POST = _responder  # noqa: N815

        def log_message(self, *args):
            pass

    servidor = HTTPServer(("127.0.0.1", 0), Manejador)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    try:
        url = f"http://127.0.0.1:{servidor.server_port}/api/v1/x"
        assert cliente.solicitar_http("GET", url, 5.0) == b"cuerpo"
        assert cliente.solicitar_http("POST", url, 5.0) == b"cuerpo"
        assert visto["metodo"] == "POST"
    finally:
        servidor.shutdown()
        servidor.server_close()
        hilo.join(timeout=5)

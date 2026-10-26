"""Orquestacion de la sesion con reloj, cliente y procesos simulados."""

import json

import pytest
from tools.emulador import sesion
from tools.emulador.dominio import EmuladorError

from tests.emulador import sintetica
from tests.emulador.dobles import ClienteFalso, Reloj, fallo, ram_con

NEGRO = sintetica.png_negro()
CON_CONTENIDO = sintetica.png_con_contenido()


class Entorno:
    """Agrupa los dobles de una sesion y registra el apagado."""

    def __init__(self, tmp_path, **config):
        self.reloj = Reloj()
        self.terminados = []
        self.lanzados = []
        self.vivos = []
        self.puerto_ocupado = [False]
        self.config = sesion.ConfigSesion(
            imagen=tmp_path / "juego.cue",
            bios=tmp_path / "bios.bin",
            ejecutable=tmp_path / "redux.exe",
            carpeta_trabajo=tmp_path / "trabajo",
            salida=tmp_path / "salida",
            **config,
        )

    def lanzar(self, ejecutable, imagen, bios, trabajo, puerto):
        self.lanzados.append((ejecutable, imagen, bios, trabajo, puerto))
        return 777

    def ejecutar(self, cliente, config=None):
        ocupado = self.puerto_ocupado
        return sesion.ejecutar_sesion(
            config or self.config,
            cliente=cliente,
            lanzar=self.lanzar,
            terminar=self.terminados.append,
            listar=lambda: self.vivos,
            puerto_en_uso=lambda puerto: ocupado.pop(0) if len(ocupado) > 1 else ocupado[0],
            reloj=self.reloj,
            dormir=self.reloj.dormir,
        )


def test_sesion_completa_espera_pantalla_no_negra_y_escribe_resultados(tmp_path):
    entorno = Entorno(tmp_path)
    ram = ram_con(0x14A00, b"juego")
    cliente = ClienteFalso(
        corriendo=[fallo(), False, True],
        pantallas=[NEGRO, ValueError("x"), b"no png", CON_CONTENIDO],
        rams=[ram],
    )
    resultado = entorno.ejecutar(cliente)
    assert entorno.terminados == [777]
    assert (tmp_path / "salida" / "ram.bin").read_bytes() == ram
    assert (tmp_path / "salida" / "pantalla.png").read_bytes() == CON_CONTENIDO
    escrito = json.loads((tmp_path / "salida" / "sesion.json").read_text(encoding="utf-8"))
    assert escrito == resultado
    assert resultado["segundosHastaRunning"] == 0.5
    assert resultado["segundosHastaPantalla"] == 3.5
    assert resultado["segundosHastaEjecutable"] is None
    assert resultado["bytesRam"] == len(ram)
    assert resultado["bytesPng"] == len(CON_CONTENIDO)
    assert resultado["procesosVivosAlFinal"] == 0
    assert len(resultado["sha256Ram"]) == 64
    assert cliente.llamadas.index("pausar") < cliente.llamadas.index("volcar_ram")


def test_hito_running_no_mide_pantalla(tmp_path):
    entorno = Entorno(tmp_path, hito="running")
    cliente = ClienteFalso(pantallas=[CON_CONTENIDO], rams=[ram_con(0, b"")])
    resultado = entorno.ejecutar(cliente)
    assert resultado["segundosHastaPantalla"] is None
    assert cliente.llamadas.count("capturar_pantalla") == 1


def test_retardo_extra_espera_antes_de_volcar(tmp_path):
    entorno = Entorno(tmp_path, hito="running", retardo_extra=12.0)
    entorno.ejecutar(ClienteFalso(pantallas=[CON_CONTENIDO], rams=[ram_con(0, b"")]))
    assert 12.0 in entorno.reloj.pausas


def test_hito_ejecutable_espera_la_huella_en_ram(tmp_path):
    exe = tmp_path / "SLUS"
    exe.write_bytes(sintetica.ejecutable_psx(0x80014A00))
    huella = sintetica.ejecutable_psx()[0x800:0x900]
    entorno = Entorno(tmp_path, hito="ejecutable", exe_juego=exe)
    cliente = ClienteFalso(
        pantallas=[CON_CONTENIDO],
        rams=[ram_con(0x14A00, b"otra cosa"), fallo(), ram_con(0x14A00, huella)],
    )
    resultado = entorno.ejecutar(cliente)
    assert resultado["segundosHastaEjecutable"] == 2.0
    assert resultado["segundosHastaPantalla"] is None


def test_hito_ejecutable_sin_ejecutable_se_rechaza_y_apaga(tmp_path):
    entorno = Entorno(tmp_path, hito="ejecutable")
    with pytest.raises(ValueError, match="--exe-juego"):
        entorno.ejecutar(ClienteFalso(rams=[ram_con(0, b"")]))
    assert entorno.terminados == [777]


def test_hito_ejecutable_agotado_apaga_y_falla(tmp_path):
    exe = tmp_path / "SLUS"
    exe.write_bytes(sintetica.ejecutable_psx())
    entorno = Entorno(tmp_path, hito="ejecutable", exe_juego=exe, tope_hito=5.0)
    with pytest.raises(EmuladorError, match="no aparecio"):
        entorno.ejecutar(ClienteFalso(rams=[ram_con(0, b"")]))
    assert entorno.terminados == [777]
    assert not (tmp_path / "salida" / "sesion.json").exists()


def test_pantalla_siempre_negra_agota_el_tope_y_apaga(tmp_path):
    entorno = Entorno(tmp_path, tope_hito=6.0)
    with pytest.raises(EmuladorError, match="sigue negra"):
        entorno.ejecutar(ClienteFalso(pantallas=[NEGRO], rams=[ram_con(0, b"")]))
    assert entorno.terminados == [777]
    assert not (tmp_path / "salida" / "ram.bin").exists()


def test_running_que_nunca_llega_apaga_y_falla(tmp_path):
    entorno = Entorno(tmp_path)
    with pytest.raises(EmuladorError, match="running"):
        entorno.ejecutar(ClienteFalso(corriendo=[False]))
    assert entorno.terminados == [777]


def test_un_fallo_al_lanzar_aun_pasa_por_el_apagado(tmp_path):
    entorno = Entorno(tmp_path)

    def lanzar_roto(*argumentos):
        raise EmuladorError("emulador: no existe el archivo indicado")

    with pytest.raises(EmuladorError, match="no existe"):
        sesion.ejecutar_sesion(
            entorno.config,
            cliente=ClienteFalso(),
            lanzar=lanzar_roto,
            terminar=entorno.terminados.append,
            listar=lambda: [],
            puerto_en_uso=lambda puerto: False,
            reloj=entorno.reloj,
            dormir=entorno.reloj.dormir,
        )
    assert entorno.terminados == [None]


def test_un_fallo_al_volcar_apaga_y_no_escribe_resumen(tmp_path):
    entorno = Entorno(tmp_path, hito="running")
    cliente = ClienteFalso(pantallas=[CON_CONTENIDO], rams=[ValueError("tamano")])
    with pytest.raises(ValueError, match="tamano"):
        entorno.ejecutar(cliente)
    assert entorno.terminados == [777]
    assert not (tmp_path / "salida" / "sesion.json").exists()


def test_puerto_ocupado_antes_de_lanzar_no_lanza_nada(tmp_path):
    entorno = Entorno(tmp_path)
    entorno.puerto_ocupado = [True]
    with pytest.raises(EmuladorError, match="ya esta ocupado"):
        entorno.ejecutar(ClienteFalso())
    assert entorno.lanzados == []
    assert entorno.terminados == []


def test_procesos_vivos_tras_apagar_son_un_error(tmp_path):
    entorno = Entorno(tmp_path, hito="running")
    entorno.vivos = ["pcsx-redux.main.exe"]
    with pytest.raises(EmuladorError, match="siguen"):
        entorno.ejecutar(ClienteFalso(pantallas=[CON_CONTENIDO], rams=[ram_con(0, b"")]))


def test_puerto_ocupado_tras_apagar_es_un_error(tmp_path):
    entorno = Entorno(tmp_path, hito="running")
    entorno.puerto_ocupado = [False, True]
    with pytest.raises(EmuladorError, match="siguen"):
        entorno.ejecutar(ClienteFalso(pantallas=[CON_CONTENIDO], rams=[ram_con(0, b"")]))


def test_hito_desconocido_se_rechaza_antes_de_lanzar(tmp_path):
    entorno = Entorno(tmp_path, hito="menu")
    with pytest.raises(ValueError, match="hito"):
        entorno.ejecutar(ClienteFalso())
    assert entorno.lanzados == []


def test_sesion_usa_un_cliente_propio_si_no_se_inyecta(tmp_path, monkeypatch):
    creados = []

    def fabrica(puerto):
        creados.append(puerto)
        return ClienteFalso(pantallas=[CON_CONTENIDO], rams=[ram_con(0, b"")])

    monkeypatch.setattr(sesion, "ClienteRedux", fabrica)
    entorno = Entorno(tmp_path, hito="running", puerto=8123)
    sesion.ejecutar_sesion(
        entorno.config,
        lanzar=entorno.lanzar,
        terminar=entorno.terminados.append,
        listar=lambda: [],
        puerto_en_uso=lambda puerto: False,
        reloj=entorno.reloj,
        dormir=entorno.reloj.dormir,
    )
    assert creados == [8123]


def _disco_sintetico(raiz):
    """Crea `raiz/disc/Juego/juego.bin` y `.cue`, y devuelve (carpeta_bin, bin, cue)."""
    carpeta = raiz / "disc" / "Juego"
    carpeta.mkdir(parents=True)
    imagen = carpeta / "juego.bin"
    imagen.write_bytes(b"x")
    cue = carpeta / "juego.cue"
    cue.write_text("FILE", encoding="utf-8")
    return carpeta, imagen, cue


@pytest.mark.parametrize("forma", ["bin", "cue", "carpeta_bin", "carpeta_superior"])
def test_cada_forma_de_bblit_disc_protege_la_carpeta_de_la_imagen(tmp_path, forma):
    carpeta, imagen, cue = _disco_sintetico(tmp_path)
    valor = {"bin": imagen, "cue": cue, "carpeta_bin": carpeta, "carpeta_superior": tmp_path / "disc"}[forma]
    assert sesion.carpetas_protegidas(str(valor)) == [carpeta.resolve()]
    with pytest.raises(ValueError, match="disco original"):
        sesion.validar_salida(carpeta / "volcados", str(valor))
    # La carpeta superior y los hermanos legitimos no se protegen de mas.
    sesion.validar_salida(tmp_path / "disc" / "analisis", str(valor))
    sesion.validar_salida(tmp_path / "build", str(valor))


def test_carpeta_con_fs_protege_esa_carpeta_y_la_de_la_imagen(tmp_path):
    raiz = tmp_path / "disc"
    (raiz / "fs").mkdir(parents=True)
    (raiz / "juego.bin").write_bytes(b"x")
    assert sesion.carpetas_protegidas(str(raiz)) == [raiz.resolve()]
    with pytest.raises(ValueError, match="disco original"):
        sesion.validar_salida(raiz / "fs" / "salida", str(raiz))


def test_imagen_en_subcarpeta_y_fs_protegen_dos_carpetas_distintas(tmp_path):
    raiz = tmp_path / "disc"
    (raiz / "fs").mkdir(parents=True)
    (raiz / "ISO").mkdir()
    (raiz / "ISO" / "juego.bin").write_bytes(b"x")
    assert sesion.carpetas_protegidas(str(raiz)) == [(raiz / "ISO").resolve(), raiz.resolve()]
    with pytest.raises(ValueError, match="disco original"):
        sesion.validar_salida(raiz / "ISO" / "salida", str(raiz))
    with pytest.raises(ValueError, match="disco original"):
        sesion.validar_salida(raiz / "fs" / "salida", str(raiz))
    sesion.validar_salida(tmp_path / "build", str(raiz))


def test_carpeta_con_fs_sin_imagen_protege_solo_esa_carpeta(tmp_path):
    raiz = tmp_path / "disc"
    (raiz / "fs").mkdir(parents=True)
    assert sesion.carpetas_protegidas(str(raiz)) == [raiz.resolve()]


@pytest.mark.parametrize("caso", ["inexistente", "carpeta_vacia", "extension", "varias", "cue_sin_bin"])
def test_disco_no_resoluble_no_inventa_carpetas_protegidas(tmp_path, caso):
    disco = tmp_path / "disc"
    if caso == "carpeta_vacia":
        disco.mkdir()
    elif caso == "extension":
        disco = tmp_path / "juego.iso"
        disco.write_bytes(b"x")
    elif caso == "varias":
        disco.mkdir()
        (disco / "a.bin").write_bytes(b"x")
        (disco / "b.bin").write_bytes(b"x")
    elif caso == "cue_sin_bin":
        disco = tmp_path / "juego.cue"
        disco.write_text("FILE", encoding="utf-8")
    assert sesion.carpetas_protegidas(str(disco)) == []
    sesion.validar_salida(tmp_path / "cualquiera", str(disco))


def test_sin_bblit_disc_no_se_protege_nada(tmp_path):
    assert sesion.carpetas_protegidas(None) == []
    assert sesion.carpetas_protegidas("") == []
    sesion.validar_salida(tmp_path / "x", None)


def test_sesion_respeta_bblit_disc_del_entorno(tmp_path, monkeypatch):
    carpeta, imagen, _ = _disco_sintetico(tmp_path)
    monkeypatch.setenv("BBLIT_DISC", str(imagen))
    entorno = Entorno(tmp_path)
    entorno.config = sesion.ConfigSesion(
        imagen=tmp_path / "a.cue",
        bios=tmp_path / "b.bin",
        ejecutable=tmp_path / "c.exe",
        carpeta_trabajo=tmp_path / "t",
        salida=carpeta / "salida",
    )
    with pytest.raises(ValueError, match="disco original"):
        entorno.ejecutar(ClienteFalso())
    assert entorno.lanzados == []

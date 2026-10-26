"""
Sesion completa de emulador: arrancar, esperar un hito, volcar, capturar y apagar.

Contexto:
    Capa de servicio de `tools.emulador`. Orquesta `proceso` y `cliente` con relojes inyectables
    para que los tiempos de espera se prueben sin esperar. El apagado ocurre siempre en un
    `finally`, de modo que un fallo a medias no deja procesos ni el puerto ocupado.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tools.emulador import proceso
from tools.emulador.cliente import PUERTO_POR_DEFECTO, ClienteRedux
from tools.emulador.dominio import EmuladorError, offset_de_ram, prefijo_de_ejecutable
from tools.emulador.pantalla import decodificar_png, es_pantalla_negra, fraccion_con_contenido
from tools.reconstruccion.infraestructura import localizar_imagen

HITOS = ("running", "pantalla", "ejecutable")
TOPE_PANTALLA_POR_DEFECTO = 90.0
TOPE_RUNNING = 30.0
INTERVALO_SONDEO = 1.0
INTERVALO_RUNNING = 0.25


@dataclass(frozen=True)
class ConfigSesion:
    """
    Parametros de una sesion de emulador.

    Contexto:
        La construye el CLI a partir de argumentos y variables `BBLIT_*`; nunca contiene rutas
        fijas de una maquina concreta.

    Attributes:
        imagen (Path): Imagen `.cue` a cargar.
        bios (Path): BIOS de PlayStation.
        ejecutable (Path): `pcsx-redux.exe`.
        carpeta_trabajo (Path): Directorio de trabajo del emulador (configuracion y tarjetas de memoria).
        salida (Path): Carpeta donde se escriben `ram.bin`, `pantalla.png` y `sesion.json`.
        puerto (int): Puerto del servidor web.
        hito (str): `running`, `pantalla` (primera captura no negra) o `ejecutable` (el juego
            ya esta cargado en RAM; exige `exe_juego`).
        tope_hito (float): Segundos maximos de espera del hito `pantalla`.
        retardo_extra (float): Segundos adicionales tras alcanzar el hito, antes de volcar.
        exe_juego (Path, opcional): Ejecutable del juego cuya huella se busca en RAM.
    """

    imagen: Path
    bios: Path
    ejecutable: Path
    carpeta_trabajo: Path
    salida: Path
    puerto: int = PUERTO_POR_DEFECTO
    hito: str = "pantalla"
    tope_hito: float = TOPE_PANTALLA_POR_DEFECTO
    retardo_extra: float = 0.0
    exe_juego: Path | None = None


def carpetas_protegidas(valor_disco: str | None) -> list[Path]:
    """
    Calcula las carpetas del disco original donde no se debe escribir.

    Contexto:
        `BBLIT_DISC` admite cinco formas (`.bin`, `.cue`, carpeta del `.bin`, carpeta superior
        y carpeta con `fs/`). La resolucion de la imagen es unica y vive en
        `tools.reconstruccion.infraestructura.localizar_imagen`; aqui solo se reutiliza.
        Se protege la carpeta que CONTIENE la imagen resuelta y, si el valor es una carpeta con
        `fs/`, esa carpeta. Si la imagen no se puede resolver no se inventa ninguna carpeta: la
        validacion no protege nada por esa via (el disco sigue siendo de solo lectura por contrato).

    Args:
        valor_disco (str, opcional): Valor de `BBLIT_DISC`, o None.

    Returns:
        list[Path]: Carpetas protegidas, ya resueltas; vacia si no hay nada que proteger.

    Ejemplo:
        protegidas = carpetas_protegidas(os.environ.get("BBLIT_DISC"))
    """
    if not valor_disco:
        return []
    disco = Path(valor_disco)
    protegidas: list[Path] = []
    try:
        imagen = localizar_imagen(disco)
    except (ValueError, OSError):
        imagen = None
    if imagen is not None:
        protegidas.append(imagen.resolve().parent)
    if (disco / "fs").is_dir() and disco.resolve() not in protegidas:
        protegidas.append(disco.resolve())
    return protegidas


def validar_salida(salida: Path, valor_disco: str | None) -> None:
    """
    Rechaza una carpeta de salida situada dentro de la carpeta del disco original.

    Contexto:
        El disco es material de solo lectura: ningun volcado debe escribirse junto a el.

    Args:
        salida (Path): Carpeta de salida solicitada.
        valor_disco (str, opcional): Valor de `BBLIT_DISC` en cualquiera de sus cinco formas.

    Raises:
        ValueError: Si la salida cae dentro de una carpeta protegida del disco original.

    Ejemplo:
        validar_salida(Path("analisis/emulador/sesion_titulo"), os.environ.get("BBLIT_DISC"))
    """
    destino = salida.resolve()
    if any(destino.is_relative_to(protegida) for protegida in carpetas_protegidas(valor_disco)):
        raise ValueError("salida: no se puede escribir dentro de la carpeta del disco original")


def esperar_running(
    cliente: ClienteRedux, reloj: Callable[[], float], dormir: Callable[[float], None], inicio: float
) -> float:
    """
    Espera a que el emulador informe `running` verdadero.

    Contexto:
        Primer hito de toda sesion; el servidor web tarda menos de un segundo en responder.

    Args:
        cliente (ClienteRedux): Cliente de la API.
        reloj (Callable): Reloj monotono en segundos.
        dormir (Callable): Funcion de espera.
        inicio (float): Instante de referencia de la sesion.

    Returns:
        float: Segundos transcurridos desde `inicio` hasta `running`.

    Raises:
        EmuladorError: Si no se alcanza en `TOPE_RUNNING` segundos.

    Ejemplo:
        segundos = esperar_running(cliente, time.monotonic, time.sleep, inicio)
    """
    while reloj() - inicio < TOPE_RUNNING:
        try:
            if cliente.esta_corriendo():
                return reloj() - inicio
        except EmuladorError:
            pass
        dormir(INTERVALO_RUNNING)
    raise EmuladorError(f"el emulador no llego a `running` en {TOPE_RUNNING:.0f} s")


def _esperar_pantalla(
    cliente: ClienteRedux,
    config: ConfigSesion,
    reloj: Callable[[], float],
    dormir: Callable[[float], None],
    inicio: float,
) -> float:
    """
    Espera a que la captura deje de ser negra, medido sobre los pixeles.

    Contexto:
        Segundo hito de la sesion. Un fallo puntual de captura o un PNG ilegible se toman como
        "todavia no": el emulador responde con errores mientras la BIOS arranca.

    Args:
        cliente (ClienteRedux): Cliente de la API.
        config (ConfigSesion): Parametros con el tope de espera.
        reloj (Callable): Reloj monotono en segundos.
        dormir (Callable): Funcion de espera.
        inicio (float): Instante de referencia de la sesion.

    Returns:
        float: Segundos desde `inicio` hasta la primera captura con contenido.

    Raises:
        EmuladorError: Si la pantalla sigue negra al agotar `config.tope_hito`.

    Ejemplo:
        segundos = _esperar_pantalla(cliente, config, time.monotonic, time.sleep, inicio)
    """
    limite = reloj() + config.tope_hito
    while reloj() < limite:
        try:
            if not es_pantalla_negra(cliente.capturar_pantalla()):
                return reloj() - inicio
        except (EmuladorError, ValueError):
            pass
        dormir(INTERVALO_SONDEO)
    raise EmuladorError(f"la pantalla sigue negra tras {config.tope_hito:.0f} s")


def _esperar_ejecutable(
    cliente: ClienteRedux,
    config: ConfigSesion,
    reloj: Callable[[], float],
    dormir: Callable[[float], None],
    inicio: float,
) -> float:
    """
    Espera a que la RAM contenga el inicio del ejecutable del juego.

    Contexto:
        Tercer hito de la sesion: la BIOS muestra sus propias pantallas antes de cargar el
        juego, asi que "pantalla no negra" no prueba que el juego haya arrancado; la huella
        del ejecutable en su direccion de carga si lo prueba.

    Args:
        cliente (ClienteRedux): Cliente de la API.
        config (ConfigSesion): Parametros con el ejecutable y el tope de espera.
        reloj (Callable): Reloj monotono en segundos.
        dormir (Callable): Funcion de espera.
        inicio (float): Instante de referencia de la sesion.

    Returns:
        float: Segundos desde `inicio` hasta que la huella aparece en RAM.

    Raises:
        ValueError: Si no se indico `exe_juego` o el ejecutable no es valido.
        EmuladorError: Si la huella no aparece dentro de `config.tope_hito`.

    Ejemplo:
        segundos = _esperar_ejecutable(cliente, config, time.monotonic, time.sleep, inicio)
    """
    if config.exe_juego is None:
        raise ValueError("hito `ejecutable`: falta indicar el ejecutable del juego (--exe-juego)")
    direccion, huella = prefijo_de_ejecutable(config.exe_juego.read_bytes())
    inicio_ram = offset_de_ram(direccion, len(huella))
    limite = reloj() + config.tope_hito
    while reloj() < limite:
        try:
            if cliente.volcar_ram()[inicio_ram : inicio_ram + len(huella)] == huella:
                return reloj() - inicio
        except (EmuladorError, ValueError):
            pass
        dormir(INTERVALO_SONDEO)
    raise EmuladorError(f"el ejecutable no aparecio en RAM tras {config.tope_hito:.0f} s")


def _escribir_resultados(config: ConfigSesion, ram: bytes, png: bytes) -> None:
    """
    Escribe `ram.bin` y `pantalla.png` en la carpeta de salida.

    Contexto:
        Se hace antes del apagado para que un fallo posterior no pierda el volcado.

    Args:
        config (ConfigSesion): Parametros con la carpeta de salida.
        ram (bytes): Volcado de RAM ya validado.
        png (bytes): Captura de pantalla.

    Ejemplo:
        _escribir_resultados(config, ram, png)
    """
    config.salida.mkdir(parents=True, exist_ok=True)
    (config.salida / "ram.bin").write_bytes(ram)
    (config.salida / "pantalla.png").write_bytes(png)


def ejecutar_sesion(
    config: ConfigSesion,
    *,
    cliente: ClienteRedux | None = None,
    lanzar: Callable[..., int] = proceso.lanzar_emulador,
    terminar: Callable[[int | None], None] = proceso.terminar_procesos,
    listar: Callable[[], list[str]] = proceso.listar_procesos,
    puerto_en_uso: Callable[[int], bool] = proceso.puerto_ocupado,
    reloj: Callable[[], float] = time.monotonic,
    dormir: Callable[[float], None] = time.sleep,
) -> dict[str, object]:
    """
    Arranca el emulador, espera el hito, pausa, vuelca RAM y pantalla, y apaga.

    Contexto:
        Implementa el subcomando `sesion`. Toda dependencia externa se inyecta para probar la
        orquestacion con dobles; el apagado en `finally` es la garantia de no dejar procesos.

    Args:
        config (ConfigSesion): Parametros de la sesion.
        cliente (ClienteRedux, opcional): Cliente de la API; por defecto uno para `config.puerto`.
        lanzar (Callable, opcional): Lanzador del emulador.
        terminar (Callable, opcional): Terminador de procesos (recibe el PID o None).
        listar (Callable, opcional): Listado de procesos `pcsx-redux*` vivos.
        puerto_en_uso (Callable, opcional): Comprobacion de puerto ocupado.
        reloj (Callable, opcional): Reloj monotono en segundos.
        dormir (Callable, opcional): Funcion de espera.

    Returns:
        dict[str, object]: Contenido escrito en `sesion.json` (claves en camelCase).

    Raises:
        ValueError: Si el hito es desconocido, falta el ejecutable del hito `ejecutable` o la
            salida cae dentro de la carpeta del disco.
        EmuladorError: Si falta el emulador, la imagen o la BIOS, el puerto esta ocupado, un
            hito no se alcanza, o tras apagar queda algun proceso vivo o el puerto ocupado.

    Ejemplo:
        resultado = ejecutar_sesion(ConfigSesion(cue, bios, exe, trabajo, salida))
    """
    if config.hito not in HITOS:
        raise ValueError(f"hito `{config.hito}`: se esperaba uno de {', '.join(HITOS)}")
    validar_salida(config.salida, os.environ.get("BBLIT_DISC"))
    if puerto_en_uso(config.puerto):
        raise EmuladorError(f"el puerto {config.puerto} ya esta ocupado; use otro con --puerto o `apagar`")
    cliente = cliente or ClienteRedux(config.puerto)
    inicio = reloj()
    pid: int | None = None
    try:
        pid = lanzar(config.ejecutable, config.imagen, config.bios, config.carpeta_trabajo, config.puerto)
        hasta_running = esperar_running(cliente, reloj, dormir, inicio)
        hasta_pantalla: float | None = None
        hasta_ejecutable: float | None = None
        if config.hito == "pantalla":
            hasta_pantalla = _esperar_pantalla(cliente, config, reloj, dormir, inicio)
        elif config.hito == "ejecutable":
            hasta_ejecutable = _esperar_ejecutable(cliente, config, reloj, dormir, inicio)
        if config.retardo_extra > 0:
            dormir(config.retardo_extra)
        cliente.pausar()
        ram = cliente.volcar_ram()
        png = cliente.capturar_pantalla()
        _escribir_resultados(config, ram, png)
    finally:
        terminar(pid)
    restantes = listar()
    if restantes or puerto_en_uso(config.puerto):
        raise EmuladorError("tras apagar siguen procesos del emulador vivos o el puerto ocupado")
    resultado: dict[str, object] = {
        "imagen": config.imagen.name,
        "hito": config.hito,
        "segundosHastaRunning": round(hasta_running, 2),
        "segundosHastaPantalla": None if hasta_pantalla is None else round(hasta_pantalla, 2),
        "segundosHastaEjecutable": None if hasta_ejecutable is None else round(hasta_ejecutable, 2),
        "retardoExtra": config.retardo_extra,
        "fraccionContenido": round(fraccion_con_contenido(decodificar_png(png)), 5),
        "sha256Ram": hashlib.sha256(ram).hexdigest(),
        "bytesRam": len(ram),
        "bytesPng": len(png),
        "puerto": config.puerto,
        "procesosVivosAlFinal": 0,
    }
    (config.salida / "sesion.json").write_text(json.dumps(resultado, indent=2) + "\n", encoding="utf-8")
    return resultado

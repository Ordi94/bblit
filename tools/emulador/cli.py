"""
Interfaz de linea de comandos de `tools.emulador`.

Contexto:
    Capa de presentacion: traduce argumentos a llamadas de `sesion`, `cliente`, `proceso` y
    `comparacion`, y los errores a mensajes breves con codigo de salida 1, sin trazas ni rutas
    internas. Las rutas del emulador y la BIOS se reciben por argumento, por las variables
    `BBLIT_REDUX` y `BBLIT_BIOS`, o se buscan en el toolchain (`BBLIT_TOOLCHAIN`, `config/local.toml`
    o `<raiz>/toolchain`) con la misma resolucion que `tools/build.py`. Las rutas por defecto cuelgan
    de la raiz del repositorio, nunca del directorio desde el que se lanza la orden.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from tools.emulador import comparacion, proceso, sesion
from tools.emulador.cliente import PUERTO_POR_DEFECTO, ClienteRedux
from tools.emulador.dominio import EmuladorError
from tools.toolchain.configuracion import leer_local_toml, resolver_rutas

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
RUTA_LOCAL = Path("config") / "local.toml"
VARIABLE_EMULADOR = "BBLIT_REDUX"
VARIABLE_BIOS = "BBLIT_BIOS"
# Ubicacion de los componentes dentro del toolchain.
EMULADOR_EN_TOOLCHAIN = "pcsx-redux/pcsx-redux.exe"
BIOS_EN_TOOLCHAIN = "duckstation/bios/ps-22a.bin"
# Ubicacion de la imagen de prueba y de la carpeta de trabajo dentro del repositorio.
IMAGEN_POR_DEFECTO = "build/bblit_prueba.cue"
TRABAJO_POR_DEFECTO = "build/emulador"


@dataclass(frozen=True)
class RutasEmulador:
    """Rutas por defecto de las opciones de arranque.

    Attributes:
        emulador: Ejecutable de PCSX-Redux.
        bios: BIOS de PlayStation.
        imagen: Imagen ``.cue`` a cargar.
        trabajo: Carpeta de trabajo del emulador.
    """

    emulador: Path
    bios: Path
    imagen: Path
    trabajo: Path


def resolver_rutas_emulador(entorno: Mapping[str, str], raiz: Path = RAIZ_REPOSITORIO) -> RutasEmulador:
    """
    Resuelve las rutas por defecto del emulador, la BIOS, la imagen y la carpeta de trabajo.

    Contexto:
        Lo usa `construir_parser` para dar valor por defecto a las opciones de arranque. El
        emulador y la BIOS salen del toolchain con la misma politica que `tools/build.py` (variable
        `BBLIT_TOOLCHAIN`, luego `config/local.toml`, luego `<raiz>/toolchain`); `BBLIT_REDUX` y
        `BBLIT_BIOS` los anulan de forma explicita. Una variable vacia se trata como ausente. La
        imagen y la carpeta de trabajo cuelgan de la raiz, no del directorio actual.

    Args:
        entorno (Mapping[str, str]): Variables de entorno (normalmente `os.environ`).
        raiz (Path, opcional): Raiz del repositorio (sustituible en pruebas).

    Returns:
        RutasEmulador: Rutas por defecto.

    Raises:
        ValueError: Si `config/local.toml` existe y no es valido.

    Ejemplo:
        rutas = resolver_rutas_emulador(os.environ)
    """
    toolchain = resolver_rutas(raiz, entorno, leer_local_toml(raiz / RUTA_LOCAL)).toolchain
    return RutasEmulador(
        emulador=Path(entorno.get(VARIABLE_EMULADOR) or toolchain / EMULADOR_EN_TOOLCHAIN),
        bios=Path(entorno.get(VARIABLE_BIOS) or toolchain / BIOS_EN_TOOLCHAIN),
        imagen=raiz / IMAGEN_POR_DEFECTO,
        trabajo=raiz / TRABAJO_POR_DEFECTO,
    )


def _entero(texto: str) -> int:
    """
    Convierte un entero decimal o hexadecimal (`0x...`) recibido por linea de comandos.

    Contexto:
        Tipo de argumento de las direcciones, offsets y longitudes de `comparar`.

    Args:
        texto (str): Valor escrito por el usuario.

    Returns:
        int: Valor entero.

    Raises:
        argparse.ArgumentTypeError: Si el texto no es un entero valido.

    Ejemplo:
        _entero("0x80014A00")
    """
    try:
        return int(texto, 0)
    except ValueError:
        raise argparse.ArgumentTypeError(f"`{texto}`: se esperaba un entero (decimal o 0x)") from None


def _agregar_puerto(parser: argparse.ArgumentParser) -> None:
    """
    Agrega la opcion `--puerto` a un subcomando.

    Contexto:
        Comun a todos los subcomandos que hablan con un emulador ya arrancado.

    Args:
        parser (argparse.ArgumentParser): Subcomando que recibe la opcion.

    Ejemplo:
        _agregar_puerto(sub.add_parser("pausar"))
    """
    parser.add_argument("--puerto", type=int, default=PUERTO_POR_DEFECTO, help="puerto del servidor web")


def _agregar_arranque(parser: argparse.ArgumentParser, rutas: RutasEmulador) -> None:
    """
    Agrega las opciones de arranque (imagen, BIOS, emulador, carpeta de trabajo, puerto).

    Contexto:
        Comun a `arrancar` y `sesion`.

    Args:
        parser (argparse.ArgumentParser): Subcomando que recibe las opciones.
        rutas (RutasEmulador): Valores por defecto de las rutas.

    Ejemplo:
        _agregar_arranque(sub.add_parser("arrancar"), resolver_rutas_emulador(os.environ))
    """
    parser.add_argument("--imagen", type=Path, default=rutas.imagen, help="imagen .cue a cargar")
    parser.add_argument("--bios", type=Path, default=rutas.bios, help="BIOS")
    parser.add_argument("--emulador", type=Path, default=rutas.emulador, help="pcsx-redux.exe")
    parser.add_argument("--trabajo", type=Path, default=rutas.trabajo, help="carpeta de trabajo del emulador")
    _agregar_puerto(parser)


def construir_parser(
    entorno: Mapping[str, str] | None = None, raiz: Path = RAIZ_REPOSITORIO
) -> argparse.ArgumentParser:
    """
    Construye el analizador de argumentos con todos los subcomandos.

    Contexto:
        Lo usa `main`; se expone para probar los argumentos por separado.

    Args:
        entorno (Mapping[str, str], opcional): Variables de entorno; por defecto `os.environ`.
        raiz (Path, opcional): Raiz del repositorio (sustituible en pruebas).

    Returns:
        argparse.ArgumentParser: Analizador listo para `parse_args`.

    Raises:
        ValueError: Si `config/local.toml` existe y no es valido.

    Ejemplo:
        argumentos = construir_parser().parse_args(["apagar"])
    """
    rutas = resolver_rutas_emulador(os.environ if entorno is None else entorno, raiz)
    parser = argparse.ArgumentParser(prog="python -m tools.emulador", description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)

    arrancar = sub.add_parser("arrancar", help="lanza el emulador y espera a `running`")
    _agregar_arranque(arrancar, rutas)

    for nombre, ayuda in (("volcar", "guarda la RAM (2 MiB)"), ("capturar", "guarda la pantalla en PNG")):
        guardar = sub.add_parser(nombre, help=ayuda)
        guardar.add_argument("--salida", type=Path, required=True, help="archivo de destino")
        _agregar_puerto(guardar)

    for nombre, ayuda in (("pausar", "pausa la emulacion"), ("reanudar", "reanuda la emulacion")):
        _agregar_puerto(sub.add_parser(nombre, help=ayuda))

    apagar = sub.add_parser("apagar", help="termina todos los procesos pcsx-redux")
    _agregar_puerto(apagar)

    comparar = sub.add_parser("comparar", help="compara una region de un volcado con un archivo o volcado")
    comparar.add_argument("--volcado", type=Path, required=True, help="volcado de RAM")
    comparar.add_argument("--direccion", type=_entero, required=True, help="direccion 0x80...")
    destino = comparar.add_mutually_exclusive_group(required=True)
    destino.add_argument("--archivo", type=Path, help="archivo con el que comparar")
    destino.add_argument("--volcado-b", type=Path, help="segundo volcado de RAM")
    comparar.add_argument("--offset-archivo", type=_entero, default=0, help="offset en el archivo")
    comparar.add_argument("--longitud", type=_entero, default=None, help="bytes a comparar")

    sesion_p = sub.add_parser("sesion", help="arranca, espera un hito, vuelca RAM y pantalla, y apaga")
    _agregar_arranque(sesion_p, rutas)
    sesion_p.add_argument("--salida", type=Path, required=True, help="carpeta de salida")
    sesion_p.add_argument("--espera-hito", choices=sesion.HITOS, default="pantalla", help="hito a esperar")
    sesion_p.add_argument(
        "--tope", type=float, default=sesion.TOPE_PANTALLA_POR_DEFECTO, help="segundos maximos del hito"
    )
    sesion_p.add_argument("--exe-juego", type=Path, default=None, help="PS-X EXE del hito `ejecutable`")
    sesion_p.add_argument("--retardo", type=float, default=0.0, help="segundos extra tras el hito")
    return parser


def _imprimir(datos: dict[str, object]) -> None:
    """
    Imprime un diccionario como JSON legible.

    Contexto:
        Formato de salida comun de los subcomandos.

    Args:
        datos (dict[str, object]): Contenido a imprimir.

    Ejemplo:
        _imprimir({"estado": "ok"})
    """
    print(json.dumps(datos, indent=2))


def _ejecutar_arrancar(argumentos: argparse.Namespace) -> None:
    """
    Lanza el emulador, espera a `running` y deja el emulador corriendo.

    Contexto:
        Subcomando `arrancar`. Si la espera falla, termina lo que haya lanzado.

    Args:
        argumentos (argparse.Namespace): Argumentos del subcomando.

    Raises:
        EmuladorError: Si falta algun archivo, el puerto esta ocupado o no llega a `running`.

    Ejemplo:
        _ejecutar_arrancar(argumentos)
    """
    if proceso.puerto_ocupado(argumentos.puerto):
        raise EmuladorError(f"el puerto {argumentos.puerto} ya esta ocupado; use otro con --puerto")
    inicio = time.monotonic()
    pid = proceso.lanzar_emulador(
        argumentos.emulador, argumentos.imagen, argumentos.bios, argumentos.trabajo, argumentos.puerto
    )
    try:
        segundos = sesion.esperar_running(ClienteRedux(argumentos.puerto), time.monotonic, time.sleep, inicio)
    except EmuladorError:
        proceso.terminar_procesos(pid)
        raise
    _imprimir({"pid": pid, "puerto": argumentos.puerto, "segundosHastaRunning": round(segundos, 2)})


def _ejecutar_guardado(argumentos: argparse.Namespace) -> None:
    """
    Guarda la RAM o la pantalla de un emulador ya arrancado.

    Contexto:
        Subcomandos `volcar` y `capturar`.

    Args:
        argumentos (argparse.Namespace): Argumentos del subcomando.

    Raises:
        EmuladorError: Si el emulador no responde o la respuesta no es valida.
        ValueError: Si el volcado no tiene el tamano de la RAM o la salida es invalida.

    Ejemplo:
        _ejecutar_guardado(argumentos)
    """
    sesion.validar_salida(argumentos.salida, os.environ.get("BBLIT_DISC"))
    cliente = ClienteRedux(argumentos.puerto)
    datos = cliente.volcar_ram() if argumentos.comando == "volcar" else cliente.capturar_pantalla()
    argumentos.salida.parent.mkdir(parents=True, exist_ok=True)
    argumentos.salida.write_bytes(datos)
    _imprimir({"salida": argumentos.salida.name, "bytes": len(datos)})


def _ejecutar_comparar(argumentos: argparse.Namespace) -> None:
    """
    Compara una region de un volcado y muestra el resultado en JSON.

    Contexto:
        Subcomando `comparar`.

    Args:
        argumentos (argparse.Namespace): Argumentos del subcomando.

    Raises:
        ValueError: Si el volcado, la direccion o los offsets son invalidos.
        OSError: Si algun archivo no se puede leer.

    Ejemplo:
        _ejecutar_comparar(argumentos)
    """
    if argumentos.archivo is not None:
        resultado = comparacion.comparar_con_archivo(
            argumentos.volcado,
            argumentos.direccion,
            argumentos.archivo,
            argumentos.offset_archivo,
            argumentos.longitud,
        )
    else:
        resultado = comparacion.comparar_volcados(
            argumentos.volcado, argumentos.volcado_b, argumentos.direccion, argumentos.longitud
        )
    _imprimir(resultado.a_json())


def _ejecutar_apagar(argumentos: argparse.Namespace) -> None:
    """
    Termina los procesos del emulador y comprueba que no queda ninguno.

    Contexto:
        Subcomando `apagar`; no depende del cliente HTTP, asi que funciona aunque el emulador
        este colgado.

    Args:
        argumentos (argparse.Namespace): Argumentos del subcomando.

    Raises:
        EmuladorError: Si tras terminar siguen procesos vivos o el puerto ocupado.

    Ejemplo:
        _ejecutar_apagar(argumentos)
    """
    proceso.terminar_procesos(None)
    restantes = proceso.listar_procesos()
    if restantes or proceso.puerto_ocupado(argumentos.puerto):
        raise EmuladorError("siguen procesos del emulador vivos o el puerto ocupado")
    _imprimir({"procesosVivos": 0, "puerto": argumentos.puerto})


def _ejecutar_sesion(argumentos: argparse.Namespace) -> None:
    """
    Ejecuta una sesion completa y muestra su resumen.

    Contexto:
        Subcomando `sesion`.

    Args:
        argumentos (argparse.Namespace): Argumentos del subcomando.

    Raises:
        EmuladorError: Si un hito no se alcanza o queda algo vivo al final.
        ValueError: Si los parametros son invalidos.

    Ejemplo:
        _ejecutar_sesion(argumentos)
    """
    config = sesion.ConfigSesion(
        imagen=argumentos.imagen,
        bios=argumentos.bios,
        ejecutable=argumentos.emulador,
        carpeta_trabajo=argumentos.trabajo,
        salida=argumentos.salida,
        puerto=argumentos.puerto,
        hito=argumentos.espera_hito,
        tope_hito=argumentos.tope,
        retardo_extra=argumentos.retardo,
        exe_juego=argumentos.exe_juego,
    )
    _imprimir(sesion.ejecutar_sesion(config))


def main(
    argv: Sequence[str] | None = None,
    entorno: Mapping[str, str] | None = None,
    raiz: Path = RAIZ_REPOSITORIO,
) -> int:
    """
    Ejecuta el subcomando solicitado y devuelve el codigo de salida del proceso.

    Contexto:
        Punto de entrada de `python -m tools.emulador`.

    Args:
        argv (Sequence[str], opcional): Argumentos; por defecto los de la linea de comandos.
        entorno (Mapping[str, str], opcional): Variables de entorno; por defecto `os.environ`.
        raiz (Path, opcional): Raiz del repositorio (sustituible en pruebas).

    Returns:
        int: 0 si termino bien, 1 si una validacion, el emulador o un archivo fallo.

    Ejemplo:
        codigo = main(["comparar", "--volcado", "ram.bin", "--direccion", "0x80014A00", "--archivo", "x"])
    """
    ejecutores = {
        "arrancar": _ejecutar_arrancar,
        "volcar": _ejecutar_guardado,
        "capturar": _ejecutar_guardado,
        "comparar": _ejecutar_comparar,
        "apagar": _ejecutar_apagar,
        "sesion": _ejecutar_sesion,
    }
    try:
        argumentos = construir_parser(entorno, raiz).parse_args(argv)
        if argumentos.comando == "pausar":
            ClienteRedux(argumentos.puerto).pausar()
            _imprimir({"estado": "pausado"})
        elif argumentos.comando == "reanudar":
            ClienteRedux(argumentos.puerto).reanudar()
            _imprimir({"estado": "en marcha"})
        else:
            ejecutores[argumentos.comando](argumentos)
    except (ValueError, EmuladorError) as error:
        print(f"error: {error}")
        return 1
    except OSError as error:
        print(f"error de entrada/salida: {type(error).__name__}")
        return 1
    return 0

"""
Gestion de los procesos de PCSX-Redux: lanzar, listar y terminar.

Contexto:
    Capa de infraestructura de procesos de `tools.emulador`. El lanzador `pcsx-redux.exe` crea
    un segundo proceso `pcsx-redux.main`; ambos deben terminar o el puerto web queda ocupado.
    La terminacion se hace por arbol de PID y ademas por nombre, porque el lanzador puede haber
    salido ya y dejar al proceso principal huerfano.
"""

from __future__ import annotations

import socket
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from tools.emulador.dominio import EmuladorError

PATRON_PROCESOS = "pcsx-redux*"
TIEMPO_ORDEN = 30.0

Ejecutor = Callable[[Sequence[str]], str]
Lanzador = Callable[[Sequence[str], Path], int]


def ejecutar_orden(argumentos: Sequence[str]) -> str:
    """
    Ejecuta una orden del sistema con tiempo limite y devuelve su salida estandar.

    Contexto:
        Transporte real de `listar_procesos` y `terminar_procesos`. El codigo de salida se
        ignora a proposito: `taskkill` devuelve error cuando no hay nada que terminar.

    Args:
        argumentos (Sequence[str]): Orden y argumentos, sin pasar por un interprete de comandos.

    Returns:
        str: Salida estandar decodificada.

    Raises:
        subprocess.TimeoutExpired: Si la orden tarda mas de `TIEMPO_ORDEN` segundos.

    Ejemplo:
        salida = ejecutar_orden(["tasklist", "/FO", "CSV", "/NH"])
    """
    resultado = subprocess.run(
        list(argumentos),
        capture_output=True,
        text=True,
        errors="replace",
        timeout=TIEMPO_ORDEN,
        check=False,
    )
    return resultado.stdout


def lanzar_proceso(argumentos: Sequence[str], carpeta_trabajo: Path) -> int:
    """
    Lanza un proceso desacoplado de la consola y devuelve su PID.

    Contexto:
        Transporte real de `lanzar_emulador`; sin canales heredados para que el emulador no
        bloquee al llamador ni escriba en su consola.

    Args:
        argumentos (Sequence[str]): Ejecutable y argumentos.
        carpeta_trabajo (Path): Directorio de trabajo del proceso.

    Returns:
        int: PID del proceso lanzado.

    Raises:
        OSError: Si el ejecutable no se puede lanzar.

    Ejemplo:
        pid = lanzar_proceso(["pcsx-redux.exe"], Path("build/emulador"))
    """
    proceso = subprocess.Popen(
        list(argumentos),
        cwd=carpeta_trabajo,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proceso.pid


def puerto_ocupado(puerto: int, tiempo_espera: float = 1.0) -> bool:
    """
    Comprueba si algun proceso escucha en el puerto local.

    Contexto:
        Se consulta antes de lanzar (para fallar con un mensaje claro) y despues de apagar
        (para demostrar que no quedo nada).

    Args:
        puerto (int): Puerto TCP en 127.0.0.1.
        tiempo_espera (float, opcional): Segundos maximos para el intento de conexion.

    Returns:
        bool: True si una conexion al puerto tiene exito.

    Ejemplo:
        if puerto_ocupado(8080): ...
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conexion:
        conexion.settimeout(tiempo_espera)
        return conexion.connect_ex(("127.0.0.1", puerto)) == 0


def construir_argumentos(ejecutable: Path, imagen: Path, bios: Path, puerto: int) -> list[str]:
    """
    Construye la linea de comandos de PCSX-Redux con servidor web.

    Contexto:
        Las rutas se resuelven a absolutas porque el emulador se lanza con un directorio de
        trabajo distinto del llamador (`-portable` escribe su configuracion ahi).

    Args:
        ejecutable (Path): `pcsx-redux.exe`.
        imagen (Path): Archivo `.cue` o `.bin` a cargar.
        bios (Path): BIOS de PlayStation.
        puerto (int): Puerto del servidor web.

    Returns:
        list[str]: Argumentos listos para lanzar.

    Ejemplo:
        argumentos = construir_argumentos(exe, cue, bios, 8080)
    """
    return [
        str(ejecutable.resolve()),
        "-portable",
        "-loadiso",
        str(imagen.resolve()),
        "-bios",
        str(bios.resolve()),
        "-run",
        "-webserver",
        "-webserver-port",
        str(puerto),
    ]


def lanzar_emulador(
    ejecutable: Path,
    imagen: Path,
    bios: Path,
    carpeta_trabajo: Path,
    puerto: int,
    *,
    lanzador: Lanzador = lanzar_proceso,
) -> int:
    """
    Lanza PCSX-Redux con la imagen y la BIOS indicadas.

    Contexto:
        Primer paso de `sesion` y del subcomando `arrancar`.

    Args:
        ejecutable (Path): `pcsx-redux.exe`.
        imagen (Path): Imagen a cargar.
        bios (Path): BIOS de PlayStation.
        carpeta_trabajo (Path): Directorio de trabajo; se crea si no existe.
        puerto (int): Puerto del servidor web.
        lanzador (Lanzador, opcional): Funcion que lanza el proceso; por defecto la real.

    Returns:
        int: PID del lanzador (el proceso principal es un hijo suyo).

    Raises:
        EmuladorError: Si el ejecutable, la imagen o la BIOS no existen.

    Ejemplo:
        pid = lanzar_emulador(exe, cue, bios, Path("build/emulador"), 8080)
    """
    for nombre, ruta in (("emulador", ejecutable), ("imagen", imagen), ("bios", bios)):
        if not ruta.is_file():
            raise EmuladorError(f"{nombre}: no existe el archivo indicado")
    carpeta_trabajo.mkdir(parents=True, exist_ok=True)
    return lanzador(construir_argumentos(ejecutable, imagen, bios, puerto), carpeta_trabajo.resolve())


def listar_procesos(ejecutor: Ejecutor = ejecutar_orden) -> list[str]:
    """
    Lista los procesos cuyo nombre empieza por `pcsx-redux`.

    Contexto:
        Comprobacion final de la sesion y del subcomando `apagar`.

    Args:
        ejecutor (Ejecutor, opcional): Funcion que ejecuta la orden del sistema.

    Returns:
        list[str]: Nombres de imagen de los procesos vivos; vacia si no hay ninguno.

    Ejemplo:
        assert listar_procesos() == []
    """
    salida = ejecutor(["tasklist", "/FI", f"IMAGENAME eq {PATRON_PROCESOS}", "/FO", "CSV", "/NH"])
    nombres = []
    for linea in salida.splitlines():
        if linea.startswith('"'):
            nombres.append(linea.split('","')[0].strip('"'))
    return nombres


def terminar_procesos(pid: int | None = None, ejecutor: Ejecutor = ejecutar_orden) -> None:
    """
    Termina el arbol del lanzador y todo proceso `pcsx-redux*` que siga vivo.

    Contexto:
        Se llama siempre desde un `finally`, de modo que no depende de que el cliente HTTP
        funcione. La segunda orden por nombre cubre al proceso principal si el lanzador ya salio.

    Args:
        pid (int, opcional): PID del lanzador; si es None solo se termina por nombre.
        ejecutor (Ejecutor, opcional): Funcion que ejecuta la orden del sistema.

    Ejemplo:
        terminar_procesos(pid)
    """
    if pid is not None:
        ejecutor(["taskkill", "/F", "/T", "/PID", str(pid)])
    ejecutor(["taskkill", "/F", "/T", "/IM", PATRON_PROCESOS])

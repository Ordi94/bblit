"""Particion, ensamblado, enlace y verificacion del overlay de codigo.

Capa de procesos del paquete. Reutiliza de ``tools.reconstruccion`` el ejecutor de procesos y
la construccion de las ordenes de splat, ensamblador, enlazador y objcopy; todo lo que escribe
queda dentro de ``asm/overlay/``, ``build/overlay/`` y ``config/symbols_overlay.txt``.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from tools.overlay import dominio
from tools.overlay.dominio import VarianteExtraida
from tools.overlay.extraccion import leer_binario
from tools.reconstruccion import dominio as dominio_exe
from tools.reconstruccion.infraestructura import (
    Ejecutor,
    Herramientas,
    ProcesoError,
    ejecutar_proceso,
)

RUTA_SIMBOLOS = "config/symbols_overlay.txt"
TIMEOUT_SPLAT_S = 300
TIMEOUT_ENSAMBLAR_S = 120
TIMEOUT_ENLAZAR_S = 120


@dataclass(frozen=True)
class ResumenParticion:
    """Conteos de una particion terminada.

    Attributes:
        identificador: Variante particionada.
        funciones: Funciones declaradas en el archivo de simbolos.
        glabel: Funciones que el particionador emitio en el codigo.
        palabras_en_texto: Palabras no decodificadas dentro del texto (debe ser cero).
    """

    identificador: str
    funciones: int
    glabel: int
    palabras_en_texto: int


def _ruta_asm(identificador: str) -> str:
    """Carpeta de ensamblador de una variante."""
    return f"asm/overlay/{identificador}"


def _artefactos(identificador: str) -> tuple[str, ...]:
    """Rutas (relativas a la raiz) que ``split`` y ``build`` generan para una variante."""
    base = f"build/overlay/{identificador}"
    return (
        _ruta_asm(identificador),
        base,
        f"{base}.ld",
        f"{base}.enlace.ld",
        f"{base}_undefined_funcs_auto.txt",
        f"{base}_undefined_syms_auto.txt",
        f"{base}.elf",
        f"{base}.map",
        f"{base}.bin",
    )


def _borrar(ruta: Path) -> bool:
    """Elimina un archivo o carpeta si existe; informa si habia algo que eliminar."""
    if ruta.is_dir():
        shutil.rmtree(ruta)
        return True
    if ruta.exists():
        ruta.unlink()
        return True
    return False


def salidas_de_construccion(identificador: str) -> tuple[str, ...]:
    """
    Lista las rutas que ``build`` produce para una variante y que ``verify`` consume.

    Contexto:
        Son los objetos, el script de enlace propio, el ELF, el mapa y la imagen plana. No
        incluye el script de splat (``<id>.ld``) ni las listas ``_undefined_*_auto.txt``:
        son salida de ``split`` y entrada de ``build``, asi que borrarlas lo dejaria sin
        poder ejecutarse.

    Args:
        identificador (str): Identificador de la variante.

    Returns:
        tuple[str, ...]: Rutas relativas a la raiz del repositorio.

    Ejemplo:
        rutas = salidas_de_construccion("a")
    """
    base = f"build/overlay/{identificador}"
    return (base, f"{base}.enlace.ld", f"{base}.elf", f"{base}.map", f"{base}.bin")


def invalidar_salida(raiz: Path, identificador: str) -> list[str]:
    """
    Elimina la salida de una construccion anterior de la variante.

    Contexto:
        Si ``build`` falla a mitad (fuente roto, herramienta ausente) no debe sobrevivir el
        binario de la corrida anterior: ``verify`` lo aprobaria aunque ya no corresponda al
        codigo. Con la salida invalidada, un build fallido deja ``verify`` en ``FAIL``.
        Es idempotente: una variante sin salida previa no es un error.

    Args:
        raiz (Path): Raiz del repositorio.
        identificador (str): Identificador de la variante.

    Returns:
        list[str]: Rutas relativas que existian y se eliminaron.

    Ejemplo:
        eliminadas = invalidar_salida(Path("."), "a")
    """
    return [ruta for ruta in salidas_de_construccion(identificador) if _borrar(raiz / ruta)]


def generar_simbolos(raiz: Path, variantes: list[VarianteExtraida]) -> list[int]:
    """
    Genera ``config/symbols_overlay.txt`` a partir de las variantes extraidas.

    Contexto:
        Orden ``simbolos``. El archivo es comun a las tres variantes, asi que se exige que
        sus inicios de funcion coincidan; si una edicion futura los separara habria que
        pasar a un archivo por variante.

    Args:
        raiz (Path): Raiz del repositorio.
        variantes (list[VarianteExtraida]): Variantes registradas en la configuracion.

    Returns:
        list[int]: Desplazamientos de las funciones escritas.

    Raises:
        FileNotFoundError: Si falta algun binario extraido.
        ValueError: Si un binario no es valido o las variantes no comparten inicios de funcion.

    Ejemplo:
        funciones = generar_simbolos(Path("."), variantes)
    """
    por_variante = {v.identificador: dominio.descubrir_funciones(leer_binario(raiz, v)) for v in variantes}
    referencia = next(iter(por_variante.values()))
    for identificador, inicios in por_variante.items():
        if inicios != referencia:
            raise ValueError(f"la variante '{identificador}' no comparte los inicios de funcion de las demas")
    destino = raiz / RUTA_SIMBOLOS
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(dominio.texto_simbolos(referencia), encoding="utf-8", newline="\n")
    return list(referencia)


def dividir(
    raiz: Path, variante: VarianteExtraida, python: str, ejecutar: Ejecutor = ejecutar_proceso
) -> ResumenParticion:
    """
    Particiona una variante con splat y contrasta funciones y palabras sin decodificar.

    Contexto:
        Orden ``split``. Es idempotente: borra la salida anterior de la variante. Despues de
        particionar comprueba que cada funcion declarada produjo exactamente un ``glabel`` y que
        el texto no contiene palabras sueltas.

    Args:
        raiz (Path): Raiz del repositorio.
        variante (VarianteExtraida): Variante a particionar.
        python (str): Interprete que ejecuta el particionador.
        ejecutar (Ejecutor, opcional): Ejecutor de procesos, sustituible en pruebas.

    Returns:
        ResumenParticion: Conteos de la particion.

    Raises:
        FileNotFoundError: Si falta el binario, la configuracion de splat o el archivo de simbolos.
        ValueError: Si el binario no coincide con su huella, el archivo de simbolos no declara
            funciones o los conteos no cuadran.
        ProcesoError: Si splat falla o no genera el script del enlazador.

    Ejemplo:
        resumen = dividir(Path("."), variante, sys.executable)
    """
    identificador = variante.identificador
    leer_binario(raiz, variante)
    simbolos = raiz / RUTA_SIMBOLOS
    if not simbolos.is_file():
        raise FileNotFoundError("falta config/symbols_overlay.txt: ejecute primero 'simbolos'")
    funciones = sorted(set(dominio.funciones_de_simbolos(simbolos.read_text(encoding="utf-8"))))
    if not funciones:
        raise ValueError("config/symbols_overlay.txt no declara ninguna funcion")
    configuracion = f"config/splat_overlay_{identificador}.yaml"
    if not (raiz / configuracion).is_file():
        raise FileNotFoundError(f"falta {configuracion}")
    for ruta in _artefactos(identificador):
        _borrar(raiz / ruta)
    ejecutar(dominio_exe.comando_splat(python, configuracion), raiz, TIMEOUT_SPLAT_S)
    if not (raiz / f"build/overlay/{identificador}.ld").is_file():
        raise ProcesoError("splat no genero el script del enlazador")
    asm = (raiz / _ruta_asm(identificador) / "codigo.s").read_text(encoding="utf-8")
    resumen = ResumenParticion(
        identificador, len(funciones), dominio.contar_glabel(asm), dominio.contar_palabras(asm)
    )
    if resumen.glabel != resumen.funciones:
        raise ValueError(
            f"variante '{identificador}': {resumen.glabel} funciones en el asm y "
            f"{resumen.funciones} en config/symbols_overlay.txt"
        )
    if resumen.palabras_en_texto:
        raise ValueError(
            f"variante '{identificador}': {resumen.palabras_en_texto} palabras sin decodificar en el texto"
        )
    return resumen


def construir(
    raiz: Path, variante: VarianteExtraida, herramientas: Herramientas, ejecutar: Ejecutor = ejecutar_proceso
) -> Path:
    """
    Ensambla y enlaza una variante y extrae la imagen plana.

    Contexto:
        Orden ``build``. Los objetos salen del script de splat; el enlace usa un script propio
        sin alineaciones (ver ``generar_script_enlace``). Antes de ensamblar elimina la salida
        de la construccion anterior de la variante (ver ``invalidar_salida``), de modo que un
        fallo a mitad no deja un binario obsoleto que ``verify`` pueda aprobar.

    Args:
        raiz (Path): Raiz del repositorio.
        variante (VarianteExtraida): Variante a construir.
        herramientas (Herramientas): Ensamblador, enlazador y objcopy.
        ejecutar (Ejecutor, opcional): Ejecutor de procesos, sustituible en pruebas.

    Returns:
        Path: Ruta de ``build/overlay/<id>.bin``.

    Raises:
        FileNotFoundError: Si falta el script de splat o un fuente (hay que ejecutar ``split``).
        ValueError: Si el script no referencia objetos conocidos.
        ProcesoError: Si una herramienta falla.

    Ejemplo:
        binario = construir(Path("."), variante, herramientas)
    """
    identificador = variante.identificador
    base = f"build/overlay/{identificador}"
    script = raiz / f"{base}.ld"
    if not script.is_file():
        raise FileNotFoundError("falta el script del enlazador: ejecute primero 'split'")
    invalidar_salida(raiz, identificador)
    entradas = dominio.entradas_del_enlazador(script.read_text(encoding="utf-8"))
    for objeto in dict.fromkeys(objeto for objeto, _ in entradas):
        fuente = dominio.fuente_de_objeto(objeto, identificador)
        if not (raiz / fuente).is_file():
            raise FileNotFoundError(f"falta el fuente '{fuente}': ejecute primero 'split'")
        (raiz / objeto).parent.mkdir(parents=True, exist_ok=True)
        comando = dominio_exe.comando_ensamblar(
            herramientas.ensamblador, fuente, objeto, f"{_ruta_asm(identificador)}/include"
        )
        ejecutar(comando, raiz, TIMEOUT_ENSAMBLAR_S)
    enlace = f"{base}.enlace.ld"
    (raiz / enlace).write_text(dominio.generar_script_enlace(entradas), encoding="utf-8", newline="\n")
    automaticos = [
        ruta
        for ruta in (f"{base}_undefined_funcs_auto.txt", f"{base}_undefined_syms_auto.txt")
        if (raiz / ruta).is_file()
    ]
    ejecutar(
        dominio_exe.comando_enlazar(
            herramientas.enlazador, [enlace, *automaticos], f"{base}.elf", f"{base}.map"
        ),
        raiz,
        TIMEOUT_ENLAZAR_S,
    )
    ejecutar(
        dominio_exe.comando_objcopy(herramientas.objcopy, f"{base}.elf", f"{base}.bin"),
        raiz,
        TIMEOUT_ENSAMBLAR_S,
    )
    return raiz / f"{base}.bin"


def verificar(raiz: Path, variante: VarianteExtraida) -> tuple[bool, str]:
    """
    Compara el binario reconstruido de una variante con el extraido del disco.

    Contexto:
        Orden ``verify``: la comparacion es byte a byte y el mensaje de fallo incluye el
        desplazamiento de la primera diferencia. Una variante sin binario reconstruido (no se
        construyo o su construccion fallo) es un ``FAIL`` de esa variante y no una excepcion,
        para que la orden siga con las demas y devuelva 1 al final.

    Args:
        raiz (Path): Raiz del repositorio.
        variante (VarianteExtraida): Variante a verificar.

    Returns:
        tuple[bool, str]: Si coinciden y la linea a imprimir (``OK`` o ``FAIL``).

    Raises:
        FileNotFoundError: Si falta el binario extraido (hay que ejecutar ``extraer``).
        ValueError: Si el binario extraido no coincide con su huella registrada.

    Ejemplo:
        coincide, mensaje = verificar(Path("."), variante)
    """
    esperado = leer_binario(raiz, variante)
    construido = raiz / f"build/overlay/{variante.identificador}.bin"
    if not construido.is_file():
        return False, f"FAIL {variante.identificador} el binario reconstruido no existe"
    if construido.stat().st_size > dominio.TAMANO_HUECO:
        return False, f"FAIL {variante.identificador} el binario reconstruido excede el hueco del overlay"
    return dominio.resultado_verificacion(variante.identificador, construido.read_bytes(), esperado)

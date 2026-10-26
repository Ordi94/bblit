"""Lectura de archivos BZZ, desempaquetado a disco e inventario.

Contexto:
    Capa de entrada/salida del paquete: abre los archivos, recorta cada seccion con la
    cabecera ya validada (``dominio``), la descomprime (``descompresion``) y escribe los
    resultados. Las reglas del formato no viven aqui.
"""

from __future__ import annotations

import csv
import hashlib
import json
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from tools.bzz.descompresion import descomprimir_detallado
from tools.bzz.dominio import Cabecera, Seccion, leer_cabecera, nombre_archivo_seccion, validar_consumo

TAMANO_MAXIMO_ARCHIVO = 256 * 1024 * 1024
"""Cota del tamano de un archivo BZZ; los reales miden menos de 2 MiB."""

NOMBRE_MANIFIESTO = "manifiesto.json"
"""Nombre del manifiesto que acompana a las secciones desempaquetadas."""

COLUMNAS_INVENTARIO = (
    "archivo",
    "indice",
    "tipo",
    "offset",
    "tamano_comprimido",
    "tamano_descomprimido",
    "sha256",
    "segundos",
)
"""Columnas del CSV de inventario, una fila por seccion."""


@dataclass(frozen=True)
class SeccionDescomprimida:
    """Una seccion ya descomprimida junto con los datos de su lectura.

    Attributes:
        seccion: Entrada de la tabla de secciones.
        datos: Contenido descomprimido.
        sha256: Resumen SHA-256 del contenido descomprimido, en hexadecimal.
        segundos: Tiempo empleado en descomprimir la seccion.
    """

    seccion: Seccion
    datos: bytes
    sha256: str
    segundos: float


def leer_archivo_bzz(ruta: Path) -> bytes:
    """Lee un archivo BZZ completo acotando su tamano.

    Contexto:
        Punto de entrada de todos los flujos de la capa: evita cargar en memoria un archivo
        que no puede ser un contenedor valido.

    Args:
        ruta (Path): Ubicacion del archivo.

    Returns:
        bytes: Contenido completo.

    Raises:
        ValueError: Si el archivo supera ``TAMANO_MAXIMO_ARCHIVO``.
        OSError: Si el archivo no existe o no se puede leer.

    Ejemplo:
        datos = leer_archivo_bzz(Path("L01A.BZZ"))
    """
    tamano = ruta.stat().st_size
    if tamano > TAMANO_MAXIMO_ARCHIVO:
        raise ValueError(f"tamano del archivo={tamano} supera el maximo de {TAMANO_MAXIMO_ARCHIVO}")
    return ruta.read_bytes()


def descomprimir_secciones(datos: bytes, cabecera: Cabecera | None = None) -> Iterator[SeccionDescomprimida]:
    """Descomprime una a una las secciones de un contenedor BZZ.

    Contexto:
        Base de ``desempaquetar`` y ``generar_inventario``. Es un generador para no tener
        todas las secciones descomprimidas en memoria a la vez.

    Args:
        datos (bytes): Contenido completo del archivo .BZZ.
        cabecera (Cabecera, opcional): Cabecera ya validada de ``datos``; si se omite se lee
            y valida aqui.

    Yields:
        SeccionDescomprimida: Cada seccion en el orden de la tabla.

    Raises:
        ValueError: Si la cabecera es invalida o alguna seccion no se puede descomprimir; el
            mensaje indica el indice de la seccion.

    Ejemplo:
        for item in descomprimir_secciones(datos):
            print(item.seccion.indice, len(item.datos))
    """
    if cabecera is None:
        cabecera = leer_cabecera(datos)
    for seccion in cabecera.secciones:
        fin = seccion.offset + seccion.tamano_alineado
        inicio_reloj = time.perf_counter()
        try:
            resultado = descomprimir_detallado(datos[seccion.offset : fin])
        except ValueError as error:
            raise ValueError(f"seccion {seccion.indice}: {error}") from None
        segundos = time.perf_counter() - inicio_reloj
        validar_consumo(seccion.indice, resultado.bytes_consumidos, seccion.tamano)
        yield SeccionDescomprimida(
            seccion=seccion,
            datos=resultado.datos,
            sha256=hashlib.sha256(resultado.datos).hexdigest(),
            segundos=segundos,
        )


def construir_manifiesto(
    nombre_archivo: str,
    cabecera: Cabecera,
    secciones: list[SeccionDescomprimida],
) -> dict[str, object]:
    """Arma el manifiesto JSON de un archivo desempaquetado.

    Contexto:
        El manifiesto es el contrato con las herramientas de extraccion posteriores; usa
        camelCase porque es JSON.

    Args:
        nombre_archivo (str): Nombre del archivo de origen, sin carpetas.
        cabecera (Cabecera): Cabecera ya validada.
        secciones (list[SeccionDescomprimida]): Secciones descomprimidas, en orden.

    Returns:
        dict[str, object]: Diccionario con ``archivo``, ``version`` y ``secciones``.

    Raises:
        ValueError: Si la cantidad de secciones no coincide con la cabecera.

    Ejemplo:
        manifiesto = construir_manifiesto("L01A.BZZ", cabecera, secciones)
    """
    if len(secciones) != len(cabecera.secciones):
        raise ValueError(
            f"secciones={len(secciones)} distinto de la cabecera={len(cabecera.secciones)}",
        )
    return {
        "archivo": nombre_archivo,
        "version": cabecera.version,
        "secciones": [
            {
                "indice": item.seccion.indice,
                "tipo": item.seccion.tipo,
                "offset": item.seccion.offset,
                "tamanoComprimido": item.seccion.tamano,
                "tamanoAlineado": item.seccion.tamano_alineado,
                "tamanoDescomprimido": len(item.datos),
                "sha256": item.sha256,
            }
            for item in secciones
        ],
    }


def desempaquetar(ruta_bzz: Path, carpeta_destino: Path) -> dict[str, object]:
    """Descomprime todas las secciones de un archivo BZZ a una carpeta.

    Contexto:
        Orden ``desempaquetar`` de la linea de comandos. Escribe una salida por seccion
        con el nombre ``<indice:02d>_tipo<tipo:02d>.bin`` y un ``manifiesto.json``.

    Args:
        ruta_bzz (Path): Archivo .BZZ de origen.
        carpeta_destino (Path): Carpeta de salida; se crea si no existe.

    Returns:
        dict[str, object]: El manifiesto escrito.

    Raises:
        ValueError: Si el archivo es demasiado grande o su contenido es invalido.
        OSError: Si no se puede leer el origen o escribir en el destino.

    Ejemplo:
        manifiesto = desempaquetar(Path("L01A.BZZ"), Path("salida/L01A"))
    """
    datos = leer_archivo_bzz(ruta_bzz)
    cabecera = leer_cabecera(datos)
    carpeta_destino.mkdir(parents=True, exist_ok=True)
    descomprimidas: list[SeccionDescomprimida] = []
    for item in descomprimir_secciones(datos, cabecera):
        nombre = nombre_archivo_seccion(item.seccion.indice, item.seccion.tipo)
        (carpeta_destino / nombre).write_bytes(item.datos)
        descomprimidas.append(item)
    manifiesto = construir_manifiesto(ruta_bzz.name, cabecera, descomprimidas)
    texto = json.dumps(manifiesto, indent=2, ensure_ascii=True)
    (carpeta_destino / NOMBRE_MANIFIESTO).write_text(texto + "\n", encoding="utf-8")
    return manifiesto


def generar_inventario(carpeta_fs: Path, salida_csv: Path) -> int:
    """Descomprime todos los archivos BZZ de una carpeta y escribe un CSV por seccion.

    Contexto:
        Orden ``inventario`` de la linea de comandos. Recorre la carpeta de forma recursiva
        y en orden alfabetico para que el CSV sea reproducible (salvo la columna de tiempos).

    Args:
        carpeta_fs (Path): Carpeta con los archivos .BZZ del sistema de archivos del disco.
        salida_csv (Path): Archivo CSV de salida; se crea la carpeta que lo contiene.

    Returns:
        int: Numero de filas (secciones) escritas.

    Raises:
        ValueError: Si algun archivo es invalido; el mensaje incluye el nombre relativo.
        OSError: Si no se puede leer la carpeta o escribir el CSV.

    Ejemplo:
        filas = generar_inventario(Path("disc/fs"), Path("inventario.csv"))
    """
    archivos = sorted(carpeta_fs.rglob("*.BZZ"), key=lambda ruta: ruta.relative_to(carpeta_fs).as_posix())
    salida_csv.parent.mkdir(parents=True, exist_ok=True)
    filas = 0
    with salida_csv.open("w", newline="", encoding="utf-8") as destino:
        escritor = csv.writer(destino, lineterminator="\n")
        escritor.writerow(COLUMNAS_INVENTARIO)
        for ruta in archivos:
            relativa = ruta.relative_to(carpeta_fs).as_posix()
            try:
                for item in descomprimir_secciones(leer_archivo_bzz(ruta)):
                    escritor.writerow(
                        (
                            relativa,
                            item.seccion.indice,
                            item.seccion.tipo,
                            item.seccion.offset,
                            item.seccion.tamano,
                            len(item.datos),
                            item.sha256,
                            f"{item.segundos:.4f}",
                        ),
                    )
                    filas += 1
            except ValueError as error:
                raise ValueError(f"{relativa}: {error}") from None
    return filas

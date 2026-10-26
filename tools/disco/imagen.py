"""
Acceso a la imagen de disco MODE2/2352 y reempaquetado por sectores.

Contexto:
    Capa de infraestructura de `tools.disco`: lee y escribe el archivo `.bin` sector por
    sector (la imagen ronda los 600 MB y nunca se carga entera en memoria) apoyandose en las
    reglas puras de `tools.disco.dominio`.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import BinaryIO, Self

from tools.disco import dominio

NOMBRE_BIN_SALIDA = "bblit_prueba.bin"
NOMBRE_CUE_SALIDA = "bblit_prueba.cue"
MAX_SECTORES_DIRECTORIO = 512
MAX_PROFUNDIDAD_RUTA = 8


@dataclass(frozen=True)
class ResultadoReempaquetado:
    """Resumen de un reempaquetado: archivos escritos y sectores realmente modificados."""

    ruta_bin: Path
    ruta_cue: Path
    sectores_totales: int
    sectores_modificados: int
    sha1: str


class ImagenCd:
    """Lector (y escritor opcional) de sectores crudos de una imagen MODE2/2352."""

    def __init__(self, ruta: Path, escritura: bool = False) -> None:
        """
        Abre la imagen y valida que su tamano sea multiplo del sector crudo.

        Contexto:
            Punto de entrada de toda lectura de la imagen original y de la copia parchada.

        Args:
            ruta (Path): Archivo `.bin` a abrir.
            escritura (bool, opcional): True para abrir en lectura y escritura.

        Raises:
            ValueError: Si el archivo esta vacio o su tamano no es multiplo de 2352.
            OSError: Si el archivo no se puede abrir.

        Ejemplo:
            with ImagenCd(Path("juego.bin")) as imagen:
                sector = imagen.leer_sector(16)
        """
        tamano = ruta.stat().st_size
        if tamano == 0 or tamano % dominio.TAMANO_SECTOR_CRUDO:
            raise ValueError(
                f"tamano de imagen={tamano}: se esperaba un multiplo de {dominio.TAMANO_SECTOR_CRUDO}"
            )
        self.total_sectores = tamano // dominio.TAMANO_SECTOR_CRUDO
        self._manejador: BinaryIO = ruta.open("r+b" if escritura else "rb")

    def __enter__(self) -> Self:
        """Devuelve la propia imagen para su uso en un bloque `with`."""
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        valor: BaseException | None,
        traza: TracebackType | None,
    ) -> None:
        """Cierra el archivo al salir del bloque `with`."""
        self.cerrar()

    def cerrar(self) -> None:
        """
        Cierra el archivo subyacente.

        Contexto:
            Lo invoca `__exit__`; es idempotente.

        Ejemplo:
            imagen.cerrar()
        """
        self._manejador.close()

    def _validar_lba(self, lba: int) -> int:
        """
        Comprueba que el sector exista dentro de la imagen y devuelve su offset.

        Contexto:
            Cota comun de `leer_sector` y `escribir_sector`.

        Args:
            lba (int): Sector logico.

        Returns:
            int: Offset en bytes del sector.

        Raises:
            ValueError: Si `lba` esta fuera de 0..total_sectores-1.

        Ejemplo:
            offset = self._validar_lba(16)
        """
        if not 0 <= lba < self.total_sectores:
            raise ValueError(f"lba={lba} fuera de rango 0..{self.total_sectores - 1}")
        return dominio.lba_a_offset(lba)

    def leer_sector(self, lba: int) -> bytes:
        """
        Lee un sector crudo de 2352 bytes.

        Contexto:
            Base de la lectura del directorio, de la sustitucion y de las verificaciones.

        Args:
            lba (int): Sector logico a leer.

        Returns:
            bytes: Sector crudo completo.

        Raises:
            ValueError: Si `lba` esta fuera de la imagen.

        Ejemplo:
            sector = imagen.leer_sector(16)
        """
        self._manejador.seek(self._validar_lba(lba))
        return self._manejador.read(dominio.TAMANO_SECTOR_CRUDO)

    def escribir_sector(self, lba: int, sector: bytes) -> None:
        """
        Escribe un sector crudo de 2352 bytes en su posicion.

        Contexto:
            Solo se usa sobre la copia de trabajo en la carpeta de salida, nunca sobre la
            imagen original.

        Args:
            lba (int): Sector logico a escribir.
            sector (bytes): Sector crudo de 2352 bytes.

        Raises:
            ValueError: Si `lba` esta fuera de la imagen o el sector no mide 2352 bytes.

        Ejemplo:
            imagen.escribir_sector(200, sector_nuevo)
        """
        if len(sector) != dominio.TAMANO_SECTOR_CRUDO:
            raise ValueError(f"sector de {len(sector)} bytes: se esperaban {dominio.TAMANO_SECTOR_CRUDO}")
        self._manejador.seek(self._validar_lba(lba))
        self._manejador.write(sector)


def _leer_directorio(imagen: ImagenCd, entrada: dominio.EntradaDirectorio) -> list[dominio.EntradaDirectorio]:
    """
    Lee todas las entradas de un directorio ISO 9660 recorriendo sus sectores.

    Contexto:
        Paso intermedio de `buscar_archivo` por cada componente de la ruta.

    Args:
        imagen (ImagenCd): Imagen abierta.
        entrada (EntradaDirectorio): Entrada que describe el directorio.

    Returns:
        list[EntradaDirectorio]: Entradas de todos los sectores del directorio.

    Raises:
        ValueError: Si el directorio excede la cota de sectores o se sale de la imagen.

    Ejemplo:
        entradas = _leer_directorio(imagen, raiz)
    """
    sectores = -(-entrada.tamano // dominio.TAMANO_DATOS)
    if not 1 <= sectores <= MAX_SECTORES_DIRECTORIO:
        raise ValueError(f"directorio de {sectores} sectores fuera de rango 1..{MAX_SECTORES_DIRECTORIO}")
    entradas: list[dominio.EntradaDirectorio] = []
    for indice in range(sectores):
        datos = dominio.extraer_datos(imagen.leer_sector(entrada.lba + indice))
        entradas.extend(dominio.parsear_directorio(datos))
    return entradas


def buscar_archivo(imagen: ImagenCd, ruta: str) -> dominio.EntradaDirectorio:
    """
    Localiza un archivo en el sistema ISO 9660 de la imagen, leyendo LBA y tamano reales.

    Contexto:
        Primer paso del reempaquetado: la posicion y el tamano del ejecutable nunca se
        suponen, siempre se leen del directorio del propio disco.

    Args:
        imagen (ImagenCd): Imagen abierta.
        ruta (str): Ruta con `/` como separador, p. ej. `SLUS_008.38` o `XA/MUSIC.XA`.

    Returns:
        EntradaDirectorio: Entrada del archivo (LBA y tamano).

    Raises:
        ValueError: Si la ruta es vacia o demasiado profunda, algun componente no existe o
            un componente intermedio no es directorio, o el archivo se sale de la imagen.

    Ejemplo:
        entrada = buscar_archivo(imagen, "SLUS_008.38")
    """
    partes = [p for p in ruta.split("/") if p]
    if not 1 <= len(partes) <= MAX_PROFUNDIDAD_RUTA:
        raise ValueError(f"ruta con {len(partes)} componentes: se esperaban 1..{MAX_PROFUNDIDAD_RUTA}")
    actual = dominio.parsear_raiz(dominio.extraer_datos(imagen.leer_sector(dominio.LBA_DESCRIPTOR_VOLUMEN)))
    for posicion, parte in enumerate(partes):
        objetivo = dominio.normalizar_nombre(parte)
        coincidencias = [
            e for e in _leer_directorio(imagen, actual) if dominio.normalizar_nombre(e.nombre) == objetivo
        ]
        if not coincidencias:
            raise ValueError(f"componente '{parte}' no encontrado en el directorio de la imagen")
        actual = coincidencias[0]
        es_ultimo = posicion == len(partes) - 1
        if not es_ultimo and not actual.es_directorio:
            raise ValueError(f"componente '{parte}' no es un directorio")
    if actual.es_directorio:
        raise ValueError(f"'{ruta}' es un directorio, se esperaba un archivo")
    sectores = -(-actual.tamano // dominio.TAMANO_DATOS)
    if actual.lba + sectores > imagen.total_sectores:
        raise ValueError(f"archivo '{ruta}' fuera de la imagen: lba={actual.lba}, sectores={sectores}")
    return actual


def _calcular_sha1(ruta: Path) -> str:
    """
    Calcula el SHA-1 de un archivo leyendolo por bloques.

    Contexto:
        Permite comparar la imagen reempaquetada con el volcado de referencia sin cargarla
        en memoria.

    Args:
        ruta (Path): Archivo a resumir.

    Returns:
        str: Resumen SHA-1 en hexadecimal minusculas.

    Ejemplo:
        _calcular_sha1(Path("build/bblit_prueba.bin"))
    """
    with ruta.open("rb") as manejador:
        return hashlib.file_digest(manejador, "sha1").hexdigest()


def _parchar_ejecutable(ruta_trabajo: Path, entrada: dominio.EntradaDirectorio, contenido: bytes) -> int:
    """
    Sustituye los sectores del ejecutable en la copia de trabajo recalculando EDC/ECC.

    Contexto:
        Antes de escribir un sector se comprueba que el algoritmo reproduce exactamente el
        EDC/ECC del sector original; si no, la imagen resultante fallaria en emuladores
        estrictos y se aborta.

    Args:
        ruta_trabajo (Path): Copia de la imagen sobre la que se escribe.
        entrada (EntradaDirectorio): Posicion y tamano del archivo en la imagen.
        contenido (bytes): Nuevo contenido, del mismo tamano que el registrado.

    Returns:
        int: Numero de sectores cuyo contenido cambio y se reescribio.

    Raises:
        ValueError: Si un sector es Form 2, o si EDC/ECC recalculados no coinciden con los
            del sector original.

    Ejemplo:
        modificados = _parchar_ejecutable(copia, entrada, exe)
    """
    modificados = 0
    sectores = -(-entrada.tamano // dominio.TAMANO_DATOS)
    with ImagenCd(ruta_trabajo, escritura=True) as imagen:
        for indice in range(sectores):
            lba = entrada.lba + indice
            original = imagen.leer_sector(lba)
            datos_originales = dominio.extraer_datos(original)
            if dominio.construir_sector_form1(original, datos_originales) != original:
                raise ValueError(f"EDC/ECC recalculados no coinciden con los del sector lba={lba}")
            trozo = contenido[indice * dominio.TAMANO_DATOS : (indice + 1) * dominio.TAMANO_DATOS]
            nuevos = trozo.ljust(dominio.TAMANO_DATOS, b"\x00")
            if nuevos != datos_originales:
                imagen.escribir_sector(lba, dominio.construir_sector_form1(original, nuevos))
                modificados += 1
    return modificados


def reempaquetar(
    ruta_imagen: Path, ruta_exe: Path, carpeta_salida: Path, archivo: str = "SLUS_008.38"
) -> ResultadoReempaquetado:
    """
    Genera una imagen de prueba con el ejecutable del disco sustituido in-place.

    Contexto:
        Es la operacion de `python -m tools.disco reempaquetar`. Copia la imagen original a
        la carpeta de salida, parcha solo los sectores del ejecutable y escribe el `.cue`.
        La imagen de entrada no se modifica nunca.

    Args:
        ruta_imagen (Path): `.bin` original (solo lectura).
        ruta_exe (Path): Ejecutable de reemplazo; debe medir lo mismo que el registrado.
        carpeta_salida (Path): Carpeta donde se escriben `bblit_prueba.bin` y `.cue`.
        archivo (str, opcional): Ruta del archivo a sustituir dentro del disco.

    Returns:
        ResultadoReempaquetado: Rutas escritas, sectores modificados y SHA-1 de la imagen.

    Raises:
        ValueError: Si el ejecutable mide distinto del registrado, si la salida coincide con
            la imagen de entrada o si alguna validacion de la imagen falla.
        OSError: Si no se puede leer o escribir algun archivo.

    Ejemplo:
        resultado = reempaquetar(Path("juego.bin"), Path("build/SLUS_008.38"), Path("build"))
    """
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    ruta_bin = carpeta_salida / NOMBRE_BIN_SALIDA
    if ruta_bin.exists() and ruta_bin.samefile(ruta_imagen):
        raise ValueError("la imagen de salida coincide con la de entrada: elija otra carpeta")
    with ImagenCd(ruta_imagen) as imagen:
        entrada = buscar_archivo(imagen, archivo)
        total = imagen.total_sectores
    dominio.validar_tamano_ejecutable(ruta_exe.stat().st_size, entrada.tamano)
    contenido = ruta_exe.read_bytes()
    ruta_parcial = ruta_bin.with_suffix(".bin.parcial")
    try:
        shutil.copyfile(ruta_imagen, ruta_parcial)
        modificados = _parchar_ejecutable(ruta_parcial, entrada, contenido)
        os.replace(ruta_parcial, ruta_bin)
    finally:
        ruta_parcial.unlink(missing_ok=True)
    ruta_cue = carpeta_salida / NOMBRE_CUE_SALIDA
    ruta_cue.write_bytes(dominio.generar_cue(ruta_bin.name).encode("ascii"))
    return ResultadoReempaquetado(ruta_bin, ruta_cue, total, modificados, _calcular_sha1(ruta_bin))

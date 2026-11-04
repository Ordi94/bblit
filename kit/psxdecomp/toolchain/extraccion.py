"""Extraccion de los archivos descargados a la carpeta de cada componente.

Capa de infraestructura. Soporta zip (biblioteca estandar), 7z y rar mediante el ejecutable
de 7-Zip, e imagenes de CD ISO 9660 contenidas en un rar. Toda ruta de miembro se valida
contra escapes del destino y se aplican cotas de cantidad y tamano.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import zipfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from tools.toolchain import iso9660
from tools.toolchain.dominio import Componente, coincide_patron, ruta_miembro_segura

MAX_MIEMBROS = 100000
MAX_BYTES_EXTRAIDOS = 2 * 1024 * 1024 * 1024
TIMEOUT_7ZIP_S = 900


def localizar_7zip(configurado: Path | None, entorno: Mapping[str, str]) -> Path:
    """
    Encuentra el ejecutable de 7-Zip.

    Contexto:
        Necesario para los formatos 7z y rar. El orden es: ruta configurada, ``7z`` en el
        PATH, y la carpeta ``7-Zip`` bajo la variable de entorno ``ProgramFiles``.

    Args:
        configurado (Path, opcional): Ruta fijada por variable o ``config/local.toml``.
        entorno (Mapping[str, str]): Variables de entorno.

    Returns:
        Path: Ruta del ejecutable.

    Raises:
        FileNotFoundError: Si no se encuentra en ninguna ubicacion.

    Ejemplo:
        ejecutable = localizar_7zip(None, os.environ)
    """
    candidatos: list[Path] = []
    if configurado is not None:
        candidatos.append(configurado)
    for nombre in ("7z", "7zz"):
        encontrado = shutil.which(nombre)
        if encontrado:
            candidatos.append(Path(encontrado))
    programas = entorno.get("ProgramFiles")
    if programas:
        candidatos.append(Path(programas) / "7-Zip" / "7z.exe")
    for candidato in candidatos:
        if candidato.is_file():
            return candidato
    raise FileNotFoundError(
        "no se encontro 7-Zip: instalelo o defina BBLIT_7ZIP / siete_zip en config/local.toml"
    )


def _destino_seguro(destino: Path, ruta: PurePosixPath) -> Path:
    """Resuelve la ruta final de un miembro y comprueba que quede dentro de ``destino``."""
    final = (destino / Path(*ruta.parts)).resolve()
    if not final.is_relative_to(destino.resolve()):
        raise ValueError("un miembro del archivo intenta escribir fuera de la carpeta del componente")
    return final


def _quitar_raiz(ruta: PurePosixPath) -> PurePosixPath | None:
    """Descarta el primer segmento; devuelve ``None`` si no queda nada (era la carpeta raiz)."""
    return PurePosixPath(*ruta.parts[1:]) if len(ruta.parts) > 1 else None


def extraer_zip(componente: Componente, archivo: Path, destino: Path) -> int:
    """
    Extrae de un zip los miembros que coinciden con los patrones del componente.

    Contexto:
        Usado por el SDK 4.6/4.7, PSn00bSDK (binutils) y los zip de GitHub (maspsx, m2c,
        asm-differ).

    Args:
        componente (Componente): Define patrones de extraccion y si se quita la raiz.
        archivo (Path): Zip descargado y ya verificado.
        destino (Path): Carpeta del componente.

    Returns:
        int: Cantidad de archivos escritos.

    Raises:
        ValueError: Si hay demasiados miembros, el total supera la cota o una ruta escapa.

    Ejemplo:
        escritos = extraer_zip(componente, Path("a.zip"), Path("toolchain/a"))
    """
    escritos = 0
    total = 0
    with zipfile.ZipFile(archivo) as zf:
        miembros = zf.infolist()
        if len(miembros) > MAX_MIEMBROS:
            raise ValueError(f"componente '{componente.nombre}': el archivo tiene demasiados miembros")
        for info in miembros:
            if info.is_dir():
                continue
            ruta = ruta_miembro_segura(info.filename)
            if componente.quitar_raiz:
                recortada = _quitar_raiz(ruta)
                if recortada is None:
                    continue
                ruta = recortada
            if not coincide_patron(ruta, componente.extraer):
                continue
            total += info.file_size
            if total > MAX_BYTES_EXTRAIDOS:
                raise ValueError(
                    f"componente '{componente.nombre}': el contenido excede la cota de extraccion"
                )
            final = _destino_seguro(destino, ruta)
            final.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as origen, final.open("wb") as salida:
                shutil.copyfileobj(origen, salida)
            escritos += 1
    return escritos


def _ejecutar_7zip(siete_zip: Path, argumentos: list[str], nombre: str) -> None:
    """Invoca 7-Zip con lista de argumentos, tiempo limite y sin shell."""
    try:
        resultado = subprocess.run(
            [str(siete_zip), *argumentos],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_7ZIP_S,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"componente '{nombre}': 7-Zip excedio {TIMEOUT_7ZIP_S} s") from None
    if resultado.returncode != 0:
        raise RuntimeError(f"componente '{nombre}': 7-Zip termino con codigo {resultado.returncode}")


def _verificar_arbol(destino: Path, nombre: str) -> int:
    """Comprueba que nada extraido haya salido de ``destino`` y cuenta los archivos."""
    base = destino.resolve()
    cuenta = 0
    for raiz, _carpetas, archivos in os.walk(base):
        for archivo in archivos:
            if not (Path(raiz) / archivo).resolve().is_relative_to(base):
                raise ValueError(f"componente '{nombre}': el archivo extraido salio del destino")
            cuenta += 1
    return cuenta


def extraer_7z(componente: Componente, archivo: Path, destino: Path, siete_zip: Path) -> int:
    """
    Extrae un 7z delegando en 7-Zip, restringido a los patrones del componente.

    Contexto:
        Usado por el Runtime Library 4.4 (formato 7z de ~80 MB).

    Args:
        componente (Componente): Define los patrones de extraccion.
        archivo (Path): Archivo descargado y verificado.
        destino (Path): Carpeta del componente.
        siete_zip (Path): Ejecutable de 7-Zip.

    Returns:
        int: Cantidad de archivos presentes en el destino tras extraer.

    Raises:
        RuntimeError: Si 7-Zip falla.
        TimeoutError: Si 7-Zip excede el tiempo limite.
        ValueError: Si algun archivo extraido queda fuera del destino.

    Ejemplo:
        cuenta = extraer_7z(componente, Path("a.7z"), Path("toolchain/a"), Path("7z.exe"))
    """
    patrones = [patron.replace("/", "\\") for patron in componente.extraer]
    _ejecutar_7zip(siete_zip, ["x", "-y", "-bd", f"-o{destino}", str(archivo), *patrones], componente.nombre)
    return _verificar_arbol(destino, componente.nombre)


def extraer_rar_iso(componente: Componente, archivo: Path, destino: Path, siete_zip: Path) -> int:
    """
    Extrae de un rar que contiene una imagen de CD los archivos que coinciden con los patrones.

    Contexto:
        Usado por el Runtime Library 4.1, cuyo compilador GCC 2.7.2 solo se distribuye
        dentro de una imagen de CD. Se descomprime la imagen a una carpeta temporal dentro
        del destino, se leen los archivos pedidos y se borra la imagen.

    Args:
        componente (Componente): Define los patrones de extraccion.
        archivo (Path): Rar descargado y verificado.
        destino (Path): Carpeta del componente.
        siete_zip (Path): Ejecutable de 7-Zip.

    Returns:
        int: Cantidad de archivos escritos.

    Raises:
        RuntimeError: Si 7-Zip falla.
        ValueError: Si no hay una unica imagen ``.bin`` o la imagen es invalida.

    Ejemplo:
        escritos = extraer_rar_iso(componente, Path("a.rar"), Path("toolchain/a"), Path("7z.exe"))
    """
    temporal = destino / "_imagen_temporal"
    try:
        _ejecutar_7zip(
            siete_zip, ["x", "-y", "-bd", f"-o{temporal}", str(archivo), "*.bin"], componente.nombre
        )
        imagenes = sorted(temporal.glob("*.bin"))
        if len(imagenes) != 1:
            raise ValueError(f"componente '{componente.nombre}': se esperaba una unica imagen .bin")
        return _extraer_imagen(componente, imagenes[0], destino)
    finally:
        shutil.rmtree(temporal, ignore_errors=True)


def _extraer_imagen(componente: Componente, imagen: Path, destino: Path) -> int:
    """Lee la imagen ISO por demanda y escribe los archivos que cumplen los patrones."""
    escritos = 0
    total = 0
    with imagen.open("rb") as fuente:

        def leer_rango(desde: int, largo: int) -> bytes:
            fuente.seek(desde)
            return fuente.read(largo)

        lector = iso9660.crear_lector(imagen.stat().st_size, leer_rango)
        for entrada in iso9660.listar_archivos(lector):
            if not coincide_patron(entrada.ruta, componente.extraer):
                continue
            total += entrada.tamano
            if total > MAX_BYTES_EXTRAIDOS:
                raise ValueError(
                    f"componente '{componente.nombre}': el contenido excede la cota de extraccion"
                )
            final = _destino_seguro(destino, entrada.ruta)
            final.parent.mkdir(parents=True, exist_ok=True)
            final.write_bytes(iso9660.leer_archivo(lector, entrada))
            escritos += 1
    return escritos


def extraer_archivo_simple(archivo: Path, destino: Path) -> int:
    """
    Copia un archivo descargado que no necesita extraccion al destino.

    Contexto:
        Para componentes que son un unico ejecutable o script.

    Args:
        archivo (Path): Archivo descargado y verificado.
        destino (Path): Carpeta del componente.

    Returns:
        int: Siempre 1.

    Ejemplo:
        extraer_archivo_simple(Path("tool.exe"), Path("toolchain/tool"))
    """
    destino.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archivo, destino / archivo.name)
    return 1


def extraer(
    componente: Componente,
    archivo: Path,
    destino: Path,
    siete_zip: Path | None,
) -> int:
    """
    Despacha la extraccion segun el formato declarado del componente.

    Contexto:
        Lo invoca la instalacion tras verificar la huella de la descarga.

    Args:
        componente (Componente): Componente con su formato.
        archivo (Path): Archivo descargado y verificado.
        destino (Path): Carpeta del componente (se crea si no existe).
        siete_zip (Path, opcional): Ejecutable de 7-Zip, obligatorio para 7z y rar_iso.

    Returns:
        int: Cantidad de archivos instalados.

    Raises:
        ValueError: Si el formato lo requiere y falta 7-Zip, o el formato no esta soportado.

    Ejemplo:
        instalados = extraer(componente, archivo, destino, None)
    """
    destino.mkdir(parents=True, exist_ok=True)
    if componente.formato == "zip":
        return extraer_zip(componente, archivo, destino)
    if componente.formato == "archivo":
        return extraer_archivo_simple(archivo, destino)
    if siete_zip is None:
        raise ValueError(
            f"componente '{componente.nombre}': el formato '{componente.formato}' requiere 7-Zip"
        )
    if componente.formato == "7z":
        return extraer_7z(componente, archivo, destino, siete_zip)
    return extraer_rar_iso(componente, archivo, destino, siete_zip)

"""Extraccion del overlay desde el disco: lectura de contenedores, seccion de codigo y salida.

Capa de entrada/salida del paquete. Las reglas (variantes, validaciones, formato de la
configuracion) viven en ``dominio``; aqui solo se abren archivos, se descomprime la seccion de
tipo 2 de cada contenedor BZZ y se escribe el resultado.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from pathlib import Path

from tools.bzz.descompresion import descomprimir_detallado
from tools.bzz.dominio import leer_cabecera, validar_consumo
from tools.bzz.lectura import TAMANO_MAXIMO_ARCHIVO, leer_archivo_bzz
from tools.overlay import dominio
from tools.overlay.dominio import VARIANTES_CONOCIDAS, VarianteConocida, VarianteExtraida
from tools.reconstruccion.infraestructura import localizar_imagen
from tools.toolchain import iso9660

RUTA_CONFIG = Path("config") / "overlay.json"
CARPETA_EXTRAIDOS = Path("expected") / "overlay"


def extraer_codigo(datos_bzz: bytes) -> bytes | None:
    """
    Descomprime la seccion de codigo (tipo 2) de un contenedor BZZ.

    Contexto:
        Solo se descomprime esa seccion: las otras nueve pesan decenas de megabytes por
        contenedor y no interesan aqui.

    Args:
        datos_bzz (bytes): Contenido completo del archivo ``.BZZ``.

    Returns:
        bytes | None: Seccion descomprimida, o ``None`` si el contenedor no trae tipo 2.

    Raises:
        ValueError: Si la cabecera o el flujo son invalidos, o si hay mas de una seccion de
            tipo 2.

    Ejemplo:
        codigo = extraer_codigo(Path("L01A.BZZ").read_bytes())
    """
    cabecera = leer_cabecera(datos_bzz)
    candidatas = [seccion for seccion in cabecera.secciones if seccion.tipo == dominio.TIPO_SECCION_CODIGO]
    if len(candidatas) > 1:
        raise ValueError(
            f"hay {len(candidatas)} secciones de tipo {dominio.TIPO_SECCION_CODIGO}, se esperaba 1"
        )
    if not candidatas:
        return None
    seccion = candidatas[0]
    fin = seccion.offset + seccion.tamano_alineado
    try:
        resultado = descomprimir_detallado(datos_bzz[seccion.offset : fin])
    except ValueError as error:
        raise ValueError(f"seccion {seccion.indice}: {error}") from None
    validar_consumo(seccion.indice, resultado.bytes_consumidos, seccion.tamano)
    return resultado.datos


def _bzz_de_sistema_de_archivos(fs: Path) -> Iterator[tuple[str, bytes]]:
    """Recorre los ``.BZZ`` de un sistema de archivos extraido, ordenados por ruta relativa."""
    rutas = sorted(
        (ruta for ruta in fs.rglob("*") if ruta.is_file() and ruta.suffix.upper() == ".BZZ"),
        key=lambda ruta: ruta.relative_to(fs).as_posix(),
    )
    if len(rutas) > dominio.MAX_ARCHIVOS_BZZ:
        raise ValueError(
            f"hay {len(rutas)} contenedores BZZ, el maximo admitido es {dominio.MAX_ARCHIVOS_BZZ}"
        )
    for ruta in rutas:
        yield ruta.relative_to(fs).as_posix(), leer_archivo_bzz(ruta)


def _bzz_de_imagen(imagen: Path) -> Iterator[tuple[str, bytes]]:
    """Recorre los ``.BZZ`` del sistema de archivos ISO 9660 de una imagen de CD."""
    with imagen.open("rb") as fuente:

        def leer_rango(desde: int, largo: int) -> bytes:
            fuente.seek(desde)
            return fuente.read(largo)

        lector = iso9660.crear_lector(imagen.stat().st_size, leer_rango)
        entradas = sorted(
            (e for e in iso9660.listar_archivos(lector) if e.ruta.suffix.upper() == ".BZZ"),
            key=lambda e: str(e.ruta),
        )
        if len(entradas) > dominio.MAX_ARCHIVOS_BZZ:
            raise ValueError(
                f"hay {len(entradas)} contenedores BZZ, el maximo admitido es {dominio.MAX_ARCHIVOS_BZZ}"
            )
        for entrada in entradas:
            if entrada.tamano > TAMANO_MAXIMO_ARCHIVO:
                raise ValueError(f"{entrada.ruta}: tamano={entrada.tamano} supera el maximo admitido")
            yield str(entrada.ruta), iso9660.leer_archivo(lector, entrada)


def contenedores_del_disco(disc: Path | None) -> Iterator[tuple[str, bytes]]:
    """
    Itera los contenedores BZZ del disco en orden alfabetico de ruta relativa.

    Contexto:
        Acepta las mismas formas de ``BBLIT_DISC`` que el resto de herramientas: carpeta con
        el sistema de archivos extraido (``fs/``), imagen ``.bin``, su ``.cue``, o carpeta que
        guarda la imagen. Si hay ``fs/`` se usa; si no, se lee la imagen ISO 9660.

    Args:
        disc (Path | None): Valor de ``BBLIT_DISC``, ``--disc`` o ``config/local.toml``.

    Yields:
        tuple[str, bytes]: Ruta relativa con ``/`` y contenido de cada ``.BZZ``.

    Raises:
        ValueError: Si no se configuro el disco, la imagen es ambigua o invalida, o hay mas
            contenedores que el maximo admitido.
        FileNotFoundError: Si la ubicacion no existe o no contiene ni ``fs/`` ni imagen.

    Ejemplo:
        for nombre, datos in contenedores_del_disco(Path("disc")):
            print(nombre, len(datos))
    """
    if disc is None:
        raise ValueError(
            "falta la ubicacion del disco: defina BBLIT_DISC, --disc o 'disc' en config/local.toml"
        )
    if not disc.exists():
        raise FileNotFoundError("la ubicacion del disco no existe")
    if disc.is_dir() and (disc / "fs").is_dir():
        yield from _bzz_de_sistema_de_archivos(disc / "fs")
        return
    imagen = localizar_imagen(disc)
    if imagen is None:
        raise FileNotFoundError("no se encontro fs/ ni una imagen .bin en la ubicacion del disco")
    yield from _bzz_de_imagen(imagen)


def extraer_variantes(
    disc: Path | None, conocidas: Sequence[VarianteConocida] = VARIANTES_CONOCIDAS
) -> tuple[list[VarianteExtraida], dict[str, bytes]]:
    """
    Extrae y clasifica el codigo de todos los contenedores del disco.

    Contexto:
        Nucleo de la orden ``extraer``: lee cada contenedor, descomprime su seccion tipo 2,
        agrupa por huella y contrasta el resultado con las variantes conocidas.

    Args:
        disc (Path | None): Ubicacion del disco.
        conocidas (Sequence[VarianteConocida], opcional): Variantes esperadas; por omision las
            de la edicion soportada.

    Returns:
        tuple[list[VarianteExtraida], dict[str, bytes]]: Variantes y bytes de cada una.

    Raises:
        ValueError: Si algun contenedor es invalido (el mensaje incluye su ruta) o el resultado
            no coincide con las variantes conocidas.
        FileNotFoundError: Si no se encuentra el disco.

    Ejemplo:
        variantes, binarios = extraer_variantes(Path("disc"))
    """
    secciones: list[tuple[str, bytes]] = []
    for nombre, datos in contenedores_del_disco(disc):
        try:
            codigo = extraer_codigo(datos)
            if codigo is not None:
                dominio.validar_tamano_codigo(len(codigo))
        except ValueError as error:
            raise ValueError(f"{nombre}: {error}") from None
        if codigo is not None:
            secciones.append((nombre, codigo))
    return dominio.identificar_variantes(dominio.agrupar_por_huella(secciones), conocidas)


def escribir_extraccion(
    raiz: Path, variantes: Sequence[VarianteExtraida], binarios: dict[str, bytes]
) -> None:
    """
    Escribe los binarios extraidos y la configuracion.

    Contexto:
        Ultimo paso de ``extraer``. ``expected/overlay/`` esta ignorado por git porque contiene
        material del disco; ``config/overlay.json`` solo guarda huellas, tamanos y nombres.

    Args:
        raiz (Path): Raiz del repositorio.
        variantes (Sequence[VarianteExtraida]): Variantes a registrar.
        binarios (dict[str, bytes]): Bytes de cada variante por identificador.

    Raises:
        OSError: Si no se puede escribir.

    Ejemplo:
        escribir_extraccion(Path("."), variantes, binarios)
    """
    destino = raiz / CARPETA_EXTRAIDOS
    destino.mkdir(parents=True, exist_ok=True)
    for variante in variantes:
        (destino / f"{variante.identificador}.bin").write_bytes(binarios[variante.identificador])
    (raiz / RUTA_CONFIG).parent.mkdir(parents=True, exist_ok=True)
    (raiz / RUTA_CONFIG).write_text(dominio.serializar_config(variantes), encoding="utf-8", newline="\n")


def leer_variantes(
    raiz: Path, conocidas: Sequence[VarianteConocida] = VARIANTES_CONOCIDAS
) -> list[VarianteExtraida]:
    """
    Lee y valida ``config/overlay.json``.

    Contexto:
        Primer paso de ``split``, ``build``, ``verify`` y ``ram``.

    Args:
        raiz (Path): Raiz del repositorio.
        conocidas (Sequence[VarianteConocida], opcional): Variantes esperadas.

    Returns:
        list[VarianteExtraida]: Variantes registradas.

    Raises:
        FileNotFoundError: Si el archivo no existe (hay que ejecutar ``extraer``).
        ValueError: Si es demasiado grande, no es JSON o no cumple el esquema.

    Ejemplo:
        variantes = leer_variantes(Path("."))
    """
    ruta = raiz / RUTA_CONFIG
    if not ruta.is_file():
        raise FileNotFoundError("falta config/overlay.json: ejecute primero 'extraer'")
    if ruta.stat().st_size > dominio.MAX_BYTES_CONFIG:
        raise ValueError("config/overlay.json excede el tamano permitido")
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except ValueError:
        raise ValueError("config/overlay.json no es JSON valido") from None
    return dominio.variantes_desde_config(datos, conocidas)


def leer_binario(raiz: Path, variante: VarianteExtraida) -> bytes:
    """
    Lee el binario extraido de una variante y comprueba su huella.

    Contexto:
        Evita particionar o comparar contra un archivo alterado o de otra extraccion.

    Args:
        raiz (Path): Raiz del repositorio.
        variante (VarianteExtraida): Variante a leer.

    Returns:
        bytes: Contenido de ``expected/overlay/<id>.bin``.

    Raises:
        FileNotFoundError: Si no existe (hay que ejecutar ``extraer``).
        ValueError: Si su huella no es la registrada.

    Ejemplo:
        datos = leer_binario(Path("."), variante)
    """
    ruta = raiz / CARPETA_EXTRAIDOS / f"{variante.identificador}.bin"
    if not ruta.is_file():
        raise FileNotFoundError(
            f"falta expected/overlay/{variante.identificador}.bin: ejecute primero 'extraer'"
        )
    if ruta.stat().st_size > dominio.TAMANO_HUECO:
        raise ValueError(f"expected/overlay/{variante.identificador}.bin excede el hueco del overlay")
    datos = ruta.read_bytes()
    if dominio.huella_sha256(datos) != variante.sha256:
        raise ValueError(f"expected/overlay/{variante.identificador}.bin no coincide con config/overlay.json")
    return datos

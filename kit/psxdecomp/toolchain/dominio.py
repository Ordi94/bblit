"""Modelo de dominio del toolchain: componentes, archivo de bloqueo y reglas de validacion.

Este modulo no toca disco, red ni procesos: solo recibe estructuras ya leidas (diccionarios,
cadenas) y devuelve objetos validados o lanza ``ValueError`` con el nombre del componente y el
campo ofensivo. Las capas de infraestructura (descarga, extraccion) confian en que lo que
sale de aqui ya paso las cotas.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

VERSION_LOCK = 1
"""Version del esquema del archivo de bloqueo que este codigo sabe interpretar."""

FORMATOS_ADMITIDOS = ("zip", "7z", "rar_iso", "archivo")
"""Formas de empaquetado soportadas; cualquier otra se rechaza (lista de admitidos)."""

HOSTS_ADMITIDOS = ("archive.org", "arthus.net", "github.com", "githubusercontent.com")
"""Dominios desde los que se admite descargar. El hash sigue siendo la garantia real."""

MAX_COMPONENTES = 64
MAX_ARCHIVOS_CLAVE = 64
MAX_PATRONES = 64
MAX_NOTAS = 2000
MAX_RUTA = 260

_PATRON_NOMBRE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")
_PATRON_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PATRON_ALIAS = re.compile(r"^[a-z0-9][a-z0-9._-]{0,47}$")
_PATRON_ARCHIVO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,120}$")


@dataclass(frozen=True)
class Componente:
    """Una pieza del toolchain descargable y verificable por hash.

    Attributes:
        nombre: Identificador unico, tambien nombre de la carpeta bajo ``toolchain/``.
        url: Direccion HTTPS del archivo a descargar.
        sha256: Huella SHA-256 esperada del archivo descargado, en hexadecimal minusculas.
        fecha_registro: Fecha (ISO 8601) en la que se calculo y registro la huella.
        notas: Procedencia, version y observaciones del componente.
        formato: Empaquetado del archivo descargado (ver ``FORMATOS_ADMITIDOS``).
        extraer: Patrones (estilo shell, con ``/``) de los miembros a instalar; vacio instala todo.
        archivos_clave: Alias de herramienta mapeado a su ruta relativa dentro del componente.
        quitar_raiz: Si es verdadero, descarta la carpeta unica de primer nivel de un zip
            (las descargas de GitHub traen ``proyecto-<commit>/``).
    """

    nombre: str
    url: str
    sha256: str
    fecha_registro: str
    notas: str
    formato: str
    extraer: tuple[str, ...]
    archivos_clave: tuple[tuple[str, str], ...]
    quitar_raiz: bool = False

    def ruta_clave(self, alias: str) -> str:
        """
        Devuelve la ruta relativa de un archivo clave del componente.

        Contexto:
            La usan la instalacion (para comprobar que el componente quedo completo) y la
            construccion (para localizar ``as``, ``ld``, ``CC1PSX.EXE``, etc.).

        Args:
            alias (str): Nombre corto de la herramienta, p. ej. ``"as"``.

        Returns:
            str: Ruta relativa con ``/`` dentro de la carpeta del componente.

        Raises:
            ValueError: Si el componente no declara ese alias.

        Ejemplo:
            ruta = componente.ruta_clave("as")
        """
        for clave, ruta in self.archivos_clave:
            if clave == alias:
                return ruta
        raise ValueError(f"el componente '{self.nombre}' no declara el archivo clave '{alias}'")


def _exigir_texto(valor: object, campo: str, nombre: str, maximo: int) -> str:
    """Valida que un campo sea una cadena no vacia dentro de la cota indicada."""
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"componente '{nombre}': el campo '{campo}' debe ser texto no vacio")
    if len(valor) > maximo:
        raise ValueError(f"componente '{nombre}': el campo '{campo}' excede {maximo} caracteres")
    return valor


def host_admitido(host: str) -> bool:
    """
    Indica si un nombre de host pertenece a algun dominio de la lista de admitidos.

    Contexto:
        Se aplica a la URL del lock y a la URL final tras las redirecciones de la descarga.

    Args:
        host (str): Nombre de host en minusculas, sin puerto.

    Returns:
        bool: ``True`` si es el dominio admitido o un subdominio suyo.

    Ejemplo:
        host_admitido("codeload.github.com")  # True
    """
    return any(host == base or host.endswith("." + base) for base in HOSTS_ADMITIDOS)


def validar_url(url: str, nombre: str) -> str:
    """
    Comprueba que una URL sea HTTPS, sin credenciales y de un host admitido.

    Contexto:
        Primera defensa antes de abrir una conexion; protege contra un lock manipulado que
        apunte a un servidor arbitrario.

    Args:
        url (str): URL leida del archivo de bloqueo.
        nombre (str): Nombre del componente, solo para el mensaje de error.

    Returns:
        str: La misma URL si es valida.

    Raises:
        ValueError: Si el esquema no es HTTPS, trae usuario/clave o el host no esta admitido.

    Ejemplo:
        validar_url("https://github.com/mkst/maspsx/archive/abc.zip", "maspsx")
    """
    partes = urlsplit(url)
    host = (partes.hostname or "").lower()
    if partes.scheme != "https" or partes.username or partes.password:
        raise ValueError(f"componente '{nombre}': la URL debe ser HTTPS y sin credenciales")
    if not host_admitido(host):
        raise ValueError(f"componente '{nombre}': el host de la URL no esta en la lista de admitidos")
    return url


def nombre_archivo_desde_url(url: str, nombre: str) -> str:
    """
    Deriva el nombre de archivo local a partir del ultimo segmento de la URL.

    Contexto:
        La descarga guarda el archivo con su nombre original dentro de la carpeta del
        componente; el nombre sale de una URL externa, asi que se valida antes de usarlo
        como parte de una ruta.

    Args:
        url (str): URL ya validada del componente.
        nombre (str): Nombre del componente, solo para el mensaje de error.

    Returns:
        str: Nombre de archivo sin separadores de ruta.

    Raises:
        ValueError: Si el ultimo segmento esta vacio o trae caracteres no admitidos.

    Ejemplo:
        nombre_archivo_desde_url("https://archive.org/download/x/Runtime%20Library%204.4.7z", "psyq")
    """
    candidato = unquote(PurePosixPath(urlsplit(url).path).name)
    if not _PATRON_ARCHIVO.match(candidato) or ".." in candidato:
        raise ValueError(f"componente '{nombre}': la URL no termina en un nombre de archivo valido")
    return candidato


def ruta_miembro_segura(miembro: str) -> PurePosixPath:
    r"""
    Normaliza la ruta de un miembro de archivo comprimido y rechaza escapes del destino.

    Contexto:
        Se aplica a cada entrada de un zip o de una imagen ISO antes de escribirla, para
        impedir que un archivo hostil escriba fuera de la carpeta del componente (zip-slip).

    Args:
        miembro (str): Ruta tal como figura en el archivo comprimido (``/`` o ``\\``).

    Returns:
        PurePosixPath: Ruta relativa normalizada con ``/``.

    Raises:
        ValueError: Si es absoluta, tiene unidad, contiene ``..``, esta vacia o es demasiado larga.

    Ejemplo:
        ruta_miembro_segura("bin\\\\mipsel-none-elf-as.exe")
    """
    texto = miembro.replace("\\", "/")
    if not texto or len(texto) > MAX_RUTA or "\x00" in texto:
        raise ValueError("ruta de miembro vacia, demasiado larga o con caracteres no validos")
    if texto.startswith("/") or re.match(r"^[A-Za-z]:", texto):
        raise ValueError("ruta de miembro absoluta no permitida")
    partes = [p for p in texto.split("/") if p not in ("", ".")]
    if not partes or any(p == ".." for p in partes):
        raise ValueError("ruta de miembro con '..' o vacia no permitida")
    return PurePosixPath(*partes)


def coincide_patron(miembro: PurePosixPath, patrones: tuple[str, ...]) -> bool:
    """
    Decide si un miembro debe instalarse segun los patrones del componente.

    Contexto:
        Permite instalar solo el subconjunto necesario de archivos grandes (p. ej. el SDK).
        La comparacion ignora mayusculas porque los archivos de los 90 vienen en MAYUSCULAS.

    Args:
        miembro (PurePosixPath): Ruta normalizada del miembro.
        patrones (tuple[str, ...]): Patrones estilo shell; tupla vacia significa "todo".

    Returns:
        bool: ``True`` si el miembro debe extraerse.

    Ejemplo:
        coincide_patron(PurePosixPath("PSX/LIB/LIBAPI.LIB"), ("psx/lib/*",))  # True
    """
    if not patrones:
        return True
    texto = str(miembro).lower()
    return any(fnmatch.fnmatchcase(texto, patron.lower()) for patron in patrones)


def _validar_patrones(valor: object, nombre: str) -> tuple[str, ...]:
    """Valida la lista de patrones de extraccion."""
    if valor is None:
        return ()
    if not isinstance(valor, list) or len(valor) > MAX_PATRONES:
        raise ValueError(f"componente '{nombre}': 'extraer' debe ser una lista de hasta {MAX_PATRONES}")
    resultado = []
    for patron in valor:
        texto = _exigir_texto(patron, "extraer", nombre, MAX_RUTA).replace("\\", "/")
        if texto.startswith("/") or ".." in texto.split("/"):
            raise ValueError(f"componente '{nombre}': patron de extraccion no permitido")
        resultado.append(texto)
    return tuple(resultado)


def _validar_archivos_clave(valor: object, nombre: str) -> tuple[tuple[str, str], ...]:
    """Valida el mapa alias -> ruta relativa de los archivos clave."""
    if valor is None:
        return ()
    if not isinstance(valor, dict) or len(valor) > MAX_ARCHIVOS_CLAVE:
        raise ValueError(
            f"componente '{nombre}': 'archivos_clave' debe ser un objeto de hasta {MAX_ARCHIVOS_CLAVE}"
        )
    resultado = []
    for alias, ruta in valor.items():
        if not isinstance(alias, str) or not _PATRON_ALIAS.match(alias):
            raise ValueError(f"componente '{nombre}': alias de archivo clave no valido")
        texto = _exigir_texto(ruta, "archivos_clave", nombre, MAX_RUTA)
        resultado.append((alias, str(ruta_miembro_segura(texto))))
    return tuple(resultado)


def _validar_booleano(valor: object, campo: str, nombre: str) -> bool:
    """Valida que un campo sea un booleano JSON estricto."""
    if not isinstance(valor, bool):
        raise ValueError(f"componente '{nombre}': el campo '{campo}' debe ser verdadero o falso")
    return valor


def _validar_fecha(valor: object, nombre: str) -> str:
    """Valida una fecha ISO 8601 (AAAA-MM-DD)."""
    texto = _exigir_texto(valor, "fecha_registro", nombre, 10)
    try:
        date.fromisoformat(texto)
    except ValueError:
        raise ValueError(f"componente '{nombre}': 'fecha_registro' debe ser AAAA-MM-DD") from None
    return texto


def parsear_componente(nombre: str, datos: object) -> Componente:
    """
    Construye un ``Componente`` validando cada campo del bloque del lock.

    Contexto:
        Lo invoca ``cargar_lock`` por cada entrada del archivo de bloqueo.

    Args:
        nombre (str): Clave bajo la que figura el componente.
        datos (object): Valor JSON asociado a esa clave.

    Returns:
        Componente: Componente validado.

    Raises:
        ValueError: Si el nombre, la URL, la huella, la fecha, el formato o las listas no cumplen.

    Ejemplo:
        componente = parsear_componente("maspsx", {"url": "https://...", "sha256": "..."})
    """
    if not _PATRON_NOMBRE.match(nombre):
        raise ValueError("nombre de componente no valido: solo minusculas, digitos, '.', '_' y '-'")
    if not isinstance(datos, dict):
        raise ValueError(f"componente '{nombre}': el bloque debe ser un objeto")
    sha = _exigir_texto(datos.get("sha256"), "sha256", nombre, 64).lower()
    if not _PATRON_SHA256.match(sha):
        raise ValueError(f"componente '{nombre}': 'sha256' debe tener 64 digitos hexadecimales")
    formato = _exigir_texto(datos.get("formato", "archivo"), "formato", nombre, 16)
    if formato not in FORMATOS_ADMITIDOS:
        raise ValueError(f"componente '{nombre}': formato '{formato}' no admitido")
    url = validar_url(_exigir_texto(datos.get("url"), "url", nombre, 1000), nombre)
    return Componente(
        nombre=nombre,
        url=url,
        sha256=sha,
        fecha_registro=_validar_fecha(datos.get("fecha_registro"), nombre),
        notas=_exigir_texto(datos.get("notas"), "notas", nombre, MAX_NOTAS),
        formato=formato,
        extraer=_validar_patrones(datos.get("extraer"), nombre),
        archivos_clave=_validar_archivos_clave(datos.get("archivos_clave"), nombre),
        quitar_raiz=_validar_booleano(datos.get("quitar_raiz", False), "quitar_raiz", nombre),
    )


def cargar_lock(datos: object) -> dict[str, Componente]:
    """
    Valida el contenido completo del archivo de bloqueo y lo convierte en componentes.

    Contexto:
        Punto de entrada de la capa de dominio: la CLI lee el JSON y lo pasa tal cual.

    Args:
        datos (object): Resultado de ``json.load`` sobre ``config/toolchain.lock.json``.

    Returns:
        dict[str, Componente]: Componentes indexados por nombre, en el orden del archivo.

    Raises:
        ValueError: Si la version del esquema no coincide, falta la seccion de componentes o
            alguno de ellos no es valido.

    Ejemplo:
        lock = cargar_lock(json.loads(texto))
    """
    if not isinstance(datos, dict) or datos.get("version") != VERSION_LOCK:
        raise ValueError(f"el archivo de bloqueo debe ser un objeto con 'version' igual a {VERSION_LOCK}")
    bloque = datos.get("componentes")
    if not isinstance(bloque, dict) or not bloque or len(bloque) > MAX_COMPONENTES:
        raise ValueError(f"'componentes' debe ser un objeto con entre 1 y {MAX_COMPONENTES} entradas")
    return {nombre: parsear_componente(nombre, valor) for nombre, valor in bloque.items()}


def obtener_componente(lock: dict[str, Componente], nombre: str) -> Componente:
    """
    Busca un componente en el lock y falla nombrandolo si no existe.

    Contexto:
        Se usa al pedir una instalacion parcial (``--solo``) o al resolver una herramienta.

    Args:
        lock (dict[str, Componente]): Lock ya validado.
        nombre (str): Componente buscado.

    Returns:
        Componente: La entrada encontrada.

    Raises:
        ValueError: Si el componente no figura en el lock.

    Ejemplo:
        componente = obtener_componente(lock, "binutils-mipsel")
    """
    try:
        return lock[nombre]
    except KeyError:
        raise ValueError(f"el componente '{nombre}' no figura en el archivo de bloqueo") from None


def verificar_sha256(componente: Componente, obtenido: str) -> None:
    """
    Compara la huella calculada con la registrada en el lock.

    Contexto:
        Se ejecuta tras cada descarga, antes de dar por bueno el archivo.

    Args:
        componente (Componente): Componente con la huella esperada.
        obtenido (str): SHA-256 calculado del archivo descargado, en hexadecimal.

    Raises:
        ValueError: Si las huellas difieren; el mensaje nombra el componente y ambas huellas.

    Ejemplo:
        verificar_sha256(componente, "ab12...")
    """
    if obtenido.lower() != componente.sha256:
        raise ValueError(
            f"componente '{componente.nombre}': huella SHA-256 distinta a la registrada "
            f"(esperada {componente.sha256}, obtenida {obtenido.lower()})"
        )

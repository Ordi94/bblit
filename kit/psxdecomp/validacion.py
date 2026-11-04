"""Validadores primitivos de datos externos: tablas TOML, textos, rutas, direcciones y expresiones.

Capa inferior del cargador del manifiesto. Cada validador recibe una tabla ya leida, el nombre de
la clave y el nombre de la seccion, acepta solo lo que enumera (listas de admitidos) y rechaza lo
demas con un ``ManifiestoError`` que dice que campo falla y que se esperaba. Los mensajes nunca
incluyen el valor recibido ni rutas absolutas: el contenido del manifiesto es entrada no confiable.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from typing import Any

from psxdecomp.constantes import NOMBRE_MANIFIESTO

DIRECCION_MINIMA = 0x80000000
DIRECCION_MAXIMA = 0x80800000
MAX_LARGO_RUTA = 200
MAX_LARGO_REGEX = 200
MAX_ELEMENTOS_LISTA = 16
MAX_LARGO_CLAVE_EN_MENSAJE = 40

PATRON_NOMBRE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
PATRON_SEGMENTO = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}$")
PATRON_RUTA = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*$")
PATRON_MACRO = re.compile(r"^[A-Z_][A-Z0-9_]{0,31}$")
PATRON_PREFIJO_ENTORNO = re.compile(r"^[A-Z](?:[A-Z0-9_]{0,30}[A-Z0-9])?$")
PATRON_VERSION_ASPSX = re.compile(r"^[0-9]{1,3}\.[0-9]{1,3}$")
# Opcion del compilador: guion, una letra y caracteres de identificador. Se excluyen por diseno
# -G (el umbral de datos pequenos lo fija cada archivo) y -o (la salida la fija el kit).
PATRON_OPCION_COMPILADOR = re.compile(r"^-(?![Go])[A-Za-z][A-Za-z0-9_.=+-]{0,31}$")
PATRON_PLUGIN = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*$")


class ManifiestoError(ValueError):
    """Error de validacion del manifiesto: el mensaje nombra el campo y lo esperado, nada mas."""


def fallo(seccion: str, clave: str | None, esperado: str) -> ManifiestoError:
    """
    Construye el error uniforme de validacion.

    Contexto:
        Unico punto donde se da formato a los mensajes, para que ninguno filtre el valor recibido.

    Args:
        seccion (str): Nombre de la seccion del manifiesto, o ``raiz`` para el nivel superior.
        clave (str, opcional): Clave que falla; ``None`` si el fallo afecta a la seccion entera.
        esperado (str): Descripcion de lo que se esperaba.

    Returns:
        ManifiestoError: Excepcion lista para lanzar.

    Ejemplo:
        raise fallo("rutas", "fuentes", "una cadena")
    """
    campo = f"[{seccion}]" if clave is None else f"[{seccion}].{clave}"
    return ManifiestoError(f"{NOMBRE_MANIFIESTO}: {campo}: se esperaba {esperado}")


def exigir_tabla(valor: object, seccion: str) -> Mapping[str, Any]:
    """
    Comprueba que un valor leido del TOML es una tabla.

    Contexto:
        Primer paso de cada seccion: un manifiesto con ``rutas = 3`` debe fallar aqui y no mas abajo.

    Args:
        valor (object): Valor leido.
        seccion (str): Nombre de la seccion, para el mensaje.

    Returns:
        Mapping[str, Any]: La misma tabla.

    Raises:
        ManifiestoError: Si el valor no es una tabla.

    Ejemplo:
        tabla = exigir_tabla({"nombre": "demo"}, "proyecto")
    """
    if not isinstance(valor, dict):
        raise fallo(seccion, None, "una tabla")
    return valor


def rechazar_claves_desconocidas(tabla: Mapping[str, Any], admitidas: Collection[str], seccion: str) -> None:
    """
    Rechaza toda clave que no figure en la lista de admitidas.

    Contexto:
        Una clave mal escrita (``fuente`` por ``fuentes``) se descartaria en silencio y el
        proyecto usaria el valor por defecto sin avisar; por eso la lista es cerrada.

    Args:
        tabla (Mapping[str, Any]): Tabla a revisar.
        admitidas (Collection[str]): Claves permitidas en la seccion.
        seccion (str): Nombre de la seccion, para el mensaje.

    Raises:
        ManifiestoError: Si hay al menos una clave no admitida; el mensaje nombra la primera
            (en orden alfabetico, truncada) sin volcar su valor.

    Ejemplo:
        rechazar_claves_desconocidas({"a": 1}, {"a"}, "rutas")
    """
    desconocidas = sorted(str(clave) for clave in tabla if clave not in admitidas)
    if desconocidas:
        nombre = desconocidas[0][:MAX_LARGO_CLAVE_EN_MENSAJE]
        raise fallo(seccion, nombre, "una clave admitida (esta no existe en el contrato)")


def _obtener(tabla: Mapping[str, Any], clave: str, seccion: str, defecto: object) -> object:
    """
    Devuelve el valor de una clave o su defecto; si falta y no hay defecto, es obligatoria.

    Contexto:
        Centraliza la distincion entre clave obligatoria y opcional de todos los validadores.

    Args:
        tabla (Mapping[str, Any]): Tabla de la seccion.
        clave (str): Clave buscada.
        seccion (str): Nombre de la seccion, para el mensaje.
        defecto (object): Valor por defecto, o ``None`` si la clave es obligatoria.

    Returns:
        object: El valor de la tabla o el defecto.

    Raises:
        ManifiestoError: Si la clave es obligatoria y no esta.

    Ejemplo:
        valor = _obtener({}, "nombre", "proyecto", "demo")
    """
    if clave in tabla:
        return tabla[clave]
    if defecto is None:
        raise fallo(seccion, clave, "la clave obligatoria (falta)")
    return defecto


def leer_cadena(
    tabla: Mapping[str, Any],
    clave: str,
    seccion: str,
    *,
    patron: re.Pattern[str],
    defecto: str | None = None,
) -> str:
    """
    Lee una cadena acotada que cumple un patron de caracteres admitidos.

    Contexto:
        Nombres, macros y prefijos del manifiesto: todo texto que luego se usa como identificador.

    Args:
        tabla (Mapping[str, Any]): Tabla de la seccion.
        clave (str): Clave a leer.
        seccion (str): Nombre de la seccion.
        patron (re.Pattern[str]): Patron que debe cumplir completo (incluye la cota de largo).
        defecto (str, opcional): Valor si la clave falta; ``None`` hace la clave obligatoria.

    Returns:
        str: La cadena validada.

    Raises:
        ManifiestoError: Si falta, no es cadena o no cumple el patron.

    Ejemplo:
        nombre = leer_cadena({"nombre": "demo"}, "nombre", "proyecto", patron=PATRON_NOMBRE)
    """
    valor = _obtener(tabla, clave, seccion, defecto)
    if not isinstance(valor, str) or patron.fullmatch(valor) is None:
        raise fallo(seccion, clave, "una cadena con los caracteres y la longitud admitidos")
    return valor


def _validar_ruta(valor: object, clave: str, seccion: str) -> str:
    """
    Valida una ruta relativa de proyecto escrita con barras normales.

    Contexto:
        Comun a ``leer_ruta`` y ``leer_lista_rutas``. La lista de admitidos de caracteres excluye
        barra invertida, ``:`` (unidades) y espacios; los segmentos vacios, ``.`` y ``..`` se
        rechazan para que la ruta no pueda salir de la raiz del proyecto.

    Args:
        valor (object): Valor leido.
        clave (str): Clave de origen, para el mensaje.
        seccion (str): Seccion de origen, para el mensaje.

    Returns:
        str: La ruta validada, sin cambios.

    Raises:
        ManifiestoError: Si no es una ruta relativa admitida.

    Ejemplo:
        ruta = _validar_ruta("config/splat.yaml", "splat", "rutas")
    """
    esperado = "una ruta relativa a la raiz del proyecto, con barras normales y sin salir de ella"
    if not isinstance(valor, str) or len(valor) > MAX_LARGO_RUTA or PATRON_RUTA.fullmatch(valor) is None:
        raise fallo(seccion, clave, esperado)
    if any(segmento in {"", ".", ".."} for segmento in valor.split("/")):
        raise fallo(seccion, clave, esperado)
    return valor


def leer_ruta(tabla: Mapping[str, Any], clave: str, seccion: str, *, defecto: str | None = None) -> str:
    """
    Lee una ruta relativa a la raiz del proyecto.

    Contexto:
        Todas las rutas del manifiesto pasan por aqui; la comprobacion contra enlaces simbolicos
        que escapan de la raiz la hace ``comprobar_dentro_de_raiz`` al construir el proyecto.

    Args:
        tabla (Mapping[str, Any]): Tabla de la seccion.
        clave (str): Clave a leer.
        seccion (str): Nombre de la seccion.
        defecto (str, opcional): Valor si falta; ``None`` hace la clave obligatoria.

    Returns:
        str: Ruta relativa validada.

    Raises:
        ManifiestoError: Si falta o no es una ruta relativa admitida.

    Ejemplo:
        fuentes = leer_ruta({}, "fuentes", "rutas", defecto="src")
    """
    return _validar_ruta(_obtener(tabla, clave, seccion, defecto), clave, seccion)


def _leer_lista(
    tabla: Mapping[str, Any], clave: str, seccion: str, defecto: tuple[str, ...], *, minimo: int
) -> list[object]:
    """
    Lee una lista acotada en numero de elementos.

    Contexto:
        Base de las listas de rutas, segmentos y plugins; aplica la misma cota a todas.

    Args:
        tabla (Mapping[str, Any]): Tabla de la seccion.
        clave (str): Clave a leer.
        seccion (str): Nombre de la seccion.
        defecto (tuple[str, ...]): Valor si la clave falta.
        minimo (int): Numero minimo de elementos admitido.

    Returns:
        list[object]: Elementos sin validar individualmente.

    Raises:
        ManifiestoError: Si no es lista o su tamano esta fuera de ``[minimo, MAX_ELEMENTOS_LISTA]``.

    Ejemplo:
        elementos = _leer_lista({"a": ["x"]}, "a", "rutas", (), minimo=0)
    """
    valor = tabla[clave] if clave in tabla else list(defecto)
    if not isinstance(valor, list) or not minimo <= len(valor) <= MAX_ELEMENTOS_LISTA:
        raise fallo(seccion, clave, f"una lista de {minimo} a {MAX_ELEMENTOS_LISTA} elementos")
    return valor


def _sin_repetidos(elementos: tuple[str, ...], clave: str, seccion: str) -> tuple[str, ...]:
    """
    Comprueba que una lista no repite elementos.

    Contexto:
        Un elemento repetido casi siempre es un error de copia y deja la lista ambigua.

    Args:
        elementos (tuple[str, ...]): Elementos ya validados.
        clave (str): Clave de origen.
        seccion (str): Seccion de origen.

    Returns:
        tuple[str, ...]: Los mismos elementos.

    Raises:
        ManifiestoError: Si hay repetidos.

    Ejemplo:
        _sin_repetidos(("a", "b"), "simbolos", "rutas")
    """
    if len(set(elementos)) != len(elementos):
        raise fallo(seccion, clave, "elementos sin repetir")
    return elementos


def leer_lista_rutas(
    tabla: Mapping[str, Any], clave: str, seccion: str, *, defecto: tuple[str, ...], minimo: int = 0
) -> tuple[str, ...]:
    """
    Lee una lista de rutas relativas sin repetidos.

    Contexto:
        Archivos de simbolos del proyecto (``rutas.simbolos``).

    Args:
        tabla (Mapping[str, Any]): Tabla de la seccion.
        clave (str): Clave a leer.
        seccion (str): Nombre de la seccion.
        defecto (tuple[str, ...]): Valor si la clave falta.
        minimo (int, opcional): Numero minimo de elementos.

    Returns:
        tuple[str, ...]: Rutas validadas.

    Raises:
        ManifiestoError: Si algun elemento no es una ruta admitida o la lista no cumple las cotas.

    Ejemplo:
        simbolos = leer_lista_rutas({}, "simbolos", "rutas", defecto=("a.txt",), minimo=1)
    """
    elementos = _leer_lista(tabla, clave, seccion, defecto, minimo=minimo)
    rutas = tuple(_validar_ruta(elemento, clave, seccion) for elemento in elementos)
    return _sin_repetidos(rutas, clave, seccion)


def leer_lista_texto(
    tabla: Mapping[str, Any],
    clave: str,
    seccion: str,
    *,
    patron: re.Pattern[str],
    defecto: tuple[str, ...],
) -> tuple[str, ...]:
    """
    Lee una lista de cadenas que cumplen un patron, sin repetidos.

    Contexto:
        Nombres de subcarpetas ajenas y referencias de plugins.

    Args:
        tabla (Mapping[str, Any]): Tabla de la seccion.
        clave (str): Clave a leer.
        seccion (str): Nombre de la seccion.
        patron (re.Pattern[str]): Patron que debe cumplir cada elemento completo.
        defecto (tuple[str, ...]): Valor si la clave falta.

    Returns:
        tuple[str, ...]: Elementos validados.

    Raises:
        ManifiestoError: Si algun elemento no cumple el patron o la lista excede las cotas.

    Ejemplo:
        ajenas = leer_lista_texto({}, "subcarpetas_ajenas", "rutas", patron=PATRON_SEGMENTO, defecto=())
    """
    elementos = _leer_lista(tabla, clave, seccion, defecto, minimo=0)
    for elemento in elementos:
        if not isinstance(elemento, str) or patron.fullmatch(elemento) is None:
            raise fallo(seccion, clave, "elementos de texto con los caracteres y la longitud admitidos")
    return _sin_repetidos(tuple(str(elemento) for elemento in elementos), clave, seccion)


def leer_direccion(tabla: Mapping[str, Any], clave: str, seccion: str) -> int:
    """
    Lee una direccion de memoria PlayStation (obligatoria).

    Contexto:
        Zonas del ejecutable. El rango admitido es la RAM virtual KSEG0 de la consola.

    Args:
        tabla (Mapping[str, Any]): Tabla de la seccion.
        clave (str): Clave a leer.
        seccion (str): Nombre de la seccion.

    Returns:
        int: Direccion dentro de ``[DIRECCION_MINIMA, DIRECCION_MAXIMA]``.

    Raises:
        ManifiestoError: Si falta, no es entero (un booleano tampoco lo es) o esta fuera de rango.

    Ejemplo:
        desde = leer_direccion({"d": 0x80010000}, "d", "zonas")
    """
    valor = _obtener(tabla, clave, seccion, None)
    if (
        isinstance(valor, bool)
        or not isinstance(valor, int)
        or not DIRECCION_MINIMA <= valor <= DIRECCION_MAXIMA
    ):
        raise fallo(seccion, clave, f"un entero entre 0x{DIRECCION_MINIMA:08X} y 0x{DIRECCION_MAXIMA:08X}")
    return valor


def leer_entero(
    tabla: Mapping[str, Any], clave: str, seccion: str, *, defecto: int, minimo: int, maximo: int
) -> int:
    """
    Lee un entero acotado a un rango cerrado.

    Contexto:
        Cotas numericas del manifiesto (por ejemplo el mayor umbral de datos pequenos admitido).
        Un valor fuera de rango acaba como argumento de un proceso externo, por eso se rechaza aqui.

    Args:
        tabla (Mapping[str, Any]): Tabla de la seccion.
        clave (str): Clave a leer.
        seccion (str): Nombre de la seccion.
        defecto (int): Valor si la clave falta.
        minimo (int): Menor valor admitido.
        maximo (int): Mayor valor admitido.

    Returns:
        int: El entero validado.

    Raises:
        ManifiestoError: Si no es entero (un booleano tampoco lo es) o esta fuera de ``[minimo, maximo]``.

    Ejemplo:
        tope = leer_entero({}, "max_valor_g", "convenciones", defecto=64, minimo=0, maximo=4096)
    """
    valor = _obtener(tabla, clave, seccion, defecto)
    if isinstance(valor, bool) or not isinstance(valor, int) or not minimo <= valor <= maximo:
        raise fallo(seccion, clave, f"un entero entre {minimo} y {maximo}")
    return valor


def leer_regex(
    tabla: Mapping[str, Any], clave: str, seccion: str, *, defecto: str, grupos: int | None = None
) -> str:
    r"""
    Lee una expresion regular acotada y comprueba que compila.

    Contexto:
        Convenciones de comentarios del proyecto. Compilarla aqui evita que una expresion invalida
        reviente en mitad de una construccion, lejos del manifiesto que la contiene.

    Args:
        tabla (Mapping[str, Any]): Tabla de la seccion.
        clave (str): Clave a leer.
        seccion (str): Nombre de la seccion.
        defecto (str): Valor si la clave falta.
        grupos (int, opcional): Numero exacto de grupos de captura exigido; ``None`` no lo exige.

    Returns:
        str: El texto de la expresion, validado.

    Raises:
        ManifiestoError: Si no es cadena, excede ``MAX_LARGO_REGEX``, no compila o tiene otro
            numero de grupos.

    Ejemplo:
        patron = leer_regex({}, "sufijo", "convenciones", defecto=r"_\d+$")
    """
    valor = _obtener(tabla, clave, seccion, defecto)
    esperado = "una expresion regular valida"
    if grupos is not None:
        esperado += f" con {grupos} grupo(s) de captura"
    if not isinstance(valor, str) or not valor or len(valor) > MAX_LARGO_REGEX:
        raise fallo(seccion, clave, esperado)
    try:
        compilada = re.compile(valor)
    except re.error:
        raise fallo(seccion, clave, esperado) from None
    if grupos is not None and compilada.groups != grupos:
        raise fallo(seccion, clave, esperado)
    return valor

"""Modelo del manifiesto: secciones inmutables y su construccion a partir de tablas ya leidas.

Capa de dominio del cargador. Todo lo que hay aqui opera sobre datos en memoria: recibe el
documento TOML ya analizado y entrega un ``Proyecto`` o un ``ManifiestoError``. No lee archivos ni
resuelve rutas contra el disco (eso es de ``lectura``), de modo que cada regla se prueba con
diccionarios. La unica excepcion declarada es ``Proyecto.ruta_absoluta``, que reutiliza la regla de
``confinamiento`` porque se invoca despues de cargar y debe aplicar exactamente la misma.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psxdecomp import validacion as val
from psxdecomp.confinamiento import esta_confinada
from psxdecomp.constantes import NOMBRE_MANIFIESTO
from psxdecomp.validacion import ManifiestoError

PREFIJO_PROPIO = "PSXDECOMP"
PATRON_SUFIJO_ENTORNO = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")

SECCIONES = frozenset({"proyecto", "rutas", "zonas", "convenciones", "plugins"})
CLAVES_PROYECTO = frozenset({"nombre", "ejecutable", "referencia", "prefijo_entorno"})
CLAVES_RUTAS = frozenset(
    {
        "fuentes",
        "incluir",
        "asm",
        "build",
        "expected",
        "splat",
        "simbolos",
        "simbolos_adicionales",
        "opciones_compilacion",
        "toolchain_lock",
        "local",
        "documento_progreso",
        "subcarpetas_ajenas",
        "asm_auxiliares",
    }
)
CLAVES_ZONAS = frozenset({"juego_desde", "librerias_desde", "librerias_hasta"})
CLAVES_CONVENCIONES = frozenset(
    {"macro_no_coincidente", "macro_ensamblador", "pendiente", "sufijo_subsistema"}
)
CLAVES_PLUGINS = frozenset({"subcomandos", "antes_de_construir", "despues_de_verificar"})

RUTAS_SENCILLAS_POR_DEFECTO = {
    "fuentes": "src",
    "incluir": "include",
    "asm": "asm",
    "build": "build",
    "expected": "expected",
    "splat": "config/splat.yaml",
    "simbolos_adicionales": "config/simbolos_adicionales.txt",
    "opciones_compilacion": "config/opciones_compilacion.toml",
    "toolchain_lock": "config/toolchain.lock.json",
    "local": "config/local.toml",
    "documento_progreso": "docs/PROGRESO.md",
}


@dataclass(frozen=True, slots=True)
class Identidad:
    """Seccion ``[proyecto]``: quien es el proyecto y como se llama su ejecutable."""

    nombre: str
    ejecutable: str
    referencia: str
    prefijo_entorno: str


@dataclass(frozen=True, slots=True)
class Rutas:
    """Seccion ``[rutas]``: carpetas y archivos del proyecto, todos relativos a su raiz."""

    fuentes: str
    incluir: str
    asm: str
    build: str
    expected: str
    splat: str
    simbolos: tuple[str, ...]
    simbolos_adicionales: str
    opciones_compilacion: str
    toolchain_lock: str
    local: str
    documento_progreso: str
    subcarpetas_ajenas: tuple[str, ...]
    asm_auxiliares: tuple[str, ...]

    def pares(self) -> tuple[tuple[str, str], ...]:
        """
        Enumera cada ruta declarada junto a la clave del manifiesto de la que procede.

        Contexto:
            La lectura del manifiesto comprueba el confinamiento de todas las rutas contra el disco;
            este metodo le entrega la lista sin que conozca los nombres de los campos y permite que
            el error nombre la clave exacta. Las subcarpetas ajenas y los auxiliares son segmentos
            sueltos, no rutas, y no se incluyen.

        Returns:
            tuple[tuple[str, str], ...]: Pares ``(clave, ruta)``; ``simbolos`` aporta uno por elemento.

        Ejemplo:
            for clave, ruta in rutas.pares():
                ...
        """
        sencillas = tuple((clave, getattr(self, clave)) for clave in RUTAS_SENCILLAS_POR_DEFECTO)
        return (*sencillas, *(("simbolos", ruta) for ruta in self.simbolos))


@dataclass(frozen=True, slots=True)
class Zonas:
    """Seccion ``[zonas]``: limites de memoria del ejecutable (inicio inclusivo, fin exclusivo)."""

    juego_desde: int
    librerias_desde: int
    librerias_hasta: int


@dataclass(frozen=True, slots=True)
class Convenciones:
    """Seccion ``[convenciones]``: macros y formatos de comentario que reconoce el analisis de C."""

    macro_no_coincidente: str
    macro_ensamblador: str
    pendiente: str
    sufijo_subsistema: str


@dataclass(frozen=True, slots=True)
class Plugins:
    """Seccion ``[plugins]``: extensiones del proyecto como referencias ``modulo:funcion``."""

    subcomandos: tuple[str, ...]
    antes_de_construir: tuple[str, ...]
    despues_de_verificar: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Proyecto:
    """Manifiesto validado de un proyecto consumidor, inmutable y listo para pasarse al kit."""

    raiz: Path
    identidad: Identidad
    rutas: Rutas
    zonas: Zonas
    convenciones: Convenciones
    plugins: Plugins

    def variable_entorno(self, sufijo: str, entorno: Mapping[str, str] | None = None) -> str | None:
        """
        Resuelve una variable de entorno del proyecto con su alias de transicion.

        Contexto:
            Todo el kit lee su configuracion de entorno (disco, toolchain, Wine) por aqui. El
            prefijo propio ``PSXDECOMP_`` manda; el prefijo del manifiesto (por ejemplo el que
            usaba el proyecto antes de adoptar el kit) se acepta como alias para no romper entornos
            ya configurados. Una variable definida pero vacia cuenta como ausente.

        Args:
            sufijo (str): Nombre sin prefijo en mayusculas, por ejemplo ``DISC``.
            entorno (Mapping[str, str], opcional): Entorno a consultar; por omision ``os.environ``.

        Returns:
            str | None: Valor de la primera variable definida y no vacia, o ``None``.

        Raises:
            ValueError: Si ``sufijo`` no es un identificador en mayusculas (evita consultar nombres
                construidos con entrada arbitraria).

        Ejemplo:
            disco = proyecto.variable_entorno("DISC")
        """
        if PATRON_SUFIJO_ENTORNO.fullmatch(sufijo) is None:
            raise ValueError("el sufijo de variable de entorno debe ser un identificador en mayusculas")
        fuente = os.environ if entorno is None else entorno
        prefijos = (PREFIJO_PROPIO, self.identidad.prefijo_entorno)
        for prefijo in dict.fromkeys(prefijos):
            valor = fuente.get(f"{prefijo}_{sufijo}")
            if valor:
                return valor
        return None

    def ruta_absoluta(self, relativa: str) -> Path:
        """
        Convierte una ruta del manifiesto en ruta absoluta bajo la raiz del proyecto.

        Contexto:
            Los modulos del kit guardan rutas relativas del manifiesto y solo las resuelven al
            tocar disco. Es el unico metodo del modelo que consulta el sistema de archivos, y lo
            hace por la misma regla de ``confinamiento`` que aplico la lectura al cargar.

        Args:
            relativa (str): Ruta relativa, normalmente un campo de ``rutas``.

        Returns:
            Path: ``raiz / relativa``.

        Raises:
            ValueError: Si la ruta tiene unidad o raiz (``/x``, ``C:/x``, ruta de red), contiene
                ``..`` o, resuelta, queda fuera de la raiz del proyecto.

        Ejemplo:
            fuentes = proyecto.ruta_absoluta(proyecto.rutas.fuentes)
        """
        if not esta_confinada(self.raiz, relativa):
            raise ValueError("la ruta debe ser relativa y no salir de la raiz del proyecto")
        return self.raiz / relativa

    def resumen(self) -> str:
        """
        Resume el manifiesto validado en texto, sin rutas absolutas.

        Contexto:
            Es lo que imprime ``python -m psxdecomp.cli comprobar``.

        Returns:
            str: Una clave por linea, con las direcciones en hexadecimal.

        Ejemplo:
            print(proyecto.resumen())
        """
        ident, rutas, zonas, conv, plug = (
            self.identidad,
            self.rutas,
            self.zonas,
            self.convenciones,
            self.plugins,
        )
        lineas = [
            f"proyecto: {ident.nombre}",
            f"ejecutable: {ident.ejecutable}",
            f"referencia: {ident.referencia}",
            f"prefijo_entorno: {ident.prefijo_entorno}",
            f"fuentes: {rutas.fuentes}  incluir: {rutas.incluir}  asm: {rutas.asm}",
            f"build: {rutas.build}  expected: {rutas.expected}",
            f"simbolos: {', '.join(rutas.simbolos)}",
            f"subcarpetas_ajenas: {', '.join(rutas.subcarpetas_ajenas) or '-'}",
            f"zonas: juego 0x{zonas.juego_desde:08X}, "
            f"librerias 0x{zonas.librerias_desde:08X}-0x{zonas.librerias_hasta:08X}",
            f"macros: {conv.macro_no_coincidente}, {conv.macro_ensamblador}",
            f"plugins: {len(plug.subcomandos)} subcomando(s), "
            f"{len(plug.antes_de_construir)} antes de construir, "
            f"{len(plug.despues_de_verificar)} despues de verificar",
        ]
        return "\n".join(lineas)


def extraer_seccion(
    datos: Mapping[str, Any], nombre: str, admitidas: frozenset[str], *, obligatoria: bool
) -> Mapping[str, Any]:
    """
    Extrae una seccion, comprueba que es tabla y que solo usa claves admitidas.

    Contexto:
        Evita repetir la secuencia existencia, tipo y claves en cada una de las cinco secciones.

    Args:
        datos (Mapping[str, Any]): Documento TOML completo.
        nombre (str): Nombre de la seccion.
        admitidas (frozenset[str]): Claves permitidas en ella.
        obligatoria (bool): Si ``True`` la ausencia de la seccion es un error.

    Returns:
        Mapping[str, Any]: La tabla, o una vacia si es opcional y falta.

    Raises:
        ManifiestoError: Si falta siendo obligatoria, no es tabla o tiene claves desconocidas.

    Ejemplo:
        tabla = extraer_seccion({"zonas": {}}, "zonas", CLAVES_ZONAS, obligatoria=False)
    """
    if nombre not in datos:
        if obligatoria:
            raise ManifiestoError(f"{NOMBRE_MANIFIESTO}: [{nombre}]: se esperaba la seccion (falta)")
        return {}
    tabla = val.exigir_tabla(datos[nombre], nombre)
    val.rechazar_claves_desconocidas(tabla, admitidas, nombre)
    return tabla


def construir_identidad(tabla: Mapping[str, Any]) -> Identidad:
    """
    Construye la seccion ``[proyecto]``.

    Contexto:
        ``nombre`` y ``ejecutable`` no tienen valor por defecto: identifican al proyecto y el kit
        no puede suponerlos. Que la referencia no escape de la raiz lo comprueba la lectura, que
        es quien conoce el disco.

    Args:
        tabla (Mapping[str, Any]): Tabla ``[proyecto]`` ya revisada.

    Returns:
        Identidad: Seccion validada.

    Raises:
        ManifiestoError: Si algun campo no cumple su contrato.

    Ejemplo:
        identidad = construir_identidad({"nombre": "demo", "ejecutable": "EJEC.01"})
    """
    return Identidad(
        nombre=val.leer_cadena(tabla, "nombre", "proyecto", patron=val.PATRON_NOMBRE),
        ejecutable=val.leer_cadena(tabla, "ejecutable", "proyecto", patron=val.PATRON_NOMBRE),
        referencia=val.leer_ruta(tabla, "referencia", "proyecto", defecto="config/ejecutable.json"),
        prefijo_entorno=val.leer_cadena(
            tabla, "prefijo_entorno", "proyecto", patron=val.PATRON_PREFIJO_ENTORNO, defecto=PREFIJO_PROPIO
        ),
    )


def construir_rutas(tabla: Mapping[str, Any]) -> Rutas:
    """
    Construye la seccion ``[rutas]`` con los valores por defecto genericos del kit.

    Contexto:
        Cada ruta se valida lexicamente; el confinamiento contra enlaces simbolicos que escapen de
        la raiz lo aplica la lectura despues, porque exige consultar el disco.

    Args:
        tabla (Mapping[str, Any]): Tabla ``[rutas]`` ya revisada (puede estar vacia).

    Returns:
        Rutas: Seccion validada.

    Raises:
        ManifiestoError: Si alguna ruta o lista no cumple su contrato.

    Ejemplo:
        rutas = construir_rutas({})
    """
    valores: dict[str, Any] = {
        clave: val.leer_ruta(tabla, clave, "rutas", defecto=defecto)
        for clave, defecto in RUTAS_SENCILLAS_POR_DEFECTO.items()
    }
    valores["simbolos"] = val.leer_lista_rutas(
        tabla, "simbolos", "rutas", defecto=("config/symbols.txt",), minimo=1
    )
    for clave in ("subcarpetas_ajenas", "asm_auxiliares"):
        valores[clave] = val.leer_lista_texto(tabla, clave, "rutas", patron=val.PATRON_SEGMENTO, defecto=())
    return Rutas(**valores)


def construir_zonas(tabla: Mapping[str, Any]) -> Zonas:
    """
    Construye la seccion ``[zonas]`` y comprueba que los limites estan ordenados.

    Contexto:
        Las tres direcciones son obligatorias porque dependen del ejecutable concreto. Si no
        estuvieran en orden estricto, la clasificacion de funciones por zona seria incoherente.

    Args:
        tabla (Mapping[str, Any]): Tabla ``[zonas]`` ya revisada.

    Returns:
        Zonas: Seccion validada.

    Raises:
        ManifiestoError: Si falta alguna direccion, esta fuera de rango o el orden no es estricto.

    Ejemplo:
        zonas = construir_zonas({"juego_desde": 0x80010000, "librerias_desde": 0x80020000,
                                 "librerias_hasta": 0x80030000})
    """
    zonas = Zonas(
        juego_desde=val.leer_direccion(tabla, "juego_desde", "zonas"),
        librerias_desde=val.leer_direccion(tabla, "librerias_desde", "zonas"),
        librerias_hasta=val.leer_direccion(tabla, "librerias_hasta", "zonas"),
    )
    if not zonas.juego_desde < zonas.librerias_desde < zonas.librerias_hasta:
        raise ManifiestoError(
            f"{NOMBRE_MANIFIESTO}: [zonas]: se esperaba juego_desde < librerias_desde < librerias_hasta"
        )
    return zonas


def construir_convenciones(tabla: Mapping[str, Any]) -> Convenciones:
    """
    Construye la seccion ``[convenciones]`` con los valores por defecto del kit.

    Contexto:
        ``pendiente`` debe tener exactamente un grupo de captura: el numero de la puntuacion que
        el analisis de C compara con la ultima medicion.

    Args:
        tabla (Mapping[str, Any]): Tabla ``[convenciones]`` ya revisada (puede estar vacia).

    Returns:
        Convenciones: Seccion validada.

    Raises:
        ManifiestoError: Si una macro o expresion no cumple su contrato.

    Ejemplo:
        convenciones = construir_convenciones({})
    """
    return Convenciones(
        macro_no_coincidente=val.leer_cadena(
            tabla, "macro_no_coincidente", "convenciones", patron=val.PATRON_MACRO, defecto="NON_MATCHING"
        ),
        macro_ensamblador=val.leer_cadena(
            tabla, "macro_ensamblador", "convenciones", patron=val.PATRON_MACRO, defecto="INCLUDE_ASM"
        ),
        pendiente=val.leer_regex(
            tabla, "pendiente", "convenciones", defecto=r"\APendiente:\s*puntuacion\s+(\d+)\b", grupos=1
        ),
        sufijo_subsistema=val.leer_regex(tabla, "sufijo_subsistema", "convenciones", defecto=r"_\d+$"),
    )


def construir_plugins(tabla: Mapping[str, Any]) -> Plugins:
    """
    Construye la seccion ``[plugins]``: referencias ``modulo:funcion`` que el kit importara.

    Contexto:
        Aqui solo se valida la forma de la referencia; importar el modulo corresponde a quien la use.

    Args:
        tabla (Mapping[str, Any]): Tabla ``[plugins]`` ya revisada (puede estar vacia).

    Returns:
        Plugins: Seccion validada.

    Raises:
        ManifiestoError: Si alguna referencia no tiene la forma ``paquete.modulo:funcion``.

    Ejemplo:
        plugins = construir_plugins({"subcomandos": ["paquete.modulo:registrar"]})
    """
    return Plugins(
        **{
            clave: val.leer_lista_texto(tabla, clave, "plugins", patron=val.PATRON_PLUGIN, defecto=())
            for clave in ("subcomandos", "antes_de_construir", "despues_de_verificar")
        }
    )


def construir_proyecto(datos: Mapping[str, Any], raiz: Path) -> Proyecto:
    """
    Construye el ``Proyecto`` a partir del documento TOML ya analizado.

    Contexto:
        Nucleo puro del cargador: valida secciones, claves, tipos y cotas sin tocar el disco. La
        raiz solo se guarda en el resultado; el confinamiento de rutas es responsabilidad de
        ``lectura.cargar_proyecto``, que invoca esta funcion y despues lo comprueba.

    Args:
        datos (Mapping[str, Any]): Documento TOML completo.
        raiz (Path): Raiz del proyecto que se conserva en ``Proyecto.raiz``.

    Returns:
        Proyecto: Manifiesto validado e inmutable.

    Raises:
        ManifiestoError: Si hay secciones o claves desconocidas, falta una seccion obligatoria o
            algun valor incumple su contrato.

    Ejemplo:
        proyecto = construir_proyecto({"proyecto": {...}, "zonas": {...}}, Path("."))
    """
    val.rechazar_claves_desconocidas(datos, SECCIONES, "raiz")
    return Proyecto(
        raiz=raiz,
        identidad=construir_identidad(extraer_seccion(datos, "proyecto", CLAVES_PROYECTO, obligatoria=True)),
        rutas=construir_rutas(extraer_seccion(datos, "rutas", CLAVES_RUTAS, obligatoria=False)),
        zonas=construir_zonas(extraer_seccion(datos, "zonas", CLAVES_ZONAS, obligatoria=True)),
        convenciones=construir_convenciones(
            extraer_seccion(datos, "convenciones", CLAVES_CONVENCIONES, obligatoria=False)
        ),
        plugins=construir_plugins(extraer_seccion(datos, "plugins", CLAVES_PLUGINS, obligatoria=False)),
    )

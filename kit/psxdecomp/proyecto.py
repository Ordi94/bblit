"""Manifiesto ``psxdecomp.toml`` del proyecto consumidor y el objeto inmutable ``Proyecto``.

El kit no conoce ningun juego: nombre del ejecutable, rutas, zonas de memoria y convenciones de
los comentarios llegan siempre por este manifiesto. ``cargar_proyecto`` lo lee, lo valida contra
una lista cerrada de claves y cotas, y entrega un ``Proyecto`` que el resto del kit recibe por
parametro. El modulo tambien se puede ejecutar para comprobar un manifiesto::

    python -m psxdecomp.proyecto --comprobar [ruta]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psxdecomp import validacion as val
from psxdecomp.validacion import ManifiestoError

NOMBRE_MANIFIESTO = "psxdecomp.toml"
MAX_BYTES_MANIFIESTO = 64 * 1024
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
            tocar disco.

        Args:
            relativa (str): Ruta relativa, normalmente un campo de ``rutas``.

        Returns:
            Path: ``raiz / relativa``.

        Raises:
            ValueError: Si la ruta es absoluta o contiene ``..``.

        Ejemplo:
            fuentes = proyecto.ruta_absoluta(proyecto.rutas.fuentes)
        """
        candidata = Path(relativa)
        if candidata.is_absolute() or ".." in candidata.parts:
            raise ValueError("la ruta debe ser relativa y no salir de la raiz del proyecto")
        return self.raiz / candidata

    def resumen(self) -> str:
        """
        Resume el manifiesto validado en texto, sin rutas absolutas.

        Contexto:
            Es lo que imprime ``python -m psxdecomp.proyecto --comprobar``.

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


def _leer_texto_manifiesto(raiz: Path) -> str:
    """
    Lee el texto del manifiesto aplicando las comprobaciones previas al analisis TOML.

    Contexto:
        Primera barrera de ``cargar_proyecto``: existencia, tamano acotado y codificacion UTF-8.

    Args:
        raiz (Path): Raiz del proyecto.

    Returns:
        str: Contenido del manifiesto.

    Raises:
        ManifiestoError: Si la raiz no es carpeta, el archivo falta, excede el limite, no se puede
            leer o no es UTF-8. Los mensajes no incluyen rutas.

    Ejemplo:
        texto = _leer_texto_manifiesto(Path("."))
    """
    ruta = raiz / NOMBRE_MANIFIESTO
    if not raiz.is_dir() or not ruta.is_file():
        raise ManifiestoError(f"no existe {NOMBRE_MANIFIESTO} en la raiz del proyecto indicada")
    if ruta.stat().st_size > MAX_BYTES_MANIFIESTO:
        raise ManifiestoError(f"{NOMBRE_MANIFIESTO}: excede el tamano maximo de {MAX_BYTES_MANIFIESTO} bytes")
    try:
        return ruta.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise ManifiestoError(f"{NOMBRE_MANIFIESTO}: no se pudo leer como texto UTF-8") from None


def _seccion(
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
        tabla = _seccion({"zonas": {}}, "zonas", CLAVES_ZONAS, obligatoria=False)
    """
    if nombre not in datos:
        if obligatoria:
            raise ManifiestoError(f"{NOMBRE_MANIFIESTO}: [{nombre}]: se esperaba la seccion (falta)")
        return {}
    tabla = val.exigir_tabla(datos[nombre], nombre)
    val.rechazar_claves_desconocidas(tabla, admitidas, nombre)
    return tabla


def _construir_identidad(tabla: Mapping[str, Any], raiz: Path) -> Identidad:
    """
    Construye la seccion ``[proyecto]``.

    Contexto:
        ``nombre`` y ``ejecutable`` no tienen valor por defecto: identifican al proyecto y el kit
        no puede suponerlos.

    Args:
        tabla (Mapping[str, Any]): Tabla ``[proyecto]`` ya revisada.
        raiz (Path): Raiz del proyecto, para comprobar la ruta de la referencia.

    Returns:
        Identidad: Seccion validada.

    Raises:
        ManifiestoError: Si algun campo no cumple su contrato.

    Ejemplo:
        identidad = _construir_identidad({"nombre": "demo", "ejecutable": "EJEC.01"}, Path("."))
    """
    referencia = val.leer_ruta(tabla, "referencia", "proyecto", defecto="config/ejecutable.json")
    val.comprobar_dentro_de_raiz(raiz, referencia, "referencia", "proyecto")
    return Identidad(
        nombre=val.leer_cadena(tabla, "nombre", "proyecto", patron=val.PATRON_NOMBRE),
        ejecutable=val.leer_cadena(tabla, "ejecutable", "proyecto", patron=val.PATRON_NOMBRE),
        referencia=referencia,
        prefijo_entorno=val.leer_cadena(
            tabla, "prefijo_entorno", "proyecto", patron=val.PATRON_PREFIJO_ENTORNO, defecto=PREFIJO_PROPIO
        ),
    )


def _construir_rutas(tabla: Mapping[str, Any], raiz: Path) -> Rutas:
    """
    Construye la seccion ``[rutas]`` con los valores por defecto genericos del kit.

    Contexto:
        Cada ruta se valida lexicamente y despues contra enlaces simbolicos que escapen de la raiz.

    Args:
        tabla (Mapping[str, Any]): Tabla ``[rutas]`` ya revisada (puede estar vacia).
        raiz (Path): Raiz del proyecto.

    Returns:
        Rutas: Seccion validada.

    Raises:
        ManifiestoError: Si alguna ruta o lista no cumple su contrato.

    Ejemplo:
        rutas = _construir_rutas({}, Path("."))
    """
    sencillas = {
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
    valores: dict[str, Any] = {
        clave: val.leer_ruta(tabla, clave, "rutas", defecto=defecto) for clave, defecto in sencillas.items()
    }
    valores["simbolos"] = val.leer_lista_rutas(
        tabla, "simbolos", "rutas", defecto=("config/symbols.txt",), minimo=1
    )
    for clave in ("subcarpetas_ajenas", "asm_auxiliares"):
        valores[clave] = val.leer_lista_texto(tabla, clave, "rutas", patron=val.PATRON_SEGMENTO, defecto=())
    for clave in (*sencillas, "simbolos"):
        valor = valores[clave]
        for ruta in (valor,) if isinstance(valor, str) else valor:
            val.comprobar_dentro_de_raiz(raiz, ruta, clave, "rutas")
    return Rutas(**valores)


def _construir_zonas(tabla: Mapping[str, Any]) -> Zonas:
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
        zonas = _construir_zonas({"juego_desde": 0x80010000, "librerias_desde": 0x80020000,
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


def _construir_convenciones(tabla: Mapping[str, Any]) -> Convenciones:
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
        convenciones = _construir_convenciones({})
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


def _construir_plugins(tabla: Mapping[str, Any]) -> Plugins:
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
        plugins = _construir_plugins({"subcomandos": ["paquete.modulo:registrar"]})
    """
    return Plugins(
        **{
            clave: val.leer_lista_texto(tabla, clave, "plugins", patron=val.PATRON_PLUGIN, defecto=())
            for clave in ("subcomandos", "antes_de_construir", "despues_de_verificar")
        }
    )


def cargar_proyecto(raiz: Path) -> Proyecto:
    """
    Carga y valida el manifiesto ``psxdecomp.toml`` de la raiz de un proyecto.

    Contexto:
        Punto de entrada del kit: la CLI y cualquier modulo que necesite saber rutas, zonas o
        convenciones del proyecto empiezan aqui y reciben el ``Proyecto`` por parametro.

    Args:
        raiz (Path): Carpeta raiz del proyecto consumidor.

    Returns:
        Proyecto: Manifiesto validado e inmutable.

    Raises:
        ManifiestoError: Si el archivo falta, es muy grande, no es TOML valido, tiene secciones o
            claves desconocidas, o algun valor incumple su contrato. El mensaje dice que campo
            fallo y que se esperaba; nunca incluye rutas absolutas ni trazas.

    Ejemplo:
        proyecto = cargar_proyecto(Path("."))
    """
    texto = _leer_texto_manifiesto(raiz)
    try:
        datos = tomllib.loads(texto)
    except tomllib.TOMLDecodeError as error:
        raise ManifiestoError(f"{NOMBRE_MANIFIESTO}: no es un TOML valido ({error})") from None
    val.rechazar_claves_desconocidas(datos, SECCIONES, "raiz")
    return Proyecto(
        raiz=raiz,
        identidad=_construir_identidad(_seccion(datos, "proyecto", CLAVES_PROYECTO, obligatoria=True), raiz),
        rutas=_construir_rutas(_seccion(datos, "rutas", CLAVES_RUTAS, obligatoria=False), raiz),
        zonas=_construir_zonas(_seccion(datos, "zonas", CLAVES_ZONAS, obligatoria=True)),
        convenciones=_construir_convenciones(
            _seccion(datos, "convenciones", CLAVES_CONVENCIONES, obligatoria=False)
        ),
        plugins=_construir_plugins(_seccion(datos, "plugins", CLAVES_PLUGINS, obligatoria=False)),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """
    Punto de entrada de ``python -m psxdecomp.proyecto``.

    Contexto:
        Permite validar un manifiesto sin ejecutar ninguna otra herramienta del kit.

    Args:
        argv (Sequence[str], opcional): Argumentos; por omision ``sys.argv[1:]``.

    Returns:
        int: ``0`` si el manifiesto es valido, ``1`` si no lo es, ``2`` si falta ``--comprobar``.

    Ejemplo:
        codigo = main(["--comprobar", "."])
    """
    parser = argparse.ArgumentParser(prog="python -m psxdecomp.proyecto", description=__doc__)
    parser.add_argument("--comprobar", action="store_true", help="valida el manifiesto e imprime el resumen")
    parser.add_argument("ruta", nargs="?", default=".", help="raiz del proyecto (por omision la actual)")
    args = parser.parse_args(argv)
    if not args.comprobar:
        parser.print_usage(sys.stderr)
        return 2
    try:
        proyecto = cargar_proyecto(Path(args.ruta))
    except ManifiestoError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(proyecto.resumen())
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Reglas puras del overlay de codigo: variantes, configuracion, funciones, enlace y comparacion.

El juego carga en ``0x80010200`` un bloque de codigo MIPS que viaja comprimido dentro de la
seccion de tipo 2 de 76 contenedores BZZ, en tres variantes. Este modulo no toca disco ni lanza
procesos: recibe datos ya leidos y devuelve valores, textos o ``ValueError`` con el campo
ofensivo, de modo que se prueba sin entorno y las capas de extraccion y particion quedan
reducidas a ejecutar lo que aqui se decide.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

DIRECCION_CARGA = 0x80010200
"""Direccion virtual donde el cargador deja el overlay."""

FIN_HUECO = 0x80014A00
"""Primera direccion del ejecutable principal: el overlay no puede llegar hasta aqui."""

TAMANO_HUECO = FIN_HUECO - DIRECCION_CARGA
"""Bytes disponibles para el overlay entre la zona del sistema y el ejecutable."""

TIPO_SECCION_CODIGO = 2
"""Tipo de seccion BZZ que contiene el overlay."""

MASCARA_FISICA = 0x1FFFFFFF
"""Mascara que convierte una direccion de KSEG0 en desplazamiento dentro de la RAM."""

MAX_ARCHIVOS_BZZ = 512
"""Cota de contenedores que se aceptan; el disco real trae 108."""

MAX_BYTES_CONFIG = 64 * 1024
"""Cota del tamano de ``config/overlay.json``; el real mide menos de 6 KiB."""

MAX_BYTES_VOLCADO = 16 * 1024 * 1024
"""Cota del tamano de un volcado de RAM; los reales miden 2 MiB."""

OFFSETS_ENTRADA = (0x4, 0xC, 0x58, 0x28B0, 0x28E4)
"""Desplazamientos que el ejecutable invoca con ``jal`` (``0x80010204`` a ``0x80012AE4``)."""

NOMBRE_RANURA = "ranura_cargador"
"""Nombre de la palabra inicial del overlay, donde el cargador escribe un puntero."""

MAX_RANGOS_INFORMADOS = 16
"""Cota de rangos distintos que se listan al describir una comparacion con la RAM."""

_INSTRUCCION_JR_RA = 0x03E00008
_OPCODE_J = 2
_OPCODE_JAL = 3
_PREFIJO_ADDIU_SP = 0x27BD
_BIT_SIGNO_INMEDIATO = 0x8000
_TAMANO_PALABRA = 4

_PATRON_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PATRON_NOMBRE_BZZ = re.compile(r"^[A-Za-z0-9_]+(/[A-Za-z0-9_]+)*\.BZZ$")
_PATRON_ENTRADA_ENLACE = re.compile(r"^\s*(build/[A-Za-z0-9_./-]+\.s\.o)\((\.[a-z]+)\);", re.MULTILINE)
_PATRON_GLABEL = re.compile(r"^glabel\s", re.MULTILINE)
_PATRON_PALABRA = re.compile(r"^\s*(?:/\*.*?\*/\s*)?\.word\s", re.MULTILINE)
_PATRON_SIMBOLO_FUNCION = re.compile(
    r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*0x([0-9A-Fa-f]+)\s*;\s*//.*\btype:func\b", re.MULTILINE
)


@dataclass(frozen=True)
class VarianteConocida:
    """Variante del overlay documentada para la edicion soportada del juego.

    Attributes:
        identificador: Letra con la que se nombran sus archivos (``a``, ``b`` o ``c``).
        sha256: Huella esperada de la seccion descomprimida.
        tamano: Tamano esperado en bytes.
        cantidad_archivos: Contenedores BZZ que la traen.
    """

    identificador: str
    sha256: str
    tamano: int
    cantidad_archivos: int


VARIANTES_CONOCIDAS = (
    VarianteConocida("a", "3e45e436f793ec642361caf2c0d371b0d2482bb6a01f3bdbcfa5424dbbdf43d7", 17076, 48),
    VarianteConocida("b", "9b5b5e2c1a05b7f6daef69281025abff8622203976a37a33b09d976891b82491", 17072, 24),
    VarianteConocida("c", "67cbfff30aa3d00b66f04e60aac8c50f182e3bc7251d5114d859355ee8ac8538", 17080, 4),
)
"""Las tres variantes de la edicion soportada, de mayor a menor numero de contenedores."""


@dataclass(frozen=True)
class GrupoCodigo:
    """Contenedores que traen exactamente el mismo bloque de codigo.

    Attributes:
        datos: Seccion descomprimida compartida.
        archivos: Rutas relativas de los contenedores, ordenadas.
    """

    datos: bytes
    archivos: tuple[str, ...]


@dataclass(frozen=True)
class VarianteExtraida:
    """Variante tal como queda registrada en ``config/overlay.json``.

    Attributes:
        identificador: Identificador de la variante.
        sha256: Huella de la seccion descomprimida.
        tamano: Tamano en bytes.
        archivos: Rutas relativas de los contenedores BZZ que la traen, ordenadas.
    """

    identificador: str
    sha256: str
    tamano: int
    archivos: tuple[str, ...]


@dataclass(frozen=True)
class ComparacionRam:
    """Resultado de comparar una variante con el bloque equivalente de un volcado de RAM.

    Attributes:
        identificador: Variante comparada.
        tamano: Bytes comparados.
        bytes_distintos: Cantidad de bytes que difieren.
        rangos: Rangos ``[inicio, fin)`` de desplazamientos distintos, relativos al overlay.
        coincide: ``True`` si no hay diferencias salvo la ranura del cargador (primera palabra).
    """

    identificador: str
    tamano: int
    bytes_distintos: int
    rangos: tuple[tuple[int, int], ...]
    coincide: bool


def huella_sha256(datos: bytes) -> str:
    """
    Calcula el SHA-256 de unos bytes.

    Contexto:
        Clave de agrupacion de las secciones extraidas y valor de ``config/overlay.json``.

    Args:
        datos (bytes): Contenido a resumir.

    Returns:
        str: Huella en hexadecimal minusculas.

    Ejemplo:
        huella = huella_sha256(b"abc")
    """
    return hashlib.sha256(datos).hexdigest()


def validar_nombre_bzz(nombre: str) -> str:
    """
    Comprueba que un nombre relativo de contenedor es una ruta simple con ``/``.

    Contexto:
        Los nombres vienen del sistema de archivos del disco o de la imagen, que son entradas
        ajenas: se aceptan solo letras, digitos y guion bajo, sin ``..`` ni rutas absolutas.

    Args:
        nombre (str): Ruta relativa, por ejemplo ``LEVEL1/L01A.BZZ``.

    Returns:
        str: El mismo nombre si es valido.

    Raises:
        ValueError: Si el nombre no cumple el patron o supera 128 caracteres.

    Ejemplo:
        nombre = validar_nombre_bzz("LEVEL1/L01A.BZZ")
    """
    if len(nombre) > 128 or not _PATRON_NOMBRE_BZZ.match(nombre):
        raise ValueError("nombre de contenedor BZZ no valido: se esperaba CARPETA/NOMBRE.BZZ")
    return nombre


def validar_tamano_codigo(tamano: int) -> int:
    """
    Comprueba que una seccion de codigo cabe en el hueco del overlay.

    Contexto:
        Se aplica a cada seccion tipo 2 antes de agruparla: una seccion mayor que el hueco
        pisaria el ejecutable al cargarse.

    Args:
        tamano (int): Longitud descomprimida en bytes.

    Returns:
        int: El mismo tamano si es valido.

    Raises:
        ValueError: Si es cero, no es multiplo de 4 o supera ``TAMANO_HUECO``.

    Ejemplo:
        validar_tamano_codigo(17076)
    """
    if not 0 < tamano <= TAMANO_HUECO or tamano % _TAMANO_PALABRA:
        raise ValueError(
            f"tamano de la seccion de codigo={tamano}: se esperaba un multiplo de 4 entre 4 y {TAMANO_HUECO}"
        )
    return tamano


def agrupar_por_huella(secciones: Iterable[tuple[str, bytes]]) -> dict[str, GrupoCodigo]:
    """
    Agrupa las secciones de codigo por su SHA-256.

    Contexto:
        Segundo paso de ``extraer``: las 76 secciones colapsan en las variantes distintas.

    Args:
        secciones (Iterable[tuple[str, bytes]]): Pares ``(ruta del contenedor, seccion)``.

    Returns:
        dict[str, GrupoCodigo]: Un grupo por huella, con archivos ordenados; las claves se
        insertan por orden de huella para que la salida sea reproducible.

    Raises:
        ValueError: Si un nombre o un tamano no son validos o hay rutas repetidas.

    Ejemplo:
        grupos = agrupar_por_huella([("LEVEL1/L01A.BZZ", datos)])
    """
    acumulado: dict[str, tuple[bytes, list[str]]] = {}
    vistos: set[str] = set()
    for nombre, datos in secciones:
        validar_nombre_bzz(nombre)
        validar_tamano_codigo(len(datos))
        if nombre in vistos:
            raise ValueError(f"contenedor repetido: {nombre}")
        vistos.add(nombre)
        acumulado.setdefault(huella_sha256(datos), (datos, []))[1].append(nombre)
    return {
        huella: GrupoCodigo(datos, tuple(sorted(archivos)))
        for huella, (datos, archivos) in sorted(acumulado.items())
    }


def identificar_variantes(
    grupos: Mapping[str, GrupoCodigo],
    conocidas: Sequence[VarianteConocida] = VARIANTES_CONOCIDAS,
) -> tuple[list[VarianteExtraida], dict[str, bytes]]:
    """
    Asocia cada grupo con una variante conocida y exige que esten todas.

    Contexto:
        Es el valor con esperado conocido de la extraccion: huella y cantidad de contenedores
        de cada variante proceden del analisis del disco y aqui se contrastan contra lo leido.

    Args:
        grupos (Mapping[str, GrupoCodigo]): Resultado de ``agrupar_por_huella``.
        conocidas (Sequence[VarianteConocida], opcional): Variantes esperadas; por omision las
            de la edicion soportada (las pruebas inyectan variantes sinteticas).

    Returns:
        tuple[list[VarianteExtraida], dict[str, bytes]]: Las variantes en el orden de
        ``conocidas`` y los bytes de cada una por identificador.

    Raises:
        ValueError: Si hay una huella desconocida, falta una variante o su cantidad de
            contenedores no es la esperada.

    Ejemplo:
        variantes, binarios = identificar_variantes(agrupar_por_huella(secciones))
    """
    huellas = {variante.sha256 for variante in conocidas}
    for huella in grupos:
        if huella not in huellas:
            raise ValueError(f"variante desconocida del overlay: sha256={huella[:16]}")
    variantes: list[VarianteExtraida] = []
    binarios: dict[str, bytes] = {}
    for conocida in conocidas:
        grupo = grupos.get(conocida.sha256)
        if grupo is None:
            raise ValueError(f"falta la variante '{conocida.identificador}' del overlay")
        if len(grupo.archivos) != conocida.cantidad_archivos:
            raise ValueError(
                f"variante '{conocida.identificador}': {len(grupo.archivos)} contenedores, "
                f"se esperaban {conocida.cantidad_archivos}"
            )
        variantes.append(
            VarianteExtraida(conocida.identificador, conocida.sha256, len(grupo.datos), grupo.archivos)
        )
        binarios[conocida.identificador] = grupo.datos
    return variantes, binarios


def serializar_config(variantes: Sequence[VarianteExtraida]) -> str:
    """
    Genera el texto de ``config/overlay.json``.

    Contexto:
        La salida es determinista (orden de claves fijo, listas ordenadas, ASCII) para que dos
        extracciones produzcan archivos identicos.

    Args:
        variantes (Sequence[VarianteExtraida]): Variantes a registrar.

    Returns:
        str: JSON con sangria de dos espacios y salto de linea final.

    Ejemplo:
        texto = serializar_config(variantes)
    """
    datos = {
        "direccionCarga": f"0x{DIRECCION_CARGA:08X}",
        "tipoSeccion": TIPO_SECCION_CODIGO,
        "variantes": [
            {
                "id": variante.identificador,
                "sha256": variante.sha256,
                "tamano": variante.tamano,
                "archivos": list(variante.archivos),
            }
            for variante in variantes
        ],
    }
    return json.dumps(datos, indent=2, ensure_ascii=True) + "\n"


def _exigir_tipo(valor: object, tipo: type, campo: str) -> None:
    """Falla si ``valor`` no es del tipo esperado (los booleanos no cuentan como enteros)."""
    if not isinstance(valor, tipo) or (tipo is int and isinstance(valor, bool)):
        raise ValueError(f"campo '{campo}': tipo no valido")


def _variante_desde_datos(entrada: object, conocidas: Sequence[VarianteConocida]) -> VarianteExtraida:
    """Valida un elemento de la lista ``variantes`` de ``config/overlay.json``."""
    if not isinstance(entrada, dict):
        raise ValueError("campo 'variantes': cada elemento debe ser un objeto")
    identificador = entrada.get("id")
    huella = entrada.get("sha256")
    tamano = entrada.get("tamano")
    archivos = entrada.get("archivos")
    _exigir_tipo(identificador, str, "id")
    _exigir_tipo(huella, str, "sha256")
    _exigir_tipo(tamano, int, "tamano")
    _exigir_tipo(archivos, list, "archivos")
    conocida = next((v for v in conocidas if v.identificador == identificador), None)
    if conocida is None:
        raise ValueError("campo 'id': variante no reconocida")
    if not _PATRON_SHA256.match(str(huella)) or huella != conocida.sha256:
        raise ValueError(f"campo 'sha256' de la variante '{conocida.identificador}': no es el esperado")
    if tamano != conocida.tamano:
        raise ValueError(f"campo 'tamano' de la variante '{conocida.identificador}': no es el esperado")
    nombres = [validar_nombre_bzz(str(nombre)) for nombre in list(archivos or [])[:MAX_ARCHIVOS_BZZ]]
    if len(nombres) != conocida.cantidad_archivos or nombres != sorted(set(nombres)):
        raise ValueError(
            f"campo 'archivos' de la variante '{conocida.identificador}': "
            f"se esperaban {conocida.cantidad_archivos} rutas unicas y ordenadas"
        )
    return VarianteExtraida(conocida.identificador, conocida.sha256, conocida.tamano, tuple(nombres))


def variantes_desde_config(
    datos: object, conocidas: Sequence[VarianteConocida] = VARIANTES_CONOCIDAS
) -> list[VarianteExtraida]:
    """
    Valida el contenido de ``config/overlay.json``.

    Contexto:
        ``split``, ``build`` y ``verify`` leen este archivo para saber que variantes existen y
        con que huella; un archivo manipulado o de otra edicion se rechaza aqui.

    Args:
        datos (object): Resultado de ``json.loads``.
        conocidas (Sequence[VarianteConocida], opcional): Variantes esperadas; por omision las
            de la edicion soportada.

    Returns:
        list[VarianteExtraida]: Las variantes registradas, en el orden del archivo.

    Raises:
        ValueError: Si falta un campo, la direccion de carga o el tipo no son los esperados,
            una variante se repite o no coincide con las conocidas.

    Ejemplo:
        variantes = variantes_desde_config(json.loads(texto))
    """
    if not isinstance(datos, dict):
        raise ValueError("config/overlay.json debe ser un objeto")
    if datos.get("direccionCarga") != f"0x{DIRECCION_CARGA:08X}":
        raise ValueError(f"campo 'direccionCarga': se esperaba 0x{DIRECCION_CARGA:08X}")
    if datos.get("tipoSeccion") != TIPO_SECCION_CODIGO or isinstance(datos.get("tipoSeccion"), bool):
        raise ValueError(f"campo 'tipoSeccion': se esperaba {TIPO_SECCION_CODIGO}")
    lista = datos.get("variantes")
    if not isinstance(lista, list) or not 1 <= len(lista) <= len(conocidas):
        raise ValueError("campo 'variantes': se esperaba una lista no vacia de variantes conocidas")
    variantes = [_variante_desde_datos(entrada, conocidas) for entrada in lista]
    if len({variante.identificador for variante in variantes}) != len(variantes):
        raise ValueError("campo 'variantes': hay identificadores repetidos")
    return variantes


def _palabras(datos: bytes) -> tuple[int, ...]:
    """Interpreta los bytes como palabras de 32 bits little endian."""
    if len(datos) % _TAMANO_PALABRA:
        raise ValueError("el codigo debe tener una longitud multiplo de 4")
    return struct.unpack(f"<{len(datos) // _TAMANO_PALABRA}I", datos)


def _offset_de_salto(palabra: int) -> int:
    """Desplazamiento dentro del overlay al que apunta una instruccion ``j`` o ``jal``."""
    destino = ((palabra & 0x03FFFFFF) << 2) | (DIRECCION_CARGA & 0xF0000000)
    return destino - DIRECCION_CARGA


def fin_de_codigo(datos: bytes) -> int:
    """
    Calcula donde termina el codigo ejecutable del overlay.

    Contexto:
        Tras el codigo vienen la tabla de saltos y las tablas de busqueda; la ultima funcion
        cierra con ``jr ra`` y su ranura de retardo. Las tablas posteriores no contienen
        la palabra ``jr ra``, de modo que la ultima aparicion en todo el archivo delimita el codigo.

    Args:
        datos (bytes): Seccion descomprimida.

    Returns:
        int: Desplazamiento del primer byte posterior a la ranura de retardo del ultimo ``jr ra``.

    Raises:
        ValueError: Si la longitud no es multiplo de 4 o no hay ningun ``jr ra`` con ranura.

    Ejemplo:
        fin = fin_de_codigo(datos)
    """
    palabras = _palabras(datos)
    indices = [i for i, palabra in enumerate(palabras) if palabra == _INSTRUCCION_JR_RA]
    if not indices or indices[-1] + 2 > len(palabras):
        raise ValueError("el codigo no contiene ningun 'jr ra' con su ranura de retardo")
    return (indices[-1] + 2) * _TAMANO_PALABRA


def descubrir_funciones(datos: bytes) -> tuple[int, ...]:
    """
    Localiza los inicios de funcion del overlay.

    Contexto:
        Alimenta ``config/symbols_overlay.txt``. Un inicio es: el destino del ``j`` del
        desplazamiento 4, los puntos de entrada que invoca el ejecutable, todo destino de
        ``jal`` dentro del codigo y todo prologo ``addiu sp,sp,-N``. El desensamblador no
        puede deducir por si solo las entradas que nadie llama desde dentro.

    Args:
        datos (bytes): Seccion descomprimida de una variante.

    Returns:
        tuple[int, ...]: Desplazamientos ordenados y sin repetidos.

    Raises:
        ValueError: Si el codigo es demasiado corto, no empieza con el salto esperado en el
            desplazamiento 4 o algun punto de entrada cae fuera del codigo.

    Ejemplo:
        inicios = descubrir_funciones(datos)
    """
    fin = fin_de_codigo(datos)
    palabras = _palabras(datos)
    if len(palabras) < 2 or palabras[1] >> 26 != _OPCODE_J:
        raise ValueError("el desplazamiento 4 debe contener un salto 'j' al cuerpo del overlay")
    inicios = {_offset_de_salto(palabras[1])}
    for entrada in OFFSETS_ENTRADA:
        if not 0 < entrada < fin:
            raise ValueError(f"punto de entrada 0x{entrada:X} fuera del codigo (fin 0x{fin:X})")
        inicios.add(entrada)
    for indice in range(1, fin // _TAMANO_PALABRA):
        palabra = palabras[indice]
        if palabra >> 26 == _OPCODE_JAL:
            inicios.add(_offset_de_salto(palabra))
        elif palabra >> 16 == _PREFIJO_ADDIU_SP and palabra & _BIT_SIGNO_INMEDIATO:
            inicios.add(indice * _TAMANO_PALABRA)
    fuera = [inicio for inicio in inicios if not 0 < inicio < fin]
    if fuera:
        raise ValueError(f"destino de salto 0x{min(fuera):X} fuera del codigo (fin 0x{fin:X})")
    return tuple(sorted(inicios))


def nombre_funcion(offset: int) -> str:
    """
    Nombre convencional de una funcion aun sin identificar.

    Contexto:
        Misma convencion que el ejecutable: ``func_`` seguido de la direccion en mayusculas.

    Args:
        offset (int): Desplazamiento dentro del overlay.

    Returns:
        str: Por ejemplo ``func_80010204`` para el desplazamiento 4.

    Ejemplo:
        nombre = nombre_funcion(4)
    """
    return f"func_{DIRECCION_CARGA + offset:08X}"


def texto_simbolos(inicios: Sequence[int]) -> str:
    """
    Genera ``config/symbols_overlay.txt`` en formato del particionador.

    Contexto:
        Un unico archivo sirve a las tres variantes porque todos los inicios de funcion
        coinciden en direccion: las diferencias entre variantes caen dentro de cuerpos y en
        las tablas posteriores al codigo, que no llevan simbolo. La primera palabra (la ranura
        del cargador) vale cero en el archivo y se declara como una funcion de una sola
        instruccion: el desensamblador debe tratarla como texto para que el resto del codigo
        siga siendo texto, y ``nop`` ensambla a los mismos cuatro bytes de ceros.

    Args:
        inicios (Sequence[int]): Desplazamientos de inicio de funcion.

    Returns:
        str: La ranura del cargador y una linea ``nombre = direccion; // type:func`` por
        funcion, tras una cabecera.

    Ejemplo:
        texto = texto_simbolos(descubrir_funciones(datos))
    """
    cabecera = (
        "// Funciones del overlay de codigo cargado en 0x80010200.\n"
        "// Las tres variantes comparten estas direcciones; lo genera 'python -m tools.overlay simbolos'.\n"
    )
    ranura = f"{NOMBRE_RANURA} = 0x{DIRECCION_CARGA:08X}; // type:func\n"
    lineas = [f"{nombre_funcion(i)} = 0x{DIRECCION_CARGA + i:08X}; // type:func\n" for i in sorted(inicios)]
    return cabecera + ranura + "".join(lineas)


def funciones_de_simbolos(texto: str) -> list[int]:
    """
    Extrae los desplazamientos de las funciones declaradas en un archivo de simbolos.

    Contexto:
        Es la tabla de funciones contra la que ``split`` contrasta el numero de ``glabel``.

    Args:
        texto (str): Contenido de ``config/symbols_overlay.txt``.

    Returns:
        list[int]: Desplazamientos dentro del overlay, en el orden del archivo.

    Raises:
        ValueError: Si una direccion queda fuera del hueco del overlay.

    Ejemplo:
        tabla = funciones_de_simbolos(Path("config/symbols_overlay.txt").read_text())
    """
    desplazamientos = []
    for coincidencia in _PATRON_SIMBOLO_FUNCION.finditer(texto):
        offset = int(coincidencia.group(1), 16) - DIRECCION_CARGA
        if not 0 <= offset < TAMANO_HUECO:
            raise ValueError(f"simbolo 0x{DIRECCION_CARGA + offset:X} fuera del hueco del overlay")
        desplazamientos.append(offset)
    return desplazamientos


def contar_glabel(asm: str) -> int:
    """
    Cuenta las funciones que el desensamblador emitio en un archivo de ensamblador.

    Contexto:
        Cada funcion arranca con una linea ``glabel``; es el valor medible de la particion.

    Args:
        asm (str): Contenido de un ``.s`` de codigo.

    Returns:
        int: Numero de lineas ``glabel``.

    Ejemplo:
        total = contar_glabel(texto_asm)
    """
    return len(_PATRON_GLABEL.findall(asm))


def contar_palabras(asm: str) -> int:
    """
    Cuenta las directivas ``.word`` de un archivo de ensamblador.

    Contexto:
        En el texto, un ``.word`` delata una palabra que el desensamblador no pudo decodificar
        como instruccion; en los segmentos de datos son las propias tablas.

    Args:
        asm (str): Contenido de un ``.s``.

    Returns:
        int: Numero de lineas con ``.word``.

    Ejemplo:
        total = contar_palabras(texto_asm)
    """
    return len(_PATRON_PALABRA.findall(asm))


def entradas_del_enlazador(script: str) -> list[tuple[str, str]]:
    """
    Extrae del script de splat los objetos y secciones en el orden en que se enlazan.

    Contexto:
        El script lo genera el particionador; leerlo evita fijar a mano la lista de fuentes.

    Args:
        script (str): Contenido del ``.ld`` generado por splat.

    Returns:
        list[tuple[str, str]]: Pares ``(objeto, seccion)``, por ejemplo
        ``("build/overlay/a/asm/overlay/a/codigo.s.o", ".text")``.

    Ejemplo:
        entradas = entradas_del_enlazador(Path("build/overlay/a.ld").read_text())
    """
    return [(m.group(1), m.group(2)) for m in _PATRON_ENTRADA_ENLACE.finditer(script)]


def fuente_de_objeto(objeto: str, identificador: str) -> str:
    """
    Deduce el ensamblador fuente de un objeto de una variante.

    Contexto:
        ``build/overlay/a/asm/overlay/a/codigo.s.o`` proviene de ``asm/overlay/a/codigo.s``.

    Args:
        objeto (str): Ruta relativa del objeto.
        identificador (str): Variante a la que pertenece.

    Returns:
        str: Ruta relativa del ``.s``.

    Raises:
        ValueError: Si el objeto no esta dentro de la carpeta de build de la variante, no
            proviene de su carpeta de ensamblador o contiene ``..``.

    Ejemplo:
        fuente = fuente_de_objeto("build/overlay/a/asm/overlay/a/codigo.s.o", "a")
    """
    prefijo = f"build/overlay/{identificador}/"
    fuente = objeto[len(prefijo) : -len(".o")]
    if (
        not (objeto.startswith(prefijo) and objeto.endswith(".s.o"))
        or not fuente.startswith(f"asm/overlay/{identificador}/")
        or ".." in objeto.split("/")
    ):
        raise ValueError(f"objeto '{objeto}' no corresponde a un fuente de la variante '{identificador}'")
    return fuente


def generar_script_enlace(entradas: Sequence[tuple[str, str]]) -> str:
    """
    Genera el script de enlace que concatena los objetos sin alineaciones.

    Contexto:
        El script de splat alinea a 16 bytes al cambiar de seccion; en el overlay la tabla de
        saltos empieza justo donde acaba el codigo (desplazamiento ``0x2954``, no multiplo de 16)
        y esa alineacion insertaria relleno. Este script conserva el orden de splat y elimina
        toda alineacion; ``build`` comprueba despues que el binario coincide byte a byte.

    Args:
        entradas (Sequence[tuple[str, str]]): Pares ``(objeto, seccion)`` en orden de enlace.

    Returns:
        str: Texto del script para ``ld``.

    Raises:
        ValueError: Si no hay ninguna entrada.

    Ejemplo:
        script = generar_script_enlace([("build/overlay/a/asm/overlay/a/codigo.s.o", ".text")])
    """
    if not entradas:
        raise ValueError("el script de splat no referencia ningun objeto")
    cuerpo = "".join(f"        {objeto}({seccion});\n" for objeto, seccion in entradas)
    return (
        "SECTIONS\n"
        "{\n"
        f"    .overlay 0x{DIRECCION_CARGA:08X} : AT(0)\n"
        "    {\n"
        f"{cuerpo}"
        "    }\n"
        "    /DISCARD/ : { *(*); }\n"
        "}\n"
    )


def primera_diferencia(obtenido: bytes, esperado: bytes) -> int | None:
    """
    Busca el primer desplazamiento en que dos bloques difieren.

    Contexto:
        Base del mensaje ``FAIL`` de ``verify``.

    Args:
        obtenido (bytes): Binario reconstruido.
        esperado (bytes): Binario original.

    Returns:
        int | None: Desplazamiento de la primera diferencia (o la longitud del mas corto si
        uno es prefijo del otro), o ``None`` si son identicos.

    Ejemplo:
        posicion = primera_diferencia(b"ab", b"ac")
    """
    for posicion, (a, b) in enumerate(zip(obtenido, esperado, strict=False)):
        if a != b:
            return posicion
    return None if len(obtenido) == len(esperado) else min(len(obtenido), len(esperado))


def resultado_verificacion(identificador: str, obtenido: bytes, esperado: bytes) -> tuple[bool, str]:
    """
    Compara un binario reconstruido con el original y produce la linea de ``verify``.

    Contexto:
        ``OK`` y ``FAIL`` son parte del contrato de la herramienta (los usan scripts).

    Args:
        identificador (str): Variante verificada.
        obtenido (bytes): Binario reconstruido.
        esperado (bytes): Binario original.

    Returns:
        tuple[bool, str]: Si coinciden y el mensaje a imprimir.

    Ejemplo:
        coincide, mensaje = resultado_verificacion("a", b"x", b"x")
    """
    posicion = primera_diferencia(obtenido, esperado)
    if posicion is None:
        return True, f"OK {identificador} sha256={huella_sha256(esperado)} bytes={len(esperado)}"
    return False, (
        f"FAIL {identificador} primera diferencia en el desplazamiento 0x{posicion:X} "
        f"(obtenido {len(obtenido)} bytes, esperado {len(esperado)} bytes)"
    )


def _rangos_distintos(a: bytes, b: bytes) -> tuple[tuple[int, int], ...]:
    """Agrupa en rangos ``[inicio, fin)`` los desplazamientos donde dos bloques de igual tamano difieren."""
    rangos: list[tuple[int, int]] = []
    inicio: int | None = None
    for posicion, (x, y) in enumerate(zip(a, b, strict=True)):
        if x != y and inicio is None:
            inicio = posicion
        elif x == y and inicio is not None:
            rangos.append((inicio, posicion))
            inicio = None
    if inicio is not None:
        rangos.append((inicio, len(a)))
    return tuple(rangos)


def desplazamiento_en_ram(ram: bytes, tamano: int) -> int:
    """
    Calcula donde empieza el overlay dentro de un volcado de RAM.

    Contexto:
        Los volcados son de la RAM completa: el desplazamiento es la direccion sin el
        segmento KSEG0.

    Args:
        ram (bytes): Volcado completo.
        tamano (int): Tamano del bloque que se quiere leer.

    Returns:
        int: Desplazamiento del primer byte del overlay.

    Raises:
        ValueError: Si el volcado es demasiado grande o demasiado corto para contener el bloque.

    Ejemplo:
        inicio = desplazamiento_en_ram(volcado, 17076)
    """
    inicio = DIRECCION_CARGA & MASCARA_FISICA
    if len(ram) > MAX_BYTES_VOLCADO:
        raise ValueError(f"volcado de {len(ram)} bytes: supera el maximo de {MAX_BYTES_VOLCADO}")
    if len(ram) < inicio + tamano:
        raise ValueError(f"volcado de {len(ram)} bytes: demasiado corto para contener el overlay")
    return inicio


def valor_ranura(ram: bytes) -> int:
    """
    Lee la palabra que el cargador escribe en la direccion de carga.

    Contexto:
        Tras descomprimir, el cargador deja ahi un puntero (``0x8006B2F8``) que el overlay
        usa como base de sus datos; por eso el primer word de la RAM difiere del extraido.

    Args:
        ram (bytes): Volcado completo.

    Returns:
        int: Valor de 32 bits en ``0x80010200``.

    Raises:
        ValueError: Si el volcado no cubre la direccion de carga.

    Ejemplo:
        puntero = valor_ranura(volcado)
    """
    inicio = desplazamiento_en_ram(ram, _TAMANO_PALABRA)
    return int(struct.unpack_from("<I", ram, inicio)[0])


def comparar_con_ram(ram: bytes, binarios: Mapping[str, bytes]) -> list[ComparacionRam]:
    """
    Compara cada variante con el bloque equivalente de un volcado de RAM.

    Contexto:
        Permite saber que variante esta cargada en un momento dado del juego. Se acepta una
        diferencia en la primera palabra (la ranura del cargador).

    Args:
        ram (bytes): Volcado completo de la RAM.
        binarios (Mapping[str, bytes]): Bytes de cada variante por identificador.

    Returns:
        list[ComparacionRam]: Una comparacion por variante, en el orden de ``binarios``.

    Raises:
        ValueError: Si el volcado no contiene el bloque de alguna variante.

    Ejemplo:
        resultados = comparar_con_ram(volcado, {"a": datos_a})
    """
    resultados = []
    for identificador, datos in binarios.items():
        inicio = desplazamiento_en_ram(ram, len(datos))
        rangos = _rangos_distintos(ram[inicio : inicio + len(datos)], datos)
        distintos = sum(fin - desde for desde, fin in rangos)
        solo_ranura = all(fin <= _TAMANO_PALABRA for _, fin in rangos)
        resultados.append(ComparacionRam(identificador, len(datos), distintos, rangos, solo_ranura))
    return resultados


def describir_comparacion(comparacion: ComparacionRam) -> str:
    """
    Resume una comparacion con la RAM en una linea.

    Contexto:
        Salida de la orden ``ram``; lista los primeros rangos distintos para orientar.

    Args:
        comparacion (ComparacionRam): Resultado a describir.

    Returns:
        str: Linea con el veredicto, los bytes distintos y los primeros rangos.

    Ejemplo:
        print(describir_comparacion(resultado))
    """
    veredicto = "COINCIDE" if comparacion.coincide else "DIFIERE"
    rangos = ", ".join(f"0x{i:X}-0x{f:X}" for i, f in comparacion.rangos[:MAX_RANGOS_INFORMADOS])
    extra = len(comparacion.rangos) - MAX_RANGOS_INFORMADOS
    sufijo = f" y {extra} mas" if extra > 0 else ""
    detalle = f" rangos: {rangos}{sufijo}" if rangos else ""
    return (
        f"{veredicto} {comparacion.identificador} bytes={comparacion.tamano} "
        f"distintos={comparacion.bytes_distintos}{detalle}"
    )

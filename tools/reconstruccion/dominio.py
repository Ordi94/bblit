"""Reglas puras de la reconstruccion del ejecutable: cabecera PS-X EXE, comandos y verificacion.

Nada aqui toca disco ni lanza procesos. Las funciones reciben datos ya leidos y devuelven
valores, listas de argumentos o ``ValueError`` con el campo ofensivo, de modo que se prueban
sin entorno y la capa de infraestructura queda reducida a ejecutar lo que este modulo decide.
"""

from __future__ import annotations

import re
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

TAMANO_CABECERA = 0x800
MAGIA_PSX_EXE = b"PS-X EXE"
OFFSET_REGION = 0x4C
MAX_U32 = 0xFFFFFFFF
_CAMPOS_NUMERICOS = (
    "pc0",
    "gp0",
    "t_addr",
    "t_size",
    "d_addr",
    "d_size",
    "b_addr",
    "b_size",
    "s_addr",
    "s_size",
)
_PATRON_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PATRON_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_PATRON_NOMBRE_EXE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,31}$")
_PATRON_OBJETO = re.compile(r"^\s*(build/[A-Za-z0-9_./-]+\.o)\(", re.MULTILINE)


@dataclass(frozen=True)
class CabeceraPsx:
    """Campos de la cabecera de un ejecutable PS-X EXE.

    Attributes:
        pc0: Direccion de la primera instruccion ejecutada.
        gp0: Valor inicial del registro ``gp``.
        t_addr: Direccion de carga del segmento de texto.
        t_size: Tamano en bytes del segmento cargado (el cuerpo del archivo).
        d_addr: Direccion del bloque de datos separado (0 si no existe).
        d_size: Tamano del bloque de datos separado.
        b_addr: Direccion inicial de la zona de ceros (bss).
        b_size: Tamano de la zona de ceros.
        s_addr: Valor inicial del puntero de pila.
        s_size: Desplazamiento sumado al puntero de pila.
        region: Cadena de region que muestra la BIOS.
    """

    pc0: int
    gp0: int
    t_addr: int
    t_size: int
    d_addr: int
    d_size: int
    b_addr: int
    b_size: int
    s_addr: int
    s_size: int
    region: str


@dataclass(frozen=True)
class EjecutableReferencia:
    """Descripcion del ejecutable original que se reconstruye.

    Attributes:
        nombre: Nombre del archivo en el disco (``SLUS_008.38``).
        sha256: Huella esperada del ejecutable completo.
        sha1: Huella SHA-1 que splat comprueba antes de particionar.
        tamano: Tamano total esperado en bytes.
        cabecera: Campos de la cabecera PS-X EXE.
    """

    nombre: str
    sha256: str
    sha1: str
    tamano: int
    cabecera: CabeceraPsx


def _entero_u32(valor: object, campo: str) -> int:
    """Convierte ``"0x..."`` o un entero a u32 validando el rango."""
    if isinstance(valor, bool):
        raise ValueError(f"campo '{campo}': se esperaba un numero")
    if isinstance(valor, str):
        try:
            numero = int(valor, 16) if valor.lower().startswith("0x") else int(valor)
        except ValueError:
            raise ValueError(f"campo '{campo}': numero no valido") from None
    elif isinstance(valor, int):
        numero = valor
    else:
        raise ValueError(f"campo '{campo}': se esperaba un numero")
    if not 0 <= numero <= MAX_U32:
        raise ValueError(f"campo '{campo}': fuera del rango de 32 bits sin signo")
    return numero


def cabecera_desde_datos(datos: object) -> CabeceraPsx:
    """
    Construye una cabecera validando cada campo de un objeto JSON.

    Contexto:
        Lee el bloque ``cabecera`` de ``config/ejecutable.json``.

    Args:
        datos (object): Objeto con los diez campos numericos y ``region``.

    Returns:
        CabeceraPsx: Cabecera validada.

    Raises:
        ValueError: Si falta un campo, un numero esta fuera de 32 bits o la region no es ASCII
            o no cabe entre el desplazamiento 0x4C y el final de la cabecera.

    Ejemplo:
        cabecera = cabecera_desde_datos({"pc0": "0x80014A08", ...})
    """
    if not isinstance(datos, dict):
        raise ValueError("la cabecera debe ser un objeto")
    numeros = {campo: _entero_u32(datos.get(campo), campo) for campo in _CAMPOS_NUMERICOS}
    region = datos.get("region")
    if not isinstance(region, str) or not region.isascii() or "\x00" in region:
        raise ValueError("campo 'region': debe ser texto ASCII sin nulos")
    if len(region) >= TAMANO_CABECERA - OFFSET_REGION:
        raise ValueError("campo 'region': no cabe en la cabecera")
    return CabeceraPsx(region=region, **numeros)


def referencia_desde_datos(datos: object) -> EjecutableReferencia:
    """
    Valida el contenido de ``config/ejecutable.json``.

    Contexto:
        Es la fuente unica de los hechos del ejecutable: huella, tamano y cabecera.

    Args:
        datos (object): Resultado de ``json.load``.

    Returns:
        EjecutableReferencia: Referencia validada.

    Raises:
        ValueError: Si falta algun campo, las huellas no tienen el formato esperado, el nombre
            no es un nombre de archivo simple o el tamano no cuadra con cabecera y cuerpo.

    Ejemplo:
        referencia = referencia_desde_datos(json.loads(texto))
    """
    if not isinstance(datos, dict):
        raise ValueError("la descripcion del ejecutable debe ser un objeto")
    nombre = datos.get("nombre")
    sha256 = datos.get("sha256")
    sha1 = datos.get("sha1")
    if not isinstance(nombre, str) or not _PATRON_NOMBRE_EXE.match(nombre):
        raise ValueError("campo 'nombre': debe ser un nombre de archivo simple")
    if not isinstance(sha256, str) or not _PATRON_SHA256.match(sha256):
        raise ValueError("campo 'sha256': debe tener 64 digitos hexadecimales en minusculas")
    if not isinstance(sha1, str) or not _PATRON_SHA1.match(sha1):
        raise ValueError("campo 'sha1': debe tener 40 digitos hexadecimales en minusculas")
    tamano = _entero_u32(datos.get("tamano"), "tamano")
    cabecera = cabecera_desde_datos(datos.get("cabecera"))
    if tamano != TAMANO_CABECERA + cabecera.t_size:
        raise ValueError("campo 'tamano': no coincide con la cabecera (0x800 + t_size)")
    return EjecutableReferencia(nombre, sha256, sha1, tamano, cabecera)


def serializar_cabecera(cabecera: CabeceraPsx) -> bytes:
    """
    Genera los 0x800 bytes de la cabecera PS-X EXE.

    Contexto:
        El enlazador solo produce el cuerpo cargable; la cabecera se regenera aqui con los
        campos exactos, incluida la cadena de region y el relleno de ceros hasta 0x800.

    Args:
        cabecera (CabeceraPsx): Campos a escribir.

    Returns:
        bytes: Cabecera de exactamente ``TAMANO_CABECERA`` bytes.

    Ejemplo:
        datos = serializar_cabecera(referencia.cabecera)
    """
    campos = struct.pack(
        "<10I",
        cabecera.pc0,
        cabecera.gp0,
        cabecera.t_addr,
        cabecera.t_size,
        cabecera.d_addr,
        cabecera.d_size,
        cabecera.b_addr,
        cabecera.b_size,
        cabecera.s_addr,
        cabecera.s_size,
    )
    bloque = bytearray(TAMANO_CABECERA)
    bloque[0 : len(MAGIA_PSX_EXE)] = MAGIA_PSX_EXE
    bloque[0x10 : 0x10 + len(campos)] = campos
    region = cabecera.region.encode("ascii")
    bloque[OFFSET_REGION : OFFSET_REGION + len(region)] = region
    return bytes(bloque)


def leer_cabecera(datos: bytes) -> CabeceraPsx:
    """
    Interpreta la cabecera de un ejecutable PS-X EXE existente.

    Contexto:
        Permite comparar campo a campo la cabecera generada con la del original cuando una
        verificacion falla.

    Args:
        datos (bytes): Contenido del ejecutable (al menos la cabecera).

    Returns:
        CabeceraPsx: Campos leidos.

    Raises:
        ValueError: Si es mas corto que la cabecera o la magia no es ``PS-X EXE``.

    Ejemplo:
        cabecera = leer_cabecera(ruta.read_bytes())
    """
    if len(datos) < TAMANO_CABECERA or datos[: len(MAGIA_PSX_EXE)] != MAGIA_PSX_EXE:
        raise ValueError("el archivo no tiene una cabecera PS-X EXE valida")
    campos = struct.unpack_from("<10I", datos, 0x10)
    region = datos[OFFSET_REGION:TAMANO_CABECERA].split(b"\x00", 1)[0].decode("ascii", errors="replace")
    return CabeceraPsx(
        campos[0],
        campos[1],
        campos[2],
        campos[3],
        campos[4],
        campos[5],
        campos[6],
        campos[7],
        campos[8],
        campos[9],
        region,
    )


def ensamblar_ejecutable(cabecera: CabeceraPsx, cuerpo: bytes) -> bytes:
    """
    Une la cabecera regenerada con el cuerpo enlazado.

    Contexto:
        Ultimo paso de ``build``: el resultado es el archivo que se compara por hash.

    Args:
        cabecera (CabeceraPsx): Campos de la cabecera.
        cuerpo (bytes): Imagen binaria producida por el enlazador.

    Returns:
        bytes: Ejecutable completo.

    Raises:
        ValueError: Si la longitud del cuerpo difiere de ``t_size``.

    Ejemplo:
        ejecutable = ensamblar_ejecutable(referencia.cabecera, cuerpo)
    """
    if len(cuerpo) != cabecera.t_size:
        raise ValueError(
            f"el cuerpo enlazado mide {len(cuerpo)} bytes y la cabecera declara t_size={cabecera.t_size}"
        )
    return serializar_cabecera(cabecera) + cuerpo


def describir_diferencia(obtenido: bytes, esperado: bytes) -> str:
    """
    Resume donde difieren dos ejecutables sin volcar su contenido.

    Contexto:
        Acompana al mensaje ``FAIL`` de ``verify`` para orientar la depuracion.

    Args:
        obtenido (bytes): Ejecutable reconstruido.
        esperado (bytes): Ejecutable original.

    Returns:
        str: Descripcion con el primer desplazamiento distinto y la zona (cabecera o cuerpo),
        o la diferencia de tamano si una es prefijo de la otra.

    Ejemplo:
        print(describir_diferencia(a, b))
    """
    limite = min(len(obtenido), len(esperado))
    for posicion in range(limite):
        if obtenido[posicion] != esperado[posicion]:
            zona = "cabecera" if posicion < TAMANO_CABECERA else "cuerpo"
            return f"primera diferencia en el desplazamiento 0x{posicion:X} ({zona})"
    if len(obtenido) != len(esperado):
        return f"tamanos distintos: {len(obtenido)} y {len(esperado)} bytes"
    return "sin diferencias"


def resultado_verificacion(obtenido: str, esperado: str) -> tuple[bool, str]:
    """
    Compara dos huellas y produce la linea que imprime ``verify``.

    Contexto:
        ``OK`` y ``FAIL`` son parte del contrato de la herramienta (los usan scripts).

    Args:
        obtenido (str): SHA-256 del ejecutable reconstruido.
        esperado (str): SHA-256 del ejecutable original.

    Returns:
        tuple[bool, str]: Si coinciden y el mensaje; ambos casos nombran las dos huellas.

    Ejemplo:
        coincide, mensaje = resultado_verificacion(a, b)
    """
    estado = "OK" if obtenido == esperado else "FAIL"
    return obtenido == esperado, f"{estado} esperado={esperado} obtenido={obtenido}"


def texto_simbolos_entrada(pc0: int, simbolos_existentes: str) -> str:
    """
    Genera el simbolo de la funcion de entrada si nadie lo declaro.

    Contexto:
        La direccion de entrada (``pc0``) no es destino de ningun ``jal``, asi que el
        desensamblador no la reconoce como inicio de funcion y trata como datos todo lo que
        la sigue. Declararla basta para que detecte las demas funciones a partir de ``jr ra``.

    Args:
        pc0 (int): Direccion de entrada del ejecutable.
        simbolos_existentes (str): Contenido de ``config/symbols.txt`` (vacio si no existe).

    Returns:
        str: Linea de simbolo en formato splat, o cadena vacia si la direccion ya figura.

    Ejemplo:
        texto = texto_simbolos_entrada(0x80014A08, "")
    """
    patron = re.compile(rf"=\s*0x0*{pc0:X}\s*;", re.IGNORECASE)
    if patron.search(simbolos_existentes):
        return ""
    return f"func_{pc0:08X} = 0x{pc0:08X}; // type:func\n"


def objetos_del_enlazador(script: str) -> list[str]:
    """
    Extrae, sin repetidos y en orden, los objetos que referencia el script del enlazador.

    Contexto:
        El script lo genera el particionador; leerlo evita fijar a mano la lista de fuentes
        y hace que nuevos segmentos entren en la construccion sin tocar este codigo.

    Args:
        script (str): Contenido del script ``.ld``.

    Returns:
        list[str]: Rutas de objeto relativas (``build/asm/text.s.o``).

    Ejemplo:
        objetos = objetos_del_enlazador(texto_ld)
    """
    vistos: dict[str, None] = {}
    for coincidencia in _PATRON_OBJETO.finditer(script):
        vistos.setdefault(coincidencia.group(1))
    return list(vistos)


def fuente_de_objeto(objeto: str) -> str:
    """
    Deduce la ruta del ensamblador fuente de un objeto.

    Contexto:
        ``build/asm/text.s.o`` proviene de ``asm/text.s``.

    Args:
        objeto (str): Ruta relativa del objeto.

    Returns:
        str: Ruta relativa del ``.s``.

    Raises:
        ValueError: Si el objeto no sigue el patron ``build/<ruta>.s.o``.

    Ejemplo:
        fuente = fuente_de_objeto("build/asm/text.s.o")
    """
    if not (objeto.startswith("build/") and objeto.endswith(".s.o")) or ".." in objeto.split("/"):
        raise ValueError(f"objeto '{objeto}' no corresponde a un ensamblador fuente conocido")
    return objeto[len("build/") : -len(".o")]


def comando_splat(python: str, configuracion: str) -> list[str]:
    """Devuelve los argumentos que ejecutan el particionador con la configuracion dada."""
    return [python, "-X", "utf8", "-m", "splat", "split", configuracion]


def comando_ensamblar(ensamblador: Path, fuente: str, objeto: str, incluir: str) -> list[str]:
    """
    Devuelve los argumentos para ensamblar un archivo para R3000 little-endian.

    Contexto:
        ``-march=r3000 -mips1`` fija el repertorio de la consola y ``-G0`` evita acceso
        relativo a ``gp`` (la cabecera declara ``gp0 = 0``).

    Args:
        ensamblador (Path): Ruta de ``mipsel-none-elf-as``.
        fuente (str): Archivo ``.s`` de entrada.
        objeto (str): Archivo ``.o`` de salida.
        incluir (str): Carpeta donde estan las macros incluidas por el ensamblador.

    Returns:
        list[str]: Lista de argumentos lista para ``subprocess`` (sin shell).

    Ejemplo:
        comando = comando_ensamblar(Path("as.exe"), "asm/text.s", "build/asm/text.s.o", "asm/include")
    """
    return [str(ensamblador), "-EL", "-march=r3000", "-mips1", "-G0", "-I", incluir, "-o", objeto, fuente]


def comando_enlazar(enlazador: Path, scripts: Sequence[str], elf: str, mapa: str) -> list[str]:
    """
    Devuelve los argumentos para enlazar con el script del particionador.

    Contexto:
        El primer script define las secciones; los siguientes aportan simbolos absolutos.

    Args:
        enlazador (Path): Ruta de ``mipsel-none-elf-ld``.
        scripts (Sequence[str]): Scripts en orden (``-T`` por cada uno).
        elf (str): Salida ELF.
        mapa (str): Archivo de mapa de enlace.

    Returns:
        list[str]: Lista de argumentos.

    Ejemplo:
        comando = comando_enlazar(Path("ld.exe"), ["a.ld"], "build/a.elf", "build/a.map")
    """
    comando = [str(enlazador), "-EL", "--no-warn-rwx-segments"]
    for script in scripts:
        comando += ["-T", script]
    return [*comando, "-o", elf, "-Map", mapa]


def comando_objcopy(objcopy: Path, elf: str, binario: str) -> list[str]:
    """Devuelve los argumentos que extraen la imagen binaria plana de un ELF."""
    return [str(objcopy), "-O", "binary", elf, binario]

"""Reglas puras de la reconstruccion del ejecutable: cabecera PS-X EXE, comandos y verificacion.

Nada aqui toca disco ni lanza procesos. Las funciones reciben datos ya leidos y devuelven
valores, listas de argumentos o ``ValueError`` con el campo ofensivo, de modo que se prueban
sin entorno y la capa de infraestructura queda reducida a ejecutar lo que este modulo decide.
"""

from __future__ import annotations

import re
import struct
from collections.abc import Mapping, Sequence
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
    Deduce la ruta del fuente (ensamblador o C) de un objeto.

    Contexto:
        ``build/asm/boot.s.o`` proviene de ``asm/boot.s`` y ``build/src/a.c.o`` de ``src/a.c``.

    Args:
        objeto (str): Ruta relativa del objeto.

    Returns:
        str: Ruta relativa del ``.s`` o del ``.c``.

    Raises:
        ValueError: Si el objeto no sigue el patron ``build/<ruta>.s.o`` o ``build/<ruta>.c.o``.

    Ejemplo:
        fuente = fuente_de_objeto("build/asm/boot.s.o")
    """
    valido = objeto.startswith("build/") and objeto.endswith((".s.o", ".c.o"))
    if not valido or ".." in objeto.split("/"):
        raise ValueError(
            f"objeto '{objeto}' no corresponde a un ensamblador fuente conocido ni a un archivo C "
            "(build/<ruta>.s.o o build/<ruta>.c.o)"
        )
    return objeto[len("build/") : -len(".o")]


MAX_VALOR_G = 64
_CLAVES_OPCIONES = frozenset({"g"})
_PATRON_ARCHIVO_C = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_PATRON_DATO_PEQUENO = re.compile(r"^D_[0-9A-F]{8}$")
_PATRON_FUNCION_SIMBOLO = re.compile(r"^([A-Za-z_]\w*)\s*=\s*0x([0-9A-Fa-f]{1,8})\s*;\s*//(.*)$")


def valor_gp(datos: object) -> int | None:
    """
    Lee el valor del registro ``$gp`` que declara ``config/opciones_compilacion.toml``.

    Contexto:
        El juego fija ``$gp`` en su arranque (``lui gp,0x8007 ; addiu gp,gp,-0x6CE0``) y accede a
        los datos pequenos con ``desplazamiento($gp)``. El enlazador necesita el simbolo ``_gp``
        con ese valor para resolver las referencias relativas a ``$gp`` de los objetos C; es un
        simbolo absoluto y no cambia ningun byte si ningun objeto lo referencia.

    Args:
        datos (object): Resultado de ``tomllib.loads``; tabla opcional ``enlace`` con la clave ``gp``.

    Returns:
        int | None: Valor de ``_gp``, o ``None`` si no se declara.

    Raises:
        ValueError: Si la forma no es la esperada o ``gp`` no es un entero de 32 bits alineado a 4.

    Ejemplo:
        gp = valor_gp({"enlace": {"gp": 0x80069320}})
    """
    if not isinstance(datos, dict):
        raise ValueError("opciones de compilacion: se esperaba una tabla")
    enlace = datos.get("enlace")
    if enlace is None:
        return None
    if not isinstance(enlace, dict) or set(enlace) - {"gp"}:
        raise ValueError("opciones de compilacion: 'enlace' solo admite la clave 'gp'")
    gp = enlace.get("gp")
    if isinstance(gp, bool) or not isinstance(gp, int) or not 0 < gp <= MAX_U32 or gp % 4:
        raise ValueError("opciones de compilacion: 'enlace.gp' debe ser un entero de 32 bits multiplo de 4")
    return gp


def direcciones_de_funciones(texto: str) -> dict[str, int]:
    """
    Extrae la direccion de cada funcion de un archivo de simbolos de splat.

    Contexto:
        ``diff`` necesita la direccion de la funcion en el ejecutable para enlazar su candidato
        en el mismo sitio y comparar los bytes.

    Args:
        texto (str): Contenido de ``config/symbols.txt``.

    Returns:
        dict[str, int]: Direccion por nombre; las lineas que no son funciones se ignoran.

    Ejemplo:
        direcciones = direcciones_de_funciones("f = 0x80014AC4; // type:func size:0x10")
    """
    direcciones: dict[str, int] = {}
    for linea in texto.splitlines():
        coincidencia = _PATRON_FUNCION_SIMBOLO.match(linea.strip())
        if coincidencia is not None and "type:func" in coincidencia.group(3):
            direcciones[coincidencia.group(1)] = int(coincidencia.group(2), 16)
    return direcciones


_PATRON_TIPO_SIMBOLO = re.compile(r"\btype:(\w+)")


@dataclass(frozen=True)
class SimboloDeclarado:
    """Simbolo de ``config/symbols.txt`` visto desde su direccion.

    Attributes:
        nombre: Nombre del simbolo.
        tipo: Valor de ``type:`` (``func``, ``u32``...); vacio si la linea no lo declara.
    """

    nombre: str
    tipo: str


def simbolos_declarados(texto: str) -> dict[int, list[SimboloDeclarado]]:
    """
    Agrupa por direccion los simbolos de un archivo de simbolos de splat.

    Contexto:
        Base de la comprobacion de ``[datos_pequenos]``: permite saber que declara
        ``config/symbols.txt`` en la direccion de cada clave del toml. Se leen funciones y datos;
        las lineas de comentario o sin forma ``nombre = 0x...; // ...`` se ignoran.

    Args:
        texto (str): Contenido de ``config/symbols.txt``.

    Returns:
        dict[int, list[SimboloDeclarado]]: Simbolos por direccion, en el orden del archivo.

    Ejemplo:
        declarados = simbolos_declarados("D_80069330 = 0x80069330; // type:u8 size:0x8")
    """
    declarados: dict[int, list[SimboloDeclarado]] = {}
    for linea in texto.splitlines():
        coincidencia = _PATRON_FUNCION_SIMBOLO.match(linea.strip())
        if coincidencia is None:
            continue
        tipo = _PATRON_TIPO_SIMBOLO.search(coincidencia.group(3))
        simbolo = SimboloDeclarado(coincidencia.group(1), tipo.group(1) if tipo else "")
        declarados.setdefault(int(coincidencia.group(2), 16), []).append(simbolo)
    return declarados


def avisos_datos_pequenos(
    datos: Mapping[str, int], declarados: Mapping[int, Sequence[SimboloDeclarado]]
) -> list[str]:
    """
    Avisa de las claves de ``[datos_pequenos]`` cuya direccion ya declara ``config/symbols.txt``.

    Contexto:
        El toml da nombre y direccion a los datos que el codigo direcciona por ``$gp`` hasta que la
        tabla de simbolos los declare; en cuanto esta los declara, la clave sobra o, peor, puede
        contradecirla. La comprobacion solo informa: no cambia ningun archivo ni el resultado de
        la construccion. Tres casos: mismo nombre y tipo de dato (la clave puede retirarse), otro
        nombre en esa direccion o el mismo nombre declarado como funcion (otro tipo).

    Args:
        datos (Mapping[str, int]): Tabla ``datos_pequenos`` del toml (nombre a direccion).
        declarados (Mapping[int, Sequence[SimboloDeclarado]]): Resultado de ``simbolos_declarados``.

    Returns:
        list[str]: Un aviso por cada simbolo repetido, en el orden de las claves del toml.

    Ejemplo:
        avisos = avisos_datos_pequenos({"D_800694A8": 0x800694A8}, simbolos_declarados(texto))
    """
    avisos: list[str] = []
    for nombre, direccion in datos.items():
        for existente in declarados.get(direccion, ()):
            if existente.nombre != nombre:
                motivo = f"otro nombre: config/symbols.txt declara {existente.nombre} en esa direccion"
            elif existente.tipo == "func":
                motivo = "otro tipo: config/symbols.txt lo declara como funcion"
            else:
                motivo = "mismo nombre: ya figura en config/symbols.txt, la clave puede retirarse"
            avisos.append(f"[datos_pequenos] {nombre} = 0x{direccion:08X}: {motivo}")
    return avisos


def datos_pequenos(datos: object) -> dict[str, int]:
    """
    Lee la tabla ``datos_pequenos`` de ``config/opciones_compilacion.toml``.

    Contexto:
        Un archivo C que accede a una variable pequena con ``desplazamiento($gp)`` la declara como
        definicion tentativa (``s32 D_800694A8;``): ``maspsx`` la emite como simbolo comun y
        reescribe sus accesos a ``$gp``. El enlace debe fijar la direccion real de esos simbolos
        (el ejecutable original no los nombra porque su codigo los direcciona por desplazamiento);
        esta tabla da nombre y direccion a cada uno hasta que ``config/symbols.txt`` los declare.

    Args:
        datos (object): Resultado de ``tomllib.loads``; tabla opcional ``datos_pequenos`` con
            ``NOMBRE = direccion``.

    Returns:
        dict[str, int]: Direccion por nombre de simbolo.

    Raises:
        ValueError: Si la forma no es la esperada, un nombre no es un identificador ``D_<direccion>``
            o la direccion no es un entero de 32 bits.

    Ejemplo:
        simbolos = datos_pequenos({"datos_pequenos": {"D_800694A8": 0x800694A8}})
    """
    if not isinstance(datos, dict):
        raise ValueError("opciones de compilacion: se esperaba una tabla")
    tabla = datos.get("datos_pequenos", {})
    if not isinstance(tabla, dict):
        raise ValueError("opciones de compilacion: 'datos_pequenos' debe ser una tabla")
    simbolos: dict[str, int] = {}
    for nombre, direccion in tabla.items():
        if not _PATRON_DATO_PEQUENO.match(nombre):
            raise ValueError(f"opciones de compilacion: simbolo '{nombre}' no valido (se espera D_XXXXXXXX)")
        if isinstance(direccion, bool) or not isinstance(direccion, int) or not 0 < direccion <= MAX_U32:
            raise ValueError(f"opciones de compilacion: direccion de '{nombre}' no valida")
        if int(nombre[2:], 16) != direccion:
            raise ValueError(f"opciones de compilacion: '{nombre}' no coincide con su direccion")
        simbolos[nombre] = direccion
    return simbolos


def texto_gp_ld(gp: int, simbolos: dict[str, int] | None = None) -> str:
    """
    Genera el fragmento de script del enlazador que define ``_gp``.

    Contexto:
        ``build`` lo escribe en ``build/gp.ld`` y lo pasa al enlazador despues del script principal.

    Args:
        gp (int): Valor de ``_gp``.
        simbolos (dict[str, int], opcional): Datos pequenos a los que dar direccion
            (``datos_pequenos``).

    Returns:
        str: Lineas de asignacion para el enlazador.

    Ejemplo:
        texto = texto_gp_ld(0x80069320)
    """
    lineas = [f"_gp = 0x{gp:08X};\n"]
    lineas += [f"{nombre} = 0x{direccion:08X};\n" for nombre, direccion in sorted((simbolos or {}).items())]
    return "".join(lineas)


def valores_g_por_archivo(datos: object) -> dict[str, int]:
    """
    Valida el contenido de ``config/opciones_compilacion.toml`` y devuelve el ``-G`` de cada archivo.

    Contexto:
        El umbral de datos pequenos (``-G``) del compilador cambia como se emiten las variables
        externas pequenas (acceso simbolico en lugar de ``lui`` mas desplazamiento). Los archivos
        originales no usaron todos el mismo valor, asi que se declara por archivo; los que no
        figuran usan ``-G0``. Entrada no confiable: solo se admiten claves conocidas, nombres de
        archivo simples y enteros entre 0 y ``MAX_VALOR_G``.

    Args:
        datos (object): Resultado de ``tomllib.loads``; tabla ``archivos`` con una subtabla por
            archivo C (nombre sin ``src/`` ni ``.c``) y la clave ``g``.

    Returns:
        dict[str, int]: Valor de ``-G`` por nombre de archivo (solo los declarados).

    Raises:
        ValueError: Si la forma no es la esperada, un nombre no es valido, hay una clave
            desconocida o ``g`` no es un entero en rango; el mensaje nombra el campo.

    Ejemplo:
        valores = valores_g_por_archivo({"archivos": {"camara_y_bucle_logico": {"g": 8}}})
    """
    if not isinstance(datos, dict) or set(datos) - {"archivos", "enlace", "datos_pequenos"}:
        raise ValueError(
            "opciones de compilacion: solo se admiten las tablas 'archivos', 'enlace' y 'datos_pequenos'"
        )
    tabla = datos.get("archivos", {})
    if not isinstance(tabla, dict):
        raise ValueError("opciones de compilacion: 'archivos' debe ser una tabla")
    valores: dict[str, int] = {}
    for nombre, opciones in tabla.items():
        if not _PATRON_ARCHIVO_C.match(nombre) or not isinstance(opciones, dict):
            raise ValueError(f"opciones de compilacion: archivo '{nombre}' no valido")
        desconocidas = set(opciones) - _CLAVES_OPCIONES
        if desconocidas:
            raise ValueError(
                f"opciones de compilacion: '{nombre}' tiene la clave desconocida '{min(desconocidas)}'"
            )
        valor = opciones.get("g", 0)
        if isinstance(valor, bool) or not isinstance(valor, int) or not 0 <= valor <= MAX_VALOR_G:
            raise ValueError(
                f"opciones de compilacion: '{nombre}.g' debe ser un entero entre 0 y {MAX_VALOR_G}"
            )
        valores[nombre] = valor
    return valores


_SECCION_ELF_DE_TIPO = {".rodata": ".rodata", ".rdata": ".rodata", ".data": ".data"}


def secciones_declaradas(configuracion: object) -> dict[str, frozenset[str]]:
    """
    Deduce que secciones puede generar el objeto de cada archivo C segun la particion.

    Contexto:
        El script del enlazador solo recoge de un objeto C las secciones que la particion le
        asigna: ``.text`` siempre, y ``.rodata`` o ``.data`` si existe un subsegmento de ese
        tipo (con punto: ``.rodata``) y el mismo nombre que el ``c``. Cualquier otra seccion con
        contenido se perderia en silencio o iria a un lugar distinto del original.

    Args:
        configuracion (object): Contenido cargado de ``config/splat.yaml``.

    Returns:
        dict[str, frozenset[str]]: Nombre del archivo C (sin ``src/`` ni ``.c``) y las secciones
        ELF permitidas (``.text`` y, si procede, ``.rodata`` y ``.data``).

    Raises:
        ValueError: Si la configuracion no tiene la forma ``segments[0].subsegments`` con
            entradas ``[inicio, tipo, nombre]`` o con claves ``type`` y ``name``.

    Ejemplo:
        declaradas = secciones_declaradas(yaml.safe_load(texto))
    """
    segmentos = configuracion.get("segments") if isinstance(configuracion, dict) else None
    principal = segmentos[0] if isinstance(segmentos, list) and segmentos else None
    subsegmentos = principal.get("subsegments") if isinstance(principal, dict) else None
    if not isinstance(subsegmentos, list):
        raise ValueError("splat.yaml: falta segments[0].subsegments")
    pares: list[tuple[str, str]] = []
    for entrada in subsegmentos:
        if isinstance(entrada, list) and len(entrada) >= 3:
            tipo, nombre = entrada[1], entrada[2]
        elif isinstance(entrada, dict):
            tipo, nombre = entrada.get("type"), entrada.get("name")
        else:
            continue
        if isinstance(tipo, str) and isinstance(nombre, str):
            pares.append((tipo, nombre))
    declaradas: dict[str, set[str]] = {nombre: {".text"} for tipo, nombre in pares if tipo == "c"}
    for tipo, nombre in pares:
        if tipo in _SECCION_ELF_DE_TIPO and nombre in declaradas:
            declaradas[nombre].add(_SECCION_ELF_DE_TIPO[tipo])
    return {nombre: frozenset(secciones) for nombre, secciones in declaradas.items()}


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


_PATRON_FUNCION_LOCAL = re.compile(r"^\s*glabel\s+\.L([0-9A-Fa-f]{8})\s*$", re.MULTILINE)


def funciones_con_nombre_local(texto_asm: str) -> frozenset[str]:
    """
    Busca las funciones que el particionador bautizo como etiqueta local (``.L<direccion>``).

    Contexto:
        Cuando otra funcion salta con ``j`` a la direccion de inicio de una funcion que la tabla
        de simbolos no nombra, ``splat`` la trata como etiqueta local y la llama ``.L80044904``: un
        nombre que no es un identificador de C y que, como nombre de archivo, empieza por punto.
        Las etiquetas locales genuinas de dentro de una funcion no se declaran con ``glabel``, asi
        que solo se consideran las que si lo hacen. ``split`` las renombra a ``func_<direccion>``.

    Args:
        texto_asm (str): Contenido de un archivo ``.s`` generado por el particionador.

    Returns:
        frozenset[str]: Nombres con punto inicial (``.L80044904``) declarados con ``glabel``.

    Ejemplo:
        nombres = funciones_con_nombre_local(texto_del_asm)
    """
    return frozenset(f".L{direccion}" for direccion in _PATRON_FUNCION_LOCAL.findall(texto_asm))


def renombrar_funciones_locales(texto: str, nombres: frozenset[str]) -> str:
    """
    Sustituye cada nombre ``.L<direccion>`` de ``nombres`` por ``func_<direccion>``.

    Contexto:
        Segunda mitad del saneo de ``split``: se aplica a todos los ``.s`` (definicion y saltos que
        la referencian) y a los esqueletos ``.c``. Solo toca los nombres indicados, de modo que las
        etiquetas locales de dentro de una funcion no cambian.

    Args:
        texto (str): Contenido de un ``.s`` o ``.c``.
        nombres (frozenset[str]): Nombres a sustituir, de ``funciones_con_nombre_local``.

    Returns:
        str: Texto con los nombres sustituidos.

    Ejemplo:
        nuevo = renombrar_funciones_locales("j .L80044904", frozenset({".L80044904"}))
    """
    if not nombres:
        return texto

    def sustituir(coincidencia: re.Match[str]) -> str:
        nombre = coincidencia.group(0)
        return f"func_{nombre[2:]}" if nombre in nombres else nombre

    return re.sub(r"\.L[0-9A-Fa-f]{8}(?![0-9A-Za-z_])", sustituir, texto)

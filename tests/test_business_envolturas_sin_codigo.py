"""Las referencias sin codigo deben estar declaradas y contadas.

Se admiten cuatro formas que no generan ninguna instruccion y que solo mueven el reparto de registros del
compilador: la envoltura ``do { ... } while (0)``, el par ``x--; x++;``, la condicion vacia ``if (x) {}`` y la
local sin uso con inicializador. La tecnica solo se admite con condiciones: el comentario de cabecera de la
funcion dice que la referencia no genera codigo y cierra el parrafo con una oracion fija que reconoce que se
desconoce la forma del fuente original, y ``docs/DESCOMPILACION.md`` lista cada funcion con su forma y su
numero de referencias. Estas pruebas cruzan ``src/`` con esa tabla para que una referencia nueva no entre sin
su comentario ni sin su fila, y para que una fila no sobreviva a la referencia que describia. Solo leen
archivos.
"""

import re
from pathlib import Path

from tools.proyecto import RAIZ_REPOSITORIO

FRASE_FIJA = "La forma del fuente original que producia este reparto se desconoce."
MARCADORES_SIN_CODIGO = ("no genera codigo", "no generan codigo")

ENVOLTURA = "envoltura"
DECREMENTO_INCREMENTO = "decremento-incremento"
CONDICION_VACIA = "condición vacía"
LOCAL_SIN_USO = "local sin uso"
FORMAS = (ENVOLTURA, DECREMENTO_INCREMENTO, CONDICION_VACIA, LOCAL_SIN_USO)

_CIERRE_ENVOLTURA = re.compile(r"^\s*\}\s*while\s*\(0\)\s*;")
_DEFINICION = re.compile(r"^[A-Za-z_][\w \t\*]*?[\s\*](\w+)\([^;]*\)\s*\{?\s*$")
_FILA_TABLA = re.compile(r"^\|\s*`(\w+)`\s*\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|")
_INCREMENTO = re.compile(r"^\s*(?:(\w+)(\+\+|--)|(\+\+|--)(\w+))\s*;\s*$")
_IF_VACIO_EN_UNA_LINEA = re.compile(r"^\s*(?:\}\s*else\s+)?if\s*\(.*\)\s*\{\s*\}\s*$")
_IF_ABRE = re.compile(r"^\s*(?:\}\s*else\s+)?if\s*\(.*\)\s*\{\s*$")
_CIERRE_SOLO = re.compile(r"^\s*\}\s*$")
_DECLARACION_CON_VALOR = re.compile(r"^\s+((?:[A-Za-z_]\w*[\s\*]+)+?)(\w+)\s*=\s*[^=].*;\s*$")
_PALABRAS_QUE_NO_DECLARAN = {"return", "else", "goto", "case", "sizeof", "do", "while", "if", "for", "switch"}


def _lineas_de_codigo(texto: str) -> list[str]:
    """Devuelve las lineas del texto con las de macros (``#define`` y sus continuaciones) vaciadas.

    Se conserva el numero de lineas para que los indices sigan coincidiendo con el original.
    """
    resultado: list[str] = []
    en_macro = False
    for linea in texto.splitlines():
        if en_macro or linea.lstrip().startswith("#define"):
            en_macro = linea.rstrip().endswith("\\")
            resultado.append("")
        else:
            resultado.append(linea)
    return resultado


def _funcion_que_contiene(lineas: list[str], indice: int) -> str | None:
    for anterior in range(indice, -1, -1):
        coincidencia = _DEFINICION.match(lineas[anterior])
        if coincidencia is not None:
            return coincidencia.group(1)
    return None


def _cuerpos(lineas: list[str]) -> list[tuple[str, int, int]]:
    """Lista (funcion, linea de la definicion, linea del cierre) de las definiciones del texto."""
    cuerpos: list[tuple[str, int, int]] = []
    indice = 0
    while indice < len(lineas):
        coincidencia = _DEFINICION.match(lineas[indice])
        if coincidencia is None:
            indice += 1
            continue
        cierre = indice
        while cierre < len(lineas) and lineas[cierre] != "}":
            cierre += 1
        cuerpos.append((coincidencia.group(1), indice, cierre))
        indice = cierre + 1
    return cuerpos


def _cuenta(cuentas: dict[tuple[str, str], int], funcion: str | None, forma: str) -> None:
    if funcion is not None:
        clave = (funcion, forma)
        cuentas[clave] = cuentas.get(clave, 0) + 1


def _envolturas(lineas: list[str], cuentas: dict[tuple[str, str], int]) -> None:
    for indice, linea in enumerate(lineas):
        if _CIERRE_ENVOLTURA.match(linea):
            _cuenta(cuentas, _funcion_que_contiene(lineas, indice), ENVOLTURA)


def _pares_decremento_incremento(lineas: list[str], cuentas: dict[tuple[str, str], int]) -> None:
    indice = 0
    while indice + 1 < len(lineas):
        primera = _INCREMENTO.match(lineas[indice])
        segunda = _INCREMENTO.match(lineas[indice + 1])
        if primera is not None and segunda is not None:
            nombre_a = primera.group(1) or primera.group(4)
            operador_a = primera.group(2) or primera.group(3)
            nombre_b = segunda.group(1) or segunda.group(4)
            operador_b = segunda.group(2) or segunda.group(3)
            if nombre_a == nombre_b and operador_a != operador_b:
                _cuenta(cuentas, _funcion_que_contiene(lineas, indice), DECREMENTO_INCREMENTO)
                indice += 2
                continue
        indice += 1


def _condiciones_vacias(lineas: list[str], cuentas: dict[tuple[str, str], int]) -> None:
    for indice, linea in enumerate(lineas):
        vacia = _IF_VACIO_EN_UNA_LINEA.match(linea) is not None or (
            _IF_ABRE.match(linea) is not None
            and indice + 1 < len(lineas)
            and _CIERRE_SOLO.match(lineas[indice + 1]) is not None
        )
        if vacia:
            _cuenta(cuentas, _funcion_que_contiene(lineas, indice), CONDICION_VACIA)


def _macros_del_archivo(texto: str) -> dict[str, str]:
    """Devuelve nombre de macro -> texto completo de su definicion (con las lineas de continuacion)."""
    macros: dict[str, str] = {}
    lineas = texto.splitlines()
    indice = 0
    while indice < len(lineas):
        coincidencia = re.match(r"^\s*#define\s+(\w+)", lineas[indice])
        if coincidencia is None:
            indice += 1
            continue
        definicion = [lineas[indice]]
        while definicion[-1].rstrip().endswith("\\") and indice + 1 < len(lineas):
            indice += 1
            definicion.append(lineas[indice])
        macros[coincidencia.group(1)] = "\n".join(definicion)
        indice += 1
    return macros


def _locales_sin_uso(lineas: list[str], macros: dict[str, str], cuentas: dict[tuple[str, str], int]) -> None:
    """Cuenta las locales con inicializador que nada lee, contando el uso de las macros que el cuerpo invoca.

    Una macro del archivo puede leer una local por su nombre sin recibirla como argumento: es un uso.
    """
    for funcion, inicio, cierre in _cuerpos(lineas):
        cuerpo = lineas[inicio : cierre + 1]
        texto_cuerpo = "\n".join(cuerpo)
        invocadas = [
            texto for nombre, texto in macros.items() if re.search(rf"\b{re.escape(nombre)}\b", texto_cuerpo)
        ]
        for linea in cuerpo:
            coincidencia = _DECLARACION_CON_VALOR.match(linea)
            if coincidencia is None:
                continue
            if coincidencia.group(1).split()[0].rstrip("*") in _PALABRAS_QUE_NO_DECLARAN:
                continue
            nombre = coincidencia.group(2)
            patron = re.compile(rf"\b{re.escape(nombre)}\b")
            usos = len(patron.findall(texto_cuerpo)) + sum(len(patron.findall(texto)) for texto in invocadas)
            if usos == 1:
                _cuenta(cuentas, funcion, LOCAL_SIN_USO)


def _buscar_referencias(texto: str) -> dict[tuple[str, str], int]:
    """Cuenta las referencias sin codigo por (funcion, forma), ignorando las que viven dentro de una macro."""
    lineas = _lineas_de_codigo(texto)
    cuentas: dict[tuple[str, str], int] = {}
    _envolturas(lineas, cuentas)
    _pares_decremento_incremento(lineas, cuentas)
    _condiciones_vacias(lineas, cuentas)
    _locales_sin_uso(lineas, _macros_del_archivo(texto), cuentas)
    return cuentas


def _cabecera(texto: str, funcion: str) -> str:
    """Devuelve el bloque ``/* */`` inmediatamente anterior a la definicion, o cadena vacia."""
    lineas = texto.splitlines()
    for indice, linea in enumerate(lineas):
        coincidencia = _DEFINICION.match(linea)
        if coincidencia is None or coincidencia.group(1) != funcion:
            continue
        fin = indice - 1
        if fin < 0 or not lineas[fin].rstrip().endswith("*/"):
            return ""
        inicio = fin
        while inicio >= 0 and "/*" not in lineas[inicio]:
            inicio -= 1
        return "\n".join(lineas[max(inicio, 0) : fin + 1])
    return ""


def _incumplimientos(texto: str) -> list[str]:
    """Lista las funciones con referencias cuya cabecera no lleva el marcador y la oracion fija."""
    fallos: list[str] = []
    for funcion in sorted({funcion for funcion, _ in _buscar_referencias(texto)}):
        cabecera = " ".join(_cabecera(texto, funcion).replace("*", " ").split())
        if not any(marcador in cabecera for marcador in MARCADORES_SIN_CODIGO):
            fallos.append(f"{funcion}: la cabecera no dice que la referencia no genera codigo")
        if FRASE_FIJA not in cabecera:
            fallos.append(f"{funcion}: la cabecera no lleva la oracion fija")
    return fallos


def _referencias_en_src() -> dict[tuple[str, str], tuple[str, int]]:
    """Devuelve (funcion, forma) -> (archivo relativo, referencias) para todo ``src/*.c``."""
    resultado: dict[tuple[str, str], tuple[str, int]] = {}
    for archivo in sorted((RAIZ_REPOSITORIO / "src").glob("*.c")):
        texto = archivo.read_text(encoding="utf-8")
        for clave, cantidad in _buscar_referencias(texto).items():
            resultado[clave] = (f"src/{archivo.name}", cantidad)
    return resultado


def _tabla_del_documento() -> dict[tuple[str, str], tuple[str, int]]:
    """Lee la tabla de ``## Referencias sin código`` como (funcion, forma) -> (archivo, referencias)."""
    texto = (RAIZ_REPOSITORIO / "docs" / "DESCOMPILACION.md").read_text(encoding="utf-8")
    inicio = texto.index("## Referencias sin código")
    siguiente = texto.find("\n## ", inicio + 1)
    seccion = texto[inicio : siguiente if siguiente != -1 else len(texto)]
    filas: dict[tuple[str, str], tuple[str, int]] = {}
    for linea in seccion.splitlines():
        coincidencia = _FILA_TABLA.match(linea)
        if coincidencia is not None:
            funcion, archivo, forma, cantidad = coincidencia.groups()
            filas[(funcion, forma)] = (archivo, int(cantidad))
    return filas


def _texto_con(cuerpo: str) -> str:
    return f"/* cabecera */\ns32 func_800000A0(s32 a)\n{{\n{cuerpo}    return a;\n}}\n"


def test_el_recuento_encuentra_las_envolturas_del_codigo_y_no_las_de_macros() -> None:
    texto = (
        "#define M(x) do { \\\n"
        "    x; \\\n"
        "} while (0);\n"
        "\n" + _texto_con("    do {\n        a += 2;\n    } while (0);\n")
    )
    assert _buscar_referencias(texto) == {("func_800000A0", ENVOLTURA): 1}


def test_el_recuento_encuentra_los_pares_de_decremento_e_incremento_en_cualquier_orden() -> None:
    texto = _texto_con("    a--;\n    a++;\n    b++;\n    b--;\n")
    assert _buscar_referencias(texto) == {("func_800000A0", DECREMENTO_INCREMENTO): 2}


def test_dos_incrementos_seguidos_o_de_variables_distintas_no_son_un_par() -> None:
    texto = _texto_con("    a++;\n    a++;\n    b--;\n    c++;\n")
    assert _buscar_referencias(texto) == {}


def test_el_recuento_encuentra_las_condiciones_vacias_en_una_y_en_dos_lineas() -> None:
    texto = _texto_con("    if (a) {}\n    if (a->campo) {\n    }\n    if (a) {\n        a = 1;\n    }\n")
    assert _buscar_referencias(texto) == {("func_800000A0", CONDICION_VACIA): 2}


def test_el_recuento_encuentra_la_local_sin_uso_con_inicializador_y_no_la_que_se_lee() -> None:
    texto = _texto_con("    s32 sin_uso = 2;\n    s32 usada = 3;\n    a = usada;\n")
    assert _buscar_referencias(texto) == {("func_800000A0", LOCAL_SIN_USO): 1}


def test_una_local_que_solo_lee_una_macro_invocada_se_cuenta_como_usada() -> None:
    texto = "#define LEE_K(x) ((x) + k)\n\n" + _texto_con("    s32 k = 0;\n    a = LEE_K(a);\n")
    assert _buscar_referencias(texto) == {}


def test_una_asignacion_o_un_return_no_se_toman_por_una_declaracion() -> None:
    texto = _texto_con("    a = 3;\n    p->campo = 4;\n    return a = 1;\n")
    assert _buscar_referencias(texto) == {}


def test_toda_referencia_declara_que_no_genera_codigo() -> None:
    fallos: list[str] = []
    for archivo in sorted((RAIZ_REPOSITORIO / "src").glob("*.c")):
        for fallo in _incumplimientos(archivo.read_text(encoding="utf-8")):
            if "no genera codigo" in fallo:
                fallos.append(f"{archivo.name}: {fallo}")
    assert fallos == []


def test_toda_referencia_lleva_la_oracion_fija_de_forma_original_desconocida() -> None:
    fallos: list[str] = []
    for archivo in sorted((RAIZ_REPOSITORIO / "src").glob("*.c")):
        for fallo in _incumplimientos(archivo.read_text(encoding="utf-8")):
            if "oracion fija" in fallo:
                fallos.append(f"{archivo.name}: {fallo}")
    assert fallos == []


def test_la_tabla_de_referencias_coincide_con_src() -> None:
    en_src = _referencias_en_src()
    tabla = _tabla_del_documento()
    faltan = sorted(set(en_src) - set(tabla))
    assert faltan == [], f"referencias que no estan en la tabla: {faltan}"
    for clave, (archivo, cantidad) in en_src.items():
        assert tabla[clave] == (archivo, cantidad), clave


def test_toda_fila_de_la_tabla_corresponde_a_una_referencia_en_src() -> None:
    sobran = sorted(set(_tabla_del_documento()) - set(_referencias_en_src()))
    assert sobran == [], f"filas de la tabla sin referencia en src: {sobran}"


def test_toda_fila_de_la_tabla_usa_una_de_las_cuatro_formas() -> None:
    formas = {forma for _, forma in _tabla_del_documento()}
    assert formas <= set(FORMAS), sorted(formas - set(FORMAS))


def test_la_tabla_no_esta_vacia() -> None:
    assert _tabla_del_documento()


def test_una_referencia_sin_la_frase_ni_el_marcador_se_detecta(tmp_path: Path) -> None:
    archivo = tmp_path / "inventado.c"
    archivo.write_text(
        "/*\n"
        " * Suma uno al parametro.\n"
        " */\n"
        "s32 func_800000B0(s32 a)\n"
        "{\n"
        "    a--;\n"
        "    a++;\n"
        "    return a;\n"
        "}\n",
        encoding="utf-8",
    )
    fallos = _incumplimientos(archivo.read_text(encoding="utf-8"))
    assert len(fallos) == 2
    assert any("no genera codigo" in fallo for fallo in fallos)
    assert any("oracion fija" in fallo for fallo in fallos)


def test_una_referencia_con_marcador_y_frase_en_la_cabecera_se_acepta(tmp_path: Path) -> None:
    archivo = tmp_path / "inventado.c"
    archivo.write_text(
        "/*\n"
        " * El par a--; a++; no genera codigo: pondera por dos referencias el parametro.\n"
        f" * {FRASE_FIJA}\n"
        " */\n"
        "s32 func_800000C0(s32 a)\n"
        "{\n"
        "    a--;\n"
        "    a++;\n"
        "    return a;\n"
        "}\n",
        encoding="utf-8",
    )
    assert _incumplimientos(archivo.read_text(encoding="utf-8")) == []

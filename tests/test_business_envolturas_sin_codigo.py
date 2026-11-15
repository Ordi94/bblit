"""Las referencias sin codigo deben estar declaradas y contadas.

Se admiten cinco formas que no generan ninguna instruccion propia y que solo mueven el reparto de registros o
una decision del optimizador de bucles: la envoltura ``do { ... } while (0)``, el par ``x--; x++;``, la
condicion vacia ``if (x) {}``, la local sin uso con inicializador y la sentencia duplicada en ambas ramas (la
misma sentencia escrita en las ramas de un ``if``/``else``, que el salto cruzado del compilador vuelve a
fusionar; se localiza por su comentario fijo). La tecnica solo se admite con condiciones: el comentario de
cabecera de la funcion dice que la referencia no genera codigo y cierra el parrafo con una oracion fija que
reconoce que se desconoce la forma del fuente original, y ``docs/DESCOMPILACION.md`` lista cada funcion con su
forma y su numero de referencias. Estas pruebas cruzan ``src/`` con esa tabla para que una referencia nueva no
entre sin su comentario ni sin su fila, y para que una fila no sobreviva a la referencia que describia. Solo
leen archivos.
"""

import re
from collections import Counter
from pathlib import Path

from tools.proyecto import RAIZ_REPOSITORIO

FRASE_FIJA = "La forma del fuente original que producia este reparto se desconoce."
MARCADORES_SIN_CODIGO = ("no genera codigo", "no generan codigo")

ENVOLTURA = "envoltura"
DECREMENTO_INCREMENTO = "decremento-incremento"
CONDICION_VACIA = "condición vacía"
LOCAL_SIN_USO = "local sin uso"
SENTENCIA_DUPLICADA = "sentencia duplicada en ambas ramas"
FORMAS = (ENVOLTURA, DECREMENTO_INCREMENTO, CONDICION_VACIA, LOCAL_SIN_USO, SENTENCIA_DUPLICADA)
COMENTARIO_REPLICADA = "Sentencia replicada: es la misma que la de las otras ramas."

_CIERRE_ENVOLTURA = re.compile(r"^\s*\}\s*while\s*\(0\)\s*;")
_DEFINICION = re.compile(r"^[A-Za-z_][\w \t\*]*?[\s\*](\w+)\([^;]*\)\s*\{?\s*$")
_FILA_TABLA = re.compile(r"^\|\s*`(\w+)`\s*\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|")
_INCREMENTO = re.compile(r"^\s*(?:(\w+)(\+\+|--)|(\+\+|--)(\w+))\s*;\s*$")
_IF_VACIO_EN_UNA_LINEA = re.compile(r"^\s*(?:\}\s*else\s+)?if\s*\(.*\)\s*\{\s*\}\s*$")
_IF_ABRE = re.compile(r"^\s*(?:\}\s*else\s+)?if\s*\(.*\)\s*\{\s*$")
_CIERRE_SOLO = re.compile(r"^\s*\}\s*$")
_DECLARACION_CON_VALOR = re.compile(r"^\s+((?:[A-Za-z_]\w*[\s\*]+)+?)(\w+)\s*=\s*[^=].*;\s*$")
_PALABRAS_QUE_NO_DECLARAN = {"return", "else", "goto", "case", "sizeof", "do", "while", "if", "for", "switch"}
_COMENTARIO_REPLICADA = re.compile(rf"^\s*/\*\s*{re.escape(COMENTARIO_REPLICADA)}\s*\*/\s*$")
_CABEZA_CON_TIPO = re.compile(
    r"^(?:[A-Za-z_]\w*[ \t]*\*+[ \t]*|[A-Za-z_]\w*[ \t]+)+([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)*$"
)
_CABEZA_SIN_TIPO = re.compile(r"^\**\s*([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)*$")
_TOKEN_DE_SENTENCIA = re.compile(
    r"(?P<acceso>->|\.)\s*(?P<campo>[A-Za-z_]\w*)"
    r"|(?P<literal>\d\w*)"
    r"|(?P<nombre>[A-Za-z_]\w*)(?P<llamada>\s*\()?"
)


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


def _sentencias_replicadas(lineas: list[str], cuentas: dict[tuple[str, str], int]) -> None:
    """Cuenta los comentarios fijos que marcan una sentencia replicada en las ramas de la funcion."""
    for indice, linea in enumerate(lineas):
        if _COMENTARIO_REPLICADA.match(linea):
            _cuenta(cuentas, _funcion_que_contiene(lineas, indice), SENTENCIA_DUPLICADA)


def _valor_del_literal(texto: str) -> str:
    """Devuelve el literal entero de C como ``#valor`` en decimal, para compararlo por su valor.

    Contexto:
        Lo usa ``_esqueleto``. El sufijo (``u``, ``U``, ``l``, ``L``) no cuenta: ``0x10u`` y ``16`` son el
        mismo valor y la misma instruccion. Un literal que no se pueda interpretar se conserva por su texto
        para que dos literales ilegibles solo coincidan si se escriben igual.

    Args:
        texto (str): Literal tal como aparece en el fuente, con su sufijo.

    Returns:
        str: ``#`` seguido del valor en decimal, o del texto original si no es un entero valido.

    Ejemplo:
        _valor_del_literal("0x10u") == _valor_del_literal("16")
    """
    digitos = texto.rstrip("uUlL")
    try:
        if digitos[:2] in ("0x", "0X"):
            valor = int(digitos, 16)
        elif len(digitos) > 1 and digitos.startswith("0"):
            valor = int(digitos, 8)
        else:
            valor = int(digitos)
    except ValueError:
        return f"#{texto}"
    return f"#{valor}"


def _dividir_en_comas(texto: str) -> list[str]:
    """Parte el texto por las comas que no estan dentro de parentesis, corchetes ni llaves."""
    partes: list[str] = []
    profundidad = 0
    inicio = 0
    for indice, caracter in enumerate(texto):
        if caracter in "([{":
            profundidad += 1
        elif caracter in ")]}":
            profundidad -= 1
        elif caracter == "," and profundidad == 0:
            partes.append(texto[inicio:indice])
            inicio = indice + 1
    partes.append(texto[inicio:])
    return partes


def _nombre_de_declarador(fragmento: str, con_tipo: bool) -> str | None:
    """Devuelve el nombre declarado en un fragmento ``tipo nombre`` o ``nombre``, sin inicializador.

    ``con_tipo`` exige el tipo delante (primer declarador de una linea o un parametro); sin el, se admiten
    los declaradores siguientes de ``s32 a, *b, c[3];``.
    """
    cabeza = fragmento.split("=", 1)[0].strip()
    patron = _CABEZA_CON_TIPO if con_tipo else _CABEZA_SIN_TIPO
    coincidencia = patron.match(cabeza)
    return coincidencia.group(1) if coincidencia is not None else None


def _locales_de_funcion(lineas: list[str], inicio: int, cierre: int) -> frozenset[str]:
    """Devuelve los nombres de los parametros y de las variables declaradas en la funcion.

    Contexto:
        Lo usa ``_incumplimientos_de_replicadas``: la regla solo deja variar entre las sentencias replicadas
        el nombre de la variable propia de cada camino, y esa variable es un parametro o una local de la
        funcion que contiene la sentencia. Cualquier otro identificador (un simbolo global ``D_XXXXXXXX``, una
        constante simbolica, un tipo) es parte de la sentencia y no puede cambiar.

    Se reconocen las declaraciones de varios nombres en una linea (``s32 a, b;``), los punteros
    (``u8 *p;``), los arreglos (``s16 v[3];``), las que llevan inicializador y las de los bloques internos:
    una declaracion en un bloque anidado se trata como de toda la funcion, que es lo conservador porque solo
    amplia el conjunto de nombres que pueden variar a los que la funcion declara de verdad.

    Args:
        lineas (list[str]): Lineas del archivo, con las macros vaciadas.
        inicio (int): Indice de la linea de la definicion (sus parametros cuentan).
        cierre (int): Indice de la llave que cierra la funcion.

    Returns:
        frozenset[str]: Nombres de parametros y locales; vacio si la funcion no declara ninguno.

    Ejemplo:
        _locales_de_funcion(["s32 f(s32 a)", "{", "    s32 b, *c;", "}"], 0, 3) == {"a", "b", "c"}
    """
    definicion = lineas[inicio]
    parametros = definicion[definicion.index("(") + 1 : definicion.rindex(")")]
    nombres = [_nombre_de_declarador(parametro, con_tipo=True) for parametro in _dividir_en_comas(parametros)]
    for linea in lineas[inicio + 1 : cierre]:
        texto = linea.strip()
        if not texto.endswith(";") or texto.split(None, 1)[0] in _PALABRAS_QUE_NO_DECLARAN:
            continue
        declaradores = _dividir_en_comas(texto[:-1])
        primero = _nombre_de_declarador(declaradores[0], con_tipo=True)
        if primero is None:
            continue
        nombres.append(primero)
        nombres.extend(_nombre_de_declarador(declarador, con_tipo=False) for declarador in declaradores[1:])
    return frozenset(nombre for nombre in nombres if nombre is not None)


def _esqueleto(sentencia: str, locales: frozenset[str]) -> str:
    """Devuelve la sentencia con las locales como ``I`` y todo lo demas por su valor o su nombre.

    Solo la variable propia de cada rama puede cambiar entre ramas (condicion (c) de la sentencia duplicada),
    de modo que unicamente se neutralizan los identificadores que son parametros o locales de la funcion
    (``I``). Se conserva literalmente todo lo demas: los simbolos globales (``D_80069668``), las constantes
    simbolicas sin parentesis, los tipos de una conversion (``(s16)x``), el nombre invocado (identificador
    seguido de ``(``: una macro o una funcion) y el nombre de campo (identificador tras ``.`` o ``->``, aunque
    una local se llame igual): un global, una constante, un tipo, una macro o un campo distinto es otra
    sentencia aunque tenga la misma forma. Los literales numericos tampoco son nombres: se comparan por su
    valor (``0x10`` y ``16`` coinciden; el sufijo no cuenta). El patron consume cada palabra entera, de modo
    que las cifras de ``p1`` pertenecen al identificador y los digitos de ``0x2E`` al literal.

    Contexto:
        Lo usa ``_incumplimientos_de_replicadas`` para decidir que sentencias marcadas como replicadas son la
        misma; las locales las calcula ``_locales_de_funcion``.

    Args:
        sentencia (str): Sentencia en una linea, con sus espacios originales.
        locales (frozenset[str]): Parametros y locales de la funcion que contiene la sentencia.

    Returns:
        str: Sentencia con espacios normalizados, locales como ``I``, nombres invocados, de campo, globales y
        constantes tal cual y literales como ``#valor``.

    Ejemplo:
        locales = frozenset({"p", "q"})
        _esqueleto("o->x = p | 0x10;", locales) == _esqueleto("o->x = q | 16u;", locales)
        _esqueleto("o->x = D_80069668;", locales) != _esqueleto("o->x = D_80069680;", locales)
    """

    def _sustituir(coincidencia: re.Match[str]) -> str:
        if coincidencia.group("campo") is not None:
            return coincidencia.group("acceso") + coincidencia.group("campo")
        literal = coincidencia.group("literal")
        if literal is not None:
            return _valor_del_literal(literal)
        nombre = coincidencia.group("nombre")
        if coincidencia.group("llamada") is not None:
            return nombre + "("
        return "I" if nombre in locales else nombre

    return _TOKEN_DE_SENTENCIA.sub(_sustituir, " ".join(sentencia.split()))


def _incumplimientos_de_replicadas(texto: str) -> list[str]:
    """Lista las marcas de sentencia replicada que no tienen pareja con su misma sentencia.

    Cada marca debe preceder a una sentencia, y esa sentencia debe tener en la misma funcion al menos otra
    marcada con el mismo esqueleto (locales y parametros de la funcion neutralizados; globales, constantes,
    tipos, macro invocada, campos y literales por su valor).
    Las marcas se agrupan por esqueleto y no todas contra todas: una funcion puede tener varias parejas
    distintas (un almacen en cada rama de un ``if``/``else`` y otro en cada rama de otro), pero un grupo de
    una sola sentencia es una marca huerfana y se rechaza. Limite aceptado: una funcion cuyas parejas se
    equivocan las dos a la vez, de forma que cada grupo sigue teniendo al menos dos, no se distingue de una
    con parejas distintas legitimas.

    Contexto:
        Lo ejerce la prueba que recorre ``src/``; el esqueleto lo calcula ``_esqueleto``.

    Args:
        texto (str): Contenido completo de un archivo ``.c``.

    Returns:
        list[str]: Un mensaje por cada marca que no precede a una sentencia o que queda huerfana; vacia si
        todas cumplen.

    Ejemplo:
        _incumplimientos_de_replicadas(Path("src/logica_de_niveles_3.c").read_text(encoding="utf-8")) == []
    """
    lineas = _lineas_de_codigo(texto)
    locales_por_funcion = {
        funcion: _locales_de_funcion(lineas, inicio, cierre) for funcion, inicio, cierre in _cuerpos(lineas)
    }
    sentencias: dict[str, list[str]] = {}
    for indice, linea in enumerate(lineas):
        if not _COMENTARIO_REPLICADA.match(linea):
            continue
        funcion = _funcion_que_contiene(lineas, indice) or "?"
        siguiente = lineas[indice + 1] if indice + 1 < len(lineas) else ""
        sentencias.setdefault(funcion, []).append(siguiente.strip())
    fallos: list[str] = []
    for funcion, marcadas in sorted(sentencias.items()):
        locales = locales_por_funcion.get(funcion, frozenset())
        validas = [sentencia for sentencia in marcadas if sentencia.endswith(";")]
        if len(validas) != len(marcadas):
            fallos.append(f"{funcion}: la marca de sentencia replicada no precede a una sentencia")
        grupos = Counter(_esqueleto(sentencia, locales) for sentencia in validas)
        for sentencia in validas:
            if grupos[_esqueleto(sentencia, locales)] < 2:
                huerfana = f"la sentencia replicada `{sentencia}` no tiene pareja de igual forma"
                fallos.append(f"{funcion}: {huerfana}")
    return fallos


def _buscar_referencias(texto: str) -> dict[tuple[str, str], int]:
    """Cuenta las referencias sin codigo por (funcion, forma), ignorando las que viven dentro de una macro."""
    lineas = _lineas_de_codigo(texto)
    cuentas: dict[tuple[str, str], int] = {}
    _envolturas(lineas, cuentas)
    _pares_decremento_incremento(lineas, cuentas)
    _condiciones_vacias(lineas, cuentas)
    _locales_sin_uso(lineas, _macros_del_archivo(texto), cuentas)
    _sentencias_replicadas(lineas, cuentas)
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


DECLARACIONES_BASE = "    s32 b, c, d, p, q, x2E, y17, mascara, m, num, sentido;\n    Obj *o;\n"
LOCALES_BASE = frozenset({"a", "b", "c", "d", "p", "q", "x2E", "y17", "mascara", "m", "num", "sentido", "o"})


def _texto_con(cuerpo: str, declaraciones: str = DECLARACIONES_BASE) -> str:
    return f"/* cabecera */\ns32 func_800000A0(s32 a)\n{{\n{declaraciones}{cuerpo}    return a;\n}}\n"


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


def _rama_replicada(variable: str) -> str:
    return (
        f"        {variable} = a;\n"
        f"        /* {COMENTARIO_REPLICADA} */\n"
        f"        b = {variable} + ({variable} << 8);\n"
    )


def test_el_recuento_encuentra_las_sentencias_replicadas_por_su_comentario_fijo() -> None:
    texto = _texto_con(
        "    if (a) {\n" + _rama_replicada("p") + "    } else {\n" + _rama_replicada("q") + "    }\n"
    )
    assert _buscar_referencias(texto) == {("func_800000A0", SENTENCIA_DUPLICADA): 2}


def test_un_comentario_distinto_o_dentro_de_una_macro_no_cuenta_como_sentencia_replicada() -> None:
    texto = (
        f"#define M(x) \\\n    /* {COMENTARIO_REPLICADA} */ \\\n    x\n\n"
        + _texto_con("    /* Sentencia replicada: otra cosa. */\n    b = a;\n")
    )
    assert _buscar_referencias(texto) == {}


def test_las_sentencias_replicadas_con_la_misma_forma_y_otra_variable_se_aceptan() -> None:
    texto = _texto_con(
        "    if (a) {\n" + _rama_replicada("p") + "    } else {\n" + _rama_replicada("q") + "    }\n"
    )
    assert _incumplimientos_de_replicadas(texto) == []


def _rama_con_constante(variable: str, constante: str) -> str:
    return f"        /* {COMENTARIO_REPLICADA} */\n        b = {variable} | {constante};\n"


def _texto_de_dos_ramas(constante_a: str, constante_b: str) -> str:
    return _texto_con(
        "    if (a) {\n"
        + _rama_con_constante("p", constante_a)
        + "    } else {\n"
        + _rama_con_constante("q", constante_b)
        + "    }\n"
    )


def test_sentencias_replicadas_con_literales_hexadecimales_distintos_se_rechazan() -> None:
    texto = _texto_de_dos_ramas("0x2E000000", "0x4C000000")
    esperado = [_sin_pareja("b = p | 0x2E000000;"), _sin_pareja("b = q | 0x4C000000;")]
    assert _incumplimientos_de_replicadas(texto) == esperado


def test_sentencias_replicadas_con_literales_decimales_distintos_se_rechazan() -> None:
    texto = _texto_de_dos_ramas("12", "13")
    assert len(_incumplimientos_de_replicadas(texto)) == 2


def test_sentencias_replicadas_con_el_mismo_literal_hexadecimal_se_aceptan() -> None:
    assert _incumplimientos_de_replicadas(_texto_de_dos_ramas("0x2E000000", "0x2E000000")) == []


def test_sentencias_replicadas_con_el_mismo_valor_en_hexadecimal_y_en_decimal_se_aceptan() -> None:
    assert _incumplimientos_de_replicadas(_texto_de_dos_ramas("0x10", "16")) == []


def test_el_sufijo_del_literal_no_cuenta_para_comparar_sentencias_replicadas() -> None:
    assert _incumplimientos_de_replicadas(_texto_de_dos_ramas("0x2E000000u", "0x2E000000")) == []


def test_un_literal_octal_se_compara_por_su_valor() -> None:
    assert _incumplimientos_de_replicadas(_texto_de_dos_ramas("010", "8")) == []
    assert _incumplimientos_de_replicadas(_texto_de_dos_ramas("010", "10")) != []


def test_un_identificador_con_digitos_sigue_siendo_un_identificador_y_no_un_literal() -> None:
    assert _incumplimientos_de_replicadas(_texto_de_dos_ramas("x2E", "y17")) == []
    assert _esqueleto("b = p1 | 0x2E;", LOCALES_BASE | {"p1"}) == "I = I | #46;"


def test_el_esqueleto_normaliza_los_literales_a_su_valor_y_las_locales_a_una_sola() -> None:
    assert _esqueleto("b = p | 0x2E000000;", LOCALES_BASE) != _esqueleto("b = p | 0x4C000000;", LOCALES_BASE)
    assert _esqueleto("b = p | 0x10;", LOCALES_BASE) == _esqueleto("b  =  q | 16u;", LOCALES_BASE)


def test_un_literal_que_no_se_puede_interpretar_se_compara_por_su_texto() -> None:
    assert _esqueleto("b = 0xZZ;", LOCALES_BASE) == "I = #0xZZ;"


def test_una_sola_marca_de_sentencia_replicada_se_rechaza() -> None:
    texto = _texto_con("    if (a) {\n" + _rama_replicada("p") + "    }\n")
    esperado = [_sin_pareja("b = p + (p << 8);")]
    assert _incumplimientos_de_replicadas(texto) == esperado


def test_sentencias_marcadas_que_no_son_la_misma_sentencia_se_rechazan() -> None:
    otra = f"        /* {COMENTARIO_REPLICADA} */\n        b = q * 3;\n"
    texto = _texto_con("    if (a) {\n" + _rama_replicada("p") + "    } else {\n" + otra + "    }\n")
    assert len(_incumplimientos_de_replicadas(texto)) == 2


def _sin_pareja(sentencia: str) -> str:
    return f"func_800000A0: la sentencia replicada `{sentencia}` no tiene pareja de igual forma"


def _marcada(sentencia: str) -> str:
    return f"        /* {COMENTARIO_REPLICADA} */\n        {sentencia}\n"


def _texto_de_dos_parejas(primera: tuple[str, str], segunda: tuple[str, str]) -> str:
    """Una pareja de sentencias marcadas en un if/else y otra pareja en un segundo if/else."""
    return _texto_con(
        "    if (a) {\n"
        + _marcada(primera[0])
        + "    } else {\n"
        + _marcada(primera[1])
        + "    }\n    if (b) {\n"
        + _marcada(segunda[0])
        + "    } else {\n"
        + _marcada(segunda[1])
        + "    }\n"
    )


def test_dos_parejas_de_macros_distintas_con_la_misma_forma_se_aceptan() -> None:
    alto = "MOVIL_LIMITE_ALTO(o) = num;"
    bajo = "MOVIL_LIMITE_BAJO(o) = sentido;"
    assert _incumplimientos_de_replicadas(_texto_de_dos_parejas((alto, alto), (bajo, bajo))) == []


def test_cuatro_marcas_donde_una_usa_la_macro_equivocada_se_rechazan() -> None:
    # Quedan tres marcas con la macro del limite alto y una con la del bajo: esa ultima no tiene pareja.
    alto = "MOVIL_LIMITE_ALTO(o) = num;"
    bajo = "MOVIL_LIMITE_BAJO(o) = sentido;"
    esperado = [_sin_pareja(bajo)]
    assert _incumplimientos_de_replicadas(_texto_de_dos_parejas((alto, alto), (alto, bajo))) == esperado


def test_un_trio_que_no_casa_deja_huerfanas_a_las_marcas_sin_pareja() -> None:
    # Alto una vez, bajo dos veces y una tercera macro una vez: se rechazan las dos que quedan solas.
    alto = "MOVIL_LIMITE_ALTO(o) = num;"
    bajo = "MOVIL_LIMITE_BAJO(o) = num;"
    otra = "MOVIL_OTRO(o) = num;"
    fallos = _incumplimientos_de_replicadas(_texto_de_dos_parejas((alto, bajo), (bajo, otra)))
    assert len(fallos) == 2
    assert "MOVIL_LIMITE_ALTO" in fallos[0]
    assert "MOVIL_OTRO" in fallos[1]


def test_las_marcas_de_dos_parejas_se_agrupan_por_forma_sin_importar_el_orden() -> None:
    alto = "MOVIL_LIMITE_ALTO(o) = num;"
    bajo = "MOVIL_LIMITE_BAJO(o) = num;"
    assert _incumplimientos_de_replicadas(_texto_de_dos_parejas((alto, bajo), (alto, bajo))) == []


def test_una_marca_huerfana_junto_a_una_pareja_valida_se_rechaza() -> None:
    texto = _texto_con(
        "    if (a) {\n"
        + _rama_replicada("p")
        + "    } else {\n"
        + _rama_replicada("q")
        + "    }\n    if (b) {\n"
        + _marcada("c = a * 3;")
        + "    }\n"
    )
    assert _incumplimientos_de_replicadas(texto) == [_sin_pareja("c = a * 3;")]


def test_nombres_de_campo_distintos_tras_la_flecha_se_rechazan() -> None:
    texto = _texto_de_dos_parejas(("o->vx = p;", "o->vy = q;"), ("o->vz = p;", "o->vz = q;"))
    assert _incumplimientos_de_replicadas(texto) == [_sin_pareja("o->vx = p;"), _sin_pareja("o->vy = q;")]


def test_nombres_de_campo_distintos_tras_el_punto_se_rechazan() -> None:
    locales = LOCALES_BASE | {"v", "w"}
    assert _esqueleto("v.vx = p;", locales) != _esqueleto("v.vy = p;", locales)
    assert _esqueleto("v.vx = p;", locales) == _esqueleto("w.vx = q;", locales)


def test_la_variable_propia_de_cada_rama_puede_cambiar_aunque_haya_campos_y_llamadas() -> None:
    texto = _texto_de_dos_ramas_con("o->vx = LEE(p);", "o->vx = LEE(q);")
    assert _incumplimientos_de_replicadas(texto) == []


def test_una_funcion_o_macro_invocada_distinta_se_rechaza() -> None:
    assert _esqueleto("f(a);", LOCALES_BASE) != _esqueleto("g(a);", LOCALES_BASE)
    assert _esqueleto("f(a);", LOCALES_BASE) == _esqueleto("f(b);", LOCALES_BASE)


def _texto_de_dos_ramas_con(primera: str, segunda: str, declaraciones: str = DECLARACIONES_BASE) -> str:
    cuerpo = "    if (a) {\n" + _marcada(primera) + "    } else {\n" + _marcada(segunda) + "    }\n"
    return _texto_con(cuerpo, declaraciones)


def _texto_de_tres_caminos(primero: list[str], segundo: list[str], tercero: list[str]) -> str:
    """Tres caminos a distinta profundidad que acaban en una misma cola, con sus sentencias marcadas."""
    return _texto_con(
        "    if (a) {\n"
        + "".join(_marcada(sentencia) for sentencia in primero)
        + "        goto cola;\n    }\n    if (b) {\n"
        + "".join(_marcada(sentencia) for sentencia in segundo)
        + "        goto cola;\n    }\n    if (c) {\n        if (d) {\n"
        + "".join(_marcada(sentencia) for sentencia in tercero)
        + "            goto cola;\n        }\n    }\n    cola:\n"
    )


def test_un_grupo_de_tres_caminos_con_la_misma_sentencia_se_acepta_y_cuenta_tres() -> None:
    """Tres caminos hacia una cola comun con la misma sentencia marcada son un grupo valido de tres.

    Regla:
        La sentencia replicada puede repetirse en mas de dos caminos: el recuento de la funcion es el de
        marcas y ningun camino queda huerfano.

    Ejemplo:
        Una mascara escrita en tres saltos a la misma etiqueta cuenta 3 y no produce incumplimientos.
    """
    sentencia = "o->flags = a & ~9;"
    texto = _texto_de_tres_caminos([sentencia], [sentencia], [sentencia])
    assert _incumplimientos_de_replicadas(texto) == []
    assert _buscar_referencias(texto) == {("func_800000A0", SENTENCIA_DUPLICADA): 3}


def test_un_grupo_de_tres_caminos_donde_uno_cambia_de_campo_deja_huerfana_solo_esa_marca() -> None:
    """Si uno de los tres caminos escribe otro campo, su marca no tiene pareja y las otras dos si.

    Regla:
        Cada marca se agrupa por su esqueleto: el camino que difiere en el campo o en el nombre invocado es
        otra sentencia y se rechaza, sin arrastrar a las dos que si coinciden.

    Ejemplo:
        Dos caminos con ``o->flags`` y uno con ``o->param`` dejan huerfana la sentencia de ``o->param``.
    """
    igual = "o->flags = a & ~9;"
    otro_campo = "o->param = a & ~9;"
    assert _incumplimientos_de_replicadas(_texto_de_tres_caminos([igual], [igual], [otro_campo])) == [
        _sin_pareja(otro_campo)
    ]
    otra_llamada = "LIMPIA(o) = a & ~9;"
    assert _incumplimientos_de_replicadas(_texto_de_tres_caminos([otra_llamada], [igual], [igual])) == [
        _sin_pareja(otra_llamada)
    ]


def test_dos_sentencias_por_camino_en_tres_caminos_cuentan_seis_y_se_aceptan() -> None:
    """Dos sentencias marcadas en cada uno de tres caminos son seis marcas en dos grupos de tres.

    Regla:
        Cada sentencia forma su propio grupo y el recuento es el de marcas (caminos por sentencias): seis.

    Ejemplo:
        ``mascara = ~9;`` y ``m = o->flags & mascara;`` en tres caminos cuentan 6 sin incumplimientos.
    """
    pareja = ["mascara = ~9;", "m = o->flags & mascara;"]
    texto = _texto_de_tres_caminos(pareja, pareja, pareja)
    assert _incumplimientos_de_replicadas(texto) == []
    assert _buscar_referencias(texto) == {("func_800000A0", SENTENCIA_DUPLICADA): 6}


GLOBAL_A = "D_80069668"
GLOBAL_B = "D_80069680"


def test_dos_globales_distintas_en_el_lugar_que_varia_se_rechazan() -> None:
    """Dos caminos que leen globales distintas no son la misma sentencia y ninguno tiene pareja.

    Regla:
        Condicion (c): solo cambia entre caminos el nombre de la variable propia de cada uno. Un simbolo
        global es otro dato de la memoria, no una variable del camino: leer ``D_80069668`` en uno y
        ``D_80069680`` en otro es una divergencia semantica y las dos marcas quedan huerfanas.

    Ejemplo:
        ``o->x = D_80069668;`` y ``o->x = D_80069680;`` dan dos incumplimientos.
    """
    primera = f"o->x = {GLOBAL_A};"
    segunda = f"o->x = {GLOBAL_B};"
    texto = _texto_de_dos_ramas_con(primera, segunda)
    assert _incumplimientos_de_replicadas(texto) == [_sin_pareja(primera), _sin_pareja(segunda)]


def test_la_misma_global_en_los_dos_caminos_se_acepta() -> None:
    """La misma global escrita igual en cada camino es la misma sentencia y forma pareja.

    Regla:
        Lo que no es una variable propia del camino se conserva literal en el esqueleto: si coincide, la
        sentencia es identica en los dos caminos y la condicion (c) se cumple.

    Ejemplo:
        ``o->x = D_80069668;`` en ambas ramas no produce incumplimientos.
    """
    sentencia = f"o->x = {GLOBAL_A};"
    assert _incumplimientos_de_replicadas(_texto_de_dos_ramas_con(sentencia, sentencia)) == []


def test_dos_locales_distintas_declaradas_en_la_funcion_se_aceptan() -> None:
    """Dos locales declaradas en la funcion son la variable propia de cada camino y pueden cambiar.

    Regla:
        Es el caso que regula la condicion (c): el mismo almacen con la variable de cada camino.

    Ejemplo:
        ``o->x = desplaza;`` y ``o->x = desplaza2;`` con ambas declaradas no producen incumplimientos.
    """
    declaraciones = "    s32 desplaza, desplaza2;\n    Obj *o;\n"
    texto = _texto_de_dos_ramas_con("o->x = desplaza;", "o->x = desplaza2;", declaraciones)
    assert _incumplimientos_de_replicadas(texto) == []


def test_un_parametro_frente_a_una_local_se_acepta_porque_ambos_son_variables_de_la_funcion() -> None:
    """Un parametro y una local son variables propias de la funcion: cada camino puede usar la suya.

    Regla:
        Condicion (c): lo que se prohibe es que cambie un dato ajeno a la funcion. Un parametro es una
        variable de la funcion igual que una local y el compilador lo reparte en un registro como a ella, de
        modo que un camino puede leer el parametro y otro la copia local sin cambiar de sentencia.

    Ejemplo:
        ``o->x = a;`` (``a`` es parametro) y ``o->x = p;`` (``p`` es local) no producen incumplimientos.
    """
    assert _incumplimientos_de_replicadas(_texto_de_dos_ramas_con("o->x = a;", "o->x = p;")) == []


def test_una_local_frente_a_una_global_se_rechaza() -> None:
    """Una local en un camino y una global en el otro no son la misma sentencia.

    Regla:
        Solo el nombre de una variable de la funcion puede variar: sustituirla por un simbolo global cambia
        de donde sale el valor, y las dos marcas quedan huerfanas.

    Ejemplo:
        ``o->x = p;`` y ``o->x = D_80069668;`` dan dos incumplimientos.
    """
    local = "o->x = p;"
    global_ = f"o->x = {GLOBAL_A};"
    texto = _texto_de_dos_ramas_con(local, global_)
    assert _incumplimientos_de_replicadas(texto) == [_sin_pareja(local), _sin_pareja(global_)]


def test_dos_constantes_simbolicas_distintas_sin_parentesis_se_rechazan() -> None:
    """Una macro en mayusculas sin parentesis es una constante: dos distintas son valores distintos.

    Regla:
        Las constantes simbolicas son invariantes entre caminos (condicion (c)); solo la misma constante en
        los dos caminos forma pareja.

    Ejemplo:
        ``o->x = LIMITE_ALTO;`` frente a ``o->x = LIMITE_BAJO;`` da dos incumplimientos; con la misma
        constante en ambas, ninguno.
    """
    alta = "o->x = LIMITE_ALTO;"
    baja = "o->x = LIMITE_BAJO;"
    assert _incumplimientos_de_replicadas(_texto_de_dos_ramas_con(alta, baja)) == [
        _sin_pareja(alta),
        _sin_pareja(baja),
    ]
    assert _incumplimientos_de_replicadas(_texto_de_dos_ramas_con(alta, alta)) == []


def test_el_tipo_de_una_conversion_es_invariante_entre_caminos() -> None:
    """El tipo de una conversion forma parte de la sentencia: ``(s16)p`` y ``(u16)q`` son otra sentencia.

    Regla:
        Un tipo no es una variable de la funcion; cambiarlo cambia la extension del valor y por tanto la
        instruccion. Con el mismo tipo y otra local, la pareja se acepta.

    Ejemplo:
        ``o->x = (s16)p;`` y ``o->x = (u16)q;`` dan dos incumplimientos; ``(s16)p`` y ``(s16)q``, ninguno.
    """
    con_signo = "o->x = (s16)p;"
    sin_signo = "o->x = (u16)q;"
    assert len(_incumplimientos_de_replicadas(_texto_de_dos_ramas_con(con_signo, sin_signo))) == 2
    assert _incumplimientos_de_replicadas(_texto_de_dos_ramas_con(con_signo, "o->x = (s16)q;")) == []


def test_una_local_que_se_llama_como_un_campo_no_neutraliza_el_campo() -> None:
    """El nombre tras ``->`` es un campo aunque una local se llame igual: sigue siendo invariante.

    Regla:
        Condicion (c): un campo distinto es otra sentencia. Que la funcion declare una local ``x`` no hace
        variable al campo ``x``; solo la lectura suelta de ``x`` es la variable.

    Ejemplo:
        ``o->x = x;`` es pareja de ``o->x = y;`` pero no de ``o->y = x;``.
    """
    declaraciones = "    s32 x, y;\n    Obj *o;\n"
    assert _esqueleto("o->x = x;", frozenset({"o", "x", "y"})) == "I->x = I;"
    misma_forma = _texto_de_dos_ramas_con("o->x = x;", "o->x = y;", declaraciones)
    assert _incumplimientos_de_replicadas(misma_forma) == []
    texto = _texto_de_dos_ramas_con("o->x = x;", "o->y = x;", declaraciones)
    assert _incumplimientos_de_replicadas(texto) == [_sin_pareja("o->x = x;"), _sin_pareja("o->y = x;")]


def test_las_locales_declaradas_en_el_texto_de_otra_funcion_no_cuentan() -> None:
    """Una variable declarada en otra funcion es un simbolo ajeno para la funcion que la nombra.

    Regla:
        Las locales se leen de la funcion que contiene la sentencia: un nombre que otra funcion declara no
        es variable de esta, y dos de ellos distintos son globales distintas.

    Ejemplo:
        ``g1`` y ``g2`` locales de la primera funcion no pueden variar en la segunda: dos incumplimientos.
    """
    primera = "s32 func_800000B0(s32 a)\n{\n    s32 g1, g2;\n    return a;\n}\n"
    segunda = _texto_de_dos_ramas_con("o->x = g1;", "o->x = g2;")
    texto = primera + segunda
    assert _incumplimientos_de_replicadas(texto) == [_sin_pareja("o->x = g1;"), _sin_pareja("o->x = g2;")]


def test_las_locales_se_reconocen_en_declaraciones_multiples_punteros_arreglos_y_bloques_internos() -> None:
    """Parametros y locales se reconocen en todas las formas de declaracion de C89 de este codigo.

    Regla:
        Entre las sentencias replicadas puede variar cualquier variable de la funcion: la declaracion de
        varios nombres en una linea, los punteros, los arreglos, los inicializadores, las de un bloque
        interno y los parametros. Lo que no es una declaracion (``return n;``, una asignacion, una llamada) no
        aporta nombres.

    Ejemplo:
        ``s32 u, v2;`` aporta ``u`` y ``v2``; ``u8 *w;``, ``w``; ``s16 arr[3];``, ``arr``.
    """
    lineas = [
        "s32 f(Obj *o, u8 v[4], s32 n)",
        "{",
        "    s32 u, v2;",
        "    u8 *w;",
        "    s16 arr[3];",
        "    s32 *pp, qq = g(1, 2), zz[2];",
        "    unsigned char **ptr;",
        "    if (n) {",
        "        s32 interna;",
        "        o->x = u;",
        "        g(n);",
        "        interna = w[0];",
        "    }",
        "    return n;",
        "}",
    ]
    esperadas = {"o", "v", "n", "u", "v2", "w", "arr", "pp", "qq", "zz", "ptr", "interna"}
    assert _locales_de_funcion(lineas, 0, len(lineas) - 1) == esperadas
    assert _locales_de_funcion(["s32 g(void)", "{", "    return 0;", "}"], 0, 3) == frozenset()


def test_las_locales_de_declaracion_multiple_y_puntero_pueden_variar_entre_caminos() -> None:
    """Las variables de ``s32 u, v;`` y de ``u8 *w;`` son las de cada camino y se aceptan como tales.

    Regla:
        Condicion (c) con las formas de declaracion habituales: la segunda variable de una declaracion
        multiple y un puntero son locales de la funcion como cualquier otra.

    Ejemplo:
        ``o->x = v;`` frente a ``o->x = u;`` y ``w[0] = 1;`` frente a ``p[0] = 1;`` no producen
        incumplimientos.
    """
    declaraciones = "    s32 u, v;\n    u8 *w, *z;\n    Obj *o;\n"
    de_enteros = _texto_de_dos_ramas_con("o->x = u;", "o->x = v;", declaraciones)
    de_punteros = _texto_de_dos_ramas_con("w[0] = 1;", "z[0] = 1;", declaraciones)
    assert _incumplimientos_de_replicadas(de_enteros) == []
    assert _incumplimientos_de_replicadas(de_punteros) == []


def test_una_marca_que_no_precede_a_una_sentencia_se_rechaza() -> None:
    sola = f"        /* {COMENTARIO_REPLICADA} */\n    }}\n"
    texto = _texto_con(
        "    if (a) {\n" + _rama_replicada("p") + _rama_replicada("q") + "    } else {\n" + sola
    )
    assert _incumplimientos_de_replicadas(texto) == [
        "func_800000A0: la marca de sentencia replicada no precede a una sentencia"
    ]


def test_toda_sentencia_replicada_de_src_es_la_misma_en_todas_sus_ramas() -> None:
    fallos: list[str] = []
    for archivo in sorted((RAIZ_REPOSITORIO / "src").glob("*.c")):
        for fallo in _incumplimientos_de_replicadas(archivo.read_text(encoding="utf-8")):
            fallos.append(f"{archivo.name}: {fallo}")
    assert fallos == []


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


def test_toda_fila_de_la_tabla_usa_una_de_las_cinco_formas() -> None:
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

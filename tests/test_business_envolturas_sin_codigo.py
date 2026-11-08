"""Las envolturas ``do { ... } while (0)`` sin codigo deben estar declaradas y contadas.

La tecnica solo se admite con condiciones: el comentario de cabecera de la funcion dice que la envoltura no
genera codigo y cierra el parrafo con una oracion fija que reconoce que se desconoce la forma del fuente
original, y ``docs/DESCOMPILACION.md`` lista la funcion con su numero de envolturas. Estas pruebas cruzan
``src/`` con esa tabla para que una envoltura nueva no entre sin su comentario ni sin su fila, y para que una
fila no sobreviva a la envoltura que describia. Solo leen archivos.
"""

import re
from pathlib import Path

from tools.proyecto import RAIZ_REPOSITORIO

FRASE_FIJA = "La forma del fuente original que producia este reparto se desconoce."
MARCADORES_SIN_CODIGO = ("no genera codigo", "no generan codigo")

_CIERRE_ENVOLTURA = re.compile(r"^\s*\}\s*while\s*\(0\)\s*;")
_DEFINICION = re.compile(r"^[A-Za-z_][\w \t\*]*?[\s\*](\w+)\([^;]*\)\s*\{?\s*$")
_FILA_TABLA = re.compile(r"^\|\s*`(\w+)`\s*\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|")


def _buscar_envolturas(texto: str) -> dict[str, int]:
    """Cuenta las envolturas por funcion, ignorando las que viven dentro de una macro."""
    lineas = texto.splitlines()
    cuentas: dict[str, int] = {}
    for indice, linea in enumerate(lineas):
        if not _CIERRE_ENVOLTURA.match(linea) or linea.rstrip().endswith("\\"):
            continue
        funcion = _funcion_que_contiene(lineas, indice)
        if funcion is not None:
            cuentas[funcion] = cuentas.get(funcion, 0) + 1
    return cuentas


def _funcion_que_contiene(lineas: list[str], indice: int) -> str | None:
    for anterior in range(indice, -1, -1):
        coincidencia = _DEFINICION.match(lineas[anterior])
        if coincidencia is not None:
            return coincidencia.group(1)
    return None


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
    """Lista las funciones con envoltura cuya cabecera no lleva el marcador y la oracion fija."""
    fallos: list[str] = []
    for funcion in _buscar_envolturas(texto):
        cabecera = " ".join(_cabecera(texto, funcion).replace("*", " ").split())
        if not any(marcador in cabecera for marcador in MARCADORES_SIN_CODIGO):
            fallos.append(f"{funcion}: la cabecera no dice que la envoltura no genera codigo")
        if FRASE_FIJA not in cabecera:
            fallos.append(f"{funcion}: la cabecera no lleva la oracion fija")
    return fallos


def _envolturas_en_src() -> dict[str, tuple[str, int]]:
    """Devuelve funcion -> (archivo relativo, envolturas) para todo ``src/*.c``."""
    resultado: dict[str, tuple[str, int]] = {}
    for archivo in sorted((RAIZ_REPOSITORIO / "src").glob("*.c")):
        texto = archivo.read_text(encoding="utf-8")
        for funcion, cantidad in _buscar_envolturas(texto).items():
            resultado[funcion] = (f"src/{archivo.name}", cantidad)
    return resultado


def _tabla_del_documento() -> dict[str, tuple[str, int]]:
    """Lee la tabla de ``## Envolturas sin código`` como funcion -> (archivo, envolturas)."""
    texto = (RAIZ_REPOSITORIO / "docs" / "DESCOMPILACION.md").read_text(encoding="utf-8")
    inicio = texto.index("## Envolturas sin código")
    siguiente = texto.find("\n## ", inicio + 1)
    seccion = texto[inicio : siguiente if siguiente != -1 else len(texto)]
    filas: dict[str, tuple[str, int]] = {}
    for linea in seccion.splitlines():
        coincidencia = _FILA_TABLA.match(linea)
        if coincidencia is not None:
            filas[coincidencia.group(1)] = (coincidencia.group(2), int(coincidencia.group(3)))
    return filas


def test_el_recuento_encuentra_las_envolturas_del_codigo_y_no_las_de_macros() -> None:
    texto = (
        "#define M(x) do { \\\n"
        "    x; \\\n"
        "} while (0);\n"
        "\n"
        "/* cabecera */\n"
        "s32 func_800000A0(s32 a)\n"
        "{\n"
        "    do {\n"
        "        a++;\n"
        "    } while (0);\n"
        "    return a;\n"
        "}\n"
    )
    assert _buscar_envolturas(texto) == {"func_800000A0": 1}


def test_toda_envoltura_declara_que_no_genera_codigo() -> None:
    fallos: list[str] = []
    for archivo in sorted((RAIZ_REPOSITORIO / "src").glob("*.c")):
        for fallo in _incumplimientos(archivo.read_text(encoding="utf-8")):
            if "no genera codigo" in fallo:
                fallos.append(f"{archivo.name}: {fallo}")
    assert fallos == []


def test_toda_envoltura_lleva_la_oracion_fija_de_forma_original_desconocida() -> None:
    fallos: list[str] = []
    for archivo in sorted((RAIZ_REPOSITORIO / "src").glob("*.c")):
        for fallo in _incumplimientos(archivo.read_text(encoding="utf-8")):
            if "oracion fija" in fallo:
                fallos.append(f"{archivo.name}: {fallo}")
    assert fallos == []


def test_la_tabla_de_envolturas_coincide_con_src() -> None:
    en_src = _envolturas_en_src()
    tabla = _tabla_del_documento()
    faltan = sorted(set(en_src) - set(tabla))
    assert faltan == [], f"funciones con envoltura que no estan en la tabla: {faltan}"
    for funcion, (archivo, cantidad) in en_src.items():
        assert tabla[funcion] == (archivo, cantidad), funcion


def test_toda_fila_de_la_tabla_corresponde_a_una_funcion_con_envolturas() -> None:
    sobran = sorted(set(_tabla_del_documento()) - set(_envolturas_en_src()))
    assert sobran == [], f"filas de la tabla sin envoltura en src: {sobran}"


def test_la_tabla_no_esta_vacia() -> None:
    assert _tabla_del_documento()


def test_una_envoltura_sin_la_frase_ni_el_marcador_se_detecta(tmp_path: Path) -> None:
    archivo = tmp_path / "inventado.c"
    archivo.write_text(
        "/*\n"
        " * Suma uno al parametro.\n"
        " */\n"
        "s32 func_800000B0(s32 a)\n"
        "{\n"
        "    do {\n"
        "        a++;\n"
        "    } while (0);\n"
        "    return a;\n"
        "}\n",
        encoding="utf-8",
    )
    fallos = _incumplimientos(archivo.read_text(encoding="utf-8"))
    assert len(fallos) == 2
    assert any("no genera codigo" in fallo for fallo in fallos)
    assert any("oracion fija" in fallo for fallo in fallos)


def test_una_envoltura_con_marcador_y_frase_en_la_cabecera_se_acepta(tmp_path: Path) -> None:
    archivo = tmp_path / "inventado.c"
    archivo.write_text(
        "/*\n"
        " * El do/while (0) no genera codigo: pondera por un nivel mas las referencias.\n"
        f" * {FRASE_FIJA}\n"
        " */\n"
        "s32 func_800000C0(s32 a)\n"
        "{\n"
        "    do {\n"
        "        a++;\n"
        "    } while (0);\n"
        "    return a;\n"
        "}\n",
        encoding="utf-8",
    )
    assert _incumplimientos(archivo.read_text(encoding="utf-8")) == []

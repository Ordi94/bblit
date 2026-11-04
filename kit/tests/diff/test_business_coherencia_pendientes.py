"""Reglas de negocio del aviso de coherencia: la linea de pendiente contra la ultima medicion de diff."""

import json
import os
from pathlib import Path
from typing import Any

import pytest
from psxdecomp.diff import coherencia_pendientes
from psxdecomp.dominio import construir_convenciones

from .ayudantes_variantes import CONVENCIONES, FUNCION, RUTAS

PENDIENTE = "/* Pendiente: puntuacion 120 con la configuracion versionada. Reparto de registros. */\n"


def bloque(funcion: str, cabecera: str, macro: str = "NON_MATCHING") -> str:
    """Bloque no coincidente con ``cabecera`` justo debajo del ``#ifdef``."""
    return (
        f"#ifdef {macro}\n{cabecera}s32 {funcion}(void)\n{{\n    return 0;\n}}\n#else\n"
        f'INCLUDE_ASM("ensamblador/pendientes/modulo_a", {funcion});\n#endif\n'
    )


def escribir_medicion(raiz: Path, contenido: Any, nombre: str = FUNCION) -> Path:
    ruta = raiz / "salida" / "diff" / f"{nombre}.resultado.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido if isinstance(contenido, str) else json.dumps(contenido), encoding="utf-8")
    return ruta


def medicion(puntuacion: int) -> dict[str, Any]:
    return {"funcion": FUNCION, "puntuacion": puntuacion, "maxLineas": 1024}


def preparar(raiz: Path, texto: str) -> None:
    (raiz / "codigo").mkdir()
    (raiz / "codigo" / "modulo_a.c").write_text(texto, encoding="utf-8")


def avisos(raiz: Path, convenciones: Any = CONVENCIONES) -> list[str]:
    texto = (raiz / "codigo" / "modulo_a.c").read_text(encoding="utf-8")
    return coherencia_pendientes.avisos_puntuacion_pendiente(
        raiz, {"codigo/modulo_a.c": texto}, rutas=RUTAS, convenciones=convenciones
    )


def leer(raiz: Path, referencia: float = 0.0) -> int | None:
    return coherencia_pendientes.leer_puntuacion_medida(raiz, FUNCION, referencia, rutas=RUTAS)


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    preparar(tmp_path, bloque(FUNCION, PENDIENTE))
    return tmp_path


def test_si_la_medicion_reciente_coincide_con_el_comentario_no_hay_aviso(raiz: Path) -> None:
    escribir_medicion(raiz, medicion(120))
    assert avisos(raiz) == []


def test_cifra_de_pendiente_distinta_de_la_medida_genera_aviso_con_ambas_cifras(raiz: Path) -> None:
    escribir_medicion(raiz, medicion(340))
    assert avisos(raiz) == [
        "codigo/modulo_a.c:1 rutina_a: el comentario Pendiente dice 120 y la ultima medicion de diff da 340"
    ]


def test_sin_medicion_no_se_avisa_ni_se_crea_la_carpeta_de_salida(raiz: Path) -> None:
    assert avisos(raiz) == []
    assert not (raiz / "salida").exists()


def test_una_medicion_obsoleta_anterior_a_la_ultima_edicion_del_c_no_se_contrasta(raiz: Path) -> None:
    ruta = escribir_medicion(raiz, medicion(340))
    antes = (raiz / "codigo" / "modulo_a.c").stat().st_mtime - 100
    os.utime(ruta, (antes, antes))
    assert avisos(raiz) == []
    assert leer(raiz, referencia=antes + 50) is None


def test_una_medicion_con_la_misma_fecha_que_el_c_si_se_contrasta(raiz: Path) -> None:
    ruta = escribir_medicion(raiz, medicion(340))
    igual = (raiz / "codigo" / "modulo_a.c").stat().st_mtime
    os.utime(ruta, (igual, igual))
    assert len(avisos(raiz)) == 1


def test_una_medicion_truncada_no_se_contrasta_con_el_comentario(raiz: Path) -> None:
    escribir_medicion(raiz, {**medicion(340), "truncado": True})
    assert avisos(raiz) == []
    assert leer(raiz) is None
    escribir_medicion(raiz, {**medicion(340), "truncado": False})
    assert len(avisos(raiz)) == 1
    assert leer(raiz) == 340


@pytest.mark.parametrize(
    "contenido",
    [
        "no es json",
        "[]",
        {"funcion": "otra", "puntuacion": 340},
        {"funcion": FUNCION, "puntuacion": "340"},
        {"funcion": FUNCION, "puntuacion": -1},
        {"funcion": FUNCION, "puntuacion": True},
        {"funcion": FUNCION},
        "x" * (coherencia_pendientes.MAX_BYTES_RESULTADO + 1),
    ],
)
def test_una_medicion_ilegible_o_de_otra_funcion_se_ignora(raiz: Path, contenido: Any) -> None:
    escribir_medicion(raiz, contenido)
    assert leer(raiz) is None
    assert avisos(raiz) == []


def test_una_medicion_en_el_limite_de_tamano_aun_se_lee(raiz: Path) -> None:
    base = json.dumps(medicion(120))
    relleno = " " * (coherencia_pendientes.MAX_BYTES_RESULTADO - len(base))
    escribir_medicion(raiz, base + relleno)
    assert leer(raiz) == 120


def test_la_medicion_cero_es_valida(raiz: Path) -> None:
    escribir_medicion(raiz, medicion(0))
    assert leer(raiz) == 0
    assert len(avisos(raiz)) == 1


def test_un_bloque_sin_linea_pendiente_no_genera_aviso(tmp_path: Path) -> None:
    preparar(tmp_path, bloque(FUNCION, ""))
    escribir_medicion(tmp_path, medicion(340))
    assert avisos(tmp_path) == []


def test_un_archivo_ausente_o_un_nombre_invalido_se_omiten(tmp_path: Path) -> None:
    texto = bloque("f" * 65, PENDIENTE)
    preparar(tmp_path, texto)
    assert (
        coherencia_pendientes.avisos_puntuacion_pendiente(
            tmp_path, {"codigo/modulo_a.c": texto}, rutas=RUTAS, convenciones=CONVENCIONES
        )
        == []
    )
    assert (
        coherencia_pendientes.avisos_puntuacion_pendiente(
            tmp_path, {"codigo/no_existe.c": texto}, rutas=RUTAS, convenciones=CONVENCIONES
        )
        == []
    )


def test_los_avisos_salen_ordenados_por_archivo_y_por_linea(tmp_path: Path) -> None:
    (tmp_path / "codigo").mkdir()
    textos = {
        "codigo/b.c": bloque("rutina_b", PENDIENTE),
        "codigo/a.c": bloque("rutina_a", PENDIENTE) + bloque("rutina_c", PENDIENTE),
    }
    for archivo, texto in textos.items():
        (tmp_path / archivo).write_text(texto, encoding="utf-8")
    for nombre in ("rutina_a", "rutina_b", "rutina_c"):
        escribir_medicion(tmp_path, {"funcion": nombre, "puntuacion": 5}, nombre)
    resultado = coherencia_pendientes.avisos_puntuacion_pendiente(
        tmp_path, textos, rutas=RUTAS, convenciones=CONVENCIONES
    )
    assert [a.split(":")[0] + ":" + a.split(":")[1].split(" ")[0] for a in resultado] == [
        "codigo/a.c:1",
        "codigo/a.c:10",
        "codigo/b.c:1",
    ]


def test_la_medicion_se_busca_en_la_carpeta_de_build_que_declara_el_manifiesto(raiz: Path) -> None:
    ruta_por_defecto = raiz / "build" / "diff" / f"{FUNCION}.resultado.json"
    ruta_por_defecto.parent.mkdir(parents=True)
    ruta_por_defecto.write_text(json.dumps(medicion(340)), encoding="utf-8")
    assert avisos(raiz) == []
    escribir_medicion(raiz, medicion(340))
    assert len(avisos(raiz)) == 1


def test_la_macro_y_la_expresion_de_pendiente_del_manifiesto_deciden_que_se_contrasta(
    tmp_path: Path,
) -> None:
    convenciones = construir_convenciones(
        {"macro_no_coincidente": "NO_COINCIDE", "pendiente": r"\AFalta:\s*(\d+)\s+puntos\b"}
    )
    preparar(tmp_path, bloque(FUNCION, "/* Falta: 120 puntos */\n", macro="NO_COINCIDE"))
    escribir_medicion(tmp_path, medicion(340))
    assert avisos(tmp_path, convenciones) == [
        "codigo/modulo_a.c:1 rutina_a: el comentario Pendiente dice 120 y la ultima medicion de diff da 340"
    ]
    assert avisos(tmp_path, CONVENCIONES) == [], "con las convenciones por defecto no hay bloque"
    preparar_otra = tmp_path / "otra"
    preparar_otra.mkdir()
    preparar(preparar_otra, bloque(FUNCION, PENDIENTE, macro="NO_COINCIDE"))
    escribir_medicion(preparar_otra, medicion(340))
    assert avisos(preparar_otra, convenciones) == [], "la frase por defecto no cumple la expresion propia"

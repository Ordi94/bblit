import json
import os
from pathlib import Path

import pytest
from psxdecomp.permutador import estado as est


def estado() -> est.Estado:
    return est.Estado(
        "func_X", "src/a.c", 7, 645, 600, 580, ronda=3, iteraciones=12, rondas_sin_mejora=2, segundos=4.5
    )


def test_la_carpeta_de_estado_cuelga_de_build_permutar() -> None:
    assert est.carpeta_de(Path("repo"), "func_X") == Path("repo/build/permutar/func_X")


def test_guardar_y_cargar_el_estado_conserva_todos_los_campos(tmp_path: Path) -> None:
    est.guardar_estado(tmp_path, estado())
    assert est.cargar_estado(tmp_path, "func_X") == estado()
    datos = json.loads((tmp_path / "estado.json").read_text(encoding="utf-8"))
    assert datos["puntuacionPartida"] == 645
    assert datos["rondasSinMejora"] == 2
    assert datos["version"] == est.VERSION_ESTADO


def test_cargar_sin_estado_dice_que_no_hay_busqueda_anterior(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no hay una busqueda anterior de 'func_X'"):
        est.cargar_estado(tmp_path, "func_X")


@pytest.mark.parametrize(
    ("cambio", "mensaje"),
    [
        ({"version": 9}, "version que esta herramienta no entiende"),
        ({"funcion": "otra"}, "pertenece a otra funcion"),
        ({"archivo": ""}, "'archivo' debe ser un texto no vacio"),
        ({"semilla": -1}, "'semilla' debe ser un entero no negativo"),
        ({"iteraciones": True}, "'iteraciones' debe ser un entero no negativo"),
        ({"ronda": "3"}, "'ronda' debe ser un entero no negativo"),
        ({"segundos": -1}, "'segundos' debe ser un numero no negativo"),
        ({"segundos": True}, "'segundos' debe ser un numero no negativo"),
    ],
)
def test_un_estado_manipulado_se_rechaza(tmp_path: Path, cambio: dict[str, object], mensaje: str) -> None:
    est.guardar_estado(tmp_path, estado())
    datos = json.loads((tmp_path / "estado.json").read_text(encoding="utf-8"))
    datos.update(cambio)
    (tmp_path / "estado.json").write_text(json.dumps(datos), encoding="utf-8")
    with pytest.raises(ValueError, match=mensaje):
        est.cargar_estado(tmp_path, "func_X")


def test_un_estado_que_no_es_json_ni_un_objeto_se_rechaza(tmp_path: Path) -> None:
    (tmp_path / "estado.json").write_text("{no es json", encoding="utf-8")
    with pytest.raises(ValueError, match="no es JSON valido"):
        est.cargar_estado(tmp_path, "func_X")
    (tmp_path / "estado.json").write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError, match="version que esta herramienta no entiende"):
        est.cargar_estado(tmp_path, "func_X")


def test_actual_se_guarda_y_se_lee_sin_el_salto_final(tmp_path: Path) -> None:
    est.guardar_actual(tmp_path, "s32 f(void)\n{\n}")
    assert (tmp_path / "actual.c").read_text(encoding="utf-8") == "s32 f(void)\n{\n}\n"
    assert est.cargar_actual(tmp_path) == "s32 f(void)\n{\n}"


def test_cargar_actual_sin_archivo_falla(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"falta actual\.c"):
        est.cargar_actual(tmp_path)


def test_mejor_lleva_un_comentario_con_su_puntuacion(tmp_path: Path) -> None:
    ruta = est.guardar_mejor(tmp_path / "nueva", "s32 f(void)\n{\n}", 10, 645)
    assert ruta == tmp_path / "nueva" / "mejor.c"
    texto = ruta.read_text(encoding="utf-8")
    assert (
        texto
        == "/* Candidato del permutador: puntuacion 10 (el C original puntua 645). */\ns32 f(void)\n{\n}\n"
    )


def test_el_registro_agrega_una_linea_por_mejora(tmp_path: Path) -> None:
    est.anadir_registro(tmp_path / "x", 5, 600, ["orden_sentencias(posiciones 1 y 2)"])
    est.anadir_registro(tmp_path / "x", 9, 590, ["a", "b"])
    lineas = (tmp_path / "x" / "registro.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(linea) for linea in lineas] == [
        {"iteracion": 5, "puntuacion": 600, "mutaciones": ["orden_sentencias(posiciones 1 y 2)"]},
        {"iteracion": 9, "puntuacion": 590, "mutaciones": ["a", "b"]},
    ]


def test_reiniciar_borra_solo_los_archivos_propios(tmp_path: Path) -> None:
    for nombre in est.ARCHIVOS_DEL_ESTADO:
        (tmp_path / nombre).write_text("x", encoding="utf-8")
    (tmp_path / "ajeno.txt").write_text("y", encoding="utf-8")
    est.reiniciar(tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["ajeno.txt"]
    est.reiniciar(tmp_path)


def test_una_escritura_interrumpida_deja_el_estado_anterior_y_ningun_temporal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    est.guardar_estado(tmp_path, estado())
    anterior = (tmp_path / "estado.json").read_text(encoding="utf-8")

    def fallar(origen: object, destino: object) -> None:
        raise OSError("disco lleno")

    monkeypatch.setattr(os, "replace", fallar)
    with pytest.raises(OSError, match="disco lleno"):
        est.guardar_estado(tmp_path, est.Estado("func_X", "src/a.c", 1, 1, 1, 1))
    assert (tmp_path / "estado.json").read_text(encoding="utf-8") == anterior
    assert [p.name for p in tmp_path.iterdir()] == ["estado.json"]


def test_la_carpeta_de_estado_respeta_la_carpeta_de_build_del_proyecto() -> None:
    assert est.carpeta_de(Path("repo"), "func_X", "salida") == Path("repo/salida/permutar/func_X")

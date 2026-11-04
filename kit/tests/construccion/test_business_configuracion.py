"""Reglas de negocio de la infraestructura: configuracion, enlace con ``_gp`` y varios simbolos."""

from pathlib import Path
from typing import Any

import pytest
from psxdecomp.construccion import infraestructura as infra
from psxdecomp.dominio import construir_convenciones, construir_rutas

from .test_infraestructura import (
    CONVENCIONES,
    EJECUTABLE,
    REFERENCIA,
    RUTAS,
    SALIDAS,
    Registro,
    herramientas,
)

RUTAS_PROPIAS = construir_rutas(
    {
        "fuentes": "codigo",
        "splat": "datos/particion.yaml",
        "simbolos": ["datos/a.txt", "datos/b.txt"],
        "opciones_compilacion": "datos/opciones.toml",
    }
)
SIMBOLOS_A = "rutina_a = 0x80100010; // type:func\nrutina_b = 0x80100020; // type:func\n"
SIMBOLOS_B = "rutina_b = 0x80100030; // type:func\nrutina_c = 0x80100040; // type:func\n"


def escribir(raiz: Path, relativa: str, texto: str) -> None:
    ruta = raiz / relativa
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


# --- Particion declarada --------------------------------------------------------------------------


def test_sin_archivo_de_particion_ningun_c_declara_secciones(tmp_path: Path) -> None:
    assert infra.leer_secciones_declaradas(tmp_path, rutas=RUTAS) == {}


def test_la_particion_declara_rodata_solo_para_el_c_que_tiene_ese_subsegmento(tmp_path: Path) -> None:
    escribir(
        tmp_path,
        "datos/particion.yaml",
        "segments:\n  - subsegments:\n      - [0x0, c, modulo_a]\n      - [0x10, .rodata, modulo_a]\n"
        "      - [0x20, c, modulo_b]\n",
    )
    declaradas = infra.leer_secciones_declaradas(tmp_path, rutas=RUTAS_PROPIAS)
    assert declaradas == {"modulo_a": frozenset({".text", ".rodata"}), "modulo_b": frozenset({".text"})}


def test_una_particion_con_yaml_invalido_se_rechaza_sin_citar_su_contenido(tmp_path: Path) -> None:
    escribir(tmp_path, "datos/particion.yaml", "segments: [sin cerrar\n")
    with pytest.raises(ValueError, match=r"^datos/particion.yaml no es YAML valido$"):
        infra.leer_secciones_declaradas(tmp_path, rutas=RUTAS_PROPIAS)


# --- Opciones de compilacion -----------------------------------------------------------------------


def test_sin_archivo_de_opciones_se_compila_con_g0_y_sin_gp_ni_datos_pequenos(tmp_path: Path) -> None:
    assert infra.leer_valores_g(tmp_path, rutas=RUTAS, convenciones=CONVENCIONES) == {}
    assert infra.leer_gp(tmp_path, rutas=RUTAS) is None
    assert infra.leer_datos_pequenos(tmp_path, rutas=RUTAS, convenciones=CONVENCIONES) == {}


def test_las_opciones_declaran_g_por_archivo_gp_y_datos_pequenos(tmp_path: Path) -> None:
    escribir(
        tmp_path,
        "datos/opciones.toml",
        "[archivos.modulo_a]\ng = 8\n\n[enlace]\ngp = 0x80100800\n\n"
        "[datos_pequenos]\nD_80100810 = 0x80100810\n",
    )
    assert infra.leer_valores_g(tmp_path, rutas=RUTAS_PROPIAS, convenciones=CONVENCIONES) == {"modulo_a": 8}
    assert infra.leer_gp(tmp_path, rutas=RUTAS_PROPIAS) == 0x80100800
    assert infra.leer_datos_pequenos(tmp_path, rutas=RUTAS_PROPIAS, convenciones=CONVENCIONES) == {
        "D_80100810": 0x80100810
    }


def test_el_tope_de_g_lo_fija_la_convencion_del_proyecto(tmp_path: Path) -> None:
    escribir(tmp_path, "datos/opciones.toml", "[archivos.modulo_a]\ng = 8\n")
    estrechas = construir_convenciones({"max_valor_g": 4})
    with pytest.raises(ValueError, match="modulo_a"):
        infra.leer_valores_g(tmp_path, rutas=RUTAS_PROPIAS, convenciones=estrechas)


def test_un_archivo_de_opciones_que_no_es_toml_o_excede_la_cota_se_rechaza(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    escribir(tmp_path, "datos/opciones.toml", "esto = = no es toml\n")
    with pytest.raises(ValueError, match=r"^datos/opciones.toml no es TOML valido$"):
        infra.leer_gp(tmp_path, rutas=RUTAS_PROPIAS)
    monkeypatch.setattr(infra, "MAX_BYTES_REFERENCIA", 3)
    with pytest.raises(ValueError, match=r"^datos/opciones.toml excede el tamano permitido$"):
        infra.leer_gp(tmp_path, rutas=RUTAS_PROPIAS)


# --- Simbolos ---------------------------------------------------------------------------------------


def test_los_archivos_de_simbolos_se_combinan_en_orden_y_el_ultimo_manda(tmp_path: Path) -> None:
    escribir(tmp_path, "datos/a.txt", SIMBOLOS_A)
    escribir(tmp_path, "datos/b.txt", SIMBOLOS_B)
    direcciones = infra.leer_direcciones_de_funciones(
        tmp_path, rutas=RUTAS_PROPIAS, convenciones=CONVENCIONES
    )
    assert direcciones == {"rutina_a": 0x80100010, "rutina_b": 0x80100030, "rutina_c": 0x80100040}


def test_un_archivo_de_simbolos_ausente_se_omite_y_sin_ninguno_no_hay_direcciones(tmp_path: Path) -> None:
    assert infra.leer_direcciones_de_funciones(tmp_path, rutas=RUTAS_PROPIAS, convenciones=CONVENCIONES) == {}
    escribir(tmp_path, "datos/b.txt", SIMBOLOS_B)
    direcciones = infra.leer_direcciones_de_funciones(
        tmp_path, rutas=RUTAS_PROPIAS, convenciones=CONVENCIONES
    )
    assert direcciones == {"rutina_b": 0x80100030, "rutina_c": 0x80100040}


def test_un_archivo_de_simbolos_que_excede_la_cota_se_rechaza_nombrando_su_ruta_relativa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    escribir(tmp_path, "datos/a.txt", SIMBOLOS_A)
    monkeypatch.setattr(infra, "MAX_BYTES_SIMBOLOS", 4)
    with pytest.raises(ValueError, match=r"^datos/a.txt excede el tamano permitido$"):
        infra.leer_direcciones_de_funciones(tmp_path, rutas=RUTAS_PROPIAS, convenciones=CONVENCIONES)


def test_verificar_configuracion_exige_todos_los_archivos_de_simbolos_declarados(tmp_path: Path) -> None:
    escribir(tmp_path, "datos/a.txt", SIMBOLOS_A)
    with pytest.raises(FileNotFoundError, match=r"^falta datos/b.txt$"):
        infra.verificar_configuracion(tmp_path, rutas=RUTAS_PROPIAS, convenciones=CONVENCIONES)


def test_verificar_configuracion_avisa_de_datos_pequenos_ya_declarados_citando_los_archivos(
    tmp_path: Path,
) -> None:
    escribir(tmp_path, "datos/a.txt", "D_80100810 = 0x80100810; // type:u8\n")
    escribir(tmp_path, "datos/b.txt", SIMBOLOS_B)
    escribir(tmp_path, "datos/opciones.toml", "[datos_pequenos]\nD_80100810 = 0x80100810\n")
    avisos = infra.verificar_configuracion(tmp_path, rutas=RUTAS_PROPIAS, convenciones=CONVENCIONES)
    assert len(avisos) == 1
    assert "D_80100810" in avisos[0] and "datos/a.txt, datos/b.txt" in avisos[0]


def test_verificar_configuracion_sin_datos_pequenos_no_avisa(tmp_path: Path) -> None:
    escribir(tmp_path, "datos/a.txt", SIMBOLOS_A)
    escribir(tmp_path, "datos/b.txt", SIMBOLOS_B)
    assert infra.verificar_configuracion(tmp_path, rutas=RUTAS_PROPIAS, convenciones=CONVENCIONES) == []


# --- Particion y construccion ------------------------------------------------------------------------


def test_listar_fuentes_c_usa_la_carpeta_de_fuentes_del_manifiesto_y_cita_su_ruta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    escribir(tmp_path, "codigo/a.c", "a")
    escribir(tmp_path, "src/otro.c", "no se lee")
    assert infra.listar_fuentes_c(tmp_path, rutas=RUTAS_PROPIAS) == {"codigo/a.c": "a"}
    monkeypatch.setattr(infra, "MAX_BYTES_FUENTE", 0)
    with pytest.raises(ValueError, match=r"^codigo/a.c excede el tamano permitido$"):
        infra.listar_fuentes_c(tmp_path, rutas=RUTAS_PROPIAS)


def test_dividir_concatena_los_archivos_de_simbolos_existentes_para_el_simbolo_de_entrada(
    tmp_path: Path,
) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    original = tmp_path / "disco" / "fs" / "PRUEBA.EXE"
    original.parent.mkdir(parents=True)
    original.write_bytes(EJECUTABLE)
    escribir(raiz, "datos/a.txt", "inicio = 0x80100008; // type:func\n")
    ejecutor = Registro()
    infra.dividir(
        raiz, original, REFERENCIA, herramientas(), ejecutor, rutas=RUTAS_PROPIAS, convenciones=CONVENCIONES
    )
    assert (raiz / SALIDAS.simbolos_entrada).read_text(encoding="utf-8") == ""
    assert ejecutor.comandos == [["py", "-X", "utf8", "-m", "splat", "split", "datos/particion.yaml"]]


class RegistroConC(Registro):
    """Simula un enlazador cuyo script incluye un objeto compilado desde C."""

    def __call__(self, comando: Any, directorio: Any, timeout_s: Any) -> Any:
        if "splat" in comando:
            salida = super().__call__(comando, directorio, timeout_s)
            script = directorio / SALIDAS.script_enlazador
            script.write_text(
                script.read_text(encoding="utf-8") + "    build/src/modulo_a.c.o(.text);\n", encoding="utf-8"
            )
            escribir(directorio, "src/modulo_a.c", "int x;")
            return salida
        return super().__call__(comando, directorio, timeout_s)


def test_un_fuente_c_en_el_script_sin_compilador_disponible_se_rechaza(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    ruta = tmp_path / "disco" / "fs" / "PRUEBA.EXE"
    ruta.parent.mkdir(parents=True)
    ruta.write_bytes(EJECUTABLE)
    infra.dividir(
        raiz, ruta, REFERENCIA, herramientas(), RegistroConC(), rutas=RUTAS, convenciones=CONVENCIONES
    )
    escribir(raiz, "asm/data/datos.s", "d")
    with pytest.raises(ValueError, match=r"el fuente 'src/modulo_a.c' es C y no hay compilador disponible"):
        infra.construir(raiz, REFERENCIA, herramientas(), Registro(), rutas=RUTAS, convenciones=CONVENCIONES)


def test_construir_con_compilador_delega_los_c_y_enlaza_con_gp_y_simbolos_automaticos(tmp_path: Path) -> None:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    ruta = tmp_path / "disco" / "fs" / "PRUEBA.EXE"
    ruta.parent.mkdir(parents=True)
    ruta.write_bytes(EJECUTABLE)
    infra.dividir(
        raiz, ruta, REFERENCIA, herramientas(), RegistroConC(), rutas=RUTAS, convenciones=CONVENCIONES
    )
    escribir(raiz, "asm/data/datos.s", "d")
    escribir(
        raiz,
        RUTAS.opciones_compilacion,
        "[enlace]\ngp = 0x80100800\n\n[datos_pequenos]\nD_80100810 = 0x80100810\n",
    )
    compilados: list[tuple[str, str]] = []
    ejecutor = Registro()
    destino = infra.construir_con_compilador(
        raiz,
        REFERENCIA,
        herramientas(),
        lambda fuente, objeto: compilados.append((fuente, objeto)),
        ejecutor,
        rutas=RUTAS,
        convenciones=CONVENCIONES,
    )
    assert destino == raiz / SALIDAS.ejecutable
    assert compilados == [("src/modulo_a.c", "build/src/modulo_a.c.o")]
    texto_gp = (raiz / SALIDAS.script_gp).read_text(encoding="utf-8")
    assert "_gp = 0x80100800;" in texto_gp and "D_80100810 = 0x80100810;" in texto_gp
    enlazado = next(c for c in ejecutor.comandos if Path(c[0]).name == "ld.exe")
    assert enlazado.count("-T") == 3 and SALIDAS.script_gp in enlazado
    assert enlazado.index(SALIDAS.script_enlazador) < enlazado.index(SALIDAS.script_gp)


def test_las_salidas_de_enlace_y_los_artefactos_siguen_el_nombre_del_ejecutable(tmp_path: Path) -> None:
    assert infra.salidas_de_enlace("EJEC_001.00", rutas=RUTAS) == (
        "build/EJEC_001.00",
        "build/EJEC_001.bin",
        "build/EJEC_001.elf",
        "build/EJEC_001.map",
    )
    artefactos = infra.artefactos_de_build("EJEC_001.00", rutas=RUTAS)
    assert "build/EJEC_001.ld" in artefactos and "build/gp.ld" in artefactos
    assert len(set(artefactos)) == len(artefactos)
    escribir(tmp_path, "build/EJEC_001.elf", "x")
    escribir(tmp_path, "build/EJEC_001.00", "x")
    escribir(tmp_path, "build/ajeno.bin", "x")
    assert infra.invalidar_salida(tmp_path, "EJEC_001.00", rutas=RUTAS) == [
        "build/EJEC_001.00",
        "build/EJEC_001.elf",
    ]
    assert (tmp_path / "build" / "ajeno.bin").is_file()

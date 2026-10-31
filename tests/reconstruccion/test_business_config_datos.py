"""Reglas de negocio de la configuracion: nota del lock y aviso de datos pequenos ya declarados."""

import hashlib
import json
from pathlib import Path

import pytest
from tools.reconstruccion import cli, dominio
from tools.reconstruccion import infraestructura as infra
from tools.reconstruccion.dominio import SimboloDeclarado

RAIZ_REPO = Path(__file__).resolve().parents[2]
SIMBOLOS = (
    "// tabla de ejemplo\n"
    "func_80014AC4 = 0x80014AC4; // type:func size:0x10\n"
    "D_80069330 = 0x80069330; // type:u8 size:0x8\n"
    "D_80069338 = 0x80069338; // size:0x1\n"
    "OtroNombre = 0x80069380; // type:u32 size:0x4\n"
    "esto no es un simbolo\n"
)


def preparar(raiz: Path, toml: str | None, simbolos: str | None = SIMBOLOS) -> None:
    (raiz / "config").mkdir(exist_ok=True)
    if simbolos is not None:
        (raiz / "config" / "symbols.txt").write_text(simbolos, encoding="utf-8")
    if toml is not None:
        (raiz / "config" / "opciones_compilacion.toml").write_text(toml, encoding="utf-8")


def test_los_simbolos_declarados_se_agrupan_por_direccion_e_ignoran_lo_que_no_es_simbolo() -> None:
    declarados = dominio.simbolos_declarados(SIMBOLOS)
    assert declarados[0x80014AC4] == [SimboloDeclarado("func_80014AC4", "func")]
    assert declarados[0x80069330] == [SimboloDeclarado("D_80069330", "u8")]
    assert declarados[0x80069338] == [SimboloDeclarado("D_80069338", "")]
    assert len(declarados) == 4


def test_varios_simbolos_en_una_misma_direccion_se_conservan_en_orden() -> None:
    texto = "A = 0x80069330; // type:u8\nB = 0x80069330; // type:u16\n"
    assert dominio.simbolos_declarados(texto)[0x80069330] == [
        SimboloDeclarado("A", "u8"),
        SimboloDeclarado("B", "u16"),
    ]


def test_una_clave_con_el_mismo_nombre_y_tipo_de_dato_se_avisa_como_retirable() -> None:
    avisos = dominio.avisos_datos_pequenos({"D_80069330": 0x80069330}, dominio.simbolos_declarados(SIMBOLOS))
    assert avisos == [
        "[datos_pequenos] D_80069330 = 0x80069330: mismo nombre: ya figura en config/symbols.txt, "
        "la clave puede retirarse"
    ]


def test_una_clave_cuya_direccion_tiene_otro_nombre_se_avisa_con_el_nombre_de_la_tabla() -> None:
    avisos = dominio.avisos_datos_pequenos({"D_80069380": 0x80069380}, dominio.simbolos_declarados(SIMBOLOS))
    assert avisos == [
        "[datos_pequenos] D_80069380 = 0x80069380: otro nombre: "
        "config/symbols.txt declara OtroNombre en esa direccion"
    ]


def test_una_clave_declarada_como_funcion_en_la_tabla_se_avisa_como_otro_tipo() -> None:
    declarados = dominio.simbolos_declarados(SIMBOLOS)
    avisos = dominio.avisos_datos_pequenos({"func_80014AC4": 0x80014AC4}, declarados)
    assert avisos == [
        "[datos_pequenos] func_80014AC4 = 0x80014AC4: otro tipo: config/symbols.txt lo declara como funcion"
    ]


def test_una_clave_sin_simbolo_en_la_tabla_no_genera_aviso() -> None:
    declarados = dominio.simbolos_declarados(SIMBOLOS)
    assert dominio.avisos_datos_pequenos({"D_800694A8": 0x800694A8}, declarados) == []
    assert dominio.avisos_datos_pequenos({}, declarados) == []


def test_cada_simbolo_repetido_de_una_misma_direccion_genera_su_aviso() -> None:
    declarados = dominio.simbolos_declarados(
        "D_80069330 = 0x80069330; // type:u8\nAlias = 0x80069330; // type:u8\n"
    )
    avisos = dominio.avisos_datos_pequenos({"D_80069330": 0x80069330}, declarados)
    assert [a.split(": ", 1)[1].split(":")[0] for a in avisos] == ["mismo nombre", "otro nombre"]


def test_verificar_configuracion_lee_el_toml_y_la_tabla_del_repositorio(tmp_path: Path) -> None:
    preparar(tmp_path, "[datos_pequenos]\nD_80069330 = 0x80069330\nD_800694A8 = 0x800694A8\n")
    avisos = infra.verificar_configuracion(tmp_path)
    assert len(avisos) == 1 and "D_80069330" in avisos[0]


def test_sin_tabla_datos_pequenos_o_sin_toml_no_hay_avisos(tmp_path: Path) -> None:
    preparar(tmp_path, None)
    assert infra.verificar_configuracion(tmp_path) == []
    preparar(tmp_path, "[enlace]\ngp = 0x80069320\n")
    assert infra.verificar_configuracion(tmp_path) == []


def test_sin_symbols_txt_la_verificacion_lo_dice(tmp_path: Path) -> None:
    preparar(tmp_path, "[datos_pequenos]\nD_80069330 = 0x80069330\n", simbolos=None)
    with pytest.raises(FileNotFoundError, match=r"falta config/symbols.txt"):
        infra.verificar_configuracion(tmp_path)


def test_un_symbols_txt_demasiado_grande_se_rechaza(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    preparar(tmp_path, None)
    monkeypatch.setattr(infra, "MAX_BYTES_SIMBOLOS", 4)
    with pytest.raises(ValueError, match="excede el tamano permitido"):
        infra.verificar_configuracion(tmp_path)


def test_un_toml_con_claves_duplicadas_se_rechaza_sin_traza(tmp_path: Path) -> None:
    preparar(tmp_path, "[datos_pequenos]\nD_80069330 = 0x80069330\nD_80069330 = 0x80069330\n")
    with pytest.raises(ValueError, match="no es TOML valido"):
        infra.verificar_configuracion(tmp_path)


def test_la_orden_verificar_config_falla_por_cada_duplicacion_y_no_modifica_nada(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    preparar(tmp_path, "[datos_pequenos]\nD_80069330 = 0x80069330\nD_80069380 = 0x80069380\n")
    antes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path / "config").iterdir()}
    assert cli.main(["verificar-config"], {}, tmp_path) == 1
    salida = capsys.readouterr()
    assert salida.out == "verificar-config: 2 errores\n"
    assert salida.err.count("error: [datos_pequenos]") == 2
    despues = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path / "config").iterdir()}
    assert antes == despues
    assert sorted(p.name for p in tmp_path.iterdir()) == ["config"]


def test_la_orden_verificar_config_sin_duplicaciones_sale_limpia(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    preparar(tmp_path, "[datos_pequenos]\nD_800699AA = 0x800699AA\n")
    assert cli.main(["verificar-config"], {}, tmp_path) == 0
    salida = capsys.readouterr()
    assert (salida.out, salida.err) == ("verificar-config: 0 errores\n", "")


def test_split_sigue_avisando_de_la_duplicacion_sin_fallar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    preparar(tmp_path, "[datos_pequenos]\nD_80069330 = 0x80069330\n")
    cli._avisar_configuracion(tmp_path)
    assert capsys.readouterr().err.startswith("aviso: [datos_pequenos] D_80069330")


def test_la_orden_verificar_config_con_un_toml_invalido_es_un_error_y_no_un_aviso(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    preparar(tmp_path, "esto no es toml [")
    assert cli.main(["verificar-config"], {}, tmp_path) == 1
    salida = capsys.readouterr()
    assert salida.out == ""
    assert salida.err == "error: config/opciones_compilacion.toml no es TOML valido\n"


def test_la_orden_verificar_config_sin_symbols_txt_es_un_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    preparar(tmp_path, "[datos_pequenos]\nD_80069330 = 0x80069330\n", simbolos=None)
    assert cli.main(["verificar-config"], {}, tmp_path) == 1
    assert capsys.readouterr().err == "error: falta config/symbols.txt\n"


def test_el_repositorio_no_repite_en_datos_pequenos_nada_que_symbols_txt_ya_declare() -> None:
    assert infra.verificar_configuracion(RAIZ_REPO) == []


def test_la_nota_del_lock_dice_aspsx_279_y_las_huellas_no_cambian() -> None:
    lock = json.loads((RAIZ_REPO / "config" / "toolchain.lock.json").read_text(encoding="utf-8"))
    sdk = lock["componentes"]["psyq-4.4"]
    assert "ASPSX 2.79" in sdk["notas"] and "2.86" not in sdk["notas"]
    assert sdk["sha256"] == "75d20b9d31372ff0629482f30ee27edd726eaa57d8be39fa0d93e583144063f7"
    assert lock["componentes"]["maspsx"]["sha256"] == (
        "ef60294812d9e4bf6f97ccac973102ebedcc233b8afbccab770be6eac104713c"
    )

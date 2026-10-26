import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest
from tools.ghidra.ejecucion import (
    CARGADOR_PSX,
    RAIZ_REPOSITORIO,
    SIN_VALOR,
    VERSIONES_FIRMAS,
    Carga,
    ConfiguracionGhidra,
    ResultadoEjecucion,
    construir_comando_analisis,
    construir_comando_exportacion,
    ejecutar_analisis,
    ejecutar_exportacion,
    ejecutar_proceso,
    resolver_ejecutable,
    resolver_instalacion,
    verificar_carga,
)
from tools.reconstruccion import infraestructura

REGISTRO_VALIDO = (
    "INFO  Using Loader: PSX Executables Loader (ProgramLoader)\n"
    "INFO  PrepararAnalisis.java> BBLIT base=0x80014A00 (GhidraScript)\n"
    "INFO  PrepararAnalisis.java> BBLIT fin=0x800699FF (GhidraScript)\n"
    "INFO  PrepararAnalisis.java> BBLIT entrada=0x80014A08 (GhidraScript)\n"
)


@pytest.fixture
def config(tmp_path: Path) -> ConfiguracionGhidra:
    instalacion = tmp_path / "ghidra con espacios"
    (instalacion / "support").mkdir(parents=True)
    return ConfiguracionGhidra(
        instalacion=instalacion,
        proyecto=tmp_path / "proyecto",
        scripts=tmp_path / "scripts",
    )


class EjecutorDoble:
    """Sustituye al proceso de Ghidra: registra la llamada y devuelve un resultado fijo."""

    def __init__(self, resultado: ResultadoEjecucion, *, crear: Path | None = None) -> None:
        self.resultado = resultado
        self.crear = crear
        self.llamadas: list[tuple[list[str], int]] = []

    def __call__(self, comando: Sequence[str], segundos: int) -> ResultadoEjecucion:
        self.llamadas.append((list(comando), segundos))
        if self.crear is not None:
            self.crear.write_text("direccion\n", encoding="utf-8")
        return self.resultado


def test_lanzador_usa_bat_en_windows_y_sin_extension_en_otros(
    config: ConfiguracionGhidra, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    assert config.lanzador == config.instalacion / "support" / "analyzeHeadless.bat"
    monkeypatch.setattr(sys, "platform", "linux")
    assert config.lanzador == config.instalacion / "support" / "analyzeHeadless"


def test_resolver_instalacion_prefiere_el_argumento(config: ConfiguracionGhidra, tmp_path: Path) -> None:
    assert resolver_instalacion(config.instalacion, {"BBLIT_GHIDRA": str(tmp_path)}) == config.instalacion


def test_resolver_instalacion_usa_la_variable_de_entorno(config: ConfiguracionGhidra) -> None:
    assert resolver_instalacion(None, {"BBLIT_GHIDRA": str(config.instalacion)}) == config.instalacion


def test_resolver_instalacion_sin_ruta_pide_argumento_o_variable() -> None:
    with pytest.raises(ValueError, match=r"indique --ghidra o defina la variable BBLIT_GHIDRA"):
        resolver_instalacion(None, {})


def test_resolver_instalacion_exige_el_subdirectorio_support(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"la carpeta de Ghidra no contiene el subdirectorio support"):
        resolver_instalacion(tmp_path, {})


def test_resolver_ejecutable_con_argumento(tmp_path: Path) -> None:
    exe = tmp_path / "SLUS_008.38"
    exe.write_bytes(b"x")
    assert resolver_ejecutable(exe, {}) == exe


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    """Raiz de repositorio sintetica con la descripcion real del ejecutable."""
    carpeta = tmp_path / "repo"
    (carpeta / "config").mkdir(parents=True)
    origen = RAIZ_REPOSITORIO / "config" / "ejecutable.json"
    (carpeta / "config" / "ejecutable.json").write_bytes(origen.read_bytes())
    return carpeta


@pytest.fixture
def extraccion(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Sustituye la extraccion ISO 9660 por una que escribe un archivo y registra la imagen."""
    imagenes: list[Path] = []

    def doble(imagen: Path, _referencia: object, destino: Path) -> None:
        imagenes.append(imagen)
        destino.write_bytes(b"x")

    monkeypatch.setattr(infraestructura, "extraer_de_imagen", doble)
    return imagenes


def test_resolver_ejecutable_con_carpeta_de_sistema_de_archivos_extraido(tmp_path: Path, raiz: Path) -> None:
    exe = tmp_path / "disco" / "fs" / "SLUS_008.38"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"x")
    assert resolver_ejecutable(None, {"BBLIT_DISC": str(tmp_path / "disco")}, raiz) == exe


@pytest.mark.parametrize("forma", ["bin", "cue", "carpeta_del_bin", "carpeta_superior"])
def test_resolver_ejecutable_acepta_las_formas_de_imagen_de_bblit_disc(
    tmp_path: Path, raiz: Path, extraccion: list[Path], forma: str
) -> None:
    carpeta = tmp_path / "disco" / "juego"
    carpeta.mkdir(parents=True)
    imagen = carpeta / "juego.bin"
    imagen.write_bytes(b"x")
    (carpeta / "juego.cue").write_text("FILE", encoding="utf-8")
    indicado = {
        "bin": imagen,
        "cue": carpeta / "juego.cue",
        "carpeta_del_bin": carpeta,
        "carpeta_superior": tmp_path / "disco",
    }[forma]
    exe = resolver_ejecutable(None, {"BBLIT_DISC": str(indicado)}, raiz)
    assert exe == raiz / "expected" / "SLUS_008.38"
    assert exe.is_file()
    assert extraccion == [imagen]


def test_resolver_ejecutable_con_ruta_inexistente_falla_con_mensaje_claro(tmp_path: Path, raiz: Path) -> None:
    with pytest.raises(ValueError, match=r"^BBLIT_DISC: la ubicacion del disco no existe$"):
        resolver_ejecutable(None, {"BBLIT_DISC": str(tmp_path / "nada")}, raiz)


def test_resolver_ejecutable_sin_imagen_ni_fs_explica_que_se_busco(tmp_path: Path, raiz: Path) -> None:
    (tmp_path / "vacia").mkdir()
    with pytest.raises(ValueError, match=r"no se encontro fs/SLUS_008\.38 ni una imagen \.bin"):
        resolver_ejecutable(None, {"BBLIT_DISC": str(tmp_path / "vacia")}, raiz)


def test_resolver_ejecutable_con_imagen_ambigua_se_rechaza(tmp_path: Path, raiz: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"x")
    (tmp_path / "b.bin").write_bytes(b"x")
    with pytest.raises(ValueError, match=r"hay varias imagenes"):
        resolver_ejecutable(None, {"BBLIT_DISC": str(tmp_path)}, raiz)


def test_resolver_ejecutable_sin_ruta_pide_argumento_o_variable() -> None:
    with pytest.raises(ValueError, match=r"indique --exe o defina la variable BBLIT_DISC"):
        resolver_ejecutable(None, {})


def test_resolver_ejecutable_con_argumento_inexistente_nombra_solo_el_archivo(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"^el ejecutable SLUS_008\.38 no existe$"):
        resolver_ejecutable(tmp_path / "SLUS_008.38", {})


def test_comando_de_analisis_exacto(config: ConfiguracionGhidra, tmp_path: Path) -> None:
    exe = tmp_path / "disc" / "SLUS_008.38"
    semilla = tmp_path / "semilla.txt"
    comando = construir_comando_analisis(config, exe, semilla, ["4.6.0", "4.0.0"], 540)
    assert comando == [
        str(config.lanzador),
        str(config.proyecto),
        "bblit",
        "-import",
        str(exe),
        "-overwrite",
        "-loader",
        "PsxLoader",
        "-analysisTimeoutPerFile",
        "540",
        "-scriptPath",
        str(config.scripts),
        "-preScript",
        "PrepararAnalisis.java",
        str(semilla),
        "-postScript",
        "DescubrirFunciones.java",
        "-postScript",
        "AplicarFirmas.java",
        "4.6.0",
        "4.0.0",
    ]
    assert CARGADOR_PSX == "PsxLoader"


def test_comando_de_analisis_sin_semilla_ni_versiones(config: ConfiguracionGhidra, tmp_path: Path) -> None:
    comando = construir_comando_analisis(config, tmp_path / "SLUS_008.38", None, [], 60)
    assert comando[comando.index("-preScript") + 1 :] == [
        "PrepararAnalisis.java",
        SIN_VALOR,
        "-postScript",
        "DescubrirFunciones.java",
    ]


def test_versiones_por_defecto_son_las_documentadas() -> None:
    assert VERSIONES_FIRMAS == ("4.6.0", "4.0.0", "4.7.0", "4.4.0")


@pytest.mark.parametrize("version", ["4", "4.6.0.1", "v4.6", "4.6; calc", "", "4,6"])
def test_comando_de_analisis_rechaza_versiones_mal_formadas(
    config: ConfiguracionGhidra, tmp_path: Path, version: str
) -> None:
    with pytest.raises(ValueError, match=r"version de firmas invalida"):
        construir_comando_analisis(config, tmp_path / "SLUS_008.38", None, [version], 60)


@pytest.mark.parametrize("segundos", [0, 601, -5])
def test_comando_rechaza_tiempos_fuera_de_rango(
    config: ConfiguracionGhidra, tmp_path: Path, segundos: int
) -> None:
    with pytest.raises(ValueError, match=rf"segundos={segundos} fuera de rango 1\.\.600"):
        construir_comando_analisis(config, tmp_path / "SLUS_008.38", None, [], segundos)


@pytest.mark.parametrize("caracter", ["&", "|", "^", "%", '"', "<", ">", "\n"])
def test_comando_rechaza_caracteres_que_el_interprete_reinterpretaria(
    config: ConfiguracionGhidra, tmp_path: Path, caracter: str
) -> None:
    with pytest.raises(ValueError, match=r"ejecutable contiene caracteres no permitidos"):
        construir_comando_analisis(config, tmp_path / f"SLUS{caracter}", None, [], 60)


def test_comando_valida_tambien_el_proyecto_y_la_semilla(config: ConfiguracionGhidra, tmp_path: Path) -> None:
    malo = ConfiguracionGhidra(config.instalacion, tmp_path / "p&q", config.scripts)
    with pytest.raises(ValueError, match=r"proyecto contiene caracteres no permitidos"):
        construir_comando_analisis(malo, tmp_path / "SLUS", None, [], 60)
    with pytest.raises(ValueError, match=r"semilla contiene caracteres no permitidos"):
        construir_comando_analisis(config, tmp_path / "SLUS", tmp_path / "s|s", [], 60)


def test_comando_de_exportacion_exacto(config: ConfiguracionGhidra, tmp_path: Path) -> None:
    salida = tmp_path / "salida"
    comando = construir_comando_exportacion(
        config, "SLUS_008.38", salida, decompilar=True, segundos_por_funcion=30
    )
    assert comando == [
        str(config.lanzador),
        str(config.proyecto),
        "bblit",
        "-process",
        "SLUS_008.38",
        "-noanalysis",
        "-readOnly",
        "-scriptPath",
        str(config.scripts),
        "-postScript",
        "ExportarFunciones.java",
        str(salida),
        "si",
        "30",
    ]


def test_comando_de_exportacion_sin_decompilar(config: ConfiguracionGhidra, tmp_path: Path) -> None:
    comando = construir_comando_exportacion(
        config, "SLUS_008.38", tmp_path, decompilar=False, segundos_por_funcion=60
    )
    assert comando[-2:] == ["no", "60"]


def test_comando_de_exportacion_valida_programa_y_salida(config: ConfiguracionGhidra, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"programa contiene caracteres no permitidos"):
        construir_comando_exportacion(config, "a&b", tmp_path, decompilar=True, segundos_por_funcion=60)
    with pytest.raises(ValueError, match=r"salida contiene caracteres no permitidos"):
        construir_comando_exportacion(config, "a", tmp_path / "x%y", decompilar=True, segundos_por_funcion=60)


def test_ejecutar_proceso_captura_codigo_y_salida() -> None:
    resultado = ejecutar_proceso([sys.executable, "-c", "print('hola')"], 30)
    assert resultado == ResultadoEjecucion(0, "hola\n")


def test_ejecutar_proceso_combina_error_estandar_y_conserva_el_codigo() -> None:
    codigo = "import sys; print('a'); print('b', file=sys.stderr); sys.exit(3)"
    resultado = ejecutar_proceso([sys.executable, "-c", codigo], 30)
    assert resultado.codigo == 3
    assert sorted(resultado.salida.split()) == ["a", "b"]


def test_ejecutar_proceso_sin_entrada_estandar_no_se_bloquea() -> None:
    resultado = ejecutar_proceso([sys.executable, "-c", "import sys; print(repr(sys.stdin.read()))"], 30)
    assert resultado == ResultadoEjecucion(0, "''\n")


def test_ejecutar_proceso_termina_el_proceso_al_agotar_el_tiempo() -> None:
    with pytest.raises(TimeoutError, match=r"el proceso excedio 1 segundos"):
        ejecutar_proceso([sys.executable, "-c", "import time; time.sleep(60)"], 1)


def test_ejecutar_proceso_tolera_que_taskkill_no_exista(monkeypatch: pytest.MonkeyPatch) -> None:
    def sin_taskkill(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError("taskkill")

    monkeypatch.setattr(subprocess, "run", sin_taskkill)
    with pytest.raises(TimeoutError, match=r"el proceso excedio 1 segundos"):
        ejecutar_proceso([sys.executable, "-c", "import time; time.sleep(60)"], 1)


def test_ejecutar_proceso_invoca_taskkill_sobre_el_arbol(monkeypatch: pytest.MonkeyPatch) -> None:
    llamadas: list[list[str]] = []
    original = subprocess.run

    def espia(comando: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        llamadas.append(comando)
        return original([sys.executable, "-c", "pass"], capture_output=True, check=False)

    monkeypatch.setattr(subprocess, "run", espia)
    with pytest.raises(TimeoutError):
        ejecutar_proceso([sys.executable, "-c", "import time; time.sleep(60)"], 1)
    assert llamadas[0][0] == "taskkill"
    assert llamadas[0][3:] == ["/T", "/F"]


def test_verificar_carga_devuelve_base_y_entrada() -> None:
    assert verificar_carga(REGISTRO_VALIDO) == Carga(base=0x80014A00, entrada=0x80014A08)


def test_verificar_carga_exige_el_cargador_psx() -> None:
    registro = REGISTRO_VALIDO.replace("PSX Executables Loader", "Raw Binary")
    with pytest.raises(ValueError, match=r"el registro no confirma el uso del cargador PSX"):
        verificar_carga(registro)


@pytest.mark.parametrize(
    ("quitar", "campo"),
    [("BBLIT base=0x80014A00", "base"), ("BBLIT entrada=0x80014A08", "entrada")],
)
def test_verificar_carga_exige_las_marcas(quitar: str, campo: str) -> None:
    registro = REGISTRO_VALIDO.replace(quitar, "nada")
    with pytest.raises(ValueError, match=rf"el registro no informa la {campo} del programa"):
        verificar_carga(registro)


def test_verificar_carga_rechaza_base_distinta() -> None:
    registro = REGISTRO_VALIDO.replace("base=0x80014A00", "base=0x80010000")
    with pytest.raises(ValueError, match=r"base=0x80010000, se esperaba 0x80014A00"):
        verificar_carga(registro)


def test_verificar_carga_rechaza_entrada_distinta() -> None:
    registro = REGISTRO_VALIDO.replace("entrada=0x80014A08", "entrada=0x80014A00")
    with pytest.raises(ValueError, match=r"entrada=0x80014A00, se esperaba 0x80014A08"):
        verificar_carga(registro)


def test_ejecutar_analisis_crea_el_proyecto_lanza_ghidra_y_verifica(
    config: ConfiguracionGhidra, tmp_path: Path
) -> None:
    doble = EjecutorDoble(ResultadoEjecucion(0, REGISTRO_VALIDO))
    carga = ejecutar_analisis(config, tmp_path / "SLUS_008.38", None, ["4.6.0"], segundos=120, ejecutor=doble)
    assert carga == Carga(base=0x80014A00, entrada=0x80014A08)
    assert config.proyecto.is_dir()
    assert len(doble.llamadas) == 1
    comando, segundos = doble.llamadas[0]
    assert comando[0] == str(config.lanzador)
    assert segundos == 120


def test_ejecutar_analisis_es_idempotente_con_el_proyecto_existente(
    config: ConfiguracionGhidra, tmp_path: Path
) -> None:
    doble = EjecutorDoble(ResultadoEjecucion(0, REGISTRO_VALIDO))
    config.proyecto.mkdir()
    primera = ejecutar_analisis(config, tmp_path / "SLUS_008.38", None, [], ejecutor=doble)
    segunda = ejecutar_analisis(config, tmp_path / "SLUS_008.38", None, [], ejecutor=doble)
    assert primera == segunda
    assert doble.llamadas[0] == doble.llamadas[1]
    assert "-overwrite" in doble.llamadas[0][0]


def test_ejecutar_analisis_falla_si_ghidra_termina_con_error(
    config: ConfiguracionGhidra, tmp_path: Path
) -> None:
    doble = EjecutorDoble(ResultadoEjecucion(1, REGISTRO_VALIDO))
    with pytest.raises(ValueError, match=r"analyzeHeadless termino con codigo 1"):
        ejecutar_analisis(config, tmp_path / "SLUS_008.38", None, [], ejecutor=doble)


def test_ejecutar_analisis_falla_si_la_carga_no_es_la_esperada(
    config: ConfiguracionGhidra, tmp_path: Path
) -> None:
    doble = EjecutorDoble(ResultadoEjecucion(0, "sin marcas"))
    with pytest.raises(ValueError, match=r"el registro no confirma el uso del cargador PSX"):
        ejecutar_analisis(config, tmp_path / "SLUS_008.38", None, [], ejecutor=doble)


def test_ejecutar_exportacion_crea_la_salida_y_comprueba_funciones_csv(
    config: ConfiguracionGhidra, tmp_path: Path
) -> None:
    salida = tmp_path / "analisis" / "ghidra"
    salida.mkdir(parents=True)
    doble = EjecutorDoble(ResultadoEjecucion(0, ""), crear=salida / "funciones.csv")
    ejecutar_exportacion(config, "SLUS_008.38", salida, ejecutor=doble)
    assert (salida / "funciones.csv").is_file()
    assert doble.llamadas[0][0][-2:] == ["si", "60"]
    assert doble.llamadas[0][1] == 600


def test_ejecutar_exportacion_sin_decompilar_pasa_la_opcion(
    config: ConfiguracionGhidra, tmp_path: Path
) -> None:
    salida = tmp_path / "nueva"
    salida.mkdir()
    doble = EjecutorDoble(ResultadoEjecucion(0, ""), crear=salida / "funciones.csv")
    ejecutar_exportacion(
        config, "SLUS_008.38", salida, decompilar=False, segundos_por_funcion=5, ejecutor=doble
    )
    assert doble.llamadas[0][0][-2:] == ["no", "5"]


def test_ejecutar_exportacion_crea_la_carpeta_de_salida_si_falta(
    config: ConfiguracionGhidra, tmp_path: Path
) -> None:
    salida = tmp_path / "a" / "b"
    doble = EjecutorDoble(ResultadoEjecucion(0, ""), crear=None)
    with pytest.raises(ValueError, match=r"la exportacion no produjo funciones\.csv"):
        ejecutar_exportacion(config, "SLUS_008.38", salida, ejecutor=doble)
    assert salida.is_dir()


def test_ejecutar_exportacion_no_da_por_buena_una_exportacion_anterior(
    config: ConfiguracionGhidra, tmp_path: Path
) -> None:
    salida = tmp_path / "salida"
    salida.mkdir()
    (salida / "funciones.csv").write_text("viejo", encoding="utf-8")
    doble = EjecutorDoble(ResultadoEjecucion(0, ""), crear=None)
    with pytest.raises(ValueError, match=r"la exportacion no produjo funciones\.csv"):
        ejecutar_exportacion(config, "SLUS_008.38", salida, ejecutor=doble)
    assert not (salida / "funciones.csv").exists()


def test_ejecutar_exportacion_falla_si_ghidra_termina_con_error(
    config: ConfiguracionGhidra, tmp_path: Path
) -> None:
    doble = EjecutorDoble(ResultadoEjecucion(2, ""))
    with pytest.raises(ValueError, match=r"analyzeHeadless termino con codigo 2"):
        ejecutar_exportacion(config, "SLUS_008.38", tmp_path / "s", ejecutor=doble)

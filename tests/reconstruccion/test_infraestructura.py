import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

import pytest
from tools.reconstruccion import dominio
from tools.reconstruccion import infraestructura as infra
from tools.reconstruccion.dominio import CabeceraPsx, EjecutableReferencia
from tools.reconstruccion.infraestructura import Herramientas, ProcesoError
from tools.toolchain.dominio import cargar_lock

from tests.toolchain.ayudantes import bloque_componente, construir_iso, lock_de

CUERPO = bytes(range(16))
CABECERA = CabeceraPsx(0x80010008, 0, 0x80010000, 16, 0, 0, 0, 0, 0x801FFFF0, 0, "Region de prueba")
EJECUTABLE = dominio.ensamblar_ejecutable(CABECERA, CUERPO)
REFERENCIA = EjecutableReferencia(
    "PRUEBA.EXE",
    hashlib.sha256(EJECUTABLE).hexdigest(),
    hashlib.sha1(EJECUTABLE, usedforsecurity=False).hexdigest(),
    len(EJECUTABLE),
    CABECERA,
)
SCRIPT_LD = "main\n{\n    build/asm/text.s.o(.text);\n    build/asm/data/datos.s.o(.data);\n}\n"


def herramientas() -> Herramientas:
    return Herramientas("py", Path("as.exe"), Path("ld.exe"), Path("objcopy.exe"))


class Registro:
    """Ejecutor falso: registra los comandos y simula las salidas de splat, as, ld y objcopy."""

    def __init__(self, cuerpo: bytes = CUERPO, genera_script: bool = True, simbolos: bool = True) -> None:
        self.comandos: list[list[str]] = []
        self.directorios: list[Path] = []
        self.tiempos: list[int] = []
        self.cuerpo = cuerpo
        self.genera_script = genera_script
        self.simbolos = simbolos

    def __call__(self, comando: Any, directorio: Any, timeout_s: Any) -> Any:
        self.comandos.append(list(comando))
        self.directorios.append(directorio)
        self.tiempos.append(timeout_s)
        nombre = Path(comando[0]).name
        if "splat" in comando and self.genera_script:
            (directorio / "asm").mkdir(exist_ok=True)
            (directorio / "build").mkdir(exist_ok=True)
            (directorio / infra.SCRIPT_ENLAZADOR).write_text(SCRIPT_LD, encoding="utf-8")
            (directorio / "asm" / "text.s").write_text("t", encoding="utf-8")
            if self.simbolos:
                (directorio / infra.SIMBOLOS_AUTOMATICOS[0]).write_text("f = 0;", encoding="utf-8")
        if nombre == "objcopy.exe":
            (directorio / infra.BINARIO_SALIDA).write_bytes(self.cuerpo)
        return ""


@pytest.fixture
def original(tmp_path: Path) -> Any:
    ruta = tmp_path / "disco con espacios (copia)" / "fs" / "PRUEBA.EXE"
    ruta.parent.mkdir(parents=True)
    ruta.write_bytes(EJECUTABLE)
    return ruta


@pytest.fixture
def raiz(tmp_path: Path) -> Any:
    carpeta = tmp_path / "repo"
    carpeta.mkdir()
    return carpeta


def test_ejecutar_proceso_devuelve_la_salida_y_respeta_el_directorio(tmp_path: Path) -> None:
    carpeta = tmp_path / "carpeta con espacios (1)"
    carpeta.mkdir()
    codigo = "import os, sys; print(os.getcwd()); print(sys.argv[1]); print(os.environ['PYTHONUTF8'])"
    argumento = "valor con espacios (x) y 'comillas'"
    salida = infra.ejecutar_proceso([sys.executable, "-c", codigo, argumento], carpeta, 60)
    cwd, recibido, utf8 = salida.splitlines()
    assert Path(cwd).resolve() == carpeta.resolve()
    assert recibido == argumento
    assert utf8 == "1"


def test_ejecutar_proceso_con_error_nombra_la_herramienta_y_acota_la_salida(tmp_path: Path) -> None:
    codigo = "import sys; sys.stderr.write('x' * 5000 + 'FIN'); sys.exit(3)"
    with pytest.raises(ProcesoError) as error:
        infra.ejecutar_proceso([sys.executable, "-c", codigo], tmp_path, 60)
    mensaje = str(error.value)
    assert mensaje.startswith(f"{Path(sys.executable).name}: termino con codigo 3\n")
    assert mensaje.endswith("FIN")
    assert len(mensaje) < 1700


def test_ejecutar_proceso_usa_stdout_si_stderr_esta_vacio(tmp_path: Path) -> None:
    codigo = "print('solo salida'); raise SystemExit(1)"
    with pytest.raises(ProcesoError, match="solo salida"):
        infra.ejecutar_proceso([sys.executable, "-c", codigo], tmp_path, 60)


def test_ejecutar_proceso_con_tiempo_excedido(tmp_path: Path) -> None:
    with pytest.raises(ProcesoError, match="excedio el tiempo limite de 1 s"):
        infra.ejecutar_proceso([sys.executable, "-c", "import time; time.sleep(30)"], tmp_path, 1)


def test_sha256_archivo(tmp_path: Path) -> None:
    ruta = tmp_path / "a.bin"
    ruta.write_bytes(b"abc" * 1000)
    assert infra.sha256_archivo(ruta) == hashlib.sha256(b"abc" * 1000).hexdigest()


def referencia_json(**cambios: Any) -> Any:
    datos = {
        "nombre": "PRUEBA.EXE",
        "sha256": REFERENCIA.sha256,
        "sha1": REFERENCIA.sha1,
        "tamano": REFERENCIA.tamano,
        "cabecera": {
            **{
                c: getattr(CABECERA, c)
                for c in (
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
            },
            "region": CABECERA.region,
        },
    }
    datos.update(cambios)
    return datos


def test_leer_referencia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ruta = tmp_path / "ejecutable.json"
    ruta.write_text(json.dumps(referencia_json()), encoding="utf-8")
    assert infra.leer_referencia(ruta) == REFERENCIA
    ruta.write_text("{no json", encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape("config/ejecutable.json no es JSON valido")):
        infra.leer_referencia(ruta)
    with pytest.raises(FileNotFoundError, match=re.escape("no se encontro config/ejecutable.json")):
        infra.leer_referencia(tmp_path / "no.json")
    monkeypatch.setattr(infra, "MAX_BYTES_REFERENCIA", 2)
    with pytest.raises(ValueError, match="excede el tamano permitido"):
        infra.leer_referencia(ruta)


def test_obtener_original_usa_el_sistema_de_archivos_extraido(raiz: Path, original: Any) -> None:
    disco = original.parent.parent
    assert infra.obtener_original(raiz, disco, REFERENCIA) == original
    assert not (raiz / "expected").exists()


def test_obtener_original_sin_disco_o_con_ubicacion_inexistente(raiz: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="falta la ubicacion del disco: defina BBLIT_DISC"):
        infra.obtener_original(raiz, None, REFERENCIA)
    with pytest.raises(FileNotFoundError, match="la ubicacion del disco no existe"):
        infra.obtener_original(raiz, tmp_path / "no_existe", REFERENCIA)


def test_obtener_original_en_carpeta_sin_fs_ni_imagen(raiz: Path, tmp_path: Path) -> None:
    vacia = tmp_path / "vacia"
    vacia.mkdir()
    with pytest.raises(FileNotFoundError, match=re.escape("no se encontro fs/PRUEBA.EXE ni una imagen .bin")):
        infra.obtener_original(raiz, vacia, REFERENCIA)


def crear_imagen(carpeta: Path, nombre: str = "juego (USA).bin", contenido: bytes = EJECUTABLE) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre
    ruta.write_bytes(construir_iso({"PRUEBA.EXE;1": contenido}, modo2352=True))
    return ruta


@pytest.mark.parametrize("forma", ["bin", "cue", "carpeta", "padre"])
def test_obtener_original_extrae_de_la_imagen_en_cualquiera_de_sus_formas(
    raiz: Path, tmp_path: Path, forma: str
) -> None:
    carpeta = tmp_path / "disco (copia)" / "juego"
    imagen = crear_imagen(carpeta)
    carpeta.joinpath("juego (USA).cue").write_text("FILE x BINARY", encoding="utf-8")
    disc = {
        "bin": imagen,
        "cue": carpeta / "juego (USA).cue",
        "carpeta": carpeta,
        "padre": carpeta.parent,
    }[forma]
    original = infra.obtener_original(raiz, disc, REFERENCIA)
    assert original == raiz / "expected" / "PRUEBA.EXE"
    assert original.read_bytes() == EJECUTABLE


def test_obtener_original_rechaza_ubicaciones_ambiguas_o_invalidas(raiz: Path, tmp_path: Path) -> None:
    doble = tmp_path / "doble"
    crear_imagen(doble, "a.bin")
    crear_imagen(doble, "b.bin")
    with pytest.raises(ValueError, match=re.escape("hay varias imagenes .bin")):
        infra.obtener_original(raiz, doble, REFERENCIA)
    texto = tmp_path / "notas.txt"
    texto.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape("debe ser una carpeta, un .bin o un .cue")):
        infra.obtener_original(raiz, texto, REFERENCIA)
    huerfano = tmp_path / "solo.cue"
    huerfano.write_text("x", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match=re.escape("el .cue no tiene un .bin hermano")):
        infra.obtener_original(raiz, huerfano, REFERENCIA)


def test_obtener_original_con_imagen_sin_el_ejecutable_o_de_otro_tamano(raiz: Path, tmp_path: Path) -> None:
    sin = crear_imagen(tmp_path / "sin")
    sin.write_bytes(construir_iso({"OTRO.EXE;1": EJECUTABLE}, modo2352=True))
    with pytest.raises(ValueError, match=re.escape("no contiene PRUEBA.EXE en el directorio raiz")):
        infra.obtener_original(raiz, sin, REFERENCIA)
    corto = crear_imagen(tmp_path / "corto", contenido=EJECUTABLE[:-1])
    with pytest.raises(ValueError, match="no tiene el tamano esperado"):
        infra.obtener_original(raiz, corto, REFERENCIA)


def test_dividir_con_el_original_ya_en_expected_no_se_copia_sobre_si_mismo(
    raiz: Path, tmp_path: Path
) -> None:
    imagen = crear_imagen(tmp_path / "disco")
    original = infra.obtener_original(raiz, imagen, REFERENCIA)
    infra.dividir(raiz, original, REFERENCIA, herramientas(), Registro())
    assert (raiz / "expected" / "PRUEBA.EXE").read_bytes() == EJECUTABLE


def test_resolver_herramientas(tmp_path: Path) -> None:
    bloque = bloque_componente(
        b"x",
        archivos_clave={"as": "bin/as.exe", "ld": "bin/ld.exe", "objcopy": "bin/objcopy.exe"},
    )
    lock = cargar_lock(lock_de(**{"binutils-mipsel": bloque}))
    carpeta = tmp_path / "binutils-mipsel" / "bin"
    carpeta.mkdir(parents=True)
    for nombre in ("as.exe", "ld.exe", "objcopy.exe"):
        (carpeta / nombre).write_bytes(b"")
    resultado = infra.resolver_herramientas(lock, tmp_path, "python-x")
    assert resultado == Herramientas(
        "python-x", carpeta / "as.exe", carpeta / "ld.exe", carpeta / "objcopy.exe"
    )
    (carpeta / "ld.exe").unlink()
    with pytest.raises(FileNotFoundError, match="'ld' no esta instalado"):
        infra.resolver_herramientas(lock, tmp_path, "python-x")


def test_dividir_prepara_expected_simbolos_y_ejecuta_splat(raiz: Any, original: Any) -> None:
    ejecutor = Registro()
    infra.dividir(raiz, original, REFERENCIA, herramientas(), ejecutor)
    assert (raiz / "expected" / "PRUEBA.EXE").read_bytes() == EJECUTABLE
    assert (raiz / infra.SIMBOLOS_ENTRADA).read_text(
        encoding="utf-8"
    ) == "func_80010008 = 0x80010008; // type:func\n"
    assert ejecutor.comandos == [["py", "-X", "utf8", "-m", "splat", "split", "config/splat.yaml"]]
    assert ejecutor.directorios == [raiz]
    assert ejecutor.tiempos == [infra.TIMEOUT_SPLAT_S]


def test_dividir_respeta_un_simbolo_de_entrada_ya_declarado(raiz: Any, original: Any) -> None:
    (raiz / "config").mkdir()
    (raiz / "config" / "symbols.txt").write_text("inicio = 0x80010008; // type:func\n", encoding="utf-8")
    infra.dividir(raiz, original, REFERENCIA, herramientas(), Registro())
    assert (raiz / infra.SIMBOLOS_ENTRADA).read_text(encoding="utf-8") == ""


def test_dividir_es_idempotente_y_no_toca_archivos_ajenos_de_build(raiz: Any, original: Any) -> None:
    (raiz / "build").mkdir()
    (raiz / "build" / "otra_herramienta.bin").write_bytes(b"ajeno")
    (raiz / "asm").mkdir()
    (raiz / "asm" / "obsoleto.s").write_text("viejo", encoding="utf-8")
    (raiz / "build" / "asm").mkdir()
    (raiz / "build" / "asm" / "viejo.o").write_bytes(b"o")
    infra.dividir(raiz, original, REFERENCIA, herramientas(), Registro())
    primero = sorted(p.relative_to(raiz).as_posix() for p in raiz.rglob("*") if p.is_file())
    infra.dividir(raiz, original, REFERENCIA, herramientas(), Registro())
    segundo = sorted(p.relative_to(raiz).as_posix() for p in raiz.rglob("*") if p.is_file())
    assert primero == segundo
    assert "asm/obsoleto.s" not in primero
    assert "build/asm/viejo.o" not in primero
    assert (raiz / "build" / "otra_herramienta.bin").read_bytes() == b"ajeno"


def test_dividir_rechaza_un_ejecutable_distinto_sin_ejecutar_nada(raiz: Any, original: Any) -> None:
    original.write_bytes(EJECUTABLE + b"x")
    ejecutor = Registro()
    with pytest.raises(ValueError, match="no coincide con la edicion soportada"):
        infra.dividir(raiz, original, REFERENCIA, herramientas(), ejecutor)
    assert ejecutor.comandos == []
    assert not (raiz / "expected").exists()


def test_dividir_falla_si_splat_no_genera_el_script(raiz: Any, original: Any) -> None:
    with pytest.raises(ProcesoError, match="splat no genero el script del enlazador"):
        infra.dividir(raiz, original, REFERENCIA, herramientas(), Registro(genera_script=False))


def preparar_split(raiz: Any, original: Any, **opciones: Any) -> None:
    infra.dividir(raiz, original, REFERENCIA, herramientas(), Registro(**opciones))


def test_construir_ensambla_cada_objeto_enlaza_y_regenera_la_cabecera(raiz: Any, original: Any) -> None:
    preparar_split(raiz, original)
    (raiz / "asm" / "data").mkdir()
    (raiz / "asm" / "data" / "datos.s").write_text("d", encoding="utf-8")
    ejecutor = Registro()
    destino = infra.construir(raiz, REFERENCIA, herramientas(), ejecutor)
    assert destino == raiz / "build" / "PRUEBA.EXE"
    assert destino.read_bytes() == EJECUTABLE
    assert ejecutor.comandos == [
        [
            "as.exe",
            "-EL",
            "-march=r3000",
            "-mips1",
            "-G0",
            "-I",
            "asm/include",
            "-o",
            "build/asm/text.s.o",
            "asm/text.s",
        ],
        [
            "as.exe",
            "-EL",
            "-march=r3000",
            "-mips1",
            "-G0",
            "-I",
            "asm/include",
            "-o",
            "build/asm/data/datos.s.o",
            "asm/data/datos.s",
        ],
        [
            "ld.exe",
            "-EL",
            "--no-warn-rwx-segments",
            "-T",
            "build/SLUS_008.ld",
            "-T",
            "build/undefined_funcs_auto.txt",
            "-o",
            "build/SLUS_008.elf",
            "-Map",
            "build/SLUS_008.map",
        ],
        ["objcopy.exe", "-O", "binary", "build/SLUS_008.elf", "build/SLUS_008.bin"],
    ]
    assert (raiz / "build" / "asm" / "data").is_dir()


def test_construir_sin_script_o_sin_fuente_pide_ejecutar_split(raiz: Any, original: Any) -> None:
    with pytest.raises(FileNotFoundError, match="ejecute primero 'split'"):
        infra.construir(raiz, REFERENCIA, herramientas(), Registro())
    preparar_split(raiz, original)
    with pytest.raises(FileNotFoundError, match=re.escape("falta el fuente 'asm/data/datos.s'")):
        infra.construir(raiz, REFERENCIA, herramientas(), Registro())


def test_construir_rechaza_un_cuerpo_de_longitud_distinta_a_t_size(raiz: Any, original: Any) -> None:
    preparar_split(raiz, original)
    (raiz / "asm" / "data").mkdir()
    (raiz / "asm" / "data" / "datos.s").write_text("d", encoding="utf-8")
    with pytest.raises(ValueError, match="el cuerpo enlazado mide 15 bytes"):
        infra.construir(raiz, REFERENCIA, herramientas(), Registro(cuerpo=CUERPO[:-1]))
    assert not (raiz / "build" / "PRUEBA.EXE").exists()


def test_verificar_ok_fail_y_sin_build(raiz: Any, original: Any) -> None:
    with pytest.raises(FileNotFoundError, match="ejecute primero 'build'"):
        infra.verificar(raiz, original, REFERENCIA)
    (raiz / "build").mkdir()
    (raiz / "build" / "PRUEBA.EXE").write_bytes(EJECUTABLE)
    assert infra.verificar(raiz, original, REFERENCIA) == (
        True,
        f"OK esperado={REFERENCIA.sha256} obtenido={REFERENCIA.sha256}",
    )
    alterado = bytearray(EJECUTABLE)
    alterado[0x805] ^= 1
    (raiz / "build" / "PRUEBA.EXE").write_bytes(bytes(alterado))
    coincide, mensaje = infra.verificar(raiz, original, REFERENCIA)
    assert coincide is False
    lineas = mensaje.splitlines()
    assert lineas[0].startswith("FAIL esperado=") and "obtenido=" in lineas[0]
    assert lineas[1] == "primera diferencia en el desplazamiento 0x805 (cuerpo)"


def test_limpiar_elimina_lo_generado_y_conserva_lo_ajeno(raiz: Any, original: Any) -> None:
    preparar_split(raiz, original)
    (raiz / "build" / "PRUEBA.EXE").write_bytes(b"x")
    (raiz / "build" / "ajeno.bin").write_bytes(b"a")
    eliminadas = infra.limpiar(raiz, "PRUEBA.EXE")
    assert eliminadas[:2] == ["asm", "expected"]
    assert "build/PRUEBA.EXE" in eliminadas
    assert "build" not in eliminadas
    assert [p.name for p in (raiz / "build").iterdir()] == ["ajeno.bin"]
    assert infra.limpiar(raiz, "PRUEBA.EXE") == []


def test_limpiar_borra_build_si_queda_vacia_y_es_idempotente(raiz: Any, original: Any) -> None:
    preparar_split(raiz, original)
    eliminadas = infra.limpiar(raiz, "PRUEBA.EXE")
    assert eliminadas[-1] == "build"
    assert [p.name for p in raiz.iterdir()] == []
    assert infra.limpiar(raiz, "PRUEBA.EXE") == []


def test_limpiar_elimina_archivos_de_solo_lectura_y_rutas_que_son_archivos(raiz: Any) -> None:
    (raiz / "asm").mkdir()
    protegido = raiz / "asm" / "protegido.s"
    protegido.write_text("x", encoding="utf-8")
    os.chmod(protegido, stat.S_IREAD)
    (raiz / "expected").write_bytes(b"es un archivo, no una carpeta")
    assert infra.limpiar(raiz, "PRUEBA.EXE") == ["asm", "expected"]
    assert not (raiz / "asm").exists()


def test_el_ejecutor_por_defecto_es_ejecutar_proceso() -> None:
    assert infra.dividir.__defaults__ == (infra.ejecutar_proceso,)
    assert infra.construir.__defaults__ == (infra.ejecutar_proceso,)


def test_verificar_rechaza_un_original_de_otra_edicion(raiz: Path, original: Any) -> None:
    (raiz / "build").mkdir()
    (raiz / "build" / "PRUEBA.EXE").write_bytes(EJECUTABLE)
    original.write_bytes(EJECUTABLE + b"x")
    with pytest.raises(ValueError, match="el ejecutable original no coincide con la edicion soportada"):
        infra.verificar(raiz, original, REFERENCIA)


def test_construir_incluye_ambos_archivos_de_simbolos_automaticos(raiz: Path, original: Any) -> None:
    preparar_split(raiz, original)
    (raiz / "asm" / "data").mkdir()
    (raiz / "asm" / "data" / "datos.s").write_text("d", encoding="utf-8")
    (raiz / infra.SIMBOLOS_AUTOMATICOS[1]).write_text("g = 0;", encoding="utf-8")
    ejecutor = Registro()
    infra.construir(raiz, REFERENCIA, herramientas(), ejecutor)
    enlazado = next(c for c in ejecutor.comandos if Path(c[0]).name == "ld.exe")
    assert enlazado[3:9] == [
        "-T",
        "build/SLUS_008.ld",
        "-T",
        "build/undefined_funcs_auto.txt",
        "-T",
        "build/undefined_syms_auto.txt",
    ]


AJENOS = (
    "asm/overlay/a/codigo.s",
    "expected/overlay/a.bin",
    "build/overlay/a/salida.o",
    "build/emulador/captura.png",
    "build/bblit_prueba.bin",
    "build/bblit_prueba.cue",
)


def crear_ajenos(raiz: Any) -> None:
    for relativa in AJENOS:
        (raiz / relativa).parent.mkdir(parents=True, exist_ok=True)
        (raiz / relativa).write_text("ajeno", encoding="utf-8")


def test_split_y_clean_respetan_lo_que_pertenece_a_otras_herramientas(raiz: Any, original: Any) -> None:
    crear_ajenos(raiz)
    (raiz / "asm" / "viejo.s").write_text("propio", encoding="utf-8")
    preparar_split(raiz, original)
    assert not (raiz / "asm" / "viejo.s").exists(), "split regenera lo propio"
    for relativa in AJENOS:
        assert (raiz / relativa).read_text(encoding="utf-8") == "ajeno", relativa
    (raiz / "build" / "PRUEBA.EXE").write_bytes(b"x")
    (raiz / "build" / "src").mkdir()
    (raiz / "build" / "diff").mkdir()
    eliminadas = infra.limpiar(raiz, "PRUEBA.EXE")
    assert "asm/text.s" in eliminadas and "expected/PRUEBA.EXE" in eliminadas
    assert "build/PRUEBA.EXE" in eliminadas and "build/src" in eliminadas and "build/diff" in eliminadas
    assert "build" not in eliminadas
    for relativa in AJENOS:
        assert (raiz / relativa).read_text(encoding="utf-8") == "ajeno", relativa
    assert not (raiz / "asm" / "text.s").exists() and not (raiz / "expected" / "PRUEBA.EXE").exists()
    assert infra.limpiar(raiz, "PRUEBA.EXE") == []


def test_listar_fuentes_c(raiz: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    assert infra.listar_fuentes_c(raiz) == {}
    (raiz / "src").mkdir()
    (raiz / "src" / "b.c").write_text("b", encoding="utf-8")
    (raiz / "src" / "a.c").write_text("a", encoding="utf-8")
    (raiz / "src" / "nota.txt").write_text("x", encoding="utf-8")
    assert infra.listar_fuentes_c(raiz) == {"src/a.c": "a", "src/b.c": "b"}
    monkeypatch.setattr(infra, "MAX_BYTES_FUENTE", 0)
    with pytest.raises(ValueError, match=r"src/a.c excede el tamano permitido"):
        infra.listar_fuentes_c(raiz)


def test_localizar_imagen_con_bin_en_subcarpetas_distintas_es_ambigua(tmp_path: Path) -> None:
    for carpeta, nombre in (("a", "x.bin"), ("b", "y.bin")):
        (tmp_path / carpeta).mkdir()
        (tmp_path / carpeta / nombre).write_bytes(b"")
    with pytest.raises(ValueError, match=r"hay varias imagenes .bin"):
        infra.localizar_imagen(tmp_path)

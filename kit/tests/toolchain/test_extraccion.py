import shutil
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

import pytest
from tools.toolchain import extraccion
from tools.toolchain.dominio import parsear_componente

from .ayudantes import bloque_componente, construir_iso, zip_de


def componente(**cambios: Any) -> Any:
    return parsear_componente("pieza", bloque_componente(b"x", **cambios))


def escribir_zip(ruta: Path, miembros: dict[str, bytes]) -> Path:
    ruta.write_bytes(zip_de(miembros))
    return ruta


def test_zip_extrae_solo_lo_que_coincide_con_los_patrones(tmp_path: Path) -> None:
    archivo = escribir_zip(tmp_path / "a.zip", {"bin/as.exe": b"AS", "bin/ld.exe": b"LD", "doc/x.txt": b"X"})
    destino = tmp_path / "destino"
    escritos = extraccion.extraer_zip(componente(extraer=["bin/as.exe", "doc/*"]), archivo, destino)
    assert escritos == 2
    assert sorted(p.relative_to(destino).as_posix() for p in destino.rglob("*") if p.is_file()) == [
        "bin/as.exe",
        "doc/x.txt",
    ]
    assert (destino / "bin" / "as.exe").read_bytes() == b"AS"


def test_zip_quita_la_carpeta_raiz_y_omite_entradas_de_directorio(tmp_path: Path) -> None:
    miembros = {"proyecto-abc/": b"", "proyecto-abc/m.py": b"print()", "suelto.txt": b"s"}
    archivo = escribir_zip(tmp_path / "a.zip", miembros)
    destino = tmp_path / "destino"
    escritos = extraccion.extraer_zip(componente(quitar_raiz=True), archivo, destino)
    assert escritos == 1
    assert (destino / "m.py").read_bytes() == b"print()"
    assert not (destino / "suelto.txt").exists()


@pytest.mark.parametrize("nombre", ["../fuera.txt", "/abs.txt", "a/../../fuera.txt", "C:/x.txt"])
def test_zip_con_ruta_hostil_se_rechaza_sin_escribir(tmp_path: Path, nombre: Any) -> None:
    archivo = escribir_zip(tmp_path / "a.zip", {nombre: b"malo"})
    destino = tmp_path / "destino"
    destino.mkdir()
    with pytest.raises(ValueError):
        extraccion.extraer_zip(componente(), archivo, destino)
    assert not (tmp_path / "fuera.txt").exists()
    assert list(destino.iterdir()) == []


def test_zip_con_demasiados_miembros(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extraccion, "MAX_MIEMBROS", 1)
    archivo = escribir_zip(tmp_path / "a.zip", {"a": b"1", "b": b"2"})
    with pytest.raises(ValueError, match="'pieza': el archivo tiene demasiados miembros"):
        extraccion.extraer_zip(componente(), archivo, tmp_path / "d")


def test_zip_que_excede_la_cota_de_extraccion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extraccion, "MAX_BYTES_EXTRAIDOS", 3)
    archivo = escribir_zip(tmp_path / "a.zip", {"a": b"1234"})
    with pytest.raises(ValueError, match="excede la cota de extraccion"):
        extraccion.extraer_zip(componente(), archivo, tmp_path / "d")


def test_destino_seguro_rechaza_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="fuera de la carpeta del componente"):
        extraccion._destino_seguro(tmp_path, PurePosixPath("../fuera"))


def test_archivo_simple_se_copia_con_su_nombre(tmp_path: Path) -> None:
    origen = tmp_path / "herramienta.exe"
    origen.write_bytes(b"EXE")
    assert extraccion.extraer_archivo_simple(origen, tmp_path / "d") == 1
    assert (tmp_path / "d" / "herramienta.exe").read_bytes() == b"EXE"


class Ejecucion:
    """Doble de ``subprocess.run`` que registra la llamada y simula la salida de 7-Zip."""

    def __init__(self, codigo: Any = 0, accion: Any = None, expira: Any = False) -> None:
        self.llamadas: list[list[str]] = []
        self.codigo = codigo
        self.accion = accion
        self.expira = expira

    def __call__(self, comando: Any, **opciones: Any) -> Any:
        self.llamadas.append(comando)
        self.opciones = opciones
        if self.expira:
            raise subprocess.TimeoutExpired(comando, 1)
        if self.accion:
            self.accion(comando)
        return subprocess.CompletedProcess(comando, self.codigo, "", "")


def destino_de(comando: list[str]) -> Path:
    return Path(next(a for a in comando if a.startswith("-o"))[2:])


def test_7z_pasa_argumentos_como_lista_y_cuenta_archivos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def accion(comando: Any) -> None:
        carpeta = destino_de(comando) / "pssn" / "bin"
        carpeta.mkdir(parents=True)
        (carpeta / "CC1PSX.EXE").write_bytes(b"CC")

    ejecucion = Ejecucion(accion=accion)
    monkeypatch.setattr(subprocess, "run", ejecucion)
    destino = tmp_path / "con espacios (x)"
    cuenta = extraccion.extraer_7z(
        componente(formato="7z", extraer=["pssn/bin/*"]), tmp_path / "a b.7z", destino, Path("7z.exe")
    )
    assert cuenta == 1
    assert ejecucion.llamadas[0] == [
        "7z.exe",
        "x",
        "-y",
        "-bd",
        f"-o{destino}",
        str(tmp_path / "a b.7z"),
        "pssn\\bin\\*",
    ]
    assert ejecucion.opciones["timeout"] == extraccion.TIMEOUT_7ZIP_S
    assert "shell" not in ejecucion.opciones


def test_7zip_con_codigo_de_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", Ejecucion(codigo=2))
    with pytest.raises(RuntimeError, match="'pieza': 7-Zip termino con codigo 2"):
        extraccion.extraer_7z(componente(formato="7z"), tmp_path / "a.7z", tmp_path / "d", Path("7z.exe"))


def test_7zip_con_tiempo_excedido(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", Ejecucion(expira=True))
    with pytest.raises(TimeoutError, match="'pieza': 7-Zip excedio"):
        extraccion.extraer_7z(componente(formato="7z"), tmp_path / "a.7z", tmp_path / "d", Path("7z.exe"))


def test_verificar_arbol_detecta_archivo_fuera_del_destino(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destino = tmp_path / "d"
    destino.mkdir()
    fuera = tmp_path / "otro"
    fuera.mkdir()
    monkeypatch.setattr("tools.toolchain.extraccion.os.walk", lambda base: [(str(fuera), [], ["x.txt"])])
    with pytest.raises(ValueError, match="'pieza': el archivo extraido salio del destino"):
        extraccion._verificar_arbol(destino, "pieza")


def accion_con_imagen(arbol: Any, nombre: Any = "Image.bin") -> Any:
    def accion(comando: Any) -> None:
        carpeta = destino_de(comando)
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / nombre).write_bytes(construir_iso(arbol, modo2352=True))

    return accion


ARBOL = {"GNU": {"CC1PSX.EXE": b"GCC272", "DOS": {"VIEJO.EXE": b"dos"}}, "OTRO.TXT": b"o"}


def test_rar_iso_extrae_solo_lo_pedido_y_borra_la_imagen_temporal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(subprocess, "run", Ejecucion(accion=accion_con_imagen(ARBOL)))
    destino = tmp_path / "psyq"
    cuenta = extraccion.extraer_rar_iso(
        componente(formato="rar_iso", extraer=["gnu/cc1psx.exe"]), tmp_path / "a.rar", destino, Path("7z.exe")
    )
    assert cuenta == 1
    assert (destino / "GNU" / "CC1PSX.EXE").read_bytes() == b"GCC272"
    assert sorted(p.name for p in destino.iterdir()) == ["GNU"]


@pytest.mark.parametrize("cantidad", [0, 2])
def test_rar_iso_exige_una_unica_imagen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cantidad: Any
) -> None:
    def accion(comando: Any) -> None:
        carpeta = destino_de(comando)
        carpeta.mkdir(parents=True, exist_ok=True)
        for i in range(cantidad):
            (carpeta / f"i{i}.bin").write_bytes(b"x")

    monkeypatch.setattr(subprocess, "run", Ejecucion(accion=accion))
    with pytest.raises(ValueError, match="una unica imagen"):
        extraccion.extraer_rar_iso(
            componente(formato="rar_iso"), tmp_path / "a.rar", tmp_path / "d", Path("7z.exe")
        )
    assert not (tmp_path / "d" / "_imagen_temporal").exists()


def test_rar_iso_respeta_la_cota_de_extraccion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", Ejecucion(accion=accion_con_imagen(ARBOL)))
    monkeypatch.setattr(extraccion, "MAX_BYTES_EXTRAIDOS", 2)
    with pytest.raises(ValueError, match="excede la cota de extraccion"):
        extraccion.extraer_rar_iso(
            componente(formato="rar_iso"), tmp_path / "a.rar", tmp_path / "d", Path("7z.exe")
        )


def test_despacho_segun_formato(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    zip_ = escribir_zip(tmp_path / "a.zip", {"m.txt": b"m"})
    assert extraccion.extraer(componente(), zip_, tmp_path / "z", None) == 1
    simple = tmp_path / "s.exe"
    simple.write_bytes(b"s")
    assert extraccion.extraer(componente(formato="archivo"), simple, tmp_path / "s", None) == 1
    monkeypatch.setattr(subprocess, "run", Ejecucion(accion=accion_con_imagen(ARBOL)))
    assert (
        extraccion.extraer(componente(formato="rar_iso"), tmp_path / "a.rar", tmp_path / "r", Path("7z")) == 3
    )

    def accion(comando: Any) -> None:
        (destino_de(comando) / "x").mkdir(parents=True)
        (destino_de(comando) / "x" / "f").write_bytes(b"1")

    monkeypatch.setattr(subprocess, "run", Ejecucion(accion=accion))
    assert extraccion.extraer(componente(formato="7z"), tmp_path / "a.7z", tmp_path / "q", Path("7z")) == 1


@pytest.mark.parametrize("formato", ["7z", "rar_iso"])
def test_formatos_que_requieren_7zip_fallan_con_mensaje_claro(tmp_path: Path, formato: Any) -> None:
    with pytest.raises(ValueError, match=f"'pieza': el formato '{formato}' requiere 7-Zip"):
        extraccion.extraer(componente(formato=formato), tmp_path / "a", tmp_path / "d", None)


def test_localizar_7zip_prefiere_la_ruta_configurada(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    configurado = tmp_path / "mi7z.exe"
    configurado.write_bytes(b"")
    monkeypatch.setattr(shutil, "which", lambda nombre: None)
    assert extraccion.localizar_7zip(configurado, {}) == configurado


def test_localizar_7zip_usa_el_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    encontrado = tmp_path / "7z.exe"
    encontrado.write_bytes(b"")
    monkeypatch.setattr(shutil, "which", lambda nombre: str(encontrado) if nombre == "7z" else None)
    assert extraccion.localizar_7zip(None, {}) == encontrado


def test_localizar_7zip_usa_program_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda nombre: None)
    (tmp_path / "7-Zip").mkdir()
    (tmp_path / "7-Zip" / "7z.exe").write_bytes(b"")
    assert extraccion.localizar_7zip(None, {"ProgramFiles": str(tmp_path)}) == tmp_path / "7-Zip" / "7z.exe"


def test_localizar_7zip_inexistente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda nombre: None)
    with pytest.raises(FileNotFoundError, match="no se encontro 7-Zip"):
        extraccion.localizar_7zip(tmp_path / "no.exe", {"ProgramFiles": str(tmp_path)})

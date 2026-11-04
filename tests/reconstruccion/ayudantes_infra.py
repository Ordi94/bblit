"""Ayudantes del consumidor: ejecutable de prueba con el nombre del manifiesto y ejecutor falso."""

import hashlib
from pathlib import Path
from typing import Any

from tools.reconstruccion import dominio
from tools.reconstruccion import infraestructura as infra
from tools.reconstruccion.dominio import CabeceraPsx, EjecutableReferencia
from tools.reconstruccion.infraestructura import Herramientas
from tools.toolchain.contexto import PROYECTO

CUERPO = bytes(range(16))
CABECERA = CabeceraPsx(0x80010008, 0, 0x80010000, 16, 0, 0, 0, 0, 0x801FFFF0, 0, "Region de prueba")
EJECUTABLE = dominio.ensamblar_ejecutable(CABECERA, CUERPO)
REFERENCIA = EjecutableReferencia(
    PROYECTO.identidad.ejecutable,
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


def referencia_json(**cambios: Any) -> Any:
    datos = {
        "nombre": "SLUS_008.38",
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

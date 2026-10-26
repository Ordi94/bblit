"""Datos sinteticos para las pruebas del overlay.

Todo se arma a mano a partir de la estructura documentada en ``docs/OVERLAY.md``: ningun dato
procede del disco original. El overlay sintetico respeta la disposicion real (ranura inicial,
salto en el desplazamiento 4, entradas que invoca el ejecutable, codigo que termina en un
``jr ra`` y tablas posteriores) para poder ejercitar todas las reglas del paquete.
"""

from __future__ import annotations

import struct
from pathlib import Path

from tools.overlay.dominio import DIRECCION_CARGA, VarianteConocida, huella_sha256

from tests.bzz.ayudantes import construir_bzz, flujo_literales

JR_RA = 0x03E00008
ADDIU_SP = 0x27BDFFD8
EPILOGO_SP = 0x27BD0028
OFFSET_EPILOGO = 0x1010
"""Epilogo `addiu sp,sp,+0x28` dentro de la funcion de 0x1000: no es inicio de funcion."""
FIN_CODIGO = 0x28F8
FUNCIONES_SINTETICAS = (0x4, 0xC, 0x58, 0x61C, 0x9A4, 0x1000, 0x28B0, 0x28E4)
"""Inicios de funcion que ``descubrir_funciones`` debe encontrar en el overlay sintetico."""


def salto(opcode: int, offset: int) -> int:
    """Codifica ``j`` (2) o ``jal`` (3) hacia un desplazamiento del overlay."""
    return (opcode << 26) | (((DIRECCION_CARGA + offset) >> 2) & 0x03FFFFFF)


def construir_overlay(marca: int = 0, relleno_tabla: int = 0x40) -> bytes:
    """Overlay sintetico con tres funciones de llamada, un prologo y una tabla de punteros.

    ``marca`` cambia una palabra del codigo y otra de las tablas para producir variantes
    distintas; ``relleno_tabla`` es el numero de palabras de la tabla de busqueda.
    """
    palabras = [0] * (FIN_CODIGO // 4)
    palabras[1] = salto(2, 0x9A4)
    palabras[0x50 // 4] = JR_RA
    palabras[0x58 // 4] = ADDIU_SP
    palabras[0x100 // 4] = salto(3, 0x61C)
    palabras[0x154 // 4] = 0x25290000 | (marca & 0xFFFF)
    palabras[0x9A4 // 4] = ADDIU_SP
    palabras[0x1000 // 4] = ADDIU_SP
    palabras[OFFSET_EPILOGO // 4] = EPILOGO_SP
    palabras[0x28F0 // 4] = JR_RA
    saltos = [DIRECCION_CARGA + 0x58] * 56
    tablas = [0] * 4 + [0x1000 + marca] * relleno_tabla + [0xFFFFFF] * 4
    return struct.pack(f"<{len(palabras) + len(saltos) + len(tablas)}I", *palabras, *saltos, *tablas)


def variantes_conocidas(
    binarios: dict[str, bytes], cantidades: dict[str, int]
) -> tuple[VarianteConocida, ...]:
    """Variantes conocidas sinteticas para unos binarios y una cantidad de contenedores cada una."""
    return tuple(
        VarianteConocida(identificador, huella_sha256(datos), len(datos), cantidades[identificador])
        for identificador, datos in binarios.items()
    )


def contenedor(codigo: bytes | None) -> bytes:
    """Contenedor BZZ sintetico: script de carga, codigo opcional (tipo 2) y datos."""
    secciones = [(1, flujo_literales(b"\x2d\x45\x00\x2e" + bytes(12)))]
    if codigo is not None:
        secciones.append((2, flujo_literales(codigo)))
    secciones.append((3, flujo_literales(bytes(range(64)))))
    return construir_bzz(secciones)


def escribir_sistema_de_archivos(raiz: Path, contenidos: dict[str, bytes]) -> Path:
    """Crea ``raiz/fs/<ruta>`` con los contenedores dados y devuelve ``raiz``."""
    for nombre, datos in contenidos.items():
        destino = raiz / "fs" / nombre
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(datos)
    return raiz


class Registro:
    """Ejecutor falso: registra los comandos y simula la salida de splat, as, ld y objcopy.

    ``glabels`` y ``palabras`` permiten forzar particiones defectuosas; ``binarios`` indica el
    contenido que produce ``objcopy`` para cada variante.
    """

    def __init__(
        self,
        binarios: dict[str, bytes],
        glabels: int | None = None,
        palabras: int = 0,
        genera_script: bool = True,
    ) -> None:
        self.binarios = binarios
        self.glabels = glabels
        self.palabras = palabras
        self.genera_script = genera_script
        self.comandos: list[list[str]] = []
        self.directorios: list[Path] = []
        self.tiempos: list[int] = []

    def __call__(self, comando: object, directorio: Path, timeout_s: int) -> str:
        lista = [str(parte) for parte in comando]  # type: ignore[attr-defined]
        self.comandos.append(lista)
        self.directorios.append(directorio)
        self.tiempos.append(timeout_s)
        nombre = Path(lista[0]).name
        if "splat" in lista:
            self._splat(directorio, lista[-1])
        elif nombre == "as.exe":
            self._escribir(directorio / lista[lista.index("-o") + 1], b"objeto")
        elif nombre == "ld.exe":
            self._escribir(directorio / lista[lista.index("-o") + 1], b"elf")
        elif nombre == "objcopy.exe":
            salida = lista[-1]
            identificador = Path(salida).stem
            self._escribir(directorio / salida, self.binarios[identificador])
        return ""

    @staticmethod
    def _escribir(ruta: Path, datos: bytes) -> None:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(datos)

    def _splat(self, raiz: Path, configuracion: str) -> None:
        identificador = Path(configuracion).stem.rsplit("_", 1)[1]
        simbolos = (raiz / "config" / "symbols_overlay.txt").read_text(encoding="utf-8")
        cantidad = self.glabels if self.glabels is not None else simbolos.count("type:func")
        asm = raiz / "asm" / "overlay" / identificador
        (asm / "include").mkdir(parents=True, exist_ok=True)
        (asm / "data").mkdir(exist_ok=True)
        texto = (
            "".join(f"glabel func_{i}\n    nop\n" for i in range(cantidad))
            + self.palabras * "    .word 0x0\n"
        )
        (asm / "codigo.s").write_text(texto, encoding="utf-8")
        (asm / "data" / "tablas.data.s").write_text("dlabel D_1\n    .word 0x0\n", encoding="utf-8")
        if self.genera_script:
            base = f"build/overlay/{identificador}"
            guion = (
                f"        {base}/asm/overlay/{identificador}/codigo.s.o(.text);\n"
                f"        {base}/asm/overlay/{identificador}/data/tablas.data.s.o(.data);\n"
            )
            (raiz / "build" / "overlay").mkdir(parents=True, exist_ok=True)
            (raiz / f"{base}.ld").write_text(guion, encoding="utf-8")
            (raiz / f"{base}_undefined_syms_auto.txt").write_text("D_1 = 0x80010300;\n", encoding="utf-8")

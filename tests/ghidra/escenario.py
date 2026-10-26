"""Escenario sintetico de analisis: simbolos, desensamblado y segmento de un programa pequeno.

El programa tiene cinco funciones del juego y una de libreria. ``A`` llama dos veces a ``B``, toma
el puntero de ``C``, hace una llamada indirecta y llama a una funcion de libreria; ``B`` salta a
``C`` y usa datos; ``D`` despacha con una tabla de saltos propia y una entrada hacia ``E``; ``G``
salta a un registro sin tabla. Ningun dato proviene del disco real.
"""

from tools.ghidra.dominio import Simbolo

from tests.ghidra.segmentos import cierre, segmento

VSYNC = 0x80045DA0
TABLA = 0x8005E000
"""Direccion de la tabla de saltos en la zona de datos."""

_CUERPOS: list[tuple[str, list[str]]] = [
    (
        "A",
        [
            "lui        $a0, %hi(D_80060000)",
            "jal        {B}",
            "nop",
            "jal        {B}",
            "nop",
            "lui        $a1, %hi({C})",
            "addiu      $a1, $a1, %lo({C})",
            "jalr       $v0",
            "nop",
            "jal        VSync",
            "nop",
            "jr         $ra",
            "nop",
        ],
    ),
    (
        "B",
        [
            "lw         $v0, 0x10($gp)",
            "lui        $a0, (0x80010000 >> 16)",
            "lw         $v1, -0x8($gp)",
            "j          {C}",
            "nop",
        ],
    ),
    ("C", ["jr         $ra", "nop"]),
    (
        "D",
        [
            "lui        $v0, %hi(D_8005E000)",
            "addiu      $v0, $v0, %lo(D_8005E000)",
            "jr         $v0",
            "nop",
            "addiu      $v0, $zero, 0x1",
            "jr         $ra",
            "nop",
            "addiu      $v0, $zero, 0x2",
            "jr         $ra",
            "nop",
            "j          .L{D_ETIQUETA}",
            "nop",
        ],
    ),
    ("E", ["jr         $ra", "nop"]),
    ("G", ["jr         $t0", "nop"]),
]

A = 0x80014AC4
DIRECCIONES: dict[str, int] = {}
_cursor = A
for _clave, _instrucciones in _CUERPOS:
    DIRECCIONES[_clave] = _cursor
    _cursor += 4 * len(_instrucciones)
B, C, D, E, G = (DIRECCIONES[k] for k in "BCDEG")
D_DESTINO_1 = D + 4 * 4
"""Primer destino de la tabla de saltos de ``D`` (dentro de la propia funcion)."""
D_DESTINO_2 = D + 4 * 7
"""Segundo destino de la tabla de saltos de ``D``."""


def nombre(direccion: int) -> str:
    """Nombre automatico de una funcion en la direccion indicada."""
    return f"func_{direccion:08X}"


def _formatear(linea: str) -> str:
    """Sustituye los marcadores de direccion por los nombres reales."""
    return linea.format(
        B=nombre(B), C=nombre(C), D_ETIQUETA=f"{D:08X}", D=nombre(D), E=nombre(E), G=nombre(G)
    )


def simbolos() -> list[Simbolo]:
    """Tabla de simbolos del escenario, en orden de direccion."""
    resultado = [
        Simbolo(nombre(DIRECCIONES[clave]), DIRECCIONES[clave], "func", 4 * len(cuerpo))
        for clave, cuerpo in _CUERPOS
    ]
    resultado.append(Simbolo("VSync", VSYNC, "func", 8))
    return resultado


def texto_asm() -> str:
    """Desensamblado del escenario con el formato de splat, incluidas lineas ajenas a las funciones."""
    lineas = [
        '.include "macro.inc"',
        "",
        "nonmatching ruido, 0x4",
        "    /* 0 80014AB4 00002000 */ .word 0x00200000",
    ]
    cuerpos = dict(_CUERPOS)
    for clave, direccion in [*DIRECCIONES.items(), ("VSYNC", VSYNC)]:
        instrucciones = cuerpos.get(clave, ["jr         $ra", "nop"])
        etiqueta = "VSync" if clave == "VSYNC" else nombre(direccion)
        lineas += ["", f"glabel {etiqueta}"]
        for indice, texto in enumerate(instrucciones):
            direccion_i = direccion + 4 * indice
            sangria = (
                "   "
                if indice > 0 and instrucciones[indice - 1].split()[0] in ("jal", "j", "jalr", "jr")
                else "  "
            )
            lineas.append(
                f"    /* {direccion_i - 0x80014A00 + 0x800:X} {direccion_i:08X} 00000000 */{sangria}{_formatear(texto)}"  # noqa: E501
            )
        lineas.append(f"endlabel {etiqueta}")
    return "\n".join(lineas) + "\n"


def palabras_programa() -> dict[int, int]:
    """Palabras del segmento: el cierre de cada funcion y la tabla de saltos de ``D`` en ``TABLA``."""
    palabras: dict[int, int] = {TABLA: D_DESTINO_1, TABLA + 4: D_DESTINO_2, TABLA + 8: E}
    for simbolo in simbolos():
        palabras |= cierre(simbolo.direccion, simbolo.tamano)
    return palabras


def segmento_programa() -> bytes:
    """Segmento cargado del escenario (ver ``palabras_programa``)."""
    return segmento(palabras_programa())

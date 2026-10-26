# Progreso de la descompilación

Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del
texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la
construcción normal) y de la tabla de símbolos.

## Resumen

| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |
|---|---:|---:|---:|---:|
| Arranque | 2 | 180 | 0 | 0 |
| Código del juego | 262 | 201416 | 3 | 148 |
| Librerías Sony | 650 | 97488 | 0 | 0 |

Bytes de código del juego descompilados: 148 de 201416 (0.07 %).
Funciones marcadas `NON_MATCHING`: 2.
Coherencia con el ensamblador: correcta (911 `glabel` en `asm/` + 3 en C = 914; la tabla declara 914).

## Por archivo

| Archivo | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|
| `src/code_80014AC4.c` | 0 | 0 | 31 | 0 | 29912 |
| `src/code_8001BF9C.c` | 0 | 0 | 30 | 0 | 39324 |
| `src/code_80025938.c` | 0 | 0 | 17 | 0 | 24904 |
| `src/code_8002BA80.c` | 2 | 2 | 19 | 72 | 28148 |
| `src/code_80032874.c` | 1 | 0 | 40 | 76 | 24572 |
| `src/code_80038884.c` | 0 | 0 | 49 | 0 | 24060 |
| `src/code_8003E680.c` | 0 | 0 | 51 | 0 | 24328 |
| `src/code_80044588.c` | 0 | 0 | 20 | 0 | 6168 |

## Funciones `NON_MATCHING`

- `func_8002F990`
- `func_80030D60`

## Menciones sin símbolo de función (datos incrustados en el código; no cuentan)

- `func_800375F8`

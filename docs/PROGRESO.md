# Progreso de la descompilación

Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del
texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la
construcción normal) y de la tabla de símbolos.

## Resumen

| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |
|---|---:|---:|---:|---:|
| Arranque | 2 | 180 | 0 | 0 |
| Código del juego | 450 | 201416 | 428 | 169272 |
| Librerías Sony | 650 | 97488 | 0 | 0 |

Bytes de código del juego descompilados: 169272 de 201416 (84.04 %).
Funciones marcadas `NON_MATCHING`: 5.
Coherencia con el ensamblador: correcta (674 `glabel` en `asm/` + 428 en C = 1102; la tabla declara 1102).

## Por subsistema

| Subsistema | Archivos | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|---:|
| arranque_y_bucle_principal | 1 | 10 | 0 | 0 | 3404 | 3404 |
| audio_xa_y_spu | 1 | 37 | 0 | 0 | 8220 | 8220 |
| camara_y_bucle_logico | 1 | 10 | 1 | 0 | 11068 | 14576 |
| cargador_de_niveles_y_cd | 2 | 9 | 0 | 2 | 13592 | 14264 |
| colision_y_terreno | 1 | 4 | 0 | 0 | 12480 | 12480 |
| entrada_de_mando | 1 | 6 | 0 | 0 | 2784 | 2784 |
| gestion_y_dibujo_de_objetos | 4 | 32 | 2 | 8 | 12652 | 18624 |
| graficos_y_gte | 3 | 19 | 0 | 0 | 11812 | 11812 |
| inicializacion_de_motor | 1 | 12 | 0 | 4 | 5020 | 5276 |
| interprete_de_eventos | 1 | 195 | 0 | 2 | 11788 | 11900 |
| logica_de_niveles | 3 | 20 | 1 | 0 | 41556 | 60648 |
| manejadores_por_tabla | 1 | 12 | 0 | 0 | 384 | 384 |
| menus_e_interfaz | 1 | 26 | 0 | 1 | 13064 | 13644 |
| movimiento_y_objetos_de_escena | 3 | 27 | 0 | 0 | 18284 | 18284 |
| tarjeta_de_memoria | 1 | 9 | 1 | 0 | 3164 | 5116 |

## Por archivo

| Archivo | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|
| `src/arranque_y_bucle_principal_2.c` | 10 | 0 | 0 | 3404 | 3404 |
| `src/audio_xa_y_spu.c` | 37 | 0 | 0 | 8220 | 8220 |
| `src/camara_y_bucle_logico.c` | 10 | 1 | 0 | 11068 | 14576 |
| `src/cargador_de_niveles_y_cd.c` | 9 | 0 | 0 | 13592 | 13592 |
| `src/cargador_de_niveles_y_cd_2.c` | 0 | 0 | 2 | 0 | 672 |
| `src/colision_y_terreno.c` | 4 | 0 | 0 | 12480 | 12480 |
| `src/entrada_de_mando.c` | 6 | 0 | 0 | 2784 | 2784 |
| `src/gestion_y_dibujo_de_objetos.c` | 15 | 0 | 0 | 3812 | 3812 |
| `src/gestion_y_dibujo_de_objetos_2.c` | 10 | 2 | 8 | 4632 | 10604 |
| `src/gestion_y_dibujo_de_objetos_3.c` | 1 | 0 | 0 | 564 | 564 |
| `src/gestion_y_dibujo_de_objetos_4.c` | 6 | 0 | 0 | 3644 | 3644 |
| `src/graficos_y_gte.c` | 9 | 0 | 0 | 10072 | 10072 |
| `src/graficos_y_gte_10.c` | 6 | 0 | 0 | 1076 | 1076 |
| `src/graficos_y_gte_12.c` | 4 | 0 | 0 | 664 | 664 |
| `src/inicializacion_de_motor.c` | 12 | 0 | 4 | 5020 | 5276 |
| `src/interprete_de_eventos.c` | 195 | 0 | 2 | 11788 | 11900 |
| `src/logica_de_niveles.c` | 1 | 0 | 0 | 19880 | 19880 |
| `src/logica_de_niveles_2.c` | 3 | 0 | 0 | 2016 | 2016 |
| `src/logica_de_niveles_3.c` | 16 | 1 | 0 | 19660 | 38752 |
| `src/manejadores_por_tabla.c` | 12 | 0 | 0 | 384 | 384 |
| `src/menus_e_interfaz.c` | 26 | 0 | 1 | 13064 | 13644 |
| `src/movimiento_y_objetos_de_escena.c` | 4 | 0 | 0 | 2116 | 2116 |
| `src/movimiento_y_objetos_de_escena_2.c` | 15 | 0 | 0 | 6336 | 6336 |
| `src/movimiento_y_objetos_de_escena_3.c` | 8 | 0 | 0 | 9832 | 9832 |
| `src/tarjeta_de_memoria.c` | 9 | 1 | 0 | 3164 | 5116 |

## Funciones `NON_MATCHING`

- `SondearTarjeta`: Pendiente: puntuacion 525 con la configuracion versionada (g = 8 del archivo; ejes 76 de operando, 0 reordenadas, 188 insertadas o borradas). Flujo, orden de instrucciones y distribucion de bloques iguales al original; quedan el reparto de registros del recorrido del directorio y el orden de los dos operandos en las sumas de direccion del recorrido. Causa del residuo: el original recorre el bucle del directorio con el optimizador de bucles (base y base mas 0x24 izadas, desplazamiento de la ranura reducido a un registro que avanza 0x28 tras el contador, una copia suya en el preludio de cada buc
- `func_80026FEC`: Pendiente: puntuacion 590 con la configuracion versionada (g = 8 del archivo; ejes 496 de operando, 6 reordenadas, 156 insertadas o borradas). Los registros guardados coinciden con el original. Aparte de las diferencias de operando de forma simbolica (`%gp_rel(D_...)`, `%lo(D_1F800030)`, `%hi(D_80010012)` y `%lo(D_8006AA70+0x1)` en los dos almacenes que el ensamblador del original nombra D_8006AA71, 0x80027134 y 0x8002A82C: mismo codigo maquina), el residuo son dos causas. (1) La constante 0x1000 de los tres bloques de escala sale en t4 y el original la tiene en t7, y en el almacen posterior d
- `func_800353B0`: Pendiente: puntuacion 235 con la configuracion versionada (g = 8 del archivo): 93 diferencias de operando, 0 lineas reordenadas y 88 insertadas o borradas. El flujo coincide. Quedan diferencias de registros y de forma simbolica: (1) el registro de recarga de los punteros que las macros de la GTE leen de memoria o reciben como direccion constante, t7 aqui y a3 en el original (35 lineas); (2) 9 lineas de forma simbolica con los mismos bytes: el byte D_8006AA7C, que el original lee por el simbolo y aqui sale como `D_8006AA70+0xc`, y las direcciones del scratchpad que el desensamblado del original
- `func_80037FE8`: Pendiente: puntuacion 100 con la configuracion versionada (g = 8 del archivo; ejes 16 de operando, 0 reordenadas, 38 insertadas o borradas). Todos los grupos coinciden en instrucciones y en registros. Queda una sola instruccion distinta, la suma del indice con el puntero de estado del grupo 0xB8 (0x800383EC): el original la emite con el indice primero (`addu v0,v0,s4`) y el C con el puntero primero (`addu v0,s4,v0`); el resto son las marcas de operando por nombre de simbolo (el original lleva D_8001013C y D_80010047 donde el C genera 0x13c(v0) y 0x47(v0), y los desplazamientos D_800100F6 a D_8
- `func_80039094`: Pendiente: puntuacion 260 con la configuracion versionada (g = 8 del archivo; ejes 75 de operando, 0 reordenadas, 104 insertadas o borradas). Todas las instrucciones coinciden en numero; quedan las marcas de operando por nombre de simbolo y una sola linea de registro, la comparacion `<` de la barra 0 antes de la llamada (0x80039144): el original compara el byte leido, que sigue en v1 (`sltu v0,v1,v0`), y el C compara la copia ancha que esta en a0 (`sltu v0,a0,v0`). En el volcado `.cse` la copia ancha es una copia de registro de la extension de la primera carga (insn 44, pseudo 80 a partir del 

## Rutinas manuscritas (siguen en ensamblador por diseño)

- `RunLogicAction` (56 bytes)
- `TestLogicCond` (56 bytes)
- `func_8003753C` (68 bytes)
- `func_80037580` (68 bytes)
- `func_800375C4` (52 bytes)
- `func_800379A0` (360 bytes)
- `func_80037B08` (248 bytes)
- `func_80037C00` (248 bytes)
- `func_80037CF8` (68 bytes)
- `func_8003BDD0` (580 bytes)
- `func_80044664` (496 bytes)
- `func_80044854` (176 bytes)
- `func_80044904` (60 bytes)
- `func_80044940` (112 bytes)
- `func_800449B0` (48 bytes)
- `func_800449E0` (36 bytes)

## Menciones sin símbolo de función (datos incrustados en el código; no cuentan)

- `func_800375F8`

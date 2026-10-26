# Progreso de la descompilación

Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del
texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la
construcción normal) y de la tabla de símbolos.

## Resumen

| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |
|---|---:|---:|---:|---:|
| Arranque | 2 | 180 | 0 | 0 |
| Código del juego | 449 | 201416 | 5 | 452 |
| Librerías Sony | 650 | 97488 | 0 | 0 |

Bytes de código del juego descompilados: 452 de 201416 (0.22 %).
Funciones marcadas `NON_MATCHING`: 2.
Coherencia con el ensamblador: correcta (1096 `glabel` en `asm/` + 5 en C = 1101; la tabla declara 1101).

## Por subsistema

| Subsistema | Archivos | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|---:|
| arranque_y_bucle_principal | 1 | 0 | 0 | 10 | 0 | 3404 |
| audio_xa_y_spu | 1 | 0 | 0 | 37 | 0 | 8220 |
| camara_y_bucle_logico | 1 | 0 | 1 | 10 | 0 | 14576 |
| cargador_de_niveles_y_cd | 2 | 0 | 0 | 11 | 0 | 14264 |
| colision_y_terreno | 1 | 0 | 0 | 4 | 0 | 12480 |
| entrada_de_mando | 1 | 0 | 0 | 6 | 0 | 2784 |
| gestion_y_dibujo_de_objetos | 4 | 1 | 0 | 41 | 76 | 18624 |
| graficos_y_gte | 3 | 0 | 0 | 19 | 0 | 11812 |
| inicializacion_de_motor | 1 | 0 | 0 | 16 | 0 | 5276 |
| interprete_de_eventos | 1 | 3 | 0 | 193 | 140 | 11900 |
| logica_de_niveles | 3 | 0 | 1 | 20 | 0 | 60648 |
| manejadores_por_tabla | 1 | 0 | 0 | 12 | 0 | 384 |
| menus_e_interfaz | 1 | 0 | 0 | 27 | 0 | 13644 |
| movimiento_y_objetos_de_escena | 3 | 1 | 0 | 26 | 236 | 18284 |
| tarjeta_de_memoria | 1 | 0 | 0 | 10 | 0 | 5116 |

## Por archivo

| Archivo | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|
| `src/arranque_y_bucle_principal_2.c` | 0 | 0 | 10 | 0 | 3404 |
| `src/audio_xa_y_spu.c` | 0 | 0 | 37 | 0 | 8220 |
| `src/camara_y_bucle_logico.c` | 0 | 1 | 10 | 0 | 14576 |
| `src/cargador_de_niveles_y_cd.c` | 0 | 0 | 9 | 0 | 13592 |
| `src/cargador_de_niveles_y_cd_2.c` | 0 | 0 | 2 | 0 | 672 |
| `src/colision_y_terreno.c` | 0 | 0 | 4 | 0 | 12480 |
| `src/entrada_de_mando.c` | 0 | 0 | 6 | 0 | 2784 |
| `src/gestion_y_dibujo_de_objetos.c` | 1 | 0 | 14 | 76 | 3812 |
| `src/gestion_y_dibujo_de_objetos_2.c` | 0 | 0 | 20 | 0 | 10604 |
| `src/gestion_y_dibujo_de_objetos_3.c` | 0 | 0 | 1 | 0 | 564 |
| `src/gestion_y_dibujo_de_objetos_4.c` | 0 | 0 | 6 | 0 | 3644 |
| `src/graficos_y_gte.c` | 0 | 0 | 9 | 0 | 10072 |
| `src/graficos_y_gte_10.c` | 0 | 0 | 6 | 0 | 1076 |
| `src/graficos_y_gte_12.c` | 0 | 0 | 4 | 0 | 664 |
| `src/inicializacion_de_motor.c` | 0 | 0 | 16 | 0 | 5276 |
| `src/interprete_de_eventos.c` | 3 | 0 | 193 | 140 | 11900 |
| `src/logica_de_niveles.c` | 0 | 0 | 1 | 0 | 19880 |
| `src/logica_de_niveles_2.c` | 0 | 0 | 3 | 0 | 2016 |
| `src/logica_de_niveles_3.c` | 0 | 1 | 16 | 0 | 38752 |
| `src/manejadores_por_tabla.c` | 0 | 0 | 12 | 0 | 384 |
| `src/menus_e_interfaz.c` | 0 | 0 | 27 | 0 | 13644 |
| `src/movimiento_y_objetos_de_escena.c` | 0 | 0 | 4 | 0 | 2116 |
| `src/movimiento_y_objetos_de_escena_2.c` | 1 | 0 | 14 | 236 | 6336 |
| `src/movimiento_y_objetos_de_escena_3.c` | 0 | 0 | 8 | 0 | 9832 |
| `src/tarjeta_de_memoria.c` | 0 | 0 | 10 | 0 | 5116 |

## Funciones `NON_MATCHING`

- `func_8002F990`: Operacion aritmetica sobre un registro de 16 bits repartido en dos bytes (D_80010047 es el bajo y D_8001013C el alto). Diferencias con el original: este lee ambos bytes con un unico 'lui' (los dos simbolos comparten la parte alta) y conserva una copia del valor en el hueco de retardo del primer salto; el compilador genera dos 'lui' porque son variables externas distintas. Hay que declararlas como miembros de una misma estructura o arreglo.
- `func_80035244`: Lee los botones (D_80010010 sin los bits 0 y 3) y, si cambiaron, avanza siete secuencias de teclas de D_8005E768 (24 bytes cada una: caso, paso y diez teclas); al completar una ejecuta su caso con un switch de siete entradas. El archivo se compila con -G8 (config/opciones_compilacion.toml). Puntuacion 600: la tabla de saltos, los destinos de los casos, el reparto de registros del estado y la forma simbolica de D_80069662 coinciden; difieren la posicion del almacen en 0x104($gp) (el original no lo coloca en el hueco de retardo), las constantes 0x47 y 1, que el original carga antes del bucle, y 

## Menciones sin símbolo de función (datos incrustados en el código; no cuentan)

- `func_800375F8`

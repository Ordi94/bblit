# Progreso de la descompilación

Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del
texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la
construcción normal) y de la tabla de símbolos.

## Resumen

| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |
|---|---:|---:|---:|---:|
| Arranque | 2 | 180 | 0 | 0 |
| Código del juego | 450 | 201416 | 422 | 151072 |
| Librerías Sony | 650 | 97488 | 0 | 0 |

Bytes de código del juego descompilados: 151072 de 201416 (75.00 %).
Funciones marcadas `NON_MATCHING`: 11.
Coherencia con el ensamblador: correcta (680 `glabel` en `asm/` + 422 en C = 1102; la tabla declara 1102).

## Por subsistema

| Subsistema | Archivos | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|---:|
| arranque_y_bucle_principal | 1 | 10 | 0 | 0 | 3404 | 3404 |
| audio_xa_y_spu | 1 | 37 | 0 | 0 | 8220 | 8220 |
| camara_y_bucle_logico | 1 | 9 | 2 | 0 | 9660 | 14576 |
| cargador_de_niveles_y_cd | 2 | 8 | 1 | 2 | 1772 | 14264 |
| colision_y_terreno | 1 | 4 | 0 | 0 | 12480 | 12480 |
| entrada_de_mando | 1 | 6 | 0 | 0 | 2784 | 2784 |
| gestion_y_dibujo_de_objetos | 4 | 32 | 2 | 8 | 12652 | 18624 |
| graficos_y_gte | 3 | 19 | 0 | 0 | 11812 | 11812 |
| inicializacion_de_motor | 1 | 11 | 1 | 4 | 4484 | 5276 |
| interprete_de_eventos | 1 | 195 | 0 | 2 | 11788 | 11900 |
| logica_de_niveles | 3 | 19 | 2 | 0 | 38144 | 60648 |
| manejadores_por_tabla | 1 | 12 | 0 | 0 | 384 | 384 |
| menus_e_interfaz | 1 | 25 | 1 | 1 | 12328 | 13644 |
| movimiento_y_objetos_de_escena | 3 | 26 | 1 | 0 | 17996 | 18284 |
| tarjeta_de_memoria | 1 | 9 | 1 | 0 | 3164 | 5116 |

## Por archivo

| Archivo | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|
| `src/arranque_y_bucle_principal_2.c` | 10 | 0 | 0 | 3404 | 3404 |
| `src/audio_xa_y_spu.c` | 37 | 0 | 0 | 8220 | 8220 |
| `src/camara_y_bucle_logico.c` | 9 | 2 | 0 | 9660 | 14576 |
| `src/cargador_de_niveles_y_cd.c` | 8 | 1 | 0 | 1772 | 13592 |
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
| `src/inicializacion_de_motor.c` | 11 | 1 | 4 | 4484 | 5276 |
| `src/interprete_de_eventos.c` | 195 | 0 | 2 | 11788 | 11900 |
| `src/logica_de_niveles.c` | 1 | 0 | 0 | 19880 | 19880 |
| `src/logica_de_niveles_2.c` | 3 | 0 | 0 | 2016 | 2016 |
| `src/logica_de_niveles_3.c` | 15 | 2 | 0 | 16248 | 38752 |
| `src/manejadores_por_tabla.c` | 12 | 0 | 0 | 384 | 384 |
| `src/menus_e_interfaz.c` | 25 | 1 | 1 | 12328 | 13644 |
| `src/movimiento_y_objetos_de_escena.c` | 4 | 0 | 0 | 2116 | 2116 |
| `src/movimiento_y_objetos_de_escena_2.c` | 15 | 0 | 0 | 6336 | 6336 |
| `src/movimiento_y_objetos_de_escena_3.c` | 7 | 1 | 0 | 9544 | 9832 |
| `src/tarjeta_de_memoria.c` | 9 | 1 | 0 | 3164 | 5116 |

## Funciones `NON_MATCHING`

- `CargarContenedor`: Pendiente: puntuacion 3888 con la configuracion versionada (g = 8 del archivo; ejes 306 de operandos, 2 de lineas reordenadas y 448 de lineas insertadas o borradas). La cifra incluye palabras con direcciones absolutas dentro del archivo (saltos y tablas de saltos), de modo que depende del tamano de las funciones anteriores y de cuantas instrucciones separan cada cuerpo de caso del de su tabla. Medido: el codigo generado tiene 2953 instrucciones y el original 2955; la diferencia son dos copias de registro (`move`) que el original conserva delante de una prueba y el C no emite (0x80041CDC y 0x80
- `LogicaObjetoMovil`: Pendiente: puntuacion 20 con la configuracion versionada (g = 8 del archivo; ejes 0 de operando, 0 reordenadas, 6 insertadas o borradas). Residuo medido: (1) en la rama del paso negativo del bloque de limites el original lee el campo en v0 (0x1bc), lo copia con `move v1,v0` (0x1c4) y suma sobre la copia, y aqui el orden de las dos lecturas es el contrario (la primera cae en v1 y la copia en v0). Causa medida en el volcado de la primera planificacion (`-dS`): el planificador ordena el bloque de abajo arriba; el almacen del limite alto y la suma empatan en prioridad 2, el almacen gana el ultimo 
- `SondearTarjeta`: Pendiente: puntuacion 560 con la configuracion versionada (g = 8 del archivo; ejes 76 de operando, 0 reordenadas, 198 insertadas o borradas). Flujo, orden de instrucciones y distribucion de bloques iguales al original; quedan el reparto de registros del recorrido del directorio, el orden de los dos operandos en las sumas de direccion del recorrido y, en el caso 4 del resultado del sondeo (`D_8006AA70[0x1B] = 5`, 0x80015E64 a 0x80015E70, y su `lui` en 0x80015B98), el intercambio de v0 y v1. En ese bloque el volcado `-dg` da v0 a la base (pseudo 463, 3 referencias, con su parte alta 464, 2) y v1
- `func_8001E600`: Pendiente: puntuacion 140 con la configuracion versionada (g = 8 del archivo; ejes 3 de operando, 0 reordenadas, 52 insertadas o borradas). Mismos accesos y almacenes que el original y las instrucciones en su mismo orden: lo que queda son nombres de registro. (1) El numero de cuadro toma a2 en 0x8001E610, 0x8001E62C y 0x8001E634 (v0 en el original). (2) La constante 2 toma a3 (t0 en el original), el objeto t0 (a3), el puntero al sprite t0 (v1), el campo 0x0E a2 (a3) y la suma de +2 v1 (a2). Causa medida con `-dl` y `-dg`: el pseudo de `dato_cuadro` (86) es global y la asignacion local, que va 
- `func_80026FEC`: Pendiente: puntuacion 780 con la configuracion versionada (g = 8 del archivo; ejes 496 de operando, 6 reordenadas, 167 insertadas o borradas). Los registros guardados coinciden con el original. Aparte de las diferencias de operando de forma simbolica (`%gp_rel(D_...)`, `%lo(D_1F800030)`, `%hi(D_80010012)` y `%lo(D_8006AA70+0x1)` en los dos almacenes que el ensamblador del original nombra D_8006AA71, 0x80027134 y 0x8002A82C: mismo codigo maquina), el residuo son cinco causas. (1) La constante 0x1000 de los tres bloques de escala sale en t4 y el original la tiene en t7, y en el almacen posterior
- `func_80032B2C`: Pendiente: puntuacion 30 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y el reparto de los registros coinciden; difiere solo el orden de dos cargas contiguas de la cadena de pruebas: el original carga v28.vy (`lh a0,0x2a(s0)`, 0x80032E00) antes que max.vy (`lh a2,0x52(a1)`, 0x80032E04) y GCC las emite al reves. La prueba se escribe `max.vy < v28.vy` y no `v28.vy > max.vy`: con la segunda max.vy se carga despues de v28.vy (como el original) pero el valor pasa a 7 usos ponderados sobre 8 instrucciones (1,75), supera al objeto en curso (pseudo 143, 14 usos 
- `func_800353B0`: Pendiente: puntuacion 235 con la configuracion versionada (g = 8 del archivo): 93 diferencias de operando, 0 lineas reordenadas y 88 insertadas o borradas. El flujo coincide. Quedan diferencias de registros y de forma simbolica: (1) un puntero del contexto GTE en t7 y el original en a3 (la mayor parte de las diferencias); (2) el byte D_8006AA7C que el original lee por el simbolo y aqui sale como `D_8006AA70+0xc`, y las direcciones del scratchpad que el desensamblado del original nombra como simbolos (los mismos bytes). La atenuacion sigue el flujo del original: el original tiene una sola llama
- `func_80037FE8`: Pendiente: puntuacion 185 con la configuracion versionada (g = 8 del archivo; ejes 16 de operando, 0 reordenadas, 58 insertadas o borradas). Todos los grupos coinciden en instrucciones; difiere el reparto de registros salvados de los grupos de los contadores 0xB6 (0x800382D8 a 0x800383A0) y 0xBA (0x80038508 a 0x800385C4), y las marcas de operando por nombre de simbolo (el original lleva D_8001013C y D_80010047 donde el C genera 0x13c(v0) y 0x47(v0), y los desplazamientos D_800100F6 a D_800100FA sobre una base compartida con el puntero de estado). En esos dos grupos el original guarda el punter
- `func_80039094`: Pendiente: puntuacion 295 con la configuracion versionada (g = 8 del archivo; ejes 73 de operando, 0 reordenadas, 112 insertadas o borradas). Todas las instrucciones coinciden en numero; quedan las marcas de operando por nombre de simbolo y siete lineas de registro en un bloque de la barra 0, tras la comparacion con el valor de la vida: el original deja la base de 0x80010000 en a1 y copia el valor mostrado a a0 con `move a0,v1` en el hueco de retardo de 0x800390F4; el C copia la base a a0 en esa posicion y compara con v1. En el volcado `.cse` la asignacion `mostrado = D_80069525` es una copia 
- `func_8003AF8C`: Pendiente: puntuacion 155 con la configuracion versionada (g = 8 del archivo; ejes 13 de operando, 0 reordenadas, 54 insertadas o borradas). El residuo es de nombres de registro, en tres puntos. (1) El brillo: el original lo calcula en a3, el registro del color (`subu a3,v1,v0`, 0x8003AFF4, y `addu a3,a3,v0`, 0x8003B008); aqui es un pseudo local de su bloque (4 usos sobre 5 instrucciones) y toma v1. Se supone, sin verificar, que en el original no era un pseudo local. (2) La lista, la ranura y la entrada: el original tiene la lista y la ranura en a0 (`addu a0,a0,v0`, 0x8003B1E8), la bandera en 
- `func_80045150`: Pendiente: puntuacion 505 con la configuracion versionada (g = 8 del archivo; ejes 5 de operando, 0 reordenadas, 18 insertadas o borradas). Residuo: la copia del puntero a la primitiva (ver el ultimo parrafo) y el bloque del color, donde la constante 0x80 y la intensidad salen las dos en a0 y el original carga la constante en v1 y deja la intensidad en el mismo registro que el color, a2 (`subu a2,v1,v0`, 0x800451F4, y `addu a2,a2,a0`, 0x80045210). En el volcado de reparto (`-dl`, `-dg`) la intensidad es un pseudo local de la rama, atado al de la constante, y el color un pseudo global que toma 

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

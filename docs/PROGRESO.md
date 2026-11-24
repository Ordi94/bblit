# Progreso de la descompilación

Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del
texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la
construcción normal) y de la tabla de símbolos.

## Resumen

| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |
|---|---:|---:|---:|---:|
| Arranque | 2 | 180 | 0 | 0 |
| Código del juego | 450 | 201416 | 419 | 142212 |
| Librerías Sony | 650 | 97488 | 0 | 0 |

Bytes de código del juego descompilados: 142212 de 201416 (70.61 %).
Funciones marcadas `NON_MATCHING`: 14.
Coherencia con el ensamblador: correcta (683 `glabel` en `asm/` + 419 en C = 1102; la tabla declara 1102).

## Por subsistema

| Subsistema | Archivos | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|---:|
| arranque_y_bucle_principal | 1 | 10 | 0 | 0 | 3404 | 3404 |
| audio_xa_y_spu | 1 | 37 | 0 | 0 | 8220 | 8220 |
| camara_y_bucle_logico | 1 | 8 | 3 | 0 | 2712 | 14576 |
| cargador_de_niveles_y_cd | 2 | 8 | 1 | 2 | 1772 | 14264 |
| colision_y_terreno | 1 | 4 | 0 | 0 | 12480 | 12480 |
| entrada_de_mando | 1 | 5 | 1 | 0 | 1260 | 2784 |
| gestion_y_dibujo_de_objetos | 4 | 32 | 2 | 8 | 12652 | 18624 |
| graficos_y_gte | 3 | 19 | 0 | 0 | 11812 | 11812 |
| inicializacion_de_motor | 1 | 11 | 1 | 4 | 4484 | 5276 |
| interprete_de_eventos | 1 | 195 | 0 | 2 | 11788 | 11900 |
| logica_de_niveles | 3 | 19 | 2 | 0 | 38144 | 60648 |
| manejadores_por_tabla | 1 | 12 | 0 | 0 | 384 | 384 |
| menus_e_interfaz | 1 | 24 | 2 | 1 | 11940 | 13644 |
| movimiento_y_objetos_de_escena | 3 | 26 | 1 | 0 | 17996 | 18284 |
| tarjeta_de_memoria | 1 | 9 | 1 | 0 | 3164 | 5116 |

## Por archivo

| Archivo | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|
| `src/arranque_y_bucle_principal_2.c` | 10 | 0 | 0 | 3404 | 3404 |
| `src/audio_xa_y_spu.c` | 37 | 0 | 0 | 8220 | 8220 |
| `src/camara_y_bucle_logico.c` | 8 | 3 | 0 | 2712 | 14576 |
| `src/cargador_de_niveles_y_cd.c` | 8 | 1 | 0 | 1772 | 13592 |
| `src/cargador_de_niveles_y_cd_2.c` | 0 | 0 | 2 | 0 | 672 |
| `src/colision_y_terreno.c` | 4 | 0 | 0 | 12480 | 12480 |
| `src/entrada_de_mando.c` | 5 | 1 | 0 | 1260 | 2784 |
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
| `src/menus_e_interfaz.c` | 24 | 2 | 1 | 11940 | 13644 |
| `src/movimiento_y_objetos_de_escena.c` | 4 | 0 | 0 | 2116 | 2116 |
| `src/movimiento_y_objetos_de_escena_2.c` | 15 | 0 | 0 | 6336 | 6336 |
| `src/movimiento_y_objetos_de_escena_3.c` | 7 | 1 | 0 | 9544 | 9832 |
| `src/tarjeta_de_memoria.c` | 9 | 1 | 0 | 3164 | 5116 |

## Funciones `NON_MATCHING`

- `ActualizarCamaraSeguimiento`: Pendiente: puntuacion 545 con la configuracion versionada (g = 8 del archivo; ejes 127 de operandos, 0 de lineas reordenadas y 214 de lineas insertadas o borradas). La resta `i = n - 10` del final de la funcion se escribe antes de la prueba de zonas y no dentro de ella: el original la calcula en el hueco de retardo del primer `beq` (`addiu s0,s1,-0xa` en 0x80034D94) y escrita dentro de la prueba sale en el hueco del `bnez` siguiente (665 con la resta dentro). El flujo, las macros vectoriales y las constantes coinciden. Por tramos, con desplazamientos desde 0x80033358 (la puntuacion cuenta como
- `CargarContenedor`: Pendiente: puntuacion 4963 con la configuracion versionada (g = 8 del archivo; ejes 292 de operandos, 8 de lineas reordenadas y 534 de lineas insertadas o borradas). La cifra incluye palabras con direcciones absolutas dentro del archivo (saltos y tablas de saltos), de modo que depende del tamano de las funciones anteriores y de cuantas instrucciones separan cada cuerpo de caso del de su tabla. Medido: el codigo generado tiene 2951 instrucciones y el original 2955; la diferencia son cuatro copias de registro (`move`) que el original conserva y el C no emite (0x80041CDC, 0x80042F20, 0x80042F78 y
- `LogicaObjetoMovil`: Pendiente: puntuacion 20 con la configuracion versionada (g = 8 del archivo; ejes 0 de operando, 0 reordenadas, 6 insertadas o borradas). Residuo medido: (1) en la rama del paso negativo del bloque de limites el original lee el campo en v0 (0x1bc), lo copia con `move v1,v0` (0x1c4) y suma sobre la copia, y aqui el orden de las dos lecturas es el contrario (la primera cae en v1 y la copia en v0): en el volcado de planificacion (`-dS`) la lectura que alimenta la suma queda antes que la lectura del limite alto, se supone, sin verificar, porque las dos tienen la misma prioridad (2 usos y el mismo 
- `SondearTarjeta`: Pendiente: puntuacion 560 con la configuracion versionada (g = 8 del archivo; ejes 76 de operando, 0 reordenadas, 198 insertadas o borradas). Flujo, orden de instrucciones y distribucion de bloques iguales al original; quedan permutaciones de registros temporales (v0/v1) en el bloque de la orden de grabar con sonido (base de D_8006AA70 y constante 5 del caso 4 del sondeo) y el reparto de registros del recorrido del directorio. Recorrido del directorio: el original recalcula en cada uso el desplazamiento de la ranura (tres cadenas `sll 4 ; subu ; sll 3` en 0x80015CC0, 0x80015D10 y 0x80015D40) y
- `func_8001E600`: Pendiente: puntuacion 190 con la configuracion versionada (g = 8 del archivo; ejes 3 de operando, 0 reordenadas, 60 insertadas o borradas). Mismos accesos y almacenes que el original. Ya igual al original: la cabecera (tabla de fotogramas leida en la reunion de las ramas, `lw v1,0x20(t3)` en 0x30 con `nop` en el hueco del `j`), la constante 2 al abrir el grupo de lecturas (`li t0,2`, 0x3c), la pagina en v1 y el orden de las cadenas aritmeticas, la lectura tardia del puntero crudo en v0 con el campo 0x0E entre ella y la suma del puntero al sprite, esa suma antes del primer almacen, las cadenas 
- `func_80026FEC`: Pendiente: puntuacion 760 con la configuracion versionada (g = 8 del archivo; ejes 496 de operando, 6 reordenadas, 159 insertadas o borradas). Difiere en: orden de cargas y reparto de temporales. Formas con efecto propio vigentes (medidas en estados anteriores de la funcion, sin remedir en el estado final; se supone, sin verificar, que cada una sigue bajando la cifra): leer la altura del objeto en una local antes de la histeresis baja; la copia local del hijo antes de soltarlo (`hijo_soltado`), que reproduce la carga del original del hijo; la resta de la X del portador en el barrido escrita di
- `func_80032B2C`: Pendiente: puntuacion 30 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y el reparto de los registros coinciden; difiere solo el orden de dos cargas contiguas de la cadena de pruebas: el original carga v28.vy (`lh a0,0x2a(s0)`, 0x80032E00) antes que max.vy (`lh a2,0x52(a1)`, 0x80032E04) y GCC las emite al reves. La prueba se escribe `max.vy < v28.vy` y no `v28.vy > max.vy`: con la segunda max.vy se carga despues de v28.vy (como el original) pero el valor pasa a 7 usos ponderados sobre 8 instrucciones (1,75), supera al objeto en curso (pseudo 143, 14 usos 
- `func_800353B0`: Pendiente: puntuacion 345 con la configuracion versionada (g = 8 del archivo): 91 diferencias de operando, 0 lineas reordenadas y 95 insertadas o borradas. El flujo coincide salvo el `nop` del hueco de retardo de 0x800357D4 (la copia del limite de la busqueda del modelo, ver abajo). Quedan diferencias de registros y de forma simbolica: (1) un puntero del contexto GTE en t7 y el original en a3 (la mayor parte de las diferencias; causa medida: la lista de destruidos de la macro de distancia aproximada declara `$7`, que su cuerpo escribe, y con ella la recarga evita `a3`; sin `$7` en la lista la 
- `func_80037FE8`: Pendiente: puntuacion 185 con la configuracion versionada (g = 8 del archivo; ejes 16 de operando, 0 reordenadas, 58 insertadas o borradas). Todos los grupos coinciden en instrucciones; difiere el reparto de registros salvados de los grupos de los contadores 0xB6 (0x800382D8 a 0x800383A0) y 0xBA (0x80038508 a 0x800385C4), y las marcas de operando por nombre de simbolo (el original lleva D_8001013C y D_80010047 donde el C genera 0x13c(v0) y 0x47(v0), y los desplazamientos D_800100F6 a D_800100FA sobre una base compartida con el puntero de estado). En esos dos grupos el original guarda el punter
- `func_80039094`: Pendiente: puntuacion 375 con la configuracion versionada (g = 8 del archivo; ejes 73 de operando, 0 reordenadas, 120 insertadas o borradas). Coinciden la estructura, los desplazamientos y los simbolos; las barras 3 y 7, los cuatro temporizadores y las pruebas del prologo coinciden en instrucciones y registros (quedan las marcas de operando por nombre de simbolo). Difiere solo el reparto de registros de dos bloques de la barra 0: (1) tras la comparacion con el valor de la vida: el original deja la base de 0x80010000 en a1 y copia el valor mostrado a a0 con `move a0,v1` en el hueco de retardo d
- `func_8003AE08`: Pendiente: puntuacion 40 con la configuracion versionada (ejes 2 de operando, 0 reordenadas, 14 insertadas o borradas); solo queda el nombre de dos registros en el segundo paquete. El enlace de 24 bits de cada paquete se escribe en una sola sentencia, `(x << 8) >> 8` con `x` de tipo `s32` (el original emite `sll` y `sra`). Las instrucciones salen en el orden del original (en el segundo paquete el `sll` va entre la carga del punto 6, 0x8003AF18, y su almacen) y el primer paquete coincide entero: paquete en v1, `sll` y `sra` sobre ese mismo registro tras los almacenes (0x8003AE9C), ranura de la 
- `func_8003AF8C`: Pendiente: puntuacion 40 con la configuracion versionada (g = 8 del archivo; ejes 13 de operando, 0 reordenadas, 14 insertadas o borradas). Dos causas. (1) El recorte de la direccion del primitivo a 24 bits se escribe en una sola sentencia (`p = (u32*)(((s32)p << 8) >> 8)`): el original emite `sll` y `sra` consecutivos sobre a1 (0x8003B218 y 0x8003B21C), tras los almacenes de la palabra de ordenacion (0x8003B210) y del color (0x8003B214); aqui el `sll` queda detras de los almacenes, como el original, pero su temporal cae en v0 y el `sra` escribe en a1 desde v0 (tres lineas de operando). Se sup
- `func_8004048C`: Pendiente: puntuacion 575 con la configuracion versionada (g = 8 del archivo). Reserva de pila: el original reserva 0x28 (`addiu sp` en 0x80040494) y sin la local el marco es 0x20; la cifra medida sin la local es 649 y con ella 575. El original no usa 0x10(sp) ni 0x14(sp) y guarda ra, s0, s1 y s2 en 0x24, 0x18, 0x1c y 0x20; el volcado del reparto no deja ningun pseudo sin registro, de modo que se desconoce que local del original desaparecio (se supone, sin verificar, que el original tenia una llamada con seis palabras de argumentos que el compilador elimino y que no reduce el area de argumento
- `func_80045150`: Pendiente: puntuacion 320 con la configuracion versionada (g = 8 del archivo; ejes 5 de operando, 0 reordenadas, 9 insertadas o borradas: la causa mayor es la copia del puntero a la primitiva (ver Residuo), y ademas la lectura de D_80069652 sale en a2 en lugar de v0 por compartir `color`). La intensidad y el color empaquetado comparten la local `color`, como en el original, donde la intensidad (`subu a2,v1,v0`, 0x800451F4) y el color (`addu a2,a2,a0`, 0x80045210) viven en el mismo registro: con una local para cada uno el compilador deja la intensidad en a0 y el color en a2 y la puntuacion es 5

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

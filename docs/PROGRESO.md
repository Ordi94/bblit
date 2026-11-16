# Progreso de la descompilación

Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del
texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la
construcción normal) y de la tabla de símbolos.

## Resumen

| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |
|---|---:|---:|---:|---:|
| Arranque | 2 | 180 | 0 | 0 |
| Código del juego | 450 | 201416 | 414 | 103232 |
| Librerías Sony | 650 | 97488 | 0 | 0 |

Bytes de código del juego descompilados: 103232 de 201416 (51.25 %).
Funciones marcadas `NON_MATCHING`: 19.
Coherencia con el ensamblador: correcta (688 `glabel` en `asm/` + 414 en C = 1102; la tabla declara 1102).

## Por subsistema

| Subsistema | Archivos | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|---:|
| arranque_y_bucle_principal | 1 | 9 | 1 | 0 | 1364 | 3404 |
| audio_xa_y_spu | 1 | 37 | 0 | 0 | 8220 | 8220 |
| camara_y_bucle_logico | 1 | 8 | 3 | 0 | 2712 | 14576 |
| cargador_de_niveles_y_cd | 2 | 7 | 2 | 2 | 1096 | 14264 |
| colision_y_terreno | 1 | 3 | 1 | 0 | 1432 | 12480 |
| entrada_de_mando | 1 | 5 | 1 | 0 | 1260 | 2784 |
| gestion_y_dibujo_de_objetos | 4 | 31 | 3 | 8 | 11516 | 18624 |
| graficos_y_gte | 3 | 18 | 1 | 0 | 7224 | 11812 |
| inicializacion_de_motor | 1 | 11 | 1 | 4 | 4484 | 5276 |
| interprete_de_eventos | 1 | 195 | 0 | 2 | 11788 | 11900 |
| logica_de_niveles | 3 | 18 | 3 | 0 | 18264 | 60648 |
| manejadores_por_tabla | 1 | 12 | 0 | 0 | 384 | 384 |
| menus_e_interfaz | 1 | 25 | 1 | 1 | 12328 | 13644 |
| movimiento_y_objetos_de_escena | 3 | 26 | 1 | 0 | 17996 | 18284 |
| tarjeta_de_memoria | 1 | 9 | 1 | 0 | 3164 | 5116 |

## Por archivo

| Archivo | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|
| `src/arranque_y_bucle_principal_2.c` | 9 | 1 | 0 | 1364 | 3404 |
| `src/audio_xa_y_spu.c` | 37 | 0 | 0 | 8220 | 8220 |
| `src/camara_y_bucle_logico.c` | 8 | 3 | 0 | 2712 | 14576 |
| `src/cargador_de_niveles_y_cd.c` | 7 | 2 | 0 | 1096 | 13592 |
| `src/cargador_de_niveles_y_cd_2.c` | 0 | 0 | 2 | 0 | 672 |
| `src/colision_y_terreno.c` | 3 | 1 | 0 | 1432 | 12480 |
| `src/entrada_de_mando.c` | 5 | 1 | 0 | 1260 | 2784 |
| `src/gestion_y_dibujo_de_objetos.c` | 15 | 0 | 0 | 3812 | 3812 |
| `src/gestion_y_dibujo_de_objetos_2.c` | 10 | 2 | 8 | 4632 | 10604 |
| `src/gestion_y_dibujo_de_objetos_3.c` | 1 | 0 | 0 | 564 | 564 |
| `src/gestion_y_dibujo_de_objetos_4.c` | 5 | 1 | 0 | 2508 | 3644 |
| `src/graficos_y_gte.c` | 8 | 1 | 0 | 5484 | 10072 |
| `src/graficos_y_gte_10.c` | 6 | 0 | 0 | 1076 | 1076 |
| `src/graficos_y_gte_12.c` | 4 | 0 | 0 | 664 | 664 |
| `src/inicializacion_de_motor.c` | 11 | 1 | 4 | 4484 | 5276 |
| `src/interprete_de_eventos.c` | 195 | 0 | 2 | 11788 | 11900 |
| `src/logica_de_niveles.c` | 0 | 1 | 0 | 0 | 19880 |
| `src/logica_de_niveles_2.c` | 3 | 0 | 0 | 2016 | 2016 |
| `src/logica_de_niveles_3.c` | 15 | 2 | 0 | 16248 | 38752 |
| `src/manejadores_por_tabla.c` | 12 | 0 | 0 | 384 | 384 |
| `src/menus_e_interfaz.c` | 25 | 1 | 1 | 12328 | 13644 |
| `src/movimiento_y_objetos_de_escena.c` | 4 | 0 | 0 | 2116 | 2116 |
| `src/movimiento_y_objetos_de_escena_2.c` | 15 | 0 | 0 | 6336 | 6336 |
| `src/movimiento_y_objetos_de_escena_3.c` | 7 | 1 | 0 | 9544 | 9832 |
| `src/tarjeta_de_memoria.c` | 9 | 1 | 0 | 3164 | 5116 |

## Funciones `NON_MATCHING`

- `ActualizarCamaraSeguimiento`: Pendiente: puntuacion 2590 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y las constantes coinciden. Por tramos, con desplazamientos desde 0x80033358 (la puntuacion cuenta como diferencia cada acceso por `$gp` del original frente al simbolo del actual, unas 97 lineas que no son diferencia de bytes): los bucles de las ocho sondas (modo de apuntado y seguimiento libre) coinciden con `i++` escrito DESPUES de la llamada a BarrerTerreno (con `i++` justo tras la llamada de colision, o tras la asignacion de `v30.vy`, el incremento del contador y del puntero sal
- `BarrerTerreno`: Pendiente: puntuacion 800 con la configuracion versionada (g = 0 del archivo; ejes 213 de operando, 3 reordenadas, 85 insertadas o borradas). Difiere en: orden de escrituras y reparto de registros, a saber, en los cuatro avances del recorrido general (subcelda y baldosa) el original almacena la copia del punto previo en rx o bx (rz/bz antes) despues de la copia `move` de la segunda lectura y con el punto previo en v1 y la altura en a1/a2, mientras que aqui ese almacen sube justo tras las lecturas y los registros salen permutados; y la posicion de dos instrucciones del prologo (el original colo
- `CargarContenedor`: Pendiente: puntuacion 21788 con la configuracion versionada (g = 8 del archivo). La cifra incluye palabras con direcciones absolutas dentro del archivo (saltos y tablas de saltos), de modo que depende del tamano de las funciones anteriores y de cuantas instrucciones separan cada cuerpo de caso del de su tabla. Medido: el codigo generado tiene 2944 instrucciones frente a 2955 del original, y alineando el texto de ambos 2834 coinciden en el mnemonico (95,9 %). Los cuerpos de los casos de los cinco `switch` y del despacho de primer nivel van en el orden de direcciones de las tablas de saltos del 
- `DibujarSombras`: Pendiente: puntuacion 825 con la configuracion versionada (g = 8 del archivo; ejes 20 de operando, 0 reordenadas, 43 insertadas o borradas). Difiere el reparto de registros y el orden del prologo y el cierre del bucle de nodos (el original conserva el salto condicional hacia atras). La direccion de la caja de relleno, que el original deriva de la base del scratchpad (`ori a0,s0,0x38`), se reproduce tomandola del propio contexto, `&c->caja`: baja de 930 a 825 (con la constante `(GsBOXF*)0x1F800038` salian `move a0,s0` y `ori a0,a0,0x38`). Causa medida del prologo (volcados de `cc1`): las dos le
- `LogicaObjetoMovil`: Pendiente: puntuacion 165 con la configuracion versionada (g = 8 del archivo; ejes 112 de operando, 4 reordenadas, 23 insertadas o borradas). Residuo medido en tres trozos: (1) bloque de limites del movil: el original deja el paso en a0, el limite alto en v0 y el bajo en v1 y conserva la copia `move v1,v0` tambien en la rama del paso negativo (0x1c4), mientras aqui el paso cae en v0, el limite alto en a0 y la suma de la rama negativa se pliega sin copia (la escritura directa de cada limite con su propia lectura del campo da el reparto del original en la rama positiva pero invierte v0 y v1 en l
- `ResolverReferenciasContenedor`: Pendiente: puntuacion 335 con la configuracion versionada (g = 8 del archivo; ejes 17 de operando, 0 reordenadas, 108 insertadas o borradas; el diff no muestra ninguna linea de un solo lado, todas son diferencias de registro). Mismas instrucciones, mismo flujo y mismos huecos de retardo que el ensamblador; difiere solo en el reparto de registros. El original deja en las cinco variables del primer bucle (lista A, puntero a los campos, busqueda en B, fin de los campos e identificador) v1, a0, a1, a2 y a3, y el identificador en a3 en todos los bucles de busqueda; aqui salen v1 (busqueda), a0, a1 
- `SondearTarjeta`: Pendiente: puntuacion 1255 con la configuracion versionada (g = 8 del archivo; ejes 72 de operando, 11 reordenadas, 216 insertadas o borradas). Flujo y distribucion de bloques iguales al original; quedan permutaciones de registros temporales (v0/v1, a0/a1) en el resultado de MemCardFormat, en la mascara de ranuras y en el bloque de tarjeta sin formato, el reparto de la suma de bloques por 0x2000 y, sobre todo, el segundo bucle del directorio: el original recalcula en cada uso el desplazamiento de la ranura (ranura * 120) y GCC lo iza del bucle como invariante. Medido en el volcado del optimiza
- `func_80017478`: Pendiente: puntuacion 3066 con la configuracion versionada (g = 8 del archivo). Ejes medidos con `diff`: 96 de operando, 19 reordenadas y 268 insertadas o borradas; el original ocupa 0x11EC bytes (1147 instrucciones). El marco del C es el del original, de 0x50 bytes, y el reparto de los registros salvados coincide con el del original (`w` s1, direccion de D_80069D18 s2, `mejor` s3, constante 0x2000000 s6, `mejor_d` s7, `dif` fp) salvo `a` y `v`. Formas que reproducen el original; entre parentesis, la puntuacion que da este mismo C con la forma contraria: - `k` es una sola variable que vive en 
- `func_8001E600`: Pendiente: puntuacion 905 con la configuracion versionada (g = 8 del archivo; ejes 3 de operando, 0 reordenadas, 55 insertadas o borradas). Difiere en: momento de dos lecturas y reparto de registros. Medido en los volcados de `cc1`: los seis pseudos globales (objeto, bloque, puntero al sprite, desplazamiento de color, indice y puntero al fotograma) se reparten como el original salvo el puntero al sprite (pseudo de 16 usos y vida 32, prioridad 2,0), que toma `a3` y en el original `v1`. Causa: el puntero crudo leido de +0x78 (pseudo local de 3 usos y vida 9) recibe `a3` de la asignacion local y 
- `func_80020B90`: Pendiente: puntuacion 3750 con la configuracion versionada (g = 8 del archivo; ejes 476 de operando, 5 reordenadas, 485 insertadas o borradas). La logica coincide. El tramo en Z de la guarda de D_80069D30 (0x800222B8..0x80022308) se escribe por un puntero a la base del arreglo (`p = D_80069D30; p[2]`) y con un valor propio del bloque (`z_nueva`) que recoge las tres ramas y se almacena una sola vez: el original carga la base en a0 (`lui v0 ; addiu a0,v0,%lo(D_80069D30)` en 0x800222B8) y lee y escribe el campo con desplazamiento 8 sobre ese registro, con el valor en v0; con el acceso por nombre 
- `func_80026FEC`: Pendiente: puntuacion 1790 con la configuracion versionada (g = 8 del archivo; ejes 496 de operando, 5 reordenadas, 252 insertadas o borradas). Difiere en: orden de cargas y reparto de temporales. Leer la altura del objeto en una local antes de la histeresis baja de 2655 a 2625; la copia local del hijo antes de soltarlo (`hijo_soltado`) reproduce la carga del original del hijo y baja de 2625 a 2605. La resta de la X del portador en el barrido se escribe directa (`o->param.trans.vx - o->p70->param.trans.vx`): con una local previa (`x_portador`) la cifra es 1915. La traslacion en Z de la rama de
- `func_80032B2C`: Pendiente: puntuacion 60 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y el reparto de los registros salvados coinciden; difiere la posicion de una sola instruccion: el original coloca el almacen de i58 (sw v0,0x58) tras la copia del objeto en curso (move v1,a1) y GCC lo deja antes, porque el do/while que abre las escrituras de a48 impide subir la copia por encima del almacen. Meter el almacen en ese do/while lo coloca bien pero intercambia a1 y a2 en la cadena de pruebas (60 tambien): el temporal del objeto en curso (14 usos ponderados sobre 25 instrucc
- `func_800353B0`: Pendiente: puntuacion 410 con la configuracion versionada (g = 8 del archivo): 91 diferencias de operando, 0 lineas reordenadas y 119 insertadas o borradas. El flujo coincide salvo el `nop` del hueco de retardo de 0x80035704 (la copia del limite de la busqueda del modelo, ver abajo). Quedan diferencias de registros y de forma simbolica: (1) un puntero del contexto GTE en t7 y el original en a3 (la mayor parte de las diferencias; causa medida: la lista de destruidos de la macro de distancia aproximada declara `$7`, que su cuerpo escribe, y con ella la recarga evita `a3`; sin `$7` en una copia d
- `func_80037FE8`: Pendiente: puntuacion 925 con la configuracion versionada (g = 8 del archivo; ejes 16 de operando, 0 reordenadas, 75 insertadas o borradas). Difiere en: reparto de registros de los dos ultimos grupos. Los cuatro primeros grupos coinciden en codigo (quedan solo las marcas de operando por nombre de simbolo: el original lleva D_8005E836 y D_8005E858 donde el C genera D_8005E830+6 y D_8005E830+0x28, y D_8001013C o D_80010047 donde el C genera 0x13c(v0) o 0x47(v0)). Residuo medido: (1) grupo del contador 0xB8 (D_800100F8): el original guarda el puntero a 0x80010000 en s4 y el puntero a la pila en s
- `func_80039094`: Pendiente: puntuacion 1300 con la configuracion versionada (g = 8 del archivo; ejes 67 de operando, 0 reordenadas, 159 insertadas o borradas). Coinciden la estructura, los desplazamientos y los simbolos; difiere en el reparto de registros de la barra 0 (el original deja la base de 0x80010000 en a1 y copia el valor mostrado a a0 con `move a0,v1` en el hueco de retardo de 0x5c; el C copia la base a a1 en esa posicion y compara con v1, de modo que el valor mostrado no tiene copia propia), en el orden de dos copias y tres huecos de retardo de la barra 0 y de la barra 3, y en el hueco de retardo de
- `func_8003AF8C`: Pendiente: puntuacion 360 con la configuracion versionada (g = 8 del archivo; ejes 13 de operando, 0 reordenadas, 56 insertadas o borradas). Las dos ramas que recortan el nivel de la lista coinciden: el nivel se guarda dentro de cada rama, antes de leer la lista, y el original las funde en una cola comun que empieza por ese almacen (con una variable `n` y un solo almacen tras la union la puntuacion sube de 360 a 575). La cola del color coincide en forma (`or ; lui 0x2c00 ; or`) y el color cae en a3 como en el original. Difiere el reparto de registros del resto: el original deja el desplazamien
- `func_8004048C`: Pendiente: puntuacion 1655 con la configuracion versionada (g = 8 del archivo): 52 diferencias de operando, 0 lineas reordenadas y 270 insertadas o borradas. Reserva de pila: el original reserva 0x28 (`addiu sp` en 0x80040494) y sin la local el marco es 0x20; la cifra medida sin la local es 1729 y con ella 1655. El original no usa 0x10(sp) ni 0x14(sp) y guarda ra, s0, s1 y s2 en 0x24, 0x18, 0x1c y 0x20; el volcado del reparto no deja ningun pseudo sin registro, de modo que se desconoce que local del original desaparecio (en una copia de diagnostico fuera de la rama, una llamada eliminada con s
- `func_80045150`: Pendiente: puntuacion 1356 con la configuracion versionada (g = 8 del archivo; ejes 4 de operando, 0 reordenadas, 100 insertadas o borradas). Difiere en: reparto de registros guardados. Misma estructura de bucle y de escrituras de la primitiva; el original reparte s1 a la coordenada y y s3 a la v del glifo, s6 al contador y s7 y s8 a las dimensiones, el C los reparte al reves (el contador queda con la menor prioridad de los registros guardados), y carga el puntero a la primitiva (D_80076188) despues de la direccion de la cabeza de la lista, mientras GCC lo adelanta. Leer el puntero a la primit
- `main`: Pendiente: puntuacion 315 con la configuracion versionada (g = 8 del archivo; ejes 48 de operando, 0 reordenadas, 108 insertadas o borradas). Difiere en: copia del cero y registros v0/v1. El flujo y los tipos coinciden (pausa y demostracion son s16, el contador de cuadros D_80069676 es volatile u16); el estado principal y los registros del mando se acceden por su direccion sin variable local (con una copia local del puntero la puntuacion es 1025). Difieren la copia del cero del contador de ocioso (el original usa otro `move` desde zero) y los registros v0/v1 de la lectura de la pila de botones

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

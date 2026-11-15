# Progreso de la descompilación

Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del
texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la
construcción normal) y de la tabla de símbolos.

## Resumen

| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |
|---|---:|---:|---:|---:|
| Arranque | 2 | 180 | 0 | 0 |
| Código del juego | 450 | 201416 | 410 | 93368 |
| Librerías Sony | 650 | 97488 | 0 | 0 |

Bytes de código del juego descompilados: 93368 de 201416 (46.36 %).
Funciones marcadas `NON_MATCHING`: 23.
Coherencia con el ensamblador: correcta (692 `glabel` en `asm/` + 410 en C = 1102; la tabla declara 1102).

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
| logica_de_niveles | 3 | 17 | 4 | 0 | 13128 | 60648 |
| manejadores_por_tabla | 1 | 12 | 0 | 0 | 384 | 384 |
| menus_e_interfaz | 1 | 25 | 1 | 1 | 12328 | 13644 |
| movimiento_y_objetos_de_escena | 3 | 24 | 3 | 0 | 14540 | 18284 |
| tarjeta_de_memoria | 1 | 8 | 2 | 0 | 1892 | 5116 |

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
| `src/logica_de_niveles_3.c` | 14 | 3 | 0 | 11112 | 38752 |
| `src/manejadores_por_tabla.c` | 12 | 0 | 0 | 384 | 384 |
| `src/menus_e_interfaz.c` | 25 | 1 | 1 | 12328 | 13644 |
| `src/movimiento_y_objetos_de_escena.c` | 4 | 0 | 0 | 2116 | 2116 |
| `src/movimiento_y_objetos_de_escena_2.c` | 14 | 1 | 0 | 5768 | 6336 |
| `src/movimiento_y_objetos_de_escena_3.c` | 6 | 2 | 0 | 6656 | 9832 |
| `src/tarjeta_de_memoria.c` | 8 | 2 | 0 | 1892 | 5116 |

## Funciones `NON_MATCHING`

- `ActualizarCamaraSeguimiento`: Pendiente: puntuacion 10175 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y las constantes coinciden; difieren el reparto de registros temporales y la planificacion de las cargas y los almacenes en las sondas de apuntado (0x80033700-0x80033888), la direccion normalizada del modo guiado (0x80033CB4-0x80033D64), el giro lateral (0x80033F00-0x80034160), los barridos contra el terreno (0x80034348-0x80034720), las ocho sondas de empuje (0x800348C8-0x80034A9C) y el bloque de alturas (0x80034B00-0x80034E34).
- `AvanzarAnimacionSprite`: Pendiente: puntuacion 50 con la configuracion versionada (g = 8 del archivo; ejes 72 de operando, 0 reordenadas, 20 insertadas o borradas). Instrucciones y flujo identicos al original; solo difiere el temporal del cociente de las cinco multiplicaciones (desplazamientos 0x210, 0x230, 0x250, 0x29C y 0x2C4): el original usa $t4 y el C $t5, porque la macro de escala 0x1000 escribe $t4 y lo declara destruido (su cuerpo lo escribe) y esa lista no se altera; sin declararlo el C da $t4. Medido con un cambio temporal de la macro (no aplicado): si se anade tambien $13 a su lista el temporal pasa a $t6, 
- `BarrerTerreno`: Pendiente: puntuacion 800 con la configuracion versionada (g = 0 del archivo; ejes 213 de operando, 3 reordenadas, 85 insertadas o borradas). Difiere en: orden de escrituras y reparto de registros, a saber, en los cuatro avances del recorrido general (subcelda y baldosa) el original almacena la copia del punto previo en rx o bx (rz/bz antes) despues de la copia `move` de la segunda lectura y con el punto previo en v1 y la altura en a1/a2, mientras que aqui ese almacen sube justo tras las lecturas y los registros salen permutados; y la posicion de dos instrucciones del prologo (el original colo
- `CargarContenedor`: Pendiente: puntuacion 259843 con la configuracion versionada (g = 8 del archivo). La cifra depende de la composicion del objeto: la comparacion incluye palabras con direcciones absolutas dentro del archivo, y cualquier funcion cerrada en este mismo archivo las desplaza sin que cambie el codigo de esta (no comprobado comparando los objetos). Tambien depende del tamano de la funcion anterior, aun pendiente: al cambiar su tamano la cifra pasa de 259563 a 259843 sin tocar el codigo de esta. La estructura (bloques, bucles, llamadas, las cinco tablas de saltos) sigue el ensamblador completo y el mar
- `DibujarSombras`: Pendiente: puntuacion 825 con la configuracion versionada (g = 8 del archivo; ejes 20 de operando, 0 reordenadas, 43 insertadas o borradas). Difiere el reparto de registros y el orden del prologo y el cierre del bucle de nodos (el original conserva el salto condicional hacia atras). La direccion de la caja de relleno, que el original deriva de la base del scratchpad (`ori a0,s0,0x38`), se reproduce tomandola del propio contexto, `&c->caja`: baja de 930 a 825 (con la constante `(GsBOXF*)0x1F800038` salian `move a0,s0` y `ori a0,a0,0x38`). Causa medida del prologo (volcados de `cc1`): las dos le
- `LogicaBloqueEmpujable`: Pendiente: puntuacion 14728 con la configuracion versionada (g = 8 del archivo). Reparto de registros: el original guarda el objeto en s4, el scratchpad en s3, el area en s5 y el margen de la caja en s6 y deja s0 a s2 para los punteros de la preparacion; el compilador los reparte un registro mas abajo. La estructura de las ocho esquinas y de los dos modos coincide.
- `LogicaObjetoMovil`: Pendiente: puntuacion 165 con la configuracion versionada (g = 8 del archivo; ejes 112 de operando, 4 reordenadas, 23 insertadas o borradas). Residuo medido en tres trozos: (1) bloque de limites del movil: el original deja el paso en a0, el limite alto en v0 y el bajo en v1 y conserva la copia `move v1,v0` tambien en la rama del paso negativo (0x1c4), mientras aqui el paso cae en v0, el limite alto en a0 y la suma de la rama negativa se pliega sin copia (la escritura directa de cada limite con su propia lectura del campo da el reparto del original en la rama positiva pero invierte v0 y v1 en l
- `ResolverReferenciasContenedor`: Pendiente: puntuacion 335 con la configuracion versionada (g = 8 del archivo; ejes 17 de operando, 0 reordenadas, 108 insertadas o borradas; el diff no muestra ninguna linea de un solo lado, todas son diferencias de registro). Mismas instrucciones, mismo flujo y mismos huecos de retardo que el ensamblador; difiere solo en el reparto de registros. El original deja en las cinco variables del primer bucle (lista A, puntero a los campos, busqueda en B, fin de los campos e identificador) v1, a0, a1, a2 y a3, y el identificador en a3 en todos los bucles de busqueda; aqui salen v1 (busqueda), a0, a1 
- `SondearTarjeta`: Pendiente: puntuacion 2835 con la configuracion versionada (g = 8 del archivo; ejes 71 de operando, 0 reordenadas, 235 insertadas o borradas). Flujo y distribucion de bloques iguales al original; quedan permutaciones de registros temporales (v0/v1, a0/a1) en el resultado de MemCardFormat, en la mascara de ranuras y en el bloque de tarjeta sin formato, el reparto de la suma de bloques por 0x2000 y, sobre todo, el segundo bucle del directorio: el original recalcula en cada uso el desplazamiento de la ranura (ranura * 120) y GCC lo iza del bucle como invariante. Medido en el volcado del optimizad
- `func_800151FC`: Pendiente: puntuacion 17285 con la configuracion versionada (g = 8 del archivo). No se reprodujo la disposicion de los bloques locales de la pila ni las copias de estructura con comprobacion de alineacion en tiempo de ejecucion; un solo intento. Da formato al archivo de partida: arma en la pila un bloque de 0x200 bytes con la cabecera de la tarjeta ("SC", bandera de icono, un bloque, titulo, paleta e imagenes), lo copia con la cabecera de D_8006D060 y su suma de control al buffer D_80069520 + 0x2000 y escribe 0x400 bytes con open/write (hasta cinco intentos), comprobando despues la lectura.
- `func_80017478`: Pendiente: puntuacion 19849 con la configuracion versionada (g = 8 del archivo). Traduccion completa sin afinar: el reparto de registros y el orden de las comparaciones de las regiones no se han ajustado al original. La lista de registros destruidos de GEO_NORMA2_XZ la mueve 100 puntos (antes 19749). Desliza el volumen de a por la velocidad v contra los objetos solidos de la lista cuyos indicadores coinciden con mascara: para cada candidato lleva los cinco puntos del barrido a su sistema local, recorta la velocidad contra la pared que cruzan y, si ninguno la cruza, usa la arista mas cercana. D
- `func_8001D75C`: Pendiente: puntuacion 8935 con la configuracion versionada (g = 8 del archivo). Misma logica de condiciones y mismos almacenes, primer borrador sin igualar el orden de bloques: el original reparte el dano por defecto (1) y el de la rama con atacante en bloques compartidos con saltos distintos y dos formas de cerrar el llamador.
- `func_8001E600`: Pendiente: puntuacion 905 con la configuracion versionada (g = 8 del archivo; ejes 3 de operando, 0 reordenadas, 55 insertadas o borradas). Difiere en: momento de dos lecturas y reparto de registros. Medido en los volcados de `cc1`: los seis pseudos globales (objeto, bloque, puntero al sprite, desplazamiento de color, indice y puntero al fotograma) se reparten como el original salvo el puntero al sprite (pseudo de 16 usos y vida 32, prioridad 2,0), que toma `a3` y en el original `v1`. Causa: el puntero crudo leido de +0x78 (pseudo local de 3 usos y vida 9) recibe `a3` de la asignacion local y 
- `func_80020B90`: Pendiente: puntuacion 14290 con la configuracion versionada (g = 8 del archivo). Las diferencias son de reparto de registros (v0/v1/a0 y punteros s0-s2) y del orden en que el compilador planifica los almacenamientos de las transiciones de cada contacto; la logica coincide.
- `func_80026FEC`: Pendiente: puntuacion 2590 con la configuracion versionada (g = 8 del archivo; ejes 497 de operando, 3 reordenadas, 325 insertadas o borradas). Difiere en: orden de cargas y reparto de temporales. Leer la altura del objeto en una local antes de la histeresis baja de 2655 a 2625; la copia local del hijo antes de soltarlo (`hijo_soltado`) reproduce la carga del original del hijo y baja de 2625 a 2605; leer la X del portador en una local antes de restarla (`x_portador`) baja a 2590. El residuo que queda es de operandos (497) y de orden (3 lineas reordenadas, 325 insertadas o borradas). Los regist
- `func_80032B2C`: Pendiente: puntuacion 60 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y el reparto de los registros salvados coinciden; difiere la posicion de una sola instruccion: el original coloca el almacen de i58 (sw v0,0x58) tras la copia del objeto en curso (move v1,a1) y GCC lo deja antes, porque el do/while que abre las escrituras de a48 impide subir la copia por encima del almacen. Meter el almacen en ese do/while lo coloca bien pero intercambia a1 y a2 en la cadena de pruebas (60 tambien): el temporal del objeto en curso (14 usos ponderados sobre 25 instrucc
- `func_800353B0`: Pendiente: puntuacion 7961 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y las constantes coinciden; difieren el reparto de registros (el original conserva el scratchpad, &sx, &z6C y la mascara -3 en s1..s4 y no hoistea &v80 ni &c104), el relleno de los huecos de retardo de la macro de distancia (maspsx anade un nop extra tras dos de sus saltos) y la forma de la busqueda en la tabla D_8006A940 (el original relee el puntero guardado en el scratchpad en cada vuelta). Reescribir en C la suma de vectores y la distancia da 9641 y 11566 (ver GEO_SUMAR_W y GEO_
- `func_80037FE8`: Pendiente: puntuacion 2287 con la configuracion versionada (g = 8 del archivo; ejes 16 de operando, 0 reordenadas, 174 insertadas o borradas). Difiere en: reparto de registros y orden de cargas de las tablas. Una sola local de 32 bits para el byte alto y el byte extra del contador baja de 2297 a 2287. La estructura de los seis grupos coincide, pero el original rematerializa el puntero a 0x80010000 en cada grupo salvo en los tres ultimos, donde lo conserva en un registro salvado a traves de la llamada a la conversion BCD; GCC lo trata como una sola constante y reparte los registros de otra form
- `func_80039094`: Pendiente: puntuacion 1300 con la configuracion versionada (g = 8 del archivo; ejes 67 de operando, 0 reordenadas, 159 insertadas o borradas). Coinciden la estructura, los desplazamientos y los simbolos; difiere en el reparto de registros de la barra 0 (el original deja la base de 0x80010000 en a1 y copia el valor mostrado a a0 con `move a0,v1` en el hueco de retardo de 0x5c; el C copia la base a a1 en esa posicion y compara con v1, de modo que el valor mostrado no tiene copia propia), en el orden de dos copias y tres huecos de retardo de la barra 0 y de la barra 3, y en el hueco de retardo de
- `func_8003AF8C`: Pendiente: puntuacion 360 con la configuracion versionada (g = 8 del archivo; ejes 13 de operando, 0 reordenadas, 56 insertadas o borradas). Las dos ramas que recortan el nivel de la lista coinciden: el nivel se guarda dentro de cada rama, antes de leer la lista, y el original las funde en una cola comun que empieza por ese almacen (con una variable `n` y un solo almacen tras la union la puntuacion sube de 360 a 575). La cola del color coincide en forma (`or ; lui 0x2c00 ; or`) y el color cae en a3 como en el original. Difiere el reparto de registros del resto: el original deja el desplazamien
- `func_8004048C`: Pendiente: puntuacion 7254 con la configuracion versionada (g = 8 del archivo). El marco de pila del original es 8 bytes mayor, el reparto de registros de la rama de grabacion es otro y GCC fusiona el xor de (D_8006CFF2 ^ 0xFF) << 8 con el desplazamiento. Lectura del mando por cuadro. Con la entrada bloqueada (maquina de estados no nula o entidad con el bit 24) borra el estado y sale. En reproduccion de demo (0x8001004F) toma los cuatro registros del cuadro de la grabacion; si no, convierte el bufer de la BIOS (D_8006CFF1..7: id, botones invertidos y ejes) en botones logicos y ejes de +/-0x7F.
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

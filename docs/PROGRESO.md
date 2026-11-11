# Progreso de la descompilación

Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del
texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la
construcción normal) y de la tabla de símbolos.

## Resumen

| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |
|---|---:|---:|---:|---:|
| Arranque | 2 | 180 | 0 | 0 |
| Código del juego | 450 | 201416 | 397 | 81800 |
| Librerías Sony | 650 | 97488 | 0 | 0 |

Bytes de código del juego descompilados: 81800 de 201416 (40.61 %).
Funciones marcadas `NON_MATCHING`: 36.
Coherencia con el ensamblador: correcta (705 `glabel` en `asm/` + 397 en C = 1102; la tabla declara 1102).

## Por subsistema

| Subsistema | Archivos | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|---:|
| arranque_y_bucle_principal | 1 | 9 | 1 | 0 | 1364 | 3404 |
| audio_xa_y_spu | 1 | 37 | 0 | 0 | 8220 | 8220 |
| camara_y_bucle_logico | 1 | 8 | 3 | 0 | 2712 | 14576 |
| cargador_de_niveles_y_cd | 2 | 7 | 2 | 2 | 1096 | 14264 |
| colision_y_terreno | 1 | 2 | 2 | 0 | 680 | 12480 |
| entrada_de_mando | 1 | 5 | 1 | 0 | 1260 | 2784 |
| gestion_y_dibujo_de_objetos | 4 | 29 | 5 | 8 | 9504 | 18624 |
| graficos_y_gte | 3 | 17 | 2 | 0 | 5684 | 11812 |
| inicializacion_de_motor | 1 | 10 | 2 | 4 | 4152 | 5276 |
| interprete_de_eventos | 1 | 195 | 0 | 2 | 11788 | 11900 |
| logica_de_niveles | 3 | 16 | 5 | 0 | 10648 | 60648 |
| manejadores_por_tabla | 1 | 12 | 0 | 0 | 384 | 384 |
| menus_e_interfaz | 1 | 24 | 2 | 1 | 10244 | 13644 |
| movimiento_y_objetos_de_escena | 3 | 18 | 9 | 0 | 12172 | 18284 |
| tarjeta_de_memoria | 1 | 8 | 2 | 0 | 1892 | 5116 |

## Por archivo

| Archivo | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|
| `src/arranque_y_bucle_principal_2.c` | 9 | 1 | 0 | 1364 | 3404 |
| `src/audio_xa_y_spu.c` | 37 | 0 | 0 | 8220 | 8220 |
| `src/camara_y_bucle_logico.c` | 8 | 3 | 0 | 2712 | 14576 |
| `src/cargador_de_niveles_y_cd.c` | 7 | 2 | 0 | 1096 | 13592 |
| `src/cargador_de_niveles_y_cd_2.c` | 0 | 0 | 2 | 0 | 672 |
| `src/colision_y_terreno.c` | 2 | 2 | 0 | 680 | 12480 |
| `src/entrada_de_mando.c` | 5 | 1 | 0 | 1260 | 2784 |
| `src/gestion_y_dibujo_de_objetos.c` | 13 | 2 | 0 | 1800 | 3812 |
| `src/gestion_y_dibujo_de_objetos_2.c` | 10 | 2 | 8 | 4632 | 10604 |
| `src/gestion_y_dibujo_de_objetos_3.c` | 1 | 0 | 0 | 564 | 564 |
| `src/gestion_y_dibujo_de_objetos_4.c` | 5 | 1 | 0 | 2508 | 3644 |
| `src/graficos_y_gte.c` | 7 | 2 | 0 | 3944 | 10072 |
| `src/graficos_y_gte_10.c` | 6 | 0 | 0 | 1076 | 1076 |
| `src/graficos_y_gte_12.c` | 4 | 0 | 0 | 664 | 664 |
| `src/inicializacion_de_motor.c` | 10 | 2 | 4 | 4152 | 5276 |
| `src/interprete_de_eventos.c` | 195 | 0 | 2 | 11788 | 11900 |
| `src/logica_de_niveles.c` | 0 | 1 | 0 | 0 | 19880 |
| `src/logica_de_niveles_2.c` | 3 | 0 | 0 | 2016 | 2016 |
| `src/logica_de_niveles_3.c` | 13 | 4 | 0 | 8632 | 38752 |
| `src/manejadores_por_tabla.c` | 12 | 0 | 0 | 384 | 384 |
| `src/menus_e_interfaz.c` | 24 | 2 | 1 | 10244 | 13644 |
| `src/movimiento_y_objetos_de_escena.c` | 3 | 1 | 0 | 1572 | 2116 |
| `src/movimiento_y_objetos_de_escena_2.c` | 11 | 4 | 0 | 4416 | 6336 |
| `src/movimiento_y_objetos_de_escena_3.c` | 4 | 4 | 0 | 6184 | 9832 |
| `src/tarjeta_de_memoria.c` | 8 | 2 | 0 | 1892 | 5116 |

## Funciones `NON_MATCHING`

- `ActualizarCamaraSeguimiento`: Pendiente: puntuacion 10175 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y las constantes coinciden; difieren el reparto de registros temporales y la planificacion de las cargas y los almacenes en las sondas de apuntado (0x80033700-0x80033888), la direccion normalizada del modo guiado (0x80033CB4-0x80033D64), el giro lateral (0x80033F00-0x80034160), los barridos contra el terreno (0x80034348-0x80034720), las ocho sondas de empuje (0x800348C8-0x80034A9C) y el bloque de alturas (0x80034B00-0x80034E34).
- `AplicarCuadro`: Pendiente: puntuacion 465 con la configuracion versionada (g = 8 del archivo). Instrucciones y flujo identicos al original; difiere el reparto de registros callee-saved: el original deja el area de trabajo en $s1 y la ayuda en $s0 y GCC los intercambia (prioridad de global-alloc por referencias y longitud de vida); el radio de la caja y las banderas de la pista de ayudante en variables propias (distintas de las banderas de pose) bajan de 510.
- `AvanzarAnimacionSprite`: Pendiente: puntuacion 80 con la configuracion versionada (g = 8 del archivo). Instrucciones y flujo identicos al original; difieren el temporal del cociente de las multiplicaciones (el original usa $t4, el C $t5: la macro de escala 0x1000 escribe $t4 y lo declara destruido porque su cuerpo lo escribe, y esa lista no se altera; sin declararlo el C da $t4 y la puntuacion baja en 50) y el reparto de $v0/$v1 en la lectura de los dos contadores de 8 bits. La cuenta de eventos (3 usos sobre 7 instrucciones, 0,43) queda por debajo de los ticks (3 sobre 4, 0,75) y toma $v1; subirla a 1,75 con una vari
- `BarrerTerreno`: Pendiente: puntuacion 2030 con la configuracion versionada (g = 0 del archivo; ejes 213 de operando, 3 reordenadas, 118 insertadas o borradas). Difiere en: orden de escrituras y reparto de registros, a saber, el orden de las escrituras del avance por subcelda y por baldosa del recorrido general (rangos 0x8001A050-0x8001A563), el reparto de v0/v1 en las banderas de los planos 0x7E y 0x7F del caso estatico (0x8001BCD4-0x8001BF6B) y la posicion de dos instrucciones del prologo.
- `CargarContenedor`: Pendiente: puntuacion 259563 con la configuracion versionada (g = 8 del archivo). La cifra depende de la composicion del objeto: la comparacion incluye palabras con direcciones absolutas dentro del archivo, y cualquier funcion cerrada en este mismo archivo las desplaza sin que cambie el codigo de esta (no comprobado comparando los objetos). La estructura (bloques, bucles, llamadas, las cinco tablas de saltos) sigue el ensamblador completo y el marco de pila mide lo mismo (0x210 bytes); difieren el reparto de registros (s1 y s8 intercambiados desde el prologo), el orden de las cargas de la cabe
- `DibujarSombras`: Pendiente: puntuacion 930 con la configuracion versionada (g = 8 del archivo). Difiere el reparto de registros del prologo, el cierre del bucle de nodos (el original conserva el salto condicional hacia atras) y la direccion de la caja de relleno, que el original deriva de la base del scratchpad.
- `LogicaBloqueEmpujable`: Pendiente: puntuacion 14728 con la configuracion versionada (g = 8 del archivo). Reparto de registros: el original guarda el objeto en s4, el scratchpad en s3, el area en s5 y el margen de la caja en s6 y deja s0 a s2 para los punteros de la preparacion; el compilador los reparte un registro mas abajo. La estructura de las ocho esquinas y de los dos modos coincide.
- `LogicaDirectorCamara`: Pendiente: puntuacion 365 con la configuracion versionada (g = 8 del archivo). Prologo y salida de la busqueda por id: el original deriva la matriz del scratchpad de la base despues de calcular la parte alta de la camara, y sale de la busqueda con un salto directo al caso sin origen en lugar de volver a probar el cursor. La constante de la matriz (lui compartido con la base, ori) la emite el original despues del par que el optimizador de bucles iza para D_8006D928, y aqui sale antes: es la posicion de una constante fuera del bucle frente a una izada, y las colocaciones dentro del bucle la deja
- `LogicaObjetoMovil`: Pendiente: puntuacion 2510 con la configuracion versionada (g = 8 del archivo; ejes 106 de operando, 3 reordenadas, 134 insertadas o borradas). Reparto de registros y orden de instrucciones: el original comparte entre los modos 0x10 y 0x400 la llamada a ApplyMatrixLV, calcula el divisor del balancin con otro orden de cargas y reparte el paso y el empuje en a0 y v1; en el modo de movil con limites el original deja el limite alto en v0 y el bajo en v1 y escribe los dos antes de comprobar la bandera 0x40, mientras aqui caen en a0 y a2.
- `ResolverReferenciasContenedor`: Pendiente: puntuacion 1070 con la configuracion versionada (g = 8 del archivo; ejes 19 de operando, 0 reordenadas, 92 insertadas o borradas). Difiere en: reparto de registros y un nop de retardo. Mismas instrucciones y mismo flujo que el original; el original deja el puntero de la lista A en v1 y el de busqueda en a1, aqui salen a2 y v1, y rellena un nop de retardo que aqui queda. El identificador en 32 bits y las copias locales del contenedor y del nodo de C en sus ramas bajan de 1115 a 1070. Convierte, en un contenedor ya cargado, las referencias entre registros por identificador en desplaza
- `SondearTarjeta`: Pendiente: puntuacion 3160 con la configuracion versionada (g = 8 del archivo). Flujo y distribucion de bloques iguales al original; quedan permutaciones de registros temporales (v0/v1, a0/a1) en el resultado de MemCardFormat, en la mascara de ranuras y en el bloque de tarjeta sin formato, el reparto de la suma de bloques por 0x2000 y, sobre todo, el segundo bucle del directorio: el original recalcula en cada uso el desplazamiento de la ranura (ranura * 120) y GCC lo iza del bucle como invariante. Sondeo por cuadro de la tarjeta de memoria. Primero atiende la orden pendiente del banco de regis
- `func_800151FC`: Pendiente: puntuacion 17285 con la configuracion versionada (g = 8 del archivo). No se reprodujo la disposicion de los bloques locales de la pila ni las copias de estructura con comprobacion de alineacion en tiempo de ejecucion; un solo intento. Da formato al archivo de partida: arma en la pila un bloque de 0x200 bytes con la cabecera de la tarjeta ("SC", bandera de icono, un bloque, titulo, paleta e imagenes), lo copia con la cabecera de D_8006D060 y su suma de control al buffer D_80069520 + 0x2000 y escribe 0x400 bytes con open/write (hasta cinco intentos), comprobando despues la lectura.
- `func_80017478`: Pendiente: puntuacion 19849 con la configuracion versionada (g = 8 del archivo). Traduccion completa sin afinar: el reparto de registros y el orden de las comparaciones de las regiones no se han ajustado al original. La lista de registros destruidos de GEO_NORMA2_XZ la mueve 100 puntos (antes 19749). Desliza el volumen de a por la velocidad v contra los objetos solidos de la lista cuyos indicadores coinciden con mascara: para cada candidato lleva los cinco puntos del barrido a su sistema local, recorta la velocidad contra la pared que cruzan y, si ninguno la cruza, usa la arista mas cercana. D
- `func_80018664`: Pendiente: puntuacion 1555 con la configuracion versionada (g = 8 del archivo). Reparto de registros del tramo final del bucle de puntos (el original carga el area de trabajo en a2 y el objeto b en a1, y aqui caen al reves) y cadena de comparaciones de las esquinas que el original comparte entre regiones. Comprueba si alguno de los cinco puntos barridos por el volumen de a, llevados al sistema local de b, cae en el cuadrante de b que indican los angulos de sus esquinas (ampliado por el radio); devuelve 1 si lo toca. En las dos ramas de cierre (la de esquina positiva y la de esquina negativa en
- `func_8001C134`: Pendiente: puntuacion 455 con la configuracion versionada (g = 0, no carga globales). Los registros guardados y la copia de la zona coinciden; difiere el orden de las dos divisiones por 320 del resto de la baldosa (el original calcula x antes que z, GCC al reves con cualquier orden del fuente) y la suma del indice de subcelda (el original suma primero base + (baldosa << 6) y despues z / 40 * 8 + x / 40). Consulta la baldosa bajo el punto pos: busca la zona del punto (con el grupo recordado en res), lee el valor de la baldosa de 320 unidades y la subcelda de 40 unidades, y rellena res con la cl
- `func_8001C998`: Pendiente: puntuacion 1055 con la configuracion versionada (g = 8 del archivo; ejes 15 de operando, 1 reordenada, 43 insertadas o borradas). Difiere en: reparto de registros y orden de bloques de salto. Mismas ramas y almacenes que el ensamblador; el original reparte s0 al area de trabajo, s1 a la altura nueva, s2 al suelo anterior y s4 al tope, y con la envoltura el C los reparte igual; queda el orden de los bloques de salto del final. El area + 0x28 se precalcula como el original. La envoltura do/while (0) de la consulta de la baldosa no genera codigo: pondera por un nivel mas las referencia
- `func_8001D31C`: Pendiente: puntuacion 190 con la configuracion versionada (g = 8 del archivo; ejes 2 de operando, 0 reordenadas, 29 insertadas o borradas). Difiere en: reparto de registros del prologo. El original copia el primer argumento a a3 antes de cargar D_80069698 (puntero en a0, objeto llevado en v0 con su copia en v1); aqui el puntero queda en v1, el objeto llevado en a3 y la copia de x en t0, que ocupa el hueco de retardo del salto que en el original ocupa la copia del objeto llevado. El compilador funde la copia que el original conserva y no se ha encontrado una forma que la mantenga.
- `func_8001D588`: Pendiente: puntuacion 110 con la configuracion versionada (g = 8 del archivo; ejes 3 de operando, 0 reordenadas, 20 insertadas o borradas). Difiere en: copia del objeto enlazado, alias del objeto controlado y orden de un almacen. Mismas operaciones y almacenes; el original carga el objeto enlazado en +0x70 en v0 y lo copia a v1 en el hueco de retardo del salto (aqui se carga directo en v1), usa el objeto controlado en a2 sin copiarlo (aqui el alias de la variable `e` lo copia a a0) y ejecuta el almacen de la coordenada z del objeto (sw 0xec) antes del de cero a D_80069402 (el planificador lo h
- `func_8001D75C`: Pendiente: puntuacion 8935 con la configuracion versionada (g = 8 del archivo). Misma logica de condiciones y mismos almacenes, primer borrador sin igualar el orden de bloques: el original reparte el dano por defecto (1) y el de la rama con atacante en bloques compartidos con saltos distintos y dos formas de cerrar el llamador.
- `func_8001DF28`: Pendiente: puntuacion 585 con la configuracion versionada (g = 8 del archivo). Mismo codigo GTE y mismas operaciones; solo difiere el bloque de la bandera 0x8000000: el original calcula h52 antes que h94, repite el desplazamiento `(s16)alto >> 1` en dos expresiones sin fundirlas y resta el valor de 32 bits de h94 de h4E sin releerlo, mientras que GCC funde el desplazamiento, calcula primero h94 y relee la mitad con signo de 16 bits.
- `func_8001E528`: Pendiente: puntuacion 400 con la configuracion versionada (g = 8 del archivo). Mismos accesos y almacenes; el original conserva el registro del cuadro en t0 hasta leer las banderas, que es lo ultimo que hace (y deja el indice en v0 y las coordenadas en a3, a1, a0, a2), mientras que el C debe leer paleta y banderas antes de los almacenes de coordenadas: con las banderas al final el compilador copia el desplazamiento del indice dentro de cada rama (1340 y 715) y el registro del cuadro cae en v0, con la base de los fotogramas en v1 en vez de v0.
- `func_8001E600`: Pendiente: puntuacion 905 con la configuracion versionada (g = 8 del archivo; ejes 3 de operando, 0 reordenadas, 55 insertadas o borradas). Difiere en: momento de dos lecturas y reparto de registros. La lectura del campo 0x0E del fotograma en una local tres sentencias antes de su almacen, el cuadro por indice, la copia del modo y la copia del fotograma para la paleta bajan de 935 a 905. Mismos accesos y almacenes; difieren el momento de dos lecturas y el reparto de registros: el original copia el objeto a a3 al entrar, lee la tabla de fotogramas despues de la reunion de las dos ramas del cuadr
- `func_80020A90`: Pendiente: puntuacion 2290 con la configuracion versionada (g = 8 del archivo; ejes 2 de operando, 0 reordenadas, 45 insertadas o borradas). Difiere en: orden de bloques de salto (la suma del paso en dos sentencias baja de 2350 a 2290). Misma logica y mismos accesos; el original deja los retornos 2 y 1 como bloques separados con el delay slot relleno y la lista recorrida con el indice en el hueco de salto, el C los reunifica.
- `func_80020B90`: Pendiente: puntuacion 14290 con la configuracion versionada (g = 8 del archivo). Las diferencias son de reparto de registros (v0/v1/a0 y punteros s0-s2) y del orden en que el compilador planifica los almacenamientos de las transiciones de cada contacto; la logica coincide.
- `func_80026FEC`: Pendiente: puntuacion 2605 con la configuracion versionada (g = 8 del archivo; ejes 495 de operando, 5 reordenadas, 318 insertadas o borradas). Difiere en: orden de cargas y reparto de temporales. Leer la altura del objeto en una local antes de la histeresis baja de 2655 a 2625. Los registros guardados ya coinciden con el original; quedan unos 25 tramos de 1 a 6 instrucciones: orden de las cargas del contador de andadura y de las alturas del vuelo, el hueco de retardo de la llamada compartida a func_8001CFCC, la rama invertida del bucle de busqueda del objetivo y el temporal de mflo (a0 en lug
- `func_80032B2C`: Pendiente: puntuacion 60 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y el reparto de los registros salvados coinciden; difiere la posicion de una sola instruccion: el original coloca el almacen de i58 (sw v0,0x58) tras la copia del objeto en curso (move v1,a1) y GCC lo deja antes, porque el do/while que abre las escrituras de a48 impide subir la copia por encima del almacen. Meter el almacen en ese do/while lo coloca bien pero intercambia a1 y a2 en la cadena de pruebas (60 tambien): el temporal del objeto en curso (14 usos ponderados sobre 25 instrucc
- `func_800353B0`: Pendiente: puntuacion 7961 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y las constantes coinciden; difieren el reparto de registros (el original conserva el scratchpad, &sx, &z6C y la mascara -3 en s1..s4 y no hoistea &v80 ni &c104), el relleno de los huecos de retardo de la macro de distancia (maspsx anade un nop extra tras dos de sus saltos) y la forma de la busqueda en la tabla D_8006A940 (el original relee el puntero guardado en el scratchpad en cada vuelta). Reescribir en C la suma de vectores y la distancia da 9641 y 11566 (ver GEO_SUMAR_W y GEO_
- `func_800363D4`: Pendiente: puntuacion 110 con la configuracion versionada (g = 8 del archivo). Coincide el reparto del nodo en $a0 y del puntero inducido en $a1; difiere solo la base de la ultima escritura (el original escribe sw $zero,0x48($a0) tras copiar la direccion de la subestructura a $a0, y GCC la plega a 0x50($a1) sobre el puntero inducido). Las 0x2E escrituras de sw $zero,0($a2) del original son un bucle real de 0x2E vueltas (contador en $v1, sltiu/bnez, la escritura en el hueco de retardo), no una secuencia desenrollada; escritas como 0x2E sentencias explicitas el resultado empeora (895), porque GC
- `func_80037FE8`: Pendiente: puntuacion 2287 con la configuracion versionada (g = 8 del archivo; ejes 16 de operando, 0 reordenadas, 174 insertadas o borradas). Difiere en: reparto de registros y orden de cargas de las tablas. Una sola local de 32 bits para el byte alto y el byte extra del contador baja de 2297 a 2287. La estructura de los seis grupos coincide, pero el original rematerializa el puntero a 0x80010000 en cada grupo salvo en los tres ultimos, donde lo conserva en un registro salvado a traves de la llamada a la conversion BCD; GCC lo trata como una sola constante y reparte los registros de otra form
- `func_80039094`: Pendiente: puntuacion 1525 con la configuracion versionada (g = 8 del archivo; ejes 69 de operando, 0 reordenadas, 185 insertadas o borradas). Coinciden la estructura, los desplazamientos y los simbolos; difiere en el reparto de registros (la base de 0x80010000, el indice y el valor de las barras 3 y 7 caen en registros distintos de los del original, que usa a1, v0 y a0 segun el bloque), en el orden de dos copias y tres huecos de retardo de la barra 0 y de las barras 3 y 7, y en una recarga de la parte alta de D_8006AA7C que el compilador anade en los tres ultimos temporizadores. Leer el estad
- `func_8003AF8C`: Pendiente: puntuacion 1135 con la configuracion versionada (g = 8 del archivo; ejes 13 de operando, 0 reordenadas, 73 insertadas o borradas). Difiere en: reparto de registros y posicion de lecturas. Mismas instrucciones y flujo; el original deja el color en a3 y el desplazamiento de la textura en a2, y aqui caen en a0 y a1; la direccion de las palabras del sprite queda en v1 en lugar de a0, y la bandera de transparencia se lee en t0 (el original la deja en v1) y el almacen de la palabra de ordenacion va antes de elegir el modo. La direccion de la ranura en dos sentencias (base y luego desplaza
- `func_8003B5AC`: Pendiente: puntuacion 790 con la configuracion versionada (-G0 salvo g = 8 del archivo; ejes 45 de operando, 1 reordenada, 49 insertadas o borradas). Misma estructura de bloques y mismo bucle de objetos; difieren el registro de la carga del desplazamiento geometrico (gte_SetGeomOffset usa t4/t5 con dos desplazamientos y el original t2/t3 sin ellos), el reparto v0/v1 del nivel del fundido (el original guarda el nivel una sola vez tras la union y relee esc->estado.w8 despues del almacen de D_800694E2; aqui el almacen en cada rama obliga a la relectura pero la deja antes de ese almacen) y el orde
- `func_8004048C`: Pendiente: puntuacion 7254 con la configuracion versionada (g = 8 del archivo). El marco de pila del original es 8 bytes mayor, el reparto de registros de la rama de grabacion es otro y GCC fusiona el xor de (D_8006CFF2 ^ 0xFF) << 8 con el desplazamiento. Lectura del mando por cuadro. Con la entrada bloqueada (maquina de estados no nula o entidad con el bit 24) borra el estado y sale. En reproduccion de demo (0x8001004F) toma los cuatro registros del cuadro de la grabacion; si no, convierte el bufer de la BIOS (D_8006CFF1..7: id, botones invertidos y ejes) en botones logicos y ejes de +/-0x7F.
- `func_80045150`: Pendiente: puntuacion 1356 con la configuracion versionada (g = 8 del archivo; ejes 4 de operando, 0 reordenadas, 100 insertadas o borradas). Difiere en: reparto de registros guardados. Misma estructura de bucle y de escrituras de la primitiva; el original reparte s1 a la coordenada y y s3 a la v del glifo, s6 al contador y s7 y s8 a las dimensiones, el C los reparte al reves (el contador queda con la menor prioridad de los registros guardados), y carga el puntero a la primitiva (D_80076188) despues de la direccion de la cabeza de la lista, mientras GCC lo adelanta. Leer el puntero a la primit
- `func_80045C4C`: Pendiente: puntuacion 115 con la configuracion versionada (g = 8 del archivo). Mismo flujo, mismas escrituras y mismo orden; el estado del lector se lee como D_8006AA70[0xC] (arreglo) para que el lui de la base pueda separarse de la carga, como en el original. Solo difiere la primera comparacion: el original la hace sobre una copia de a2 en v0 (move v0,a2 ; beqz v0) y GCC compara a2 directamente, porque el CSE sustituye cualquier copia local del parametro por el primer pseudo de su clase (copia previa, bandera entera y copia dentro de un do/while dan 115; a diferencia de un retorno estrechado 
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

# Progreso de la descompilación

Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del
texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la
construcción normal) y de la tabla de símbolos.

## Resumen

| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |
|---|---:|---:|---:|---:|
| Arranque | 2 | 180 | 0 | 0 |
| Código del juego | 450 | 201416 | 345 | 46424 |
| Librerías Sony | 650 | 97488 | 0 | 0 |

Bytes de código del juego descompilados: 46424 de 201416 (23.05 %).
Funciones marcadas `NON_MATCHING`: 62.
Coherencia con el ensamblador: correcta (757 `glabel` en `asm/` + 345 en C = 1102; la tabla declara 1102).

## Por subsistema

| Subsistema | Archivos | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|---:|
| arranque_y_bucle_principal | 1 | 9 | 1 | 0 | 1364 | 3404 |
| audio_xa_y_spu | 1 | 34 | 3 | 0 | 6316 | 8220 |
| camara_y_bucle_logico | 1 | 7 | 3 | 1 | 2348 | 14576 |
| cargador_de_niveles_y_cd | 2 | 6 | 5 | 0 | 804 | 14264 |
| colision_y_terreno | 1 | 2 | 1 | 1 | 680 | 12480 |
| entrada_de_mando | 1 | 5 | 1 | 0 | 1260 | 2784 |
| gestion_y_dibujo_de_objetos | 4 | 23 | 7 | 12 | 5772 | 18624 |
| graficos_y_gte | 3 | 13 | 6 | 0 | 3316 | 11812 |
| inicializacion_de_motor | 1 | 6 | 8 | 2 | 1028 | 5276 |
| interprete_de_eventos | 1 | 192 | 3 | 2 | 10868 | 11900 |
| logica_de_niveles | 3 | 0 | 1 | 20 | 0 | 60648 |
| manejadores_por_tabla | 1 | 12 | 0 | 0 | 384 | 384 |
| menus_e_interfaz | 1 | 22 | 4 | 1 | 9256 | 13644 |
| movimiento_y_objetos_de_escena | 3 | 8 | 16 | 3 | 1400 | 18284 |
| tarjeta_de_memoria | 1 | 6 | 3 | 1 | 1628 | 5116 |

## Por archivo

| Archivo | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|
| `src/arranque_y_bucle_principal_2.c` | 9 | 1 | 0 | 1364 | 3404 |
| `src/audio_xa_y_spu.c` | 34 | 3 | 0 | 6316 | 8220 |
| `src/camara_y_bucle_logico.c` | 7 | 3 | 1 | 2348 | 14576 |
| `src/cargador_de_niveles_y_cd.c` | 6 | 3 | 0 | 804 | 13592 |
| `src/cargador_de_niveles_y_cd_2.c` | 0 | 2 | 0 | 0 | 672 |
| `src/colision_y_terreno.c` | 2 | 1 | 1 | 680 | 12480 |
| `src/entrada_de_mando.c` | 5 | 1 | 0 | 1260 | 2784 |
| `src/gestion_y_dibujo_de_objetos.c` | 12 | 2 | 1 | 1696 | 3812 |
| `src/gestion_y_dibujo_de_objetos_2.c` | 7 | 4 | 9 | 3184 | 10604 |
| `src/gestion_y_dibujo_de_objetos_3.c` | 1 | 0 | 0 | 564 | 564 |
| `src/gestion_y_dibujo_de_objetos_4.c` | 3 | 1 | 2 | 328 | 3644 |
| `src/graficos_y_gte.c` | 3 | 6 | 0 | 1576 | 10072 |
| `src/graficos_y_gte_10.c` | 6 | 0 | 0 | 1076 | 1076 |
| `src/graficos_y_gte_12.c` | 4 | 0 | 0 | 664 | 664 |
| `src/inicializacion_de_motor.c` | 6 | 8 | 2 | 1028 | 5276 |
| `src/interprete_de_eventos.c` | 192 | 3 | 2 | 10868 | 11900 |
| `src/logica_de_niveles.c` | 0 | 0 | 1 | 0 | 19880 |
| `src/logica_de_niveles_2.c` | 0 | 0 | 3 | 0 | 2016 |
| `src/logica_de_niveles_3.c` | 0 | 1 | 16 | 0 | 38752 |
| `src/manejadores_por_tabla.c` | 12 | 0 | 0 | 384 | 384 |
| `src/menus_e_interfaz.c` | 22 | 4 | 1 | 9256 | 13644 |
| `src/movimiento_y_objetos_de_escena.c` | 1 | 3 | 0 | 176 | 2116 |
| `src/movimiento_y_objetos_de_escena_2.c` | 6 | 9 | 0 | 1176 | 6336 |
| `src/movimiento_y_objetos_de_escena_3.c` | 1 | 4 | 3 | 48 | 9832 |
| `src/tarjeta_de_memoria.c` | 6 | 3 | 1 | 1628 | 5116 |

## Funciones `NON_MATCHING`

- `func_80014AC4`: Pendiente: puntuacion 895 con la configuracion versionada (g = 8 del archivo). El original direcciona la tabla de cuentas con `addiu v0,gp,0x38`, que maspsx emite desde ASPSX 2.80 (la version fijada), y calcula la base del nombre una sola vez antes del bucle. Variantes probadas: 8 (bucles por indice y por puntero). Busca en el directorio de la ranura `ranura` la entrada cuyo nombre coincide con los 18 caracteres de D_8005E051 y devuelve su indice, o -1 si no esta.
- `func_800151FC`: Pendiente: puntuacion 17285 con la configuracion versionada (g = 8 del archivo). Variantes probadas: 1. No se reprodujo la disposicion de los bloques locales de la pila ni las copias de estructura con comprobacion de alineacion en tiempo de ejecucion; un solo intento. Da formato al archivo de partida: arma en la pila un bloque de 0x200 bytes con la cabecera de la tarjeta ("SC", bandera de icono, un bloque, titulo, paleta e imagenes), lo copia con la cabecera de D_8006D060 y su suma de control al buffer D_80069520 + 0x2000 y escribe 0x400 bytes con open/write (hasta cinco intentos), comprobando
- `func_80015E94`: Pendiente: puntuacion 120 con la configuracion versionada (g = 8 del archivo). El original calcula las dos direcciones de $gp con `addiu a1,gp,0x40` y `addiu a2,gp,0x48` (ASPSX 2.80, la version fijada) y coloca el almacen del byte antes de cargar el modo. Variantes probadas: 3. Espera el resultado de la tarjeta: baja la bandera 0x3C($gp) y llama a MemCardSync(1, ...).
- `func_80016C0C`: Pendiente: puntuacion 70 con la configuracion versionada (g = 8 del archivo). Solo difiere la posicion de un addiu (el calculo de &o->m se emite una instruccion antes que en el original) y el registro del puntero de destino de la norma al cuadrado (v0 en lugar de a0). Motivo: reparto de registros del compilador (global-alloc ordena por refs/vida); cierra solo con una barrera asm vacia, recurso no admitido. Variantes probadas: 6.
- `func_800171E4`: Pendiente: puntuacion 308 con la configuracion versionada (g = 8 del archivo). El objeto de trabajo y el radio ampliado intercambian s2 y s3 respecto del original. Ademas el puntero de destino de la norma al cuadrado queda en v0 y el original lo mantiene en a0. Motivo: reparto de registros del compilador (global-alloc ordena por refs/vida); cierra solo con una barrera asm vacia, recurso no admitido. Variantes probadas: 12.
- `func_80017478`: Pendiente: puntuacion 10583 con la configuracion versionada (g = 8 del archivo). Traduccion completa sin afinar: el reparto de registros y el orden de las comparaciones de las regiones no se han ajustado al original. Variantes probadas: 1. Desliza el volumen de a por la velocidad v contra los objetos solidos de la lista cuyos indicadores coinciden con mascara: para cada candidato lleva los cinco puntos del barrido a su sistema local, recorta la velocidad contra la pared que cruzan y, si ninguno la cruza, usa la arista mas cercana. Devuelve el candidato elegido (el de menor distancia, con prefe
- `func_80018664`: Pendiente: puntuacion 2420 con la configuracion versionada (g = 8 del archivo). Reparto de registros del prologo (el original usa a0 como copia de la posicion de a) y cadena de comparaciones de las esquinas que el original comparte entre regiones. Variantes probadas: 3. Comprueba si alguno de los cinco puntos barridos por el volumen de a, llevados al sistema local de b, cae en el cuadrante de b que indican los angulos de sus esquinas (ampliado por el radio); devuelve 1 si lo toca.
- `func_80018D98`: Pendiente: puntuacion 108 con la configuracion versionada (g = 8 del archivo). El area de trabajo y el puntero a la diferencia intercambian s2 y s3 respecto del original. Ademas el puntero de destino de la norma al cuadrado queda en v0 y el original lo mantiene en a0. Motivo: reparto de registros del compilador (global-alloc ordena por refs/vida); cierra solo con una barrera asm vacia, recurso no admitido. Variantes probadas: 6.
- `func_80018F80`: Pendiente: puntuacion 108 con la configuracion versionada (g = 8 del archivo). El area de trabajo y el puntero a la diferencia intercambian s2 y s3 respecto del original. Ademas el puntero de destino de la norma al cuadrado queda en v0 y el original lo mantiene en a0. Motivo: reparto de registros del compilador (global-alloc ordena por refs/vida); cierra solo con una barrera asm vacia, recurso no admitido. Variantes probadas: 6.
- `func_8001C134`: Pendiente: puntuacion 1078 con la configuracion versionada (g = 0, no carga globales). El compilador asigna s0/s1 al reves (el original guarda la estructura de trabajo en s0 y el resultado en s1) y falta un `move t2,a3`. Variantes probadas: 9 (copias de z, orden de sentencias, barreras, copias locales de los punteros de trabajo). Consulta la baldosa bajo el punto pos: busca la zona del punto (con el grupo recordado en res), lee el valor de la baldosa de 320 unidades y la subcelda de 40 unidades, y rellena res con la clase de terreno. 0x7E y 0x7F de la subcelda son transiciones de zona; cualqui
- `func_8001C424`: Pendiente: puntuacion 1135 con la configuracion versionada (-G0). Misma estructura de ramas y mismos almacenes; en el bloque de despegue el original conserva dos copias de las banderas (move v1,v0) y ordena los almacenes de h108 y w10E de otro modo. Variantes probadas: 14.
- `func_8001C6CC`: Pendiente: puntuacion 498 con la configuracion versionada (-G0). Misma secuencia de llamadas y almacenes; el original reparte s1 al objeto y s0 al area de trabajo y ordena un almacen de d->z antes de la lectura de w->h18, el C los asigna al reves. Variantes probadas: 7.
- `func_8001C998`: Pendiente: puntuacion 3636 con la configuracion versionada (-G0). Mismas ramas y almacenes que el ensamblador; el original reparte s0 al area de trabajo, s1 a la altura nueva y s2 al suelo anterior, y precalcula area + 0x28 al principio, el C asigna los registros en otro orden y cambia el reparto de los saltos. Variantes probadas: 2.
- `func_8001CC68`: Pendiente: puntuacion 40 con la configuracion versionada (g = 8 del archivo). Mismas escrituras y orden; en la suma de la posicion con el vector rotado el original carga el operando de la posicion en v0 y el del vector en a0, el C los carga al reves. Variantes probadas: 9.
- `func_8001D028`: Pendiente: puntuacion 300 con la configuracion versionada (g = 8 del archivo). Mismas operaciones y mismo orden de almacenes; el original copia el tercer argumento a a3 al principio y lo reutiliza como cuarto argumento de la llamada, el C lo copia despues. Variantes probadas: 9.
- `func_8001D0FC`: Pendiente: puntuacion 670 con la configuracion versionada (g = 8 del archivo). Mismas busquedas y almacenes; el original conserva el argumento b en a3 y deriva b + 0x10 en s1 desde el principio, el C usa b en s1 y calcula b + 0x10 al final. Variantes probadas: 4.
- `func_8001D31C`: Pendiente: puntuacion 1624 con la configuracion versionada (g = 8 del archivo). Mismas operaciones y mismo orden de almacenes; el original no conserva el puntero a la camara en un registro salvado (recalcula D_8006D928 en los dos caminos y no reserva s0) y copia el primer argumento a a3 antes de cargar D_80069698, el C mantiene la camara en s0 y reparte v1 y a0 de otro modo en el prologo. Variantes probadas: 4.
- `func_8001D588`: Pendiente: puntuacion 840 con la configuracion versionada (g = 8 del archivo). Mismas operaciones y almacenes; el original ejecuta los dos almacenes de bytes de D_8006965A y D_80069659 antes de leer la lista del objeto, el planificador del C adelanta la lectura de p70. Variantes probadas: 3.
- `func_8001D75C`: Pendiente: puntuacion 8935 con la configuracion versionada (g = 8 del archivo). Misma logica de condiciones y mismos almacenes, primer borrador sin igualar el orden de bloques: el original reparte el dano por defecto (1) y el de la rama con atacante en bloques compartidos con saltos distintos y dos formas de cerrar el llamador. Variantes probadas: 1.
- `func_8001DA14`: Pendiente: puntuacion 590 con la configuracion versionada (g = 8 del archivo). Mismo bucle de prueba de rumbos y mismas llamadas GTE; el original asigna s4 al area de consulta, s7 al vector rotado y s6 al resultado de baldosa, el C reparte esos tres punteros y el modo centrado de otro modo, y calcula la mascara ~6 en un registro. Variantes probadas: 7.
- `func_8001DF28`: Pendiente: puntuacion 3500 con la configuracion versionada (g = 8 del archivo). Mismo codigo GTE (matriz de rotacion, vector de traslacion, rtps) y mismas operaciones; el original conserva el segundo argumento en a1 y copia solo el objeto a a2, y usa a3 como base de la matriz, el C copia ambos y usa t2. Variantes probadas: 8.
- `func_8001E1A4`: Pendiente: puntuacion 200 con la configuracion versionada (g = 8 del archivo). La unica diferencia es la carga del argumento de func_8003F06C: el original usa lw y el C con la conversion (s16) usa lh; sin la conversion el compilador iza la direccion de D_8006B558 fuera del bucle y la puntuacion sube a 692. Variantes probadas: 6.
- `func_8001E528`: Pendiente: puntuacion 1535 con la configuracion versionada (-G0). Mismos accesos y mismos almacenes; el original funde el desplazamiento de 16 bytes del registro tras la reunion de las dos ramas y reparte a0..a3 y t0 a las cuatro lecturas del registro, el C duplica el desplazamiento en cada rama y usa v0 y t0. Variantes probadas: 8.
- `func_8001E600`: Pendiente: puntuacion 2665 con la configuracion versionada (-G0). Mismos accesos y almacenes; el original calcula el desplazamiento de color en t2 y deja el puntero al sprite en v1, el C reparte otros registros y reordena las lecturas del registro del cuadro. Variantes probadas: 3.
- `func_80020240`: Pendiente: puntuacion 605 con la configuracion versionada (-G0). La condicion de continuar (bit 4 apagado o bit 0x10 activo) y la reunion de las dos ramas de la altura no se reproducen: el compilador adelanta la carga de las banderas y repite el almacen de h10A en cada rama. Variantes probadas: 10.
- `func_80020A90`: Pendiente: puntuacion 2360 con la configuracion versionada (-G0). Misma logica y mismos accesos; el original deja los retornos 2 y 1 como bloques separados con el delay slot relleno y la lista recorrida con el indice en el hueco de salto, el C los reunifica. Variantes probadas: 4.
- `func_8002F990`: Pendiente: puntuacion 350 con la configuracion versionada. Dos 'lui' donde el original usa uno solo para los dos bytes (los simbolos son variables externas distintas). Operacion aritmetica sobre un registro de 16 bits repartido en dos bytes (D_80010047 es el bajo y D_8001013C el alto). Diferencias con el original: este lee ambos bytes con un unico 'lui' (los dos simbolos comparten la parte alta) y conserva una copia del valor en el hueco de retardo del primer salto; el compilador genera dos 'lui' porque son variables externas distintas. Hay que declararlas como miembros de una misma estructura
- `func_8003147C`: Pendiente: puntuacion 190 con la configuracion versionada (g = 8 del archivo). El original deja el objeto controlado en a2 y el enlace p70 en a0 con una copia en v1; GCC los reparte en a0 y a1 sin esa copia. Variantes probadas: 8 (a0 reasignado, locales h y c, copia c = a0 antes y despues, puntero j al objeto controlado).
- `func_800324A4`: Pendiente: puntuacion 265 con la configuracion versionada (g = 8 del archivo). Solo difiere el prologo: el original reparte a0 (base del banco A), v1 (D_8006D064) y v0 (indice) y GCC los asigna en otro orden; las seis ramas siguientes coinciden. Variantes probadas: 8 (RA con puntero constante, extern D_80010040[], copia local de la mascara, tipos de v, puntero local).
- `func_80032708`: Pendiente: puntuacion 600 con la configuracion versionada (g = 8 del archivo). Los cuatro bucles de busqueda coinciden con la forma for/while; difiere el reparto de a0, a2 y v1 del prologo (el original comparte con a2 la base de D_80010040 y D_80010010). Variantes probadas: 9 (do/while con guarda, for, while y copias locales de la mascara).
- `func_80032B2C`: Pendiente: puntuacion 774 con la configuracion versionada (g = 8 del archivo). El flujo y las macros vectoriales coinciden; difiere el reparto de los registros salvados (el original deja los argumentos en s5 y s2 y los punteros hoisted &w->i58, &w->rot, &w->v28, &w->d30 en s6, s4, s3, s1). Variantes probadas: 15 (punteros locales hoisted en distinto orden y subconjunto, asignacion al inicio o dentro del bloque). Rayo de camara contra la lista de objetos solidos D_80069630: para cada objeto cuyos indicadores casan con la mascara y cuya caja esta a menos de su alcance, lleva la posicion al siste
- `func_80035244`: Pendiente: puntuacion 550 con la configuracion versionada (g = 8 del archivo). El original carga antes del bucle las constantes 0x47 y 1 de la ultima rama (t2 y t1) y por eso la tabla de saltos cae en t3; GCC las deja dentro de la rama. Variantes: indexado por D_8005E768[i], constantes en locales, paso++, puntero local al estado. Lee los botones (D_80010010 sin los bits 0 y 3) y, si cambiaron respecto al cuadro anterior (dato pequeno 0x104($gp)), avanza siete secuencias de teclas de D_8005E768 (24 bytes cada una: caso, paso y diez teclas); al completar una ejecuta su caso con un switch de siet
- `func_800353B0`: Pendiente: puntuacion 7961 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y las constantes coinciden; difieren el reparto de registros (el original conserva el scratchpad, &sx, &z6C y la mascara -3 en s1..s4 y no hoistea &v80 ni &c104), el relleno de los huecos de retardo de la macro de distancia (maspsx anade un nop extra tras dos de sus saltos) y la forma de la busqueda en la tabla D_8006A940 (el original relee el puntero guardado en el scratchpad en cada vuelta). Variantes probadas: 12 (locales del objeto, punteros hoisted, mascara en local, macro de d
- `func_80036164`: Pendiente: puntuacion 415 con la configuracion versionada (g = 8 del archivo). GCC deriva un segundo puntero inducido (p + 4) para los dos accesos de campo y devuelve el puntero base; el original usa un solo puntero con desplazamientos 0x0C y 0x04. Variantes probadas: 9.
- `func_800363D4`: Pendiente: puntuacion 205 con la configuracion versionada (g = 8 del archivo). El original mantiene el nodo en $a0 y deriva el puntero inducido en $a1; GCC los intercambia. Las 0x2E escrituras de sw $zero,0($a2) del original son un bucle real de 0x2E vueltas (contador en $v1, sltiu/bnez, la escritura en el hueco de retardo), no una secuencia desenrollada; escritas como 0x2E sentencias explicitas el resultado empeora (895), porque GCC no las pliega a ese bucle. Variantes probadas: 11.
- `func_80037184`: Pendiente: puntuacion 929 con la configuracion versionada (g = 8 del archivo). El cuerpo coincide instruccion por instruccion salvo el reparto de registros: GCC iza la constante 1 de la marca de visibilidad a $s5 fuera de los bucles y el original la carga junto al almacen. Variantes probadas: 9.
- `func_80037D3C`: Pendiente: puntuacion 120 con la configuracion versionada (g = 8 del archivo). Convierte un valor de 0 a 999 en tres digitos BCD (centenas, decenas, unidades); el original conserva las centenas en $a1 hasta el final y calcula centenas << 8 justo despues de la multiplicacion, mientras que GCC las deja en $v0 y las desplaza mas tarde (reparto de registros y orden de evaluacion). Variantes probadas: 12.
- `func_80037FE8`: Pendiente: puntuacion 3403 con la configuracion versionada (g = 8 del archivo). La estructura de los seis grupos coincide, pero el original rematerializa el puntero a 0x80010000 en cada grupo salvo en los tres ultimos, donde lo conserva en un registro salvado a traves de la llamada a la conversion BCD; GCC lo trata como una sola constante y reparte los registros de otra forma. Variantes probadas: 6.
- `func_80038884`: Pendiente: puntuacion 324 con la configuracion versionada (g = 8 del archivo). Coincide la estructura; difiere la asignacion de registros salvados (el original deja los tres identificadores en $s7, $s6 y $s5 y el parametro en $s4). Variantes probadas: 8.
- `func_8003A3D0`: Pendiente: puntuacion 316 con la configuracion versionada (g = 8 del archivo). El cuerpo y los saltos coinciden; difiere solo el reparto de registros salvados: el original deja el area de trabajo en $s0, la salida en $s1, el objeto en $s2 y la direccion de la baldosa en $s3; GCC da $s0 a la salida y $s3 al objeto. Ni el orden de las declaraciones locales, ni izar la direccion de la baldosa o la constante -1 antes de la primera rama, ni un bucle con salida explicita cambian el reparto (las dos ultimas formas empeoran a 1144 y 1326). Variantes probadas: 17.
- `func_8003AE08`: Pendiente: puntuacion 990 con la configuracion versionada (g = 8 del archivo). Las instrucciones y el flujo coinciden; difiere el reparto de registros (la tabla de ordenacion y el cursor intercambian v1 y a1, y las constantes 1, 0x80000000 y 0x05000000 caen en t0/a3/a2 en lugar de t1/t0/a3) y la posicion de la carga del cursor en el segundo paquete. Variantes probadas: 40 (720 permutaciones de las escrituras del primer paquete, cursor volatile, macros, estructura de paquete).
- `func_8003AF8C`: Pendiente: puntuacion 1680 con la configuracion versionada (g = 8 del archivo). Mismas instrucciones y flujo; difiere el reparto de registros (el desplazamiento de la textura cae en a0 y la plantilla en v1, en lugar de a2 y a0) y la posicion del almacen de la profundidad, que el original deja justo antes de indexar la lista de ordenacion. Variantes probadas: 160 (forma de la plantilla, orden de declaracion de los locales, acumulacion del color).
- `func_8003B354`: Pendiente: puntuacion 485 con la configuracion versionada (g = 8 del archivo). Las instrucciones y el flujo coinciden; solo difiere el reparto de v0/v1/a0 en la comparacion del numero de salas (la constante 0x10000 se carga antes del almacen de la profundidad) y en el puntero de la entrada visible. Variantes probadas: 60 (forma de la comparacion con shifts, orden de las escrituras previas al bucle, indexado frente a aritmetica de punteros, orden del cierre de la lista).
- `func_8003B5AC`: Pendiente: puntuacion 1518 con la configuracion versionada (-G0 salvo g = 8 del archivo). Misma estructura de bloques y mismo bucle de objetos; difieren el registro de la carga del desplazamiento geometrico (gte_SetGeomOffset usa t4/t5 y el original t2/t3), el reparto v0/v1 del nivel del fundido (el compilador reutiliza el registro en lugar de releer el nivel guardado, y el almacen de D_800694E2 se coloca antes que la relectura), el orden de las cargas de los limites del buffer en el prologo y el orden de dos movimientos de argumentos antes de func_8003AE08. Variantes probadas: 80 (900 permuta
- `func_8003E298`: Pendiente: puntuacion 70 con la configuracion versionada (g = 8 del archivo). Las instrucciones y el flujo coinciden; difiere solo el orden de los dos lui iniciales (el original emite la base de la tabla de posiciones antes que la del estado principal).
- `func_8003EDA8`: Pendiente: puntuacion 85 con la configuracion versionada (g = 8 del archivo). Las instrucciones y los registros coinciden (el resultado, una union de dos bytes, queda en s2); difiere solo la posicion de un sll (x << 8) respecto al mflo en la rama de angulo positivo.
- `func_8003F06C`: Pendiente: puntuacion 2792 con la configuracion versionada (g = 8 del archivo). El flujo coincide; el original recorre la tabla de efectos con dos punteros que avanzan juntos (entrada y entrada + 4) y aqui la reduccion de fuerza del bucle exterior reparte un tercero para los accesos de +2 y +3, lo que desplaza los registros s.
- `func_8004048C`: Pendiente: puntuacion 7254 con la configuracion versionada (g = 8 del archivo). El marco de pila del original es 8 bytes mayor, el reparto de registros de la rama de grabacion es otro y GCC fusiona el xor de (D_8006CFF2 ^ 0xFF) << 8 con el desplazamiento. Variantes probadas: 14 (switch con goto, if/else, copias). Lectura del mando por cuadro. Con la entrada bloqueada (maquina de estados no nula o entidad con el bit 24) borra el estado y sale. En reproduccion de demo (0x8001004F) toma los cuatro registros del cuadro de la grabacion; si no, convierte el bufer de la BIOS (D_8006CFF1..7: id, boton
- `func_80040F78`: Pendiente: puntuacion 390 con la configuracion versionada (g = 8 del archivo). Mismas instrucciones que el original; solo difiere el reparto de registros de la ultima etapa (el original deja el puntero del bucle en a2 y la constante 4 en a3, el indice en t0 en todas las etapas). Variantes probadas: mas de 10 (orden de declaracion, puntero propio por etapa, bucles rotados, parametro de relleno). Recorre la cabecera de secciones de un contenedor (n entradas de tipo, tamano y tamano alineado) y calcula la posicion, en bytes desde el inicio del archivo, de los datos del banco que se pide: devuelve
- `func_80041298`: Pendiente: puntuacion 1115 con la configuracion versionada (g = 8 del archivo). Mismas instrucciones y mismo flujo que el original; difiere el reparto de registros (el original deja el puntero de la lista A en v1 y el de busqueda en a1, aqui salen a2 y v1) y un nop de retardo que el original rellena. Variantes probadas: 14 (indice o puntero en el bucle de cinco, tipo del contador, temporales para el reparto, orden de declaracion). Convierte, en un contenedor ya cargado, las referencias entre registros por identificador en desplazamientos dentro de cada lista, para que el codigo que las usa no 
- `func_800415A0`: Pendiente: puntuacion 285 con la configuracion versionada (g = 8 del archivo). La estructura (bloques, bucles, llamadas, las cinco tablas de saltos) sigue el ensamblador completo y el marco de pila mide lo mismo (0x210 bytes); difieren el reparto de registros (s1 y s8 intercambiados desde el prologo), el orden de las cargas de la cabecera de secciones y el codigo de cada etiqueta, que GCC emite en otro orden. Variantes probadas: 2 (tamano del bufer de campos y de la tabla de secciones). Carga un contenedor de nivel o escena por su identificador (indice de D_8005F200) en `destino`. Lee la cabec
- `func_80044664`: Pendiente: puntuacion 13855 con la configuracion versionada (g = 0 del archivo). El original no usa marco de pila, guarda ra y s0..fp en el area de contexto que recibe en a2 y mantiene el flujo de entrada en a0, t4 y t0 durante todo el cuerpo, forma que GCC no emite. La descripcion en C sigue el algoritmo instruccion por instruccion. Variantes probadas: 1 (estado en estructura); las otras formas dependen de variables de registro, que no pueden ser los argumentos a0 a a2. Descomprime el flujo `entrada` en `salida`. El primer byte fija k (bits 0-2) y la escala de las longitudes largas (bits 3-4)
- `func_80044854`: Pendiente: puntuacion 5145 con la configuracion versionada (g = 0 del archivo). El original guarda ra en el contexto del llamador (4(s1)), devuelve el flujo en a0, t4 y t0 y avanza s0, que son registros del llamador que GCC no deja usar sin marco; no es expresable como funcion C con parametros. Variantes probadas: 2 (estado en estructura, 5145; variables de registro globales en a0, t4, t0, s0 y s1, 3955). Espera un sector completo en el anillo de lectura y deja el flujo apuntando a su primer byte. Sondea el contador de bytes disponibles (D_80069480) hasta 0xFFFF veces; si la unidad informa un 
- `func_80044940`: Pendiente: puntuacion 1460 con la configuracion versionada (g = 8 del archivo). Ensamblador manuscrito: neg y add con trampa de desbordamiento, registros fijos t0 a t2 y el temporal at en slt; GCC emite negu, addu y otro reparto de registros. Variantes probadas: 3.
- `func_800449B0`: Pendiente: puntuacion 960 con la configuracion versionada (g = 8 del archivo). Ensamblador manuscrito: registros fijos t0 y t1, nop explicito tras cada lw y el simbolo de la funcion vecina cargado con lui + lw; GCC reparte v0, v1 y a0. Variantes probadas: 2.
- `func_800449E0`: Pendiente: puntuacion 210 con la configuracion versionada (g = 8 del archivo). Solo difieren dos instrucciones muertas del original (ori a1,zero,0x200 y ori a2,zero,0x1FF antes de la etiqueta de entrada func_800449E8) que GCC elimina. Variantes probadas: 2.
- `func_80044A04`: Pendiente: puntuacion 415 con la configuracion versionada (g = 8 del archivo). Mismas escrituras y mismo orden; el original coloca lui a0 de la primera llamada despues de la lectura de D_800695A6 y la planificacion del compilador la adelanta. Variantes probadas: 6.
- `func_80044EA8`: Pendiente: puntuacion 355 con la configuracion versionada (g = 8 del archivo). Misma estructura que el original; difiere la planificacion de la carga de la direccion de D_8006D018 (lui) y de la mascara andi 0xFFFF. Variantes probadas: 9.
- `func_80045150`: Pendiente: puntuacion 3641 con la configuracion versionada (g = 8 del archivo). Misma estructura de bucle y de escrituras de la primitiva; el original reparte s6 al contador y s7 y fp a las dimensiones del glifo, el C los reparte al reves y desplaza el resto de la planificacion. Variantes probadas: 8.
- `func_800453D0`: Pendiente: puntuacion 230 con la configuracion versionada (g = 8 del archivo). El bucle de digitos incrementa el indice antes de leer en el original (li a1 frente a addiu a1,a1,1 y desplazamiento 0 frente a -1). Variantes probadas: 16.
- `func_80045C4C`: Pendiente: puntuacion 175 con la configuracion versionada (g = 8 del archivo). Mismo flujo y mismas escrituras; el original conserva una copia de a2 en v0 para la primera comparacion y emite el sh de +0x26 despues de la carga del byte de D_8006AA7C. Variantes probadas: 12.
- `main`: Pendiente: puntuacion 1025 con la configuracion versionada (g = 8 del archivo). Variantes probadas: 11. El flujo y los tipos coinciden (pausa y demostracion son s16, el contador de cuadros D_80069676 es volatile u16); difieren el reparto de registros salvados de las constantes 2 y 3 y de la tabla de tiempos D_8006CF68, y la base `lui` del estado se hoistea antes que en el original. Arranque y bucle principal. Tras iniciar el hardware y cargar el primer contenido, cada vuelta del bucle sincroniza los tres buffers, actualiza el cuadro, atiende la tarjeta de memoria, la pausa y la maquina de esta

## Rutinas manuscritas (siguen en ensamblador por diseño)

- `func_8003753C` (68 bytes)
- `func_80037580` (68 bytes)
- `func_800375C4` (52 bytes)
- `func_80037CF8` (68 bytes)
- `func_8003BDD0` (580 bytes)

## `INCLUDE_ASM` sin comentario en archivos con funciones en C

- `func_80033358` (`src/camara_y_bucle_logico.c`)
- `func_80019474` (`src/colision_y_terreno.c`)
- `func_8003690C` (`src/gestion_y_dibujo_de_objetos.c`)
- `func_8003760C` (`src/gestion_y_dibujo_de_objetos_2.c`)
- `func_800379A0` (`src/gestion_y_dibujo_de_objetos_2.c`)
- `func_80037B08` (`src/gestion_y_dibujo_de_objetos_2.c`)
- `func_80037C00` (`src/gestion_y_dibujo_de_objetos_2.c`)
- `func_80039094` (`src/gestion_y_dibujo_de_objetos_2.c`)
- `func_80039D44` (`src/gestion_y_dibujo_de_objetos_4.c`)
- `func_8003A5C8` (`src/gestion_y_dibujo_de_objetos_4.c`)
- `func_80044904` (`src/inicializacion_de_motor.c`)
- `func_80045498` (`src/inicializacion_de_motor.c`)
- `RunLogicAction` (`src/interprete_de_eventos.c`)
- `TestLogicCond` (`src/interprete_de_eventos.c`)
- `func_8001E720` (`src/movimiento_y_objetos_de_escena_3.c`)
- `func_8001F268` (`src/movimiento_y_objetos_de_escena_3.c`)
- `func_80020354` (`src/movimiento_y_objetos_de_escena_3.c`)

## Menciones sin símbolo de función (datos incrustados en el código; no cuentan)

- `func_800375F8`

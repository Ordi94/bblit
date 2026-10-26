# Progreso de la descompilación

Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del
texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la
construcción normal) y de la tabla de símbolos.

## Resumen

| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |
|---|---:|---:|---:|---:|
| Arranque | 2 | 180 | 0 | 0 |
| Código del juego | 450 | 201416 | 256 | 24176 |
| Librerías Sony | 650 | 97488 | 0 | 0 |

Bytes de código del juego descompilados: 24176 de 201416 (12.00 %).
Funciones marcadas `NON_MATCHING`: 22.
Coherencia con el ensamblador: correcta (846 `glabel` en `asm/` + 256 en C = 1102; la tabla declara 1102).

## Por subsistema

| Subsistema | Archivos | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|---:|
| arranque_y_bucle_principal | 1 | 9 | 1 | 0 | 1364 | 3404 |
| audio_xa_y_spu | 1 | 0 | 0 | 37 | 0 | 8220 |
| camara_y_bucle_logico | 1 | 7 | 3 | 1 | 2348 | 14576 |
| cargador_de_niveles_y_cd | 2 | 6 | 5 | 0 | 804 | 14264 |
| colision_y_terreno | 1 | 2 | 1 | 1 | 680 | 12480 |
| entrada_de_mando | 1 | 4 | 2 | 0 | 764 | 2784 |
| gestion_y_dibujo_de_objetos | 4 | 1 | 0 | 41 | 76 | 18624 |
| graficos_y_gte | 3 | 16 | 3 | 0 | 5024 | 11812 |
| inicializacion_de_motor | 1 | 0 | 0 | 16 | 0 | 5276 |
| interprete_de_eventos | 1 | 192 | 3 | 2 | 10868 | 11900 |
| logica_de_niveles | 3 | 0 | 1 | 20 | 0 | 60648 |
| manejadores_por_tabla | 1 | 12 | 0 | 0 | 384 | 384 |
| menus_e_interfaz | 1 | 0 | 0 | 27 | 0 | 13644 |
| movimiento_y_objetos_de_escena | 3 | 1 | 0 | 26 | 236 | 18284 |
| tarjeta_de_memoria | 1 | 6 | 3 | 1 | 1628 | 5116 |

## Por archivo

| Archivo | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|
| `src/arranque_y_bucle_principal_2.c` | 9 | 1 | 0 | 1364 | 3404 |
| `src/audio_xa_y_spu.c` | 0 | 0 | 37 | 0 | 8220 |
| `src/camara_y_bucle_logico.c` | 7 | 3 | 1 | 2348 | 14576 |
| `src/cargador_de_niveles_y_cd.c` | 6 | 3 | 0 | 804 | 13592 |
| `src/cargador_de_niveles_y_cd_2.c` | 0 | 2 | 0 | 0 | 672 |
| `src/colision_y_terreno.c` | 2 | 1 | 1 | 680 | 12480 |
| `src/entrada_de_mando.c` | 4 | 2 | 0 | 764 | 2784 |
| `src/gestion_y_dibujo_de_objetos.c` | 1 | 0 | 14 | 76 | 3812 |
| `src/gestion_y_dibujo_de_objetos_2.c` | 0 | 0 | 20 | 0 | 10604 |
| `src/gestion_y_dibujo_de_objetos_3.c` | 0 | 0 | 1 | 0 | 564 |
| `src/gestion_y_dibujo_de_objetos_4.c` | 0 | 0 | 6 | 0 | 3644 |
| `src/graficos_y_gte.c` | 6 | 3 | 0 | 3284 | 10072 |
| `src/graficos_y_gte_10.c` | 6 | 0 | 0 | 1076 | 1076 |
| `src/graficos_y_gte_12.c` | 4 | 0 | 0 | 664 | 664 |
| `src/inicializacion_de_motor.c` | 0 | 0 | 16 | 0 | 5276 |
| `src/interprete_de_eventos.c` | 192 | 3 | 2 | 10868 | 11900 |
| `src/logica_de_niveles.c` | 0 | 0 | 1 | 0 | 19880 |
| `src/logica_de_niveles_2.c` | 0 | 0 | 3 | 0 | 2016 |
| `src/logica_de_niveles_3.c` | 0 | 1 | 16 | 0 | 38752 |
| `src/manejadores_por_tabla.c` | 12 | 0 | 0 | 384 | 384 |
| `src/menus_e_interfaz.c` | 0 | 0 | 27 | 0 | 13644 |
| `src/movimiento_y_objetos_de_escena.c` | 0 | 0 | 4 | 0 | 2116 |
| `src/movimiento_y_objetos_de_escena_2.c` | 1 | 0 | 14 | 236 | 6336 |
| `src/movimiento_y_objetos_de_escena_3.c` | 0 | 0 | 8 | 0 | 9832 |
| `src/tarjeta_de_memoria.c` | 6 | 3 | 1 | 1628 | 5116 |

## Funciones `NON_MATCHING`

- `func_80014AC4`: Pendiente: puntuacion 895 con la configuracion versionada (g = 8 del archivo). El original direcciona la tabla de cuentas con `addiu v0,gp,0x38`, que maspsx solo emite desde ASPSX 2.80 (hoy 2.79), y calcula la base del nombre una sola vez antes del bucle. Variantes probadas: 8 (bucles por indice y por puntero). Busca en el directorio de la ranura `ranura` la entrada cuyo nombre coincide con los 18 caracteres de D_8005E051 y devuelve su indice, o -1 si no esta.
- `func_800151FC`: Pendiente: puntuacion 17285 con la configuracion versionada (g = 8 del archivo). Variantes probadas: 1. No se reprodujo la disposicion de los bloques locales de la pila ni las copias de estructura con comprobacion de alineacion en tiempo de ejecucion; un solo intento. Da formato al archivo de partida: arma en la pila un bloque de 0x200 bytes con la cabecera de la tarjeta ("SC", bandera de icono, un bloque, titulo, paleta e imagenes), lo copia con la cabecera de D_8006D060 y su suma de control al buffer D_80069520 + 0x2000 y escribe 0x400 bytes con open/write (hasta cinco intentos), comprobando
- `func_80015E94`: Pendiente: puntuacion 120 con la configuracion versionada (g = 8 del archivo). El original calcula las dos direcciones de $gp con `addiu a1,gp,0x40` y `addiu a2,gp,0x48` (ASPSX 2.80) y coloca el almacen del byte antes de cargar el modo; con 2.79 la forma no se emite. Variantes probadas: 3. Espera el resultado de la tarjeta: baja la bandera 0x3C($gp) y llama a MemCardSync(1, ...).
- `func_800171E4`: Pendiente: puntuacion 103 con la configuracion versionada (g = 8 del archivo). El objeto de trabajo y el radio ampliado intercambian s2 y s3 respecto del original. Variantes probadas: 8.
- `func_80017478`: Pendiente: puntuacion 10573 con la configuracion versionada (g = 8 del archivo). Traduccion completa sin afinar: el reparto de registros y el orden de las comparaciones de las regiones no se han ajustado al original. Variantes probadas: 1. Desliza el volumen de a por la velocidad v contra los objetos solidos de la lista cuyos indicadores coinciden con mascara: para cada candidato lleva los cinco puntos del barrido a su sistema local, recorta la velocidad contra la pared que cruzan y, si ninguno la cruza, usa la arista mas cercana. Devuelve el candidato elegido (el de menor distancia, con prefe
- `func_80018664`: Pendiente: puntuacion 2420 con la configuracion versionada (g = 8 del archivo). Reparto de registros del prologo (el original usa a0 como copia de la posicion de a) y cadena de comparaciones de las esquinas que el original comparte entre regiones. Variantes probadas: 3. Comprueba si alguno de los cinco puntos barridos por el volumen de a, llevados al sistema local de b, cae en el cuadrante de b que indican los angulos de sus esquinas (ampliado por el radio); devuelve 1 si lo toca.
- `func_8001C134`: Pendiente: puntuacion 1078 con la configuracion versionada (g = 0, no carga globales). El compilador asigna s0/s1 al reves (el original guarda la estructura de trabajo en s0 y el resultado en s1) y falta un `move t2,a3`. Variantes probadas: 9 (copias de z, orden de sentencias, barreras, copias locales de los punteros de trabajo). Consulta la baldosa bajo el punto pos: busca la zona del punto (con el grupo recordado en res), lee el valor de la baldosa de 320 unidades y la subcelda de 40 unidades, y rellena res con la clase de terreno. 0x7E y 0x7F de la subcelda son transiciones de zona; cualqui
- `func_8002F990`: Operacion aritmetica sobre un registro de 16 bits repartido en dos bytes (D_80010047 es el bajo y D_8001013C el alto). Diferencias con el original: este lee ambos bytes con un unico 'lui' (los dos simbolos comparten la parte alta) y conserva una copia del valor en el hueco de retardo del primer salto; el compilador genera dos 'lui' porque son variables externas distintas. Hay que declararlas como miembros de una misma estructura o arreglo.
- `func_8003147C`: Pendiente: puntuacion 190 con la configuracion versionada (g = 8 del archivo). El original deja el objeto controlado en a2 y el enlace p70 en a0 con una copia en v1; GCC los reparte en a0 y a1 sin esa copia. Variantes probadas: 8 (a0 reasignado, locales h y c, copia c = a0 antes y despues, puntero j al objeto controlado).
- `func_800324A4`: Pendiente: puntuacion 265 con la configuracion versionada (g = 8 del archivo). Solo difiere el prologo: el original reparte a0 (base del banco A), v1 (D_8006D064) y v0 (indice) y GCC los asigna en otro orden; las seis ramas siguientes coinciden. Variantes probadas: 8 (RA con puntero constante, extern D_80010040[], copia local de la mascara, tipos de v, puntero local).
- `func_80032708`: Pendiente: puntuacion 600 con la configuracion versionada (g = 8 del archivo). Los cuatro bucles de busqueda coinciden con la forma for/while; difiere el reparto de a0, a2 y v1 del prologo (el original comparte con a2 la base de D_80010040 y D_80010010). Variantes probadas: 9 (do/while con guarda, for, while y copias locales de la mascara).
- `func_80032B2C`: Pendiente: puntuacion 774 con la configuracion versionada (g = 8 del archivo). El flujo y las macros vectoriales coinciden; difiere el reparto de los registros salvados (el original deja los argumentos en s5 y s2 y los punteros hoisted &w->i58, &w->rot, &w->v28, &w->d30 en s6, s4, s3, s1). Variantes probadas: 15 (punteros locales hoisted en distinto orden y subconjunto, asignacion al inicio o dentro del bloque). Rayo de camara contra la lista de objetos solidos D_80069630: para cada objeto cuyos indicadores casan con la mascara y cuya caja esta a menos de su alcance, lleva la posicion al siste
- `func_80035244`: Pendiente: puntuacion 550 con la configuracion versionada (g = 8 del archivo). El original carga antes del bucle las constantes 0x47 y 1 de la ultima rama (t2 y t1) y por eso la tabla de saltos cae en t3; GCC las deja dentro de la rama. Variantes: indexado por D_8005E768[i], constantes en locales, paso++, puntero local al estado. Lee los botones (D_80010010 sin los bits 0 y 3) y, si cambiaron respecto al cuadro anterior (dato pequeno 0x104($gp)), avanza siete secuencias de teclas de D_8005E768 (24 bytes cada una: caso, paso y diez teclas); al completar una ejecuta su caso con un switch de siet
- `func_800353B0`: Pendiente: puntuacion 7961 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y las constantes coinciden; difieren el reparto de registros (el original conserva el scratchpad, &sx, &z6C y la mascara -3 en s1..s4 y no hoistea &v80 ni &c104), el relleno de los huecos de retardo de la macro de distancia (maspsx anade un nop extra tras dos de sus saltos) y la forma de la busqueda en la tabla D_8006A940 (el original relee el puntero guardado en el scratchpad en cada vuelta). Variantes probadas: 12 (locales del objeto, punteros hoisted, mascara en local, macro de d
- `func_80040240`: Pendiente: puntuacion 130 con la configuracion versionada (g = 8 del archivo). El original calcula la direccion del bloque de alineacion con `addiu a1,gp,0x10`; maspsx solo la reescribe a $gp desde la version 2.80 de ASPSX (gp_allow_la) y la configuracion versionada fija 2.79, de modo que sale `lui` + `addiu`. Con 2.80 la funcion coincide en bytes (puntuacion 25 por la forma simbolica de 0x800100E7 y de D_80069330) y el ejecutable completo sigue verificando. Variantes: base_gp + 0x10, variable intermedia al principio y al final, conversion a u32, definicion tentativa del dato pequeno. Vibracio
- `func_8004048C`: Pendiente: puntuacion 7264 con la configuracion versionada (g = 8 del archivo). El marco de pila del original es 8 bytes mayor, el reparto de registros de la rama de grabacion es otro y GCC fusiona el xor de (D_8006CFF2 ^ 0xFF) << 8 con el desplazamiento. Variantes probadas: 14 (switch con goto, if/else, copias). Lectura del mando por cuadro. Con la entrada bloqueada (maquina de estados no nula o entidad con el bit 24) borra el estado y sale. En reproduccion de demo (0x8001004F) toma los cuatro registros del cuadro de la grabacion; si no, convierte el bufer de la BIOS (D_8006CFF1..7: id, boton
- `func_80040F78`: Pendiente: puntuacion 390 con la configuracion versionada (g = 8 del archivo). Mismas instrucciones que el original; solo difiere el reparto de registros de la ultima etapa (el original deja el puntero del bucle en a2 y la constante 4 en a3, el indice en t0 en todas las etapas). Variantes probadas: mas de 10 (orden de declaracion, puntero propio por etapa, bucles rotados, parametro de relleno). Recorre la cabecera de secciones de un contenedor (n entradas de tipo, tamano y tamano alineado) y calcula la posicion, en bytes desde el inicio del archivo, de los datos del banco que se pide: devuelve
- `func_80041298`: Pendiente: puntuacion 1115 con la configuracion versionada (g = 8 del archivo). Mismas instrucciones y mismo flujo que el original; difiere el reparto de registros (el original deja el puntero de la lista A en v1 y el de busqueda en a1, aqui salen a2 y v1) y un nop de retardo que el original rellena. Variantes probadas: 14 (indice o puntero en el bucle de cinco, tipo del contador, temporales para el reparto, orden de declaracion). Convierte, en un contenedor ya cargado, las referencias entre registros por identificador en desplazamientos dentro de cada lista, para que el codigo que las usa no 
- `func_800415A0`: Pendiente: puntuacion 285 con la configuracion versionada (g = 8 del archivo). La estructura (bloques, bucles, llamadas, las cinco tablas de saltos) sigue el ensamblador completo y el marco de pila mide lo mismo (0x210 bytes); difieren el reparto de registros (s1 y s8 intercambiados desde el prologo), el orden de las cargas de la cabecera de secciones y el codigo de cada etiqueta, que GCC emite en otro orden. Variantes probadas: 2 (tamano del bufer de campos y de la tabla de secciones). Carga un contenedor de nivel o escena por su identificador (indice de D_8005F200) en `destino`. Lee la cabec
- `func_80044664`: Pendiente: puntuacion 13855 con la configuracion versionada (g = 0 del archivo). El original no usa marco de pila, guarda ra y s0..fp en el area de contexto que recibe en a2 y mantiene el flujo de entrada en a0, t4 y t0 durante todo el cuerpo, forma que GCC no emite. La descripcion en C sigue el algoritmo instruccion por instruccion. Variantes probadas: 1 (estado en estructura); las otras formas dependen de variables de registro, que no pueden ser los argumentos a0 a a2. Descomprime el flujo `entrada` en `salida`. El primer byte fija k (bits 0-2) y la escala de las longitudes largas (bits 3-4)
- `func_80044854`: Pendiente: puntuacion 5145 con la configuracion versionada (g = 0 del archivo). El original guarda ra en el contexto del llamador (4(s1)), devuelve el flujo en a0, t4 y t0 y avanza s0, que son registros del llamador que GCC no deja usar sin marco; no es expresable como funcion C con parametros. Variantes probadas: 2 (estado en estructura, 5145; variables de registro globales en a0, t4, t0, s0 y s1, 3955). Espera un sector completo en el anillo de lectura y deja el flujo apuntando a su primer byte. Sondea el contador de bytes disponibles (D_80069480) hasta 0xFFFF veces; si la unidad informa un 
- `main`: Pendiente: puntuacion 1025 con la configuracion versionada (g = 8 del archivo). Variantes probadas: 11. El flujo y los tipos coinciden (pausa y demostracion son s16, el contador de cuadros D_80069676 es volatile u16); difieren el reparto de registros salvados de las constantes 2 y 3 y de la tabla de tiempos D_8006CF68, y la base `lui` del estado se hoistea antes que en el original. Arranque y bucle principal. Tras iniciar el hardware y cargar el primer contenido, cada vuelta del bucle sincroniza los tres buffers, actualiza el cuadro, atiende la tarjeta de memoria, la pausa y la maquina de esta

## Menciones sin símbolo de función (datos incrustados en el código; no cuentan)

- `func_800375F8`

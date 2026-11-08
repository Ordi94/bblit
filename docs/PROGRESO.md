# Progreso de la descompilación

Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del
texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la
construcción normal) y de la tabla de símbolos.

## Resumen

| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |
|---|---:|---:|---:|---:|
| Arranque | 2 | 180 | 0 | 0 |
| Código del juego | 450 | 201416 | 390 | 78256 |
| Librerías Sony | 650 | 97488 | 0 | 0 |

Bytes de código del juego descompilados: 78256 de 201416 (38.85 %).
Funciones marcadas `NON_MATCHING`: 43.
Coherencia con el ensamblador: correcta (712 `glabel` en `asm/` + 390 en C = 1102; la tabla declara 1102).

## Por subsistema

| Subsistema | Archivos | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|---:|
| arranque_y_bucle_principal | 1 | 9 | 1 | 0 | 1364 | 3404 |
| audio_xa_y_spu | 1 | 36 | 1 | 0 | 7320 | 8220 |
| camara_y_bucle_logico | 1 | 8 | 3 | 0 | 2712 | 14576 |
| cargador_de_niveles_y_cd | 2 | 7 | 2 | 2 | 1096 | 14264 |
| colision_y_terreno | 1 | 2 | 2 | 0 | 680 | 12480 |
| entrada_de_mando | 1 | 5 | 1 | 0 | 1260 | 2784 |
| gestion_y_dibujo_de_objetos | 4 | 27 | 7 | 8 | 9024 | 18624 |
| graficos_y_gte | 3 | 17 | 2 | 0 | 5684 | 11812 |
| inicializacion_de_motor | 1 | 10 | 2 | 4 | 4152 | 5276 |
| interprete_de_eventos | 1 | 195 | 0 | 2 | 11788 | 11900 |
| logica_de_niveles | 3 | 16 | 5 | 0 | 10648 | 60648 |
| manejadores_por_tabla | 1 | 12 | 0 | 0 | 384 | 384 |
| menus_e_interfaz | 1 | 22 | 4 | 1 | 9256 | 13644 |
| movimiento_y_objetos_de_escena | 3 | 16 | 11 | 0 | 10996 | 18284 |
| tarjeta_de_memoria | 1 | 8 | 2 | 0 | 1892 | 5116 |

## Por archivo

| Archivo | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|
| `src/arranque_y_bucle_principal_2.c` | 9 | 1 | 0 | 1364 | 3404 |
| `src/audio_xa_y_spu.c` | 36 | 1 | 0 | 7320 | 8220 |
| `src/camara_y_bucle_logico.c` | 8 | 3 | 0 | 2712 | 14576 |
| `src/cargador_de_niveles_y_cd.c` | 7 | 2 | 0 | 1096 | 13592 |
| `src/cargador_de_niveles_y_cd_2.c` | 0 | 0 | 2 | 0 | 672 |
| `src/colision_y_terreno.c` | 2 | 2 | 0 | 680 | 12480 |
| `src/entrada_de_mando.c` | 5 | 1 | 0 | 1260 | 2784 |
| `src/gestion_y_dibujo_de_objetos.c` | 12 | 3 | 0 | 1696 | 3812 |
| `src/gestion_y_dibujo_de_objetos_2.c` | 9 | 3 | 8 | 4256 | 10604 |
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
| `src/menus_e_interfaz.c` | 22 | 4 | 1 | 9256 | 13644 |
| `src/movimiento_y_objetos_de_escena.c` | 3 | 1 | 0 | 1572 | 2116 |
| `src/movimiento_y_objetos_de_escena_2.c` | 10 | 5 | 0 | 3516 | 6336 |
| `src/movimiento_y_objetos_de_escena_3.c` | 3 | 5 | 0 | 5908 | 9832 |
| `src/tarjeta_de_memoria.c` | 8 | 2 | 0 | 1892 | 5116 |

## Funciones `NON_MATCHING`

- `ActualizarCamaraSeguimiento`: Pendiente: puntuacion 10175 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y las constantes coinciden; difieren el reparto de registros temporales y la planificacion de las cargas y los almacenes en las sondas de apuntado (0x80033700-0x80033888), la direccion normalizada del modo guiado (0x80033CB4-0x80033D64), el giro lateral (0x80033F00-0x80034160), los barridos contra el terreno (0x80034348-0x80034720), las ocho sondas de empuje (0x800348C8-0x80034A9C) y el bloque de alturas (0x80034B00-0x80034E34).
- `AplicarCuadro`: Pendiente: puntuacion 465 con la configuracion versionada (g = 8 del archivo). Instrucciones y flujo identicos al original; difiere el reparto de registros callee-saved: el original deja el area de trabajo en $s1 y la ayuda en $s0 y GCC los intercambia (prioridad de global-alloc por referencias y longitud de vida); el radio de la caja y las banderas de la pista de ayudante en variables propias (distintas de las banderas de pose) bajan de 510.
- `AvanzarAnimacionSprite`: Pendiente: puntuacion 160 con la configuracion versionada (g = 8 del archivo). Instrucciones y flujo identicos al original; difieren el temporal del cociente de las multiplicaciones (el original usa $t4, el C $t5: la macro de escala 0x1000 escribe $t4 y lo declara destruido porque su cuerpo lo escribe, y esa lista no se altera; sin declararlo el C da $t4 y la puntuacion baja en 50), el reparto de $v0/$v1 en la lectura de los dos contadores de 8 bits y el orden de las tres copias de escala del bloque de agarre.
- `BarrerTerreno`: Pendiente: puntuacion 2080 con la configuracion versionada (g = 0 del archivo). Difieren el orden de las escrituras del avance por subcelda y por baldosa del recorrido general (rangos 0x8001A050-0x8001A563), el reparto de v0/v1 en las banderas de los planos 0x7E y 0x7F del caso estatico (0x8001BCD4-0x8001BF6B) y la posicion de dos instrucciones del prologo.
- `CargarContenedor`: Pendiente: puntuacion 259563 con la configuracion versionada (g = 8 del archivo). La cifra depende de la composicion del objeto: la comparacion incluye palabras con direcciones absolutas dentro del archivo, y cualquier funcion cerrada en este mismo archivo las desplaza sin que cambie el codigo de esta (no comprobado comparando los objetos). La estructura (bloques, bucles, llamadas, las cinco tablas de saltos) sigue el ensamblador completo y el marco de pila mide lo mismo (0x210 bytes); difieren el reparto de registros (s1 y s8 intercambiados desde el prologo), el orden de las cargas de la cabe
- `DibujarSombras`: Pendiente: puntuacion 930 con la configuracion versionada (g = 8 del archivo). Difiere el reparto de registros del prologo, el cierre del bucle de nodos (el original conserva el salto condicional hacia atras) y la direccion de la caja de relleno, que el original deriva de la base del scratchpad.
- `LogicaBloqueEmpujable`: Pendiente: puntuacion 14728 con la configuracion versionada (g = 8 del archivo). Reparto de registros: el original guarda el objeto en s4, el scratchpad en s3, el area en s5 y el margen de la caja en s6 y deja s0 a s2 para los punteros de la preparacion; el compilador los reparte un registro mas abajo. La estructura de las ocho esquinas y de los dos modos coincide.
- `LogicaDirectorCamara`: Pendiente: puntuacion 365 con la configuracion versionada (g = 8 del archivo). Prologo y salida de la busqueda por id: el original deriva la matriz del scratchpad de la base despues de calcular la parte alta de la camara, y sale de la busqueda con un salto directo al caso sin origen en lugar de volver a probar el cursor.
- `LogicaObjetoMovil`: Pendiente: puntuacion 2925 con la configuracion versionada (g = 8 del archivo). Reparto de registros y orden de instrucciones: el original comparte entre los modos 0x10 y 0x400 la llamada a ApplyMatrixLV, calcula el divisor del balancin con otro orden de cargas y reparte el paso y el empuje en a0 y v1.
- `ResolverReferenciasContenedor`: Pendiente: puntuacion 1115 con la configuracion versionada (g = 8 del archivo). Mismas instrucciones y mismo flujo que el original; difiere el reparto de registros (el original deja el puntero de la lista A en v1 y el de busqueda en a1, aqui salen a2 y v1) y un nop de retardo que el original rellena. Convierte, en un contenedor ya cargado, las referencias entre registros por identificador en desplazamientos dentro de cada lista, para que el codigo que las usa no tenga que buscar: las cinco referencias de cada nodo de la lista A apuntan a la lista B (desplazamiento en bytes, multiplo de 0x20), 
- `SondearTarjeta`: Pendiente: puntuacion 3175 con la configuracion versionada (g = 8 del archivo). Flujo y distribucion de bloques iguales al original; quedan permutaciones de registros temporales (v0/v1, a0/a1) en el resultado de MemCardFormat, en la mascara de ranuras y en el bloque de tarjeta sin formato, el reparto de la suma de bloques por 0x2000 y, sobre todo, el segundo bucle del directorio: el original recalcula en cada uso el desplazamiento de la ranura (ranura * 120) y GCC lo iza del bucle como invariante. Sondeo por cuadro de la tarjeta de memoria. Primero atiende la orden pendiente del banco de regis
- `func_800151FC`: Pendiente: puntuacion 17285 con la configuracion versionada (g = 8 del archivo). No se reprodujo la disposicion de los bloques locales de la pila ni las copias de estructura con comprobacion de alineacion en tiempo de ejecucion; un solo intento. Da formato al archivo de partida: arma en la pila un bloque de 0x200 bytes con la cabecera de la tarjeta ("SC", bandera de icono, un bloque, titulo, paleta e imagenes), lo copia con la cabecera de D_8006D060 y su suma de control al buffer D_80069520 + 0x2000 y escribe 0x400 bytes con open/write (hasta cinco intentos), comprobando despues la lectura.
- `func_80017478`: Pendiente: puntuacion 19849 con la configuracion versionada (g = 8 del archivo). Traduccion completa sin afinar: el reparto de registros y el orden de las comparaciones de las regiones no se han ajustado al original. La lista de registros destruidos de GEO_NORMA2_XZ la mueve 100 puntos (antes 19749). Desliza el volumen de a por la velocidad v contra los objetos solidos de la lista cuyos indicadores coinciden con mascara: para cada candidato lleva los cinco puntos del barrido a su sistema local, recorta la velocidad contra la pared que cruzan y, si ninguno la cruza, usa la arista mas cercana. D
- `func_80018664`: Pendiente: puntuacion 1555 con la configuracion versionada (g = 8 del archivo). Reparto de registros del tramo final del bucle de puntos (el original carga el area de trabajo en a2 y el objeto b en a1, y aqui caen al reves) y cadena de comparaciones de las esquinas que el original comparte entre regiones. Comprueba si alguno de los cinco puntos barridos por el volumen de a, llevados al sistema local de b, cae en el cuadrante de b que indican los angulos de sus esquinas (ampliado por el radio); devuelve 1 si lo toca. En las dos ramas de cierre (la de esquina positiva y la de esquina negativa en
- `func_8001C134`: Pendiente: puntuacion 460 con la configuracion versionada (g = 0, no carga globales). Los registros guardados y la copia de la zona coinciden; difiere el orden de las dos divisiones por 320 del resto de la baldosa (el original calcula x antes que z, GCC al reves con cualquier orden del fuente) y la suma del indice de subcelda (el original suma primero base + (baldosa << 6) y despues z / 40 * 8 + x / 40). Consulta la baldosa bajo el punto pos: busca la zona del punto (con el grupo recordado en res), lee el valor de la baldosa de 320 unidades y la subcelda de 40 unidades, y rellena res con la cl
- `func_8001C998`: Pendiente: puntuacion 1292 con la configuracion versionada (g = 8 del archivo). Mismas ramas y almacenes que el ensamblador; el original reparte s0 al area de trabajo, s1 a la altura nueva, s2 al suelo anterior y s4 al tope (el C rota esos cuatro registros: area en s4, altura en s0, suelo en s1, tope en s2) y ordena los bloques de salto de otro modo. El area + 0x28 se precalcula como el original.
- `func_8001D31C`: Pendiente: puntuacion 1124 con la configuracion versionada (g = 8 del archivo). Mismas operaciones y mismo orden de almacenes; el original no conserva el puntero a la camara en un registro salvado (recalcula D_8006D928 en los dos caminos y no reserva s0) y copia el primer argumento a a3 antes de cargar D_80069698; el C mantiene la camara en s0 y reparte v1 y a0 de otro modo en el prologo. Con el simbolo de la camara escrito directo desaparece s0 y el cierre coincide, pero GCC adelanta entonces la lectura de D_8006D9A8 por encima de los almacenes de la posicion, que el original deja despues.
- `func_8001D588`: Pendiente: puntuacion 660 con la configuracion versionada (g = 8 del archivo). Mismas operaciones y almacenes; el original ejecuta los dos almacenes de bytes de D_8006965A y D_80069659 antes de leer la lista del objeto (el planificador del C los deja despues de los almacenes de la camara) y reparte el objeto controlado en a2 y su alias en v1/a1 de otra forma. Leer p->vz antes de los almacenes al objeto y compartir la variable del alias bajan de 840.
- `func_8001D75C`: Pendiente: puntuacion 8935 con la configuracion versionada (g = 8 del archivo). Misma logica de condiciones y mismos almacenes, primer borrador sin igualar el orden de bloques: el original reparte el dano por defecto (1) y el de la rama con atacante en bloques compartidos con saltos distintos y dos formas de cerrar el llamador.
- `func_8001DF28`: Pendiente: puntuacion 585 con la configuracion versionada (g = 8 del archivo). Mismo codigo GTE y mismas operaciones; solo difiere el bloque de la bandera 0x8000000: el original calcula h52 antes que h94, repite el desplazamiento `(s16)alto >> 1` en dos expresiones sin fundirlas y resta el valor de 32 bits de h94 de h4E sin releerlo, mientras que GCC funde el desplazamiento, calcula primero h94 y relee la mitad con signo de 16 bits.
- `func_8001E1A4`: Pendiente: puntuacion 200 con la configuracion versionada (g = 8 del archivo). La unica diferencia es la carga del argumento de func_8003F06C: el original usa lw y el C con la conversion (s16) usa lh; sin la conversion el bucle tiene menos instrucciones antes de la optimizacion de bucles y el compilador iza la direccion de D_8006B558 fuera de el, con lo que la puntuacion sube a 692.
- `func_8001E528`: Pendiente: puntuacion 465 con la configuracion versionada (g = 8 del archivo). Mismos accesos y almacenes; el original conserva el registro del cuadro en t0 hasta leer las banderas, que es lo ultimo que hace (y deja el indice en v0 y las coordenadas en a3, a1, a0, a2), mientras que el C debe leer paleta y banderas antes de los almacenes de coordenadas: con las banderas al final el compilador copia el desplazamiento del indice dentro de cada rama (1340 y 715) y el registro del cuadro cae en v0.
- `func_8001E600`: Pendiente: puntuacion 935 con la configuracion versionada (g = 8 del archivo). Mismos accesos y almacenes; difieren el momento de dos lecturas y el reparto de registros: el original copia el objeto a a3 al entrar, lee la tabla de fotogramas despues de la reunion de las dos ramas del cuadro y el puntero al sprite (+0x78 del objeto) tras los campos del cuadro (la altura en a3 y la anchura del bloque despues del primer almacen), mientras que GCC lee la tabla antes de la rama y el puntero justo despues del cuadro, y usa t3, t1 y a3 en otro orden.
- `func_80020240`: Pendiente: puntuacion 605 con la configuracion versionada (g = 8 del archivo). La condicion de continuar (bit 4 apagado o bit 0x10 activo) y la reunion de las dos ramas de la altura no se reproducen: el compilador adelanta la carga de las banderas y repite el almacen de h10A en cada rama.
- `func_80020A90`: Pendiente: puntuacion 2360 con la configuracion versionada (g = 8 del archivo). Misma logica y mismos accesos; el original deja los retornos 2 y 1 como bloques separados con el delay slot relleno y la lista recorrida con el indice en el hueco de salto, el C los reunifica.
- `func_80020B90`: Pendiente: puntuacion 14290 con la configuracion versionada (g = 8 del archivo). Las diferencias son de reparto de registros (v0/v1/a0 y punteros s0-s2) y del orden en que el compilador planifica los almacenamientos de las transiciones de cada contacto; la logica coincide.
- `func_80026FEC`: Pendiente: puntuacion 2815 con la configuracion versionada (g = 8 del archivo). Los registros guardados ya coinciden con el original; quedan unos 25 tramos de 1 a 6 instrucciones: orden de las cargas del contador de andadura y de las alturas del vuelo, el hueco de retardo de la llamada compartida a func_8001CFCC, la rama invertida del bucle de busqueda del objetivo y el temporal de mflo (a0 en lugar de t7), el ida y vuelta por memoria del contador 0x17c(s3) del final (sh y lhu en el original, andi 0xffff aqui) y el orden de un sw adicional a 0x14(s3).
- `func_80032B2C`: Pendiente: puntuacion 60 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y el reparto de los registros salvados coinciden; difiere la posicion de una sola instruccion: el original coloca el almacen de i58 (sw v0,0x58) tras la copia del objeto en curso (move v1,a1) y GCC lo deja antes, porque el do/while que abre las escrituras de a48 impide subir la copia por encima del almacen. Meter el almacen en ese do/while lo coloca bien pero intercambia a1 y a2 en la cadena de pruebas (60 tambien). Los tres do/while (0) no generan codigo: ponderan por un nivel mas la
- `func_800353B0`: Pendiente: puntuacion 7961 con la configuracion versionada (g = 8 del archivo). El flujo, las macros vectoriales y las constantes coinciden; difieren el reparto de registros (el original conserva el scratchpad, &sx, &z6C y la mascara -3 en s1..s4 y no hoistea &v80 ni &c104), el relleno de los huecos de retardo de la macro de distancia (maspsx anade un nop extra tras dos de sus saltos) y la forma de la busqueda en la tabla D_8006A940 (el original relee el puntero guardado en el scratchpad en cada vuelta). Reescribir en C la suma de vectores y la distancia da 9641 y 11566 (ver GEO_SUMAR_W y GEO_
- `func_80036164`: Pendiente: puntuacion 395 con la configuracion versionada (g = 8 del archivo). GCC deriva un segundo puntero inducido (p + 4) para los dos accesos de campo y devuelve el puntero base; el original usa un solo puntero con desplazamientos 0x0C y 0x04 y conserva una copia de la cuenta (move a2,v0) para la prueba del bucle. Compartir la variable del indice con la que recibe la cuenta baja de 415; el recorrido por indice sobre el arreglo, la reordenacion de los incrementos y el acceso por desplazamiento en bytes no eliminan el puntero derivado.
- `func_800363D4`: Pendiente: puntuacion 205 con la configuracion versionada (g = 8 del archivo). El original mantiene el nodo en $a0 y deriva el puntero inducido en $a1; GCC los intercambia. Las 0x2E escrituras de sw $zero,0($a2) del original son un bucle real de 0x2E vueltas (contador en $v1, sltiu/bnez, la escritura en el hueco de retardo), no una secuencia desenrollada; escritas como 0x2E sentencias explicitas el resultado empeora (895), porque GCC no las pliega a ese bucle.
- `func_80037FE8`: Pendiente: puntuacion 3403 con la configuracion versionada (g = 8 del archivo). La estructura de los seis grupos coincide, pero el original rematerializa el puntero a 0x80010000 en cada grupo salvo en los tres ultimos, donde lo conserva en un registro salvado a traves de la llamada a la conversion BCD; GCC lo trata como una sola constante y reparte los registros de otra forma.
- `func_80038884`: Pendiente: puntuacion 65 con la configuracion versionada (g = 8 del archivo). Coincide la estructura, el marco de pila y el reparto de los registros salvados (parametro en $s4, tabla de posiciones en $s3, identificadores en $s7, $s6 y $s5); difiere solo el registro de los temporales de la mitad de k en las tres ramas: el original los deja en $a2, junto con el indice que sigue, y aqui los dos primeros caen en $v0. La causa de ese reparto esta sin verificar: no se midio en el volcado de cc1 por que el asignador deja el indice y los temporales en registros distintos.
- `func_80039094`: Pendiente: puntuacion 1950 con la configuracion versionada (g = 8 del archivo). Coinciden la estructura, los desplazamientos y los simbolos; difiere en el reparto de registros (la base de 0x80010000, el indice y el valor de las barras 3 y 7 caen en registros distintos de los del original, que usa a1, v0 y a0 segun el bloque), en el orden de dos copias y tres huecos de retardo de la barra 0 y de las barras 3 y 7, y en una recarga de la parte alta de D_8006AA7C que el compilador anade en los tres ultimos temporizadores.
- `func_8003AE08`: Pendiente: puntuacion 605 con la configuracion versionada (g = 8 del archivo). Las instrucciones y el flujo coinciden; difiere la posicion de la carga de la palabra 8 de los puntos (el original la hace despues del almacen del cursor), el planificado de los desplazamientos del segundo paquete (el original adelanta el sll) y el registro destino del desplazamiento del primer paquete (v1 en el original, v0 aqui). La copia del parametro de puntos y la variable que une la copia del cursor con su relectura final bajan de 990.
- `func_8003AF8C`: Pendiente: puntuacion 1515 con la configuracion versionada (g = 8 del archivo). Mismas instrucciones y flujo; difiere el reparto de registros (el original deja el color en a3 y el desplazamiento de la textura en a2, y aqui caen en a2 y a0; la direccion de las palabras del sprite queda en v1 en lugar de a0) y la posicion de dos lecturas: el original lee la bandera de transparencia y calcula la palabra de la lista de ordenacion despues de guardar la profundidad.
- `func_8003B354`: Pendiente: puntuacion 315 con la configuracion versionada (g = 8 del archivo). Las instrucciones y el flujo coinciden; difiere el reparto de v0/v1 en las constantes previas al bucle (el original deja el uno compartido en v1, -0x80 en v0, la constante 0x10000 en v1 y el desplazado en v0; aqui van al reves) y los registros de la entrada visible del bucle (v1 en el original, a0 aqui) y de la entrada nueva.
- `func_8003B5AC`: Pendiente: puntuacion 870 con la configuracion versionada (-G0 salvo g = 8 del archivo). Misma estructura de bloques y mismo bucle de objetos; difieren el registro de la carga del desplazamiento geometrico (gte_SetGeomOffset usa t4/t5 y el original t2/t3), el reparto v0/v1 del nivel del fundido (el original relee esc->estado.w8 tras los dos almacenes y el compilador reutiliza el registro del nivel, y el almacen de D_800694E2 se coloca antes que la relectura) y el orden de dos cargas antes del bucle de objetos (el original calcula D_8006D928 antes que la tabla D_8006AD80, que aqui se usa direct
- `func_8003F06C`: Pendiente: puntuacion 175 con la configuracion versionada (g = 8 del archivo). Los dos punteros de la tabla y el orden de los incrementos de los bucles coinciden; difieren la posicion de `addiu s1,s3,4` en la entrada del bucle (el original la emite tras la de s2), la copia `move a0,v0` del contador del bucle de busqueda y el reparto de v0/v1 en el calculo del volumen replicado en los dos bytes (el original deja el nivel en v0 y el desplazado en v1).
- `func_8004048C`: Pendiente: puntuacion 7254 con la configuracion versionada (g = 8 del archivo). El marco de pila del original es 8 bytes mayor, el reparto de registros de la rama de grabacion es otro y GCC fusiona el xor de (D_8006CFF2 ^ 0xFF) << 8 con el desplazamiento. Lectura del mando por cuadro. Con la entrada bloqueada (maquina de estados no nula o entidad con el bit 24) borra el estado y sale. En reproduccion de demo (0x8001004F) toma los cuatro registros del cuadro de la grabacion; si no, convierte el bufer de la BIOS (D_8006CFF1..7: id, botones invertidos y ejes) en botones logicos y ejes de +/-0x7F.
- `func_80045150`: Pendiente: puntuacion 1501 con la configuracion versionada (g = 8 del archivo). Misma estructura de bucle y de escrituras de la primitiva; el original reparte s1 a la coordenada y y s3 a la v del glifo, s6 al contador y s7 y s8 a las dimensiones, el C los reparte al reves (el contador queda con la menor prioridad de los registros guardados), y carga el puntero a la primitiva (D_80076188) despues de la direccion de la cabeza de la lista, mientras GCC lo adelanta.
- `func_80045C4C`: Pendiente: puntuacion 115 con la configuracion versionada (g = 8 del archivo). Mismo flujo, mismas escrituras y mismo orden; el estado del lector se lee como D_8006AA70[0xC] (arreglo) para que el lui de la base pueda separarse de la carga, como en el original. Solo difiere la primera comparacion: el original la hace sobre una copia de a2 en v0 (move v0,a2 ; beqz v0) y GCC compara a2 directamente, porque el CSE sustituye cualquier copia local del parametro por el primer pseudo de su clase (copia previa, bandera entera y copia dentro de un do/while dan 115; a diferencia de un retorno estrechado 
- `main`: Pendiente: puntuacion 1025 con la configuracion versionada (g = 8 del archivo). El flujo y los tipos coinciden (pausa y demostracion son s16, el contador de cuadros D_80069676 es volatile u16); difieren el reparto de registros salvados de las constantes 2 y 3 y de la tabla de tiempos D_8006CF68, y la base `lui` del estado se hoistea antes que en el original. Arranque y bucle principal. Tras iniciar el hardware y cargar el primer contenido, cada vuelta del bucle sincroniza los tres buffers, actualiza el cuadro, atiende la tarjeta de memoria, la pausa y la maquina de estados D_80069662 (el estad

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

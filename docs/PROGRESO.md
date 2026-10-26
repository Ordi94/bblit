# Progreso de la descompilación

Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del
texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la
construcción normal) y de la tabla de símbolos.

## Resumen

| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |
|---|---:|---:|---:|---:|
| Arranque | 2 | 180 | 0 | 0 |
| Código del juego | 449 | 201416 | 25 | 3232 |
| Librerías Sony | 650 | 97488 | 0 | 0 |

Bytes de código del juego descompilados: 3232 de 201416 (1.60 %).
Funciones marcadas `NON_MATCHING`: 20.
Coherencia con el ensamblador: correcta (1076 `glabel` en `asm/` + 25 en C = 1101; la tabla declara 1101).

## Por subsistema

| Subsistema | Archivos | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|---:|
| arranque_y_bucle_principal | 1 | 0 | 0 | 10 | 0 | 3404 |
| audio_xa_y_spu | 1 | 0 | 0 | 37 | 0 | 8220 |
| camara_y_bucle_logico | 1 | 0 | 1 | 10 | 0 | 14576 |
| cargador_de_niveles_y_cd | 2 | 0 | 0 | 11 | 0 | 14264 |
| colision_y_terreno | 1 | 2 | 1 | 1 | 680 | 12480 |
| entrada_de_mando | 1 | 1 | 5 | 0 | 232 | 2784 |
| gestion_y_dibujo_de_objetos | 4 | 1 | 0 | 41 | 76 | 18624 |
| graficos_y_gte | 3 | 5 | 12 | 2 | 1484 | 11812 |
| inicializacion_de_motor | 1 | 0 | 0 | 16 | 0 | 5276 |
| interprete_de_eventos | 1 | 3 | 0 | 193 | 140 | 11900 |
| logica_de_niveles | 3 | 0 | 1 | 20 | 0 | 60648 |
| manejadores_por_tabla | 1 | 12 | 0 | 0 | 384 | 384 |
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
| `src/colision_y_terreno.c` | 2 | 1 | 1 | 680 | 12480 |
| `src/entrada_de_mando.c` | 1 | 5 | 0 | 232 | 2784 |
| `src/gestion_y_dibujo_de_objetos.c` | 1 | 0 | 14 | 76 | 3812 |
| `src/gestion_y_dibujo_de_objetos_2.c` | 0 | 0 | 20 | 0 | 10604 |
| `src/gestion_y_dibujo_de_objetos_3.c` | 0 | 0 | 1 | 0 | 564 |
| `src/gestion_y_dibujo_de_objetos_4.c` | 0 | 0 | 6 | 0 | 3644 |
| `src/graficos_y_gte.c` | 3 | 4 | 2 | 1304 | 10072 |
| `src/graficos_y_gte_10.c` | 1 | 5 | 0 | 68 | 1076 |
| `src/graficos_y_gte_12.c` | 1 | 3 | 0 | 112 | 664 |
| `src/inicializacion_de_motor.c` | 0 | 0 | 16 | 0 | 5276 |
| `src/interprete_de_eventos.c` | 3 | 0 | 193 | 140 | 11900 |
| `src/logica_de_niveles.c` | 0 | 0 | 1 | 0 | 19880 |
| `src/logica_de_niveles_2.c` | 0 | 0 | 3 | 0 | 2016 |
| `src/logica_de_niveles_3.c` | 0 | 1 | 16 | 0 | 38752 |
| `src/manejadores_por_tabla.c` | 12 | 0 | 0 | 384 | 384 |
| `src/menus_e_interfaz.c` | 0 | 0 | 27 | 0 | 13644 |
| `src/movimiento_y_objetos_de_escena.c` | 0 | 0 | 4 | 0 | 2116 |
| `src/movimiento_y_objetos_de_escena_2.c` | 1 | 0 | 14 | 236 | 6336 |
| `src/movimiento_y_objetos_de_escena_3.c` | 0 | 0 | 8 | 0 | 9832 |
| `src/tarjeta_de_memoria.c` | 0 | 0 | 10 | 0 | 5116 |

## Funciones `NON_MATCHING`

- `func_80016C0C`
- `func_80016ED0`
- `func_800171E4`
- `func_80019180`
- `func_8001C134`
- `func_8002F990`: Operacion aritmetica sobre un registro de 16 bits repartido en dos bytes (D_80010047 es el bajo y D_8001013C el alto). Diferencias con el original: este lee ambos bytes con un unico 'lui' (los dos simbolos comparten la parte alta) y conserva una copia del valor en el hueco de retardo del primer salto; el compilador genera dos 'lui' porque son variables externas distintas. Hay que declararlas como miembros de una misma estructura o arreglo.
- `func_80035244`: Lee los botones (D_80010010 sin los bits 0 y 3) y, si cambiaron, avanza siete secuencias de teclas de D_8005E768 (24 bytes cada una: caso, paso y diez teclas); al completar una ejecuta su caso con un switch de siete entradas. El archivo se compila con -G8 (config/opciones_compilacion.toml). Puntuacion 600: la tabla de saltos, los destinos de los casos, el reparto de registros del estado y la forma simbolica de D_80069662 coinciden; difieren la posicion del almacen en 0x104($gp) (el original no lo coloca en el hueco de retardo), las constantes 0x47 y 1, que el original carga antes del bucle, y 
- `func_8003FFA0`: Coincide con g = 8 (25, solo marcas i); con la configuracion actual -G0 da 955. Arranque del mando: borra el estado de vibracion y de repeticion, inicia la tarjeta de memoria y el controlador directo, y espera hasta 30 cuadros a que el mando 0 este estable (PadStateStable); si admite el modo extendido lo fija en analogico (hasta 5 intentos). Puntuacion 25 con -G8: solo cambia la forma de las direcciones 0x8001000A..0x80010010 (simbolo en el objetivo, numero en el candidato); los bytes son los del original. Con el -G0 por omision las escrituras a 0x80069xxx usan un registro general en lugar de 
- `func_800400C0`: No coincide en el diff (70 con g = 8 y con -G0), aunque los bytes son los del original (build y verify OK con este cuerpo): el objetivo usa los simbolos D_80010026..D_8001003C y D_80010051 y el candidato direcciones numericas con un lui compartido. Con un extern por dato el compilador emite un lui por simbolo (2435). Carga la configuracion de botones: fija las mascaras de las cuatro direcciones y copia a la tabla de salida los ocho valores de la configuracion elegida (16 bytes por entrada).
- `func_80040240`: No coincide: 240 con g = 8; con la configuracion actual -G0 da 3210. Vibracion del mando: mientras el mando 0 anuncia el modo extendido (PadInfoMode 1 = 7 y PadInfoMode 2 distinto de cero) descuenta los dos temporizadores de pulso (D_80069659 el pequeno, D_8006965A el grande) y fija los motores D_8006965C/D_8006965D si el estado global lo permite (bits 7 y 0 de 0x800100E7); si no, borra todo. Al reconectarse (estado 1) o mientras falte la alineacion, reenvia la vibracion con PadSetAct y PadSetActAlign. Puntuacion 240 con -G8: difiere solo el orden de las dos ultimas instrucciones antes de PadS
- `func_80040430`: Coincide con g = 8 (10, solo marcas i); con la configuracion actual -G0 da 285. Repeticion automatica de un boton: mientras esta pulsado cuenta hacia atras el contador de retardo; al llegar a cero marca el boton en D_800695EA (botones que disparan este cuadro). Soltarlo rearma el retardo en 2 cuadros. Puntuacion 10 con -G8: solo cambia la forma de la direccion 0x8001000C; con -G0 el almacen a D_800695EA no usa $at.
- `func_8004048C`: No coincide: 7419 con g = 8; con la configuracion actual -G0 da 10074. Lectura del mando por cuadro. Con la entrada bloqueada (maquina de estados no nula o entidad con el bit 24) borra el estado y sale. En reproduccion de demo (0x8001004F) toma los cuatro registros del cuadro de la grabacion; si no, convierte el bufer de la BIOS (D_8006CFF1..7: id, botones invertidos y ejes) en botones logicos y ejes de +/-0x7F. Puntuacion 7419 con -G8 (switch con goto, la formulacion mas cercana): la estructura de saltos y casi todo el cuerpo coinciden; difieren el marco de pila (el original reserva 8 bytes m
- `func_80040A80`: Depende de $gp y de g = 8: 110 con g = 8; con la configuracion actual -G0 da 210. Retorno de llamada de DrawSync: si hay un cuadro por presentar (cuenta de cuadros positiva), ya pasaron al menos dos VSync y la GPU esta libre, lanza el dibujo. Puntuacion 110 con -G8: solo difiere el acceso a la bandera D_80069338, que el original hace como lb 0x18($gp) antes de reservar el marco. Con una variable de registro $28 el compilador reserva el marco antes de cargar la bandera.
- `func_80040AF0`: Coincide con g = 8 (0); con la configuracion actual -G0 da 1600. Retorno de llamada de VSync: cuenta el cuadro y, si la comprobacion de disco no esta activa, intenta presentar el siguiente. Puntuacion 0 con -G8 (umbral de datos pequenos de este archivo); con el -G0 por omision las escrituras no usan $at.
- `func_80040B8C`: Depende de $gp y de g = 8: 220 con g = 8; con la configuracion actual -G0 da 3978. Presenta el cuadro: si la GPU esta ocupada deja la bandera de pendiente (y reinicia el grafico si lleva cuatro VSync colgada); si no, avanza el anillo de buffers y envia las tres listas de ordenacion del buffer activo. Puntuacion 220 con -G8: solo difiere el acceso a la bandera D_80069338 ($gp + 0x18, lb y sb).
- `func_80040DDC`: Depende de $gp: 110 con g = 8 y tambien con -G0. Copia de VRAM de la barra de progreso de carga si la pantalla de carga esta activa (bit 0 de 0x800694A8). Puntuacion 110 con -G8: solo difiere la lectura de 0x188($gp).
- `func_80040E30`: Depende de $gp y de g = 8: 330 con g = 8; con la configuracion actual -G0 da 590. Copia de VRAM de la barra de progreso de carga: el ancho es restante / (total / 300) (0x80069488 y 0x800694A4, datos pequenos de $gp). Puntuacion 330 con -G8: solo difieren las tres lecturas de $gp (0x188, 0x184 y 0x168).
- `func_8004443C`: No coincide: 555 con g = 8; con la configuracion actual -G0 da 1254. Reinicia el hardware grafico y muestra la pantalla de carga del archivo pedido: apaga los retornos de llamada, limpia la VRAM, carga la imagen asociada y reactiva la pantalla. Para el archivo 3 el numero de pantalla depende de D_80010065 (nivel). Puntuacion 555 con -G8: el cuerpo coincide salvo las cuatro escrituras de 0x188($gp) y el orden de la base de la tabla D_8005F200 frente al indice (el original calcula la base antes del desplazamiento).
- `func_80044588`: No coincide: 290 con g = 8; con la configuracion actual -G0 da 230. Carga la pantalla del archivo pedido sin reiniciar la pantalla. Puntuacion 290 con -G8: difieren la escritura de 0x188($gp) y que el original conserva el valor leido en dos registros (el de comparacion y el del argumento).
- `func_800445E8`: Coincide con g = 8 (0); con la configuracion actual -G0 da 110. Carga el contenedor pedido, entrega el resultado a func_80019364 y deja armados los retornos de llamada de VSync (func_80040AF0) y de audio y menus. Puntuacion 0 con -G8; con el -G0 por omision la carga de D_800694FC usa otro registro y la funcion pierde un nop.

## Menciones sin símbolo de función (datos incrustados en el código; no cuentan)

- `func_800375F8`

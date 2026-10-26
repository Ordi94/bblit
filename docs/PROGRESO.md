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
Funciones marcadas `NON_MATCHING`: 21.
Coherencia con el ensamblador: correcta (1096 `glabel` en `asm/` + 5 en C = 1101; la tabla declara 1101).

## Por subsistema

| Subsistema | Archivos | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|---:|
| arranque_y_bucle_principal | 1 | 0 | 10 | 0 | 0 | 3404 |
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
| tarjeta_de_memoria | 1 | 0 | 9 | 1 | 0 | 5116 |

## Por archivo

| Archivo | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|
| `src/arranque_y_bucle_principal_2.c` | 0 | 10 | 0 | 0 | 3404 |
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
| `src/tarjeta_de_memoria.c` | 0 | 9 | 1 | 0 | 5116 |

## Funciones `NON_MATCHING`

- `func_80014AC4`: Busca en el directorio de la ranura `ranura` la entrada cuyo nombre coincide con los 18 caracteres de D_8005E051 y devuelve su indice, o -1 si no esta. Pendiente (895): el original accede a la cuenta de entradas por $gp (0x38($gp)) y el archivo se compila con -G0; ademas el original calcula la base del nombre una sola vez antes del bucle.
- `func_80014BA0`: Lee `cantidad` bytes del archivo de partida a partir de `desplazamiento`; 1 si se leyo completo.
- `func_80014C54`: Lee y valida la cabecera del archivo de partida (hasta cinco intentos): comprueba la suma de control sobre los 0x200 bytes con la primera palabra a cero, la copia a D_8006D060 y, si el estado principal vale 0, vuelca los seis registros de nivel en el banco de registros del interprete.
- `func_80014E24`: Lee la partida del slot D_800100DF (0x180 bytes a partir de 0x400 + (slot - 1) * 0x180) al buffer D_80069520, comprueba la suma de control de los primeros 0x140 bytes (palabra en +4 a cero durante el calculo) y los copia al estado principal; hasta cinco intentos. La reserva de 0x200 bytes en la pila no se usa: el marco de pila del original la conserva.
- `func_80014EF8`: Escribe `cantidad` bytes en el archivo de partida a partir de `desplazamiento`; 1 si se escribio completo.
- `func_80014FAC`: Escribe la cabecera del archivo de partida: guarda el valor de 16 bits formado por los bytes 0x13C (alto) y 0x47 (bajo) del estado principal y el byte 0x45 en el registro del nivel que indica el byte 0xDF, recalcula la suma de control sobre el bloque de 0x200 bytes y lo graba (hasta cinco intentos).
- `func_8001515C`: Graba la partida: calcula la suma de control del estado principal (0x140 bytes con la palabra +4 a cero), actualiza la cabecera y escribe el bloque de 0x180 bytes del slot D_800100DF (hasta cinco intentos).
- `func_800151FC`: Da formato al archivo de partida: arma en la pila un bloque de 0x200 bytes con la cabecera de la tarjeta ("SC", bandera de icono, un bloque, titulo, paleta e imagenes), lo copia con la cabecera de D_8006D060 y su suma de control al buffer D_80069520 + 0x2000 y escribe 0x400 bytes con open/write (hasta cinco intentos), comprobando despues la lectura. Pendiente (17610): no se reprodujo la disposicion de los bloques locales de la pila ni las copias de estructura con comprobacion de alineacion en tiempo de ejecucion; un solo intento.
- `func_80015E94`: Espera el resultado de la tarjeta: baja la bandera 0x3C($gp) y llama a MemCardSync(1, ...). Pendiente (120): usa $gp; con -G0 el compilador coloca el almacen en el hueco de retardo de la llamada y el original lo coloca antes de cargar el modo; pendiente de soporte -G8.
- `func_80015EC0`
- `func_80015F38`
- `func_80015FC8`
- `func_80016044`
- `func_800160A8`
- `func_80016118`
- `func_800161A8`
- `func_80016218`: Actualiza un cuadro: contadores de tiempo, lectura de mandos, logica y ordenacion de primitivas. La ordenacion corre con la pila en el bloque de memoria rapida (scratchpad): la pila se guarda en 0x1F8003FC, se cambia a esa zona y se restaura al terminar. Las dos secuencias son ensamblador porque el compilador no tiene forma de mover el puntero de pila.
- `func_800163E4`
- `func_8002F990`: Operacion aritmetica sobre un registro de 16 bits repartido en dos bytes (D_80010047 es el bajo y D_8001013C el alto). Diferencias con el original: este lee ambos bytes con un unico 'lui' (los dos simbolos comparten la parte alta) y conserva una copia del valor en el hueco de retardo del primer salto; el compilador genera dos 'lui' porque son variables externas distintas. Hay que declararlas como miembros de una misma estructura o arreglo.
- `func_80035244`: Lee los botones (D_80010010 sin los bits 0 y 3) y, si cambiaron, avanza siete secuencias de teclas de D_8005E768 (24 bytes cada una: caso, paso y diez teclas); al completar una ejecuta su caso con un switch de siete entradas. El archivo se compila con -G8 (config/opciones_compilacion.toml). Puntuacion 600: la tabla de saltos, los destinos de los casos, el reparto de registros del estado y la forma simbolica de D_80069662 coinciden; difieren la posicion del almacen en 0x104($gp) (el original no lo coloca en el hueco de retardo), las constantes 0x47 y 1, que el original carga antes del bucle, y 
- `main`: Arranque y bucle principal. Tras iniciar el hardware y cargar el primer contenido, cada vuelta del bucle sincroniza los tres buffers, actualiza el cuadro, atiende la tarjeta de memoria, la pausa y la maquina de estados D_80069662 (el estado 0x16 en adelante recarga el contenido). Con el mando ocioso unos 900 cuadros entra en el ciclo de demostracion. Pendiente (1135, 11 variantes): el flujo y los tipos coinciden (pausa y demostracion son s16, el contador de cuadros D_80069676 es volatile u16); difieren el reparto de registros salvados de las constantes 2 y 3 y de la tabla de tiempos D_8006CF68

## Menciones sin símbolo de función (datos incrustados en el código; no cuentan)

- `func_800375F8`

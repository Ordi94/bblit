# Progreso de la descompilación

Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del
texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la
construcción normal) y de la tabla de símbolos.

## Resumen

| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |
|---|---:|---:|---:|---:|
| Arranque | 2 | 180 | 0 | 0 |
| Código del juego | 450 | 201416 | 237 | 20056 |
| Librerías Sony | 650 | 97488 | 0 | 0 |

Bytes de código del juego descompilados: 20056 de 201416 (9.96 %).
Funciones marcadas `NON_MATCHING`: 29.
Coherencia con el ensamblador: correcta (865 `glabel` en `asm/` + 237 en C = 1102; la tabla declara 1102).

## Por subsistema

| Subsistema | Archivos | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|---:|
| arranque_y_bucle_principal | 1 | 9 | 1 | 0 | 1364 | 3404 |
| audio_xa_y_spu | 1 | 0 | 0 | 37 | 0 | 8220 |
| camara_y_bucle_logico | 1 | 0 | 1 | 10 | 0 | 14576 |
| cargador_de_niveles_y_cd | 2 | 6 | 5 | 0 | 804 | 14264 |
| colision_y_terreno | 1 | 2 | 1 | 1 | 680 | 12480 |
| entrada_de_mando | 1 | 4 | 2 | 0 | 764 | 2784 |
| gestion_y_dibujo_de_objetos | 4 | 1 | 0 | 41 | 76 | 18624 |
| graficos_y_gte | 3 | 13 | 4 | 2 | 3888 | 11812 |
| inicializacion_de_motor | 1 | 0 | 0 | 16 | 0 | 5276 |
| interprete_de_eventos | 1 | 183 | 11 | 3 | 10232 | 11900 |
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
| `src/camara_y_bucle_logico.c` | 0 | 1 | 10 | 0 | 14576 |
| `src/cargador_de_niveles_y_cd.c` | 6 | 3 | 0 | 804 | 13592 |
| `src/cargador_de_niveles_y_cd_2.c` | 0 | 2 | 0 | 0 | 672 |
| `src/colision_y_terreno.c` | 2 | 1 | 1 | 680 | 12480 |
| `src/entrada_de_mando.c` | 4 | 2 | 0 | 764 | 2784 |
| `src/gestion_y_dibujo_de_objetos.c` | 1 | 0 | 14 | 76 | 3812 |
| `src/gestion_y_dibujo_de_objetos_2.c` | 0 | 0 | 20 | 0 | 10604 |
| `src/gestion_y_dibujo_de_objetos_3.c` | 0 | 0 | 1 | 0 | 564 |
| `src/gestion_y_dibujo_de_objetos_4.c` | 0 | 0 | 6 | 0 | 3644 |
| `src/graficos_y_gte.c` | 5 | 2 | 2 | 2576 | 10072 |
| `src/graficos_y_gte_10.c` | 6 | 0 | 0 | 1076 | 1076 |
| `src/graficos_y_gte_12.c` | 2 | 2 | 0 | 236 | 664 |
| `src/inicializacion_de_motor.c` | 0 | 0 | 16 | 0 | 5276 |
| `src/interprete_de_eventos.c` | 183 | 11 | 3 | 10232 | 11900 |
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

- `func_80014AC4`: Busca en el directorio de la ranura `ranura` la entrada cuyo nombre coincide con los 18 caracteres de D_8005E051 y devuelve su indice, o -1 si no esta. Pendiente (895): el original accede a la cuenta de entradas por $gp (0x38($gp)) y el archivo se compila con -G0; ademas el original calcula la base del nombre una sola vez antes del bucle. NON_MATCHING: usa $gp; pendiente de soporte -G8. Puntuacion 895 con la configuracion versionada (-G0) y 895 con g = 8.
- `func_800151FC`: Da formato al archivo de partida: arma en la pila un bloque de 0x200 bytes con la cabecera de la tarjeta ("SC", bandera de icono, un bloque, titulo, paleta e imagenes), lo copia con la cabecera de D_8006D060 y su suma de control al buffer D_80069520 + 0x2000 y escribe 0x400 bytes con open/write (hasta cinco intentos), comprobando despues la lectura. Pendiente (17610): no se reprodujo la disposicion de los bloques locales de la pila ni las copias de estructura con comprobacion de alineacion en tiempo de ejecucion; un solo intento.
- `func_80015E94`: Espera el resultado de la tarjeta: baja la bandera 0x3C($gp) y llama a MemCardSync(1, ...). Pendiente (120): usa $gp; con -G0 el compilador coloca el almacen en el hueco de retardo de la llamada y el original lo coloca antes de cargar el modo; pendiente de soporte -G8. NON_MATCHING: usa $gp; pendiente de soporte -G8. Puntuacion 120 con la configuracion versionada (-G0) y 120 con g = 8.
- `func_80016C0C`
- `func_800171E4`
- `func_8001C134`
- `func_8002F990`: Operacion aritmetica sobre un registro de 16 bits repartido en dos bytes (D_80010047 es el bajo y D_8001013C el alto). Diferencias con el original: este lee ambos bytes con un unico 'lui' (los dos simbolos comparten la parte alta) y conserva una copia del valor en el hueco de retardo del primer salto; el compilador genera dos 'lui' porque son variables externas distintas. Hay que declararlas como miembros de una misma estructura o arreglo.
- `func_8002FF38`
- `func_800313D4`
- `func_8003147C`
- `func_80031650`
- `func_80031A0C`
- `func_80031AE4`
- `func_80031B1C`
- `func_80031CD4`
- `func_80031E24`
- `func_800324A4`
- `func_80032708`
- `func_80035244`: Lee los botones (D_80010010 sin los bits 0 y 3) y, si cambiaron, avanza siete secuencias de teclas de D_8005E768 (24 bytes cada una: caso, paso y diez teclas); al completar una ejecuta su caso con un switch de siete entradas. El archivo se compila con -G8 (config/opciones_compilacion.toml). Puntuacion 600: la tabla de saltos, los destinos de los casos, el reparto de registros del estado y la forma simbolica de D_80069662 coinciden; difieren la posicion del almacen en 0x104($gp) (el original no lo coloca en el hueco de retardo), las constantes 0x47 y 1, que el original carga antes del bucle, y 
- `func_80040240`: No coincide: puntuacion 240 (el archivo se compila con g = 8; 3210 con -G0). Vibracion del mando: mientras el mando 0 anuncia el modo extendido (PadInfoMode 1 = 7 y PadInfoMode 2 distinto de cero) descuenta los dos temporizadores de pulso (D_80069659 el pequeno, D_8006965A el grande) y fija los motores D_8006965C/D_8006965D si el estado global lo permite (bits 7 y 0 de 0x800100E7); si no, borra todo. Al reconectarse (estado 1) o mientras falte la alineacion, reenvia la vibracion con PadSetAct y PadSetActAlign. Puntuacion 240 con -G8: difiere solo el orden de las dos ultimas instrucciones antes
- `func_8004048C`: No coincide: puntuacion 7264 (el archivo se compila con g = 8). Lectura del mando por cuadro. Con la entrada bloqueada (maquina de estados no nula o entidad con el bit 24) borra el estado y sale. En reproduccion de demo (0x8001004F) toma los cuatro registros del cuadro de la grabacion; si no, convierte el bufer de la BIOS (D_8006CFF1..7: id, botones invertidos y ejes) en botones logicos y ejes de +/-0x7F. Puntuacion 7264 con -G8 (switch con goto, la formulacion mas cercana): la estructura de saltos y casi todo el cuerpo coinciden; difieren el marco de pila (el original reserva 8 bytes mas, 0x2
- `func_80040F78`: Pendiente: puntuacion 390 con la configuracion versionada (g = 8 del archivo). Mismas instrucciones que el original; solo difiere el reparto de registros de la ultima etapa (el original deja el puntero del bucle en a2 y la constante 4 en a3, el indice en t0 en todas las etapas). Variantes probadas: mas de 10 (orden de declaracion, puntero propio por etapa, bucles rotados, parametro de relleno). Recorre la cabecera de secciones de un contenedor (n entradas de tipo, tamano y tamano alineado) y calcula la posicion, en bytes desde el inicio del archivo, de los datos del banco que se pide: devuelve
- `func_80041298`: Pendiente: puntuacion 1115 con la configuracion versionada (g = 8 del archivo). Mismas instrucciones y mismo flujo que el original; difiere el reparto de registros (el original deja el puntero de la lista A en v1 y el de busqueda en a1, aqui salen a2 y v1) y un nop de retardo que el original rellena. Variantes probadas: 14 (indice o puntero en el bucle de cinco, tipo del contador, temporales para el reparto, orden de declaracion). Convierte, en un contenedor ya cargado, las referencias entre registros por identificador en desplazamientos dentro de cada lista, para que el codigo que las usa no 
- `func_800415A0`: Pendiente: puntuacion 285 con la configuracion versionada (g = 8 del archivo). La estructura (bloques, bucles, llamadas, las cinco tablas de saltos) sigue el ensamblador completo y el marco de pila mide lo mismo (0x210 bytes); difieren el reparto de registros (s1 y s8 intercambiados desde el prologo), el orden de las cargas de la cabecera de secciones y el codigo de cada etiqueta, que GCC emite en otro orden. Variantes probadas: 2 (tamano del bufer de campos y de la tabla de secciones). Carga un contenedor de nivel o escena por su identificador (indice de D_8005F200) en `destino`. Lee la cabec
- `func_8004443C`: No coincide: puntuacion 240 (el archivo se compila con g = 8 y define D_800694A8; era 555 con la variable declarada extern y 1254 con -G0). Reinicia el hardware grafico y muestra la pantalla de carga del archivo pedido: apaga los retornos de llamada, limpia la VRAM, carga la imagen asociada y reactiva la pantalla. Para el archivo 3 el numero de pantalla depende de D_80010065 (nivel). Puntuacion 555 con -G8: el cuerpo coincide salvo las cuatro escrituras de 0x188($gp) y el orden de la base de la tabla D_8005F200 frente al indice (el original calcula la base antes del desplazamiento).
- `func_80044588`: No coincide: puntuacion 175 (el archivo se compila con g = 8 y define D_800694A8; era 290 con la variable declarada extern). Carga la pantalla del archivo pedido sin reiniciar la pantalla. Puntuacion 290 con -G8: difiere que el original conserva el valor leido en dos registros (el de comparacion y el del argumento).
- `func_80044664`: Pendiente: puntuacion 13855 con la configuracion versionada (g = 0 del archivo). El original no usa marco de pila, guarda ra y s0..fp en el area de contexto que recibe en a2 y mantiene el flujo de entrada en a0, t4 y t0 durante todo el cuerpo, forma que GCC no emite. La descripcion en C sigue el algoritmo instruccion por instruccion. Variantes probadas: 1 (estado en estructura); las otras formas dependen de variables de registro, que no pueden ser los argumentos a0 a a2. Descomprime el flujo `entrada` en `salida`. El primer byte fija k (bits 0-2) y la escala de las longitudes largas (bits 3-4)
- `func_80044854`: Pendiente: puntuacion 5145 con la configuracion versionada (g = 0 del archivo). El original guarda ra en el contexto del llamador (4(s1)), devuelve el flujo en a0, t4 y t0 y avanza s0, que son registros del llamador que GCC no deja usar sin marco; no es expresable como funcion C con parametros. Variantes probadas: 2 (estado en estructura, 5145; variables de registro globales en a0, t4, t0, s0 y s1, 3955). Espera un sector completo en el anillo de lectura y deja el flujo apuntando a su primer byte. Sondea el contador de bytes disponibles (D_80069480) hasta 0xFFFF veces; si la unidad informa un 
- `main`: Arranque y bucle principal. Tras iniciar el hardware y cargar el primer contenido, cada vuelta del bucle sincroniza los tres buffers, actualiza el cuadro, atiende la tarjeta de memoria, la pausa y la maquina de estados D_80069662 (el estado 0x16 en adelante recarga el contenido). Con el mando ocioso unos 900 cuadros entra en el ciclo de demostracion. Pendiente (1025, 11 variantes): el flujo y los tipos coinciden (pausa y demostracion son s16, el contador de cuadros D_80069676 es volatile u16); difieren el reparto de registros salvados de las constantes 2 y 3 y de la tabla de tiempos D_8006CF68

## Menciones sin símbolo de función (datos incrustados en el código; no cuentan)

- `func_800375F8`

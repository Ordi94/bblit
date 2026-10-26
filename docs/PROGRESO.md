# Progreso de la descompilación

Generado por `python tools/build.py progreso`; no se edita a mano. Los conteos salen del
texto de `src/*.c` (una función cuenta como descompilada solo si está definida en C en la
construcción normal) y de la tabla de símbolos.

## Resumen

| Zona | Funciones | Bytes | En C (funciones) | En C (bytes) |
|---|---:|---:|---:|---:|
| Arranque | 2 | 180 | 0 | 0 |
| Código del juego | 450 | 201416 | 244 | 21444 |
| Librerías Sony | 650 | 97488 | 0 | 0 |

Bytes de código del juego descompilados: 21444 de 201416 (10.65 %).
Funciones marcadas `NON_MATCHING`: 48.
Coherencia con el ensamblador: correcta (858 `glabel` en `asm/` + 244 en C = 1102; la tabla declara 1102).

## Por subsistema

| Subsistema | Archivos | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|---:|
| arranque_y_bucle_principal | 1 | 9 | 1 | 0 | 1364 | 3404 |
| audio_xa_y_spu | 1 | 0 | 0 | 37 | 0 | 8220 |
| camara_y_bucle_logico | 1 | 0 | 1 | 10 | 0 | 14576 |
| cargador_de_niveles_y_cd | 2 | 0 | 0 | 11 | 0 | 14264 |
| colision_y_terreno | 1 | 2 | 1 | 1 | 680 | 12480 |
| entrada_de_mando | 1 | 4 | 2 | 0 | 764 | 2784 |
| gestion_y_dibujo_de_objetos | 4 | 1 | 0 | 41 | 76 | 18624 |
| graficos_y_gte | 3 | 13 | 4 | 2 | 3888 | 11812 |
| inicializacion_de_motor | 1 | 6 | 8 | 2 | 1028 | 5276 |
| interprete_de_eventos | 1 | 183 | 11 | 3 | 10232 | 11900 |
| logica_de_niveles | 3 | 0 | 1 | 20 | 0 | 60648 |
| manejadores_por_tabla | 1 | 12 | 0 | 0 | 384 | 384 |
| menus_e_interfaz | 1 | 0 | 0 | 27 | 0 | 13644 |
| movimiento_y_objetos_de_escena | 3 | 8 | 16 | 3 | 1400 | 18284 |
| tarjeta_de_memoria | 1 | 6 | 3 | 1 | 1628 | 5116 |

## Por archivo

| Archivo | En C | `NON_MATCHING` | En ensamblador | Bytes en C | Bytes totales |
|---|---:|---:|---:|---:|---:|
| `src/arranque_y_bucle_principal_2.c` | 9 | 1 | 0 | 1364 | 3404 |
| `src/audio_xa_y_spu.c` | 0 | 0 | 37 | 0 | 8220 |
| `src/camara_y_bucle_logico.c` | 0 | 1 | 10 | 0 | 14576 |
| `src/cargador_de_niveles_y_cd.c` | 0 | 0 | 9 | 0 | 13592 |
| `src/cargador_de_niveles_y_cd_2.c` | 0 | 0 | 2 | 0 | 672 |
| `src/colision_y_terreno.c` | 2 | 1 | 1 | 680 | 12480 |
| `src/entrada_de_mando.c` | 4 | 2 | 0 | 764 | 2784 |
| `src/gestion_y_dibujo_de_objetos.c` | 1 | 0 | 14 | 76 | 3812 |
| `src/gestion_y_dibujo_de_objetos_2.c` | 0 | 0 | 20 | 0 | 10604 |
| `src/gestion_y_dibujo_de_objetos_3.c` | 0 | 0 | 1 | 0 | 564 |
| `src/gestion_y_dibujo_de_objetos_4.c` | 0 | 0 | 6 | 0 | 3644 |
| `src/graficos_y_gte.c` | 5 | 2 | 2 | 2576 | 10072 |
| `src/graficos_y_gte_10.c` | 6 | 0 | 0 | 1076 | 1076 |
| `src/graficos_y_gte_12.c` | 2 | 2 | 0 | 236 | 664 |
| `src/inicializacion_de_motor.c` | 6 | 8 | 2 | 1028 | 5276 |
| `src/interprete_de_eventos.c` | 183 | 11 | 3 | 10232 | 11900 |
| `src/logica_de_niveles.c` | 0 | 0 | 1 | 0 | 19880 |
| `src/logica_de_niveles_2.c` | 0 | 0 | 3 | 0 | 2016 |
| `src/logica_de_niveles_3.c` | 0 | 1 | 16 | 0 | 38752 |
| `src/manejadores_por_tabla.c` | 12 | 0 | 0 | 384 | 384 |
| `src/menus_e_interfaz.c` | 0 | 0 | 27 | 0 | 13644 |
| `src/movimiento_y_objetos_de_escena.c` | 1 | 3 | 0 | 176 | 2116 |
| `src/movimiento_y_objetos_de_escena_2.c` | 6 | 9 | 0 | 1176 | 6336 |
| `src/movimiento_y_objetos_de_escena_3.c` | 1 | 4 | 3 | 48 | 9832 |
| `src/tarjeta_de_memoria.c` | 6 | 3 | 1 | 1628 | 5116 |

## Funciones `NON_MATCHING`

- `func_80014AC4`: Busca en el directorio de la ranura `ranura` la entrada cuyo nombre coincide con los 18 caracteres de D_8005E051 y devuelve su indice, o -1 si no esta. Pendiente (895): el original accede a la cuenta de entradas por $gp (0x38($gp)) y el archivo se compila con -G0; ademas el original calcula la base del nombre una sola vez antes del bucle. NON_MATCHING: usa $gp; pendiente de soporte -G8. Puntuacion 895 con la configuracion versionada (-G0) y 895 con g = 8.
- `func_800151FC`: Da formato al archivo de partida: arma en la pila un bloque de 0x200 bytes con la cabecera de la tarjeta ("SC", bandera de icono, un bloque, titulo, paleta e imagenes), lo copia con la cabecera de D_8006D060 y su suma de control al buffer D_80069520 + 0x2000 y escribe 0x400 bytes con open/write (hasta cinco intentos), comprobando despues la lectura. Pendiente (17610): no se reprodujo la disposicion de los bloques locales de la pila ni las copias de estructura con comprobacion de alineacion en tiempo de ejecucion; un solo intento.
- `func_80015E94`: Espera el resultado de la tarjeta: baja la bandera 0x3C($gp) y llama a MemCardSync(1, ...). Pendiente (120): usa $gp; con -G0 el compilador coloca el almacen en el hueco de retardo de la llamada y el original lo coloca antes de cargar el modo; pendiente de soporte -G8. NON_MATCHING: usa $gp; pendiente de soporte -G8. Puntuacion 120 con la configuracion versionada (-G0) y 120 con g = 8.
- `func_80016C0C`
- `func_800171E4`
- `func_8001C134`
- `func_8001C424`: Pendiente: puntuacion 1135 con la configuracion versionada (-G0). Misma estructura de ramas y mismos almacenes; en el bloque de despegue el original conserva dos copias de las banderas (move v1,v0) y ordena los almacenes de h108 y w10E de otro modo. Variantes probadas: 14.
- `func_8001C6CC`: Pendiente: puntuacion 498 con la configuracion versionada (-G0). Misma secuencia de llamadas y almacenes; el original reparte s1 al objeto y s0 al area de trabajo y ordena un almacen de d->z antes de la lectura de w->h18, el C los asigna al reves. Variantes probadas: 7.
- `func_8001C998`: Pendiente: puntuacion 3636 con la configuracion versionada (-G0). Mismas ramas y almacenes que el ensamblador; el original reparte s0 al area de trabajo, s1 a la altura nueva y s2 al suelo anterior, y precalcula area + 0x28 al principio, el C asigna los registros en otro orden y cambia el reparto de los saltos. Variantes probadas: 2.
- `func_8001CC68`: Pendiente: puntuacion 40 con la configuracion versionada (g = 8 del archivo). Mismas escrituras y orden; en la suma de la posicion con el vector rotado el original carga el operando de la posicion en v0 y el del vector en a0, el C los carga al reves. Variantes probadas: 9.
- `func_8001D028`: Pendiente: puntuacion 300 con la configuracion versionada (g = 8 del archivo). Mismas operaciones y mismo orden de almacenes; el original copia el tercer argumento a a3 al principio y lo reutiliza como cuarto argumento de la llamada, el C lo copia despues. Variantes probadas: 9.
- `func_8001D0FC`: Pendiente: puntuacion 670 con la configuracion versionada (g = 8 del archivo). Mismas busquedas y almacenes; el original conserva el argumento b en a3 y deriva b + 0x10 en s1 desde el principio, el C usa b en s1 y calcula b + 0x10 al final. Variantes probadas: 4.
- `func_8001D31C`: Pendiente: puntuacion 1764 con la configuracion versionada (g = 8 del archivo). Mismas operaciones y mismo orden de almacenes; el original no conserva el puntero a la camara en un registro salvado y recalcula D_8006D928 en los dos caminos, el C lo mantiene en s0. Variantes probadas: 4.
- `func_8001D588`: Pendiente: puntuacion 840 con la configuracion versionada (g = 8 del archivo). Mismas operaciones y almacenes; el original ejecuta los dos almacenes de bytes de D_8006965A y D_80069659 antes de leer la lista del objeto, el planificador del C adelanta la lectura de p70. Variantes probadas: 3.
- `func_8001D75C`: Pendiente: puntuacion 8935 con la configuracion versionada (g = 8 del archivo). Misma logica de condiciones y mismos almacenes, primer borrador sin igualar el orden de bloques: el original reparte el dano por defecto (1) y el de la rama con atacante en bloques compartidos con saltos distintos y dos formas de cerrar el llamador. Variantes probadas: 1.
- `func_8001DA14`: Pendiente: puntuacion 590 con la configuracion versionada (g = 8 del archivo). Mismo bucle de prueba de rumbos y mismas llamadas GTE; el original asigna s4 al area de consulta, s7 al vector rotado y s6 al resultado de baldosa, el C reparte esos tres punteros y el modo centrado de otro modo, y calcula la mascara ~6 en un registro. Variantes probadas: 7.
- `func_8001DF28`: Pendiente: puntuacion 3500 con la configuracion versionada (g = 8 del archivo). Mismo codigo GTE (matriz de rotacion, vector de traslacion, rtps) y mismas operaciones; el original conserva el segundo argumento en a1 y copia solo el objeto a a2, y usa a3 como base de la matriz, el C copia ambos y usa t2. Variantes probadas: 8.
- `func_8001E1A4`: Pendiente: puntuacion 200 con la configuracion versionada (g = 8 del archivo). La unica diferencia es la carga del argumento de func_8003F06C: el original usa lw y el C con la conversion (s16) usa lh; sin la conversion el compilador iza la direccion de D_8006B558 fuera del bucle y la puntuacion sube a 692. Variantes probadas: 6.
- `func_8001E528`: Pendiente: puntuacion 1535 con la configuracion versionada (-G0). Mismos accesos y mismos almacenes; el original funde el desplazamiento de 16 bytes del registro tras la reunion de las dos ramas y reparte a0..a3 y t0 a las cuatro lecturas del registro, el C duplica el desplazamiento en cada rama y usa v0 y t0. Variantes probadas: 8.
- `func_8001E600`: Pendiente: puntuacion 2665 con la configuracion versionada (-G0). Mismos accesos y almacenes; el original calcula el desplazamiento de color en t2 y deja el puntero al sprite en v1, el C reparte otros registros y reordena las lecturas del registro del cuadro. Variantes probadas: 3.
- `func_80020240`: Pendiente: puntuacion 605 con la configuracion versionada (-G0). La condicion de continuar (bit 4 apagado o bit 0x10 activo) y la reunion de las dos ramas de la altura no se reproducen: el compilador adelanta la carga de las banderas y repite el almacen de h10A en cada rama. Variantes probadas: 10.
- `func_80020A90`: Pendiente: puntuacion 2360 con la configuracion versionada (-G0). Misma logica y mismos accesos; el original deja los retornos 2 y 1 como bloques separados con el delay slot relleno y la lista recorrida con el indice en el hueco de salto, el C los reunifica. Variantes probadas: 4.
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
- `func_8004443C`: No coincide: puntuacion 240 (el archivo se compila con g = 8 y define D_800694A8; era 555 con la variable declarada extern y 1254 con -G0). Reinicia el hardware grafico y muestra la pantalla de carga del archivo pedido: apaga los retornos de llamada, limpia la VRAM, carga la imagen asociada y reactiva la pantalla. Para el archivo 3 el numero de pantalla depende de D_80010065 (nivel). Puntuacion 555 con -G8: el cuerpo coincide salvo las cuatro escrituras de 0x188($gp) y el orden de la base de la tabla D_8005F200 frente al indice (el original calcula la base antes del desplazamiento).
- `func_80044588`: No coincide: puntuacion 175 (el archivo se compila con g = 8 y define D_800694A8; era 290 con la variable declarada extern). Carga la pantalla del archivo pedido sin reiniciar la pantalla. Puntuacion 290 con -G8: difiere que el original conserva el valor leido en dos registros (el de comparacion y el del argumento).
- `func_80044940`: Pendiente: puntuacion 1460 con la configuracion versionada (g = 8 del archivo). Ensamblador manuscrito: neg y add con trampa de desbordamiento, registros fijos t0 a t2 y el temporal at en slt; GCC emite negu, addu y otro reparto de registros. Variantes probadas: 3.
- `func_800449B0`: Pendiente: puntuacion 960 con la configuracion versionada (g = 8 del archivo). Ensamblador manuscrito: registros fijos t0 y t1, nop explicito tras cada lw y el simbolo de la funcion vecina cargado con lui + lw; GCC reparte v0, v1 y a0. Variantes probadas: 2.
- `func_800449E0`: Pendiente: puntuacion 210 con la configuracion versionada (g = 8 del archivo). Solo difieren dos instrucciones muertas del original (ori a1,zero,0x200 y ori a2,zero,0x1FF antes de la etiqueta de entrada func_800449E8) que GCC elimina. Variantes probadas: 2.
- `func_80044A04`: Pendiente: puntuacion 415 con la configuracion versionada (g = 8 del archivo). Mismas escrituras y mismo orden; el original coloca lui a0 de la primera llamada despues de la lectura de D_800695A6 y la planificacion del compilador la adelanta. Variantes probadas: 6.
- `func_80044EA8`: Pendiente: puntuacion 355 con la configuracion versionada (g = 8 del archivo). Misma estructura que el original; difiere la planificacion de la carga de la direccion de D_8006D018 (lui) y de la mascara andi 0xFFFF. Variantes probadas: 9.
- `func_80045150`: Pendiente: puntuacion 3641 con la configuracion versionada (g = 8 del archivo). Misma estructura de bucle y de escrituras de la primitiva; el original reparte s6 al contador y s7 y fp a las dimensiones del glifo, el C los reparte al reves y desplaza el resto de la planificacion. Variantes probadas: 8.
- `func_800453D0`: Pendiente: puntuacion 230 con la configuracion versionada (g = 8 del archivo). El bucle de digitos incrementa el indice antes de leer en el original (li a1 frente a addiu a1,a1,1 y desplazamiento 0 frente a -1). Variantes probadas: 16.
- `func_80045C4C`: Pendiente: puntuacion 175 con la configuracion versionada (g = 8 del archivo). Mismo flujo y mismas escrituras; el original conserva una copia de a2 en v0 para la primera comparacion y emite el sh de +0x26 despues de la carga del byte de D_8006AA7C. Variantes probadas: 12.
- `main`: Arranque y bucle principal. Tras iniciar el hardware y cargar el primer contenido, cada vuelta del bucle sincroniza los tres buffers, actualiza el cuadro, atiende la tarjeta de memoria, la pausa y la maquina de estados D_80069662 (el estado 0x16 en adelante recarga el contenido). Con el mando ocioso unos 900 cuadros entra en el ciclo de demostracion. Pendiente (1025, 11 variantes): el flujo y los tipos coinciden (pausa y demostracion son s16, el contador de cuadros D_80069676 es volatile u16); difieren el reparto de registros salvados de las constantes 2 y 3 y de la tabla de tiempos D_8006CF68

## Menciones sin símbolo de función (datos incrustados en el código; no cuentan)

- `func_800375F8`

# Subsistemas del juego

Propuesta de reparto del codigo propio del juego (`0x80014A00..0x80045DA0`, 258 funciones con las dos
de arranque) en 15 subsistemas, con la evidencia que la respalda. Es un insumo para repartir la
descompilacion: los limites son hipotesis medibles, no hechos, y los nombres describen lo que el
codigo hace segun las llamadas a librerias, las cadenas, los datos y los borradores en C. Se
regenera con los comandos de la seccion final.

## Metodo y cifras

**Nota sobre las cifras de funciones.** Cada numero cuenta una cosa distinta:

- **1102** simbolos de funcion en el ejecutable (`config/symbols.txt`): 650 estan en la zona de librerias de
  Sony (`0x80045DA0..0x8005DEA0`), 2 son de arranque y 450 son codigo del juego. Eran 908 al hacer este analisis
  (256 en el rango del juego); la tabla actual separa 194 rutinas que se llaman solo por tablas de punteros
  (908 - 1 + 194 = 1101) y, con la regla del retorno intermedio, una mas (1102; ver `docs/GHIDRA.md`).
  `config/simbolos_adicionales.txt` ya no existe.
- **450** simbolos en el rango de codigo del juego `0x80014AC4..0x80045DA0`; es la cifra que usa `docs/PROGRESO.md`,
  que es la fuente de las cifras actuales por subsistema. Las 194 rutinas nuevas caen en `interprete_de_eventos`
  (196 funciones con las dos de 0x38 bytes) y la fusion de `func_800415A0` con `func_80042BB8` deja
  `cargador_de_niveles_y_cd` en 11. Las demas filas no cambian; las secciones de detalle de mas abajo conservan
  los conteos de la tabla de 908 simbolos con la que se calcularon.
- **282** funciones "del juego" segun las firmas de Ghidra (`es_libreria` en 0 en `funciones.csv`); 23 de ellas
  caen en la zona de librerias, y por eso no coincide con 256.
- **309** rutinas en el ambito de los borradores en C (`m2c`): las 256 del rango, las 52 de la zona de librerias
  que ninguna firma reconoce y la entrada `func_80014A08`. Los analisis de grafo y subsistemas se calcularon con
  la tabla anterior de 908 simbolos, de modo que ven 258 funciones del juego con `__main` y `start`.

- Desensamblado: copia propia con `splat` en una carpeta de trabajo (no se usa `asm/` del repositorio,
  cuya forma cambia con la particion). 908 funciones, las de la tabla de entonces (hoy `config/symbols.txt` tiene 1102).
- Grafo de llamadas (`python -m tools.ghidra grafo`): 1596 aristas con destino conocido y 2631
  sitios de llamada. `jal` 1532, `j` 32, por tabla 32, llamadas indirectas 184 instrucciones (en 139
  funciones). Del codigo del juego: 525 hacia el juego, 309 hacia librerias de Sony, 8 hacia la RAM
  previa al segmento (rutinas cargadas en ejecucion). 10 `jr` son `switch` de 7 funciones. Se toma el
  puntero de otra funcion (callbacks) 86 veces.
- Comprobacion cruzada: el numero de llamadores de cada funcion del juego coincide con el de Ghidra en
  262 de 262 casos (Ghidra cuenta los sitios `jal`/`j`). De 1095 datos referenciados, 620 tienen
  exactamente las mismas funciones que `xrefs_datos.csv`, 85 un subconjunto y 213 difieren (Ghidra
  propaga constantes a traves de registros base; el grafo solo ve direcciones simbolicas).
- Un `jr` a registro es un `switch` si la funcion lee una tabla con destinos dentro de si misma; si no,
  es una llamada indirecta. Las tablas de punteros a codigo estan en `0x8005E35C..0x8005E6F8` (231
  palabras, mezcla de `switch` y de punteros a funcion) y en `0x80067E64..0x800683B8`.
- Los cortes entre subsistemas coinciden con los 13 cortes que ningun enlace cruza en una ventana de
  12 funciones (ver `docs/ARCHIVOS_ORIGEN.md`) en `0x80026118`, `0x80037048`, `0x800399C8`,
  `0x80039BFC`, `0x8003AA38`, `0x8003DF84`, `0x8003FFA0` y `0x80040A80`; el resto sale de la familia de
  librerias dominante y de la lectura de los borradores.

## Resumen

| Subsistema | Rangos | Funciones | Bytes | Librerias de Sony principales |
|---|---|---|---|---|
| arranque_y_bucle_principal | `0x80014A00..0x80014AC4`, `0x80015EC0..0x80016C0C` | 12 | 3584 | VSync, DrawSync, DrawSyncCallback, GsClearOt |
| tarjeta_de_memoria | `0x80014AC4..0x80015EC0` | 10 | 5116 | close, open, MemCardSync, VSync |
| graficos_y_gte | `0x80016C0C..0x80019364`, `0x80040A80..0x80040EB4`, `0x800443CC..0x80044664` | 19 | 11812 | ApplyMatrixSV, RotMatrixZYX, DrawSync, DrawSyncCallback |
| colision_y_terreno | `0x80019364..0x8001C424` | 4 | 12480 | SquareRoot0 |
| movimiento_y_objetos_de_escena | `0x8001C424..0x80020B90` | 27 | 18284 | RotMatrix, ApplyMatrix, ScaleMatrix, func_8004FADC |
| logica_de_niveles | `0x80020B90..0x80026118`, `0x80026298..0x8002F9F8` | 21 | 60648 | SquareRoot0, ApplyMatrixSV, RotMatrix, RotMatrixY |
| manejadores_por_tabla | `0x80026118..0x80026298` | 12 | 384 | ninguna |
| interprete_de_eventos | `0x8002F9F8..0x80032874` | 196 (2 al calcular el analisis) | 11900 | ratan2 |
| camara_y_bucle_logico | `0x80032874..0x80036164` | 11 | 14576 | RotMatrix, ratan2, RotMatrixY, RotMatrixZYX |
| gestion_y_dibujo_de_objetos | `0x80036164..0x8003AA38` | 42 | 18624 | RotMatrix, RotMatrixY, RotMatrixZ, ScaleMatrix |
| menus_e_interfaz | `0x8003AA38..0x8003DF84` | 27 | 13644 | ApplyMatrixLV, GsGetLw, GsSortBoxFill, SquareRoot0 |
| audio_xa_y_spu | `0x8003DF84..0x8003FFA0` | 37 | 8220 | CdControlB, CdPosToInt, CdIntToPos, CdReadyCallback |
| entrada_de_mando | `0x8003FFA0..0x80040A80` | 6 | 2784 | PadGetState, PadInfoMode, MemCardStart, PadInitDirect |
| cargador_de_niveles_y_cd | `0x80040EB4..0x800443CC`, `0x80044664..0x80044904` | 11 (12 al calcular el analisis) | 14264 | CdControl, CdIntToPos, CdPosToInt, CdReadyCallback |
| inicializacion_de_motor | `0x80044904..0x80045DA0` | 16 | 5276 | CdDataCallback, CdInit, CdReadCallback, CdReadyCallback |

## Subsistemas

### 1. Arranque y bucle principal (`arranque_y_bucle_principal`)

El codigo de arranque del SDK (`__main`, `func_80014A08`: limpia el bss, fija `$gp`, `InitHeap`, llama a `main`) y, tras el bloque de la tarjeta de memoria, las rutinas de preparacion de pantalla, la actualizacion de cuadro `func_80016218` y `main`. `main` es la raiz del grafo: llama a 32 funciones de 10 subsistemas y casi nadie la llama a ella.

- **Rangos:** `0x80014A00..0x80014AC4`, `0x80015EC0..0x80016C0C`
- **Funciones (12, 3584 bytes):** `80014A00` __main, `80014A08` func_80014A08, `80015EC0` func_80015EC0, `80015F38` func_80015F38, `80015FC8` func_80015FC8, `80016044` func_80016044, `800160A8` func_800160A8, `80016118` func_80016118, `800161A8` func_800161A8, `80016218` func_80016218, `800163E4` func_800163E4, `80016414` main
- **Librerias de Sony (llamadas):** VSync (3), DrawSync (1), DrawSyncCallback (1), GsClearOt (1), GsSetRefView2L (1), InitHeap (1), MoveImage (1), PutDispEnv (1), SetDefDispEnv (1), SetDispMask (1), SetRCnt (1), StartRCnt (1), VSyncCallback (1), srand (1)
- **Cadenas que lo delatan:** ninguna referenciada directamente
- **Datos que toca (direcciones distintas por region):** bss 40, cadenas_y_mensajes 1, codigo_y_literales 1, estado_global 25, heap 2, otra 4, scratchpad 1
- **Llama a (aristas):** audio_xa_y_spu (11), camara_y_bucle_logico (3), cargador_de_niveles_y_cd (2), colision_y_terreno (1), entrada_de_mando (4), gestion_y_dibujo_de_objetos (6), graficos_y_gte (7), inicializacion_de_motor (3), menus_e_interfaz (3), tarjeta_de_memoria (2)
- **Lo llaman (aristas):** tarjeta_de_memoria (1)
- **Datos compartidos (8 o mas direcciones en comun):** interprete_de_eventos (23), entrada_de_mando (20), gestion_y_dibujo_de_objetos (19), logica_de_niveles (17), inicializacion_de_motor (16), cargador_de_niveles_y_cd (15), menus_e_interfaz (14), graficos_y_gte (13), movimiento_y_objetos_de_escena (12), camara_y_bucle_logico (10), audio_xa_y_spu (9), tarjeta_de_memoria (8)

### 2. Tarjeta de memoria y guardado (`tarjeta_de_memoria`)

Guardado y carga de partidas con la API de archivos de la BIOS (`open`, `read`, `write`, `lseek`, `close`) sobre el archivo `bu00:BASLUS-00838 BBLIT`, mas la libreria de tarjetas (`MemCardExist`, `MemCardAccept`, `MemCardFormat`, `MemCardGetDirentry`, `MemCardSync`). `func_800156F4` (1952 bytes) es el sondeo por cuadro; `main` llama a `func_80015E94` (`MemCardSync`) cuando no hay nada que hacer. Usa la suma de control de `0x80041238`.

- **Rangos:** `0x80014AC4..0x80015EC0`
- **Funciones (10, 5116 bytes):** `80014AC4` func_80014AC4, `80014BA0` func_80014BA0, `80014C54` func_80014C54, `80014E24` func_80014E24, `80014EF8` func_80014EF8, `80014FAC` func_80014FAC, `8001515C` func_8001515C, `800151FC` func_800151FC, `800156F4` func_800156F4, `80015E94` func_80015E94
- **Librerias de Sony (llamadas):** close (3), open (3), MemCardSync (2), VSync (2), lseek (2), write (2), MemCardAccept (1), MemCardExist (1), MemCardFormat (1), MemCardGetDirentry (1), memset (1), read (1)
- **Cadenas que lo delatan:** `0x8005E04C` "bu00:BASLUS-00838 BBLIT"
- **Datos que toca (direcciones distintas por region):** bss 17, cadenas_y_mensajes 1, datos_pequenos 1, datos_y_tablas 4, estado_global 13
- **Llama a (aristas):** arranque_y_bucle_principal (1), audio_xa_y_spu (1), cargador_de_niveles_y_cd (6)
- **Lo llaman (aristas):** arranque_y_bucle_principal (2)
- **Datos compartidos (8 o mas direcciones en comun):** interprete_de_eventos (9), arranque_y_bucle_principal (8)

### 3. Graficos, GTE y retorno de video (`graficos_y_gte`)

Tres bloques. (1) `0x80016C0C..0x80019364`: nueve rutinas de calculo de matrices por objeto (`ApplyMatrixSV` y `RotMatrixZYX` en todas), sin llamadas a otras funciones del juego y llamadas solo desde las funciones gigantes y los manejadores de nivel. (2) `0x80040A80..0x80040EB4`: retornos de llamada de VSync (`func_80040AF0`) y DrawSync (`func_80040A80`) y el envio de primitivas `func_80040B8C` (`DrawSync`, anillo de tres buffers, `GsSwapDispBuff`, tres `DrawOTag`). (3) `0x800443CC..0x80044664`: `ClearImage`, `ResetGraph`, `PutDispEnv`. Los mensajes `Error: Can't push matrix,stack(max 20) is full!` (`0x80067C7C`) y `...stack is empty!` pertenecen a las rutinas de libgs (`0x8005567C`, `0x80055720`), no al juego: el juego no maneja la pila de matrices, usa directamente `RotMatrix`/`ScaleMatrix` y las instrucciones del GTE.

- **Rangos:** `0x80016C0C..0x80019364`, `0x80040A80..0x80040EB4`, `0x800443CC..0x80044664`
- **Funciones (19, 11812 bytes):** `80016C0C` func_80016C0C, `80016ED0` func_80016ED0, `800171E4` func_800171E4, `80017478` func_80017478, `80018664` func_80018664, `80018C68` func_80018C68, `80018D98` func_80018D98, `80018F80` func_80018F80, `80019180` func_80019180, `80040A80` func_80040A80, `80040AF0` func_80040AF0, `80040B8C` func_80040B8C, `80040D98` func_80040D98, `80040DDC` func_80040DDC, `80040E30` func_80040E30, `800443CC` func_800443CC, `8004443C` func_8004443C, `80044588` func_80044588, `800445E8` func_800445E8
- **Librerias de Sony (llamadas):** ApplyMatrixSV (9), RotMatrixZYX (9), DrawSync (4), DrawSyncCallback (3), MoveImage (2), ResetGraph (2), RotMatrix (2), VSyncCallback (2), ratan2 (2), CdReadyCallback (1), ClearImage (1), DrawOTag (1), GsSwapDispBuff (1), PutDispEnv (1), SetDefDispEnv (1), SetDispMask (1), SquareRoot0 (1), VSync (1)
- **Cadenas que lo delatan:** ninguna referenciada directamente
- **Datos que toca (direcciones distintas por region):** bss 25, datos_pequenos 1, datos_y_tablas 1, estado_global 1, heap 1, otra 3
- **Llama a (aristas):** audio_xa_y_spu (4), cargador_de_niveles_y_cd (3), colision_y_terreno (1), inicializacion_de_motor (2)
- **Lo llaman (aristas):** arranque_y_bucle_principal (7), cargador_de_niveles_y_cd (4), logica_de_niveles (15), movimiento_y_objetos_de_escena (3)
- **Datos compartidos (8 o mas direcciones en comun):** arranque_y_bucle_principal (13), cargador_de_niveles_y_cd (12), gestion_y_dibujo_de_objetos (9), inicializacion_de_motor (9), menus_e_interfaz (8)

### 4. Colision y terreno (`colision_y_terreno`)

Cuatro funciones, ninguna llama a otra del juego. `func_80019364` carga la tabla de zonas (60 entradas de 0x44 bytes en `0x80069C18`; cuenta y puntero en `$gp+0x58` y `$gp+0x5C`); `func_8001BF9C` busca la zona que contiene un punto (x, y, z); `func_8001C134` consulta la baldosa bajo el punto (celdas de 320 unidades, subceldas de 40; los valores `0x7E` y `0x7F` producen una transicion de zona); `func_80019474` (11.048 bytes) mueve un punto contra el terreno. Es un servicio puro: lo usan 6 subsistemas y no depende de ninguno.

- **Rangos:** `0x80019364..0x8001C424`
- **Funciones (4, 12480 bytes):** `80019364` func_80019364, `80019474` func_80019474, `8001BF9C` func_8001BF9C, `8001C134` func_8001C134
- **Librerias de Sony (llamadas):** SquareRoot0 (1)
- **Cadenas que lo delatan:** ninguna referenciada directamente
- **Datos que toca (direcciones distintas por region):** bss 3, otra 1, scratchpad 1
- **Llama a (aristas):** ningun otro subsistema
- **Lo llaman (aristas):** arranque_y_bucle_principal (1), camara_y_bucle_logico (4), gestion_y_dibujo_de_objetos (2), graficos_y_gte (1), logica_de_niveles (8), movimiento_y_objetos_de_escena (6)
- **Datos compartidos (8 o mas direcciones en comun):** menos de 8 con cualquier otro

### 5. Movimiento de entidades, objetos de escena y eventos de zona (`movimiento_y_objetos_de_escena`)

Entidades con la posicion en los campos `0xE4/0xE8/0xEC`. `func_8001C424` (salto con `rsin`), `func_8001C6CC` (aplica un desplazamiento llamando a `func_80019474` y actualiza la posicion), `func_8001CF50`/`func_8001CFCC` (reconstruyen la matriz de un objeto con `RotMatrix`, `ScaleMatrix` y la rutina de libreria sin nombre `func_8004FADC`; 11 y 13 llamadores), la lista de eventos de la entidad del jugador (`D_80069698`, `func_8001D0FC`), la interaccion `func_8001D75C`, y `func_8001E1A4`, que recorre los eventos de la zona, evalua la condicion con `func_8002F9F8` y ejecuta la accion con `func_80030ECC`. Incluye dos rutinas grandes (`func_8001E720`, 2888 bytes; `func_8001F268`, 4008 bytes).

- **Rangos:** `0x8001C424..0x80020B90`
- **Funciones (27, 18284 bytes):** `8001C424` func_8001C424, `8001C6CC` func_8001C6CC, `8001C998` func_8001C998, `8001CBB8` func_8001CBB8, `8001CC68` func_8001CC68, `8001CD84` func_8001CD84, `8001CE64` func_8001CE64, `8001CF50` func_8001CF50, `8001CFCC` func_8001CFCC, `8001D028` func_8001D028, `8001D0FC` func_8001D0FC, `8001D31C` func_8001D31C, `8001D414` func_8001D414, `8001D588` func_8001D588, `8001D75C` func_8001D75C, `8001D994` func_8001D994, `8001DA14` func_8001DA14, `8001DF28` func_8001DF28, `8001E1A4` func_8001E1A4, `8001E528` func_8001E528, `8001E600` func_8001E600, `8001E720` func_8001E720, `8001F268` func_8001F268, `80020210` func_80020210, `80020240` func_80020240, `80020354` func_80020354, `80020A90` func_80020A90
- **Librerias de Sony (llamadas):** RotMatrix (4), ApplyMatrix (2), ScaleMatrix (2), func_8004FADC (2), rsin (2), MulMatrix2 (1), RotMatrixZYX (1)
- **Cadenas que lo delatan:** ninguna referenciada directamente
- **Datos que toca (direcciones distintas por region):** bss 24, datos_y_tablas 2, estado_global 4, otra 8
- **Llama a (aristas):** audio_xa_y_spu (4), camara_y_bucle_logico (2), colision_y_terreno (6), gestion_y_dibujo_de_objetos (4), graficos_y_gte (3), interprete_de_eventos (6), menus_e_interfaz (1)
- **Lo llaman (aristas):** audio_xa_y_spu (1), camara_y_bucle_logico (4), gestion_y_dibujo_de_objetos (3), interprete_de_eventos (2), logica_de_niveles (52), menus_e_interfaz (2)
- **Datos compartidos (8 o mas direcciones en comun):** logica_de_niveles (22), camara_y_bucle_logico (18), interprete_de_eventos (18), arranque_y_bucle_principal (12), gestion_y_dibujo_de_objetos (10), menus_e_interfaz (10), inicializacion_de_motor (9), entrada_de_mando (8)

### 6. Logica de niveles (rutinas por tabla y las dos funciones gigantes) (`logica_de_niveles`)

Rutinas por nivel o por tipo de nivel. `func_800353B0` (camara y logica de cada cuadro) lee la tabla de punteros a codigo de `0x8005E35C` (37 entradas, 32 destinos distintos) y por eso estas funciones no tienen `jal` entrante. Contiene las dos funciones gigantes (`func_80020B90`, `func_80026FEC`), rutinas medianas (`func_80025938`, `func_80025B2C`, `func_8002BA80`..`func_8002F6B4`), rutinas vacias (`func_80025B24`, `func_8002EA9C`, `func_8002F968`: solo `jr ra`) y `func_80026298`, la rutina comun que invocan los 12 manejadores de 32 bytes.

- **Rangos:** `0x80020B90..0x80026118`, `0x80026298..0x8002F9F8`
- **Funciones (21, 60648 bytes):** `80020B90` func_80020B90, `80025938` func_80025938, `80025B24` func_80025B24, `80025B2C` func_80025B2C, `80026298` func_80026298, `80026FEC` func_80026FEC, `8002BA80` func_8002BA80, `8002C1DC` func_8002C1DC, `8002CB8C` func_8002CB8C, `8002CEC4` func_8002CEC4, `8002D03C` func_8002D03C, `8002D68C` func_8002D68C, `8002EA9C` func_8002EA9C, `8002EAA4` func_8002EAA4, `8002F018` func_8002F018, `8002F510` func_8002F510, `8002F614` func_8002F614, `8002F6B4` func_8002F6B4, `8002F968` func_8002F968, `8002F970` func_8002F970, `8002F990` func_8002F990
- **Librerias de Sony (llamadas):** SquareRoot0 (6), ApplyMatrixSV (5), RotMatrix (5), RotMatrixY (4), ratan2 (4), ApplyMatrix (3), ApplyMatrixLV (3), GsInitCoordinate2 (3), RotMatrixX (3), RotMatrixZ (3), ScaleMatrix (3), func_8004FADC (3), rsin (3), RotMatrixYXZ (1), RotMatrixZYX (1)
- **Cadenas que lo delatan:** ninguna referenciada directamente
- **Datos que toca (direcciones distintas por region):** bss 61, datos_y_tablas 1, estado_global 8, otra 35, scratchpad 34
- **Llama a (aristas):** audio_xa_y_spu (8), camara_y_bucle_logico (5), colision_y_terreno (8), gestion_y_dibujo_de_objetos (10), graficos_y_gte (15), inicializacion_de_motor (4), interprete_de_eventos (16), menus_e_interfaz (1), movimiento_y_objetos_de_escena (52)
- **Lo llaman (aristas):** camara_y_bucle_logico (19), interprete_de_eventos (1), manejadores_por_tabla (12)
- **Datos compartidos (8 o mas direcciones en comun):** camara_y_bucle_logico (31), interprete_de_eventos (28), movimiento_y_objetos_de_escena (22), gestion_y_dibujo_de_objetos (20), arranque_y_bucle_principal (17), inicializacion_de_motor (15), entrada_de_mando (14), menus_e_interfaz (14), cargador_de_niveles_y_cd (9)

### 7. Manejadores de 32 bytes llamados por tabla (`manejadores_por_tabla`)

Doce rutinas identicas de 32 bytes entre `0x80026118` y `0x80026298`: cada una guarda `ra`, llama a `func_80026298(entidad, mascara)` y retorna. La mascara de cada manejador es, en orden de direccion, `0x2, 0x1, 0x80, 0x4, 0x8, 0x10, 0x20, 0x22, 0x40, 0x100, 0x200, 0x400`: son banderas de bits. Solo se alcanzan por la tabla de `0x8005E35C` (aristas `tabla` desde `func_800353B0`).

- **Rangos:** `0x80026118..0x80026298`
- **Funciones (12, 384 bytes):** `80026118` func_80026118, `80026138` func_80026138, `80026158` func_80026158, `80026178` func_80026178, `80026198` func_80026198, `800261B8` func_800261B8, `800261D8` func_800261D8, `800261F8` func_800261F8, `80026218` func_80026218, `80026238` func_80026238, `80026258` func_80026258, `80026278` func_80026278
- **Librerias de Sony (llamadas):** ninguna
- **Cadenas que lo delatan:** ninguna referenciada directamente
- **Datos que toca (direcciones distintas por region):** ninguno
- **Llama a (aristas):** logica_de_niveles (12)
- **Lo llaman (aristas):** camara_y_bucle_logico (12)
- **Datos compartidos (8 o mas direcciones en comun):** menos de 8 con cualquier otro

### 8. Evaluador de condiciones y ejecutor de acciones de eventos (`interprete_de_eventos`)

`func_8002F9F8` y `func_80030ECC` leen un byte de codigo de operacion (`lbu 0($a1)`) y saltan por una tabla: 92 entradas en `0x8005E3F0` (condiciones) y 102 en `0x8005E560` (acciones). Cada entrada apunta a una rutina hoja dentro del mismo simbolo, por eso la tabla de simbolos las tiene fundidas (ver la nota al final). Cada una tiene 11 llamadores, entre ellos `func_8001E1A4`, y lee y escribe el estado global del juego: comparte 8 o mas datos con 11 de los otros 14 subsistemas.

- **Rangos:** `0x8002F9F8..0x80032874`
- **Funciones (2, 11900 bytes):** `8002F9F8` func_8002F9F8, `80030ECC` func_80030ECC
- **Librerias de Sony (llamadas):** ratan2 (2)
- **Cadenas que lo delatan:** ninguna referenciada directamente
- **Datos que toca (direcciones distintas por region):** bss 40, datos_y_tablas 2, estado_global 12, otra 6
- **Llama a (aristas):** audio_xa_y_spu (5), camara_y_bucle_logico (1), inicializacion_de_motor (3), logica_de_niveles (1), menus_e_interfaz (2), movimiento_y_objetos_de_escena (2)
- **Lo llaman (aristas):** logica_de_niveles (16), movimiento_y_objetos_de_escena (6)
- **Datos compartidos (8 o mas direcciones en comun):** logica_de_niveles (28), arranque_y_bucle_principal (23), camara_y_bucle_logico (20), movimiento_y_objetos_de_escena (18), entrada_de_mando (16), gestion_y_dibujo_de_objetos (16), inicializacion_de_motor (13), menus_e_interfaz (12), audio_xa_y_spu (11), cargador_de_niveles_y_cd (11), tarjeta_de_memoria (9)

### 9. Camara y logica de cada cuadro (`camara_y_bucle_logico`)

`func_80032874` (envoltorio de `rand`, 7 llamadores), la camara (`func_80032894` copia la estructura `D_8006D928`, la misma que `main` pasa a `GsSetRefView2L`; `func_80032B2C`, `func_80033358` con 6948 bytes y 53 accesos relativos a `$gp`) y la logica de cada cuadro (`func_80035244`, con un `switch` de 7 casos, y `func_800353B0`, 3508 bytes y 35 funciones llamadas). La invocan `func_80016218` y `main`.

- **Rangos:** `0x80032874..0x80036164`
- **Funciones (11, 14576 bytes):** `80032874` func_80032874, `80032894` func_80032894, `80032A24` func_80032A24, `80032B2C` func_80032B2C, `800330AC` func_800330AC, `80033358` func_80033358, `80034E7C` func_80034E7C, `8003502C` func_8003502C, `800351B4` func_800351B4, `80035244` func_80035244, `800353B0` func_800353B0
- **Librerias de Sony (llamadas):** RotMatrix (3), ratan2 (3), RotMatrixY (2), RotMatrixZYX (2), SquareRoot0 (2), ApplyMatrix (1), ApplyMatrixSV (1), RotMatrixX (1), rand (1), rcos (1), rsin (1)
- **Cadenas que lo delatan:** ninguna referenciada directamente
- **Datos que toca (direcciones distintas por region):** bss 44, cadenas_y_mensajes 1, datos_y_tablas 4, estado_global 7, otra 4, scratchpad 19
- **Llama a (aristas):** audio_xa_y_spu (2), colision_y_terreno (4), gestion_y_dibujo_de_objetos (5), logica_de_niveles (19), manejadores_por_tabla (12), movimiento_y_objetos_de_escena (4)
- **Lo llaman (aristas):** arranque_y_bucle_principal (3), audio_xa_y_spu (1), inicializacion_de_motor (1), interprete_de_eventos (1), logica_de_niveles (5), movimiento_y_objetos_de_escena (2)
- **Datos compartidos (8 o mas direcciones en comun):** logica_de_niveles (31), interprete_de_eventos (20), movimiento_y_objetos_de_escena (18), gestion_y_dibujo_de_objetos (15), inicializacion_de_motor (15), menus_e_interfaz (15), entrada_de_mando (11), arranque_y_bucle_principal (10)

### 10. Reserva de objetos, listas y dibujo de la escena (`gestion_y_dibujo_de_objetos`)

Reserva de objetos en pozos de tamano fijo (`func_80036204` busca la ranura libre por una bandera, `func_80036250` la libera con `memset`; `func_80036734` copia una plantilla de 0x1F4 bytes), listas de objetos (`func_80037048` recorre la lista de la escena guardando punteros en el scratchpad `0x1F800000`; `func_80037FB8` apaga la bandera 2 de todos los objetos de una lista; `main` la llama al pausar y al cambiar de estado), matrices y dibujo (`func_8003690C`, `func_80037184`, `func_80037DB4` con `GsInitCoordinate2`, `func_8003A5C8` con `GsSortBoxFill`).

- **Rangos:** `0x80036164..0x8003AA38`
- **Funciones (42, 18624 bytes):** `80036164` func_80036164, `800361CC` func_800361CC, `80036204` func_80036204, `80036250` func_80036250, `800362D0` func_800362D0, `80036358` func_80036358, `8003638C` func_8003638C, `800363D4` func_800363D4, `80036474` func_80036474, `800364E0` func_800364E0, `8003652C` func_8003652C, `800365D0` func_800365D0, `80036734` func_80036734, `800368E8` func_800368E8, `8003690C` func_8003690C, `80037048` func_80037048, `80037184` func_80037184, `8003753C` func_8003753C, `80037580` func_80037580, `800375C4` func_800375C4, `8003760C` func_8003760C, `800379A0` func_800379A0, `80037B08` func_80037B08, `80037C00` func_80037C00, `80037CF8` func_80037CF8, `80037D3C` func_80037D3C, `80037DB4` func_80037DB4, `80037FB8` func_80037FB8, `80037FE8` func_80037FE8, `8003861C` func_8003861C, `80038884` func_80038884, `800389FC` func_800389FC, `80038C2C` func_80038C2C, `80038E84` func_80038E84, `80039094` func_80039094, `800399C8` func_800399C8, `80039BFC` func_80039BFC, `80039C3C` func_80039C3C, `80039CD0` func_80039CD0, `80039D44` func_80039D44, `8003A3D0` func_8003A3D0, `8003A5C8` func_8003A5C8
- **Librerias de Sony (llamadas):** RotMatrix (2), RotMatrixY (2), RotMatrixZ (2), ScaleMatrix (2), func_8004FADC (2), ApplyMatrixSV (1), GsInitCoordinate2 (1), GsSortBoxFill (1), RotMatrixX (1), memset (1), ratan2 (1)
- **Cadenas que lo delatan:** ninguna referenciada directamente
- **Datos que toca (direcciones distintas por region):** bss 58, cadenas_y_mensajes 1, codigo_y_literales 1, datos_y_tablas 21, estado_global 25, otra 7, scratchpad 9
- **Llama a (aristas):** colision_y_terreno (2), menus_e_interfaz (3), movimiento_y_objetos_de_escena (3)
- **Lo llaman (aristas):** arranque_y_bucle_principal (6), camara_y_bucle_logico (5), cargador_de_niveles_y_cd (11), inicializacion_de_motor (5), logica_de_niveles (10), menus_e_interfaz (6), movimiento_y_objetos_de_escena (4)
- **Datos compartidos (8 o mas direcciones en comun):** inicializacion_de_motor (41), menus_e_interfaz (25), cargador_de_niveles_y_cd (24), logica_de_niveles (20), arranque_y_bucle_principal (19), interprete_de_eventos (16), camara_y_bucle_logico (15), movimiento_y_objetos_de_escena (10), graficos_y_gte (9)

### 11. Menus, fundidos e interfaz (`menus_e_interfaz`)

Tres rutinas vacias sin llamadores (`func_8003AA38`, `func_8003AA40`, `func_8003AA48`), el control de fundidos (`func_8003AA50(modo, duracion)` y `func_8003AA7C`, que `main` llama con `(1, 0x100)` y `(2, 0x100)`) y las pantallas de interfaz que dibujan con `GsSortBoxFill`: `func_8003B5AC` (2084 bytes), `func_8003C1C8` (2196 bytes, un `switch` de 21 casos), `func_8003CA5C`, `func_8003D0D4`. La asignacion de nombre es una hipotesis: no hay cadenas de menu en el ejecutable (los textos viven en los contenedores de niveles).

- **Rangos:** `0x8003AA38..0x8003DF84`
- **Funciones (27, 13644 bytes):** `8003AA38` func_8003AA38, `8003AA40` func_8003AA40, `8003AA48` func_8003AA48, `8003AA50` func_8003AA50, `8003AA7C` func_8003AA7C, `8003AAA8` func_8003AAA8, `8003AB3C` func_8003AB3C, `8003ABB4` func_8003ABB4, `8003ACA8` func_8003ACA8, `8003AE08` func_8003AE08, `8003AF8C` func_8003AF8C, `8003B26C` func_8003B26C, `8003B354` func_8003B354, `8003B5AC` func_8003B5AC, `8003BDD0` func_8003BDD0, `8003C014` func_8003C014, `8003C1C8` func_8003C1C8, `8003CA5C` func_8003CA5C, `8003D0D4` func_8003D0D4, `8003D7C4` func_8003D7C4, `8003D814` func_8003D814, `8003D880` func_8003D880, `8003D904` func_8003D904, `8003D988` func_8003D988, `8003DA4C` func_8003DA4C, `8003DD70` func_8003DD70, `8003DF10` func_8003DF10
- **Librerias de Sony (llamadas):** ApplyMatrixLV (1), GsGetLw (1), GsSortBoxFill (1), SquareRoot0 (1), ratan2 (1)
- **Cadenas que lo delatan:** ninguna referenciada directamente
- **Datos que toca (direcciones distintas por region):** bss 49, cadenas_y_mensajes 1, estado_global 1, otra 8, scratchpad 2
- **Llama a (aristas):** gestion_y_dibujo_de_objetos (6), movimiento_y_objetos_de_escena (2)
- **Lo llaman (aristas):** arranque_y_bucle_principal (3), gestion_y_dibujo_de_objetos (3), interprete_de_eventos (2), logica_de_niveles (1), movimiento_y_objetos_de_escena (1)
- **Datos compartidos (8 o mas direcciones en comun):** inicializacion_de_motor (29), gestion_y_dibujo_de_objetos (25), cargador_de_niveles_y_cd (17), camara_y_bucle_logico (15), arranque_y_bucle_principal (14), logica_de_niveles (14), interprete_de_eventos (12), movimiento_y_objetos_de_escena (10), graficos_y_gte (8)

### 12. Audio XA, SPU y comprobacion del disco (`audio_xa_y_spu`)

Audio en streaming XA (`func_8003E034`, `func_8003E16C`, `func_8003E298`, `func_8003E680`, `func_8003E88C`: modo `0xCA` con `CdControlB(0x0E)` y lectura continua con `CdControlB(0x1B)`; posiciones en la tabla de `0x8005E968`), la comprobacion del disco `func_8003E9E8` (`CdSearchFile` con `\LEVEL5\MERLIN.BZZ;1`, cadena en `0x80067EF0`), y efectos por SPU: reverberacion (`func_8003ECF8`), voces (`func_8003F528` con `SpuSetKey`, `func_8003FA2C`, `func_8003FC88`, `func_8003FD60`, `func_8003FEEC`), volumen maestro (`func_8003F984`) y lectura de memoria de sonido (`func_8003F9C4`). `func_8003F06C` (900 bytes, 14 llamadores, sin librerias) parece ser el punto de entrada comun de los efectos de sonido (hipotesis).

- **Rangos:** `0x8003DF84..0x8003FFA0`
- **Funciones (37, 8220 bytes):** `8003DF84` func_8003DF84, `8003DFE4` func_8003DFE4, `8003E034` func_8003E034, `8003E068` func_8003E068, `8003E094` func_8003E094, `8003E0C8` func_8003E0C8, `8003E120` func_8003E120, `8003E16C` func_8003E16C, `8003E298` func_8003E298, `8003E3C0` func_8003E3C0, `8003E680` func_8003E680, `8003E88C` func_8003E88C, `8003E948` func_8003E948, `8003E9E8` func_8003E9E8, `8003EAEC` func_8003EAEC, `8003EB48` func_8003EB48, `8003EB80` func_8003EB80, `8003EB88` func_8003EB88, `8003EC3C` func_8003EC3C, `8003ECD4` func_8003ECD4, `8003ECF8` func_8003ECF8, `8003ED6C` func_8003ED6C, `8003ED94` func_8003ED94, `8003EDA8` func_8003EDA8, `8003F06C` func_8003F06C, `8003F3F0` func_8003F3F0, `8003F528` func_8003F528, `8003F900` func_8003F900, `8003F984` func_8003F984, `8003F9C4` func_8003F9C4, `8003FA2C` func_8003FA2C, `8003FB54` func_8003FB54, `8003FC04` func_8003FC04, `8003FC88` func_8003FC88, `8003FD60` func_8003FD60, `8003FDEC` func_8003FDEC, `8003FEEC` func_8003FEEC
- **Librerias de Sony (llamadas):** CdControlB (8), CdPosToInt (4), CdIntToPos (3), CdReadyCallback (3), SpuSetVoicePitch (3), VSync (3), SpuSetKey (2), SpuSetReverbVoice (2), SpuSetVoiceVolume (2), CdControl (1), CdControlF (1), CdDiskReady (1), CdGetDiskType (1), CdMix (1), CdSearchFile (1), CdStatus (1), SpuGetAllKeysStatus (1), SpuGetVoicePitch (1), SpuIsTransferCompleted (1), SpuRead (1), SpuReserveReverbWorkArea (1), SpuSetCommonAttr (1), SpuSetCommonCDMix (1), SpuSetCommonMasterVolume (1), SpuSetReverb (1), SpuSetReverbDepth (1), SpuSetReverbModeParam (1), SpuSetTransferStartAddr (1), SpuSetVoiceStartAddr (1), SsUtReverbOff (1), func_8004D860 (1), ratan2 (1)
- **Cadenas que lo delatan:** ninguna referenciada directamente
- **Datos que toca (direcciones distintas por region):** bss 48, cadenas_y_mensajes 1, datos_y_tablas 6, estado_global 4, otra 1
- **Llama a (aristas):** camara_y_bucle_logico (1), inicializacion_de_motor (1), movimiento_y_objetos_de_escena (1)
- **Lo llaman (aristas):** arranque_y_bucle_principal (11), camara_y_bucle_logico (2), cargador_de_niveles_y_cd (7), graficos_y_gte (4), inicializacion_de_motor (1), interprete_de_eventos (5), logica_de_niveles (8), movimiento_y_objetos_de_escena (4), tarjeta_de_memoria (1)
- **Datos compartidos (8 o mas direcciones en comun):** cargador_de_niveles_y_cd (17), interprete_de_eventos (11), arranque_y_bucle_principal (9)

### 13. Entrada de mando (`entrada_de_mando`)

`func_8003FFA0` inicializa los mandos (`PadInitDirect`, `PadStartCom`, `MemCardStart`), `func_80040240` gestiona la vibracion (`PadSetAct`, `PadSetActAlign`, `PadGetState`) y `func_8004048C` (1524 bytes) parece traducir el estado de los mandos a la palabra de entrada que el resto del juego lee en `0x80010000` (28 referencias al estado global). Ninguna llama a otra funcion del juego.

- **Rangos:** `0x8003FFA0..0x80040A80`
- **Funciones (6, 2784 bytes):** `8003FFA0` func_8003FFA0, `800400C0` func_800400C0, `80040158` func_80040158, `80040240` func_80040240, `80040430` func_80040430, `8004048C` func_8004048C
- **Librerias de Sony (llamadas):** PadGetState (2), PadInfoMode (2), MemCardStart (1), PadInitDirect (1), PadSetAct (1), PadSetActAlign (1), PadSetMainMode (1), PadStartCom (1), VSync (1), func_8005A21C (1)
- **Cadenas que lo delatan:** ninguna referenciada directamente
- **Datos que toca (direcciones distintas por region):** bss 29, datos_y_tablas 1, estado_global 28
- **Llama a (aristas):** ningun otro subsistema
- **Lo llaman (aristas):** arranque_y_bucle_principal (4), inicializacion_de_motor (2)
- **Datos compartidos (8 o mas direcciones en comun):** arranque_y_bucle_principal (20), interprete_de_eventos (16), logica_de_niveles (14), camara_y_bucle_logico (11), inicializacion_de_motor (9), movimiento_y_objetos_de_escena (8)

### 14. Cargador de niveles, lectura de CD y descompresor (`cargador_de_niveles_y_cd`)

`func_80040EB4` construye al arrancar la tabla de 113 entradas (sector, tamano) desde `0x8005EE78` (registros de posicion de CD desde `0x8005F206`); `func_800411F0` inicia una lectura de sectores crudos y `func_8004109C` es el retorno de llamada que copia cada sector; `func_80041238` es la suma de control, `func_80041264` un lector de flujo de bytes, `func_80044664` el descompresor (496 bytes, usa el scratchpad como area de trabajo) y `func_800415A0` el cargador de niveles. La cadena `BouzeID %d not found` (`0x80067F54`) sale de `func_800415A0`.

- **Rangos:** `0x80040EB4..0x800443CC`, `0x80044664..0x80044904`
- **Funciones (12, 14264 bytes):** `80040EB4` func_80040EB4, `80040F78` func_80040F78, `8004109C` func_8004109C, `800411F0` func_800411F0, `80041238` func_80041238, `80041264` func_80041264, `80041298` func_80041298, `8004153C` func_8004153C, `800415A0` func_800415A0, `80042BB8` func_80042BB8, `80044664` func_80044664, `80044854` func_80044854
- **Librerias de Sony (llamadas):** CdControl (3), CdIntToPos (3), CdPosToInt (2), CdReadyCallback (2), CdStatus (2), printf (2), CdControlB (1), CdGetSector (1), CdSync (1), DrawSync (1), GsGetTimInfo (1), GsMapModelingData (1), LoadImage (1), RotMatrix (1), ScaleMatrix (1), SetDispMask (1), EnterCriticalSection (1), ExitCriticalSection (1), func_8004FADC (1), memset (1)
- **Cadenas que lo delatan:** `0x80067F54` "BouzeID %d not found"; `0x8006933C` "Got it"
- **Datos que toca (direcciones distintas por region):** bss 77, cadenas_y_mensajes 8, datos_pequenos 1, datos_y_tablas 2, estado_global 4, scratchpad 1
- **Llama a (aristas):** audio_xa_y_spu (7), gestion_y_dibujo_de_objetos (11), graficos_y_gte (4), inicializacion_de_motor (2)
- **Lo llaman (aristas):** arranque_y_bucle_principal (2), graficos_y_gte (3), tarjeta_de_memoria (6)
- **Datos compartidos (8 o mas direcciones en comun):** gestion_y_dibujo_de_objetos (24), inicializacion_de_motor (20), audio_xa_y_spu (17), menus_e_interfaz (17), arranque_y_bucle_principal (15), graficos_y_gte (12), interprete_de_eventos (11), logica_de_niveles (9)

### 15. Inicializacion del motor y utilidades finales (`inicializacion_de_motor`)

Inicializacion del SDK y del motor: `func_80044D44` (`CdInit`, retornos de llamada de CD, `DecDCTReset`), `func_80044E58` (`GsSetRefView2L`, `memset`), `func_80044A04` (`GsGetActiveBuff`) y utilidades que usan casi todos los subsistemas (`func_80045150`, que `func_80016218` llama en cada cuadro, y `func_80045498`, 1972 bytes, que toca el estado global).

- **Rangos:** `0x80044904..0x80045DA0`
- **Funciones (16, 5276 bytes):** `80044904` func_80044904, `80044940` func_80044940, `800449B0` func_800449B0, `800449E0` func_800449E0, `80044A04` func_80044A04, `80044D44` func_80044D44, `80044E58` func_80044E58, `80044EA8` func_80044EA8, `80044F20` func_80044F20, `800450E8` func_800450E8, `80045150` func_80045150, `80045368` func_80045368, `800453D0` func_800453D0, `80045498` func_80045498, `80045C4C` func_80045C4C, `80045D98` func_80045D98
- **Librerias de Sony (llamadas):** CdDataCallback (1), CdInit (1), CdReadCallback (1), CdReadyCallback (1), CdSetDebug (1), CdSyncCallback (1), DecDCTReset (1), DecDCTinCallback (1), DecDCToutCallback (1), DrawSyncCallback (1), FlushCache (1), GsDefDispBuff (1), GsGetActiveBuff (1), GsInit3D (1), GsInitGraph (1), GsSetRefView2L (1), InitGeom (1), ResetCallback (1), ResetGraph (1), SetGraphDebug (1), SpuSetIRQCallback (1), SpuStSetPreparationFinishedCallback (1), SpuStSetStreamFinishedCallback (1), SpuStSetTransferFinishedCallback (1), VSyncCallback (1), func_8004BBF0 (1), func_8004E584 (1), func_8005595C (1), func_80055AFC (1), memset (1)
- **Cadenas que lo delatan:** ninguna referenciada directamente
- **Datos que toca (direcciones distintas por region):** bss 83, datos_y_tablas 3, estado_global 13, otra 4
- **Llama a (aristas):** audio_xa_y_spu (1), camara_y_bucle_logico (1), entrada_de_mando (2), gestion_y_dibujo_de_objetos (5)
- **Lo llaman (aristas):** arranque_y_bucle_principal (3), audio_xa_y_spu (1), cargador_de_niveles_y_cd (2), graficos_y_gte (2), interprete_de_eventos (3), logica_de_niveles (4)
- **Datos compartidos (8 o mas direcciones en comun):** gestion_y_dibujo_de_objetos (41), menus_e_interfaz (29), cargador_de_niveles_y_cd (20), arranque_y_bucle_principal (16), camara_y_bucle_logico (15), logica_de_niveles (15), interprete_de_eventos (13), entrada_de_mando (9), graficos_y_gte (9), movimiento_y_objetos_de_escena (9)

## Las tres funciones gigantes

| Funcion | Bytes | Que parece ser | Como partirla |
|---|---|---|---|
| `func_80020B90` | 19.880 | Logica de un nivel o tipo de nivel: se alcanza solo por la tabla de `0x8005E35C` (arista `tabla` desde `func_800353B0`). Llama 24 funciones; las mas frecuentes son `func_8001CFCC` (11 veces), `func_80019474` (9) y `func_8001CE64` (8). Sin `switch`: es codigo lineal con 37 etiquetas de salto en el borrador. | Por bloques de condiciones de primer nivel; cada bloque que termina en llamadas a `func_8001CFCC`/`func_8001CE64` es una rutina de objeto. 65 accesos a `$gp`. |
| `func_80026FEC` | 19.092 | Gemela estructural de la anterior (mismas funciones llamadas: `func_8001CFCC` 20 veces, `func_80032874` 8, `func_8001CE64` 6); otro nivel o tipo de nivel de la misma tabla. | Igual que la anterior; conviene descompilar primero una y reutilizar el reparto de bloques en la otra. |
| `func_80019474` | 11.048 | Movimiento contra el terreno: la llama `func_8001C6CC` con la posicion de la entidad, un desplazamiento, banderas y una estructura de resultado, y llama 4 veces a la busqueda de zona `func_8001BF9C`. Usa `SquareRoot0`. | Por eje de movimiento y por tipo de baldosa (los valores especiales de la consulta de baldosa); 32 etiquetas de salto indican unos 30 bloques. |

Las dos primeras comparten tantas llamadas que el reparto de la descompilacion debe asignarlas al mismo
equipo. `func_80019474` es independiente del resto y se puede abordar a la vez.

## Descripcion de tres rutinas clave

### `main` (`0x80016414`, 2040 bytes)

Inicializa en este orden: `__main`, `func_80044D44` (CD y retornos de llamada), `func_80044E58` (video
y matrices), `func_80015EC0`, fija el estado `0x80010000 = 2`, `func_80040EB4` (tabla de sectores),
`func_80016118` y `func_8004443C`, y repite `func_800415A0(D_80010000, 0x80077000)` hasta que devuelve 0
(carga del primer contenido). Despues carga la tabla de zonas (`func_80019364`), instala `VSyncCallback`
con `func_80040AF0`, siembra `srand(1)`, pone a cero contadores, llama a `func_800353B0` con
`D_80069518`, arranca el contador de la raiz 2 y lanza el audio XA (`func_8003DF84`) y un fundido
(`func_8003AA50(1, 0x100)`). El bucle infinito usa un anillo de tres buffers (`D_8006967C` de 0 a 2):
comprueba el disco (`func_8003E9E8`), mide con `VSync(1)` antes y despues de `func_80016218`, sondea la
tarjeta de memoria (`func_800156F4` o `func_80015E94`), trata la pausa (boton `0x800` del estado de
entrada: apaga banderas con `func_80037FB8`/`func_80037FE8`, redibuja tres cuadros) y avanza una maquina de
estados en `D_80069662`; si el mando esta ocioso unos 900 cuadros (`0x385`) entra en un ciclo de
demostracion que rota entre cuatro valores (`0x4A..0x4D`). Al llegar al estado `0x16` recarga contenido
(`func_8004443C`, `func_800445E8`), reinicia contadores y vuelve a llamar a `func_800353B0`.
Los borradores marcan con `M2C_ERROR` un valor leido sin asignar en esa rama: hay que revisar el asm.

### `func_80016218` (`0x80016218`, 460 bytes): actualizacion de cuadro

Incrementa el contador de cuadros `D_80069534`, calcula el tiempo transcurrido
(`D_80069694 = D_80069510 - D_80069638`), lee los mandos con `func_8004048C`, ejecuta la logica con
`func_800353B0(D_80069518)` y fija la vista con `GsSetRefView2L(&D_8006D928)`. Limpia las tres tablas de
ordenacion del buffer actual con `GsClearOt` (indice `D_8006967C`, 0x14 bytes por entrada) y llena esas
tablas: `func_80037048` (recorre la escena), `func_800399C8`, `func_8003B5AC` y `func_8003A5C8` (cajas
con `GsSortBoxFill`), `func_80045150` y `func_80037184`. Si `D_800694D8` no es nulo llama dos veces a la
rutina de la RAM previa `0x8001020C` (parte del codigo cargado en ejecucion) para dibujar una segunda capa.

### `func_800415A0` (`0x800415A0`, 5656 bytes mas 6164 de `func_80042BB8`): carga de archivo

Recibe el numero de contenedor y la direccion destino. Limpia el estado de juego (`memset` de 0x100 bytes
en `0x8006AA70`, contadores y listas), consulta la entrada `numero * 0x10 + 0x8005F200` de la tabla de
sectores y, si esta vacia, imprime `BouzeID %d not found`. Fija el modo de CD (`CdControlB(0x0E)`), espera
(`CdlNop`), busca la posicion (`CdControlB(0x15)`), lee la cabecera con `func_800411F0` en `0x8006A928`
y la valida con la suma de control `func_80041238` sobre 0x7FC bytes. Despues recorre las secciones:
lee mas sectores, descomprime cada una con `func_80044664` usando el scratchpad (`0x1F800000`), interpreta
los campos con el lector de bytes `func_80041264` (tamanos de 3 a 12 bytes), copia con `func_8004153C`,
reserva y libera ranuras con `func_80036204`/`func_80036250`, carga modelos y texturas (`GsMapModelingData`,
`GsGetTimInfo`, `LoadImage`, `DrawSync`) y reactiva la pantalla (`SetDispMask`). El grafo de flujo no es
reducible: el borrador queda en saltos. El simbolo `func_80042BB8` es la continuacion del mismo cuerpo (comparte
el epilogo `0x8004439C`) y no se llama por separado.

## Hallazgos para repartir la descompilacion

- **Independientes (sin llamadas hacia otros subsistemas):** `colision_y_terreno`, `entrada_de_mando`,
  `manejadores_por_tabla` (solo llama a `func_80026298`) y los nueve calculos de matrices de `graficos_y_gte`.
  Son los mejores puntos de partida y se pueden descompilar en paralelo.
- **Comparten estado global:** el estado principal `0x80010000` (17 funciones) y las variables de `0x80069xxx`
  ligan `interprete_de_eventos`, `logica_de_niveles`, `camara_y_bucle_logico` e `inicializacion_de_motor`: sus
  tipos deben fijarse una vez en `include/` antes de repartirlos.
- **Funciones que no son una funcion:** `func_8002F9F8` (5332 bytes) y, probablemente, `func_80030ECC` (6568 bytes)
  contienen decenas de rutinas hoja alcanzadas por las tablas de 92 y 102 entradas, y `func_80042BB8` es la
  continuacion de `func_800415A0`. Hay que separarlas antes de asignarlas.
- **Descompilacion con apoyo de borradores:** 298 de 309 rutinas tienen borrador propio, 3 estan absorbidas en una funcion contigua y 8 fallan; 64 borradores contienen `M2C_ERROR`,
  en su mayor parte instrucciones del GTE (`ctc2`, `lwc2`, `mvmva`) que `m2c` no traduce y que hay que
  escribir con macros del SDK. Las ocho que fallan son rutinas internas de libreria sin firma (`FALLIDAS.csv`).

## Limitaciones y pendientes

- Los nombres de subsistema son hipotesis. `menus_e_interfaz` y `gestion_y_dibujo_de_objetos` se infirieron
  de las llamadas a `GsSortBoxFill`, las listas de objetos y los datos, sin cadenas que los confirmen.
- Este analisis se calculo con la tabla de 908 simbolos, en la que `func_8002F9F8` y `func_80030ECC` agrupaban
  decenas de rutinas. La tabla actual (1102) las separa; las cifras de funciones de las secciones de detalle
  no se han recalculado y la referencia vigente es `docs/PROGRESO.md`.

## Como se regenera

```text
python -m tools.ghidra borradores  --salida <carpeta> --exportacion <exportacion de Ghidra> --exe <SLUS_008.38>
python -m tools.ghidra grafo       --salida <carpeta> --exportacion <exportacion de Ghidra> --exe <SLUS_008.38>
python -m tools.ghidra subsistemas --salida <carpeta> --exportacion <exportacion de Ghidra> --exe <SLUS_008.38> --rangos <rangos.csv>
python -m tools.ghidra limites     --salida <carpeta> --exportacion <exportacion de Ghidra> --exe <SLUS_008.38> --rangos <rangos.csv>
```

`borradores` deja `asm/<direccion>_<nombre>.s`, `m2c/<direccion>_<nombre>.c`, `m2c/FALLIDAS.csv`,
`m2c/FUSIONADAS.csv` y `contexto_m2c.c`; `grafo` deja `grafo_llamadas.csv`, `datos_compartidos.csv` y
`punteros_funcion.csv`. Todo se escribe fuera del repositorio porque deriva del binario.

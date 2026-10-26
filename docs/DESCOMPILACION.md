# Descompilación: del ensamblador a C con verificación byte a byte

Este documento es el contrato de C del proyecto. Explica cómo está organizado el código fuente,
cómo se mueve una función del ensamblador original a C que compile exactamente al mismo código,
cómo se comprueba y cómo se mide el avance. Toda la cadena corre de forma nativa en Windows (ver
`docs/TOOLCHAIN.md`); el compilador y su elección están justificados en `docs/COMPILADOR.md`.

## Resumen del flujo

```text
python tools/build.py split            # genera asm/ y src/ (solo crea los .c que no existen)
python toolchain/m2c/m2c.py ...        # borrador en C de la función (opcional)
  (editar src/<archivo>.c)
python tools/build.py diff <función>   # compara la función compilada con su original
python tools/build.py build            # compila los .c, ensambla el resto y enlaza
python tools/build.py verify           # el ejecutable completo debe ser idéntico (OK)
python tools/build.py progreso         # actualiza docs/PROGRESO.md y build/progreso.json
```

El criterio final es siempre `verify`: el ejecutable reconstruido debe tener el SHA-256 del
original. `diff` es la herramienta de trabajo diario porque compara una sola función y muestra
dónde difiere; no sustituye a `verify`.

## Organización del código

| Ruta | Contenido |
|---|---|
| `src/<subsistema>[_N].c` | Código del juego, un archivo por unidad de compilación propuesta (ver `docs/ARCHIVOS_ORIGEN.md`). Los archivos de un mismo subsistema se numeran. |
| `include/common.h` | Tipos de ancho fijo y `NULL`. Todo `.c` empieza con `#include "common.h"`. |
| `include/macro.h` | Macro `INCLUDE_ASM`. Lo incluye `common.h`. |
| `include/gte.h` | Comandos del GTE por mnemónico (ver «Comandos del GTE»). Se incluye en lugar de `psyq/INLINE_C.H`. |
| `include/globales.h` | Tipos de la memoria que comparten los subsistemas (`Objeto` de 0x1F4 bytes, `EstadoCamara`, `AcumuladorNodos`, `EntradaVisible`...) y la declaración única de cada variable `D_` y de cada rutina que usan dos o más archivos. |
| `include/arranque.h` | `EstadoPrincipal` (0x80010000..0x8001013F) con el bloque `Mando` y el banco de 256 registros de 8 bits. |
| `include/eventos.h` | Registro de acción del intérprete de eventos; incluye `arranque.h` y `globales.h`. |
| `include/objetos.h` | Pozos de objetos y de ayudantes (`NodoLista`, `Ayuda`, `EntradaId`, `EntradaPunto`), sus variables y los prototipos de la reserva, las listas y el dibujo de la escena. |
| `include/motor.h` | Tipos del movimiento y de la animación (`Movimiento`, `TrabajoMov`, `NodoSecuencia`, `ProyeccionSprite`) y los prototipos de las rutinas del motor. |
| `include/geometria.h` | Colisión y volúmenes: `ZonaColision`, `ResultadoBaldosa`, las áreas de consulta y las macros vectoriales. |
| `include/menus.h` | Dibujo de escena y polígonos: `ModeloDibujo`, `VistaDibujo`, `EstadoDibujo` y las primitivas. |
| `include/cargador.h` | Tabla de sectores, registros por archivo, contenedor cargado y contexto del descompresor. |
| `asm/boot.s`, `asm/libs.s` | Ensamblador que no se descompila en esta fase: arranque del SDK y librerías Sony. |
| `asm/nonmatchings/<archivo>/<función>.s` | Ensamblador original de cada función que sigue pendiente, con el `rodata` que usa si su archivo tiene subsegmento `.rodata`. Lo incluye `INCLUDE_ASM`. |
| `asm/matchings/<archivo>/<función>.s` | Ensamblador original de las funciones que ya están en C. Es el objetivo de `diff`. |
| `asm/data/` | Datos, cadenas, tablas de saltos y zona de ceros (`data`, `rodata`, `bss`), en trozos con el nombre del archivo que los posee. |
| `build/simbolos_entrada.txt` | Lo genera `split`; sale vacío mientras `config/symbols.txt` ya define la función de entrada (`func_80014A08`), y solo la declara si esa tabla no la tiene. |

`asm/`, `build/`, `expected/` y `toolchain/` están ignorados por git; se regeneran con `split` y
`build`. `src/` e `include/` sí se versionan.

El código del juego (`0x80014AC4..0x80045DA0`) está repartido en 25 archivos por subsistema. Cada
corte cae en el inicio de una función y figura en `docs/ARCHIVOS_ORIGEN.md`; el nombre del
subsistema es el del archivo sin el sufijo numérico y es la unidad de reparto de la traducción:

| Archivo | Desde | Hasta (exclusivo) | Funciones | Bytes |
|---|---|---|---:|---:|
| `src/tarjeta_de_memoria.c` | `0x80014AC4` | `0x80015EC0` | 10 | 5116 |
| `src/arranque_y_bucle_principal_2.c` | `0x80015EC0` | `0x80016C0C` | 10 | 3404 |
| `src/graficos_y_gte.c` | `0x80016C0C` | `0x80019364` | 9 | 10072 |
| `src/colision_y_terreno.c` | `0x80019364` | `0x8001C424` | 4 | 12480 |
| `src/movimiento_y_objetos_de_escena.c` | `0x8001C424` | `0x8001CC68` | 4 | 2116 |
| `src/movimiento_y_objetos_de_escena_2.c` | `0x8001CC68` | `0x8001E528` | 15 | 6336 |
| `src/movimiento_y_objetos_de_escena_3.c` | `0x8001E528` | `0x80020B90` | 8 | 9832 |
| `src/logica_de_niveles.c` | `0x80020B90` | `0x80025938` | 1 | 19880 |
| `src/logica_de_niveles_2.c` | `0x80025938` | `0x80026118` | 3 | 2016 |
| `src/manejadores_por_tabla.c` | `0x80026118` | `0x80026298` | 12 | 384 |
| `src/logica_de_niveles_3.c` | `0x80026298` | `0x8002F9F8` | 17 | 38752 |
| `src/interprete_de_eventos.c` | `0x8002F9F8` | `0x80032874` | 196 | 11900 |
| `src/camara_y_bucle_logico.c` | `0x80032874` | `0x80036164` | 11 | 14576 |
| `src/gestion_y_dibujo_de_objetos.c` | `0x80036164` | `0x80037048` | 15 | 3812 |
| `src/gestion_y_dibujo_de_objetos_2.c` | `0x80037048` | `0x800399C8` | 20 | 10604 |
| `src/gestion_y_dibujo_de_objetos_3.c` | `0x800399C8` | `0x80039BFC` | 1 | 564 |
| `src/gestion_y_dibujo_de_objetos_4.c` | `0x80039BFC` | `0x8003AA38` | 6 | 3644 |
| `src/menus_e_interfaz.c` | `0x8003AA38` | `0x8003DF84` | 27 | 13644 |
| `src/audio_xa_y_spu.c` | `0x8003DF84` | `0x8003FFA0` | 37 | 8220 |
| `src/entrada_de_mando.c` | `0x8003FFA0` | `0x80040A80` | 6 | 2784 |
| `src/graficos_y_gte_10.c` | `0x80040A80` | `0x80040EB4` | 6 | 1076 |
| `src/cargador_de_niveles_y_cd.c` | `0x80040EB4` | `0x800443CC` | 9 | 13592 |
| `src/graficos_y_gte_12.c` | `0x800443CC` | `0x80044664` | 4 | 664 |
| `src/cargador_de_niveles_y_cd_2.c` | `0x80044664` | `0x80044904` | 2 | 672 |
| `src/inicializacion_de_motor.c` | `0x80044904` | `0x80045DA0` | 16 | 5276 |

Las fronteras están en `config/splat.yaml` como subsegmentos de tipo `c`. El orden de las
funciones dentro de cada `.c` es el orden de direcciones: el enlazador coloca el código en el
orden en que el compilador lo emite, así que nunca se reordenan.

### Cortes de la propuesta que no se aplicaron

La propuesta tiene 36 filas (23 de confianza alta y 13 media). Se aplican todas las de confianza
alta salvo la primera, y de las medias las que dejan archivos de tamaño útil:

| Corte | Confianza | Razón |
|---|---|---|
| `arranque_y_bucle_principal` (`0x80014A08`) | alta | Son 188 bytes de código de arranque escrito a mano (`start`) y un bloque de cuatro palabras; no es traducible a C y se queda en `asm/boot.s`. |
| `graficos_y_gte_2` a `graficos_y_gte_9` (`0x80016ED0..0x80019180`) | media | Ocho rutinas de cálculo de matrices que no se llaman entre sí, cada una en su propio archivo de una función (304 a 4.588 bytes). Se funden con `graficos_y_gte` en un solo archivo de nueve funciones independientes, como sugiere la propia propuesta. |
| `logica_de_niveles_4` (`0x8002F968`) | media | Dejaba un archivo de 144 bytes con tres funciones; se funde con `logica_de_niveles_3`. |
| `graficos_y_gte_11` (`0x80040D98`) | media | Dejaba un archivo de 284 bytes; se funde con `graficos_y_gte_10`. |

Los demás cortes de confianza media (`movimiento_y_objetos_de_escena_2` y `_3`,
`logica_de_niveles_2`) se aplicaron: la compilación y `verify` no se rompen y los archivos miden
entre 2 y 10 KB. La numeración de `graficos_y_gte_10` y `graficos_y_gte_12` conserva la de la
propuesta para que los nombres coincidan con ella.

### Cómo se genera `src/`

`split` ejecuta el particionador. Si `src/<archivo>.c` no existe, lo crea con una línea
`INCLUDE_ASM` por función; si ya existe, **no lo toca** y solo escribe el ensamblador de las
funciones que siguen en `INCLUDE_ASM` (en `asm/nonmatchings/`) y el de las ya descompiladas (en
`asm/matchings/`). Por eso `split` es idempotente y se puede repetir sin perder trabajo.

Para mover una frontera entre dos archivos hay que cambiar el desplazamiento en `splat.yaml` y
trasladar a mano las líneas de las funciones afectadas de un `.c` al otro. Cuando la partición
cambia mucho (renombrar o repartir archivos), lo seguro es regenerar: mover `src/` aparte,
`clean`, `split` (crea los `.c` con una línea `INCLUDE_ASM` por función con las rutas nuevas),
reinsertar los bloques de C escritos en el lugar de su `INCLUDE_ASM` y repetir `split` para que
las funciones ya en C pasen a `asm/matchings/`. No se editan a mano las rutas de `INCLUDE_ASM`.

## Datos y rodata por archivo

El script del enlazador que genera el particionador tiene el orden fijo texto, datos,
datos de solo lectura y ceros, y coloca las secciones de cada objeto C en la posición de su
subsegmento. Por eso un archivo posee sus datos declarando subsegmentos **con su mismo nombre**:

- **`data` (ensamblador de datos).** El tramo `0x8005DEA0..0x8005F000` contiene las tablas
  privadas de cada archivo (secuencias de teclas, tablas de punteros a rutinas, tablas de
  sectores). Está dividido en trozos `[desplazamiento, data, <archivo>]`; cada uno genera
  `asm/data/<archivo>.data.s` y se enlaza en su sitio. La tabla de punteros `0x8005E35C`, que
  lee el despachador de `camara_y_bucle_logico` y varios subsistemas más, tiene su propio trozo
  `tablas_compartidas`. Estas tablas son datos inicializados (`.data`), no rodata: el compilador
  las emite en `.data` y el enlazador las coloca en el grupo de datos. Para que un archivo C
  posea un tramo, se divide el trozo de ensamblador y se declara `[desplazamiento, .data, <archivo>]`
  (con punto) con el nombre del `c`; el trozo de ensamblador anterior **debe llamarse distinto**
  (`tarjeta_de_memoria_tablas`), porque el particionador resuelve los trozos por nombre y dos
  entradas con el mismo nombre se pisan. Primer tramo migrado: la cadena del archivo de partida de
  la tarjeta de memoria (`0x8005E04C`, 24 bytes), que vive en `src/tarjeta_de_memoria.c` como
  `char D_8005E04C[] = "bu00:BASLUS-00838 BBLIT";`. El símbolo interior `D_8005E051` (otras
  funciones leen la cadena desde su sexto byte) queda como símbolo absoluto del enlazador.
- **`.rodata` con punto (rodata migrado).** Para las tablas de salto de un `switch` y las
  cadenas del tramo `0x80067E64..0x800683B8`, un subsegmento `[desplazamiento, .rodata, <archivo>]`
  hace que el particionador *migre* cada símbolo de solo lectura al `.s` de la función que lo usa
  (sección `.rodata` dentro del propio `asm/nonmatchings/<archivo>/<función>.s`) y que el
  enlazador recoja `build/src/<archivo>.c.o(.rodata)` en la posición correcta. Sin el punto
  (`rodata`) el particionador genera un archivo ensamblador aparte y los símbolos se duplican.
  Archivos con rodata migrado: `camara_y_bucle_logico` (`0x80067E64`, tabla de `func_80035244`),
  `gestion_y_dibujo_de_objetos` (`0x80067E80`, tabla de `func_8003690C`) y `menus_e_interfaz`
  (`0x80067E9C`, tabla de `func_8003C1C8`), `audio_xa_y_spu` (`0x80067EF0`) y
  `cargador_de_niveles_y_cd` (`0x80067F18`). El resto del rodata sigue en trozos de
  ensamblador (`rodata`, `rodata_constante`, `rodata_resto`).
- **Símbolos de solo lectura sin función propia (`INCLUDE_RODATA`).** Un símbolo que ninguna
  función del archivo referencia directamente (la ruta `\LEVEL5\MERLIN.BZZ;1` y su puntero, las
  cadenas y punteros del cargador) no viaja dentro de un `.s` de función: el particionador lo escribe
  en `asm/nonmatchings/<archivo>/<símbolo>.s` y lo incluye en el `.c`, en orden de direcciones, con
  `INCLUDE_RODATA("asm/nonmatchings/<archivo>", <símbolo>);`. La macro (en `include/macro.h`) abre
  la sección `.rodata`, incluye el `.s` y vuelve a `.text`. Para pasar uno de estos símbolos a C se
  sustituye su línea `INCLUDE_RODATA` por la definición (`const char D_X[] = "...";`) respetando
  el orden y el relleno originales; `verify` delata cualquier desajuste.

Cada objeto C se comprueba al compilarlo: solo puede generar `.text` y las secciones que su
nombre declara en `splat.yaml` (`.rodata` o `.data` si hay subsegmento con punto). Cualquier otra
sección con contenido hace fallar la construcción con el archivo y la sección
(`inicializacion_de_motor.c.o: genera 4 bytes en la seccion inesperada '.data'`).

### Cómo mover una función con `switch`

1. El archivo debe tener el subsegmento `.rodata` con su nombre, en el desplazamiento donde está la
   tabla (ver arriba). Si no lo tiene, añadirlo en `splat.yaml` entre el trozo anterior y el siguiente
   (cada trozo termina donde empieza el siguiente) y regenerar `src/`.
2. Escribir la función con `switch` en C en su sitio. El compilador emite la tabla en `.rdata`
   (que el ensamblador llama `.rodata`) con una entrada por caso; el relleno de casos ausentes lo
   aporta la etiqueta del caso por omisión.
3. `diff <función>` muestra las filas `.rodata+0x..` (una por entrada de la tabla): si todas
   coinciden, la tabla y los destinos de los casos están en el mismo orden y distancia que el original.
4. `build` y `verify`. Una tabla distinta en tamaño desplaza todo lo que sigue y `verify` lo delata.

Resultado con `func_80035244` (siete casos): el C que escribió el desarrollador reproduce la tabla
completa (las siete entradas coinciden en `diff`) pero la función no llega a puntuación 0
(1.510 con `-G0`, 600 con `-G8` y la mejor variante del banco), así que queda como
`NON_MATCHING` (ver `docs/PROGRESO.md`). Las diferencias restantes están en el texto, no en la
sección de datos: la posición del almacén en `0x104($gp)`, las constantes `0x47` y `1`, que el
original carga una vez antes del bucle, y el orden de los incrementos de los punteros.


## Tipos y macros

`include/common.h` define `u8`, `u16`, `u32`, `s8`, `s16`, `s32`, `vu8`, `vu16`, `vu32` y `NULL`
para el R3000 (`char` 8 bits, `short` 16, `int` y `long` 32). El compilador es GCC 2.8.1, es decir
C89 estricto:

- Sin comentarios `//`.
- Sin declaraciones después de sentencias: todas las variables locales al inicio del bloque.
- Sin `stdint.h`, sin `bool`, sin inicializadores designados, sin arreglos de longitud variable.

`INCLUDE_ASM(carpeta, función)` inserta en `.text` el ensamblador original de una función. La
carpeta es una cadena literal relativa a la raíz del repositorio:

```c
INCLUDE_ASM("asm/nonmatchings/tarjeta_de_memoria", func_80014BA0);
```

La macro preprocesa a un `__asm__` de nivel superior que ensambla el `.s` con `.set noat` y
`.set noreorder` (el ensamblador original usa `$at` y rellena a mano los huecos de salto) y
después restaura los valores que espera el compilador. Las macros de etiquetas (`glabel`,
`endlabel`, `nonmatching`) se cargan una sola vez al incluir `common.h`; incluir el archivo de
macros dos veces es un error del ensamblador.

## Cómo mover una función de ensamblador a C

1. **Elegir** la función y localizar su archivo: `asm/nonmatchings/<archivo>/<función>.s` y la
   línea `INCLUDE_ASM` en `src/<archivo>.c`.
2. **Borrador** (opcional):
   `python toolchain/m2c/m2c.py --target mipsel-gcc-c asm/nonmatchings/<archivo>/<función>.s`.
   El resultado es un punto de partida, casi nunca el C original.
3. **Escribir** la función en `src/<archivo>.c` **en el lugar de su `INCLUDE_ASM`** (mismo orden
   que las direcciones). Mientras no coincida, envolverla así:

   ```c
   #ifdef NON_MATCHING
   /* Pendiente: puntuacion 120 con la configuracion versionada (g = 8 del archivo). Reparto de registros. */
   s32 func_80030D60(void* a0, Rango* a1)
   {
       /* mejor intento */
   }
   #else
   INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030D60);
   #endif
   ```

   La construcción normal no define `NON_MATCHING`, así que sigue usando el ensamblador y el
   ejecutable no cambia. `diff` sí lo define y compara el intento.

   **Posición exacta del comentario de pendientes.** Lo primero que hay debajo de cada
   `#ifdef NON_MATCHING` es un comentario (`/* ... */` o `//`) cuyo texto empieza por
   `Pendiente: puntuacion N`, con `N` la puntuación de `diff`, seguido del motivo técnico en una frase.
   Es el comentario que `progreso` copia a `docs/PROGRESO.md` como motivo del intento. Un comentario
   encima del `#ifdef`, después del código, o que empiece por otro texto no cuenta, y `progreso` termina
   con error (`N funcion(es) NON_MATCHING sin la linea 'Pendiente: puntuacion N'...`) con el archivo, la
   línea del `#ifdef` y la función de cada bloque afectado, sin escribir `docs/PROGRESO.md`.
4. **Comparar**: `python tools/build.py diff func_80030D60`. La puntuación 0 y el código de
   salida 0 indican que las instrucciones y los símbolos coinciden. Cualquier otra puntuación
   termina con código 1 y muestra las dos columnas (objetivo y compilado) con una marca en las
   filas distintas (`r` registro, `i` inmediato, `|` instrucción, `<` y `>` sobrante).
5. **Cerrar la función**: cuando `diff` da 0, quitar `#ifdef NON_MATCHING`, `#else`, el
   `INCLUDE_ASM` y `#endif`, dejando solo el C. Después de esto ya no existe
   `asm/nonmatchings/<archivo>/<función>.s`; `split` escribe el original en `asm/matchings/`.
6. **Verificar**: `python tools/build.py build` y `python tools/build.py verify` deben imprimir
   `OK`. Si no, la función cambió algo más (tamaño, relleno, símbolos) que `diff` no ve.
7. **Registrar**: `python tools/build.py progreso`.

### Reglas de escritura para que el particionador vea la función

El particionador decide qué funciones ya están en C leyendo el texto de `src/*.c` con una
expresión regular. Si no reconoce una definición, sigue declarando el símbolo como indefinido y el
enlazador falla con un símbolo duplicado. Por eso:

- El tipo de retorno es **una sola palabra**, con el `*` pegado al tipo: `Ranura* func_80036204(...)`,
  no `struct Ranura *func_80036204(...)`. Usar `typedef` para las estructuras.
- Una función auxiliar (`static`) que solo usa un intento `NON_MATCHING` va **fuera** del bloque
  condicional; dentro, `progreso` la tomaría por una función sin `INCLUDE_ASM`.
- `progreso` y `diff` rechazan con un mensaje claro lo que el particionador no reconocería.

## Declarar datos externos

Los datos del juego se nombran `D_80XXXXXX` y viven en el ensamblador de `asm/data/` o fuera de la
imagen (hardware y variables de RAM por debajo de `0x80014A00`). Mientras no se identifiquen, se
declaran en el propio `.c` con el tipo mínimo que haga coincidir el código:

```c
extern u8 D_8006AA70[];          /* tabla de bytes */
extern u32 D_80069698;           /* palabra */
```

- Un arreglo sin tamaño (`u8 D_X[]`) genera acceso por dirección base más índice, que es lo que
  suele tener el original; un escalar genera una carga directa.
- Dos variables contiguas que el original lee con un único `lui` (misma parte alta) deben
  declararse como miembros de una misma estructura o arreglo; como variables externas distintas
  GCC emite un `lui` por cada una (es la diferencia de `func_8002F990`).
- Un símbolo que usan dos o más archivos se declara una sola vez, en `include/globales.h` o en la
  cabecera de su subsistema, con el ancho y el signo que fija el ensamblador (`lb`, `lbu`, `lh`,
  `lhu`, `lw`): dos declaraciones con tipos distintos no las detecta el enlazador y cada una cambia
  el código del archivo que la ve. Si una rutina lee el dato con otro ancho, se deja un cast local
  con la instrucción que lo exige (`D_8006955E` es `vu8` y `func_80044854` lo lee como `u16`, porque
  el original usa `lhu`). Un campo de una estructura compartida que se lee con dos signos se resuelve
  con un cast local o con una unión con nombre (`GiroObjeto` en `Objeto`).
- Una estructura describe una sola vez cada región de memoria: `Objeto` es el objeto de escena
  completo (la reserva, la lógica, el volumen y el dibujo), `EstadoPrincipal` el estado de
  `0x80010000` y `EstadoCamara` el de `D_8006D928`. Las variables sueltas `D_8001xxxx` que
  conviven con `EstadoPrincipal` son los accesos con la forma simbólica (un `lui` por acceso) que el
  original usa en algunas rutinas; no se acceden por la estructura porque eso comparte el `lui`.
- Una rutina compartida se prototipa en la cabecera de su subsistema con los tipos de su
  definición. Un parámetro estrecho (`u8`, `s16`) hace que cada llamador recorte el argumento; si el
  original pasa el valor sin recortar y la rutina lo recorta dentro, el parámetro es `s32` y el
  recorte un cast (`func_8002F990`).
- No hay que definir el símbolo: el enlazador lo resuelve contra `asm/data/` o contra
  `build/undefined_syms_auto.txt`. Definir un dato en C solo es posible cuando también se migra su
  zona (ver trampas).
  Excepción: una variable pequeña direccionada por `$gp` se define (sin `extern`) en el archivo que la
  usa; ver «Datos pequeños y `$gp`».
- Cuando se identifique el propósito, se renombra en `config/symbols.txt` (única fuente de
  nombres) y se regenera con `split`.

## Opciones de compilación por archivo

`config/opciones_compilacion.toml` declara, por archivo `src/<nombre>.c`, opciones que `build`,
`diff` y `probar` aplican por igual (una sola función las lee, así que las tres órdenes compilan
cada archivo con exactamente las mismas banderas). Tiene tres tablas:

```toml
[archivos.interprete_de_eventos]   # umbral de datos pequeños (-G) de ese archivo, 0 a 64
g = 8

[enlace]                           # valor de $gp que fija el arranque del juego
gp = 0x80069320

[datos_pequenos]                   # variables que el código direcciona con desplazamiento($gp)
D_800694A8 = 0x800694A8
```

Los archivos que no figuran usan `-G0`. Hoy compilan con `g = 8` los ocho archivos cuyo original
usa datos pequeños o almacenes simbólicos: `camara_y_bucle_logico`, `arranque_y_bucle_principal_2`,
`tarjeta_de_memoria`, `entrada_de_mando`, `graficos_y_gte`, `graficos_y_gte_10`, `graficos_y_gte_12` e
`interprete_de_eventos`. La regla para añadir uno es empírica: una función que sale con puntuación
distinta de cero en `-G0` y 0 con `-G8` demuestra que el original usó datos pequeños.

Con un `-G` mayor que cero el compilador emite las variables externas pequeñas en forma
simbólica (`sh $2,D_80069662`, que el ensamblador expande con `lui $at`), como el original, en
lugar de `lui` más desplazamiento. Efecto medido en `func_80035244` (archivo
`camara_y_bucle_logico`): 1.510 con `-G0`, 1.025 con `-G8` y 600 con `-G8` y la mejor variante del
banco. La coincidencia exacta requiere además las constantes cargadas antes del bucle y el almacén
fuera del hueco de retardo; el motivo queda en `docs/PROGRESO.md`.

## Datos pequeños y `$gp`

El arranque del juego fija `$gp` en `0x80069320` (`lui gp,0x8007 ; addiu gp,gp,-0x6CE0`). Con datos
pequeños (`-G8`) el código accede a las variables de unos pocos bytes con `desplazamiento($gp)` en
lugar de `lui` más desplazamiento. El soporte tiene cuatro piezas que se apoyan entre sí.

### Orden de emisión de GCC y la macro `INCLUDE_ASM`

Con `-G0` `CC1PSX.EXE` emite las funciones C en el mismo orden en que aparecen en el fuente, entre los
bloques `__asm__` de las funciones aún en ensamblador. Con `-G` mayor que cero emite primero todas las
directivas `.globl` y deja **todos los cuerpos de funciones C al final**, después de cada `__asm__` de
nivel superior: en un archivo mixto las funciones C acaban fuera de su posición y el ejecutable ya no
coincide. La solución es la que documenta `maspsx` para este caso: `INCLUDE_ASM` (`include/macro.h`)
envuelve el `__asm__` en una función ficticia `__maspsx_include_asm_hack_<NOMBRE>` cuyas líneas llevan la
marca `# maspsx-keep`; `maspsx` comenta todo lo demás del envoltorio y deja el ensamblador en su sitio,
de modo que el orden del fuente vuelve a ser el de salida con cualquier `-G`. Se comprobó con
`interprete_de_eventos` (`g = 8`), que mezcla funciones en C, intentos `NON_MATCHING` e `INCLUDE_ASM` y
reproduce el ejecutable con `verify` en OK.

Ejemplo sintético, compilado de verdad con el compilador del proyecto: dos funciones C con un
`INCLUDE_ASM` entre ellas.

```c
s32 func_primera_c(s32 x) { return x + D_80069338; }
INCLUDE_ASM("asm_ejemplo", func_en_asm);
s32 func_segunda_c(s32 x) { return x * 2; }
```

Orden en que `CC1PSX.EXE` emite las etiquetas, con la macro anterior (un `__asm__` suelto, sin función
de relleno) y con la actual, y orden final de las funciones en `.text` del objeto:

| Macro | `-G` | Salida de `cc1` (abreviada) | Orden en `.text` |
|---|---|---|---|
| sin relleno | 0 | `.globl primera`, `primera:`, `[asm func_en_asm]`, `.globl segunda`, `segunda:` | primera, en_asm, segunda (correcto) |
| sin relleno | 8 | `.globl primera`, `[asm func_en_asm]`, `.globl segunda`, `primera:`, `segunda:` | en_asm, primera, segunda (**roto**) |
| con relleno | 0 | `.globl primera`, `primera:`, `.globl hack_en_asm`, `hack_en_asm:`, `[asm func_en_asm]`, `.globl segunda`, `segunda:` | primera, en_asm, segunda (correcto) |
| con relleno | 8 | `.globl primera`, `.globl hack_en_asm`, `.globl segunda`, `primera:`, `hack_en_asm:`, `[asm func_en_asm]`, `segunda:` | primera, en_asm, segunda (correcto) |

Con `-G8` y sin relleno todos los `.globl` salen primero y el `__asm__` de nivel superior cae antes
de cualquier cuerpo de función C: el ensamblador original queda al principio del archivo. Con el
relleno, el `__asm__` pasa a ser el cuerpo de una función más y sigue el orden de las demás. Para repetir la
medición basta compilar un archivo como el del ejemplo con `-G0` y con `-G8` y comparar el orden de las
etiquetas y de los cuerpos en la salida de `cc1`; la tabla resume ese resultado.

### Declarar una variable pequeña

`maspsx` solo reescribe a `$gp` los símbolos que el **propio archivo define** (en `.sbss`, `.sdata` o
como común); un símbolo `extern` queda como `lui`. Por eso:

1. Se declara la variable en el archivo que la usa como **definición tentativa, sin `extern`**:
   `u8 D_800694A8;`. Con `--use-comm-section` (que `build` pasa a `maspsx`) queda como símbolo común y
   la reubicación `GPREL16` apunta al símbolo mismo.
2. Se añade `D_800694A8 = 0x800694A8` a `[datos_pequenos]`. `build` escribe `build/gp.ld` con
   `_gp = 0x80069320;` y una asignación por símbolo, y lo pasa al enlazador después del script
   principal: la asignación sustituye al símbolo común y el desplazamiento resultante es el exacto del
   original (`lw v0,0x188(gp)`). Son símbolos absolutos: no mueven ningún byte.
3. Se define en cada archivo que lo accede por `$gp`; los que lo acceden por `lui` lo ven `extern`, con la
   declaración única de `include/globales.h`. `D_800694A8` se define en `cargador_de_niveles_y_cd`,
   `graficos_y_gte_10` y `graficos_y_gte_12`, y `D_800694A4` y `D_80069488` en los dos primeros, porque
   las funciones de cada archivo los direccionan por `$gp` y ya coinciden: el enlazador funde las
   definiciones comunes en un solo símbolo, y declararlos `extern` en cabecera empeora cuatro funciones.
   `D_800693B8` (`s16`, `sh`/`lhu` con `0x98($gp)`) se define en `logica_de_niveles` y en
   `movimiento_y_objetos_de_escena_2` por el mismo motivo. Esa es la lista completa de datos pequeños definidos
   en más de un archivo; los demás (`D_800693F0`, `D_800693F6`, `D_800693F8`, `D_80069402`, `D_80069416`,
   `D_8006947C`, `D_80069480`, `D_80069490` y `D_8006949C`) se definen en un solo archivo.

Datos pequeños de `tarjeta_de_memoria` (`g = 8`), todos definidos solo en ese archivo y usados por
`func_80015E94`, que los direcciona por `$gp` (el original usa `sb zero,0x3c($gp)`,
`addiu a1,gp,0x40` y `addiu a2,gp,0x48`; `0x80069320` más cada desplazamiento da la dirección):

| Símbolo | Dirección | Tipo | Evidencia en `func_80015E94` |
|---|---|---|---|
| `D_8006935C` | `0x8006935C` | `u8` | `sb zero,0x3c($gp)`: bandera de operación pendiente, a cero antes de `MemCardSync` |
| `D_80069360` | `0x80069360` | `s32` | `addiu a1,gp,0x40`: segundo argumento de `MemCardSync`, pasado por dirección |
| `D_80069368` | `0x80069368` | `s32` | `addiu a2,gp,0x48`: tercer argumento de `MemCardSync`, pasado por dirección |

Cuando `config/symbols.txt` declare esos datos pequeños se retirarán de `[datos_pequenos]` (hoy figuran
allí porque el ejecutable original no los nombra).

### Detectar un acceso por `$gp`

En el ensamblador de la función (`asm/nonmatchings/<archivo>/<función>.s`) se busca
`desplazamiento($gp)`: la dirección de la variable es `0x80069320` más el desplazamiento con signo
(`0x188($gp)` es `0x800694A8`). El mnemónico da el tamaño (`lb`/`sb` un byte, `lh`/`sh` dos, `lw`/`sw`
cuatro). En el juego hay 63 desplazamientos distintos. Si el original accede así a una variable, ese
archivo se compiló con datos pequeños y se declara con `g = 8`. La variable de registro
`register u8* base_gp __asm__("$28");` (`include/globales.h`) sigue siendo válida para acceder por
desplazamiento a una zona sin nombre, pero en algunos casos reserva el marco antes de cargar la bandera
y el orden de las instrucciones ya no es el del original: una variable definida en el archivo es
preferible.

### Cuando `maspsx` no reescribe el símbolo

- **Variable externa que debía ser pequeña**: el código sale con `lui` más desplazamiento. Se define en el
  archivo (pasos 1 y 2) en lugar de declararla `extern`.
- **`addiu rX,$gp,desplazamiento` (dirección de una variable pequeña)**: ASPSX 2.79 no lo emite; con la 2.80 fijada (`gp_allow_la` en `maspsx`) sí. Hace falta
  ASPSX 2.80 o posterior (`gp_allow_la` en `maspsx`). Las tres funciones de `tarjeta_de_memoria` que lo
  necesitan (`func_80014AC4`, `func_80015E94` y `func_800156F4`) se quedan en `NON_MATCHING`.

### Comparación por bytes (`diff` y `probar`)

`asm-differ` compara instrucción por instrucción con los símbolos como los escribe el objeto, de modo que
un C que accede a `0x800694A8` por `$gp` y el original pueden diferir solo en la **forma** (inmediato
numérico frente a símbolo) aunque tras enlazar produzcan los mismos bytes. Cuando la puntuación no es 0,
`diff` y `probar` enlazan el candidato y el original por separado en la dirección de la función
(`config/symbols.txt`), resolviendo los símbolos contra `build/SLUS_008.elf` de la última construcción
correcta, y comparan los bytes. Si coinciden, la función **puntúa 0**, igual que una que coincide instrucción
por instrucción: la forma de una referencia (símbolo o número) no es una diferencia. `diff` termina con código 0 y
deja el número de referencias en forma numérica y la puntuación que dio `asm-differ` como nota aparte, antes
del veredicto:

```text
nota: 14 referencias en forma numerica (asm-differ puntua 70)
func_800400C0 (src/entrada_de_mando.c): puntuacion 0 (coincide en bytes)
```

Una función con coincidencia exacta imprime solo `func_8003E034 (src/audio_xa_y_spu.c): puntuacion 0`. La nota es
información para quien quiera escribir esas referencias en forma simbólica; no cambia el estado de la función. Una
función «cerrada» (definida en C en la construcción normal) cuenta igual en `progreso` y en `docs/PROGRESO.md` haya
coincidido de una forma o de otra: esos documentos no distinguen entre las dos. `probar` marca la variante con
`(bytes iguales)` y la ordena como coincidente. Sin `build/SLUS_008.elf` o sin la dirección en la
tabla de símbolos no se hace la comparación por bytes y vale la puntuación de `asm-differ`.

## Banco de variantes (`probar`)

`python tools/build.py probar <función> <carpeta>` compila cada `.c` de la carpeta como una
variante completa de la función (con su `#include "common.h"`, tipos y `extern`), con las
mismas opciones que el archivo donde vive la función, la compara con `asm-differ` contra el
ensamblador original y muestra una tabla ordenada de menor a mayor puntuación:

```text
variante  puntuacion
i.c       690
d.c       1025
rota.c    error: CC1PSX.EXE: termino con codigo 33
```

Una variante que no compila aparece con su error y no detiene a las demás.
El código de salida es 0 solo si la mejor tiene puntuación 0. Límites: 200 variantes por carpeta, 256
KiB cada una, nombres simples (`[A-Za-z0-9_.-]`). Todo el trabajo queda en `build/diff/`; no escribe
en `src/`. Se usa antes de `diff`: se prueban muchas formulaciones, se copia la mejor a `src/` bajo
`NON_MATCHING` y se sigue con `diff`.

Una variante que no define la función pedida (define otra, o está vacía o solo la declara) también es una fila de
error: tras compilarla se consulta la tabla de símbolos del objeto y, si `.text` no trae la función con tamaño
mayor que cero, la fila dice `error: la variante no define <función>`. Esa fila no lleva puntuación, no se envía a
`asm-differ` (que puntuaría el hueco contra el original con un número alto pero válido) y queda al final de la
tabla, igual que una que no compila:

```text
variante  puntuacion
ok.c      70 (bytes iguales)
otra.c    error: la variante no define func_800400C0
```

## Invalidación de la salida

Una construcción elimina antes de empezar el ejecutable (`build/SLUS_008.38`), el binario plano,
el ELF y el mapa de la anterior. Si la construcción falla a mitad (por ejemplo por una sección no
declarada) no queda ningún ejecutable y `verify` imprime `FAIL el ejecutable reconstruido no
existe` con código 1. Antes de este cambio sobrevivía el ejecutable anterior y `verify` lo aprobaba
aunque ya no correspondiera al código. `split` y `clean` también lo eliminan.

## Comandos del GTE

Las macros de comando de `psyq/INLINE_C.H` (`gte_rtv0`, `gte_rtpt`...) emiten `nop; nop; .word
0x....`, donde la palabra es una ficha que el programa DMPSX del SDK sustituye por la
instrucción real. Aquí el flujo es `cc1`, `maspsx` y `as`, sin DMPSX, y la ficha llega sin sustituir
al objeto (`0x0000013f` en lugar de `0x4a486012`). Se evaluó integrar `DMPSX.EXE`: espera un
objeto de ASPSX (`DMPSX object-file [-b][-o output-file]`) y rechaza el objeto ELF de GNU `as`
(`DMPSX: Illegal input file format`), así que no es aplicable sin cambiar todo el ensamblado.

Decisión: `include/gte.h` redefine los 64 comandos que tienen equivalente como
`__asm__ volatile ("nop; nop; <mnemónico>")`, con el mnemónico de `asm/include/gte_macros.inc`
(que `macro.h` carga), y produce la misma palabra que el ejecutable. Se incluye **en lugar de**
`psyq/INLINE_C.H` (lo incluye él mismo, con `TYPES.H` y `LIBGTE.H`). `gte_rt` no tiene mnemónico y
su uso es un error de compilación a propósito. Las macros de carga y lectura de registros
(`gte_ldv0`, `gte_stlvnl`, `gte_SetRotMatrix`...) son ensamblador directo y se usan tal cual:
`func_8001CE64` coincide con puntuación 0.

## Medir el progreso

`python tools/build.py progreso` escribe `docs/PROGRESO.md` (legible) y `build/progreso.json`
(para otras herramientas, claves en camelCase). Los conteos se derivan del código real:

- Una función está **en C** si el archivo la define en la construcción normal y no tiene
  `INCLUDE_ASM`.
- Está **`NON_MATCHING`** si su definición está bajo `#ifdef NON_MATCHING` y la rama normal usa
  `INCLUDE_ASM`.
- Los bytes salen del tamaño declarado en `config/symbols.txt`.
- Intentos pendientes hoy (`docs/PROGRESO.md` los lista con su motivo): `func_8002F990` (puntuación 350) y
  `func_80035244` (puntuación 600 con `-G8`), entre otros: la lista completa está en
  `docs/PROGRESO.md`.
- Control de coherencia: los `glabel` de `asm/` más las funciones en C deben sumar las funciones
  de la tabla; si no, `progreso` termina con error y hay que ejecutar `split`.
- Guardia de pendientes: todo bloque `#ifdef NON_MATCHING` debe llevar la línea `Pendiente: puntuacion N`
  bajo el `#ifdef` (ver «Cómo mover una función de ensamblador a C»); si falta, `progreso` termina con error.
- **Rutinas manuscritas.** Una función que se queda en `INCLUDE_ASM` porque el original es una rutina
  escrita a mano (sin `addiu sp`, temporales fijos, marca `Handwritten` del particionador) lleva encima,
  sin línea en blanco de por medio, un comentario que dice «rutina escrita a mano en el original» (también
  vale «Rutina de GTE escrita a mano en el original»). `progreso` las lista aparte, con su tamaño, en la
  categoría «Rutinas manuscritas» de `docs/PROGRESO.md` (y en `manuscritas` de `build/progreso.json`); no
  cuentan como funciones en C. Además avisa (por la salida de errores, sin cambiar el código de salida y en
  la sección «`INCLUDE_ASM` sin comentario» del documento) de cada `INCLUDE_ASM` sin ningún comentario
  encima en un archivo que ya tiene funciones en C: o es una rutina manuscrita sin marcar o falta explicar
  por qué sigue en ensamblador. Los `INCLUDE_ASM` de la rama `#else` de un bloque `NON_MATCHING` son intentos
  pendientes y no se clasifican.

Las funciones triviales vacías (`jr ra; nop`) también entran como `INCLUDE_ASM`: pasarlas a C es
una decisión del desarrollador, así el progreso solo cuenta lo que alguien escribió.

## Qué hace cada orden

| Orden | Efecto |
|---|---|
| `split` | Copia el original a `expected/`, ejecuta el particionador y genera `asm/`, `src/` (los `.c` que falten) y el script del enlazador. No toca `asm/overlay/`. |
| `build` | Para cada objeto del script del enlazador: ensambla el `.s` o compila el `.c` (preprocesador, `CC1PSX.EXE -O2 -G<g>`, `maspsx --aspsx-version=2.80`, `as`). Enlaza en el orden del script y escribe `build/SLUS_008.38`. Antes de empezar elimina la salida de la construcción anterior (ver «Invalidación de la salida»). |
| `verify` | Compara el SHA-256 con el del original. Imprime `OK` o `FAIL` con el desplazamiento de la primera diferencia; si no existe el ejecutable reconstruido imprime `FAIL ... no existe` y devuelve 1. |
| `diff <función>` | Compila el `.c` que contiene la función con `NON_MATCHING`, ensambla el original y ejecuta `asm-differ`. Código 0 si la puntuación informada es 0: instrucciones iguales o bytes enlazados iguales (en ese caso informa 0 y añade una nota con las referencias en forma numérica y la puntuación de `asm-differ`). Una función que sigue solo en `INCLUDE_ASM` se rechaza: compararla consigo misma daría 0 sin significar nada. |
| `probar <función> <carpeta>` | Compila y puntúa cada variante `.c` de la carpeta contra el original y muestra la tabla ordenada. Código 0 si la mejor coincide (puntuación 0 o bytes iguales). |
| `progreso` | Escribe `docs/PROGRESO.md` y `build/progreso.json`. No necesita el disco ni el toolchain. Termina con error si algún bloque `NON_MATCHING` no lleva la línea `Pendiente: puntuacion N`. |
| `verificar-config` | Avisa de las claves de `[datos_pequenos]` (`config/opciones_compilacion.toml`) cuya dirección ya declara `config/symbols.txt` (mismo nombre, otro nombre u otro tipo). Solo informa; `split` imprime los mismos avisos al terminar. No necesita el disco ni el toolchain. |
| `clean` | Elimina `asm/`, `expected/` y los artefactos propios de `build/`. Conserva `asm/overlay/`, `expected/overlay/`, `build/overlay/`, `build/emulador/` y `build/bblit_prueba.*`, que son de otras herramientas. |

Los objetos intermedios (`.i`, `.s` y `.o` de cada compilación) quedan en `build/src/` y los de
`diff` en `build/diff/`.

## Trampas conocidas

- **Funciones llamadas `.L<direccion>` por el particionador.** Si otra función salta con `j` al inicio de
  una función que `config/symbols.txt` no nombra, `splat` la trata como etiqueta local: el `.s` se llama
  `.L80044904.s` y el esqueleto `.c` lleva `INCLUDE_ASM(..., .L80044904)`, que no compila. `split` las
  renombra a `func_<direccion>` en el archivo, en las directivas, en los saltos que las referencian y en
  los esqueletos de `src/`. Las etiquetas locales de dentro de una función no se tocan.
- **Los esqueletos regenerados no traen los datos que posee el código.** Con `src/` borrado, `split` genera
  los 25 `.c` y todos compilan, pero el enlace falla por los símbolos de los subsegmentos `.data` que
  pertenecen a un archivo C (hoy `D_8005E04C`, de `tarjeta_de_memoria`): el esqueleto no lleva ningún
  `INCLUDE` de ese dato. Por eso `src/` forma parte del repositorio y no se regenera.

- **Datos y tablas de salto que el compilador emite.** `CC1PSX.EXE` deja las constantes, las
  cadenas y las tablas de salto de un `switch` en `.rdata` (que el ensamblador llama `.rodata`)
  y las variables inicializadas en `.data`. Solo se aceptan si el archivo declara el
  subsegmento correspondiente (ver «Datos y rodata por archivo»); si no, la construcción falla
  con el archivo y la sección en lugar de producir un ejecutable con los datos movidos.
- **Datos incrustados en el código.** Hay bloques de datos entre funciones (por ejemplo
  `0x800375F8`, cinco palabras, y los cuatro de `0x80014AB4`). El particionador los emite como
  `dlabel` con `.word`; entran por `INCLUDE_ASM` como cualquier otra pieza y no cuentan como
  función en `progreso`. No se pueden pasar a C.
- **`-G` no es igual para todos los archivos.** El valor por omisión es `-G0`, pero muchas funciones
  del juego usan `desplazamiento($gp)` o almacenes simbólicos, señal de que su archivo original se
  compiló con `-G8`. Ver «Opciones de compilación por archivo» y «Datos pequeños y `$gp`».
- **`CC1PSX.EXE` no preprocesa.** Por eso `#include` y las macros pasan antes por `CPPPSX.EXE`
  con `-Iinclude`. La macro `INCLUDE_ASM` usa `#NAME` y concatenación de cadenas, que el
  preprocesador del SDK soporta.
- **`maspsx` se cuelga si hereda la entrada estándar y exige la ruta absoluta del ensamblador**
  (`--gnu-as-path`). La herramienta lo lanza siempre con la entrada cerrada y con la ruta
  resuelta desde el lock del toolchain.
- **Relleno entre objetos.** El enlazador alinea cada objeto a 16 bytes por omisión y el
  arranque mide 196 bytes; `splat.yaml` fija `subalign: 4` para que los objetos queden
  contiguos como en el original.
- **Símbolos fundidos.** La tabla `config/symbols.txt` separa ya las rutinas hoja que antes
  estaban fundidas en `func_8002F9F8` y `func_80030ECC` (cada una es ahora una función de 0x38
  bytes más sus rutinas) y fusiona `func_800415A0` y `func_80042BB8` en una sola función de
  0x2E2C bytes (evidencia en `docs/GHIDRA.md`). Ya no hace falta ningún archivo de símbolos
  adicional.
- **`asm-differ` y el tamaño de la función.** Con un archivo C entero como objeto, `asm-differ`
  volcaría todo lo que sigue a la función. `diff` lo corta tras tantos `jr $ra` como tiene el
  original (opción `-s` repetida), y genera `diff_settings.py` en `build/diff/` con la ruta de
  `objdump` resuelta en ese momento.
- **`asm-differ` y el límite de líneas.** `asm-differ` solo compara las primeras 1024 instrucciones de
  cada lado (`--max-lines`); lo que pasa de ahí no puntúa. `diff` y `probar` cuentan las instrucciones del
  original de la función (huecos de salto incluidos) y pasan `--max-lines` igual a ese número más 64 de
  margen, nunca menos de 1024. La puntuación cubre, por tanto, la función entera: en las funciones de más
  de 1024 instrucciones sube respecto a la que daba el corte antiguo (más instrucciones comparadas), y la
  cifra anotada en un comentario `Pendiente` con el límite viejo deja de coincidir. Las funciones de 1024
  instrucciones o menos puntúan igual que antes.
- **Aviso de cifra vieja en `Pendiente`.** `diff` deja la puntuación informada en
  `build/diff/<función>.resultado.json`. `progreso` la contrasta con la cifra del comentario `Pendiente` de
  cada `NON_MATCHING` y, si difieren, imprime `aviso:` por la salida de errores (no cambia el código de
  salida). Solo cuenta una medición posterior a la última edición del archivo C; nunca ejecuta `diff`, y sin
  medición (o con una ilegible) no dice nada. La cifra se corrige a mano en el comentario.
- **Diferencias típicas entre el C y el original.** Los nombres de registro y el orden de
  instrucciones dependen de cómo se escriba el C; probar variantes (`while` por `for`, una variable
  intermedia, el tipo de una variable local) antes de concluir que la función no coincide. Los
  símbolos de datos distintos entre el candidato y el objetivo (`D_8001013C` frente a una
  dirección absoluta) suelen indicar que falta agrupar variables en una estructura.
- **Rutas y saltos de línea.** Las rutas con espacios y paréntesis (el
  disco, por ejemplo) son válidas: ningún proceso hijo recibe una cadena de shell. Los archivos
  generados se escriben con salto de línea LF.

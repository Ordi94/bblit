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
| `src/code_<dirección>.c` | Código del juego. Un archivo por tramo de direcciones; el nombre es la dirección de su primera función. |
| `include/common.h` | Tipos de ancho fijo y `NULL`. Todo `.c` empieza con `#include "common.h"`. |
| `include/macro.h` | Macro `INCLUDE_ASM`. Lo incluye `common.h`. |
| `asm/boot.s`, `asm/libs.s` | Ensamblador que no se descompila en esta fase: arranque del SDK y librerías Sony. |
| `asm/nonmatchings/<archivo>/<función>.s` | Ensamblador original de cada función que sigue pendiente. Lo incluye `INCLUDE_ASM`. |
| `asm/matchings/<archivo>/<función>.s` | Ensamblador original de las funciones que ya están en C. Es el objetivo de `diff`. |
| `build/simbolos_entrada.txt` | Lo genera `split`; sale vacío mientras `config/symbols.txt` ya define la función de entrada (`func_80014A08`), y solo la declara si esa tabla no la tiene. |
| `asm/data/` | Datos, cadenas, tablas de saltos y zona de ceros (`data`, `rodata`, `bss`). |
| `config/simbolos_adicionales.txt` | Símbolos de función que `config/symbols.txt` tiene fundidos dentro de otra (ver trampas). |

`asm/`, `build/`, `expected/` y `toolchain/` están ignorados por git; se regeneran con `split` y
`build`. `src/` e `include/` sí se versionan.

El código del juego (`0x80014AC4..0x80045DA0`) está repartido en ocho archivos por rango de
direcciones, hasta que se identifiquen las unidades de compilación originales:

| Archivo | Desde | Hasta (exclusivo) |
|---|---|---|
| `src/code_80014AC4.c` | `0x80014AC4` | `0x8001BF9C` |
| `src/code_8001BF9C.c` | `0x8001BF9C` | `0x80025938` |
| `src/code_80025938.c` | `0x80025938` | `0x8002BA80` |
| `src/code_8002BA80.c` | `0x8002BA80` | `0x80032874` |
| `src/code_80032874.c` | `0x80032874` | `0x80038884` |
| `src/code_80038884.c` | `0x80038884` | `0x8003E680` |
| `src/code_8003E680.c` | `0x8003E680` | `0x80044588` |
| `src/code_80044588.c` | `0x80044588` | `0x80045DA0` |

Las fronteras están en `config/splat.yaml` como subsegmentos de tipo `c`. El orden de las
funciones dentro de cada `.c` es el orden de direcciones: el enlazador coloca el código en el
orden en que el compilador lo emite, así que nunca se reordenan.

### Cómo se genera `src/`

`split` ejecuta el particionador. Si `src/<archivo>.c` no existe, lo crea con una línea
`INCLUDE_ASM` por función; si ya existe, **no lo toca** y solo escribe el ensamblador de las
funciones que siguen en `INCLUDE_ASM` (en `asm/nonmatchings/`) y el de las ya descompiladas (en
`asm/matchings/`). Por eso `split` es idempotente y se puede repetir sin perder trabajo.

Para mover una frontera entre dos archivos hay que cambiar el desplazamiento en `splat.yaml` y
trasladar a mano las líneas de las funciones afectadas de un `.c` al otro.

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
INCLUDE_ASM("asm/nonmatchings/code_80014AC4", func_80014BA0);
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
   s32 func_80030D60(void* a0, Rango* a1)
   {
       /* mejor intento */
   }
   #else
   INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_80030D60);
   #endif
   ```

   La construcción normal no define `NON_MATCHING`, así que sigue usando el ensamblador y el
   ejecutable no cambia. `diff` sí lo define y compara el intento.
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
- No hay que definir el símbolo: el enlazador lo resuelve contra `asm/data/` o contra
  `build/undefined_syms_auto.txt`. Definir un dato en C solo es posible cuando también se migra su
  zona (ver trampas).
- Cuando se identifique el propósito, se renombra en `config/symbols.txt` (única fuente de
  nombres) y se regenera con `split`.

## Medir el progreso

`python tools/build.py progreso` escribe `docs/PROGRESO.md` (legible) y `build/progreso.json`
(para otras herramientas, claves en camelCase). Los conteos se derivan del código real:

- Una función está **en C** si el archivo la define en la construcción normal y no tiene
  `INCLUDE_ASM`.
- Está **`NON_MATCHING`** si su definición está bajo `#ifdef NON_MATCHING` y la rama normal usa
  `INCLUDE_ASM`.
- Los bytes salen del tamaño declarado en `config/symbols.txt` (más `simbolos_adicionales.txt`).
- Control de coherencia: los `glabel` de `asm/` más las funciones en C deben sumar las funciones
  de la tabla; si no, `progreso` termina con error y hay que ejecutar `split`.

Las funciones triviales vacías (`jr ra; nop`) también entran como `INCLUDE_ASM`: pasarlas a C es
una decisión del desarrollador, así el progreso solo cuenta lo que alguien escribió.

## Qué hace cada orden

| Orden | Efecto |
|---|---|
| `split` | Copia el original a `expected/`, ejecuta el particionador y genera `asm/`, `src/` (los `.c` que falten) y el script del enlazador. No toca `asm/overlay/`. |
| `build` | Para cada objeto del script del enlazador: ensambla el `.s` o compila el `.c` (preprocesador, `CC1PSX.EXE -O2 -G0`, `maspsx --aspsx-version=2.79`, `as`). Enlaza en el orden del script y escribe `build/SLUS_008.38`. |
| `verify` | Compara el SHA-256 con el del original. Imprime `OK` o `FAIL` con el desplazamiento de la primera diferencia. |
| `diff <función>` | Compila el `.c` que contiene la función con `NON_MATCHING`, ensambla el original y ejecuta `asm-differ`. Código 0 solo si la puntuación es 0. Una función que sigue solo en `INCLUDE_ASM` se rechaza: compararla consigo misma daría 0 sin significar nada. |
| `progreso` | Escribe `docs/PROGRESO.md` y `build/progreso.json`. No necesita el disco ni el toolchain. |
| `clean` | Elimina `asm/`, `expected/` y los artefactos propios de `build/`. Conserva `asm/overlay/`, `expected/overlay/`, `build/overlay/`, `build/emulador/` y `build/bblit_prueba.*`, que son de otras herramientas. |

Los objetos intermedios (`.i`, `.s` y `.o` de cada compilación) quedan en `build/src/` y los de
`diff` en `build/diff/`.

## Trampas conocidas

- **Datos y tablas de salto que el compilador emite.** `CC1PSX.EXE` deja las constantes, las
  cadenas y las tablas de salto de un `switch` en `.rdata`, y las variables inicializadas en
  `.data`. El script del enlazador coloca esas secciones de cada objeto C antes que las del
  ensamblador de datos, y el original las tiene en otra posición: el ejecutable saldría con
  los datos movidos. La construcción lo detecta y falla con el nombre de la sección
  (`genera N bytes en la seccion '.rodata'`). Para pasar a C una función con `switch` o con
  cadenas hay que migrar también su zona de `rodata`: dividir el subsegmento `rodata` de
  `splat.yaml` por archivo (`[desplazamiento, .rodata, code_XXXX]`), de modo que cada `.c`
  posea sus constantes en el orden original, y relajar la comprobación de
  `compilacion.verificar_solo_texto` para ese archivo. Esa migración está pendiente.
- **Datos incrustados en el código.** Hay bloques de datos entre funciones (por ejemplo
  `0x800375F8`, cinco palabras, y los cuatro de `0x80014AB4`). El particionador los emite como
  `dlabel` con `.word`; entran por `INCLUDE_ASM` como cualquier otra pieza y no cuentan como
  función en `progreso`. No se pueden pasar a C.
- **`-G0` es obligatorio.** La cabecera declara `gp0 = 0` y el código no usa `$gp` para datos
  pequeños; sin `-G0` el compilador emitiría accesos relativos a `$gp`. Ya está fijado en
  `compilacion.OPCIONES_COMPILADOR`.
- **`CC1PSX.EXE` no preprocesa.** Por eso `#include` y las macros pasan antes por `CPPPSX.EXE`
  con `-Iinclude`. La macro `INCLUDE_ASM` usa `#NAME` y concatenación de cadenas, que el
  preprocesador del SDK soporta.
- **`maspsx` se cuelga si hereda la entrada estándar y exige la ruta absoluta del ensamblador**
  (`--gnu-as-path`). La herramienta lo lanza siempre con la entrada cerrada y con la ruta
  resuelta desde el lock del toolchain.
- **Relleno entre objetos.** El enlazador alinea cada objeto a 16 bytes por omisión y el
  arranque mide 196 bytes; `splat.yaml` fija `subalign: 4` para que los objetos queden
  contiguos como en el original.
- **Símbolos fundidos.** `config/symbols.txt` agrupa en `func_8002F9F8` (5.332 bytes) decenas de
  rutinas hoja que solo se llaman por tabla. Mientras la tabla no las separe, las que se quieran
  pasar a C se aíslan en `config/simbolos_adicionales.txt`, que se lee después de
  `symbols.txt`: una línea con la misma dirección reemplaza a la anterior (así se reduce el
  tamaño de `func_8002F9F8`) y las demás particionan el resto. Los tramos `func_8002FA60`,
  `func_8002FB38` y `func_80030DA4` siguen siendo bloques con varias rutinas.
- **`asm-differ` y el tamaño de la función.** Con un archivo C entero como objeto, `asm-differ`
  volcaría todo lo que sigue a la función. `diff` lo corta tras tantos `jr $ra` como tiene el
  original (opción `-s` repetida), y genera `diff_settings.py` en `build/diff/` con la ruta de
  `objdump` resuelta en ese momento.
- **Diferencias típicas entre el C y el original.** Los nombres de registro y el orden de
  instrucciones dependen de cómo se escriba el C; probar variantes (`while` por `for`, una variable
  intermedia, el tipo de una variable local) antes de concluir que la función no coincide. Los
  símbolos de datos distintos entre el candidato y el objetivo (`D_8001013C` frente a una
  dirección absoluta) suelen indicar que falta agrupar variables en una estructura.
- **Rutas y saltos de línea.** Las rutas con espacios y paréntesis (el
  disco, por ejemplo) son válidas: ningún proceso hijo recibe una cadena de shell. Los archivos
  generados se escriben con salto de línea LF.

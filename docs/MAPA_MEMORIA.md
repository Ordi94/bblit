# Mapa de memoria de `SLUS_008.38`

Resumen de como esta organizada la RAM del juego, deducido del analisis con Ghidra (ver
`docs/GHIDRA.md`) y de la lectura del codigo de arranque. Las direcciones de codigo son exactas
(limites de funciones identificadas); los limites entre rodata y data son una deduccion a partir
de las referencias del codigo con granularidad de `0x100` bytes y se marcan como aproximados.

## Vista general

| Region | Inicio | Fin (exclusivo) | Contenido | Certeza |
|---|---|---|---|---|
| RAM de trabajo previa | `0x80010000` | `0x80014A00` | Variables globales del juego (71 direcciones referenciadas, `0x80010000..0x8001013F`) y rutinas cargadas en ejecucion (`0x80010204`, `0x8001020C`, `0x80010258`, `0x80012AB0`, `0x80012AE4`) | Media |
| Arranque | `0x80014A00` | `0x80014AC4` | Codigo de arranque del SDK (`__main`, `start`, `stup1`, `stup0`) y 16 bytes de datos desde `0x80014AB4` (en `0x80014AB0` hay un `break`) | Alta |
| Codigo del juego | `0x80014AC4` | `0x80045DA0` | 449 simbolos de funcion (201.416 bytes) | Alta |
| Codigo de librerias Sony | `0x80045DA0` | `0x8005DEA0` | 98.560 bytes; 650 simbolos de funcion (598 identificados por firma) | Alta |
| Rodata (tablas de saltos, cadenas del juego) | `0x8005DEA0` | `0x8005F000` | Tablas de saltos en `0x8005E300..0x8005E700`, tabla de ficheros en `0x8005EE78` | Media |
| Data inicializada | `0x8005F000` | `0x80067800` | Tablas y estructuras del juego (el bloque `0x80061900..0x80066500` no se referencia directamente: se accede por punteros) | Media |
| Rodata de librerias y mensajes | `0x80067800` | `0x80069000` | Cadenas de librerias y del motor, tablas de punteros | Media |
| Datos pequenos (`sdata`) | `0x80069000` | `0x80069348` | Variables inicializadas accedidas con `$gp` | Alta |
| BSS | `0x80069348` | `0x800768A8` | Variables sin inicializar, borradas por el arranque | Alta |
| Heap | `0x800768A8` | (pila) | Memoria dinamica (`InitHeap` en el arranque) | Media |

El archivo termina en `0x80069A00`: sus ultimos `0x6B8` bytes ya caen dentro del BSS y son ceros.
La cabecera declara `gp0 = 0` y `bss = 0`, pero el codigo de arranque fija sus propios valores.

### Evidencia de los limites del BSS y de `$gp`

El arranque (`0x80014A08`) ejecuta, con las constantes tal como aparecen en el codigo:

```
0x80014A08  lui v0,0x8007 ; addiu v0,v0,-0x6CB8      ; v0 = 0x80069348 (inicio del BSS)
0x80014A10  lui v1,0x8007 ; addiu v1,v1,0x68A8       ; v1 = 0x800768A8 (fin del BSS)
0x80014A18  sw zero,0(v0) ; addiu v0,v0,4 ; sltu ; bne  ; bucle que borra de palabra en palabra
0x80014A88  lui gp,0x8007 ; addiu gp,gp,-0x6CE0      ; gp = 0x80069320
0x80014A94  jal 0x8004E5AC                            ; InitHeap
0x80014AA8  jal 0x80016414                            ; main
```

`$gp = 0x80069320` hace que los accesos `lb v0,0x18(gp)` apunten a `0x80069338`: los datos pequenos
se agrupan alrededor de esa direccion (`0x80069000..0x8006A000` concentra la mayor densidad de
referencias del segmento).

## Codigo

- **Arranque del SDK**: `0x80014A00..0x80014AC4`. `start` (`0x80014A08`) limpia el BSS, fija `gp`,
  inicializa el heap y llama a `main`.
- **Codigo del juego**: `0x80014AC4..0x80045DA0`. 449 simbolos de funcion. Incluye tres funciones enormes
  (`0x80020B90` con 19.880 bytes, `0x80026FEC` con 19.092 bytes y `0x80019474` con 11.048 bytes) y
  un grupo de 12 rutinas de 32 bytes en `0x80026118..0x80026298` que solo se invocan por tabla.
  `main` esta en `0x80016414`.
- **Codigo de librerias Sony**: `0x80045DA0..0x8005DEA0` (`0x8005DE98..0x8005DEA0` son dos `nop` de relleno tras la ultima funcion, el mismo limite que usa la particion), agrupado por libreria en este orden
  aproximado (direccion de la primera funcion identificada): libpress `0x80045DA0`, libcd
  `0x80046420`, libspu `0x80049A90`, libetc `0x8004D8C0`, libapi `0x8004E5BC`, libc `0x8004E86C`,
  libgte `0x8004F52C`, libgpu `0x80050B3C`, libgs `0x8005486C`, libpad `0x8005712C`, libcard
  `0x8005A7CC`, libmcrd `0x8005AA9C` hasta `0x8005DE10`. Las versiones del SDK no coinciden entre
  librerias (libetc es del SDK 4.0, libcd, libgs y libgte del 4.6).

### Recuento de funciones

La tabla `config/symbols.txt` tiene 1101 simbolos de funcion: 2 de arranque comunes (`__main`
y `start`), 449 en la zona del juego y 650 en la zona de librerias. La depuracion de 1217 candidatos de
Ghidra (935 de libreria y 282 del juego) dio 1217 - 306 fundidos - 10 descartados + 7 rutinas
completas que ningun candidato cubria = 908 (detalle en `docs/GHIDRA.md`). Separar las rutinas que solo se
llaman por tablas de punteros (194 nuevas: 92 de `func_8002F9F8` y 102 de `func_80030ECC`, que quedan de
0x38 bytes) y fusionar `func_800415A0` con `func_80042BB8` da 908 - 1 + 194 = 1101. Las cifras de origen
de abajo (599, 277, 32) corresponden a los 908 de la depuracion. Por origen, 599 son de
libreria identificada por firma (400 con nombre oficial), 277 del juego y 32 tienen una direccion que no figura entre los candidatos (rutinas nuevas o funciones cuyo inicio se adelanto). Dentro de la zona de librerias hay 52 simbolos
que ninguna firma reconoce (rutinas internas de libreria).

**Nota sobre las cifras de funciones.** Cada numero cuenta una cosa distinta:

- **1101** simbolos de funcion en el ejecutable (`config/symbols.txt`): 650 estan en la zona de librerias de Sony
  (`0x80045DA0..0x8005DEA0`), 2 son de arranque y 449 son codigo del juego.
- **449** simbolos en el rango de codigo del juego `0x80014AC4..0x80045DA0` (256 antes de separar las rutinas por
  tablas de punteros); es la cifra que usa `docs/PROGRESO.md`.
- **282** funciones "del juego" segun las firmas de Ghidra (`es_libreria` en 0 en `funciones.csv`); 23 de ellas
  caen en la zona de librerias, y por eso no coincide con 256.
- **309** rutinas en el ambito de los borradores en C (`m2c`): las 256 del rango, las 52 de la zona de librerias
  que ninguna firma reconoce y la entrada `func_80014A08`. Los analisis de grafo y subsistemas se calcularon con
  la tabla anterior de 908 simbolos, de modo que ven 258 funciones del juego con `__main` y `start`.

## Datos

Deduccion a partir de 1570 direcciones de datos referenciadas desde el codigo (lecturas y
escrituras por instruccion):

- `0x8005DEA0..0x8005F000`: solo lecturas. Cadenas del juego y tablas de saltos de `switch`
  (`0x8005E300..0x8005E700` contiene punteros a codigo).
- `0x8005F000..0x80067800`: lecturas y escrituras mezcladas, es decir, `.data`. La zona
  `0x80060000..0x80061000` concentra la mayor densidad de accesos del bloque.
- `0x80067800..0x80069000`: cadenas y tablas de punteros. Contiene los mensajes
  `Error: Can't push matrix,stack(max 20) is full!` (`0x80067C7C`), `\LEVEL5\MERLIN.BZZ;1`
  (`0x80067EF0`), `BouzeID %d not found` (`0x80067F54`), las marcas `$Id` de las librerias
  (`bios.c` en `0x80068630`, `intr.c` en `0x800689C8`, `sys.c` en `0x80068D30`) y
  `ps_sort_sprite,bg: z resolution overflow` (`0x80068F50`).
- `0x80069000..0x80069348`: datos pequenos escritos y leidos (111 escrituras en el bloque
  `0x80069000`).
- `0x80069348..0x800768A8`: BSS. Las referencias llegan hasta `0x80077000`, ya en el heap
  (`0x80077000` es un buffer que recibe `0x800415A0` desde `main`).
- `0x80010000..0x8001013F`: 71 direcciones de variables globales (la mas usada,
  `0x80010000`, es el estado principal: la referencian 17 funciones).

## Puntos clave del programa

### Cadena `\LEVEL5\MERLIN.BZZ;1`

- Cadena en `0x80067EF0`, apuntada desde `0x80067F08`.
- La referencia la hace `0x8003E9E8`, llamada desde el bucle de `main`. Es una comprobacion del
  disco: mientras el flag `0x80069620` este activo ejecuta `VSync(0)`, `CdControlB(0x01,...)`
  (`CdlNop`), `CdDiskReady`, `CdGetDiskType` y `CdSearchFile` con esa ruta; si encuentra el
  archivo desactiva el flag y reinicia la pista de audio (`0x8003E16C`). No carga el nivel: confirma que el
  disco correcto esta insertado.

### Lectura de CD

- `CdRead` (`0x80049360`) y `CdReadSync` (`0x800494FC`) solo las invoca `0x80048BEC`
  (rutina interna de libcd, objeto `ISO9660.OBJ`), que a su vez la usan las rutinas internas de
  `CdSearchFile` (`0x800482F0`). El juego las alcanza unicamente al buscar archivos por nombre.
- La carga de los `.BZZ` no usa `CdRead`. Usa lectura de sectores crudos:
  - `0x80040EB4` construye al arrancar una tabla de 113 entradas (`0x71`) de pares
    (sector, tamano en bytes) a partir de `0x8005EE78`, y para cada una guarda la posicion de CD
    (`CdIntToPos`) en registros de 16 bytes desde `0x8005F206`. 108 de los tamanos coinciden
    exactamente con los de los `.BZZ` del disco; las dos ultimas entradas corresponden a los
    audios XA (tamanos de 133.095.936 y 299.363.072 bytes).
  - `0x800411F0(loc)` inicia la lectura: instala `0x8004109C` como callback de sector listo y
    ordena `CdControl(0x06)` (`CdlReadN`).
  - `0x8004109C` es el callback: copia cada sector con `CdGetSector(destino, 0x200)` (2048
    bytes), avanza el destino, cuenta los bytes recibidos y, al llegar al total, desactiva el
    callback y ordena `CdControl(0x09)` (`CdlPause`). Hay un modo con anillo
    (`0x80069490..0x8006947C`).
- La musica y las voces (XA) las controlan `0x8003E034`, `0x8003E16C`, `0x8003E298`,
  `0x8003E680` (callback) y `0x8003E88C`: fijan el modo `0xCA` con `CdControlB(0x0E,...)` y
  arrancan la lectura continua con `CdControlB(0x1B,...)` (`CdlReadS`); las posiciones salen de
  una tabla en `0x8005E968`.

### Bucle principal

- `main` (`0x80016414`, 2040 bytes): tras inicializar (`0x80044D44`, `0x80044E58`,
  `0x80015EC0`, `0x80040EB4`, `0x80016118`) y registrar `VSyncCallback(0x80040AF0)` y
  `DrawSyncCallback(0)`, entra en un bucle infinito. Cada iteracion: comprueba el disco
  (`0x8003E9E8`), mide el tiempo con `VSync(1)` antes y despues de actualizar el cuadro
  (`0x80016218`: `GsSetRefView2L`, `GsClearOt` por triplicado, ordenacion de primitivas),
  procesa la entrada y las transiciones de estado y vuelve a empezar. `VSync` aparece 3 veces
  en `main`.
- El envio de primitivas esta separado: `0x80040B8C` (524 bytes) llama a `DrawSync(1)`, avanza
  un anillo de 3 buffers, ejecuta `GsSwapDispBuff` y tres `DrawOTag`. La invocan el callback de
  `VSync` (`0x80040AF0`) y el callback de `DrawSync` (`0x80040A80`), no `main`.
- `VSync(0)` y `DrawSync(0)` repetidos en bucle de dos pasadas aparecen en `0x80016044`
  (`MoveImage`) y `0x800443CC` (`ClearImage`): limpian y copian los buffers de imagen al arrancar.

## Como se regenera

```
python -m tools.ghidra analizar --exe <SLUS_008.38> --proyecto <carpeta>
python -m tools.ghidra exportar --proyecto <carpeta> --salida <carpeta>
python -m tools.ghidra simbolos --funciones <funciones.csv> --salida config/symbols.txt
```

Las referencias a datos (`xrefs_datos.csv`), las cadenas (`strings.csv`) y el C de cada funcion
(`decomp/`) que respaldan este mapa se generan con `exportar` y no se versionan.

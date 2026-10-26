# Analisis del ejecutable con Ghidra

Este documento describe como se importa `SLUS_008.38` en Ghidra de forma reproducible, que
identifica el analisis y como se convierte en la tabla de simbolos `config/symbols.txt`. Todo el
analisis corre sin interfaz grafica; lo unico que se versiona es la tabla de nombres y
direcciones, nunca el proyecto de Ghidra ni sus exportaciones, que son derivados del binario.

## Requisitos

- Ghidra 12.1.2 (se indica su carpeta con `--ghidra` o la variable `BBLIT_GHIDRA`) y un JDK 21.
- La extension `ghidra_psx_ldr` instalada a nivel de usuario (seccion siguiente).
- El ejecutable `SLUS_008.38` (se indica con `--exe` o con `BBLIT_DISC`, que puede apuntar a la
  carpeta del disco extraido: se busca `fs/SLUS_008.38` y despues `SLUS_008.38`).
- El entorno virtual del proyecto (`python -m tools.ghidra ...`).

## Extension del cargador PSX

| Dato | Valor |
|---|---|
| Proyecto | `lab313ru/ghidra_psx_ldr` |
| Procedencia | Version publicada 2026.10.03, paquete precompilado para Ghidra 12.1.2 (no se compilo) |
| Archivo | `ghidra_12.1.2_PUBLIC_20261004_ghidra_psx_ldr.zip` (9.159.249 bytes) |
| SHA-256 | `738e65e026d9edfb56a2d6d9223abcfb8b1d24bf2c0e4fdae107742ad640a316` |
| Verificacion | Coincide con el resumen que publica el repositorio para ese archivo |

El hash se verifico antes de extraer. Instalacion sin tocar la carpeta de Ghidra: se descomprime
la carpeta `ghidra_psx_ldr` del paquete en el directorio de extensiones del usuario, que en
Ghidra 12.1 es `%APPDATA%\ghidra\ghidra_12.1.2_PUBLIC\Extensions\` (las versiones antiguas usaban
`~/.ghidra/.ghidra_<version>/Extensions`; el registro de arranque de Ghidra muestra la ruta real
en la linea `Loading user preferences`). El paquete trae el cargador `PsxLoader`, el analizador
`PsyQ Signatures` y los indices de firmas de las versiones 2.6 a 4.7 del SDK.

El cargador se pide por el nombre de su clase (`-loader PsxLoader`): el nombre visible
`PSX Executables Loader` no lo acepta la opcion `-loader` de `analyzeHeadless`.

## Uso

```
python -m tools.ghidra analizar --exe <SLUS_008.38> --proyecto <carpeta> [--semilla <txt>]
python -m tools.ghidra exportar --proyecto <carpeta> --salida <carpeta>
python -m tools.ghidra simbolos --funciones <funciones.csv> --exe <SLUS_008.38> --salida config/symbols.txt
python -m tools.ghidra informe  --funciones <funciones.csv> [--verificar config/symbols.txt]
```

- `analizar` ejecuta `analyzeHeadless` en primer plano (unos 4 a 5 minutos), con limite de
  tiempo, y comprueba en el registro que se uso el cargador PSX con base `0x80014A00` y entrada
  `0x80014A08`. Es idempotente: `-overwrite` reemplaza el programa de una corrida anterior.
- `exportar` abre el proyecto en solo lectura, sin reanalizar (unos 20 segundos), y borra antes
  la exportacion previa para que un script que no compile no deje pasar un resultado viejo.
- `simbolos` valida cada campo del CSV (falla con `ValueError` que nombra fila y campo), lee las
  instrucciones del ejecutable y depura los candidatos a funcion antes de escribir la tabla
  (seccion siguiente a los resultados).
- `informe` imprime los conteos y la cobertura; con `--verificar` lee `symbols.txt` con el lector
  propio y comprueba el contrato.

### Pasos del analisis

1. Importacion con el cargador PSX (`gp0 = 0`, un segmento de `0x55000` bytes en `0x80014A00`).
2. `PrepararAnalisis.java` (antes del analisis): siembra como funciones las direcciones de un
   archivo de semilla opcional. Solo se aceptan direcciones con bytes reales del ejecutable.
3. Auto-analisis de Ghidra con el analizador de firmas `PsyQ Signatures`. El cargador detecta la
   version 4.5 del SDK en el binario.
4. `DescubrirFunciones.java`: rutinas que solo se invocan mediante tablas de punteros (no tienen
   `jal` que las alcance). Reglas, de mas a menos estricta: prologo `addiu sp,sp,-N` precedido de
   `jr ra` o de relleno; rutina sin marco de pila (hueco con un `jr ra` cercano); y fusion de un
   fragmento suelto con la funcion sin llamadores que le sigue (manejadores cuya primera
   instruccion no es un ajuste de pila). Repite el analisis hasta que no aparezcan mas.
5. `AplicarFirmas.java`: el ejecutable enlaza librerias de epocas distintas del SDK (libetc
   coincide con el SDK 4.0, libcd/libgs/libgte con el 4.6) y el cargador solo aplica una version.
   Se aplican pasadas adicionales con 4.6.0, 4.0.0, 4.7.0 y 4.4.0; cada una nombra solo las
   funciones que siguen sin nombre propio, asi que nunca pisa una identificacion previa. Las dos
   ultimas no aportaron funciones nuevas; se dejan por si cambia la semilla.

La semilla usada son las direcciones de destino de `jal` de un primer barrido del ejecutable
(569 direcciones, todas dentro del segmento). Es opcional: sin ella el analisis tambien funciona,
pero parte de las rutinas de libreria se detectan peor.

### Archivos de la exportacion (fuera del repositorio)

| Archivo | Contenido |
|---|---|
| `funciones.csv` | direccion, nombre, tamano, es_libreria, libreria_origen, numero_de_llamadores, nombre_oficial, comentario |
| `strings.csv` | direccion, longitud, texto (cadenas ASCII terminadas en cero, minimo 5 caracteres) |
| `xrefs_datos.csv` | direccion_dato, tamano, funciones_que_lo_usan, lecturas, escrituras |
| `decomp/<DIRECCION>_<nombre>.c` | C que produce el decompilador para cada funcion |

Una funcion es de libreria cuando su nombre figura como etiqueta en alguna firma del SDK. Una
etiqueta de firma sobre menos de 4 bytes (datos dentro de un objeto) no se exporta como funcion.

## Resultados

Medidos sobre el ejecutable del disco con la configuracion descrita:

| Concepto | Valor |
|---|---|
| Funciones en el segmento (candidatos de Ghidra) | 1217 |
| De libreria identificada por firma | 935 |
| Con nombre oficial del SDK | 402 |
| Rutinas internas de un objeto de libreria (sin nombre exportado) | 533 |
| Del juego (ninguna firma las identifica) | 282 |
| Libreria con candidatos alternos anotados | 61 |
| Segmento cubierto por cuerpos de funcion | 85,10 % (296.284 de 348.160 bytes) |

Distribucion por libreria (una funcion puede coincidir con varias): libcd 170, libspu 142,
libpad 126, libmcrd 116, libapi 76, libc2 71, libgte 64, libgpu 63, libetc 50, libgs 50,
libpress 24, libc 17, libcard 17. libsnd solo tiene una coincidencia ambigua, asi que no esta
confirmada.

Fuera de las funciones queda el 14,9 % del segmento: datos (tablas, cadenas, variables), relleno
de alineacion y unas tres decenas de fragmentos de codigo de libreria entre dos funciones que ninguna firma
ni referencia delimita. De las 282 funciones del juego, 23 caen dentro de la zona de librerias:
son rutinas internas de libreria que ninguna firma reconoce.

## Depuracion de candidatos a funcion

Las 1217 funciones de `funciones.csv` no son todas funciones completas. Las firmas de libreria
etiquetan puntos de entrada secundarios (destinos de salto dentro de una rutina; por ejemplo
`S_SR_OBJ_B0`, de 4 bytes, y `S_SR_OBJ_B4`, el epilogo de `SpuSetReverb`) y el descubrimiento por
prologo puede partir una rutina. Si se emiten como simbolos de tipo funcion, el desensamblador
deja de tratar como codigo la region que sigue: con la tabla sin depurar solo salian 425 etiquetas
de funcion y el codigo de librerias, desde `0x8004A810`, quedaba como palabras sueltas.

`simbolos` lee el segmento del ejecutable y aplica estas reglas (modulo `depuracion`):

0. Una funcion "cierra" si su ultima instruccion real (la anterior a la ranura de retardo, en
   `direccion + tamano - 8`) es una transferencia que no continua en la siguiente (`jr`, `j`, o una
   rama que se toma siempre: `b`, es decir `beq` con registros iguales, y `bgez` sobre `zero`) y el
   cuerpo contiene una salida real (`jr` o `j`). Se rechaza cualquier otra cosa: un retorno en
   medio no basta si el cuerpo acaba en una instruccion corriente. Una rama condicional tampoco
   cierra, porque si no se toma el flujo cae en la instruccion siguiente; `jal` y `jalr` vuelven.
   Un bucle final (`b` hacia atras) con el `jr ra` en medio si cierra.
1. Un candidato pegado (o solapado) al final de otro que no cierra hasta esa frontera es
   continuacion de este: se funde y la funcion anterior crece. Una funcion abierta puede
   absorber varios fragmentos seguidos.
2. Un candidato de menos de 8 bytes (un retorno y su ranura) que sigue a una funcion que cierra
   se descarta: no puede ser una funcion.
3. Una funcion abierta solo se emite si su cuerpo definitivo cierra, recortado al siguiente
   candidato. Si el cuerpo no cierra pero lo hace mas adelante, antes del siguiente candidato, se
   prolonga (Ghidra corta el cuerpo de las funciones con tabla de saltos y deja fuera el
   epilogo). Si no, se descarta junto con lo que absorbio. Excepcion: el punto de entrada de la
   cabecera (`0x80014A08`), cuyo codigo de arranque llama a `main` y no retorna.
4. El codigo que ningun candidato cubre (hueco entre funciones, hasta `0x8005DEA0`) se completa.
   Tras saltar el relleno de ceros, cada hueco acaba en un unico destino:
   - primera palabra que no decodifica como instruccion (datos incrustados): se registra como
     tramo sin codigo (`huerfanos`, con direccion y tamano) y no se emite;
   - el hueco cierra: es una rutina que Ghidra no creo y se anade como funcion;
   - no cierra y la funcion siguiente no tiene nombre oficial: es su cabecera y se une a ella;
   - no cierra y la siguiente tiene nombre oficial (el nombre pertenece a su direccion): si mide
     8 bytes o mas queda como rutina propia que continua en ella; si mide menos, se registra
     como tramo sin codigo;
   - es el ultimo tramo antes de `0x8005DEA0` y no cierra: se registra en los descartados y como
     tramo sin codigo.
5. Al final se recorta cada funcion al inicio de la siguiente, de modo que no hay solapes. Una
   propiedad comprobada en las pruebas: toda palabra no nula del rango de codigo pertenece a una
   funcion o a un tramo registrado, y cada funcion cierra o continua exactamente en la siguiente.

Reconciliacion de cifras: las secciones anteriores cuentan candidatos de Ghidra (1217: 935 de
libreria y 282 del juego); la tabla final tiene 908 simbolos. 1217 - 306 fundidos - 10 descartados
= 901 funciones; a ellas se suman 7 rutinas completas que ningun candidato cubria = 908. De los 39
huecos de codigo completados, los otros 32 no anaden simbolos: son la cabecera de una funcion
siguiente sin nombre oficial, que pasa a empezar antes. Sobre los 908: 599 son de libreria
identificada por firma (400 con nombre oficial y 199 rutinas internas), 277 son del juego y 32
tienen una direccion que no figura en `funciones.csv` (rutinas nuevas o funciones cuyo inicio se
adelanto), por lo que no hereda clasificacion; por zona, 258 simbolos estan en
`0x80014A00..0x80045DA0` y 650 en la zona de librerias, 52 de ellos sin firma.

Resultado sobre este ejecutable: de 1217 candidatos, 306 se fundieron en la funcion anterior, 10
se descartaron (todos de 4 bytes: etiquetas de objeto de libc, libgte, libpad y libmcrd) y se
completaron 39 huecos de codigo (7 funciones nuevas y 32 cabeceras unidas a la funcion siguiente);
la tabla queda con 908 simbolos. No hay ningun tramo de menos de 8 bytes antes de una funcion
oficial ni ultimo tramo sin salto. Entre los fundidos estan dos nombres de `2MBYTE.OBJ` (`stup1`,
`stup0`), tramos del codigo de arranque, ahora una sola funcion desde `0x80014A08`.

Tramos sin codigo registrados (datos incrustados entre rutinas, 13 palabras que no decodifican
como instruccion): `0x80014AB4` (16 bytes), `0x800375F8` (20), `0x8004E5CC` (8) y `0x8004F69C` (8).
Son las unicas palabras del codigo desensamblado (el segmento `asm` de arranque y de librerias y los
subsegmentos por archivo bajo `asm/nonmatchings/`, ver `docs/DESCOMPILACION.md`) que quedan como `.word`.

## Reglas de nombres de `config/symbols.txt`

- Formato: `nombre = 0xDIRECCION; // type:func size:0xTAMANO`, direcciones y tamanos en
  hexadecimal mayuscula, orden ascendente por direccion, una linea por simbolo.
- Funcion de libreria con nombre exportado por el SDK (identificada por firma): ese nombre
  (`DrawSync`, `CdReadSync`, `VSync`, ...).
- La depuracion anterior dejo 908 simbolos; la separacion de rutinas por tablas de punteros (ver
  abajo) la lleva a 1101 funciones, la regla del retorno intermedio a 1102 y los 66 datos pequenos de `$gp` a 1168
  lineas, que es la tabla definitiva actual.
- Rutina interna de un objeto de libreria sin nombre exportado (Ghidra la llama
  `LIBPRESS_OBJ_188`: objeto y desplazamiento): `func_80XXXXXX`. El origen consta en la columna
  `libreria_origen` de `funciones.csv`, no en el nombre.
- Funcion del juego sin identificar: `func_80XXXXXX`.
- `main`: se conserva. El cargador la reconoce por la secuencia de arranque (el codigo de
  `0x80014A08` la invoca) y no por una firma.
- Un nombre oficial que aparece en varias direcciones (copias estaticas del mismo objeto, por
  ejemplo `memclr` en `0x8004E188`, `0x8004E2B0` y `0x8004E558`) se desambigua con la direccion:
  `memclr_8004E188`. Dos simbolos no pueden compartir identificador.
- El tamano es el que atribuye Ghidra recortado al inicio de la funcion siguiente y al final del
  segmento, para que ningun par de simbolos se solape.
- No hay simbolos de datos: ninguna firma aporta etiquetas de datos dentro del segmento con
  tamano conocido, y los nombres de datos se asignaran al estudiarlos.

La validacion (`validar_simbolos`) rechaza con el nombre del simbolo: identificador invalido,
nombre repetido, direccion fuera de `0x80014A00..0x80069A00`, funcion no alineada a 4, tamano
nulo o que excede el segmento, desorden y solapes.

## Evidencia de los nombres

Todos los nombres oficiales proceden de coincidencia de firmas (patron de bytes de la funcion
frente al indice del SDK); no se ha puesto ningun nombre por cadena o por intuicion. Casos que
merecen cautela:

| Caso | Evidencia |
|---|---|
| 61 funciones con candidatos alternos (`comentario` en el CSV) | Funciones muy cortas cuyo patron coincide con varios objetos. Ghidra aplica una y anota las otras. Las de las rutinas de CD (`CdSync`, `CdReady`, `CdFlush`, `CdDataSync`) son contiguas a `CdSyncCallback`/`CdReadyCallback` en el orden del objeto de libreria, lo que respalda el nombre |
| `main` en `0x80016414` | Llamada desde el codigo de arranque tras limpiar el bss (`jal` en `0x80014AA8`) |
| `start` en `0x80014A08` (`func_80014A08` en la tabla) | El cargador lo llama `start`; la firma lo da como candidato `stup2` de `2MBYTE.OBJ`, igual que sus vecinos `stup1` y `stup0`. Se deja generico porque la firma lo anota como ambiguo |
| `__main` en `0x80014A00` | Coincide con cinco objetos de arranque a la vez (`2MBYTE`, `8MBYTE`, `SNMAIN`, `NOHEAP`, `NONE3`); es el `jr ra` vacio comun a todos |
| `InitHeap` en `0x8004E5AC` | Llamada desde el arranque justo despues de limpiar el bss |

## Limitaciones conocidas

- Ghidra no decodifica la instruccion de `0x80014AB4` (datos entre dos rutinas de arranque) y
  la decompilacion de las tres funciones de arranque lo avisa. No afecta a la tabla.
- El codigo que se invoca en `0x80010204`, `0x8001020C`, `0x80010258`, `0x80012AB0` y
  `0x80012AE4` no esta en el ejecutable: vive en la RAM anterior al segmento y se carga en
  ejecucion. Ghidra lo ve como funciones sin cuerpo.
- Los grandes bloques de codigo (`0x80020B90`, `0x80026FEC`, `0x80019474`) son funciones de
  decenas de kilobytes; el decompilador las produce, pero requieren partirse a mano.

## Tablas de punteros a codigo y rutinas sin prologo

Algunas "funciones" de la depuracion anterior eran bloques de decenas de rutinas hoja a las que el juego llega
por una tabla de punteros: no tienen prologo de pila ni ningun `jal` que las delate, asi que nada las separaba.
Hay tablas de punteros a codigo en dos usos distintos y la tabla de simbolos solo debe cambiar por uno de ellos.

**Clasificacion de una tabla** (`tools/ghidra/tablas.py`, `clasificar_tablas`). Se buscan en el codigo las
instrucciones que forman o leen una direccion dentro de cada corrida de punteros (`lui` mas `addiu`/`ori`, una
suma con un indice, un `lw`), se sigue el valor leido hasta el `jr` o `jalr` que lo usa y se decide:

- `jalr` sobre el valor leido: tabla de punteros a funcion (se llama a cada destino).
- `lw` mas `jr` sin enlace: puede ser un `switch` o un despachador por salto directo. Los destinos ordenados
  parten el codigo en tramos; si cada tramo termina en una transferencia incondicional y no se bifurca a otro
  tramo, son rutinas independientes. Eso solo basta para decidir "puntero a funcion" si ademas la direccion del
  elemento se calcula con `add` (suma con desbordamiento), que el compilador no emite para indexar y delata un
  despachador escrito a mano. Un `switch` del compilador con casos que retornan por separado tambien tiene
  tramos independientes, pero indexa con `addu` y va precedido de una comparacion de rango: queda como `salto`.
- sin consumo visible (la tabla se copia a una estructura): puntero a funcion si los tramos son independientes o
  si todos los destinos ya son inicio de funcion; en otro caso, `salto`.

La ventana de seguimiento de registros es de 100 instrucciones. Se calibro sobre las tablas con consumidor
de la poblacion completa (23 consumos con `jr` o `jalr`): con 24 instrucciones se encuentran 21, con 48 se encuentran 22 y desde 64 se
encuentran las 23 (300 no cambia nada).

**Regla de la tabla de simbolos** (`tools/ghidra/depuracion.py`, `refinar_con_tablas`). Todo destino de una tabla
de punteros a funcion dentro del rango del juego (`0x80014AC4..0x80045DA0`) es inicio de funcion aunque no tenga
prologo. La funcion que lo contenia se parte en ese punto si el tramo anterior cierra como una funcion completa
(termina en una transferencia incondicional y contiene un `jr` o `j`); si no cierra se informa como conflicto y no se
parte. Los destinos de las tablas de `switch` no generan funciones: son etiquetas dentro de una funcion. Los
destinos fuera del rango del juego (las tablas de punteros de las librerias) se informan sin aplicar. En sentido
contrario, una funcion del juego se une a la anterior, que ocupa justo antes, si nadie la llama (ni `jal` ni
tabla de punteros) y la anterior cae en ella con una rama condicional o con un `j` al interior, o su primera
instruccion es destino de un `switch` consumido por la anterior.

**Resultado sobre este ejecutable** (`python -m tools.ghidra simbolos ... --tablas ... --nuevas ...`):

| Cifra | Valor |
|---|---|
| Tablas de punteros a codigo | 24 (6 de punteros a funcion, 18 de `switch`) |
| Tablas de punteros a funcion en el juego | `0x8005E35C` (37 entradas, `jalr` en `0x8003607C`, consumida por `func_800353B0`; 31 destinos distintos, todos ya eran funcion), `0x8005E3F0` (92 entradas, `lw`+`jr` en `0x8002FA20`) y `0x8005E560` (102 entradas, `lw`+`jr` en `0x80030EF4`) |
| Tablas de punteros a funcion en librerias | `0x800619AC`, `0x80067848`, `0x80067D9C` (sus destinos ya eran funciones de libreria) |
| Tablas de `switch` | las 18 restantes, entre ellas las 5 de `func_800415A0` y las de `func_80035244`, `func_8003690C` y `func_8003C1C8` |
| Simbolos de funcion | 908 antes, 1101 despues (908 - 1 + 194); 1102 con la regla del retorno intermedio |
| Funciones nuevas | 194, de 8 a 424 bytes cada una (6 de 8 bytes): 92 salen de `func_8002F9F8` y 102 de `func_80030ECC` |
| Bloques madre tras partir | `func_8002F9F8` y `func_80030ECC` quedan de `0x38` bytes (el despachador y los `jr ra` de las rutas por defecto) |
| Funciones del juego en el rango | 449 (antes 256 con `symbols.txt` y 262 con el parche) |
| Destinos no aplicados | 23, todos en el codigo de librerias (fuera del rango del juego); ninguno en el juego |

`func_8002FA60`, `func_8002FB38` y `func_80030DA4`, que seguian fundidas con el parche, ya no lo estan: son
funciones de `0x30`, `0x20` y `0x7C` bytes entre otras rutinas de la tabla de condiciones. `func_8002FA38`
(`0x28`), `func_8002FB18` (`0x20`) y `func_80036204` (`0x4C`) conservan nombre y tamano, que es lo que necesitan
las tres funciones ya escritas en C. El orden de las rutinas coincide con el de las direcciones, no con el del
indice de la tabla, y hay destinos repetidos en `0x8005E35C` (varias entradas apuntan a las mismas rutinas
vacias de 8 bytes).

**`func_800415A0` y `func_80042BB8` son una sola funcion** de `0x2E2C` bytes. Evidencia: la primera cierra con
`j` en `0x80042BB0`, pero el cuerpo de `func_800415A0` bifurca 13 veces con ramas condicionales y 9 con `j` al
interior de la segunda y la segunda bifurca 2 veces con ramas condicionales de vuelta a la primera; el epilogo
compartido esta en `0x8004439C`, dentro de la segunda; la segunda empieza con `lbu v0, 0(s2)` usando un registro
guardado por el prologo de la primera y sin prologo propio; ningun `jal` ni tabla de punteros la nombra, y su
direccion solo aparece como destino exacto de un `switch` de la primera. El borrador de `m2c` solo se obtiene si se
fusionan. La regla de fusion arriba la aplica automaticamente y es la unica fusion del rango del juego.

**Efecto en el consumidor** (medido en una copia aislada del repositorio, con `config/splat.yaml` sin cambios en
la copia salvo lo que se indica):

- Con `config/simbolos_adicionales.txt` presente (ya retirado), `split` funcionaba pero `build` fallaba: el parche redefinia despues
  de `symbols.txt` los tamanos de `func_8002FA60` (`0xB8`), `func_8002FB38` (`0x1228`) y `func_80030DA4` (`0x128`)
  y esos rangos solapaban las funciones nuevas, de modo que `splat` no generaba su ensamblador.
- Cada `src/*.c` lleva una linea `INCLUDE_ASM` por funcion y `split` no los regenera: con la tabla nueva
  hacian falta 188 lineas nuevas (los otros 6 nombres de las 194 ya tenian linea) y quitar la de `func_80042BB8`;
  sin ellas el codigo de las funciones nuevas desaparece del ejecutable. Se resolvio regenerando `src/` con la
  particion por subsistema (`docs/DESCOMPILACION.md`).
- Con el parche retirado (archivo y linea de `symbol_addrs_path`) y las lineas de `src/` adaptadas:
  `python tools/build.py clean && split && build && verify` da OK (SHA-256 `0fad70d9...c87df0`). Estado actual
  con 5 funciones en C: `asm/` tiene 1096 `glabel` (2 de `boot`, 650 de `libs`, 444 de `nonmatchings`) y hay 5
  funciones en C, es decir 1101, que es el total de la tabla; el texto desensamblado conserva las 13 palabras
  `.word`; `progreso` informa 5 funciones en C de 449 (452 de 201416 bytes).

**Hecho.** `config/simbolos_adicionales.txt` y su linea en `config/splat.yaml` se retiraron, las lineas
`INCLUDE_ASM` de `src/` se regeneraron con la particion por subsistema y la comprobacion de reparto del archivo
retirado se elimino. Las cifras de `docs/SUBSISTEMAS.md` y `docs/ARCHIVOS_ORIGEN.md` y los borradores se calcularon
con la tabla de 908 simbolos; la fuente de las cifras actuales por subsistema es `docs/PROGRESO.md`.

## Rutinas pegadas tras un retorno

La regla de las tablas de punteros no ve las rutinas que nadie enumera. `func_8002FF38` (0x40 bytes) contenia dos
rutinas de 0x20 bytes, cada una con su propio `jr ra`; la segunda no esta en ninguna tabla. Regla
(`depuracion.py`, `_partir_por_retornos`, aplicada a las funciones del juego tras partir por tablas y fusionar
continuaciones): un `jr ra` con su ranura de retardo en medio de una funcion separa dos rutinas si ninguna rama
condicional ni `j` de la funcion cruza ese punto (ni de un lado al otro ni en sentido contrario), la ranura no es un
salto, no hay destinos de `switch` a ambos lados ni en el propio punto, y las dos piezas cierran como funciones
completas. La razon tecnica: todo lo que sigue a un retorno completo de una funcion de un solo cuerpo es destino de
alguna rama anterior; si ninguna lo es, ese codigo solo puede alcanzarse llamandolo, es decir, es otra rutina. Las
funciones con varios retornos legitimos siempre tienen ramas que cruzan el punto (el salto sobre el epilogo).

Calibracion sobre la poblacion completa del codigo del juego: 41 puntos con `jr ra` en medio de una funcion, 40
cruzados por alguna rama o `j` y 1 libre (`0x8002FF58`). La regla separa exactamente ese: `func_8002FF38` y
`func_8002FF58`, de 0x20 bytes cada una. No parte ninguna funcion legitima (la tabla conserva las mismas 1101
funciones anteriores mas esta).

## Datos pequenos direccionados con `$gp`

El codigo accede a variables pequenas con un desplazamiento de 16 bits sobre `$gp` (`0x80069320`, que el arranque
fija con `lui gp` y `addiu gp`). Ninguna firma ni funcion las declara, pero el codigo las delata, y
`tools/ghidra/datos_pequenos.py` las descubre por regla al generar la tabla: cada direccion `gp + desplazamiento`
distinta es un simbolo `D_<direccion>`. El tipo y el tamano salen del acceso mas ancho: `lb`/`lbu`/`sb` dan `u8` de 1
byte, `lh`/`lhu`/`sh` dan `u16` de 2 y `lw`/`sw` dan `u32` de 4. Si solo se toma la direccion (`addiu reg, gp, desp`)
se declara `u8` con la distancia al siguiente dato como tamano, con tope de 0x40; es una cota superior, no el tamano
real (afecta a `D_80069330`, `D_80069390` y `D_80069444`).

Hay 66 datos, de `0x80069330` a `0x800694AC`: 63 acceden con `lb`/`lh`/`lw` y 3 solo con `addiu`. La evidencia de cada uno
(mnemonicos, veces y funciones) esta en el aporte de simbolos. Dos cuestiones del formato:

- `splat` solo acepta como `type:` los tipos de su lista (`u8`, `u16`, `u32`, `s32`, ...): `type:data` es un error de
  lectura, asi que la tabla escribe el tipo concreto (`D_80069338 = 0x80069338; // type:u8 size:0x1`).
- Un acceso ancho puede abarcar a la variable siguiente (`D_8006935C` u32 contiene a `D_8006935E` u16, que tambien se
  accede como media palabra). Ambas se declaran y el validador de la tabla admite que un dato contenga a otro; dos
  funciones, o una funcion y un dato, siguen sin poder solaparse.

Con los datos en la tabla, `build` ya no necesita la seccion `[datos_pequenos]` de `config/opciones_compilacion.toml`:
medido en una copia del repositorio con la seccion vaciada, `split`, `build` y `verify` dan OK (el `gp.ld` solo define
`_gp`) y `python tools/build.py diff func_80040AF0` sigue en 0. Los consumidores de la tabla que solo tratan funciones
(el grafo, los borradores, los subsistemas) ignoran los simbolos que no son `func`, igual que `progreso` y la lectura de
direcciones de funcion de `build`.

**Cifras tras esta regla:** 1102 simbolos de funcion (908 - 1 + 194 + 1) y 66 de dato, es decir 1168 lineas en
`config/symbols.txt`. Las funciones en el rango del juego son 450.

**Pendiente para el dueno de `src/`:** la funcion nueva `func_8002FF58` necesita su linea
`INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FF58);` justo despues del bloque de `func_8002FF38` en
`src/interprete_de_eventos.c`; sin ella el cuerpo enlazado mide 32 bytes menos que la cabecera y `build` falla. Con esa
unica linea (medido en una copia): `clean`, `split`, `build` y `verify` dan OK, 871 `glabel` en `asm/` mas 231 funciones
en C suman las 1102 de la tabla. Despues de esa linea el criterio de la tabla de simbolos pasa de 1101 a 1102 funciones.

## Nombres de funciones

`config/symbols.txt` no se edita a mano: se regenera con `python -m tools.ghidra simbolos`. Los nombres que no salen de
una firma del SDK viven en un archivo propio y versionado, `config/nombres_funciones.txt`, con una linea
`0xDIRECCION Nombre  # origen: ...` por funcion (se ignoran las lineas vacias y las que empiezan por `#`). El comando
lo lee con `--nombres` y aplica cada nombre a la funcion que empieza en esa direccion:

```text
python -m tools.ghidra simbolos --funciones <funciones.csv> --salida config/symbols.txt --nombres config/nombres_funciones.txt --exe <SLUS_008.38>
```

Reglas (`tools/ghidra/nombres.py`):

- Un nombre oficial del SDK identificado por firma, y `main`, tienen prioridad: si el archivo propone otro nombre
  para esa direccion no se aplica y el comando informa del choque (`firma`). Si propone el mismo nombre no hay choque.
- Un nombre que ya usa otro simbolo (de firma, por defecto `func_<direccion>` o del propio archivo) tampoco se aplica
  (`repetido`); una direccion que no es inicio de funcion se informa como `sin funcion`.
- El archivo se valida entero antes de usarlo: cada linea debe tener direccion de ocho digitos hexadecimales e
  identificador C valido, y ni una direccion ni un nombre pueden repetirse.

Contenido actual: 76 nombres, de la descompilacion de la version de PC del juego usada solo como referencia
semantica, verificados contra nuestro desensamblado (el codigo de condicion o de accion de PC es el indice de las
tablas `0x8005E3F0` y `0x8005E560`, la rutina de ese indice esta en la direccion indicada y la semantica coincide).
Son 75 rutinas del juego (condiciones `Cond*` y acciones `Action*` del interprete de eventos, sus dos despachadores
`TestLogicCond` y `RunLogicAction`, `BugsRand` y las cinco rutinas de la lista de nodos) y `TransMatrix`. Cuatro de
ellas (`TestLogicCond`, `RunLogicAction`, `ActionAddgi`, `ActionSubgi`) se comportan distinto en PC y PS1, pero su
nombre es correcto y se aplican. Se excluyen tres nombres dudosos hasta comprobarlos (`CondTpnmv`, `CondTpmov`,
`GsSetProjection`). Con este archivo la regeneracion aplica los 76 y no tiene choques.

Cambiar un nombre exige regenerar la tabla y renombrar el codigo que lo cita: las definiciones, los prototipos, las
llamadas y las lineas `INCLUDE_ASM` de `src/` e `include/` (el ensamblador de `asm/nonmatchings/` se regenera con
`split`). La documentacion historica (este documento, `docs/SUBSISTEMAS.md`, `docs/ARCHIVOS_ORIGEN.md`) sigue
citando las funciones por su nombre automatico `func_<direccion>`; la correspondencia esta en el archivo de nombres.

## Analisis derivado de la exportacion

Los comandos `borradores`, `grafo`, `subsistemas` y `limites` de `python -m tools.ghidra` producen, fuera del
repositorio, borradores en C con `m2c` (con un contexto de tipos que sale de las firmas de Ghidra y de los
tamanos de `xrefs_datos.csv`), el grafo de llamadas y de datos compartidos y la caracterizacion de subsistemas.
Trabajan sobre una copia propia del desensamblado generada con `splat` a partir de `config/symbols.txt`, no
sobre `asm/`. Sus resultados publicados se calcularon con la tabla de 908 simbolos.
Los resultados y su lectura estan en `docs/SUBSISTEMAS.md` y `docs/ARCHIVOS_ORIGEN.md`.

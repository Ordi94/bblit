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
- La tabla definitiva tiene 908 simbolos tras la depuracion anterior.
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

## Simbolos adicionales

`config/simbolos_adicionales.txt` se lee despues de `config/symbols.txt` y aisla como simbolos propios rutinas
que la tabla principal tiene fundidas dentro de otra, para poder pasar a C las que ya coinciden. Hoy reduce
`func_8002F9F8` a los `0x40` bytes que le corresponden (el despachador por codigo de operacion). La tabla
principal no se modifica en esa tarea, de modo que las dos tablas suman 914 simbolos de funcion (908 mas 6).

Pendiente: los tramos `func_8002FA60`, `func_8002FB38` y `func_80030DA4` siguen fundidos (cada uno agrupa varias
rutinas hoja alcanzadas solo por la tabla de saltos de `0x8005E3F0`) a la espera de separarse en la tabla
principal. `func_80030ECC` tiene la misma forma con su tabla de `0x8005E560`.

## Analisis derivado de la exportacion

Los comandos `borradores`, `grafo`, `subsistemas` y `limites` de `python -m tools.ghidra` producen, fuera del
repositorio, borradores en C con `m2c` (con un contexto de tipos que sale de las firmas de Ghidra y de los
tamanos de `xrefs_datos.csv`), el grafo de llamadas y de datos compartidos y la caracterizacion de subsistemas.
Trabajan sobre una copia propia del desensamblado generada con `splat` a partir de `config/symbols.txt`, no
sobre `asm/`; por eso no ven `config/simbolos_adicionales.txt` (la copia propia trata `func_8002F9F8` completa).
Los resultados y su lectura estan en `docs/SUBSISTEMAS.md` y `docs/ARCHIVOS_ORIGEN.md`.

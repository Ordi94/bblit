# Formato de los contenedores `.BZZ`

Especificacion del contenedor de niveles, menus, pantallas de carga y escenas de
*Bugs Bunny: Lost in Time* (PlayStation, SLUS-00838), escrita a partir del ejecutable
`SLUS_008.38` y de los 108 archivos `.BZZ` del disco. Las direcciones `0x8001xxxx` a
`0x8006xxxx` son direcciones de memoria del ejecutable (base de carga `0x80014A00`).

La implementacion de referencia es el paquete `tools/bzz/` (`python -m tools.bzz`).

## 1. Contenedor

Todo es little endian. El archivo se compone de un sector de cabecera y de las secciones,
cada una alineada a sectores de 0x800 bytes.

| Offset | Tamano | Campo | Descripcion |
|---|---|---|---|
| 0x000 | u32 | `version` | Siempre 1. |
| 0x004 | u32 | `n_secciones` | 3, 4 o 10 en el disco; el lector admite 1 a 64. |
| 0x008 | 12 x n | tabla de secciones | Por entrada: `u32 tipo`, `u32 tamano`, `u32 tamano_alineado`. |
| (tras la tabla) | | relleno | Ceros hasta el offset 0x7FC. |
| 0x7FC | u32 | `suma_control` | Suma de los bytes 0x000-0x7FB tomados como enteros **con signo**, a 32 bits. |
| 0x800 | | seccion 0 | Primera seccion. |

Reglas, verificadas en los 108 archivos (742 secciones):

- `tamano` es la longitud del flujo comprimido (multiplo de 4 en todos los casos observados);
  `tamano_alineado` es el menor multiplo de 0x800 que lo contiene.
- La seccion `i` empieza en `0x800 + suma(tamano_alineado[0..i-1])`; el relleno entre `tamano` y
  `tamano_alineado` son ceros.
- `0x800 + suma(tamano_alineado)` es exactamente el tamano del archivo.
- `tipo` vale de 1 a 10. Los archivos de pantallas de carga (`LOADING/`) traen tipos 1, 3 y 4;
  los menus y escenas, 1 a 4; los niveles jugables, los diez tipos.
- La suma de control la calcula `func_80041238` (`0x80041238`) y el cargador la compara en
  `0x80041850` con la palabra de `0x7FC`.
- El orden de las secciones en el archivo no es el de los tipos: en los niveles jugables es
  `1, 2, 3, 6, 5, 7, 8, 9, 10, 4`.

La funcion que carga un archivo es `0x800415A0` (recibe el indice de archivo y el buffer de
destino). Localiza el archivo en la tabla de archivos del ejecutable (113 entradas), lee el
sector de cabecera, valida la suma de control y recorre la tabla de secciones. Por cada
seccion llama al descompresor desde `0x80041920`, `0x800419D0`, `0x80041A0C` y `0x8004225C`.
Si el identificador de archivo no existe imprime `BouzeID %d not found`.

## 2. Flujo comprimido de una seccion

Todas las secciones estan comprimidas, sin excepcion. El descompresor es la funcion
`0x80044664` (`origen`, `destino`, `area de guardado`), con la lectura de sectores
(`0x80044854`) integrada en el bucle; devuelve en `v0` la direccion final de la salida.
El area de guardado es el scratchpad (`0x1F800000`), donde se salvan registros y se construye
la tabla de longitudes. El algoritmo es un LZSS con ventana de 4 KB y banderas por bit.

### 2.1 Cabecera del flujo (4 bytes)

| Byte | Significado |
|---|---|
| 0 | Parametros. Bits 0-2: `k`. Bits 3-4: `escala`. Bits 5-7: cero. En el disco vale siempre `0x0B` (`k = 3`, `escala = 1`). |
| 1-3 | `n` en **big endian** (24 bits). El flujo contiene `n + 1` operaciones. |

`k` reparte los 16 bits de cada referencia: los `9 + k` bits altos son la distancia y los
`7 - k` bits bajos son el indice de longitud. Con `k = 3`: distancia de 12 bits (1 a 4095) e
indice de 4 bits (0 a 15).

Esto explica los bytes iniciales observados: `0B` es el byte de parametros y los tres
siguientes el numero de operaciones menos uno; lo que sigue ya es el primer byte de banderas
(`FF`, `7F`, `1F`...) y los literales de la estructura descomprimida, que por eso se repiten
entre archivos del mismo tipo (`ff 2d 45 00` en el tipo 1, `bd 00 00 10` en el 2, etc.).

### 2.2 Tabla de longitudes

Se construye una vez por flujo, con `mascara = 0x7F >> k` y `umbral = mascara >> 1`
(el original usa 19 como umbral cuando `mascara >= 31`, es decir `k < 3`; ningun archivo del
disco lo usa y no se implementa):

```
para indice en 0 .. mascara:
    si indice <= umbral:  extra = indice
    si no:                extra = umbral + ((indice - umbral) << escala)
    longitud[indice] = 3 + extra
```

Con `k = 3, escala = 1` resulta `3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 22, 24, 26`. En el
ensamblador cada entrada guarda `extra + 2` y la copia repite `entrada + 1` bytes.

### 2.3 Bucle de operaciones

```
posicion = 4;  banderas = 0;  restantes = n + 1
mientras restantes > 0:
    restantes -= 1
    si banderas <= 1:                        # se agotaron los 8 bits (solo queda el centinela)
        banderas = origen[posicion] | 0x100; posicion += 1
    bit = banderas & 1;  banderas >>= 1      # bit menos significativo primero
    si bit == 1:                             # literal
        salida.agregar(origen[posicion]); posicion += 1
    si no:                                   # referencia
        codigo   = (origen[posicion] << 8) | origen[posicion + 1]    # big endian
        posicion += 2
        distancia = codigo >> (7 - k)
        longitud  = tabla[codigo & (0x7F >> k)]
        copiar `longitud` bytes desde salida[-distancia:], byte a byte hacia adelante
```

- La copia es byte a byte, de modo que si `distancia < longitud` la referencia se solapa
  consigo misma y repite el patron de `distancia` bytes (como un RLE).
- El flujo se lee de forma contigua a traves de los sectores: el cambio de sector del
  original (`0x80044854`, que espera al CD y avanza el puntero de lectura 0x800 bytes) no
  altera los datos.
- La longitud descomprimida no esta declarada en el contenedor: la determina el numero de
  operaciones. Cada operacion produce 1 byte (literal) o entre 3 y 26 (referencia).

### 2.4 Fin del flujo y referencia de distancia 0

En 103 de las 742 secciones la ultima de las `n + 1` operaciones es una referencia de
**distancia 0**: en 102 el codificador no la escribio y el decodificador la lee de los ceros de
relleno del sector (`00 00`, longitud 3), y en una esta escrita de forma explicita (`00 01`,
longitud 4). En el original esa referencia copia memoria de salida todavia sin escribir, de
modo que su contenido no esta definido (depende de lo que hubiera antes en el buffer de
destino). En las 639 secciones restantes la ultima operacion es una operacion real.

El descompresor de `tools.bzz` acepta una referencia de distancia 0 solo como **ultima**
operacion y la omite (la longitud descomprimida queda sin esos 3 o 4 bytes). Una distancia 0
en cualquier otra posicion, una distancia mayor que lo ya producido o un flujo que se acaba
antes de cumplir sus operaciones son errores.

`tamano` es la longitud del flujo redondeada a multiplo de 4, y la ultima operacion puede
leer unos bytes de relleno, asi que la diferencia `bytes consumidos - tamano` va de -3 a +3 en
las 742 secciones. Aparece +1 incluso sin relleno de distancia 0 (78 secciones): el redondeo del
original no siempre es hacia arriba. `descomprimir_secciones` rechaza una diferencia mayor de 3 en valor absoluto
porque delata un `n` corrupto (un `n` menor al real termina antes y dejaria datos truncados).

### 2.5 Cotas del lector

`leer_cabecera` y `descomprimir` no confian en la entrada: rechazan cualquier campo fuera de
rango (version, numero de secciones, tipo, tamanos, alineacion, suma de control, bits
reservados), nunca leen fuera del flujo y limitan la salida a 64 MiB por defecto. Los mensajes
nombran el campo y el valor esperado.

## 3. Salida de `desempaquetar`

`python -m tools.bzz desempaquetar <archivo.bzz> <carpeta>` escribe por cada seccion
`<indice:02d>_tipo<tipo:02d>.bin` con los bytes descomprimidos y un `manifiesto.json`:

```json
{
  "archivo": "L01A.BZZ",
  "version": 1,
  "secciones": [
    {"indice": 0, "tipo": 1, "offset": 2048, "tamanoComprimido": 28760,
     "tamanoAlineado": 30720, "tamanoDescomprimido": 100205, "sha256": "..."}
  ]
}
```

`python -m tools.bzz inventario <carpeta_fs> <salida.csv>` recorre todos los `.BZZ` y escribe
una fila por seccion (`archivo, indice, tipo, offset, tamano_comprimido, tamano_descomprimido,
sha256, segundos`).

## 4. Contenido por tipo

Medido sobre las 742 secciones descomprimidas (157.558.875 bytes en total).

| Tipo | Secciones | Tamano descomprimido | Contenido | Como se identifico |
|---|---|---|---|---|
| 1 | 108 | 228 a 118.699 | Script de carga y tablas de metadatos del archivo. | Comandos con prefijo `-` (0x2D) cerrados por `.`; marcas `.-IJ`, `.-\x00\x01`, `.-)*`. |
| 2 | 76 | 17.072 a 17.080 | **Codigo MIPS** (modulo de codigo cargado en memoria), 3 variantes. | Prologos `addiu sp,sp,-N`, `jr ra`, destinos `jal` internos; el ejecutable llama a sus puntos de entrada. |
| 3 | 108 | 107.784 a 1.016.247 | Banco de sonido, tablas de textos en seis idiomas e imagenes TIM, concatenados. | Las tablas del tipo 1 apuntan aqui; cada entrada de imagen empieza con cabecera TIM. |
| 4 | 108 | 56 a 1.342.066 | Tablas de registros del nivel o la escena (con 382 imagenes TIM incrustadas). | Cabecera de offsets (`0x108` en los niveles) y registros de 24 bytes. Semantica sin identificar. |
| 5 a 10 | 57 cada uno | 13.716 a 189.532 | Seis bancos con la misma cabecera y el mismo formato de registros que el tipo 4; solo en niveles jugables. Sin imagenes ni codigo. | Misma cabecera de offsets (`0x108` seguido de un tamano), registros de 24 bytes. Semantica sin identificar. |

El identificador de un archivo es su índice en la tabla de sectores de `0x8005EE78` (entrada = `LBA, tamaño`; las
dos últimas son los audios XA). Para los 108 archivos `.BZZ` del disco la entrada coincide con su posición y su
tamaño en el disco; por ejemplo, la 51 (`0x33`) es `LEVEL5\MERLIN.BZZ`, de 1.581.056 bytes.

### Tipo 1: script y tablas

- Los 76 archivos con tipo 2 empiezan por `2D 45 00 2E` (`-E`, indice 0, `.`); los 32 sin tipo 2
  (todos de `LOADING/`) empiezan por `2D 3B 3C FF`. El comando `E <indice>` ordena descomprimir
  a continuacion la seccion siguiente del archivo en el destino `tabla_destinos[indice]` (tabla en `0x80067E98`); el
  indice 0 es `0x80010200`, donde vive el codigo del tipo 2. Tras descomprimir, el cargador
  escribe en la primera palabra del destino el puntero `0x8006B2F8`.
- `.-IJ` (`2E 2D 49 4A`): a partir de +4, seis pares `u32 offset, u32 longitud` (uno por idioma)
  dentro de la seccion de tipo 3. Presente en 65 archivos.
- `.-\x00\x01` (`2E 2D 00 01`): el par `u32 offset, u32 longitud` del banco de sonido esta en +0xD,
  tambien dentro de la seccion de tipo 3. Presente en 72 archivos.
- `.-)*` (`2E 2D 29 2A`): desde +3, entradas de 9 bytes: `0x2A` y `u32 offset, u32 longitud`
  de cada imagen en la seccion de tipo 3. Presente en los 108 archivos (23.455 imagenes).

### Tipo 2: codigo

Ver la seccion 5.

### Tipo 3: sonido, textos, imagenes

- **Imagenes:** las 23.455 entradas de la tabla `.-)*` empiezan con la cabecera TIM
  (`10 00 00 00` y flags). Flags 8 (4 bpp con paleta): 21.911; flags 9 (8 bpp con paleta):
  1.512; flags 2 (16 bpp): 32. En las pantallas de carga la seccion empieza directamente por
  una TIM.
- **Textos:** cada idioma es una tabla de `u16` de offsets crecientes (el primero, dividido
  por 2, da el numero de cadenas) seguida de cadenas terminadas en cero.
- **Sonido:** datos SPU-ADPCM de bloques de 16 bytes, sin cabecera `VAGp`; empieza con un
  bloque de ceros. La longitud siempre es multiplo de 16.

## 5. Modulo de codigo (tipo 2)

Existe en 76 de los 108 archivos (todos los niveles jugables, bonus, demos, creditos, titulo
y el archivo de idioma) en tres variantes de 17.076, 17.072 y 17.080 bytes. Se carga en
`0x80010200`, justo debajo del ejecutable (`0x80014A00`); ocupa 0x42B4 de los 0x4800 bytes
disponibles. Las tres variantes comparten direccion y estructura (prologos en +0x58, +0x9A4 y
+0x27B4, 39 `jr ra`).

El ejecutable lo llama por direcciones fijas: `0x80010204`, `0x8001020C`, `0x80010258`,
`0x80012AB0` y `0x80012AE4`. El modulo lee en `0x80010200` (palabra que escribe el cargador)
el puntero a una estructura del ejecutable y accede a sus datos desde ahi; no hace llamadas
`jal` ni `jalr` al ejecutable.

## 6. Validacion

El descompresor se contrasto byte a byte con una herramienta comunitaria independiente
(`toolBZZ` 1.4) en los 108 archivos: las 742 secciones coinciden. La unica diferencia es el
relleno de distancia 0 de la seccion 2.4, que esa herramienta rellena con memoria sin inicializar.

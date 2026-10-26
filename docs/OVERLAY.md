# Overlay de código

El juego carga en `0x80010200`, justo debajo del ejecutable principal (`0x80014A00`), un bloque
de código MIPS de unos 17 KB que no está en `SLUS_008.38`: viaja comprimido dentro de la sección
de tipo 2 de 76 de los 108 contenedores `.BZZ` (todos menos `LOADING/`) y existe en tres
variantes. Este documento describe cómo se extrae, cómo se particiona y se reconstruye byte a
byte, qué contiene y cómo lo carga el ejecutable. La implementación es el paquete `tools/overlay/`
(`python -m tools.overlay`).

## 1. Comandos

```text
python -m tools.overlay extraer     # lee el disco y escribe expected/overlay/<variante>.bin y config/overlay.json
python -m tools.overlay simbolos    # regenera config/symbols_overlay.txt desde los binarios extraídos
python -m tools.overlay split       # splat: genera asm/overlay/<variante>/ y el script del enlazador
python -m tools.overlay build       # ensambla y enlaza: build/overlay/<variante>.bin
python -m tools.overlay verify      # compara byte a byte; imprime OK o FAIL con el desplazamiento y devuelve 0 o 1
python -m tools.overlay ram <vol>   # indica qué variante contiene un volcado de la RAM completa
```

`split`, `build` y `verify` aceptan `--variante a|b|c|todas` (por defecto, todas). El disco se
resuelve igual que en el resto de herramientas (`--disc`, `BBLIT_DISC` o `config/local.toml`) y
admite el `.bin`, el `.cue`, la carpeta que contiene la imagen o una carpeta con el sistema de
archivos ya extraído (`fs/`). Con `fs/` se leen los `.BZZ` de ahí; si no, se recorre el sistema
ISO 9660 de la imagen. Ambos caminos producen archivos idénticos.

Orden de uso: `extraer`, `simbolos` (solo si cambió la extracción), `split`, `build`, `verify`.

Las carpetas del overlay (`asm/overlay/`, `expected/overlay/` y `build/overlay/`) sobreviven a
`python tools/build.py split` y `clean` del ejecutable: solo `python -m tools.overlay` las toca. El
overlay escribe únicamente dentro de esas carpetas y de `config/`.

## 2. Variantes extraídas

`extraer` descomprime únicamente la sección de tipo 2 de cada contenedor (el descompresor de
`tools/bzz`), agrupa por SHA-256, contrasta el resultado con las tres variantes conocidas y escribe
`config/overlay.json` (huella, tamaño y contenedores de cada variante). Si aparece una huella
desconocida, falta una variante o cambia el número de contenedores, falla con un error: una
edición distinta del juego no se acepta en silencio.

| Variante | Bytes | SHA-256 | Contenedores |
|---|---|---|---|
| `a` | 17 076 | `3e45e436f793ec642361caf2c0d371b0d2482bb6a01f3bdbcfa5424dbbdf43d7` | 48 |
| `b` | 17 072 | `9b5b5e2c1a05b7f6daef69281025abff8622203976a37a33b09d976891b82491` | 24 |
| `c` | 17 080 | `67cbfff30aa3d00b66f04e60aac8c50f182e3bc7251d5114d859355ee8ac8538` | 4 |

Dos corridas producen archivos idénticos (el orden de los contenedores es el alfabético de su
ruta relativa y el JSON se serializa con orden fijo).

### Qué variante trae cada grupo de contenedores

| Carpeta | `a` | `b` | `c` |
|---|---|---|---|
| `BONUS` | 1 | 2 (`LB02`, `LB04`) | |
| `CC` (incluye introducción y créditos) | 17 | | |
| `DEMO` | | 2 (`DEMO3C1`, `DEMO4A1`) | 3 (`DEMO2A2`, `DEMO5C`, `DEMOB02`) |
| `LEVEL1` | 7 (incluye `TITLE`) | | 1 (`LANGUAGE`) |
| `LEVEL2` | 9 | 3 (`L02A5`, `L02A6`, `L02C2`) | |
| `LEVEL3` | 2 (`L03A`, `L03D1`) | 6 | |
| `LEVEL4` | 4 | 9 | |
| `LEVEL5` | 8 | 2 (`L05A4`, `MERLIN`) | |
| Total | 48 | 24 | 4 |

La lista completa está en `config/overlay.json`.

## 3. Estructura

Es un binario crudo (sin cabecera PS-X EXE) cargado en `0x80010200`. Disposición de la variante
`a`; las otras difieren como se indica en la sección 6.

| Desplazamiento | Dirección | Contenido |
|---|---|---|
| `0x0000` | `0x80010200` | Ranura de 4 bytes. En el archivo vale cero; el cargador escribe ahí `0x8006B2F8` (sección 5). |
| `0x0004` | `0x80010204` | `j 0x80010BA4` y su ranura de retardo: vector de entrada. |
| `0x0004`–`0x2954` | `0x80010204` | Código: 35 funciones, de las cuales 5 son puntos de entrada del ejecutable (sección 4). Termina con el `jr ra` de `0x294C` y su ranura de retardo. |
| `0x2954`–`0x2A34` | `0x80012B54` | Tabla de 56 punteros a rutinas del propio overlay (destinos de un salto indirecto). La mayoría de las entradas apuntan a `0x80012AA0`, un bucle de captura (`break 1` seguido de un salto a sí mismo) que hace de caso por omisión. |
| `0x2A34`–`0x2E34` | `0x80012C34` | 1 024 bytes de ceros (reserva de trabajo). |
| `0x2E34`–`0x32B4` | `0x80013034` | Tabla de 576 halfwords: `0`, una rampa de 62 valores de `0x40` a `0xF80` (de 64 en 64), 512 entradas saturadas a `0x1000` y un cero final. |
| `0x32B4`–`0x3AB4` | `0x800134B4` | Tabla de 512 palabras de color gris de 24 bits: 449 valores `0x00FFFFFF` y después un descenso de 4 en 4 desde `0x00FCFCFC` hasta `0x00040404`. |
| `0x3AB4`–`0x42B4` | `0x80013CB4` | 2 048 bytes de ceros (reserva de trabajo). |

Los ceros son bytes reales del archivo: el cargador copia el bloque tal cual y el binario
reconstruido debe contenerlos.

El análisis previo hablaba de una «tabla de punteros en el desplazamiento `0x2E94`». No lo es: esa
posición cae dentro de la rampa de halfwords y las siete palabras con forma de `jal` son datos
(`0x0C400C00`, `0x0CC00C80`...). Los datos del ejecutable se alcanzan por la tabla de la sección 5.

### Código

El código está escrito a mano en ensamblador (no hay marcos de pila salvo en tres funciones, y el
particionador marca 24 de las 36 piezas como «Handwritten function», entre ellas todas las de
0x100 bytes o más). Usa el coprocesador GTE de forma intensiva (348 transferencias `mtc2`, `mfc2`,
`ctc2`, `cfc2`, `lwc2` y `swc2`, además de órdenes de cálculo como `dpcs`), así que es código de
tratamiento de geometría y color, no de lógica de juego. No usa `jalr` ni `jal` hacia el ejecutable: toda la comunicación con él es por datos.

Estructura de funciones (direcciones iguales en las tres variantes; tamaños en bytes):

| Dirección | Tamaño | Notas |
|---|---|---|
| `0x80010200` | 4 | Ranura del cargador (se declara como función de un `nop` para que el resto siga siendo texto). |
| `0x80010204` | 8 | Vector: salta a `0x80010BA4`. |
| `0x8001020C` | 0x4C | Parchea seis instrucciones (sección 4). |
| `0x80010258` | 0x5C4 | Función grande con GTE (prólogo en `0x80010258`). |
| `0x8001081C`, `0x8001083C`, `0x80010880`, `0x800108D4` | 0x20, 0x44, 0x54, 0x2D0 | Rutinas locales (destinos de `jal`). |
| `0x80010BA4` | 0x734 | Función grande con GTE (prólogo de 0x28 bytes). |
| `0x800112D8`, `0x800112F8`, `0x80011340`, `0x80011394`, `0x800113E4`, `0x8001142C`, `0x8001147C` | 0x20, 0x48, 0x54, 0x50, 0x48, 0x50, 0x48 | Rutinas locales. |
| `0x800114C4` | 0x57C | Función grande. |
| `0x80011A40`, `0x80011A9C`, `0x80011B00`, `0x80011C1C`, `0x80011C8C`, `0x80011D10`, `0x80011D40`, `0x80011E40`, `0x80011F70`, `0x80011F88`, `0x80011FA4` | 0x5C, 0x64, 0x11C, 0x70, 0x84, 0x30, 0x100, 0x130, 0x18, 0x1C, 0x100 | Rutinas locales. |
| `0x800120A4`, `0x8001251C`, `0x80012558` | 0x478, 0x3C, 0x358 | Una función grande, una pequeña y otra grande. |
| `0x800128B0`, `0x8001294C`, `0x800129B4` | 0x9C, 0x68, 0xF8 | La última tiene prólogo de pila y cierra con un bucle de captura (`0x80012AA0`). |
| `0x80012AB0` | 0x34 | Punto de entrada: escribe un paquete (sección 4). |
| `0x80012AE4` | 0x70 | Punto de entrada: escribe un paquete (sección 4). |

La lista exacta de funciones es `config/symbols_overlay.txt`: la ranura más 35 funciones. Salen
de: el destino del salto del vector (`0x80010BA4`), los cinco puntos de entrada, los 29 destinos
de `jal` internos y los tres prólogos `addiu sp,sp,-N` (muchos coinciden). Un único archivo sirve
a las tres variantes porque todas las direcciones de inicio de función coinciden; lo que cambia
entre variantes cae dentro de cuerpos y en las tablas posteriores al código, que no llevan símbolo.

## 4. Puntos de entrada que invoca el ejecutable

El ejecutable llama con `jal` a cinco direcciones del overlay (nueve llamadas: 3, 2, 2, 1 y 1;
los llamantes se dan por dirección de la instrucción `jal`):

| Entrada | Desplazamiento | Qué es | Llamadas desde |
|---|---|---|---|
| `0x80010204` | `0x4` | Vector `j 0x80010BA4`: entra a la función grande de `0x734` bytes. | `0x8003B310`, `0x8003B3C0`, `0x8003C16C` |
| `0x8001020C` | `0xC` | Escribe el halfword bajo de `$a0` en el campo de desplazamiento de seis ramas `blez` de la función `0x80010258` (en los desplazamientos `0x1A4`, `0x260`, `0x330`, `0x3EC`, `0x4B4` y `0x57C`): fija el límite de unos bucles. Es código automodificable. | `0x800163A8`, `0x800163C0` |
| `0x80010258` | `0x58` | Función grande con GTE. | `0x80039B98`, `0x8003C188` |
| `0x80012AB0` | `0x28B0` | Escribe en la lista de ordenación un paquete de dos palabras con el comando GP0 `0xE1000620` (ajuste del modo de dibujo) y devuelve el puntero siguiente. | `0x8003B95C` |
| `0x80012AE4` | `0x28E4` | Escribe un paquete de seis palabras con el comando GP0 `0x2A` (polígono plano semitransparente de cuatro vértices) con el color recibido y cuatro vértices fijos de pantalla completa (`x` de -256 a 256, `y` de -120 a 120); devuelve el puntero siguiente. | `0x8003B948` |

Las dos primeras funciones grandes (`0x80010258` y `0x80010BA4`) toman como base de datos
`$fp = *(0x80010200)`, es decir, el valor que escribe el cargador (sección 5).

## 5. Tabla de enlace con el ejecutable

El primer word del overlay (`0x80010200`) contiene `0x8006B2F8` tras la carga. Las dos funciones
grandes de `0x80010258` y `0x80010BA4` abren con `lui $fp,0x8001 ; lw $fp,0x200($fp)` y a partir de ahí leen punteros a datos del
ejecutable en esa tabla. `0x8006B2F8` es una tabla de 23 palabras (0x5C bytes) de punteros a
`0x8006xxxx`; el overlay usa los campos en los desplazamientos `0x10`, `0x14`, `0x18`, `0x1C`,
`0x20`, `0x24`, `0x28`, `0x2C`, `0x30`, `0x34`, `0x38`, `0x4C`, `0x54` y `0x58`. Es el único
contrato de datos entre el overlay y el ejecutable. Su contenido es idéntico en los dos volcados de
RAM comprobados.

## 6. Diferencias entre variantes

Las tres comparten todo el código salvo estas diferencias (desplazamientos dentro del overlay):

| Cambio | `a` | `b` | `c` |
|---|---|---|---|
| Inmediatos de dirección de tablas en `0x154`, `0x6D8`, `0xBD8`, `0x1844` (`addiu ...,0x2Bxx/0x2Cxx`) y en `0x1B50`, `0x1BE4`, `0x1C50`, `0x1D04`, `0x1DB4`, `0x1E48`, `0x1EB4`, `0x1F6C` (`addiu $s7,$s7,0x3034/0x3BB4`) | base | −4 | +4 |
| `sub $a2,$a2,$s7` en `0x6E0` y `0x184C` | `sub` | `subu` | `sub` |
| `slti $at,$a2,N` en `0xC4C`, `0xDDC`, `0xFA4`, `0x135C`, `0x1508`, `0x16B8` | `0x81` | `0x21` | `0x81` |
| `addiu $v0,$v0,0x180` en `0x28FC` (función `0x80012AE4`) | presente | ausente | presente |
| Palabra de relleno tras el código (`0x2954`) | no | no | sí (un `nop`) |
| Entradas saturadas a `0x1000` de la tabla de halfwords | 512 | 512 | 256 (las otras 256 valen 0) |

Consecuencias: en `b` el código termina 4 bytes antes (`0x2950`) y todas las tablas empiezan 4 bytes
antes, y en `c` empiezan 4 bytes después (`0x2958`); por eso cambian los inmediatos que las
direccionan. Los inicios de función son los mismos. Las diferencias de comportamiento son tres
parámetros: aritmética con o sin captura de desbordamiento, un umbral de comparación (128 en `a` y
`c`, 32 en `b`) y la posición del paquete de pantalla completa en la lista de ordenación, más el
recorte de la tabla de saturación en `c`.

## 7. Mecanismo de carga

La rutina `0x800415A0` carga un contenedor `.BZZ` (recibe el índice del archivo y el buffer de
destino; la llaman `main` en `0x80016494` y las funciones `0x8004452C`, `0x800445C8` y
`0x80044608`). Tras validar la suma de control (`0x80041238`, comparada en `0x80041850`):

1. `0x80041920`: `jal 0x80044664` descomprime la sección de tipo 1 (el script de carga) al buffer.
2. `0x80041930`–`0x80041958`: comprueba que el script empieza por `2D 45` (`-E`).
3. `0x8004197C`: por cada comando `E` lee el índice de destino (`0x8004198C`, `jal 0x80041264`) y
   toma el destino de la tabla `0x80067E98` (`0x800419A4`–`0x800419C4`). La entrada 0 vale
   `0x80010200`; las demás apuntan a datos del ejecutable (`0x8003C2F4`, `0x8003CA10`...).
4. `0x800419D0`: `jal 0x80044664` descomprime la sección siguiente (el overlay, tipo 2) directamente
   en el destino.
5. `0x800419D8`: `sw $s4,0($s0)` escribe `0x8006B2F8` en la primera palabra del destino, es decir,
   en `0x80010200`.

La ruta de carga con espera al CD hace lo mismo: destino tomado de `0x80067E98`
(`0x80041BB0`–`0x80041BC4`), espera a que el indicador `0x8006955E` quede a cero
(`0x80041BEC`–`0x80041C0C`) y escribe el puntero con `sw $t3,0($s0)` en `0x80041C18`.

Los 76 contenedores con overlay son exactamente los 76 cuyo script empieza por `-E 00`. Cada
carga de un contenedor sobrescribe el overlay anterior.

## 8. Qué variante hay cargada

`python -m tools.overlay ram <volcado>` compara el bloque `0x80010200` de un volcado de la RAM
completa (2 MiB, ver `docs/EMULADOR.md`) con las tres variantes. Se acepta como coincidencia que
solo difiera la primera palabra (la ranura del cargador).

| Volcado | Resultado |
|---|---|
| Pantalla de título | Coincide con la variante `a` (solo difiere la ranura: `0x8006B2F8`). Es la variante de `LEVEL1/TITLE`. |
| Partida en curso | Coincide con la variante `b` (solo difiere la ranura). |

Los seis sitios que parchea `0x8001020C` coinciden con el archivo en ambos volcados: o la rutina no
se había llamado todavía o escribió los mismos valores. La variante `b` no la trae ningún
contenedor de `LEVEL1` (`LEVEL1` trae `a` y `c`), así que el volcado de la partida no es de un
nivel 1 de ese directorio; para saber cuál de los 24 contenedores de `b` estaba cargado basta un
punto de ruptura en `0x800415A0` y leer el índice de archivo.

## 9. Partición y reconstrucción

- `config/splat_overlay_<variante>.yaml` particiona cada variante como un único segmento `code`
  con `vram: 0x80010200` y `start: 0`: código (`codigo`), tabla de saltos (`saltos`) y datos
  (`tablas`, que llegan al final del archivo). Cada variante tiene su propio archivo porque las
  fronteras de los datos cambian (`0x2954`/`0x2950`/`0x2958`).
- `config/symbols_overlay.txt` es común a las tres variantes y lo genera `simbolos`.
- `split` comprueba al terminar que cada función declarada produjo exactamente un `glabel`
  (36 por variante: la ranura y 35 funciones) y que el texto no contiene ninguna directiva `.word`
  (código sin decodificar). Los únicos `.word` del particionado son los de la tabla de saltos y las
  tablas de datos (56 y 1 568 líneas por variante).
- `build` ensambla con `as` (`-march=r3000 -mips1 -G0`) y enlaza con un script propio, generado a
  partir del que escribe splat: mismo orden de objetos y secciones, sin las alineaciones a 16 bytes.
  Esas alineaciones desplazarían la tabla de saltos, que empieza justo donde acaba el código
  (`0x2954`, no múltiplo de 16).
- `verify` compara `build/overlay/<variante>.bin` con `expected/overlay/<variante>.bin`:
  `OK <variante> sha256=... bytes=...` o `FAIL <variante> primera diferencia en el desplazamiento 0x...`.

## 10. Qué necesita la descompilación del overlay

- Casi todo el código es ensamblador escrito a mano con GTE, saltos por tabla y código
  automodificable (`0x8001020C`). Un compilador de C no reproducirá ese código byte a byte; lo
  realista es conservarlo como ensamblador en el repositorio (las tres variantes ya se
  reconstruyen desde `asm/overlay/`) y documentar sus funciones, no reescribirlas en C. Solo tres
  funciones tienen prólogo de pila (`0x80010258`, `0x80010BA4` y `0x800129B4`); son las únicas con
  forma de código de compilador, y las tres son grandes y usan GTE.
- Nombrar las funciones requiere entender el contrato de la tabla `0x8006B2F8` (sección 5): cada
  campo es un puntero a datos del ejecutable cuyo nombre y tipo hay que fijar en
  `config/symbols.txt`.
- Hay que decidir cómo se modelan las tres variantes en el código final: comparten el 99 % de los
  bytes y difieren en cuatro parámetros (sección 6), de modo que un solo fuente con las diferencias
  condicionadas por una constante por variante es suficiente.
- Identificar qué contenedor trae cada variante en tiempo de ejecución (sección 8) ayuda a saber
  cuándo importan las diferencias.

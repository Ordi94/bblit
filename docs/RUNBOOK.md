# Guia de ejecucion de extremo a extremo

Secuencia verificada para pasar de un checkout con el toolchain presente a un ejecutable
reconstruido, una imagen de prueba y su arranque en emulador. Todos los comandos se lanzan desde
la raiz del repositorio con `PYTHONUTF8=1` y el interprete `.venv\Scripts\python.exe`.

## 1. Preparacion

El generico de descompilacion vive en `kit/` (paquete `psxdecomp`, instalable por separado). Tras crear el
entorno virtual se instalan las dependencias (`requirements.txt` incluye el kit en modo editable) y se
comprueba el manifiesto:

```
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m psxdecomp.cli comprobar
```

La segunda orden valida `psxdecomp.toml`, el manifiesto del proyecto (rutas, zonas de memoria y
convenciones que el kit lee en vez de suponerlas). Las pruebas del proyecto y las del kit se lanzan juntas
con `python -m pytest`; las del kit solas, con cobertura del 100 %, con `python -m pytest` desde `kit/`.
Las pruebas del proyecto que ejercen el kit contra los datos reales (particion, compilacion, comparacion,
progreso y ciclo completo) estan en `tests/integracion_kit/`; la cobertura de ramas del codigo propio
(`tools/`) se mide con `python -m pytest tests --cov` y exige el 100 %.

```
set PYTHONUTF8=1
set BBLIT_DISC=<ruta al .bin, al .cue, a la carpeta del .bin, a la carpeta superior o a una carpeta con fs/>
.venv\Scripts\python.exe -m tools.toolchain instalar
```

La entrada preferente es `.venv\Scripts\python.exe -m psxdecomp.toolchain instalar` (mismo resultado; usa el
manifiesto de la carpeta actual o `--proyecto <raiz>`). `python -m tools.toolchain` se conserva por compatibilidad.

`instalar` es idempotente: con los componentes presentes solo verifica huellas y lista cada uno
como `vigente`, sin descargar.

## 2. Reconstruccion y verificacion

```
.venv\Scripts\python.exe tools\build.py clean
.venv\Scripts\python.exe tools\build.py split
.venv\Scripts\python.exe tools\build.py build
.venv\Scripts\python.exe tools\build.py verify
```

Resultado esperado: `OK` con SHA-256
`0fad70d9b4cb324d78f113f7fd70c0aa954388fefad01af373509e0473c87df0`. Todos los subcomandos
excepto `clean` necesitan la ubicacion del disco (incluido `verify`).

La entrada preferente es la del kit: `.venv\Scripts\python.exe -m psxdecomp.cli <subcomando>` desde la raiz del
repositorio (o con `--proyecto <raiz>`), con los mismos subcomandos, la misma salida y los mismos codigos de
retorno; la ayuda de cada uno nombra las rutas del manifiesto (`psxdecomp.toml`). `tools/build.py` sigue
funcionando igual y es la entrada que usan los scripts y las definiciones existentes: es un archivo de pocas
lineas que llama a la linea de ordenes del kit con el manifiesto del juego (misma ayuda, misma salida y
mismos codigos de retorno). `progreso` es una orden comun del kit y esta en las dos entradas. Los ganchos
`antes_de_construir` y `despues_de_verificar` del manifiesto (hoy vacios) se invocan desde ambas entradas.

### Progreso del README

```
.venv\Scripts\python.exe tools\build.py progreso
```

Mide el codigo del juego y reescribe, ademas de `docs/PROGRESO.md` y `build/progreso.json`, la
seccion «Progreso» del `README.md`, delimitada por `<!-- progreso:inicio -->` y
`<!-- progreso:fin -->` (si faltan, se inserta tras el primer parrafo). Lleva la fecha, el hash corto
del commit (`git rev-parse --short HEAD`), la tabla de cifras y los comandos para reproducirla.
La orden respeta los finales de linea del archivo y es idempotente. Con `--sin-readme` no toca el
README. Regenerarla antes de cada commit que cambie `src/`; el hash que muestra es el del commit
anterior, asi que el siguiente commit lo refresca. La orden es del kit (`psxdecomp.progreso`).

### Comparar una funcion

```
.venv\Scripts\python.exe tools\build.py diff <funcion>
.venv\Scripts\python.exe tools\build.py probar <funcion> <carpeta de variantes>
```

Cada ejecucion de `diff` y de `probar` trabaja en su propia carpeta dentro de `build/diff/`
(`<funcion>-<pid>-<sufijo aleatorio>`), la elimina al terminar y deja solo
`build/diff/<funcion>.resultado.json`, escrito de forma atomica. Por eso se pueden lanzar varias
comparaciones a la vez, sobre funciones distintas o del mismo archivo C, sin que se pisen el objeto
candidato ni la configuracion de `asm-differ`. Si una ejecucion se interrumpe a la fuerza puede quedar
una carpeta suelta en `build/diff/`; `clean` la elimina.

### Permutar una funcion

```
.venv\Scripts\python.exe tools\build.py permutar <funcion> [--iteraciones N] [--minutos M] [--procesos P] [--semilla S] [--reanudar]
```

Busca por mutaciones la forma de C que hace coincidir una funcion `NON_MATCHING`: toma su C vigente, genera
variantes que conservan su significado, compila y puntua cada una con la misma cadena y la misma cifra que
`diff` y avanza por escalada con reinicios aleatorios. Necesita `split` y un `build` previo (el ELF de la ultima
construccion sirve para comparar bytes enlazados, igual que `diff`). Nunca escribe en `src/`.

- Limites: `--iteraciones` acota las variantes medidas y `--minutos` la duracion de la sesion; sin ninguno de
  los dos dura 10 minutos. `--procesos` (1 a 16) son las mediciones simultaneas: cada una usa su propia carpeta de
  `build/diff/`, como `diff`, y son hilos de un solo proceso, de modo que no queda nada vivo al terminar. Una
  medicion tarda cerca de un segundo; con 4 procesos son entre 6 y 8 variantes por segundo.
- `--semilla` fija la secuencia aleatoria (por omision se elige una y se imprime). Con la misma semilla, el
  mismo C y el mismo limite de iteraciones la busqueda repite las mismas variantes.
- Resultado en `build/permutar/<funcion>/`: `mejor.c` (definicion de la mejor variante, con un comentario que
  declara su puntuacion), `actual.c` (desde donde continua la escalada), `registro.jsonl` (una linea por
  mejora: iteracion, puntuacion y mutaciones) y `estado.json` (semilla y contadores). `clean` borra la carpeta.
- `--reanudar` continua la busqueda guardada con su semilla y sus contadores acumulados; `--iteraciones` y
  `--minutos` se aplican a la sesion nueva. Una interrupcion con Ctrl+C guarda el estado y deja un resumen.
  Sin `--reanudar` se descarta el estado anterior de la funcion.
- Salida: iteraciones, puntuacion de partida y mejor, ruta del candidato, variantes descartadas y tiempo.
  Codigo 0 si alguna variante llego a puntuacion 0, 1 si mejoro sin cerrar y 2 si no mejoro (los errores de uso
  se imprimen como `error: ...` y tambien salen con 1).

Como aplicar un candidato. `mejor.c` es una propuesta, no un parche: se lee antes de usarla.

1. Abrir `build/permutar/<funcion>/mejor.c` y copiar la definicion (todo salvo el primer comentario) sobre la de
   la rama `#ifdef NON_MATCHING` de `src/<archivo>.c`, sin tocar el `#else` con el `INCLUDE_ASM`.
2. `python tools/build.py diff <funcion>` debe dar la puntuacion que declara `mejor.c`. Si la cifra es 0 se
   quita el bloque `NON_MATCHING` y el `INCLUDE_ASM` (la funcion pasa a C) y se ejecutan `build` y `verify`; si
   no, se actualiza la linea `Pendiente: puntuacion N` del bloque.
3. Para comprobarlo sin tocar el arbol de trabajo, hacerlo en una copia del repositorio (con `asm/` y `build/`
   ya generados) y ejecutar `diff` ahi.

Limites. El analizador entiende el C que usa `src/` (declaraciones al inicio del bloque, `if`, bucles, `switch`,
`goto`, llamadas y macros de funcion, todos los operadores binarios, unarios y de asignacion de C con su
precedencia, moldes a tipos con calificadores o a punteros a arreglo o funcion y nombres de tipo como argumento
de una macro, y variables locales de puntero a funcion o a arreglo); un parametro declarado como arreglo, un
tipo de funcion, un comentario dentro de una expresion (entre los argumentos de una llamada, junto a un
operador o antes de una llave de control; solo se conservan los que abren una sentencia o cierran un bloque)
o una construccion fuera de ese subconjunto se rechazan con un mensaje en lugar de adivinarse. Las mutaciones suponen que dos
accesos con rutas de campo distintas (`a->x` y `b->y`) no se solapan; un cambio que dependa de ese supuesto
se revisa al leer el candidato. No cierra lo que solo cierra con un recurso que el proyecto no admite
(ensamblador en linea, `volatile`, `register`, barreras): para esas funciones el resultado es 2. Las
mutaciones que se usan y las que no estan en `docs/DESCOMPILACION.md`, seccion «Permutador».

## 3. Imagen de prueba

```
.venv\Scripts\python.exe -m tools.disco reempaquetar --imagen "<.bin>" --exe build\SLUS_008.38 --salida build
```

Necesita el ejecutable producido por `build`; `split` y `clean` lo eliminan. Si falta, termina con
codigo 2 y el mensaje `error: --exe: no existe el archivo indicado; ejecute 'python tools/build.py build'
antes de reempaquetar`. Lo mismo ocurre con una `--imagen` inexistente (sin la pista de `build`).

Con el ejecutable sin modificar: `0 de 249595 sectores modificados` y SHA-1
`6024341f559c3789b5612e941c8d0ab227ff6361`.

## 4. Simbolos

```
.venv\Scripts\python.exe -m tools.ghidra simbolos --funciones <funciones.csv> --nombres config/nombres_funciones.txt --salida <archivo symbols.txt>
```

`--salida` (igual que `--tablas` y `--nuevas`) es un **archivo**, no una carpeta: se reemplaza de forma
atomica y su carpeta se crea si falta. Si la ruta indicada es una carpeta existente el comando termina con
`error: --salida debe ser un archivo, no una carpeta` y codigo 2, sin escribir nada.

`<funciones.csv>` es el que produce `python -m tools.ghidra exportar` (carpeta de exportacion de Ghidra,
fuera del repositorio). Con `BBLIT_DISC` definida (cualquiera de las cinco formas: .bin, .cue, carpeta del .bin, carpeta superior o carpeta con fs/) o con `--exe`. Genera 1168 lineas
(1102 simbolos de funcion y 66 variables pequenas direccionadas por `$gp`; ver `docs/GHIDRA.md`) y aplica los
109 nombres de `config/nombres_funciones.txt` (un nombre repetido aborta con `error: nombres linea N`; uno que
choca con un nombre oficial del SDK se informa y no se aplica). El resultado debe ser identico a
`config/symbols.txt`.

## 5. Arranque en emulador

Ejecutar desde la raiz del repositorio (el emulador escribe `pcsx.json`, tarjetas de memoria y
`.sentry-native/` en el directorio de trabajo: borrarlos al terminar o lanzar desde otra carpeta
con rutas absolutas):

```
toolchain\pcsx-redux\pcsx-redux.exe -portable -loadiso build/bblit_prueba.cue ^
    -bios toolchain/duckstation/bios/ps-22a.bin -run -webserver -webserver-port 8080
```

`python -m tools.emulador` no necesita esos comandos a mano: resuelve el emulador y la BIOS igual que
`tools/build.py` resuelve el toolchain. Orden de prioridad: argumento (`--emulador`, `--bios`), variables
`BBLIT_REDUX` y `BBLIT_BIOS` (anulacion explicita), y por ultimo el toolchain: `BBLIT_TOOLCHAIN`, luego
`[rutas] toolchain` de `config/local.toml`, luego `<raiz del repositorio>/toolchain`
(`pcsx-redux/pcsx-redux.exe` y `duckstation/bios/ps-22a.bin`). Desde un worktree sin `toolchain/` basta con
`BBLIT_TOOLCHAIN`. Las rutas por defecto cuelgan de la raiz del repositorio (tambien la imagen
`build/bblit_prueba.cue` y la carpeta de trabajo `build/emulador`), no del directorio desde el que se lanza.

1. Comprobar que el puerto 8080 esta libre y que no hay procesos `pcsx-redux` previos.
2. `GET http://127.0.0.1:8080/api/v1/execution-flow` debe devolver `"running":true` (responde
   en menos de 1 s).
3. La BIOS tarda en ceder el control y hay fotogramas negros dentro del arranque; los tiempos
   medidos (tres corridas en frio, segundos desde el lanzamiento) son: `running` 1,0 a 1,2;
   primera captura no negra (logotipo Sony de la BIOS) 4,7 a 5,3; logotipo PlayStation 14,3 a
   14,8; ejecutable del juego en RAM 19,2 a 20,2; logotipo Infogrames 26,6 a 26,8; selector de
   idioma 40,1 a 40,5; pantalla de titulo 87,1 a 87,4. Un PNG negro puede pesar mas de 10 KB:
   validar por contenido (valores de pixel), no por tamano. Todo el arranque, la espera y el
   volcado estan automatizados: `python -m tools.emulador sesion --espera-hito ejecutable
   --exe-juego <SLUS_008.38> --salida <carpeta>` espera a que el juego este cargado en RAM, pausa,
   guarda `ram.bin` y `pantalla.png`, y apaga (detalle y tabla completa en `docs/EMULADOR.md`).
   Sin `--retardo` solo se garantiza el ejecutable en RAM; para que el overlay de codigo tambien este
   cargado (selector de idioma y titulo) usar `--retardo 70` (unos 93 s en total). Despues,
   `python -m tools.emulador comparar --volcado <ram.bin> --direccion 0x80014A00 --archivo build/SLUS_008.38
   --offset-archivo 0x800` da cerca de 99,6 % y, con `--direccion 0x80010200 --archivo expected/overlay/a.bin`,
   la variante `a` coincide salvo la primera palabra (4 bytes). Una imagen inexistente termina con
   `error: imagen: no existe el archivo indicado`, codigo 1 y sin procesos vivos.
4. `POST execution-flow?function=pause`, leer `cpu/ram/raw` (2.097.152 bytes) y
   `screen/still`, y `POST execution-flow?function=resume`.
5. Comprobacion de carga: en la RAM, el offset `0x14A00` (direccion `0x80014A00`) coincide con
   los bytes desde el offset `0x800` de `build/SLUS_008.38`.
6. Cerrar `pcsx-redux` y `pcsx-redux.main` (son dos procesos).

## 6. Overlay

El código que el juego carga en `0x80010200` (tres variantes) se reconstruye aparte, en este orden:

```
.venv\Scripts\python.exe -m tools.overlay extraer
.venv\Scripts\python.exe -m tools.overlay split
.venv\Scripts\python.exe -m tools.overlay build
.venv\Scripts\python.exe -m tools.overlay verify
```

Debe salir `OK` para las tres variantes (`a`, `b` y `c`) y `split` debe informar 36 funciones y 36 `glabel`
por variante, sin palabras sin decodificar. Detalles en `docs/OVERLAY.md`.

`clean` y `split` de `tools/build.py` no tocan `asm/overlay/`, `expected/overlay/` ni `build/overlay/`: el
overlay sigue verificable con `python -m tools.overlay verify` sin volver a extraer. Cada `build` borra antes
de empezar el ejecutable de la construccion anterior: si falla, `build/SLUS_008.38` no existe y `verify`
responde `FAIL el ejecutable reconstruido no existe` con codigo de salida 1, de modo que un ejecutable
obsoleto nunca se da por bueno. No hace falta `clean` entre un error de compilacion y el siguiente intento.

## 7. Analisis derivado

Con la exportacion de Ghidra en `<exportacion>` (que contiene `funciones.csv`) y las salidas en carpetas
fuera del repositorio:

```
.venv\Scripts\python.exe -m tools.ghidra grafo       --salida <carpeta> --exportacion <exportacion>
.venv\Scripts\python.exe -m tools.ghidra subsistemas --salida <carpeta> --exportacion <exportacion> --rangos <exportacion>\subsistemas_rangos.csv
.venv\Scripts\python.exe -m tools.ghidra borradores  --salida <carpeta> --exportacion <exportacion> --solo-rango
```

Resultado esperado: 1596 aristas y 262 de 262 llamadores coincidentes; 15 subsistemas; 256 funciones del
juego con borrador, 0 fallidas (unos 70 s). Cifras calculadas con la tabla anterior de 908 simbolos; con la
actual el rango del juego tiene 450 funciones.

## 8. Opciones de compilacion por archivo

`config/opciones_compilacion.toml` fija, por archivo `src/<nombre>.c`, las opciones del compilador (hoy el
umbral de datos pequenos `-G`; los archivos que no figuran compilan con `-G0`). `build`, `diff` y `probar` leen
ese mismo archivo, asi que compilan cada fuente con las mismas banderas. Si una funcion no coincide con `-G0`,
se prueba con el `g` del archivo antes de reescribir el C. Formato, archivos que hoy usan `g = 8` y criterio
para anadir uno nuevo: `docs/DESCOMPILACION.md`, seccion «Opciones de compilacion por archivo».

## 9. Linux (Wine)

Las herramientas corren en Linux (probado en Debian 13). El SDK original (`CPPPSX.EXE`, `CC1PSX.EXE`) son
ejecutables Win32: `kit/psxdecomp/toolchain/plataforma.py` los lanza con Wine fuera de Windows. Los binutils de MIPS
(`as`, `ld`, `objcopy`, `objdump`) no pasan por Wine: se usan binutils nativos del `PATH`, que arrancan en
milisegundos (un `.exe` bajo Wine paga el arranque del emulador en cada llamada, y una busqueda del permutador
hace miles). `maspsx` y `asm-differ` son Python y no cambian.

Importante: los binutils deben ser los mismos que usa el toolchain de Windows (GNU binutils 2.40,
`mipsel-none-elf`; PSn00bSDK v0.24 publica el build de Linux). Los `binutils-mipsel-linux-gnu` de Debian generan
objetos con secciones alineadas a 16 bytes en lugar de 4: el ejecutable sale 208 bytes mayor, `build` se detiene
con el aviso de `t_size` y nunca coincidiria byte a byte. `scripts/instalar_linux.sh` descarga los correctos
(verificando su SHA-256).

Paquetes Debian que instala el guion: `dpkg --add-architecture i386`, `apt-get update` y
`apt-get install wine wine32:i386 python3 python3-venv python3-pip git ca-certificates curl unzip`; ademas crea
`.venv` con `requirements.txt` e inicializa el prefijo de Wine.

Variables (cada `BBLIT_X` tiene el equivalente `PSXDECOMP_X`, que manda si ambas estan definidas):

| Variable | Por omision | Efecto |
|---|---|---|
| `BBLIT_TOOLCHAIN` | `toolchain/` | Carpeta con `psyq-4.4`, `maspsx` y `asm-differ` (los binutils del lock no se usan en Linux) |
| `BBLIT_DISC` | - | Ruta al `.bin` del disco (copia propia, nunca versionada) |
| `BBLIT_WINE` | `wine` | Ejecutable de Wine |
| `BBLIT_BINUTILS_PREFIX` | `mipsel-none-elf-` | Prefijo de los binutils nativos; sus carpetas `bin` van en el `PATH` |
| `WINEPREFIX` | `~/.wine` | Prefijo de Wine; `WINEDEBUG=-all` se fija solo si no esta definida |

Procedimiento:

```
bash scripts/instalar_linux.sh
export PATH="$HOME/.local/mipsel-none-elf/bin:$PATH" PYTHONUTF8=1
export BBLIT_TOOLCHAIN=/ruta/toolchain BBLIT_DISC=/ruta/disco.bin
.venv/bin/python tools/build.py split
.venv/bin/python tools/build.py build
.venv/bin/python tools/build.py verify
```

El resultado de `verify` es el mismo SHA-256 que en Windows. El toolchain se copia desde una instalacion de
Windows (`tar` conserva los nombres); la busqueda de los `.EXE` ignora diferencias de mayusculas. Las rutas con
espacios funcionan porque ningun comando pasa por un shell.

Series largas (`permutar`, `build` repetidos): Wine arranca su `wineserver` en cada llamada si no hay uno vivo
(unos 2 s por compilacion, frente a ~70 ms con uno vivo). Lanzar `wineserver -p </dev/null >/dev/null 2>&1`
antes de la serie lo mantiene persistente (sin redirigir la salida, una sesion `ssh` no termina) y
`wineserver -k` lo cierra al acabar. Sin servidor persistente, el `wineserver` termina solo unos segundos
despues de la ultima llamada; ese proceso no es una medicion colgada.

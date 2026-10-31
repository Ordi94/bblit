# Guia de ejecucion de extremo a extremo

Secuencia verificada para pasar de un checkout con el toolchain presente a un ejecutable
reconstruido, una imagen de prueba y su arranque en emulador. Todos los comandos se lanzan desde
la raiz del repositorio con `PYTHONUTF8=1` y el interprete `.venv\Scripts\python.exe`.

## 1. Preparacion

```
set PYTHONUTF8=1
set BBLIT_DISC=<ruta al .bin, al .cue, a la carpeta del .bin, a la carpeta superior o a una carpeta con fs/>
.venv\Scripts\python.exe -m tools.toolchain instalar
```

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
anterior, asi que el siguiente commit lo refresca.

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

## 3. Imagen de prueba

```
.venv\Scripts\python.exe -m tools.disco reempaquetar --imagen "<.bin>" --exe build\SLUS_008.38 --salida build
```

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

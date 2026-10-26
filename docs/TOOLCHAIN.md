# Toolchain nativo para Windows

Este documento describe cómo se instala el toolchain, cómo se particiona el ejecutable
principal del juego (`SLUS_008.38`) y cómo se reconstruye byte a byte. Todo corre de forma
nativa en Windows 11 x64: sin contenedores, sin WSL y sin máquinas virtuales.

## Por qué es nativo

Los ejecutables del SDK Psy-Q (`CC1PSX.EXE`, `ASPSX.EXE`, `PSYLINK.EXE`, `DMPSX.EXE`) son
programas Win32 de 1998 y 1999. En Windows se ejecutan directamente mediante WoW64; las
comunidades que trabajan en Linux necesitan Wine para lo mismo. Los binutils MIPS se
descargan ya compilados para Windows, de modo que no hace falta ningún compilador en la
máquina. Los componentes de 16 bits o de extensor DOS que traen los paquetes antiguos no se
instalan: Windows de 64 bits no los ejecuta.

## Requisitos previos

- Python 3.13 en el entorno virtual `.venv` del repositorio, con las dependencias del
  particionador: `splat64[mips]==0.50.1` (el extra `mips` aporta `n64img`, que `splat` importa
  siempre), `watchdog`, `levenshtein`, `cxxfilt` y `colorama` (los usa `asm-differ`), y para las
  pruebas `pytest`, `pytest-cov`, `types-requests` y `types-PyYAML`.
- 7-Zip para los formatos `7z` y `rar`. Se busca en `BBLIT_7ZIP`, en `siete_zip` de
  `config/local.toml`, en el `PATH` y en `%ProgramFiles%\7-Zip`.
- El disco original. `BBLIT_DISC` acepta cualquiera de estas formas: la carpeta que contiene la
  imagen `.bin`, la ruta del `.bin` o del `.cue`, una carpeta superior que guarda la imagen en una
  subcarpeta, o una carpeta con el sistema de archivos ya extraído (`fs/SLUS_008.38`). Cuando solo
  hay imagen, el ejecutable se extrae del sistema de archivos ISO 9660 de la imagen a `expected/`;
  la carpeta del disco nunca se modifica.

## Configuración de rutas

El repositorio no contiene rutas de ninguna máquina. Cada ruta se resuelve en este orden:
argumento, variable de entorno, `config/local.toml` (ignorado por git) y valor por defecto.

| Ruta | Argumento | Variable | Clave en `local.toml` | Por defecto |
|---|---|---|---|---|
| Disco (ver arriba) | `--disc` | `BBLIT_DISC` | `disc` | sin valor |
| Carpeta del toolchain | `--toolchain` | `BBLIT_TOOLCHAIN` | `toolchain` | `toolchain/` |
| Ejecutable de 7-Zip | — | `BBLIT_7ZIP` | `siete_zip` | búsqueda automática |

`config/local.example.toml` es la plantilla. Las rutas con espacios y paréntesis son válidas:
todo proceso hijo recibe una lista de argumentos, nunca una cadena para un intérprete.

### Qué herramientas leen `BBLIT_DISC`

Las cuatro formas aceptadas para el disco son: la imagen `.bin`, su `.cue`, la carpeta que
contiene el `.bin` (o una carpeta superior que lo guarda en una subcarpeta) y una carpeta con el
sistema de archivos ya extraído (`fs/SLUS_008.38`).

| Herramienta | Cómo recibe el disco | Ejemplo |
|---|---|---|
| `tools/build.py` | `--disc`, `BBLIT_DISC` o `config/local.toml` | `python tools/build.py split` con `BBLIT_DISC` definida |
| `tools.ghidra` | `--exe` o `BBLIT_DISC` (mismas formas) | `python -m tools.ghidra ...` con `BBLIT_DISC` definida |
| `tools.disco` | argumentos explícitos, no lee `BBLIT_DISC` | `python -m tools.disco reempaquetar --imagen "<ruta>/juego.bin" --exe build/SLUS_008.38 --salida <carpeta>` |
| `tools.bzz` | argumentos explícitos, no lee `BBLIT_DISC` | `python -m tools.bzz desempaquetar <archivo.BZZ> <carpeta>` |

### Cabeceras del SDK

Las cabeceras del proyecto en `include/psyq/` deben ser las del SDK 4.4 (`psyq-4.4`, la misma
versión del compilador identificado, GCC 2.8.1; ver `docs/COMPILADOR.md`). Las cabeceras 4.7
solo sirven de consulta y no deben copiarse al proyecto: algunas declaraciones difieren entre
versiones y alterarían la compilación.

## Componentes

`config/toolchain.lock.json` fija, para cada componente, la URL, la huella SHA-256, la fecha
de registro y notas de procedencia. Un archivo descargado solo se instala si su huella
coincide; si no, la instalación se detiene con un error que nombra el componente y no deja
ningún archivo en el destino. Las URL admitidas son HTTPS y de los dominios `archive.org`,
`arthus.net`, `github.com` y `githubusercontent.com`.

| Componente | Contenido | Versión | Procedencia | SHA-256 del archivo |
|---|---|---|---|---|
| `psyq-4.4` | `CC1PSX.EXE` (GCC 2.8.1), `CCPSX.EXE`, `CPPPSX.EXE`, `ASPSX.EXE` 2.79, `PSYLINK.EXE`, `DMPSX.EXE`, `LIB\*.LIB`, `INCLUDE\*.H` | Runtime Library 4.4 (octubre de 1998), GCC 2.8.1 SN32 build 4.0.0010 | Espejo `ps1_sdks` de archive.org | `75d20b9d31372ff0629482f30ee27edd726eaa57d8be39fa0d93e583144063f7` |
| `psyq-4.1` | `CC1PSX.EXE` (GCC 2.7.2), `CCPSX.EXE`, `ASPSX.EXE` 2.67, `PSYLINK.EXE`, `DMPSX.EXE` | Runtime Library 4.1 (diciembre de 1997), GCC cygnus-2.7.2-970404 SN32.3.7.0004 | Espejo `ps1_sdks` de archive.org (imagen de CD dentro de un rar) | `de0e9de0178aba886912bd8f9e434c2201e2cc331f0d0c67136e811711785c7c` |
| `binutils-mipsel` | `as`, `ld`, `objcopy`, `objdump`, `readelf`, `nm` para `mipsel-none-elf` | GNU binutils 2.40 | Release v0.24 de PSn00bSDK | `51df48145d5ef4b396d3932b72ccba538cc605c7c7745b32c58c277aa00523c5` |
| `maspsx` | Preprocesador de ensamblador que imita a ASPSX | commit `4ffa8b5` | GitHub `mkst/maspsx` | `ef60294812d9e4bf6f97ccac973102ebedcc233b8afbccab770be6eac104713c` |
| `m2c` | Traductor de ensamblador MIPS a C | commit `c632946` | GitHub `matt-kempster/m2c` | `503714b92b14ba0e1affcc6decf4ad5763b37035cca66247858298cdf1b38971` |
| `asm-differ` | Comparador de funciones objetivo contra compiladas | commit `0dd09af` | GitHub `simonlindholm/asm-differ` | `87db719b97bc97f206a35df9758fbba8a6e7e460ce0dd676bfb01933cf18adee` |

Notas de procedencia:

- La única fuente localizada del GCC 2.7.2 de Psy-Q como ejecutable Win32 es la imagen de CD
  del Runtime Library 4.1 (el `CC1PSX.EXE` de 1995 que trae el paquete `PSYQ_SDK.zip` es de
  32 bits con extensor DOS y no corre en Windows de 64 bits). Por eso `psyq-4.1` se extrae de
  la imagen con un lector ISO 9660 propio (`tools/toolchain/iso9660.py`).
- Los paquetes 4.6 y 4.7 incluyen GCC 2.95.2 (fecha 1999-10-24), posterior al juego; no se
  instalan.
- Los hash de los archivos de GitHub corresponden al `zip` de un commit concreto. Si GitHub
  cambiara el formato de compresión de esos archivos, la instalación fallaría con el error de
  huella distinta y habría que volver a registrar el valor.
- Windows Defender puede marcar como sospechosos los ejecutables de 1998 y 1999. Es un
  falso positivo conocido de binarios antiguos sin firma; no se desactiva ninguna protección.
  Si ocurriera, se añade una exclusión puntual de la carpeta `toolchain/`.

## Flujo de trabajo

```text
python -m tools.toolchain instalar        # descarga y verifica; idempotente
python -m tools.toolchain verificar       # OK o FALTA por componente
python tools/build.py split               # particiona con splat: genera asm/, src/ y el script del enlazador
python tools/build.py build               # compila los src/*.c, ensambla el resto, enlaza y genera build/SLUS_008.38
python tools/build.py verify              # compara por SHA-256 con el original: OK o FAIL
python tools/build.py diff <función>      # compara una función compilada desde C con su original
python tools/build.py probar <función> <carpeta>   # puntúa variantes .c de una función contra el original
python tools/build.py progreso            # escribe docs/PROGRESO.md y build/progreso.json
python tools/build.py clean               # elimina asm/, expected/ y los artefactos de build/
```

- `instalar` acepta `--solo COMPONENTE` (repetible). Cada componente queda en
  `toolchain/<componente>/` con un archivo `INSTALADO.json` que registra la huella instalada;
  si el lock cambia de huella el componente se reinstala desde cero.
- `split` comprueba antes que el ejecutable de origen tenga el SHA-256 de la edición
  soportada (`config/ejecutable.json`), lo copia a `expected/` y ejecuta `splat`. Es
  idempotente: borra su salida anterior antes de generar. Con `PYTHONUTF8=1`, porque la consola
  de Windows no usa UTF-8 por defecto.
- `build` empieza eliminando el ejecutable, el binario plano, el ELF y el mapa de la construcción
  anterior, de modo que una construcción fallida no deja nada que `verify` pueda aprobar.
- `build` recorre los objetos que referencia el script del enlazador: ensambla cada `.s` y
  compila cada `src/*.c` (preprocesador `CPPPSX.EXE`, `CC1PSX.EXE -O2 -G<g>`, `maspsx` con ASPSX 2.80 y
  `as`; ver `docs/DESCOMPILACION.md`). Después enlaza con `mipsel-none-elf-ld` y extrae la imagen
  plana con `objcopy`. La cabecera PS-X EXE de 0x800 bytes se regenera desde
  `config/ejecutable.json` (no se copia del original). El orden de enlace lo fija el script, así que
  es el mismo con o sin C.
- `verify` imprime `OK esperado=<huella> obtenido=<huella>` y devuelve 0, o `FAIL ...` con
  el desplazamiento de la primera diferencia y devuelve 1.
- `clean` elimina `asm/`, `expected/` y lo que `split`, `build`, `diff` y `progreso` generan
  dentro de `build/`. Conserva `asm/overlay/`, `expected/overlay/`, `build/overlay/`,
  `build/emulador/` y `build/bblit_prueba.*`, que pertenecen a otras herramientas. La carpeta
  `build/` se borra entera solo si queda vacía.

El ejecutable original nunca se modifica: se lee desde `BBLIT_DISC` y se trabaja sobre la
copia de `expected/`.

## Cómo se reproduce el ejecutable

- El cuerpo del ejecutable (`0x800..0x55800`) es un único segmento cargado en `0x80014A00`
  (`t_addr`, `t_size = 0x55000`). `config/splat.yaml` lo describe con los subsegmentos
  `asm` (arranque y librerías), `c` (25 archivos `src/<subsistema>.c` para el código del juego),
  `data`, `rodata` y `bss`, estos tres divididos en trozos con el nombre del archivo que posee
  cada tabla (ver `docs/DESCOMPILACION.md`). El enlazador agrupa siempre `data` antes que
  `rodata`, y la frontera entre ambos es provisional: se afinará al identificar los objetos
  originales.
- `splat` solo reconoce como función lo que es destino de un `jal` o está declarado. La
  dirección de entrada (`pc0 = 0x80014A08`) no lo es, así que `split` la declara en
  `build/simbolos_entrada.txt` (salvo que `config/symbols.txt` ya la defina). El proyecto
  declara 1102 símbolos de función en `config/symbols.txt`;
  sin tabla de símbolos, `splat` detectaría unas 978 funciones por sus `jr $ra`.
- El ensamblador es GNU `as` con `-EL -march=r3000 -mips1` (`maspsx` le fuerza `-G0`). Las instrucciones del
  coprocesador GTE se expanden con las macros que genera `splat` en `asm/include/`
  (`gte_macros.inc`).
- `config/symbols.txt` (formato `nombre = 0xDIRECCION; // type:func size:0xNN`) es la única
  fuente de nombres. Si no existe, el build funciona con nombres `func_80XXXXXX`.

## Si algún componente faltara

La vía de regreso es Docker en un laboratorio externo con el mismo toolchain de la
comunidad (GCC 2.7.2 y 2.8.1 compilados desde `decompals/old-gcc`, binutils y Wine solo si
hiciera falta). Antes de usarla hay que consultar a quien administra ese entorno. Los
componentes de este documento no la necesitan.

## Solución de problemas

- `huella SHA-256 distinta`: el espejo cambió el archivo o la descarga se alteró. No se
  instala nada. Verifique la URL y vuelva a registrar el valor solo si el origen es confiable.
- `no se encontró 7-Zip`: instale 7-Zip o defina `BBLIT_7ZIP`.
- `el ejecutable de origen no coincide con la edición soportada`: el disco no es el volcado
  de la edición norteamericana (SLUS-00838).
- `FAIL ... primera diferencia en el desplazamiento 0x...`: el valor indica si el cambio está
  en la cabecera (menor que `0x800`) o en el cuerpo.

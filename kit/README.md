# psx-decomp-kit

Herramientas para descompilar juegos de PlayStation 1 hasta obtener C que, compilado con el
compilador original del SDK, reproduce el ejecutable byte a byte (descompilacion "matching").

## Que es

Un paquete Python, `psxdecomp`, con las piezas genericas de un proyecto de descompilacion matching:

- particion del ejecutable con `splat` y construccion completa (compilar los `.c`, ensamblar el resto, enlazar);
- verificacion del ejecutable reconstruido por huella SHA-256;
- comparacion funcion a funcion contra el original con `asm-differ` (`diff`) y banco de variantes (`probar`);
- busqueda automatica de la forma de C que hace coincidir una funcion (`permutar`);
- medicion de progreso (`progreso`): cuanto del ejecutable ya esta en C, por zona y por subsistema;
- instalacion verificada del toolchain externo (SDK, binutils, `maspsx`, `asm-differ`);
- cargador y validador del manifiesto `psxdecomp.toml`, unica fuente de todo lo que depende del proyecto.

Version 0.1.0, Python 3.13 o superior, licencia MIT.

## Que no es

- No incluye binarios del SDK, del compilador ni del juego: cada proyecto los descarga o los
  aporta por su cuenta y declara donde estan (el kit solo descarga con verificacion de huella lo
  que el archivo de bloqueo del proyecto enumera).
- No contiene datos de ningun juego. Todo lo que depende del proyecto (nombre del ejecutable,
  rutas, zonas de memoria, convenciones de los comentarios) se declara en el manifiesto
  `psxdecomp.toml` de la raiz del proyecto consumidor.
- No traduce funciones: automatiza construir, comparar y medir; el C lo escribe el proyecto.

## Requisitos

| Requisito | Detalle |
|---|---|
| Python | 3.13 o superior |
| Windows | Funciona de forma nativa con las herramientas del SDK empaquetadas |
| Linux | Necesita Wine (`WINE` o `<PREFIJO>_WINE`) para el compilador del SDK y binutils MIPS nativos (`mipsel-linux-gnu-as`, `ld`, `objcopy`, `objdump`; prefijo en `BINUTILS_PREFIX`) |
| Dependencias de ejecucion | `requests`, `PyYAML` |
| Particion (`split`) | extra `particion`: `splat64[mips]` |
| Comparacion (`diff`, `probar`, `permutar`) | extra `comparacion`: `rapidfuzz`, `Levenshtein`, `cxxfilt`, `colorama`, `watchdog` |
| Desarrollo | extra `desarrollo`: `pytest`, `pytest-cov`, `mypy`, `ruff` |

## Instalacion

Desde el repositorio publicado, fijando una version:

```
python -m pip install "psx-decomp-kit[particion,comparacion] @ git+https://github.com/Ordi94/psx-decomp-kit@v0.1.0"
```

En modo editable, desde una copia local del kit (por ejemplo `kit/` dentro de un proyecto):

```
python -m pip install -e "./kit[particion,comparacion,desarrollo]"
```

Para fijar el kit en el `requirements.txt` de un proyecto:

```
psx-decomp-kit[particion,comparacion] @ git+https://github.com/Ordi94/psx-decomp-kit@v0.1.0
```

## Uso minimo

1. Crear `psxdecomp.toml` en la raiz del proyecto (ver "Manifiesto"); basta `[proyecto]` y `[zonas]`.
2. `python -m psxdecomp.cli comprobar` valida el manifiesto e imprime el resumen.
3. `python -m psxdecomp.toolchain instalar` descarga el toolchain que declare el archivo de bloqueo.
4. `python -m psxdecomp.cli split`, `build` y `verify` reconstruyen y comprueban el ejecutable.

La raiz del proyecto es `--proyecto <raiz>` o la carpeta actual.

## Manifiesto

`psxdecomp.toml` se lee con `tomllib`; toda seccion o clave desconocida es un error, y los valores se validan
con listas de admitidos y cotas. Las rutas son relativas a la raiz del proyecto, no pueden contener `..` ni salir
de ella (tampoco por enlaces simbolicos). Obligatorias: `[proyecto]` con `nombre` y `ejecutable`, y `[zonas]`.

### `[proyecto]`

| Clave | Defecto | Contenido |
|---|---|---|
| `nombre` | obligatoria | Nombre del proyecto. |
| `ejecutable` | obligatoria | Nombre del ejecutable original (por ejemplo `EJEC_001.00`). |
| `referencia` | `config/ejecutable.json` | Archivo JSON con el nombre, las huellas y la cabecera PS-X EXE del ejecutable original. |
| `prefijo_entorno` | `PSXDECOMP` | Alias de las variables de entorno del proyecto (ver "Variables de entorno"). |
| `comando` | `python -m psxdecomp.cli` | Como invoca el proyecto al kit; solo aparece en los textos generados, nunca se ejecuta. |
| `funcion_ejemplo` | ninguna | Funcion que cita el texto de ayuda de `diff`. |

### `[rutas]` (todas opcionales)

| Clave | Defecto | Contenido |
|---|---|---|
| `fuentes` | `src` | Archivos C del proyecto. |
| `incluir` | `include` | Cabeceras. |
| `asm` | `asm` | Ensamblador generado por la particion. |
| `macros` | `asm/include` | Macros del ensamblador. |
| `asm_coincidente` | `asm/matchings` | Ensamblador original de las funciones ya escritas en C. |
| `asm_pendiente` | `asm/nonmatchings` | Ensamblador original de las que siguen pendientes. |
| `build` | `build` | Salidas de la construccion. |
| `expected` | `expected` | Segmentos extraidos del ejecutable original. |
| `splat` | `config/splat.yaml` | Configuracion del particionador. |
| `simbolos` | `["config/symbols.txt"]` | Archivos de simbolos, en orden (el ultimo que repite un nombre gana); al menos uno. |
| `simbolos_adicionales` | `config/simbolos_adicionales.txt` | Simbolos que se suman a los anteriores (el ultimo que declara una direccion manda). |
| `opciones_compilacion` | `config/opciones_compilacion.toml` | Umbral `-G` y datos pequenos por archivo. |
| `toolchain_lock` | `config/toolchain.lock.json` | Archivo de bloqueo del toolchain. |
| `local` | `config/local.toml` | Rutas locales de la maquina (disco, toolchain); no se versiona. |
| `documento_progreso` | `docs/PROGRESO.md` | Documento que escribe `progreso`. |
| `readme` | `README.md` | README con los marcadores `<!-- progreso:inicio -->` y `<!-- progreso:fin -->`. |
| `subcarpetas_ajenas` | `[]` | Carpetas de `asm/` y `expected/` de otras herramientas: `split` y `clean` no las tocan. |
| `asm_auxiliares` | `[]` | Carpetas de `asm/` que el medidor no cuenta como codigo propio. |

### `[zonas]` (obligatoria)

| Clave | Contenido |
|---|---|
| `juego_desde` | Primera direccion del codigo propio del juego (inclusive). |
| `librerias_desde` | Primera direccion del codigo de librerias del SDK (inclusive). |
| `librerias_hasta` | Fin del codigo de librerias (exclusivo). |

Deben cumplir `juego_desde < librerias_desde < librerias_hasta`, dentro de la RAM de PlayStation
(`0x80000000` a `0x80800000`). Lo anterior a `juego_desde` es `arranque`; lo posterior a `librerias_hasta`, `otra`.

### `[convenciones]` (todas opcionales)

| Clave | Defecto | Contenido |
|---|---|---|
| `macro_no_coincidente` | `NON_MATCHING` | Macro bajo la que vive el intento en C de una funcion pendiente. |
| `macro_ensamblador` | `INCLUDE_ASM` | Macro que incluye el ensamblador original de una funcion. |
| `pendiente` | `\APendiente:\s*puntuacion\s+(\d+)\b` | Linea de pendiente; un grupo de captura: la puntuacion. |
| `sufijo_subsistema` | `_\d+$` | Sufijo numerico que se quita al agrupar archivos por subsistema. |
| `manuscrita` | `\brutina(?:\s+de\s+\w+)?\s+escrita\s+a\s+mano\s+en\s+el\s+original\b` | Frase que marca una rutina escrita a mano. |
| `patron_simbolo_datos` | `^D_([0-9A-F]{8})$` | Nombre de un simbolo de datos pequenos; un grupo: la direccion. |
| `patron_linea_simbolo` | `^([A-Za-z_]\w*)\s*=\s*0x([0-9A-Fa-f]{1,8})\s*;\s*//(.*)$` | Linea del archivo de simbolos; tres grupos: nombre, direccion y atributos. |
| `max_valor_g` | `64` | Mayor umbral `-G` admitido, de 0 a 4096. |

### `[compilacion]` (todas opcionales)

| Clave | Defecto | Contenido |
|---|---|---|
| `version_aspsx` | `"2.80"` | Version del ensamblador original que imita `maspsx`, `major.minor`. Es un dato del binario. |
| `opciones_compilador` | `["-quiet", "-O2"]` | Hasta 16 opciones del compilador, sin `-G` ni `-o`. Una lista vacia es valida. |

### `[plugins]` (todas opcionales)

`subcomandos`, `antes_de_construir`, `despues_de_verificar` (listas) y `entrada_progreso` (una referencia),
todas como `paquete.modulo:funcion`; el contrato esta en "Plugins y ganchos".

### Variables de entorno

Las rutas se resuelven con la regla: argumento, `PSXDECOMP_X`, `<alias>_X`, archivo local, valor por
defecto. `X` es `DISC` (imagen del disco), `TOOLCHAIN` (carpeta del toolchain), `7ZIP`, `WINE` o
`BINUTILS_PREFIX`; `<alias>` es `proyecto.prefijo_entorno`.

## Como lo consume un proyecto

El proyecto conserva su propia entrada con una orden estable (`python tools/build.py <orden>`) que carga el
manifiesto una vez y delega en el kit:

```python
"""Entrada del proyecto: ``python tools/build.py <orden>``."""

import sys
from pathlib import Path

from psxdecomp.cli import main
from psxdecomp.lectura import cargar_proyecto

RAIZ = Path(__file__).resolve().parents[1]
PROYECTO = cargar_proyecto(RAIZ)

if __name__ == "__main__":
    sys.exit(
        main(
            proyecto=PROYECTO,
            prog=PROYECTO.identidad.comando,
            descripcion="Reconstruccion del proyecto.",
        )
    )
```

Lo propio del proyecto (formatos del juego, herramientas de analisis) vive en sus paquetes y se engancha por
`[plugins]` o importando `psxdecomp`; el kit nunca importa codigo del proyecto.

## Pruebas

```
python -m pytest
```

Ejecutado desde `kit/` (con el extra `desarrollo`), exige cobertura del 100 % de lineas y ramas del paquete.
`mypy` en modo estricto y `ruff` deben pasar sin avisos. Las pruebas de coherencia del consumidor se omiten, con
el motivo visible, cuando el kit no esta dentro de un proyecto con `psxdecomp.toml`.

## Capas del cargador

| Modulo | Responsabilidad |
|---|---|
| `dominio` | Secciones inmutables del manifiesto y su construccion desde tablas ya leidas; no toca disco. |
| `validacion` | Validadores primitivos de datos externos (listas de admitidos, cotas); no toca disco. |
| `confinamiento` | Unica regla que consulta el disco: ninguna ruta del proyecto sale de su raiz. |
| `lectura` | Lectura del archivo, analisis TOML y comprobacion de confinamiento. |
| `cli` | Subpaquete de la linea de ordenes (ver "Linea de ordenes"). |
| `proyecto` | Fachada: reexporta `Proyecto`, `cargar_proyecto` y `ManifiestoError`. |

## Toolchain

`python -m psxdecomp.toolchain {instalar,verificar,listar,ruta}` instala y consulta las herramientas
externas (SDK, binutils, maspsx, asm-differ) descargandolas con verificacion SHA-256. Toma del
manifiesto la ruta del archivo de bloqueo (`rutas.toolchain_lock`), la del archivo local de rutas
(`rutas.local`) y el alias de las variables de entorno (`proyecto.prefijo_entorno`). La raiz del
proyecto es `--proyecto` o la carpeta actual.

Un componente del lock puede declarar `"nativo_fuera_de_windows": true` (booleano estricto; si
falta, es falso). Fuera de Windows, `resolver_herramienta` toma entonces `as`, `ld`, `objcopy` y
`objdump` de ese componente del `PATH` (con el prefijo de `BINUTILS_PREFIX`) en lugar del
ejecutable de Windows empaquetado. La decision depende solo de ese campo, nunca del nombre del
componente, de modo que cada proyecto nombra su entrada de binutils como quiera. Para pruebas,
`resolver_herramienta` acepta `entorno`, un mapeo que sustituye a `os.environ`.

Las rutas se resuelven con la regla: argumento, `PSXDECOMP_X`, `<alias>_X`, archivo local, valor por
defecto. Las variables son `DISC`, `TOOLCHAIN`, `7ZIP`, `WINE` y `BINUTILS_PREFIX`; `psxdecomp.entorno.Variables`
concentra la regla y los mensajes de error nombran las dos variables.

| Modulo | Responsabilidad |
|---|---|
| `entorno` | Nombres de variable de entorno: prefijo propio y alias del proyecto. |
| `toolchain.dominio` | Modelo y validacion del archivo de bloqueo. |
| `toolchain.configuracion` | Resolucion de rutas (argumento, entorno, archivo local, defecto). |
| `toolchain.descarga` | Descarga con verificacion de huella antes de dejar el archivo. |
| `toolchain.extraccion`, `toolchain.iso9660` | Extraccion de zip, 7z, rar e imagenes ISO 9660. |
| `toolchain.instalacion` | Instalacion idempotente y localizacion de herramientas. |
| `toolchain.plataforma` | Adaptacion a Windows o Linux (Wine, binutils nativos). |
| `toolchain.cli` | Linea de ordenes. |

## Linea de ordenes

`python -m psxdecomp.cli <orden>` es la entrada preferente del kit. La raiz del proyecto es `--proyecto <raiz>`
o la carpeta actual. Ordenes comunes: `split`, `build`, `verify`, `clean`, `diff <funcion>`,
`probar <funcion> <carpeta>`, `permutar <funcion>`, `verificar-config`, `progreso [--sin-readme]` y `comprobar [ruta]`. Los codigos de retorno
son `0` (bien), `1` (error esperado o verificacion fallida; `permutar` tambien `1` si mejora sin cerrar) y `2`
(uso incorrecto, o `permutar` sin mejora). Los errores esperados se imprimen en una linea, sin traza ni rutas de la
maquina. La ayuda de cada orden nombra las rutas y los nombres de variable del manifiesto, nunca los de un juego.
Un manifiesto invalido solo impide las ordenes que necesitan el proyecto: `--help` y `comprobar` siguen
funcionando.

| Modulo | Responsabilidad |
|---|---|
| `cli.errores` | `describir_error_de_sistema`, `motivo_sin_rutas` y los errores de la CLI (`PluginInvalidoError`). |
| `cli.contexto` | `Contexto` (proyecto, argumentos, entorno, ejecutor, interprete) con lectura perezosa de la referencia del ejecutable, el disco y el toolchain y el archivo de bloqueo; `ResultadoVerificacion`. |
| `cli.plugins` | Resolucion de referencias `modulo:funcion`, registro de subcomandos y ganchos. |
| `cli.comandos` | Una funcion por orden (`ejecutar_split`, `ejecutar_build`, ...). |
| `cli.orden_progreso` | La orden `progreso`: mide, escribe el documento y el resumen y actualiza el README sin abortar si este falla. |
| `cli.parser` | `construir_parser(proyecto, ...)`: argumentos, textos de ayuda y `manejador` de cada orden. |
| `cli.principal` | `main(argv, entorno, ejecutar, *, proyecto, raiz, prog, descripcion)`. |

Un proyecto consumidor conserva su propia entrada llamando a `main` con su `Proyecto` ya cargado (y su `prog`):
sin `proyecto`, la entrada es la propia del kit y acepta `--proyecto` y `comprobar`.

### Plugins y ganchos (`[plugins]`)

Cada referencia es `paquete.modulo:funcion` y se resuelve con `importlib` al usarla; la raiz del proyecto se agrega
a `sys.path` solo durante la importacion. Un modulo que no se importa, un nombre que no existe o no es invocable,
un subcomando repetido o sin `manejador` dan un `PluginInvalidoError` que nombra la referencia.

| Clave | Contrato |
|---|---|
| `subcomandos` | `registrar(subparsers, proyecto)` anade subcomandos; cada uno fija `set_defaults(manejador=funcion)` y la funcion recibe un `Contexto` y devuelve el codigo de retorno. Se registran despues de las ordenes comunes. |
| `antes_de_construir` | `gancho(proyecto)`: se invoca al empezar `build`, antes de compilar (`split` ya dejo el ensamblador). Si lanza `ValueError`, `ProcesoError` u `OSError`, `build` termina con ese error. |
| `entrada_progreso` | Opcional, una sola referencia: `agrupar(proyecto, archivo)` recibe la ruta relativa de un archivo C y devuelve el nombre de su subsistema (1 a 64 caracteres sin barras verticales ni comillas invertidas); sustituye a `convenciones.sufijo_subsistema` en la orden `progreso`. Un nombre invalido da un `PluginInvalidoError`. |
| `despues_de_verificar` | `gancho(proyecto, resultado)`: se invoca al terminar `verify` con `ResultadoVerificacion(coincide, mensaje)`, tambien si las huellas difieren o falta el ejecutable reconstruido. El codigo de `verify` depende solo del resultado, salvo que un gancho falle con un error esperado. |

## Prueba de coherencia

`tests/test_coherencia_consumidor.py` comprueba lo que el manifiesto del proyecto consumidor declara sobre
otros archivos suyos: que las referencias de los plugins se resuelvan, que el nombre del ejecutable coincida
con el de su archivo de referencia y que las zonas de memoria caigan dentro del segmento que esa referencia
describe. Se ejecuta contra el proyecto que contiene al kit (la carpeta superior a `kit/` con un
`psxdecomp.toml`); si el kit se usa fuera de un proyecto consumidor, esas pruebas se omiten y el resumen de
`pytest` (`-rs`) lista el motivo. Un proyecto no debe repetir en su codigo lo que el manifiesto ya declara: lo
lee de el.

## Progreso

`psxdecomp.progreso` mide cuanto del ejecutable ya esta en C y lo presenta. Ninguna pieza conoce un proyecto:
las zonas de memoria salen de `[zonas]`, las carpetas y el documento de `[rutas]`, las macros y el sufijo de
subsistema de `[convenciones]` y el comando de `proyecto.comando`.

| Modulo | Responsabilidad |
|---|---|
| `progreso.calculo` | Reglas puras (sin E/S): lectura de simbolos, clasificacion por zona (`arranque`, `juego`, `libreria`, `otra`), agrupado por subsistema y `calcular_progreso`. Recibe `Zonas` y la regla de agrupado. |
| `progreso.documento` | `a_json` (claves en camelCase) y `a_markdown`; los nombres de macro, carpetas y comando del texto salen del manifiesto. |
| `progreso.medicion` | Lee la tabla de simbolos (`rutas.simbolos` y `rutas.simbolos_adicionales`, el ultimo que declara una direccion manda), los fuentes y los `glabel` del ensamblador (sin `rutas.asm_auxiliares` ni `rutas.subcarpetas_ajenas`), y escribe `rutas.documento_progreso` y `<build>/progreso.json`. |
| `progreso.readme` | Seccion entre los marcadores `<!-- progreso:inicio -->` y `<!-- progreso:fin -->` de `rutas.readme`: cifras, fecha, hash corto del commit y los comandos de reproduccion (`proyecto.comando`, la variable del disco de `proyecto.prefijo_entorno`, el SHA-256 de la referencia del ejecutable). Respeta los finales de linea y es idempotente. |

La orden `progreso` devuelve `1` si los `glabel` mas las funciones en C no suman las de la tabla; un fallo al
actualizar el README es un aviso y no cambia el resultado.

## Permutador

`psxdecomp.permutador` reune las piezas que no dependen del proyecto consumidor de la busqueda de
la forma de C que hace coincidir una funcion: no importa nada fuera de `psxdecomp` y no conoce
ejecutables, rutas ni convenciones de ningun juego.

| Modulo | Responsabilidad |
|---|---|
| `permutador.c` | Analizador y generador de C del cuerpo de una funcion (tokens, arbol, impresion). |
| `permutador.analisis` | Tipos de campos y globales, efectos de lectura y escritura, hipotesis de aliasing. |
| `permutador.mutaciones` | Reformulaciones del arbol que conservan el significado y filtro `variante_permitida`. |
| `permutador.estado` | Estado persistente de una busqueda en `<build>/permutar/<funcion>/` (`estado.json`, `registro.jsonl`, `mejor.c`, `actual.c`). `carpeta_de` recibe la carpeta de build del proyecto. |
| `permutador.evaluacion` | Medicion de una variante con la misma cadena y puntuacion que `diff`: sustituye la definicion en el texto del archivo, compila, comprueba que el objeto define la funcion y puntua. `preparar_medicion` recibe `Rutas`, `Convenciones`, `Compilacion` y el nombre del ejecutable. |
| `permutador.busqueda` | Escalada con reinicios aleatorios sobre las variantes, en varios hilos, con estado reanudable (`permutar_funcion`, `Busqueda`, `Opciones`, `Resumen`). Recibe las mismas secciones del manifiesto; `leer_cabeceras` usa `rutas.incluir`. Nunca escribe en la carpeta de fuentes. |

## Construccion

`psxdecomp.construccion` reune las reglas del ejecutable y la compilacion de los archivos C con el
compilador original del SDK. No importa nada fuera de `psxdecomp`: lo que depende del proyecto
llega por parametro explicito, sin estado global.

| Modulo | Responsabilidad |
|---|---|
| `construccion.dominio` | Reglas puras (sin E/S): cabecera PS-X EXE, comandos de `splat`, `as`, `ld` y `objcopy`, verificacion por huella, opciones de compilacion por archivo (`-G`), valor de `_gp`, datos pequenos y lectura del archivo de simbolos. |
| `construccion.compilacion` | Cadena preprocesador, compilador, `maspsx` y ensamblador para un archivo C; validacion de las secciones del objeto. Recibe `Rutas`, `Convenciones` y `Compilacion` en cada llamada. `construir_mixto` construye el ejecutable completo: compila los C, ensambla el resto y enlaza en el orden del script del enlazador. |
| `construccion.salidas` | Nombres puros de lo que genera la construccion (`calcular_salidas`): script del enlazador, ELF, mapa, binario, carpetas de objetos, de `diff` y de `permutar`. Se derivan del nombre del ejecutable y de `rutas.build`. |
| `construccion.infraestructura` | Disco y procesos: ejecutar herramientas con tiempo limite, extraer el ejecutable de la imagen del disco, dividir con `splat`, ensamblar, enlazar, verificar por huella y limpiar. Lee los archivos de configuracion del proyecto con cotas de tamano. |

Las funciones de `construccion.dominio` que interpretan formatos reciben `Convenciones`
(`patron_linea_simbolo`, `patron_simbolo_datos`, `max_valor_g`); las de `construccion.compilacion`
reciben `Rutas` (`fuentes`, `incluir`, `macros`, `splat`), `Convenciones` (`max_valor_g`) y `Compilacion`
(`version_aspsx`, `opciones_compilador`). Las de `construccion.infraestructura` reciben `Rutas` y,
cuando interpretan simbolos u opciones, `Convenciones`; el nombre del ejecutable llega como argumento
(`referencia.nombre` o `nombre_ejecutable`) y el kit nunca lo supone.

Suposiciones de la infraestructura, que un proyecto debe respetar:

- El particionador nombra el script del enlazador y las salidas del enlace con el nombre del ejecutable
  sin su ultima extension (`EJEC_001.00` produce `EJEC_001.ld`, `.elf`, `.map` y `.bin`).
- El script del enlazador referencia los objetos como `build/<ruta>.s.o` y `build/<ruta>.c.o`; los
  objetos de ensamblador y de C viven en `<build>/<asm>` y `<build>/<fuentes>`.
- Si `rutas.simbolos` lista varios archivos, se combinan en el orden declarado (el ultimo gana si repiten
  un nombre) y los que no existen se omiten; `verificar_configuracion` exige que existan todos.
- Una imagen de disco con el sistema de archivos ya extraido se busca en `<disco>/fs/<ejecutable>`.
- Los mensajes de error nombran las variables de entorno con `Variables.describir`: el prefijo propio y el
  alias del proyecto. `ejecutar_proceso` recibe `variables` para localizar Wine con ese alias.

## Comparacion

`psxdecomp.diff.comparacion` compara una funcion compilada desde C con su objetivo original usando
`asm-differ` y guarda la ultima puntuacion en `<build>/diff/<funcion>.resultado.json`. Se llama
`comparacion` y no `diff` para que `psxdecomp.diff.diff` no repita el nombre del paquete.
`psxdecomp.diff.enlace_diff` decide, enlazando cada objeto en la direccion de la funcion, si los bytes
coinciden aunque `asm-differ` puntue la forma simbolica de una referencia frente a la numerica; recibe la
ruta del ELF de la ultima construccion (`SalidasDeBuild.elf`). `comparar_funcion` recibe `Rutas`,
`Convenciones`, `Compilacion` y el nombre del ejecutable.

`psxdecomp.diff.fuentes_c` analiza el texto de los archivos C y deduce el estado de cada funcion (en C,
intento no coincidente o ensamblador), la linea de pendiente de cada intento y las rutinas escritas a
mano. Las macros, la expresion de la linea de pendiente y la frase de rutina manuscrita se declaran en
`[convenciones]` (`macro_no_coincidente`, `macro_ensamblador`, `pendiente`, `manuscrita`); la carpeta de
fuentes, en `[rutas]`.

`psxdecomp.diff.variantes` es el banco de variantes de la orden `probar`: compila cada `.c` de una carpeta con
las opciones del archivo donde vive la funcion y devuelve una tabla ordenada de variante a puntuacion; no
escribe en los fuentes. `psxdecomp.diff.coherencia_pendientes` contrasta la cifra de la linea de pendiente de
cada intento no coincidente con la ultima medicion que dejo `diff` y devuelve avisos; nunca ejecuta `diff`.
Ambos reciben `Rutas`, `Convenciones` (y, el banco, `Compilacion` y el nombre del ejecutable) por parametro.

Claves de `[convenciones]` y `[rutas]` que incorporan estos modulos (todas con defecto, validadas con
listas de admitidos y cotas):

| Clave | Contenido |
|---|---|
| `rutas.macros` | Carpeta de macros del ensamblador (defecto `asm/include`). |
| `rutas.asm_coincidente` | Ensamblador original, por funcion, de las funciones ya escritas en C (defecto `asm/matchings`). |
| `rutas.asm_pendiente` | Ensamblador original, por funcion, de las que siguen en ensamblador o pendientes (defecto `asm/nonmatchings`). |
| `convenciones.manuscrita` | Expresion de la frase que marca una rutina escrita a mano. |
| `convenciones.patron_simbolo_datos` | Nombre de un simbolo de datos pequenos; su unico grupo es la direccion en hexadecimal. |
| `convenciones.patron_linea_simbolo` | Linea del archivo de simbolos; tres grupos: nombre, direccion y atributos. |
| `convenciones.max_valor_g` | Mayor umbral `-G` admitido, entero de 0 a 4096 (defecto 64). |
| `compilacion.version_aspsx` | Version del ensamblador original que imita `maspsx`, `major.minor` en digitos (defecto `"2.80"`). Es un dato del binario: se determina comparando la salida con funciones reales, y un proyecto con otro SDK declara la suya. |
| `compilacion.opciones_compilador` | Opciones del compilador, en orden: hasta 16 cadenas sin repetidos que empiezan por `-` y una letra, sin espacios ni separadores. No admite `-G` (lo fija cada archivo) ni `-o` (la salida la fija el kit). Una lista vacia es valida y compila sin opciones (defecto `["-quiet", "-O2"]`). |

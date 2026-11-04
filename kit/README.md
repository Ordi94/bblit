# psx-decomp-kit

Herramientas para descompilar juegos de PlayStation 1 hasta obtener C que, compilado con el
compilador original del SDK, reproduce el ejecutable byte a byte: particion con splat,
compilacion, comparacion funcion a funcion, medicion de progreso y busqueda de formas de C.

El kit es el paquete Python `psxdecomp` (Python 3.13 o superior, licencia MIT).

## Que no es

- No incluye binarios del SDK, del compilador ni del juego: cada proyecto los descarga o los
  aporta por su cuenta y declara donde estan.
- No contiene datos de ningun juego. Todo lo que depende del proyecto (nombre del ejecutable,
  rutas, zonas de memoria, convenciones de los comentarios) se declara en el manifiesto
  `psxdecomp.toml` de la raiz del proyecto consumidor.

## Instalacion

Desde la raiz del repositorio que lo contiene, dentro del entorno virtual del proyecto:

```
python -m pip install -e ./kit
```

La unica dependencia de ejecucion es `requests` (descarga del toolchain); el resto usa la biblioteca estandar.

## Manifiesto

`python -m psxdecomp.cli comprobar [ruta]` (ver "Linea de ordenes") carga y valida el `psxdecomp.toml` de la
carpeta indicada (por omision la actual) e imprime el resumen. Las secciones son `[proyecto]`,
`[rutas]`, `[zonas]`, `[convenciones]`, `[compilacion]` y `[plugins]`; toda clave desconocida es un error.

## Pruebas

```
python -m pytest
```

Ejecutado desde `kit/`, exige cobertura del 100 % (lineas y ramas) del paquete.

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
`probar <funcion> <carpeta>`, `permutar <funcion>`, `verificar-config` y `comprobar [ruta]`. Los codigos de retorno
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
| `despues_de_verificar` | `gancho(proyecto, resultado)`: se invoca al terminar `verify` con `ResultadoVerificacion(coincide, mensaje)`, tambien si las huellas difieren o falta el ejecutable reconstruido. El codigo de `verify` depende solo del resultado, salvo que un gancho falle con un error esperado. |

## Prueba de coherencia

`tests/test_coherencia_consumidor.py` compara el manifiesto del proyecto consumidor con las constantes de
su paquete `tools`. Se ejecuta contra el proyecto que contiene al kit: si la carpeta superior a `kit/`
tiene un `psxdecomp.toml`, `tests/conftest.py` pone esa raiz en `sys.path` y la comprobacion corre igual
desde `kit/` que desde la raiz. Si el kit se usa fuera de un proyecto consumidor, esas pruebas se omiten
y el resumen de `pytest` (`-rs`) lista el motivo de cada salto.

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

# Emulador, reempaquetado de la imagen y volcados de RAM

Este documento describe como probar un ejecutable reconstruido dentro de una imagen de disco
arrancable y como obtener volcados de la RAM del juego en marcha. Todo corre de forma nativa en
Windows, sin instalacion ni privilegios de administrador: los emuladores viven en
`toolchain/` (carpeta ignorada por git) y las imagenes generadas en `build/` (tambien ignorada).

## 1. Reempaquetar la imagen

```
python -m tools.disco reempaquetar --imagen "<ruta>/Bugs Bunny - Lost in Time (USA) (En,Fr,Es).bin" ^
    --exe <ruta>/SLUS_008.38 --salida build
```

Genera `build/bblit_prueba.bin` y `build/bblit_prueba.cue` sin tocar la imagen de entrada.

Como funciona y por que es seguro:

- La posicion (LBA) y el tamano del ejecutable se leen del directorio ISO 9660 de la propia
  imagen; nunca se suponen. En este disco `SLUS_008.38` ocupa 171 sectores exactos de 2048 bytes
  (350.208 bytes).
- La sustitucion es in-place: solo se reescriben los sectores cuyo contenido cambia. Un
  ejecutable de tamano distinto al registrado se rechaza con un error, porque desplazaria todo el
  contenido posterior del disco y haria falta reconstruir la imagen completa (por ejemplo con
  `mkpsxiso`).
- Los sectores del ejecutable son Mode 2 Form 1: 12 bytes de sincronia, 4 de cabecera, 8 de
  subcabecera, 2048 de datos, 4 de EDC y 276 de ECC. Al cambiar los datos se recalculan EDC (CRC
  de 32 bits sobre subcabecera y datos) y ECC (paridades P y Q de Reed-Solomon, calculadas con la
  direccion de la cabecera a cero). Antes de escribir cada sector se comprueba que el algoritmo
  reproduce exactamente el EDC/ECC del sector original; si no coincide, se aborta.
- Los sectores Form 2 (audio XA, 2324 bytes de datos, sin ECC) nunca se reescriben. Por eso los
  `.XA` extraidos al sistema de archivos del disco no sirven para reempaquetar: la imagen se
  copia entera y solo se parchan los sectores del ejecutable.
- La imagen se lee y escribe por sectores; reempaquetar la imagen completa (587 MB) tarda menos
  de un segundo y el resultado con el ejecutable original es identico byte a byte al volcado
  de referencia (SHA-1 `6024341f559c3789b5612e941c8d0ab227ff6361`).
- El resultado se escribe primero a un archivo temporal y se renombra al terminar, de modo que un
  fallo a medias no deja una imagen truncada con el nombre final.

Prueba contra la imagen real: definir `BBLIT_DISC` con la ruta del `.bin` y ejecutar
`python -m pytest tests/disco`. Sin la variable, esas pruebas se omiten.

## 2. BIOS

Los emuladores exigen una BIOS de PlayStation. No se descarga de internet ni se versiona.
La instalacion local usa `ps-22a.bin` (SCPH-1001, region NTSC-U, version 2.2) tomada del
archivo personal del usuario:

| Dato | Valor |
|---|---|
| Archivo | `toolchain/duckstation/bios/ps-22a.bin` |
| Tamano | 524.288 bytes |
| MD5 | `924e392ed05558ffdb115408c263dccf` |
| SHA-1 | `10155d8d6e6e832d6ea66db9bc098321fb5e8ebf` |

En otra maquina hay que aportar una BIOS propia (volcada de la consola del usuario) y copiarla a
`toolchain/duckstation/bios/`. PCSX-Redux la recibe por la opcion `-bios <ruta>`.

## 3. DuckStation (arranque y depuracion)

Instalacion portable (version `0.1-10413`, `duckstation-qt-x64-ReleaseLTCG.exe`, SHA-256
`83647c821c432b417aaef58ce386b379dc7f31e6611c08d145b2155ae6140de0`): se copia la carpeta del
emulador a `toolchain/duckstation/` y se crea un archivo vacio `portable.txt` a su lado para que
la configuracion viva en esa carpeta. Configuracion minima en `settings.ini`:

```
[Main]
SetupWizardIncomplete = false
[BIOS]
SearchDirectory = bios
PatchFastBoot = true
```

Arranque desde la raiz del repositorio (`bblit\`): `toolchain\duckstation\duckstation-qt-x64-ReleaseLTCG.exe -fastboot -- build/bblit_prueba.cue` (o menu
Sistema, Iniciar archivo). El juego arranca, muestra el logotipo de Behaviour y el selector
de idioma. La interfaz se puede cerrar desde el programa que lo lanzo con un tiempo limite.

Servidor GDB: con `[Debug] EnableGDBServer = true` y `GDBServerPort = 2345` el emulador acepta
el protocolo remoto de GDB. Los paquetes `m<direccion>,<largo>` leen memoria (la RAM empieza en
`0x80000000`) y funcionan, pero cada peticion tarda unos 70 ms y una lectura de 2 MiB lleva
minutos; ademas el byte de interrupcion `0x03` deja de responder. Sirve para consultas
puntuales; para volcados completos es mejor PCSX-Redux.

## 4. PCSX-Redux (volcados de RAM y capturas)

Se eligio PCSX-Redux para automatizar porque expone una API REST local que devuelve la RAM
completa y capturas de pantalla sin interaccion con la interfaz.

Instalacion portable: compilacion `dev-win-x64` numero 710 (`29732.20261025.57`), descargada de
`https://distrib.app/pub/org/pcsx-redux/project/dev-win-x64`, paquete
`pcsx-redux-nightly-29732.20261025.57-x64.zip`, SHA-1 `9d86a0b2e567cabdb0b35ad24e72f21a5c6db75c`
(coincide con el del manifiesto publicado), SHA-256
`4f7f3c678f4db1b1ef873e56d570d1d011b98e8df42e0315f56e11c5e555a18f`. Se descomprime en
`toolchain/pcsx-redux/`.

Arranque desde la raiz del repositorio (`bblit\`; todas las rutas son relativas a ella). El lanzador
`pcsx-redux.exe` crea un segundo proceso `pcsx-redux.main`; para cerrarlo hay que terminar ambos:

```
toolchain\pcsx-redux\pcsx-redux.exe -portable -loadiso build/bblit_prueba.cue ^
    -bios toolchain/duckstation/bios/ps-22a.bin -run -webserver -webserver-port 8080
```

API REST usada (todas sobre `http://127.0.0.1:8080/api/v1/`):

| Peticion | Resultado |
|---|---|
| `GET execution-flow` | Estado de la emulacion (JSON) |
| `POST execution-flow?function=pause` y `...=resume` | Pausa y reanuda; pausar antes de capturar asegura que pantalla y RAM son del mismo instante |
| `GET cpu/ram/raw` | 2.097.152 bytes: la RAM de 2 MB; el offset 0 equivale a la direccion `0x80000000` |
| `GET screen/still` | Captura de pantalla en PNG |
| `GET cd/info` | Datos del disco cargado (`SLUS00838`) |

Ejemplo (PowerShell) de un par coherente captura y RAM:

```
Invoke-RestMethod -Method Post http://127.0.0.1:8080/api/v1/execution-flow?function=pause
Invoke-WebRequest http://127.0.0.1:8080/api/v1/cpu/ram/raw -OutFile ram.bin
Invoke-WebRequest http://127.0.0.1:8080/api/v1/screen/still -OutFile pantalla.png
Invoke-RestMethod -Method Post http://127.0.0.1:8080/api/v1/execution-flow?function=resume
```

Comprobacion del volcado: el segmento de codigo y datos del ejecutable se carga en
`0x80014A00` (offset `0x14A00` del volcado, 0x55000 bytes tomados del ejecutable a partir del
offset `0x800`); en los dos volcados obtenidos coincide en un 99,62 % con el archivo del disco
(lo que cambia son variables en `.data` y `.bss`).

### Navegar hasta el primer nivel

Redux solo recibe teclado en su ventana; las teclas por defecto son X (cruz), D (circulo),
Z (cuadrado), S (triangulo), Enter (Start), Retroceso (Select) y las flechas. Los comandos
sinteticos (`keybd_event`) funcionan si la ventana tiene el foco; hay que apuntar al proceso
`pcsx-redux.main`, no al lanzador. Cada pulsacion debe durar 150 a 400 ms; las mas cortas se pierden en los
menus del juego.

1. Esperar unos 25 s al logotipo de Behaviour y al selector de idioma (avanza solo a ingles).
2. El titulo (`Bugs Bunny Lost in Time`) cicla con demostraciones. Pulsar Enter en cuanto
   aparezca el texto `PRESS START`; antes de que aparezca la tecla se ignora. Detectar el texto
   comparando la region de pixeles de la captura (`x` 196 a 306, `y` 84 a 98 en la captura de
   512x240) permite sincronizar sin intervencion.
3. Aparecen avisos de la tarjeta de memoria: pulsar X en `Continue`, y X en `Create file` (crea
   un archivo de partida en `memcard1.mcd` dentro de `toolchain/pcsx-redux/`, ignorado por git).
4. En el menu de partidas, con `New game` resaltado pulsar X dos veces (se elige la ranura 1),
   y X en `Start`.
5. Corre la secuencia de introduccion y una pantalla de carga con el nombre del nivel. Pulsar
   Enter varias veces la salta; Enter tambien pausa y reanuda el juego (aparece el menu
   `Game Paused`), asi que hay que terminar con el juego sin pausar.
6. Con el personaje controlable en el primer nivel (`Nowhere`, con el contador de zanahorias en
   pantalla), pausar la emulacion y capturar pantalla y RAM.

Las demostraciones del titulo (`DEMO MODE PRESS START`) tambien cargan niveles distintos del
primero; sirven para obtener volcados de otros niveles sin jugar, pero la entrada de mando se
ignora durante ellas hasta que vuelve el titulo.

## 5. Limites conocidos

- La API REST de Redux no permite inyectar entrada de mando; la entrada se simula con el
  teclado y requiere que la ventana este en primer plano. Los archivos que el Lua del emulador
  intenta leer desde otro proceso no se actualizan de forma fiable, asi que no se usa ese canal.
- Los volcados son instantaneas de 2 MiB (RAM principal). La RAM de video (1 MiB) se obtiene con
  `GET gpu/vram/raw`; la RAM de sonido no esta expuesta por la API.
- Con un ejecutable reconstruido de tamano distinto hace falta reconstruir la imagen completa;
  PCSX-Redux documenta ademas `POST cd/patch` para parchar un archivo sobre la imagen ya cargada,
  util para pruebas rapidas (no se ha probado aqui); no genera una imagen en disco.

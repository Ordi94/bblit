# Guia de ejecucion de extremo a extremo

Secuencia verificada para pasar de un checkout con el toolchain presente a un ejecutable
reconstruido, una imagen de prueba y su arranque en emulador. Todos los comandos se lanzan desde
la raiz del repositorio con `PYTHONUTF8=1` y el interprete `.venv\Scripts\python.exe`.

## 1. Preparacion

```
set PYTHONUTF8=1
set BBLIT_DISC=<ruta al .bin, al .cue, a su carpeta o a una carpeta con fs/>
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

## 3. Imagen de prueba

```
.venv\Scripts\python.exe -m tools.disco reempaquetar --imagen "<.bin>" --exe build\SLUS_008.38 --salida build
```

Con el ejecutable sin modificar: `0 de 249595 sectores modificados` y SHA-1
`6024341f559c3789b5612e941c8d0ab227ff6361`.

## 4. Simbolos

```
.venv\Scripts\python.exe -m tools.ghidra simbolos --funciones <funciones.csv> --salida <destino>
```

Con `BBLIT_DISC` definida (cualquiera de las cuatro formas) o con `--exe`. Genera 908 simbolos;
el resultado debe ser identico a `config/symbols.txt`.

## 5. Arranque en emulador

Ejecutar desde la raiz del repositorio (el emulador escribe `pcsx.json`, tarjetas de memoria y
`.sentry-native/` en el directorio de trabajo: borrarlos al terminar o lanzar desde otra carpeta
con rutas absolutas):

```
toolchain\pcsx-redux\pcsx-redux.exe -portable -loadiso build/bblit_prueba.cue ^
    -bios toolchain/duckstation/bios/ps-22a.bin -run -webserver -webserver-port 8080
```

1. Comprobar que el puerto 8080 esta libre y que no hay procesos `pcsx-redux` previos.
2. `GET http://127.0.0.1:8080/api/v1/execution-flow` debe devolver `"running":true` (responde
   en menos de 1 s).
3. La BIOS tarda en ceder el control: a los 20 s aun se ve el logotipo de PlayStation y a los 25 s
   la pantalla puede seguir en negro. Capturar `screen/still` a partir de unos 45 s (selector de
   idioma). Un PNG negro puede pesar mas de 10 KB: validar por contenido (valores de pixel), no por
   tamano.
4. `POST execution-flow?function=pause`, leer `cpu/ram/raw` (2.097.152 bytes) y
   `screen/still`, y `POST execution-flow?function=resume`.
5. Comprobacion de carga: en la RAM, el offset `0x14A00` (direccion `0x80014A00`) coincide con
   los bytes desde el offset `0x800` de `build/SLUS_008.38`.
6. Cerrar `pcsx-redux` y `pcsx-redux.main` (son dos procesos).

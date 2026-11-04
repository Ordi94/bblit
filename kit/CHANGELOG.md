# Registro de cambios

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el versionado es semantico.

## [0.1.0] - 2026-11-04

Primera version publicable del kit.

### Incluye

- Manifiesto `psxdecomp.toml`: cargador, validacion con listas de admitidos y cotas, confinamiento de rutas a la
  raiz del proyecto y mensajes de error sin rutas de la maquina.
- Linea de ordenes `python -m psxdecomp.cli`: `split`, `build`, `verify`, `clean`, `diff`, `probar`, `permutar`,
  `verificar-config`, `progreso` y `comprobar`; entrada reutilizable (`main`, `construir_parser`) para que un
  proyecto conserve su propia orden.
- Extensiones por `[plugins]`: subcomandos, ganchos antes de construir y despues de verificar, y agrupado propio
  de subsistemas para el progreso.
- Construccion: compilacion de los archivos C con el compilador original del SDK, ensamblado del resto, enlace
  en el orden del script del enlazador y verificacion por huella SHA-256.
- Comparacion funcion a funcion con `asm-differ`, banco de variantes y coherencia de las lineas de pendiente.
- Permutador: busqueda de la forma de C que hace coincidir una funcion, con estado reanudable.
- Progreso: medicion por zona y subsistema, documento en Markdown y JSON y seccion del README del proyecto.
- Toolchain: instalacion idempotente con verificacion de huella, extraccion de zip, 7z, rar e ISO 9660, y
  adaptacion a Windows o Linux (Wine y binutils nativos).
- Variables de entorno con prefijo propio (`PSXDECOMP_`) y alias configurable por proyecto.
- Paquete tipado (`py.typed`), cobertura del 100 % de lineas y ramas, `mypy` estricto y `ruff` sin avisos.

### Dependencias

`requests` y `PyYAML`; extras `particion` (`splat64`), `comparacion` (`rapidfuzz`, `Levenshtein`, `cxxfilt`,
`colorama`, `watchdog`) y `desarrollo`.

### No incluye

Binarios del SDK, del compilador ni de ningun juego.

# bblit

Descompilacion de **Bugs Bunny: Lost in Time** (PlayStation, 1999, SLUS-00838) a codigo C
que, compilado con el toolchain original Psy-Q, reproduce byte a byte el ejecutable del disco.
El objetivo final es contar con el codigo fuente completo del juego para preservarlo,
estudiarlo y portarlo a plataformas modernas.

Este repositorio **no contiene ningun dato del juego**: ni la imagen del disco, ni el
ejecutable, ni texturas, modelos o audio. Para construir hace falta una copia propia del
disco original. Todo lo que se deriva del disco (desensamblado, archivos extraidos,
volcados) se genera localmente y esta excluido del control de versiones.

## Estructura

| Carpeta | Contenido |
|---|---|
| `tools/` | Herramientas Python: toolchain, construccion, formatos de archivo, analisis |
| `config/` | Configuracion del desensamblador (splat), simbolos, hashes del toolchain |
| `src/` | Codigo C descompilado, organizado por subsistema |
| `include/` | Cabeceras propias y del SDK |
| `tests/` | Pruebas de las herramientas Python |
| `docs/` | Especificaciones de formatos, mapa de memoria, toolchain, progreso |

## Requisitos

- Windows 10/11 x64 (el toolchain Psy-Q es Win32 nativo)
- Python 3.13
- Copia propia del disco en formato `.bin/.cue`

## Herramientas

| Comando | Para que sirve |
|---|---|
| `python tools/build.py split` | Particiona el ejecutable con splat (genera `asm/` y los `src/*.c` que falten) |
| `python tools/build.py build` | Compila los `src/*.c`, ensambla el resto y enlaza `build/SLUS_008.38` |
| `python tools/build.py verify` | Compara el SHA-256 del ejecutable reconstruido con el original |
| `python tools/build.py diff <funcion>` | Compara una funcion compilada desde C con su original (`asm-differ`) |
| `python tools/build.py progreso` | Escribe `docs/PROGRESO.md` y `build/progreso.json` |
| `python tools/build.py probar <funcion> <carpeta>` | Compila cada variante `.c` de la carpeta para esa funcion y las ordena por puntuacion de `asm-differ` |
| `python tools/build.py clean` | Elimina lo generado (`asm/`, `expected/`, artefactos de `build/`) |
| `python -m tools.toolchain instalar` / `verificar` / `listar` / `ruta` | Instala y consulta los componentes del toolchain |
| `python -m tools.bzz desempaquetar` / `inventario` | Descomprime las secciones de un `.BZZ` / genera un CSV por seccion |
| `python -m tools.disco reempaquetar` | Sustituye el ejecutable de la imagen del disco |
| `python -m tools.ghidra analizar` / `exportar` / `simbolos` / `informe` | Analiza el ejecutable con Ghidra y genera la tabla de simbolos |
| `python -m tools.ghidra borradores` / `grafo` / `subsistemas` / `limites` | Borradores en C, grafo de llamadas, subsistemas y limites de unidades |
| `python -m tools.overlay extraer` / `simbolos` / `split` / `build` / `verify` / `ram` | Reconstruye las variantes del overlay de codigo |
| `python -m tools.emulador arrancar` / `pausar` / `reanudar` / `volcar` / `capturar` / `apagar` / `comparar` / `sesion` | Controla PCSX-Redux y compara volcados de RAM |

Cada comando acepta `--help` con sus opciones. El flujo de descompilacion esta en
`docs/DESCOMPILACION.md`.

## Construccion

```
python -m venv .venv
.venv\Scripts\pip install -e .[dev]
python tools/build.py --help
```

## Licencia y aviso legal

Las herramientas, la documentacion y la reconstruccion de este repositorio se publican bajo la licencia MIT (archivo LICENSE). El codigo C recuperado reproduce el comportamiento del ejecutable original de Bugs Bunny: Lost in Time, cuyos derechos pertenecen a sus titulares (Infogrames y Behaviour Interactive); se publica con fines de preservacion e interoperabilidad y no concede ningun derecho sobre el juego. Este repositorio no contiene ni distribuye el disco, el ejecutable original, los recursos del juego ni el SDK Psy-Q: para reconstruir hace falta una copia propia del disco y el toolchain instalado localmente (ver docs/TOOLCHAIN.md y docs/RUNBOOK.md).

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

## Construccion

```
python -m venv .venv
.venv\Scripts\pip install -e .[dev]
python tools/build.py --help
```

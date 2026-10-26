# Archivos de origen propuestos

Propuesta de limites entre las unidades de compilacion originales dentro del codigo del juego, en un
formato que se puede trasladar a subsegmentos de `config/splat.yaml`. Es una hipotesis con evidencia
medida, no una verdad: `config/splat.yaml` aplica 25 de estos cortes como archivos `src/<nombre>.c` (los
descartados y su razon estan en `docs/DESCOMPILACION.md`).

## Lo que se midio

- **Relleno de `nop`:** ninguno. De los 257 cortes entre funciones consecutivas del juego, 0 tienen
  palabras nulas tras la ranura de retardo del `jr ra`; todas las funciones empiezan alineadas a 4,
  no a 16. El relleno entre objetos no sirve de evidencia en este ejecutable.
- **Cadenas de solo lectura:** el juego referencia pocas cadenas propias desde el codigo (la ruta del
  archivo de partida en `0x8005E04C`, `BouzeID %d not found` en `0x80067F54` y `Got it` en `0x8006933C`), de
  modo que el cambio de grupo de cadenas solo delimita el bloque de la tarjeta de memoria y el cargador.
  Las tablas de datos privados (usadas por una o dos funciones) crecen con la direccion del codigo:
  `0x80014AC4` usa `0x8005E04C`; `0x8001DA14`, `0x8005E064..0x8005E078`; `0x80025B2C`, `0x8005E08C`;
  `0x8002F9F8`, `0x8005E3F0`; `0x80030ECC`, `0x8005E560`; `0x800330AC`, `0x8005E6F8`; `0x80033358`,
  `0x8005E728`; `0x80035244`, `0x8005E768` y `0x80067E64`; `0x80037FE8`, `0x8005E81C..0x8005E938`. La tabla del
  despachador (`func_800353B0`, `0x8005E35C`) es la excepcion: queda antes que los datos de las funciones
  vecinas, asi que viene de otro objeto o de una seccion de datos distinta.
- **Cortes limpios:** un corte entre dos funciones consecutivas es limpio si ningun enlace cercano lo
  cruza (llamada directa, puntero a funcion o dato usado por 2 a 6 funciones). Con ventanas de 12, 8 y 5
  funciones hay 13, 35 y 61 cortes limpios de 257. Una funcion hoja sin enlaces produce cortes limpios a
  ambos lados sin ser un archivo por si sola, por eso se descartan cortes a menos de 256 bytes del
  anterior (con 0, 128, 256, 512 y 1024 bytes salen 47, 37, 36, 35 y 30 archivos).
- **Confianza:** alta = inicio de subsistema o corte limpio en 12 funciones; media = limpio en 8 funciones,
  o en 5 con cambio de familia de librerias. Los cortes de confianza baja no se listan.

## Propuesta

`offset` es el desplazamiento en el archivo `SLUS_008.38` (direccion menos `0x80014A00` mas `0x800`).

| Direccion | Offset | Archivo propuesto | Confianza | Evidencia |
|---|---|---|---|---|
| `0x80014A08` | `0x808` | `src/arranque_y_bucle_principal.c` | alta | ningun enlace cruza el corte en una ventana de 12 funciones |
| `0x80014AC4` | `0x8C4` | `src/tarjeta_de_memoria.c` | alta | inicio de subsistema; ningun enlace cruza el corte en una ventana de 12 funciones |
| `0x80015EC0` | `0x1CC0` | `src/arranque_y_bucle_principal_2.c` | alta | inicio de subsistema |
| `0x80016C0C` | `0x2A0C` | `src/graficos_y_gte.c` | alta | inicio de subsistema; ningun enlace cruza el corte en una ventana de 8 funciones; cambia la familia de librerias (sistema a geometria_gte) |
| `0x80016ED0` | `0x2CD0` | `src/graficos_y_gte_2.c` | media | ningun enlace cruza el corte en una ventana de 8 funciones |
| `0x800171E4` | `0x2FE4` | `src/graficos_y_gte_3.c` | media | ningun enlace cruza el corte en una ventana de 8 funciones |
| `0x80017478` | `0x3278` | `src/graficos_y_gte_4.c` | media | ningun enlace cruza el corte en una ventana de 8 funciones |
| `0x80018664` | `0x4464` | `src/graficos_y_gte_5.c` | media | ningun enlace cruza el corte en una ventana de 8 funciones |
| `0x80018C68` | `0x4A68` | `src/graficos_y_gte_6.c` | media | ningun enlace cruza el corte en una ventana de 8 funciones |
| `0x80018D98` | `0x4B98` | `src/graficos_y_gte_7.c` | media | ningun enlace cruza el corte en una ventana de 8 funciones |
| `0x80018F80` | `0x4D80` | `src/graficos_y_gte_8.c` | media | ningun enlace cruza el corte en una ventana de 8 funciones |
| `0x80019180` | `0x4F80` | `src/graficos_y_gte_9.c` | media | ningun enlace cruza el corte en una ventana de 8 funciones |
| `0x80019364` | `0x5164` | `src/colision_y_terreno.c` | alta | inicio de subsistema; ningun enlace cruza el corte en una ventana de 8 funciones |
| `0x8001C424` | `0x8224` | `src/movimiento_y_objetos_de_escena.c` | alta | inicio de subsistema |
| `0x8001CC68` | `0x8A68` | `src/movimiento_y_objetos_de_escena_2.c` | media | ningun enlace cruza el corte en una ventana de 8 funciones |
| `0x8001E528` | `0xA328` | `src/movimiento_y_objetos_de_escena_3.c` | media | ningun enlace cruza el corte en una ventana de 8 funciones |
| `0x80020B90` | `0xC990` | `src/logica_de_niveles.c` | alta | inicio de subsistema |
| `0x80025938` | `0x11738` | `src/logica_de_niveles_2.c` | media | ningun enlace cruza el corte en una ventana de 5 funciones; cambia la familia de librerias (geometria_gte a graficos) |
| `0x80026118` | `0x11F18` | `src/manejadores_por_tabla.c` | alta | inicio de subsistema; ningun enlace cruza el corte en una ventana de 12 funciones |
| `0x80026298` | `0x12098` | `src/logica_de_niveles_3.c` | alta | inicio de subsistema |
| `0x8002F968` | `0x1B768` | `src/logica_de_niveles_4.c` | media | ningun enlace cruza el corte en una ventana de 8 funciones |
| `0x8002F9F8` | `0x1B7F8` | `src/interprete_de_eventos.c` | alta | inicio de subsistema |
| `0x80032874` | `0x1E674` | `src/camara_y_bucle_logico.c` | alta | inicio de subsistema; cambia la familia de librerias (geometria_gte a sistema) |
| `0x80036164` | `0x21F64` | `src/gestion_y_dibujo_de_objetos.c` | alta | inicio de subsistema; ningun enlace cruza el corte en una ventana de 5 funciones |
| `0x80037048` | `0x22E48` | `src/gestion_y_dibujo_de_objetos_2.c` | alta | ningun enlace cruza el corte en una ventana de 12 funciones |
| `0x800399C8` | `0x257C8` | `src/gestion_y_dibujo_de_objetos_3.c` | alta | ningun enlace cruza el corte en una ventana de 12 funciones |
| `0x80039BFC` | `0x259FC` | `src/gestion_y_dibujo_de_objetos_4.c` | alta | ningun enlace cruza el corte en una ventana de 12 funciones |
| `0x8003AA38` | `0x26838` | `src/menus_e_interfaz.c` | alta | inicio de subsistema; ningun enlace cruza el corte en una ventana de 12 funciones |
| `0x8003DF84` | `0x29D84` | `src/audio_xa_y_spu.c` | alta | inicio de subsistema; ningun enlace cruza el corte en una ventana de 12 funciones |
| `0x8003FFA0` | `0x2BDA0` | `src/entrada_de_mando.c` | alta | inicio de subsistema; ningun enlace cruza el corte en una ventana de 12 funciones; cambia la familia de librerias (audio_spu a mando) |
| `0x80040A80` | `0x2C880` | `src/graficos_y_gte_10.c` | alta | inicio de subsistema; ningun enlace cruza el corte en una ventana de 12 funciones |
| `0x80040D98` | `0x2CB98` | `src/graficos_y_gte_11.c` | media | ningun enlace cruza el corte en una ventana de 8 funciones |
| `0x80040EB4` | `0x2CCB4` | `src/cargador_de_niveles_y_cd.c` | alta | inicio de subsistema; cambia la familia de librerias (graficos a cd) |
| `0x800443CC` | `0x301CC` | `src/graficos_y_gte_12.c` | alta | inicio de subsistema |
| `0x80044664` | `0x30464` | `src/cargador_de_niveles_y_cd_2.c` | alta | inicio de subsistema; ningun enlace cruza el corte en una ventana de 5 funciones |
| `0x80044904` | `0x30704` | `src/inicializacion_de_motor.c` | alta | inicio de subsistema |

Para `splat.yaml`, cada fila equivale a un subsegmento `- [offset, c, nombre]`; por ejemplo:

```yaml
- [0x808, c, arranque_y_bucle_principal]  # 0x80014A08
- [0x8C4, c, tarjeta_de_memoria]  # 0x80014AC4
- [0x1CC0, c, arranque_y_bucle_principal_2]  # 0x80015EC0
- [0x2A0C, c, graficos_y_gte]  # 0x80016C0C
```

## Limites de esta propuesta

- Los cortes dentro de `graficos_y_gte` (`0x80016C0C..0x80019364`) separan nueve rutinas de calculo de
  matrices que no se llaman entre si; podrian ser un solo archivo con funciones independientes.
- Dentro de `gestion_y_dibujo_de_objetos` los cortes de `0x80037048`, `0x800399C8` y `0x80039BFC` son de
  confianza alta, pero el rango entre `0x80036164` y `0x80037048` agrupa utilidades de lista que usan
  muchos subsistemas y que pudieron estar en un archivo de utilidades.
- Las funciones fundidas en `func_8002F9F8`, `func_80030ECC` y `func_800415A0`/`func_80042BB8` ya se
  separaron o fusionaron en `config/symbols.txt` (1102 simbolos de funcion; ver `docs/GHIDRA.md`); las cifras de este
  documento se calcularon con la tabla anterior de 908.

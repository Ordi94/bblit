#ifndef GLOBALES_H
#define GLOBALES_H

#include "common.h"

/*
 * Variables globales que mas de un archivo del juego declara. Una sola declaracion por simbolo:
 * el tipo sale del ensamblador original (el ancho de la instruccion de carga y de almacen) y
 * cambiarlo cambia el codigo generado, asi que no se retoca sin repetir diff y verify.
 */

/*
 * D_80069662: estado de la maquina de `main` y de los menus. El ensamblador lo compara con lh en
 * todas partes y solo lo incrementa cargando con lhu; declarado u16, `main` sube de 1135 a 2135.
 */
extern s16 D_80069662;

/*
 * $gp: el registro que el arranque del juego fija en 0x80069320. Recurso transitorio para
 * acceder a datos pequenos por desplazamiento en las funciones que lo usaban antes de que el
 * build soportara -G8 por archivo; el codigo nuevo define el dato como variable pequena (sin
 * extern, ver docs/DESCOMPILACION.md) y deja que maspsx lo reescriba a $gp.
 */
register u8* base_gp __asm__("$28");

/*
 * D_80069698: puntero al objeto o entidad actual. No se declara aqui porque cada archivo lo usa
 * con la vista de la estructura que necesita (Objeto en eventos.h, EntidadActual en el mando,
 * ObjetoVolumen en la geometria): la declaracion unica queda pendiente de unificar esas
 * vistas en una sola estructura.
 */

#endif

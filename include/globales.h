#ifndef GLOBALES_H
#define GLOBALES_H

#include "common.h"
#include "psyq/TYPES.H"
#include "psyq/LIBGTE.H"
#include "psyq/LIBGPU.H"
#include "psyq/LIBGS.H"

/*
 * Variables globales que mas de un archivo del juego declara. Una sola declaracion por simbolo:
 * el tipo sale del ensamblador original (el ancho de la instruccion de carga y de almacen) y
 * cambiarlo cambia el codigo generado, asi que no se retoca sin repetir diff y verify.
 *
 * Un dato nuevo que dos archivos compartan se declara aqui, no en cada .c; un dato que solo usa
 * un archivo sigue declarandose en ese archivo.
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

/* --- Estado del bucle principal y de la presentacion de cuadros ------------------------- */

/* Anillo de tres buffers de dibujo: indice mostrado (0 a 2). Las comparaciones cargan con lh; solo los incrementos de `main` usan lhu + sh. */
extern s16 D_8006967C;

/* Diferencia de marcas de tiempo entre cuadros (D_80069510 - D_80069638); lw y sw de 32 bits, se resta con signo. */
extern s32 D_80069694;

/* Banco de registros de 8 bits que manejan los eventos y la pausa (lbu en la pausa, sb en la tarjeta de memoria). */
extern u8 D_8006AA70[];

/* Pantalla activa. SetDefDispEnv y PutDispEnv lo rellenan y activan: es un DISPENV del SDK. */
extern DISPENV D_8006CF78;

/* --- Banderas de un byte -------------------------------------------------------------- */

/* Botones del cuadro en el estado principal (0x80010010): lhu en los eventos y la camara, sh en el mando. */
extern u16 D_80010010;

/* Banderas de `main`, de los eventos y de los menus: se escriben con sb y se leen con lbu. */
extern u8 D_800694E0;
extern u8 D_800694E1;
extern u8 D_800694E8;
extern u8 D_80069594;
extern u8 D_800695DC;
extern u8 D_80069659;
extern u8 D_8006965E;

/*
 * D_8006966A: bandera de menu. La leen con lb las rutinas que ya estan en C (func_80031FE0,
 * func_8004048C) y con lbu las que aun no lo estan, que solo la comparan con cero.
 */
extern s8 D_8006966A;

/* Cursor descendente de la demostracion: se carga y se guarda como puntero (lw / sw). */
extern u16* D_800695B0;

#endif

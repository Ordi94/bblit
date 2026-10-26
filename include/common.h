#ifndef COMMON_H
#define COMMON_H

/*
 * Tipos de ancho fijo del proyecto. El compilador (GCC 2.8.1) es C89: sin <stdint.h>, sin
 * comentarios de linea y sin declaraciones despues de sentencias.
 *
 * En MIPS R3000 de 32 bits: char = 8, short = 16, int = long = 32.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed char s8;
typedef signed short s16;
typedef signed int s32;

/* Variantes volatiles para registros de hardware y memoria que cambia sin avisar. */
typedef volatile unsigned char vu8;
typedef volatile unsigned short vu16;
typedef volatile unsigned int vu32;

#ifndef NULL
#define NULL ((void *)0)
#endif

#include "macro.h"

#endif

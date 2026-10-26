#ifndef EVENTOS_H
#define EVENTOS_H

#include "common.h"

/*
 * Tipos compartidos del interprete de eventos.
 *
 * Las rutinas de condicion reciben (objeto, registro de condicion) y devuelven 0 o 1; las de
 * accion reciben (objeto, registro de accion) y no devuelven nada. El primer byte del registro
 * de condicion (offset 0) elige la rutina y el del registro de accion esta en el offset 3.
 */

/* Objeto de escena; solo se declaran los campos que el interprete usa. */
typedef struct Objeto {
    struct Objeto* siguiente;
    u8 pad04[0x14 - 0x04];
    u32 flags14;
    u32 flags18;
    u16 w1C;
    s16 s1E;
    u8 pad20[2];
    u16 w22;
    u8 pad24[2];
    u16 w26;
    u16 w28;
    u8 pad2A[0x2C - 0x2A];
    u16 w2C;
    u8 pad2E[0x38 - 0x2E];
    u16 w38;
    u8 pad3A[2];
    u16 w3C;
    u8 pad3E[0x6C - 0x3E];
    struct Objeto* p6C;
    struct Objeto* p70;
    u8 pad74[0xC0 - 0x74];
    struct Objeto* pC0;
    s32 iC4;
    u8 padC8[0xDC - 0xC8];
    u16 wDC;
    u16 wDE;
    u16 wE0;
    u8 padE2[0xE4 - 0xE2];
    s32 xE4;
    s32 yE8;
    s32 zEC;
    u8 padF0[0x158 - 0xF0];
    s32 i158;
    u32 flags15C;
    u8 pad160[0x17C - 0x160];
    u16 w17C;
    u16 w17E;
    u16* p180;
    u8 pad184[0x192 - 0x184];
    u16 w192;
    u8 pad194[2];
    u16 w196;
} Objeto;

/* Registro de accion: el codigo de operacion esta en el byte 3; w4 y w6 son los operandos. */
typedef struct Accion {
    u8 pad00[4];
    u8 b4;
    u8 pad5;
    u16 w6;
} Accion;
#define ACC_W4(a) (*(u16*)&(a)->b4)

/*
 * Estado principal del juego en 0x80010000 (RAM previa al ejecutable): el original lo
 * direcciona con un unico lui, es decir, con una direccion constante y no con simbolos
 * externos separados.
 */
typedef struct EstadoPrincipal {
    u32 modo;
    u8 pad04[0x10 - 0x04];
    u16 botones;
    s16 s12;
    u8 pad14[0x40 - 0x14];
    u8 r[0x100];
} EstadoPrincipal;
#define ESTADO ((EstadoPrincipal*)0x80010000)

/* Estado de la camara y de la escena en 0x8006D928. */
typedef struct EstadoCamara {
    u8 pad00[0x0C];
    s32 x;
    s32 y;
    s32 z;
    u8 pad18[0x80 - 0x18];
    u16 flags80;
    u8 pad82[0x86 - 0x82];
    s16 s86;
    s16 s88;
    s16 s8A;
} EstadoCamara;
extern EstadoCamara D_8006D928;

/* Banco de registros de 8 bits de los eventos. */
extern u8 D_8006AA70[];

/* Objeto controlado (el protagonista). */
extern Objeto* D_80069698;

#endif

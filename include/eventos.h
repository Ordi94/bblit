#ifndef EVENTOS_H
#define EVENTOS_H

#include "common.h"
#include "globales.h"

/*
 * Tipos compartidos del interprete de eventos.
 *
 * Las rutinas de condicion reciben (objeto, registro de condicion) y devuelven 0 o 1; las de
 * accion reciben (objeto, registro de accion) y no devuelven nada. El primer byte del registro
 * de condicion (offset 0) elige la rutina y el del registro de accion esta en el offset 3.
 */

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


/* Objeto controlado (el protagonista). */

#endif

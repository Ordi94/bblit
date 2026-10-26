#ifndef ARRANQUE_H
#define ARRANQUE_H

#include "common.h"

/*
 * Estado principal del juego en la RAM previa al ejecutable (0x80010000..0x8001013F, 0x140 bytes):
 * una sola definicion para el arranque, el bucle principal, el mando, los eventos, la camara y la
 * tarjeta de memoria. Los 0x140 bytes completos viajan en el archivo de partida (tarjeta_de_memoria.c).
 *
 * El juego accede a esta zona por una direccion absoluta: GCC comparte el `lui` de la base cuando la
 * direccion vive en una variable puntero, por eso el C usa `EstadoPrincipal* e = ESTADO_PRINCIPAL;`.
 * Algunos accesos del original usan en cambio la forma simbolica (un `lui` propio por acceso); esos
 * bytes se declaran aparte como variables sueltas en globales.h (D_80010000, D_8001000A, D_8001003E,
 * D_80010041, D_80010065, D_800100E6...) y no se acceden por esta estructura: hacerlo cambia el
 * reparto del `lui` y el codigo generado.
 *
 * Anchos y signos por campo (los demas son relleno):
 * - nivel (s32): las comparaciones de `main` lo tratan con signo (nivel >= 0); el interprete de
 *   eventos solo lo escribe.
 * - botones_a, botones_c, botones_e y botones (u16): la pausa lee botones_a con lhu; el mando
 *   escribe los cuatro con sh y el interprete lee botones con lhu.
 * - eje_x y eje_y (u16): el mando solo los escribe (sh). El interprete multiplica eje_x por el
 *   avance con lh (func_80031794 y func_800317FC) y lo lee con un cast (s16) local: declararlos s16 sube
 *   func_8004048C de 7264 a 8229 puntos.
 * - f16..f1E y centro_y (s16): func_80015EC0 los inicia con sh; el mando carga centro_x y
 *   centro_y como s16 (lh) para restarlos del valor crudo del analogico.
 * - r[] (u8 x 0x100): banco de registros de 8 bits de 0x80010040 que leen y escriben los eventos
 *   (indice variable) y las rutinas fijas con indice constante.
 */
/*
 * Entradas del mando que escriben func_8003FFA0, func_80040158 y func_8004048C (0x80010008..0x8001003F).
 * func_80040158 recibe la direccion de este bloque (0x80010008) y lee botones_c y mapa por ella.
 */
typedef struct Mando {
    u8 pad00[2];
    u16 botones_a;                 /* 0x0A: la pausa lo lee (bit 0x800) y func_80015FC8 espera sus bits */
    u16 botones_c;                 /* 0x0C: botones del cuadro que lee func_80040158 */
    u16 botones_e;                 /* 0x0E: botones del cuadro anterior, enmascarados */
    u16 botones;                   /* 0x10: botones pulsados (cero = mando ocioso) */
    u16 eje_x;                     /* 0x12: desviacion del analogico en X (el interprete lo lee como s16) */
    u16 eje_y;                     /* 0x14: desviacion del analogico en Y */
    s16 f16;                       /* 0x16..0x20: seis valores de 16 bits que func_80015EC0 inicia */
    s16 f18;
    s16 centro_x;                  /* 0x1A: centro del analogico en X */
    s16 f1C;
    s16 f1E;
    s16 centro_y;                  /* 0x20: centro del analogico en Y */
    u16 w22;                       /* 0x22: solo escrito por el mando */
    u16 w24;                       /* 0x24: solo escrito por el mando */
    u16 direcciones[4];            /* 0x26: mascaras de las cuatro direcciones */
    u16 mapa[8];                   /* 0x2E: mascara de salida por boton fisico (copia de D_8005EE38) */
    u16 w3E;                       /* 0x3E: botones agrupados que consultan los eventos */
} Mando;

typedef struct EstadoPrincipal {
    s32 nivel;                     /* 0x00: numero de contenedor .BZZ en curso (argumento de la carga de archivo) */
    u32 suma;                      /* 0x04: suma de control del bloque al guardar la partida */
    Mando mando;                   /* 0x08 */
    u8 r[0x100];                   /* 0x40..0x13F: banco de registros de 8 bits, ver BANCO_* */
} EstadoPrincipal;

#define ESTADO_PRINCIPAL ((EstadoPrincipal*)0x80010000)

/* Indices del banco r[] con papel conocido (la direccion es 0x80010040 + indice). */
#define BANCO_DEMO 0x0F      /* 0x8001004F: distinto de cero durante la demostracion */
#define BANCO_CONFIG 0x11    /* 0x80010051: indice de la tabla de configuracion de botones */
#define BANCO_PAUSA 0x36     /* 0x80010076: la pausa solo ocurre si vale cero */
#define BANCO_PARTIDA 0x9F   /* 0x800100DF: ranura de partida (1 a 6) */
#define BANCO_VIBRACION 0xA7 /* 0x800100E7: bits 7 y 0 habilitan la vibracion */

#endif

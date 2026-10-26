#ifndef ARRANQUE_H
#define ARRANQUE_H

#include "common.h"

/*
 * Estado principal del juego en la RAM previa al ejecutable (0x80010000..0x8001013F). Solo se declaran
 * los campos que el arranque, el bucle principal y la tarjeta de memoria leen o escriben; los huecos
 * son relleno. Los 0x140 bytes completos viajan en el archivo de partida (ver tarjeta_de_memoria.c).
 *
 * El juego accede a esta zona por una direccion absoluta: GCC comparte el `lui` de la base cuando la
 * direccion vive en una variable puntero, por eso el C usa `EstadoPrincipal* e = ESTADO_PRINCIPAL;`.
 */
typedef struct EstadoPrincipal {
    s32 nivel;                     /* 0x00: numero de contenedor .BZZ en curso (argumento de la carga de archivo) */
    u32 suma;                      /* 0x04: suma de control del bloque al guardar la partida */
    u8 pad08[0x0A - 0x08];
    /* Los sufijos a, c y e de los tres primeros campos son el ultimo digito hexadecimal de su desplazamiento (0x0A, 0x0C, 0x0E): su papel individual no se conoce, solo que la demostracion los reescribe junto con `botones`. */
    u16 botones_a;                 /* 0x0A: la pausa lo lee (bit 0x800) y func_80015FC8 espera sus bits */
    u16 botones_c;                 /* 0x0C: solo escrito por la demostracion */
    u16 botones_e;                 /* 0x0E: solo escrito por la demostracion */
    u16 botones;                   /* 0x10: botones pulsados (cero = mando ocioso) */
    u8 pad12[0x16 - 0x12];
    s16 f16;                       /* 0x16..0x20: seis valores de 16 bits que func_80015EC0 inicia */
    s16 f18;
    s16 f1A;
    s16 f1C;
    s16 f1E;
    s16 f20;
    u8 pad22[0x40 - 0x22];
    u8 f40;                        /* 0x40..0x13F: 256 bytes que func_80015EC0 pone a cero */
    u8 f41;
    u8 f42;
    u8 pad43[0x45 - 0x43];
    u8 f45;
    u8 pad46;
    u8 f47;
    u8 pad48[0x4E - 0x48];
    u8 f4E;                        /* 0x4E: func_800156F4 lo fija a 0x38 en dos ramas; significado desconocido */
    u8 f4F;                        /* 0x4F: distinto de cero durante el ciclo de demostracion */
    u8 f50;
    u8 f51;
    u8 pad52[0x76 - 0x52];
    u8 f76;
    u8 pad77[0xCD - 0x77];
    u8 fCD;
    u8 padCE[0xDF - 0xCE];
    u8 fDF;                        /* 0xDF: ranura de partida (1 a 6) */
    u8 padE0[0xE5 - 0xE0];
    u8 fE5;
    u8 fE6;
    u8 fE7;
    u8 fE8;
    u8 padE9[0xF6 - 0xE9];
    u8 fF6;
    u8 padF7;
    u8 fF8;
    u8 padF9[0x13B - 0xF9];
    u8 f13B;                       /* 0x13B: func_800156F4 lo pone a 0 tras cargar una partida; significado desconocido */
    u8 f13C;
    u8 pad13D[0x140 - 0x13D];
} EstadoPrincipal;

#define ESTADO_PRINCIPAL ((EstadoPrincipal*)0x80010000)

#endif

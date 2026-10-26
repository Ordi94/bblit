#ifndef AUDIO_H
#define AUDIO_H

#include "common.h"
#include "globales.h"

/*
 * Tipos de la tabla de ranuras de voz de efectos (D_8006B378), compartidos por el audio, que la
 * llena y la recorre, y por el interprete de eventos, que consulta que efecto suena en cada ranura.
 * Una sola definicion: dos vistas de la misma memoria con otros tipos no las detecta el enlazador.
 */

/*
 * Definicion de un efecto de sonido: 128 entradas de 8 bytes en D_8006AEE0. func_8003EB88 las
 * registra al cargar el nivel; func_8003F06C busca por identificador y func_8003F528 lee los
 * campos de la entrada que tiene asociada cada ranura de voz.
 *
 * grupo y fila indexan las tablas de sonidos que lee func_8003FDEC (lbu 2 y 3 de la entrada en
 * func_8003F528). cuenta (+6) es el tope de volumen cuando flags tiene el bit 2 (func_8003F06C,
 * func_8003F3F0) y el periodo de repeticion en cuadros cuando tiene los bits 4 y 8
 * (func_8003F528); azar (+7) es el umbral de la tirada de BugsRand cuando flags tiene el bit 7.
 */
typedef struct Efecto {
    u16 id;
    u8 grupo;
    u8 fila;
    u16 flags;
    u8 cuenta;
    u8 azar;
} Efecto;

/* Volumen de una voz: un byte por canal. Se pasa por valor a las rutinas del SPU. */
typedef struct Canales {
    u8 izq;
    u8 der;
} Canales;

typedef union VolVoz {
    u16 w;
    Canales c;
} VolVoz;

/*
 * Ranura de voz de efecto: 24 entradas de 0x14 bytes en D_8006B378. Cada campo cita la
 * instruccion del ensamblador que fija su ancho y su signo.
 */
typedef struct Voz {
    /* +0x00: sh / lhu (func_8003F06C 0x8003F320 y 0x8003F304): bit 15 ranura ocupada; bits 0, 1 y 2 estado. */
    u16 flags;
    /* +0x02: lh con signo (func_8003F528, -0xA($s0) con $s0 = ranura + 0xC): voz del SPU, negativa si no hay. */
    s16 voz;
    /* +0x04: sw / lw (func_8003F06C 0x8003F2F4, -0xA($v1) con $v1 = ranura + 0xE): objeto emisor. */
    Objeto* objeto;
    /* +0x08: sw / lw (func_8003F06C 0x8003F2E0) y despues lhu 0 (0x8003F2E4): efecto en curso. */
    Efecto* efecto;
    /* +0x0C: lhu (func_8003F528): volumen de la voz, un byte por canal. */
    VolVoz vol;
    /* +0x0E: sb / lbu (func_8003F06C 0x8003F318): clave que func_8003F528 compara con su argumento. */
    u8 id;
    u8 pad0F;
    /* +0x10: sh / lhu (func_8003F528): pasadas que lleva sonando la voz (a 0 al encenderla). */
    u16 cuenta;
    u8 pad12[2];
} Voz;

extern Voz D_8006B378[];

#endif

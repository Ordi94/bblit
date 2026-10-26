#include "common.h"

/*
 * Pendiente de traducir: tiene marco de pila (addiu sp inicial y epilogo simetrico), asi que no es una
 * rutina escrita a mano; la marca Handwritten del particionador procede de instrucciones sueltas del GTE.
 */
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_2", func_80025938);

/*
 * Pendiente de traducir: cuerpo vacio (jr ra con nop en el hueco, 8 bytes); pasarlo a C es solo cuestion de
 * decidirlo, no hay nada que igualar.
 */
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_2", func_80025B24);

/*
 * Pendiente de traducir: tiene marco de pila de 0x30 bytes con s0..s4 y ra guardados (no es manuscrita); la
 * marca Handwritten del particionador procede de las instrucciones sueltas del GTE (ctc2, mvmva, swc2).
 */
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_2", func_80025B2C);

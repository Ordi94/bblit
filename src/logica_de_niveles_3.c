#include "common.h"
#include "globales.h"

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_80026298);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_80026FEC);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002BA80);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002C1DC);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002CB8C);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002CEC4);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002D03C);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002D68C);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002EA9C);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002EAA4);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F018);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F510);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F614);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F6B4);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F968);

INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F970);

#ifdef NON_MATCHING
/*
 * Operacion aritmetica sobre un registro de 16 bits repartido en dos bytes (D_80010047 es el
 * bajo y D_8001013C el alto). Diferencias con el original: este lee ambos bytes con un unico
 * 'lui' (los dos simbolos comparten la parte alta) y conserva una copia del valor en el hueco de
 * retardo del primer salto; el compilador genera dos 'lui' porque son variables externas
 * distintas. Hay que declararlas como miembros de una misma estructura o arreglo.
 *
 * El operando se trunca a un byte dentro de la rutina (andi 0xFF en 0x8002F9AC y 0x8002F9DC) y los
 * llamadores le pasan el valor de 16 bits sin truncar (lhu): por eso el parametro es s32 y el
 * truncamiento un cast. Declarado u8, cada llamador recorta el argumento con lbu.
 */
extern u8 D_8001013C;
extern u8 D_80010047;

void func_8002F990(s32 a0, s32 a1)
{
    u32 reg;
    u32 alto;

    reg = D_80010047 | (D_8001013C << 8);
    if (a1 == 0) {
        reg = (u8)a0 + reg;
    }
    if (a1 == 1) {
        reg = reg + 1;
    }
    if (a1 == 2) {
        reg = reg - 1;
    }
    alto = reg & 0xFFFF;
    if (a1 == 3) {
        reg = reg - (u8)a0;
        alto = reg & 0xFFFF;
    }
    D_80010047 = reg;
    D_8001013C = alto >> 8;
}
#else
INCLUDE_ASM("asm/nonmatchings/logica_de_niveles_3", func_8002F990);
#endif

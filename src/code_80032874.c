#include "common.h"

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80032874);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80032894);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80032A24);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80032B2C);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_800330AC);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80033358);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80034E7C);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_8003502C);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_800351B4);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80035244);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_800353B0);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80036164);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_800361CC);

/* Ranura de una reserva: 'marca' con el bit 0 activo indica que esta ocupada. */
typedef struct Ranura {
    s32 dato;
    u32 marca;
} Ranura;

/* Devuelve la primera ranura marcada, la libera y avanza por la reserva de 'paso' en 'paso'. */
Ranura* func_80036204(u8* base, s32 paso, s32 total)
{
    u8* p;
    u8* fin;

    p = base;
    fin = p + total;
    while (p < fin) {
        if (((Ranura*)p)->marca & 1) {
            ((Ranura*)p)->marca = 0;
            ((Ranura*)p)->dato = 0;
            return (Ranura*)p;
        }
        p = base + paso;
        base = p;
    }
    return 0;
}

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80036250);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_800362D0);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80036358);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_8003638C);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_800363D4);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80036474);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_800364E0);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_8003652C);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_800365D0);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80036734);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_800368E8);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_8003690C);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80037048);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80037184);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_8003753C);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80037580);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_800375C4);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_800375F8);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_8003760C);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_800379A0);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80037B08);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80037C00);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80037CF8);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80037D3C);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80037DB4);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80037FB8);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_80037FE8);

INCLUDE_ASM("asm/nonmatchings/code_80032874", func_8003861C);

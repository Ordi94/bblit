#include "common.h"

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002F9F8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FA30);

/* Compara un byte de un registro con la entrada de la tabla D_8006AA70 que indica otro byte. */
extern u8 D_8006AA70[];

s32 func_8002FA38(void* a0, u8* a1)
{
    return D_8006AA70[a1[2]] == a1[1];
}

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FA60);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FA90);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FAB8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FAE8);

/* Igual que func_8002FA38 pero con la comparacion 'mayor que'. */
s32 func_8002FB18(void* a0, u8* a1)
{
    return D_8006AA70[a1[2]] > a1[1];
}

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FB38);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FB58);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FB80);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FBA8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FBD0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FBF0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FC10);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FC38);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FC60);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FC88);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FCB0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FCD8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FD00);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FD24);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FD50);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FD74);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FDA0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FDCC);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FDE8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FE04);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FE28);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FE4C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FE68);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FE84);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FEA8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FECC);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FEF0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FF14);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FF38);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FF78);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FF98);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FFB8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FFD8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FFF8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030018);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003004C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003006C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003008C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030098);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800300A4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800300C4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800300E4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800301E8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800302F8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030404);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030504);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030520);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003053C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003055C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030590);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800305C4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030620);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030654);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030688);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800306C0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800306D0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800306F8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003071C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030734);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003074C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800307B4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800307D4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800307F4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030814);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030834);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030874);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003088C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030924);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030990);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800309A8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800309B8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800309C8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800309E0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800309F8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030A18);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030A38);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030B78);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030CB8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030CE0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030D08);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030D34);

/*
 * Comprueba que el valor (alto) de la estructura global D_80069698 este dentro del rango
 * [min, max] de la entrada. Las dos comparaciones con return explicito de 1 y 0 producen las
 * dos ramas con el valor en el hueco de retardo, como el original.
 */
typedef struct Rango {
    s8 pad0;
    s8 min;
    s8 max;
} Rango;

typedef struct EstadoGlobal {
    u8 pad0[0xE8];
    s32 valor;
} EstadoGlobal;

extern EstadoGlobal* D_80069698;

s32 func_80030D60(void* a0, Rango* a1)
{
    s32 v;

    v = D_80069698->valor >> 8;
    if (v >= a1->min && v <= a1->max) {
        return 1;
    }
    return 0;
}

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030DA4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030E20);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030EB4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030ECC);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030F04);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030F0C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030F30);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030F88);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030FA4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030FBC);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030FE0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031038);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031050);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031064);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031088);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800310A8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800310D0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800310F4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003111C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031140);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031164);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031184);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800311AC);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800311D4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031214);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800312B0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800312F8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003133C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031350);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031384);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800313D4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003141C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031424);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003147C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031500);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031520);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031540);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031554);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031624);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031650);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031694);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800316BC);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031714);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003173C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031794);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800317FC);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003186C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800318AC);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800318F8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003190C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003192C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031948);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031960);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031974);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031990);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800319AC);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800319CC);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031A0C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031A34);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031AE4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031B1C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031B50);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031B64);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031B78);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031B98);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031BAC);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031C10);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031C54);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031CC4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031CCC);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031CD4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031D1C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031D30);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031D38);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031D60);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031E24);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031EF8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031F70);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031FBC);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031FE0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800320D8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800320F4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032110);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003213C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032170);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800321A4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800321D8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003220C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003222C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032318);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032344);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032360);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003237C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003238C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800323A0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032474);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032490);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800324A4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003264C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032668);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032684);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032694);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800326B4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800326D0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800326EC);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032708);

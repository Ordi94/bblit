#include "common.h"

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002BA80);

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002C1DC);

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002CB8C);

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002CEC4);

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002D03C);

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002D68C);

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002EA9C);

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002EAA4);

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002F018);

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002F510);

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002F614);

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002F6B4);

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002F968);

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002F970);

#ifdef NON_MATCHING
/*
 * Operacion aritmetica sobre un registro de 16 bits repartido en dos bytes (D_80010047 es el
 * bajo y D_8001013C el alto). Diferencias con el original: este lee ambos bytes con un unico
 * 'lui' (los dos simbolos comparten la parte alta) y conserva una copia del valor en el hueco de
 * retardo del primer salto; el compilador genera dos 'lui' porque son variables externas
 * distintas. Hay que declararlas como miembros de una misma estructura o arreglo.
 */
extern u8 D_8001013C;
extern u8 D_80010047;

void func_8002F990(u8 a0, s32 a1)
{
    u32 reg;
    u32 alto;

    reg = D_80010047 | (D_8001013C << 8);
    if (a1 == 0) {
        reg = a0 + reg;
    }
    if (a1 == 1) {
        reg = reg + 1;
    }
    if (a1 == 2) {
        reg = reg - 1;
    }
    alto = reg & 0xFFFF;
    if (a1 == 3) {
        reg = reg - a0;
        alto = reg & 0xFFFF;
    }
    D_80010047 = reg;
    D_8001013C = alto >> 8;
}
#else
INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002F990);
#endif

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002F9F8);

/* Compara un byte de un registro con la entrada de la tabla D_8006AA70 que indica otro byte. */
extern u8 D_8006AA70[];

s32 func_8002FA38(void* a0, u8* a1)
{
    return D_8006AA70[a1[2]] == a1[1];
}

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002FA60);

/* Igual que func_8002FA38 pero con la comparacion 'mayor que'. */
s32 func_8002FB18(void* a0, u8* a1)
{
    return D_8006AA70[a1[2]] > a1[1];
}

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_8002FB38);

#ifdef NON_MATCHING
/*
 * Comprueba que el valor (alto) de la estructura global D_80069698 este dentro del rango
 * [min, max] de la entrada. Diferencias con el original: este escribe el desplazamiento
 * aritmetico sobre a0 (argumento que la funcion no usa) y produce el 1 con una rama; el
 * compilador reutiliza el registro del dato y convierte la rama en un 'xori'.
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
    s32 r;

    v = D_80069698->valor >> 8;
    r = 0;
    if (v >= a1->min) {
        r = 1;
        if (a1->max < v) {
            r = 0;
        }
    }
    return r;
}
#else
INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_80030D60);
#endif

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_80030DA4);

INCLUDE_ASM("asm/nonmatchings/code_8002BA80", func_80030ECC);

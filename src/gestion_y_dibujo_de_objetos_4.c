#include "common.h"
#include "objetos.h"

extern u32 D_80069610;
extern u32 D_80069614;
extern s32 D_8006954C;
extern vu16 D_800695A6;

/* Resta de vectores de tres componentes: resultado = b - a. */
void func_80039BFC(s32* a, s32* b, s32* resultado)
{
    resultado[0] = b[0] - a[0];
    resultado[1] = b[1] - a[1];
    resultado[2] = b[2] - a[2];
}

/* Producto vectorial de dos vectores de tres componentes: resultado = a x b (sin GTE). */
void func_80039C3C(s32* a, s32* b, s32* resultado)
{
    resultado[0] = a[1] * b[2] - a[2] * b[1];
    resultado[1] = a[2] * b[0] - a[0] * b[2];
    resultado[2] = a[0] * b[1] - a[1] * b[0];
}

/*
 * Espera a que el contador de posicion del anillo de dibujo D_80069610, que reescribe el retorno
 * de llamada de VSync, quede a menos de 0x800 posiciones por delante de 'limite' (el anillo
 * tiene D_8006954C posiciones: la diferencia negativa se corrige con su longitud). Si pasan
 * cuatro VSync sin avanzar, restaura la posicion anterior D_80069614 para no bloquearse.
 */
void func_80039CD0(s32 limite)
{
    s32 anillo;
    u32 previo;
    s32 d;

    anillo = D_8006954C;
    previo = D_80069614;
    for (;;) {
        d = D_80069610 - limite;
        if (d < 0) {
            d -= 0x400;
            d += anillo;
        }
        if (d >= 0x800) {
            return;
        }
        if ((s16)D_800695A6 >= 4) {
            D_80069610 = previo;
        }
    }
}

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_4", func_80039D44);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_4", func_8003A3D0);

INCLUDE_ASM("asm/nonmatchings/gestion_y_dibujo_de_objetos_4", func_8003A5C8);

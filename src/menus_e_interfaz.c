#include "common.h"
#include "globales.h"

/*
 * Estado del fundido de pantalla (todas las variables son datos pequenos que el original
 * direcciona con lui + desplazamiento y escribe con lui at, de ahi g = 8 para este archivo).
 * D_80069566: nivel actual del fundido, en 1/4096. D_80069668: nivel complementario que usa el
 * dibujo. D_80069686: paso por cuadro. D_8006966A: banderas de fase (ver func_8003ABB4).
 */
extern s16 D_80069566;
extern s16 D_80069668;
extern u16 D_80069686;

/*
 * Anillo de marcas de tiempo de los cuadros (los mismos datos que usa la presentacion de cuadros):
 * D_80069610 la reescribe el retorno de llamada de VSync, D_800695A6 cuenta los VSync desde el
 * ultimo dibujo y D_8006954C es la longitud del anillo.
 */
extern s32 D_8006954C;
extern u32 D_80069610;
extern u32 D_80069614;
extern vu16 D_800695A6;

/*
 * Cursor de escritura de primitivas GPU: direccion de la siguiente primitiva libre del cuadro. Se
 * compara con signo contra los limites del contexto, por eso es s32 y no un puntero.
 */
extern s32 D_80076188;
extern void func_80039CD0(s32 cursor);

/* Contexto de dibujo: rango del buffer de primitivas (+0x2C inicio, +0x30 limite). */
typedef struct ContextoDibujo {
    u8 pad00[0x2C];
    s32 inicio;
    s32 limite;
} ContextoDibujo;

void func_8003AA38(void)
{
}

void func_8003AA40(void)
{
}

void func_8003AA48(void)
{
}

void func_8003AA50(u8 modo, u16 duracion)
{
    D_8006966A = modo;
    D_80069686 = duracion;
    D_80069566 = 0;
    D_80069668 = 0x1000;
}

void func_8003AA7C(u8 modo, u16 duracion)
{
    D_8006966A = modo;
    D_80069686 = duracion;
    D_80069566 = 0x1000;
    D_80069668 = 0;
}

void func_8003AAA8(void)
{
    u16 actual;
    u8 fase;

    actual = D_80069566;
    if (D_80069566 >= 0x1000) {
        fase = D_8006966A;
        D_80069566 = 0x1000;
        D_80069668 = 0;
        if (fase & 0x40) {
            D_8006966A = (fase & 0xFE) | 2;
        } else {
            D_8006966A = 0x10;
        }
    } else {
        D_80069668 = 0x1000 - actual;
        D_80069566 = actual + D_80069686;
    }
}

void func_8003AB3C(void)
{
    u16 actual;
    u8 fase;

    actual = D_80069566;
    if (D_80069566 <= 0) {
        fase = D_8006966A;
        D_80069566 = 0;
        D_80069668 = 0x1000;
        if (fase & 0x40) {
            D_8006966A = 0x20;
        }
    } else {
        D_80069668 = 0x1000 - actual;
        D_80069566 = actual - D_80069686;
    }
}

void func_8003ABB4(void)
{
    u8 fase;

    fase = D_8006966A;
    if (D_8006966A != 0) {
        if (fase & 4) {
            func_8003AA50(1, 0x100);
        } else if (fase & 8) {
            func_8003AA7C(2, 0x100);
        } else if (D_8006AA70[0x19] == 0) {
            if (fase & 2) {
                func_8003AB3C();
            } else if (fase & 1) {
                func_8003AAA8();
            }
        }
        if (D_8006966A & 0x30) {
            D_8006966A = 0;
            D_80069668 = 0;
        }
    } else if (D_8006AA70[0xC] != 0) {
        D_80069668 = 0xE00;
    } else {
        D_80069668 = 0;
    }
}

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003ACA8);

/* Pendiente: puntuacion 1245 con la configuracion versionada (g = 8 del archivo). El cursor de primitivas se carga antes que en el original y los registros t0/t1/a1/v1 se reparten distinto; la estructura de las dos primitivas de 6 palabras coincide. Variantes probadas: 14 (orden de las 6 escrituras, 720 permutaciones del primer bloque, macro sobre D_80076188, estructura de paquete). */
#ifdef NON_MATCHING
s32 func_8003AE08(u32* puntos, ContextoDibujo* ctx)
{
    u32* tabla;
    s32 actual;
    s32 siguiente;

    func_80039CD0(D_80076188);
    tabla = (u32*)D_8006AEA0[D_8006967C].org;
    actual = D_80076188;
    ((u32*)actual)[0] = *tabla | 0x05000000;
    ((u32*)actual)[2] = 0x80000000;
    ((u32*)actual)[1] = 1;
    ((u32*)actual)[3] = puntos[3];
    ((u32*)actual)[4] = puntos[5];
    ((u32*)actual)[5] = puntos[7];
    *tabla = (actual << 8) >> 8;
    actual = D_80076188;
    siguiente = actual + 0x18;
    D_80076188 = siguiente;
    if (puntos[8] != 0) {
        tabla = (u32*)D_8006AEA0[D_8006967C].org;
        ((u32*)actual)[6] = *tabla | 0x05000000;
        ((u32*)siguiente)[1] = 1;
        ((u32*)siguiente)[2] = 0x80000000;
        ((u32*)siguiente)[3] = puntos[4];
        ((u32*)siguiente)[4] = puntos[6];
        ((u32*)siguiente)[5] = puntos[8];
        *tabla = (siguiente << 8) >> 8;
        D_80076188 += 0x18;
    }
    if (ctx->limite < D_80076188) {
        D_80076188 = ctx->inicio;
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003AE08);
#endif

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003AF8C);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003B26C);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003B354);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003B5AC);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003BDD0);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003C014);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003C1C8);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003CA5C);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003D0D4);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003D7C4);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003D814);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003D880);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003D904);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003D988);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003DA4C);

INCLUDE_ASM("asm/nonmatchings/menus_e_interfaz", func_8003DD70);

void func_8003DF10(s32 limite)
{
    s32 anillo;
    u32 reinicio;
    s32 libre;

    anillo = D_8006954C;
    reinicio = D_80069614;
    while (1) {
        libre = D_80069610 - limite;
        if (libre < 0) {
            libre -= 0x400;
            libre += anillo;
        }
        if (libre >= 0x800) {
            return;
        }
        if ((s16)D_800695A6 >= 4) {
            D_80069610 = reinicio;
        }
    }
}

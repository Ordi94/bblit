#include "common.h"
#include "globales.h"
#include "arranque.h"
#include "psyq/TYPES.H"
#include "psyq/LIBGTE.H"
#include "psyq/LIBGPU.H"
#include "psyq/LIBGS.H"

extern s32 D_80069534;
extern s32 D_80069510;
extern s32 D_80069638;
extern u32 D_80069518;
extern void* D_80069630;
extern void* D_80069508;
extern void* D_800694B8;
extern void* D_800694D8;
extern s32 D_80076188;
extern s32 D_8006AD40[];
extern u8 D_8006AD80[];
extern GsRVIEW2 D_8006D928;
extern GsOT D_8006AE20[];
extern GsOT D_8006AE60[];
extern GsOT D_8006AEA0[];

extern u16 D_800694F0;
extern u32 D_800694FC;
extern volatile u16 D_80069676;
extern s32 D_8006CF68[];
extern u16 D_8006D9A8;
extern u8 D_8006965A;
extern u8 D_8006963C;
extern u8 D_80069595;
extern u8 D_800695A0;
extern u8 D_80069628;

extern s32 SetRCnt(u32 canal, u16 destino, s32 modo);
extern s32 StartRCnt(u32 canal);
extern s32 VSyncCallback(void (*funcion)());
extern void srand(u32 semilla);
extern void func_80044D44(void);
extern void func_80044E58(void);
extern void func_80040EB4(void);
extern s32 func_800415A0(s16 nivel, void* destino);
extern void func_80019364(void* tabla);
extern void func_80040AF0();
extern void func_8003DF84(void);
extern void func_8003AA50(u32 modo, u32 duracion);
extern void func_8003AA7C(u32 modo, u32 duracion);
extern void func_8003E9E8(void);
extern void func_800156F4();
extern void func_80015E94(void);
extern void func_80015F38(void);
extern void func_80037FB8(void* a);
extern void func_80037FE8(void* a);
extern void func_80040240(void);
extern void func_8003E88C(void);
extern void func_8003FC88(void);
extern void func_8003E948(void);
extern void func_8003FD60(void);
extern void func_8003E094(void);
extern void func_8003E068(void);
extern void func_800445E8(s16 nivel);
extern s32 BugsRand(void);
extern s32 VSync(s32 modo);
extern void SetDispMask(s32 mascara);
extern void func_800443CC(void);
extern void func_8004443C(s32 nivel);
extern void func_80044588(s32 nivel);
extern void func_8004048C(void);
extern void func_80015EC0(void);
extern void func_80015FC8(s32 segundos, u16 mascara);
extern void func_80016044(void);
extern void func_800160A8(void);
extern void func_8003E3C0(void);
extern void func_8003F3F0(s16 indice);
extern void func_800353B0(u32 a);
extern void func_80037048(void* a);
extern void func_800399C8(void* a);
extern void func_8003B5AC(void* a);
extern void func_8003A5C8(void* a);
extern void func_80045150(void* a);
extern void func_80037184(void* a);
extern void func_8001020C(s32 a);

void func_80015EC0(void)
{
    EstadoPrincipal* e;
    s32 i;
    u8* p;

    i = 0xFF;
    p = (u8*)0x800100FF;
    do {
        p[0x40] = 0;
        p--;
        i--;
    } while (i >= 0);
    e = ESTADO_PRINCIPAL;
    e->f41 = 6;
    e->f42 = 6;
    e->f40 = 3;
    e->fE5 = 0x80;
    e->fE6 = 0x50;
    D_80069594 = 0x50;
    e->fE7 = 1;
    e->f16 = 0;
    e->f18 = 0xFF;
    e->f1A = 0x7F;
    e->f1C = 0;
    e->f1E = 0xFF;
    e->f20 = 0x7F;
}

void func_80015F38(void)
{
    EstadoPrincipal* e;
    u8 a;
    u8 b;
    u8 c;
    u8 d;
    u8 f;
    u8 g;

    e = ESTADO_PRINCIPAL;
    a = e->f50;
    b = e->f51;
    c = e->fE5;
    d = e->fE6;
    f = e->fE7;
    g = e->fE8;
    func_80015EC0();
    e->f50 = a;
    e->f51 = b;
    e->fE5 = c;
    e->fE6 = d;
    D_80069594 = d;
    e->fE7 = f;
    e->fE8 = g;
}

void func_80015FC8(s32 segundos, u16 mascara)
{
    s32 i;

    for (i = 0; i < segundos * 0x3C; i++) {
        VSync(0);
        func_8004048C();
        if (ESTADO_PRINCIPAL->botones_a & mascara) {
            break;
        }
    }
}

void func_80016044(void)
{
    RECT r;
    s32 i;

    i = 0;
    r.x = 0;
    r.y = 0;
    r.w = 0x200;
    r.h = 0x200;
    do {
        VSync(0);
        MoveImage(&r, 0x200, 0);
        DrawSync(0);
        i++;
    } while (i < 2);
}

void func_800160A8(void)
{
    SetDispMask(0);
    func_800443CC();
    SetDefDispEnv(&D_8006CF78, 0x200, 0, 0x200, 0x1E0);
    D_8006CF78.isrgb24 = 0;
    do {
    } while (PutDispEnv(&D_8006CF78) == 0);
    SetDispMask(1);
}

void func_80016118(void)
{
    EstadoPrincipal* e;

    func_800160A8();
    e = ESTADO_PRINCIPAL;
    e->nivel = 0x4E;
    func_8004443C(0x4E);
    e->nivel = 0x4F;
    func_80044588(0x4F);
    func_80015FC8(3, 0);
    func_80016044();
    e->nivel = 0x50;
    func_80044588(0x50);
    func_80015FC8(3, 0);
    func_80016044();
    e->nivel = 2;
    func_80015FC8(2, 0);
}

void func_800161A8(void)
{
    EstadoPrincipal* e;

    func_800160A8();
    e = ESTADO_PRINCIPAL;
    e->nivel = 0x6D;
    e->f4F = 0;
    func_8004443C(0x6D);
    func_80016044();
    func_80015FC8(0x1E, 0x140);
    e->nivel = 0x6E;
    func_80044588(0x6E);
    func_80016044();
    func_80015FC8(0x14, 0x140);
}

/*
 * Actualiza un cuadro: contadores de tiempo, lectura de mandos, logica y ordenacion de primitivas.
 * La ordenacion corre con la pila en el bloque de memoria rapida (scratchpad): la pila se guarda en
 * 0x1F8003FC, se cambia a esa zona y se restaura al terminar. Las dos secuencias son ensamblador
 * porque el compilador no tiene forma de mover el puntero de pila.
 *
 */
void func_80016218(void)
{
    D_80069534 += 1;
    D_80069694 = D_80069510 - D_80069638;
    D_80069638 = D_80069510;
    func_8004048C();
    func_800353B0(D_80069518);
    __asm__ volatile ("move $8, %0\n\t"
                      "sw $29, 0($8)\n\t"
                      "addiu $8, $8, -4\n\t"
                      "move $29, $8"
                      : : "r"(0x1F8003FC) : "$8");
    GsSetRefView2L(&D_8006D928);
    GsClearOt(0, 0, &D_8006AE20[D_8006967C]);
    GsClearOt(0, 0, &D_8006AE60[D_8006967C]);
    GsClearOt(0, 0, &D_8006AEA0[D_8006967C]);
    func_80037048(D_80069630);
    D_8006AD40[D_8006967C] = D_80076188;
    func_800399C8(D_80069508);
    func_8003B5AC(D_80069630);
    func_8003A5C8(D_8006AD80);
    func_80045150(D_800694B8);
    func_80037184(D_80069630);
    if (D_800694D8 != 0) {
        func_8001020C(0x1C40);
        func_8003B5AC(D_800694D8);
        func_8001020C(0x1840);
    }
    __asm__ volatile ("addiu $29, $29, 4\n\t"
                      "lw $29, 0($29)\n\t"
                      "nop");
}

void func_800163E4(void)
{
    func_8003E3C0();
    func_8003F3F0(D_8006967C);
}

#ifdef NON_MATCHING
/*
 * Arranque y bucle principal. Tras iniciar el hardware y cargar el primer contenido, cada vuelta
 * del bucle sincroniza los tres buffers, actualiza el cuadro, atiende la tarjeta de memoria, la
 * pausa y la maquina de estados D_80069662 (el estado 0x16 en adelante recarga el contenido).
 * Con el mando ocioso unos 900 cuadros entra en el ciclo de demostracion.
 *
 * Pendiente (1135, 11 variantes): el flujo y los tipos coinciden (pausa y demostracion son s16, el
 * contador de cuadros D_80069676 es volatile u16); difieren el reparto de registros salvados de las
 * constantes 2 y 3 y de la tabla de tiempos D_8006CF68, y la base `lui` del estado se hoistea antes
 * que en el original.
 *
 * NON_MATCHING: sin cerrar. Puntuacion 1135 (el archivo se compila con g = 8; 15140 con -G0).
 */
s32 main(void)
{
    EstadoPrincipal* e0;
    EstadoPrincipal* e;
    s16 contador;
    s16 ocioso;
    s16 demo;
    s16 pausa;
    u8* regs;

    func_80044D44();
    func_80044E58();
    func_80015EC0();
    e0 = ESTADO_PRINCIPAL;
    e0->nivel = 2;
    func_80040EB4();
    func_80016118();
    D_800694F0 = e0->nivel;
    func_8004443C(e0->nivel);
    while (func_800415A0((s16)ESTADO_PRINCIPAL->nivel, (void*)0x80077000) != 0) {
    }
    e = ESTADO_PRINCIPAL;
    pausa = 0;
    ocioso = 0;
    demo = 0x4A;
    regs = D_8006AA70;
    func_80019364((void*)D_800694FC);
    DrawSyncCallback(0);
    VSyncCallback(func_80040AF0);
    srand(1);
    D_80069534 = 0;
    D_80069694 = 0;
    D_80069638 = 0;
    D_80069510 = 1;
    D_800695DC = 0;
    D_8006967C += 1;
    func_800353B0(D_80069518);
    SetRCnt(0xF2000000 | 2, 0xFFFF, 0x2000);
    StartRCnt(0xF2000000 | 2);
    func_8003DF84();
    func_8003AA50(1, 0x100);
    for (;;) {
        if (D_8006967C == 3) {
            D_8006967C = 0;
        }
        do {
            func_8003E9E8();
        } while ((s16)D_80069676 == 2);
        D_8006CF68[D_8006967C] = VSync(1);
        func_80016218();
        D_8006CF68[D_8006967C] = VSync(1) - D_8006CF68[D_8006967C];
        if (D_80069662 == 0 && regs[3] != 0) {
            func_800156F4(1);
        } else {
            func_80015E94();
        }
        if (pausa != 0) {
            if (!(e->botones_a & 0x800)) {
                pausa = 0;
            }
        } else if (D_8006AA70[0] == 0) {
            if (regs[0xC] == 0 && D_80069662 == 0) {
                if ((e->botones_a & 0x800) && D_8006966A == 0 && (!(D_8006D9A8 & 0x300) || (D_8006D9A8 & 1)) && e->f76 == 0) {
                    contador = 0;
                    func_80037FB8(D_80069508);
                    func_80037FE8(D_80069508);
                    regs[0xC] = 1;
                    regs[0xD] = 0;
                    regs[0xE] = 1;
                    regs[0xF] = 0;
                    regs[0x10] = 1;
                    D_8006965A = 0;
                    D_80069659 = 0;
                    func_80040240();
                    do {
                        D_8006967C += 1;
                        D_80069676 += 1;
                        if (D_8006967C == 3) {
                            D_8006967C = 0;
                        }
                        do {
                        } while ((s16)D_80069676 == 2);
                        func_80016218();
                        func_800163E4();
                        contador++;
                    } while (contador < 3);
                    D_8006965A = 0;
                    D_80069659 = 0;
                    func_80040240();
                    func_8003E88C();
                    func_8003FC88();
                    if (e->botones != 0) {
                        for (;;) {
                            func_8004048C();
                            if (e->botones == 0) {
                                break;
                            }
                        }
                    }
                }
            } else if (regs[0xC] == 2) {
                regs[0xC] = 0;
                D_8006963C = 0;
                D_80069595 = 0;
                D_800695A0 = 0;
                pausa = 1;
                func_8003E948();
                func_8003FD60();
                D_80069628 = pausa;
                func_80037FB8(D_80069508);
            }
        }
        if (e->nivel == 0) {
            ocioso++;
            if (e->fCD & 2) {
                ocioso = 0;
            }
            if (ocioso >= 0x385) {
                ocioso = 0;
                D_80069662 = 1;
                e->nivel = demo;
                e->f4F = 1;
            }
        }
        if (D_80069662 != 0) {
            if (D_80069662 == 1) {
                func_8003E094();
                func_8003AA7C(2, 0x100);
                D_800694E0 = 0;
                D_800694E1 = 0;
                D_800694E8 = 0;
                func_80037FB8(D_80069508);
            } else if (D_80069662 >= 0x16 && e->nivel >= 0) {
                func_8003E068();
                if (e->nivel == 0) {
                    ocioso = 0;
                    func_80015F38();
                }
                D_8006965A = 0;
                D_80069659 = 0;
                func_80040240();
                D_800694F0 = e->nivel;
                func_8004443C(e->nivel);
                func_800445E8(e->nivel);
                D_8006965A = 0;
                D_80069659 = 0;
                func_80040240();
                if (e->f4F == 0) {
                    srand((BugsRand() + VSync(1)) % 300);
                } else {
                    func_80015F38();
                    if (demo == 0x4A) {
                        demo = 0x4B;
                        e->fF8 = 0x83;
                        e->fF6 = 0x5D;
                    } else if (demo == 0x4B) {
                        demo = 0x4C;
                        e->fF8 = 0x85;
                        e->fF6 = 0x5F;
                    } else if (demo == 0x4C) {
                        demo = 0x4D;
                        e->fF8 = 0x8C;
                        e->fF6 = 0x66;
                    } else if (demo == 0x4D) {
                        demo = 0x4A;
                        e->fF8 = 0xEA;
                        e->fF6 = 0xEB;
                    }
                    e->f4F = 1;
                    srand(1);
                }
                D_80069534 = 0;
                D_80069694 = 0;
                D_80069638 = 0;
                D_80069510 = 1;
                D_800695DC = 0;
                D_8006967C += 1;
                func_800353B0(D_80069518);
                func_8003E3C0();
                func_8003AA50(1, 0x100);
                continue;
            }
            D_80069662 += 1;
        }
        if (e->f4F != 0 && (e->botones & 0x100)) {
            e->botones_a = *D_800695B0--;
            e->botones_e = *D_800695B0--;
            e->botones_c = *D_800695B0--;
            e->botones = *D_800695B0--;
            if (D_80069662 == 0) {
                D_80069662 = 1;
                e->nivel = 0;
            }
        }
        if (regs[0xC] == 0) {
            func_800163E4();
        }
        D_8006967C += 1;
        D_80069676 += 1;
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/arranque_y_bucle_principal_2", main);
#endif

#include "eventos.h"

/*
 * Rutinas del interprete de eventos. Las tablas de saltos de condiciones (D_8005E3F0) y de
 * acciones (D_8005E560) apuntan a las rutinas hoja de este archivo; las dos entradas que las
 * recorren (func_8002F9F8 y func_80030ECC) son ensamblador manuscrito.
 */

#define RA ESTADO->r

/* Vector de tres componentes del que solo se rellenan x y z antes de llamar a ratan2. */
typedef struct Vec3 {
    s32 x;
    s32 y;
    s32 z;
} Vec3;

/* Entrada de 20 bytes de la tabla de seguimiento D_8006B378 (24 entradas). */
typedef struct Entrada {
    u16 flags;
    u8 pad02[2];
    Objeto* objeto;
    u16* valor;
    u8 pad0C[8];
} Entrada;

/*
 * Escalar de un byte declarado como estructura: el planificador del compilador solo mantiene el
 * orden entre estas escrituras y las lecturas por puntero del registro de accion si ambos
 * accesos son de campos de estructura.
 */
typedef struct Byte {
    u8 v;
} Byte;

extern Objeto* D_80069518;
extern s32* D_80069640;
extern s32 D_800693B4;
extern s32 D_800693C0;
extern s16 D_800693F6;
extern u16 D_8001000A;
extern u8 D_800100E6;
extern u8 D_80010041;
extern u8 D_800694E0;
extern u8 D_800694E1;
extern u8 D_800694E8;
extern u8 D_800694F2;
extern s32 D_800694F8;
extern s32 D_80069554;
extern s32 D_80069560;
extern u8 D_80069586;
extern u8 D_80069594;
extern s32 D_8006960C;
extern s32 D_80069618;
extern s32 D_8006961C;
extern s32 D_80069624;
extern u8 D_80069659;
extern Byte D_8006965A;
extern Byte D_8006965B;
extern u8 D_8006965E;
extern s16 D_80069662;
extern s8 D_8006966A;
extern u8 D_80069674;
extern s16 D_8006967C;
extern s32 D_80069690;
extern s32 D_80069694;
extern u16 D_800695D0;
extern u16 D_8006B658[];
extern u8 D_8006B558[];
extern Entrada D_8006B378[];
extern u32 D_8006D064;
extern u16 D_8006D9A8[5];

extern void func_8001CFCC(void* a0);
extern void func_8001D588(s32 a0, void* a1);
extern s32 func_80032874(void);
extern void func_8003AA50(s32 a0, s32 a1);
extern void func_8003AA7C(s32 a0, s32 a1);
extern void func_8003DFE4(void);
extern void func_8003E094(void);
extern void func_8003E3C0(void);
extern void func_8003E88C(void);
extern s32 func_8003F06C(void* a0, s32 a1, s32 a2, s32 a3);
extern s32 func_80044940(void* a0);
extern s32 func_80045C4C(s32 a0, s32 a1, s32 a2);
extern s32 ratan2(s32 a0, s32 a1);

/* Acceso a la base de $gp: los datos pequenos del original se direccionan por registro. */
register u8* base_gp __asm__("$28");


INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002F9F8);

s32 func_8002FA30(void) { return 1; }

/* Compara un byte de un registro con la entrada de la tabla D_8006AA70 que indica otro byte. */
s32 func_8002FA38(void* a0, u8* a1)
{
    return D_8006AA70[a1[2]] == a1[1];
}

s32 func_8002FA60(void* a0, u8* a1) { return D_8006AA70[a1[2]] == D_8006AA70[a1[1]]; }

s32 func_8002FA90(void* a0, u8* a1) { return D_8006AA70[a1[2]] != a1[1]; }

s32 func_8002FAB8(void* a0, u8* a1) { return D_8006AA70[a1[2]] != D_8006AA70[a1[1]]; }

s32 func_8002FAE8(void* a0, u8* a1) { return D_8006AA70[a1[2]] == D_8006AA70[a1[1]]; }

/* Igual que func_8002FA38 pero con la comparacion 'mayor que'. */
s32 func_8002FB18(void* a0, u8* a1)
{
    return D_8006AA70[a1[2]] > a1[1];
}

s32 func_8002FB38(void* a0, u8* a1) { return (s8)D_8006AA70[a1[2]] > (s8)a1[1]; }

s32 func_8002FB58(void* a0, u8* a1) { return D_8006AA70[a1[2]] > D_8006AA70[a1[1]]; }

s32 func_8002FB80(void* a0, u8* a1) { return (s8)D_8006AA70[a1[2]] > (s8)D_8006AA70[a1[1]]; }

s32 func_8002FBA8(void* a0, u8* a1) { return D_8006AA70[a1[2]] >= a1[1]; }

s32 func_8002FBD0(void* a0, u8* a1) { return D_8006AA70[a1[2]] < a1[1]; }

s32 func_8002FBF0(void* a0, u8* a1) { return (s8)D_8006AA70[a1[2]] < (s8)a1[1]; }

s32 func_8002FC10(void* a0, u8* a1) { return D_8006AA70[a1[2]] < D_8006AA70[a1[1]]; }

s32 func_8002FC38(void* a0, u8* a1) { return (s8)D_8006AA70[a1[2]] < (s8)D_8006AA70[a1[1]]; }

s32 func_8002FC60(void* a0, u8* a1) { return D_8006AA70[a1[2]] <= a1[1]; }

s32 func_8002FC88(void* a0, u8* a1) { return (D_8006AA70[a1[2]] & a1[1]) != 0; }

s32 func_8002FCB0(void* a0, u8* a1) { return (D_8006AA70[a1[2]] & a1[1]) == 0; }

s32 func_8002FCD8(void* a0, u8* a1) { return (D_8006AA70[a1[2]] & a1[1]) == 0; }

s32 func_8002FD00(void* a0, u8* a1) { return RA[a1[2]] == a1[1]; }

s32 func_8002FD24(void* a0, u8* a1) { return RA[a1[2]] == RA[a1[1]]; }

s32 func_8002FD50(void* a0, u8* a1) { return RA[a1[2]] != a1[1]; }

s32 func_8002FD74(void* a0, u8* a1) { return RA[a1[2]] != RA[a1[1]]; }

s32 func_8002FDA0(void* a0, u8* a1) { return RA[a1[2]] == RA[a1[1]]; }

s32 func_8002FDCC(void* a0, u8* a1) { return RA[a1[2]] > a1[1]; }

s32 func_8002FDE8(void* a0, u8* a1) { return (s8)RA[a1[2]] > (s8)a1[1]; }

s32 func_8002FE04(void* a0, u8* a1) { return RA[a1[2]] > RA[a1[1]]; }

s32 func_8002FE28(void* a0, u8* a1) { return RA[a1[2]] >= a1[1]; }

s32 func_8002FE4C(void* a0, u8* a1) { return RA[a1[2]] < a1[1]; }

s32 func_8002FE68(void* a0, u8* a1) { return (s8)RA[a1[2]] < (s8)a1[1]; }

s32 func_8002FE84(void* a0, u8* a1) { return RA[a1[2]] < RA[a1[1]]; }

s32 func_8002FEA8(void* a0, u8* a1) { return RA[a1[2]] <= a1[1]; }

s32 func_8002FECC(void* a0, u8* a1) { return (RA[a1[2]] & a1[1]) != 0; }

s32 func_8002FEF0(void* a0, u8* a1) { return (RA[a1[2]] & a1[1]) == 0; }

s32 func_8002FF14(void* a0, u8* a1) { return (RA[a1[2]] & a1[1]) == 0; }

/* El simbolo cubre dos rutinas de 0x20 bytes: esta (flags14 & 0x2000020 == 0) y la de 0x8002FF58 (flags14 & 0x8000 == 0), que necesitan simbolos propios; el C de arriba solo reproduce la primera mitad */
#ifdef NON_MATCHING
s32 func_8002FF38(Objeto* a0, u8* a1) { return (D_80069698->flags14 & 0x2000020) == 0; }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8002FF38);
#endif

s32 func_8002FF78(Objeto* a0, u8* a1) { return (D_80069698->flags14 & 0x2000020) != 0; }

s32 func_8002FF98(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags14 & 0x1000000; return v != 0; }

s32 func_8002FFB8(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags14 & 0x1000000; return v == 0; }

s32 func_8002FFD8(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags14 & 0x10; return v != 0; }

s32 func_8002FFF8(Objeto* a0, u8* a1) { return D_80069698->w17C == a1[1]; }

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030018);

s32 func_8003004C(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags14 & 0x40; return v != 0; }

s32 func_8003006C(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags14 & 0x40; return v == 0; }

s32 func_8003008C(Objeto* a0, u8* a1) { return a0->p6C == 0; }

s32 func_80030098(Objeto* a0, u8* a1) { return a0->p6C != 0; }

s32 func_800300A4(Objeto* a0, u8* a1) { return (s16)D_80069698->w26 == a1[1]; }

s32 func_800300C4(Objeto* a0, u8* a1) { return (s16)D_80069698->w26 != a1[1]; }

#ifdef NON_MATCHING
s32 func_800300E4(Objeto* a0, u8* a1)
{
    Vec3 v;
    s32 ang;
    s32 t;
    v.x = D_80069640[0] - a0->xE4;
    v.z = D_80069640[2] - a0->zEC;
    ang = ratan2(v.x, v.z);
    if (ang < 0) {
        ang += 0x1000;
    }
    t = (s16)(((s16)D_80069698->wDE) % 0x1000);
    if (t < 0) {
        t += 0x1000;
    }
    ang -= t;
    if (ang < 0) {
        ang += 0x1000;
    }
    if (ang > 0x800) {
        ang -= 0x1000;
    }
    if ((u32)(ang + 0x293) < 0x527) {
        return 0;
    }
    if (a1[1] == 1) {
        if (ang > 0) {
            return 0;
        }
    }
    if (a1[1] == 2) {
        if (ang < 0) {
            return 0;
        }
    }
    return 1;
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800300E4);
#endif

#ifdef NON_MATCHING
s32 func_800301E8(Objeto* a0, u8* a1)
{
    Vec3 v;
    s32 ang;
    s32 t;
    v.x = D_80069640[0] - a0->xE4;
    v.z = D_80069640[2] - a0->zEC;
    ang = ratan2(v.x, v.z);
    if (ang < 0) {
        ang += 0x1000;
    }
    t = (s16)(((s16)D_80069698->wDE) % 0x1000);
    if (t < 0) {
        t += 0x1000;
    }
    ang -= t;
    if (ang < 0) {
        ang += 0x1000;
    }
    if (ang > 0x800) {
        ang -= 0x1000;
    }
    if ((u32)(ang + 0x293) < 0x527) {
        if (a1[1] == 1) {
            if (ang > 0) {
                return 0;
            }
        }
        if (a1[1] == 2) {
            if (ang < 0) {
                return 0;
            }
        }
        return 1;
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800301E8);
#endif

#ifdef NON_MATCHING
s32 func_800302F8(Objeto* a0, u8* a1)
{
    Vec3 v;
    s32 ang;
    s32 t;
    v.x = D_80069698->xE4 - a0->xE4;
    v.z = D_80069698->zEC - a0->zEC;
    ang = ratan2(v.x, v.z);
    if (ang < 0) {
        ang += 0x1000;
    }
    t = (s16)(((s16)a0->wDE) % 0x1000);
    if (t < 0) {
        t += 0x1000;
    }
    ang -= t;
    if (ang < 0) {
        ang += 0x1000;
    }
    if (ang > 0x800) {
        ang -= 0x1000;
    }
    if ((u32)(ang + 0x293) < 0x527) {
        if (a1[1] == 1) {
            if (ang > 0) {
                return 0;
            }
        }
        if (a1[1] == 2) {
            if (ang < 0) {
                return 0;
            }
        }
        return 1;
    }
    return 0;
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800302F8);
#endif

#ifdef NON_MATCHING
s32 func_80030404(Objeto* a0, u8* a1)
{
    Vec3 v;
    s32 ang;
    s32 t;
    v.x = D_80069698->xE4 - a0->xE4;
    v.z = D_80069698->zEC - a0->zEC;
    ang = ratan2(v.x, v.z);
    if (ang < 0) {
        ang += 0x1000;
    }
    t = (s16)(((s16)a0->wDE) % 0x1000);
    if (t < 0) {
        t += 0x1000;
    }
    ang -= t;
    if (ang < 0) {
        ang += 0x1000;
    }
    if (ang > 0x800) {
        ang -= 0x1000;
    }
    if ((u32)(ang + 0x293) < 0x527) {
        return 0;
    }
    if (a1[1] == 1) {
        if (ang > 0) {
            return 0;
        }
    }
    if (a1[1] == 2) {
        if (ang < 0) {
            return 0;
        }
    }
    return 1;
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030404);
#endif

s32 func_80030504(Objeto* a0, u8* a1) { u32 v = a1[1] | (a1[2] << 8); return a0->w22 < v; }

s32 func_80030520(Objeto* a0, u8* a1) { u32 v = a1[1] | (a1[2] << 8); return v < a0->w22; }

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003053C);

s32 func_8003055C(Objeto* a0, u8* a1) { u32 v = a1[1] | (a1[2] << 8); return a0->w22 / 30 < v; }

s32 func_80030590(Objeto* a0, u8* a1) { u32 v = a1[1] | (a1[2] << 8); return v < a0->w22 / 30; }

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800305C4);

s32 func_80030620(Objeto* a0, u8* a1) { u32 v = a1[1] | (a1[2] << 8); return a0->w22 / 1800 < v; }

s32 func_80030654(Objeto* a0, u8* a1) { u32 v = a1[1] | (a1[2] << 8); return v < a0->w22 / 1800; }

s32 func_80030688(Objeto* a0, u8* a1) { u32 v = a1[1] | (a1[2] << 8); return a0->w22 / 1800 == v; }

s32 func_800306C0(Objeto* a0, u8* a1) { return D_800693F6 != 0; }

s32 func_800306D0(Objeto* a0, u8* a1) { return D_8006AA70[a1[2]] == a1[1]; }

s32 func_800306F8(Objeto* a0, u8* a1) { return ESTADO->r[a1[2]] == a1[1]; }

s32 func_8003071C(Objeto* a0, u8* a1) { u32 v; v = D_8001000A & 8; return v != 0; }

s32 func_80030734(Objeto* a0, u8* a1) { u32 v; v = D_8001000A & 8; return v == 0; }

s32 func_8003074C(Objeto* a0, u8* a1)
{
    s32 a;
    a = (s16)((s16)a0->wDE % 0x1000) >> 4;
    if (a < 0) {
        a += 0x100;
    }
    if (a1[1] < (u32)a && (u32)a < a1[2]) {
        return 1;
    }
    return 0;
}

s32 func_800307B4(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags18 & 2; return v != 0; }

s32 func_800307D4(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags18 & 4; return v != 0; }

s32 func_800307F4(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags18 & 2; return v == 0; }

s32 func_80030814(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags18 & 4; return v == 0; }

s32 func_80030834(Objeto* a0, u8* a1)
{
    s32 v;
    v = func_80045C4C(*(u16*)(a1 + 4), 0, 0);
    *(s32*)(base_gp + 0xC0) = v;
    return (a1[1] & v) != 0;
}

s32 func_80030874(Objeto* a0, u8* a1) { return (a1[1] & *(s32*)(base_gp + 0xC0)) != 0; }

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003088C);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030924);

s32 func_80030990(Objeto* a0, u8* a1) { return a1[1] == a0->s1E; }

s32 func_800309A8(Objeto* a0, u8* a1) { return a0->s1E > a1[1]; }

s32 func_800309B8(Objeto* a0, u8* a1) { return a0->s1E < a1[1]; }

s32 func_800309C8(Objeto* a0, u8* a1) { return (s16)a0->w26 == a1[1]; }

s32 func_800309E0(Objeto* a0, u8* a1) { return (s16)a0->w26 != a1[1]; }

s32 func_800309F8(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags14 & 0x10; return v != 0; }

s32 func_80030A18(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags14 & 0x10; return v == 0; }

s32 func_80030A38(Objeto* a0, u8* a1)
{
    u32 m;
    u32 f;
    m = a1[1];
    f = D_80069698->flags14;
    if ((m & 1) && (f & 1)) return 1;
    if ((m & 2) && (f & 2)) return 1;
    if ((m & 4) && (f & 0x10)) return 1;
    if ((m & 8) && (f & 8)) return 1;
    if ((m & 0x10) && (f & 0x200)) return 1;
    if ((m & 0x20) && (f & 0x400)) return 1;
    if ((m & 0x40) && (f & 0x4000)) return 1;
    if ((m & 0x80) && (f & 0x1000000)) return 1;
    m = a1[2];
    f = D_80069698->flags18;
    if ((m & 1) && (f & 0x2000000)) return 1;
    if ((m & 2) && (f & 0x10000000)) return 1;
    if ((m & 4) && (s32)f < 0) return 1;
    if ((m & 8) && (f & 2)) return 1;
    if ((m & 0x10) && (f & 4)) return 1;
    return 0;
}

s32 func_80030B78(Objeto* a0, u8* a1)
{
    u32 m;
    u32 f;
    m = a1[1];
    f = D_80069698->flags14;
    if ((m & 1) && (f & 1)) return 0;
    if ((m & 2) && (f & 2)) return 0;
    if ((m & 4) && (f & 0x10)) return 0;
    if ((m & 8) && (f & 8)) return 0;
    if ((m & 0x10) && (f & 0x200)) return 0;
    if ((m & 0x20) && (f & 0x400)) return 0;
    if ((m & 0x40) && (f & 0x4000)) return 0;
    if ((m & 0x80) && (f & 0x1000000)) return 0;
    m = a1[2];
    f = D_80069698->flags18;
    if ((m & 1) && (f & 0x2000000)) return 0;
    if ((m & 2) && (f & 0x10000000)) return 0;
    if ((m & 4) && (s32)f < 0) return 0;
    if ((m & 8) && (f & 2)) return 0;
    if ((m & 0x10) && (f & 4)) return 0;
    return 1;
}

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030CB8);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030CE0);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030D08);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030D34);

/*
 * Comprueba que la altura (Y >> 8) del objeto controlado D_80069698 este dentro del rango
 * [min, max] de la entrada. Las dos comparaciones con return explicito de 1 y 0 producen las
 * dos ramas con el valor en el hueco de retardo, como el original.
 */
typedef struct Rango {
    s8 pad0;
    s8 min;
    s8 max;
} Rango;

s32 func_80030D60(void* a0, Rango* a1)
{
    s32 v;

    v = D_80069698->yE8 >> 8;
    if (v >= a1->min && v <= a1->max) {
        return 1;
    }
    return 0;
}

s32 func_80030DA4(Objeto* a0, u8* a1)
{
    s32 i;
    Entrada* e;
    u32 v;
    e = D_8006B378;
    v = a1[1];
    for (i = 0; i < 24; i++) {
        if ((e->flags & 0x8000) && (e->flags & 5) && *e->valor == v) {
            return a1[2] == 1;
        }
        e++;
    }
    return a1[2] != 1;
}

s32 func_80030E20(Objeto* a0, u8* a1)
{
    s32 i;
    Entrada* e;
    u32 v;
    e = D_8006B378;
    v = a1[1];
    for (i = 0; i < 24; i++) {
        if ((e->flags & 0x8000) && (e->flags & 5) && *e->valor == v && e->objeto == a0) {
            return a1[2] == 1;
        }
        e++;
    }
    return a1[2] != 1;
}

s32 func_80030EB4(Objeto* a0, u8* a1) { return D_80069698->p6C != 0; }

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80030ECC);

void func_80030F04(void) {}

void func_80030F0C(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6]++; }

void func_80030F30(Objeto* a0, Accion* a1)
{
    if (a1->w6 == 7) {
        func_8002F990(ACC_W4(a1), 1);
    } else {
        RA[a1->w6]++;
    }
}

void func_80030F88(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] = a1->b4; }

void func_80030FA4(Objeto* a0, Accion* a1) { RA[a1->w6] = a1->b4; }

void func_80030FBC(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6]--; }

void func_80030FE0(Objeto* a0, Accion* a1)
{
    if (a1->w6 == 7) {
        func_8002F990(ACC_W4(a1), 2);
    } else {
        RA[a1->w6]--;
    }
}

void func_80031038(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] = 0; }

void func_80031050(Objeto* a0, Accion* a1) { RA[a1->w6] = 0; }

void func_80031064(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] = -D_8006AA70[a1->w6]; }

void func_80031088(Objeto* a0, Accion* a1) { RA[a1->w6] = -RA[a1->w6]; }

void func_800310A8(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] |= a1->b4; }

void func_800310D0(Objeto* a0, Accion* a1) { RA[a1->w6] |= a1->b4; }

void func_800310F4(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] &= a1->b4; }

void func_8003111C(Objeto* a0, Accion* a1) { RA[a1->w6] &= a1->b4; }

void func_80031140(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] = D_8006AA70[ACC_W4(a1)]; }

void func_80031164(Objeto* a0, Accion* a1) { RA[a1->w6] = RA[ACC_W4(a1)]; }

void func_80031184(Objeto* a0, Accion* a1) { RA[a1->w6] = D_8006AA70[ACC_W4(a1)]; }

void func_800311AC(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] = RA[ACC_W4(a1)]; }

void func_800311D4(Objeto* a0, Accion* a1)
{
    D_8006AA70[a1->w6]++;
    D_8006AA70[ACC_W4(a1)]++;
}

void func_80031214(Objeto* a0, Accion* a1)
{
    if (a1->w6 == 7) {
        func_8002F990(ACC_W4(a1), 1);
    } else {
        RA[a1->w6]++;
    }
    if (ACC_W4(a1) == 7) {
        func_8002F990(ACC_W4(a1), 1);
    } else {
        RA[ACC_W4(a1)]++;
    }
}

void func_800312B0(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] = func_80032874() % ACC_W4(a1); }

void func_800312F8(Objeto* a0, Accion* a1) { RA[a1->w6] = func_80032874() % ACC_W4(a1); }

void func_8003133C(Objeto* a0, Accion* a1) { a0->flags14 |= 0x100; }

void func_80031350(Objeto* a0, Accion* a1)
{
    D_8006AA70[a1->w6]++;
    a0->flags14 |= 0x100;
}

void func_80031384(Objeto* a0, Accion* a1)
{
    D_8006AA70[a1->w6]++;
    D_8006AA70[ACC_W4(a1)]++;
    a0->flags14 |= 0x100;
}

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800313D4);

void func_8003141C(Objeto* a0, Accion* a1) { a0->w22 = 0; }

void func_80031424(Objeto* a0, Accion* a1)
{
    u8* p;
    p = &D_8006AA70[a1->w6];
    if (*p != 0 && (u16)(a0->w22 / 30) >= 2) {
        *p = *p - 1;
        a0->w22 = 0;
    }
}

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003147C);

void func_80031500(Objeto* a0, Accion* a1) { a0->flags14 = (a0->flags14 & 0xFFBFFFFF) | 0x200000; }

void func_80031520(Objeto* a0, Accion* a1) { a0->flags14 = (a0->flags14 & 0xFFDFFFFF) | 0x400000; }

void func_80031540(Objeto* a0, Accion* a1) { a0->w3C &= 0xFFBF; }

void func_80031554(Objeto* a0)
{
    if (a0->p6C != 0) {
        a0->p6C->flags14 &= ~0x814;
        a0->p6C->flags14 |= 0x1000;
        a0->p6C->iC4 = 0;
        a0->p6C->pC0 = (Objeto*)((u8*)a0->p6C + 0xCC);
        a0->p6C->w26 = a0->w26;
        a0->p6C->wDC = a0->wDC;
        a0->p6C->wDE = a0->wDE;
        a0->p6C->wE0 = a0->wE0;
        a0->p6C->p70 = 0;
        func_8001CFCC((u8*)a0->p6C + 0x7C);
        a0->p6C = 0;
    }
}

#ifdef NON_MATCHING
void func_80031624(Objeto* a0, Accion* a1) { func_8003F06C(a0, ACC_W4(a1), 1, D_8006967C); }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031624);
#endif

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031650);

void func_80031694(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] += a1->b4; }

void func_800316BC(Objeto* a0, Accion* a1)
{
    if (a1->w6 == 7) {
        func_8002F990(ACC_W4(a1), 0);
    } else {
        RA[a1->w6] += a1->b4;
    }
}

void func_80031714(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] -= a1->b4; }

void func_8003173C(Objeto* a0, Accion* a1)
{
    if (a1->w6 == 7) {
        func_8002F990(ACC_W4(a1), 3);
    } else {
        RA[a1->w6] -= a1->b4;
    }
}

#ifdef NON_MATCHING
void func_80031794(Objeto* a0, Accion* a1)
{
    Objeto* p;
    p = a0->pC0;
    *(u16*)((u8*)p + 0x12) += (u32)(((ACC_W4(a1) << 4) + a1->w6) * D_80069694 * ESTADO->s12) >> 7;
    func_8001CFCC((u8*)a0 + 0x7C);
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031794);
#endif

#ifdef NON_MATCHING
void func_800317FC(Objeto* a0, Accion* a1)
{
    Objeto* p;
    p = a0->pC0;
    *(u16*)((u8*)p + 0x12) += (u32)((s8)D_8006AA70[a1->w6] * D_80069694 * ESTADO->s12) >> 7;
    func_8001CFCC((u8*)a0 + 0x7C);
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800317FC);
#endif

void func_8003186C(Objeto* a0, Accion* a1)
{
    Objeto* p;
    p = a0->pC0;
    *(u16*)((u8*)p + 0x12) += (ACC_W4(a1) << 4) + a1->w6;
    func_8001CFCC((u8*)a0 + 0x7C);
}

void func_800318AC(Objeto* a0, Accion* a1)
{
    Objeto* p;
    s8 v;
    v = D_8006AA70[a1->w6];
    p = a0->pC0;
    *(u16*)((u8*)p + 0x12) += v;
    func_8001CFCC((u8*)a0 + 0x7C);
}

#ifdef NON_MATCHING
void func_800318F8(Objeto* a0, Accion* a1) { D_800693F6 = ACC_W4(a1); }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800318F8);
#endif

#ifdef NON_MATCHING
void func_8003190C(Objeto* a0, Accion* a1) { D_80069698->flags14 |= 0x80000000; }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003190C);
#endif

#ifdef NON_MATCHING
void func_8003192C(Objeto* a0, Accion* a1)
{
    ESTADO->modo = ESTADO->r[0xE];
    *(u16*)&D_80069662 = 1;
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003192C);
#endif

#ifdef NON_MATCHING
void func_80031948(Objeto* a0, Accion* a1) { D_80069698->wDE = ACC_W4(a1) << 4; }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031948);
#endif

#ifdef NON_MATCHING
void func_80031960(Objeto* a0, Accion* a1) { D_80069698->w28 = ACC_W4(a1); }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031960);
#endif

void func_80031974(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] = a0->s1E; }

void func_80031990(Objeto* a0, Accion* a1) { a0->s1E = D_8006AA70[a1->w6]; }

#ifdef NON_MATCHING
void func_800319AC(Objeto* a0, Accion* a1) { D_80069698->flags18 |= 1; }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800319AC);
#endif

void func_800319CC(Objeto* a0, Accion* a1)
{
    if (RA[1] != RA[2]) {
        RA[1]++;
    } else {
        RA[a1->w6]++;
    }
}

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031A0C);

#ifdef NON_MATCHING
void func_80031A34(Objeto* a0, Accion* a1)
{
    Objeto* o;
    if (ACC_W4(a1) == 0xFF) {
        for (o = D_80069518; o != 0; o = o->siguiente) {
            if (o->w2C == 0x20) {
                o->flags14 |= 0x100;
            }
        }
    } else {
        for (o = D_80069518; o != 0; o = o->siguiente) {
            if (o->w1C == ACC_W4(a1)) {
                break;
            }
        }
        if (o != 0) {
            o->flags14 |= 0x100;
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031A34);
#endif

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031AE4);

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031B1C);

void func_80031B50(Objeto* a0, Accion* a1) { a0->flags15C |= 0x10; }

void func_80031B64(Objeto* a0, Accion* a1) { a0->flags15C &= ~0x10; }

#ifdef NON_MATCHING
void func_80031B78(Objeto* a0, Accion* a1)
{
    u16 v;
    v = *(u16*)&a0->yE8;
    D_800693C0 = 0;
    D_800693B4 = 0;
    a0->w192 = 0;
    a0->w196 = v;
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031B78);
#endif

#ifdef NON_MATCHING
void func_80031B98(Objeto* a0, Accion* a1) { D_80069659 = a1->b4; }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031B98);
#endif

#ifdef NON_MATCHING
void func_80031BAC(Objeto* a0, Accion* a1)
{
    u8 v;
    if (a0 != D_80069698 || a0->i158 != 0x25 || (D_800694F2 & 1)) {
        D_8006965A.v = a1->b4;
        v = ((u8*)a1)[6];
        D_8006965E = 0;
        D_8006965B.v = v;
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031BAC);
#endif

void func_80031C10(Objeto* a0, Accion* a1)
{
    if (D_8006D928.s88 == 0) {
        D_8006D928.s8A = 0;
    }
    D_8006D928.s86 = ACC_W4(a1) * 11;
    D_8006D928.s88 = a1->w6;
}

void func_80031C54(Objeto* a0, Accion* a1)
{
    s16 n;
    u32 bits;
    n = ACC_W4(a1);
    bits = RA[a1->w6];
    if (n > 0) {
        do {
            if ((bits & 1) == 0) {
                func_8002F990(0, 1);
            }
            n--;
            bits >>= 1;
        } while (n > 0);
    }
}

void func_80031CC4(void) {}

void func_80031CCC(void) {}

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031CD4);

void func_80031D1C(Objeto* a0, Accion* a1) { a0->w3C |= 0x40; }

void func_80031D30(void) {}

#ifdef NON_MATCHING
void func_80031D38(Objeto* a0, Accion* a1)
{
    D_8006965B.v = 0;
    D_8006965A.v = a1->b4;
    D_8006965E = ((u8*)a1)[6];
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031D38);
#endif

#ifdef NON_MATCHING
void func_80031D60(Objeto* a0, Accion* a1)
{
    s32 v[3];
    s32 d;
    v[0] = a0->xE4 - D_8006D928.x;
    v[1] = a0->yE8 - D_8006D928.y;
    v[2] = a0->zEC - D_8006D928.z;
    d = func_80044940(v);
    if (d < 0x800) {
        D_8006965A.v = a1->b4;
        d = (a1->w6 * d) / 2048;
        if (d <= 0) {
            D_8006965B.v = 0;
        } else {
            D_8006965B.v = d;
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031D60);
#endif

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031E24);

#ifdef NON_MATCHING
void func_80031EF8(Objeto* a0, Accion* a1)
{
    switch (a1->w6) {
    case 0:
        D_800694E8 = a1->b4;
        break;
    case 1:
        D_800694E1 = a1->b4;
        break;
    case 2:
        D_800694E0 = a1->b4;
        break;
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031EF8);
#endif

void func_80031F70(Objeto* a0, Accion* a1)
{
    if (ACC_W4(a1) == 0) {
        func_8003AA50(1, 0x100);
    } else if (ACC_W4(a1) == 1) {
        func_8003AA7C(2, 0x100);
    }
}

void func_80031FBC(Objeto* a0, Accion* a1) { func_8003AA50(0x41, 0x400); }

#ifdef NON_MATCHING
void func_80031FE0(Objeto* a0, Accion* a1)
{
    u32 v1;
    u32 f;
    if (D_80069690 > 0) {
        return;
    }
    if (D_80069662 != 0) {
        return;
    }
    if (D_8006966A != 0) {
        return;
    }
    v1 = D_8006D9A8[0];
    if ((v1 & 0x100) || (s32)D_80069698->flags14 < 0) {
        if ((v1 & 0x200) == 0) {
            return;
        }
    }
    D_80069698->w38 = ACC_W4(a1);
    RA[1] -= a1->b4;
    D_80069698->flags14 |= 0x2000000;
    f = a0->flags18;
    a0->flags18 = f | 0x4000;
    D_80069690 = 30;
    if ((s8)RA[1] > 0) {
        return;
    }
    if (D_80069698->flags14 & 0x1000000) {
        return;
    }
    a0->flags18 = f | 0x6000;
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80031FE0);
#endif

void func_800320D8(Objeto* a0, Accion* a1) { D_8006D928.flags80 &= 0xDFFF; }

void func_800320F4(Objeto* a0, Accion* a1) { D_8006D928.flags80 |= 0x2000; }

#ifdef NON_MATCHING
void func_80032110(Objeto* a0, Accion* a1)
{
    D_80069624 = -200;
    D_80069618 = 600;
    D_8006961C = 1100;
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032110);
#endif

#ifdef NON_MATCHING
void func_8003213C(Objeto* a0, Accion* a1) { D_80069624 = ACC_W4(a1) * 100 + a1->w6; }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003213C);
#endif

#ifdef NON_MATCHING
void func_80032170(Objeto* a0, Accion* a1) { D_80069618 = ACC_W4(a1) * 100 + a1->w6; }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032170);
#endif

#ifdef NON_MATCHING
void func_800321A4(Objeto* a0, Accion* a1) { D_8006961C = ACC_W4(a1) * 100 + a1->w6; }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800321A4);
#endif

#ifdef NON_MATCHING
void func_800321D8(Objeto* a0, Accion* a1) { D_8006960C = ((s8*)a1)[4] * 100 + ((s8*)a1)[6]; }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800321D8);
#endif

#ifdef NON_MATCHING
void func_8003220C(Objeto* a0, Accion* a1) { D_8006960C = (ACC_W4(a1) << 8) | a1->w6; }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003220C);
#endif

#ifdef NON_MATCHING
void func_8003222C(Objeto* a0, Accion* a1)
{
    u32 w;
    w = ACC_W4(a1);
    if (w >= 2) {
        u8 t;
        func_8003E094();
        t = a1->b4;
        D_8006AA70[0x17] = 8;
        D_80069586 = t;
    } else if (w == 1) {
        D_80069586 = 0;
        D_80069674 = 0;
        D_800100E6 = D_80069594;
        func_8003DFE4();
        func_8003E88C();
        D_8006AA70[0x17] = w;
    } else if (w == 0) {
        D_80069586 = 0;
        if (D_8006AA70[0x17] != 0) {
            D_8006AA70[0x17] = 0;
            D_80069674 = 0;
            D_800100E6 = D_80069594;
            func_8003E3C0();
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003222C);
#endif

#ifdef NON_MATCHING
void func_80032318(Objeto* a0, Accion* a1) { func_8003F06C(a0, ACC_W4(a1), 2, D_8006967C); }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032318);
#endif

void func_80032344(Objeto* a0, Accion* a1) { D_8006D928.flags80 &= 0x7FFF; }

void func_80032360(Objeto* a0, Accion* a1) { D_8006D928.flags80 |= 0x8000; }

#ifdef NON_MATCHING
void func_8003237C(Objeto* a0) { D_80069560 = (s32)a0; }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003237C);
#endif

void func_8003238C(Objeto* a0, Accion* a1) { a0->flags18 |= 0x400; }

#ifdef NON_MATCHING
void func_800323A0(Objeto* a0, Accion* a1)
{
    Vec3 v;
    s32 ang;
    s32 t;
    v.x = D_80069698->xE4 - a0->xE4;
    v.z = D_80069698->zEC - a0->zEC;
    ang = ratan2(v.x, v.z);
    if (ang < 0) {
        ang += 0x1000;
    }
    t = (s16)(((s16)a0->wDE) % 0x1000);
    if (t < 0) {
        t += 0x1000;
    }
    ang -= t;
    if (ang < 0) {
        ang += 0x1000;
    }
    if (ang > 0x800) {
        ang -= 0x1000;
    }
    D_8006AA70[a1->w6] = ang >> 4;
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800323A0);
#endif

void func_80032474(Objeto* a0, Accion* a1) { D_8006D928.flags80 &= 0xFCFF; }

#ifdef NON_MATCHING
void func_80032490(Objeto* a0, Accion* a1) { D_80069554 = ACC_W4(a1); }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032490);
#endif

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800324A4);

void func_8003264C(Objeto* a0, Accion* a1) { D_8006D928.flags80 |= 1; }

void func_80032668(Objeto* a0, Accion* a1) { D_8006D928.flags80 &= 0xFFFE; }

void func_80032684(Objeto* a0, Accion* a1) { D_8006D9A8[0] = 0x10; }

#ifdef NON_MATCHING
void func_80032694(Objeto* a0, Accion* a1) { D_80069698->flags14 &= ~9; }
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032694);
#endif

void func_800326B4(Objeto* a0, Accion* a1) { D_8006D928.flags80 |= 0x20; }

void func_800326D0(Objeto* a0, Accion* a1) { D_8006D928.flags80 &= 0xFFDF; }

void func_800326EC(Objeto* a0, Accion* a1) { D_8006D928.flags80 |= 4; }

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032708);

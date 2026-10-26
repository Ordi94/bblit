#include "eventos.h"
#include "globales.h"

/*
 * Rutinas del interprete de eventos. Las tablas de saltos de condiciones (D_8005E3F0) y de
 * acciones (D_8005E560) apuntan a las rutinas hoja de este archivo; las dos entradas que las
 * recorren (TestLogicCond y RunLogicAction) son ensamblador manuscrito.
 *
 * Las rutinas bajo NON_MATCHING con cuerpo completo reproducen el original compiladas con -G8:
 * el original escribe las variables globales con la forma simbolica (lui $at) y accede por
 * $gp. Con -G distinto de cero el compilador emite todas las funciones C al final del archivo,
 * despues del ensamblador incluido, de modo que no pueden estar activas mientras queden
 * INCLUDE_ASM por delante en el mismo archivo.
 */

#define RA ESTADO->r

/* Registro de condicion de rango: min y max con signo en los bytes 1 y 2. */
typedef struct Rango {
    s8 pad0;
    s8 min;
    s8 max;
} Rango;

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
 * Vista de un byte como estructura de un campo, solo para func_80031D60. D_8006965A y D_8006965B
 * se declaran u8 en globales.h; con el escalar el planificador sube la lectura por puntero del
 * registro de accion por encima de la escritura al byte y la funcion sale 410 en lugar de 0. El
 * orden del original solo se conserva si ambos accesos son de campos de estructura.
 */
typedef struct Byte {
    u8 v;
} Byte;

extern s32* D_80069640;
extern s32 D_800693B4;
extern s32 D_800693C0;
extern s16 D_800693F6;
/*
 * Variables sueltas del estado principal que el original lee con la forma simbolica (lui al
 * registro de destino): como simbolos externos reproducen esa forma; el acceso por la
 * estructura de ESTADO daria un lui compartido distinto.
 */
extern u16 D_8001000A;
extern u16 D_8001003E;
extern u8 D_800100E6;
extern u8 D_80010041;
extern u8 D_800694F2;
extern s32 D_800694F8;
extern s32 D_80069554;
extern u8 D_80069586;
extern s32 D_8006960C;
extern u8 D_80069674;
extern s32 D_80069690;

/* Dato pequeno: el original lo direcciona como 0xC0($gp). */
s32 D_800693E0;
extern Entrada D_8006B378[];
extern u32 D_8006D064;

/*
 * Registro de 16 bits partido en bytes (indice 7 del banco A). Se declara sin prototipo: el
 * original pasa el operando de 16 bits (lhu) y un prototipo con u8, como la definicion, lo
 * estrecharia con lbu.
 */
extern void func_8002F990();
extern void func_8001CFCC(void* a0);
extern void func_8001D588(s32 a0, void* a1);
extern s32 BugsRand(void);
extern void func_8003AA50(s32 a0, s32 a1);
extern void func_8003AA7C(s32 a0, s32 a1);
extern void func_8003DFE4(void);
extern void func_8003E094(void);
extern void func_8003E3C0(void);
extern void func_8003E88C(void);
extern s32 func_8003F06C(void* a0, s32 a1, s32 a2, s32 a3);
extern s32 func_80044940(void* a0);
extern s32 func_80045C4C(s32 a0, s32 a1, s32 a2);

/* Acceso a la base de $gp: los datos pequenos del original se direccionan por registro. */


INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", TestLogicCond);

s32 CondTrue(void) { return 1; }

/* Compara un byte de un registro con la entrada de la tabla D_8006AA70 que indica otro byte. */
s32 CondCiseq(void* a0, u8* a1)
{
    return D_8006AA70[a1[2]] == a1[1];
}

s32 CondCseq(void* a0, u8* a1) { return D_8006AA70[a1[2]] == D_8006AA70[a1[1]]; }

s32 CondCisne(void* a0, u8* a1) { return D_8006AA70[a1[2]] != a1[1]; }

s32 CondCsne(void* a0, u8* a1) { return D_8006AA70[a1[2]] != D_8006AA70[a1[1]]; }

s32 CondCsseq(void* a0, u8* a1) { return D_8006AA70[a1[2]] == D_8006AA70[a1[1]]; }

/* Igual que CondCiseq pero con la comparacion 'mayor que'. */
s32 CondCisltu(void* a0, u8* a1)
{
    return D_8006AA70[a1[2]] > a1[1];
}

s32 CondCislt(void* a0, u8* a1) { return (s8)D_8006AA70[a1[2]] > (s8)a1[1]; }

s32 CondCsltu(void* a0, u8* a1) { return D_8006AA70[a1[2]] > D_8006AA70[a1[1]]; }

s32 CondCslt(void* a0, u8* a1) { return (s8)D_8006AA70[a1[2]] > (s8)D_8006AA70[a1[1]]; }

s32 CondCisleu(void* a0, u8* a1) { return D_8006AA70[a1[2]] >= a1[1]; }

s32 CondCisgtu(void* a0, u8* a1) { return D_8006AA70[a1[2]] < a1[1]; }

s32 CondCisgt(void* a0, u8* a1) { return (s8)D_8006AA70[a1[2]] < (s8)a1[1]; }

s32 CondCsgtu(void* a0, u8* a1) { return D_8006AA70[a1[2]] < D_8006AA70[a1[1]]; }

s32 CondCsgt(void* a0, u8* a1) { return (s8)D_8006AA70[a1[2]] < (s8)D_8006AA70[a1[1]]; }

s32 CondCisgeu(void* a0, u8* a1) { return D_8006AA70[a1[2]] <= a1[1]; }

s32 CondTismnz(void* a0, u8* a1) { return (D_8006AA70[a1[2]] & a1[1]) != 0; }

s32 CondTisaz(void* a0, u8* a1) { return (D_8006AA70[a1[2]] & a1[1]) == 0; }

s32 CondTismz(void* a0, u8* a1) { return (D_8006AA70[a1[2]] & a1[1]) == 0; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondCigeq(void* a0, u8* a1) { return RA[a1[2]] == a1[1]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondCgeq(void* a0, u8* a1) { return RA[a1[2]] == RA[a1[1]]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondCigne(void* a0, u8* a1) { return RA[a1[2]] != a1[1]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondCgne(void* a0, u8* a1) { return RA[a1[2]] != RA[a1[1]]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondCggeq(void* a0, u8* a1) { return RA[a1[2]] == RA[a1[1]]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondCigltu(void* a0, u8* a1) { return RA[a1[2]] > a1[1]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondCiglt(void* a0, u8* a1) { return (s8)RA[a1[2]] > (s8)a1[1]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondCgltu(void* a0, u8* a1) { return RA[a1[2]] > RA[a1[1]]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondCigleu(void* a0, u8* a1) { return RA[a1[2]] >= a1[1]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondCiggtu(void* a0, u8* a1) { return RA[a1[2]] < a1[1]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondCiggt(void* a0, u8* a1) { return (s8)RA[a1[2]] < (s8)a1[1]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondCggtu(void* a0, u8* a1) { return RA[a1[2]] < RA[a1[1]]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondCiggeu(void* a0, u8* a1) { return RA[a1[2]] <= a1[1]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondTigmnz(void* a0, u8* a1) { return (RA[a1[2]] & a1[1]) != 0; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondTigaz(void* a0, u8* a1) { return (RA[a1[2]] & a1[1]) == 0; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondTigmz(void* a0, u8* a1) { return (RA[a1[2]] & a1[1]) == 0; }

/* Comprueba que ni flags14 & 0x2000000 ni flags14 & 0x20 esten activos en el objeto controlado. */
s32 func_8002FF38(Objeto* a0, u8* a1) { return (D_80069698->flags14 & 0x2000020) == 0; }

/* Comprueba que el bit 15 de flags14 del objeto controlado este apagado. */
s32 func_8002FF58(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags14 & 0x8000; return v == 0; }

s32 func_8002FF78(Objeto* a0, u8* a1) { return (D_80069698->flags14 & 0x2000020) != 0; }

s32 func_8002FF98(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags14 & 0x1000000; return v != 0; }

s32 func_8002FFB8(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags14 & 0x1000000; return v == 0; }

s32 func_8002FFD8(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags14 & 0x10; return v != 0; }

s32 func_8002FFF8(Objeto* a0, u8* a1) { return D_80069698->w17C == a1[1]; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
s32 func_80030018(Objeto* a0, u8* a1)
{
    u16* p;
    p = (u16*)D_80069698->p180; /* lw 0x180(reg): el nodo de la secuencia se lee como tabla de u16 */
    p += D_80069698->w17E;
    return p[3] == a1[1];
}

s32 func_8003004C(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags14 & 0x40; return v != 0; }

s32 func_8003006C(Objeto* a0, u8* a1) { u32 v; v = D_80069698->flags14 & 0x40; return v == 0; }

s32 func_8003008C(Objeto* a0, u8* a1) { return a0->p6C == 0; }

s32 func_80030098(Objeto* a0, u8* a1) { return a0->p6C != 0; }

s32 func_800300A4(Objeto* a0, u8* a1) { return (s16)D_80069698->w26 == a1[1]; }

s32 func_800300C4(Objeto* a0, u8* a1) { return (s16)D_80069698->w26 != a1[1]; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
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

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
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

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
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

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
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

s32 func_80030504(Objeto* a0, u8* a1) { u32 v = a1[1] | (a1[2] << 8); return a0->w22 < v; }

s32 func_80030520(Objeto* a0, u8* a1) { u32 v = a1[1] | (a1[2] << 8); return v < a0->w22; }

s32 func_8003053C(Objeto* a0, u8* a1)
{
    u32 v = a1[1];
    v |= a1[2] << 8;
    return a0->w22 == v;
}

s32 func_8003055C(Objeto* a0, u8* a1) { u32 v = a1[1] | (a1[2] << 8); return a0->w22 / 30 < v; }

s32 func_80030590(Objeto* a0, u8* a1) { u32 v = a1[1] | (a1[2] << 8); return v < a0->w22 / 30; }

s32 func_800305C4(Objeto* a0, u8* a1)
{
    u32 v = a1[1];
    v |= a1[2] << 8;
    if (a0->w22 % 30 == 0 && (u16)(a0->w22 / 30) == v) {
        return 1;
    }
    return 0;
}

s32 func_80030620(Objeto* a0, u8* a1) { u32 v = a1[1] | (a1[2] << 8); return a0->w22 / 1800 < v; }

s32 func_80030654(Objeto* a0, u8* a1) { u32 v = a1[1] | (a1[2] << 8); return v < a0->w22 / 1800; }

s32 func_80030688(Objeto* a0, u8* a1) { u32 v = a1[1] | (a1[2] << 8); return a0->w22 / 1800 == v; }

s32 func_800306C0(Objeto* a0, u8* a1) { return D_800693F6 != 0; }

s32 CondTisxz(Objeto* a0, u8* a1) { return D_8006AA70[a1[2]] == a1[1]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 CondTigxz(Objeto* a0, u8* a1) { return ESTADO->r[a1[2]] == a1[1]; }

s32 CondTbdact(Objeto* a0, u8* a1) { u32 v; v = D_8001000A & 8; return v != 0; }

s32 CondTbuact(Objeto* a0, u8* a1) { u32 v; v = D_8001000A & 8; return v == 0; }

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
    D_800693E0 = v;
    return (a1[1] & v) != 0;
}

s32 func_80030874(Objeto* a0, u8* a1) { return (a1[1] & D_800693E0) != 0; }

/* Coincide en bytes (el diff marca 30 por direccion absoluta); el archivo se compila con -G8 */
s32 func_8003088C(Objeto* a0, u8* a1)
{
    u32 b;
    b = ESTADO->botones;
    if (RA[0xF] == 0) {
        if (D_8006AA70[0xC] != 0 || RA[0x36] != 0) {
            if (b & 0x800) {
                b |= 0x40;
            }
        }
    }
    if (D_80069586 == 0x2F) {
        if (a0->w22 < 0x4B) {
            b &= ~0x40;
        }
    }
    b = ((b & 0xF000) >> 8) | ((b & 0xF0) >> 4);
    return (a1[1] & b) != 0;
}

/* Coincide en bytes; diff puntua la forma simbolica. */
s32 func_80030924(Objeto* a0, u8* a1)
{
    u32 b;
    b = ESTADO->botones;
    if (RA[0xF] == 0) {
        if (D_8006AA70[0xC] != 0 || RA[0x36] != 0) {
            if (b & 0x800) {
                b |= 0x40;
            }
        }
    }
    b = ((b & 0xF000) >> 8) | ((b & 0xF0) >> 4);
    return (a1[1] & b) == 0;
}

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

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
s32 func_80030CB8(Objeto* a0, u8* a1)
{
    u32 b;
    b = D_80010010;
    b = ((b & 0xF00) >> 4) | (b & 0xF);
    return (a1[1] & b) != 0;
}

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
s32 func_80030CE0(Objeto* a0, u8* a1)
{
    u32 b;
    b = D_80010010;
    b = ((b & 0xF00) >> 4) | (b & 0xF);
    return (a1[1] & b) == 0;
}

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
s32 func_80030D08(Objeto* a0, u8* a1)
{
    u32 b;
    b = D_8001003E;
    b = ((b & 0xF000) >> 8) | ((b & 0xF0) >> 4);
    return (a1[1] & b) != 0;
}

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
s32 func_80030D34(Objeto* a0, u8* a1)
{
    u32 b;
    b = D_8001003E;
    b = ((b & 0xF000) >> 8) | ((b & 0xF0) >> 4);
    return (a1[1] & b) == 0;
}

/* Altura (Y >> 8) del objeto controlado dentro de [min, max]; return explicito de 1 y 0 para el li del hueco de retardo. */
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

INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", RunLogicAction);

void ActionNop(void) {}

void ActionIncs(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6]++; }

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionIncg(Objeto* a0, Accion* a1)
{
    if (a1->w6 == 7) {
        func_8002F990(ACC_W4(a1), 1);
    } else {
        RA[a1->w6]++;
    }
}

void ActionMovsi(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] = a1->b4; }

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionMovgi(Objeto* a0, Accion* a1) { RA[a1->w6] = a1->b4; }

void ActionDecs(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6]--; }

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionDecg(Objeto* a0, Accion* a1)
{
    if (a1->w6 == 7) {
        func_8002F990(ACC_W4(a1), 2);
    } else {
        RA[a1->w6]--;
    }
}

void ActionClrs(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] = 0; }

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionClrg(Objeto* a0, Accion* a1) { RA[a1->w6] = 0; }

void ActionNegs(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] = -D_8006AA70[a1->w6]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionNegg(Objeto* a0, Accion* a1) { RA[a1->w6] = -RA[a1->w6]; }

void ActionOrsi(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] |= a1->b4; }

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionOrgi(Objeto* a0, Accion* a1) { RA[a1->w6] |= a1->b4; }

void ActionAndsi(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] &= a1->b4; }

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionAndgi(Objeto* a0, Accion* a1) { RA[a1->w6] &= a1->b4; }

void ActionMovss(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] = D_8006AA70[ACC_W4(a1)]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionMovgg(Objeto* a0, Accion* a1) { RA[a1->w6] = RA[ACC_W4(a1)]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionMovgs(Objeto* a0, Accion* a1) { RA[a1->w6] = D_8006AA70[ACC_W4(a1)]; }

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionMovsg(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] = RA[ACC_W4(a1)]; }

void ActionIncss(Objeto* a0, Accion* a1)
{
    D_8006AA70[a1->w6]++;
    D_8006AA70[ACC_W4(a1)]++;
}

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionIncgg(Objeto* a0, Accion* a1)
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

void ActionRnds(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] = BugsRand() % ACC_W4(a1); }

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionRndg(Objeto* a0, Accion* a1) { RA[a1->w6] = BugsRand() % ACC_W4(a1); }

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

/*
 * Apila un valor en el banco D_8006B658 (ocho entradas de 16 bits) si queda espacio. El contador es volatile:
 * el original lo lee dos veces, una para la comparacion y otra para el indice, y escribe la entrada antes
 * de guardar el contador incrementado.
 */
void func_800313D4(Objeto* a0, Accion* a1)
{
    u16 i;
    if (D_800695D0 < 8) {
        i = D_800695D0;
        D_8006B658[i] = ACC_W4(a1);
        D_800695D0 = i + 1;
    }
}

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

#ifdef NON_MATCHING
/* Pendiente: puntuacion 190 con la configuracion versionada (g = 8 del archivo). El original deja el objeto controlado en a2 y el enlace p70 en a0 con una copia en v1; GCC los reparte en a0 y a1 sin esa copia. Variantes probadas: 8 (a0 reasignado, locales h y c, copia c = a0 antes y despues, puntero j al objeto controlado). */
void func_8003147C(Objeto* a0, Accion* a1)
{
    Objeto* c;
    D_80069698->wDE = a0->wDE + 0x800;
    D_80069698->w17E = 0;
    D_80069698->w17C = ACC_W4(a1);
    D_80069698->flags14 |= 0x2000000;
    a0 = D_80069698->p70;
    if (a0 != 0) {
        D_80069698->nodo.padre = NULL;
        D_80069698->nodo.transf = (Transformacion*)((u8*)D_80069698 + 0xCC);
        c = a0;
        if (c->p6C == c) {
            c->p6C = 0;
        }
        D_80069698->p70 = 0;
        D_80069698->flags14 &= ~0x14;
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_8003147C);
#endif

void func_80031500(Objeto* a0, Accion* a1) { a0->flags14 = (a0->flags14 & 0xFFBFFFFF) | 0x200000; }

void func_80031520(Objeto* a0, Accion* a1) { a0->flags14 = (a0->flags14 & 0xFFDFFFFF) | 0x400000; }

void func_80031540(Objeto* a0, Accion* a1) { a0->w3C &= 0xFFBF; }

void func_80031554(Objeto* a0)
{
    if (a0->p6C != 0) {
        a0->p6C->flags14 &= ~0x814;
        a0->p6C->flags14 |= 0x1000;
        a0->p6C->nodo.padre = NULL;
        a0->p6C->nodo.transf = (Transformacion*)((u8*)a0->p6C + 0xCC);
        a0->p6C->w26 = a0->w26;
        a0->p6C->wDC = a0->wDC;
        a0->p6C->wDE = a0->wDE;
        a0->p6C->wE0 = a0->wE0;
        a0->p6C->p70 = 0;
        func_8001CFCC((u8*)a0->p6C + 0x7C);
        a0->p6C = 0;
    }
}

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_80031624(Objeto* a0, Accion* a1) { func_8003F06C(a0, ACC_W4(a1), 1, D_8006967C); }

/* Pide a func_8001D588 la pantalla D_80069554 o, si no hay ninguna, la de D_800694F8; la llamada es incondicional. */
void func_80031650(Objeto* a0, Accion* a1)
{
    s32 v;
    D_80010041 = 0;
    v = D_80069554;
    if (v == 0) {
        v = D_800694F8;
    }
    func_8001D588(v, D_8006B558);
}

void ActionAddsi(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] += a1->b4; }

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionAddgi(Objeto* a0, Accion* a1)
{
    if (a1->w6 == 7) {
        func_8002F990(ACC_W4(a1), 0);
    } else {
        RA[a1->w6] += a1->b4;
    }
}

void ActionSubsi(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] -= a1->b4; }

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionSubgi(Objeto* a0, Accion* a1)
{
    if (a1->w6 == 7) {
        func_8002F990(ACC_W4(a1), 3);
    } else {
        RA[a1->w6] -= a1->b4;
    }
}

/* Coincide en bytes (el diff marca 10 por direccion absoluta); el archivo se compila con -G8 */
void func_80031794(Objeto* a0, Accion* a1)
{
    Transformacion* p;
    p = a0->nodo.transf;
    *(u16*)((u8*)p + 0x12) += (u32)(((ACC_W4(a1) << 4) + a1->w6) * D_80069694 * ESTADO->s12) >> 7;
    func_8001CFCC((u8*)a0 + 0x7C);
}

/* Coincide en bytes (el diff marca 10 por direccion absoluta); el archivo se compila con -G8 */
void func_800317FC(Objeto* a0, Accion* a1)
{
    Transformacion* p;
    p = a0->nodo.transf;
    *(u16*)((u8*)p + 0x12) += (u32)((s8)D_8006AA70[a1->w6] * D_80069694 * ESTADO->s12) >> 7;
    func_8001CFCC((u8*)a0 + 0x7C);
}

void func_8003186C(Objeto* a0, Accion* a1)
{
    Transformacion* p;
    p = a0->nodo.transf;
    *(u16*)((u8*)p + 0x12) += (ACC_W4(a1) << 4) + a1->w6;
    func_8001CFCC((u8*)a0 + 0x7C);
}

void func_800318AC(Objeto* a0, Accion* a1)
{
    Transformacion* p;
    s8 v;
    v = D_8006AA70[a1->w6];
    p = a0->nodo.transf;
    *(u16*)((u8*)p + 0x12) += v;
    func_8001CFCC((u8*)a0 + 0x7C);
}

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_800318F8(Objeto* a0, Accion* a1) { D_800693F6 = ACC_W4(a1); }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_8003190C(Objeto* a0, Accion* a1) { D_80069698->flags14 |= 0x80000000; }

/* Coincide en bytes (el diff marca 15 por direccion absoluta); el archivo se compila con -G8 */
void func_8003192C(Objeto* a0, Accion* a1)
{
    ESTADO->modo = ESTADO->r[0xE];
    D_80069662 = 1;
}

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_80031948(Objeto* a0, Accion* a1) { D_80069698->wDE = ACC_W4(a1) << 4; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_80031960(Objeto* a0, Accion* a1) { D_80069698->w28 = ACC_W4(a1); }

void func_80031974(Objeto* a0, Accion* a1) { D_8006AA70[a1->w6] = a0->s1E; }

void func_80031990(Objeto* a0, Accion* a1) { a0->s1E = D_8006AA70[a1->w6]; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_800319AC(Objeto* a0, Accion* a1) { D_80069698->flags18 |= 1; }

/* Coincide en bytes; diff puntua la forma simbolica. */
void ActionGvcrt(Objeto* a0, Accion* a1)
{
    if (RA[1] != RA[2]) {
        RA[1]++;
    } else {
        RA[a1->w6]++;
    }
}

/* Guarda en el dato pequeno D_800693E0 el resultado de func_80045C4C; el original lo direcciona por $gp.
 * Coincide en bytes (1 referencia en forma numerica; el diff puntua 5 por la forma simbolica). */
void func_80031A0C(Objeto* a0, Accion* a1)
{
    D_800693E0 = func_80045C4C(ACC_W4(a1), 0, 0);
}

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
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

/* Guarda en el dato pequeno D_800693E0 el resultado de func_80045C4C; el original lo direcciona por $gp.
 * Coincide en bytes (1 referencia en forma numerica; el diff puntua 5 por la forma simbolica). */
void func_80031AE4(Objeto* a0, Accion* a1)
{
    D_800693E0 = func_80045C4C(D_8006AA70[a1->w6], 0, 0);
}

/* Como func_80031AE4 pero con el valor del banco A de registros. Coincide en bytes (3 referencias en forma
 * numerica; el diff puntua 15 por la forma simbolica). */
void func_80031B1C(Objeto* a0, Accion* a1)
{
    D_800693E0 = func_80045C4C(RA[a1->w6], 0, 0);
}

void func_80031B50(Objeto* a0, Accion* a1) { a0->trabajo.flags18 |= 0x10; }

void func_80031B64(Objeto* a0, Accion* a1) { a0->trabajo.flags18 &= ~0x10; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_80031B78(Objeto* a0, Accion* a1)
{
    u16 v;
    v = *(u16*)&a0->yE8;
    D_800693C0 = 0;
    D_800693B4 = 0;
    a0->w192 = 0;
    a0->w196 = v;
}

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_80031B98(Objeto* a0, Accion* a1) { D_80069659 = a1->b4; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_80031BAC(Objeto* a0, Accion* a1)
{
    u8 v;
    if (a0 != D_80069698 || a0->trabajo.i14 != 0x25 || (D_800694F2 & 1)) {
        D_8006965A = a1->b4;
        v = ((u8*)a1)[6];
        D_8006965E = 0;
        D_8006965B = v;
    }
}

void func_80031C10(Objeto* a0, Accion* a1)
{
    if (D_8006D928.s88 == 0) {
        D_8006D928.s8A = 0;
    }
    D_8006D928.s86 = ACC_W4(a1) * 11;
    D_8006D928.s88 = a1->w6;
}

/* Coincide en bytes; diff puntua la forma simbolica. */
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

/* Suelta el enlace del hijo p6C: lo marca con 0x100, borra su vuelta a este objeto si apuntaba a el y rompe el propio enlace. */
void func_80031CD4(Objeto* a0, Accion* a1)
{
    Objeto* o;
    o = a0->p6C;
    if (o != 0) {
        o->flags14 |= 0x100;
        o = a0->p6C;
        if (o->p70 == a0) {
            o->p70 = 0;
        }
        a0->p6C = 0;
    }
}

void func_80031D1C(Objeto* a0, Accion* a1) { a0->w3C |= 0x40; }

void func_80031D30(void) {}

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_80031D38(Objeto* a0, Accion* a1)
{
    D_8006965B = 0;
    D_8006965A = a1->b4;
    D_8006965E = ((u8*)a1)[6];
}

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_80031D60(Objeto* a0, Accion* a1)
{
    s32 v[3];
    s32 d;
    v[0] = a0->xE4 - D_8006D928.x;
    v[1] = a0->yE8 - D_8006D928.y;
    v[2] = a0->zEC - D_8006D928.z;
    d = func_80044940(v);
    if (d < 0x800) {
        /* 0x80031DD0, 0x80031E00 y 0x80031E10: sb a D_8006965A / D_8006965B con lui $at; el escalar u8 cambia el orden de la lectura de a1. */
        ((Byte*)&D_8006965A)->v = a1->b4;
        d = (a1->w6 * d) / 2048;
        if (d <= 0) {
            ((Byte*)&D_8006965B)->v = 0;
        } else {
            ((Byte*)&D_8006965B)->v = d;
        }
    }
}

/*
 * Sacude la camara con una amplitud proporcional a la cercania de un objeto: si no hay sacudida en curso y la
 * distancia al punto de vista es menor de 0x800, la amplitud es w6 * distancia / 2048 y la velocidad angular w4 * 11.
 */
void func_80031E24(Objeto* a0, Accion* a1)
{
    s32 v[3];
    s32 d;
    if (D_8006D928.s88 == 0) {
        v[0] = a0->xE4 - D_8006D928.x;
        v[1] = a0->yE8 - D_8006D928.y;
        v[2] = a0->zEC - D_8006D928.z;
        d = func_80044940(v);
        if (d < 0x800) {
            d = (a1->w6 * d) / 2048;
            if (d > 0) {
                D_8006D928.s8A = 0;
                D_8006D928.s86 = ACC_W4(a1) * 11;
                D_8006D928.s88 = d;
            }
        }
    }
}

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
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

void func_80031F70(Objeto* a0, Accion* a1)
{
    if (ACC_W4(a1) == 0) {
        func_8003AA50(1, 0x100);
    } else if (ACC_W4(a1) == 1) {
        func_8003AA7C(2, 0x100);
    }
}

void func_80031FBC(Objeto* a0, Accion* a1) { func_8003AA50(0x41, 0x400); }

/* Coincide en bytes (el diff marca 20 por direccion absoluta); el archivo se compila con -G8 */
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

void func_800320D8(Objeto* a0, Accion* a1) { D_8006D928.flags80 &= 0xDFFF; }

void func_800320F4(Objeto* a0, Accion* a1) { D_8006D928.flags80 |= 0x2000; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_80032110(Objeto* a0, Accion* a1)
{
    D_80069624 = -200;
    D_80069618 = 600;
    D_8006961C = 1100;
}

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_8003213C(Objeto* a0, Accion* a1) { D_80069624 = ACC_W4(a1) * 100 + a1->w6; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_80032170(Objeto* a0, Accion* a1) { D_80069618 = ACC_W4(a1) * 100 + a1->w6; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_800321A4(Objeto* a0, Accion* a1) { D_8006961C = ACC_W4(a1) * 100 + a1->w6; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_800321D8(Objeto* a0, Accion* a1) { D_8006960C = ((s8*)a1)[4] * 100 + ((s8*)a1)[6]; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_8003220C(Objeto* a0, Accion* a1) { D_8006960C = (ACC_W4(a1) << 8) | a1->w6; }

/* Coincide en bytes (el diff marca 20 por direccion absoluta); el archivo se compila con -G8 */
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

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_80032318(Objeto* a0, Accion* a1) { func_8003F06C(a0, ACC_W4(a1), 2, D_8006967C); }

void func_80032344(Objeto* a0, Accion* a1) { D_8006D928.flags80 &= 0x7FFF; }

void func_80032360(Objeto* a0, Accion* a1) { D_8006D928.flags80 |= 0x8000; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_8003237C(Objeto* a0) { D_80069560 = a0; }

void func_8003238C(Objeto* a0, Accion* a1) { a0->flags18 |= 0x400; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
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

void func_80032474(Objeto* a0, Accion* a1) { D_8006D928.flags80 &= 0xFCFF; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_80032490(Objeto* a0, Accion* a1) { D_80069554 = ACC_W4(a1); }

#ifdef NON_MATCHING
/* Pendiente: puntuacion 265 con la configuracion versionada (g = 8 del archivo). Solo difiere el prologo: el original reparte a0 (base del banco A), v1 (D_8006D064) y v0 (indice) y GCC los asigna en otro orden; las seis ramas siguientes coinciden. Variantes probadas: 8 (RA con puntero constante, extern D_80010040[], copia local de la mascara, tipos de v, puntero local). */
void func_800324A4(Objeto* a0, Accion* a1)
{
    u32 v;
    s32 a;
    v = RA[ACC_W4(a1)];
    if (D_8006D064 & 0x1) {
        a = 0x36;
        if (v != 1) {
            a = 0x2E;
        }
    } else {
        a = 0x3E;
        if (v == 1) {
            a = 0x46;
        }
    }
    func_80045C4C(a, 0, 0);
    if (D_8006D064 & 0x2) {
        a = 0x37;
        if (v != 2) {
            a = 0x2F;
        }
    } else {
        a = 0x3F;
        if (v == 2) {
            a = 0x47;
        }
    }
    func_80045C4C(a, 0, 0);
    if (D_8006D064 & 0x4) {
        a = 0x38;
        if (v != 3) {
            a = 0x30;
        }
    } else {
        a = 0x40;
        if (v == 3) {
            a = 0x48;
        }
    }
    func_80045C4C(a, 0, 0);
    if (D_8006D064 & 0x8) {
        a = 0x39;
        if (v != 4) {
            a = 0x31;
        }
    } else {
        a = 0x41;
        if (v == 4) {
            a = 0x49;
        }
    }
    func_80045C4C(a, 0, 0);
    if (D_8006D064 & 0x10) {
        a = 0x3A;
        if (v != 5) {
            a = 0x32;
        }
    } else {
        a = 0x42;
        if (v == 5) {
            a = 0x4A;
        }
    }
    func_80045C4C(a, 0, 0);
    if (D_8006D064 & 0x20) {
        a = 0x3B;
        if (v != 6) {
            a = 0x33;
        }
    } else {
        a = 0x43;
        if (v == 6) {
            a = 0x4B;
        }
    }
    func_80045C4C(a, 0, 0);
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_800324A4);
#endif

void func_8003264C(Objeto* a0, Accion* a1) { D_8006D928.flags80 |= 1; }

void func_80032668(Objeto* a0, Accion* a1) { D_8006D928.flags80 &= 0xFFFE; }

void func_80032684(Objeto* a0, Accion* a1) { D_8006D9A8[0] = 0x10; }

/* Almacenes en forma simbolica: el archivo se compila con -G8 (config/opciones_compilacion.toml) */
void func_80032694(Objeto* a0, Accion* a1) { D_80069698->flags14 &= ~9; }

void func_800326B4(Objeto* a0, Accion* a1) { D_8006D928.flags80 |= 0x20; }

void func_800326D0(Objeto* a0, Accion* a1) { D_8006D928.flags80 &= 0xFFDF; }

void func_800326EC(Objeto* a0, Accion* a1) { D_8006D928.flags80 |= 4; }

#ifdef NON_MATCHING
/* Pendiente: puntuacion 600 con la configuracion versionada (g = 8 del archivo). Los cuatro bucles de busqueda coinciden con la forma for/while; difiere el reparto de a0, a2 y v1 del prologo (el original comparte con a2 la base de D_80010040 y D_80010010). Variantes probadas: 9 (do/while con guarda, for, while y copias locales de la mascara). */
/* Mueve la seleccion del menu al siguiente elemento habilitado de los seis posibles, hacia delante o hacia atras segun la direccion pulsada. */
void func_80032708(Objeto* a0, Accion* a1)
{
    s32 v;
    s32 i;
    v = RA[ACC_W4(a1)];
    if (D_8006D064 & (1 << (v - 1))) {
        return;
    }
    if (ESTADO->botones & 0x6000) {
        for (i = v; i < 7; i++) {
            if (D_8006D064 & (1 << (i - 1))) {
                break;
            }
        }
        if (i >= 7) {
            if (ESTADO->botones & 0x2000) {
                i = v - 3;
            } else {
        for (i = 6; i > 0; i--) {
            if (D_8006D064 & (1 << (i - 1))) {
                break;
            }
        }
            }
        }
    } else {
        for (i = v; i > 0; i--) {
            if (D_8006D064 & (1 << (i - 1))) {
                break;
            }
        }
        if (i <= 0) {
            if (ESTADO->botones & 0x8000) {
                i = v + 3;
            } else {
        for (i = 1; i < 7; i++) {
            if (D_8006D064 & (1 << (i - 1))) {
                break;
            }
        }
            }
        }
    }
    RA[ACC_W4(a1)] = i;
}
#else
INCLUDE_ASM("asm/nonmatchings/interprete_de_eventos", func_80032708);
#endif

#include "common.h"
#include "psyq/TYPES.H"
#include "psyq/LIBGTE.H"
#include "psyq/LIBGPU.H"

/*
 * Presentacion de cuadros: el retorno de llamada de VSync (func_80040AF0) cuenta cuadros y
 * el de DrawSync (func_80040A80) dispara func_80040B8C, que avanza el anillo de tres buffers
 * de dibujo y envia sus listas de ordenacion.
 *
 * Las funciones de este archivo que escriben variables de la zona 0x80069xxx se emiten en
 * forma simbolica (sh $2,D_xxx, que el ensamblador expande con $at), como el original, solo
 * con un umbral de datos pequenos mayor que cero (-G8) para este archivo. Con el -G0 por
 * omision de config/opciones_compilacion.toml conservan el ensamblador (NON_MATCHING).
 * Las que ademas leen o escriben datos pequenos direccionados con $gp (func_80040A80,
 * func_80040B8C, func_80040DDC y func_80040E30) no se pueden reproducir con el ensamblador
 * del flujo: el original usa un simbolo externo pequeno con desplazamiento $gp, que GNU as
 * solo reescribe a $gp si el simbolo se define en el mismo archivo; el resto del cuerpo
 * coincide.
 */

/*
 * Estado de presentacion de cuadros (zona 0x80069xxx). Las dos cuentas son volatile porque
 * el retorno de llamada de VSync las modifica mientras el bucle principal las lee.
 */
extern vu16 D_80069676;
extern vu16 D_800695A6;
extern s16 D_800695BC;
extern s16 D_8006967C;
extern u32 D_80069610;
extern u32 D_80069614;
extern u32 D_80069510;
extern u8 D_800695DC;
extern u8 D_80069620;
extern u32 D_8006AD40[];

/* Tres listas de ordenacion por buffer: cada entrada mide 0x14 bytes y su puntero esta en +0x10. */
typedef struct EntradaOrden {
    u8 pad0[0x10];
    u_long* ot;
} EntradaOrden;
extern EntradaOrden D_8006AE20[];
extern EntradaOrden D_8006AE60[];
extern EntradaOrden D_8006AEA0[];

/* Alias no cacheado (0xA0000000) de func_80040A80, registrado como retorno de DrawSync. */
extern u8 D_A0040A80[];

extern void GsSwapDispBuff(void);
extern void func_8003F528(s32 buffer);
extern void func_80040B8C(void);

/* Datos pequenos direccionados con $gp (0x80069320 + desplazamiento). */
extern s8 D_80069338;
extern u8 D_800694A8;
extern s32 D_800694A4;
extern s32 D_80069488;

#ifdef NON_MATCHING
/*
 * Depende de $gp y de g = 8: 110 con g = 8; con la configuracion actual -G0 da 210.
 * Retorno de llamada de DrawSync: si hay un cuadro por presentar (cuenta de cuadros
 * positiva), ya pasaron al menos dos VSync y la GPU esta libre, lanza el dibujo.
 * Puntuacion 110 con -G8: solo difiere el acceso a la bandera D_80069338, que el original
 * hace como lb 0x18($gp) antes de reservar el marco. Con una variable de registro $28 el
 * compilador reserva el marco antes de cargar la bandera.
 */
void func_80040A80(void)
{
    if (D_80069338 != 0 && (s16)D_80069676 > 0 && (s16)D_800695A6 >= 2 && DrawSync(1) == 0) {
        func_80040B8C();
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte_10", func_80040A80);
#endif

#ifdef NON_MATCHING
/*
 * Coincide con g = 8 (0); con la configuracion actual -G0 da 1600.
 * Retorno de llamada de VSync: cuenta el cuadro y, si la comprobacion de disco no esta
 * activa, intenta presentar el siguiente. Puntuacion 0 con -G8 (umbral de datos pequenos
 * de este archivo); con el -G0 por omision las escrituras no usan $at.
 */
void func_80040AF0(void)
{
    if (D_80069620 == 0) {
        D_800695A6 += 1;
        D_800695DC += 1;
        D_80069510 += 1;
        if ((s16)D_80069676 > 0 && (s16)D_800695A6 >= 2) {
            func_80040B8C();
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte_10", func_80040AF0);
#endif

#ifdef NON_MATCHING
/*
 * Depende de $gp y de g = 8: 220 con g = 8; con la configuracion actual -G0 da 3978.
 * Presenta el cuadro: si la GPU esta ocupada deja la bandera de pendiente (y reinicia el
 * grafico si lleva cuatro VSync colgada); si no, avanza el anillo de buffers y envia las
 * tres listas de ordenacion del buffer activo. Puntuacion 220 con -G8: solo difiere el
 * acceso a la bandera D_80069338 ($gp + 0x18, lb y sb).
 */
void func_80040B8C(void)
{
    if (DrawSync(1) == 0) {
        D_80069338 = 0;
        DrawSyncCallback(NULL);
        D_800695BC += 1;
        if (D_800695BC == 3) {
            D_800695BC = 0;
        }
        if (D_800695BC == D_8006967C) {
            D_800695BC -= 1;
            if (D_800695BC < 0) {
                D_800695BC = 2;
            }
            D_80069676 -= 1;
            return;
        }
        GsSwapDispBuff();
        func_8003F528(D_800695BC);
        DrawOTag(D_8006AEA0[D_800695BC].ot);
        DrawOTag(D_8006AE60[D_800695BC].ot);
        DrawOTag(D_8006AE20[D_800695BC].ot);
        DrawSyncCallback((void (*)())D_A0040A80);
        D_800695A6 = 0;
        D_80069610 = D_80069614;
        D_80069676 -= 1;
        D_80069614 = D_8006AD40[D_800695BC];
    } else {
        D_80069338 = 1;
        if ((s16)D_800695A6 >= 4 && DrawSync(1) != 0) {
            ResetGraph(1);
            while (DrawSync(1) != 0) {
            }
        }
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte_10", func_80040B8C);
#endif

/*
 * Marca con el bit 15 cada celda no nula de una tabla de s16 (el bit alto distingue una
 * entrada ocupada); el numero de celdas esta en el campo +4 de la cabecera.
 */
typedef struct CabeceraLista {
    s16 pad0;
    s16 pad2;
    s16 cuenta;
} CabeceraLista;

void func_80040D98(CabeceraLista* a0, s16* a1)
{
    s32 i;

    for (i = 0; i < a0->cuenta; i++) {
        if (*a1 != 0) {
            *a1 = *a1 | 0x8000;
        }
        a1++;
    }
}

#ifdef NON_MATCHING
/*
 * Depende de $gp: 110 con g = 8 y tambien con -G0.
 * Copia de VRAM de la barra de progreso de carga si la pantalla de carga esta activa
 * (bit 0 de 0x800694A8). Puntuacion 110 con -G8: solo difiere la lectura de 0x188($gp).
 */
void func_80040DDC(void)
{
    RECT r;

    if (D_800694A8 & 1) {
        r.x = 0x26C;
        r.y = 0x1E0;
        r.w = 0x12C;
        r.h = 0x10;
        MoveImage(&r, 0x26C, 0x19A);
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte_10", func_80040DDC);
#endif

#ifdef NON_MATCHING
/*
 * Depende de $gp y de g = 8: 330 con g = 8; con la configuracion actual -G0 da 590.
 * Copia de VRAM de la barra de progreso de carga: el ancho es restante / (total / 300)
 * (0x80069488 y 0x800694A4, datos pequenos de $gp). Puntuacion 330 con -G8: solo difieren
 * las tres lecturas de $gp (0x188, 0x184 y 0x168).
 */
void func_80040E30(void)
{
    RECT r;

    if ((D_800694A8 & 1) && D_800694A4 != 0) {
        r.x = 0x26C;
        r.y = 0x1F0;
        r.h = 0x10;
        r.w = D_80069488 / (D_800694A4 / 300);
        MoveImage(&r, 0x26C, 0x199);
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/graficos_y_gte_10", func_80040E30);
#endif

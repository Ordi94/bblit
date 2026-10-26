#include "common.h"
#include "globales.h"
#include "psyq/TYPES.H"
#include "psyq/LIBGTE.H"
#include "psyq/LIBGPU.H"

/*
 * Presentacion de cuadros: el retorno de llamada de VSync (func_80040AF0) cuenta cuadros y
 * el de DrawSync (func_80040A80) dispara func_80040B8C, que avanza el anillo de tres buffers
 * de dibujo y envia sus listas de ordenacion.
 *
 * Este archivo se compila con un umbral de datos pequenos (-G8, config/opciones_compilacion.toml):
 * las escrituras a variables de la zona 0x80069xxx salen en forma simbolica (sh $2,D_xxx, que
 * el ensamblador expande con $at), como en el original. Las variables que el original direcciona
 * con desplazamiento($gp) (D_80069338, D_80069488, D_800694A4 y D_800694A8) se definen aqui sin
 * extern: maspsx las reescribe a $gp y el enlace les da su direccion (tabla datos_pequenos).
 */


/* Alias no cacheado (0xA0000000) de func_80040A80, registrado como retorno de DrawSync. */
extern u8 D_A0040A80[];

extern void GsSwapDispBuff(void);
extern void func_8003F528(s32 buffer);
extern void func_80040B8C(void);

/*
 * Datos pequenos direccionados con $gp (0x80069320 + desplazamiento). D_80069488 lleva volatile
 * igual que en cargador_de_niveles_y_cd.c, que es quien lo escribe: la definicion tentativa debe
 * tener el mismo calificador en los dos archivos, y la medicion de ambos con y sin volatile
 * deja las funciones en C del par con la misma puntuacion con volatile y empeora func_8004109C
 * (105 a 705) sin el.
 */
s8 D_80069338;
u8 D_800694A8;
s32 D_800694A4;
volatile s32 D_80069488;

/*
 * Retorno de llamada de DrawSync: si hay un cuadro por presentar (cuenta de cuadros
 * positiva), ya pasaron al menos dos VSync y la GPU esta libre, lanza el dibujo.
 * La bandera D_80069338 se lee como lb 0x18($gp) antes de reservar el marco: solo sale asi
 * con la variable definida en el archivo; con una variable de registro $28 el compilador
 * reserva el marco antes de cargarla. El diff marca la forma numerica de la referencia.
 */
void func_80040A80(void)
{
    if (D_80069338 != 0 && (s16)D_80069676 > 0 && (s16)D_800695A6 >= 2 && DrawSync(1) == 0) {
        func_80040B8C();
    }
}

/*
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

/*
 * Presenta el cuadro: si la GPU esta ocupada deja la bandera de pendiente (y reinicia el
 * grafico si lleva cuatro VSync colgada); si no, avanza el anillo de buffers y envia las
 * tres listas de ordenacion del buffer activo. La bandera D_80069338 ($gp + 0x18, lb y sb)
 * es una variable pequena definida en este archivo.
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
        /* 0x80040C74, 0x80040CA0 y 0x80040CCC: lw a0,0x10(v0) carga GsOT.tag (+0x10) y lo pasa a DrawOTag, que espera u_long*. */
        DrawOTag((u_long*)D_8006AEA0[D_800695BC].tag);
        DrawOTag((u_long*)D_8006AE60[D_800695BC].tag);
        DrawOTag((u_long*)D_8006AE20[D_800695BC].tag);
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

/*
 * Marca con el bit 15 cada celda no nula de una tabla de s16 (el bit alto distingue una
 * entrada ocupada); el numero de celdas esta en el campo +4 de la cabecera.
 */
void func_80040D98(RECT* a0, s16* a1)
{
    s32 i;

    for (i = 0; i < a0->w; i++) {
        if (*a1 != 0) {
            *a1 = *a1 | 0x8000;
        }
        a1++;
    }
}

/*
 * Copia de VRAM de la barra de progreso de carga si la pantalla de carga esta activa
 * (bit 0 de 0x800694A8, dato pequeno de $gp + 0x188).
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

/*
 * Copia de VRAM de la barra de progreso de carga: el ancho es restante / (total / 300)
 * (0x80069488 y 0x800694A4, datos pequenos de $gp: 0x168, 0x184 y 0x188).
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

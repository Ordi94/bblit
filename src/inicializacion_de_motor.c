#include "common.h"
#include "globales.h"
#include "objetos.h"
#include "psyq/LIBETC.H"
#include "psyq/LIBCD.H"
#include "psyq/LIBPRESS.H"
#include "psyq/LIBSPU.H"
#include "motor.h"

/* Origen de una entrada: un u16 en +0 y un byte en +4. */
typedef struct OrigenEntrada {
    u16 h0;
    u8 pad2[2];
    u8 b4;
} OrigenEntrada;

extern void func_800449E0(u8* destino);
extern void* memset(void* destino, s32 valor, u32 cantidad);
extern void FlushCache(void);
extern void func_8003ED6C(void);
extern void func_8003FFA0(void);
extern void func_8003502C(Objeto* objeto);
extern void func_8004BBF0(s32 valor);
extern void func_8004E584(s32 valor);
extern void func_80044EA8(s32 a0, u32 a1, Objeto* a2);
extern void func_80055AFC(s32 valor);
extern void func_8005595C(s32 valor);

/* Registro de la pantalla de la libreria grafica; el arreglo evita la forma simbolica de -G8 (lui + desplazamiento en el original). */
extern u16 D_80075FFE[5];
extern u16 D_8006D018[];
extern void func_80039CD0(s32 prim);
extern u32 func_80045498(Objeto* objeto, void* guion, BloqueTrabajo* bloque);
/*
 * Estado que func_80044A04 reinicia al empezar el nivel. Los de un tamano de dos o cuatro bytes se
 * declaran escalares: el original los escribe con la forma simbolica de -G8 (lui at).
 */
extern s16 D_80069650;
extern s16 D_800694CC;
extern s16 D_80069634;
extern s16 D_800694E4;
extern s16 D_800694BC;
extern s16 D_80069602;
extern s32 D_8006962C;
extern u8 D_800694B2;
extern u8 D_8006956C;
extern u8 D_8006963D;
extern u8 D_80069574;
extern u8 D_8006965F;
extern u8 D_8006950C;
extern u8 D_80069514;
extern u8 D_80069525;
extern u8 D_80069500;
extern u8 D_80069684;
extern s16 D_8006956A;
extern s32 D_80069604;
extern u8 D_800694F6;
extern s16 D_80069526;
extern s16 D_8006969E;
extern s16 D_8006968A;
extern s16 D_800695C0;
extern void func_800449E8(u8* tabla);
extern void func_800400C0(void);

/* Tabla de veintisiete punteros a datos del motor que el overlay consulta. */
extern u8 D_800695B8[];
extern u8 D_80069664[];


INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_80044904);

#ifdef NON_MATCHING
/* Pendiente: puntuacion 1460 con la configuracion versionada (g = 8 del archivo). Ensamblador manuscrito: neg y add con trampa de desbordamiento, registros fijos t0 a t2 y el temporal at en slt; GCC emite negu, addu y otro reparto de registros. Variantes probadas: 3. */
u32 func_80044940(s32* v)
{
    s32 x;
    s32 y;
    s32 z;
    s32 mayor;
    s32 medio;
    s32 menor;

    x = v[0];
    y = v[1];
    z = v[2];
    if (x < 0) {
        x = -x;
    }
    if (y < 0) {
        y = -y;
    }
    if (z < 0) {
        z = -z;
    }
    mayor = x;
    menor = y;
    if (x < y) {
        mayor = y;
        menor = x;
    }
    medio = z;
    if (mayor < z) {
        medio = mayor;
        mayor = z;
    }
    return (mayor + ((u32)menor >> 2) + ((u32)medio >> 2)) | 1;
}
#else
INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_80044940);
#endif

#ifdef NON_MATCHING
/* Pendiente: puntuacion 960 con la configuracion versionada (g = 8 del archivo). Ensamblador manuscrito: registros fijos t0 y t1, nop explicito tras cada lw y el simbolo de la funcion vecina cargado con lui + lw; GCC reparte v0, v1 y a0. Variantes probadas: 2. */
void func_800449B0(void)
{
    u32* destino;
    u32* origen;

    destino = (u32*)FntLoad;
    origen = (u32*)func_800449E0;
    destino[9] = origen[0];
    destino[12] = origen[1];
}
#else
INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_800449B0);
#endif

#ifdef NON_MATCHING
/* Pendiente: puntuacion 210 con la configuracion versionada (g = 8 del archivo). Solo difieren dos instrucciones muertas del original (ori a1,zero,0x200 y ori a2,zero,0x1FF antes de la etiqueta de entrada func_800449E8) que GCC elimina. Variantes probadas: 2. */
void func_800449E0(u8* a0)
{
    s32 i;

    i = 0x21;
    do {
        *a0 = 0;
        i--;
        a0++;
    } while (i >= 0);
}
#else
INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_800449E0);
#endif

#ifdef NON_MATCHING
/* Pendiente: puntuacion 415 con la configuracion versionada (g = 8 del archivo). Mismas escrituras y mismo orden; el original coloca lui a0 de la primera llamada despues de la lectura de D_800695A6 y la planificacion del compilador la adelanta. Variantes probadas: 6. */
void func_80044A04(void)
{
    s32 buffer;
    u8* estado;

    D_80069650 = 0;
    D_800694CC = 0;
    D_8006966A = 0;
    D_800695F6 = 0;
    buffer = GsGetActiveBuff();
    D_800695A6 = 0;
    D_8006967C = buffer;
    D_800695BC = buffer;
    D_80069634 = buffer;
    D_8006D018[0] = 0;
    D_8006952C = 0x32;
    D_80069676 = D_800695A6;
    D_80069560 = 0;
    D_80069508 = NULL;
    D_80069698 = NULL;
    D_80069584 = 0;
    D_800694E4 = 0;
    D_80069668 = 0;
    D_800694BC = 0;
    D_80069602 = 0x80;
    D_80069628 = D_80069676;
    func_800449E8(D_8006CFF0);
    func_800449E8(D_8006D038);
    func_800400C0();
    D_800694C8 = -1;
    D_8006962C = 0x1E;
    D_800694B2 = 0xFF;
    D_8006956C = 0xFF;
    D_8006963D = 0xFF;
    D_80069574 = 0xFF;
    D_8006965F = 0xFF;
    D_8006950C = 0xFF;
    D_80069514 = 0xFF;
    D_80069525 = 0xFF;
    D_80069524 = 0xFF;
    D_80069500 = 0xFF;
    D_80069684 = 0xFF;
    D_80069662 = 0;
    D_80069588 = 0;
    D_8006956A = 0;
    D_80069604 = 0;
    D_800694F6 = 0;
    D_800694F2 = 0;
    D_80069526 = 0;
    D_8006969E = 0;
    D_8006968A = 0;
    D_800695C0 = 0;
    estado = (u8*)0x80010000;
    estado[0x49] = 0;
    estado[0x4A] = 0;
    estado[0x4B] = 0;
    estado[0x4C] = 0;
    estado[0x70] = 0;
    estado[0x71] = 0;
    estado[0x72] = 0;
    estado[0x73] = 0;
    D_8006B2F8[0] = D_8006AE20;
    D_8006B2F8[1] = D_8006AE60;
    D_8006B2F8[2] = D_8006AEA0;
    D_8006B2F8[3] = &D_8006967C;
    D_8006B2F8[4] = D_8006A940;
    D_8006B2F8[5] = &D_80069588;
    D_8006B2F8[6] = D_800695B8;
    D_8006B2F8[7] = &D_80069680;
    D_8006B2F8[8] = &D_8006958C;
    D_8006B2F8[9] = &D_80069610;
    D_8006B2F8[10] = (void*)&D_800695A6;
    D_8006B2F8[11] = D_80069664;
    D_8006B2F8[12] = &D_8006954C;
    D_8006B2F8[13] = &D_800695D0;
    D_8006B2F8[14] = D_8006B658;
    D_8006B2F8[15] = &D_8006969C;
    D_8006B2F8[16] = &D_800694B0;
    D_8006B2F8[17] = &D_800695F2;
    D_8006B2F8[18] = &D_800695F4;
    D_8006B2F8[19] = D_8006B668;
    D_8006B2F8[20] = &D_8006956A;
    D_8006B2F8[21] = &D_800695DA;
    D_8006B2F8[22] = &D_800695C4;
    D_8006B2F8[25] = &D_800695A2;
    D_8006B2F8[26] = &D_800695A4;
    D_8006D928.z = 0;
    D_8006D928.y = 0;
    D_8006D928.x = 0;
    D_8006D928.vpz = 0;
    D_8006D928.vpy = 0;
    D_8006D928.vpx = 0;
    D_80069558 = NULL;
}
#else
INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_80044A04);
#endif

void func_80044D44(void)
{
    FlushCache();
    ResetGraph(0);
    SetGraphDebug(0);
    func_8003ED6C();
    func_8003FFA0();
    CdInit();
    CdSetDebug(0);
    func_8004E584(0);
    GsInitGraph(0x200, 0xF0, 4, 1, 0);
    GsDefDispBuff(0x200, 0, 0x200, 0x100);
    D_80075FFE[0] = 0xF0;
    GsInit3D();
    InitGeom();
    ResetCallback();
    CdDataCallback(NULL);
    CdReadCallback(NULL);
    CdReadyCallback(NULL);
    CdSyncCallback(NULL);
    VSyncCallback(NULL);
    DrawSyncCallback(NULL);
    DecDCTinCallback(NULL);
    DecDCToutCallback(NULL);
    func_8004BBF0(0);
    SpuSetIRQCallback(NULL);
    SpuStSetPreparationFinishedCallback(NULL);
    SpuStSetTransferFinishedCallback(NULL);
    SpuStSetStreamFinishedCallback(NULL);
    DecDCTReset(0);
}

void func_80044E58(void)
{
    memset(&D_8006D928, 0, 0xE8);
    D_8006D928.super = NULL;
    GsSetRefView2L((GsRVIEW2*)&D_8006D928);
    func_80055AFC(0x190);
    func_8005595C(0x64);
}

#ifdef NON_MATCHING
/* Pendiente: puntuacion 355 con la configuracion versionada (g = 8 del archivo). Misma estructura que el original; difiere la planificacion de la carga de la direccion de D_8006D018 (lui) y de la mascara andi 0xFFFF. Variantes probadas: 9. */
void func_80044EA8(s32 a0, u32 a1, Objeto* a2)
{
    NodoAnimacion* nodo;
    TablaFotogramas* tabla;
    Fotograma* f;

    nodo = a2->lista;
    while (nodo != NULL && nodo->def->tipo != 8) {
        nodo = nodo->sig;
    }
    tabla = nodo->def->tabla;
    a2->tabla = tabla;
    f = &tabla->fotogramas[a1 & 0xFFFF];
    D_8006D018[(s16)a0] = f->h0A;
}
#else
INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_80044EA8);
#endif

void func_80044F20(void)
{
    Objeto* o;

    o = func_80036734(0x44, NULL, NULL);
    if (o == NULL) {
        D_8006D018[0] = 0;
    } else {
        func_80044EA8(0, 0, o);
        func_80044EA8(5, 0x66, o);
        func_80044EA8(6, 0x67, o);
        func_80044EA8(7, 0x68, o);
        func_80044EA8(8, 0x69, o);
        func_80044EA8(9, 0x6B, o);
        func_80044EA8(0xA, 0x6A, o);
        func_80044EA8(0xB, 0x6C, o);
        func_80044EA8(0xC, 0x6D, o);
        func_8003502C(o);
    }
    o = func_80036734(0x303, NULL, NULL);
    if (o == NULL) {
        D_8006D018[1] = 0;
    } else {
        func_80044EA8(1, 0, o);
        func_8003502C(o);
    }
    o = func_80036734(0x302, NULL, NULL);
    if (o == NULL) {
        D_8006D018[2] = 0;
    } else {
        func_80044EA8(2, 0, o);
        func_8003502C(o);
    }
    o = func_80036734(0x312, NULL, NULL);
    if (o == NULL) {
        D_8006D018[3] = 0;
    } else {
        func_80044EA8(3, 0, o);
        func_8003502C(o);
    }
    o = func_80036734(0x301, NULL, NULL);
    if (o == NULL) {
        D_8006D018[4] = 0;
        return;
    }
    func_80044EA8(4, 0, o);
    func_8003502C(o);
}

void func_800450E8(Glifo* a0, u8 a1, OrigenEntrada* a2)
{
    D_800694D4->glifo = a0;
    D_800694D4->x = a2->h0;
    D_800694D4->y = a2->b4;
    D_800694D4->idx = a1;
    D_800694D4++;
    D_80069652++;
}

#ifdef NON_MATCHING
/* Pendiente: puntuacion 3641 con la configuracion versionada (g = 8 del archivo). Misma estructura de bucle y de escrituras de la primitiva; el original reparte s6 al contador y s7 y fp a las dimensiones del glifo, el C los reparte al reves y desplaza el resto de la planificacion. Variantes probadas: 8. */
void func_80045150(EntradaLista* e)
{
    Glifo* g;
    u8* p;
    s32 i;
    u16 x;
    s32 y;
    u8 u;
    u8 v;
    s32 w;
    s32 h;
    s32 c;
    s32 color;
    u32* cabeza;

    i = 0;
    if (D_80069652 > 0) {
        do {
            g = e->glifo;
            x = e->x;
            y = (s8)e->y;
            u = g->u;
            v = g->v;
            w = g->w - 1;
            h = g->h - 1;
            func_80039CD0(D_80076188);
            if (D_8006966A != 0) {
                c = 0x80 - ((s16)D_800694E2 >> 5);
                color = c + ((c << 16) + ((c << 8) + 0x2C000000));
            } else {
                color = 0x2C808080;
            }
            cabeza = (u32*)D_8006AE20[D_8006967C].org;
            p = (u8*)D_80076188;
            *(s32*)(p + 4) = color;
            *(u32*)p = *cabeza | 0x09000000;
            *cabeza = ((s32)p << 8) >> 8;
            *(s16*)(p + 0x10) = x + w;
            *(s16*)(p + 0x20) = x + w;
            *(s16*)(p + 0x22) = y + h;
            *(s16*)(p + 0x1A) = y + h;
            p[0x24] = u + w;
            p[0x14] = u + w;
            *(s16*)(p + 0x18) = x;
            *(s16*)(p + 8) = x;
            *(s16*)(p + 0x12) = y;
            *(s16*)(p + 0xA) = y;
            p[0x1C] = u;
            p[0xC] = u;
            p[0x15] = v;
            p[0xD] = v;
            p[0x25] = v + h;
            p[0x1D] = v + h;
            *(u16*)(p + 0x16) = e->glifo->tpage;
            D_80076188 += 0x28;
            *(u16*)(p + 0xE) = D_8006D018[e->idx];
            if (D_8006958C < D_80076188) {
                D_80076188 = D_80069680;
            }
            i++;
            e++;
        } while (i < D_80069652);
    }
}
#else
INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_80045150);
#endif

void func_80045368(s16 a0, s16 a1)
{
    EntradaLista* e;
    s16 i;
    s16 n;
    s32 d;

    d = a1 >> 1;
    i = a0;
    n = D_80069652;
    if (i < n) {
        do {
            e = (EntradaLista*)((i << 3) + (s32)D_800694B8);
            i++;
            e->x -= d;
        } while (i < n);
    }
}

#ifdef NON_MATCHING
/* Pendiente: puntuacion 230 con la configuracion versionada (g = 8 del archivo). El bucle de digitos incrementa el indice antes de leer en el original (li a1 frente a addiu a1,a1,1 y desplazamiento 0 frente a -1). Variantes probadas: 16. */
s32 func_800453D0(u8** p)
{
    s32 signo;
    s32 valor;
    s32 n;
    s32 i;
    u8* t;

    signo = 1;
    if (**p == 0x2D) {
        signo = -1;
        *p = *p + 1;
    }
    valor = 0;
    n = 0;
    if ((**p >> 4) == 3) {
        t = *p;
        n++;
        do {
            n++;
        } while ((t[n - 1] >> 4) == 3);
        n--;
    }
    i = n - 1;
    for (; i >= 0; i--) {
        valor += ((*p)[i] & 0xF) * signo;
        signo *= 10;
    }
    *p = *p + n;
    return valor;
}
#else
INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_800453D0);
#endif

INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_80045498);

#ifdef NON_MATCHING
/* Pendiente: puntuacion 175 con la configuracion versionada (g = 8 del archivo). Mismo flujo y mismas escrituras; el original conserva una copia de a2 en v0 para la primera comparacion y emite el sh de +0x26 despues de la carga del byte de D_8006AA7C. Variantes probadas: 12. */
u32 func_80045C4C(u32 a0, void* a1, Objeto* a2)
{
    BloqueTrabajo* bloque;
    NodoAnimacion* nodo;
    TablaFotogramas* tabla;
    u32 r;
    u32 v;

    if (a2 != NULL) {
        a1 = a2->p180;
        bloque = &a2->trabajo;
        a2->p180 = NULL;
    } else {
        a2 = func_80036734(0x44, NULL, NULL);
        if (a2 == NULL) {
            return 0;
        }
        nodo = a2->lista;
        bloque = &a2->trabajo;
        while (nodo != NULL && nodo->def->tipo != 8) {
            nodo = nodo->sig;
        }
        tabla = nodo->def->tabla;
        a2->tabla = tabla;
        bloque->fotogramas = tabla->fotogramas;
        a2->w17E = a0 + 0x8000;
        a2->p180 = NULL;
        a1 = (u8*)D_80069590 + D_80069590[a0];
        a2->w26 = D_80069698->w26;
        if (D_8006AA7C == 1) {
            a2->flags0C |= 0x40000000;
        }
    }
    r = func_80045498(a2, a1, bloque);
    v = (r >> 4) & 8;
    if (r & 0x20) {
        v |= 2;
    }
    if (r & 0x10) {
        v |= 1;
    }
    if (r & 0x40) {
        v |= 4;
    }
    return v;
}
#else
INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_80045C4C);
#endif

void func_80045D98(void)
{
}

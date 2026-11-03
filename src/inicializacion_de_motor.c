#include "common.h"
#include "globales.h"
#include "objetos.h"
#include "arranque.h"
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
extern u32 func_80045498(Objeto* objeto, u8* guion, BloqueTrabajo* bloque);
extern u32 func_80037D3C(u16 valor);
extern u32 func_80045D98(u32 mascara);

/* Posicion de la pluma de texto: func_800450E8 la lee por la direccion (x en +0, y en +4). */
typedef struct PosicionTexto {
    s32 x;
    s32 y;
} PosicionTexto;

/* Tablas del texto: indice de glifo y avance horizontal por caracter, y nombres de boton por configuracion. */
extern u8 D_8005F940[];
extern u8 D_8005FA40[];
extern u8 D_8005F920[];
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
extern u8 D_8006965F;
extern u8 D_8006950C;
extern u8 D_80069500;
extern u8 D_80069684;
extern s16 D_8006956A;
extern s32 D_80069604;
extern void func_800449E8(u8* tabla);
extern void func_800400C0(void);

/* Tabla de veintisiete punteros a datos del motor que el overlay consulta. */
extern u8 D_80069664[];


/*
 * Rutina escrita a mano en el original: sin addiu sp, es la salida de func_80044664; toma el contexto
 * de s1 (addu a2,s1,zero en 0x80044904), guarda s0 en D_8006949C (0x8004490C), restaura ra y s0..fp
 * desde ese contexto (lw 0x80044910..0x80044934) y vuelve con jr ra.
 */
INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_80044904);

/*
 * Rutina escrita a mano en el original: sin addiu sp, con los temporales fijos t0..t2 (lw en
 * 0x80044940..0x80044948), neg y add con trampa de desbordamiento (neg en 0x80044954, 0x80044960 y
 * 0x8004496C; add en 0x800449A0 y 0x800449A4) y at como destino de los slt (0x80044970 y
 * 0x80044984). Calcula la magnitud aproximada de un vector de tres componentes (mayor + menor/4 +
 * medio/4) | 1. GCC emite negu, addu y otro reparto de registros.
 */
INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_80044940);

/*
 * Rutina escrita a mano en el original: sin addiu sp, con los temporales fijos t0 y t1 (lui/addiu
 * en 0x800449B0 y 0x800449B4), nop explicito tras cada lw (0x800449C0 y 0x800449D0) y el simbolo de
 * la funcion vecina cargado con lui + lw (0x800449B8..0x800449BC y 0x800449C8..0x800449CC) para
 * copiar sus dos primeras palabras dentro de FntLoad. GCC reparte v0, v1 y a0.
 */
INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_800449B0);

/*
 * Rutina escrita a mano en el original: sin marco de pila, dos ori de relleno (0x800449E0 y
 * 0x800449E4) antes del segundo punto de entrada func_800449E8 (0x800449E8), y func_800449B0 copia
 * sus dos primeras palabras como datos dentro de FntLoad. GCC elimina los ori muertos y no existe
 * C que reproduzca un segundo punto de entrada, por eso se conserva como ensamblador.
 */
INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_800449E0);

/*
 * Reinicia el estado del motor: banderas, indices de los tres buffers, tabla de punteros de datos
 * del codigo superpuesto (D_8006B2F8) y camara. Los dos buffers del mando (D_8006CFF0 y
 * D_8006D038) se pasan por direccion de un byte suelto: con -G8 la direccion de un objeto de
 * hasta 8 bytes se emite como un solo `la`, que el planificador no parte ni usa para rellenar el
 * hueco de retardo del `jal`, igual que el original.
 */
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
    func_800449E8(&D_8006CFF0);
    func_800449E8(&D_8006D038);
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
    D_8006B2F8[6] = &D_800695B8;
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
/* Pendiente: puntuacion 310 con la configuracion versionada (g = 8 del archivo). Misma estructura y mismo reparto de registros que el original (la tabla comparte registro con la definicion del nodo); difiere la planificacion: el original coloca la parte alta de D_8006D018 (lui) en el hueco de la carga de la definicion y carga el arreglo de fotogramas despues de guardar la tabla en el objeto, mientras que GCC carga el arreglo antes del almacen y deja un nop tras la lectura de la definicion. */
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
    /* La direccion del arreglo de fotogramas se calcula antes de guardar la tabla en el objeto:
     * con el almacen primero la tabla cae en otro registro que la definicion del nodo. */
    f = &tabla->fotogramas[a1 & 0xFFFF];
    a2->trabajo.tabla = tabla;
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

void func_800450E8(Glifo* a0, u16 a1, OrigenEntrada* a2)
{
    D_800694D4->glifo = a0;
    D_800694D4->x = a2->h0;
    D_800694D4->y = a2->b4;
    D_800694D4->idx = a1;
    D_800694D4++;
    D_80069652++;
}

#ifdef NON_MATCHING
/* Pendiente: puntuacion 3641 con la configuracion versionada (g = 8 del archivo). Misma estructura de bucle y de escrituras de la primitiva; el original reparte s6 al contador y s7 y fp a las dimensiones del glifo, el C los reparte al reves y desplaza el resto de la planificacion. */
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

/*
 * Lee un entero decimal con signo opcional ('-') en la cadena apuntada por *p y deja *p justo
 * despues de la ultima cifra. Cifra = byte cuyo nibble alto es 3 (0x30..0x3F).
 */
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
    /* La primera cifra se prueba fuera del bucle y el bucle recorre una copia del puntero:
     * asi la cuenta no se pliega con el primer incremento, como en el original. */
    if ((**p >> 4) == 3) {
        t = *p;
        while ((t[n] >> 4) == 3) {
            n++;
        }
    }
    i = n - 1;
    for (; i >= 0; i--) {
        valor += ((*p)[i] & 0xF) * signo;
        signo *= 10;
    }
    *p = *p + n;
    return valor;
}

/*
 * Interprete de guiones de texto: recorre los bytes de `guion` y deja en la lista de glifos un glifo por
 * caracter imprimible, con la posicion que lleva en `pos`. Los codigos de control empiezan por '>'.
 * Devuelve la mascara de opciones de ventana (0x10, 0x20, 0x40, 0x80), o cero si el guion queda en pausa.
 */
#ifdef NON_MATCHING
/* Pendiente: puntuacion 245 con la configuracion versionada (g = 8 del archivo). Reparto de registros: el original inicializa la mascara con el registro cero y el ancho desde la mascara (no desde la paleta), el digito se suma con addiu y no con ori, y la x del cursor se trunca desde el valor devuelto y no desde su copia. */
u32 func_80045498(Objeto* o, u8* guion, BloqueTrabajo* cursor)
{
    PosicionTexto pos;
    s32 reserva[2];
    u8 boton[3];
    s16 y0;
    s32 x0;
    s16 primero;
    s16 ancho;
    u32 mascara;
    u8 abierta;
    s32 paleta;
    s32 q;
    u32 t;
    u8 c;
    u8 g;
    u8 sub;
    s32 i;

    if (D_8006D018[0] == 0) {
        func_80044F20();
    }
    paleta = 0;
    primero = -1;
    abierta = 0;
    mascara = 0;
    ancho = 0;
    pos.x = -0xC8;
    pos.y = -0x3C;
    x0 = -0xC8;
    c = *guion;
    y0 = -0x3C;
    while (c != 0) {
        g = D_8005F940[c];
        if (g != 0) {
            if (primero < 0) {
                primero = D_80069652;
            }
            q = paleta;
            if (g == 0x6C) {
                q = 9;
            } else if (g == 0x6B) {
                q = 0xA;
            } else if (g == 0x68) {
                q = 6;
            } else if (g == 0x6A) {
                q = 8;
            } else if (g == 0x69) {
                q = 7;
            } else if (g == 0x67) {
                q = 5;
            } else if (g == 0x6D) {
                q = 0xB;
            } else if (g == 0x6E) {
                q = 0xC;
            }
            func_800450E8((Glifo*)cursor->fotogramas + (g - 1), q, (OrigenEntrada*)&pos);
            ancho += D_8005FA40[c];
            pos.x += D_8005FA40[c];
        } else if (c == 0xA) {
            if (abierta) {
                func_80045368(primero, ancho);
            }
            ancho = 0;
            abierta = 0;
            primero = -1;
            pos.x = (s16)x0;
            pos.y += 0xD;
        } else if (c == 0x20) {
            ancho += 6;
            pos.x += 6;
        } else if (c == 9) {
            ancho += 0x18;
            pos.x += 0x18;
        } else if (c == 0x3E) {
            guion++;
            sub = *guion;
            if (sub == 0x43) {
                guion++;
                c = *guion;
                guion++;
                if (c == 0x4C) {
                    pos.x = (s16)x0;
                    pos.y = (s16)y0;
                    mascara = 0;
                    o->u78.p = ClearList((NodoLista*)&o->u78);
                } else if (c == 0x58) {
                    goto leer_x;
                } else if (c == 0x59) {
                    y0 = func_800453D0(&guion);
                    pos.y = y0;
                } else if (c == sub) {
                    abierta = 1;
                    leer_x:
                    x0 = func_800453D0(&guion);
                    pos.x = (s16)x0;
                } else if (c == 0x50) {
                    paleta = func_800453D0(&guion);
                }
            } else if (sub == 0x50) {
                guion++;
g = *guion;
                guion++;
                if (g & 8) {
                    mascara |= 0x80;
                }
                if (g & 2) {
                    mascara |= 0x20;
                }
                if (g & 1) {
                    mascara |= 0x10;
                }
                if (g & 4) {
                    mascara |= 0x40;
                }
            } else if (sub == 0x57) {
                guion++;
                t = func_800453D0(&guion);
                if (t == 0) {
                    if (mascara == 0) {
                        mascara = 0x40;
                    }
                    mascara = func_80045D98(mascara);
                    o->w17C = 2;
                } else {
                    o->w22 = 0;
                    o->w17C = t;
                    if (guion[1] != 0) {
                        o->p180 = (struct NodoSecuencia*)guion;
                    }
                    if (abierta) {
                        func_80045368(primero, ancho);
                    }
                    return 0;
                }
            } else if (sub == 0x49) {
                guion++;
                c = *guion;
                guion++;
                if (c == 0x44) {
                    o->w1C = *guion;
                    guion++;
                }
            } else if (sub == 0x42) {
                guion++;
                c = *guion;
                guion++;
                t = *guion;
                guion++;
                if (c == 0x47) {
                    if (t == 7) {
                        t = (ESTADO_PRINCIPAL->r[0xFC] << 8) + ESTADO_PRINCIPAL->r[7];
                    } else {
                        t = ESTADO_PRINCIPAL->r[t];
                    }
                } else if (D_80010000 == 0) {
                    if (t >= 0x2A && t <= 0x34) {
                        t = (D_8006AA70[t + 1] << 8) + D_8006AA70[t];
                    } else {
                        t = D_8006AA70[t];
                    }
                } else {
                    t = D_8006AA70[t];
                }
                t = func_80037D3C(t);
q = 8;
                if ((t & 0xF0000000) == 0) {
                    t <<= 4;
                    q = 7;
                    while (q > 1 && (t & 0xF0000000) == 0) {
                        t <<= 4;
                        q--;
                    }
                }
                if (q > 0) {
                    do {
                        if (primero < 0) {
                            primero = D_80069652;
                        }
                        c = (t >> 28) + 0x30;
                        func_800450E8((Glifo*)cursor->fotogramas + (D_8005F940[c] - 1), paleta, (OrigenEntrada*)&pos);
                        ancho += D_8005FA40[c];
                        pos.x += D_8005FA40[c];
                        q--;
                        t <<= 4;
                    } while (q > 0);
                }
            } else if (sub == 0x44) {
                guion++;
                g = D_8005F920[*guion + ESTADO_PRINCIPAL->r[BANCO_CONFIG] * 8];
                q = paleta;
                boton[2] = 0;
                boton[1] = 0;
                if (g == 0) {
                    boton[0] = 0xAD;
                    q = 6;
                } else if (g == 1) {
                    boton[0] = 0xAF;
                    q = 8;
                } else if (g == 2) {
                    boton[0] = 0xAE;
                    q = 7;
                } else if (g == 3) {
                    boton[0] = 0xAC;
                    q = 5;
                } else if (g == 4) {
                    boton[0] = 0x4C;
                    boton[1] = 0x31;
                } else if (g == 5) {
                    boton[0] = 0x4C;
                    boton[1] = 0x32;
                } else if (g == 6) {
                    boton[0] = 0x52;
                    boton[1] = 0x31;
                } else if (g == 7) {
                    boton[0] = 0x52;
                    boton[1] = 0x32;
                }
                c = boton[0];
i = 0;
                while (c != 0 && i < 3) {
                    g = D_8005F940[c];
                    if (g != 0) {
                        if (primero < 0) {
                            primero = D_80069652;
                        }
                        func_800450E8((Glifo*)cursor->fotogramas + (g - 1), q, (OrigenEntrada*)&pos);
                        ancho += D_8005FA40[c];
                        pos.x += D_8005FA40[c];
                    }
i++;
                    c = boton[i];
                }
            }
        }
        guion++;
        c = *guion;
    }
    if (abierta) {
        func_80045368(primero, ancho);
    }
    return mascara;
}
#else
/*
 * Pendiente de traducir: interprete de guiones de texto que compone una linea de glifos (0x7B4 bytes,
 * 14 llamadas); tiene marco de pila (0x58) y no es una rutina manuscrita.
 */
INCLUDE_ASM("asm/nonmatchings/inicializacion_de_motor", func_80045498);
#endif

#ifdef NON_MATCHING
/* Pendiente: puntuacion 115 con la configuracion versionada (g = 8 del archivo). Mismo flujo, mismas escrituras y mismo orden; el estado del lector se lee como D_8006AA70[0xC] (arreglo) para que el lui de la base pueda separarse de la carga, como en el original. Solo difiere la primera comparacion: el original la hace sobre una copia de a2 en v0 (move v0,a2 ; beqz v0) y GCC compara a2 directamente. */
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
        a2->trabajo.tabla = tabla;
        bloque->fotogramas = tabla->fotogramas;
        a2->w17E = a0 + 0x8000;
        a2->p180 = NULL;
        a1 = (u8*)D_80069590 + D_80069590[a0];
        a2->w26 = D_80069698->w26;
        if (D_8006AA70[0xC] == 1) {
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

u32 func_80045D98(u32 mascara)
{
}

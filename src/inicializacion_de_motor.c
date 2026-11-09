#include "common.h"
#include "globales.h"
#include "objetos.h"
#include "arranque.h"
#include "psyq/LIBETC.H"
#include "psyq/LIBCD.H"
#include "psyq/LIBPRESS.H"
#include "psyq/LIBSPU.H"
#include "motor.h"
#include "niveles.h"

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
extern u32 func_80045D98(u32 mascara);

/*
 * Posicion de la pluma de texto: vista de 32 bits de la misma memoria que OrigenEntrada (x en +0, y en +4).
 * El interprete la escribe con accesos de palabra y func_800450E8 la lee por la direccion con lhu y lb; no se
 * funden en un solo tipo porque la lectura pasaria a lw y cambiaria el codigo de func_800450E8.
 */
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

/*
 * Guarda la tabla de fotogramas de la primera animacion de tipo 8 del objeto y anota en D_8006D018[ranura] el
 * campo h0A del fotograma indicado. El mismo puntero recorre el arreglo de fotogramas y luego apunta al
 * fotograma elegido: con una variable por cada paso la direccion del arreglo se calcula antes del almacen de la
 * tabla y el reparto de registros deja de coincidir.
 */
void func_80044EA8(s32 a0, u32 a1, Objeto* a2)
{
    NodoAnimacion* nodo;
    TablaFotogramas* tabla;
    Fotograma* fotograma;

    nodo = a2->lista;
    while (nodo != NULL && nodo->def->tipo != 8) {
        nodo = nodo->sig;
    }
    tabla = nodo->def->tabla;
    a2->trabajo.tabla = tabla;
    fotograma = tabla->fotogramas;
    fotograma = &fotograma[a1 & 0xFFFF];
    D_8006D018[(s16)a0] = fotograma->h0A;
}

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

/* La paleta es de 16 bits: los llamadores la recortan con andi 0xFFFF antes de pasarla. */
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
/* Pendiente: puntuacion 1501 con la configuracion versionada (g = 8 del archivo). Misma estructura de bucle y de escrituras de la primitiva; el original reparte s1 a la coordenada y y s3 a la v del glifo, s6 al contador y s7 y s8 a las dimensiones, el C los reparte al reves (el contador queda con la menor prioridad de los registros guardados), y carga el puntero a la primitiva (D_80076188) despues de la direccion de la cabeza de la lista, mientras GCC lo adelanta. */
void func_80045150(EntradaLista* e)
{
    Glifo* g;
    s16 y;
    u8* p;
    u16 x;
    u8 v;
    s32 w;
    u8 u;
    s32 i;
    s32 h;
    s32 c;
    s32 color;
    u32* cabeza;
    s32 c_rojo;

    /* El orden de las lecturas del glifo y del elemento, la anchura y la altura menos uno en 32 bits, el
     * componente desplazado del color en una local y D_80076188 sumado tras escribir el indice de paleta
     * son los que acercan el reparto de registros guardados al original. */
    i = 0;
    if (D_80069652 > 0) {
        do {
            g = e->glifo;
            u = g->u;
            x = e->x;
            w = g->w - 1;
            v = g->v;
            y = (s8)e->y;
            h = g->h - 1;
            func_80039CD0(D_80076188);
            if (D_8006966A != 0) {
                c = 0x80 - ((s16)D_800694E2 >> 5);
                c_rojo = c << 16;
                color = c + ((c << 8) + 0x2C000000 + c_rojo);
            } else {
                color = 0x2C808080;
            }
            cabeza = (u32*)(D_8006AE20 + D_8006967C)->org;
            p = (u8*)D_80076188;
            *(s32*)(p + 4) = color;
            *(u32*)p = *cabeza | 0x09000000;
            *cabeza = ((s32)p << 8) >> 8;
            *(s16*)(p + 0x10) = x + w;
            *(s16*)(p + 0x20) = w + x;
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
            *(u16*)(p + 0xE) = D_8006D018[e->idx];
            D_80076188 = D_80076188 + 0x28;
            if (D_8006958C < D_80076188) {
                D_80076188 = D_80069680;
            }
            e++;
            i++;
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

/* Posicion inicial de la pluma de texto: esquina superior izquierda de la ventana, en pixeles con signo. */
#define TEXTO_X_INICIAL (-0xC8)
#define TEXTO_Y_INICIAL (-0x3C)
/* Avance vertical del salto de linea y anchos fijos del espacio y del tabulador. */
#define TEXTO_AVANCE_LINEA 0xD
#define TEXTO_ANCHO_ESPACIO 6
#define TEXTO_ANCHO_TABULADOR 0x18

/*
 * Glifos de color: estos ocho indices de la tabla de glifos fuerzan la paleta de la derecha, sea cual sea la
 * paleta activa (el resto de los glifos usa la que fijo '>CP').
 */
#define GLIFO_COLOR_67 0x67
#define GLIFO_COLOR_68 0x68
#define GLIFO_COLOR_69 0x69
#define GLIFO_COLOR_6A 0x6A
#define GLIFO_COLOR_6B 0x6B
#define GLIFO_COLOR_6C 0x6C
#define GLIFO_COLOR_6D 0x6D
#define GLIFO_COLOR_6E 0x6E
#define PALETA_67 5
#define PALETA_68 6
#define PALETA_69 7
#define PALETA_6A 8
#define PALETA_6B 0xA
#define PALETA_6C 9
#define PALETA_6D 0xB
#define PALETA_6E 0xC

/* Glifos de los cuatro primeros nombres de boton; los otros cuatro se escriben con letras ('L1', 'L2', 'R1', 'R2'). */
#define GLIFO_BOTON_0 0xAD
#define GLIFO_BOTON_1 0xAF
#define GLIFO_BOTON_2 0xAE
#define GLIFO_BOTON_3 0xAC

/* Codigo de control: un '>' seguido de una letra que elige la orden. */
#define CODIGO_CONTROL '>'
#define CTRL_COLOR 'C'          /* '>C?': subordenes de posicion y paleta */
#define CTRL_COLOR_LIMPIAR 'L'  /* '>CL': reinicia la pluma y vacia la lista de glifos */
#define CTRL_COLOR_X 'X'        /* '>CX n': fija la x de inicio de linea */
#define CTRL_COLOR_Y 'Y'        /* '>CY n': fija la y */
#define CTRL_COLOR_PALETA 'P'   /* '>CP n': fija la paleta */
#define CTRL_OPCIONES 'P'       /* '>P b': opciones de ventana (cuatro bits) */
#define CTRL_PAUSA 'W'          /* '>W n': pausa de n cuadros, o cierra la ventana si es cero */
#define CTRL_ICONO 'I'          /* '>I?': icono */
#define CTRL_ICONO_DATO 'D'     /* '>ID b': guarda el byte b en el campo w1C del objeto */
#define CTRL_NUMERO 'B'         /* '>B? n': escribe el valor de una variable */
#define CTRL_NUMERO_GLOBAL 'G'  /* '>BG n': variable del estado principal; otra letra: banco de variables */
#define CTRL_BOTON 'D'          /* '>D n': nombre del boton n segun la configuracion elegida */

/*
 * Opciones de ventana que devuelve el interprete. Los bits del byte de '>P' (1, 2, 4, 8) se reordenan a
 * 0x10, 0x20, 0x40, 0x80; si no hay opciones y la pausa es cero se usa 0x40.
 */
#define OPCION_VENTANA_10 0x10
#define OPCION_VENTANA_20 0x20
#define OPCION_VENTANA_40 0x40
#define OPCION_VENTANA_80 0x80

/*
 * Variables del estado principal: la numero 7 ocupa dos bytes (bajo en r[7], alto en r[0xFC]). En el banco
 * comun, las variables 0x2A..0x34 ocupan dos bytes consecutivos (bajo primero) cuando D_80010000 es cero.
 */
#define VARIABLE_DOBLE 7
#define VARIABLE_DOBLE_ALTO 0xFC
#define BANCO_DOBLE_MIN 0x2A
#define BANCO_DOBLE_MAX 0x34

/*
 * Interprete de guiones de texto: recorre los bytes de `guion` y deja en la lista de glifos un glifo por
 * caracter imprimible, con la posicion que lleva en `pos`. Los codigos de control empiezan por '>'.
 * Devuelve la mascara de opciones de ventana (0x10, 0x20, 0x40, 0x80), o cero si el guion queda en pausa.
 *
 * La x inicial del cursor (x0) es de 16 bits: el estrechamiento del valor devuelto crea un pseudo temporal
 * del retorno que el optimizador toma como canonico, y asi el truncado de la x leida sale desde v0 y no
 * desde la copia en s8 (la rama de y0 ya se comporta asi). El do/while (0) no genera codigo: pondera por un
 * nivel mas la definicion de x0, que suma 8 usos ponderados sobre 387 instrucciones de vida (0,062) y supera
 * al objeto (15 usos sobre 822, 0,055), de modo que x0 ocupa $fp y el objeto se queda en la pila como en el
 * original. Con 7 usos (0,036) el objeto roba $fp.
 * La forma del fuente original que producia este reparto se desconoce.
 */
u32 func_80045498(Objeto* o, u8* guion, BloqueTrabajo* cursor)
{
    /* pos es la pluma de texto (x en +0, y en +4) que func_800450E8 lee por la direccion. */
    PosicionTexto pos;
    /* Reserva sin uso: el original deja 8 bytes entre la pluma y la lista de botones. */
    s32 reserva[2];
    /* Hasta tres caracteres del nombre de un boton, terminados en cero. */
    u8 boton[3];
    s16 y0;
    s16 x0;
    s16 primero;
    s16 ancho;
    u32 mascara;
    u8 abierta;
    u16 paleta;
    u16 pal;
    s32 n;
    s32 d;
    s32 t;
    u8 c;
    u8 g;
    u8 sub;

    if (D_8006D018[0] == 0) {
        func_80044F20();
    }
    paleta = 0;
    primero = -1;
    abierta = 0;
    mascara = 0;
    ancho = 0;
    pos.x = TEXTO_X_INICIAL;
    pos.y = TEXTO_Y_INICIAL;
    x0 = TEXTO_X_INICIAL;
    c = *guion;
    y0 = TEXTO_Y_INICIAL;
    while (c != 0) {
        g = D_8005F940[c];
        if (g != 0) {
            if (primero < 0) {
                primero = D_80069652;
            }
            pal = paleta;
            if (g == GLIFO_COLOR_6C) {
                pal = PALETA_6C;
            } else if (g == GLIFO_COLOR_6B) {
                pal = PALETA_6B;
            } else if (g == GLIFO_COLOR_68) {
                pal = PALETA_68;
            } else if (g == GLIFO_COLOR_6A) {
                pal = PALETA_6A;
            } else if (g == GLIFO_COLOR_69) {
                pal = PALETA_69;
            } else if (g == GLIFO_COLOR_67) {
                pal = PALETA_67;
            } else if (g == GLIFO_COLOR_6D) {
                pal = PALETA_6D;
            } else if (g == GLIFO_COLOR_6E) {
                pal = PALETA_6E;
            }
            func_800450E8((Glifo*)cursor->fotogramas + (g - 1), pal, (OrigenEntrada*)&pos);
            ancho += D_8005FA40[c];
            pos.x += D_8005FA40[c];
        } else if (c == '\n') {
            if (abierta) {
                func_80045368(primero, ancho);
            }
            ancho = 0;
            abierta = 0;
            primero = -1;
            pos.x = (s16)x0;
            pos.y += TEXTO_AVANCE_LINEA;
        } else if (c == ' ') {
            ancho += TEXTO_ANCHO_ESPACIO;
            pos.x += TEXTO_ANCHO_ESPACIO;
        } else if (c == '\t') {
            ancho += TEXTO_ANCHO_TABULADOR;
            pos.x += TEXTO_ANCHO_TABULADOR;
        } else if (c == CODIGO_CONTROL) {
            guion++;
            sub = *guion;
            if (sub == CTRL_COLOR) {
                guion++;
                c = *guion;
                guion++;
                if (c == CTRL_COLOR_LIMPIAR) {
                    pos.x = (s16)x0;
                    pos.y = (s16)y0;
                    mascara = 0;
                    o->u78.p = ClearList((NodoLista*)&o->u78);
                } else if (c == CTRL_COLOR_X) {
                    goto leer_x;
                } else if (c == CTRL_COLOR_Y) {
                    y0 = func_800453D0(&guion);
                    pos.y = y0;
                } else if (c == sub) {
                    abierta = 1;
                    leer_x:
                    do {
                        x0 = func_800453D0(&guion);
                        pos.x = (s16)x0;
                    } while (0);
                } else if (c == CTRL_COLOR_PALETA) {
                    paleta = func_800453D0(&guion);
                }
            } else if (sub == CTRL_OPCIONES) {
                guion++;
                g = *guion;
                guion++;
                if (g & 8) {
                    mascara |= OPCION_VENTANA_80;
                }
                if (g & 2) {
                    mascara |= OPCION_VENTANA_20;
                }
                if (g & 1) {
                    mascara |= OPCION_VENTANA_10;
                }
                if (g & 4) {
                    mascara |= OPCION_VENTANA_40;
                }
            } else if (sub == CTRL_PAUSA) {
                guion++;
                t = func_800453D0(&guion);
                if (t == 0) {
                    if (mascara == 0) {
                        mascara = OPCION_VENTANA_40;
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
            } else if (sub == CTRL_ICONO) {
                guion++;
                c = *guion;
                guion++;
                if (c == CTRL_ICONO_DATO) {
                    o->w1C = *guion;
                    guion++;
                }
            } else if (sub == CTRL_NUMERO) {
                guion++;
                c = *guion;
                guion++;
                t = *guion;
                guion++;
                if (c == CTRL_NUMERO_GLOBAL) {
                    if (t == VARIABLE_DOBLE) {
                        t = (ESTADO_PRINCIPAL->r[VARIABLE_DOBLE_ALTO] << 8) + ESTADO_PRINCIPAL->r[VARIABLE_DOBLE];
                    } else {
                        t = ESTADO_PRINCIPAL->r[t];
                    }
                } else if (D_80010000 == 0) {
                    if (t >= BANCO_DOBLE_MIN && t <= BANCO_DOBLE_MAX) {
                        t = (D_8006AA70[t + 1] << 8) + D_8006AA70[t];
                    } else {
                        t = D_8006AA70[t];
                    }
                } else {
                    t = D_8006AA70[t];
                }
                /* Valor en BCD de ocho digitos: se descartan los ceros de la izquierda (queda al menos uno). */
                t = func_80037D3C(t);
                n = 8;
                if ((t & 0xF0000000) == 0) {
                    t <<= 4;
                    n = 7;
                    while (n > 1 && (t & 0xF0000000) == 0) {
                        t <<= 4;
                        n--;
                    }
                }
                if (n > 0) {
                    do {
                        if (primero < 0) {
                            primero = D_80069652;
                        }
                        d = ((u32)t >> 28) + '0';
                        func_800450E8((Glifo*)cursor->fotogramas + (D_8005F940[d] - 1), paleta, (OrigenEntrada*)&pos);
                        ancho += D_8005FA40[d];
                        pos.x += D_8005FA40[d];
                        n--;
                        t <<= 4;
                    } while (n > 0);
                }
            } else if (sub == CTRL_BOTON) {
                guion++;
                g = D_8005F920[*guion + ESTADO_PRINCIPAL->r[BANCO_CONFIG] * 8];
                pal = paleta;
                boton[2] = 0;
                boton[1] = 0;
                if (g == 0) {
                    boton[0] = GLIFO_BOTON_0;
                    pal = PALETA_68;
                } else if (g == 1) {
                    boton[0] = GLIFO_BOTON_1;
                    pal = PALETA_6A;
                } else if (g == 2) {
                    boton[0] = GLIFO_BOTON_2;
                    pal = PALETA_69;
                } else if (g == 3) {
                    boton[0] = GLIFO_BOTON_3;
                    pal = PALETA_67;
                } else if (g == 4) {
                    boton[0] = 'L';
                    boton[1] = '1';
                } else if (g == 5) {
                    boton[0] = 'L';
                    boton[1] = '2';
                } else if (g == 6) {
                    boton[0] = 'R';
                    boton[1] = '1';
                } else if (g == 7) {
                    boton[0] = 'R';
                    boton[1] = '2';
                }
                c = boton[0];
                t = 0;
                while (c != 0 && t < 3) {
                    g = D_8005F940[c];
                    if (g != 0) {
                        if (primero < 0) {
                            primero = D_80069652;
                        }
                        func_800450E8((Glifo*)cursor->fotogramas + (g - 1), pal, (OrigenEntrada*)&pos);
                        ancho += D_8005FA40[c];
                        pos.x += D_8005FA40[c];
                    }
                    t++;
                    c = boton[t];
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

#ifdef NON_MATCHING
/* Pendiente: puntuacion 115 con la configuracion versionada (g = 8 del archivo). Mismo flujo, mismas escrituras y mismo orden; el estado del lector se lee como D_8006AA70[0xC] (arreglo) para que el lui de la base pueda separarse de la carga, como en el original. Solo difiere la primera comparacion: el original la hace sobre una copia de a2 en v0 (move v0,a2 ; beqz v0) y GCC compara a2 directamente, porque el CSE sustituye cualquier copia local del parametro por el primer pseudo de su clase (copia previa, bandera entera y copia dentro de un do/while dan 115; a diferencia de un retorno estrechado a 16 bits, aqui no se crea un temporal canonico). El parametro entra con una copia propia (pseudo 82) y la prueba la lee directamente; una copia local no sobrevive al CSE, y un par `a2--; a2++` sobre el parametro tampoco: el CSE y el combinador lo pliegan y la prueba sigue sobre a2. */
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

/*
 * Rutina vacia del original: func_80045498 la llama con la mascara de opciones en a0 y recoge v0 como
 * nueva mascara, por eso lleva parametro y valor de retorno aunque no emita codigo.
 */
u32 func_80045D98(u32 mascara)
{
}
